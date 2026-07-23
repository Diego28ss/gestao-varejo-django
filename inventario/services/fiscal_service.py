import os
import json
import re
import requests
from django.utils import timezone
from django.conf import settings
from inventario.models import Vendas, Produtos, ConfiguracaoEmissor

class FiscalService:
    """
    Camada de Serviço responsável pela comunicação com a API Notaas.
    Focada em varejo: NF-e (55) e NFC-e (65).
    """

    @classmethod
    def _get_config(cls):
        """Retorna os Headers com a x-api-key e a URL Base oficial da Notaas"""
        api_key = getattr(settings, 'NOTAAS_API_KEY', os.getenv('NOTAAS_API_KEY', ''))
        
        base_url = "https://platform.notaas.com.br/api/v1"
            
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        return headers, base_url

    @staticmethod
    def _get_emissor_dados():
        emissor = ConfiguracaoEmissor.objects.first()
        cnpj = "".join(filter(str.isdigit, str(emissor.cnpj))) if emissor and emissor.cnpj else "00000000000000"
        return emissor, cnpj

    @classmethod
    def emitir_saida(cls, venda, dados):
        headers, base_url = cls._get_config()

        tipo_nota = dados.get('tipo_nota', 'NFE')
        modelo = 55 if tipo_nota == 'NFE' else 65
        
        venda.modelo_fiscal = str(modelo)
        venda.status_fiscal = 'ENVIANDO'
        venda.save(update_fields=['modelo_fiscal', 'status_fiscal'])

        valor_total_float = float(venda.valor_total or 0.00)

        # 1. Estrutura Base
        payload = {
            "modelo": modelo,
            "naturezaOperacao": dados.get('natureza_operacao', 'Venda de mercadoria'),
            "tipoOperacao": 1, # 1 = Saída
            "finalidade": 1,   # 1 = Normal
            "presencaComprador": 1, 
        }

        # 2. Dados do Destinatário
        doc_req = ''.join(filter(str.isdigit, str(dados.get('dest_cpf_cnpj', ''))))
        ie_req = ''.join(filter(str.isdigit, str(dados.get('dest_ie', ''))))
        
        if doc_req or modelo == 55:
            dest = {}
            if len(doc_req) > 11:
                dest["cnpj"] = doc_req
                if ie_req:
                    dest["ie"] = ie_req
            elif len(doc_req) == 11:
                dest["cpf"] = doc_req

            dest["nome"] = dados.get('dest_nome', 'Consumidor Final')
            dest["indicadorIE"] = 1 if ie_req else 9
            
            cep = ''.join(filter(str.isdigit, str(dados.get('dest_cep', ''))))
            if cep:
                dest["endereco"] = {
                    "logradouro": dados.get('dest_logradouro', 'Nao Informado'),
                    "numero": str(dados.get('dest_numero', 'SN')),
                    "bairro": dados.get('dest_bairro', 'Centro'),
                    "codigoMunicipio": int(''.join(filter(str.isdigit, str(dados.get('dest_codigo_municipio', '3550308')))) or 3550308),
                    "cidade": dados.get('dest_municipio', 'Sao Paulo'),
                    "uf": dados.get('dest_estado', 'SP'),
                    "cep": cep
                }
            payload["dest"] = dest

        # 3. Itens da Venda
        items_payload = []
        if venda.cupom_texto:
            try:
                carrinho = json.loads(venda.cupom_texto)
                for idx, item in enumerate(carrinho):
                    qtd = float(item.get('qtd', 1))
                    vlr_unit = float(item.get('preco_desconto', item.get('preco_venda', item.get('preco', 0))))
                    vlr_total_item = round(qtd * vlr_unit, 2)
                    
                    prod = Produtos.objects.filter(cod_interno=str(item.get('id', ''))).first()
                    ncm = "".join(filter(str.isdigit, str(getattr(prod, 'ncm', '32091010'))))[:8]
                    
                    item_data = {
                        "codigo": str(item.get('id', f"PRD{idx}")),
                        "descricao": item.get('nome', 'Produto'),
                        "ncm": ncm if len(ncm) == 8 else "32091010",
                        "cfop": str(dados.get('cfop', '5102')),
                        "valorTotal": vlr_total_item,
                        "quantidade": qtd,
                        "valorUnitario": vlr_unit,
                        "unidade": getattr(prod, 'unidade', 'UN') if prod else "UN",
                        "csosn": getattr(prod, 'cst_csosn', '102') # MEI Simples Nacional
                    }
                    items_payload.append(item_data)
            except Exception: pass
        
        if not items_payload:
            items_payload.append({
                "descricao": "Venda de mercadoria",
                "ncm": "32091010",
                "cfop": str(dados.get('cfop', '5102')),
                "valorTotal": valor_total_float,
                "csosn": "102"
            })
            
        payload["items"] = items_payload

        # 4. Pagamentos
        forma_pagto_map = {'DINHEIRO': '01', 'CREDITO': '03', 'DEBITO': '04', 'PIX': '17'}
        tipo_pagamento = forma_pagto_map.get(dados.get('forma_pagamento', '01'), '01')
        
        payload["pagamentos"] = [{"tipoPagamento": tipo_pagamento, "valor": valor_total_float}]

        try:
            resposta = requests.post(f"{base_url}/nfe/emitir", json=payload, headers=headers, timeout=15)
            
            if resposta.status_code == 202:
                resp_json = resposta.json()
                venda.status_fiscal = 'PROCESSANDO_NUVEM'
                venda.id_transacao_api = resp_json.get('invoiceId')
                venda.save(update_fields=['status_fiscal', 'id_transacao_api'])
                return {'sucesso': True, 'mensagem': f"Documento fiscal enviado! Aguardando autorização."}
            else:
                erro_json = resposta.json()
                msg_erro = erro_json.get('error', {}).get('message', str(erro_json))
                venda.status_fiscal = 'ERRO_REJEICAO'
                venda.motivo_erro = msg_erro
                venda.save(update_fields=['status_fiscal', 'motivo_erro'])
                return {'sucesso': False, 'erro': f"Erro: {msg_erro}"}
        except Exception as e:
            venda.status_fiscal = 'ERRO_REJEICAO'
            venda.motivo_erro = str(e)
            venda.save(update_fields=['status_fiscal', 'motivo_erro'])
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def emitir_devolucao(cls, venda_original, nova_devolucao, dados):
        headers, base_url = cls._get_config()
        emissor, cnpj_emitente = cls._get_emissor_dados()
        
        chave_limpa = "".join(filter(str.isdigit, str(dados.get('chave_original', ''))))[:44]
        cfop_devolucao = dados.get('cfop_devolucao', '1202')
        justificativa = dados.get('justificativa', 'Devolucao')
        
        payload = {
            "modelo": 55,
            "naturezaOperacao": "Devolucao de mercadoria",
            "tipoOperacao": 0, # 0 = Entrada
            "finalidade": 4,   # 4 = Devolução
            "presencaComprador": 1,
            "nfesReferenciadas": [chave_limpa],
            "infCpl": f"Devolucao da nota {chave_limpa}. Motivo: {justificativa}",
            "pagamentos": [{"tipoPagamento": "90", "valor": 0}] # 90 = Sem Pagamento
        }

        # Na devolução, o destinatário informado no XML é o cliente que está devolvendo
        doc_req = ''.join(filter(str.isdigit, str(dados.get('dest_cpf_cnpj', ''))))
        ie_req = ''.join(filter(str.isdigit, str(dados.get('dest_ie', ''))))
        
        dest = {}
        if len(doc_req) > 11:
            dest["cnpj"] = doc_req
            if ie_req: dest["ie"] = ie_req
        elif len(doc_req) == 11:
            dest["cpf"] = doc_req

        dest["nome"] = dados.get('dest_nome', 'Cliente Devolucao')
        dest["indicadorIE"] = 1 if ie_req else 9
        
        cep = ''.join(filter(str.isdigit, str(dados.get('dest_cep', ''))))
        if cep:
            dest["endereco"] = {
                "logradouro": dados.get('dest_logradouro', 'Nao Informado'),
                "numero": str(dados.get('dest_numero', 'SN')),
                "bairro": dados.get('dest_bairro', 'Centro'),
                "codigoMunicipio": int(''.join(filter(str.isdigit, str(dados.get('dest_codigo_municipio', '3550308')))) or 3550308),
                "cidade": dados.get('dest_municipio', 'Sao Paulo'),
                "uf": dados.get('dest_estado', 'SP'),
                "cep": cep
            }
        payload["dest"] = dest

        itens_payload = []
        for idx, item in enumerate(dados.get('itens_devolvidos', [])):
            prod = Produtos.objects.filter(cod_interno=item.get('cod_interno')).first()
            if prod:
                qtd = float(item.get('quantidade'))
                vlr_unit = float(prod.preco_venda)
                
                itens_payload.append({
                    "codigo": str(prod.cod_interno),
                    "descricao": prod.nome, 
                    "cfop": cfop_devolucao,
                    "unidade": getattr(prod, 'unidade', 'UN'),
                    "quantidade": qtd,
                    "valorUnitario": vlr_unit,
                    "valorTotal": round(qtd * vlr_unit, 2),
                    "ncm": "".join(filter(str.isdigit, str(getattr(prod, 'ncm', '32091010'))))[:8],
                    "csosn": getattr(prod, 'cst_csosn', '102')
                })
                
                # Reversão de Estoque
                prod.estoque_atual += int(qtd)
                prod.save()

        payload["items"] = itens_payload

        try:
            resposta = requests.post(f"{base_url}/nfe/emitir", json=payload, headers=headers)
            
            if resposta.status_code == 202:
                resp_json = resposta.json()
                venda_original.status = 'DEVOLVIDO'
                venda_original.save()
                nova_devolucao.id_transacao_api = resp_json.get('invoiceId')
                nova_devolucao.save()
                return {'sucesso': True, 'mensagem': "Devolução processada! Consulte o status."}
            else:
                nova_devolucao.delete()
                erro_json = resposta.json()
                return {'sucesso': False, 'erro': erro_json.get('error', {}).get('message', str(erro_json))}
        except Exception as e:
            nova_devolucao.delete()
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def consultar_status(cls, venda):
        headers, base_url = cls._get_config()
        invoice_id = venda.id_transacao_api
        
        if not invoice_id:
            return {'sucesso': False, 'erro': 'A nota não possui invoiceId de transação.'}
        
        try:
            resposta = requests.get(f"{base_url}/nfe/invoices/{invoice_id}/status", headers=headers, timeout=10)
            
            if resposta.status_code == 200:
                dados = resposta.json()
                status_resp = dados.get('status', '').lower()
                
                if status_resp == 'issued':
                    venda.status_fiscal = 'AUTORIZADO'
                    venda.chave_acesso = dados.get('chaveAcesso', venda.chave_acesso)
                    venda.link_pdf = dados.get('pdfUrl', venda.link_pdf)
                    venda.link_xml = dados.get('xmlUrl', venda.link_xml)
                elif status_resp == 'cancelled':
                    venda.status_fiscal = 'CANCELADO'
                elif status_resp == 'error':
                    venda.status_fiscal = 'ERRO_REJEICAO'
                    venda.motivo_erro = dados.get('xMotivo', dados.get('errorMessage', 'Erro de SEFAZ'))
                elif status_resp in ['queued', 'processing']:
                    venda.status_fiscal = 'PROCESSANDO_NUVEM'
                
                venda.save(update_fields=['status_fiscal', 'chave_acesso', 'link_pdf', 'link_xml', 'motivo_erro'])
                return {'sucesso': True, 'status_fiscal': venda.status_fiscal, 'chave_acesso': venda.chave_acesso, 'motivo': venda.motivo_erro, 'status_interno': venda.status}
            return {'sucesso': False, 'erro': f'Erro API: {resposta.status_code}'}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def cancelar_nota(cls, venda, justificativa):
        headers, base_url = cls._get_config()
        
        # Manutenção da lógica local de exclusão/reversão se for Rascunho de Devolução
        if venda.status == 'DEVOLUCAO_ENTRADA' and venda.status_fiscal in ['ERRO', 'REJEITADO', 'ERRO_AUTORIZACAO', 'ERRO_REJEICAO']:
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
            return {'sucesso': True, 'mensagem': 'Rascunho excluído! O estoque foi revertido.'}

        invoice_id = venda.id_transacao_api
        if not invoice_id:
            return {'sucesso': False, 'erro': 'Nota sem invoiceId na API.'}

        # SEFAZ exige motivo com no mínimo 15 caracteres
        motivo = justificativa if len(justificativa) >= 15 else f"{justificativa} - Cancelamento pelo sistema ERP"

        payload = {
            "invoiceId": invoice_id,
            "motivo": motivo
        }
        
        try:
            resposta = requests.post(f"{base_url}/nfe/cancelar", json=payload, headers=headers)
            if resposta.status_code == 202:
                venda.status_fiscal = 'CANCELANDO'
                venda.save()
                return {'sucesso': True, 'mensagem': 'Pedido de cancelamento enviado para a SEFAZ!'}
            return {'sucesso': False, 'erro': resposta.json().get('error', {}).get('message', 'Erro ao cancelar')}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def emitir_cce(cls, venda, correcao):
        if venda.modelo_fiscal == '65':
            return {'sucesso': False, 'erro': 'A SEFAZ não permite CC-e para NFC-e (Modelo 65).'}
            
        headers, base_url = cls._get_config()
        invoice_id = venda.id_transacao_api
        
        if not invoice_id:
            return {'sucesso': False, 'erro': 'Nota sem invoiceId na API.'}
            
        payload = {"correcao": correcao}
        
        try:
            resposta = requests.post(f"{base_url}/nfe/invoices/{invoice_id}/correcao", json=payload, headers=headers)
            if resposta.status_code == 200:
                return {'sucesso': True, 'mensagem': "CC-e processada com sucesso!"}
            return {'sucesso': False, 'erro': resposta.json().get('error', {}).get('message', 'Falha na Correção')}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}
        
    @classmethod
    def download_arquivo(cls, venda, tipo='pdf'):
        """Efetua o download do binário diretamente pelas rotas /danfe e /xml"""
        headers, base_url = cls._get_config()
        invoice_id = venda.id_transacao_api
        
        if not invoice_id: return None
        
        endpoint = "danfe" if tipo == 'pdf' else "xml"
        
        try:
            resp_arquivo = requests.get(f"{base_url}/nfe/invoices/{invoice_id}/{endpoint}", headers=headers)
            if resp_arquivo.status_code == 200:
                return resp_arquivo.content
            return None
        except Exception:
            return None

    @classmethod
    def enviar_email(cls, venda, email_destino):
        """Notaas API não expõe endpoint direto de disparo de e-mail. Requer rotina SMTP local."""
        return {'sucesso': False, 'erro': 'Disparo de e-mail deve ser processado internamente pelo sistema ERP.'}

    @classmethod
    def inutilizar_numeracao(cls, dados):
        """Notaas API realiza inutilização automaticamente quando o status é 539, não possuindo endpoint manual exposto."""
        return {'sucesso': False, 'erro': 'Endpoint de inutilização manual não suportado na API Notaas.'}
    