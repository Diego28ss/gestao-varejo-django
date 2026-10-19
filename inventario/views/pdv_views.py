import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from inventario.models import Produtos, Clientes, Usuarios
from inventario.services import fidelidade
from inventario.services.vendas.venda_service import VendaService
from inventario.services.vendas.pdv_service import PDVService

def tela_pdv(request):
    if 'usuario_logado' not in request.session: return redirect('login')

    clientes = Clientes.objects.all()
    return render(request, 'inventario/pdv.html', {
        'produtos': Produtos.objects.exclude(status='INATIVO'),
        'vendedores': Usuarios.objects.exclude(perfil='DEV'),
        'vendedores_list': Usuarios.objects.exclude(perfil='DEV'),
        'clientes': clientes,
        'pintores': clientes.filter(tipo__icontains='PINTOR'),
    })

def api_consultar_pontos(request):
    nome_cliente = request.GET.get('cliente', '')
    return JsonResponse(fidelidade.calcular_resgate_pontos(nome_cliente))

def api_buscar_produtos(request):
    query = request.GET.get('q', '').strip()
    try: offset = int(request.GET.get('offset', 0))
    except ValueError: offset = 0
    
    resultados, has_more = PDVService.buscar_produtos(query, offset)
    return JsonResponse({'produtos': resultados, 'has_more': has_more})

def api_salvar_venda(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            if dados.get('cpf_rapido'): dados['dest_cpf_cnpj'] = dados['cpf_rapido']
            venda_id = VendaService.registrar_checkout(dados)
            return JsonResponse({'status': 'sucesso', 'venda_id': venda_id})
        except ValueError as e: return JsonResponse({'status': 'erro', 'mensagem': str(e)})
        except Exception as e: return JsonResponse({'status': 'erro', 'mensagem': f"Erro interno no PDV: {str(e)}"})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_registrar_ruptura(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            PDVService.registrar_ruptura(dados.get('produto_id'), int(dados.get('quantidade_perdida', 1)))
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Ruptura registrada com sucesso.'})
        except Produtos.DoesNotExist: return JsonResponse({'status': 'erro', 'mensagem': 'Produto não encontrado na base.'})
        except Exception as e: return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_consultar_situacao_estoque(request, produto_id):
    try:
        return JsonResponse({'status': 'sucesso', **PDVService.consultar_situacao(produto_id)})
    except Produtos.DoesNotExist: return JsonResponse({'status': 'erro', 'mensagem': 'Produto não encontrado.'})
    except Exception as e: return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    