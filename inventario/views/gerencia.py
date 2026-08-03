from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from datetime import datetime
from django.contrib import messages # 🚀 CORREÇÃO 1: Importação de mensagens de alerta
import json

# Importações do DRF
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from inventario.models import Vendas, Clientes, Produtos
from inventario.models.configuracoes import ConfiguracaoSistema # 🚀 CORREÇÃO 2: Importação da nova tabela de configurações
from inventario.services.fiscal_service import FiscalService
from inventario.serializers import (
    CancelamentoSerializer, EmailSerializer, 
    DevolucaoSerializer, InutilizacaoSerializer, CorrecaoSerializer
)

# ==========================================
# TELAS DO MÓDULO FISCAL E GERENCIAL
# ==========================================
def tela_painel_gerencia(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/painel_gerencia.html')

def tela_centro_fiscal(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/centro_fiscal_painel.html')

def tela_relatorios_painel(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/relatorios_painel.html')

def emitir_notas(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/emitir_notas.html', {
        'vendas_pendentes': Vendas.objects.all().order_by('-id'),
        'todos_clientes': Clientes.objects.all().order_by('nome')
    })

def tela_consulta_nfe(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    vendas = Vendas.objects.filter(modelo_fiscal='55').exclude(status_fiscal='SEM_NOTA').exclude(status='DEVOLUCAO_ENTRADA').order_by('-id')
    return render(request, 'inventario/consulta_nfe.html', {'vendas_processadas': vendas, 'todos_clientes': Clientes.objects.all().order_by('nome')})

def tela_consulta_nfce(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    vendas = Vendas.objects.filter(modelo_fiscal='65').exclude(status_fiscal='SEM_NOTA').order_by('-id')
    return render(request, 'inventario/consulta_nfce.html', {'vendas_processadas': vendas, 'todos_clientes': Clientes.objects.all().order_by('nome')})

def tela_devolucoes(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/devolucoes.html', {'devolucoes': Vendas.objects.filter(status='DEVOLUCAO_ENTRADA').order_by('-id')})


# ==========================================
# APIs (DJANGO REST FRAMEWORK)
# ==========================================

@api_view(['GET'])
def api_detalhes_venda(request):
    try:
        venda = Vendas.objects.get(id=request.GET.get('venda_id'))
        carrinho = json.loads(venda.cupom_texto) if venda.cupom_texto else []
        itens = [{
            'cod_interno': i.get('id', ''), 'descricao': i.get('nome', ''), 
            'quantidade': i.get('qtd', 1), 'valor_unitario': i.get('preco_desconto', i.get('preco_venda', 0)),
            'total': float(i.get('qtd', 1)) * float(i.get('preco_desconto', i.get('preco_venda', 0)))
        } for i in carrinho]
        
        forma_pgto = "Não Informado"
        try:
            pag_data = json.loads(venda.pagamentos_texto) if venda.pagamentos_texto else None
            if isinstance(pag_data, list) and len(pag_data) > 0: forma_pgto = pag_data[0].get('forma', 'Pagamento Múltiplo')
        except Exception: pass
                
        cli_id = Clientes.objects.filter(nome__iexact=str(venda.cliente).strip()).first().id if venda.cliente and str(venda.cliente).strip().lower() != 'none' and Clientes.objects.filter(nome__iexact=str(venda.cliente).strip()).first() else None
        return Response({'sucesso': True, 'itens': itens, 'venda_cliente_id': cli_id, 'forma_pagamento': forma_pgto})
    except Vendas.DoesNotExist:
        return Response({'sucesso': False, 'erro': 'Venda não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def api_buscar_cliente(request):
    try:
        cli = Clientes.objects.get(id=request.GET.get('cliente_id'))
        doc = cli.cnpj if cli.tipo_pessoa == 'PJ' and cli.cnpj else cli.cpf
        return Response({
            'sucesso': True, 'nome': cli.nome, 'cpf_cnpj': doc or cli.cnpj or cli.cpf, 
            'cep': getattr(cli, 'cep', ''), 'endereco': getattr(cli, 'endereco', ''),
            'numero': getattr(cli, 'numero', ''), 'complemento': getattr(cli, 'complemento', ''),
            'bairro': getattr(cli, 'bairro', ''), 'cidade': getattr(cli, 'cidade', ''),
            'estado': getattr(cli, 'estado', getattr(cli, 'uf', '')), 'email': getattr(cli, 'email', ''),
            'inscricao_estadual': getattr(cli, 'inscricao_estadual', '')
        })
    except Clientes.DoesNotExist:
        return Response({'sucesso': False, 'erro': 'Cliente não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def api_consultar_status_nfe(request):
    """
    Consulta o status do documento fiscal na SEFAZ (Via Notaas)
    """
    try:
        venda = Vendas.objects.get(id=request.GET.get('venda_id'))
        resultado = FiscalService.consultar_status(venda)
        
        # O FiscalService agora retorna 'AUTORIZADO', 'PROCESSANDO_NUVEM' ou 'ERRO_REJEICAO'
        if resultado.get('sucesso'):
            venda.refresh_from_db()
            resultado['link_pdf'] = venda.link_pdf or ''
            resultado['link_xml'] = venda.link_xml or ''
            
        return Response(resultado)
    except Vendas.DoesNotExist:
        return Response({'sucesso': False, 'erro': 'Venda não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'sucesso': False, 'erro': str(e)})
    

@api_view(['POST'])
def api_cancelar_nota(request):
    serializer = CancelamentoSerializer(data=request.data)
    if serializer.is_valid():
        try:
            venda = Vendas.objects.get(id=serializer.validated_data['venda_id'])
            return Response(FiscalService.cancelar_nota(venda, serializer.validated_data['justificativa']))
        except Vendas.DoesNotExist:
            return Response({'sucesso': False, 'erro': 'Venda não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'sucesso': False, 'erro': 'Dados inválidos.', 'detalhes': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def api_enviar_email_nota(request):
    serializer = EmailSerializer(data=request.data)
    if serializer.is_valid():
        try:
            venda = Vendas.objects.get(id=serializer.validated_data['venda_id'])
            return Response(FiscalService.enviar_email(venda, serializer.validated_data['email']))
        except Vendas.DoesNotExist:
            return Response({'sucesso': False, 'erro': 'Venda não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'sucesso': False, 'erro': 'E-mail inválido.'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def api_acionar_emissao(request):
    """
    Dispara a emissão de nota de saída para a Gerando Nota Fácil
    """
    try:
        venda = Vendas.objects.get(id=request.data.get('venda_id'))
        resultado = FiscalService.emitir_saida(venda, request.data)
        
        if resultado.get('sucesso'):
            venda.refresh_from_db()
            resultado['link_pdf'] = venda.link_pdf or ''
            resultado['link_xml'] = venda.link_xml or ''
            resultado['id_transacao'] = venda.id_transacao_api or venda.chave_acesso or ''
            
        return Response(resultado)
    except Vendas.DoesNotExist:
        return Response({'sucesso': False, 'erro': 'Venda não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'sucesso': False, 'erro': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
def api_emitir_devolucao(request):
    serializer = DevolucaoSerializer(data=request.data)
    if serializer.is_valid():
        try:
            dados = serializer.validated_data
            venda = Vendas.objects.get(id=dados['venda_id'])
            
            valor_total_dev = sum([float(i['quantidade']) * float(Produtos.objects.filter(cod_interno=i['cod_interno']).first().preco_venda) for i in dados['itens_devolvidos'] if Produtos.objects.filter(cod_interno=i['cod_interno']).first()])
            
            nova_devolucao = Vendas.objects.create(
                data_venda=timezone.now(), valor_total=valor_total_dev,
                status='DEVOLUCAO_ENTRADA', status_fiscal='PROCESSANDO_NUVEM', modelo_fiscal='55',
                cliente=venda.cliente, numero_nota=f"Ref a Venda Orig. #{venda.id}",
                motivo_erro=dados['justificativa'],
                cupom_texto=json.dumps(request.data.get('itens_devolvidos', []))
            )
            return Response(FiscalService.emitir_devolucao(venda, nova_devolucao, request.data))
        except Exception as e:
            return Response({'sucesso': False, 'erro': str(e)})
    return Response({'sucesso': False, 'erro': 'Dados inconsistentes.', 'detalhes': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def api_sincronizar_lote(request):
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
    return Response({'sucesso': True, 'mensagem': f"{atualizadas} documentos sincronizados com sucesso."})

@api_view(['POST'])
def api_inutilizar_numeracao(request):
    serializer = InutilizacaoSerializer(data=request.data)
    if serializer.is_valid():
        return Response(FiscalService.inutilizar_numeracao(serializer.validated_data))
    return Response({'sucesso': False, 'erro': 'Campos inválidos.', 'detalhes': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def api_emitir_cce(request):
    serializer = CorrecaoSerializer(data=request.data)
    if serializer.is_valid():
        try:
            venda = Vendas.objects.get(id=serializer.validated_data['venda_id'])
            return Response(FiscalService.emitir_cce(venda, serializer.validated_data['correcao']))
        except Vendas.DoesNotExist:
            return Response({'sucesso': False, 'erro': 'Venda não encontrada.'})
    return Response({'sucesso': False, 'erro': 'Texto de correção inválido.'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def api_exportar_zip(request):
    ano = request.data.get('ano')
    mes = request.data.get('mes')
    return Response({'sucesso': True, 'mensagem': f"Backup de {mes}/{ano} solicitado. Link será enviado por e-mail."})

def imprimir_danfe_nfe(request, venda_id):
    """
    Abre o PDF (DANFE) da Nota. 
    O Django atua como proxy, baixando da Notaas com a API Key e entregando ao navegador.
    """
    try:
        venda = Vendas.objects.get(id=venda_id)
        
        # O Django vai até a API buscar o PDF usando a x-api-key
        arquivo_binario = FiscalService.download_arquivo(venda, tipo='pdf')
        
        if arquivo_binario:
            resp = HttpResponse(arquivo_binario, content_type='application/pdf')
            # 'inline' faz o PDF abrir direto na tela. Se quiser forçar o download, troque para 'attachment'
            resp['Content-Disposition'] = f'inline; filename="DANFE_{venda_id}.pdf"'
            return resp
            
        return HttpResponse("<p>Documento DANFE indisponível. A nota pode não estar autorizada na SEFAZ.</p>", status=404)
    except Exception as e:
        return HttpResponse(f"Erro interno ao gerar PDF: {str(e)}", status=500)


def baixar_xml_nfe(request, venda_id):
    """
    Faz o download do arquivo XML autorizado da Nota.
    """
    try:
        venda = Vendas.objects.get(id=venda_id)
        
        # O Django vai até a API buscar o XML usando a x-api-key
        arquivo_binario = FiscalService.download_arquivo(venda, tipo='xml')
        
        if arquivo_binario:
            resp = HttpResponse(arquivo_binario, content_type='application/xml')
            resp['Content-Disposition'] = f'attachment; filename="XML_{venda_id}.xml"'
            return resp
            
        return HttpResponse("<p>XML indisponível. A nota pode não estar autorizada na SEFAZ.</p>", status=404)
    except Exception as e:
        return HttpResponse(f"Erro interno ao gerar XML: {str(e)}", status=500)
    
@csrf_exempt
def api_webhook_notaas(request):
    """
    Endpoint para receber notificações automáticas da Notaas (SEFAZ).
    Lembre-se de alterar a rota no seu urls.py de 'webhook_gnf' para 'webhook_notaas'.
    """
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido.'}, status=405)
        
    try:
        payload = json.loads(request.body)
        
        # A Notaas envia o tipo de evento na raiz e os dados dentro do objeto "data"
        event = payload.get('event', '')
        data = payload.get('data', {})
        
        id_transacao = data.get('invoiceId')
        chave_nfe = data.get('chaveAcesso', '')
        motivo = data.get('xMotivo', data.get('errorMessage', ''))

        if not id_transacao:
            return JsonResponse({'erro': 'ID da transação não fornecido.'}, status=400)

        # Localiza a venda correspondente pelo ID da Notaas
        venda = Vendas.objects.filter(id_transacao_api=id_transacao).first()
        if not venda:
            return JsonResponse({'erro': 'Venda correspondente não encontrada no ERP.'}, status=404)

        # Processa os eventos específicos da Notaas (NF-e ou NFC-e)
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
        return JsonResponse({'status': 'sucesso', 'mensagem': 'Webhook Notaas processado com sucesso.'})
        
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao processar Webhook: {str(e)}'}, status=500)

def relatorio_comissao(request):
    # Importação local para garantir que pegamos os usuários
    from inventario.models import Usuarios 
    
    # Pega o mês e ano atual como padrão
    hoje = datetime.now()
    mes_atual = int(request.GET.get('mes', hoje.month))
    ano_atual = int(request.GET.get('ano', hoje.year))
    
    # 🚀 NOVO: Captura o colaborador selecionado no filtro
    vendedor_selecionado = request.GET.get('vendedor', '')

    # Busca apenas as vendas finalizadas dentro desse mês e ano
    vendas_mes = Vendas.objects.filter(
        data_venda__month=mes_atual,
        data_venda__year=ano_atual,
        status='VENDA'
    ).exclude(vendedor__isnull=True).exclude(vendedor='')
    
    # 🚀 NOVO: Aplica o filtro de vendedor, se algum foi selecionado
    if vendedor_selecionado:
        vendas_mes = vendas_mes.filter(vendedor=vendedor_selecionado)

    # Agrupa os valores pelo nome do vendedor e soma as vendas e comissões
    dados_comissao = vendas_mes.values('vendedor').annotate(
        total_vendas=Sum('valor_total'),
        total_comissao=Sum('valor_comissao')
    ).order_by('-total_comissao')

    # Lista para o filtro de meses na tela
    meses = [
        {'valor': 1, 'nome': 'Janeiro'}, {'valor': 2, 'nome': 'Fevereiro'},
        {'valor': 3, 'nome': 'Março'}, {'valor': 4, 'nome': 'Abril'},
        {'valor': 5, 'nome': 'Maio'}, {'valor': 6, 'nome': 'Junho'},
        {'valor': 7, 'nome': 'Julho'}, {'valor': 8, 'nome': 'Agosto'},
        {'valor': 9, 'nome': 'Setembro'}, {'valor': 10, 'nome': 'Outubro'},
        {'valor': 11, 'nome': 'Novembro'}, {'valor': 12, 'nome': 'Dezembro'}
    ]
    
    # 🚀 NOVO: Busca todos os colaboradores para montar o menu suspenso
    vendedores = Usuarios.objects.all().order_by('login')

    context = {
        'dados_comissao': dados_comissao,
        'mes_selecionado': mes_atual,
        'ano_selecionado': ano_atual,
        'vendedor_selecionado': vendedor_selecionado,
        'meses': meses,
        'vendedores': vendedores,
    }
    
    return render(request, 'inventario/relatorio_comissao.html', context)

def tela_configuracoes_sistema(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    
    # Busca a configuração (se não existir, cria a primeira com o padrão de 15 dias)
    config, created = ConfiguracaoSistema.objects.get_or_create(id=1)
    
    return render(request, 'inventario/configuracoes_sistema.html', {'config': config})

def salvar_configuracoes_sistema(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
        
    if request.method == 'POST':
        dias = request.POST.get('dias_seguranca')
        try:
            config = ConfiguracaoSistema.objects.get(id=1)
            config.dias_seguranca_estoque = int(dias)
            config.save()
            messages.success(request, "Configurações do sistema atualizadas com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao salvar configurações: {e}")
            
    return redirect('tela_configuracoes_sistema')
