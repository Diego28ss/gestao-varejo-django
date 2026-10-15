import xml.etree.ElementTree as ET
from django.db import transaction
from django.db.models import F
from inventario.models import Produtos, InventarioSessao, AlertaPreco

def processar_xml_nfe(xml_file):
    """ Serviço puro para ler, converter e estruturar os dados de um XML de NFe """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
    infNFe = root.find('.//ns:infNFe', ns)
    
    if infNFe is None: 
        raise ValueError('NFe inválida ou corrompida.')

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

    # Bloco: Fornecedor
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

    # Bloco: Destinatário
    enderDest = dest.find('ns:enderDest', ns) if dest else None
    destinatario = {
        'nome': get_text(dest, 'ns:xNome'),
        'cnpj': get_text(dest, 'ns:CNPJ'),
        'ie': get_text(dest, 'ns:IE'),
        'endereco': f"{get_text(enderDest, 'ns:xLgr')}, {get_text(enderDest, 'ns:nro')} - {get_text(enderDest, 'ns:xBairro')}",
        'cidade_uf': f"{get_text(enderDest, 'ns:xMun')} - {get_text(enderDest, 'ns:UF')} - {get_text(enderDest, 'ns:CEP')}",
        'telefone': get_text(dest, 'ns:fone'),
        'email': get_text(dest, 'ns:email')
    } if dest else {}

    # Bloco: Impostos (Restaurado completo para a UI)
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

    # Bloco: Transporte (Restaurado completo para a UI)
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

    # Bloco: Informações Adicionais (Restaurado completo para a UI)
    informacoes = {
        'fisco': get_text(infAdic, 'ns:infAdFisco'),
        'contribuinte': get_text(infAdic, 'ns:infCpl')
    }

    produtos_lista = []
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
        
        # Lógica de vínculo automático
        if cod_forn_xml:
            prod_db = Produtos.objects.filter(cod_forn=cod_forn_xml, status='ATIVO').first()
            if not prod_db and cod_barras_xml and cod_barras_xml.upper() != 'SEM GTIN':
                prod_db = Produtos.objects.filter(cod_barras=cod_barras_xml, status='ATIVO').first()
            if prod_db:
                cod_interno_vinculado = prod_db.cod_interno
                nome_interno_vinculado = prod_db.nome

        produtos_lista.append({
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

    return {
        'chave_acesso': chave_acesso,
        'numero': get_text(ide, 'ns:nNF', 'S/N'),
        'serie': get_text(ide, 'ns:serie', '1'),
        'modelo': get_text(ide, 'ns:mod', '55'),
        'data': get_text(ide, 'ns:dhEmi')[:10],
        'data_saida': get_text(ide, 'ns:dhSaiEnt')[:10],
        'natureza': get_text(ide, 'ns:natOp'),
        'fornecedor': fornecedor,
        'destinatario': destinatario,
        'impostos': impostos,
        'transporte': transporte,
        'informacoes': informacoes,
        'produtos': produtos_lista
    }

def efetivar_lote_nfe(itens):
    """ Regra de negócio pura: Atualiza estoques, custos e gera alertas """
    if InventarioSessao.objects.filter(status='ABERTO').exists():
        raise ValueError('BLOQUEADO: Existem inventários ABERTOS. Finalize ou cancele-os antes de importar Notas Fiscais.')

    if not itens: 
        raise ValueError('Nenhum produto foi enviado para o estoque.')
        
    produtos_atualizados = 0

    with transaction.atomic():
        for item in itens:
            cod_interno = item.get('codigo_interno')
            qtd_final = int(item.get('qtd_final', 0))
            custo_unitario_nfe = float(item.get('custo_unitario', 0.0))
            
            if cod_interno and qtd_final > 0:
                produto = Produtos.objects.filter(cod_interno=cod_interno).first()
                if produto:
                    produto.estoque_atual = F('estoque_atual') + qtd_final
                    
                    custo_atual_db = float(produto.preco_custo or 0.0)
                    venda_antigo = float(produto.preco_venda or 0.0)
                    
                    if custo_unitario_nfe > 0:
                        if custo_unitario_nfe > custo_atual_db:
                            # Nova entrada mais cara: Atualiza Venda e gera Alerta
                            margem_fixa = float(produto.margem_lucro or 0.0)
                            novo_preco_venda = custo_unitario_nfe + (custo_unitario_nfe * (margem_fixa / 100.0))
                            
                            if novo_preco_venda != venda_antigo:
                                AlertaPreco.objects.create(
                                    produto=produto,
                                    custo_anterior=custo_atual_db,
                                    custo_novo=custo_unitario_nfe,
                                    venda_anterior=venda_antigo,
                                    venda_novo=novo_preco_venda,
                                    origem='AUTOMATICA'
                                )

                            produto.preco_venda = novo_preco_venda
                            produto.preco_custo = custo_unitario_nfe
                            produto.aviso_estoque = "" 
                        
                        elif custo_unitario_nfe < custo_atual_db:
                            # Nova entrada mais barata: Trava na Gôndola para revisão
                            produto.aviso_estoque = f"BAIXA_CUSTO|{custo_atual_db:.2f}|{custo_unitario_nfe:.2f}"
                    
                    # Atualiza dados fiscais do XML se vieram
                    cod_forn_nfe = item.get('codigo_fornecedor', '') 
                    if cod_forn_nfe and produto.cod_forn != cod_forn_nfe:
                        produto.cod_forn = cod_forn_nfe
                        
                    ncm_nfe = item.get('ncm', '')
                    if ncm_nfe and ncm_nfe != 'N/A':
                        produto.ncm = ncm_nfe
                        
                    produto.save()
                    produtos_atualizados += 1
                    
    return produtos_atualizados

def estornar_lote_nfe(itens):
    """ Serviço para reverter estoques inseridos """
    if not itens: 
        raise ValueError('Nenhum produto foi enviado para o estorno.')
    
    produtos_estornados = 0
    with transaction.atomic():
        for item in itens:
            cod_interno = item.get('codigo_interno')
            qtd_final = int(item.get('qtd_final', 0))

            if cod_interno and qtd_final > 0:
                produto = Produtos.objects.filter(cod_interno=cod_interno).first()
                if produto:
                    estoque_real = produto.estoque_atual - qtd_final
                    produto.estoque_atual = 0 if estoque_real < 0 else estoque_real
                    produto.save(update_fields=['estoque_atual'])
                    produtos_estornados += 1
                    
    return produtos_estornados
