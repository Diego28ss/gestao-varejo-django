// ==========================================
// 📥 MÓDULO DE ENTRADA DE CARGA (XML NFe)
// Caminho: static/js/entrada_carga.js
// ==========================================

let notaAtual = null;

document.addEventListener("DOMContentLoaded", function() {
    // Configura o evento do input de ficheiro assim que a tela carrega
    const inputXml = document.getElementById('inputXml');
    if (inputXml) {
        inputXml.addEventListener('change', processarImportacaoXML);
    }
});

function processarImportacaoXML(event) {
    let file = event.target.files[0];
    if (!file) return;

    if (!window.CSRF_TOKEN) {
        alert("Erro de segurança: Token CSRF não encontrado.");
        return;
    }

    let formData = new FormData();
    formData.append('xml_file', file);

    // Seleciona o botão de importar para mostrar o "Carregando"
    let btnImportar = document.getElementById('btnImportarXml');
    let originalText = btnImportar.innerHTML;
    btnImportar.innerHTML = '<i class="bi bi-hourglass-split"></i> A LER XML...';
    btnImportar.disabled = true;

    // Envia o ficheiro para o Python processar
    fetch('/api/importar-xml/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': window.CSRF_TOKEN
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // Restaura o botão
        btnImportar.innerHTML = originalText;
        btnImportar.disabled = false;
        event.target.value = ''; // Limpa o input de ficheiro

        if (data.erro) {
            alert("Erro ao importar: " + data.erro);
            return;
        }

        // Sucesso! Guarda a nota na memória e renderiza na tela
        notaAtual = data.nota;
        console.log("XML Processado com Sucesso:", notaAtual);
        alert(`✅ NFe Nº ${notaAtual.numero} de ${notaAtual.fornecedor_nome} importada com sucesso!`);
        
        atualizarListaDeNotas(notaAtual);
    })
    .catch(error => {
        console.error("Erro na requisição Fetch:", error);
        alert("Falha de comunicação com o servidor ao enviar o XML.");
        btnImportar.innerHTML = originalText;
        btnImportar.disabled = false;
        event.target.value = '';
    });
}

// --- FUNÇÕES DE INTERFACE (UI) ---

function atualizarListaDeNotas(nota) {
    let tbody = document.querySelector('#tela-lista-notas tbody');
    
    if (tbody.innerHTML.includes("Pendente")) {
        tbody.innerHTML = ''; 
    }

    let tr = document.createElement('tr');
    tr.innerHTML = `
        <td><span class="badge bg-warning text-dark shadow-sm">Nova Importação</span></td>
        <td class="fw-bold text-primary">${nota.numero}</td>
        <td class="text-start fw-bold">${nota.fornecedor_nome}</td>
        <td>${nota.data}</td>
        <td class="text-success fw-bold fs-6">R$ ${parseFloat(nota.valor_total).toFixed(2).replace('.', ',')}</td>
        <td>
            <button class="btn btn-sm btn-primary shadow-sm fw-bold" onclick="abrirDetalhesNota()" title="Conferir Nota">
                ✏️ Conferir
            </button>
        </td>
    `;
    
    tbody.appendChild(tr);
}

function abrirDetalhesNota() {
    document.getElementById('tela-lista-notas').style.display = 'none';
    document.getElementById('tela-detalhes-nota').style.display = 'block';
    
    if(notaAtual) {
        preencherTelaDetalhes(notaAtual);
    }
}

function preencherTelaDetalhes(nota) {
    // 1. Injetar Dados no Cabeçalho
    document.getElementById('lbl-numero-nota').innerText = nota.numero;
    document.getElementById('lbl-data-emissao').innerText = nota.data;
    document.getElementById('lbl-fornecedor-nome').innerText = nota.fornecedor_nome;
    document.getElementById('lbl-fornecedor-cnpj').innerText = nota.fornecedor_cnpj;
    
    let valorTotalFormatado = parseFloat(nota.valor_total).toFixed(2).replace('.', ',');
    document.getElementById('lbl-valor-total').innerText = "R$ " + valorTotalFormatado;
    document.getElementById('lbl-valor-produtos').innerText = "R$ " + valorTotalFormatado;

    // 2. Injetar a Tabela de Produtos Dinâmica
    let tbody = document.getElementById('tbody-produtos');
    tbody.innerHTML = ''; // Limpa antes de preencher

    nota.produtos.forEach(p => {
        let tr = document.createElement('tr');
        
        let vUnit = parseFloat(p.v_unitario).toFixed(2).replace('.', ',');
        let vTot = parseFloat(p.v_total).toFixed(2).replace('.', ',');

        tr.innerHTML = `
            <td class="text-muted">${p.codigo_fornecedor}</td>
            <td class="text-start fw-bold" style="font-size: 0.8rem;">${p.descricao}</td>
            <td>
                <input type="text" class="form-control form-control-sm text-center" value="${p.cfop_origem}" style="width: 55px; margin: 0 auto; font-size: 0.8rem;">
            </td>
            <td><span class="badge bg-secondary">${p.qtd} ${p.unidade}</span></td>
            <td>R$ ${vUnit}</td>
            <td class="fw-bold text-success">R$ ${vTot}</td>
            
            <td style="border-left: 3px solid #0D1B4C;">
                <div class="input-group input-group-sm" style="width: 120px; margin: 0 auto;">
                    <input type="text" class="form-control text-center fw-bold" placeholder="Cód. JB" id="cod-int-${p.id_linha}">
                    <button class="btn btn-outline-secondary" type="button" title="Procurar Produto" onclick="abrirModalPesquisa(${p.id_linha})">🔍</button>
                </div>
            </td>
            <td>
                <input type="number" class="form-control form-control-sm text-center" value="1" style="width: 55px; margin: 0 auto;">
            </td>
            <td><span class="badge bg-success">${p.qtd} UN</span></td>
            <td>
                <button class="btn btn-sm btn-warning fw-bold text-dark w-100 shadow-sm" id="btn-liberar-${p.id_linha}" onclick="liberarItem(${p.id_linha})">
                    ⏳ Liberar
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function voltarParaLista() {
    document.getElementById('tela-detalhes-nota').style.display = 'none';
    document.getElementById('tela-lista-notas').style.display = 'block';
}


function liberarItem(idItemTabela) {
    let btn = document.getElementById('btn-liberar-' + idItemTabela);
    if (btn.innerText.includes("⏳")) {
        btn.innerHTML = "✅ Liberado";
        btn.classList.remove('btn-warning');
        btn.classList.add('btn-success', 'text-white');
    } else {
        btn.innerHTML = "⏳ Liberar";
        btn.classList.remove('btn-success', 'text-white');
        btn.classList.add('btn-warning');
    }
}
// ==========================================
// MOTOR DE PESQUISA E VÍNCULO (DE/PARA)
// ==========================================
let modalPesquisa = null;

document.addEventListener("DOMContentLoaded", function() {
    let elModal = document.getElementById('modalPesquisaProduto');
    if (elModal) modalPesquisa = new bootstrap.Modal(elModal);
});

function abrirModalPesquisa(linhaId) {
    document.getElementById('linhaAlvoVinculo').value = linhaId;
    document.getElementById('inputBuscaJB').value = '';
    document.getElementById('listaResultadosJB').innerHTML = '<div class="text-center p-3 text-muted small">Digite algo para pesquisar...</div>';
    
    if (modalPesquisa) modalPesquisa.show();
    
    // Foca automaticamente no campo de pesquisa
    setTimeout(() => document.getElementById('inputBuscaJB').focus(), 500);
}

function buscarProdutoJB(event) {
    // Só pesquisa se carregar no Enter ou clicar no botão
    if (event.key !== 'Enter' && event.type !== 'click') return;
    
    let q = document.getElementById('inputBuscaJB').value;
    if (q.length < 2) return;

    document.getElementById('listaResultadosJB').innerHTML = '<div class="text-center p-3 text-primary fw-bold"><i class="bi bi-hourglass-split"></i> A buscar...</div>';

    fetch(`/api/pesquisar-produto-nfe/?q=${encodeURIComponent(q)}`)
    .then(res => res.json())
    .then(data => {
        let html = '';
        if (data.produtos.length === 0) {
            html = '<div class="text-center p-3 text-danger fw-bold">Nenhum produto encontrado.</div>';
        } else {
            data.produtos.forEach(p => {
                html += `
                <button type="button" class="list-group-item list-group-item-action" onclick="selecionarProdutoJB('${p.cod_interno}')">
                    <div class="d-flex justify-content-between align-items-center">
                        <strong>${p.nome}</strong>
                        <span class="badge bg-secondary">Cód: ${p.cod_interno}</span>
                    </div>
                </button>`;
            });
        }
        document.getElementById('listaResultadosJB').innerHTML = html;
    })
    .catch(error => {
        document.getElementById('listaResultadosJB').innerHTML = '<div class="text-center p-3 text-danger">Erro de comunicação com o servidor.</div>';
    });
}

function selecionarProdutoJB(codigoInterno) {
    // Vai buscar a linha que pediu a pesquisa e injeta o código lá dentro
    let linhaId = document.getElementById('linhaAlvoVinculo').value;
    document.getElementById(`cod-int-${linhaId}`).value = codigoInterno;
    
    // Fecha o modal
    if(modalPesquisa) modalPesquisa.hide();
}

