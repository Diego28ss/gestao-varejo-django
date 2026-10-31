// --- Lógica Geral do Inventário (Criação e Exclusão) ---
function validarFiltros() {
    let count = 0;
    if(document.getElementById('f_marca').value !== "") count++;
    if(document.getElementById('f_familia').value !== "") count++;
    if(document.getElementById('f_unidade').value !== "") count++;

    if(count < 2) {
        window.mostrarAviso("Você deve selecionar pelo menos 2 filtros!", "aviso");
        return false;
    }
    return true;
}

function excluirInventario(id) {
    if(confirm("Tem certeza que deseja apagar este item? (O estoque não será alterado)")) {
        fetch(`/api/inventario/excluir/${id}/`, {
            method: 'POST',
            headers: {'X-CSRFToken': window.CSRF_TOKEN}
        }).then(res => res.json()).then(data => {
            if(data.status === 'sucesso') location.reload();
            else window.mostrarAviso(data.mensagem, 'erro');
        });
    }
}

// --- Lógica da Tela de Bipagem Dinâmica ---
document.addEventListener("DOMContentLoaded", function() {
    let modalEl = document.getElementById('modalOmissos');
    if (modalEl) window.modalOmisso = new bootstrap.Modal(modalEl);
    
    let inputCod = document.getElementById('inputCodigo');
    if (inputCod) inputCod.focus();
});

document.addEventListener('keydown', function(e) {
    const modalEl = document.getElementById('modalOmissos');
    if (modalEl && modalEl.classList.contains('show')) return;
    if (e.ctrlKey || e.altKey || e.metaKey || e.key.startsWith('F')) return;

    if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') return;

    if (e.key.length === 1) {
        const inputCodigo = document.getElementById('inputCodigo');
        if (inputCodigo && document.activeElement !== inputCodigo) {
            inputCodigo.focus();
        }
    }
});

if(document.getElementById('inputCodigo')){
    document.getElementById('inputCodigo').addEventListener('keyup', function(e) { 
        if (e.key === 'Enter') biparProduto(); 
    });
}
if(document.getElementById('inputQtd')){
    document.getElementById('inputQtd').addEventListener('keyup', function(e) { 
        if (e.key === 'Enter') document.getElementById('inputCodigo').focus();
    });
}

function biparProduto() {
    const inputCodigo = document.getElementById('inputCodigo');
    const inputQtd = document.getElementById('inputQtd');
    
    let codigo = inputCodigo.value.trim();
    let qtd = parseInt(inputQtd.value) || 1;
    
    if (codigo === "") {
        inputCodigo.focus();
        return;
    }

    inputCodigo.value = ""; 
    inputQtd.value = 1; 
    inputCodigo.focus(); 

    fetch('/api/inventario/bipar-dinamico/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN}, 
        body: JSON.stringify({ sessao_id: window.sessaoId, codigo: codigo, quantidade: qtd })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') {
            window.mostrarAviso(`${qtd}x ${data.produto_nome} registrado!`, 'sucesso');
            recarregarTabela();
        } else {
            window.mostrarAviso(data.mensagem, 'erro');
        }
    }).catch(() => window.mostrarAviso("Erro de conexão.", "erro"));
}

function atualizarQuantidadeDireta(produtoId, novaQtd) {
    let qtd = parseInt(novaQtd);
    if (isNaN(qtd) || qtd < 0) return window.mostrarAviso("Quantidade inválida.", "erro");

    fetch('/api/inventario/atualizar-qtd-dinamico/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
        body: JSON.stringify({ sessao_id: window.sessaoId, produto_id: produtoId, quantidade: qtd })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') recarregarTabela();
        else window.mostrarAviso(data.mensagem, 'erro');
    }).catch(() => window.mostrarAviso("Erro de conexão ao atualizar.", "erro"));
}

function reduzirProduto(produtoId) {
    fetch('/api/inventario/reduzir-dinamico/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
        body: JSON.stringify({ sessao_id: window.sessaoId, produto_id: produtoId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') recarregarTabela();
        else window.mostrarAviso(data.mensagem, 'erro');
    }).catch(() => window.mostrarAviso("Erro de conexão ao remover item.", "erro"));
}

function recarregarTabela() {
    fetch(window.location.href).then(response => response.text()).then(html => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        document.getElementById('tabelaItens').innerHTML = doc.getElementById('tabelaItens').innerHTML;
    });
}

function iniciarRevisaoOmissos() {
    let btn = document.getElementById('btnIniciarRevisao');
    let txtOriginal = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Verificando...';
    btn.disabled = true;

    fetch(`/api/inventario/revisao-omissos/${window.sessaoId}/`)
    .then(res => res.json())
    .then(data => {
        btn.innerHTML = txtOriginal;
        btn.disabled = false;

        if (data.status === 'sucesso') {
            if (data.omissos.length === 0) {
                enviarFinalizacao('IGNORAR');
            } else {
                let html = '';
                data.omissos.forEach(o => {
                    html += `<tr><td class="text-start ps-3 fw-bold">${o.nome}</td><td class="text-danger fw-bold fs-6">${o.saldo_sistema} un.</td></tr>`;
                });
                document.getElementById('listaOmissosModal').innerHTML = html;
                window.modalOmisso.show();
            }
        } else {
            window.mostrarAviso(data.mensagem, 'erro');
        }
    }).catch(err => {
        btn.innerHTML = txtOriginal;
        btn.disabled = false;
        window.mostrarAviso("Falha ao buscar itens não contados.", "erro");
    });
}

function enviarFinalizacao(acao_direta = null) {
    let acao = acao_direta;
    
    if (!acao) {
        const opcao = document.querySelector('input[name="radioOmissos"]:checked');
        acao = opcao ? opcao.value : 'IGNORAR';
    }

    let btn = document.getElementById('btnConcluirInventario');
    if (btn) {
        btn.innerHTML = "⏳ FINALIZANDO...";
        btn.disabled = true;
    }

    fetch(`/api/inventario/finalizar-dinamico/${window.sessaoId}/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
        body: JSON.stringify({ acao_omissos: acao })
    })
    .then(res => res.json())
    .then(data => {
        if(data.status === 'sucesso') {
            window.location.href = data.url;
        } else {
            window.mostrarAviso(data.mensagem, 'erro');
            if (btn) { 
                btn.innerHTML = '<i class="bi bi-database-check"></i> Aplicar Matemática e Concluir'; 
                btn.disabled = false; 
            }
        }
    }).catch(err => {
        window.mostrarAviso("Erro fatal de conexão ao finalizar.", "erro");
        if (btn) { 
            btn.innerHTML = '<i class="bi bi-database-check"></i> Aplicar Matemática e Concluir'; 
            btn.disabled = false; 
        }
    });
}
