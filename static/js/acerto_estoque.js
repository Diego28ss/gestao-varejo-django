let produtoAtual = null;
let timeoutBusca = null;

// ==========================================
// 1. BUSCA INTELIGENTE DE PRODUTO
// ==========================================
document.getElementById('inputBuscaGeral').addEventListener('input', function () {
    clearTimeout(timeoutBusca);
    let query = this.value.trim();
    let lista = document.getElementById('listaResultados');

    if (query.length < 2) {
        lista.style.display = 'none';
        return;
    }

    timeoutBusca = setTimeout(() => {
        // Usa a mesma rota poderosa do PDV para buscar por nome/ean/codigo
        fetch(`/api/buscar-produtos/?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                lista.innerHTML = '';
                if (data.produtos && data.produtos.length > 0) {
                    data.produtos.forEach(p => {
                        let li = document.createElement('li');
                        li.className = 'list-group-item list-group-item-action cursor-pointer p-3';
                        li.innerHTML = `
                            <div class="d-flex justify-content-between align-items-center">
                                <div><strong class="text-primary">${p.cod_interno}</strong> - <span class="fw-bold">${p.nome}</span><br>
                                <small class="text-muted"><i class="bi bi-upc"></i> EAN: ${p.cod_barras || 'N/A'}</small></div>
                                <span class="badge bg-secondary fs-6">Saldo: ${p.estoque_atual}</span>
                            </div>`;
                        li.onclick = () => selecionarProduto(p);
                        lista.appendChild(li);
                    });
                    lista.style.display = 'block';
                } else {
                    lista.innerHTML = '<li class="list-group-item text-muted p-3">Nenhum produto encontrado.</li>';
                    lista.style.display = 'block';
                }
            })
            .catch(err => console.error(err));
    }, 300);
});

// Fecha lista ao clicar fora
document.addEventListener('click', function (e) {
    if (e.target.id !== 'inputBuscaGeral') {
        document.getElementById('listaResultados').style.display = 'none';
    }
});

// ==========================================
// 2. TRAVAR PRODUTO E LIBERAR TELA
// ==========================================
function selecionarProduto(p) {
    produtoAtual = p;

    // Atualiza Layout Visual
    document.getElementById('lblNomeProduto').innerText = p.nome;
    document.getElementById('lblCodInterno').innerText = p.cod_interno || 'S/N';
    document.getElementById('lblCodBarras').innerText = p.cod_barras || 'S/N';
    document.getElementById('lblSaldoSistema').innerText = p.estoque_atual;

    // Alimenta Inputs Iniciais
    document.getElementById('inputQtdManual').value = p.estoque_atual;
    document.getElementById('inputMotivo').value = '';
    calcularVariacao();

    // Troca os Cartões
    document.getElementById('cardBusca').classList.add('d-none');
    document.getElementById('cardAcerto').classList.remove('d-none');

    // Foca automaticamente no bipador
    let inputBipador = document.getElementById('inputBipador');
    inputBipador.value = '';
    inputBipador.focus();
}

function cancelarAcerto() {
    produtoAtual = null;
    document.getElementById('cardAcerto').classList.add('d-none');

    let busca = document.getElementById('cardBusca');
    busca.classList.remove('d-none');

    let inputBusca = document.getElementById('inputBuscaGeral');
    inputBusca.value = '';
    inputBusca.focus();
}

// ==========================================
// 3. REGRAS DE BIPAGEM CONTÍNUA
// ==========================================
document.getElementById('inputBipador').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        let lido = this.value.trim();
        this.value = ''; // Limpa rápido pro próximo bip

        if (!produtoAtual) return;

        // VALIDAÇÃO EXTREMA: Só aceita se for o EAN ou Cód. Interno do produto travado
        if (lido === produtoAtual.cod_barras || lido === produtoAtual.cod_interno) {
            let inputQtd = document.getElementById('inputQtdManual');
            let qtdAtual = parseInt(inputQtd.value) || 0;
            inputQtd.value = qtdAtual + 1;
            calcularVariacao();

            // Pisca verde
            this.classList.add('is-valid', 'bg-success', 'text-white');
            setTimeout(() => this.classList.remove('is-valid', 'bg-success', 'text-white'), 200);
        } else {
            if (typeof window.mostrarAviso === 'function') {
                window.mostrarAviso("O código lido não pertence a este produto!", "erro");
            } else {
                alert("O código lido não pertence a este produto!");
            }
            // Pisca vermelho
            this.classList.add('is-invalid');
            setTimeout(() => this.classList.remove('is-invalid'), 500);
        }
    }
});

function calcularVariacao() {
    if (!produtoAtual) return;
    let novaQtd = parseInt(document.getElementById('inputQtdManual').value) || 0;
    let saldoAntigo = parseInt(produtoAtual.estoque_atual) || 0;
    let variacao = novaQtd - saldoAntigo;

    let lbl = document.getElementById('lblVariacao');
    if (variacao > 0) {
        lbl.innerHTML = `<span class="text-success"><i class="bi bi-arrow-up-circle"></i> Var: +${variacao} (Entrada)</span>`;
    } else if (variacao < 0) {
        lbl.innerHTML = `<span class="text-danger"><i class="bi bi-arrow-down-circle"></i> Var: ${variacao} (Saída)</span>`;
    } else {
        lbl.innerHTML = `<span class="text-muted"><i class="bi bi-dash-circle"></i> Var: 0 (Sem alteração)</span>`;
    }
}

// ==========================================
// 4. SALVAR E VOLTAR PARA A BUSCA
// ==========================================
function salvarAcerto() {
    if (!produtoAtual) return;

    let novaQtd = document.getElementById('inputQtdManual').value;
    let motivo = document.getElementById('inputMotivo').value.trim();

    if (novaQtd === '') {
        window.mostrarAviso("A quantidade manual não pode ficar vazia.", "erro");
        return;
    }

    let payload = [{
        id: produtoAtual.id,
        nova_qtd: parseInt(novaQtd),
        motivo: motivo || 'Acerto Dinâmico Rápido'
    }];

    let btnSalvar = document.getElementById('btnSalvarAcerto');
    let textoOriginal = btnSalvar.innerHTML;
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Gravando Auditoria...';

    fetch('/api/processar-acerto-estoque/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ itens: payload })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'sucesso') {
                if (typeof window.mostrarAviso === 'function') window.mostrarAviso(data.mensagem, "sucesso");
                cancelarAcerto(); // Reseta tudo para bipar o próximo produto!
            } else {
                if (typeof window.mostrarAviso === 'function') window.mostrarAviso(data.mensagem, "erro");
            }
        })
        .catch(err => {
            console.error(err);
            if (typeof window.mostrarAviso === 'function') window.mostrarAviso("Falha no servidor ao salvar.", "erro");
        })
        .finally(() => {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = textoOriginal;
        });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        let cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
