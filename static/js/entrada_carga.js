// ==========================================
// 📥 MÓDULO DE ENTRADA DE CARGA (XML NFe)
// Caminho: static/js/entrada_carga.js
// ==========================================

let notaAtual = null;
let modalConfirmacaoAcao = null;
let itensParaSalvarTemporario = [];


document.addEventListener("DOMContentLoaded", function() {
    const inputXml = document.getElementById('inputXml');
    if (inputXml) {
        inputXml.addEventListener('change', processarImportacaoXML);
    }
    
    let elModal = document.getElementById('modalPesquisaProduto');
    if (elModal) modalPesquisa = new bootstrap.Modal(elModal);

    let elModalConf = document.getElementById('modalConfirmacao');
    if (elModalConf) modalConfirmacaoAcao = new bootstrap.Modal(elModalConf);
});


function processarImportacaoXML(event) {
    let file = event.target.files[0];
    if (!file) return;

    if (!window.CSRF_TOKEN) {
        mostrarAviso("Erro de segurança: Token CSRF não encontrado.", "danger");
        return;
    }

    let formData = new FormData();
    formData.append('xml_file', file);

    let btnImportar = document.getElementById('btnImportarXml');
    let originalText = btnImportar.innerHTML;
    btnImportar.innerHTML = '<i class="bi bi-hourglass-split"></i> A LER XML...';
    btnImportar.disabled = true;

    fetch('/api/importar-xml/', {
        method: 'POST',
        headers: { 'X-CSRFToken': window.CSRF_TOKEN },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        btnImportar.innerHTML = originalText;
        btnImportar.disabled = false;
        event.target.value = ''; 

        if (data.erro) {
            mostrarAviso("Erro ao importar: " + data.erro, "danger");
            return;
        }

        notaAtual = data.nota;
        mostrarAviso(`NFe Nº ${notaAtual.numero} importada com sucesso!`, "success");
        atualizarListaDeNotas(notaAtual);
    })
    .catch(error => {
        console.error("Erro:", error);
        mostrarAviso("Falha de comunicação com o servidor ao enviar o XML.", "danger");
        btnImportar.innerHTML = originalText;
        btnImportar.disabled = false;
        event.target.value = '';
    });
}

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
    // 1. Cabeçalho e Fornecedor
    document.getElementById('lbl-chave').innerText = nota.chave_acesso;
    document.getElementById('lbl-numero-nota').innerText = nota.numero;
    document.getElementById('lbl-data-emissao').innerText = nota.data;
    document.getElementById('lbl-fornecedor-nome').innerText = nota.fornecedor_nome;
    document.getElementById('lbl-fornecedor-cnpj').innerText = nota.fornecedor_cnpj;
    document.getElementById('lbl-fornecedor-endereco').innerText = nota.fornecedor_endereco;
    
    // 2. Totais e Impostos
    const formataBr = (valor) => parseFloat(valor).toFixed(2).replace('.', ',');
    let vTot = formataBr(nota.valor_total);
    
    document.getElementById('lbl-valor-total').innerText = "R$ " + vTot;
    document.getElementById('lbl-valor-produtos').innerText = "R$ " + vTot;
    document.getElementById('lbl-base-icms').innerText = "R$ " + formataBr(nota.impostos.base_icms);
    document.getElementById('lbl-valor-icms').innerText = "R$ " + formataBr(nota.impostos.valor_icms);
    document.getElementById('lbl-valor-ipi').innerText = "R$ " + formataBr(nota.impostos.valor_ipi);
    document.getElementById('lbl-valor-frete').innerText = "R$ " + formataBr(nota.impostos.valor_frete);

    // 3. Transporte
    document.getElementById('sel-mod-frete').value = nota.transporte.mod_frete;
    document.getElementById('lbl-transp-nome').innerText = nota.transporte.nome + (nota.transporte.cnpj ? ` (CNPJ: ${nota.transporte.cnpj})` : '');
    document.getElementById('lbl-transp-volumes').innerText = `${nota.transporte.volumes} VOLUMES | Peso Bruto: ${formataBr(nota.transporte.peso)} KG`;

    // 4. Produtos
    let tbody = document.getElementById('tbody-produtos');
    tbody.innerHTML = ''; 

    nota.produtos.forEach(p => {
        let tr = document.createElement('tr');
        let vUnit = formataBr(p.v_unitario);
        let vTotalItem = formataBr(p.v_total);
        let qtdLimpa = parseFloat(p.qtd) || 0;

        tr.innerHTML = `
            <td class="text-muted">${p.codigo_fornecedor}</td>
            <td class="text-start fw-bold" style="font-size: 0.8rem;">${p.descricao}</td>
            <td><input type="text" class="form-control form-control-sm text-center" value="${p.cfop_origem}" style="width: 55px; margin: 0 auto; font-size: 0.8rem;"></td>
            <td><span class="badge bg-secondary">${qtdLimpa} ${p.unidade}</span></td>
            <td id="vunit-${p.id_linha}">R$ ${vUnit}</td>
            <td class="fw-bold text-success">R$ ${vTotalItem}</td>
            <td style="border-left: 3px solid #0D1B4C;">
                <div class="input-group input-group-sm" style="width: 120px; margin: 0 auto;">
                    <input type="text" class="form-control text-center fw-bold" placeholder="Cód. JB" id="cod-int-${p.id_linha}">
                    <button class="btn btn-outline-secondary" type="button" title="Procurar Produto" onclick="abrirModalPesquisa(${p.id_linha})">🔍</button>
                </div>
            </td>
            <td><input type="number" id="fator-${p.id_linha}" class="form-control form-control-sm text-center" value="1" style="width: 55px; margin: 0 auto;" oninput="recalcularQtdInterna(${p.id_linha}, ${qtdLimpa})"></td>
            <td><span id="badge-qtd-${p.id_linha}" class="badge bg-success">${qtdLimpa} UN</span></td>
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

function abrirModalPesquisa(linhaId) {
    document.getElementById('linhaAlvoVinculo').value = linhaId;
    document.getElementById('inputBuscaJB').value = '';
    document.getElementById('listaResultadosJB').innerHTML = '<div class="text-center p-3 text-muted small">Digite algo para pesquisar...</div>';
    
    if (modalPesquisa) modalPesquisa.show();
    setTimeout(() => document.getElementById('inputBuscaJB').focus(), 500);
}

function buscarProdutoJB(event) {
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
    let linhaId = document.getElementById('linhaAlvoVinculo').value;
    document.getElementById(`cod-int-${linhaId}`).value = codigoInterno;
    if(modalPesquisa) modalPesquisa.hide();
}

// ==========================================
// CÁLCULOS E EFETIVAÇÃO DE STOCK
// ==========================================

function recalcularQtdInterna(linhaId, qtdNfe) {
    let fator = parseFloat(document.getElementById(`fator-${linhaId}`).value) || 1;
    let qtdFinal = Math.floor(qtdNfe * fator);
    document.getElementById(`badge-qtd-${linhaId}`).innerText = `${qtdFinal} UN`;
}

function liberarTodasDivergencias() {
    let linhas = document.querySelectorAll('#tbody-produtos tr');
    let liberados = 0;
    let semVinculo = 0;

    linhas.forEach(linha => {
        let btnLiberar = linha.querySelector('[id^="btn-liberar-"]');
        if (!btnLiberar) return;

        let linhaId = btnLiberar.id.replace('btn-liberar-', '');
        let inputCodInterno = document.getElementById(`cod-int-${linhaId}`);
        
        if (inputCodInterno && inputCodInterno.value.trim() !== "") {
            if (btnLiberar.innerText.includes("⏳")) {
                btnLiberar.innerHTML = "✅ Liberado";
                btnLiberar.classList.remove('btn-warning');
                btnLiberar.classList.add('btn-success', 'text-white');
                liberados++;
            }
        } else {
            semVinculo++;
        }
    });

    if (liberados > 0) mostrarAviso(`${liberados} itens foram marcados como Liberados!`, "success");
    if (semVinculo > 0) mostrarAviso(`Atenção: ${semVinculo} item(ns) não foram liberados pois falta o 'Cód JB'.`, "warning");
}


function trocarCfopLote() {
    // O prompt é útil para captura de dados, mas mudámos o alert de sucesso final
    let novoCfop = prompt("Digite o novo CFOP de Entrada (Ex: 1403, 1102, 5405):");
    if (novoCfop !== null && novoCfop.trim() !== "") {
        novoCfop = novoCfop.trim();
        let inputsCfop = document.querySelectorAll('#tbody-produtos input[value]');
        let alterados = 0;

        inputsCfop.forEach(input => {
            if (input.value && input.value.length === 4 && !input.id.includes('fator')) {
                input.value = novoCfop;
                alterados++;
            }
        });
        if(alterados > 0) mostrarAviso(`CFOP alterado para ${novoCfop} em ${alterados} produtos!`, "success");
    }
}

function finalizarEntradaStock() {
    let linhas = document.querySelectorAll('#tbody-produtos tr');
    let itensParaSalvar = [];
    let itensPendentes = 0;

    linhas.forEach(linha => {
        let btnLiberar = linha.querySelector('[id^="btn-liberar-"]');
        if (!btnLiberar) return;
        
        let linhaId = btnLiberar.id.replace('btn-liberar-', '');
        let isLiberado = btnLiberar.innerText.includes("✅");
        
        let inputCodInterno = document.getElementById(`cod-int-${linhaId}`);
        let inputFator = document.getElementById(`fator-${linhaId}`);
        
        if (inputCodInterno && inputFator) {
            let codInterno = inputCodInterno.value.trim();
            
            if (isLiberado && codInterno !== "") {
                let badgeQtd = document.getElementById(`badge-qtd-${linhaId}`);
                
                // Leitura limpa e segura da quantidade
                let qtdFinal = parseInt(badgeQtd.innerText); 
                
                let vUnitTexto = document.getElementById(`vunit-${linhaId}`).innerText;
                let custoUnitario = parseFloat(vUnitTexto.replace('R$ ', '').replace(/\./g, '').replace(',', '.'));

                itensParaSalvar.push({
                    codigo_interno: codInterno,
                    qtd_final: qtdFinal,
                    custo_unitario: custoUnitario
                });
            } else if (!isLiberado) {
                itensPendentes++;
            }
        }
    });

    if (itensParaSalvar.length === 0) {
        mostrarAviso("Erro: Não há nenhum produto Liberado e com 'Cód JB' preenchido para salvar!", "danger");
        return;
    }

    // A MÁGICA DA NOVA INTERFACE AQUI:
    if (itensPendentes > 0) {
        // Se houver pendentes, escreve a mensagem no Modal, guarda os dados e ABRE O MODAL
        document.getElementById('textoModalConfirmacao').innerText = `Atenção: Tem ${itensPendentes} item(ns) pendentes. Eles NÃO darão entrada no estoque. Deseja prosseguir?`;
        itensParaSalvarTemporario = itensParaSalvar; // Salva na memória global para a próxima função usar
        if (modalConfirmacaoAcao) modalConfirmacaoAcao.show();
        return; // Pára a execução aqui!
    }

    // Se estiver tudo 100% liberado (0 pendentes), vai direto sem perguntar
    itensParaSalvarTemporario = itensParaSalvar;
    confirmarEnvioBackend();
}

// =========================================================================
// NOVA FUNÇÃO: mostrarAviso (Substitui os alert() nativos)
// =========================================================================
function mostrarAviso(mensagem, tipo = 'success') {
    const container = document.getElementById('alert-container');
    if (!container) return;

    const alertDiv = document.createElement('div');
    
    // Configuração de cores e ícones consoante o tipo de aviso
    let icon = tipo === 'success' ? 'check-circle-fill' : (tipo === 'warning' ? 'exclamation-triangle-fill' : 'x-circle-fill');
    let bgClass = tipo === 'success' ? 'bg-success' : (tipo === 'warning' ? 'bg-warning text-dark' : 'bg-danger');
    let textClass = tipo === 'warning' ? 'text-dark' : 'text-white';

    alertDiv.className = `toast align-items-center ${bgClass} ${textClass} border-0 show mb-2 shadow`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.setAttribute('aria-live', 'assertive');
    alertDiv.setAttribute('aria-atomic', 'true');

    alertDiv.innerHTML = `
        <div class="d-flex">
            <div class="toast-body fw-bold">
                <i class="bi bi-${icon} me-2"></i> ${mensagem}
            </div>
            <button type="button" class="btn-close ${tipo === 'warning' ? '' : 'btn-close-white'} me-2 m-auto" data-bs-dismiss="toast" aria-label="Close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;

    container.appendChild(alertDiv);

    // Remove automaticamente o balão do ecrã após 4 segundos
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 300);
    }, 4000);
}
function confirmarEnvioBackend() {
    // 1. Esconde o modal suavemente
    if (modalConfirmacaoAcao) modalConfirmacaoAcao.hide();

    let btnSalvar = document.getElementById('btnFinalizarNFe');
    btnSalvar.innerHTML = "⏳ A SALVAR...";
    btnSalvar.disabled = true;

    // 2. Faz o envio (fetch) usando os dados que guardámos em itensParaSalvarTemporario
    fetch('/api/efetivar-nfe/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.CSRF_TOKEN
        },
        body: JSON.stringify({ itens: itensParaSalvarTemporario })
    })
    .then(res => res.json())
    .then(data => {
        if (data.erro) {
            mostrarAviso("Erro do Servidor: " + data.erro, "danger");
            btnSalvar.innerHTML = "✅ Finalizar Entrada no Stock";
            btnSalvar.disabled = false;
        } else {
            mostrarAviso(data.mensagem, "success"); 
            voltarParaLista();
            document.getElementById('tela-lista-notas').querySelector('tbody').innerHTML = '';
            btnSalvar.innerHTML = "✅ Finalizar Entrada no Stock";
            btnSalvar.disabled = false;
            itensParaSalvarTemporario = []; // Limpa a memória por segurança
        }
    })
    .catch(err => {
        mostrarAviso("Erro fatal ao salvar stock. Verifique a consola (F12).", "danger");
        console.error(err);
        btnSalvar.innerHTML = "✅ Finalizar Entrada no Stock";
        btnSalvar.disabled = false;
    });
}
