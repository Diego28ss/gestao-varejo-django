import json
from django.db import transaction
from .models import Produtos, Clientes, ConfiguracaoPontos
from .forms import VendaForm


def calcular_resgate_pontos(nome_cliente):
    """Calcula os pontos utilizáveis e o valor em reais para um cliente."""
    if not nome_cliente:
        return {'pontos_totais': 0, 'pontos_utilizaveis': 0, 'valor_reais': 0.0}

    cliente = Clientes.objects.filter(nome=nome_cliente).first()
    if not cliente or cliente.pontos <= 0:
        return {'pontos_totais': 0, 'pontos_utilizaveis': 0, 'valor_reais': 0.0}

    # Puxa a regra definida pelo gerente
    tipo_regra = 'PINTOR' if 'PINTOR' in cliente.tipo else 'CLIENTE'
    conf = ConfiguracaoPontos.objects.filter(tipo_usuario=tipo_regra).first()

    if not conf or conf.pontos_necessarios_resgate <= 0:
        return {'pontos_totais': cliente.pontos, 'pontos_utilizaveis': 0, 'valor_reais': 0.0}

    # Faz a matemática de conversão
    blocos = cliente.pontos // conf.pontos_necessarios_resgate
    valor_em_reais = float(blocos * float(conf.valor_resgate_reais))
    pontos_utilizaveis = blocos * conf.pontos_necessarios_resgate

    return {
        'pontos_totais': cliente.pontos,
        'pontos_utilizaveis': pontos_utilizaveis,
        'valor_reais': valor_em_reais
    }


@transaction.atomic
def processar_nova_venda(dados_venda, carrinho, status_venda, pontos_resgatados):
    """Processa a venda, baixa estoque e movimenta os pontos de fidelidade."""
    form = VendaForm(dados_venda)

    if not form.is_valid():
        raise ValueError('Erro de validação nos dados da venda.')

    nova_venda = form.save()

    if status_venda == 'VENDA':
        # 1. Baixa de estoque
        for item in carrinho:
            prod = Produtos.objects.get(id=item['id'])
            prod.estoque_atual -= int(item['qtd'])
            prod.save()

        nome_cliente = dados_venda.get('cliente')
        nome_indicante = dados_venda.get('indicante')

        # 2. DÉBITO - Abater pontos utilizados como desconto
        if pontos_resgatados > 0 and nome_cliente:
            cliente_obj = Clientes.objects.filter(nome=nome_cliente).first()
            if cliente_obj and cliente_obj.pontos >= pontos_resgatados:
                cliente_obj.pontos -= pontos_resgatados
                cliente_obj.save()

        # 3. CRÉDITO - Acumular pontos da nova compra
        valor_final_compra = float(dados_venda.get('valor_total', 0))
        pontos_ganhos = int(valor_final_compra)

        if nome_cliente and nome_cliente.strip() != "":
            cliente_obj = Clientes.objects.filter(nome=nome_cliente).first()
            if cliente_obj:
                cliente_obj.pontos += pontos_ganhos
                cliente_obj.save()

        if nome_indicante and nome_indicante.strip() != "":
            indicante_obj = Clientes.objects.filter(nome=nome_indicante).first()
            if indicante_obj:
                indicante_obj.pontos += pontos_ganhos
                indicante_obj.save()

    return nova_venda.id