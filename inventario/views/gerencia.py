from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from django.utils import timezone
from inventario.models import Vendas, DadosNF, Clientes

# ==========================================
# PAINEL DE GERÊNCIA PRINCIPAL
# ==========================================
def tela_painel_gerencia(request):
    """
    Controla o acesso à tela centralizadora do Painel de Gerência.
    """
    if 'usuario_logado' not in request.session:
        return redirect('login')
    
    return render(request, 'inventario/painel_gerencia.html')


# ==========================================
# TELA: FILA FISCAL
# ==========================================
def emitir_notas(request):
    """
    Tela dedicada para o faturamento fiscal.
    Lista as vendas pendentes e também carrega todos os clientes para o seletor do Modal.
    """
    if 'usuario_logado' not in request.session:
        return redirect('login')

    vendas_pendentes = Vendas.objects.filter(
        status_fiscal='AGUARDANDO_EMISSAO'
    ).order_by('-data_venda')
    
    todos_clientes = Clientes.objects.all().order_by('nome')
    
    contexto = {
        'vendas_pendentes': vendas_pendentes,
        'todos_clientes': todos_clientes
    }
    
    return render(request, 'inventario/emitir_notas.html', contexto)


# ==========================================
# API: ENVIO PARA A API FOCUS NFE
# ==========================================
# ==========================================
# API: ENVIO PARA A API FOCUS NFE
# ==========================================
@csrf_exempt
def api_acionar_emissao(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda_id = dados.get('venda_id')
            tipo_nota = dados.get('tipo_nota')
            cliente_id = dados.get('cliente_id') # Recebe o cliente selecionado na tela
            
            venda = Vendas.objects.get(id=venda_id)
            TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu" 
            
            ambiente = "homologacao"
            base_url = f"https://{ambiente}.focusnfe.com.br/v2"
            
            url_api = f"{base_url}/nfe?ref={venda.id}" if tipo_nota == 'NFE' else f"{base_url}/nfce?ref={venda.id}"

            # 2. MONTANDO O CABEÇALHO BÁSICO
            payload_focus = {
                "cnpj_emitente": "36848840000156",
                "natureza_operacao": dados.get('natureza_operacao'),
                "data_emissao": timezone.now().strftime("%Y-%m-%dT%H:%M:%S-03:00"),
                "tipo_documento": "1", 
                "local_destino": "1",  
                "finalidade_emissao": "1", 
                "consumidor_final": dados.get('consumidor_final', '1'),
                "presenca_comprador": dados.get('indicador_presenca', '1'),
                "informacoes_adicionais_contribuinte": dados.get('info_complementar', ''),
                "modalidade_frete": dados.get('modalidade_frete', '9'), # <-- AGORA CAPTURA O VALOR SELECIONADO DO MODAL!
            }

            # Busca o objeto real do cliente para extrair os dados fiscais sem ler string
            cliente_obj = None
            if cliente_id:
                cliente_obj = Clientes.objects.filter(id=cliente_id).first()
            
            if not cliente_obj and venda.cliente and str(venda.cliente).strip() and str(venda.cliente).strip().lower() != 'none':
                cliente_obj = Clientes.objects.filter(nome__iexact=str(venda.cliente).strip()).first()
            
            if cliente_obj:
                doc = getattr(cliente_obj, 'cpf_cnpj', getattr(cliente_obj, 'cpf', getattr(cliente_obj, 'cnpj', '')))
                doc_limpo = ''.join(filter(str.isdigit, str(doc)))
                
                if len(doc_limpo) > 11:
                    payload_focus["cnpj_destinatario"] = doc_limpo
                    ie = getattr(cliente_obj, 'inscricao_estadual', '')
                    if ie:
                        payload_focus["inscricao_estadual_destinatario"] = ''.join(filter(str.isdigit, str(ie)))
                        payload_focus["indicador_inscricao_estadual_destinatario"] = "1"
                    else:
                        payload_focus["indicador_inscricao_estadual_destinatario"] = "9"
                else:
                    payload_focus["cpf_destinatario"] = doc_limpo
                    payload_focus["indicador_inscricao_estadual_destinatario"] = "9"

                payload_focus["nome_destinatario"] = cliente_obj.nome
                payload_focus["logradouro_destinatario"] = getattr(cliente_obj, 'endereco', 'Rua Não Informada')
                numero = getattr(cliente_obj, 'numero', getattr(cliente_obj, 'numero_endereco', 'S/N'))
                payload_focus["numero_destinatario"] = str(numero) if numero else 'S/N'
                payload_focus["bairro_destinatario"] = getattr(cliente_obj, 'bairro', 'Centro')
                payload_focus["municipio_destinatario"] = getattr(cliente_obj, 'cidade', 'São Paulo')
                payload_focus["uf_destinatario"] = getattr(cliente_obj, 'estado', getattr(cliente_obj, 'uf', 'SP'))
                
                cep = getattr(cliente_obj, 'cep', '')
                if cep:
                    payload_focus["cep_destinatario"] = ''.join(filter(str.isdigit, str(cep)))

            # Bloco de Produtos estruturado
            itens_focus = []
            if venda.cupom_texto:
                try:
                    carrinho = json.loads(venda.cupom_texto)
                    for idx, item in enumerate(carrinho):
                        qtd = float(item.get('qtd', 1))
                        vlr_unit = float(item.get('preco_desconto', item.get('preco_venda', item.get('preco', 0))))
                        
                        itens_focus.append({
                            "numero_item": str(idx + 1),
                            "codigo_produto": str(item.get('id', f'PRD{idx+1}')),
                            "descricao": item.get('nome', 'Produto Padrão'),
                            "cfop": dados.get('cfop', '5102'),
                            "unidade_comercial": "UN",
                            "quantidade_comercial": f"{qtd:.2f}",
                            "valor_unitario_comercial": f"{vlr_unit:.2f}",
                            "valor_bruto": f"{qtd * vlr_unit:.2f}",
                            "codigo_ncm": "32091010", 
                            "icms_origem": "0",
                            "icms_situacao_tributaria": "102"
                        })
                except json.JSONDecodeError:
                    pass 
            
            payload_focus["itens"] = itens_focus

            resposta = requests.post(url_api, json=payload_focus, auth=(TOKEN_FOCUS, ""))
            
            if resposta.status_code in [200, 201, 202]:
                retorno = resposta.json()
                venda.status_fiscal = 'PROCESSANDO_NUVEM'
                venda.chave_acesso = retorno.get('chave_nfe', '')
                venda.save()
                return JsonResponse({'sucesso': True, 'mensagem': f"Ordem NFe {venda.id} enviada com sucesso para a SEFAZ!"})
            else:
                try:
                    erro_json = resposta.json()
                    msg_erro = erro_json.get('mensagem', str(erro_json))
                    
                    # 🔥 NOVA LÓGICA: Capturar e mostrar os detalhes exatos do Schema XML!
                    erros_detalhados = erro_json.get('erros', [])
                    if erros_detalhados:
                        lista_detalhes = [e.get('mensagem', '') for e in erros_detalhados]
                        msg_erro = f"{msg_erro} | Motivo: " + " / ".join(lista_detalhes)
                        
                except Exception:
                    msg_erro = f"Código {resposta.status_code} - Erro na validação ou na rota da Focus NFe."
                
                return JsonResponse({'sucesso': False, 'erro': msg_erro})

        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': f"Erro interno do servidor: {str(e)}"})
            
    return JsonResponse({'sucesso': False, 'erro': 'Método não permitido.'})

# ==========================================
# APIS INTELIGENTES: CARREGAMENTO DOS DETALHES DA VENDA
# ==========================================
def api_detalhes_venda(request):
    """
    Retorna os itens faturados no carrinho.
    Lê o formato JSON moderno do PDV e mantém compatibilidade com textos antigos.
    """
    venda_id = request.GET.get('venda_id')
    try:
        venda = Vendas.objects.get(id=venda_id)
        itens_formatados = []
        
        if venda.cupom_texto:
            try:
                # 1. TENTA LER O FORMATO MODERNO (JSON do pdv.py)
                carrinho = json.loads(venda.cupom_texto)
                for idx, item in enumerate(carrinho):
                    
                    # Extrai os dados do dicionário gerado pelo PDV
                    descricao = item.get('nome', f'Produto não especificado {idx}')
                    qtd = item.get('qtd', 1)
                    
                    # Puxa o preço (priorizando desconto se houver)
                    vlr_unit = item.get('preco_desconto', item.get('preco_venda', item.get('preco', 0)))
                    
                    # Calcula o total do item
                    total = item.get('total', float(qtd) * float(vlr_unit))
                    
                    itens_formatados.append({
                        'cod_interno': str(item.get('id', f'INT-{100 + idx}')),
                        'descricao': descricao,
                        'quantidade': qtd,
                        'valor_unitario': f"{float(vlr_unit):.2f}".replace('.', ','),
                        'total': f"{float(total):.2f}".replace('.', ',')
                    })
                    
            except json.JSONDecodeError:
                # 2. FALLBACK (Se for uma venda muito antiga salva como texto)
                linhas = venda.cupom_texto.split('\n')
                for idx, linha in enumerate(linhas):
                    if 'x R$' in linha:
                        partes = linha.split('-')
                        if len(partes) >= 2:
                            descricao = partes[0].strip()
                            resto = partes[1].strip().split('x')
                            qtd = resto[0].strip()
                            valores = resto[1].split('=')
                            vlr_unit = valores[0].replace('R$', '').strip()
                            total = valores[1].replace('R$', '').strip()
                            
                            itens_formatados.append({
                                'cod_interno': f"INT-{100 + idx}",
                                'descricao': descricao,
                                'quantidade': qtd,
                                'valor_unitario': vlr_unit,
                                'total': total
                            })

        # 3. Mapeamento do Cliente
        cliente_id_encontrado = None
        if venda.cliente and str(venda.cliente).strip() and str(venda.cliente).strip().lower() != 'none':
            cliente_obj = Clientes.objects.filter(nome__iexact=str(venda.cliente).strip()).first()
            if cliente_obj:
                cliente_id_encontrado = cliente_obj.id

        return JsonResponse({
            'sucesso': True, 
            'itens': itens_formatados,
            'venda_cliente_id': cliente_id_encontrado
        })
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})
    

def api_buscar_cliente(request):
    """
    Retorna os dados com mapeamento defensivo (fallbacks) para garantir
    que colunas como cpf, cnpj, numero ou uf sejam capturadas sem erros.
    """
    cliente_id = request.GET.get('cliente_id')
    try:
        cliente = Clientes.objects.get(id=cliente_id)
        
        # 1. Fallback robusto para CPF / CNPJ
        documento_detectado = getattr(cliente, 'cpf_cnpj', '')
        if not documento_detectado:
            cpf = getattr(cliente, 'cpf', '')
            cnpj = getattr(cliente, 'cnpj', '')
            documento_detectado = cpf if cpf else cnpj

        # 2. Fallback robusto para o Número do Endereço
        numero_detectado = getattr(cliente, 'numero', '')
        if not numero_detectado:
            numero_detectado = getattr(cliente, 'numero_endereco', '')
        if not numero_detectado or str(numero_detectado).strip().lower() == 'none':
            numero_detectado = 'S/N'

        # 3. Fallback robusto para o Estado / UF
        estado_detectado = getattr(cliente, 'estado', '')
        if not estado_detectado:
            estado_detectado = getattr(cliente, 'uf', 'SP')

        # 4. Fallback robusto para o CEP (Correção do "undefined")
        cep_detectado = getattr(cliente, 'cep', '')
        if not cep_detectado or str(cep_detectado).strip().lower() == 'none':
            cep_detectado = ''

        return JsonResponse({
            'sucesso': True,
            'nome': getattr(cliente, 'nome', ''),
            'cpf_cnpj': documento_detectado,
            'inscricao_estadual': getattr(cliente, 'inscricao_estadual', ''),
            'inscricao_municipal': getattr(cliente, 'inscricao_municipal', ''),
            'endereco': getattr(cliente, 'endereco', ''),
            'numero': numero_detectado,
            'complemento': getattr(cliente, 'complemento', ''),
            'bairro': getattr(cliente, 'bairro', ''),
            'cidade': getattr(cliente, 'cidade', 'São Paulo'),
            'estado': estado_detectado,
            'cep': cep_detectado,  # <--- A LINHA QUE FALTAVA!
            'email': getattr(cliente, 'email', '')
        })
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})
def tela_consulta_nfe(request):
    """
    Abre a tela com a lista de notas já enviadas para processamento.
    Traz apenas vendas onde o campo status_fiscal não está vazio.
    """
    vendas_enviadas = Vendas.objects.exclude(status_fiscal__isnull=True).exclude(status_fiscal='').order_by('-id')
    return render(request, 'inventario/consulta_nfe.html', {'vendas_processadas': vendas_enviadas})

@csrf_exempt
def api_consultar_status_nfe(request):
    """
    Busca o status final da NFe na Focus NFe e retorna os links do PDF/XML.
    """
    venda_id = request.GET.get('venda_id')
    try:
        venda = Vendas.objects.get(id=venda_id)
        TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
        ambiente = "homologacao"
        
        url_consulta = f"https://{ambiente}.focusnfe.com.br/v2/nfe/{venda.id}"
        resposta = requests.get(url_consulta, auth=(TOKEN_FOCUS, ""))
        
        if resposta.status_code == 200:
            dados_nfe = resposta.json()
            status_sefaz = dados_nfe.get('status', 'PROCESSANDO')
            
            if status_sefaz == 'autorizado':
                venda.status_fiscal = 'AUTORIZADO'
                venda.chave_acesso = dados_nfe.get('chave_nfe', venda.chave_acesso)
                venda.save()
            elif status_sefaz == 'erro_autorizacao':
                venda.status_fiscal = 'ERRO'
                venda.save()

            return JsonResponse({
                'sucesso': True,
                'status_fiscal': status_sefaz.upper(),
                'motivo': dados_nfe.get('status_sefaz', ''),
                'chave_acesso': dados_nfe.get('chave_nfe', ''),
                'url_pdf': dados_nfe.get('url_danfe', ''),
                'url_xml': dados_nfe.get('url_xml', '')
            })
        else:
            return JsonResponse({'sucesso': False, 'erro': "Erro na Focus NFe. Aguarde um instante."})
            
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})
    