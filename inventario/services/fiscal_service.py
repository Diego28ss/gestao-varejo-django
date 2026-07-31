import os
import json
import re
import requests
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from inventario.models import Vendas, Produtos, ConfiguracaoEmissor, Clientes

class FiscalService:
    """
    Camada de Serviço responsável pela comunicação com a API Notaas.
    Focada em varejo: NF-e (Modelo 55) e NFC-e (Modelo 65).
    """

    @classmethod
    def _get_config(cls):
        api_key = getattr(settings, 'NOTAAS_API_KEY', '')
        base_url = "https://platform.notaas.com.br/api/v1"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        return headers, base_url

    @staticmethod
    def _get_emissor_dados():
        emissor = ConfiguracaoEmissor.objects.first()
        cnpj = "".join(filter(str.isdigit, str(emissor.cnpj))) if emissor and emissor.cnpj else "00000000000000"
        return emissor, cnpj

    @staticmethod
    def _validar_chave_sefaz(chave):
        """Calcula o Módulo 11 oficial da SEFAZ para provar se a chave é real"""
        if len(chave) != 44 or not chave.isdigit():
            return False
        soma = 0
        peso = 2
        for i in range(42, -1, -1):
            soma += int(chave[i]) * peso
            peso = 2 if peso == 9 else peso + 1
        resto = soma % 11
        dv = 0 if resto <= 1 else 11 - resto
        return dv == int(chave[43])

    @classmethod
    def _extrair_mensagem_erro(cls, resposta):
        try:
            erro_json = resposta.json()
            if isinstance(erro_json, dict):
                err = erro_json.get('error')
                if isinstance(err, dict):
                    return err.get('message', str(erro_json))
                elif isinstance(err, str):
                    return err
                return erro_json.get('message', erro_json.get('mensagem', str(erro_json)))
            return str(erro_json)
        except ValueError:
            return resposta.text

    @classmethod
    def emitir_saida(cls, venda, dados):
        headers, base_url = cls._get_config()

        tipo_nota = dados.get('tipo_nota', 'NFE')
        modelo = 55 if tipo_nota == 'NFE' else 65

        payload = {
            "modelo": modelo,
            "naturezaOperacao": dados.get('natureza_operacao', 'Venda de mercadoria'),
            "tipoOperacao": 1, 
            "finalidade": 1,   
            "presencaComprador": 1, 
        }

        cliente_id = dados.get('cliente_id')
        cliente_banco = None
        
        if cliente_id and str(cliente_id).isdigit():
            cliente_banco = Clientes.objects.filter(id=cliente_id).first()

        if cliente_banco:
            cpf_cnpj_raw = cliente_banco.cnpj if cliente_banco.tipo_pessoa == 'PJ' and cliente_banco.cnpj else cliente_banco.cpf
            doc_req = ''.join(filter(str.isdigit, str(cpf_cnpj_raw or '')))
            ie_req = ''.join(filter(str.isdigit, str(cliente_banco.inscricao_estadual or '')))
            nome_req = cliente_banco.razao_social if cliente_banco.tipo_pessoa == 'PJ' and cliente_banco.razao_social else cliente_banco.nome
            cep_req = ''.join(filter(str.isdigit, str(cliente_banco.cep or '')))
            logradouro_req = cliente_banco.endereco or 'Nao Informado'
            numero_req = cliente_banco.numero or 'SN'
            bairro_req = cliente_banco.bairro or 'Centro'
            cidade_req = cliente_banco.cidade or 'Sao Paulo'
            estado_req = cliente_banco.estado or 'SP'
        else:
            doc_req = ''.join(filter(str.isdigit, str(dados.get('dest_cpf_cnpj', ''))))
            ie_req = ''.join(filter(str.isdigit, str(dados.get('dest_ie', ''))))
            nome_req = dados.get('dest_nome') or 'Consumidor Final'
            cep_req = ''.join(filter(str.isdigit, str(dados.get('dest_cep', ''))))
            logradouro_req = dados.get('dest_logradouro') or 'Nao Informado'
            numero_req = dados.get('dest_numero') or 'SN'
            bairro_req = dados.get('dest_bairro') or 'Centro'
            cidade_req = dados.get('dest_municipio') or 'Sao Paulo'
            estado_req = dados.get('dest_estado') or 'SP'

        if modelo == 55 or (modelo == 65 and len(doc_req) >= 11):
            dest = {}
            if len(doc_req) >= 14:
                dest["cnpj"] = doc_req[:14]
                if ie_req: dest["ie"] = ie_req
            elif len(doc_req) >= 11:
                dest["cpf"] = doc_req[:11]
            elif modelo == 55:
                return {'sucesso': False, 'erro': 'Para emitir NF-e, o cliente precisa ter CPF ou CNPJ preenchido no cadastro.'}

            dest["nome"] = nome_req or 'Consumidor Final'
            dest["indicadorIE"] = 1 if ie_req else 9
            
            if cep_req or modelo == 55:
                dest["endereco"] = {
                    "logradouro": logradouro_req,
                    "numero": str(numero_req),
                    "bairro": bairro_req,
                    "codigoMunicipio": int(''.join(filter(str.isdigit, str(dados.get('dest_codigo_municipio', '3550308')))) or 3550308),
                    "cidade": cidade_req,
                    "uf": estado_req,
                    "cep": cep_req if len(cep_req) == 8 else '01010100'
                }
            payload["dest"] = dest

        # ATUALIZAÇÃO DO NOME DO CLIENTE NO BANCO DE DADOS AQUI!
        venda.modelo_fiscal = str(modelo)
        venda.status_fiscal = 'ENVIANDO'
        venda.cliente = str(nome_req)[:255]
        
        try:
            venda.save(update_fields=['modelo_fiscal', 'status_fiscal', 'cliente'])
        except Exception:
            venda.save()

        valor_total_float = float(venda.valor_total or 0.00)

        items_payload = []
        if venda.cupom_texto:
            try:
                carrinho = json.loads(venda.cupom_texto)
                if isinstance(carrinho, str): carrinho = json.loads(carrinho)
                    
                for idx, item in enumerate(carrinho):
                    if not isinstance(item, dict): continue
                        
                    qtd = float(item.get('qtd', 1))
                    vlr_unit = float(item.get('preco_desconto', item.get('preco_venda', item.get('preco', 0))))
                    vlr_total_item = round(qtd * vlr_unit, 2)
                    
                    item_id = str(item.get('id', '')).strip()
                    prod = None
                    if item_id.isdigit():
                        prod = Produtos.objects.filter(Q(id=int(item_id)) | Q(cod_interno=item_id)).first()
                    else:
                        prod = Produtos.objects.filter(cod_interno=item_id).first()
                        
                    ncm_raw = str(getattr(prod, 'ncm', '32091010')) if prod else '32091010'
                    ncm = "".join(filter(str.isdigit, ncm_raw))[:8]
                    
                    item_data = {
                        "codigo": item_id or f"PRD{idx}",
                        "descricao": item.get('nome', 'Produto'),
                        "ncm": ncm if len(ncm) == 8 else "32091010",
                        "cfop": str(dados.get('cfop', '5102')),
                        "valorTotal": vlr_total_item,
                        "quantidade": qtd,
                        "valorUnitario": vlr_unit,
                        "unidade": getattr(prod, 'unidade', 'UN') if prod else "UN",
                        "csosn": getattr(prod, 'cst_csosn', '102') if prod else "102"
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
                return {'sucesso': True, 'mensagem': "Documento fiscal enviado! Aguardando autorização."}
            else:
                msg_erro = cls._extrair_mensagem_erro(resposta)
                venda.status_fiscal = 'ERRO_REJEICAO'
                venda.motivo_erro = msg_erro[:250]
                venda.save(update_fields=['status_fiscal', 'motivo_erro'])
                return {'sucesso': False, 'erro': msg_erro}
        except Exception as e:
            venda.status_fiscal = 'ERRO_REJEICAO'
            venda.motivo_erro = str(e)[:250]
            venda.save(update_fields=['status_fiscal', 'motivo_erro'])
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def emitir_devolucao(cls, venda_original, nova_devolucao, dados):
        headers, base_url = cls._get_config()
        emissor, cnpj_emitente = cls._get_emissor_dados()
        
        chave_original_bruta = str(dados.get('chave_original', ''))
        chave_limpa = "".join(filter(str.isdigit, chave_original_bruta))[:44]
        
        if not cls._validar_chave_sefaz(chave_limpa):
            nova_devolucao.delete()
            return {
                'sucesso': False, 
                'erro': f'SISTEMA BLOQUEADO: A chave da nota original ({chave_limpa}) é falsa ou matematicamente inválida.'
            }

        cfop_devolucao = str(dados.get('cfop_devolucao', '1202'))[:4]
        justificativa = dados.get('justificativa', 'Devolucao de mercadoria')
        
        payload = {
            "modelo": 55,
            "naturezaOperacao": "Devolucao de mercadoria",
            "tipoOperacao": 0,
            "finalidade": 4, 
            "infCpl": f"Devolucao da nota {chave_limpa}. Motivo: {justificativa}",
            "pagamentos": [{"tipoPagamento": "90", "valor": 0}] 
        }

        cliente_nome = str(venda_original.cliente).strip()
        cliente_banco = Clientes.objects.filter(nome__iexact=cliente_nome).first() if cliente_nome and cliente_nome.lower() != 'none' else None

        if cliente_banco and (cliente_banco.cpf or cliente_banco.cnpj):
            doc_raw = cliente_banco.cnpj if cliente_banco.tipo_pessoa == 'PJ' and cliente_banco.cnpj else cliente_banco.cpf
            doc_req = ''.join(filter(str.isdigit, str(doc_raw or '')))
            ie_req = ''.join(filter(str.isdigit, str(cliente_banco.inscricao_estadual or '')))
            nome_req = cliente_banco.razao_social if cliente_banco.tipo_pessoa == 'PJ' and cliente_banco.razao_social else cliente_banco.nome
            cep_req = ''.join(filter(str.isdigit, str(cliente_banco.cep or '')))
            logradouro_req = cliente_banco.endereco or 'Nao Informado'
            numero_req = cliente_banco.numero or 'SN'
            bairro_req = cliente_banco.bairro or 'Centro'
            cidade_req = cliente_banco.cidade or 'Sao Paulo'
            estado_req = cliente_banco.estado or 'SP'
        else:
            doc_req = ''.join(filter(str.isdigit, str(emissor.cnpj or '')))
            ie_req = ''.join(filter(str.isdigit, str(emissor.inscricao_estadual or '')))
            nome_req = emissor.razao_social or 'Consumidor Final'
            cep_req = ''.join(filter(str.isdigit, str(emissor.cep or '')))
            logradouro_req = emissor.endereco or 'Nao Informado'
            numero_req = str(emissor.numero or 'SN')
            bairro_req = emissor.bairro or 'Centro'
            cidade_req = emissor.cidade or 'Sao Paulo'
            estado_req = emissor.estado or 'SP'

        dest = {}
        if len(doc_req) >= 14:
            dest["cnpj"] = doc_req[:14]
            if ie_req: dest["ie"] = ie_req
        elif len(doc_req) >= 11:
            dest["cpf"] = doc_req[:11]
        else:
            nova_devolucao.delete()
            return {'sucesso': False, 'erro': 'A loja precisa ter um CNPJ válido configurado para emitir devolução de vendas anônimas.'}

        dest["nome"] = nome_req
        dest["indicadorIE"] = 1 if ie_req else 9
        dest["endereco"] = {
            "logradouro": logradouro_req,
            "numero": str(numero_req),
            "bairro": bairro_req,
            "codigoMunicipio": 3550308, 
            "cidade": cidade_req,
            "uf": estado_req,
            "cep": cep_req if len(cep_req) == 8 else '01010100'
        }
        payload["dest"] = dest

        itens_payload = []
        produtos_alterados_estoque = []
        carrinho_original = []
        
        try:
            carrinho_original = json.loads(venda_original.cupom_texto)
            if isinstance(carrinho_original, str): carrinho_original = json.loads(carrinho_original)
        except: pass

        for idx, item in enumerate(dados.get('itens_devolvidos', [])):
            if not isinstance(item, dict): continue
            
            cod_interno = str(item.get('cod_interno', '')).strip()
            qtd = float(item.get('quantidade', 1))
            if qtd <= 0: continue
            
            prod = None
            if cod_interno.isdigit():
                prod = Produtos.objects.filter(Q(id=int(cod_interno)) | Q(cod_interno=cod_interno)).first()
            else:
                prod = Produtos.objects.filter(cod_interno=cod_interno).first()
            
            orig_item = {}
            n_item_original = idx + 1 
            for orig_idx, orig_i in enumerate(carrinho_original):
                if str(orig_i.get('id', '')) == cod_interno:
                    orig_item = orig_i
                    n_item_original = orig_idx + 1
                    break
            
            descricao = prod.nome if prod else orig_item.get('nome', f'Item Devolvido {idx}')
            vlr_unit = float(prod.preco_venda) if prod else float(orig_item.get('preco_desconto', orig_item.get('preco_venda', 0)))
            if vlr_unit <= 0: vlr_unit = 0.01 
            
            ncm_raw = str(getattr(prod, 'ncm', '32091010')) if prod else "32091010"
            ncm = "".join(filter(str.isdigit, ncm_raw))[:8]
            
            itens_payload.append({
                "codigo": cod_interno or f"DEV{idx}",
                "descricao": descricao, 
                "cfop": cfop_devolucao,
                "unidade": getattr(prod, 'unidade', 'UN') if prod else 'UN',
                "quantidade": qtd,
                "valorUnitario": vlr_unit,
                "valorTotal": round(qtd * vlr_unit, 2),
                "ncm": ncm if len(ncm) == 8 else "32091010",
                "csosn": getattr(prod, 'cst_csosn', '102') if prod else '102',
                "nfeReferenciada": {
                    "chaveAcesso": chave_limpa,
                    "nItem": n_item_original
                }
            })
            
            if prod:
                prod.estoque_atual = float(prod.estoque_atual or 0) + qtd
                prod.save()
                produtos_alterados_estoque.append((prod, qtd))

        if not itens_payload:
            nova_devolucao.delete()
            return {'sucesso': False, 'erro': 'Nenhum item válido foi processado para devolução.'}

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
                for p_rev, q_rev in produtos_alterados_estoque:
                    p_rev.estoque_atual = float(p_rev.estoque_atual or 0) - q_rev
                    p_rev.save()
                return {'sucesso': False, 'erro': cls._extrair_mensagem_erro(resposta)}
        except Exception as e:
            nova_devolucao.delete()
            for p_rev, q_rev in produtos_alterados_estoque:
                p_rev.estoque_atual = float(p_rev.estoque_atual or 0) - q_rev
                p_rev.save()
            return {'sucesso': False, 'erro': str(e)}

    @classmethod
    def consultar_status(cls, venda):
        headers, base_url = cls._get_config()
        invoice_id = venda.id_transacao_api
        
        if not invoice_id:
            return {'sucesso': False, 'erro': 'A nota não possui invoiceId para consulta.'}
        
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
        
        if venda.status == 'DEVOLUCAO_ENTRADA' and venda.status_fiscal in ['ERRO', 'REJEITADO', 'ERRO_AUTORIZACAO', 'ERRO_REJEICAO']:
            if venda.cupom_texto:
                try:
                    carrinho = json.loads(venda.cupom_texto)
                    if isinstance(carrinho, str): carrinho = json.loads(carrinho)
                    for item in carrinho:
                        if isinstance(item, dict):
                            item_id = str(item.get('id') or item.get('cod_interno', '')).strip()
                            prod = None
                            if item_id.isdigit():
                                prod = Produtos.objects.filter(Q(id=int(item_id)) | Q(cod_interno=item_id)).first()
                            else:
                                prod = Produtos.objects.filter(cod_interno=item_id).first()
                                
                            if prod:
                                prod.estoque_atual = float(prod.estoque_atual or 0) - float(item.get('quantidade', item.get('qtd', 0)))
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
            return {'sucesso': False, 'erro': cls._extrair_mensagem_erro(resposta)}
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
            return {'sucesso': False, 'erro': cls._extrair_mensagem_erro(resposta)}
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}
        
    @classmethod
    def download_arquivo(cls, venda, tipo='pdf'):
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
        return {'sucesso': False, 'erro': 'A Notaas não dispara e-mail diretamente. Integre com o SMTP local do ERP.'}

    @classmethod
    def inutilizar_numeracao(cls, dados):
        return {'sucesso': False, 'erro': 'A Notaas trata rejeições 539 automaticamente. Inutilização manual não exposta.'}
    