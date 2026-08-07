let carrinhoGerente = JSON.parse(localStorage.getItem('carrinhoGerente')) || [];

document.addEventListener('DOMContentLoaded', function() {
    renderizarCarrinhoGerente();
});

function renderizarCarrinhoGerente() {
    let tbody = document.getElementById('tabelaCarrinhoGerente');
    let html = '';

    if (carrinhoGerente.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="p-5 text-center text-muted fw-bold fs-5">
                    <i class="bi bi-cart-x display-4 d-block mb-3 text-secondary"></i>
                    Seu carrinho de pedidos está vazio.
                </td>
            </tr>`;
        document.getElementById('btnFinalizarCarrinho').disabled = true;
        return;
    }

    document.getElementById('btnFinalizarCarrinho').disabled = false;

    carrinhoGerente.forEach((item, index) => {
        html += `
        <tr>
            <td class="text-start ps-4 fw-bold text-dark">${item.nome}</td>
            <td>
                <input type="number" class="form-control form-control-sm text-center fw-bold" value="${item.qtd}" min="1" onchange="alterarQtdItem(${index}, this.value)">
            </td>
            <td>
                <input type="date" class="form-control form-control-sm text-center" value="${item.data}" onchange="alterarDataItem(${index}, this.value)">
            </td>
            <td>
                <button class="btn btn-sm btn-outline-danger p-1 shadow-sm" title="Remover item" onclick="removerItemCarrinho(${index})">
                    <i class="bi bi-trash-fill fs-6"></i>
                </button>
            </td>
        </tr>`;
    });

    tbody.innerHTML = html;
}

function alterarQtdItem(index, novaQtd) {
    let qtd = parseInt(novaQtd);
    if (qtd > 0) {
        carrinhoGerente[index].qtd = qtd;
        localStorage.setItem('carrinhoGerente', JSON.stringify(carrinhoGerente));
    }
}

function alterarDataItem(index, novaData) {
    if (novaData) {
        carrinhoGerente[index].data = novaData;
        localStorage.setItem('carrinhoGerente', JSON.stringify(carrinhoGerente));
    }
}

function removerItemCarrinho(index) {
    carrinhoGerente.splice(index, 1);
    localStorage.setItem('carrinhoGerente', JSON.stringify(carrinhoGerente));
    renderizarCarrinhoGerente();
}

function cancelarCarrinhoGerente() {
    if (confirm("Deseja realmente cancelar o pedido? Todos os itens voltarão para a lista de suprimento.")) {
        localStorage.removeItem('carrinhoGerente');
        window.location.href = window.CARRINHO_CONFIG.urlSuprirEstoque;
    }
}

// Dispara o envio em massa para o banco de dados
function finalizarCarrinhoGerente() {
    if (carrinhoGerente.length === 0) return;

    let btn = document.getElementById('btnFinalizarCarrinho');
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Processando Pedido...';
    btn.disabled = true;

    // Envia o array inteiro para uma nova API que criaremos a seguir
    fetch('/api/finalizar-carrinho-gerente/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.CARRINHO_CONFIG.csrfToken
        },
        body: JSON.stringify({ itens: carrinhoGerente })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') {
            localStorage.removeItem('carrinhoGerente');
            alert("Pedido finalizado com sucesso! Os produtos foram atualizados para o status 'em trânsito'.");
            window.location.href = window.CARRINHO_CONFIG.urlSuprirEstoque;
        } else {
            alert("Erro ao finalizar pedido: " + data.mensagem);
            btn.innerHTML = '<i class="bi bi-check2-all me-2"></i> Finalizar Compra e Enviar';
            btn.disabled = false;
        }
    })
    .catch(err => {
        alert("Erro de conexão com o servidor.");
        btn.innerHTML = '<i class="bi bi-check2-all me-2"></i> Finalizar Compra e Enviar';
        btn.disabled = false;
    });
}
