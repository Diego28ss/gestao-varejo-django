import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.db import connections
import xml.etree.ElementTree as ET
import traceback


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
    # 1. Busca todos os produtos trazendo a marca e familia na mesma consulta
    produtos = Produtos.objects.select_related('marca', 'familia').all().order_by('-id')
    
    
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
        
        produto_id = dados_corrigidos.get('produto_id')
        cod_barras = dados_corrigidos.get('cod_barras', '').strip()
        
        # 🛡️ TRAVA 1: Impede Código de Barras Duplicado (Ignorando se estiver vazio ou SEM GTIN)
        if cod_barras and cod_barras.upper() != 'SEM GTIN':
            # Procura se existe outro produto com este código (que não seja ele mesmo em caso de edição)
            query = Produtos.objects.filter(cod_barras=cod_barras)
            if produto_id:
                query = query.exclude(id=produto_id)
                
            produto_existente = query.first()
            if produto_existente:
                messages.error(request, f"⚠️ Erro de Duplicidade: O código de barras {cod_barras} já pertence ao produto '{produto_existente.nome}'.")
                return redirect('tela_estoque_produtos')

        # --- 🛡️ INÍCIO DA BARREIRA DE FERRO FISCAL ---
        ncm_teste = dados_corrigidos.get('ncm', '').strip()
        csosn_teste = dados_corrigidos.get('cst_csosn', '').strip()
        unidade_teste = dados_corrigidos.get('unidade', '').strip()
        marca_teste = dados_corrigidos.get('marca', '').strip()
        familia_teste = dados_corrigidos.get('familia', '').strip()
        preco_teste = dados_corrigidos.get('preco_venda', '').strip()

        if not all([ncm_teste, csosn_teste, unidade_teste, marca_teste, familia_teste, preco_teste]):
            messages.error(request, "⚠️ Segurança Fiscal: Marca, Família, NCM, CSOSN, Unidade e Preço de Venda são obrigatórios.")
            return redirect('tela_estoque_produtos')
        # --- FIM DA BARREIRA DE FERRO FISCAL ---
        
        # 2. Trocamos as vírgulas por pontos antes de entregar ao Django
        for campo in ['preco_custo', 'margem_lucro', 'preco_venda']:
            if dados_corrigidos.get(campo):
                dados_corrigidos[campo] = dados_corrigidos[campo].replace(',', '.')
        
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
    # 🛡️ TRAVA 2: Anti-Exclusão (Apenas inativamos para proteger a contabilidade)
    try:
        produto = get_object_or_404(Produtos, id=id)
        produto.status = 'INATIVO'
        produto.save(update_fields=['status'])
        messages.success(request, f"✅ O produto '{produto.nome}' foi INATIVADO com sucesso e removido da tela de vendas.")
    except Exception as e:
        messages.error(request, f"⚠️ Erro ao inativar produto: {str(e)}")
    
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

def tela_painel_estoque(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    return render(request, 'inventario/painel_estoque.html')

def api_importar_xml(request):
    """Recebe o ficheiro XML, lê a NFe e devolve os dados estruturados em JSON"""
    if request.method == 'POST' and request.FILES.get('xml_file'):
        xml_file = request.FILES['xml_file']
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
            infNFe = root.find('.//ns:infNFe', ns)
            if infNFe is None:
                return JsonResponse({'erro': 'O ficheiro selecionado não parece ser uma NFe válida.'}, status=400)

            # 1. Chave de Acesso
            chave_acesso = infNFe.attrib.get('Id', '')[3:] if 'Id' in infNFe.attrib else 'Extração Falhou'

            ide = infNFe.find('ns:ide', ns)
            emit = infNFe.find('ns:emit', ns)
            total = infNFe.find('ns:total/ns:ICMSTot', ns)
            transp = infNFe.find('ns:transp', ns)

            numero_nota = ide.find('ns:nNF', ns).text if ide.find('ns:nNF', ns) is not None else 'S/N'
            data_emissao = ide.find('ns:dhEmi', ns).text[:10] if ide.find('ns:dhEmi', ns) is not None else ''
            
            fornecedor_nome = emit.find('ns:xNome', ns).text if emit.find('ns:xNome', ns) is not None else 'Desconhecido'
            fornecedor_cnpj = emit.find('ns:CNPJ', ns).text if emit.find('ns:CNPJ', ns) is not None else ''

            # 2. Endereço do Fornecedor
            enderEmit = emit.find('ns:enderEmit', ns)
            if enderEmit is not None:
                lgr = enderEmit.find('ns:xLgr', ns).text if enderEmit.find('ns:xLgr', ns) is not None else ''
                nro = enderEmit.find('ns:nro', ns).text if enderEmit.find('ns:nro', ns) is not None else ''
                bairro = enderEmit.find('ns:xBairro', ns).text if enderEmit.find('ns:xBairro', ns) is not None else ''
                mun = enderEmit.find('ns:xMun', ns).text if enderEmit.find('ns:xMun', ns) is not None else ''
                uf = enderEmit.find('ns:UF', ns).text if enderEmit.find('ns:UF', ns) is not None else ''
                fornecedor_endereco = f"{lgr}, {nro} - {bairro}, {mun} - {uf}"
            else:
                fornecedor_endereco = "Não informado"

            # 3. Totais e Impostos
            valor_total = total.find('ns:vNF', ns).text if total.find('ns:vNF', ns) is not None else '0.00'
            base_icms = total.find('ns:vBC', ns).text if total.find('ns:vBC', ns) is not None else '0.00'
            valor_icms = total.find('ns:vICMS', ns).text if total.find('ns:vICMS', ns) is not None else '0.00'
            valor_ipi = total.find('ns:vIPI', ns).text if total.find('ns:vIPI', ns) is not None else '0.00'
            valor_frete = total.find('ns:vFrete', ns).text if total.find('ns:vFrete', ns) is not None else '0.00'

            # 4. Transporte e Volumes
            if transp is not None:
                modFrete = transp.find('ns:modFrete', ns).text if transp.find('ns:modFrete', ns) is not None else '9'
                transporta = transp.find('ns:transporta', ns)
                if transporta is not None:
                    transp_nome = transporta.find('ns:xNome', ns).text if transporta.find('ns:xNome', ns) is not None else 'O Mesmo (Próprio)'
                    transp_cnpj = transporta.find('ns:CNPJ', ns).text if transporta.find('ns:CNPJ', ns) is not None else ''
                else:
                    transp_nome, transp_cnpj = 'O Mesmo (Próprio)', ''

                vol = transp.find('ns:vol', ns)
                if vol is not None:
                    transp_qVol = vol.find('ns:qVol', ns).text if vol.find('ns:qVol', ns) is not None else '0'
                    transp_pesoB = vol.find('ns:pesoB', ns).text if vol.find('ns:pesoB', ns) is not None else '0.000'
                else:
                    transp_qVol, transp_pesoB = '0', '0.000'
            else:
                modFrete, transp_nome, transp_cnpj, transp_qVol, transp_pesoB = '9', 'Não Informada', '', '0', '0.000'

            produtos = []
            for idx, det in enumerate(infNFe.findall('ns:det', ns)):
                prod = det.find('ns:prod', ns)
                produtos.append({
                    'id_linha': idx + 1,
                    'codigo_fornecedor': prod.find('ns:cProd', ns).text if prod.find('ns:cProd', ns) is not None else '',
                    'descricao': prod.find('ns:xProd', ns).text if prod.find('ns:xProd', ns) is not None else '',
                    'cfop_origem': prod.find('ns:CFOP', ns).text if prod.find('ns:CFOP', ns) is not None else '',
                    'qtd': prod.find('ns:qCom', ns).text if prod.find('ns:qCom', ns) is not None else '0',
                    'unidade': prod.find('ns:uCom', ns).text if prod.find('ns:uCom', ns) is not None else '',
                    'v_unitario': prod.find('ns:vUnCom', ns).text if prod.find('ns:vUnCom', ns) is not None else '0',
                    'v_total': prod.find('ns:vProd', ns).text if prod.find('ns:vProd', ns) is not None else '0',
                })

            return JsonResponse({
                'sucesso': True,
                'nota': {
                    'chave_acesso': chave_acesso,
                    'numero': numero_nota,
                    'data': data_emissao,
                    'fornecedor_nome': fornecedor_nome,
                    'fornecedor_cnpj': fornecedor_cnpj,
                    'fornecedor_endereco': fornecedor_endereco,
                    'impostos': {
                        'base_icms': base_icms, 'valor_icms': valor_icms, 'valor_ipi': valor_ipi, 'valor_frete': valor_frete
                    },
                    'transporte': {
                        'mod_frete': modFrete, 'nome': transp_nome, 'cnpj': transp_cnpj, 'volumes': transp_qVol, 'peso': transp_pesoB
                    },
                    'valor_total': valor_total,
                    'produtos': produtos
                }
            })

        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({'erro': f'Erro ao ler o ficheiro XML: {str(e)}'}, status=500)
            
    return JsonResponse({'erro': 'Nenhum ficheiro enviado ou método inválido.'}, status=400)

def api_pesquisar_produto_nfe(request):
    """Busca rápida de produtos da JB Tintas para vincular ao XML"""
    q = request.GET.get('q', '').strip()
    
    # Exige pelo menos 2 letras para não sobrecarregar o banco de dados
    if len(q) < 2:
        return JsonResponse({'produtos': []})

    # Procura no Nome, Código de Barras ou Código Interno
    produtos = Produtos.objects.filter(
        Q(nome__icontains=q) | 
        Q(cod_barras__icontains=q) | 
        Q(cod_interno__icontains=q)
    ).filter(status='ATIVO')[:15] # Traz apenas os 15 melhores resultados

    resultado = []
    for p in produtos:
        # Pega o Código Interno, se não tiver usa o de Barras, se não tiver usa o ID
        cod = p.cod_interno if p.cod_interno else (p.cod_barras if p.cod_barras else str(p.id))
        resultado.append({
            'id': p.id,
            'nome': p.nome,
            'cod_interno': cod
        })

    return JsonResponse({'produtos': resultado})
def api_efetivar_nfe(request):
    """Recebe a lista final conferida e injeta no estoque da JB Tintas"""
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            itens = dados.get('itens', [])

            if not itens:
                return JsonResponse({'erro': 'Nenhum produto foi enviado para o estoque.'}, status=400)

            produtos_atualizados = 0

            for item in itens:
                cod_interno = item.get('codigo_interno')
                qtd_final = int(item.get('qtd_final', 0))
                custo_unitario = float(item.get('custo_unitario', 0.0))

                # Ignora itens sem vínculo ou com quantidade zero
                if cod_interno and qtd_final > 0:
                    produto = Produtos.objects.filter(cod_interno=cod_interno).first()
                    if produto:
                        # 1. Atualiza a quantidade no stock
                        produto.estoque_atual += qtd_final
                        
                        # 2. Atualiza o preço de custo (se o valor na nota for maior que zero)
                        if custo_unitario > 0:
                            produto.preco_custo = custo_unitario
                            
                        produto.save()
                        produtos_atualizados += 1

            return JsonResponse({
                'sucesso': True, 
                'mensagem': f'{produtos_atualizados} produtos tiveram o seu estoque atualizado com sucesso!'
            })

        except Exception as e:
            return JsonResponse({'erro': f'Erro ao processar: {str(e)}'}, status=500)
            
    return JsonResponse({'erro': 'Método inválido.'}, status=400)

