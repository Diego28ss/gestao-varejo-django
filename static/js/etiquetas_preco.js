let filaImpressao = [];
let codigosNaoEncontrados = [];

document.addEventListener("DOMContentLoaded", function() {
    const filaSalva = localStorage.getItem('jb_fila_etiquetas');
    const falhosSalvos = localStorage.getItem('jb_codigos_falhos');
    
    if (filaSalva) {
        try { filaImpressao = JSON.parse(filaSalva); } catch (e) { filaImpressao = []; }
    }
    if (falhosSalvos) {
        try { codigosNaoEncontrados = JSON.parse(falhosSalvos); } catch (e) { codigosNaoEncontrados = []; }
    }
    
    renderizarTabela();
    atualizarBadgeNaoEncontrados();

    const inputBusca = document.getElementById('inputBuscaProduto');
    if(inputBusca) {
        inputBusca.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') buscarProdutoReal();
        });
    }

    document.addEventListener('click', function(event) {
        const listaResultados = document.getElementById('listaResultados');
        const inptBusca = document.getElementById('inputBuscaProduto');
        if (inptBusca && listaResultados && !inptBusca.contains(event.target) && !listaResultados.contains(event.target)) {
            listaResultados.style.display = 'none';
        }
    });
});

function salvarFilaLocal() {
    localStorage.setItem('jb_fila_etiquetas', JSON.stringify(filaImpressao));
}

function salvarFalhosLocal() {
    localStorage.setItem('jb_codigos_falhos', JSON.stringify(codigosNaoEncontrados));
    atualizarBadgeNaoEncontrados();
}

function atualizarSelecao() {
    document.querySelectorAll('.card-modelo').forEach(c => c.classList.remove('selected'));
    const selecionado = document.querySelector('input[name="modelo_etiqueta"]:checked');
    if (selecionado) {
        document.getElementById('card-' + selecionado.value).classList.add('selected');
    }
}

function buscarProdutoReal() {
    const inputBusca = document.getElementById('inputBuscaProduto');
    const listaResultados = document.getElementById('listaResultados');
    const termo = inputBusca.value.trim();
    if (termo === '') return;

    fetch('/api/etiquetas/buscar-produto/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
        body: JSON.stringify({ termo: termo })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'exato') {
            adicionarNaFila(data.produto);
            inputBusca.value = '';
            listaResultados.style.display = 'none';
            inputBusca.focus();
        } else if (data.status === 'lista' && data.produtos.length > 0) {
            mostrarLista(data.produtos);
        } else {
            window.mostrarAviso(`Código ${termo} não encontrado!`, "erro");
            listaResultados.style.display = 'none';
            
            if (!codigosNaoEncontrados.includes(termo)) {
                codigosNaoEncontrados.push(termo);
                salvarFalhosLocal();
            }

            inputBusca.value = '';
            inputBusca.focus();
        }
    })
    .catch(() => window.mostrarAviso("Erro na conexão.", "erro"));
}

function mostrarLista(produtos) {
    const listaResultados = document.getElementById('listaResultados');
    const inputBusca = document.getElementById('inputBuscaProduto');
    listaResultados.innerHTML = '';
    
    produtos.forEach(p => {
        let li = document.createElement('li');
        li.className = 'list-group-item list-group-item-action'
        li.style.cursor = 'pointer';
        li.innerHTML = `<div class="d-flex justify-content-between align-items-center">
                            <div><strong class="text-dark">${p.nome}</strong><br><small class="text-muted fw-bold">${p.codigo}</small></div>
                            <span class="badge bg-success shadow-sm">R$ ${p.preco}</span>
                        </div>`;
        li.onclick = () => {
            adicionarNaFila(p);
            inputBusca.value = '';
            listaResultados.style.display = 'none';
            inputBusca.focus();
        };
        listaResultados.appendChild(li);
    });
    listaResultados.style.display = 'block';
}

function adicionarNaFila(produto) {
    let index = filaImpressao.findIndex(p => p.id === produto.id);
    if (index > -1) {
        filaImpressao[index].qtd += 1; 
    } else {
        filaImpressao.push({...produto, qtd: 1});
    }
    salvarFilaLocal();
    renderizarTabela();
}

function removerProduto(index) {
    filaImpressao.splice(index, 1);
    salvarFilaLocal();
    renderizarTabela();
}

function alterarQtd(index, valor) {
    let novaQtd = parseInt(valor);
    if (novaQtd > 0) {
        filaImpressao[index].qtd = novaQtd;
        salvarFilaLocal();
    }
}

function limparFila() {
    filaImpressao = [];
    localStorage.removeItem('jb_fila_etiquetas');
    renderizarTabela();
}

function renderizarTabela() {
    const tbody = document.getElementById('tabelaFila');
    
    if (filaImpressao.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="py-5 text-muted fw-bold"><i class="bi bi-upc-scan fs-3 d-block mb-2 text-secondary"></i>Nenhum produto na fila.</td></tr>`;
        return;
    }

    tbody.innerHTML = '';
    filaImpressao.forEach((prod, index) => {
        tbody.innerHTML += `
            <tr>
                <td class="text-start ps-3 fw-bold text-dark" style="font-size: 0.85rem;">${prod.nome}</td>
                <td class="text-secondary fw-bold">${prod.codigo}</td>
                <td class="text-success fw-bold">R$ ${prod.preco}</td>
                <td>
                    <input type="number" class="form-control form-control-sm text-center fw-bold border-secondary mx-auto shadow-sm" 
                           value="${prod.qtd}" min="1" onchange="alterarQtd(${index}, this.value)" style="max-width: 80px;">
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-danger shadow-sm fw-bold" onclick="removerProduto(${index})">
                        <i class="bi bi-trash-fill"></i>
                    </button>
                </td>
            </tr>
        `;
    });
}

function atualizarBadgeNaoEncontrados() {
    document.getElementById('badgeNaoEncontrados').innerText = codigosNaoEncontrados.length;
}

function abrirModalNaoEncontrados() {
    const ul = document.getElementById('listaCodigosFalhos');
    ul.innerHTML = '';

    if (codigosNaoEncontrados.length === 0) {
        ul.innerHTML = '<li class="list-group-item text-center text-muted fw-bold py-4">Nenhum código falhou nesta sessão.</li>';
    } else {
        codigosNaoEncontrados.forEach((codigo, index) => {
            ul.innerHTML += `
                <li class="list-group-item d-flex justify-content-between align-items-center fw-bold text-danger">
                    <span><i class="bi bi-upc-scan me-2 text-secondary"></i> ${codigo}</span>
                    <button class="btn btn-sm btn-outline-secondary border-0" onclick="removerFalho(${index})" title="Remover da lista">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </li>
            `;
        });
    }
    new bootstrap.Modal(document.getElementById('modalNaoEncontrados')).show();
}

function removerFalho(index) {
    codigosNaoEncontrados.splice(index, 1);
    salvarFalhosLocal();
    abrirModalNaoEncontrados(); 
}

function limparListaNaoEncontrados() {
    codigosNaoEncontrados = [];
    localStorage.removeItem('jb_codigos_falhos');
    atualizarBadgeNaoEncontrados();
    abrirModalNaoEncontrados(); 
}

function gerarPDF() {
    if (filaImpressao.length === 0) {
        window.mostrarAviso("Adicione pelo menos um produto na fila para gerar as etiquetas.", "erro");
        return;
    }
    
    const selecionado = document.querySelector('input[name="modelo_etiqueta"]:checked');
    const modelo = selecionado ? selecionado.value : 'PEQUENO';
    let btn = document.querySelector('button[onclick="gerarPDF()"]');
    let txtOriginal = btn.innerHTML;
    
    btn.innerHTML = "⏳ ABRINDO PDF...";
    btn.disabled = true;

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/api/etiquetas/gerar-pdf/';
    form.target = '_blank';

    let inputs = [
        {name: 'csrfmiddlewaretoken', value: window.CSRF_TOKEN},
        {name: 'payload', value: JSON.stringify({ modelo: modelo, produtos: filaImpressao })}
    ];

    inputs.forEach(item => {
        let input = document.createElement('input');
        input.type = 'hidden';
        input.name = item.name;
        input.value = item.value;
        form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);

    setTimeout(() => {
        btn.innerHTML = txtOriginal;
        btn.disabled = false;
    }, 1000);
}
