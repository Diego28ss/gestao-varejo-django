from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connections
from inventario.models import RelacaoEmbalagensTintometrico, Produtos # 🔥 Garanta que Produtos esteja aqui no topo!
from inventario.forms import TintometricoForm
from inventario.services import tintometrico as tintometrico_service

# ==========================================
# 🎨 VIEWS DO TINTOMÉTRICO
# ==========================================

def cadastrar_tintometrico(request):
    if request.method == 'POST':
        form = TintometricoForm(request.POST)
        if form.is_valid():
            # Cria a instância sem salvar no banco ainda
            vinculo = form.save(commit=False)
            
            # Busca o produto validado e vincula
            produto = Produtos.objects.get(cod_interno=form.cleaned_data['produto_cod_interno'])
            vinculo.produto_cod_interno = produto
            
            # Salva explicitamente no banco isolado
            vinculo.save(using='tintometrico_db')
            
            # Recarrega a própria página para limpar o formulário (ou mude para a URL que desejar)
            return redirect('lista_tintometrico')
    else:
        form = TintometricoForm()
    
    # Agora o Python sabe quem é 'Produtos' e vai carregar a lista para o autocomplete!
    produtos = Produtos.objects.all()
    
    return render(request, 'inventario/cadastro_tintometrico.html', {
        'form': form, 
        'produtos_estoque': produtos
    })


def consultar_dados_embalagem(request):
    """
    View que recebe a base e o tamanho e retorna os dados do produto vinculado.
    """
    base = request.GET.get('base', '').upper().strip()
    tamanho = request.GET.get('tamanho', '').upper().strip()

    try:
        # Busca a amarração usando o banco 'tintometrico_db'
        relacao = RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').get(
            codigo_base_tintometrico=base,
            tamanho_codigo=tamanho
        )
        
        # Acessa o produto relacionado (nome do campo definido no seu models.py)
        # Usei 'produto_cod_interno' conforme definimos anteriormente
        produto = relacao.produto_cod_interno
        
        return JsonResponse({
            'sucesso': True,
            'cod_interno': produto.cod_interno,
            'cod_barras': getattr(produto, 'cod_barras', "SEM GTIN") or "SEM GTIN",
            'estoque': produto.estoque_atual,
            'unidade': produto.unidade
        })
    except RelacaoEmbalagensTintometrico.DoesNotExist:
        return JsonResponse({
            'sucesso': False, 
            'mensagem': 'Nenhum produto vinculado encontrado para esta combinação.'
        })

def api_buscar_cores(request):
    # (Mantive sua lógica de busca inalterada pois ela funciona bem)
    query = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0)) 
    
    if len(query) < 2:
        return JsonResponse({'cores': [], 'has_more': False})

    resultados_dict = {}
    
    with connections['tintometrico'].cursor() as cursor:
        cursor.execute("""
            SELECT TRIM(nome_busca), TRIM(codigo_tecnico) 
            FROM cores 
            WHERE nome_busca LIKE %s OR codigo_tecnico LIKE %s 
            ORDER BY nome_busca
            LIMIT 26 OFFSET %s
        """, [f"%{query}%", f"%{query}%", offset])
        
        cores_banco = cursor.fetchall()
        if not cores_banco: return JsonResponse({'cores': [], 'has_more': False})

        codigos_e_nomes_para_busca = []
        for nome, codigo in cores_banco:
            chave = f"{nome}_{codigo}"
            resultados_dict[chave] = {'nome': nome, 'codigo': codigo, 'combinacoes_validas': []}
            codigos_e_nomes_para_busca.extend([nome.upper(), codigo.upper()])

        placeholders = ', '.join(['%s'] * len(codigos_e_nomes_para_busca))
        cursor.execute(f"""
            SELECT UPPER(TRIM(codigo_cor)), id_linha, id_emb 
            FROM formulas 
            WHERE UPPER(TRIM(codigo_cor)) IN ({placeholders})
        """, codigos_e_nomes_para_busca)
        
        formulas_banco = cursor.fetchall()
        for codigo_cor_formula, id_linha, id_emb in formulas_banco:
            for chave, dados in resultados_dict.items():
                if dados['nome'].upper() == codigo_cor_formula or dados['codigo'].upper() == codigo_cor_formula:
                    dados['combinacoes_validas'].append({'linha': str(id_linha), 'embalagem': str(id_emb)})
                
    todas_cores = list(resultados_dict.values())
    return JsonResponse({'cores': todas_cores[:25], 'has_more': len(todas_cores) > 25})

def tela_tintometrico(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
        
    context = {}
    linhas, embalagens = tintometrico_service.obter_linhas_e_embalagens()
    context['linhas'], context['embalagens'] = linhas, embalagens
    
    cor_busca, linha_id, embalagem_id = request.GET.get('cor', ''), request.GET.get('linha', ''), request.GET.get('embalagem', '')
    
    if cor_busca and linha_id and embalagem_id:
        try:
            context['resultado'] = tintometrico_service.calcular_formula(cor_busca, linha_id, embalagem_id)
        except Exception as e:
            context['resultado'] = {'sucesso': False, 'erro': str(e)}
            
    return render(request, 'inventario/tintometrico.html', context)
