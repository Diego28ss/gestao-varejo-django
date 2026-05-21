from django.db import transaction
from .models import Clientes, Produtos, Vendas, ConfiguracaoPontos
import json

def calcular_resgate_pontos(nome_cliente):
    if not nome_cliente:
        return {'pontos': 0, 'valor_desconto': 0.0, 'mensagem': 'Cliente não informado.'}

    cliente = Clientes.objects.filter(nome=nome_cliente).first()
    if not cliente:
        return {'pontos': 0, 'valor_desconto': 0.0, 'mensagem': 'Cliente não encontrado.'}

    tipo_usuario = 'PINTOR' if 'PINTOR' in cliente.tipo.upper() else 'CLIENTE'
    config = ConfiguracaoPontos.objects.filter(tipo_usuario=tipo_usuario).first()

    if not config:
        return {
            'pontos': cliente.pontos,
            'valor_desconto': 0.0,
            'mensagem': 'Regra de fidelidade não configurada para este tipo de cliente.'
        }

    if cliente.pontos >= config.pontos_necessarios_resgate:
        multiplicador = cliente.pontos // config.pontos_necessarios_resgate
        pontos_a_resgatar = multiplicador * config.pontos_necessarios_resgate
        valor_desconto = multiplicador * float(config.valor_resgate_reais)
        return {
            'pontos': cliente.pontos,
            'pontos_a_resgatar': pontos_a_resgatar,
            'valor_desconto': valor_desconto,
            'mensagem': f'Disponível para resgate: {pontos_a_resgatar} pontos por R$ {valor_desconto:.2f}'
        }

    return {
        'pontos': cliente.pontos,
        'pontos_a_resgatar': 0,
        'valor_desconto': 0.0,
        'mensagem': f'Pontos insuficientes para resgate (mínimo {config.pontos_necessarios_resgate} pontos).'
    }


def processar_nova_venda(dados_venda, carrinho, status_venda, pontos_resgatados):
    with transaction.atomic():
        # 1. Cria o registo físico da venda no banco de dados
        venda = Vendas.objects.create(
            valor_total=dados_venda['valor_total'],
            valor_desconto=dados_venda['valor_desconto'],
            vendedor=dados_venda['vendedor'],
            cliente=dados_venda['cliente'],
            indicante=dados_venda['indicante'],
            status=status_venda,
            cupom_texto=dados_venda['cupom_texto']
        )

        # Se for apenas um orçamento, não mexe no estoque nem nos pontos
        if status_venda == 'ORCAMENTO':
            return venda.id

        # 2. Faz a baixa automática dos produtos no estoque
        for item in carrinho:
            p_id = item.get('id') or item.get('produto_id')
            # 🔥 CORREÇÃO: O HTML envia 'qtd', não 'quantidade'!
            p_qtd = int(item.get('qtd', 0))

            if p_id and p_qtd > 0:
                produto = Produtos.objects.select_for_update().filter(id=p_id).first()
                if produto:
                    produto.estoque_atual -= p_qtd
                    produto.save()

        # 3. Atualiza os pontos de fidelidade do cliente
        nome_cliente = dados_venda.get('cliente')
        if nome_cliente:
            cliente_obj = Clientes.objects.filter(nome=nome_cliente).first()
            if cliente_obj:
                # Deduz os pontos que ele usou como desconto
                if pontos_resgatados > 0:
                    cliente_obj.pontos = max(0, cliente_obj.pontos - pontos_resgatados)

                # Atribui novos pontos baseados no valor da compra atual
                config_cli = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()
                if config_cli:
                    novos_pontos = int(float(dados_venda['valor_total']) * config_cli.pontos_por_real)
                    cliente_obj.pontos += novos_pontos

                cliente_obj.save()

        # 4. Atribui os pontos de indicação para o Pintor (se houver)
        nome_indicante = dados_venda.get('indicante')
        if nome_indicante and nome_indicante != nome_cliente:
            pintor_obj = Clientes.objects.filter(nome=nome_indicante, tipo__icontains='PINTOR').first()
            if pintor_obj:
                config_pin = ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()
                if config_pin:
                    pontos_indicacao = int(float(dados_venda['valor_total']) * config_pin.pontos_por_real)
                    pintor_obj.pontos += pontos_indicacao
                    pintor_obj.save()

        return venda.id