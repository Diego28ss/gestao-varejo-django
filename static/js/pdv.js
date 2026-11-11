let carrinho = JSON.parse(localStorage.getItem('carrinho')) || [];
let pagamentos = JSON.parse(localStorage.getItem('pagamentos')) || [];
let pointsToRedeem = 0;
let descontoManualAplicado = false;
let descontoGlobalAplicado = false;
window.DADOS_PONTOS_CLIENTE = null; // Memória de Fidelidade
window.CUSTO_TOTAL_MAQUININHA = 0.00; // 🚀 Memória da Maquininha

// 🚀 FASE 22: Cache de Regras de Parcelamento
let regrasParcelamentoCache = [];

// ==========================================
// 🚀 EVENTO DE FECHAMENTO DA ABA
// ==========================================
window.addEventListener('beforeunload', function () {
    if (window.PEDIDO_ABERTO_ID && !window.VENDA_FINALIZADA_ID && !window.PEDIDO_IMPORTADO_ID) {
        fetch(`/api/pdv/cancelar-aberto/${window.PEDIDO_ABERTO_ID}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN },
            keepalive: true
        });
    }
    localStorage.removeItem('carrinho');
    localStorage.removeItem('pagamentos');
});

// ==========================================
// 🚀 INICIALIZAÇÃO DA TELA
// ==========================================
window.onload = function () {
    if (window.PEDIDO_ABERTO_ID) {
        if (Array.isArray(window.PEDIDO_JSON_INJETADO) && window.PEDIDO_JSON_INJETADO.length > 0) {
            carrinho = window.PEDIDO_JSON_INJETADO;
            localStorage.setItem('carrinho', JSON.stringify(carrinho));
        } else if (Array.isArray(window.PEDIDO_JSON_INJETADO) && window.PEDIDO_JSON_INJETADO.length === 0) {
            carrinho = [];
            pagamentos = [];
            localStorage.removeItem('carrinho');
            localStorage.removeItem('pagamentos');
        }
    }

    let selectVend = document.getElementById('selectVendedor');
    if (selectVend && window.OPERADOR_ATUAL) {
        selectVend.value = window.OPERADOR_ATUAL;
        selectVend.disabled = true;
    }

    if (carrinho.length > 0) atualizarTela();
    iniciarAutoSave();

    // Configura o evento keyup no input de pagamento para filtrar
    let inputValPag = document.getElementById('inputValorPagamento');
    let selectMetodo = document.getElementById('selectMetodoPagamento');
    if (inputValPag && selectMetodo) {
        inputValPag.addEventListener('keyup', () => {
            if (selectMetodo.value === 'CARTAO_CREDITO') {
                filtrarParcelas(parseFloat(inputValPag.value) || 0);
            }
        });
    }
};

// ==========================================
// 🚀 FASE 22: LÓGICA DE PARCELAMENTO DINÂMICO
// ==========================================
window.verificarParcelamento = function () {
    let metodoSelect = document.getElementById('selectMetodoPagamento');
    let parcelasSelect = document.getElementById('selectParcelas');
    let valorInput = document.getElementById('inputValorPagamento');

    if (!metodoSelect || !parcelasSelect || !valorInput) return;

    let metodo = metodoSelect.value;
    let valorFalta = parseFloat(valorInput.value) || 0;

    if (metodo === 'CARTAO_CREDITO') {
        parcelasSelect.style.display = 'block'; // Mostra o campo de parcelas
        parcelasSelect.disabled = false;
        parcelasSelect.innerHTML = '<option value="1">Buscando regras...</option>';

        fetch(`/api/taxas-maquininha/?metodo=${metodo}`)
            .then(res => res.json())
            .then(data => {
                if (data.status === 'sucesso') {
                    regrasParcelamentoCache = data.regras;
                    filtrarParcelas(valorFalta);
                } else {
                    parcelasSelect.innerHTML = '<option value="1">1x (Erro ao buscar limites)</option>';
                }
            });
    } else {
        parcelasSelect.style.display = 'none'; // Esconde o campo de parcelas
        parcelasSelect.innerHTML = '<option value="1">1x (À Vista)</option>';
        parcelasSelect.disabled = true;
    }
};

function filtrarParcelas(valorDaFalta) {
    let parcelasSelect = document.getElementById('selectParcelas');
    if (!parcelasSelect) return;

    let html = '';
    let parcelasValidas = 0;

    regrasParcelamentoCache.forEach(r => {
        let liberado = true;

        // 🚀 REGRA SIMPLIFICADA: Se a parcela tem valor mínimo, verifica se a compra atinge o valor
        if (r.valor_minimo > 0 && valorDaFalta < r.valor_minimo) {
            liberado = false;
        }

        if (liberado) {
            let nomeParcela = r.parcelas === 1 ? '1x (À Vista)' : `${r.parcelas}x`;
            html += `<option value="${r.parcelas}">${nomeParcela}</option>`;
            parcelasValidas++;
        }
    });

    if (parcelasValidas === 0) {
        html = '<option value="1">1x (Abaixo do limite p/ parcelar)</option>';
    }
    parcelasSelect.innerHTML = html;
}

// ==========================================
// ⚙️ GESTÃO DO CARRINHO
// ==========================================
window.aoSelecionarProdutoBusca = function (botao) {
    let id = parseInt(botao.getAttribute('data-id'));
    let nome = botao.getAttribute('data-nome');
    let preco = parseFloat(botao.getAttribute('data-preco'));
    let custo = parseFloat(botao.getAttribute('data-custo'));
    let estoque = parseFloat(botao.getAttribute('data-estoque'));

    let item = carrinho.find(i => i.id === id);
    if (item) {
        item.qtd++;
    } else {
        carrinho.push({ id: id, nome: nome, preco: preco, preco_desconto: preco, custo: custo, estoque: estoque, qtd: 1 });
    }

    descontoGlobalAplicado = false;
    atualizarTela();
    document.getElementById('inputBuscaUniversal').focus();
};

window.mudarQtd = function (index, valor) {
    carrinho[index].qtd = parseInt(valor) || 1;
    descontoGlobalAplicado = false;
    atualizarTela();
};

window.mudarPrecoDesconto = function (index, valor) {
    let novoPreco = parseFloat(valor);
    let item = carrinho[index];
    if (novoPreco > item.preco || novoPreco < 0) {
        item.preco_desconto = item.preco;
    } else {
        item.preco_desconto = novoPreco || item.preco;
    }
    descontoGlobalAplicado = false;
    atualizarTela();
};

window.mudarPercDescontoItem = function (index, percStr) {
    let perc = parseFloat(percStr) || 0;
    let item = carrinho[index];
    if (perc < 0 || perc > 100) {
        item.preco_desconto = item.preco;
    } else if (perc === 0) {
        item.preco_desconto = item.preco;
    } else {
        item.preco_desconto = item.preco - (item.preco * (perc / 100));
    }
    descontoGlobalAplicado = false;
    atualizarTela();
};

window.removerItem = function (index) {
    carrinho.splice(index, 1);
    descontoGlobalAplicado = false;
    atualizarTela();
};

window.aplicarDescontoGlobalPorPorcentagem = function () {
    let perc = parseFloat(document.getElementById('inputDescontoPerc').value) || 0;
    if (perc < 0) {
        perc = 0;
        document.getElementById('inputDescontoPerc').value = '';
    }
    let totalItens = carrinho.reduce((s, i) => s + (i.preco_desconto * i.qtd), 0);
    let novoValorFinal = totalItens - (totalItens * (perc / 100));
    document.getElementById('inputValorFinal').value = novoValorFinal.toFixed(2);
    descontoGlobalAplicado = true;
    descontoManualAplicado = true;
    atualizarResumoCaixa();
};

window.aplicarDescontoGlobalPorValor = function () {
    let valorFinalInput = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    let totalItens = carrinho.reduce((s, i) => s + (i.preco_desconto * i.qtd), 0);
    if (totalItens > 0) {
        if (valorFinalInput > totalItens) {
            document.getElementById('inputDescontoPerc').value = '';
        } else {
            let perc = ((totalItens - valorFinalInput) / totalItens) * 100;
            document.getElementById('inputDescontoPerc').value = perc.toFixed(2);
        }
    }
    descontoGlobalAplicado = true;
    descontoManualAplicado = true;
    atualizarResumoCaixa();
};

window.abrirModalEditarNome = function (index) {
    document.getElementById('editItemIndex').value = index;
    let item = carrinho[index];
    document.getElementById('inputNomeCustomizado').value = item.nome_customizado ? item.nome_customizado : item.nome;

    let precoBase = item.preco_original_base || item.preco_venda || item.preco;
    document.getElementById('editItemPrecoOriginal').value = precoBase;
    document.getElementById('spanPrecoOriginalBase').innerText = precoBase.toFixed(2).replace('.', ',');

    let inputNovoPreco = document.getElementById('inputPrecoCustomizado');
    inputNovoPreco.value = item.preco.toFixed(2);
    inputNovoPreco.min = precoBase;

    new bootstrap.Modal(document.getElementById('modalEditarNomeProduto')).show();
};

window.salvarNomeCustomizado = function () {
    let index = document.getElementById('editItemIndex').value;
    let novoNome = document.getElementById('inputNomeCustomizado').value.trim().toUpperCase();
    let precoBase = parseFloat(document.getElementById('editItemPrecoOriginal').value);
    let novoPreco = parseFloat(document.getElementById('inputPrecoCustomizado').value);

    // 🚀 CORREÇÃO: Substituímos diretamente a chave 'nome' para garantir que ela vá para o banco e para o cupom
    if (novoNome !== "") {
        carrinho[index].nome = novoNome;
        carrinho[index].nome_customizado = novoNome; // Mantido por precaução
    }

    if (!isNaN(novoPreco)) {
        if (novoPreco < precoBase) {
            if (typeof window.mostrarAviso === 'function') window.mostrarAviso("O preço base só pode ser aumentado.", "erro");
            return;
        }
        carrinho[index].preco_original_base = precoBase;
        carrinho[index].preco = novoPreco;
        carrinho[index].preco_desconto = novoPreco;
    }

    bootstrap.Modal.getInstance(document.getElementById('modalEditarNomeProduto')).hide();
    atualizarTela();
};


function atualizarTela() {
    let chaveStorage = window.location.pathname.includes('/pdv/') ? 'carrinho' : 'carrinho_novo_pedido';
    localStorage.setItem(chaveStorage, JSON.stringify(carrinho));
    let html = '';
    let subtotalBruto = 0;
    let totalComDescontoItens = 0;

    let isImportado = typeof window.PEDIDO_IMPORTADO_ID !== 'undefined' && window.PEDIDO_IMPORTADO_ID !== null;
    let lockAttr = isImportado ? 'disabled' : '';
    let lockClass = isImportado ? 'd-none' : '';

    carrinho.forEach((item, index) => {
        if (item.preco === undefined) item.preco = item.preco_venda || 0;
        if (item.preco_desconto === undefined) item.preco_desconto = item.preco;

        let linhaBruto = item.preco * item.qtd;
        let linhaTotal = item.preco_desconto * item.qtd;
        subtotalBruto += linhaBruto;
        totalComDescontoItens += linhaTotal;

        let percDesc = 0;
        if (item.preco > 0 && item.preco_desconto < item.preco) {
            percDesc = ((item.preco - item.preco_desconto) / item.preco) * 100;
        }

        let nomeExibicao = item.nome; // Como agora atualizamos o 'item.nome' na hora de salvar, basta usá-lo diretamente. Se quiser ter redundância: item.nome_customizado || item.nome

        html += `<tr>
            <td class="align-middle">
                <button type="button" class="btn btn-sm text-primary p-0 ${lockClass}" title="Editar Nome e Preço Base" onclick="abrirModalEditarNome(${index})"><i class="bi bi-pencil-square fs-5"></i></button>
            </td>
            <td class="text-start fw-bold small" style="color: var(--azul-escuro);">${nomeExibicao}</td>
            <td class="align-middle text-center">
                <button type="button" class="btn btn-sm text-info p-0" title="Situação do Estoque e Ruptura" onclick="consultarSituacaoEstoque(${index})"><i class="bi bi-box-seam fs-5"></i></button>
            </td>
            <td><input type="number" class="form-control form-control-sm text-center fw-bold border-secondary" value="${item.qtd}" min="1" step="1" onchange="mudarQtd(${index}, this.value)" ${lockAttr}></td>
            <td class="text-muted align-middle small fw-bold">R$ ${item.preco.toFixed(2).replace('.', ',')}</td>
            <td><input type="number" class="form-control form-control-sm text-center fw-bold text-danger" style="border-color: #ffc107; background-color: #fffdf5;" value="${percDesc > 0 ? percDesc.toFixed(1) : ''}" step="0.1" min="0" onchange="mudarPercDescontoItem(${index}, this.value)" placeholder="0.0" ${lockAttr}></td>
            <td><input type="number" class="form-control form-control-sm text-center fw-bold" style="color: var(--verde-crescimento); border-color: var(--turquesa-automacao);" value="${item.preco_desconto.toFixed(2)}" step="0.01" min="0" onchange="mudarPrecoDesconto(${index}, this.value)" ${lockAttr}></td>
            <td class="fw-bold align-middle small" style="color: var(--azul-escuro);">R$ ${linhaTotal.toFixed(2).replace('.', ',')}</td>
            <td class="align-middle">
                <button type="button" class="btn btn-sm text-danger p-0 ${lockClass}" title="Excluir" onclick="removerItem(${index})"><i class="bi bi-trash-fill fs-5"></i></button>
            </td>
        </tr>`;
    });

    if (carrinho.length === 0) html = `<tr><td colspan="9" class="py-5 text-muted small">O carrinho está vazio.</td></tr>`;
    document.getElementById('tabelaCarrinho').innerHTML = html;

    let inputValorFinal = document.getElementById('inputValorFinal');

    if (inputValorFinal && !descontoGlobalAplicado && !isImportado) {
        inputValorFinal.value = totalComDescontoItens.toFixed(2);
    }

    if (inputValorFinal) {
        if (isImportado) inputValorFinal.disabled = true;
        let descontoPercInput = document.getElementById('inputDescontoPerc');
        if (descontoPercInput && isImportado) descontoPercInput.disabled = true;
    }

    if (typeof atualizarResumoCaixa === "function") {
        atualizarResumoCaixa();
    }
}

function atualizarResumoCaixa() {
    let subtotalOriginal = carrinho.reduce((s, i) => s + (i.preco * i.qtd), 0);
    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;

    let economiaTotal = subtotalOriginal - valorFinal;
    let economiaPontos = pointsToRedeem > 0 ? (window.DADOS_PONTOS_CLIENTE ? window.DADOS_PONTOS_CLIENTE.valor_reais : 0) : 0;
    let economiaManual = economiaTotal - economiaPontos;
    if (economiaManual < 0) economiaManual = 0;

    document.getElementById('txtSubtotal').innerText = `R$ ${subtotalOriginal.toFixed(2).replace('.', ',')}`;
    document.getElementById('txtDescontoManual').innerText = `- R$ ${economiaManual > 0 ? economiaManual.toFixed(2).replace('.', ',') : '0,00'}`;

    let divPontos = document.getElementById('divDescontoPontos');
    if (economiaPontos > 0) {
        document.getElementById('txtDescontoPontos').innerText = `- R$ ${economiaPontos.toFixed(2).replace('.', ',')}`;
        divPontos.classList.remove('d-none');
    } else {
        divPontos.classList.add('d-none');
    }
    calcularPagamentos(valorFinal);
}

// ==========================================
// 💳 SISTEMA DE PAGAMENTOS COM BUSCA DE TAXAS
// ==========================================
window.adicionarPagamento = function () {
    let metodoSelect = document.getElementById('selectMetodoPagamento');
    let metodo = metodoSelect.value;
    let metodoNome = metodoSelect.options[metodoSelect.selectedIndex].text;

    let parcelas = 1;
    if (metodo === 'CARTAO_CREDITO') {
        parcelas = parseInt(document.getElementById('selectParcelas').value) || 1;
        if (parcelas > 1) {
            metodoNome += ` (${parcelas}x)`;
        }
    }

    let valorInput = document.getElementById('inputValorPagamento');
    let valor = parseFloat(valorInput.value);

    if (isNaN(valor) || valor <= 0) {
        window.mostrarAviso("Digite um valor válido para o pagamento!", 'aviso');
        return;
    }

    if (metodo === 'CARTAO_CREDITO' || metodo === 'CARTAO_DEBITO') {
        valorInput.value = 'Buscando...';
        valorInput.disabled = true;

        fetch(`/api/taxas-maquininha/?metodo=${metodo}`)
            .then(res => res.json())
            .then(data => {
                let desconto = 0;
                if (data.status === 'sucesso') {
                    let regra = data.regras.find(r => r.parcelas === parcelas);
                    if (regra && regra.taxa_percentual > 0) {
                        desconto = valor * (regra.taxa_percentual / 100);
                    }
                }

                pagamentos.push({
                    metodo: metodo, parcelas: parcelas,
                    metodoNome: metodoNome, valor: valor,
                    desconto_maquininha: desconto
                });
                concluirAdicaoPagamento();
            }).catch(e => {
                pagamentos.push({ metodo: metodo, parcelas: parcelas, metodoNome: metodoNome, valor: valor, desconto_maquininha: 0 });
                concluirAdicaoPagamento();
            });
    } else {
        pagamentos.push({ metodo: metodo, parcelas: parcelas, metodoNome: metodoNome, valor: valor, desconto_maquininha: 0 });
        concluirAdicaoPagamento();
    }
};

function concluirAdicaoPagamento() {
    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    calcularPagamentos(valorFinal);

    let valInput = document.getElementById('inputValorPagamento');
    valInput.disabled = false;
    let buscaUniversal = document.getElementById('inputBuscaUniversal');
    if (buscaUniversal) buscaUniversal.focus();
}

window.removerPagamento = function (index) {
    if (pagamentos[index].metodo === 'PONTOS') {
        pointsToRedeem = 0;
        descontoManualAplicado = false;
        let btnFidelidade = document.getElementById('btnAcionarFidelidade');
        if (btnFidelidade) btnFidelidade.disabled = false;

        let inputFinal = document.getElementById('inputValorFinal');
        let valorDescontoAnterior = window.DADOS_PONTOS_CLIENTE ? window.DADOS_PONTOS_CLIENTE.valor_reais : 0;
        inputFinal.value = (parseFloat(inputFinal.value) + valorDescontoAnterior).toFixed(2);
    }

    pagamentos.splice(index, 1);
    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    calcularPagamentos(valorFinal);
    atualizarResumoCaixa();
};

function calcularPagamentos(valorTotalCompra) {
    localStorage.setItem('pagamentos', JSON.stringify(pagamentos));

    let totalPago = pagamentos.reduce((sum, p) => sum + p.valor, 0);
    window.CUSTO_TOTAL_MAQUININHA = pagamentos.reduce((sum, p) => sum + (p.desconto_maquininha || 0), 0);

    let falta = valorTotalCompra - totalPago;
    let troco = 0;

    if (falta <= 0) {
        troco = Math.abs(falta);
        falta = 0;
    }

    document.getElementById('txtTotalPago').innerText = `R$ ${totalPago.toFixed(2).replace('.', ',')}`;
    document.getElementById('txtFaltaPagar').innerText = `R$ ${falta.toFixed(2).replace('.', ',')}`;
    document.getElementById('txtTroco').innerText = `R$ ${troco.toFixed(2).replace('.', ',')}`;

    let htmlLista = '';
    if (pagamentos.length === 0) {
        htmlLista = '<li class="list-group-item text-muted text-center py-1">Nenhum pagamento inserido.</li>';
    } else {
        pagamentos.forEach((p, index) => {
            let avisoTaxa = p.desconto_maquininha > 0 ? `<small class="text-danger d-block" style="font-size: 0.70rem;">Custo Maq: R$ ${p.desconto_maquininha.toFixed(2).replace('.', ',')}</small>` : '';

            htmlLista += `
            <li class="list-group-item d-flex justify-content-between align-items-center py-1">
                <div>
                    <span style="color: var(--azul-escuro); font-weight: 500;">${p.metodoNome}</span>
                    ${avisoTaxa}
                </div>
                <div>
                    <strong class="me-2" style="color: var(--verde-crescimento);">R$ ${p.valor.toFixed(2).replace('.', ',')}</strong>
                    <button class="btn btn-sm text-danger p-0 m-0" onclick="removerPagamento(${index})"><i class="bi bi-x-circle-fill"></i></button>
                </div>
            </li>`;
        });
    }
    document.getElementById('listaPagamentosUI').innerHTML = htmlLista;
    document.getElementById('inputValorPagamento').value = falta > 0 ? falta.toFixed(2) : '';

    let metodoSelect = document.getElementById('selectMetodoPagamento');
    if (metodoSelect && metodoSelect.value === 'CARTAO_CREDITO' && falta > 0) {
        filtrarParcelas(falta);
    }
}

window.limparCarrinho = function () {
    if (confirm("Deseja realmente cancelar toda a operação e limpar o caixa?")) {
        carrinho = [];
        pagamentos = [];
        localStorage.removeItem('carrinho');
        localStorage.removeItem('pagamentos');
        pointsToRedeem = 0;
        descontoGlobalAplicado = false;
        descontoManualAplicado = false;
        window.CUSTO_TOTAL_MAQUININHA = 0;
        window.PEDIDO_IMPORTADO_ID = null;

        if (typeof BuscaUniversal !== 'undefined') BuscaUniversal.limpar(true);
        window.location.href = '/pdv/';
    }
};

// FIDELIDADE INTELIGENTE
window.verificarPontos = function () {
    let selCliente = document.getElementById('selectCliente');
    let optSelecionada = selCliente.options[selCliente.selectedIndex];
    pointsToRedeem = 0;
    window.DADOS_PONTOS_CLIENTE = null;

    let indexExistente = pagamentos.findIndex(p => p.metodo === 'PONTOS');
    if (indexExistente !== -1) {
        pagamentos.splice(indexExistente, 1);
        let valorF = parseFloat(document.getElementById('inputValorFinal').value) || 0;
        calcularPagamentos(valorF);
        atualizarResumoCaixa();
    }

    if (optSelecionada.value) {
        let saldoPontos = parseFloat(optSelecionada.getAttribute('data-pontos')) || 0;
        if (saldoPontos > 0) {
            let valorReais = Math.round(saldoPontos * 0.01 * 100) / 100;
            window.DADOS_PONTOS_CLIENTE = {
                pontos_utilizaveis: saldoPontos,
                valor_reais: valorReais
            };
        }
    }
};

window.tentarFinalizarVenda = function () {
    let saldoVirtual = window.DADOS_PONTOS_CLIENTE ? window.DADOS_PONTOS_CLIENTE.valor_reais : 0;
    if (saldoVirtual > 0 && pointsToRedeem === 0) {
        document.getElementById('fidPontosTxt').innerText = window.DADOS_PONTOS_CLIENTE.pontos_utilizaveis;
        document.getElementById('fidReaisTxt').innerText = saldoVirtual.toFixed(2).replace('.', ',');
        new bootstrap.Modal(document.getElementById('modalFidelidade')).show();
    } else {
        iniciarVerificacao('VENDA');
    }
};

window.aceitarDescontoPontos = function () {
    let valorReaisPontos = window.DADOS_PONTOS_CLIENTE.valor_reais;
    let inputFinal = document.getElementById('inputValorFinal');
    let valorAtual = parseFloat(inputFinal.value) || 0;
    let valorAUsar = valorReaisPontos > valorAtual ? valorAtual : valorReaisPontos;
    inputFinal.value = (valorAtual - valorAUsar).toFixed(2);
    descontoGlobalAplicado = true;
    pointsToRedeem = window.DADOS_PONTOS_CLIENTE.pontos_utilizaveis;
    pagamentos.push({
        metodo: 'PONTOS', parcelas: 1, metodoNome: 'PONTOS (RESGATE)', valor: valorAUsar, desconto_maquininha: 0
    });
    atualizarResumoCaixa();
    bootstrap.Modal.getInstance(document.getElementById('modalFidelidade')).hide();
    iniciarVerificacao('VENDA');
};

window.prosseguirVendaDireto = function () {
    bootstrap.Modal.getInstance(document.getElementById('modalFidelidade')).hide();
    iniciarVerificacao('VENDA');
};

window.iniciarVerificacao = function (statusSelecionado) {
    if (statusSelecionado === 'VENDA') {
        statusSelecionado = 'FATURADO';
    }

    if (carrinho.length === 0) {
        window.mostrarAviso("O carrinho está vazio!", 'aviso');
        return;
    }

    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    let totalPago = pagamentos.reduce((sum, p) => sum + p.valor, 0);

    if (statusSelecionado === 'FATURADO' && totalPago < valorFinal) {
        let valorFaltante = (valorFinal - totalPago).toFixed(2).replace('.', ',');
        window.mostrarAviso(`Operação Bloqueada: Ainda falta pagar R$ ${valorFaltante} para finalizar esta venda.`, 'erro');
        return;
    }

    let avisos = [];
    carrinho.forEach(item => {
        if (statusSelecionado === 'FATURADO' && item.qtd > item.estoque && !item.id.toString().startsWith('TINTA-')) {
            let falta = item.qtd - item.estoque;
            avisos.push(`<li><b>${item.nome}</b>: Estoque Insuficiente (Tem ${item.estoque}, Faltam ${falta}).</li>`);
        }
        if (item.custo && item.custo > 0 && item.preco_desconto <= item.custo) {
            avisos.push(`<li><b>${item.nome}</b>: Preço final (R$ ${item.preco_desconto.toFixed(2)}) está abaixo ou igual ao custo.</li>`);
        }
    });

    if (avisos.length > 0) {
        let htmlAvisos = `<p>O sistema identificou os seguintes alertas de segurança:</p><ul class="text-danger">`;
        avisos.forEach(a => htmlAvisos += a);
        htmlAvisos += `</ul><p class="mt-3 fw-bold mb-0">Deseja ignorar os avisos e prosseguir mesmo assim?</p>`;

        document.getElementById('textoModalAlerta').innerHTML = htmlAvisos;
        let btnConfirmar = document.getElementById('btnConfirmarModal');
        btnConfirmar.innerHTML = "Sim, Autorizar Venda";
        btnConfirmar.className = "btn btn-danger fw-bold";

        btnConfirmar.onclick = function () {
            bootstrap.Modal.getInstance(document.getElementById('modalAlertaPDV')).hide();
            enviarVendaAPI(statusSelecionado, totalPago);
        };
        new bootstrap.Modal(document.getElementById('modalAlertaPDV')).show();

    } else {
        enviarVendaAPI(statusSelecionado, totalPago);
    }
};

function enviarVendaAPI(statusSelecionado, totalPago) {
    const btnOrcamento = document.getElementById('btnOrcamento');
    const btnVenda = document.getElementById('btnVenda');

    if (statusSelecionado === 'ORCAMENTO') {
        btnOrcamento.disabled = true;
        btnOrcamento.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processando...';
        btnVenda.disabled = true;
    } else {
        btnVenda.disabled = true;
        btnVenda.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processando...';
        btnOrcamento.disabled = true;
    }

    let subtotalBrutoTotal = carrinho.reduce((s, i) => s + (i.preco * i.qtd), 0);
    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;

    let economiaTotalDaCompra = subtotalBrutoTotal - valorFinal;
    let descontoPorPontos = pointsToRedeem > 0 ? (window.DADOS_PONTOS_CLIENTE ? window.DADOS_PONTOS_CLIENTE.valor_reais : 0) : 0;
    let descontoManualFornecido = economiaTotalDaCompra - descontoPorPontos;
    if (descontoManualFornecido < 0) descontoManualFornecido = 0;

    let trocoReal = totalPago > valorFinal ? (totalPago - valorFinal) : 0;
    let totalTaxasCobradoDaLoja = window.CUSTO_TOTAL_MAQUININHA || 0;

    let selCliente = document.getElementById('selectCliente');
    let idCliente = selCliente.value;
    let nomeCliente = idCliente ? selCliente.options[selCliente.selectedIndex].text : '';

    let selIndicante = document.getElementById('selectIndicante');
    let idIndicante = selIndicante.value;
    let nomeIndicante = idIndicante ? selIndicante.options[selIndicante.selectedIndex].text : '';

    let pacote = {
        pedido_aberto_id: window.PEDIDO_IMPORTADO_ID || null,
        cliente_id: idCliente,
        cliente: nomeCliente,
        indicante_id: idIndicante,
        indicante: nomeIndicante,
        vendedor: document.getElementById('selectVendedor').value,
        status: statusSelecionado,
        valor_final: valorFinal,

        desconto_pontos: descontoPorPontos,
        desconto_comum: descontoManualFornecido,
        pontos_resgatados: pointsToRedeem,
        valor_taxa_maquininha: totalTaxasCobradoDaLoja,

        carrinho: carrinho,
        pagamentos: pagamentos,
        troco: trocoReal
    };

    fetch('/api/salvar-venda/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN },
        body: JSON.stringify(pacote)
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'sucesso') {
                if (window.PEDIDO_IMPORTADO_ID && statusSelecionado === 'FATURADO') {
                    fetch(`/api/pdv/faturar-pedido/${window.PEDIDO_IMPORTADO_ID}/`, {
                        method: 'POST',
                        headers: { 'X-CSRFToken': window.CSRF_TOKEN }
                    });
                }

                carrinho = [];
                pagamentos = [];
                localStorage.removeItem('carrinho');
                localStorage.removeItem('pagamentos');

                if (typeof BuscaUniversal !== 'undefined') BuscaUniversal.limpar(true);

                window.VENDA_FINALIZADA_ID = data.venda_id;
                window.PEDIDO_IMPORTADO_ID = null;

                if (statusSelecionado === 'ORCAMENTO') {
                    window.mostrarAviso('Orçamento gerado com sucesso!', 'sucesso');
                } else {
                    window.mostrarAviso('Venda finalizada com sucesso! Troco: R$ ' + trocoReal.toFixed(2).replace('.', ','), 'sucesso');
                }

                new bootstrap.Modal(document.getElementById('modalImpressao')).show();

            } else {
                window.mostrarAviso("Erro ao salvar a operação: " + data.mensagem, 'erro');
                restaurarBotoesFinalizar();
            }
        })
        .catch(err => {
            window.mostrarAviso("Erro de conexão. Verifique a internet e tente novamente.", 'erro');
            restaurarBotoesFinalizar();
        });
}

window.imprimirCupom = function (tipo) {
    if (tipo === 'bobina') {
        window.open(`/venda/cupom/${window.VENDA_FINALIZADA_ID}/`, '_blank', 'width=1024,height=850,scrollbars=yes,resizable=yes');
    } else if (tipo === 'a4') {
        window.open(`/venda/cupom-a4/${window.VENDA_FINALIZADA_ID}/`, '_blank', 'width=1024,height=850,scrollbars=yes,resizable=yes');
    }

    bootstrap.Modal.getInstance(document.getElementById('modalImpressao')).hide();
    window.location.href = '/pdv/';
};

function restaurarBotoesFinalizar() {
    const btnOrcamento = document.getElementById('btnOrcamento');
    const btnVenda = document.getElementById('btnVenda');
    if (btnOrcamento) { btnOrcamento.disabled = false; btnOrcamento.innerHTML = '📝 ORÇAMENTO'; }
    if (btnVenda) { btnVenda.disabled = false; btnVenda.innerHTML = '💰 VENDA'; }
}

window.abrirModalMenuTintometrico = function () {
    document.getElementById('menuSistemasTinto').style.display = 'block';
    document.getElementById('iframeTintometrico').style.display = 'none';
    document.getElementById('iframeTintometrico').src = "";
    new bootstrap.Modal(document.getElementById('modalTintometrico')).show();
};

window.carregarSistemaTinto = function (url) {
    document.getElementById('menuSistemasTinto').style.display = 'none';
    let iframe = document.getElementById('iframeTintometrico');
    iframe.src = url;
    iframe.style.display = 'block';
};

window.receberTintaDoIframe = function () {
    bootstrap.Modal.getInstance(document.getElementById('modalTintometrico')).hide();
    carrinho = JSON.parse(localStorage.getItem('carrinho')) || [];
    descontoGlobalAplicado = false;
    atualizarTela();
    let buscaUniversal = document.getElementById('inputBuscaUniversal');
    if (buscaUniversal) buscaUniversal.focus();
};

let modalSituacaoEstoqueObj = null;

window.consultarSituacaoEstoque = function (index) {
    let item = carrinho[index];
    indexProdutoFalta = index;

    document.getElementById('situacaoNomeProduto').innerText = item.nome;
    document.getElementById('situacaoQtdAtual').innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    if (!modalSituacaoEstoqueObj) modalSituacaoEstoqueObj = new bootstrap.Modal(document.getElementById('modalSituacaoEstoque'));
    modalSituacaoEstoqueObj.show();

    fetch(`/api/situacao-estoque/${item.id}/`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'sucesso') {
                document.getElementById('situacaoQtdAtual').innerText = data.estoque_atual;
                if (data.qtd_em_transito > 0) {
                    document.getElementById('situacaoQtdTransito').innerText = data.qtd_em_transito;
                    document.getElementById('situacaoDataPrevisao').innerText = data.data_previsao || 'Sem data';
                } else {
                    document.getElementById('situacaoQtdTransito').innerText = '0';
                    document.getElementById('situacaoDataPrevisao').innerText = '--/--/----';
                }
            }
        });
};

function sincronizarComBanco() {
    if (!window.PEDIDO_ABERTO_ID || window.VENDA_FINALIZADA_ID || window.PEDIDO_IMPORTADO_ID) return;
    const carrinhoAtual = localStorage.getItem('carrinho') || '[]';

    fetch(`/api/pdv/sincronizar/${window.PEDIDO_ABERTO_ID}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN },
        body: carrinhoAtual
    });
}

function iniciarAutoSave() {
    let ultimoCarrinhoVisto = localStorage.getItem('carrinho');
    setInterval(() => {
        let carrinhoAgora = localStorage.getItem('carrinho');
        if (carrinhoAgora !== ultimoCarrinhoVisto) {
            sincronizarComBanco();
            ultimoCarrinhoVisto = carrinhoAgora;
        }
    }, 5000);
}

window.abrirModalPedidosPDV = function () {
    new bootstrap.Modal(document.getElementById('modalPedidosPDV')).show();
    carregarPedidosPendentes();
    setTimeout(() => {
        let inputBusca = document.getElementById('inputBuscaPedidoCaixa');
        if (inputBusca) inputBusca.focus();
    }, 500);
};

window.pesquisarPedidoDigitado = function () {
    let inputEl = document.getElementById('inputBuscaPedidoCaixa');
    let numeroPedido = inputEl.value.trim();
    if (numeroPedido === "") { window.mostrarAviso("Bipe ou digite o número do pedido!", 'aviso'); return; }
    importarPedidoParaCaixa(numeroPedido);
    inputEl.value = "";
};

document.addEventListener('DOMContentLoaded', function () {
    let inputBuscaPedido = document.getElementById('inputBuscaPedidoCaixa');
    if (inputBuscaPedido) {
        inputBuscaPedido.addEventListener('keyup', function (event) {
            if (event.key === 'Enter') window.pesquisarPedidoDigitado();
        });
    }
});

window.carregarPedidosPendentes = function () {
    document.getElementById('listaPedidosPDV').innerHTML = '<tr><td colspan="5" class="py-4"><span class="spinner-border text-primary"></span> Buscando pedidos...</td></tr>';
    fetch('/api/pdv/pedidos-pendentes/')
        .then(res => res.json())
        .then(data => {
            let html = '';
            if (data.pedidos.length === 0) {
                html = '<tr><td colspan="5" class="py-4 text-muted fw-bold">Nenhum pedido aguardando no caixa.</td></tr>';
            } else {
                data.pedidos.forEach(p => {
                    html += `<tr>
                        <td class="fw-bold fs-5 text-primary">#${p.id}</td>
                        <td class="text-uppercase">${p.vendedor}</td>
                        <td class="fw-bold">${p.cliente}</td>
                        <td class="text-success fw-bold fs-5">R$ ${p.valor_total.toFixed(2).replace('.', ',')}</td>
                        <td>
                            <button class="btn btn-sm text-white fw-bold shadow-sm" style="background-color: var(--verde-crescimento);" onclick="importarPedidoParaCaixa(${p.id})">
                                <i class="bi bi-download"></i> Importar
                            </button>
                        </td>
                    </tr>`;
                });
            }
            document.getElementById('listaPedidosPDV').innerHTML = html;
        });
};

function selecionarOpcaoPorTexto(selectId, texto) {
    let select = document.getElementById(selectId);
    if (!select || !texto) return;
    let textoLimpo = String(texto).trim().toUpperCase();
    for (let i = 0; i < select.options.length; i++) {
        if (select.options[i].text.trim().toUpperCase() === textoLimpo ||
            select.options[i].value.trim().toUpperCase() === textoLimpo) {
            select.selectedIndex = i;
            select.dispatchEvent(new Event('change'));
            return;
        }
    }
}

window.importarPedidoParaCaixa = function (pedido_id) {
    fetch(`/api/pdv/importar-pedido/${pedido_id}/`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'sucesso') {
                if (data.pedido.status === 'FATURADO') {
                    window.mostrarAviso("Erro ao importar: Este pedido já está FATURADO no caixa.", "erro");
                    return;
                }
                carrinho = data.pedido.carrinho;
                if (data.pedido.cliente) selecionarOpcaoPorTexto('selectCliente', data.pedido.cliente);
                if (data.pedido.vendedor) selecionarOpcaoPorTexto('selectVendedor', data.pedido.vendedor);
                if (data.pedido.indicante) selecionarOpcaoPorTexto('selectIndicante', data.pedido.indicante);

                document.getElementById('selectCliente').disabled = true;
                document.getElementById('selectVendedor').disabled = true;
                document.getElementById('selectIndicante').disabled = true;

                let btnOrcamento = document.getElementById('btnOrcamento');
                if (btnOrcamento) { btnOrcamento.disabled = true; btnOrcamento.classList.add('d-none'); }

                let btnVenda = document.getElementById('btnVenda');
                if (btnVenda) { btnVenda.disabled = false; btnVenda.classList.remove('d-none'); }

                let totalItens = carrinho.reduce((s, i) => s + (i.preco_desconto * i.qtd), 0);
                let descontoRetaguarda = parseFloat(data.pedido.desconto) || 0;
                let valorFinalCalculado = totalItens - descontoRetaguarda;

                let inputFinal = document.getElementById('inputValorFinal');
                if (inputFinal) inputFinal.value = valorFinalCalculado.toFixed(2);
                descontoGlobalAplicado = true;
                window.PEDIDO_IMPORTADO_ID = pedido_id;

                bootstrap.Modal.getInstance(document.getElementById('modalPedidosPDV')).hide();
                atualizarTela();
                window.mostrarAviso(`Pedido #${pedido_id} bloqueado para edição e pronto para pagamento!`, 'sucesso');
            } else {
                window.mostrarAviso("Erro ao importar: O pedido não foi encontrado.", "erro");
            }
        });
};
