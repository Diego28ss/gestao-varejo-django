import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q

# Importação dos modelos para gerir o estoque e tabelas auxiliares
from inventario.models import Produtos, Marca, Familia
# 🔥 ADICIONE A IMPORTAÇÃO DO FORMULÁRIO DE PRODUTO:
from inventario.forms import ProdutoForm


# ==========================================
# 📦 CONTROLE DE ESTOQUE E CARGAS
# ==========================================

# 1. FUNÇÃO QUE RENDERIZA A TELA E ENTREGA OS DADOS PARA O JAVASCRIPT
def tela_estoque_produtos(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    query = request.GET.get('q', '').strip()
    
    # select_related faz um JOIN único para carregar Marca e Família sem deixar o sistema lento
    produtos = Produtos.objects.all().select_related('marca', 'familia').order_by('nome')

    if query:
        produtos = produtos.filter(
            Q(nome__icontains=query) |
            Q(cod_barras__icontains=query) |
            Q(cod_interno__icontains=query) |
            Q(marca__nome__icontains=query) |
            Q(familia__nome__icontains=query)
        )

    marcas = Marca.objects.all().order_by('nome')
    familias = Familia.objects.all().order_by('nome')

    context = {
        'produtos': produtos,
        'query': query,
        'marcas': marcas,
        'marcas_list': marcas,
        'fabricantes': marcas,
        'familias': familias,
        'familias_list': familias,
        'grupos': familias,
    }
    return render(request, 'inventario/estoque_produtos.html', context)


# 2. FUNÇÃO QUE SALVA OU EDITA O PRODUTO VINDO DO MODAL
def salvar_produto(request):
    if request.method == "POST":
        produto_id = request.POST.get('produto_id')
        
        # Se veio ID, estamos editando, senão estamos criando um novo
        if produto_id:
            produto = get_object_or_404(Produtos, id=produto_id)
            form = ProdutoForm(request.POST, instance=produto)
        else:
            form = ProdutoForm(request.POST)

        if form.is_valid():
            # O form.save() vai disparar a nossa função save() customizada do models.py,
            # gerando o código interno de 6 dígitos de forma 100% automática!
            form.save()
            messages.success(request, "Produto gravado com sucesso!")
        else:
            messages.error(request, "Erro ao validar os dados do produto.")
            
    return redirect('tela_estoque_produtos')


def excluir_produto(request, id):
    produto = get_object_or_404(Produtos, id=id)
    nome = produto.nome
    produto.delete()
    messages.success(request, f"Produto '{nome}' excluído!")
    return redirect('tela_estoque_produtos')


def tela_entrada_carga(request):
    # Nota de histórico: O código exclui a funcionalidade "Importar XML NFe" conforme a sua diretiva anterior, mantendo apenas a entrada manual.
    if 'usuario_logado' not in request.session:
        return redirect('login')
    return render(request, 'inventario/entrada_carga.html')


def api_produto_por_codigo(request):
    codigo = request.GET.get('codigo', '').strip()
    produto = Produtos.objects.filter(cod_barras=codigo).first()
    if produto:
        return JsonResponse({
            'status': 'ok',
            'id': produto.id,
            'nome': produto.nome
        })
    return JsonResponse({'status': 'erro', 'mensagem': 'Produto não cadastrado!'})


def api_efetivar_entrada(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            itens = dados.get('itens', [])

            with transaction.atomic():
                for item in itens:
                    produto_id = item.get('id')
                    qtd_a_entrar = int(item.get('qtd', 0))

                    if qtd_a_entrar > 0:
                        produto = get_object_or_404(Produtos, id=produto_id)
                        produto.estoque_atual += qtd_a_entrar
                        produto.save()

            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})
