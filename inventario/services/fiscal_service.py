import os
import json
import re
import requests
from django.utils import timezone
from django.conf import settings
from inventario.models import Vendas, Produtos, ConfiguracaoEmissor

class FiscalService:
    """
    Camada de Serviço responsável pela comunicação com a API Gerando Nota Fácil.
    Isola a regra de negócio fiscal das Views.
    """

    @classmethod
    def _get_config(cls):
        """Retorna os Headers com o Bearer Token e a URL Base correta (Homologação ou Produção)"""
        token = getattr(settings, 'GNF_API_TOKEN', os.getenv('GNF_API_TOKEN', ''))
        ambiente = getattr(settings, 'GNF_AMBIENTE', os.getenv('GNF_AMBIENTE', 'homologacao'))
        
        if ambiente.lower() == 'producao':
            base_url = "https://api.gerandonotafacil.com.br/api/v1"
        else:
            base_url = "https://homologacao.gerandonotafacil.com.br/api/v1"
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        return headers, base_url

    @staticmethod
    def _get_emissor_dados():
        emissor = ConfiguracaoEmissor.objects.first()
        cnpj = "".join(filter(str.isdigit, str(emissor.cnpj))) if emissor and emissor.cnpj else "00000000000000"
        return emissor, cnpj

    @classmethod
    def consultar_status(cls, venda):
        headers, base_url = cls._get_config()
        # Assume que o ID da transação da API foi salvo na chave_acesso ou campo próprio
        id_transacao = venda.chave_acesso if venda.chave_acesso else venda.id
        
        endpoint = f"{base_url}/nfe/{id_transacao}"
        
        try:
            resposta = requests.get(endpoint, headers=headers, timeout=15)
            
            if resposta.status_code == 200:
                dados = resposta.json()
                status = dados.get('status', '').lower()
                
                if status in ['autorizado', 'aprovado']:
                    venda.status_fiscal = 'AUTORIZADO'
                    venda.chave_acesso = dados.get('chave', venda.chave_acesso)
                elif status == 'cancelado':
                    venda.status_fiscal = 'CANCELADO'
                elif status in ['erro', 'rejeitado']:
                    venda.status_fiscal = 'ERRO'
                else:
                    venda.status_fiscal = status.upper()
                
                venda.save(update_fields=['status_fiscal', 'chave_acesso'])
                motivo = dados.get('motivo', dados.get('mensagem', '')) if venda.status_fiscal == 'ERRO' else ''
                
                return {'sucesso': True, 'status_fiscal': venda.status_fiscal, 'chave_acesso': venda.chave_acesso, 'motivo': motivo, 'status_interno': venda.status}
            return {'sucesso': False, 'erro': f'Erro API: {resposta.status_code} - {resposta.text}'}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def cancelar_nota(cls, venda, justificativa):
        headers, base_url = cls._get_config()
        
        # AUTO-CURA PARA DEVOLUÇÕES REJEITADAS (Mantido da sua lógica original)
        if venda.status == 'DEVOLUCAO_ENTRADA' and venda.status_fiscal in ['ERRO', 'REJEITADO', 'ERRO_AUTORIZACAO']:
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

        # Fluxo Normal de Cancelamento GNF
        id_transacao = venda.chave_acesso if venda.chave_acesso else venda.id
        endpoint = f"{base_url}/nfe/{id_transacao}/cancelar"
        
        try:
            resposta = requests.post(endpoint, json={"justificativa": justificativa}, headers=headers)
            if resposta.status_code in [200, 201]:
                venda.status_fiscal = 'CANCELADO'
                venda.status = 'CANCELADO'
                venda.save()
                return {'sucesso': True, 'mensagem': 'Documento cancelado com sucesso na SEFAZ!'}
            return {'sucesso': False, 'erro': resposta.json().get('mensagem', 'Erro desconhecido')}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def enviar_email(cls, venda, email_destino):
        headers, base_url = cls._get_config()
        id_transacao = venda.chave_acesso if venda.chave_acesso else venda.id
        endpoint = f"{base_url}/nfe/{id_transacao}/email"
        
        try:
            resposta = requests.post(endpoint, json={"email": email_destino}, headers=headers)
            if resposta.status_code in [200, 201, 202]:
                return {'sucesso': True, 'mensagem': f'Enviado com sucesso para {email_destino}!'}
            return {'sucesso': False, 'erro': f"Recusado pela API: {resposta.json().get('mensagem', 'Falha')}"}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def emitir_saida(cls, venda, dados):
        tipo_nota = dados.get('tipo_nota', 'NFE')
        venda.modelo_fiscal = '55' if tipo_nota == 'NFE' else '65'
        venda.status_fiscal = 'ENVIANDO'
        venda.save(update_fields=['modelo_fiscal', 'status_fiscal'])

        headers, base_url = cls._get_config()
        _, cnpj_emitente = cls._get_emissor_dados()
        endpoint = f"{base_url}/nfe/emitir"

        # Payload adaptado para o padrão REST genérico da GNF
        payload = {
            "natureza_operacao": dados.get('natureza_operacao', 'Venda de mercadoria'),
            "data_emissao": timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            "tipo_documento": 1,
            "finalidade_emissao": 1, 
            "consumidor_final": int(dados.get('consumidor_final', 1)),
            "presenca_comprador": int(dados.get('indicador_presenca', 1)),
            "informacoes_adicionais": dados.get('info_complementar', ''),
            "modalidade_frete": int(dados.get('modalidade_frete', 9)), 
        }

        # Destinatário
        doc_req = ''.join(filter(str.isdigit, str(dados.get('dest_cpf_cnpj', ''))))
        ie_req = ''.join(filter(str.isdigit, str(dados.get('dest_ie', ''))))
        
        destinatario = {}
        if len(doc_req) > 11:
            destinatario["cnpj"] = doc_req
            if ie_req:
                destinatario["inscricao_estadual"] = ie_req
                destinatario["indicador_ie"] = 1
            else:
                destinatario["indicador_ie"] = 9
        elif len(doc_req) == 11:
            destinatario["cpf"] = doc_req
            destinatario["indicador_ie"] = 9

        if dados.get('dest_nome'): destinatario["nome"] = dados['dest_nome']
        if dados.get('dest_logradouro'): destinatario["logradouro"] = dados['dest_logradouro']
        if dados.get('dest_numero'): destinatario["numero"] = str(dados['dest_numero'])
        if dados.get('dest_bairro'): destinatario["bairro"] = dados['dest_bairro']
        if dados.get('dest_municipio'): destinatario["municipio"] = dados['dest_municipio']
        if dados.get('dest_estado'): destinatario["uf"] = dados['dest_estado']
        if dados.get('dest_cep'): destinatario["cep"] = ''.join(filter(str.isdigit, str(dados['dest_cep'])))
        
        payload["destinatario"] = destinatario

        # Itens
        itens_gnf = []
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
                        "numero_item": idx + 1,
                        "codigo": str(item.get('id', f'PRD{idx+1}')),
                        "descricao": item.get('nome', 'Produto'),
                        "cfop": dados.get('cfop', '5102'),
                        "unidade": getattr(prod, 'unidade', 'UN') if prod else "UN",
                        "quantidade": qtd,
                        "valor_unitario": vlr_unit,
                        "ncm": "".join(filter(str.isdigit, str(getattr(prod, 'ncm', '32091010'))))[:8], 
                        "impostos": {
                            "icms": {
                                "origem": int(getattr(prod, 'origem', '0') if prod else 0),
                                "csosn": getattr(prod, 'cst_csosn', '102') if prod else "102"
                            },
                            "pis": {"cst": dados.get('pis_cst', '07')},
                            "cofins": {"cst": dados.get('cofins_cst', '07')}
                        },
                        "codigo_barras": gtin
                    }
                    itens_gnf.append(item_payload)
            except Exception: pass
        
        payload["itens"] = itens_gnf
        payload["pagamento"] = {"forma": dados.get('forma_pagamento', '01'), "valor": venda.valor_total}

        try:
            resposta = requests.post(endpoint, json=payload, headers=headers)
            
            if resposta.status_code in [200, 201, 202]:
                venda.status_fiscal = 'PROCESSANDO_NUVEM'
                venda.chave_acesso = resposta.json().get('id', resposta.json().get('chave', ''))
                venda.save(update_fields=['status_fiscal', 'chave_acesso'])
                return {'sucesso': True, 'mensagem': f"Documento fiscal {venda.id} enviado para a SEFAZ!"}
            else:
                erro_json = resposta.json()
                msg_erro = erro_json.get('mensagem', str(erro_json))
                venda.status_fiscal = 'ERRO_REJEICAO'
                venda.save(update_fields=['status_fiscal'])
                return {'sucesso': False, 'erro': msg_erro}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def emitir_devolucao(cls, venda_original, nova_devolucao, dados):
        headers, base_url = cls._get_config()
        emissor, cnpj_emitente = cls._get_emissor_dados()
        
        chave_limpa = "".join(filter(str.isdigit, str(dados.get('chave_original', ''))))[:44]
        cfop_devolucao = dados.get('cfop_devolucao', '1202')
        justificativa = dados.get('justificativa', 'Devolucao')
        
        payload = {
            "natureza_operacao": "Devolucao de venda",
            "data_emissao": timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            "tipo_documento": 0, 
            "finalidade_emissao": 4, 
            "consumidor_final": 1, 
            "presenca_comprador": 1, 
            "modalidade_frete": 9,
            "notas_referenciadas": [chave_limpa],
            "informacoes_adicionais": f"Devolucao da nota {chave_limpa}. Motivo: {justificativa}",
        }

        if emissor:
            ie_limpa = "".join(filter(str.isdigit, str(emissor.inscricao_estadual)))
            payload["destinatario"] = {
                "cnpj": "".join(filter(str.isdigit, str(emissor.cnpj))),
                "inscricao_estadual": ie_limpa if ie_limpa else "",
                "indicador_ie": 1 if ie_limpa else 9,
                "nome": emissor.razao_social or "SISTEMA JB TINTAS",
                "logradouro": emissor.endereco or "Nao Informado",
                "numero": str(emissor.numero) if emissor.numero else "S/N",
                "bairro": emissor.bairro or "Centro",
                "municipio": emissor.cidade or "Sao Paulo",
                "uf": emissor.estado or "SP",
                "cep": "".join(filter(str.isdigit, str(emissor.cep))) if emissor.cep else ""
            }

        itens_gnf = []
        for idx, item in enumerate(dados.get('itens_devolvidos', [])):
            prod = Produtos.objects.filter(cod_interno=item.get('cod_interno')).first()
            if prod:
                qtd = float(item.get('quantidade'))
                vlr_unit = float(prod.preco_venda)
                cod_barras = "".join(filter(str.isdigit, str(prod.cod_barras)))
                gtin = cod_barras if cod_barras and len(cod_barras) in [8,12,13,14] else "SEM GTIN"

                itens_gnf.append({
                    "numero_item": idx + 1, 
                    "codigo": str(prod.cod_interno),
                    "descricao": prod.nome, 
                    "cfop": cfop_devolucao,
                    "unidade": getattr(prod, 'unidade', 'UN'),
                    "quantidade": qtd,
                    "valor_unitario": vlr_unit,
                    "ncm": "".join(filter(str.isdigit, str(getattr(prod, 'ncm', '32091010'))))[:8],
                    "impostos": {
                        "icms": {
                            "origem": 0, 
                            "csosn": getattr(prod, 'cst_csosn', '102')
                        },
                        "pis": {"cst": "07"}, 
                        "cofins": {"cst": "07"}
                    },
                    "codigo_barras": gtin
                })
                prod.estoque_atual += int(qtd)
                prod.save()

        payload["itens"] = itens_gnf
        payload["pagamento"] = {"forma": "90", "valor": 0.00}

        endpoint = f"{base_url}/nfe/emitir"
        try:
            resposta = requests.post(endpoint, json=payload, headers=headers)
            
            if resposta.status_code in [200, 201, 202]:
                venda_original.status = 'DEVOLVIDO'
                venda_original.save()
                nova_devolucao.chave_acesso = resposta.json().get('id', '')
                nova_devolucao.save()
                return {'sucesso': True, 'mensagem': "NF-e gerada! Consulte o Painel de Devoluções."}
            else:
                nova_devolucao.delete()
                erro_json = resposta.json()
                return {'sucesso': False, 'erro': erro_json.get('mensagem', str(erro_json))}
        except Exception as e:
            nova_devolucao.delete()
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def inutilizar_numeracao(cls, dados):
        headers, base_url = cls._get_config()
        endpoint = f"{base_url}/nfe/inutilizar"
        
        payload = {
            "serie": 1,
            "numero_inicial": dados.get('numero_inicial'),
            "numero_final": dados.get('numero_final'),
            "justificativa": dados.get('justificativa')
        }
        try:
            resposta = requests.post(endpoint, json=payload, headers=headers)
            if resposta.status_code in [200, 201]:
                return {'sucesso': True, 'mensagem': "Numeração inutilizada com sucesso na SEFAZ!"}
            return {'sucesso': False, 'erro': resposta.json().get('mensagem', 'Erro na inutilização')}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def emitir_cce(cls, venda, correcao):
        if venda.modelo_fiscal == '65':
            return {'sucesso': False, 'erro': 'A SEFAZ não permite CC-e para NFC-e (Modelo 65).'}
            
        headers, base_url = cls._get_config()
        id_transacao = venda.chave_acesso if venda.chave_acesso else venda.id
        endpoint = f"{base_url}/nfe/{id_transacao}/cce"
        
        try:
            resposta = requests.post(endpoint, json={"justificativa": correcao}, headers=headers)
            if resposta.status_code in [200, 201]:
                return {'sucesso': True, 'mensagem': "CC-e enviada com sucesso na SEFAZ!"}
            return {'sucesso': False, 'erro': resposta.json().get('mensagem', 'Erro ao emitir CC-e')}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}
        
    @classmethod
    def download_arquivo(cls, venda, tipo='pdf'):
        headers, base_url = cls._get_config()
        id_transacao = venda.chave_acesso if venda.chave_acesso else venda.id
        endpoint = f"{base_url}/nfe/{id_transacao}"
        
        try:
            resp_consulta = requests.get(endpoint, headers=headers)
            if resp_consulta.status_code == 200:
                dados = resp_consulta.json()
                
                # A GNF geralmente retorna a URL do PDF e do XML direto no JSON
                url_arquivo = dados.get('pdf' if tipo == 'pdf' else 'xml')
                
                if url_arquivo:
                    resp_arquivo = requests.get(url_arquivo)
                    if resp_arquivo.status_code == 200:
                        return resp_arquivo.content
            return None
        except Exception:
            return None
        