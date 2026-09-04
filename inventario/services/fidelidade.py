from inventario.models import Clientes, ConfiguracaoPontos

# ==========================================
# 🎁 REGRAS DE RESGATE DE PONTOS
# ==========================================

def calcular_resgate_pontos(nome_cliente):
    if not nome_cliente:
        return {'pontos_totais': 0, 'pontos_utilizaveis': 0, 'valor_reais': 0.0, 'mensagem': 'Cliente não informado.'}

    cliente = Clientes.objects.filter(nome=nome_cliente).first()
    if not cliente or not cliente.pontos:
        return {'pontos_totais': 0, 'pontos_utilizaveis': 0, 'valor_reais': 0.0, 'mensagem': 'Cliente sem saldo.'}

    pontos = int(cliente.pontos)

    # 🚀 A MOEDA UNIVERSAL: A regra de resgate é sempre a do 'CLIENTE'
    config = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()

    # Prevenção contra divisão por zero se a loja não tiver configurado a regra
    if not config or not config.pontos_necessarios_resgate or float(config.pontos_necessarios_resgate) <= 0:
        return {'pontos_totais': pontos, 'pontos_utilizaveis': 0, 'valor_reais': 0.0, 'mensagem': 'Regra de conversão não configurada.'}

    taxa_resgate = float(config.pontos_necessarios_resgate)
    valor_moeda = float(config.valor_resgate_reais or 1.0)

    # 🚀 Matemática do Varejo (ex: (477 pontos / Fator 50) * R$ 1.00 = R$ 9,54)
    valor_em_reais = (pontos / taxa_resgate) * valor_moeda

    return {
        'pontos_totais': pontos,
        'pontos_utilizaveis': pontos,
        'valor_reais': round(valor_em_reais, 2),
        'mensagem': f'Disponível: R$ {valor_em_reais:.2f}'
    }
