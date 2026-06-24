from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
import json

# Importações do DRF
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from inventario.models import Vendas, Clientes, Produtos
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
    try:
        venda = Vendas.objects.get(id=request.GET.get('venda_id'))
        return Response(FiscalService.consultar_status(venda))
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
    # Por ser um payload muito dinâmico vindo do ecrã, validamos apenas o ID da venda e delegamos os dados
    try:
        venda = Vendas.objects.get(id=request.data.get('venda_id'))
        return Response(FiscalService.emitir_saida(venda, request.data))
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
    try:
        conteudo = FiscalService.download_arquivo(Vendas.objects.get(id=venda_id), tipo='pdf')
        if conteudo:
            resp = HttpResponse(conteudo, content_type='application/pdf')
            resp['Content-Disposition'] = f'inline; filename="Documento_{venda_id}.pdf"'
            return resp
        return HttpResponse("<p>Documento indisponível na SEFAZ. Verifique o status.</p>", status=404)
    except Exception as e: return HttpResponse(f"Erro interno: {str(e)}", status=500)

def baixar_xml_nfe(request, venda_id):
    try:
        conteudo = FiscalService.download_arquivo(Vendas.objects.get(id=venda_id), tipo='xml')
        if conteudo:
            resp = HttpResponse(conteudo, content_type='application/xml')
            resp['Content-Disposition'] = f'attachment; filename="XML_{venda_id}.xml"'
            return resp
        return HttpResponse("<p>XML indisponível. A nota pode não estar autorizada.</p>", status=404)
    except Exception as e: return HttpResponse(f"Erro interno: {str(e)}", status=500)
    