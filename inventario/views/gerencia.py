from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from django.utils import timezone
from inventario.models import Vendas, DadosNF, Clientes
from django.http import JsonResponse, HttpResponse
from inventario.models import Vendas, DadosNF, Clientes, Produtos



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
    Lista TODAS as vendas da loja para o histórico completo.
    """
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
# API: ENVIO PARA A API FOCUS NFE
# ==========================================
@csrf_exempt
@csrf_exempt
def api_acionar_emissao(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda_id = dados.get('venda_id')
            tipo_nota = dados.get('tipo_nota')
            cliente_id = dados.get('cliente_id')
            
            # 🚀 NOVO: Captura as escolhas fiscais do modal (Usa '07' como fallback padrão seguro)
            pis_req = dados.get('pis_cst', '07')
            cofins_req = dados.get('cofins_cst', '07')
            
            venda = Vendas.objects.get(id=venda_id)
            TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu" 
            
            ambiente = "homologacao"
            base_url = f"https://{ambiente}.focusnfe.com.br/v2"
            
            url_api = f"{base_url}/nfe?ref={venda.id}" if tipo_nota == 'NFE' else f"{base_url}/nfce?ref={venda.id}"

            # 2. MONTANDO O CABEÇALHO BÁSICO CORRIGIDO (FUSO HORÁRIO)
            payload_focus = {
                "cnpj_emitente": "36848840000156",
                "natureza_operacao": dados.get('natureza_operacao'),
                
                # 🔥 CORREÇÃO: Converte o UTC para o horário local de Brasília/SP antes de formatar
                "data_emissao": timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M:%S-03:00"),
                
                "tipo_documento": "1", 
                "local_destino": "1",  
                "finalidade_emissao": "1", 
                "consumidor_final": dados.get('consumidor_final', '1'),
                "presenca_comprador": dados.get('indicador_presenca', '1'),
                "informacoes_adicionais_contribuinte": dados.get('info_complementar', ''),
                "modalidade_frete": dados.get('modalidade_frete', '9'), 
            }
            
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

            # =======================================================
            # 🚀 BLOCO DE PRODUTOS ESTRUTURADO E DINÂMICO
            # =======================================================
            itens_focus = []
            if venda.cupom_texto:
                try:
                    carrinho = json.loads(venda.cupom_texto)
                    for idx, item in enumerate(carrinho):
                        qtd = float(item.get('qtd', 1))
                        vlr_unit = float(item.get('preco_desconto', item.get('preco_venda', item.get('preco', 0))))
                        
                        # 1. Tenta identificar o produto no Banco de Dados
                        cod_produto_carrinho = str(item.get('id', ''))
                        produto_db = Produtos.objects.filter(cod_interno=cod_produto_carrinho).first()
                        if not produto_db and cod_produto_carrinho.isdigit():
                            produto_db = Produtos.objects.filter(id=cod_produto_carrinho).first()
                        
                        # 2. Define os valores de segurança caso o produto não seja encontrado
                        ncm_real = "32091010"
                        csosn_real = "102"
                        origem_real = "0"
                        cest_real = ""
                        
                        # 3. Se encontrou o produto, extrai as informações fiscais exatas dele
                        if produto_db:
                            ncm_real = produto_db.ncm if produto_db.ncm else ncm_real
                            csosn_real = produto_db.cst_csosn if produto_db.cst_csosn else csosn_real
                            origem_real = getattr(produto_db, 'origem', origem_real)
                            cest_real = getattr(produto_db, 'cest', '')
                        
                        # 4. Monta o item a enviar para a SEFAZ
                        item_payload = {
                            "numero_item": str(idx + 1),
                            "codigo_produto": cod_produto_carrinho if cod_produto_carrinho else f'PRD{idx+1}',
                            "descricao": item.get('nome', 'Produto Padrão'),
                            "cfop": dados.get('cfop', '5102'),
                            "unidade_comercial": "UN",
                            "quantidade_comercial": f"{qtd:.2f}",
                            "valor_unitario_comercial": f"{vlr_unit:.2f}",
                            "valor_bruto": f"{qtd * vlr_unit:.2f}",
                            
                            # DADOS FISCAIS DINÂMICOS PUXADOS DA TABELA PRODUTOS
                            "codigo_ncm": "".join(filter(str.isdigit, str(ncm_real))), 
                            "icms_origem": str(origem_real),
                            "icms_situacao_tributaria": str(csosn_real),
                            
                            "pis_situacao_tributaria": pis_req,
                            "cofins_situacao_tributaria": cofins_req
                        }
                        
                        # 5. Adiciona o CEST apenas se o produto possuir (importante para ST)
                        cest_limpo = "".join(filter(str.isdigit, str(cest_real)))
                        if cest_limpo:
                            item_payload["codigo_cest"] = cest_limpo
                            
                        itens_focus.append(item_payload)
                except json.JSONDecodeError:
                    pass 
            
            payload_focus["itens"] = itens_focus

            # =======================================================
            # DISPARO PARA A FOCUS NFE
            # =======================================================
            resposta = requests.post(url_api, json=payload_focus, auth=(TOKEN_FOCUS, ""))
            
            if resposta.status_code in [200, 201, 202]:
                retorno = resposta.json()
                venda.status_fiscal = 'PROCESSANDO_NUVEM'
                venda.chave_acesso = retorno.get('chave_nfe', '')
                venda.modelo_fiscal = '55' if tipo_nota == 'NFE' else '65'
                venda.save()
                return JsonResponse({'sucesso': True, 'mensagem': f"Ordem NFe {venda.id} enviada com sucesso para a SEFAZ!"})
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
# APIS AUXILIARES: DETALHES E CLIENTES
# ==========================================
def api_detalhes_venda(request):
    venda_id = request.GET.get('venda_id')
    try:
        venda = Vendas.objects.get(id=venda_id)
        itens_formatados = []
        
        if venda.cupom_texto:
            try:
                carrinho = json.loads(venda.cupom_texto)
                for idx, item in enumerate(carrinho):
                    vlr_unit = item.get('preco_desconto', item.get('preco_venda', item.get('preco', 0)))
                    total = item.get('total', float(item.get('qtd', 1)) * float(vlr_unit))
                    itens_formatados.append({
                        'cod_interno': str(item.get('id', f'INT-{100 + idx}')),
                        'descricao': item.get('nome', f'Produto {idx}'),
                        'quantidade': item.get('qtd', 1),
                        'valor_unitario': f"{float(vlr_unit):.2f}".replace('.', ','),
                        'total': f"{float(total):.2f}".replace('.', ',')
                    })
            except json.JSONDecodeError:
                pass

        cliente_id_encontrado = None
        if venda.cliente and str(venda.cliente).strip().lower() != 'none':
            cliente_obj = Clientes.objects.filter(nome__iexact=str(venda.cliente).strip()).first()
            if cliente_obj:
                cliente_id_encontrado = cliente_obj.id

        return JsonResponse({'sucesso': True, 'itens': itens_formatados, 'venda_cliente_id': cliente_id_encontrado})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})
    

def api_buscar_cliente(request):
    cliente_id = request.GET.get('cliente_id')
    try:
        cliente = Clientes.objects.get(id=cliente_id)
        doc = getattr(cliente, 'cpf_cnpj', getattr(cliente, 'cpf', getattr(cliente, 'cnpj', '')))
        num = getattr(cliente, 'numero', 'S/N')
        uf = getattr(cliente, 'estado', getattr(cliente, 'uf', 'SP'))
        
        return JsonResponse({
            'sucesso': True,
            'nome': cliente.nome,
            'cpf_cnpj': doc,
            'inscricao_estadual': getattr(cliente, 'inscricao_estadual', ''),
            'inscricao_municipal': getattr(cliente, 'inscricao_municipal', ''),
            'endereco': getattr(cliente, 'endereco', ''),
            'numero': num if num else 'S/N',
            'complemento': getattr(cliente, 'complemento', ''),
            'bairro': getattr(cliente, 'bairro', ''),
            'cidade': getattr(cliente, 'cidade', 'São Paulo'),
            'estado': uf,
            'cep': getattr(cliente, 'cep', ''),
            'email': getattr(cliente, 'email', '')
        })
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})


# ==========================================
# PAINEL DE GESTÃO: CONSULTA E AUDITORIA
# ==========================================
def tela_consulta_nfe(request):
    """
    Abre a tela de Consulta trazendo EXCLUSIVAMENTE as vendas emitidas como NF-e (Modelo 55).
    Injeta a lista de todos os clientes para permitir correções cadastrais no reenvio.
    """
    if 'usuario_logado' not in request.session:
        return redirect('login')

    vendas_nfe = Vendas.objects.filter(modelo_fiscal='55').order_by('-id')
    todos_clientes = Clientes.objects.all().order_by('nome') # <-- ADICIONADO PARA O MODAL
    
    contexto = {
        'vendas_processadas': vendas_nfe,
        'todos_clientes': todos_clientes
    }
    return render(request, 'inventario/consulta_nfe.html', contexto)


@csrf_exempt
def api_consultar_status_nfe(request):
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
            elif status_sefaz == 'cancelado':
                venda.status_fiscal = 'CANCELADO'
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
            return JsonResponse({'sucesso': False, 'erro': "Erro ao ler dados da Focus NFe."})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})


# ==========================================
# 🚀 NOVAS FUNÇÕES ADICIONADAS: CANCELAMENTO E EMAIL
# ==========================================
@csrf_exempt
def api_cancelar_nota(request):
    """
    Aciona o cancelamento da Nota Fiscal na SEFAZ via Focus NFe (Método DELETE).
    """
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Método não permitido.'})
    try:
        dados = json.loads(request.body)
        venda_id = dados.get('venda_id')
        justificativa = dados.get('justificativa', '').strip()
        
        if len(justificativa) < 15:
            return JsonResponse({'sucesso': False, 'erro': 'A justificativa exige ao menos 15 caracteres.'})
            
        venda = Vendas.objects.get(id=venda_id)
        TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
        ambiente = "homologacao"
        
        # O cancelamento na Focus NFe V2 é feito via requisição DELETE
        url_cancelar = f"https://{ambiente}.focusnfe.com.br/v2/nfe/{venda.id}"
        resposta = requests.delete(url_cancelar, json={"justificativa": justificativa}, auth=(TOKEN_FOCUS, ""))
        
        if resposta.status_code in [200, 201, 202]:
            retorno = resposta.json()
            if retorno.get('status') == 'cancelado':
                venda.status_fiscal = 'CANCELADO'
                venda.save()
                return JsonResponse({'sucesso': True, 'mensagem': 'Nota Fiscal CANCELADA com sucesso na SEFAZ!'})
            else:
                return JsonResponse({'sucesso': False, 'erro': retorno.get('mensagem', 'Cancelamento rejeitado.')})
        else:
            erro_msg = resposta.json().get('mensagem', 'Erro de comunicação HTTP.')
            return JsonResponse({'sucesso': False, 'erro': erro_msg})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})


@csrf_exempt
@csrf_exempt
def api_enviar_email_nota(request):
    """
    Dispara o e-mail oficial com os anexos através do servidor da Focus NFe.
    Inclui texto personalizado da JB Tintas e tratamento de erros detalhado.
    """
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Método não permitido.'})
    try:
        dados = json.loads(request.body)
        venda_id = dados.get('venda_id')
        email_destino = dados.get('email', '').strip()
        
        venda = Vendas.objects.get(id=venda_id)
        TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
        ambiente = "homologacao"
        
        # 1. Tenta identificar o nome do cliente para personalizar o e-mail
        nome_cliente = "Cliente"
        if venda.cliente and str(venda.cliente).strip() and str(venda.cliente).strip().lower() != 'none':
            nome_cliente = str(venda.cliente).strip()

        # 2. Monta o texto personalizado que será injetado no corpo do e-mail
        texto_personalizado = (
            f"Olá, {nome_cliente}!\n\n"
            f"Agradecemos por comprar na JB Tintas.\n\n"
            f"Segue em anexo o arquivo PDF (DANFE) e o XML da sua Nota Fiscal Eletrônica referente à Venda #{venda.id}.\n\n"
            f"Chave de Acesso: {venda.chave_acesso}\n\n"
            f"Qualquer dúvida, a nossa equipa está à disposição!\n\n"
            f"Um abraço,\nEquipe JB Tintas"
        )
        
        url_email = f"https://{ambiente}.focusnfe.com.br/v2/nfe/{venda.id}/email"
        
        # 3. Adiciona a chave 'mensagem' ao payload da Focus NFe
        payload = {
            "emails": [email_destino],
            "mensagem": texto_personalizado
        }
        
        resposta = requests.post(url_email, json=payload, auth=(TOKEN_FOCUS, ""))
        
        # 4. Avalia a resposta. Se não for sucesso, captura o texto exato do erro!
        if resposta.status_code in [200, 201, 202]:
            return JsonResponse({'sucesso': True, 'mensagem': f'XML e DANFE enviados com sucesso para {email_destino}!'})
        else:
            try:
                erro_json = resposta.json()
                msg_erro = erro_json.get('mensagem', resposta.text)
            except:
                msg_erro = f"Erro HTTP {resposta.status_code}: Falha de comunicação."
                
            return JsonResponse({'sucesso': False, 'erro': f"Recusado pela Focus NFe: {msg_erro}"})
            
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': f"Erro interno: {str(e)}"})
    
    # ==========================================
# IMPRESSÃO E DOWNLOAD (PROXY SEGURO FOCUS NFE)
# ==========================================
def imprimir_danfe_nfe(request, venda_id):
    """ Busca o PDF da nota na Focus NFe usando o Token e entrega ao navegador """
    try:
        venda = Vendas.objects.get(id=venda_id)
        TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
        ambiente = "homologacao"
        
        # 1. Consulta onde o PDF está guardado
        url_consulta = f"https://{ambiente}.focusnfe.com.br/v2/nfe/{venda.id}"
        resp_consulta = requests.get(url_consulta, auth=(TOKEN_FOCUS, ""))
        
        if resp_consulta.status_code == 200:
            dados = resp_consulta.json()
            caminho_danfe = dados.get('caminho_danfe')
            
            if caminho_danfe:
                # 2. Baixa o PDF usando as nossas credenciais secretas
                url_pdf = caminho_danfe if caminho_danfe.startswith('http') else f"https://{ambiente}.focusnfe.com.br{caminho_danfe}"
                resp_pdf = requests.get(url_pdf, auth=(TOKEN_FOCUS, ""))
                
                if resp_pdf.status_code == 200:
                    response = HttpResponse(resp_pdf.content, content_type='application/pdf')
                    response['Content-Disposition'] = f'inline; filename="DANFE_JB_TINTAS_Venda_{venda.id}.pdf"'
                    return response
                    
        return HttpResponse("<h1>O DANFE ainda não está disponível.</h1><p>Verifique se a nota já foi autorizada pela SEFAZ.</p>", status=404)
    except Exception as e:
        return HttpResponse(f"Erro interno: {str(e)}", status=500)


def baixar_xml_nfe(request, venda_id):
    """ Busca o XML da nota na Focus NFe usando o Token e faz o download """
    try:
        venda = Vendas.objects.get(id=venda_id)
        TOKEN_FOCUS = "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu"
        ambiente = "homologacao"
        
        url_consulta = f"https://{ambiente}.focusnfe.com.br/v2/nfe/{venda.id}"
        resp_consulta = requests.get(url_consulta, auth=(TOKEN_FOCUS, ""))
        
        if resp_consulta.status_code == 200:
            dados = resp_consulta.json()
            caminho_xml = dados.get('caminho_xml_nota_fiscal')
            
            if caminho_xml:
                url_xml = caminho_xml if caminho_xml.startswith('http') else f"https://{ambiente}.focusnfe.com.br{caminho_xml}"
                resp_xml = requests.get(url_xml, auth=(TOKEN_FOCUS, ""))
                
                if resp_xml.status_code == 200:
                    response = HttpResponse(resp_xml.content, content_type='application/xml')
                    response['Content-Disposition'] = f'attachment; filename="XML_NFe_{venda.chave_acesso}.xml"'
                    return response
                    
        return HttpResponse("<h1>O XML ainda não está disponível na SEFAZ.</h1>", status=404)
    except Exception as e:
        return HttpResponse(f"Erro interno: {str(e)}", status=500)
    
    