import os
import json
import re
import requests
from django.utils import timezone
from inventario.models import Vendas, Produtos, ConfiguracaoEmissor

class FiscalService:
    """
    Camada de Serviço responsável por toda a comunicação externa com a API da Focus NFe.
    Isola a regra de negócio fiscal das Views (Skinny Views).
    """

    @staticmethod
    def _get_auth(modelo_fiscal='55'):
        # LÓGICA DE AMBIENTE HÍBRIDO E TOKENS INDEPENDENTES
        if str(modelo_fiscal) == '65':
            # NFC-e (Cupom) -> Ambiente de testes com Token de Homologação
            token = os.getenv("FOCUS_TOKEN_NFCE", "DRpdO4K7pZrNjcu3MTuSJ4863f5X2Vnu")
            ambiente = os.getenv("AMBIENTE_FOCUS_NFCE", "homologacao")
        else:
            # NF-e (Nota Grande e Devolução) -> Ambiente Real com Token de Produção
            token = os.getenv("FOCUS_TOKEN_NFE", "zFsuc7SHa8NeP98qaNpAJvlZqDHaLB3B")
            ambiente = os.getenv("AMBIENTE_FOCUS_NFE", "api")
            
        base_url = f"https://{ambiente}.focusnfe.com.br/v2"
        return (token, ""), base_url

    @staticmethod
    def _get_emissor_dados():
        emissor = ConfiguracaoEmissor.objects.first()
        cnpj = "".join(filter(str.isdigit, str(emissor.cnpj))) if emissor and emissor.cnpj else "36848840000156"
        return emissor, cnpj

    @classmethod
    def consultar_status(cls, venda):
        auth, base_url = cls._get_auth(venda.modelo_fiscal)
        endpoint = 'nfce' if venda.modelo_fiscal == '65' else 'nfe'
        
        resposta = requests.get(f"{base_url}/{endpoint}/{venda.id}", auth=auth)
        
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
            venda.save(update_fields=['status_fiscal', 'chave_acesso'])

            motivo = dados.get('mensagem_sefaz', '') if status == 'erro_autorizacao' else ''
            return {'sucesso': True, 'status_fiscal': venda.status_fiscal, 'chave_acesso': venda.chave_acesso, 'motivo': motivo, 'status_interno': venda.status}
        return {'sucesso': False, 'erro': f'Erro API: {resposta.status_code}'}

    @classmethod
    def cancelar_nota(cls, venda, justificativa):
        auth, base_url = cls._get_auth(venda.modelo_fiscal)
        endpoint = 'nfce' if venda.modelo_fiscal == '65' else 'nfe'
        url = f"{base_url}/{endpoint}/{venda.id}"

        # AUTO-CURA PARA DEVOLUÇÕES REJEITADAS
        if venda.status == 'DEVOLUCAO_ENTRADA' and venda.status_fiscal in ['ERRO', 'REJEITADO', 'ERRO_AUTORIZACAO']:
            requests.delete(url, auth=auth) # Limpa o rascunho na nuvem
            
            if venda.cupom_texto:
                try:
                    for item in json.loads(venda.cupom_texto):
                        prod = Produtos.objects.filter(cod_interno=item.get('cod_interno')).first()
                        if prod:
                            prod.estoque_atual -= int(float(item.get('quantidade', 0)))
                            prod.save()
                except Exception: pass
                    
            match = re.search(r'#(\d+)', str(venda.numero_nota))
            if match:
                venda_orig = Vendas.objects.filter(id=int(match.group(1))).first()
                if venda_orig:
                    venda_orig.status = 'FATURADO'
                    venda_orig.save()
                    
            venda.delete()
            return {'sucesso': True, 'mensagem': 'Rascunho com erro excluído! O estoque foi revertido. Pode emitir nova devolução.'}

        # Fluxo Normal de Cancelamento
        resposta = requests.delete(url, json={"justificativa": justificativa}, auth=auth)
        if resposta.status_code in [200, 201]:
            venda.status_fiscal = 'CANCELADO'
            venda.status = 'CANCELADO'
            venda.save()
            return {'sucesso': True, 'mensagem': 'Documento cancelado com sucesso na SEFAZ!'}
        return {'sucesso': False, 'erro': resposta.json().get('mensagem', 'Erro desconhecido')}

    @classmethod
    def enviar_email(cls, venda, email_destino):
        auth, base_url = cls._get_auth(venda.modelo_fiscal)
        endpoint = 'nfce' if venda.modelo_fiscal == '65' else 'nfe'
        
        nome_cliente = str(venda.cliente).strip() if venda.cliente and str(venda.cliente).strip().lower() != 'none' else "Cliente"
        texto = f"Olá, {nome_cliente}!\nAgradecemos por comprar na JB Tintas.\nSegue em anexo o PDF e o XML da Venda #{venda.id}.\nChave: {venda.chave_acesso}\nEquipe JB Tintas"
        
        resposta = requests.post(f"{base_url}/{endpoint}/{venda.id}/email", json={"emails": [email_destino], "mensagem": texto}, auth=auth)
        
        if resposta.status_code in [200, 201, 202]:
            return {'sucesso': True, 'mensagem': f'Enviado com sucesso para {email_destino}!'}
        return {'sucesso': False, 'erro': f"Recusado pela Focus NFe: {resposta.json().get('mensagem', 'Falha')}"}

    @classmethod
    def emitir_saida(cls, venda, dados):
        tipo_nota = dados.get('tipo_nota', 'NFE')
        venda.modelo_fiscal = '55' if tipo_nota == 'NFE' else '65'
        venda.status_fiscal = 'ENVIANDO'
        venda.save(update_fields=['modelo_fiscal', 'status_fiscal'])

        # Busca a URL correta com base no modelo acabado de definir
        auth, base_url = cls._get_auth(venda.modelo_fiscal)
        _, cnpj_emitente = cls._get_emissor_dados()

        endpoint = 'nfe' if tipo_nota == 'NFE' else 'nfce'
        url_api = f"{base_url}/{endpoint}?ref={venda.id}"

        payload = {
            "cnpj_emitente": cnpj_emitente,
            "natureza_operacao": dados.get('natureza_operacao', 'Venda de mercadoria'),
            "data_emissao": timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            "tipo_documento": "1", "local_destino": "1", "finalidade_emissao": "1", 
            "consumidor_final": dados.get('consumidor_final', '1'),
            "presenca_comprador": dados.get('indicador_presenca', '1'),
            "informacoes_adicionais_contribuinte": dados.get('info_complementar', ''),
            "modalidade_frete": dados.get('modalidade_frete', '9'), 
        }

        # Destinatário
        doc_req = ''.join(filter(str.isdigit, str(dados.get('dest_cpf_cnpj', ''))))
        ie_req = ''.join(filter(str.isdigit, str(dados.get('dest_ie', ''))))
        
        if len(doc_req) > 11:
            payload["cnpj_destinatario"] = doc_req
            if ie_req:
                payload["inscricao_estadual_destinatario"] = ie_req
                payload["indicador_inscricao_estadual_destinatario"] = "1"
            else:
                payload["indicador_inscricao_estadual_destinatario"] = "9"
        elif len(doc_req) == 11:
            payload["cpf_destinatario"] = doc_req
            payload["indicador_inscricao_estadual_destinatario"] = "9"

        if dados.get('dest_nome'): payload["nome_destinatario"] = dados['dest_nome']
        if dados.get('dest_logradouro'): payload["logradouro_destinatario"] = dados['dest_logradouro']
        if dados.get('dest_numero'): payload["numero_destinatario"] = str(dados['dest_numero'])
        if dados.get('dest_bairro'): payload["bairro_destinatario"] = dados['dest_bairro']
        if dados.get('dest_municipio'): payload["municipio_destinatario"] = dados['dest_municipio']
        if dados.get('dest_estado'): payload["uf_destinatario"] = dados['dest_estado']
        if dados.get('dest_cep'): payload["cep_destinatario"] = ''.join(filter(str.isdigit, str(dados['dest_cep'])))

        # Itens
        itens_focus = []
        if venda.cupom_texto:
            try:
                carrinho = json.loads(venda.cupom_texto)
                for idx, item in enumerate(carrinho):
                    qtd = float(item.get('qtd', 1))
                    vlr_unit = float(item.get('preco_desconto', item.get('preco_venda', item.get('preco', 0))))
                    
                    prod = Produtos.objects.filter(cod_interno=str(item.get('id', ''))).first()
                    if not prod and str(item.get('id', '')).isdigit():
                        prod = Produtos.objects.filter(id=str(item.get('id', ''))).first()
                    
                    cod_barras = "".join(filter(str.isdigit, str(getattr(prod, 'cod_barras', '')))) if prod else ""
                    gtin = cod_barras if cod_barras and len(cod_barras) in [8, 12, 13, 14] else "SEM GTIN"

                    item_payload = {
                        "numero_item": str(idx + 1),
                        "codigo_produto": str(item.get('id', f'PRD{idx+1}')),
                        "descricao": item.get('nome', 'Produto'),
                        "cfop": dados.get('cfop', '5102'),
                        "unidade_comercial": getattr(prod, 'unidade', 'UN') if prod else "UN",
                        "quantidade_comercial": f"{qtd:.2f}",
                        "valor_unitario_comercial": f"{vlr_unit:.2f}",
                        "valor_bruto": f"{qtd * vlr_unit:.2f}",
                        "codigo_ncm": "".join(filter(str.isdigit, str(getattr(prod, 'ncm', '32091010'))))[:8], 
                        "icms_origem": getattr(prod, 'origem', '0') if prod else "0",
                        "icms_situacao_tributaria": getattr(prod, 'cst_csosn', '102') if prod else "102",
                        "pis_situacao_tributaria": dados.get('pis_cst', '07'),
                        "cofins_situacao_tributaria": dados.get('cofins_cst', '07'),
                        "codigo_barras_comercial": gtin,
                        "codigo_barras_tributavel": gtin
                    }
                    itens_focus.append(item_payload)
            except Exception: pass
        
        payload["itens"] = itens_focus
        payload["formas_pagamento"] = [{"forma_pagamento": dados.get('forma_pagamento', '01'), "valor_pagamento": f"{venda.valor_total:.2f}"}]

        resposta = requests.post(url_api, json=payload, auth=auth)
        
        if resposta.status_code in [200, 201, 202]:
            venda.status_fiscal = 'PROCESSANDO_NUVEM'
            venda.chave_acesso = resposta.json().get('chave_nfe', '')
            venda.save(update_fields=['status_fiscal', 'chave_acesso'])
            return {'sucesso': True, 'mensagem': f"Documento fiscal {venda.id} enviado para a SEFAZ!"}
        else:
            erro_json = resposta.json()
            msg_erro = erro_json.get('mensagem', str(erro_json))
            if "já autorizada" in msg_erro.lower() or "referência já" in msg_erro.lower():
                venda.status_fiscal = 'PROCESSANDO_NUVEM'
                venda.save(update_fields=['status_fiscal'])
                return {'sucesso': True, 'mensagem': "Resgate: O sistema sincronizou uma nota que já estava autorizada."}

            if erro_json.get('erros'):
                msg_erro += " | " + " / ".join([e.get('mensagem', '') for e in erro_json.get('erros')])
            venda.status_fiscal = 'ERRO_REJEICAO'
            venda.save(update_fields=['status_fiscal'])
            return {'sucesso': False, 'erro': msg_erro}

    @classmethod
    def emitir_devolucao(cls, venda_original, nova_devolucao, dados):
        # Notas de Devolução são sempre Modelo 55 (NF-e)
        auth, base_url = cls._get_auth('55')
        emissor, cnpj_emitente = cls._get_emissor_dados()
        
        chave_limpa = "".join(filter(str.isdigit, str(dados.get('chave_original', ''))))[:44]
        cfop_devolucao = dados.get('cfop_devolucao', '1202')
        justificativa = dados.get('justificativa', 'Devolucao')
        
        payload = {
            "cnpj_emitente": cnpj_emitente,
            "natureza_operacao": "Devolucao de venda",
            "data_emissao": timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            "tipo_documento": "0", "finalidade_emissao": "4", "local_destino": "1",
            "consumidor_final": "1", "presenca_comprador": "1", "modalidade_frete": "9",
            "notas_referenciadas": [{"chave_nfe": chave_limpa}],
            "informacoes_adicionais_contribuinte": f"Devolucao da nota {chave_limpa}. Motivo: {justificativa}",
        }

        if emissor:
            payload["cnpj_destinatario"] = "".join(filter(str.isdigit, str(emissor.cnpj)))
            ie_limpa = "".join(filter(str.isdigit, str(emissor.inscricao_estadual)))
            payload["inscricao_estadual_destinatario"] = ie_limpa if ie_limpa else ""
            payload["indicador_inscricao_estadual_destinatario"] = "1" if ie_limpa else "9"
            payload["nome_destinatario"] = emissor.razao_social or "SISTEMA JB TINTAS"
            payload["logradouro_destinatario"] = emissor.endereco or "Nao Informado"
            payload["numero_destinatario"] = str(emissor.numero) if emissor.numero else "S/N"
            payload["bairro_destinatario"] = emissor.bairro or "Centro"
            payload["municipio_destinatario"] = emissor.cidade or "Sao Paulo"
            payload["uf_destinatario"] = emissor.estado or "SP"
            if emissor.cep: payload["cep_destinatario"] = "".join(filter(str.isdigit, str(emissor.cep)))

        itens_focus = []
        for idx, item in enumerate(dados.get('itens_devolvidos', [])):
            prod = Produtos.objects.filter(cod_interno=item.get('cod_interno')).first()
            if prod:
                qtd = float(item.get('quantidade'))
                vlr_unit = float(prod.preco_venda)
                cod_barras = "".join(filter(str.isdigit, str(prod.cod_barras)))
                gtin = cod_barras if cod_barras and len(cod_barras) in [8,12,13,14] else "SEM GTIN"

                itens_focus.append({
                    "numero_item": str(idx + 1), "codigo_produto": str(prod.cod_interno),
                    "descricao": prod.nome, "cfop": cfop_devolucao,
                    "unidade_comercial": getattr(prod, 'unidade', 'UN'),
                    "quantidade_comercial": f"{qtd:.2f}",
                    "valor_unitario_comercial": f"{vlr_unit:.2f}",
                    "valor_bruto": f"{qtd * vlr_unit:.2f}",
                    "codigo_ncm": "".join(filter(str.isdigit, str(getattr(prod, 'ncm', '32091010'))))[:8],
                    "icms_origem": "0", "icms_situacao_tributaria": getattr(prod, 'cst_csosn', '102'),
                    "pis_situacao_tributaria": "07", "cofins_situacao_tributaria": "07",
                    "codigo_barras_comercial": gtin, "codigo_barras_tributavel": gtin
                })
                prod.estoque_atual += int(qtd)
                prod.save()

        payload["itens"] = itens_focus
        payload["formas_pagamento"] = [{"forma_pagamento": "90", "valor_pagamento": "0.00"}]

        resposta = requests.post(f"{base_url}/nfe?ref={nova_devolucao.id}", json=payload, auth=auth)
        
        if resposta.status_code in [200, 201, 202]:
            venda_original.status = 'DEVOLVIDO'
            venda_original.save()
            nova_devolucao.chave_acesso = resposta.json().get('chave_nfe', '')
            nova_devolucao.save()
            return {'sucesso': True, 'mensagem': "NF-e gerada! Consulte o Painel de Devoluções."}
        else:
            nova_devolucao.delete()
            erro_json = resposta.json()
            msg = erro_json.get('mensagem', str(erro_json))
            if erro_json.get('erros'): msg += " | " + " / ".join([e.get('mensagem', '') for e in erro_json.get('erros')])
            return {'sucesso': False, 'erro': msg}

    @classmethod
    def inutilizar_numeracao(cls, dados):
        modelo = dados.get('modelo', '55')
        auth, base_url = cls._get_auth(modelo)
        _, cnpj_emitente = cls._get_emissor_dados()
        endpoint = 'nfe_inutilizacoes' if modelo == '55' else 'nfce_inutilizacoes'
        
        payload = {
            "cnpj": cnpj_emitente, "serie": "1",
            "numero_inicial": dados.get('numero_inicial'),
            "numero_final": dados.get('numero_final'),
            "justificativa": dados.get('justificativa')
        }
        resposta = requests.post(f"{base_url}/{endpoint}", json=payload, auth=auth)
        if resposta.status_code in [200, 201]:
            return {'sucesso': True, 'mensagem': "Numeração inutilizada com sucesso na SEFAZ!"}
        return {'sucesso': False, 'erro': resposta.json().get('mensagem', 'Erro na inutilização')}

    @classmethod
    def emitir_cce(cls, venda, correcao):
        auth, base_url = cls._get_auth(venda.modelo_fiscal)
        if venda.modelo_fiscal == '65':
            return {'sucesso': False, 'erro': 'A SEFAZ não permite CC-e para NFC-e (Modelo 65).'}
        
        resposta = requests.post(f"{base_url}/nfe/{venda.id}/carta_correcao", json={"correcao": correcao}, auth=auth)
        if resposta.status_code in [200, 201]:
            return {'sucesso': True, 'mensagem': "CC-e enviada com sucesso na SEFAZ!"}
        return {'sucesso': False, 'erro': resposta.json().get('mensagem', 'Erro ao emitir CC-e')}
        
    @classmethod
    def download_arquivo(cls, venda, tipo='pdf'):
        auth, base_url = cls._get_auth(venda.modelo_fiscal)
        endpoint = 'nfce' if venda.modelo_fiscal == '65' else 'nfe'
        
        resp_consulta = requests.get(f"{base_url}/{endpoint}/{venda.id}", auth=auth)
        if resp_consulta.status_code == 200:
            dados = resp_consulta.json()
            caminho = dados.get('caminho_danfe' if tipo == 'pdf' else 'caminho_xml_nota_fiscal')
            if caminho:
                dominio = base_url.replace('/v2', '') 
                url_arquivo = caminho if caminho.startswith('http') else f"{dominio}{caminho}"
                
                resp_arquivo = requests.get(url_arquivo, auth=auth)
                if resp_arquivo.status_code == 200:
                    return resp_arquivo.content
        return None
    