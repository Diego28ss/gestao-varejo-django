from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect
from django.db.models import Q
from inventario.models import Vendas, Produtos, Usuarios, Clientes
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from inventario.models.configuracoes import ConfiguracaoEmissor
from django.db import transaction


# ==========================================
# 📋 PAINEL DE PEDIDOS (Listagem e Filtros)
# ==========================================
def tela_painel_pedidos(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    agora = timezone.now()
    hoje = agora.date()

    filtro_status = request.GET.get('status', 'TODOS')
    filtro_periodo = request.GET.get('periodo', '7d')

    query = Q()

    if filtro_periodo == '7d':
        query &= Q(data_venda__gte=agora - timedelta(days=7))
    elif filtro_periodo == '14d':
        query &= Q(data_venda__gte=agora - timedelta(days=14))
    elif filtro_periodo == '30d':
        query &= Q(data_venda__gte=agora - timedelta(days=30))
    elif filtro_periodo == '60d':
        query &= Q(data_venda__gte=agora - timedelta(days=60))
    elif filtro_periodo == 'este_mes':
        query &= Q(data_venda__year=hoje.year, data_venda__month=hoje.month)

    # 🚀 CORREÇÃO DO PDV: O status "VENDA" do PDV agora é puxado junto com o FATURADO
    if filtro_status == 'FATURADO':
        query &= Q(status__in=['FATURADO', 'VENDA'])
    elif filtro_status != 'TODOS':
        query &= Q(status=filtro_status)

    pedidos = Vendas.objects.filter(query).order_by('-id')

    context = {
        'pedidos': pedidos,
        'filtro_status': filtro_status,
        'filtro_periodo': filtro_periodo,
    }
    return render(request, 'inventario/painel_pedidos.html', context)

# ==========================================
# ⚙️ GERAR NOVO PEDIDO EM BRANCO
# ==========================================
def gerar_novo_pedido(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    vendedor_logado = request.session.get('usuario_logado', 'Sistema')
    
    # Cria o pedido no banco de dados imediatamente como Rascunho
    novo_pedido = Vendas.objects.create(
        vendedor=vendedor_logado,
        status='ABERTO',
        valor_total=0,
        cupom_texto='[]' # Garante que o carrinho nasça limpo
    )
    
    # Redireciona o vendedor para a tela de Novo Pedido já com o ID gerado na URL
    return redirect('tela_novo_pedido_reabrir', pedido_id=novo_pedido.id)


# ==========================================
# 📝 TELA DE EDIÇÃO/MONTAGEM DO PEDIDO
# ==========================================
def tela_novo_pedido(request, pedido_id=None):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    produtos = Produtos.objects.exclude(status='INATIVO')
    vendedores = Usuarios.objects.exclude(perfil='DEV')
    clientes = Clientes.objects.all()
    
    # Lendo os dados do carrinho direto da coluna cupom_texto
    pedido_json = "[]" 
    if pedido_id:
        try:
            pedido = Vendas.objects.get(id=pedido_id)
            if pedido.cupom_texto:
                pedido_json = pedido.cupom_texto
        except Vendas.DoesNotExist:
            pass

    context = {
        'produtos': produtos,
        'vendedores': vendedores,
        'clientes': clientes,
        'pintores': clientes.filter(tipo__icontains='PINTOR'),
        'pedido_id_reabertura': pedido_id,
        'pedido_json_injetado': pedido_json
    }
    return render(request, 'inventario/novo_pedido.html', context)

# ==========================================
# 🔄 REABRIR E CANCELAR PEDIDOS (API)
# ==========================================
@csrf_exempt
def api_cancelar_pedido(request, pedido_id):
    """
    Cancela uma Venda ou Orçamento.
    Contém a Trava de Ouro Fiscal: Impede o cancelamento se houver nota na Sefaz.
    Reverte o estoque automaticamente se a venda já tinha saído.
    """
    if request.method == 'POST':
        try:
            venda = Vendas.objects.get(id=pedido_id)

            # ==========================================
            # 🚀 TRAVA DE OURO FISCAL
            # ==========================================
            status_fiscais_bloqueados = ['AUTORIZADO', 'PROCESSANDO_NUVEM', 'ENVIANDO', 'CANCELANDO']
            if venda.status_fiscal in status_fiscais_bloqueados:
                return JsonResponse({
                    'status': 'erro', 
                    'mensagem': f'Operação Bloqueada: Esta venda possui uma Nota Fiscal na SEFAZ (Status: {venda.status_fiscal}). Você deve ir ao "Painel Gerencial > Emitir Nota" e Cancelar a Nota primeiro.'
                })

            # Evitar duplo cancelamento
            if venda.status == 'CANCELADA':
                return JsonResponse({'status': 'erro', 'mensagem': 'Este pedido já se encontra cancelado.'})

            # ==========================================
            # 📦 REVERSÃO DE ESTOQUE (Se aplicável)
            # ==========================================
            with transaction.atomic():
                # Só devolve o estoque se a venda já tinha sido faturada/finalizada internamente
                if venda.status in ['FATURADO', 'FINALIZADO'] and venda.cupom_texto:
                    try:
                        carrinho = json.loads(venda.cupom_texto)
                        if isinstance(carrinho, str): 
                            carrinho = json.loads(carrinho)
                            
                        for item in carrinho:
                            if isinstance(item, dict):
                                item_id = str(item.get('id', '')).strip()
                                qtd = float(item.get('qtd', item.get('quantidade', 0)))
                                
                                if qtd > 0:
                                    # Busca o produto pelo ID ou Código Interno
                                    if item_id.isdigit():
                                        prod = Produtos.objects.filter(id=int(item_id)).first()
                                    else:
                                        prod = Produtos.objects.filter(cod_interno=item_id).first()
                                        
                                    if prod:
                                        # Devolve a quantidade ao estoque atual
                                        prod.estoque_atual = float(prod.estoque_atual or 0) + qtd
                                        prod.save(update_fields=['estoque_atual'])
                                        
                    except Exception as e:
                        print(f"Erro ao tentar reverter estoque no cancelamento da venda {pedido_id}: {e}")

                # Atualiza o status do pedido para CANCELADA
                venda.status = 'CANCELADA'
                # Limpa qualquer intenção fiscal para não poluir a fila de emissões
                venda.status_fiscal = 'SEM_NOTA' 
                venda.save(update_fields=['status', 'status_fiscal'])

            return JsonResponse({'status': 'sucesso', 'mensagem': 'Pedido cancelado com sucesso! Estoque revertido.'})

        except Vendas.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'Pedido não encontrado no banco de dados.'})
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({'status': 'erro', 'mensagem': f'Erro interno do servidor: {str(e)}'})

    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido. Use POST.'})

    
@csrf_exempt
def api_reabrir_pedido(request, pedido_id):
    """ Exige senha para reabrir pedidos que já afetaram o estoque/caixa """
    try:
        dados = json.loads(request.body)
        motivo = dados.get('motivo', '').strip()
        login = dados.get('login', '').strip()
        senha = dados.get('senha', '').strip()
        
        pedido = Vendas.objects.get(id=pedido_id)
        
        # Exige autorização
        autorizador = Usuarios.objects.filter(login=login, senha=senha, perfil__in=['Gerente', 'Supervisor', 'ADMINISTRADOR', 'DEV']).first()
        if not autorizador:
            return JsonResponse({'status': 'erro', 'mensagem': 'Acesso negado: Login ou senha inválidos, ou utilizador sem privilégios de gerência.'})
        
        if pedido.status in ['FATURADO', 'FINALIZADO', 'VENDA']:
            from inventario.services.vendas import VendaService
            VendaService.estornar_fidelidade_e_estoque(pedido)
            
        pedido.status = 'ABERTO'
        if hasattr(pedido, 'observacoes'):
            obs_atual = pedido.observacoes or ""
            nova_obs = f"REABERTO por {autorizador.login.upper()} ({timezone.localtime().strftime('%d/%m %H:%M')}): {motivo}"
            pedido.observacoes = f"{obs_atual}\n{nova_obs}" if obs_atual else nova_obs
            
        pedido.save()
        
        url_destino = reverse('tela_novo_pedido_reabrir', args=[pedido.id])
        return JsonResponse({'status': 'sucesso', 'url_redirecionamento': url_destino})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    
@csrf_exempt
def api_estornar_faturamento(request, pedido_id):
    """ Estorna um pedido FATURADO no caixa e volta ele para ABERTO na tela de vendas """
    try:
        pedido = Vendas.objects.get(id=pedido_id)
        pedido.status = 'ABERTO'
        
        # Opcional: Registra na observação que ocorreu um estorno
        if hasattr(pedido, 'observacoes'):
            obs_atual = pedido.observacoes or ""
            nova_obs = f"ESTORNO DE CAIXA ({timezone.localtime().strftime('%d/%m %H:%M')})"
            pedido.observacoes = f"{obs_atual}\n{nova_obs}" if obs_atual else nova_obs
            
        pedido.save()
        return JsonResponse({'status': 'sucesso'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})

# ==========================================
# 💰 PDV E CAIXA (API)
# ==========================================
def api_pedidos_pendentes(request):
    """ Lista no Caixa todos os pedidos FINALIZADOS pela Retaguarda """
    pedidos = Vendas.objects.filter(status='FINALIZADO').order_by('-id')
    lista = []
    for p in pedidos:
        lista.append({
            'id': p.id,
            'vendedor': p.vendedor,
            'cliente': p.cliente if p.cliente else 'Consumidor Padrão',
            'valor_total': float(p.valor_total)
        })
    return JsonResponse({'pedidos': lista})

def api_importar_pedido(request, pedido_id):
    """ Entrega os produtos e valores exatos para a tela do PDV """
    try:
        pedido = Vendas.objects.get(id=pedido_id)
        carrinho = json.loads(pedido.cupom_texto) if pedido.cupom_texto else []
        dados = {
            'id': pedido.id,
            'vendedor': pedido.vendedor,
            'cliente': pedido.cliente,
            'indicante': pedido.indicante,
            'observacoes': getattr(pedido, 'observacoes', ''), # 🚀 NOVO
            'desconto': float(pedido.valor_desconto),          # 🚀 NOVO
            'carrinho': carrinho,
            'status': pedido.status
        }
        return JsonResponse({'status': 'sucesso', 'pedido': dados})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    
@csrf_exempt
def api_faturar_pedido(request, pedido_id):
    """ Muda o status do pedido da Retaguarda para FATURADO quando pago no PDV """
    try:
        pedido = Vendas.objects.get(id=pedido_id)
        pedido.status = 'FATURADO'
        pedido.save()
        return JsonResponse({'status': 'sucesso'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})

def imprimir_ticket_pedido(request, pedido_id):
    """ Gera o ticket térmico de pré-venda com código de barras """
    if 'usuario_logado' not in request.session:
        return redirect('login')
        
    try:
        pedido = Vendas.objects.get(id=pedido_id)
        # Busca os dados da loja
        loja = ConfiguracaoEmissor.objects.first()
        
        return render(request, 'inventario/cupom_pedido.html', {'pedido': pedido, 'loja': loja})
    except Vendas.DoesNotExist:
        return redirect('tela_painel_pedidos')
    
    