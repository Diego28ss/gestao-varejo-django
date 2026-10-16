import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages

# Importa a inteligência do Service
from inventario.services.estoque.estoque_compras_service import (
    calcular_necessidades_suprimento,
    resolver_ruptura_estoque,
    registrar_encomenda_produto,
    processar_carrinho_gerente
)


def tela_suprir_estoque(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']:
        messages.error(request, "Acesso restrito a Gerentes e Supervisores.")
        return redirect('tela_estoque_produtos')
        
    produtos_necessarios, dias_seguranca = calcular_necessidades_suprimento()
    return render(request, 'inventario/suprir_estoque.html', {'produtos': produtos_necessarios, 'dias_seguranca': dias_seguranca})

def api_resolver_ruptura(request, produto_id):
    if request.method == 'POST':
        try:
            resolver_ruptura_estoque(produto_id)
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_registrar_encomenda(request, produto_id):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            registrar_encomenda_produto(produto_id, dados.get('quantidade'), dados.get('data_previsao'))
            return JsonResponse({'status': 'sucesso'})
        except ValueError as ve:
            return JsonResponse({'status': 'erro', 'mensagem': str(ve)})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_finalizar_carrinho_gerente(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            processar_carrinho_gerente(dados.get('itens', []))
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def tela_carrinho_pedido(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/carrinho_pedido.html')

def gerar_pdf_suprimentos(request):
    if 'usuario_logado' not in request.session: return redirect('login')
        
    produtos_necessarios, dias_seguranca = calcular_necessidades_suprimento()
    return render(request, 'inventario/relatorio_suprir_pdf.html', {'produtos': produtos_necessarios, 'dias': dias_seguranca})
