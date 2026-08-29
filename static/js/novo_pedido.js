// Usamos uma chave diferente no localStorage para não misturar com o Caixa
let carrinho = JSON.parse(localStorage.getItem('carrinho_novo_pedido')) || [];
let tagsBusca = [];

// ==========================================
// INICIALIZAÇÃO
// ==========================================
window.onload = function() {
    if (window.PEDIDO_ABERTO_ID) {
        if (Array.isArray(window.PEDIDO_JSON_INJETADO) && window.PEDIDO_JSON_INJETADO.length > 0) {
            carrinho = window.PEDIDO_JSON_INJETADO;
            localStorage.setItem('carrinho_novo_pedido', JSON.stringify(carrinho));
        }
    }
    atualizarTela();
};

// ==========================================
// SISTEMA DE BUSCA COM TAGS
// ==========================================
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
    atualizarTela();
    document.getElementById('inputBusca').focus();
}

// ==========================================
// RENDERIZAÇÃO DO CARRINHO E CÁLCULOS
// ==========================================
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
        let nomeSeguro = nomeExibicao.replace(/'/g, "\\'");

        // 🚀 Ocultamento aplicado exclusivamente na tag do botão
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

    let inputValorFinal = document.getElementById('inputValorFinal') || document.getElementById('inputDescontoValor');
    if (inputValorFinal) {
        if (isImportado) inputValorFinal.disabled = true;
        let descontoPercInput = document.getElementById('inputDescontoPerc');
        if(descontoPercInput && isImportado) descontoPercInput.disabled = true;
    }

    if (typeof atualizarResumoCaixa === "function") {
        atualizarResumoCaixa();
    } else {
        let descontoGlobal = parseFloat(inputValorFinal ? inputValorFinal.value : 0) || 0;
        let totalFinal = totalComDescontoItens - descontoGlobal;
        if (totalFinal < 0) totalFinal = 0;
        let descontoTotal = (subtotalBruto - totalComDescontoItens) + descontoGlobal;
        document.getElementById('txtSubtotal').innerText = `R$ ${subtotalBruto.toFixed(2).replace('.', ',')}`;
        document.getElementById('txtDesconto').innerText = `- R$ ${descontoTotal > 0 ? descontoTotal.toFixed(2).replace('.', ',') : '0,00'}`;
        document.getElementById('txtTotal').innerText = `R$ ${totalFinal.toFixed(2).replace('.', ',')}`;
    }
}

window.aplicarDescontoGlobalPorPorcentagem = function() {
    let perc = parseFloat(document.getElementById('inputDescontoPerc').value) || 0;
    if (perc < 0) perc = 0;
    
    let totalItens = carrinho.reduce((s, i) => s + ((i.preco_desconto || i.preco) * i.qtd), 0);
    let desconto = totalItens * (perc / 100);
    
    document.getElementById('inputDescontoValor').value = desconto.toFixed(2);
    atualizarTela();
};

window.aplicarDescontoGlobalPorValor = function() {
    let valor = parseFloat(document.getElementById('inputDescontoValor').value) || 0;
    if (valor < 0) valor = 0;
    
    let totalItens = carrinho.reduce((s, i) => s + ((i.preco_desconto || i.preco) * i.qtd), 0);
    
    if (totalItens > 0) {
        let perc = (valor / totalItens) * 100;
        document.getElementById('inputDescontoPerc').value = perc.toFixed(2);
    } else {
        document.getElementById('inputDescontoPerc').value = '';
    }
    atualizarTela();
};


// ==========================================
// FUNÇÕES AUXILIARES DOS ITENS
// ==========================================
function mudarQtd(index, valor) {
    carrinho[index].qtd = parseInt(valor) || 1;
    atualizarTela();
}

function mudarPrecoDesconto(index, valor) {
    carrinho[index].preco_desconto = parseFloat(valor) || carrinho[index].preco;
    atualizarTela();
}

function mudarPercDescontoItem(index, percStr) {
    let perc = parseFloat(percStr) || 0;
    let item = carrinho[index];
    if (perc <= 0) {
        item.preco_desconto = item.preco;
    } else {
        item.preco_desconto = item.preco - (item.preco * (perc / 100));
    }
    atualizarTela();
}

function removerItem(index) {
    carrinho.splice(index, 1);
    atualizarTela();
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
    
    if (!isNaN(novoPreco) && novoPreco > precoBase) {
        carrinho[index].preco_original_base = precoBase;
        carrinho[index].preco = novoPreco;
        if (carrinho[index].preco_desconto < precoBase) {
            // Mantém desconto se o gerente já havia dado antes
        } else {
            carrinho[index].preco_desconto = novoPreco; 
        }
    } else if (!isNaN(novoPreco) && novoPreco < precoBase) {
        if(typeof window.mostrarAviso === 'function') window.mostrarAviso("O preço de venda não pode ser menor que o original de tabela.", "aviso");
        else alert("O preço de venda não pode ser menor que o original de tabela.");
        return; 
    }
    
    bootstrap.Modal.getInstance(document.getElementById('modalEditarNomeProduto')).hide();
    atualizarTela();
}

let indexProdutoFalta = null;


function marcarFalta(index) {
    let item = carrinho[index];
    
    if(confirm(`Deseja registrar RUPTURA (Falta de Estoque) para:\n\n${item.nome}\n\nEle será removido do carrinho e a gerência será notificada.`)) {
        fetch('/api/registrar-ruptura/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
            body: JSON.stringify({
                produto_id: item.id,
                produto_nome: item.nome,
                quantidade_perdida: item.qtd
            })
        }).then(res => {
            window.mostrarAviso(`Alerta de Ruptura salvo! O produto foi removido.`, 'sucesso');
        }).catch(err => {
            window.mostrarAviso(`Falta registrada localmente. O produto foi removido.`, 'aviso');
        });

        carrinho.splice(index, 1);
        atualizarTela();
    }
}

// ==========================================
// INTEGRAÇÕES VISUAIS E TINTOMÉTRICO
// ==========================================
function abrirModalMenuTintometrico() {
    document.getElementById('menuSistemasTinto').style.display = 'block';
    document.getElementById('iframeTintometrico').style.display = 'none';
    new bootstrap.Modal(document.getElementById('modalTintometrico')).show();
}

function carregarSistemaTinto(url) {
    document.getElementById('menuSistemasTinto').style.display = 'none';
    let iframe = document.getElementById('iframeTintometrico');
    iframe.src = url;
    iframe.style.display = 'block';
}

window.receberTintaDoIframe = function() {
    bootstrap.Modal.getInstance(document.getElementById('modalTintometrico')).hide();
    let carrinhoPDV = JSON.parse(localStorage.getItem('carrinho')) || [];
    if(carrinhoPDV.length > 0) {
        let ultimaTinta = carrinhoPDV[carrinhoPDV.length - 1];
        if (ultimaTinta.id.toString().startsWith('TINTA-')) {
            carrinho.push(ultimaTinta);
            carrinhoPDV.pop();
            localStorage.setItem('carrinho', JSON.stringify(carrinhoPDV));
        }
    }
    atualizarTela();
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


// ==========================================
// 💾 ENVIAR PEDIDO AO BANCO DE DADOS
// ==========================================
window.VENDA_FINALIZADA_ID = null; // Memória para a impressão

window.salvarPedidoAPI = function(statusDesejado) {
    if (!window.PEDIDO_ABERTO_ID) {
        window.mostrarAviso("Nenhum pedido gerado. Clique em Novo Pedido.", "erro");
        return;
    }

    if (typeof carrinho === 'undefined' || carrinho.length === 0) {
        window.mostrarAviso("Adicione produtos antes de salvar o pedido!", "aviso");
        return;
    }

    let valorFinalText = document.getElementById('txtTotal').innerText.replace('R$ ', '').replace('.', '').replace(',', '.');
    let valorDescontoText = document.getElementById('txtDesconto').innerText.replace('- R$ ', '').replace('.', '').replace(',', '.');
    
    let pacote = {
        pedido_aberto_id: window.PEDIDO_ABERTO_ID, 
        cliente: document.getElementById('selectCliente') ? document.getElementById('selectCliente').value : '',
        indicante: document.getElementById('selectIndicante') ? document.getElementById('selectIndicante').value : '',
        vendedor: document.getElementById('selectVendedor') ? document.getElementById('selectVendedor').value : '',
        status: statusDesejado,
        valor_final: parseFloat(valorFinalText) || 0,
        desconto: parseFloat(valorDescontoText) || 0,
        pontos_resgatados: 0,
        carrinho: carrinho, 
        pagamentos: [], 
        troco: 0
    };

    let obs = document.getElementById('textoObservacoes');
    if (obs) {
        pacote.observacoes = obs.value;
    }

    fetch('/api/salvar-venda/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
        body: JSON.stringify(pacote)
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') {
            if(statusDesejado === 'ABERTO') {
                window.mostrarAviso('Alterações salvas com sucesso! (Rascunho)', 'sucesso');
            } 
            else if(statusDesejado === 'ORCAMENTO') {
                window.mostrarAviso('Orçamento gerado com sucesso!', 'sucesso');
                localStorage.removeItem('carrinho_novo_pedido');
                window.VENDA_FINALIZADA_ID = data.venda_id;
                
                // Abre o Modal de Impressão e trava a tela de fundo
                let modalImpressao = new bootstrap.Modal(document.getElementById('modalImpressao'), {
                    backdrop: 'static',
                    keyboard: false
                });
                modalImpressao.show();
            } 
            else if(statusDesejado === 'FINALIZADO') {
                window.mostrarAviso('Pedido Finalizado e Enviado ao Caixa!', 'sucesso');
                localStorage.removeItem('carrinho_novo_pedido');
                
                // Abre o ticket com código de barras em uma nova aba
                window.open(`/venda/ticket-pedido/${data.venda_id}/`, '_blank');
                
                // Depois redireciona a tela principal de volta para o painel de pedidos
                setTimeout(() => window.location.href = '/paineldepedidos/', 1000); 
            }
        } else {
            window.mostrarAviso("Erro ao salvar: " + data.mensagem, 'erro');
        }
    })
    .catch(err => {
        console.error(err);
        window.mostrarAviso("Erro de conexão. Tente novamente.", 'erro');
    });
};

// ==========================================
// 🖨️ ESCOLHA DE IMPRESSÃO DO ORÇAMENTO
// ==========================================
window.escolherImpressao = function(tipo) {
    if(tipo === 'bobina') {
        window.open(`/venda/cupom/${window.VENDA_FINALIZADA_ID}/`, '_blank');
    } else if(tipo === 'a4') {
        window.open(`/venda/cupom-a4/${window.VENDA_FINALIZADA_ID}/`, '_blank');
    }
    
    // Esconde o modal
    let modalEl = document.getElementById('modalImpressao');
    let modal = bootstrap.Modal.getInstance(modalEl);
    if(modal) modal.hide();
    
    // Redireciona o vendedor de volta para o painel de pedidos
    setTimeout(() => {
        window.location.href = '/paineldepedidos/';
    }, 500);
};

// ==========================================
// 🗑️ CANCELAR PEDIDO E LIMPAR TELA
// ==========================================
window.cancelarPedidoAtual = function() {
    if (!window.PEDIDO_ABERTO_ID) {
        window.location.href = '/paineldepedidos/';
        return;
    }
    let modalEl = document.getElementById('modalCancelarPedido');
    if(modalEl) {
        new bootstrap.Modal(modalEl).show();
    } else {
        window.mostrarAviso("Modal de cancelamento não encontrado.", "erro");
    }
};

window.confirmarCancelamentoPedido = function() {
    let motivo = document.getElementById('motivoCancelamentoPedido').value.trim();
    if (motivo.length < 5) {
        window.mostrarAviso("Digite um motivo válido para o cancelamento (mínimo 5 caracteres).", "aviso");
        return;
    }

    fetch(`/api/pdv/cancelar-pedido/${window.PEDIDO_ABERTO_ID}/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
        body: JSON.stringify({ motivo: motivo })
    }).then(res => res.json()).then(data => {
        if(data.status === 'sucesso'){
            localStorage.removeItem('carrinho_novo_pedido');
            window.location.href = '/paineldepedidos/';
        } else {
            window.mostrarAviso("Erro ao cancelar: " + data.mensagem, "erro");
        }
    });
};

function marcarFaltaPeloModal() {
    if (indexProdutoFalta === null) return;
    let item = carrinho[indexProdutoFalta];
    
    if(confirm(`Deseja registrar RUPTURA (Falta de Estoque) para:\n\n${item.nome}\n\nEle será removido do carrinho e a gerência será notificada.`)) {
        fetch('/api/registrar-ruptura/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
            body: JSON.stringify({
                produto_id: item.id,
                quantidade_perdida: item.qtd
            })
        }).then(res => {
            if(typeof window.mostrarAviso === 'function') window.mostrarAviso(`Alerta de Ruptura salvo! Produto removido.`, 'sucesso');
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
