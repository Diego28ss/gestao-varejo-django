// ==========================================
// 📥 MÓDULO DE ENTRADA DE CARGA (XML NFe)
// Caminho: static/js/entrada_carga.js
// ==========================================

let notasImportadas = []; // Agora guardamos uma LISTA de notas
let notaAtualIndex = null; // Para saber qual nota estamos a editar
let notaAtual = null;
let modalConfirmacaoAcao = null;
let itensParaSalvarTemporario = [];
let modalPesquisa = null;
let modalCancelamento = null;
let notaParaCancelarIndex = null;


document.addEventListener("DOMContentLoaded", function() {
    const inputXml = document.getElementById('inputXml');
    if (inputXml) {
        inputXml.addEventListener('change', processarImportacaoXML);
    }
    
    // Inicialização dos Modais do Bootstrap
    let elModal = document.getElementById('modalPesquisaProduto');
    if (elModal) modalPesquisa = new bootstrap.Modal(elModal);

    let elModalConf = document.getElementById('modalConfirmacao');
    if (elModalConf) modalConfirmacaoAcao = new bootstrap.Modal(elModalConf);

    let elModalCanc = document.getElementById('modalCancelarEntrada');
    if (elModalCanc) modalCancelamento = new bootstrap.Modal(elModalCanc);

    // ========================================================
    // MAGIA DO F5: Recupera as notas salvas no LocalStorage
    // ========================================================
    let salvas = localStorage.getItem('notasImportadasJB');
    let tbody = document.querySelector('#tela-lista-notas tbody');
    
    if (salvas) {
        notasImportadas = JSON.parse(salvas);
        tbody.innerHTML = ''; // Limpa a tabela
        
        if(notasImportadas.length > 0) {
            notasImportadas.forEach((n, idx) => atualizarListaDeNotas(n, idx));
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="text-muted p-4">Nenhuma nota pendente de conferência.</td></tr>';
        }
    } else {
        tbody.innerHTML = '<tr><td colspan="6" class="text-muted p-4">Nenhuma nota pendente de conferência.</td></tr>';
    }
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

        // Adiciona a nota nova à lista com status Pendente e salva no Disco (LocalStorage)
        notaAtual = data.nota;
        notaAtual.status = 'Pendente'; // INJETAMOS O STATUS AQUI
        
        notasImportadas.push(notaAtual);
        localStorage.setItem('notasImportadasJB', JSON.stringify(notasImportadas));
        
        mostrarAviso(`NFe Nº ${notaAtual.numero} importada com sucesso!`, "success");
        
        let tbody = document.querySelector('#tela-lista-notas tbody');
        if (tbody.innerHTML.includes("Nenhuma nota pendente")) {
            tbody.innerHTML = '';
        }
        
        // Renderiza a nova nota na tabela passando o seu índice exato
        atualizarListaDeNotas(notaAtual, notasImportadas.length - 1);
    })
    .catch(error => {
        console.error("Erro:", error);
        mostrarAviso("Falha de comunicação com o servidor ao enviar o XML.", "danger");
        btnImportar.innerHTML = originalText;
        btnImportar.disabled = false;
        event.target.value = '';
    });
}


function atualizarListaDeNotas(nota, index) {
    let tbody = document.querySelector('#tela-lista-notas tbody');
    let tr = document.createElement('tr');
    
    let nomeFornecedor = nota.fornecedor ? nota.fornecedor.nome : 'Desconhecido';
    let valorTotal = nota.impostos ? parseFloat(nota.impostos.vNF || 0) : 0;
    
    // Define a cor e os botões consoante o Status da Nota
    let statusBadge = '';
    let botoesAcao = '';

    if (nota.status === 'Finalizado') {
        statusBadge = '<span class="badge bg-success shadow-sm">Finalizada</span>';
        botoesAcao = `
            <button class="btn btn-sm btn-danger shadow-sm fw-bold me-1" onclick="abrirModalCancelar(${index})" title="Cancelar Entrada">
                ❌ Cancelar
            </button>
            <button class="btn btn-sm btn-info text-white shadow-sm fw-bold" onclick="baixarXML(${index})" title="Baixar XML">
                ⬇️ Baixar XML
            </button>
        `;
    } else if (nota.status === 'Cancelado') {
        statusBadge = '<span class="badge bg-danger shadow-sm">Cancelada</span>';
        botoesAcao = `
            <button class="btn btn-sm btn-outline-secondary shadow-sm fw-bold disabled">
                🚫 Sem Ações
            </button>
        `;
    } else {
        // Padrão: Pendente
        statusBadge = '<span class="badge bg-warning text-dark shadow-sm">Pendente</span>';
        botoesAcao = `
            <button class="btn btn-sm btn-primary shadow-sm fw-bold me-1" onclick="abrirDetalhesNota(${index})" title="Conferir Nota">
                ✏️ Conferir
            </button>
            <button class="btn btn-sm btn-outline-danger shadow-sm fw-bold" onclick="removerNotaImportada(${index})" title="Excluir XML">
                🗑️
            </button>
        `;
    }

    tr.innerHTML = `
        <td>${statusBadge}</td>
        <td class="fw-bold text-primary">${nota.numero}</td>
        <td class="text-start fw-bold">${nomeFornecedor}</td>
        <td>${nota.data}</td>
        <td class="text-success fw-bold fs-6">R$ ${valorTotal.toFixed(2).replace('.', ',')}</td>
        <td>${botoesAcao}</td>
    `;
    tbody.appendChild(tr);
}


function removerNotaImportada(index) {
    if(confirm("Deseja realmente remover esta nota da fila de espera?")) {
        notasImportadas.splice(index, 1);
        localStorage.setItem('notasImportadasJB', JSON.stringify(notasImportadas));
        
        let tbody = document.querySelector('#tela-lista-notas tbody');
        tbody.innerHTML = '';
        if(notasImportadas.length > 0) {
            notasImportadas.forEach((n, idx) => atualizarListaDeNotas(n, idx));
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="text-muted p-4">Nenhuma nota pendente de conferência.</td></tr>';
        }
    }
}


function abrirDetalhesNota(index) {
    notaAtualIndex = index;
    notaAtual = notasImportadas[index];
    
    document.getElementById('tela-lista-notas').style.display = 'none';
    document.getElementById('tela-detalhes-nota').style.display = 'block';
    
    if(notaAtual) {
        preencherTelaDetalhes(notaAtual);
    }
}

function preencherTelaDetalhes(nota) {
    const fBr = (v) => parseFloat(v || 0).toFixed(2).replace('.', ',');

    // 1. Cabeçalho e Fornecedor
    document.getElementById('lbl-chave').innerText = nota.chave_acesso;
    document.getElementById('lbl-numero-nota').innerText = nota.numero;
    document.getElementById('lbl-serie').innerText = nota.serie;
    document.getElementById('lbl-modelo').innerText = nota.modelo;
    document.getElementById('lbl-data-emissao').innerText = nota.data;
    document.getElementById('lbl-data-saida').innerText = nota.data_saida;
    document.getElementById('lbl-natop').innerText = nota.natureza;
    
    let crtText = nota.fornecedor.crt === '1' ? '1 - Simples Nacional' : (nota.fornecedor.crt === '3' ? '3 - Regime Normal' : nota.fornecedor.crt);
    document.getElementById('lbl-crt').innerText = crtText;
    
    document.getElementById('lbl-forn-nome').innerText = nota.fornecedor.nome;
    document.getElementById('lbl-forn-cnpj').innerText = nota.fornecedor.cnpj;
    document.getElementById('lbl-forn-ie').innerText = nota.fornecedor.ie;
    document.getElementById('lbl-forn-im').innerText = nota.fornecedor.im;
    document.getElementById('lbl-forn-end').innerText = nota.fornecedor.endereco;
    document.getElementById('lbl-forn-cid').innerText = nota.fornecedor.cidade_uf;
    document.getElementById('lbl-forn-tel').innerText = nota.fornecedor.telefone;
    
    document.getElementById('lbl-inf-contribuinte').innerText = nota.informacoes.contribuinte;
    document.getElementById('lbl-inf-fisco').innerText = nota.informacoes.fisco;

    // 2. Destinatário
    document.getElementById('lbl-dest-nome').innerText = nota.destinatario.nome;
    document.getElementById('lbl-dest-cnpj').innerText = nota.destinatario.cnpj;
    document.getElementById('lbl-dest-ie').innerText = nota.destinatario.ie;
    document.getElementById('lbl-dest-end').innerText = nota.destinatario.endereco;
    document.getElementById('lbl-dest-cid').innerText = nota.destinatario.cidade_uf;
    document.getElementById('lbl-dest-tel').innerText = nota.destinatario.telefone;
    document.getElementById('lbl-dest-email').innerText = nota.destinatario.email;

    // 3. Totais e Impostos
    document.getElementById('tot-prod').innerText = "R$ " + fBr(nota.impostos.vProd);
    document.getElementById('tot-bc').innerText = "R$ " + fBr(nota.impostos.vBC);
    document.getElementById('tot-icms').innerText = "R$ " + fBr(nota.impostos.vICMS);
    document.getElementById('tot-bcst').innerText = "R$ " + fBr(nota.impostos.vBCST);
    document.getElementById('tot-st').innerText = "R$ " + fBr(nota.impostos.vST);
    document.getElementById('tot-frete').innerText = "R$ " + fBr(nota.impostos.vFrete);
    document.getElementById('tot-seg').innerText = "R$ " + fBr(nota.impostos.vSeg);
    document.getElementById('tot-desc').innerText = "R$ " + fBr(nota.impostos.vDesc);
    document.getElementById('tot-ii').innerText = "R$ " + fBr(nota.impostos.vII);
    document.getElementById('tot-ipi').innerText = "R$ " + fBr(nota.impostos.vIPI);
    document.getElementById('tot-fcpst').innerText = "R$ " + fBr(nota.impostos.vFCPST);
    document.getElementById('tot-pis').innerText = "R$ " + fBr(nota.impostos.vPIS);
    document.getElementById('tot-cofins').innerText = "R$ " + fBr(nota.impostos.vCOFINS);
    document.getElementById('tot-outras').innerText = "R$ " + fBr(nota.impostos.vOutro);
    document.getElementById('tot-nfe').innerText = "R$ " + fBr(nota.impostos.vNF);

    // 4. Transporte
    document.getElementById('sel-mod-frete').value = nota.transporte.modFrete;
    document.getElementById('lbl-transp-nome').innerText = nota.transporte.nome;
    document.getElementById('lbl-transp-cnpj').innerText = nota.transporte.cnpj;
    document.getElementById('lbl-transp-ie').innerText = nota.transporte.ie;
    document.getElementById('lbl-transp-end').innerText = nota.transporte.endereco;
    
    document.getElementById('lbl-transp-placa').innerText = nota.transporte.placa;
    document.getElementById('lbl-transp-rntc').innerText = nota.transporte.rntc;
    document.getElementById('lbl-transp-uf').innerText = nota.transporte.uf_veiculo;
    
    document.getElementById('lbl-vol-qtd').innerText = nota.transporte.qVol;
    document.getElementById('lbl-vol-esp').innerText = nota.transporte.esp;
    document.getElementById('lbl-vol-marca').innerText = nota.transporte.marca;
    document.getElementById('lbl-vol-pesol').innerText = fBr(nota.transporte.pesoL);
    document.getElementById('lbl-vol-pesob').innerText = fBr(nota.transporte.pesoB);

    // 5. Produtos (Tabela)
    let tbody = document.getElementById('tbody-produtos');
    tbody.innerHTML = ''; 

    nota.produtos.forEach(p => {
        let tr = document.createElement('tr');
        let qtdLimpa = parseFloat(p.qtd) || 0;

        tr.innerHTML = `
            <td>${p.id_linha}</td>
            <td class="text-muted">${p.codigo_fornecedor}</td>
            <td class="text-start fw-bold text-wrap" style="min-width: 200px;">${p.descricao}</td>
            <td>${p.cfop_origem}</td>
            <td><input type="text" class="form-control form-control-sm text-center" value="${p.cfop_origem}" style="width: 55px; margin: 0 auto;"></td>
            <td>${qtdLimpa}</td>
            <td>${p.unidade}</td>
            <td id="vunit-${p.id_linha}">${fBr(p.v_unitario)}</td>
            <td class="fw-bold">${fBr(p.v_total)}</td>
            <td class="text-muted">${p.cst_csosn}</td>
            <td class="text-muted">${fBr(p.bc_icms)}</td>
            <td class="text-muted">${fBr(p.v_icms)}</td>
            <td class="text-muted">${fBr(p.v_ipi)}</td>
            <td class="text-muted">${fBr(p.p_icms)}</td>
            <td class="text-muted">${fBr(p.p_ipi)}</td>
            
            <!-- Colunas da JB Tintas -->
            <td style="border-left: 3px solid #0D1B4C;">
                <div class="input-group input-group-sm" style="width: 100px; margin: 0 auto;">
                    <input type="text" class="form-control text-center fw-bold" placeholder="Cód" id="cod-int-${p.id_linha}">
                    <button class="btn btn-outline-secondary" type="button" onclick="abrirModalPesquisa(${p.id_linha})">🔍</button>
                </div>
            </td>
            <td><span id="desc-int-${p.id_linha}" class="small text-muted fst-italic">Vincule na lupa...</span></td>
            <td><input type="number" id="fator-${p.id_linha}" class="form-control form-control-sm text-center" value="1" style="width: 50px; margin: 0 auto;" oninput="recalcularQtdInterna(${p.id_linha}, ${qtdLimpa})"></td>
            <td><span id="badge-qtd-${p.id_linha}" class="badge bg-success">${qtdLimpa} UN</span></td>
            <td>
                <button class="btn btn-sm btn-warning fw-bold text-dark w-100 shadow-sm" id="btn-liberar-${p.id_linha}" onclick="liberarItem(${p.id_linha})">⏳ Liberar</button>
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
    let inputCodInterno = document.getElementById('cod-int-' + idItemTabela);

    if (btn.innerText.includes("⏳")) {
        if (!inputCodInterno || inputCodInterno.value.trim() === "") {
            mostrarAviso("Não é possível liberar! Este produto ainda não foi vinculado ao estoque.", "warning");
            if (inputCodInterno) inputCodInterno.focus();
            return; 
        }
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

    document.getElementById('listaResultadosJB').innerHTML = '<div class="text-center p-3 text-primary fw-bold"><i class="bi bi-hourglass-split"></i> Buscando...</div>';

    fetch(`/api/pesquisar-produto-nfe/?q=${encodeURIComponent(q)}`)
    .then(res => res.json())
    .then(data => {
        let html = '';
        if (data.produtos.length === 0) {
            html = '<div class="text-center p-3 text-danger fw-bold">Nenhum produto encontrado.</div>';
        } else {
            data.produtos.forEach(p => {
                let nomeSeguro = p.nome.replace(/'/g, "\\'").replace(/"/g, "&quot;");
                html += `
                <button type="button" class="list-group-item list-group-item-action" onclick="selecionarProdutoJB('${p.cod_interno}', '${nomeSeguro}')">
                    <div class="d-flex justify-content-between align-items-center">
                        <strong>${p.nome}</strong><span class="badge bg-secondary">Cód: ${p.cod_interno}</span>
                    </div>
                </button>`;
            });
        }
        document.getElementById('listaResultadosJB').innerHTML = html;
    })
    .catch(error => { document.getElementById('listaResultadosJB').innerHTML = '<div class="text-center p-3 text-danger">Erro de servidor.</div>'; });
}

function selecionarProdutoJB(codigoInterno, nomeProduto) {
    let linhaId = document.getElementById('linhaAlvoVinculo').value;
    document.getElementById(`cod-int-${linhaId}`).value = codigoInterno;
    
    let lblDesc = document.getElementById(`desc-int-${linhaId}`);
    if(lblDesc) {
        lblDesc.innerText = nomeProduto;
        lblDesc.classList.remove('text-muted', 'fst-italic');
        lblDesc.classList.add('fw-bold', 'text-primary');
    }
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
    if (modalConfirmacaoAcao) modalConfirmacaoAcao.hide();

    let btnSalvar = document.getElementById('btnFinalizarNFe');
    btnSalvar.innerHTML = "⏳ A SALVAR...";
    btnSalvar.disabled = true;

    fetch('/api/efetivar-nfe/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN },
        body: JSON.stringify({ itens: itensParaSalvarTemporario })
    })
    .then(res => res.json())
    .then(data => {
        if (data.erro) {
            mostrarAviso("Erro do Servidor: " + data.erro, "danger");
        } else {
            mostrarAviso(data.mensagem, "success"); 
            
            // MAGIA AQUI: Em vez de excluir, mudamos o status para Finalizado!
            notasImportadas[notaAtualIndex].status = 'Finalizado';
            localStorage.setItem('notasImportadasJB', JSON.stringify(notasImportadas));
            
            // Recarrega a tabela inicial
            let tbody = document.querySelector('#tela-lista-notas tbody');
            tbody.innerHTML = '';
            notasImportadas.forEach((n, idx) => atualizarListaDeNotas(n, idx));
            
            voltarParaLista();
        }
    })
    .catch(err => {
        mostrarAviso("Erro fatal ao salvar stock.", "danger");
        console.error(err);
    })
    .finally(() => {
        btnSalvar.innerHTML = "✅ Finalizar Entrada no Stock";
        btnSalvar.disabled = false;
        itensParaSalvarTemporario = []; 
    });
}

function abrirModalCancelar(index) {
    notaParaCancelarIndex = index;
    document.getElementById('inputJustificativa').value = '';
    document.getElementById('erroJustificativa').classList.add('d-none');
    if(modalCancelamento) modalCancelamento.show();
}

function efetivarCancelamento() {
    let justificativa = document.getElementById('inputJustificativa').value.trim();
    let erroTexto = document.getElementById('erroJustificativa');
    
    if(justificativa.length < 5) {
        erroTexto.classList.remove('d-none');
        return;
    }
    
    // Futuro: Disparo para o Python (Backend) informando o cancelamento
    // fetch('/api/cancelar-nfe/', { ... })

    // Simulação do sucesso:
    notasImportadas[notaParaCancelarIndex].status = 'Cancelado';
    notasImportadas[notaParaCancelarIndex].justificativa = justificativa;
    localStorage.setItem('notasImportadasJB', JSON.stringify(notasImportadas));
    
    if(modalCancelamento) modalCancelamento.hide();
    mostrarAviso("Entrada da nota cancelada com sucesso!", "success");
    
    // Recarrega a tabela
    let tbody = document.querySelector('#tela-lista-notas tbody');
    tbody.innerHTML = '';
    notasImportadas.forEach((n, idx) => atualizarListaDeNotas(n, idx));
}

function baixarXML(index) {
    let nota = notasImportadas[index];
    mostrarAviso("Gerando download do XML da NFe " + nota.numero + "...", "success");
    
    // Futuro: Redirecionamento para a URL do Django que serve o ficheiro XML
    // window.open(`/api/download-xml/?chave=${nota.chave_acesso}`, '_blank');
}

