import json
import traceback
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from inventario.models import Vendas, Produtos, Usuarios, Clientes
from inventario.models.configuracoes import ConfiguracaoEmissor
from inventario.services.vendas.retaguarda_service import RetaguardaService

# ==========================================
# PAINEL DE PEDIDOS
# ==========================================
def tela_painel_pedidos(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    filtro_status = request.GET.get('status', 'TODOS')
    filtro_periodo = request.GET.get('periodo', '7d')
    pedidos = RetaguardaService.listar_pedidos(filtro_status, filtro_periodo)

    return render(request, 'inventario/painel_pedidos.html', {
        'pedidos': pedidos, 'filtro_status': filtro_status, 'filtro_periodo': filtro_periodo,
    })

def gerar_novo_pedido(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    vendedor_logado = request.session.get('usuario_logado', 'Sistema')
    novo_pedido = Vendas.objects.create(vendedor=vendedor_logado, status='ABERTO', valor_total=0, cupom_texto='[]')
    return redirect('tela_novo_pedido_reabrir', pedido_id=novo_pedido.id)

def tela_novo_pedido(request, pedido_id=None):
    if 'usuario_logado' not in request.session: return redirect('login')

    clientes = Clientes.objects.all()
    pedido_json = "[]" 
    if pedido_id:
        try:
            pedido = Vendas.objects.get(id=pedido_id)
            if pedido.cupom_texto: pedido_json = pedido.cupom_texto
        except Vendas.DoesNotExist: pass

    return render(request, 'inventario/novo_pedido.html', {
        'produtos': Produtos.objects.exclude(status='INATIVO'),
        'vendedores': Usuarios.objects.exclude(perfil='DEV'),
        'clientes': clientes,
        'pintores': clientes.filter(tipo__icontains='PINTOR'),
        'pedido_id_reabertura': pedido_id,
        'pedido_json_injetado': pedido_json
    })

# ==========================================
# APIs DE AÇÕES DO PEDIDO
# ==========================================
@csrf_exempt
def api_cancelar_pedido(request, pedido_id):
    if request.method == 'POST':
        try:
            RetaguardaService.cancelar_pedido(pedido_id)
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Pedido cancelado com sucesso! Estoque revertido.'})
        except ValueError as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
        except Vendas.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'Pedido não encontrado no banco de dados.'})
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({'status': 'erro', 'mensagem': f'Erro interno do servidor: {str(e)}'})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

@csrf_exempt
def api_reabrir_pedido(request, pedido_id):
    try:
        dados = json.loads(request.body)
        pedido = RetaguardaService.reabrir_pedido(
            pedido_id, dados.get('login', '').strip(), 
            dados.get('senha', '').strip(), dados.get('motivo', '').strip()
        )
        url_destino = reverse('tela_novo_pedido_reabrir', args=[pedido.id])
        return JsonResponse({'status': 'sucesso', 'url_redirecionamento': url_destino})
    except ValueError as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})

@csrf_exempt
def api_estornar_faturamento(request, pedido_id):
    try:
        RetaguardaService.estornar_faturamento(pedido_id)
        return JsonResponse({'status': 'sucesso'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})

# ==========================================
# INTEGRAÇÃO COM O CAIXA (PDV APIs)
# ==========================================
def api_pedidos_pendentes(request):
    pedidos = Vendas.objects.filter(status='FINALIZADO').order_by('-id')
    lista = [{'id': p.id, 'vendedor': p.vendedor, 'cliente': p.cliente or 'Consumidor Padrão', 'valor_total': float(p.valor_total)} for p in pedidos]
    return JsonResponse({'pedidos': lista})

def api_importar_pedido(request, pedido_id):
    try:
        pedido = Vendas.objects.get(id=pedido_id)
        carrinho = json.loads(pedido.cupom_texto) if pedido.cupom_texto else []
        dados = {
            'id': pedido.id, 'vendedor': pedido.vendedor, 'cliente': pedido.cliente,
            'indicante': getattr(pedido, 'indicante', ''), 'observacoes': getattr(pedido, 'observacoes', ''),
            'desconto': float(pedido.valor_desconto), 'carrinho': carrinho, 'status': pedido.status
        }
        return JsonResponse({'status': 'sucesso', 'pedido': dados})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    
@csrf_exempt
def api_faturar_pedido(request, pedido_id):
    try:
        pedido = Vendas.objects.get(id=pedido_id)
        pedido.status = 'FATURADO'
        pedido.save()
        return JsonResponse({'status': 'sucesso'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})

def imprimir_ticket_pedido(request, pedido_id):
    if 'usuario_logado' not in request.session: return redirect('login')
    try:
        pedido = Vendas.objects.get(id=pedido_id)
        loja = ConfiguracaoEmissor.objects.first()
        return render(request, 'inventario/cupom_pedido.html', {'pedido': pedido, 'loja': loja})
    except Vendas.DoesNotExist:
        return redirect('tela_painel_pedidos')
    