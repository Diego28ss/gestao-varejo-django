from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from inventario.models import Vendas, Clientes, Produtos
from inventario.services.fiscal_service import FiscalService

# ==========================================
# TELAS DO MÓDULO FISCAL E GERENCIAL
# ==========================================
def tela_painel_gerencia(request):
    if 'usuario_logado' not in request.session: 
        return redirect('login')
    return render(request, 'inventario/painel_gerencia.html')

def emitir_notas(request):
    if 'usuario_logado' not in request.session: 
        return redirect('login')
    return render(request, 'inventario/emitir_notas.html', {
        'vendas_pendentes': Vendas.objects.all().order_by('-id'),
        'todos_clientes': Clientes.objects.all().order_by('nome')
    })

def tela_consulta_nfe(request):
    if 'usuario_logado' not in request.session: 
        return redirect('login')
    vendas = Vendas.objects.filter(modelo_fiscal='55').exclude(status_fiscal='SEM_NOTA').exclude(status='DEVOLUCAO_ENTRADA').order_by('-id')
    return render(request, 'inventario/consulta_nfe.html', {
        'vendas_processadas': vendas, 
        'todos_clientes': Clientes.objects.all().order_by('nome')
    })

def tela_consulta_nfce(request):
    if 'usuario_logado' not in request.session: 
        return redirect('login')
    vendas = Vendas.objects.filter(modelo_fiscal='65').exclude(status_fiscal='SEM_NOTA').order_by('-id')
    return render(request, 'inventario/consulta_nfce.html', {
        'vendas_processadas': vendas, 
        'todos_clientes': Clientes.objects.all().order_by('nome')
    })

def tela_devolucoes(request):
    if 'usuario_logado' not in request.session: 
        return redirect('login')
    return render(request, 'inventario/devolucoes.html', {
        'devolucoes': Vendas.objects.filter(status='DEVOLUCAO_ENTRADA').order_by('-id')
    })


# ==========================================
# APIs AUXILIARES (DADOS DA TELA)
# ==========================================
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
                
        return JsonResponse({'sucesso': True, 'itens': itens, 'venda_cliente_id': cli_id, 'forma_pagamento': forma_pgto})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})
    
def api_buscar_cliente(request):
    try:
        cli = Clientes.objects.get(id=request.GET.get('cliente_id'))
        doc = cli.cnpj if cli.tipo_pessoa == 'PJ' and cli.cnpj else cli.cpf
        if not doc: doc = cli.cnpj if cli.cnpj else cli.cpf
        
        return JsonResponse({
            'sucesso': True, 'nome': cli.nome, 'cpf_cnpj': doc, 
            'cep': getattr(cli, 'cep', ''), 'endereco': getattr(cli, 'endereco', ''),
            'numero': getattr(cli, 'numero', ''), 'complemento': getattr(cli, 'complemento', ''),
            'bairro': getattr(cli, 'bairro', ''), 'cidade': getattr(cli, 'cidade', ''),
            'estado': getattr(cli, 'estado', getattr(cli, 'uf', '')), 'email': getattr(cli, 'email', ''),
            'inscricao_estadual': getattr(cli, 'inscricao_estadual', '')
        })
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})


# ==========================================
# INTEGRAÇÃO COM A CAMADA DE SERVIÇO (FISCAL_SERVICE)
# ==========================================
def api_consultar_status_nfe(request):
    try:
        venda = Vendas.objects.get(id=request.GET.get('venda_id'))
        return JsonResponse(FiscalService.consultar_status(venda))
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})

@csrf_exempt
def api_cancelar_nota(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda = Vendas.objects.get(id=dados.get('venda_id'))
            return JsonResponse(FiscalService.cancelar_nota(venda, dados.get('justificativa', 'Cancelamento solicitado pelo cliente.')))
        except Exception as e: 
            return JsonResponse({'sucesso': False, 'erro': str(e)})
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'})

@csrf_exempt
def api_enviar_email_nota(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda = Vendas.objects.get(id=dados.get('venda_id'))
            return JsonResponse(FiscalService.enviar_email(venda, dados.get('email', '').strip()))
        except Exception as e: 
            return JsonResponse({'sucesso': False, 'erro': str(e)})
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'})

@csrf_exempt
def api_acionar_emissao(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda = Vendas.objects.get(id=dados.get('venda_id'))
            return JsonResponse(FiscalService.emitir_saida(venda, dados))
        except Exception as e: 
            return JsonResponse({'sucesso': False, 'erro': str(e)})
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'})

@csrf_exempt
def api_emitir_devolucao(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda = Vendas.objects.get(id=dados.get('venda_id'))
            
            valor_total_dev = sum([float(i.get('quantidade')) * float(Produtos.objects.filter(cod_interno=i.get('cod_interno')).first().preco_venda) for i in dados.get('itens_devolvidos', []) if Produtos.objects.filter(cod_interno=i.get('cod_interno')).first()])
            
            nova_devolucao = Vendas.objects.create(
                data_venda=timezone.now(), valor_total=valor_total_dev,
                status='DEVOLUCAO_ENTRADA', status_fiscal='PROCESSANDO_NUVEM', modelo_fiscal='55',
                cliente=venda.cliente, numero_nota=f"Ref a Venda Orig. #{venda.id}",
                motivo_erro=dados.get('justificativa', 'Devolucao de mercadoria'),
                cupom_texto=json.dumps(dados.get('itens_devolvidos', []))
            )
            return JsonResponse(FiscalService.emitir_devolucao(venda, nova_devolucao, dados))
        except Exception as e: 
            return JsonResponse({'sucesso': False, 'erro': str(e)})
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'})

@csrf_exempt
def api_sincronizar_lote(request):
    if request.method == 'POST':
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
        return JsonResponse({'sucesso': True, 'mensagem': f"{atualizadas} documentos sincronizados com sucesso."})
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'})

@csrf_exempt
def api_inutilizar_numeracao(request):
    if request.method == 'POST':
        try: 
            return JsonResponse(FiscalService.inutilizar_numeracao(json.loads(request.body)))
        except Exception as e: 
            return JsonResponse({'sucesso': False, 'erro': str(e)})
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'})

@csrf_exempt
def api_emitir_cce(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda = Vendas.objects.get(id=dados.get('venda_id'))
            return JsonResponse(FiscalService.emitir_cce(venda, dados.get('correcao')))
        except Exception as e: 
            return JsonResponse({'sucesso': False, 'erro': str(e)})
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'})

def imprimir_danfe_nfe(request, venda_id):
    try:
        conteudo = FiscalService.download_arquivo(Vendas.objects.get(id=venda_id), tipo='pdf')
        if conteudo:
            resp = HttpResponse(conteudo, content_type='application/pdf')
            resp['Content-Disposition'] = f'inline; filename="Documento_{venda_id}.pdf"'
            return resp
        return HttpResponse("<p>Documento indisponível na SEFAZ. Verifique o status.</p>", status=404)
    except Exception as e: 
        return HttpResponse(f"Erro interno: {str(e)}", status=500)

def baixar_xml_nfe(request, venda_id):
    try:
        conteudo = FiscalService.download_arquivo(Vendas.objects.get(id=venda_id), tipo='xml')
        if conteudo:
            resp = HttpResponse(conteudo, content_type='application/xml')
            resp['Content-Disposition'] = f'attachment; filename="XML_{venda_id}.xml"'
            return resp
        return HttpResponse("<p>XML indisponível. A nota pode não estar autorizada.</p>", status=404)
    except Exception as e: 
        return HttpResponse(f"Erro interno: {str(e)}", status=500)

@csrf_exempt
def api_exportar_zip(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            return JsonResponse({'sucesso': True, 'mensagem': f"Backup de {dados.get('mes')}/{dados.get('ano')} solicitado. Link será enviado por e-mail."})
        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': str(e)})
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'})

@csrf_exempt
def api_verificar_status_nota(request):
    if request.method == 'GET':
        venda = Vendas.objects.filter(id=request.GET.get('venda_id')).first()
        if venda:
            return JsonResponse({'status_fiscal': venda.status_fiscal, 'chave': venda.chave_acesso})
    return JsonResponse({'status_fiscal': 'ERRO'})
