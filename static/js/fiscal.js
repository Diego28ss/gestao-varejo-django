// ==========================================
// 🚀 MOTOR GLOBAL DE OPERAÇÕES FISCAIS (NOTAAS / SEFAZ)
// Integração: Fila de Emissão, Consulta NF-e e Consulta NFC-e
// ==========================================

let modalCancelar, modalEmail, modalReenvio, modalDevolucao, modalCce, modalInutilizacao, modalExportacao, modalFiscal;

document.addEventListener("DOMContentLoaded", function() {
    // Inicialização Inteligente dos Modais
    let elCancelar = document.getElementById('modalCancelar'); if(elCancelar) modalCancelar = new bootstrap.Modal(elCancelar);
    let elEmail = document.getElementById('modalEmail'); if(elEmail) modalEmail = new bootstrap.Modal(elEmail);
    let elReenvio = document.getElementById('modalReenvio'); if(elReenvio) modalReenvio = new bootstrap.Modal(elReenvio);
    let elDev = document.getElementById('modalDevolucao'); if(elDev) modalDevolucao = new bootstrap.Modal(elDev);
    let elCce = document.getElementById('modalCce'); if(elCce) modalCce = new bootstrap.Modal(elCce);
    let elInut = document.getElementById('modalInutilizacao'); if(elInut) modalInutilizacao = new bootstrap.Modal(elInut);
    let elExp = document.getElementById('modalExportacao'); if(elExp) modalExportacao = new bootstrap.Modal(elExp);
    let elFiscal = document.getElementById('modalFiscal'); if(elFiscal) modalFiscal = new bootstrap.Modal(elFiscal);
    
    // Auto-Reloads das tabelas (Background)
    iniciarAutoReloadSefaz();
    iniciarAutoReloadFila();
});

// ==========================================
// 🛡️ HELPERS BLINDADOS CONTRA DADOS FANTASMAS (IDs Duplicados)
// ==========================================
function getValSeguro(id) {
    let modalVisivel = document.querySelector('.modal.show');
    let elemento = null;
    
    if (modalVisivel) {
        elemento = modalVisivel.querySelector(`[id="${id}"]`);
    }
    
    if (!elemento) {
        elemento = document.getElementById(id);
    }
    
    return elemento ? elemento.value.trim() : '';
}

function setValSeguro(id, valor) {
    document.querySelectorAll(`[id="${id}"]`).forEach(el => {
        if(el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA') {
            el.value = valor;
        } else {
            el.innerText = valor;
        }
    });
}

// ==========================================
// 🔄 POLLING E ATUALIZAÇÃO DE STATUS EM SEGUNDO PLANO
// ==========================================
function iniciarAutoReloadSefaz() {
    let notasProcessando = document.querySelectorAll(
        '.auto-reload-target[data-status="PROCESSANDO"], ' + 
        '.auto-reload-target[data-status="PROCESSANDO_NUVEM"], ' +
        '.auto-reload-target[data-status="ENVIANDO"], ' +
        '.auto-reload-target[data-status="DEVOLUCOES_EM_PROCESSAMENTO"]'
    );
    
    if(notasProcessando.length > 0) {
        setTimeout(() => {
            notasProcessando.forEach(badge => {
                let idNota = badge.id.replace('badge-status-', '');
                consultarStatusNfe(idNota, true); 
            });
            iniciarAutoReloadSefaz(); 
        }, 5000); // A cada 5 segundos
    }
}

function iniciarAutoReloadFila() {
    let targets = document.querySelectorAll('.auto-reload-target');
    let precisaRodar = false;
    targets.forEach(badge => {
        let status = badge.getAttribute('data-status');
        if (status === 'PROCESSANDO' || status === 'PROCESSANDO_NUVEM') precisaRodar = true;
    });
    if (precisaRodar) { setTimeout(() => { window.location.reload(); }, 5000); }
}

function consultarStatusNfe(vendaId, isAutoReload = false) {
    let badge = document.getElementById(`badge-status-${vendaId}`);
    if(!badge) return;
    
    badge.className = "badge bg-secondary animate-pulse px-2 py-1 auto-reload-target";
    badge.innerText = "⏳ Buscando...";

    fetch(`/api/fiscal/consultar-status/?venda_id=${vendaId}`)
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            badge.innerText = data.status_fiscal;
            badge.setAttribute('data-status', data.status_fiscal);
            
            let acoesDiv = document.getElementById(`acoes-autorizadas-${vendaId}`);
            let btnCorrigir = document.getElementById(`btn-corrigir-${vendaId}`);
            let tdSitInterna = document.getElementById(`sit-interna-${vendaId}`);
            let btnDevolucao = document.getElementById(`btn-devolucao-${vendaId}`);
            let txtChave = document.getElementById(`chave-${vendaId}`);
            
            if(tdSitInterna && data.status_interno) {
                if(data.status_interno === 'DEVOLVIDO') {
                    tdSitInterna.innerHTML = '<span class="badge bg-warning text-dark px-2 py-1">🟠 Devolvido</span>';
                    if(btnDevolucao) btnDevolucao.classList.add('d-none');
                } else if(data.status_interno === 'CANCELADO') {
                    tdSitInterna.innerHTML = '<span class="badge bg-dark px-2 py-1">⚫ Cancelado</span>';
                } else {
                    tdSitInterna.innerHTML = '<span class="badge bg-success px-2 py-1">🟢 Faturado</span>';
                }
            }
            
            if (data.status_fiscal === 'AUTORIZADO' || data.status_fiscal === 'AUTORIZADA') {
                badge.className = "badge bg-success fw-bold px-2 py-1 auto-reload-target";
                if(txtChave) txtChave.innerText = data.chave_acesso;
                if(acoesDiv) acoesDiv.classList.remove('d-none'); 
                if(btnCorrigir) btnCorrigir.classList.add('d-none'); 
                
            } else if (data.status_fiscal === 'CANCELADO') {
                badge.className = "badge bg-dark fw-bold px-2 py-1 auto-reload-target";
                if(txtChave) txtChave.innerText = "Cancelamento Homologado";
                if(acoesDiv) acoesDiv.classList.add('d-none');
                if(btnCorrigir) btnCorrigir.classList.add('d-none');
                
            } else if (data.status_fiscal === 'ERRO_REJEICAO' || data.status_fiscal === 'ERRO_AUTORIZACAO' || data.status_fiscal === 'ERRO' || data.status_fiscal === 'REJEITADO') {
                badge.className = "badge bg-danger fw-bold px-2 py-1 auto-reload-target";
                if(txtChave) txtChave.innerText = "Rejeitada pela SEFAZ";
                if(acoesDiv) acoesDiv.classList.add('d-none');
                if(btnCorrigir) {
                    btnCorrigir.classList.remove('d-none');
                    btnCorrigir.setAttribute('data-motivo-erro', data.motivo);
                }
                if(!isAutoReload) alert(`❌ Motivo da Rejeição: ${data.motivo}`);
            } else {
                badge.className = "badge bg-warning text-dark px-2 py-1 auto-reload-target";
                if(acoesDiv) acoesDiv.classList.add('d-none');
            }
        } else {
            badge.className = "badge bg-danger text-white px-2 py-1 auto-reload-target";
            badge.innerText = "ERRO DE CONEXÃO";
        }
    });
}

// ==========================================
// 🚀 MÓDULO DE EMISSÃO COM POLLING NO MODAL (NOTAAS)
// ==========================================
function abrirModalFiscal(tipoNota, vendaId) {
    setValSeguro('modalVendaIdTexto', vendaId);
    setValSeguro('modalTipoNotaTexto', tipoNota);
    
    // Tenta resetar os forms visíveis
    document.querySelectorAll('.modal.show form').forEach(f => f.reset());
    
    setValSeguro('vendaId', vendaId);
    setValSeguro('tipoEmissao', tipoNota);

    document.querySelectorAll('[id="containerIE"]').forEach(el => el.style.display = 'none');
    document.querySelectorAll('[id="containerIM"]').forEach(el => el.style.display = 'none');
    document.querySelectorAll('[id="spacerFisica"]').forEach(el => el.style.display = 'block');
    
    let divTransp = document.querySelector('.modal.show [id="divDadosTransportadora"]');
    if(divTransp) divTransp.style.display = 'none';
    
    let btnConf = document.querySelector('.modal.show [id="btnConfirmar"]');
    if(btnConf) btnConf.disabled = true;
    
    document.querySelectorAll('[id="alertaRejeicaoSefaz"]').forEach(el => el.classList.add('d-none')); 
    
    let badge = document.querySelector('.modal.show [id="statusCarregamento"]');
    if(badge) { badge.className = "badge bg-warning text-dark"; badge.innerText = "⏳ Lendo carrinho..."; }

    let tbody = document.querySelector('.modal.show [id="tabelaProdutosModal"]');
    if(tbody) tbody.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-primary"><span class="spinner-border spinner-border-sm me-2"></span> Carregando itens...</td></tr>`;
    
    modalFiscal.show();

    fetch(`/api/fiscal/detalhes-venda/?venda_id=${vendaId}`)
    .then(response => response.json())
    .then(data => {
        let tbodyFinal = document.querySelector('.modal.show [id="tabelaProdutosModal"]');
        if (data.sucesso) {
            tbodyFinal.innerHTML = '';
            data.itens.forEach(item => {
                tbodyFinal.innerHTML += `
                    <tr>
                        <td class="ps-3 fw-bold text-muted">${item.cod_interno}</td>
                        <td class="fw-bold">${item.descricao}</td>
                        <td class="text-center">${item.quantidade}</td>
                        <td class="text-end">R$ ${item.valor_unitario}</td>
                        <td class="text-end pe-3 text-success fw-bold">R$ ${item.total}</td>
                    </tr>`;
            });
            if (data.venda_cliente_id) {
                setValSeguro('seletorClienteModal', data.venda_cliente_id);
                carregarDadosDoClienteSelecionado(data.venda_cliente_id);
            } else {
                if(badge) { badge.className = "badge bg-info"; badge.innerText = "👤 Selecione o cliente"; }
            }
        } else {
            tbodyFinal.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-danger">Erro: ${data.erro}</td></tr>`;
        }
    });
}

function confirmarEmissao() {
    let tipoEmissao = getValSeguro('tipoEmissao');
    let docCliente = getValSeguro('destCpfCnpj').replace(/\D/g, '');
    let cep = getValSeguro('destCep');
    let logradouro = getValSeguro('destLogradouro');
    let numero = getValSeguro('destNumero');
    let bairro = getValSeguro('destBairro');
    let municipio = getValSeguro('destMunicipio');
    let estado = getValSeguro('destEstado');
    
    if (tipoEmissao === 'NFE') {
        if (!docCliente || !cep || !logradouro || !numero || !bairro || !municipio || !estado) {
            alert("⚠️ OPERAÇÃO BLOQUEADA: Para emitir uma NF-e, CPF/CNPJ e o Endereço Completo são obrigatórios.");
            return;
        }
    }

    let btn = document.querySelector('.modal.show [id="btnConfirmar"]') || document.getElementById('btnConfirmar');
    btn.innerHTML = '⏳ Transmitindo...'; btn.disabled = true;
    
    document.querySelectorAll('[id="alertaRejeicaoSefaz"]').forEach(el => el.classList.add('d-none'));
    
    let badgeCarregamento = document.querySelector('.modal.show [id="statusCarregamento"]');
    if(badgeCarregamento) { badgeCarregamento.className = "badge bg-primary"; badgeCarregamento.innerText = "Enviando..."; }

    let payload = {
        'venda_id': getValSeguro('vendaId'),
        'cliente_id': getValSeguro('seletorClienteModal'),
        'tipo_nota': tipoEmissao,
        'natureza_operacao': getValSeguro('naturezaOperacao'),
        'cfop': getValSeguro('cfop'),
        'consumidor_final': getValSeguro('consumidorFinal'),
        'indicador_presenca': getValSeguro('indicadorPresenca'),
        'info_complementar': getValSeguro('infoComplementar'),
        'dest_nome': getValSeguro('destNome'),
        'dest_cpf_cnpj': docCliente,
        'dest_ie': getValSeguro('destIe'),
        'dest_cep': cep,
        'dest_logradouro': logradouro,
        'dest_numero': numero,
        'dest_bairro': bairro,
        'dest_estado': estado,
        'dest_municipio': municipio,
        'modalidade_frete': getValSeguro('modalidadeFreteModal')
    };

    fetch('/api/fiscal/acionar-emissao/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) { 
            if(badgeCarregamento) { badgeCarregamento.className = "badge bg-warning text-dark"; badgeCarregamento.innerText = "⏳ Processando..."; }
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Aguardando SEFAZ...';
            iniciarPollingSefazNoModal(payload.venda_id, tipoEmissao, 'btnConfirmar');
        } else {
            setValSeguro('textoRejeicaoSefaz', data.erro);
            document.querySelectorAll('.modal.show [id="alertaRejeicaoSefaz"]').forEach(el => el.classList.remove('d-none'));
            btn.innerHTML = '🚀 Confirmar e Emitir Nota'; btn.disabled = false;
        }
    });
}

function iniciarPollingSefazNoModal(vendaId, tipoNota, btnId) {
    let tentativas = 0;
    const maxTentativas = 15; 
    
    const loopConsulta = setInterval(() => {
        tentativas++;
        
        fetch(`/api/fiscal/consultar-status/?venda_id=${vendaId}`)
        .then(res => res.json())
        .then(data => {
            if (data.sucesso) {
                if (data.status_fiscal === 'AUTORIZADO') {
                    clearInterval(loopConsulta);
                    alert(`✅ A ${tipoNota} foi emitida com sucesso e autorizada pela SEFAZ!`);
                    if(modalFiscal) modalFiscal.hide();
                    if(modalReenvio) modalReenvio.hide();
                    
                    if (tipoNota === 'NFE') {
                        window.location.href = '/gerenciapainel/consultanfe/?sucesso=1';
                    } else {
                        window.location.href = '/gerenciapainel/consultanfce/?sucesso=1';
                    }
                    
                } else if (data.status_fiscal === 'ERRO_REJEICAO' || data.status_fiscal === 'ERRO') {
                    clearInterval(loopConsulta);
                    setValSeguro('textoRejeicaoSefaz', "Rejeitado pela SEFAZ: " + data.motivo);
                    document.querySelectorAll('.modal.show [id="alertaRejeicaoSefaz"]').forEach(el => el.classList.remove('d-none'));
                    
                    let btn = document.querySelector(`.modal.show [id="${btnId}"]`);
                    if (btn) { btn.innerHTML = '🚀 Tentar Novamente'; btn.disabled = false; }
                    
                    let badge = document.querySelector('.modal.show [id="statusCarregamento"]');
                    if(badge) { badge.className = "badge bg-danger"; badge.innerText = "❌ Rejeição Fiscal"; }
                }
            }
            
            if (tentativas >= maxTentativas) {
                clearInterval(loopConsulta);
                setValSeguro('textoRejeicaoSefaz', "A SEFAZ está demorando muito. Feche esta tela e verifique o painel em alguns minutos.");
                document.querySelectorAll('.modal.show [id="alertaRejeicaoSefaz"]').forEach(el => el.classList.remove('d-none'));
                
                let btn = document.querySelector(`.modal.show [id="${btnId}"]`);
                if (btn) { btn.innerHTML = '🚀 Tentar Novamente'; btn.disabled = false; }
            }
        }).catch(e => console.error("Falha no polling:", e));
    }, 3000); 
}

// ==========================================
// 🛠️ MÓDULO DE REENVIO E CORREÇÃO
// ==========================================
function confirmarReenvio() {
    let tipoNotaVal = getValSeguro('tipoEmissaoReenvio') || 'NFE';
    let docCliente = getValSeguro('destCpfCnpj').replace(/\D/g, '');
    let cep = getValSeguro('destCep');
    let logradouro = getValSeguro('destLogradouro');
    let numero = getValSeguro('destNumero');
    let bairro = getValSeguro('destBairro');
    let municipio = getValSeguro('destMunicipio');
    let estado = getValSeguro('destEstado');
    
    if (docCliente.length === 0) {
        alert("⚠️ O CPF/CNPJ do destinatário é obrigatório!");
        return;
    }

    if (tipoNotaVal === 'NFE') {
        if (!cep || !logradouro || !numero || !bairro || !municipio || !estado) {
            alert("⚠️ OPERAÇÃO BLOQUEADA: Para a NF-e, o Endereço Completo do cliente é obrigatório.");
            return;
        }
    }

    let btn = document.querySelector('.modal.show [id="btnConfirmarReenvio"]');
    if(btn) { btn.innerHTML = '⏳ Transmitindo Correção...'; btn.disabled = true; }
    
    document.querySelectorAll('[id="alertaRejeicaoSefaz"]').forEach(el => el.classList.add('d-none'));
    
    let payload = {
        'venda_id': getValSeguro('vendaId'),
        'cliente_id': getValSeguro('seletorClienteModal'),
        'tipo_nota': tipoNotaVal,
        'natureza_operacao': getValSeguro('naturezaOperacao'),
        'cfop': getValSeguro('cfop'),
        'dest_nome': getValSeguro('destNome'),
        'dest_cpf_cnpj': docCliente, 
        'dest_ie': getValSeguro('destIe'),
        'dest_cep': cep,
        'dest_logradouro': logradouro,
        'dest_numero': numero,
        'dest_bairro': bairro,
        'dest_estado': estado,
        'dest_municipio': municipio
    };

    fetch('/api/fiscal/acionar-emissao/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            if(btn) btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Aguardando SEFAZ...';
            iniciarPollingSefazNoModal(payload.venda_id, tipoNotaVal, 'btnConfirmarReenvio');
        } else {
            setValSeguro('textoRejeicaoSefaz', data.erro);
            document.querySelectorAll('.modal.show [id="alertaRejeicaoSefaz"]').forEach(el => el.classList.remove('d-none'));
            if(btn) { btn.innerHTML = '🚀 Corrigir e Reenviar'; btn.disabled = false; }
        }
    });
}

function abrirModalReenvio(vendaId) {
    setValSeguro('modalVendaIdTexto', vendaId);
    document.querySelectorAll('.modal.show form').forEach(f => f.reset());
    setValSeguro('vendaId', vendaId);

    document.querySelectorAll('[id="containerIE"]').forEach(el => el.style.display = 'none');
    document.querySelectorAll('[id="containerIM"]').forEach(el => el.style.display = 'none');
    document.querySelectorAll('[id="spacerFisica"]').forEach(el => el.style.display = 'block');
    
    let btnReenvio = document.querySelector('.modal.show [id="btnConfirmarReenvio"]');
    if(btnReenvio) btnReenvio.disabled = true;

    let btnCorrigir = document.getElementById(`btn-corrigir-${vendaId}`);
    let motivoErro = btnCorrigir ? btnCorrigir.getAttribute('data-motivo-erro') : null;
    
    document.querySelectorAll('.modal.show [id="alertaRejeicaoSefaz"]').forEach(el => {
        if(motivoErro && motivoErro !== 'null') {
            setValSeguro('textoRejeicaoSefaz', motivoErro);
            el.classList.remove('d-none');
        } else {
            el.classList.add('d-none');
        }
    });

    let tbody = document.querySelector('.modal.show [id="tabelaProdutosModal"]');
    if(tbody) tbody.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-primary"><span class="spinner-border spinner-border-sm me-2"></span> Carregando itens...</td></tr>`;
    
    modalReenvio.show();

    fetch(`/api/fiscal/detalhes-venda/?venda_id=${vendaId}`)
    .then(response => response.json())
    .then(data => {
        if (data.sucesso && tbody) {
            tbody.innerHTML = '';
            data.itens.forEach(item => {
                tbody.innerHTML += `
                    <tr>
                        <td class="ps-3 fw-bold text-muted">${item.cod_interno}</td>
                        <td class="fw-bold">${item.descricao}</td>
                        <td class="text-center">${item.quantidade}</td>
                        <td class="text-end">R$ ${item.valor_unitario}</td>
                        <td class="text-end pe-3 text-success fw-bold">R$ ${item.total}</td>
                    </tr>
                `;
            });
            if (data.venda_cliente_id) {
                setValSeguro('seletorClienteModal', data.venda_cliente_id);
                carregarDadosDoClienteSelecionado(data.venda_cliente_id);
            }
        }
    });
}

function carregarDadosDoClienteSelecionado(clienteId) {
    let btnReenvio = document.querySelector('.modal.show [id="btnConfirmarReenvio"]');
    let btnEmitir = document.querySelector('.modal.show [id="btnConfirmar"]');
    
    if (!clienteId) {
        if(btnReenvio) btnReenvio.disabled = true;
        if(btnEmitir) btnEmitir.disabled = true;
        return;
    }
    fetch(`/api/fiscal/buscar-cliente/?cliente_id=${clienteId}`)
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            setValSeguro('destNome', data.nome || data.razao_social || '');
            let documento = data.cpf_cnpj || data.cnpj || data.cpf || '';
            setValSeguro('destCpfCnpj', documento);
            setValSeguro('destCep', data.cep || '');
            setValSeguro('destLogradouro', data.endereco || '');
            setValSeguro('destNumero', data.numero || '');
            setValSeguro('destBairro', data.bairro || '');
            setValSeguro('destEstado', data.estado || '');
            setValSeguro('destMunicipio', data.cidade || '');

            let docLimpo = documento.replace(/\D/g, '');
            
            document.querySelectorAll('.modal.show [id="containerIE"]').forEach(el => el.style.display = docLimpo.length > 11 ? 'block' : 'none');
            document.querySelectorAll('.modal.show [id="containerIM"]').forEach(el => el.style.display = docLimpo.length > 11 ? 'block' : 'none');
            document.querySelectorAll('.modal.show [id="spacerFisica"]').forEach(el => el.style.display = docLimpo.length > 11 ? 'none' : 'block');
            
            if (docLimpo.length > 11) {
                setValSeguro('destIe', data.inscricao_estadual || '');
            }
            
            if(btnReenvio) btnReenvio.disabled = false;
            if(btnEmitir) btnEmitir.disabled = false;
            
            let badge = document.querySelector('.modal.show [id="statusCarregamento"]');
            if(badge) { badge.className = "badge bg-success"; badge.innerText = "✅ Pronto para emitir"; }
        }
    });
}

// ==========================================
// 🖨️ AÇÕES BÁSICAS: PDF, XML e CANCELAMENTO
// ==========================================
function visualizarPdf(vendaId) { window.open(`/api/fiscal/imprimir-danfe/${vendaId}/`, '_blank'); }
function visualizarXml(vendaId) { window.open(`/api/fiscal/baixar-xml/${vendaId}/`, '_blank'); }

function prepararCancelamento(vendaId) {
    setValSeguro('vendaIdCancelar', vendaId);
    setValSeguro('justificativaCancelamento', '');
    modalCancelar.show();
}

function confirmarCancelamento() {
    let vendaId = getValSeguro('vendaIdCancelar');
    let justificativa = getValSeguro('justificativaCancelamento');
    if (justificativa.length < 15) { alert("⚠️ Mínimo 15 caracteres para a justificativa."); return; }
    
    let btn = document.querySelector('.modal.show [id="btnConfirmarCancelamento"]');
    if(btn) { btn.innerHTML = '⏳ Cancelando...'; btn.disabled = true; }

    fetch('/api/fiscal/cancelar-nota/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 'venda_id': vendaId, 'justificativa': justificativa })
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) { 
            alert("✅ " + data.mensagem); 
            modalCancelar.hide(); 
            consultarStatusNfe(vendaId); 
        } else { 
            alert("❌ Erro: " + data.erro); 
        }
        if(btn) { btn.innerHTML = 'Confirmar Cancelamento'; btn.disabled = false; }
    });
}

// ==========================================
// 📦 RETORNO E DEVOLUÇÃO
// ==========================================
function abrirModalDevolucao(vendaId, chaveAcesso) {
    if (!chaveAcesso || chaveAcesso === 'null' || chaveAcesso.trim() === '') {
        alert("⚠️ Esta nota ainda não possui Chave de Acesso válida para estorno/devolução.");
        return;
    }
    document.querySelectorAll('.modal.show form').forEach(f => f.reset());
    setValSeguro('devVendaId', vendaId);
    setValSeguro('devChaveOriginal', chaveAcesso);
    
    let btn = document.getElementById('btnConfirmarDevolucao');
    if(btn) { btn.disabled = false; btn.innerHTML = '🚀 Emitir NF-e de Retorno'; }

    let tbody = document.getElementById('tabelaItensDevolucao');
    if(tbody) tbody.innerHTML = `<tr><td colspan="4" class="text-center py-3"><span class="spinner-border spinner-border-sm me-2"></span> Buscando transações...</td></tr>`;
    
    modalDevolucao.show();

    fetch(`/api/fiscal/detalhes-venda/?venda_id=${vendaId}`)
    .then(response => response.json())
    .then(data => {
        if (data.sucesso && tbody) {
            tbody.innerHTML = '';
            data.itens.forEach((item, index) => {
                let maxQtd = parseFloat(item.quantidade);
                tbody.innerHTML += `
                    <tr>
                        <td class="text-center">
                            <input class="form-check-input item-check-devolucao border-primary fs-5" type="checkbox" id="chkDev_${index}" value="${item.cod_interno}">
                        </td>
                        <td class="fw-bold text-muted"><label for="chkDev_${index}">${item.descricao}</label></td>
                        <td class="text-center fw-bold">${maxQtd}</td>
                        <td class="text-center">
                            <input type="number" id="qtdDev_${item.cod_interno}" class="form-control form-control-sm fw-bold text-center" value="${maxQtd}" max="${maxQtd}" min="0.01" step="0.01">
                        </td>
                    </tr>
                `;
            });
        }
    });
}

function confirmarDevolucao() {
    let vendaId = getValSeguro('devVendaId');
    let items = [];
    document.querySelectorAll('.item-check-devolucao:checked').forEach(chk => {
        let cod = chk.value;
        items.push({ 'cod_interno': cod, 'quantidade': parseFloat(getValSeguro(`qtdDev_${cod}`)) });
    });

    if (items.length === 0) { alert("⚠️ Você precisa selecionar pelo menos um produto para devolver."); return; }

    let btn = document.querySelector('.modal.show [id="btnConfirmarDevolucao"]');
    if(btn) { btn.innerHTML = '⏳ Gerando NF-e de Retorno...'; btn.disabled = true; }

    fetch('/api/fiscal/emitir-devolucao/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            'venda_id': vendaId,
            'chave_original': getValSeguro('devChaveOriginal'),
            'cfop_devolucao': getValSeguro('devCfop'),
            'justificativa': getValSeguro('devJustificativa'),
            'itens_devolvidos': items
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.sucesso) {
            alert("✅ Sucesso! Mercadoria devolvida ao estoque físico e Nota gerada.");
            modalDevolucao.hide();
            setTimeout(() => { window.location.reload(); }, 1000);
        } else {
            alert("❌ Falha na SEFAZ: " + data.erro);
            if(btn) { btn.innerHTML = '🚀 Emitir NF-e de Retorno'; btn.disabled = false; }
        }
    });
}

// ==========================================
// 🛠️ FERRAMENTAS EXTRAS E UTILITÁRIOS
// ==========================================
function toggleTransportadora() {
    let frete = getValSeguro('modalidadeFreteModal');
    let divTransp = document.querySelector('.modal.show [id="divDadosTransportadora"]');
    if (!divTransp) return;
    if (frete === "0" || frete === "1") { divTransp.style.display = 'flex'; } 
    else { divTransp.style.display = 'none'; }
}

function filtrarFila(filtro) {
    let btnPendentes = document.getElementById('btn-pendentes');
    if(!btnPendentes) return; 
    let btnTodas = document.getElementById('btn-todas');
    if (filtro === 'pendentes') { btnPendentes.classList.add('active'); btnTodas.classList.remove('active'); } 
    else { btnTodas.classList.add('active'); btnPendentes.classList.remove('active'); }

    let linhas = document.querySelectorAll('.linha-venda');
    let qtdVisivel = 0;
    
    linhas.forEach(linha => {
        if (filtro === 'todas') { linha.style.display = ''; qtdVisivel++; } 
        else if (filtro === 'pendentes') {
            if (linha.getAttribute('data-status') === 'pendente') { linha.style.display = ''; qtdVisivel++; } 
            else { linha.style.display = 'none'; }
        }
    });
}

function sincronizarLote() {
    let btn = document.getElementById('btnSyncLote');
    if(!btn) return;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Sincronizando...'; btn.disabled = true;
    fetch('/api/fiscal/sincronizar-lote/', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) { window.location.reload(); } 
        else { alert("❌ Falha: " + data.erro); btn.innerHTML = '🔄 Sincronizar Fila'; btn.disabled = false; }
    });
}
