import json
from django.db import transaction
from django.db.models import F
from inventario.models import Clientes, Produtos, Vendas, ConfiguracaoPontos

class VendaService:
    """
    Camada de Serviço responsável pela regra de negócio do Checkout do PDV.
    Processa a venda, validações de segurança, baixa atómica no estoque e gestão do programa de fidelidade.
    """

    @staticmethod
    def registrar_checkout(dados):
        status_venda = dados.get('status', 'VENDA')
        pontos_resgatados = int(dados.get('pontos_resgatados', 0))
        carrinho = dados.get('carrinho', [])
        valor_final = float(dados.get('valor_final', 0))

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

        # 🚀 TRATAMENTO DOS IDS VIRTUAIS DO TINTOMÉTRICO E INTEGRIDADE DO CARRINHO
        carrinho_tratado = []
        for item in carrinho:
            qtd = int(item.get('qtd', 0))
            if qtd <= 0:
                raise ValueError(f"O produto '{item.get('nome')}' está com quantidade inválida ({qtd}). A quantidade deve ser maior que zero.")
            
            preco_desconto = float(item.get('preco_desconto', 0))
            if preco_desconto < 0:
                raise ValueError(f"O produto '{item.get('nome')}' está com preço negativo. Valores negativos não são permitidos.")

            item_id_original = str(item.get('id', ''))
            
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

            # 1. Cria o registo físico da venda
            venda = Vendas.objects.create(
                valor_total=valor_final,
                valor_desconto=float(dados.get('desconto', 0)),
                vendedor=dados.get('vendedor'),
                cliente=cliente_valido,
                indicante=indicante_valido,
                status=status_venda,
                cupom_texto=json.dumps(carrinho_tratado),
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

            return venda.id
        