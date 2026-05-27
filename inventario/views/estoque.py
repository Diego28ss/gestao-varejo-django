import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.db import connections

# Importação dos modelos para gerir o stock e tabelas auxiliares
from inventario.models import Produtos, Marca, Familia, RelacaoEmbalagensTintometrico
from inventario.forms import ProdutoForm

# ==========================================
# 📦 CONTROLO DE STOCK E CARGAS
# ==========================================

def tela_estoque_produtos(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    # 1. Busca todos os produtos do stock principal
    produtos = Produtos.objects.all()
    
    # Busca de Marcas e Famílias para preencher os menus suspensos
    marcas = Marca.objects.all().order_by('nome')
    familias = Familia.objects.all().order_by('nome')

    # 2. Listas para o modal tintométrico
    bases_tintometrico = []
    tamanhos_tintometrico = []
    mapa_vinculos = {}
    
    # Listas para os Pigmentos/Corantes
    corantes_tintometrico = []
    mapa_vinculos_pigmentos = {}

    try:
        ordem_embalagens = [1, 2, 3, 7, 8, 39, 21, 32, 9, 10, 28, 29, 30, 35, 36, 37, 38]
        with connections['tintometrico_db'].cursor() as cursor:
            
            # --- PARTE DAS BASES ---
            cursor.execute("SELECT DISTINCT nome_base FROM bases WHERE nome_base IS NOT NULL ORDER BY nome_base")
            bases_tintometrico = [row[0].strip() for row in cursor.fetchall() if row[0]]

            placeholders = ', '.join(['%s'] * len(ordem_embalagens))
            cursor.execute(f"SELECT id_emb, tamanho FROM embalagens WHERE id_emb IN ({placeholders})", ordem_embalagens)
            embalagens_banco = {row[0]: row[1].strip() for row in cursor.fetchall() if row[1]}
            
            for id_emb in ordem_embalagens:
                if id_emb in embalagens_banco:
                    tamanhos_tintometrico.append(embalagens_banco[id_emb])
                    
            vinculos_existentes = RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').all()
            for v in vinculos_existentes:
                mapa_vinculos[v.produto_cod_interno_id] = {
                    'codigo_base_tintometrico': v.codigo_base_tintometrico,
                    'tamanho_codigo': v.tamanho_codigo
                }
                
            # --- PARTE DOS CORANTES/PIGMENTOS ---
            # Busca a lista de corantes para preencher o Menu Suspenso
            cursor.execute("SELECT id_formula, letra_codigo, nome_pigmento FROM corantes ORDER BY letra_codigo")
            for row in cursor.fetchall():
                corantes_tintometrico.append({
                    'id_formula': row[0],
                    'letra': row[1],
                    'nome': row[2]
                })

            # Busca os corantes que já estão vinculados para o botão Editar lembrar a seleção
            cursor.execute("SELECT produto_cod_interno, id_formula FROM corantes WHERE produto_cod_interno IS NOT NULL")
            for row in cursor.fetchall():
                mapa_vinculos_pigmentos[row[0]] = row[1]
                
    except Exception as e:
        print(f"🔥 ERRO AO BUSCAR DADOS DO TINTOMÉTRICO: {e}")

    # Envia tudo empacotado para o HTML
    context = {
        'produtos': produtos,
        'marcas': marcas,
        'familias': familias,
        'bases_tintometrico': bases_tintometrico,
        'tamanhos_tintometrico': tamanhos_tintometrico,
        'mapa_vinculos': mapa_vinculos,
        'corantes_tintometrico': corantes_tintometrico,
        'mapa_vinculos_pigmentos': mapa_vinculos_pigmentos,
    }
    return render(request, 'inventario/estoque_produtos.html', context)


def salvar_produto(request):
    if request.method == "POST":
        # 1. Criamos uma cópia dos dados que vieram do formulário
        dados_corrigidos = request.POST.copy()
        
        # 2. Trocamos as vírgulas por pontos antes de entregar ao Django
        for campo in ['preco_custo', 'margem_lucro', 'preco_venda']:
            if dados_corrigidos.get(campo):
                dados_corrigidos[campo] = dados_corrigidos[campo].replace(',', '.')

        produto_id = dados_corrigidos.get('produto_id')
        
        # Verifica se estamos a editar ou a criar um novo registo
        if produto_id:
            produto = get_object_or_404(Produtos, id=produto_id)
            form = ProdutoForm(dados_corrigidos, instance=produto)
        else:
            # 🚀 GERAÇÃO DE CÓDIGO INTERNO BLINDADA
            if not dados_corrigidos.get('cod_interno'):
                codigos_existentes = Produtos.objects.values_list('cod_interno', flat=True)
                numericos = [int(c) for c in codigos_existentes if c and c.isdigit()]
                
                if numericos:
                    proximo_numero = max(numericos) + 1
                else:
                    proximo_numero = 1
                    
                novo_codigo = str(proximo_numero).zfill(6)
                
                while Produtos.objects.filter(cod_interno=novo_codigo).exists():
                    proximo_numero += 1
                    novo_codigo = str(proximo_numero).zfill(6)
                    
                dados_corrigidos['cod_interno'] = novo_codigo

            form = ProdutoForm(dados_corrigidos)

        if form.is_valid():
            # Guarda o produto no banco principal
            produto_salvo = form.save()
            
            # ==========================================
            # 🎨 LÓGICA DE VÍNCULO AUTOMÁTICO (TINTOMÉTRICO)
            # ==========================================
            es_base = request.POST.get('es_base_tintometrica') == 'on'
            base_sel = request.POST.get('base_tintometrica_selecionada')
            tamanho_sel = request.POST.get('tamanho_tintometrico_selecionado')
            
            es_corante = request.POST.get('es_corante_tintometrico') == 'on'
            corante_sel = request.POST.get('corante_tintometrico_selecionado')
            
            try:
                # 1️⃣ TRATA A BASE
                RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').filter(
                    produto_cod_interno_id=produto_salvo.cod_interno
                ).delete()
                
                if es_base and base_sel and tamanho_sel:
                    RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').update_or_create(
                        codigo_base_tintometrico=base_sel,
                        tamanho_codigo=tamanho_sel,
                        defaults={'produto_cod_interno_id': produto_salvo.cod_interno}
                    )

                # 2️⃣ TRATA O CORANTE
                with connections['tintometrico_db'].cursor() as cursor:
                    # Remove o código deste produto de qualquer outro corante antigo
                    cursor.execute(
                        "UPDATE corantes SET produto_cod_interno = NULL WHERE produto_cod_interno = %s",
                        [produto_salvo.cod_interno]
                    )
                    
                    # Se marcou como corante e escolheu um na lista, faz a amarração
                    if es_corante and corante_sel:
                        cursor.execute(
                            "UPDATE corantes SET produto_cod_interno = %s WHERE id_formula = %s",
                            [produto_salvo.cod_interno, corante_sel]
                        )
                    
                messages.success(request, "Produto salvo com sucesso!")
            except Exception as e:
                messages.warning(request, f"Produto salvo, mas ocorreu erro no tintométrico: {str(e)}")
        else:
            print("\n" + "="*40)
            print("❌ ERRO DE VALIDAÇÃO NO FORMULÁRIO:")
            for campo, erros in form.errors.items():
                print(f" -> Campo '{campo}': {erros}")
            print("="*40 + "\n")
            
            messages.error(request, "Erro ao validar os dados do produto.")
            
    return redirect('tela_estoque_produtos')


def excluir_produto(request, id):
    produto = get_object_or_404(Produtos, id=id)
    nome = produto.nome
    produto.delete()
    messages.success(request, f"Produto '{nome}' excluído com sucesso!")
    return redirect('tela_estoque_produtos')


def tela_entrada_carga(request):
    # Nota de histórico: O código exclui a funcionalidade "Importar XML NFe", mantendo apenas a entrada manual.
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
