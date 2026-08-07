let carrinho = JSON.parse(localStorage.getItem('carrinho')) || [];
let pagamentos = JSON.parse(localStorage.getItem('pagamentos')) || [];
let tagsBusca = [];
let pointsToRedeem = 0;
let descontoGlobalAplicado = false;

window.addEventListener('beforeunload', function (e) {
    if (carrinho.length > 0) { e.preventDefault(); e.returnValue = ''; }
});

window.onload = function() {
    if(carrinho.length > 0) atualizarTela();
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
            if(data.produtos.length === 0) {
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
    localStorage.setItem('carrinho', JSON.stringify(carrinho));
    let html = '';
    let totalComDescontosItens = 0;

    carrinho.forEach((item, index) => {
        if (item.preco === undefined) item.preco = item.preco_venda || 0;
        if (item.preco_desconto === undefined) item.preco_desconto = item.preco;
        let totalLinha = item.preco_desconto * item.qtd;
        totalComDescontosItens += totalLinha;

        let percDesc = 0;
        if (item.preco > 0 && item.preco_desconto < item.preco) {
            percDesc = ((item.preco - item.preco_desconto) / item.preco) * 100;
        }

        let nomeExibicao = item.nome_customizado ? item.nome_customizado : item.nome;
        
        // 🚀 Trava de segurança: Remove aspas simples do nome para não quebrar o HTML do botão
        let nomeSeguro = nomeExibicao.replace(/'/g, "\\'");

        html += `<tr>
            <td class="text-start fw-bold small" style="color: var(--azul-escuro);">${nomeExibicao}</td>
            
            <td class="align-middle text-center">
                <div class="d-flex justify-content-center gap-2">
                    <!-- 🚀 NOVO BOTÃO: SITUAÇÃO DO ESTOQUE -->
                    <button type="button" class="btn btn-sm text-info p-0" title="Ver Situação do Estoque e Encomendas" onclick="consultarSituacaoEstoque(${item.id}, '${nomeSeguro}')"><i class="bi bi-box-seam fs-5"></i></button>
                    
                    <!-- Botões Antigos -->
                    <button type="button" class="btn btn-sm text-danger p-0" title="Excluir do Carrinho" onclick="removerItem(${index})"><i class="bi bi-trash-fill fs-5"></i></button>
                    <button type="button" class="btn btn-sm text-primary p-0" title="Editar Nome no Cupom" onclick="abrirModalEditarNome(${index})"><i class="bi bi-pencil-square fs-5"></i></button>
                    <button type="button" class="btn btn-sm text-warning p-0" title="Marcar Ruptura/Falta" onclick="marcarFalta(${index})"><i class="bi bi-exclamation-triangle-fill fs-5"></i></button>
                </div>
            </td>

            <td><input type="number" class="form-control form-control-sm text-center fw-bold border-secondary" value="${item.qtd}" min="1" step="1" oninput="this.value = this.value.replace(/[^0-9]/g, ''); if(this.value == '0') this.value = '1';" onchange="mudarQtd(${index}, this.value)"></td>
            <td class="text-muted align-middle small">R$ ${item.preco.toFixed(2).replace('.', ',')}</td>
            <td><input type="number" class="form-control form-control-sm text-center fw-bold text-danger" style="border-color: #ffc107; background-color: #fffdf5;" value="${percDesc > 0 ? percDesc.toFixed(1) : ''}" step="0.1" min="0" onchange="mudarPercDescontoItem(${index}, this.value)" placeholder="0.0"></td>
            <td><input type="number" class="form-control form-control-sm text-center fw-bold" style="color: var(--verde-crescimento); border-color: var(--turquesa-automacao);" value="${item.preco_desconto.toFixed(2)}" step="0.01" min="0" onchange="mudarPrecoDesconto(${index}, this.value)"></td>
            <td class="fw-bold align-middle small" style="color: var(--azul-escuro);">R$ ${totalLinha.toFixed(2).replace('.', ',')}</td>
        </tr>`;
    });

    document.getElementById('tabelaCarrinho').innerHTML = html;

    if (!descontoGlobalAplicado) {
        document.getElementById('inputValorFinal').value = totalComDescontosItens.toFixed(2);
        document.getElementById('inputDescontoPerc').value = '';
    }

    atualizarResumoCaixa();

    const btnOrcamento = document.getElementById('btnOrcamento');
    const btnVenda = document.getElementById('btnVenda');
    if (carrinho.length === 0) {
        if(btnOrcamento) btnOrcamento.disabled = true;
        if(btnVenda) btnVenda.disabled = true;
    } else {
        if(btnOrcamento) btnOrcamento.disabled = false;
        if(btnVenda) btnVenda.disabled = false;
    }
}


function abrirModalEditarNome(index) {
    document.getElementById('editItemIndex').value = index;
    let item = carrinho[index];
    document.getElementById('inputNomeCustomizado').value = item.nome_customizado ? item.nome_customizado : item.nome;
    let modal = new bootstrap.Modal(document.getElementById('modalEditarNomeProduto'));
    modal.show();
}

function salvarNomeCustomizado() {
    let index = document.getElementById('editItemIndex').value;
    let novoNome = document.getElementById('inputNomeCustomizado').value.trim().toUpperCase();
    
    if (novoNome !== "") {
        carrinho[index].nome_customizado = novoNome;
    } else {
        delete carrinho[index].nome_customizado; 
    }
    
    let modalEl = document.getElementById('modalEditarNomeProduto');
    let modal = bootstrap.Modal.getInstance(modalEl);
    if(modal) modal.hide();
    
    atualizarTela();
}

// ==========================================
// 🚀 NOVA MARCAÇÃO DE RUPTURA COM O MODAL DO SISTEMA
// ==========================================
function marcarFalta(index) {
    let item = carrinho[index];
    
    // Customiza o modal existente no HTML para a Ruptura
    document.getElementById('textoModalAlerta').innerHTML = `
        <div class="text-center">
            <p class="mb-2 fs-5">Deseja registrar <strong>RUPTURA (Falta de Estoque)</strong> para o produto abaixo?</p>
            <div class="p-3 my-3 border rounded shadow-sm" style="background-color: #fffdf5; border-color: #ffc107 !important;">
                <strong class="fs-5 text-danger">${item.nome}</strong>
            </div>
            <p class="mb-0 small text-muted">Ele será removido do carrinho atual e o gerente será notificado para compra.</p>
        </div>
    `;
    
    let btnConfirmar = document.getElementById('btnConfirmarModal');
    btnConfirmar.innerHTML = "Confirmar Ruptura";
    btnConfirmar.className = "btn btn-danger fw-bold";
    
    // Cria a ação do botão confirmar
    btnConfirmar.onclick = function() {
        let modalEl = document.getElementById('modalAlertaPDV');
        let modalInstance = bootstrap.Modal.getInstance(modalEl);
        if(modalInstance) modalInstance.hide();
        
        fetch('/api/registrar-ruptura/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
            body: JSON.stringify({
                produto_id: item.id,
                produto_nome: item.nome,
                quantidade_perdida: item.qtd
            })
        }).then(res => {
            window.mostrarAviso(`Alerta de Ruptura salvo! O produto foi removido.`, 'aviso');
        }).catch(err => {
            window.mostrarAviso(`Falta registrada localmente. O produto foi removido.`, 'aviso');
        });

        carrinho.splice(index, 1);
        descontoGlobalAplicado = false;
        atualizarTela();
    };

    // Abre o modal na tela
    let modalAlerta = new bootstrap.Modal(document.getElementById('modalAlertaPDV'));
    modalAlerta.show();
}

function mudarQtd(index, valor) {
    carrinho[index].qtd = parseInt(valor) || 1;
    descontoGlobalAplicado = false;
    atualizarTela();
}

function mudarPrecoDesconto(index, valor) {
    carrinho[index].preco_desconto = parseFloat(valor) || carrinho[index].preco;
    descontoGlobalAplicado = false;
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
    if(confirm("Deseja realmente limpar toda a operação?")) {
        carrinho = [];
        pagamentos = [];
        localStorage.removeItem('carrinho'); 
        localStorage.removeItem('pagamentos'); 
        tagsBusca = [];
        pointsToRedeem = 0;
        descontoGlobalAplicado = false;
        renderizarTags();
        document.getElementById('inputBusca').value = '';
        document.getElementById('resultadosBusca').style.display = 'none';
        document.getElementById('selectCliente').value = '';
        document.getElementById('areaResgatePontos').style.display = 'none';
        atualizarTela();
    }
}

function verificarPontos() {
    let clienteNome = document.getElementById('selectCliente').value;
    let areaResgate = document.getElementById('areaResgatePontos');
    pointsToRedeem = 0;
    areaResgate.style.display = 'none';
    if (clienteNome) {
        fetch(`/api/consultar-pontos/?cliente=${encodeURIComponent(clienteNome)}`)
            .then(res => res.json())
            .then(data => {
                if (data.pontos_utilizaveis > 0) {
                    areaResgate.innerHTML = `
                        <div class="alert p-2 mb-0 shadow-sm text-center text-dark" style="background-color: #FFC107; border: none;">
                            <strong class="d-block mb-1">🎁 Saldo: ${data.pontos_totais} pontos</strong>
                            <span class="small d-block mb-2">Vale <b>R$ ${data.valor_reais.toFixed(2).replace('.', ',')}</b> de desconto!</span>
                            <button type="button" class="btn btn-sm text-white fw-bold w-100" style="background-color: var(--azul-escuro);" onclick="aplicarDescontoPontos(${data.pontos_utilizaveis}, ${data.valor_reais})">
                                💰 RESGATAR AGORA
                            </button>
                        </div>`;
                    areaResgate.style.display = 'block';
                }
            });
    }
}

function aplicarDescontoPontos(pontos, valorDesconto) {
    let totalComDescontosItens = carrinho.reduce((s, i) => s + (i.preco_desconto * i.qtd), 0);
    
    if (totalComDescontosItens <= 0) {
        window.mostrarAviso("Adicione produtos no carrinho antes de aplicar o desconto!", 'aviso');
        return;
    }
    
    if (valorDesconto > totalComDescontosItens) valorDesconto = totalComDescontosItens;
    pointsToRedeem = pontos;
    let inputFinal = document.getElementById('inputValorFinal');
    inputFinal.value = (totalComDescontosItens - valorDesconto).toFixed(2);
    aplicarDescontoGlobalPorValor(); 
    document.getElementById('areaResgatePontos').innerHTML = `
        <div class="alert p-2 mb-0 shadow-sm text-center text-white" style="background-color: var(--verde-crescimento); border: none;">
            <strong>✅ R$ ${valorDesconto.toFixed(2).replace('.', ',')} Aplicados!</strong><br>
            <small>(${pontos} pontos serão debitados na finalização)</small>
        </div>`;
}

function iniciarVerificacao(statusSelecionado) {
    if (carrinho.length === 0) {
        window.mostrarAviso("O carrinho está vazio!", 'aviso');
        return;
    }

    let valorFinal = parseFloat(document.getElementById('inputValorFinal').value) || 0;
    let totalPago = pagamentos.reduce((sum, p) => sum + p.valor, 0);
    
    if (statusSelecionado === 'VENDA' && totalPago < valorFinal) {
        let valorFaltante = (valorFinal - totalPago).toFixed(2).replace('.', ',');
        window.mostrarAviso(`Operação Bloqueada: Ainda falta pagar R$ ${valorFaltante} para finalizar esta venda.`, 'erro');
        return;
    }

    let avisos = [];
    carrinho.forEach(item => {
        if (statusSelecionado === 'VENDA' && item.qtd > item.estoque && !item.id.toString().startsWith('TINTA-')) {
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
        
        // 🚀 GARANTIA: Retorna o botão do modal para o padrão (caso a ruptura tenha mudado ele antes)
        let btnConfirmar = document.getElementById('btnConfirmarModal');
        btnConfirmar.innerHTML = "Sim, Autorizar Venda";
        btnConfirmar.className = "btn btn-danger fw-bold";
        
        btnConfirmar.onclick = function() {
            let modalEl = document.getElementById('modalAlertaPDV');
            let modalInstance = bootstrap.Modal.getInstance(modalEl);
            if(modalInstance) modalInstance.hide();
            enviarVendaAPI(statusSelecionado, totalPago);
        };

        let modalAlerta = new bootstrap.Modal(document.getElementById('modalAlertaPDV'));
        modalAlerta.show();

    } else {
        enviarVendaAPI(statusSelecionado, totalPago);
    }
}

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

    let pacote = {
        cliente: document.getElementById('selectCliente').value,
        indicante: document.getElementById('selectIndicante').value,
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
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
        body: JSON.stringify(pacote)
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') {
            carrinho = []; 
            pagamentos = [];
            localStorage.removeItem('carrinho'); 
            localStorage.removeItem('pagamentos'); 
            
            if(statusSelecionado === 'ORCAMENTO') {
                window.mostrarAviso('Orçamento gerado com sucesso!', 'sucesso');
            } else {
                window.mostrarAviso('Venda finalizada com sucesso! Troco: R$ ' + trocoReal.toFixed(2).replace('.', ','), 'sucesso');
            }
            window.open(`/venda/cupom/${data.venda_id}/`, '_blank', 'width=1024,height=850,scrollbars=yes,resizable=yes');
            
            setTimeout(() => { location.reload(); }, 1500);
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

function restaurarBotoesFinalizar() {
    const btnOrcamento = document.getElementById('btnOrcamento');
    const btnVenda = document.getElementById('btnVenda');
    if(btnOrcamento) { btnOrcamento.disabled = false; btnOrcamento.innerHTML = '📝 ORÇAMENTO'; }
    if(btnVenda) { btnVenda.disabled = false; btnVenda.innerHTML = '💰 VENDA'; }
}

function mudarPercDescontoItem(index, perc) {
    let percentual = parseFloat(perc) || 0;
    if (percentual < 0) {
        percentual = 0;
    }
    let precoBase = carrinho[index].preco;
    carrinho[index].preco_desconto = precoBase - (precoBase * (percentual / 100));
    descontoGlobalAplicado = false;
    atualizarTela();
}

function verificarParcelamento() {
    let metodo = document.getElementById('selectMetodoPagamento').value;
    let selectParcelas = document.getElementById('selectParcelas');
    if (metodo === 'CARTAO_CREDITO') {
        selectParcelas.style.display = 'block';
    } else {
        selectParcelas.style.display = 'none';
        selectParcelas.value = '1';
    }
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

window.receberTintaDoIframe = function() {
    let myModalEl = document.getElementById('modalTintometrico');
    let modal = bootstrap.Modal.getInstance(myModalEl);
    if (modal) modal.hide();
    
    carrinho = JSON.parse(localStorage.getItem('carrinho')) || [];
    descontoGlobalAplicado = false; 
    atualizarTela();
    document.getElementById('inputBusca').focus();
};

// 🚀 FUNÇÃO PARA CONSULTAR O ESTOQUE E ENCOMENDAS NO PDV
let modalSituacaoEstoqueObj = null;

function consultarSituacaoEstoque(produtoId, nomeProduto) {
    if (!produtoId) {
        alert("ID do produto inválido.");
        return;
    }

    // Prepara o modal visualmente
    document.getElementById('situacaoNomeProduto').innerText = nomeProduto;
    document.getElementById('situacaoQtdAtual').innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    document.getElementById('situacaoQtdTransito').innerText = '-';
    document.getElementById('situacaoDataPrevisao').innerText = '-';
    document.getElementById('situacaoMensagemAviso').classList.add('d-none');

    if (!modalSituacaoEstoqueObj) {
        modalSituacaoEstoqueObj = new bootstrap.Modal(document.getElementById('modalSituacaoEstoque'));
    }
    modalSituacaoEstoqueObj.show();

    // Faz a consulta silenciosa na API que criamos
    fetch(`/api/situacao-estoque/${produtoId}/`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'sucesso') {
                document.getElementById('situacaoQtdAtual').innerText = data.estoque_atual;
                
                if (data.qtd_em_transito > 0) {
                    document.getElementById('situacaoQtdTransito').innerText = data.qtd_em_transito;
                    document.getElementById('situacaoDataPrevisao').innerText = data.data_previsao || 'Sem data informada';
                    document.getElementById('situacaoMensagemAviso').classList.remove('d-none');
                } else {
                    document.getElementById('situacaoQtdTransito').innerText = '0';
                    document.getElementById('situacaoDataPrevisao').innerText = '--/--/----';
                }
            } else {
                document.getElementById('situacaoQtdAtual').innerText = 'Erro';
                alert("Erro ao buscar estoque: " + data.mensagem);
            }
        })
        .catch(err => {
            document.getElementById('situacaoQtdAtual').innerText = 'Erro';
            console.error("Erro de conexão:", err);
        });
}
