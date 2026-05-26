from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connections
from django.contrib import messages
from inventario.models import RelacaoEmbalagensTintometrico, Produtos
from inventario.forms import TintometricoForm
from inventario.services import tintometrico as tintometrico_service
from django.db import transaction


# ==========================================
# 🎨 VIEWS DO TINTOMÉTRICO
# ==========================================

from django.http import JsonResponse
from inventario.models import RelacaoEmbalagensTintometrico, Produtos

def api_buscar_detalhes_base(request):
    """
    API Invisível: Recebe a Base e o Tamanho, cruza os bancos de dados
    e devolve os dados físicos e financeiros da lata.
    """
    if request.method == "GET":
        base_exigida = request.GET.get('base', '').strip()
        tamanho = request.GET.get('tamanho', '').strip()

        # 🕵️‍♂️ RASTREADOR LIGADO: Imprime no terminal o que o HTML está a pedir
        print(f"\n🕵️‍♂️ [API TINTOMÉTRICO] Iniciando busca...")
        print(f"👉 Base pedida pelo HTML: '{base_exigida}'")
        print(f"👉 Tamanho pedido pelo HTML: '{tamanho}'")

        if not base_exigida or not tamanho:
            print("❌ Erro: Faltou a base ou o tamanho.")
            return JsonResponse({'status': 'erro', 'mensagem': 'Base e tamanho são obrigatórios.'})

        try:
            # 1️⃣ PASSO: Vai ao banco Secundário (tintometrico_db) fazer a tradução
            relacao = RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').filter(
                codigo_base_tintometrico=base_exigida,
                tamanho_codigo=tamanho
            ).first()

            # Se não houver vínculo, avisa o JavaScript para limpar a tela
            if not relacao:
                print("❌ Vínculo NÃO ENCONTRADO na tabela de tradução!")
                return JsonResponse({
                    'status': 'nao_encontrado', 
                    'mensagem': 'Esta combinação ainda não foi vinculada no inventário.'
                })

            # A chave de ligação!
            chave_cod_interno = relacao.produto_cod_interno_id
            print(f"✅ Vínculo encontrado na tabela! Código Interno gerado: '{chave_cod_interno}'")

            # 2️⃣ PASSO: Vai ao banco Principal (jb_tintas) buscar a lata física
            produto = Produtos.objects.using('default').filter(cod_interno=chave_cod_interno).first()

            if not produto:
                print(f"❌ Produto com código '{chave_cod_interno}' não encontrado no stock principal!")
                return JsonResponse({
                    'status': 'erro', 
                    'mensagem': f'O vínculo existe ({chave_cod_interno}), mas o produto foi apagado do stock!'
                })

            print("✅ Tudo perfeito! Enviando os dados de volta para a tela...")
            
            # 3️⃣ PASSO: Empacota a informação e envia de volta
            return JsonResponse({
                'status': 'sucesso',
                'dados': {
                    'cod_interno': produto.cod_interno,
                    'cod_barras': produto.cod_barras if produto.cod_barras else '---',
                    'preco_custo': float(produto.preco_custo),
                    'preco_venda': float(produto.preco_venda),
                    'estoque_atual': produto.estoque_atual,
                    'unidade': produto.unidade
                }
            })

        except Exception as e:
            print(f"🔥 ERRO FATAL NO CÓDIGO PYTHON: {str(e)}")
            return JsonResponse({'status': 'erro', 'mensagem': f'Erro interno: {str(e)}'})
            
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido. Use GET.'})


def cadastrar_tintometrico(request):
    if request.method == 'POST':
        bases = request.POST.getlist('base[]')
        tamanhos = request.POST.getlist('tamanho[]')
        produtos_cods = request.POST.getlist('produto[]')
        
        salvos = 0
        try:
            # transaction.atomic garante que salvemos tudo com segurança
            with transaction.atomic(using='tintometrico_db'):
                for base, tamanho, cod_produto in zip(bases, tamanhos, produtos_cods):
                    cod_produto = cod_produto.strip()
                    if cod_produto:  # Só tenta salvar se o usuário digitou algum código
                        try:
                            # Confirma se o produto realmente existe no estoque principal
                            produto_obj = Produtos.objects.using('default').get(cod_interno=cod_produto)
                            
                            # Atualiza se já existir, cria se for novo (Evita erro de duplicidade)
                            RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').update_or_create(
                                codigo_base_tintometrico=base,
                                tamanho_codigo=tamanho,
                                defaults={'produto_cod_interno': produto_obj}
                            )
                            salvos += 1
                        except Produtos.DoesNotExist:
                            messages.warning(request, f"Aviso: Produto {cod_produto} não encontrado. O vínculo da base '{base}' foi ignorado.")
            
            messages.success(request, f"✅ {salvos} vínculos foram atualizados/salvos com sucesso!")
            return redirect('lista_tintometrico')
        
        except Exception as e:
            messages.error(request, f"❌ Erro crítico ao salvar lote: {str(e)}")

    # ==========================================
    # LÓGICA DO GET: MONTAR A GRADE PARA A TELA
    # ==========================================
    todas_combinacoes = tintometrico_service.obter_todas_bases_tamanhos()
    vinculos_existentes = RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').all()
    
    # Cria um dicionário rápido para saber o que já está preenchido: {"BASE_3.2L": "002541"}
    mapa_vinculos = {f"{v.codigo_base_tintometrico}_{v.tamanho_codigo}": v.produto_cod_interno_id for v in vinculos_existentes}
    
    grade = []
    for combo in todas_combinacoes:
        chave = f"{combo['base']}_{combo['tamanho']}"
        grade.append({
            'base': combo['base'],
            'tamanho': combo['tamanho'],
            'produto_vinculado': mapa_vinculos.get(chave, '') # Se não tiver vínculo, fica vazio
        })
    
    produtos_estoque = Produtos.objects.all()
    
    return render(request, 'inventario/cadastro_tintometrico.html', {
        'grade': grade,
        'produtos_estoque': produtos_estoque
    })


def cadastrar_tintometrico(request):
    if request.method == 'POST':
        form = TintometricoForm(request.POST)
        if form.is_valid():
            # 1. Cria a instância do vínculo 
            vinculo = form.save(commit=False)
            
            # 2. Salva direto no banco tintométrico! 
            vinculo.save(using='tintometrico_db')
            
            # 3. Exibe sucesso e recarrega a página
            messages.success(request, "✅ Vínculo salvo com sucesso!")
            return redirect('lista_tintometrico')  
        else:
            messages.error(request, "❌ Erro ao salvar. Verifique se os dados estão corretos ou se este vínculo já existe.")
    else:
        form = TintometricoForm()
    
    produtos = Produtos.objects.all()
    
    return render(request, 'inventario/cadastro_tintometrico.html', {
        'form': form, 
        'produtos_estoque': produtos
    })

def consultar_dados_embalagem(request):
    """
    View que recebe a base e o tamanho e retorna os dados do produto vinculado.
    Versão melhorada com iexact para evitar erros de letras maiúsculas/minúsculas.
    """
    base = request.GET.get('base', '').strip()
    tamanho = request.GET.get('tamanho', '').strip()

    try:
        # Usa .filter().first() e __iexact para uma busca mais segura e flexível
        relacao = RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').filter(
            codigo_base_tintometrico__iexact=base,
            tamanho_codigo__iexact=tamanho
        ).first()
        
        if relacao:
            produto = relacao.produto_cod_interno
            return JsonResponse({
                'sucesso': True,
                'cod_interno': produto.cod_interno,
                'cod_barras': getattr(produto, 'cod_barras', "SEM GTIN") or "SEM GTIN",
                'estoque': produto.estoque_atual,
                'unidade': getattr(produto, 'unidade', 'UN')
            })
        else:
            # 🔥 AGORA A API NOS CONTA O QUE TENTOU PROCURAR!
            return JsonResponse({
                'sucesso': False, 
                'mensagem': f'FALHA: O sistema procurou pela Base "{base}" no Tamanho "{tamanho}", mas não achou vínculo.'
            })
            
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})
    

def api_buscar_cores(request):
    query = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0)) 
    
    if len(query) < 2:
        return JsonResponse({'cores': [], 'has_more': False})

    resultados_dict = {}
    
    # 🔥 CORRIGIDO AQUI: 'tintometrico_db'
    with connections['tintometrico_db'].cursor() as cursor:
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
