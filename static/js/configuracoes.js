let modalAuxiliarInstancia;

// Inicializa o modal nativo do Bootstrap assim que o DOM carregar
document.addEventListener("DOMContentLoaded", function() {
    const modalEl = document.getElementById('modalAuxiliar');
    if(modalEl) {
        modalAuxiliarInstancia = new bootstrap.Modal(modalEl);
    }
});

// ============================================================
// --- FUNÇÕES DA COLUNA ESQUERDA (CONFIGS GLOBAIS) ---
// ============================================================

window.habilitarEdicaoDias = function() {
    let inputDias = document.getElementById('inputDias');
    if(inputDias) {
        // Destrava o input
        inputDias.disabled = false;
        
        // Aplica o design de edição original (Destaque visual)
        inputDias.style.backgroundColor = "#fffdf5"; 
        inputDias.style.color = "#198754"; 
        inputDias.style.borderColor = "#ffc107"; 
        
        inputDias.focus();
        
        // Dispara a exibição do botão de salvar global
        window.mostrarBotaoSalvarGlobal();
    }
};

window.mostrarBotaoSalvarGlobal = function() {
    const divSalvar = document.getElementById('divSalvarGlobal');
    if(divSalvar) {
        divSalvar.classList.remove('d-none');
    }
};

// ============================================================
// --- FUNÇÕES DA COLUNA DIREITA (TABELAS AUXILIARES VIA AJAX) ---
// ============================================================

window.abrirModalAuxiliar = function(tabela, titulo, id = '', nome = '') {
    document.getElementById('auxTabela').value = tabela;
    document.getElementById('auxAcao').value = id === '' ? 'adicionar' : 'editar';
    document.getElementById('auxId').value = id;
    document.getElementById('auxNome').value = nome;
    document.getElementById('modalAuxiliarTitulo').innerText = titulo;
    
    if(modalAuxiliarInstancia) {
        modalAuxiliarInstancia.show();
    }
    
    // Pequeno atraso para dar foco no input após o modal terminar a animação de abertura
    setTimeout(() => {
        const inputNome = document.getElementById('auxNome');
        if(inputNome) inputNome.focus();
    }, 400);
};

window.salvarAuxiliar = async function() {
    const tabela = document.getElementById('auxTabela').value;
    const acao = document.getElementById('auxAcao').value;
    const id = document.getElementById('auxId').value;
    const nome = document.getElementById('auxNome').value.trim().toUpperCase();

    if(!nome) { 
        alert('O nome / descrição é obrigatório!'); 
        return; 
    }

    enviarRequisicaoAuxiliar(acao, tabela, id, nome);
};

window.excluirAuxiliar = function(tabela, id, nome) {
    if(confirm(`ATENÇÃO: Deseja realmente excluir o registro "${nome}"?\nProdutos vinculados a ele no estoque poderão apresentar erros de referência.`)) {
        enviarRequisicaoAuxiliar('excluir', tabela, id, '');
    }
};

// ============================================================
// --- COMUNICAÇÃO COM O BACKEND (API) ---
// ============================================================

async function enviarRequisicaoAuxiliar(acao, tabela, id, nome) {
    const csrfToken = window.CSRF_TOKEN;
    const urlApi = window.API_AUXILIARES_URL || '/api/auxiliares/'; // Puxa a URL dinâmica
    
    // Resolve o erro do Bootstrap (aria-hidden): tira o foco do botão antes da requisição
    if (document.activeElement) {
        document.activeElement.blur();
    }
    
    try {
        const res = await fetch(urlApi, { 
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json', 
                'X-CSRFToken': csrfToken 
            },
            body: JSON.stringify({ acao, tabela, id, nome })
        });
        
        // Se o servidor devolver 404 ou 500, barramos aqui antes de dar erro de JSON (<)
        if (!res.ok) {
            throw new Error(`Erro no servidor (Status: ${res.status}). Verifique o urls.py.`);
        }
        
        const data = await res.json();
        
        if(data.sucesso) {
            // Recarrega a página para atualizar as listas e refletir a modificação
            location.reload(); 
        } else {
            alert("Erro do Sistema: " + data.erro);
        }
    } catch(e) {
        console.error("Erro na requisição API:", e);
        alert("Erro de comunicação com o servidor: " + e.message);
    }
}
