from django.db import transaction
from inventario.models import Clientes, Produtos, Vendas, ConfiguracaoPontos

# ==========================================
# 🛒 PROCESSAMENTO DE VENDAS E ESTOQUE
# ==========================================

def processar_nova_venda(dados_venda, carrinho, status_venda, pontos_resgatados):
    with transaction.atomic():
        
        # 🔥 REGRA FISCAL DA JB TINTAS:
        # Se tem cliente na venda = Vai para a Fila do Gerente
        # Se não tem cliente (consumidor final rápido) = Fica 'SEM_NOTA'
        if dados_venda.get('cliente'):
            status_fiscal_definido = 'AGUARDANDO_EMISSAO'
        else:
            status_fiscal_definido = 'SEM_NOTA'

        # 1. Cria o registo físico da venda no banco de dados
        venda = Vendas.objects.create(
            valor_total=dados_venda['valor_total'],
            valor_desconto=dados_venda['valor_desconto'],
            vendedor=dados_venda['vendedor'],
            cliente=dados_venda['cliente'],
            indicante=dados_venda['indicante'],
            status=status_venda,
            cupom_texto=dados_venda['cupom_texto'],
            # Campos de pagamento
            troco=dados_venda.get('troco', 0.00),
            pagamentos_texto=dados_venda.get('pagamentos_texto', '[]'),
            # 🔥 INJETA O STATUS FISCAL AQUI
            status_fiscal=status_fiscal_definido
        )

        # Se for apenas um orçamento, não mexe no estoque nem nos pontos
        if status_venda == 'ORCAMENTO':
            return venda.id

        # 2. Faz a baixa automática dos produtos no estoque
        for item in carrinho:
            p_id = item.get('id') or item.get('produto_id')
            p_qtd = int(item.get('qtd', 0))
            cod_barras = str(item.get('cod_barras', ''))

            if p_id and p_qtd > 0:
                
                # BLINDAGEM DO TINTOMÉTRICO
                # Se o produto for uma tinta mista, nós NÃO tentamos dar baixa no estoque normal
                if 'TINTO' in str(p_id) or cod_barras == 'TINTOMETRICO':
                    continue

                # Se for um produto normal, tenta dar baixa com proteção extra
                try:
                    produto = Produtos.objects.select_for_update().filter(id=p_id).first()
                    if produto:
                        produto.estoque_atual -= p_qtd
                        produto.save()
                except ValueError:
                    pass
        
        # 3. Atualiza os pontos de fidelidade do cliente
        nome_cliente = dados_venda.get('cliente')
        if nome_cliente:
            cliente_obj = Clientes.objects.filter(nome=nome_cliente).first()
            if cliente_obj:
                # Deduz os pontos que ele usou como desconto
                if pontos_resgatados > 0:
                    cliente_obj.pontos = max(0, getattr(cliente_obj, 'pontos', 0) - pontos_resgatados)

                # Atribui novos pontos (Lembrando que na JB Tintas a regra foi mudada de divisor 50 para 25)
                config_cli = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()
                if config_cli:
                    novos_pontos = int(float(dados_venda['valor_total']) * config_cli.pontos_por_real)
                    cliente_obj.pontos = getattr(cliente_obj, 'pontos', 0) + novos_pontos

                cliente_obj.save()

        # 4. Atribui os pontos de indicação para o Pintor (se houver)
        nome_indicante = dados_venda.get('indicante')
        if nome_indicante and nome_indicante != nome_cliente:
            pintor_obj = Clientes.objects.filter(nome=nome_indicante, tipo__icontains='PINTOR').first()
            if pintor_obj:
                config_pin = ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()
                if config_pin:
                    pontos_indicacao = int(float(dados_venda['valor_total']) * config_pin.pontos_por_real)
                    pintor_obj.pontos = getattr(pintor_obj, 'pontos', 0) + pontos_indicacao
                    pintor_obj.save()

        return venda.id
    