// ==========================================
// 🧾 MÓDULO DE IMPRESSÃO DE CUPONS
// Ficheiro unificado para: Cupom Bobina 80mm e Recibo Folha A4
// ==========================================

document.addEventListener("DOMContentLoaded", function() {

    // ----------------------------------------------------
    // LÓGICA 1: CUPOM BOBINA TÉRMICA (80mm)
    // ----------------------------------------------------
    const listaItensCupom = document.getElementById('lista-itens');
    
    if (listaItensCupom && window.CUPOM_ITENS_JSON) {
        try {
            const itens = JSON.parse(window.CUPOM_ITENS_JSON);
            let htmlItens = '';
            let subtotal = 0;
            let descontoTotal = 0;
            let totalFinal = 0;

            itens.forEach(item => {
                let qtd = parseFloat(item.qtd) || 1;
                let vBruto = parseFloat(item.preco_venda || item.preco || 0);
                let vDesc = parseFloat(item.preco_desconto || vBruto);
                
                let totalItem = qtd * vDesc;
                let totalBrutoItem = qtd * vBruto;
                let itemDescontoTotal = totalBrutoItem - totalItem;

                subtotal += totalBrutoItem;
                totalFinal += totalItem;

                htmlItens += `
                    <div style="margin-bottom: 2px;">
                        <div class="text-left">${item.nome}</div>
                        <div style="display: flex; justify-content: space-between; margin-top: 2px;">
                            <span style="width: 30%; text-align: left;">&nbsp;&nbsp;${qtd}x</span>
                            <span style="width: 40%; text-align: center;">${vBruto.toFixed(2).replace('.', ',')}</span>
                            <span style="width: 30%; text-align: right;">${totalItem.toFixed(2).replace('.', ',')}</span>
                        </div>
                        ${itemDescontoTotal > 0 ? `<div style="text-align: left; margin-top: 2px;">ITEM DESC:${itemDescontoTotal.toFixed(2).replace('.', ',')}</div>` : ''}
                    </div>
                    <div class="divider"></div>
                `;
            });

            descontoTotal = subtotal - totalFinal;

            listaItensCupom.innerHTML = htmlItens;
            document.getElementById('cupom-subtotal').innerText = subtotal.toFixed(2).replace('.', ',');
            document.getElementById('cupom-desconto').innerText = descontoTotal.toFixed(2).replace('.', ',');
            document.getElementById('cupom-total').innerText = totalFinal.toFixed(2).replace('.', ',');

        } catch (e) {
            listaItensCupom.innerHTML = '<div class="text-center">Erro ao carregar lista de itens.</div>';
            console.error("Erro ao processar itens do cupom 80mm:", e);
        }

        // Processamento dos métodos de pagamento para Bobina 80mm
        try {
            const pagamentos = JSON.parse(window.CUPOM_PAGAMENTOS_JSON || "[]");
            let areaPagamentos = document.getElementById('area-pagamentos');
            
            if (pagamentos && pagamentos.length > 0) {
                let pagamentosFormatados = pagamentos.map(p => {
                    let nome = p.metodoNome || p.metodo || "NÃO INFORMADA";
                    return `${nome.toUpperCase()} (R$ ${parseFloat(p.valor).toFixed(2).replace('.', ',')})`;
                }).join('<br>');
                
                areaPagamentos.innerHTML = `FORMA DE PAGAMENTO:<br>${pagamentosFormatados}`;
            } else {
                areaPagamentos.innerHTML = `FORMA DE PAGAMENTO: NÃO INFORMADA`;
            }
        } catch (e) {
            document.getElementById('area-pagamentos').innerHTML = `FORMA DE PAGAMENTO: NÃO INFORMADA`;
            console.error("Erro ao processar pagamentos do cupom 80mm:", e);
        }
    }


    // ----------------------------------------------------
    // LÓGICA 2: RECIBO FOLHA A4 (PDF)
    // ----------------------------------------------------
    const tabelaItensA4 = document.getElementById('tabela-itens');
    
    if (tabelaItensA4) {
        let rows = tabelaItensA4.querySelectorAll("tbody tr");
        let subtotalBruto = 0;

        // 1. Calcula os valores linha a linha
        rows.forEach(row => {
            let rowQtdEl = row.querySelector(".row-qtd");
            let rowPrecoEl = row.querySelector(".row-preco");
            
            if (rowQtdEl && rowPrecoEl) {
                let qtdText = rowQtdEl.innerText.trim();
                let precoText = rowPrecoEl.innerText.replace('R$', '').replace(/\./g, '').replace(',', '.').trim();
                
                let qtd = parseFloat(qtdText) || 1;
                let preco = parseFloat(precoText) || 0;
                
                // O valor bruto real da linha (Preço x Quantidade)
                let valorBrutoLinha = qtd * preco;
                subtotalBruto += valorBrutoLinha;

                // Verifica se a coluna "Valor Total" veio vazia do sistema
                let totalSpan = row.querySelector(".calc-linha");
                if (totalSpan) {
                    let totalValue = parseFloat(totalSpan.innerText.replace(/\./g, '').replace(',', '.').trim());
                    
                    // Se estiver vazia ou for NaN, injetamos o cálculo matemático correto
                    if (isNaN(totalValue) || totalSpan.innerText.trim() === "") {
                        totalSpan.innerText = valorBrutoLinha.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    }
                }
            }
        });

        // 2. Calcula o Subtotal e o Desconto Global
        let totalPagarSpan = document.getElementById("calc-total");
        if (totalPagarSpan && subtotalBruto > 0) {
            let totalPagarText = totalPagarSpan.innerText.replace('R$', '').replace(/\./g, '').replace(',', '.').trim();
            let totalPagar = parseFloat(totalPagarText) || 0;

            // Atualiza o Subtotal Bruto
            let calcSubtotalEl = document.getElementById("calc-subtotal");
            if(calcSubtotalEl) {
                calcSubtotalEl.innerText = "R$ " + subtotalBruto.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            }
            
            // Calcula a diferença real do desconto (Subtotal Bruto - Total Pago)
            let desconto = subtotalBruto - totalPagar;
            if (desconto < 0) desconto = 0; // Evita descontos negativos
            
            // Atualiza o campo de Desconto visualmente
            let calcDescontoEl = document.getElementById("calc-desconto");
            if(calcDescontoEl) {
                calcDescontoEl.innerText = "- R$ " + desconto.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            }
        }
    }
});
