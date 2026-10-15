import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from inventario.models import InventarioSessao, InventarioItem, Produtos, Marca, Familia, Usuarios, Vendas

# Importa a inteligência do Service
from inventario.services.estoque_inventario_service import (
    criar_snapshot_dinamico, 
    registrar_bipagem_dinamica, 
    reduzir_bipagem_dinamica, 
    atualizar_quantidade_dinamica,
    conciliar_e_finalizar_inventario
)

# ==========================================
# PAINEL GERAL DO INVENTÁRIO DINÂMICO
# ==========================================
def tela_inventario_dinamico(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor', 'Dev']:
        messages.error(request, "Acesso restrito a Gerentes, Supervisores e Desenvolvedores.")
        return redirect('tela_painel_estoque')

    status_filtro = request.GET.get('status', 'TODOS')
    
    inventarios_db = InventarioSessao.objects.select_related('criado_por', 'filtro_marca', 'filtro_familia').exclude(filtro_unidade='AUDITORIA').order_by('-id')
    
    if status_filtro != 'TODOS':
        inventarios_db = inventarios_db.filter(status=status_filtro)

    lista_inventarios = []
    for inv in inventarios_db:
        filtros_usados = []
        if inv.filtro_marca: filtros_usados.append(f"Marca: {inv.filtro_marca.nome}")
        if inv.filtro_familia: filtros_usados.append(f"Família: {inv.filtro_familia.nome}")
        if inv.filtro_unidade: filtros_usados.append(f"Unidade: {inv.filtro_unidade}")
        
        lista_inventarios.append({
            'id': inv.id,
            'filtros': " | ".join(filtros_usados),
            'data_inicio': inv.data_inicio.strftime('%d/%m/%Y %H:%M'),
            'criado_por': inv.criado_por.login.upper() if inv.criado_por else 'SISTEMA',
            'qtd_contados': inv.qtd_itens_contados(),
            'qtd_esperados': inv.qtd_itens_esperados(),
            'status': inv.status,
            'valor_sobra': inv.valor_sobra, 
            'valor_perda': inv.valor_perda  
        })
        
    marcas = Marca.objects.all().order_by('nome')
    familias = Familia.objects.all().order_by('nome')
    unidades = Produtos.objects.values_list('unidade', flat=True).distinct()

    return render(request, 'inventario/inventario_dinamico.html', {
        'inventarios': lista_inventarios, 
        'filtro_atual': status_filtro,
        'marcas': marcas,
        'familias': familias,
        'unidades': unidades
    })

def criar_novo_inventario_dinamico(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor', 'Dev']:
        messages.error(request, "Acesso restrito.")
        return redirect('tela_painel_estoque')

    if request.method == 'POST':
        marca_id = request.POST.get('filtro_marca')
        familia_id = request.POST.get('filtro_familia')
        unidade = request.POST.get('filtro_unidade')
        
        filtros_preenchidos = sum([1 for f in [marca_id, familia_id, unidade] if f])
        if filtros_preenchidos < 2:
            messages.error(request, "Selecione no mínimo 2 filtros para criar o lote (Ex: Marca + Unidade).")
            return redirect('tela_inventario_dinamico')

        marca_obj = Marca.objects.filter(id=marca_id).first() if marca_id else None
        familia_obj = Familia.objects.filter(id=familia_id).first() if familia_id else None
        usuario_logado = Usuarios.objects.filter(login=request.session.get('usuario_logado')).first()
        
        try:
            lote, qtd = criar_snapshot_dinamico(usuario_logado, marca_obj, familia_obj, unidade)
            messages.success(request, f"Lote #{lote.id} aberto! Snapshot congelado para {qtd} produtos.")
            return redirect('tela_contagem_dinamica', sessao_id=lote.id)
        except ValueError as ve:
            messages.error(request, str(ve))
            return redirect('tela_inventario_dinamico')
            
    return redirect('tela_inventario_dinamico')

# ==========================================
# INTERFACE DE CONTAGEM E APIS
# ==========================================
def tela_contagem_dinamica(request, sessao_id):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor', 'Dev']:
        return redirect('tela_painel_estoque')
    
    sessao = get_object_or_404(InventarioSessao, id=sessao_id)
    if sessao.status == 'FINALIZADO':
        messages.warning(request, "Este inventário já foi fechado.")
        return redirect('tela_inventario_dinamico')
            
    itens_contados = InventarioItem.objects.filter(sessao=sessao).select_related(
        'produto', 'produto__marca', 'produto__familia'
    ).order_by('-contado', '-id')
    
    return render(request, 'inventario/inventario_contagemdin.html', {'sessao': sessao, 'itens': itens_contados})

def api_bipar_item_dinamico(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            produto = registrar_bipagem_dinamica(
                dados.get('sessao_id'), 
                dados.get('codigo', '').strip(), 
                int(dados.get('quantidade', 1))
            )
            return JsonResponse({'status': 'sucesso', 'produto_nome': produto.nome})
        except ValueError as ve:
            return JsonResponse({'status': 'erro', 'mensagem': str(ve)})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': f"Erro interno: {str(e)}"})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_reduzir_item_dinamico(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            reduzir_bipagem_dinamica(dados.get('sessao_id'), dados.get('produto_id'))
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Unidade removida.'})
        except ValueError as ve:
            return JsonResponse({'status': 'erro', 'mensagem': str(ve)})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_atualizar_quantidade_dinamico(request):
    """ View Fina: Repassa a quantidade exata digitada para o Service """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            atualizar_quantidade_dinamica(
                dados.get('sessao_id'), 
                dados.get('produto_id'), 
                int(dados.get('quantidade', 0))
            )
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Quantidade atualizada com sucesso.'})
        except ValueError as ve:
            return JsonResponse({'status': 'erro', 'mensagem': str(ve)})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_revisao_omissos(request, sessao_id):
    if request.method == 'GET':
        sessao = get_object_or_404(InventarioSessao, id=sessao_id)
        itens_omissos = InventarioItem.objects.filter(sessao=sessao, contado=False).select_related('produto')
        
        lista_omissos = [{
            'id': item.produto.id,
            'nome': item.produto.nome,
            'cod_interno': item.produto.cod_interno or item.produto.cod_barras,
            'saldo_sistema': item.produto.estoque_atual
        } for item in itens_omissos]
            
        return JsonResponse({'status': 'sucesso', 'omissos': lista_omissos})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_finalizar_inventario_dinamico(request, sessao_id):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            resultado = conciliar_e_finalizar_inventario(sessao_id, dados.get('acao_omissos'))
            
            if resultado.get('status') == 'pendente_omissos':
                return JsonResponse({
                    'status': 'pendente_omissos',
                    'quantidade': resultado['quantidade'],
                    'mensagem': f"Você esqueceu de contar {resultado['quantidade']} produto(s)."
                })
                
            return JsonResponse({'status': 'sucesso', 'url': '/estoquepainel/inventario-sessao/'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_excluir_inventario(request, sessao_id):
    if request.method == 'POST':
        InventarioSessao.objects.filter(id=sessao_id).delete()
        return JsonResponse({'status': 'sucesso'})
    return JsonResponse({'status': 'erro'})

# ==========================================
# RELATÓRIOS E PDF DO INVENTÁRIO
# ==========================================
def tela_relatorio_inventario(request, sessao_id):
    if 'usuario_logado' not in request.session: return redirect('login')
    sessao = get_object_or_404(InventarioSessao, id=sessao_id)
    itens = InventarioItem.objects.filter(sessao=sessao).select_related('produto')
    return render(request, 'inventario/inventario_relatorio.html', {'sessao': sessao, 'itens': itens})

def gerar_pdf_inventario(request, sessao_id):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    sessao = get_object_or_404(InventarioSessao, id=sessao_id)
    itens_db = InventarioItem.objects.filter(sessao=sessao).select_related('produto')
    
    vendas_periodo = Vendas.objects.filter(
        status__in=['FATURADO', 'FINALIZADO'],
        data_venda__gte=sessao.data_inicio,
        data_venda__lte=sessao.data_finalizacao if sessao.data_finalizacao else timezone.now()
    )
    
    mapa_vendas = {}
    for v in vendas_periodo:
        if v.cupom_texto:
            try:
                for it in json.loads(v.cupom_texto):
                    p_id = int(it.get('id', 0))
                    if p_id > 0: mapa_vendas[p_id] = mapa_vendas.get(p_id, 0) + int(it.get('qtd', 0))
            except: pass

    itens_divergentes = []
    for item in itens_db:
        if not item.contado: continue
            
        qtd_vendida = mapa_vendas.get(item.produto.id, 0)
        esperado = item.saldo_sistema - qtd_vendida
        diferenca = item.saldo_fisico - esperado
        
        if diferenca != 0:
            custo = float(item.produto.preco_custo or 0.0)
            itens_divergentes.append({
                'produto': item.produto.nome,
                'codigo': item.produto.cod_interno or f"INT-{item.produto.id}",
                'snapshot': item.saldo_sistema,
                'vendas': qtd_vendida,
                'esperado': esperado,
                'fisico': item.saldo_fisico,
                'diferenca': diferenca,
                'custo': custo,
                'valor_diferenca': abs(diferenca) * custo,
                'tipo': 'SOBRA' if diferenca > 0 else 'PERDA'
            })
            
    itens_divergentes.sort(key=lambda x: x['diferenca'])
    
    contexto = {
        'sessao': sessao,
        'itens': itens_divergentes,
        'saldo_liquido': float(sessao.valor_sobra or 0) - float(sessao.valor_perda or 0)
    }
    return render(request, 'inventario/inventario_relatorio_pdf.html', contexto)
