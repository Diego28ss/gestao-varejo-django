import json
from django.db import transaction
from django.db.models import F
from inventario.models import Clientes, Produtos, Vendas, ConfiguracaoPontos, Usuarios

class VendaService:

    @staticmethod
    def registrar_checkout(dados):
        status_venda = dados.get('status', 'VENDA')
        pontos_resgatados = int(dados.get('pontos_resgatados', 0))
        carrinho = dados.get('carrinho', [])
        valor_final = float(dados.get('valor_final', 0))
        nome_vendedor = dados.get('vendedor')

        # 🛡️ TRAVAS DE SEGURANÇA BÁSICAS
        if not carrinho or len(carrinho) == 0:
            raise ValueError("Bloqueio de Segurança: A operação não contém produtos.")
        if valor_final < 0:
            raise ValueError("Bloqueio de Segurança: O valor total da operação não pode ser negativo.")

        # 🚀 RESOLUÇÃO DO CONSUMIDOR PADRÃO E INDICANTE
        cliente_nome = dados.get('cliente', '').strip()
        cliente_valido = cliente_nome if cliente_nome != "" else None

        indicante_nome = dados.get('indicante', '').strip()
        indicante_valido = indicante_nome if indicante_nome != "" else None

        # 🚀 CÁLCULO DA COMISSÃO DO VENDEDOR (Baseado na % cadastrada para ele)
        comissao_em_reais = 0.00
        if nome_vendedor and status_venda != 'ORCAMENTO':
            usuario = Usuarios.objects.filter(login=nome_vendedor).first()
            if usuario and usuario.comissao > 0:
                # Calcula a comissão com base no valor final pago pelo cliente (já com descontos aplicados)
                comissao_em_reais = valor_final * (float(usuario.comissao) / 100.0)

        # 🚀 TRATAMENTO DOS IDS VIRTUAIS DO TINTOMÉTRICO E PRESERVAÇÃO DO NOME EDITADO
        carrinho_tratado = []
        for item in carrinho:
            qtd = int(item.get('qtd', 0))
            if qtd <= 0:
                raise ValueError(f"O produto '{item.get('nome')}' está com quantidade inválida ({qtd}). A quantidade deve ser maior que zero.")
            
            preco_desconto = float(item.get('preco_desconto', 0))
            if preco_desconto < 0:
                raise ValueError(f"O produto '{item.get('nome')}' está com preço negativo. Valores negativos não são permitidos.")

            item_id_original = str(item.get('id', ''))
            
            # GARANTIA: Salva explicitamente o nome atual que veio do Front-end (modal de edição)
            nome_produto = item.get('nome', 'PRODUTO NÃO IDENTIFICADO')
            item['nome'] = nome_produto
            
            # Converte produtos Tintométricos gerados dinamicamente para o ID Base Real do Banco
            if item_id_original.startswith('TINTA-') or not item_id_original.isdigit():
                cod_interno_real = item.get('id_real_estoque')
                if cod_interno_real:
                    produto_banco = Produtos.objects.filter(cod_interno=cod_interno_real).first()
                    if produto_banco:
                        item['id'] = produto_banco.id 

            carrinho_tratado.append(item)

        pagamentos_lista = dados.get('pagamentos', [])
        troco_valor = float(dados.get('troco', 0))

        # 📦 INÍCIO DA TRANSAÇÃO ATÓMICA NO BANCO DE DADOS
        with transaction.atomic():
            
            # Regra Fiscal: Sem cliente = Sem Nota
            status_fiscal_definido = 'AGUARDANDO_EMISSAO' if cliente_valido else 'SEM_NOTA'
            
            # 🚀 RESGATA A TAXA (Que veio do Front-End)
            taxa_maquininha = float(dados.get('valor_taxa_maquininha', 0.00))

            # 1. Cria o registo físico da venda
            venda = Vendas.objects.create(
                valor_total=valor_final,
                valor_desconto=float(dados.get('desconto_comum', dados.get('desconto', 0))), 
                desconto_comum=float(dados.get('desconto_comum', 0)), 
                desconto_pontos=float(dados.get('desconto_pontos', 0)), 
                vendedor=nome_vendedor,
                valor_comissao=comissao_em_reais, 
                valor_taxa_maquininha=taxa_maquininha, 
                cliente=cliente_valido,
                indicante=indicante_valido,
                status=status_venda,
                cupom_texto=json.dumps(carrinho_tratado), # Salva o array de produtos com o nome editado retido
                troco=troco_valor,
                pagamentos_texto=json.dumps(pagamentos_lista),
                status_fiscal=status_fiscal_definido
            )

            # Se for orçamento, aborta o resto para não baixar estoque
            if status_venda == 'ORCAMENTO':
                return venda.id

            # 2. Baixa Automática no Estoque (Segura e Atómica via DB Engine F())
            for item in carrinho_tratado:
                p_id = item.get('id') or item.get('produto_id')
                p_qtd = int(item.get('qtd', 0))
                cod_barras = str(item.get('cod_barras', ''))

                if p_id and p_qtd > 0:
                    if 'TINTO' in str(p_id) or cod_barras == 'TINTOMETRICO':
                        continue
                    
                    try:
                        produto = Produtos.objects.filter(id=p_id).first()
                        if produto:
                            produto.estoque_atual = F('estoque_atual') - p_qtd
                            produto.save()
                    except Exception as e:
                        print(f"Erro ao baixar estoque do produto {p_id}: {e}")
            
            # 3. Atualização de Fidelidade do Cliente
            if cliente_valido:
                cliente_obj = Clientes.objects.filter(nome=cliente_valido).first()
                if cliente_obj:
                    if pontos_resgatados > 0:
                        cliente_obj.pontos = max(0, getattr(cliente_obj, 'pontos', 0) - pontos_resgatados)

                    config_cli = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()
                    if config_cli:
                        novos_pontos = int(float(valor_final) * config_cli.pontos_por_real)
                        cliente_obj.pontos = getattr(cliente_obj, 'pontos', 0) + novos_pontos
                        cliente_obj.save()

            # 4. Atualização de Fidelidade do Pintor Indicante
            if indicante_valido and indicante_valido != cliente_valido:
                pintor_obj = Clientes.objects.filter(nome=indicante_valido, tipo__icontains='PINTOR').first()
                if pintor_obj:
                    config_pin = ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()
                    if config_pin:
                        pontos_indicacao = int(float(valor_final) * config_pin.pontos_por_real)
                        pintor_obj.pontos = getattr(pintor_obj, 'pontos', 0) + pontos_indicacao
                        pintor_obj.save()

            # Retorna o ID final gerado
            return venda.id
        

    @staticmethod
    def estornar_fidelidade_e_estoque(venda):
        carrinho = json.loads(venda.cupom_texto) if venda.cupom_texto else []
        for item in carrinho:
            p_id = item.get('id') or item.get('produto_id')
            p_qtd = int(item.get('qtd', 0))
            if p_id and p_qtd > 0 and not str(p_id).startswith('TINTO'):
                try:
                    produto = Produtos.objects.filter(id=p_id).first()
                    if produto:
                        produto.estoque_atual = F('estoque_atual') + p_qtd
                        produto.save()
                except: pass

        pagamentos = json.loads(venda.pagamentos_texto) if venda.pagamentos_texto else []
        valor_pago_em_pontos = sum([float(p.get('valor', 0)) for p in pagamentos if p.get('metodo') == 'PONTOS'])
        valor_base_pontos = max(0, float(venda.valor_total) - valor_pago_em_pontos)

        if venda.cliente_link:
            config_cli = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()
            if config_cli:
                pontos_devolvidos = 0.00
                if valor_pago_em_pontos > 0 and config_cli.valor_resgate_reais and config_cli.pontos_necessarios_resgate:
                    fator = float(config_cli.pontos_necessarios_resgate) / float(config_cli.valor_resgate_reais)
                    pontos_devolvidos = round(valor_pago_em_pontos * fator, 2)
                
                pontos_removidos = 0.00
                if config_cli.pontos_por_real:
                    pontos_removidos = round(valor_base_pontos * float(config_cli.pontos_por_real), 2)

                saldo_atual = float(venda.cliente_link.pontos) if venda.cliente_link.pontos else 0.00
                venda.cliente_link.pontos = round(max(0.00, saldo_atual + pontos_devolvidos - pontos_removidos), 2)
                venda.cliente_link.save(update_fields=['pontos'])

        if venda.indicante_link and venda.indicante_link != venda.cliente_link:
            config_pin = ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()
            if config_pin and config_pin.pontos_por_real:
                pontos_removidos_pin = round(valor_base_pontos * float(config_pin.pontos_por_real), 2)
                saldo_atual_pin = float(venda.indicante_link.pontos) if venda.indicante_link.pontos else 0.00
                venda.indicante_link.pontos = round(max(0.00, saldo_atual_pin - pontos_removidos_pin), 2)
                venda.indicante_link.save(update_fields=['pontos'])
                