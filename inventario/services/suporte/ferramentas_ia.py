from django.db.models import Q
from inventario.models import Produtos, Clientes, Vendas, LogSuporteIA


def consultar_estoque_produto(termo_busca: str) -> str:
    """
    Consulta o estoque atual, preço de venda, unidade e localização (sessão WMS)
    de um produto pelo nome, código interno ou código de barras.
    """
    termo = str(termo_busca or '').strip()
    if not termo:
        return "Informe o nome, código interno ou código de barras do produto."

    produtos = Produtos.objects.filter(
        Q(nome__icontains=termo) |
        Q(cod_interno__iexact=termo) |
        Q(cod_barras__iexact=termo)
    ).select_related('marca', 'sessao_estoque')[:6]

    if not produtos:
        return f"Nenhum produto encontrado no cadastro com o termo '{termo}'."

    linhas = [f"Resultados encontrados para '{termo}':"]
    for p in produtos:
        local = p.sessao_estoque.nome if p.sessao_estoque else "Sem corredor/sessão definida"
        marca = p.marca.nome if p.marca else "Sem marca"
        status_txt = "" if p.status == 'ATIVO' else " [INATIVO]"
        transito = f" (+ {p.qtd_em_transito} em trânsito)" if p.qtd_em_transito > 0 else ""
        linhas.append(
            f"- Cód. {p.cod_interno} | {p.nome}{status_txt} ({marca}) -> "
            f"Estoque: {p.estoque_atual} {p.unidade}{transito} | "
            f"Preço: R$ {p.preco_venda:.2f} | Local: {local}"
        )

    return "\n".join(linhas)


def consultar_pontos_cliente(nome_cliente: str) -> str:
    """
    Consulta o saldo de pontos de fidelidade e o valor equivalente em desconto (100 pontos = R$ 1,00)
    de um cliente ou pintor pelo nome.
    """
    termo = str(nome_cliente or '').strip()
    if not termo:
        return "Informe o nome do cliente para consultar os pontos."

    clientes = Clientes.objects.filter(nome__icontains=termo)[:5]
    if not clientes:
        return f"Nenhum cliente encontrado com o nome '{termo}'."

    linhas = [f"Clientes encontrados para '{termo}':"]
    for c in clientes:
        reais_desconto = c.pontos / 100.0
        linhas.append(
            f"- {c.nome} ({c.tipo}) -> Saldo: {c.pontos} pontos "
            f"(equivale a R$ {reais_desconto:.2f} de desconto no PDV)"
        )

    return "\n".join(linhas)


def diagnosticar_nota_fiscal(numero_venda: str = "") -> str:
    """
    Diagnostica o status fiscal e o motivo exato de rejeição da SEFAZ de uma venda específica
    (pelo ID da venda) ou lista as últimas vendas com erro/rejeição fiscal se nenhum número for informado.
    """
    num_limpo = ''.join(filter(str.isdigit, str(numero_venda or '')))

    if num_limpo:
        venda = Vendas.objects.select_related('cliente_link').filter(id=int(num_limpo)).first()
        if not venda:
            return f"Venda #{num_limpo} não encontrada no sistema."

        cliente_nome = venda.cliente_link.nome if venda.cliente_link else (venda.cliente or "Consumidor Padrão")
        cep_info = (venda.cliente_link.cep or "SEM CEP") if venda.cliente_link else "Cliente não vinculado"
        ibge_info = (venda.cliente_link.codigo_ibge or "SEM IBGE") if venda.cliente_link else "N/A"
        doc_info = "Cadastrado" if (venda.cliente_link and (venda.cliente_link.cpf or venda.cliente_link.cnpj)) else "Sem CPF/CNPJ"

        return (
            f"Diagnóstico da Venda #{venda.id}:\n"
            f"- Valor: R$ {venda.valor_total:.2f} | Status Venda: {venda.status}\n"
            f"- Status Fiscal: {venda.status_fiscal} | Modelo: {venda.modelo_fiscal or 'Não definido'}\n"
            f"- Número Nota: {venda.numero_nota or 'Não gerada'}\n"
            f"- Motivo do Erro SEFAZ: {venda.motivo_erro or 'Nenhum erro registrado'}\n"
            f"- Cliente: {cliente_nome} ({doc_info} | CEP: {cep_info} | Cód. IBGE: {ibge_info})"
        )

    # Se não informou número, busca as últimas 5 vendas com erro fiscal
    vendas_erro = Vendas.objects.filter(
        Q(status_fiscal__icontains='ERRO') | Q(status_fiscal__icontains='REJEI')
    ).order_by('-id')[:5]

    if not vendas_erro:
        return "Ótima notícia: não há nenhuma venda com erro ou rejeição fiscal recente no sistema!"

    linhas = ["Últimas vendas com erro/rejeição fiscal:"]
    for v in vendas_erro:
        linhas.append(
            f"- Venda #{v.id} (R$ {v.valor_total:.2f}) | Status: {v.status_fiscal} | "
            f"Erro: {v.motivo_erro or 'Sem detalhes'}"
        )
    return "\n".join(linhas)


def listar_duvidas_nao_resolvidas() -> str:
    """
    Lista as últimas perguntas feitas no chat de suporte que receberam avaliação negativa (👎)
    para que o gerente ou desenvolvedor possa melhorar o manual do sistema.
    """
    logs = LogSuporteIA.objects.filter(feedback='NAO_AJUDOU')[:10]
    if not logs:
        return "Nenhuma dúvida com avaliação negativa (👎) registrada até o momento!"

    linhas = ["Últimas dúvidas marcadas como 'Não Ajudou (👎)':"]
    for log in logs:
        data_fmt = log.data_hora.strftime('%d/%m %H:%M')
        linhas.append(
            f"- [{data_fmt}] Usuário: {log.usuario or 'Anônimo'} (Tela: {log.rota_origem or '/'}) -> "
            f"Pergunta: \"{log.pergunta}\""
        )
    return "\n".join(linhas)
