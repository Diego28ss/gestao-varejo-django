// Inicia o carrinho lendo do LocalStorage (igual ao PDV)
let carrinhoGerente = JSON.parse(localStorage.getItem('carrinhoGerente')) || [];
let produtoIdSelecionado = null;
let nomeProdutoSelecionado = "";
let modalEncomenda = null;

// Ao carregar a página, atualiza o contador e esconde os itens que já estão no carrinho
document.addEventListener('DOMContentLoaded', function() {
    atualizarContadorCarrinho();
    ocultarItensJaNoCarrinho();
});

// Abre o Modal, insere o nome do produto e sugere a quantidade
function abrirModalEncomenda(produtoId, produtoNome, qtdSugerida) {
    produtoIdSelecionado = produtoId;
    nomeProdutoSelecionado = produtoNome;
    
    // Reseta os campos e coloca a quantidade sugerida pelo sistema
    document.getElementById('qtdEncomenda').value = qtdSugerida > 0 ? qtdSugerida : 1;
    
    // Sugere a data de hoje por padrão para facilitar
    document.getElementById('dataPrevisao').valueAsDate = new Date();
    document.getElementById('nomeProdutoModal').innerText = produtoNome;
    
    if (!modalEncomenda) {
        modalEncomenda = new bootstrap.Modal(document.getElementById('modalRegistrarEncomenda'));
    }
    modalEncomenda.show();
}

// Ação de Colocar no Carrinho (Local)
document.getElementById('btnConfirmarEncomenda').addEventListener('click', function() {
    if (!produtoIdSelecionado) return;

    let qtd = parseInt(document.getElementById('qtdEncomenda').value);
    let data = document.getElementById('dataPrevisao').value;

    if(!qtd || !data) {
        alert("Por favor, preencha a quantidade e a data de previsão.");
        return;
    }

    // Verifica se o item já existe no carrinho para atualizar, senão adiciona um novo
    let itemExistente = carrinhoGerente.find(i => i.id === produtoIdSelecionado);
    if (itemExistente) {
        itemExistente.qtd = qtd;
        itemExistente.data = data;
    } else {
        carrinhoGerente.push({
            id: produtoIdSelecionado,
            nome: nomeProdutoSelecionado,
            qtd: qtd,
            data: data
        });
    }

    // Salva no navegador
    localStorage.setItem('carrinhoGerente', JSON.stringify(carrinhoGerente));

    // Esconde o modal
    modalEncomenda.hide();

    // Remove a linha visualmente da tela para o gerente saber que já processou
    let linha = document.getElementById(`linha-produto-${produtoIdSelecionado}`);
    if(linha) {
        linha.classList.add('opacity-50'); // Dá um efeitinho visual antes de sumir
        setTimeout(() => linha.remove(), 300);
    }

    atualizarContadorCarrinho();
});

// Função para atualizar o número na bolinha vermelha do botão do carrinho
function atualizarContadorCarrinho() {
    let contador = document.getElementById('contadorCarrinhoGerente');
    if(contador) {
        if (carrinhoGerente.length > 0) {
            contador.innerText = carrinhoGerente.length;
            contador.style.display = 'block';
        } else {
            contador.style.display = 'none';
        }
    }
}

// Função de segurança: se o gerente der F5 na página, 
// o JS varre a tabela e esconde os itens que já estão no carrinho
function ocultarItensJaNoCarrinho() {
    carrinhoGerente.forEach(item => {
        let linha = document.getElementById(`linha-produto-${item.id}`);
        if(linha) linha.remove();
    });
}
