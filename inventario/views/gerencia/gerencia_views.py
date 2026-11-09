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

from inventario.models import Vendas, Usuarios
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
    if 'usuario_logado' not in request.session:
        return redirect('login')

    vendedor_selecionado = request.GET.get('vendedor', '').strip()
    hoje = datetime.today()
    
    mes_str = request.GET.get('mes', '').strip()
    try:
        mes_selecionado = int(mes_str) if mes_str else hoje.month
    except ValueError:
        mes_selecionado = hoje.month
        
    ano_str = request.GET.get('ano', '').strip()
    try:
        ano_selecionado = int(ano_str) if ano_str else hoje.year
    except ValueError:
        ano_selecionado = hoje.year

    meses = [
        {'valor': 1, 'nome': 'Janeiro'}, {'valor': 2, 'nome': 'Fevereiro'},
        {'valor': 3, 'nome': 'Março'}, {'valor': 4, 'nome': 'Abril'},
        {'valor': 5, 'nome': 'Maio'}, {'valor': 6, 'nome': 'Junho'},
        {'valor': 7, 'nome': 'Julho'}, {'valor': 8, 'nome': 'Agosto'},
        {'valor': 9, 'nome': 'Setembro'}, {'valor': 10, 'nome': 'Outubro'},
        {'valor': 11, 'nome': 'Novembro'}, {'valor': 12, 'nome': 'Dezembro'},
    ]

    vendedores = Usuarios.objects.exclude(perfil='DEV').order_by('login')
    
    vendas_queryset = Vendas.objects.filter(
        status__in=['FATURADO', 'VENDA'],
        data_venda__year=ano_selecionado,
        data_venda__month=mes_selecionado
    ).order_by('-data_venda')

    if vendedor_selecionado:
        vendas_queryset = vendas_queryset.filter(vendedor__icontains=vendedor_selecionado)

    lista_vendas_extrato = []
    total_geral_comissao = 0.00
    total_geral_vendas_bruto = 0.00
    total_geral_taxa_maquininha = 0.00
    
    for v in vendas_queryset:
        v_bruto = float(v.valor_total) or 0.00
        total_geral_vendas_bruto += v_bruto
        
        # 🚀 CORREÇÃO DA VENDA 112: Se desconto_comum for zero, busca no valor_desconto (legado)
        desc_comum = float(getattr(v, 'desconto_comum', 0) or 0)
        if desc_comum == 0 and getattr(v, 'valor_desconto', 0):
            desc_comum = float(v.valor_desconto)
            
        desc_pontos = float(getattr(v, 'desconto_pontos', 0) or 0)
        
        taxa_maq = float(v.valor_taxa_maquininha) if getattr(v, 'valor_taxa_maquininha', None) else 0.00
        total_geral_taxa_maquininha += taxa_maq
        
        v_liquido = v_bruto - desc_comum - desc_pontos - taxa_maq
        if v_liquido < 0: v_liquido = 0
        
        perc_comissao = float(v.percentual_comissao) if getattr(v, 'percentual_comissao', None) else 0.00
        valor_comissao = v_liquido * (perc_comissao / 100.0)
        
        total_geral_comissao += valor_comissao
        
        forma_pagamento_formatada = ""
        if getattr(v, 'pagamentos_texto', None):
            try:
                pgts = json.loads(v.pagamentos_texto)
                nomes = [p.get('metodoNome', p.get('metodo', '')) for p in pgts]
                forma_pagamento_formatada = " + ".join(nomes)
            except Exception:
                forma_pagamento_formatada = "Desconhecido"
        
        lista_vendas_extrato.append({
            'id': v.id,
            'data': v.data_venda,
            'vendedor': v.vendedor,
            'pagamento': forma_pagamento_formatada,
            'percentual': perc_comissao,
            'valor_bruto': v_bruto,
            'desc_comum': desc_comum,
            'desc_pontos': desc_pontos,
            'taxa_maq': taxa_maq,
            'valor_liquido': v_liquido,
            'comissao': valor_comissao
        })

    return render(request, 'inventario/relatorio_comissao.html', {
        'vendedores': vendedores,
        'meses': meses,
        'vendedor_selecionado': vendedor_selecionado,
        'mes_selecionado': mes_selecionado,
        'ano_selecionado': ano_selecionado,
        'extrato': lista_vendas_extrato,
        'total_geral_vendas': total_geral_vendas_bruto,
        'total_geral_comissao': total_geral_comissao,
        'total_geral_taxa_maquininha': total_geral_taxa_maquininha
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
    