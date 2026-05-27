from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connections
from django.contrib import messages
from django.db.models import Q
from django.db import transaction

from inventario.models import RelacaoEmbalagensTintometrico, Produtos
from inventario.forms import TintometricoForm
from inventario.services import tintometrico as tintometrico_service

# ==========================================
# 🎨 VIEWS DO TINTOMÉTRICO
# ==========================================

def api_buscar_detalhes_base(request):
    """
    API Invisível: Recebe a Base/Tamanho ou um Código Interno Direto (Troca de Base).
    """
    if request.method == "GET":
        # 🚀 Lógica Nova: Se vier o código direto, foi uma troca de base pelo usuário!
        cod_interno_direto = request.GET.get('cod_interno', '').strip()
        
        base_exigida = request.GET.get('base', '').strip()
        tamanho = request.GET.get('tamanho', '').strip()

        try:
            produto = None
            nome_substituto = None

            # 1️⃣ Cenário: O usuário trocou a base manualmente no modal
            if cod_interno_direto:
                produto = Produtos.objects.using('default').filter(cod_interno=cod_interno_direto).first()
                if produto:
                    nome_substituto = produto.nome

            # 2️⃣ Cenário: Busca normal pela receita da máquina
            elif base_exigida and tamanho:
                relacao = RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').filter(
                    codigo_base_tintometrico=base_exigida,
                    tamanho_codigo=tamanho
                ).first()

                if not relacao:
                    return JsonResponse({
                        'status': 'nao_encontrado', 
                        'mensagem': 'Esta combinação ainda não foi vinculada no inventário.'
                    })

                chave_cod_interno = relacao.produto_cod_interno_id
                produto = Produtos.objects.using('default').filter(cod_interno=chave_cod_interno).first()
            
            else:
                return JsonResponse({'status': 'erro', 'mensagem': 'Parâmetros insuficientes.'})

            # Verifica se achou o produto final em qualquer um dos cenários
            if not produto:
                return JsonResponse({
                    'status': 'erro', 
                    'mensagem': 'O produto não foi encontrado no stock principal!'
                })

            # Empacota a informação e envia de volta
            dados_resposta = {
                'cod_interno': produto.cod_interno,
                'cod_barras': produto.cod_barras if produto.cod_barras else '---',
                'preco_custo': float(produto.preco_custo),
                'preco_venda': float(produto.preco_venda),
                'estoque_atual': produto.estoque_atual,
                'unidade': produto.unidade
            }
            
            # Se foi trocado, avisa o Javascript para alterar o nome na tela
            if nome_substituto:
                dados_resposta['nome_substituto'] = nome_substituto

            return JsonResponse({
                'status': 'sucesso',
                'dados': dados_resposta
            })

        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': f'Erro interno: {str(e)}'})
            
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido. Use GET.'})


# 🚀 NOVA API: Para pesquisar os produtos no Modal de Troca de Base
def api_pesquisar_base_alternativa(request):
    query = request.GET.get('q', '').strip()
    
    if len(query) < 3:
        return JsonResponse({'produtos': []})

    # Procura pelo nome, código de barras ou código interno
    produtos = Produtos.objects.using('default').filter(
        Q(nome__icontains=query) | 
        Q(cod_barras__icontains=query) |
        Q(cod_interno__icontains=query)
    ).filter(status='ATIVO')[:15] # Limita a 15 resultados rápidos

    lista_produtos = []
    for p in produtos:
        lista_produtos.append({
            'cod_interno': p.cod_interno,
            'cod_barras': getattr(p, 'cod_barras', '---') or '---',
            'nome': p.nome,
            'estoque': p.estoque_atual,
            'preco_venda': float(p.preco_venda)
        })

    return JsonResponse({'produtos': lista_produtos})


def cadastrar_tintometrico(request):
    if request.method == 'POST':
        bases = request.POST.getlist('base[]')
        tamanhos = request.POST.getlist('tamanho[]')
        produtos_cods = request.POST.getlist('produto[]')
        
        salvos = 0
        try:
            with transaction.atomic(using='tintometrico_db'):
                for base, tamanho, cod_produto in zip(bases, tamanhos, produtos_cods):
                    cod_produto = cod_produto.strip()
                    if cod_produto:
                        try:
                            produto_obj = Produtos.objects.using('default').get(cod_interno=cod_produto)
                            
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

    todas_combinacoes = tintometrico_service.obter_todas_bases_tamanhos()
    vinculos_existentes = RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').all()
    
    mapa_vinculos = {f"{v.codigo_base_tintometrico}_{v.tamanho_codigo}": v.produto_cod_interno_id for v in vinculos_existentes}
    
    grade = []
    for combo in todas_combinacoes:
        chave = f"{combo['base']}_{combo['tamanho']}"
        grade.append({
            'base': combo['base'],
            'tamanho': combo['tamanho'],
            'produto_vinculado': mapa_vinculos.get(chave, '')
        })
    
    produtos_estoque = Produtos.objects.all()
    
    return render(request, 'inventario/cadastro_tintometrico.html', {
        'grade': grade,
        'produtos_estoque': produtos_estoque
    })


def consultar_dados_embalagem(request):
    base = request.GET.get('base', '').strip()
    tamanho = request.GET.get('tamanho', '').strip()

    try:
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


# 🚀 NOVA VIEW: Painel central de seleção da marca
def tela_painel_tintometrico(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    return render(request, 'inventario/tintometrico_painel.html')


# 🚀 VIEW ATUALIZADA: Agora aceita a marca dinamicamente na URL
def tela_tintometrico(request, marca=None):
    if 'usuario_logado' not in request.session:
        return redirect('login')
        
    context = {
        'marca_selecionada': marca.upper() if marca else 'CORAL'
    }
    
    linhas, embalagens = tintometrico_service.obter_linhas_e_embalagens()
    context['linhas'], context['embalagens'] = linhas, embalagens
    
    cor_busca, linha_id, embalagem_id = request.GET.get('cor', ''), request.GET.get('linha', ''), request.GET.get('embalagem', '')
    
    if cor_busca and linha_id and embalagem_id:
        try:
            context['resultado'] = tintometrico_service.calcular_formula(cor_busca, linha_id, embalagem_id)
        except Exception as e:
            context['resultado'] = {'sucesso': False, 'erro': str(e)}
            
    return render(request, 'inventario/tintometrico.html', context)

