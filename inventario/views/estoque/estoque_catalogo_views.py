import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import connections
from django.db.models import Q
from inventario.models import Produtos, Marca, Familia
from inventario.forms import ProdutoForm

# Importa a inteligência do Service
from inventario.services.estoque.estoque_catalogo_service import (
    gerar_codigo_interno,
    verificar_duplicidade_cod_barras,
    processar_salvamento_produto,
    inativar_produto,
    obter_dados_tintometrico
)


def tela_painel_estoque(request):
    """ View Fina: Renderiza o dashboard principal com os atalhos do estoque """
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/painel_estoque.html')

def tela_estoque_produtos(request):
    """ View Fina: Processa os filtros de pesquisa e renderiza a tabela de produtos """
    if 'usuario_logado' not in request.session: return redirect('login')

    if request.GET.get('limpar') == 'true':
        if 'filtro_estoque' in request.session:
            del request.session['filtro_estoque']
        return redirect('tela_estoque_produtos')

    filtros_sessao = request.session.get('filtro_estoque', {})

    if any(k in request.GET for k in ['familia', 'marca', 'status', 'busca', 'aviso']):
        if 'familia' in request.GET: filtros_sessao['familia'] = request.GET.get('familia', '')
        if 'marca' in request.GET: filtros_sessao['marca'] = request.GET.get('marca', '')
        if 'status' in request.GET: filtros_sessao['status'] = request.GET.get('status', '')
        if 'busca' in request.GET: filtros_sessao['busca'] = request.GET.get('busca', '')
        if 'aviso' in request.GET: filtros_sessao['aviso'] = request.GET.get('aviso', '')
        request.session['filtro_estoque'] = filtros_sessao
        request.session.modified = True

    produtos = Produtos.objects.select_related('marca', 'familia').all().order_by('nome')

    if filtros_sessao.get('status'):
        produtos = produtos.filter(status=filtros_sessao['status'])
    if filtros_sessao.get('familia'):
        produtos = produtos.filter(familia__nome__iexact=filtros_sessao['familia'])
    if filtros_sessao.get('marca'):
        produtos = produtos.filter(marca__nome__iexact=filtros_sessao['marca'])
    if filtros_sessao.get('busca'):
        termo = filtros_sessao['busca']
        produtos = produtos.filter(
            Q(nome__icontains=termo) | 
            Q(cod_barras__icontains=termo) | 
            Q(cod_interno__icontains=termo)
        )
        
    if filtros_sessao.get('aviso') == 'COM_AVISO':
        produtos = produtos.exclude(Q(aviso_estoque__isnull=True) | Q(aviso_estoque__exact=''))
    elif filtros_sessao.get('aviso') == 'SEM_AVISO':
        produtos = produtos.filter(Q(aviso_estoque__isnull=True) | Q(aviso_estoque__exact=''))

    marcas = Marca.objects.all().order_by('nome')
    familias = Familia.objects.all().order_by('nome')

    unidades = []
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT nome FROM inventario_un ORDER BY nome")
            unidades = [{'nome': row[0]} for row in cursor.fetchall()]
    except Exception: pass

    # Consulta os dados auxiliares no banco secundário através do Service
    bases, tamanhos, mapa_v, corantes, mapa_vp = obter_dados_tintometrico()

    context = {
        'produtos': produtos,
        'marcas': marcas,
        'familias': familias,
        'unidades': unidades,
        'bases_tintometrico': bases,
        'tamanhos_tintometrico': tamanhos,
        'mapa_vinculos': mapa_v,
        'corantes_tintometrico': corantes,
        'mapa_vinculos_pigmentos': mapa_vp,
        'filtros_salvos': json.dumps(filtros_sessao)
    }
    return render(request, 'inventario/estoque_produtos.html', context)
    
def salvar_produto(request):
    """ View Fina: Valida a submissão do formulário, segurança fiscal e aciona a gravação """
    if request.method == "POST":
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        try:
            if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']:
                msg = "Acesso negado. Seu cargo não permite editar produtos."
                if is_ajax: return JsonResponse({'sucesso': False, 'erro': msg})
                messages.error(request, msg)
                return redirect('tela_estoque_produtos')
                
            dados_corrigidos = request.POST.copy()
            produto_id = dados_corrigidos.get('produto_id')
            cod_barras = dados_corrigidos.get('cod_barras', '').strip()
            
            if request.POST.get('sem_ncm') == 'on':
                dados_corrigidos['ncm'] = 'N/A'
            
            # Delega verificação de duplicidade de código de barras ao Service
            produto_existente = verificar_duplicidade_cod_barras(cod_barras, produto_id)
            if produto_existente:
                erro_msg = f"Erro de Duplicidade: O código de barras {cod_barras} já pertence ao produto '{produto_existente.nome}'."
                if is_ajax: return JsonResponse({'sucesso': False, 'erro': erro_msg})
                messages.error(request, erro_msg)
                return redirect('tela_estoque_produtos')

            obrigatorios = ['ncm', 'unidade', 'marca', 'familia', 'preco_venda']
            if not all(dados_corrigidos.get(campo, '').strip() for campo in obrigatorios):
                erro_msg = "Segurança Fiscal: Marca, Família, NCM, Unidade e Preço de Venda são obrigatórios."
                if is_ajax: return JsonResponse({'sucesso': False, 'erro': erro_msg})
                messages.error(request, erro_msg)
                return redirect('tela_estoque_produtos')
            
            for campo in ['preco_custo', 'margem_lucro', 'preco_venda']:
                if dados_corrigidos.get(campo):
                    dados_corrigidos[campo] = dados_corrigidos[campo].replace(',', '.')
            
            custo_antigo, venda_antigo = 0.0, 0.0
            
            if produto_id:
                produto = get_object_or_404(Produtos, id=produto_id)
                custo_antigo = float(produto.preco_custo or 0)
                venda_antigo = float(produto.preco_venda or 0)
                form = ProdutoForm(dados_corrigidos, request.FILES, instance=produto)
            else:
                if not dados_corrigidos.get('cod_interno'):
                    dados_corrigidos['cod_interno'] = gerar_codigo_interno()
                form = ProdutoForm(dados_corrigidos, request.FILES)

            if form.is_valid():
                produto_salvo = form.save(commit=False)
                
                # Delega a lógica de inserção fiscal e tintométrica ao Service
                produto_final = processar_salvamento_produto(
                    produto_salvo, dados_corrigidos, produto_id, custo_antigo, venda_antigo
                )
                
                if is_ajax:
                    return JsonResponse({
                        'sucesso': True, 
                        'mensagem': "Produto salvo com sucesso!",
                        'is_novo': not bool(produto_id),
                        'produto': {
                            'id': produto_final.id,
                            'nome': produto_final.nome,
                            'preco_custo': f"{produto_final.preco_custo:.2f}".replace('.', ','),
                            'preco_venda': f"{produto_final.preco_venda:.2f}".replace('.', ',')
                        }
                    })

                messages.success(request, "Produto salvo com sucesso!")
            else:
                erros_str = " | ".join([f"{k}: {v[0]}" for k, v in form.errors.items()])
                if is_ajax: return JsonResponse({'sucesso': False, 'erro': f"Faltam dados obrigatórios: {erros_str}"})
                messages.error(request, f"Erro ao validar: {erros_str}")
                
        except Exception as e:
            if is_ajax: return JsonResponse({'sucesso': False, 'erro': f"Erro no Servidor: {str(e)}"})
            messages.error(request, f"Erro Interno: {str(e)}")
                
    return redirect('tela_estoque_produtos')

def excluir_produto(request, id):
    """ View Fina: Executa a validação de segurança e inativa o produto através do Service """
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']:
        messages.error(request, "Acesso negado. Seu cargo não permite inativar produtos.")
        return redirect('tela_estoque_produtos')
        
    try:
        produto = inativar_produto(id)
        messages.success(request, f"O produto '{produto.nome}' foi INATIVADO com sucesso.")
    except Exception as e:
        messages.error(request, f"Erro ao inativar produto: {str(e)}")
    return redirect('tela_estoque_produtos')

def api_produto_por_codigo(request):
    """ View Fina: Busca um produto genérico por código (usado em modais e integrações do PDV) """
    if request.method == 'GET':
        codigo = request.GET.get('codigo', '').strip()
        produto = Produtos.objects.filter(Q(cod_barras=codigo) | Q(cod_interno=codigo)).first()
        
        if produto:
            return JsonResponse({
                'status': 'sucesso',
                'produto': {
                    'id': produto.id,
                    'nome': produto.nome,
                    'estoque_atual': produto.estoque_atual,
                    'preco_venda': float(produto.preco_venda or 0.0),
                    'preco_custo': float(produto.preco_custo or 0.0)
                }
            })
        return JsonResponse({'status': 'erro', 'mensagem': 'Produto não encontrado.'})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})
