from inventario.models import Clientes, ConfiguracaoPontos

# ==========================================
# 🎁 REGRAS DE RESGATE DE PONTOS
# ==========================================

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
