from django.db.models import Q
from inventario.models import Clientes, ConfiguracaoPontos, Vendas

def processar_listagem_clientes(query=''):
    """ Aplica os filtros de busca e calcula o cashback em reais dinamicamente """
    clientes_db = Clientes.objects.all()
    if query:
        clientes_db = clientes_db.filter(
            Q(nome__icontains=query) | Q(cpf__icontains=query) | Q(telefone__icontains=query)
        )

    conf_cliente = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()
    taxa_resgate = float(conf_cliente.pontos_necessarios_resgate) if conf_cliente and conf_cliente.pontos_necessarios_resgate else 0
    valor_moeda = float(conf_cliente.valor_resgate_reais or 1.0) if conf_cliente else 0

    lista_clientes = []
    for c in clientes_db:
        pontos = int(c.pontos) if c.pontos else 0
        c.saldo_reais = (pontos / taxa_resgate) * valor_moeda if taxa_resgate > 0 else 0.00
        lista_clientes.append(c)

    return lista_clientes

def salvar_cliente(dados, cliente_id=None):
    """ Valida barreiras fiscais e duplicação antes de salvar na base de dados """
    cep_teste = dados.get('cep', '').strip()
    numero_teste = dados.get('numero', '').strip()

    if not cep_teste or not numero_teste:
        raise ValueError("⚠️ Operação bloqueada: O CEP e o Número são obrigatórios para emissão de Nota Fiscal.")

    tipo_pessoa = dados.get('tipo_pessoa', 'PF')
    cpf_digitado = dados.get('cpf', '').strip()
    cnpj_digitado = dados.get('cnpj', '').strip()

    if tipo_pessoa == 'PF' and cpf_digitado:
        query = Clientes.objects.filter(cpf=cpf_digitado)
        if cliente_id: query = query.exclude(id=cliente_id)
        if query.first(): 
            raise ValueError(f"⚠️ Erro de Duplicidade: O CPF {cpf_digitado} já está em uso.")
            
    elif tipo_pessoa == 'PJ' and cnpj_digitado:
        query = Clientes.objects.filter(cnpj=cnpj_digitado)
        if cliente_id: query = query.exclude(id=cliente_id)
        if query.first(): 
            raise ValueError(f"⚠️ Erro de Duplicidade: O CNPJ {cnpj_digitado} já está em uso.")

    if cliente_id and str(cliente_id).strip():
        cliente = Clientes.objects.get(id=cliente_id)
    else:
        cliente = Clientes()

    cliente.tipo_pessoa = tipo_pessoa
    cliente.nome = dados.get('nome', '')
    cliente.telefone = dados.get('telefone', '')
    cliente.email = dados.get('email', '')

    if tipo_pessoa == 'PF':
        cliente.cpf = cpf_digitado
        cliente.cnpj = None
        cliente.razao_social = None
        cliente.inscricao_estadual = None
        cliente.ind_ie = '9'
    else:
        cliente.cnpj = cnpj_digitado
        cliente.razao_social = dados.get('razao_social', '')
        cliente.inscricao_estadual = dados.get('inscricao_estadual', '')
        cliente.cpf = None
        cliente.ind_ie = dados.get('ind_ie', '9')

    cliente.cep = dados.get('cep', '')
    cliente.endereco = dados.get('endereco', '') 
    cliente.numero = dados.get('numero', '')
    cliente.complemento = dados.get('complemento', '')
    cliente.bairro = dados.get('bairro', '')
    cliente.cidade = dados.get('cidade', '')
    cliente.estado = dados.get('estado', '')
    cliente.codigo_ibge = dados.get('codigo_ibge', '')

    tipos = []
    if dados.get('check_cliente'): tipos.append("CLIENTE")
    if dados.get('check_pintor'): tipos.append("PINTOR")
    cliente.tipo = ", ".join(tipos) if tipos else "CLIENTE"

    cliente.save()
    return cliente

def buscar_historico(cliente_id, termo_busca):
    """ Centraliza a lógica do histórico, pesquisando por ID ou nome legado """
    historico = []
    if cliente_id and str(cliente_id).isdigit():
        historico = Vendas.objects.filter(cliente_link_id=cliente_id, status__iexact='FATURADO').order_by('-data_venda')
        if not historico.exists():
            cliente_banco = Clientes.objects.filter(id=cliente_id).first()
            if cliente_banco:
                historico = Vendas.objects.filter(cliente__iexact=cliente_banco.nome, status__iexact='FATURADO').order_by('-data_venda')
    elif termo_busca:
        historico = Vendas.objects.filter(cliente__iexact=termo_busca, status__iexact='FATURADO').order_by('-data_venda')
    
    dados = []
    for v in historico:
        nome_vendedor = 'SISTEMA'
        if getattr(v, 'vendedor', None):
            nome_vendedor = getattr(v.vendedor, 'login', str(v.vendedor))

        dados.append({
            'data': v.data_venda.strftime('%d/%m/%Y') if getattr(v, 'data_venda', None) else '--/--/----',
            'valor_total': f"{v.valor_total:.2f}" if getattr(v, 'valor_total', None) else "0.00",
            'codigo_venda': v.id,
            'vendedor': nome_vendedor.upper()
        })
    return dados
    
def atualizar_regras_fidelidade(acumulo_cliente, acumulo_pintor):
    """ Salva as regras de pontos com divisor padrão """
    resgate_universal = 100
    conf_cli, _ = ConfiguracaoPontos.objects.get_or_create(tipo_usuario='CLIENTE')
    conf_cli.pontos_por_real = acumulo_cliente
    conf_cli.pontos_necessarios_resgate = resgate_universal
    conf_cli.valor_resgate_reais = 1.00
    conf_cli.save()

    conf_pin, _ = ConfiguracaoPontos.objects.get_or_create(tipo_usuario='PINTOR')
    conf_pin.pontos_por_real = acumulo_pintor
    conf_pin.pontos_necessarios_resgate = resgate_universal 
    conf_pin.valor_resgate_reais = 1.00
    conf_pin.save()
    