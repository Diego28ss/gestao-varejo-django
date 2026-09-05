import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.db import connections
import xml.etree.ElementTree as ET
import traceback
from datetime import timedelta
import math
from django.utils import timezone
from inventario.models import Vendas
from inventario.models.configuracoes import ConfiguracaoSistema

from inventario.models import Produtos, Marca, Familia, RelacaoEmbalagensTintometrico, RupturaEstoque, InventarioSessao, Usuarios
from inventario.forms import ProdutoForm

# ==========================================
# CONTROLO DE STOCK E CARGAS
# ==========================================
def tela_estoque_produtos(request):
    if 'usuario_logado' not in request.session: return redirect('login')

    if request.GET.get('limpar') == 'true':
        if 'filtro_estoque' in request.session:
            del request.session['filtro_estoque']
        return redirect('tela_estoque_produtos')

    filtros_sessao = request.session.get('filtro_estoque', {})

    if 'familia' in request.GET or 'marca' in request.GET or 'status' in request.GET or 'busca' in request.GET:
        if 'familia' in request.GET: filtros_sessao['familia'] = request.GET.get('familia', '')
        if 'marca' in request.GET: filtros_sessao['marca'] = request.GET.get('marca', '')
        if 'status' in request.GET: filtros_sessao['status'] = request.GET.get('status', '')
        if 'busca' in request.GET: filtros_sessao['busca'] = request.GET.get('busca', '')
        request.session['filtro_estoque'] = filtros_sessao
        request.session.modified = True

    produtos = Produtos.objects.select_related('marca', 'familia').all().order_by('-id')

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

    marcas = Marca.objects.all().order_by('nome')
    familias = Familia.objects.all().order_by('nome')

    unidades = []
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT nome FROM inventario_un ORDER BY nome")
            unidades = [{'nome': row[0]} for row in cursor.fetchall()]
    except Exception as e:
        print(f"Aviso: Tabela inventario_un ainda não configurada. Erro: {e}")

    bases_tintometrico = []
    tamanhos_tintometrico = []
    mapa_vinculos = {}
    corantes_tintometrico = []
    mapa_vinculos_pigmentos = {}

    try:
        ordem_embalagens = [1, 2, 3, 7, 8, 39, 21, 32, 9, 10, 28, 29, 30, 35, 36, 37, 38, 40, 41]
        with connections['tintometrico_db'].cursor() as cursor:
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
                
            cursor.execute("SELECT id_formula, letra_codigo, nome_pigmento FROM corantes ORDER BY letra_codigo")
            for row in cursor.fetchall():
                corantes_tintometrico.append({
                    'id_formula': row[0],
                    'letra': row[1],
                    'nome': row[2]
                })

            cursor.execute("SELECT produto_cod_interno, id_formula FROM corantes WHERE produto_cod_interno IS NOT NULL")
            for row in cursor.fetchall():
                mapa_vinculos_pigmentos[row[0]] = row[1]
                
    except Exception as e:
        print(f"ERRO AO BUSCAR DADOS DO TINTOMÉTRICO: {e}")

    context = {
        'produtos': produtos,
        'marcas': marcas,
        'familias': familias,
        'unidades': unidades,
        'bases_tintometrico': bases_tintometrico,
        'tamanhos_tintometrico': tamanhos_tintometrico,
        'mapa_vinculos': mapa_vinculos,
        'corantes_tintometrico': corantes_tintometrico,
        'mapa_vinculos_pigmentos': mapa_vinculos_pigmentos,
        'filtros_salvos': json.dumps(filtros_sessao)
    }
    return render(request, 'inventario/estoque_produtos.html', context)

def salvar_produto(request):
    if request.method == "POST":
        if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']:
            messages.error(request, "Acesso negado. Seu cargo não permite editar produtos.")
            return redirect('tela_estoque_produtos')
            
        dados_corrigidos = request.POST.copy()
        produto_id = dados_corrigidos.get('produto_id')
        cod_barras = dados_corrigidos.get('cod_barras', '').strip()
        cod_forn = dados_corrigidos.get('cod_forn', '').strip() 
        
        if cod_barras and cod_barras.upper() != 'SEM GTIN':
            query = Produtos.objects.filter(cod_barras=cod_barras)
            if produto_id: query = query.exclude(id=produto_id)
            produto_existente = query.first()
            if produto_existente:
                messages.error(request, f"Erro de Duplicidade: O código de barras {cod_barras} já pertence ao produto '{produto_existente.nome}'.")
                return redirect('tela_estoque_produtos')

        ncm_teste = dados_corrigidos.get('ncm', '').strip()
        csosn_teste = dados_corrigidos.get('cst_csosn', '').strip()
        unidade_teste = dados_corrigidos.get('unidade', '').strip()
        marca_teste = dados_corrigidos.get('marca', '').strip()
        familia_teste = dados_corrigidos.get('familia', '').strip()
        preco_teste = dados_corrigidos.get('preco_venda', '').strip()

        if not all([ncm_teste, csosn_teste, unidade_teste, marca_teste, familia_teste, preco_teste]):
            messages.error(request, "Segurança Fiscal: Marca, Família, NCM, CSOSN, Unidade e Preço de Venda são obrigatórios.")
            return redirect('tela_estoque_produtos')
        
        for campo in ['preco_custo', 'margem_lucro', 'preco_venda']:
            if dados_corrigidos.get(campo):
                dados_corrigidos[campo] = dados_corrigidos[campo].replace(',', '.')
        
        if produto_id:
            produto = get_object_or_404(Produtos, id=produto_id)
            form = ProdutoForm(dados_corrigidos, instance=produto)
        else:
            if not dados_corrigidos.get('cod_interno'):
                codigos_existentes = Produtos.objects.values_list('cod_interno', flat=True)
                numericos = [int(c) for c in codigos_existentes if c and c.isdigit()]
                proximo_numero = max(numericos) + 1 if numericos else 1
                novo_codigo = str(proximo_numero).zfill(6)
                
                while Produtos.objects.filter(cod_interno=novo_codigo).exists():
                    proximo_numero += 1
                    novo_codigo = str(proximo_numero).zfill(6)
                dados_corrigidos['cod_interno'] = novo_codigo

            form = ProdutoForm(dados_corrigidos)

        if form.is_valid():
            produto_salvo = form.save(commit=False)
            if cod_forn: produto_salvo.cod_forn = cod_forn
            produto_salvo.aviso_estoque = ""
            produto_salvo.save()
            
            es_base = request.POST.get('es_base_tintometrico') == 'on'
            base_sel = request.POST.get('base_tintometrico_selecionada')
            tamanho_sel = request.POST.get('tamanho_tintometrico_selecionado')
            es_corante = request.POST.get('es_corante_tintometrico') == 'on'
            corante_sel = request.POST.get('corante_tintometrico_selecionado')
            
            try:
                RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').filter(
                    produto_cod_interno_id=produto_salvo.cod_interno
                ).delete()
                if es_base and base_sel and tamanho_sel:
                    RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').update_or_create(
                        codigo_base_tintometrico=base_sel,
                        tamanho_codigo=tamanho_sel,
                        defaults={'produto_cod_interno_id': produto_salvo.cod_interno}
                    )
                with connections['tintometrico_db'].cursor() as cursor:
                    cursor.execute("UPDATE corantes SET produto_cod_interno = NULL WHERE produto_cod_interno = %s", [produto_salvo.cod_interno])
                    if es_corante and corante_sel:
                        cursor.execute("UPDATE corantes SET produto_cod_interno = %s WHERE id_formula = %s", [produto_salvo.cod_interno, corante_sel])
                messages.success(request, "Produto salvo com sucesso!")
            except Exception as e:
                messages.warning(request, f"Produto salvo, mas ocorreu erro no tintométrico: {str(e)}")
        else:
            messages.error(request, "Erro ao validar os dados do produto.")
            
    return redirect('tela_estoque_produtos')

def excluir_produto(request, id):
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']:
        messages.error(request, "Acesso negado. Seu cargo não permite inativar produtos.")
        return redirect('tela_estoque_produtos')
        
    try:
        produto = get_object_or_404(Produtos, id=id)
        produto.status = 'INATIVO'
        produto.save(update_fields=['status'])
        messages.success(request, f"O produto '{produto.nome}' foi INATIVADO com sucesso.")
    except Exception as e:
        messages.error(request, f"Erro ao inativar produto: {str(e)}")
    return redirect('tela_estoque_produtos')

def tela_entrada_carga(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']:
        messages.error(request, "Acesso restrito a Gerentes e Supervisores.")
        return redirect('tela_estoque_produtos')
    return render(request, 'inventario/entrada_carga.html')

def api_produto_por_codigo(request):
    codigo = request.GET.get('codigo', '').strip()
    produto = Produtos.objects.filter(cod_barras=codigo).first()
    if produto:
        return JsonResponse({'status': 'ok', 'id': produto.id, 'nome': produto.nome})
    return JsonResponse({'status': 'erro', 'mensagem': 'Produto não cadastrado!'})

def api_efetivar_entrada(request):
    if request.method == 'POST':
        try:
            from inventario.models import InventarioSessao
            # 🚀 PASSO 2: TRAVA DO CAMINHÃO
            if InventarioSessao.objects.filter(status='ABERTO').exists():
                return JsonResponse({'status': 'erro', 'mensagem': 'BLOQUEADO: Existem inventários ABERTOS. Finalize ou cancele-os antes de dar entrada em mercadorias.'})

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
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/painel_estoque.html')

def api_importar_xml(request):
    if request.method == 'POST' and request.FILES.get('xml_file'):
        xml_file = request.FILES['xml_file']
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
            infNFe = root.find('.//ns:infNFe', ns)
            if infNFe is None: return JsonResponse({'erro': 'NFe inválida.'}, status=400)

            def get_text(node, path, default=''):
                if node is None: return default
                el = node.find(path, ns)
                return el.text if el is not None else default

            chave_acesso = infNFe.attrib.get('Id', '')[3:] if 'Id' in infNFe.attrib else 'Extração Falhou'
            ide = infNFe.find('ns:ide', ns)
            emit = infNFe.find('ns:emit', ns)
            dest = infNFe.find('ns:dest', ns)
            total = infNFe.find('ns:total/ns:ICMSTot', ns)
            transp = infNFe.find('ns:transp', ns)
            infAdic = infNFe.find('ns:infAdic', ns)

            numero_nota = get_text(ide, 'ns:nNF', 'S/N')
            serie = get_text(ide, 'ns:serie', '1')
            modelo = get_text(ide, 'ns:mod', '55')
            data_emissao = get_text(ide, 'ns:dhEmi')[:10]
            data_saida = get_text(ide, 'ns:dhSaiEnt')[:10]
            natOp = get_text(ide, 'ns:natOp')
            
            enderEmit = emit.find('ns:enderEmit', ns)
            fornecedor = {
                'nome': get_text(emit, 'ns:xNome', 'Desconhecido'),
                'cnpj': get_text(emit, 'ns:CNPJ'),
                'ie': get_text(emit, 'ns:IE'),
                'im': get_text(emit, 'ns:IM'),
                'crt': get_text(emit, 'ns:CRT'),
                'endereco': f"{get_text(enderEmit, 'ns:xLgr')}, {get_text(enderEmit, 'ns:nro')} - {get_text(enderEmit, 'ns:xBairro')}",
                'cidade_uf': f"{get_text(enderEmit, 'ns:xMun')} - {get_text(enderEmit, 'ns:UF')} - {get_text(enderEmit, 'ns:CEP')}",
                'telefone': get_text(enderEmit, 'ns:fone')
            }

            enderDest = dest.find('ns:enderDest', ns) if dest else None
            destinatario = {
                'nome': get_text(dest, 'ns:xNome'),
                'cnpj': get_text(dest, 'ns:CNPJ'),
                'ie': get_text(dest, 'ns:IE'),
                'endereco': f"{get_text(enderDest, 'ns:xLgr')}, {get_text(enderDest, 'ns:nro')} - {get_text(enderDest, 'ns:xBairro')}",
                'cidade_uf': f"{get_text(enderDest, 'ns:xMun')} - {get_text(enderDest, 'ns:UF')} - {get_text(enderDest, 'ns:CEP')}",
                'telefone': get_text(dest, 'ns:fone'),
                'email': get_text(dest, 'ns:email')
            }

            impostos = {
                'vProd': get_text(total, 'ns:vProd', '0.00'), 'vNF': get_text(total, 'ns:vNF', '0.00'),
                'vBC': get_text(total, 'ns:vBC', '0.00'), 'vICMS': get_text(total, 'ns:vICMS', '0.00'),
                'vBCST': get_text(total, 'ns:vBCST', '0.00'), 'vST': get_text(total, 'ns:vST', '0.00'),
                'vFrete': get_text(total, 'ns:vFrete', '0.00'), 'vSeg': get_text(total, 'ns:vSeg', '0.00'),
                'vDesc': get_text(total, 'ns:vDesc', '0.00'), 'vII': get_text(total, 'ns:vII', '0.00'),
                'vIPI': get_text(total, 'ns:vIPI', '0.00'), 'vPIS': get_text(total, 'ns:vPIS', '0.00'),
                'vCOFINS': get_text(total, 'ns:vCOFINS', '0.00'), 'vFCPST': get_text(total, 'ns:vFCPST', '0.00'),
                'vOutro': get_text(total, 'ns:vOutro', '0.00')
            }

            transporta = transp.find('ns:transporta', ns) if transp else None
            veicTransp = transp.find('ns:veicTransp', ns) if transp else None
            vol = transp.find('ns:vol', ns) if transp else None
            transporte = {
                'modFrete': get_text(transp, 'ns:modFrete', '9'),
                'nome': get_text(transporta, 'ns:xNome', 'O Mesmo (Próprio)'),
                'cnpj': get_text(transporta, 'ns:CNPJ'),
                'ie': get_text(transporta, 'ns:IE'),
                'endereco': f"{get_text(transporta, 'ns:xEnder')} - {get_text(transporta, 'ns:xMun')}-{get_text(transporta, 'ns:UF')}",
                'placa': get_text(veicTransp, 'ns:placa'),
                'rntc': get_text(veicTransp, 'ns:RNTC'),
                'uf_veiculo': get_text(veicTransp, 'ns:UF'),
                'qVol': get_text(vol, 'ns:qVol', '0'),
                'esp': get_text(vol, 'ns:esp'),
                'marca': get_text(vol, 'ns:marca'),
                'pesoL': get_text(vol, 'ns:pesoL', '0.000'),
                'pesoB': get_text(vol, 'ns:pesoB', '0.000')
            }

            informacoes = {
                'fisco': get_text(infAdic, 'ns:infAdFisco'),
                'contribuinte': get_text(infAdic, 'ns:infCpl')
            }

            produtos = []
            for idx, det in enumerate(infNFe.findall('ns:det', ns)):
                prod = det.find('ns:prod', ns)
                imposto = det.find('ns:imposto', ns)
                icms_node = imposto.find('.//ns:ICMS/*', ns) if imposto else None
                ipi_node = imposto.find('.//ns:IPI/*/ns:pIPI', ns) if imposto else None
                cst = get_text(icms_node, 'ns:CST') if get_text(icms_node, 'ns:CST') else get_text(icms_node, 'ns:CSOSN')
                picms = get_text(icms_node, 'ns:pICMS', '0.00')
                pipi = ipi_node.text if ipi_node is not None else '0.00'

                cod_forn_xml = get_text(prod, 'ns:cProd')
                cod_barras_xml = get_text(prod, 'ns:cEAN', 'SEM GTIN')

                cod_interno_vinculado = ""
                nome_interno_vinculado = ""
                
                if cod_forn_xml:
                    prod_db = Produtos.objects.filter(cod_forn=cod_forn_xml, status='ATIVO').first()
                    if not prod_db and cod_barras_xml and cod_barras_xml.upper() != 'SEM GTIN':
                        prod_db = Produtos.objects.filter(cod_barras=cod_barras_xml, status='ATIVO').first()
                    if prod_db:
                        cod_interno_vinculado = prod_db.cod_interno
                        nome_interno_vinculado = prod_db.nome

                produtos.append({
                    'id_linha': idx + 1,
                    'codigo_fornecedor': cod_forn_xml,
                    'cod_barras': cod_barras_xml,
                    'ncm': get_text(prod, 'ns:NCM', ''),                 
                    'descricao': get_text(prod, 'ns:xProd'),
                    'cfop_origem': get_text(prod, 'ns:CFOP'),
                    'qtd': get_text(prod, 'ns:qCom', '0'),
                    'unidade': get_text(prod, 'ns:uCom'),
                    'v_unitario': get_text(prod, 'ns:vUnCom', '0'),
                    'v_total': get_text(prod, 'ns:vProd', '0'),
                    'cst_csosn': cst,
                    'bc_icms': get_text(icms_node, 'ns:vBC', '0.00'),
                    'v_icms': get_text(icms_node, 'ns:vICMS', '0.00'),
                    'v_ipi': get_text(imposto, './/ns:IPI/*/ns:vIPI', '0.00'),
                    'p_icms': picms,
                    'p_ipi': pipi,
                    'jb_cod_interno': cod_interno_vinculado,
                    'jb_nome_interno': nome_interno_vinculado
                })

            return JsonResponse({
                'sucesso': True,
                'nota': {
                    'chave_acesso': chave_acesso, 'numero': numero_nota, 'serie': serie, 'modelo': modelo,
                    'data': data_emissao, 'data_saida': data_saida, 'natureza': natOp,
                    'fornecedor': fornecedor, 'destinatario': destinatario, 'impostos': impostos,
                    'transporte': transporte, 'informacoes': informacoes, 'produtos': produtos
                }
            })
        except Exception as e:
            return JsonResponse({'erro': f'Erro ao ler o ficheiro XML: {str(e)}'}, status=500)
    return JsonResponse({'erro': 'Nenhum ficheiro enviado.'}, status=400)

def api_pesquisar_produto_nfe(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2: return JsonResponse({'produtos': []})
    produtos = Produtos.objects.filter(Q(nome__icontains=q) | Q(cod_barras__icontains=q) | Q(cod_interno__icontains=q)).filter(status='ATIVO')[:15]
    resultado = [{'id': p.id, 'nome': p.nome, 'cod_interno': p.cod_interno if p.cod_interno else (p.cod_barras if p.cod_barras else str(p.id))} for p in produtos]
    return JsonResponse({'produtos': resultado})

def api_efetivar_nfe(request):
    if request.method == 'POST':
        try:
            from inventario.models import InventarioSessao
            # 🚀 PASSO 2: TRAVA DO CAMINHÃO (XML)
            if InventarioSessao.objects.filter(status='ABERTO').exists():
                return JsonResponse({'erro': 'BLOQUEADO: Existem inventários ABERTOS. Finalize ou cancele-os antes de importar Notas Fiscais.'}, status=400)

            dados = json.loads(request.body)
            itens = dados.get('itens', [])
            if not itens: return JsonResponse({'erro': 'Nenhum produto foi enviado para o estoque.'}, status=400)
            produtos_atualizados = 0

            with transaction.atomic():
                for item in itens:
                    cod_interno = item.get('codigo_interno')
                    qtd_final = int(item.get('qtd_final', 0))
                    custo_unitario_nfe = float(item.get('custo_unitario', 0.0))
                    cod_forn_nfe = item.get('codigo_fornecedor', '') 
                    ncm_nfe = item.get('ncm', '')    
                    cest_nfe = item.get('cest', '')  
                    cod_barras_nfe = item.get('cod_barras', '') 

                    if cod_interno and qtd_final > 0:
                        produto = Produtos.objects.filter(cod_interno=cod_interno).first()
                        if produto:
                            produto.estoque_atual += qtd_final
                            custo_atual_db = float(produto.preco_custo)
                            
                            # Atualiza o custo e ajusta o preço de venda se o custo subir
                            if custo_unitario_nfe > 0:
                                if custo_unitario_nfe > custo_atual_db:
                                    margem_fixa = float(produto.margem_lucro)
                                    novo_preco_venda = custo_unitario_nfe + (custo_unitario_nfe * (margem_fixa / 100.0))
                                    produto.aviso_estoque = f"O Custo aumentou de R$ {custo_atual_db:.2f} para R$ {custo_unitario_nfe:.2f}. O Preço de Venda subiu para R$ {novo_preco_venda:.2f} para manter a margem de {margem_fixa}%."
                                    produto.preco_venda = novo_preco_venda
                                produto.preco_custo = custo_unitario_nfe
                            
                            if cod_forn_nfe and (not produto.cod_forn or produto.cod_forn != cod_forn_nfe):
                                produto.cod_forn = cod_forn_nfe
                            if ncm_nfe and ncm_nfe != 'N/A':
                                produto.ncm = ncm_nfe
                            if cest_nfe and cest_nfe != 'N/A':
                                produto.cest = cest_nfe
                                
                            if cod_barras_nfe and cod_barras_nfe.upper() != 'SEM GTIN':
                                if not produto.cod_barras or produto.cod_barras != cod_barras_nfe:
                                    produto.cod_barras = cod_barras_nfe
                                
                            produto.save()
                            produtos_atualizados += 1

            return JsonResponse({'sucesso': True, 'mensagem': f'{produtos_atualizados} produtos processados! Verifique os alertas no Estoque.'})
        except Exception as e:
            return JsonResponse({'erro': f'Erro ao processar: {str(e)}'}, status=500)
    return JsonResponse({'erro': 'Método inválido.'}, status=400)

def tela_suprir_estoque(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']:
        messages.error(request, "Acesso restrito a Gerentes e Supervisores.")
        return redirect('tela_estoque_produtos')
        
    config, _ = ConfiguracaoSistema.objects.get_or_create(id=1)
    dias_seguranca = config.dias_seguranca_estoque
    data_inicio = timezone.now() - timedelta(days=14)
    vendas_14d = Vendas.objects.filter(status='VENDA', data_venda__gte=data_inicio)
    
    vendas_por_produto = {}
    for venda in vendas_14d:
        if venda.cupom_texto:
            try:
                itens = json.loads(venda.cupom_texto)
                for item in itens:
                    prod_id = int(item.get('id', 0))
                    qtd = int(item.get('qtd', 0))
                    if prod_id > 0:
                        vendas_por_produto[prod_id] = vendas_por_produto.get(prod_id, 0) + qtd
            except Exception:
                pass

    rupturas_por_produto = RupturaEstoque.objects.filter(resolvido=False).values('produto_id').annotate(total_falta=Sum('quantidade_perdida'))
    mapa_rupturas = {r['produto_id']: r['total_falta'] for r in rupturas_por_produto}
                
    produtos_necessarios = []
    todos_produtos = Produtos.objects.filter(status='ATIVO')
    
    for prod in todos_produtos:
        qtd_vendida = vendas_por_produto.get(prod.id, 0)
        qtd_ruptura = mapa_rupturas.get(prod.id, 0)
        vmd = qtd_vendida / 14.0 
        qtd_recom = math.ceil(vmd * dias_seguranca) 
        qtd_pedir = (qtd_recom - prod.estoque_atual) + qtd_ruptura
        
        if qtd_pedir > 0 or qtd_ruptura > 0:
            produtos_necessarios.append({
                'id': prod.id, 'nome': prod.nome, 'cod_interno': prod.cod_interno or 'S/C',
                'estoque_atual': prod.estoque_atual, 'qtd_vendida_14d': qtd_vendida,
                'qtd_ruptura': qtd_ruptura, 'qtd_recom': qtd_recom,
                'qtd_pedir': qtd_pedir if qtd_pedir > 0 else qtd_ruptura
            })
            
    produtos_necessarios.sort(key=lambda x: x['qtd_pedir'], reverse=True)
    return render(request, 'inventario/suprir_estoque.html', {'produtos': produtos_necessarios, 'dias_seguranca': dias_seguranca})

def api_resolver_ruptura(request, produto_id):
    if request.method == 'POST':
        try:
            RupturaEstoque.objects.filter(produto_id=produto_id, resolvido=False).update(resolvido=True)
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_registrar_encomenda(request, produto_id):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            qtd = dados.get('quantidade')
            data_previsao = dados.get('data_previsao')
            if not qtd or not data_previsao: return JsonResponse({'status': 'erro', 'mensagem': 'Quantidade e Data são obrigatórios.'})
            produto = Produtos.objects.get(id=produto_id)
            produto.qtd_em_transito = int(qtd)
            produto.data_previsao_chegada = data_previsao
            produto.save()
            RupturaEstoque.objects.filter(produto=produto, resolvido=False).update(resolvido=True)
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_finalizar_carrinho_gerente(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            itens = dados.get('itens', [])
            for item in itens:
                produto_id = item.get('id')
                qtd = int(item.get('qtd', 0))
                data_previsao = item.get('data')
                if produto_id and qtd > 0:
                    produto = Produtos.objects.get(id=produto_id)
                    produto.qtd_em_transito = qtd
                    produto.data_previsao_chegada = data_previsao
                    produto.save()
                    RupturaEstoque.objects.filter(produto=produto, resolvido=False).update(resolvido=True)
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def tela_carrinho_pedido(request):
    return render(request, 'inventario/carrinho_pedido.html')

def gerar_pdf_suprimentos(request):
    if 'usuario_logado' not in request.session: return redirect('login')
        
    config, _ = ConfiguracaoSistema.objects.get_or_create(id=1)
    dias_seguranca = config.dias_seguranca_estoque
    data_inicio = timezone.now() - timedelta(days=14)
    vendas_14d = Vendas.objects.filter(status='VENDA', data_venda__gte=data_inicio)
    
    vendas_por_produto = {}
    for venda in vendas_14d:
        if venda.cupom_texto:
            try:
                itens = json.loads(venda.cupom_texto)
                for item in itens:
                    prod_id = int(item.get('id', 0))
                    qtd = int(item.get('qtd', 0))
                    if prod_id > 0:
                        vendas_por_produto[prod_id] = vendas_por_produto.get(prod_id, 0) + qtd
            except Exception: pass

    rupturas_por_produto = RupturaEstoque.objects.filter(resolvido=False).values('produto_id').annotate(total_falta=Sum('quantidade_perdida'))
    mapa_rupturas = {r['produto_id']: r['total_falta'] for r in rupturas_por_produto}
                
    produtos_necessarios = []
    todos_produtos = Produtos.objects.filter(status='ATIVO')
    
    for prod in todos_produtos:
        qtd_vendida = vendas_por_produto.get(prod.id, 0)
        qtd_ruptura = mapa_rupturas.get(prod.id, 0) 
        vmd = qtd_vendida / 14.0 
        qtd_recom = math.ceil(vmd * dias_seguranca) 
        qtd_pedir = (qtd_recom - prod.estoque_atual) + qtd_ruptura
        
        if qtd_pedir > 0 or qtd_ruptura > 0:
            produtos_necessarios.append({
                'id': prod.id, 'nome': prod.nome, 'cod_interno': prod.cod_interno or 'S/C',
                'estoque_atual': prod.estoque_atual, 'qtd_vendida_14d': qtd_vendida,
                'qtd_ruptura': qtd_ruptura, 'qtd_recom': qtd_recom,
                'qtd_pedir': qtd_pedir if qtd_pedir > 0 else qtd_ruptura
            })
            
    produtos_necessarios.sort(key=lambda x: x['qtd_pedir'], reverse=True)
    return render(request, 'inventario/relatorio_suprir_pdf.html', {'produtos': produtos_necessarios, 'dias': dias_seguranca})

def tela_inventario_sessao(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']:
        messages.error(request, "Acesso restrito a Gerentes e Supervisores.")
        return redirect('tela_painel_estoque')

    status_filtro = request.GET.get('status', 'TODOS')
    from inventario.models import InventarioSessao, SessaoEstoque
    
    inventarios_db = InventarioSessao.objects.select_related('criado_por', 'sessao_estoque').all().order_by('-id')
    if status_filtro != 'TODOS':
        inventarios_db = inventarios_db.filter(status=status_filtro)

    lista_inventarios = []
    for inv in inventarios_db:
        lista_inventarios.append({
            'id': inv.id,
            'sessao_nome': inv.sessao_estoque.nome if inv.sessao_estoque else 'SESSÃO LIVRE',
            'data_inicio': inv.data_inicio.strftime('%d/%m/%Y %H:%M'),
            'criado_por': inv.criado_por.login.upper() if inv.criado_por else 'SISTEMA',
            'qtd_itens': inv.qtd_itens_contados(),
            'status': inv.status
        })
        
    sessoes_disponiveis = SessaoEstoque.objects.all().order_by('nome')

    return render(request, 'inventario/inventario_sessao.html', {
        'inventarios': lista_inventarios, 
        'filtro_atual': status_filtro,
        'sessoes': sessoes_disponiveis
    })

def criar_novo_inventario(request):
    if request.method == 'POST':
        if 'usuario_logado' not in request.session: return redirect('login')
        if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']: return redirect('tela_painel_estoque')

        try:
            from inventario.models import Usuarios, InventarioSessao, SessaoEstoque
            acao = request.POST.get('acao')
            
            if acao == 'nova':
                nova_sessao_nome = request.POST.get('nova_sessao_nome', '').strip().upper()
                if not nova_sessao_nome:
                    messages.error(request, "Digite um nome para a nova sessão.")
                    return redirect('tela_inventario_sessao')
                sessao_obj, _ = SessaoEstoque.objects.get_or_create(nome=nova_sessao_nome)
            else:
                sessao_id = request.POST.get('sessao_existente_id')
                if not sessao_id:
                    messages.error(request, "Selecione uma sessão existente.")
                    return redirect('tela_inventario_sessao')
                sessao_obj = SessaoEstoque.objects.get(id=sessao_id)

            usuario_logado = Usuarios.objects.filter(login=request.session.get('usuario_logado')).first()
            novo_lote = InventarioSessao.objects.create(
                criado_por=usuario_logado, 
                status='ABERTO',
                sessao_estoque=sessao_obj
            )
            
            messages.success(request, f"Lote aberto para: {sessao_obj.nome}! Inicie a contagem.")
            return redirect('tela_contagem_inventario', sessao_id=novo_lote.id)
            
        except Exception as e:
            messages.error(request, f"Erro ao criar inventário: {str(e)}")
            
    return redirect('tela_inventario_sessao')

def tela_contagem_inventario(request, sessao_id):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    from inventario.models import InventarioSessao, InventarioItem, Produtos
    sessao = get_object_or_404(InventarioSessao, id=sessao_id)
    
    if sessao.status == 'FINALIZADO':
        messages.warning(request, "Este inventário já foi fechado.")
        return redirect('tela_inventario_sessao')
        
    if sessao.sessao_estoque:
        produtos_esperados = Produtos.objects.filter(sessao_estoque=sessao.sessao_estoque, status='ATIVO')
        for prod in produtos_esperados:
            InventarioItem.objects.get_or_create(
                sessao=sessao, 
                produto=prod,
                defaults={'saldo_sistema': prod.estoque_atual, 'saldo_fisico': 0}
            )
            
    itens_contados = InventarioItem.objects.filter(sessao=sessao).select_related(
        'produto', 'produto__marca', 'produto__familia', 'produto__sessao_estoque'
    ).order_by('-id')
    
    return render(request, 'inventario/inventario_contagem.html', {'sessao': sessao, 'itens': itens_contados})

def api_bipar_item_inventario(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            sessao_id = dados.get('sessao_id')
            codigo = dados.get('codigo', '').strip()
            qtd = int(dados.get('quantidade', 1))
            
            from inventario.models import InventarioSessao, InventarioItem, Produtos
            sessao = InventarioSessao.objects.get(id=sessao_id)
            if sessao.status == 'FINALIZADO':
                return JsonResponse({'status': 'erro', 'mensagem': 'Inventário fechado.'})
                
            produto = Produtos.objects.filter(Q(cod_barras=codigo) | Q(cod_interno=codigo)).first()
            if not produto:
                return JsonResponse({'status': 'erro', 'mensagem': 'Produto não encontrado.'})
            
            item, created = InventarioItem.objects.get_or_create(
                sessao=sessao, produto=produto,
                defaults={'saldo_sistema': produto.estoque_atual, 'saldo_fisico': 0}
            )
            item.saldo_fisico += qtd
            item.save()
            
            return JsonResponse({'status': 'sucesso', 'produto_nome': produto.nome, 'qtd_atualizada': item.saldo_fisico})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_autorizar_intruso(request, item_id):
    if request.method == 'POST':
        try:
            from inventario.models import InventarioItem
            item = InventarioItem.objects.get(id=item_id)
            produto = item.produto
            produto.sessao_estoque = item.sessao.sessao_estoque
            produto.save(update_fields=['sessao_estoque'])
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro'})

def api_remover_item(request, item_id):
    if request.method == 'POST':
        try:
            from inventario.models import InventarioItem
            InventarioItem.objects.get(id=item_id).delete()
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro'})

def api_finalizar_inventario(request, sessao_id):
    if request.method == 'POST':
        try:
            from inventario.models import InventarioSessao, InventarioItem
            sessao = InventarioSessao.objects.get(id=sessao_id)
            sessao.status = 'FINALIZADO'
            sessao.data_finalizacao = timezone.now()
            sessao.save()
            
            itens = InventarioItem.objects.filter(sessao=sessao)
            for item in itens:
                produto = item.produto
                produto.estoque_atual = item.saldo_fisico
                if sessao.sessao_estoque:
                    produto.sessao_estoque = sessao.sessao_estoque
                produto.save(update_fields=['estoque_atual', 'sessao_estoque'])
                
            messages.success(request, f"Inventário #{sessao_id} finalizado! Estoque e endereçamentos atualizados.")
            return JsonResponse({'status': 'sucesso', 'url': '/estoquepainel/inventario-sessao/'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})

def api_excluir_inventario(request, sessao_id):
    if request.method == 'POST':
        try:
            from inventario.models import InventarioSessao
            InventarioSessao.objects.get(id=sessao_id).delete()
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro'})


def api_autorizar_todos_intrusos(request, sessao_id):
    if request.method == 'POST':
        try:
            from inventario.models import InventarioSessao, InventarioItem
            sessao = InventarioSessao.objects.get(id=sessao_id)
            if not sessao.sessao_estoque:
                return JsonResponse({'status': 'erro', 'mensagem': 'Sessão alvo não definida.'})
                
            itens = InventarioItem.objects.filter(sessao=sessao)
            for item in itens:
                if item.produto.sessao_estoque != sessao.sessao_estoque:
                    item.produto.sessao_estoque = sessao.sessao_estoque
                    item.produto.save(update_fields=['sessao_estoque'])
                    
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro'})

def tela_relatorio_inventario(request, sessao_id):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    from inventario.models import InventarioSessao, InventarioItem
    sessao = get_object_or_404(InventarioSessao, id=sessao_id)
    itens = InventarioItem.objects.filter(sessao=sessao).select_related('produto')
    
    return render(request, 'inventario/inventario_relatorio.html', {'sessao': sessao, 'itens': itens})

def gerar_pdf_inventario(request, sessao_id):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    from inventario.models import InventarioSessao, InventarioItem
    sessao = get_object_or_404(InventarioSessao, id=sessao_id)
    itens = InventarioItem.objects.filter(sessao=sessao).select_related('produto')
    
    return render(request, 'inventario/inventario_relatorio_pdf.html', {'sessao': sessao, 'itens': itens})

def tela_inventario_dinamico(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']:
        messages.error(request, "Acesso restrito a Gerentes e Supervisores.")
        return redirect('tela_painel_estoque')

    status_filtro = request.GET.get('status', 'TODOS')
    from inventario.models import InventarioSessao, Marca, Familia, Produtos
    
    inventarios_db = InventarioSessao.objects.select_related('criado_por', 'filtro_marca', 'filtro_familia').all().order_by('-id')
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
            'status': inv.status
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
    if request.method == 'POST':
        from inventario.models import Usuarios, InventarioSessao, InventarioItem, Produtos, Marca, Familia
        
        marca_id = request.POST.get('filtro_marca')
        familia_id = request.POST.get('filtro_familia')
        unidade = request.POST.get('filtro_unidade')
        
        # 🚀 TRAVA 1: Exigir no mínimo 2 filtros para não travar o servidor
        filtros_preenchidos = sum([1 for f in [marca_id, familia_id, unidade] if f])
        if filtros_preenchidos < 2:
            messages.error(request, "Para a segurança do sistema, selecione no mínimo 2 filtros (Ex: Marca + Unidade).")
            return redirect('tela_inventario_dinamico')

        marca_obj = Marca.objects.filter(id=marca_id).first() if marca_id else None
        familia_obj = Familia.objects.filter(id=familia_id).first() if familia_id else None

        usuario_logado = Usuarios.objects.filter(login=request.session.get('usuario_logado')).first()
        
        query = Q(status='ATIVO')
        if marca_obj: query &= Q(marca=marca_obj)
        if familia_obj: query &= Q(familia=familia_obj)
        if unidade: query &= Q(unidade__iexact=unidade.strip())
        
        produtos_alvo = Produtos.objects.filter(query)

        # 🚀 PASSO 3: TRAVA DE SOBREPOSIÇÃO DE ÁREA
        produtos_em_contagem = InventarioItem.objects.filter(
            sessao__status='ABERTO', 
            produto__in=produtos_alvo
        ).values_list('produto__nome', flat=True)

        if produtos_em_contagem.exists():
            nomes_conflito = ", ".join(list(produtos_em_contagem)[:2])
            messages.error(request, f"BLOQUEIO: Alguns produtos já estão em outro inventário aberto (Ex: {nomes_conflito}...). Termine-o primeiro.")
            return redirect('tela_inventario_dinamico')
        
        # 🚀 TRAVA 2: Criar Sessão e tirar o SNAPSHOT IMEDIATO
        novo_lote = InventarioSessao.objects.create(
            criado_por=usuario_logado, status='ABERTO',
            filtro_marca=marca_obj, filtro_familia=familia_obj, filtro_unidade=unidade
        )
        
        # Congela o estoque atual de todos os produtos do filtro no exato segundo da criação
        itens_snapshot = [
            InventarioItem(sessao=novo_lote, produto=p, saldo_sistema=p.estoque_atual, saldo_fisico=0, contado=False)
            for p in produtos_alvo
        ]
        InventarioItem.objects.bulk_create(itens_snapshot)
        
        messages.success(request, f"Lote #{novo_lote.id} aberto! Snapshot congelado para {len(itens_snapshot)} produtos.")
        return redirect('tela_contagem_dinamica', sessao_id=novo_lote.id)
            
    return redirect('tela_inventario_dinamico')

def tela_contagem_dinamica(request, sessao_id):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    from inventario.models import InventarioSessao, InventarioItem
    sessao = get_object_or_404(InventarioSessao, id=sessao_id)
    
    if sessao.status == 'FINALIZADO':
        messages.warning(request, "Este inventário já foi fechado e não pode ser alterado.")
        return redirect('tela_inventario_dinamico')
            
    itens_contados = InventarioItem.objects.filter(sessao=sessao).select_related(
        'produto', 'produto__marca', 'produto__familia'
    ).order_by('-contado', '-id') # Mostra os já contados primeiro
    
    return render(request, 'inventario/inventario_contagemdin.html', {'sessao': sessao, 'itens': itens_contados})

def api_bipar_item_dinamico(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            sessao_id = dados.get('sessao_id')
            codigo = dados.get('codigo', '').strip()
            qtd = int(dados.get('quantidade', 1))
            
            from inventario.models import InventarioSessao, InventarioItem, Produtos
            sessao = InventarioSessao.objects.get(id=sessao_id)
            
            if sessao.status == 'FINALIZADO':
                return JsonResponse({'status': 'erro', 'mensagem': 'Inventário fechado.'})
                
            # Procura PRIMEIRO no snapshot fotográfico
            item_snapshot = InventarioItem.objects.filter(
                sessao=sessao
            ).filter(
                Q(produto__cod_barras=codigo) | Q(produto__cod_interno=codigo)
            ).first()
            
            if item_snapshot:
                # 🚀 TRAVA NOVA: E se o gerente inativou o produto AGORA com o inventário aberto? Bloqueia!
                if item_snapshot.produto.status == 'INATIVO':
                    return JsonResponse({'status': 'erro', 'mensagem': f'❌ BLOQUEADO: O produto {item_snapshot.produto.nome} está INATIVO no sistema e não pode ser contado.'})

                # Atualiza a contagem
                item_snapshot.saldo_fisico += qtd
                item_snapshot.contado = True
                item_snapshot.save(update_fields=['saldo_fisico', 'contado'])
                
                return JsonResponse({'status': 'sucesso', 'produto_nome': item_snapshot.produto.nome, 'qtd_atualizada': item_snapshot.saldo_fisico})
            
            else:
                # Se não achou no snapshot, procura no banco geral
                produto_intruso = Produtos.objects.filter(Q(cod_barras=codigo) | Q(cod_interno=codigo)).first()
                if produto_intruso:
                    # 🚀 TRAVA NOVA: Se bipou uma lata velha que já estava inativa no sistema
                    if produto_intruso.status == 'INATIVO':
                        return JsonResponse({'status': 'erro', 'mensagem': f'❌ BLOQUEADO: Você bipou {produto_intruso.nome}, mas ele está INATIVO no sistema!'})
                        
                    return JsonResponse({'status': 'erro', 'mensagem': f'❌ PRODUTO INTRUSO! {produto_intruso.nome} não pertence aos filtros.'})
                else:
                    return JsonResponse({'status': 'erro', 'mensagem': '❌ Produto não encontrado no sistema.'})
            
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_revisao_omissos(request, sessao_id):
    """ Retorna a lista de itens que estavam no snapshot mas não foram bipados """
    try:
        from inventario.models import InventarioItem
        omissos = InventarioItem.objects.filter(sessao_id=sessao_id, contado=False).select_related('produto')
        lista = [{'id': i.id, 'nome': i.produto.nome, 'saldo_congelado': i.saldo_sistema} for i in omissos]
        return JsonResponse({'status': 'sucesso', 'omissos': lista})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})

def api_finalizar_inventario_dinamico(request, sessao_id):
    """ A Grande Matemática da Reconciliação com Loja Aberta """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            acao_omissos = dados.get('acao_omissos', 'IGNORAR') # 'ZERAR' ou 'IGNORAR'
            
            from inventario.models import InventarioSessao, InventarioItem, Vendas, Kardex
            sessao = InventarioSessao.objects.get(id=sessao_id)
            sessao.status = 'FINALIZADO'
            sessao.data_finalizacao = timezone.now()
            
            # 1. Busca todas as vendas faturadas/finalizadas desde o Snapshot até Agora
            vendas_periodo = Vendas.objects.filter(
                status__in=['FATURADO', 'FINALIZADO'],
                data_venda__gte=sessao.data_inicio,
                data_venda__lte=sessao.data_finalizacao
            )
            
            # Mapa de vendas no formato {produto_id: quantidade_vendida}
            mapa_vendas = {}
            for v in vendas_periodo:
                if v.cupom_texto:
                    try:
                        carrinho = json.loads(v.cupom_texto)
                        for item in carrinho:
                            p_id = int(item.get('id', 0))
                            if p_id > 0:
                                mapa_vendas[p_id] = mapa_vendas.get(p_id, 0) + int(item.get('qtd', 0))
                    except: pass
            
            total_sobra = 0.0
            total_perda = 0.0
            kardex_list = []

            # 2. Aplica a fórmula para todos os itens do inventário
            itens = InventarioItem.objects.filter(sessao=sessao).select_related('produto')
            for item in itens:
                produto = item.produto
                
                # Se for omisso e a regra for ignorar, não altera o estoque físico do sistema
                if not item.contado and acao_omissos == 'IGNORAR':
                    continue
                    
                # Se for omisso e a regra for zerar, assume que a contagem física é 0
                if not item.contado and acao_omissos == 'ZERAR':
                    item.saldo_fisico = 0
                    item.contado = True
                    item.save(update_fields=['saldo_fisico', 'contado'])

                qtd_vendida = mapa_vendas.get(produto.id, 0)
                
                # 🚀 MATEMÁTICA: Estoque Novo = Fisico Contado - Vendas Pós-Snapshot
                novo_estoque = item.saldo_fisico - qtd_vendida
                if novo_estoque < 0: novo_estoque = 0 # Prevenção
                
                # 🚀 PASSO 1 e 4: O KARDEX E O FINANCEIRO
                saldo_anterior_real = produto.estoque_atual
                qtd_ajuste = novo_estoque - saldo_anterior_real
                
                if qtd_ajuste != 0: # Se o estoque sofreu alteração de fato
                    custo = float(produto.preco_custo)
                    valor_ajuste = abs(qtd_ajuste) * custo
                    
                    if qtd_ajuste > 0:
                        total_sobra += valor_ajuste
                        tipo_mov = 'AJUSTE (SOBRA)'
                    else:
                        total_perda += valor_ajuste
                        tipo_mov = 'AJUSTE (PERDA)'
                        
                    # Registra a alteração no livro-razão
                    kardex_list.append(Kardex(
                        produto=produto,
                        tipo_movimento=tipo_mov,
                        quantidade=qtd_ajuste,
                        saldo_anterior=saldo_anterior_real,
                        saldo_novo=novo_estoque,
                        motivo=f"Inventário Rotativo #{sessao.id}",
                        operador=sessao.criado_por,
                        custo_unitario=custo,
                        valor_total=valor_ajuste
                    ))

                produto.estoque_atual = novo_estoque
                produto.save(update_fields=['estoque_atual'])
            
            # Salva o Kardex no banco de dados de uma só vez (Performance)
            if kardex_list:
                Kardex.objects.bulk_create(kardex_list)
                
            # Salva o resultado financeiro no cabeçalho do Inventário
            sessao.valor_sobra = total_sobra
            sessao.valor_perda = total_perda
            sessao.save(update_fields=['status', 'data_finalizacao', 'valor_sobra', 'valor_perda'])
                
            messages.success(request, f"Rotativo #{sessao_id} Finalizado! Reconciliação e Kardex gravados.")
            return JsonResponse({'status': 'sucesso', 'url': '/estoquepainel/inventario-sessao/'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

