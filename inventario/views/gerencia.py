from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from django.utils import timezone
from inventario.models import Vendas, DadosNF, Clientes, Produtos, ConfiguracaoEmissor
import time

# ==========================================
# PAINEL DE GERÊNCIA PRINCIPAL
# ==========================================
def tela_painel_gerencia(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    return render(request, 'inventario/painel_gerencia.html')

# ==========================================
# TELA: FILA FISCAL
# ==========================================
def emitir_notas(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    vendas_pendentes = Vendas.objects.all().order_by('-id')
    todos_clientes = Clientes.objects.all().order_by('nome')
    contexto = {
        'vendas_pendentes': vendas_pendentes,
        'todos_clientes': todos_clientes
    }
    return render(request, 'inventario/emitir_notas.html', contexto)

# ==========================================
# TELA: CONSULTA NF-e (Modelo 55 - Nota Grande)
# ==========================================
def tela_consulta_nfe(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    vendas_processadas = Vendas.objects.filter(modelo_fiscal='55').exclude(status_fiscal='SEM_NOTA').order_by('-id')
    todos_clientes = Clientes.objects.all().order_by('nome')
    contexto = {
        'vendas_processadas': vendas_processadas,
        'todos_clientes': todos_clientes
    }
    return render(request, 'inventario/consulta_nfe.html', contexto)

# ==========================================
# 🚀 NOVA TELA: CONSULTA NFC-e (Modelo 65 - Cupom Fiscal)
# ==========================================
def tela_consulta_nfce(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    # Traz apenas as vendas de Cupom Fiscal (65)
    vendas_processadas = Vendas.objects.filter(modelo_fiscal='65').exclude(status_fiscal='SEM_NOTA').order_by('-id')
    todos_clientes = Clientes.objects.all().order_by('nome')
    contexto = {
        'vendas_processadas': vendas_processadas,
        'todos_clientes': todos_clientes
    }
    return render(request, 'inventario/consulta_nfce.html', contexto)

# ==========================================
# API: DETALHES DA VENDA E CLIENTE
# ==========================================
def api_detalhes_venda(request):
    venda_id = request.GET.get('venda_id')
    try:
        venda = Vendas.objects.get(id=venda_id)
        carrinho = json.loads(venda.cupom_texto) if venda.cupom_texto else []
        itens = []
        for item in carrinho:
            itens.append({
                'cod_interno': item.get('id', ''),
                'descricao': item.get('nome', ''),
                'quantidade': item.get('qtd', 1),
                'valor_unitario': item.get('preco_desconto', item.get('preco_venda', 0)),
                'total': float(item.get('qtd', 1)) * float(item.get('preco_desconto', item.get('preco_venda', 0)))
            })
        
        cliente_id = None
        if venda.cliente and str(venda.cliente).strip() and str(venda.cliente).strip().lower() != 'none':
            cliente_obj = Clientes.objects.filter(nome__iexact=str(venda.cliente).strip()).first()
            if cliente_obj:
                cliente_id = cliente_obj.id
                
        return JsonResponse({'sucesso': True, 'itens': itens, 'venda_cliente_id': cliente_id})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})

def api_buscar_cliente(request):
    cliente_id = request.GET.get('cliente_id')
    try:
        cli = Clientes.objects.get(id=cliente_id)
        doc = getattr(cli, 'cpf_cnpj', getattr(cli, 'cpf', getattr(cli, 'cnpj', '')))
        return JsonResponse({
            'sucesso': True,
            'nome': cli.nome,
            'cpf_cnpj': doc,
            'cep': getattr(cli, 'cep', ''),
            'endereco': getattr(cli, 'endereco', ''),
            'numero': getattr(cli, 'numero', ''),
            'complemento': getattr(cli, 'complemento', ''),
            'bairro': getattr(cli, 'bairro', ''),
            'cidade': getattr(cli, 'cidade', ''),
            'estado': getattr(cli, 'estado', getattr(cli, 'uf', '')),
            'email': getattr(cli, 'email', ''),
            'inscricao_estadual': getattr(cli, 'inscricao_estadual', ''),
            'inscricao_municipal': getattr(cli, 'inscricao_municipal', '')
        })
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})

# ==========================================
# API: CONSULTA, CANCELAMENTO E EMAIL (FOCUS NFE)
# ==========================================
def api_consultar_status_nfe(request):
    venda_id = request.GET.get('venda_id')
    try:
        venda = Vendas.objects.get(id=venda_id)
        TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
        ambiente = "homologacao"
        
        # 🔥 PROTEÇÃO: Verifica se é Nota (55) ou Cupom (65) para usar a URL correta da Focus
        endpoint = 'nfce' if venda.modelo_fiscal == '65' else 'nfe'
        url_status = f"https://{ambiente}.focusnfe.com.br/v2/{endpoint}/{venda.id}"
        
        resposta = requests.get(url_status, auth=(TOKEN_FOCUS, ""))
        
        if resposta.status_code == 200:
            dados = resposta.json()
            status = dados.get('status', '')
            
            if status == 'autorizado':
                venda.status_fiscal = 'AUTORIZADO'
                venda.chave_acesso = dados.get('chave_nfe', venda.chave_acesso)
            elif status == 'cancelado':
                venda.status_fiscal = 'CANCELADO'
            elif status == 'erro_autorizacao':
                venda.status_fiscal = 'ERRO'
            else:
                venda.status_fiscal = status.upper()
            venda.save()

            motivo = dados.get('mensagem_sefaz', '') if status == 'erro_autorizacao' else ''
            return JsonResponse({
                'sucesso': True, 
                'status_fiscal': venda.status_fiscal, 
                'chave_acesso': venda.chave_acesso,
                'motivo': motivo
            })
        else:
            return JsonResponse({'sucesso': False, 'erro': f'Erro API: {resposta.status_code}'})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})

@csrf_exempt
def api_cancelar_nota(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda_id = dados.get('venda_id')
            justificativa = dados.get('justificativa', 'Cancelamento solicitado pelo cliente.')
            
            venda = Vendas.objects.get(id=venda_id)
            TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
            ambiente = "homologacao"
            
            # 🔥 PROTEÇÃO DE ROTA
            endpoint = 'nfce' if venda.modelo_fiscal == '65' else 'nfe'
            url_cancelamento = f"https://{ambiente}.focusnfe.com.br/v2/{endpoint}/{venda.id}"
            
            payload = {"justificativa": justificativa}
            resposta = requests.delete(url_cancelamento, json=payload, auth=(TOKEN_FOCUS, ""))
            
            if resposta.status_code in [200, 201]:
                venda.status_fiscal = 'CANCELADO'
                venda.save()
                return JsonResponse({'sucesso': True, 'mensagem': 'Documento cancelado com sucesso na SEFAZ!'})
            else:
                erro = resposta.json()
                return JsonResponse({'sucesso': False, 'erro': erro.get('mensagem', 'Erro desconhecido')})
        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': str(e)})
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'})

@csrf_exempt
def api_enviar_email_nota(request):
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Método não permitido.'})
    try:
        dados = json.loads(request.body)
        venda_id = dados.get('venda_id')
        email_destino = dados.get('email', '').strip()
        
        venda = Vendas.objects.get(id=venda_id)
        TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
        ambiente = "homologacao"
        
        nome_cliente = "Cliente"
        if venda.cliente and str(venda.cliente).strip() and str(venda.cliente).strip().lower() != 'none':
            nome_cliente = str(venda.cliente).strip()

        texto_personalizado = (
            f"Olá, {nome_cliente}!\n\n"
            f"Agradecemos por comprar na JB Tintas.\n\n"
            f"Segue em anexo o arquivo PDF e o XML do seu documento fiscal referente à Venda #{venda.id}.\n\n"
            f"Chave de Acesso: {venda.chave_acesso}\n\n"
            f"Qualquer dúvida, a nossa equipa está à disposição!\n\n"
            f"Um abraço,\nEquipe JB Tintas"
        )
        
        # 🔥 PROTEÇÃO DE ROTA
        endpoint = 'nfce' if venda.modelo_fiscal == '65' else 'nfe'
        url_email = f"https://{ambiente}.focusnfe.com.br/v2/{endpoint}/{venda.id}/email"
        
        payload = {
            "emails": [email_destino],
            "mensagem": texto_personalizado
        }
        
        resposta = requests.post(url_email, json=payload, auth=(TOKEN_FOCUS, ""))
        
        if resposta.status_code in [200, 201, 202]:
            return JsonResponse({'sucesso': True, 'mensagem': f'Enviado com sucesso para {email_destino}!'})
        else:
            try:
                erro_json = resposta.json()
                msg_erro = erro_json.get('mensagem', resposta.text)
            except Exception:
                msg_erro = f"Erro HTTP {resposta.status_code}: Falha de comunicação."
            return JsonResponse({'sucesso': False, 'erro': f"Recusado pela Focus NFe: {msg_erro}"})
            
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': f"Erro interno: {str(e)}"})

# ==========================================
# DOWNLOADS: PDF E XML (PROXY FOCUS NFE)
# ==========================================
def imprimir_danfe_nfe(request, venda_id):
    try:
        venda = Vendas.objects.get(id=venda_id)
        TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
        ambiente = "homologacao"
        
        # 🔥 PROTEÇÃO DE ROTA
        endpoint = 'nfce' if venda.modelo_fiscal == '65' else 'nfe'
        url_consulta = f"https://{ambiente}.focusnfe.com.br/v2/{endpoint}/{venda.id}"
        
        resp_consulta = requests.get(url_consulta, auth=(TOKEN_FOCUS, ""))
        
        if resp_consulta.status_code == 200:
            dados = resp_consulta.json()
            caminho_pdf = dados.get('caminho_danfe')
            
            if caminho_pdf:
                url_pdf = caminho_pdf if caminho_pdf.startswith('http') else f"https://{ambiente}.focusnfe.com.br{caminho_pdf}"
                resp_pdf = requests.get(url_pdf, auth=(TOKEN_FOCUS, ""))
                
                if resp_pdf.status_code == 200:
                    response = HttpResponse(resp_pdf.content, content_type='application/pdf')
                    nome_arquivo = f"NFCe_Cupom_Venda_{venda.id}.pdf" if venda.modelo_fiscal == '65' else f"DANFE_Venda_{venda.id}.pdf"
                    response['Content-Disposition'] = f'inline; filename="{nome_arquivo}"'
                    return response
        
        return HttpResponse(f"<p>Documento ainda não disponível na SEFAZ. Aguarde alguns segundos e atualize o status.</p>", status=404)
    except Exception as e:
        return HttpResponse(f"Erro interno: {str(e)}", status=500)

def baixar_xml_nfe(request, venda_id):
    try:
        venda = Vendas.objects.get(id=venda_id)
        TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
        ambiente = "homologacao"
        
        # 🔥 PROTEÇÃO DE ROTA
        endpoint = 'nfce' if venda.modelo_fiscal == '65' else 'nfe'
        url_consulta = f"https://{ambiente}.focusnfe.com.br/v2/{endpoint}/{venda.id}"
        
        resp_consulta = requests.get(url_consulta, auth=(TOKEN_FOCUS, ""))
        
        if resp_consulta.status_code == 200:
            dados = resp_consulta.json()
            caminho_xml = dados.get('caminho_xml_nota_fiscal')
            
            if caminho_xml:
                url_xml = caminho_xml if caminho_xml.startswith('http') else f"https://{ambiente}.focusnfe.com.br{caminho_xml}"
                resp_xml = requests.get(url_xml, auth=(TOKEN_FOCUS, ""))
                
                if resp_xml.status_code == 200:
                    response = HttpResponse(resp_xml.content, content_type='application/xml')
                    response['Content-Disposition'] = f'attachment; filename="XML_Venda_{venda.id}.xml"'
                    return response
        
        return HttpResponse(f"<p>XML não disponível. A nota pode não estar autorizada.</p>", status=404)
    except Exception as e:
        return HttpResponse(f"Erro interno: {str(e)}", status=500)

# ==========================================
# 🚀 MOTOR DE EMISSÃO FISCAL
# ==========================================
@csrf_exempt
def api_acionar_emissao(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda_id = dados.get('venda_id')
            tipo_nota = dados.get('tipo_nota')
            cliente_id = dados.get('cliente_id')
            
            # Captura os impostos e a nova FORMA DE PAGAMENTO do frontend
            pis_req = dados.get('pis_cst', '07')
            cofins_req = dados.get('cofins_cst', '07')
            forma_pagamento_req = dados.get('forma_pagamento', '01') # Padrão: 01 (Dinheiro)
            
            venda = Vendas.objects.get(id=venda_id)
            
            # SEPARAÇÃO INTELIGENTE DE AMBIENTES (TEMPORARIAMENTE TUDO EM HOMOLOGAÇÃO PARA TESTES)
            if tipo_nota == 'NFE':
                ambiente = "homologacao" 
                TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu" 
            else:
                ambiente = "homologacao"
                TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
            
            base_url = f"https://{ambiente}.focusnfe.com.br/v2"
            url_api = f"{base_url}/nfe?ref={venda.id}" if tipo_nota == 'NFE' else f"{base_url}/nfce?ref={venda.id}"
            
            # 1. Puxa o CNPJ dinamicamente do banco de dados (Tabela ConfiguracaoEmissor)
            emissor = ConfiguracaoEmissor.objects.first()
            cnpj_emitente = "".join(filter(str.isdigit, str(emissor.cnpj))) if emissor and emissor.cnpj else "36848840000156"

            payload_focus = {
                "cnpj_emitente": cnpj_emitente,
                "natureza_operacao": dados.get('natureza_operacao'),
                "data_emissao": timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M:%S-03:00"),
                "tipo_documento": "1", 
                "local_destino": "1",  
                "finalidade_emissao": "1", 
                "consumidor_final": dados.get('consumidor_final', '1'),
                "presenca_comprador": dados.get('indicador_presenca', '1'),
                "informacoes_adicionais_contribuinte": dados.get('info_complementar', ''),
                "modalidade_frete": dados.get('modalidade_frete', '9'), 
            }
            
            # Lógica do Cliente
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

            # Lógica dos Itens do Carrinho
            itens_focus = []
            if venda.cupom_texto:
                try:
                    carrinho = json.loads(venda.cupom_texto)
                    for idx, item in enumerate(carrinho):
                        qtd = float(item.get('qtd', 1))
                        vlr_unit = float(item.get('preco_desconto', item.get('preco_venda', item.get('preco', 0))))
                        
                        cod_produto_carrinho = str(item.get('id', ''))
                        produto_db = Produtos.objects.filter(cod_interno=cod_produto_carrinho).first()
                        if not produto_db and cod_produto_carrinho.isdigit():
                            produto_db = Produtos.objects.filter(id=cod_produto_carrinho).first()
                        
                        ncm_real = "32091010"
                        csosn_real = "102"
                        origem_real = "0"
                        cest_real = ""
                        unidade_real = "UN"
                        
                        if produto_db:
                            ncm_real = produto_db.ncm if getattr(produto_db, 'ncm', '') else ncm_real
                            csosn_real = produto_db.cst_csosn if getattr(produto_db, 'cst_csosn', '') else csosn_real
                            origem_real = getattr(produto_db, 'origem', origem_real)
                            cest_real = getattr(produto_db, 'cest', '')
                            unidade_real = getattr(produto_db, 'unidade', 'UN')
                            if not unidade_real: unidade_real = "UN"
                        
                        item_payload = {
                            "numero_item": str(idx + 1),
                            "codigo_produto": cod_produto_carrinho if cod_produto_carrinho else f'PRD{idx+1}',
                            "descricao": item.get('nome', 'Produto Padrão'),
                            "cfop": dados.get('cfop', '5102'),
                            "unidade_comercial": unidade_real,
                            "quantidade_comercial": f"{qtd:.2f}",
                            "valor_unitario_comercial": f"{vlr_unit:.2f}",
                            "valor_bruto": f"{qtd * vlr_unit:.2f}",
                            "codigo_ncm": "".join(filter(str.isdigit, str(ncm_real)))[:8], 
                            "icms_origem": str(origem_real),
                            "icms_situacao_tributaria": str(csosn_real),
                            "pis_situacao_tributaria": pis_req,
                            "cofins_situacao_tributaria": cofins_req
                        }
                        
                        cod_barras = getattr(produto_db, 'cod_barras', '') if produto_db else ''
                        cod_barras_limpo = "".join(filter(str.isdigit, str(cod_barras)))
                        
                        if cod_barras_limpo and len(cod_barras_limpo) in [8, 12, 13, 14]:
                            item_payload["codigo_barras_comercial"] = cod_barras_limpo
                            item_payload["codigo_barras_tributavel"] = cod_barras_limpo
                        else:
                            item_payload["codigo_barras_comercial"] = "SEM GTIN"
                            item_payload["codigo_barras_tributavel"] = "SEM GTIN"
                        
                        cest_limpo = "".join(filter(str.isdigit, str(cest_real)))
                        if cest_limpo:
                            item_payload["codigo_cest"] = cest_limpo
                            
                        itens_focus.append(item_payload)
                except json.JSONDecodeError:
                    pass 
            
            payload_focus["itens"] = itens_focus

            # 4. Adiciona o Bloco de Pagamento Dinâmico
            payload_focus["formas_pagamento"] = [
                {
                    "forma_pagamento": forma_pagamento_req,
                    "valor_pagamento": f"{venda.valor_total:.2f}"
                }
            ]

            resposta = requests.post(url_api, json=payload_focus, auth=(TOKEN_FOCUS, ""))
            
            if resposta.status_code in [200, 201, 202]:
                retorno = resposta.json()
                venda.status_fiscal = 'PROCESSANDO_NUVEM'
                venda.chave_acesso = retorno.get('chave_nfe', '')
                venda.modelo_fiscal = '55' if tipo_nota == 'NFE' else '65'
                venda.save()
                return JsonResponse({'sucesso': True, 'mensagem': f"Documento fiscal {venda.id} enviado com sucesso para a SEFAZ!"})
            else:
                try:
                    erro_json = resposta.json()
                    msg_erro = erro_json.get('mensagem', str(erro_json))
                    erros_detalhados = erro_json.get('erros', [])
                    if erros_detalhados:
                        lista_detalhes = [e.get('mensagem', '') for e in erros_detalhados]
                        msg_erro = f"{msg_erro} | Motivo: " + " / ".join(lista_detalhes)
                except Exception:
                    msg_erro = f"Código {resposta.status_code} - Erro na validação."
                
                return JsonResponse({'sucesso': False, 'erro': msg_erro})

        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': f"Erro interno do servidor: {str(e)}"})
            
    return JsonResponse({'sucesso': False, 'erro': 'Método não permitido.'})


# ==========================================
# FASE 3: ROTA DE EMISSÃO DE DEVOLUÇÃO
# ==========================================
@csrf_exempt
def api_emitir_devolucao(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda_id = dados.get('venda_id')
            chave_original = dados.get('chave_original')
            cfop_devolucao = dados.get('cfop_devolucao')
            justificativa = dados.get('justificativa')
            itens_devolvidos = dados.get('itens_devolvidos', [])

            venda = Vendas.objects.get(id=venda_id)
            
            # 1. Configuração do Ambiente e Token (HOMOLOGAÇÃO PARA TESTES)
            # NOTA DE ENGENHARIA: Devolução é SEMPRE uma NF-e (Modelo 55), nunca um Cupom (NFC-e).
            # Portanto, a variável 'tipo_nota' não é necessária aqui e a URL base é sempre '/nfe'
            ambiente = "homologacao"
            TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
            
            base_url = f"https://{ambiente}.focusnfe.com.br/v2"
            
            # Criamos uma referência única para a devolução (para não conflitar com a venda original)
            ref_devolucao = f"DEV_{venda.id}_{int(time.time())}"
            url_api = f"{base_url}/nfe?ref={ref_devolucao}"

            # Recupera o CNPJ da Loja
            emissor = ConfiguracaoEmissor.objects.first()
            cnpj_emitente = "".join(filter(str.isdigit, str(emissor.cnpj))) if emissor and emissor.cnpj else "36848840000156"

            # 2. Construção do Cabeçalho Invertido (Nota de Entrada)
            payload_focus = {
                "cnpj_emitente": cnpj_emitente,
                "natureza_operacao": "Devolucao de venda",
                "data_emissao": timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M:%S-03:00"),
                "tipo_documento": "0",       # MÁGICA 1: 0 = Nota de Entrada (Volta pro estoque)
                "finalidade_emissao": "4",   # MÁGICA 2: 4 = Devolução de Mercadoria
                "local_destino": "1",
                "consumidor_final": "1",
                "presenca_comprador": "1",
                "notas_referenciadas": [     # MÁGICA 3: Anexa a chave da nota original para a SEFAZ
                    {"chave_nfe": chave_original}
                ],
                "informacoes_adicionais_contribuinte": f"Devolucao referente a nota {chave_original}. Motivo: {justificativa}",
                "modalidade_frete": "9",
            }

            # 3. Puxa os dados do Cliente (que agora atua como remetente da devolução)
            cliente_obj = venda.cliente_relacionado if hasattr(venda, 'cliente_relacionado') else None
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

            # 4. Processa os itens devolvidos e restaura o estoque
            itens_focus = []
            
            for idx, item in enumerate(itens_devolvidos):
                cod_interno = item.get('cod_interno')
                qtd_devolvida = float(item.get('quantidade'))

                # Localiza o produto no banco de dados da loja
                produto_db = Produtos.objects.filter(cod_interno=cod_interno).first()
                if not produto_db and str(cod_interno).isdigit():
                    produto_db = Produtos.objects.filter(id=cod_interno).first()
                
                if produto_db:
                    vlr_unit = float(produto_db.preco_venda)
                    total_item = qtd_devolvida * vlr_unit

                    ncm_real = getattr(produto_db, 'ncm', '32091010') or '32091010'
                    csosn_real = getattr(produto_db, 'cst_csosn', '102') or '102'
                    unidade_real = getattr(produto_db, 'unidade', 'UN') or 'UN'

                    item_payload = {
                        "numero_item": str(idx + 1),
                        "codigo_produto": str(cod_interno),
                        "descricao": produto_db.nome,
                        "cfop": cfop_devolucao,
                        "unidade_comercial": unidade_real,
                        "quantidade_comercial": f"{qtd_devolvida:.2f}",
                        "valor_unitario_comercial": f"{vlr_unit:.2f}",
                        "valor_bruto": f"{total_item:.2f}",
                        "codigo_ncm": "".join(filter(str.isdigit, str(ncm_real)))[:8],
                        "icms_origem": "0",
                        "icms_situacao_tributaria": str(csosn_real),
                        "pis_situacao_tributaria": "07",
                        "cofins_situacao_tributaria": "07"
                    }
                    
                    cod_barras = "".join(filter(str.isdigit, str(getattr(produto_db, 'cod_barras', ''))))
                    if cod_barras and len(cod_barras) in [8, 12, 13, 14]:
                        item_payload["codigo_barras_comercial"] = cod_barras
                        item_payload["codigo_barras_tributavel"] = cod_barras
                    else:
                        item_payload["codigo_barras_comercial"] = "SEM GTIN"
                        item_payload["codigo_barras_tributavel"] = "SEM GTIN"

                    itens_focus.append(item_payload)

                    # ♻️ MÁGICA 4: Restaura a lata de tinta no estoque da loja
                    produto_db.estoque_atual += int(qtd_devolvida)
                    produto_db.save()

            payload_focus["itens"] = itens_focus

            # 5. Informação de Pagamento
            # A SEFAZ exige a tag de pagamento. Como é devolução, usamos a forma "90" (Sem Pagamento)
            payload_focus["formas_pagamento"] = [
                {
                    "forma_pagamento": "90",
                    "valor_pagamento": "0.00"
                }
            ]

            # 6. Disparo do Foguete
            resposta = requests.post(url_api, json=payload_focus, auth=(TOKEN_FOCUS, ""))
            
            if resposta.status_code in [200, 201, 202]:
                venda.status_fiscal = 'DEVOLUCAO_EM_PROCESSAMENTO'
                venda.save()
                return JsonResponse({'sucesso': True, 'mensagem': "Devolução enviada para a SEFAZ e estoque atualizado!"})
            else:
                try:
                    erro_json = resposta.json()
                    msg_erro = erro_json.get('mensagem', str(erro_json))
                    if erro_json.get('erros'):
                        msg_erro += " | " + " / ".join([e.get('mensagem', '') for e in erro_json.get('erros')])
                except Exception:
                    msg_erro = f"Código {resposta.status_code} - Rejeição desconhecida."
                
                return JsonResponse({'sucesso': False, 'erro': msg_erro})

        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': f"Erro interno: {str(e)}"})
            
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido'})
