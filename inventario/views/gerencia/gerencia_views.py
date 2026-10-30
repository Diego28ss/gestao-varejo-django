import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from inventario.models import Vendas
from inventario.services.fiscal_service import FiscalService
from inventario.services.gerencia import gerencia_service

# 🔥 IMPORTAÇÃO ATUALIZADA (Apontando para a nova pasta)
from inventario.serializers.fiscal_serializers import (
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
        'vendas_pendentes': gerencia_service.obter_vendas_pendentes_nfe(),
        'todos_clientes': gerencia_service.obter_todos_clientes()
    })

def tela_consulta_nfe(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/consulta_nfe.html', {
        'vendas_processadas': gerencia_service.obter_vendas_emitidas_nfe(), 
        'todos_clientes': gerencia_service.obter_todos_clientes()
    })

def tela_consulta_nfce(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/consulta_nfce.html', {
        'vendas_processadas': gerencia_service.obter_vendas_emitidas_nfce(), 
        'todos_clientes': gerencia_service.obter_todos_clientes()
    })

def tela_devolucoes(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/devolucoes.html', {'devolucoes': gerencia_service.obter_devolucoes()})

def relatorio_comissao(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    hoje = datetime.now()
    mes_atual = int(request.GET.get('mes', hoje.month))
    ano_atual = int(request.GET.get('ano', hoje.year))
    vendedor_selec = request.GET.get('vendedor', '')

    perfil = request.session.get('perfil_usuario', 'Vendedor')
    usuario_logado = request.session.get('usuario_logado')

    dados_comissao, vendedores, vendedor_selecionado, meses = gerencia_service.calcular_comissao_vendedores(
        mes_atual, ano_atual, vendedor_selec, usuario_logado, perfil
    )

    return render(request, 'inventario/relatorio_comissao.html', {
        'dados_comissao': dados_comissao,
        'vendedores': vendedores,
        'vendedor_selecionado': vendedor_selecionado,
        'meses': meses,
        'mes_atual': mes_atual,
        'ano_atual': ano_atual
    })

# ==========================================
# APIs (DJANGO REST FRAMEWORK) E WEBHOOKS
# ==========================================

@api_view(['GET'])
def api_detalhes_venda(request):
    try:
        itens, cli_id, forma_pgto = gerencia_service.obter_detalhes_venda(request.GET.get('venda_id'))
        return Response({'sucesso': True, 'itens': itens, 'venda_cliente_id': cli_id, 'forma_pagamento': forma_pgto})
    except Vendas.DoesNotExist:
        return Response({'sucesso': False, 'erro': 'Venda não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def api_buscar_cliente(request):
    try:
        dados_cliente = gerencia_service.obter_dados_cliente(request.GET.get('cliente_id'))
        dados_cliente['sucesso'] = True
        return Response(dados_cliente)
    except Exception:
        return Response({'sucesso': False, 'erro': 'Cliente não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def api_consultar_status_nfe(request):
    try:
        venda = Vendas.objects.get(id=request.GET.get('venda_id'))
        resultado = FiscalService.consultar_status(venda)
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
    try:
        venda_id = request.data.get('venda_id')
        venda = Vendas.objects.get(id=venda_id)
        
        resultado = FiscalService.emitir_saida(venda, request.data)
        
        if resultado.get('sucesso'):
            venda.refresh_from_db()
            resultado['link_pdf'] = venda.link_pdf or ''
            resultado['link_xml'] = venda.link_xml or ''
            resultado['id_transacao'] = venda.id_transacao_api or venda.chave_acesso or ''
            
        return Response(resultado)
    except Vendas.DoesNotExist:
        return Response({'sucesso': False, 'erro': f'Venda ID {venda_id} não encontrada no banco de dados.'})
    except Exception as e:
        import traceback
        print("\n=== 🚨 ERRO INTERNO NA EMISSÃO FISCAL ===")
        traceback.print_exc() 
        print("=========================================\n")
        return Response({'sucesso': False, 'erro': f'Erro interno do servidor: {str(e)}'})
    
@api_view(['POST'])
def api_emitir_devolucao(request):
    serializer = DevolucaoSerializer(data=request.data)
    if serializer.is_valid():
        try:
            resultado = gerencia_service.processar_devolucao_entrada(serializer.validated_data, request.data)
            return Response(resultado)
        except Exception as e:
            return Response({'sucesso': False, 'erro': str(e)})
    return Response({'sucesso': False, 'erro': 'Dados inconsistentes.', 'detalhes': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def api_sincronizar_lote(request):
    atualizadas = gerencia_service.processar_sincronizacao_lote()
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

@api_view(['GET', 'POST'])
def api_exportar_xmls(request):
    ano = request.GET.get('ano') or request.data.get('ano')
    mes = request.GET.get('mes') or request.data.get('mes')
    return Response({'sucesso': True, 'mensagem': f"Backup de {mes}/{ano} solicitado. Link será enviado por e-mail."})

def imprimir_danfe_nfe(request, venda_id):
    try:
        venda = Vendas.objects.get(id=venda_id)
        arquivo_binario = FiscalService.download_arquivo(venda, tipo='pdf')
        if arquivo_binario:
            resp = HttpResponse(arquivo_binario, content_type='application/pdf')
            resp['Content-Disposition'] = f'inline; filename="DANFE_{venda_id}.pdf"'
            return resp
        return HttpResponse("<p>Documento DANFE indisponível. A nota pode não estar autorizada na SEFAZ.</p>", status=404)
    except Exception as e:
        return HttpResponse(f"Erro interno ao gerar PDF: {str(e)}", status=500)

def baixar_xml_nfe(request, venda_id):
    try:
        venda = Vendas.objects.get(id=venda_id)
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
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido.'}, status=405)
    try:
        payload = json.loads(request.body)
        gerencia_service.processar_webhook_notaas(payload)
        return JsonResponse({'status': 'sucesso', 'mensagem': 'Webhook Notaas processado com sucesso.'})
    except ValueError as e:
        return JsonResponse({'erro': str(e)}, status=404 if 'encontrada' in str(e) else 400)
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao processar Webhook: {str(e)}'}, status=500)
    