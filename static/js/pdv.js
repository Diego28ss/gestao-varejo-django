let carrinho = JSON.parse(localStorage.getItem('carrinho')) || [];
let pagamentos = JSON.parse(localStorage.getItem('pagamentos')) || [];
let tagsBusca = [];
let pointsToRedeem = 0;
let descontoGlobalAplicado = false;
window.DADOS_PONTOS_CLIENTE = null; // Memória de Fidelidade

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

    if (carrinho.length > 0) atualizarTela();
    iniciarAutoSave();
};

function tratarInputBusca(event, input) {
    let texto = input.value.trim();
    if (event.key === "Enter" && texto !== "") {
        tagsBusca.push(texto.toUpperCase());
        input.value = "";
        renderizarTags();
        buscarProduto("");
    } else {
        buscarProduto(texto);
    }
}

function renderizarTags() {
    let html = '';
    tagsBusca.forEach((tag, index) => {
        html += `<span class="badge text-white me-2 mb-2 p-2 fs-6 shadow-sm d-flex align-items-center" style="background-color: var(--azul-escuro);">
                    ${tag} <i class="bi bi-x-circle ms-2" style="cursor: pointer; color: var(--turquesa-automacao);" onclick="removerTag(${index})"></i>
                 </span>`;
    });
    document.getElementById('areaTags').innerHTML = html;
}

function removerTag(index) {
    tagsBusca.splice(index, 1);
    renderizarTags();
    buscarProduto(document.getElementById('inputBusca').value.trim());
}

function buscarProduto(textoDigitado) {
    let termosParaBuscar = [...tagsBusca];
    if (textoDigitado.length > 0) termosParaBuscar.push(textoDigitado);
    let queryFinal = termosParaBuscar.join(" ");

    if (queryFinal.length < 2) {
        document.getElementById('resultadosBusca').style.display = 'none';
        return;
    }

    fetch(`/api/buscar-produtos/?q=${encodeURIComponent(queryFinal)}`)
        .then(res => res.json())
        .then(data => {
            let html = '';
            if (data.produtos.length === 0) {
                html = '<div class="list-group-item text-muted text-center py-3">Nenhum produto encontrado.</div>';
            } else {
                data.produtos.forEach((p) => {
                    let nomeSeguro = p.nome.replace(/"/g, '&quot;').replace(/'/g, "\\'");
                    html += `<button type="button"
                                class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                                data-id="${p.id}" data-nome="${nomeSeguro}" data-preco="${p.preco_venda}" 
                                data-custo="${p.preco_custo}" data-estoque="${p.estoque_atual}"
                                onclick="adicionarDiretoDoBotao(this)">
                                <span class="text-start"><strong style="color: var(--azul-escuro);">${p.nome}</strong><br><small class="text-muted">Estoque: ${p.estoque_atual}</small></span>
                                <strong style="color: var(--verde-crescimento);" class="fs-5">R$ ${p.preco_venda.toFixed(2).replace('.', ',')}</strong>
                             </button>`;
                });
            }
            document.getElementById('resultadosBusca').innerHTML = html;
            document.getElementById('resultadosBusca').style.display = 'block';
        });
}

function adicionarDiretoDoBotao(botao) {
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

    document.getElementById('resultadosBusca').style.display = 'none';
    document.getElementById('inputBusca').value = '';
    descontoGlobalAplicado = false;
    atualizarTela();
    document.getElementById('inputBusca').focus();
}

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

        let nomeExibicao = item.nome_customizado ? item.nome_customizado : item.nome;

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

function abrirModalEditarNome(index) {
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
}

function salvarNomeCustomizado() {
    let index = document.getElementById('editItemIndex').value;
    let novoNome = document.getElementById('inputNomeCustomizado').value.trim().toUpperCase();
    let precoBase = parseFloat(document.getElementById('editItemPrecoOriginal').value);
    let novoPreco = parseFloat(document.getElementById('inputPrecoCustomizado').value);

    if (novoNome !== "") carrinho[index].nome_customizado = novoNome;
    else delete carrinho[index].nome_customizado;

    if (!isNaN(novoPreco)) {
        if (novoPreco < precoBase) {
            if (typeof window.mostrarAviso === 'function') window.mostrarAviso("O preço base só pode ser aumentado. Use os campos de desconto para reduzir o valor.", "erro");
            else alert("O preço base só pode ser aumentado.");
            return;
        }

        carrinho[index].preco_original_base = precoBase;
        carrinho[index].preco = novoPreco;
        carrinho[index].preco_desconto = novoPreco;
        carrinho[index].descontoValor = 0;
        carrinho[index].descontoPercentual = 0;
    }

    bootstrap.Modal.getInstance(document.getElementById('modalEditarNomeProduto')).hide();
    atualizarTela();
}

let indexProdutoFalta = null;

function mudarQtd(index, valor) {
    carrinho[index].qtd = parseInt(valor) || 1;
    descontoGlobalAplicado = false;
    atualizarTela();
}

function mudarPrecoDesconto(index, valor) {
    let novoPreco = parseFloat(valor);
    let item = carrinho[index];

    if (novoPreco > item.preco || novoPreco < 0) {
        if (typeof window.mostrarAviso === 'function') window.mostrarAviso("O desconto não pode ser negativo nem aumentar o valor original do item.", "erro");
        item.preco_desconto = item.preco;
    } else {
        item.preco_desconto = novoPreco || item.preco;
    }

    if (typeof descontoGlobalAplicado !== 'undefined') descontoGlobalAplicado = false;
    atualizarTela();
}

function mudarPercDescontoItem(index, percStr) {
    let perc = parseFloat(percStr) || 0;
    let item = carrinho[index];

    if (perc < 0 || perc > 100) {
        if (typeof window.mostrarAviso === 'function') window.mostrarAviso("A porcentagem de desconto deve estar entre 0% e 100%.", "erro");
        item.preco_desconto = item.preco;
    } else if (perc === 0) {
        item.preco_desconto = item.preco;
    } else {
        item.preco_desconto = item.preco - (item.preco * (perc / 100));
    }

    if (typeof descontoGlobalAplicado !== 'undefined') descontoGlobalAplicado = false;
    atualizarTela();
}


function removerItem(index) {
    carrinho.splice(index, 1);
    descontoGlobalAplicado = false;
    atualizarTela();
}

function aplicarDescontoGlobalPorPorcentagem() {
    let perc = parseFloat(document.getElementById('inputDescontoPerc').value) || 0;
    if (perc < 0) {
        perc = 0;
        document.getElementById('inputDescontoPerc').value = '';
    }
    let totalItens = carrinho.reduce((s, i) => s + (i.preco_desconto * i.qtd), 0);
    let novoValorFinal = totalItens - (totalItens * (perc / 100));
    document.getElementById('inputValorFinal').value = novoValorFinal.toFixed(2);
    descontoGlobalAplicado = true;
    atualizarResumoCaixa();
}

function aplicarDescontoGlobalPorValor() {
    let valorFinalInput = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    let totalItens = carrinho.reduce((s, i) => s + (i.preco_desconto * i.qtd), 0);
    if (totalItens > 0) {
        if (valorFinalInput > totalItens) {
            document.getElementById('inputDescontoPerc').value = '';
        } else {
            let perc = ((totalItens - valorFinalInput) / totalItens) * 100;
            document.getElementById('inputDescontoPerc').value = perc.toFixed(2);
        }
    } else {
        document.getElementById('inputDescontoPerc').value = '';
    }
    descontoGlobalAplicado = true;
    atualizarResumoCaixa();
}

function atualizarResumoCaixa() {
    let subtotalOriginal = carrinho.reduce((s, i) => s + (i.preco * i.qtd), 0);
    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    let economiaTotal = subtotalOriginal - valorFinal;

    document.getElementById('txtSubtotal').innerText = `R$ ${subtotalOriginal.toFixed(2).replace('.', ',')}`;
    document.getElementById('txtDesconto').innerText = `- R$ ${economiaTotal > 0 ? economiaTotal.toFixed(2).replace('.', ',') : '0,00'}`;

    calcularPagamentos(valorFinal);
}

function adicionarPagamento() {
    let metodoSelect = document.getElementById('selectMetodoPagamento');
    let metodo = metodoSelect.value;
    let metodoNome = metodoSelect.options[metodoSelect.selectedIndex].text;

    let parcelas = 1;
    if (metodo === 'CARTAO_CREDITO') {
        parcelas = parseInt(document.getElementById('selectParcelas').value);
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

    pagamentos.push({ metodo: metodo, parcelas: parcelas, metodoNome: metodoNome, valor: valor });

    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    calcularPagamentos(valorFinal);

    document.getElementById('inputValorPagamento').value = '';
    document.getElementById('inputBusca').focus();
}

function removerPagamento(index) {
    if (pagamentos[index].metodo === 'PONTOS') {
        pointsToRedeem = 0;
        let btnFidelidade = document.getElementById('btnAcionarFidelidade');
        if (btnFidelidade) btnFidelidade.disabled = false; // Devolve a opção de clicar
    }
    
    pagamentos.splice(index, 1);
    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    calcularPagamentos(valorFinal);
}


function calcularPagamentos(valorTotalCompra) {
    localStorage.setItem('pagamentos', JSON.stringify(pagamentos));

    let totalPago = pagamentos.reduce((sum, p) => sum + p.valor, 0);
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
            htmlLista += `
            <li class="list-group-item d-flex justify-content-between align-items-center py-1">
                <span style="color: var(--azul-escuro); font-weight: 500;">${p.metodoNome}</span>
                <div>
                    <strong class="me-2" style="color: var(--verde-crescimento);">R$ ${p.valor.toFixed(2).replace('.', ',')}</strong>
                    <button class="btn btn-sm text-danger p-0 m-0" onclick="removerPagamento(${index})"><i class="bi bi-x-circle-fill"></i></button>
                </div>
            </li>`;
        });
    }
    document.getElementById('listaPagamentosUI').innerHTML = htmlLista;

    document.getElementById('inputValorPagamento').value = falta > 0 ? falta.toFixed(2) : '';
}

function limparCarrinho() {
    if (confirm("Deseja realmente cancelar toda a operação e limpar o caixa?")) {
        carrinho = [];
        pagamentos = [];
        localStorage.removeItem('carrinho');
        localStorage.removeItem('pagamentos');
        tagsBusca = [];
        pointsToRedeem = 0;
        descontoGlobalAplicado = false;
        window.PEDIDO_IMPORTADO_ID = null;

        window.location.href = '/pdv/';
    }
}

// ==========================================
// 🎁 INTERCEPTADOR DE FIDELIDADE (FASE 3)
// ==========================================
function injetarModalFidelidade() {
    if (document.getElementById('modalFidelidade')) return;
    let html = `
    <div class="modal fade" id="modalFidelidade" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content border-0 shadow-lg">
                <div class="modal-header text-white" style="background-color: var(--azul-escuro);">
                    <h5 class="modal-title fw-bold">🎁 Resgate de Pontos de Fidelidade</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center p-4">
                    <i class="bi bi-gift-fill text-warning mb-2" style="font-size: 3rem;"></i>
                    <h4 class="fw-bold" style="color: var(--azul-escuro);">Cliente com Saldo!</h4>
                    <p class="fs-5 mb-1">O cliente possui <strong id="fidPontosTxt">0</strong> pontos acumulados.</p>
                    <p class="fs-5 mb-4">Isso equivale a <strong class="text-success">R$ <span id="fidReaisTxt">0,00</span></strong> de desconto na compra.</p>
                    <div class="d-grid gap-3">
                        <button type="button" class="btn btn-lg text-white fw-bold shadow-sm" style="background-color: var(--verde-crescimento);" id="btnFidResgatar">
                            💰 Aplicar Desconto Agora
                        </button>
                        <button type="button" class="btn btn-lg btn-outline-secondary fw-bold shadow-sm" id="btnFidAcumular">
                            ➕ Não usar (Deixar Acumular)
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
}

function verificarPontos() {
    let selCliente = document.getElementById('selectCliente');
    let clienteNome = selCliente.value ? selCliente.options[selCliente.selectedIndex].text : '';

    let btnFidelidade = document.getElementById('btnAcionarFidelidade');
    
    // Reseta o estado
    pointsToRedeem = 0;
    window.DADOS_PONTOS_CLIENTE = null;
    if (btnFidelidade) btnFidelidade.disabled = true;

    // Se o operador trocar de cliente, removemos os pontos que já estavam na lista de pagamento
    let indexExistente = pagamentos.findIndex(p => p.metodo === 'PONTOS');
    if (indexExistente !== -1) {
        pagamentos.splice(indexExistente, 1);
        calcularPagamentos(parseFloat(document.getElementById('inputValorFinal').value) || 0);
    }

    if (clienteNome && clienteNome !== "CONSUMIDOR PADRÃO") {
        fetch(`/api/consultar-pontos/?cliente=${encodeURIComponent(clienteNome)}`)
            .then(res => res.json())
            .then(data => {
                if (data.pontos_utilizaveis > 0) {
                    window.DADOS_PONTOS_CLIENTE = data;
                    if (btnFidelidade) btnFidelidade.disabled = false; // Desbloqueia o botão
                }
            });
    }
}

function aplicarDescontoPontos(pontos, valorDesconto) {
    let totalComDescontosItens = carrinho.reduce((s, i) => s + (i.preco_desconto * i.qtd), 0);

    if (totalComDescontosItens <= 0) return;
    if (valorDesconto > totalComDescontosItens) valorDesconto = totalComDescontosItens;
    
    pointsToRedeem = pontos;
    let inputFinal = document.getElementById('inputValorFinal');
    inputFinal.value = (totalComDescontosItens - valorDesconto).toFixed(2);
    aplicarDescontoGlobalPorValor();

    // Feedback visual opcional
    let areaLegado = document.getElementById('areaResgatePontos');
    if(areaLegado) {
        areaLegado.innerHTML = `
            <div class="alert p-2 mb-0 shadow-sm text-center text-white" style="background-color: var(--verde-crescimento); border: none;">
                <strong>✅ R$ ${valorDesconto.toFixed(2).replace('.', ',')} Aplicados!</strong><br>
                <small>(${pontos} pontos debitados)</small>
            </div>`;
        areaLegado.style.display = 'block';
    }
}

function iniciarVerificacao(statusSelecionado) {
    if (statusSelecionado === 'VENDA') {
        statusSelecionado = 'FATURADO';
    }

    if (carrinho.length === 0) {
        window.mostrarAviso("O carrinho está vazio!", 'aviso');
        return;
    }

    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    let totalPago = pagamentos.reduce((sum, p) => sum + p.valor, 0);

    // Trava do Caixa
    if (statusSelecionado === 'FATURADO' && totalPago < valorFinal) {
        let valorFaltante = (valorFinal - totalPago).toFixed(2).replace('.', ',');
        window.mostrarAviso(`Operação Bloqueada: Ainda falta pagar R$ ${valorFaltante} para finalizar esta venda.`, 'erro');
        return;
    }

    // Alertas de Segurança (Estoque/Custo)
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
            let modalEl = document.getElementById('modalAlertaPDV');
            let modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) modalInstance.hide();
            enviarVendaAPI(statusSelecionado, totalPago);
        };

        new bootstrap.Modal(document.getElementById('modalAlertaPDV')).show();

    } else {
        enviarVendaAPI(statusSelecionado, totalPago);
    }
}


function prosseguirVerificacao(statusSelecionado) {
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
            let modalEl = document.getElementById('modalAlertaPDV');
            let modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) modalInstance.hide();
            enviarVendaAPI(statusSelecionado, totalPago);
        };

        let modalAlerta = new bootstrap.Modal(document.getElementById('modalAlertaPDV'));
        modalAlerta.show();

    } else {
        enviarVendaAPI(statusSelecionado, totalPago);
    }
}

// ==========================================
// 💾 ENVIAR VENDA AO BANCO DE DADOS E DAR BAIXA
// ==========================================
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

    let subtotalComDescontosItens = carrinho.reduce((s, i) => s + (i.preco_desconto * i.qtd), 0);
    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    let descontoGlobalAdicional = subtotalComDescontosItens - valorFinal;

    let trocoReal = totalPago > valorFinal ? (totalPago - valorFinal) : 0;

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
        desconto: descontoGlobalAdicional > 0 ? descontoGlobalAdicional : 0,
        pontos_resgatados: pointsToRedeem,
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
                    }).catch(err => console.error("Aviso: Falha silenciosa ao baixar o pedido.", err));
                }

                carrinho = [];
                pagamentos = [];
                localStorage.removeItem('carrinho');
                localStorage.removeItem('pagamentos');

                window.VENDA_FINALIZADA_ID = data.venda_id;
                window.PEDIDO_IMPORTADO_ID = null;

                if (statusSelecionado === 'ORCAMENTO') {
                    window.mostrarAviso('Orçamento gerado com sucesso!', 'sucesso');
                } else {
                    window.mostrarAviso('Venda finalizada com sucesso! Troco: R$ ' + trocoReal.toFixed(2).replace('.', ','), 'sucesso');
                }

                let modalImp = new bootstrap.Modal(document.getElementById('modalImpressao'));
                modalImp.show();

            } else {
                window.mostrarAviso("Erro ao salvar a operação: " + data.mensagem, 'erro');
                restaurarBotoesFinalizar();
            }
        })
        .catch(err => {
            window.mostrarAviso("Erro de conexão com o servidor. Verifique a internet e tente novamente.", 'erro');
            restaurarBotoesFinalizar();
        });
}

window.imprimirCupom = function (tipo) {
    if (tipo === 'bobina') {
        window.open(`/venda/cupom/${window.VENDA_FINALIZADA_ID}/`, '_blank', 'width=1024,height=850,scrollbars=yes,resizable=yes');
    } else if (tipo === 'a4') {
        window.open(`/venda/cupom-a4/${window.VENDA_FINALIZADA_ID}/`, '_blank', 'width=1024,height=850,scrollbars=yes,resizable=yes');
    }

    let modalEl = document.getElementById('modalImpressao');
    let modalInstance = bootstrap.Modal.getInstance(modalEl);
    if (modalInstance) modalInstance.hide();

    window.location.href = '/pdv/';
};

function restaurarBotoesFinalizar() {
    const btnOrcamento = document.getElementById('btnOrcamento');
    const btnVenda = document.getElementById('btnVenda');
    if (btnOrcamento) { btnOrcamento.disabled = false; btnOrcamento.innerHTML = '📝 ORÇAMENTO'; }
    if (btnVenda) { btnVenda.disabled = false; btnVenda.innerHTML = '💰 VENDA'; }
}

function abrirModalMenuTintometrico() {
    document.getElementById('menuSistemasTinto').style.display = 'block';
    document.getElementById('iframeTintometrico').style.display = 'none';
    document.getElementById('iframeTintometrico').src = "";

    let modal = new bootstrap.Modal(document.getElementById('modalTintometrico'));
    modal.show();
}

function carregarSistemaTinto(url) {
    document.getElementById('menuSistemasTinto').style.display = 'none';
    let iframe = document.getElementById('iframeTintometrico');
    iframe.src = url;
    iframe.style.display = 'block';
}

window.receberTintaDoIframe = function () {
    let myModalEl = document.getElementById('modalTintometrico');
    let modal = bootstrap.Modal.getInstance(myModalEl);
    if (modal) modal.hide();

    carrinho = JSON.parse(localStorage.getItem('carrinho')) || [];
    descontoGlobalAplicado = false;
    atualizarTela();
    document.getElementById('inputBusca').focus();
};

let modalSituacaoEstoqueObj = null;

function consultarSituacaoEstoque(index) {
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
}

function sincronizarComBanco() {
    if (!window.PEDIDO_ABERTO_ID || window.VENDA_FINALIZADA_ID || window.PEDIDO_IMPORTADO_ID) return;

    const carrinhoAtual = localStorage.getItem('carrinho') || '[]';

    fetch(`/api/pdv/sincronizar/${window.PEDIDO_ABERTO_ID}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.CSRF_TOKEN
        },
        body: carrinhoAtual
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'sucesso') {
                console.log("💾 Rascunho salvo no banco em segundo plano.");
            }
        })
        .catch(err => console.error("Erro ao sincronizar rascunho:", err));
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

// ==========================================
// ☁️ PUXAR PEDIDOS DA RETAGUARDA PARA O CAIXA
// ==========================================
window.PEDIDO_IMPORTADO_ID = null;

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

    if (numeroPedido === "") {
        window.mostrarAviso("Bipe ou digite o número do pedido!", 'aviso');
        return;
    }

    importarPedidoParaCaixa(numeroPedido);
    inputEl.value = "";
};

document.addEventListener('DOMContentLoaded', function () {
    let inputBuscaPedido = document.getElementById('inputBuscaPedidoCaixa');
    if (inputBuscaPedido) {
        inputBuscaPedido.addEventListener('keyup', function (event) {
            if (event.key === 'Enter') {
                pesquisarPedidoDigitado();
            }
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
                if (btnOrcamento) {
                    btnOrcamento.disabled = true;
                    btnOrcamento.classList.add('d-none');
                }

                let btnVenda = document.getElementById('btnVenda');
                if (btnVenda) {
                    btnVenda.disabled = false;
                    btnVenda.classList.remove('d-none');
                }

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

function marcarFaltaPeloModal() {
    if (indexProdutoFalta === null) return;
    let item = carrinho[indexProdutoFalta];

    if (confirm(`Deseja registrar RUPTURA (Falta de Estoque) para:\n\n${item.nome}\n\nEle será removido do carrinho e a gerência será notificada.`)) {
        fetch('/api/registrar-ruptura/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN },
            body: JSON.stringify({
                produto_id: item.id,
                quantidade_perdida: item.qtd
            })
        }).then(res => {
            if (typeof window.mostrarAviso === 'function') window.mostrarAviso(`Alerta de Ruptura salvo! Produto removido.`, 'sucesso');
            else alert("Ruptura salva.");
        }).catch(err => {
            console.error(err);
        });

        carrinho.splice(indexProdutoFalta, 1);
        bootstrap.Modal.getInstance(document.getElementById('modalSituacaoEstoque')).hide();
        atualizarTela();
        indexProdutoFalta = null;
    }
}

function abrirModalFidelidade() {
    if (!window.DADOS_PONTOS_CLIENTE) return;

    // Verifica se os pontos já foram adicionados na lista
    let indexExistente = pagamentos.findIndex(p => p.metodo === 'PONTOS');
    if (indexExistente !== -1) {
        window.mostrarAviso("Os pontos já foram resgatados e adicionados como pagamento.", "aviso");
        return;
    }

    // Preenche os dados no HTML e mostra o Modal
    document.getElementById('fidPontosTxt').innerText = window.DADOS_PONTOS_CLIENTE.pontos_utilizaveis;
    document.getElementById('fidReaisTxt').innerText = window.DADOS_PONTOS_CLIENTE.valor_reais.toFixed(2).replace('.', ',');
    
    let modal = new bootstrap.Modal(document.getElementById('modalFidelidade'));
    modal.show();
}

function aplicarPagamentoComPontos() {
    if (!window.DADOS_PONTOS_CLIENTE) return;

    let valorFinalCompra = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    let totalPago = pagamentos.reduce((sum, p) => sum + p.valor, 0);
    let faltaPagar = valorFinalCompra - totalPago;

    if (faltaPagar <= 0) {
        window.mostrarAviso("O valor da compra já está totalmente coberto.", 'aviso');
        bootstrap.Modal.getInstance(document.getElementById('modalFidelidade')).hide();
        return;
    }

    let valorReaisPontos = window.DADOS_PONTOS_CLIENTE.valor_reais;
    
    // Calcula para não dar "troco" em cima dos pontos caso a compra seja menor que o saldo
    let valorAUsar = valorReaisPontos > faltaPagar ? faltaPagar : valorReaisPontos;

    // Lança na Tabela de Pagamentos
    pagamentos.push({ 
        metodo: 'PONTOS', 
        parcelas: 1, 
        metodoNome: 'PONTOS (RESGATE)', 
        valor: valorAUsar 
    });
    
    // Salva na memória global para enviar ao backend
    pointsToRedeem = window.DADOS_PONTOS_CLIENTE.pontos_utilizaveis;
    
    // Desativa o botão azul e recalcula a tela
    document.getElementById('btnAcionarFidelidade').disabled = true;
    calcularPagamentos(valorFinalCompra);
    
    bootstrap.Modal.getInstance(document.getElementById('modalFidelidade')).hide();
}

