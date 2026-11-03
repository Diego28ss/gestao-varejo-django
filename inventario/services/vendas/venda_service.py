import json
from django.db import transaction
from django.db.models import F
from inventario.models import Clientes, Produtos, Vendas, ConfiguracaoPontos, Usuarios

class VendaService:

    @staticmethod
    def registrar_checkout(dados):
        status_venda = dados.get('status', 'VENDA')
        carrinho = dados.get('carrinho', [])
        valor_final = float(dados.get('valor_final', 0))
        nome_vendedor = dados.get('vendedor')
        pedido_aberto_id = dados.get('pedido_aberto_id')
        
        # 🚀 NOVOS CAMPOS FATIADOS RECEBIDOS DO JS
        desconto_total_legado = float(dados.get('desconto', 0))
        desconto_pontos = float(dados.get('desconto_pontos', 0))
        desconto_comum = float(dados.get('desconto_comum', 0))

        if not carrinho or len(carrinho) == 0:
            raise ValueError("A operação não contém produtos.")

        cliente_id = dados.get('cliente_id')
        cliente_nome = dados.get('cliente', '').strip()
        cliente_obj = Clientes.objects.filter(id=cliente_id).first() if cliente_id else Clientes.objects.filter(nome=cliente_nome).first()
        cliente_valido = cliente_obj.nome if cliente_obj else (cliente_nome if cliente_nome != "" else None)

        indicante_id = dados.get('indicante_id')
        indicante_nome = dados.get('indicante', '').strip()
        indicante_obj = Clientes.objects.filter(id=indicante_id).first() if indicante_id else Clientes.objects.filter(nome=indicante_nome).first()
        indicante_valido = indicante_obj.nome if indicante_obj else (indicante_nome if indicante_nome != "" else None)

        comissao_em_reais = 0.00
        percentual_comissao = 0.00
        if nome_vendedor and status_venda not in ['ORCAMENTO', 'ABERTO']:
            usuario = Usuarios.objects.filter(login=nome_vendedor).first()
            if usuario and usuario.comissao > 0:
                percentual_comissao = float(usuario.comissao)
                comissao_em_reais = valor_final * (percentual_comissao / 100.0)

        carrinho_tratado = []
        for item in carrinho:
            qtd = int(item.get('qtd', 0))
            if qtd <= 0: raise ValueError("Quantidade inválida.")
            
            item_id_original = str(item.get('id', ''))
            if item_id_original.startswith('TINTA-') or not item_id_original.isdigit():
                cod_interno_real = item.get('id_real_estoque')
                if cod_interno_real:
                    produto_banco = Produtos.objects.filter(cod_interno=cod_interno_real).first()
                    if produto_banco: item['id'] = produto_banco.id  
            carrinho_tratado.append(item)

        pagamentos_lista = dados.get('pagamentos', [])
        troco_valor = float(dados.get('troco', 0))

        valor_pago_em_pontos = sum([float(p.get('valor', 0)) for p in pagamentos_lista if p.get('metodo') == 'PONTOS'])
        valor_base_pontos = max(0, valor_final - valor_pago_em_pontos)

        with transaction.atomic():
            status_fiscal_definido = 'AGUARDANDO_EMISSAO' if cliente_valido else 'SEM_NOTA'

            venda = Vendas.objects.filter(id=pedido_aberto_id).first() if pedido_aberto_id else None
            if venda:
                venda.valor_total = valor_final
                venda.valor_desconto = desconto_total_legado
                venda.desconto_comum = desconto_comum
                venda.desconto_pontos = desconto_pontos
                venda.percentual_comissao = percentual_comissao
                
                venda.vendedor = nome_vendedor
                venda.valor_comissao = comissao_em_reais
                venda.cliente = cliente_valido
                venda.cliente_link = cliente_obj
                venda.indicante = indicante_valido
                venda.indicante_link = indicante_obj
                venda.status = status_venda
                venda.cupom_texto = json.dumps(carrinho_tratado)
                venda.troco = troco_valor
                venda.pagamentos_texto = json.dumps(pagamentos_lista)
                venda.status_fiscal = status_fiscal_definido
                if 'observacoes' in dados and hasattr(venda, 'observacoes'):
                    venda.observacoes = dados['observacoes']
                venda.save()
            else:
                venda = Vendas.objects.create(
                    valor_total=valor_final, 
                    valor_desconto=desconto_total_legado,
                    desconto_comum=desconto_comum,
                    desconto_pontos=desconto_pontos,
                    percentual_comissao=percentual_comissao,
                    vendedor=nome_vendedor, 
                    valor_comissao=comissao_em_reais,
                    cliente=cliente_valido, 
                    cliente_link=cliente_obj, 
                    indicante=indicante_valido, 
                    indicante_link=indicante_obj,
                    status=status_venda, 
                    cupom_texto=json.dumps(carrinho_tratado),
                    troco=troco_valor, 
                    pagamentos_texto=json.dumps(pagamentos_lista),
                    status_fiscal=status_fiscal_definido
                )
                if 'observacoes' in dados and hasattr(venda, 'observacoes'):
                    venda.observacoes = dados['observacoes']
                    venda.save(update_fields=['observacoes'])

            if status_venda in ['ORCAMENTO', 'ABERTO']:
                return venda.id

            for item in carrinho_tratado:
                p_id = item.get('id') or item.get('produto_id')
                p_qtd = int(item.get('qtd', 0))
                cod_barras = str(item.get('cod_barras', ''))

                if p_id and p_qtd > 0 and 'TINTO' not in str(p_id) and cod_barras != 'TINTOMETRICO':
                    try:
                        produto = Produtos.objects.filter(id=p_id).first()
                        if produto:
                            produto.estoque_atual = F('estoque_atual') - p_qtd
                            produto.save()
                    except: pass
            
            # 🚀 FIDELIDADE CLIENTE
            if cliente_obj:
                pontos_atuais = float(cliente_obj.pontos) if cliente_obj.pontos else 0.00
                config_cli = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()
                
                pontos_a_deduzir = 0.00
                novos_pontos = 0.00
                
                if config_cli:
                    if valor_pago_em_pontos > 0 and config_cli.valor_resgate_reais and config_cli.pontos_necessarios_resgate:
                        fator = float(config_cli.pontos_necessarios_resgate) / float(config_cli.valor_resgate_reais)
                        pontos_a_deduzir = round(valor_pago_em_pontos * fator, 2)
                    
                    if config_cli.pontos_por_real:
                        # Agora aceita cêntimos (ex: 120.99 geram 1.21 pontos)
                        novos_pontos = round(valor_base_pontos * float(config_cli.pontos_por_real), 2)
                
                cliente_obj.pontos = round(max(0.00, pontos_atuais - pontos_a_deduzir) + novos_pontos, 2)
                cliente_obj.save(update_fields=['pontos'])

            # 🚀 FIDELIDADE PINTOR
            if indicante_obj and indicante_obj != cliente_obj:
                pontos_atuais_pin = float(indicante_obj.pontos) if indicante_obj.pontos else 0.00
                config_pin = ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()
                if config_pin and config_pin.pontos_por_real:
                    novos_pontos_pin = round(valor_base_pontos * float(config_pin.pontos_por_real), 2)
                    indicante_obj.pontos = round(pontos_atuais_pin + novos_pontos_pin, 2)
                    indicante_obj.save(update_fields=['pontos'])

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
                