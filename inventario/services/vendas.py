from django.db import transaction
from django.db.models import F
from inventario.models import Clientes, Produtos, Vendas, ConfiguracaoPontos

# ==========================================
# 🛒 PROCESSAMENTO DE VENDAS E ESTOQUE
# ==========================================

def processar_nova_venda(dados_venda, carrinho, status_venda, pontos_resgatados):
    """
    Processa a venda, realiza a baixa do estoque (garantindo precisão matemática)
    e gerencia a fidelidade do cliente e do pintor.
    """
    with transaction.atomic():
        
        # 🔥 REGRA FISCAL DA JB TINTAS:
        # Se tem cliente na venda = Vai para a Fila do Gerente para emissão manual
        # Se não tem cliente (consumidor final rápido) = Marca como SEM_NOTA
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
            # Grava a finalidade fiscal inicial
            status_fiscal=status_fiscal_definido
        )

        # Se for apenas um orçamento, encerra o processo sem afetar estoque ou pontos
        if status_venda == 'ORCAMENTO':
            return venda.id

        # 2. Faz a baixa automática dos produtos no estoque
        for item in carrinho:
            p_id = item.get('id') or item.get('produto_id')
            p_qtd = int(item.get('qtd', 0))
            cod_barras = str(item.get('cod_barras', ''))

            if p_id and p_qtd > 0:
                
                # Proteção para produtos tintométricos (não controlam estoque físico unitário)
                if 'TINTO' in str(p_id) or cod_barras == 'TINTOMETRICO':
                    continue

                # 🛠️ CORREÇÃO DE SEGURANÇA:
                # Usamos F() para realizar a subtração diretamente no banco de dados.
                # Isso resolve o problema de estoque não atualizar em casos negativos.
                try:
                    produto = Produtos.objects.filter(id=p_id).first()
                    if produto:
                        # O F('estoque_atual') - p_qtd garante que a subtração seja atómica
                        produto.estoque_atual = F('estoque_atual') - p_qtd
                        produto.save()
                except Exception as e:
                    print(f"Erro ao baixar estoque do produto {p_id}: {e}")
        
        # 3. Atualiza os pontos de fidelidade do cliente (Regra: Divisor 25)
        nome_cliente = dados_venda.get('cliente')
        if nome_cliente:
            cliente_obj = Clientes.objects.filter(nome=nome_cliente).first()
            if cliente_obj:
                # Deduz os pontos usados no resgate
                if pontos_resgatados > 0:
                    cliente_obj.pontos = max(0, getattr(cliente_obj, 'pontos', 0) - pontos_resgatados)

                # Atribui novos pontos baseados no divisor 25
                config_cli = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()
                if config_cli:
                    novos_pontos = int(float(dados_venda['valor_total']) * config_cli.pontos_por_real)
                    cliente_obj.pontos = getattr(cliente_obj, 'pontos', 0) + novos_pontos

                cliente_obj.save()

        # 4. Atribui pontos de indicação para o Pintor (se houver)
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
    