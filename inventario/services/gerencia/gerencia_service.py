import json
from datetime import datetime
from django.utils import timezone
from django.db.models import Sum
from inventario.models import Vendas, Clientes, Produtos, Usuarios
from inventario.services.fiscal_service import FiscalService

def obter_vendas_pendentes_nfe():
    # Retorna vendas faturadas que ainda aguardam emissão de nota
    return Vendas.objects.filter(status='FATURADO', status_fiscal='SEM_NOTA').order_by('-id')

def obter_vendas_emitidas_nfe():
    # Retorna vendas com NFe (modelo 55) já processadas
    return Vendas.objects.filter(modelo_fiscal='55').exclude(status_fiscal='SEM_NOTA').exclude(status='DEVOLUCAO_ENTRADA').order_by('-id')

def obter_vendas_emitidas_nfce():
    # Retorna vendas com NFCe (modelo 65) já processadas
    return Vendas.objects.filter(modelo_fiscal='65').exclude(status_fiscal='SEM_NOTA').order_by('-id')

def obter_devolucoes():
    # Retorna o histórico de notas de devolução
    return Vendas.objects.filter(status='DEVOLUCAO_ENTRADA').order_by('-id')

def obter_todos_clientes():
    # Retorna o catálogo de clientes para dropdowns
    return Clientes.objects.all().order_by('nome')

def obter_detalhes_venda(venda_id):
    # Extrai e formata os itens do JSON do cupão e a forma de pagamento
    venda = Vendas.objects.get(id=venda_id)
    carrinho = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    
    itens = [{
        'cod_interno': i.get('id', ''), 'descricao': i.get('nome', ''), 
        'quantidade': i.get('qtd', 1), 'valor_unitario': i.get('preco_desconto', i.get('preco_venda', 0)),
        'total': float(i.get('qtd', 1)) * float(i.get('preco_desconto', i.get('preco_venda', 0)))
    } for i in carrinho]
    
    forma_pgto = "Não Informado"
    try:
        pag_data = json.loads(venda.pagamentos_texto) if venda.pagamentos_texto else None
        if isinstance(pag_data, list) and len(pag_data) > 0: 
            forma_pgto = pag_data[0].get('forma', 'Pagamento Múltiplo')
    except Exception: pass
            
    cli = Clientes.objects.filter(nome__iexact=str(venda.cliente).strip()).first()
    cli_id = cli.id if venda.cliente and str(venda.cliente).strip().lower() != 'none' and cli else None
    
    return itens, cli_id, forma_pgto

def obter_dados_cliente(cliente_id):
    # Formata o dicionário de dados do cliente para a SEFAZ
    cli = Clientes.objects.get(id=cliente_id)
    doc = cli.cnpj if cli.tipo_pessoa == 'PJ' and cli.cnpj else cli.cpf
    return {
        'nome': cli.nome, 'cpf_cnpj': doc or cli.cnpj or cli.cpf, 
        'cep': getattr(cli, 'cep', ''), 'endereco': getattr(cli, 'endereco', ''),
        'numero': getattr(cli, 'numero', ''), 'complemento': getattr(cli, 'complemento', ''),
        'bairro': getattr(cli, 'bairro', ''), 'cidade': getattr(cli, 'cidade', ''),
        'estado': getattr(cli, 'estado', getattr(cli, 'uf', '')), 'email': getattr(cli, 'email', ''),
        'inscricao_estadual': getattr(cli, 'inscricao_estadual', '')
    }

def processar_devolucao_entrada(dados_validados, dados_requisicao):
    # Calcula totais e cria o registo da NF de devolução no banco
    venda = Vendas.objects.get(id=dados_validados['venda_id'])
    
    valor_total_dev = sum([
        float(i['quantidade']) * float(Produtos.objects.filter(cod_interno=i['cod_interno']).first().preco_venda) 
        for i in dados_validados['itens_devolvidos'] if Produtos.objects.filter(cod_interno=i['cod_interno']).first()
    ])
    
    nova_devolucao = Vendas.objects.create(
        data_venda=timezone.now(), valor_total=valor_total_dev,
        status='DEVOLUCAO_ENTRADA', status_fiscal='PROCESSANDO_NUVEM', modelo_fiscal='55',
        cliente=venda.cliente, numero_nota=f"Ref a Venda Orig. #{venda.id}",
        motivo_erro=dados_validados['justificativa'],
        cupom_texto=json.dumps(dados_requisicao.get('itens_devolvidos', []))
    )
    return FiscalService.emitir_devolucao(venda, nova_devolucao, dados_requisicao)

def processar_webhook_notaas(payload):
    # Processa o retorno assíncrono da SEFAZ e atualiza a Venda
    event = payload.get('event', '')
    data = payload.get('data', {})
    id_transacao = data.get('invoiceId')
    chave_nfe = data.get('chaveAcesso', '')
    motivo = data.get('xMotivo', data.get('errorMessage', ''))

    if not id_transacao:
        raise ValueError('ID da transação não fornecido.')

    venda = Vendas.objects.filter(id_transacao_api=id_transacao).first()
    if not venda:
        raise ValueError('Venda correspondente não encontrada no ERP.')

    if event in ['nfe.issued', 'nfce.issued']:
        venda.status_fiscal = 'AUTORIZADO'
        if chave_nfe:
            venda.chave_acesso = chave_nfe
        venda.motivo_erro = None
    elif event in ['nfe.cancelled', 'nfce.cancelled']:
        venda.status_fiscal = 'CANCELADO'
        venda.status = 'CANCELADA'
    elif event in ['nfe.error', 'nfce.error']:
        venda.status_fiscal = 'ERRO_REJEICAO'
        venda.motivo_erro = motivo

    venda.save()

def processar_sincronizacao_lote():
    # Consulta a SEFAZ para notas travadas e destrava-as localmente
    notas_pendentes = Vendas.objects.filter(status_fiscal__in=['PROCESSANDO', 'PROCESSANDO_NUVEM', 'DEVOLUCOES_EM_PROCESSAMENTO'])
    atualizadas = 0
    
    for venda in notas_pendentes:
        resp = FiscalService.consultar_status(venda)
        if resp.get('sucesso') and resp.get('status_fiscal') not in ['PROCESSANDO', 'PROCESSANDO_NUVEM', 'DEVOLUCOES_EM_PROCESSAMENTO']:
            atualizadas += 1
            if venda.status == 'DEVOLUCAO_ENTRADA' and venda.status_fiscal == 'AUTORIZADO':
                try:
                    v_orig = Vendas.objects.get(id=int(''.join(filter(str.isdigit, venda.numero_nota))))
                    v_orig.status = 'DEVOLVIDO'
                    v_orig.save()
                except Exception: pass
    return atualizadas

def calcular_comissao_vendedores(mes_atual, ano_atual, vendedor_selecionado, usuario_logado, perfil):
    # Agrega e soma as comissões bloqueando visões indevidas para o perfil Vendedor
    vendas_mes = Vendas.objects.filter(
        data_venda__month=mes_atual, data_venda__year=ano_atual, status='VENDA'
    ).exclude(vendedor__isnull=True).exclude(vendedor='')
    
    if perfil not in ['Gerente', 'Supervisor', 'Administrador']:
        vendedor_selecionado = usuario_logado
        vendedores = Usuarios.objects.filter(login=usuario_logado)
    else:
        vendedores = Usuarios.objects.exclude(perfil='DEV').order_by('login')

    if vendedor_selecionado:
        vendas_mes = vendas_mes.filter(vendedor=vendedor_selecionado)

    dados_comissao = vendas_mes.values('vendedor').annotate(
        total_vendas=Sum('valor_total'), total_comissao=Sum('valor_comissao')
    ).order_by('-total_comissao')
    
    meses = [
        {'valor': 1, 'nome': 'Janeiro'}, {'valor': 2, 'nome': 'Fevereiro'},
        {'valor': 3, 'nome': 'Março'}, {'valor': 4, 'nome': 'Abril'},
        {'valor': 5, 'nome': 'Maio'}, {'valor': 6, 'nome': 'Junho'},
        {'valor': 7, 'nome': 'Julho'}, {'valor': 8, 'nome': 'Agosto'},
        {'valor': 9, 'nome': 'Setembro'}, {'valor': 10, 'nome': 'Outubro'},
        {'valor': 11, 'nome': 'Novembro'}, {'valor': 12, 'nome': 'Dezembro'}
    ]
    
    return dados_comissao, vendedores, vendedor_selecionado, meses
