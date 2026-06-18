// ==========================================
// 🚀 MOTOR GLOBAL DE OPERAÇÕES FISCAIS (SEFAZ)
// Integração: Fila de Emissão, Consulta NF-e e Consulta NFC-e
// ==========================================

let modalCancelar, modalEmail, modalReenvio, modalDevolucao, modalCce, modalInutilizacao, modalExportacao, modalFiscal;

document.addEventListener("DOMContentLoaded", function() {
    // Inicialização Inteligente: Só cria o modal se ele existir na página atual
    let elCancelar = document.getElementById('modalCancelar'); if(elCancelar) modalCancelar = new bootstrap.Modal(elCancelar);
    let elEmail = document.getElementById('modalEmail'); if(elEmail) modalEmail = new bootstrap.Modal(elEmail);
    let elReenvio = document.getElementById('modalReenvio'); if(elReenvio) modalReenvio = new bootstrap.Modal(elReenvio);
    let elDev = document.getElementById('modalDevolucao'); if(elDev) modalDevolucao = new bootstrap.Modal(elDev);
    let elCce = document.getElementById('modalCce'); if(elCce) modalCce = new bootstrap.Modal(elCce);
    let elInut = document.getElementById('modalInutilizacao'); if(elInut) modalInutilizacao = new bootstrap.Modal(elInut);
    let elExp = document.getElementById('modalExportacao'); if(elExp) modalExportacao = new bootstrap.Modal(elExp);
    let elFiscal = document.getElementById('modalFiscal'); if(elFiscal) modalFiscal = new bootstrap.Modal(elFiscal);
    
    // Auto-Reloads (Polling)
    iniciarAutoReloadSefaz();
    iniciarAutoReloadFila();
});

// ==========================================
// 🔄 POLLING E ATUALIZAÇÃO DE STATUS (F5 INVISÍVEL)
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
        }, 5000);
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
                
            } else if (data.status_fiscal === 'ERRO_AUTORIZACAO' || data.status_fiscal === 'ERRO' || data.status_fiscal === 'REJEITADO') {
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
// 🖨️ AÇÕES BÁSICAS: PDF, XML e CANCELAMENTO
// ==========================================
function visualizarPdf(vendaId) { window.open(`/api/fiscal/imprimir-danfe/${vendaId}/`, '_blank'); }
function visualizarXml(vendaId) { window.open(`/api/fiscal/baixar-xml/${vendaId}/`, '_blank'); }

function prepararCancelamento(vendaId) {
    document.getElementById('vendaIdCancelar').value = vendaId;
    document.getElementById('justificativaCancelamento').value = '';
    modalCancelar.show();
}

function confirmarCancelamento() {
    let vendaId = document.getElementById('vendaIdCancelar').value;
    let justificativa = document.getElementById('justificativaCancelamento').value.trim();
    if (justificativa.length < 15) { alert("⚠️ Mínimo 15 caracteres para a justificativa."); return; }
    
    let btn = document.getElementById('btnConfirmarCancelamento');
    btn.innerHTML = '⏳ Cancelando...'; btn.disabled = true;

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
        btn.innerHTML = 'Confirmar Cancelamento'; btn.disabled = false;
    });
}

function prepararEmail(vendaId) {
    document.getElementById('vendaIdEmail').value = vendaId;
    document.getElementById('emailClienteDestino').value = '';
    modalEmail.show();
}

function confirmarEnvioEmail() {
    let vendaId = document.getElementById('vendaIdEmail').value;
    let email = document.getElementById('emailClienteDestino').value.trim();
    if (!email.includes('@')) { alert("⚠️ E-mail inválido."); return; }
    
    let btn = document.getElementById('btnConfirmarEmail');
    btn.innerHTML = '⏳ Enviando...'; btn.disabled = true;

    fetch('/api/fiscal/enviar-email-nota/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 'venda_id': vendaId, 'email': email })
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) { alert("✅ " + data.mensagem); modalEmail.hide(); }
        else { alert("❌ Erro: " + data.erro); }
        btn.innerHTML = 'Enviar E-mail'; btn.disabled = false;
    });
}

// ==========================================
// 🛠️ MÓDULO DE REENVIO E DEVOLUÇÃO
// ==========================================
function toggleTransportadora() {
    let frete = document.getElementById('modalidadeFreteModal').value;
    let divTransp = document.getElementById('divDadosTransportadora');
    if (!divTransp) return;
    
    if (frete === "0" || frete === "1") {
        divTransp.style.display = 'flex';
    } else {
        divTransp.style.display = 'none';
        document.getElementById('transpCnpj').value = '';
        document.getElementById('transpNome').value = '';
        document.getElementById('transpPlaca').value = '';
        document.getElementById('transpUf').value = '';
        document.getElementById('transpQtd').value = '';
        document.getElementById('transpPeso').value = '';
    }
}

function carregarDadosDoClienteSelecionado(clienteId) {
    let btnReenvio = document.getElementById('btnConfirmarReenvio');
    let btnEmitir = document.getElementById('btnConfirmar');
    
    if (!clienteId) {
        if(btnReenvio) btnReenvio.disabled = true;
        if(btnEmitir) btnEmitir.disabled = true;
        return;
    }
    fetch(`/api/fiscal/buscar-cliente/?cliente_id=${clienteId}`)
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            document.getElementById('destNome').value = data.nome || data.razao_social || '';
            let documento = data.cpf_cnpj || data.cnpj || data.cpf || '';
            document.getElementById('destCpfCnpj').value = documento;
            document.getElementById('destCep').value = data.cep || '';
            document.getElementById('destLogradouro').value = data.endereco || '';
            document.getElementById('destNumero').value = data.numero || '';
            
            let elComplemento = document.getElementById('destComplemento');
            if(elComplemento) elComplemento.value = data.complemento || '';
            
            document.getElementById('destBairro').value = data.bairro || '';
            document.getElementById('destEstado').value = data.estado || '';
            document.getElementById('destMunicipio').value = data.cidade || '';
            document.getElementById('destEmail').value = data.email || '';

            let docLimpo = documento.replace(/\D/g, '');
            let cIE = document.getElementById('containerIE');
            let cIM = document.getElementById('containerIM');
            let sFis = document.getElementById('spacerFisica');
            
            if (docLimpo.length > 11) {
                if(cIE) { cIE.style.display = 'block'; document.getElementById('destIe').value = data.inscricao_estadual || ''; }
                if(cIM) { cIM.style.display = 'block'; document.getElementById('destIm').value = data.inscricao_municipal || ''; }
                if(sFis) sFis.style.display = 'none';
            } else {
                if(cIE) cIE.style.display = 'none';
                if(cIM) cIM.style.display = 'none';
                if(sFis) sFis.style.display = 'block';
            }
            
            if(btnReenvio) btnReenvio.disabled = false;
            if(btnEmitir) btnEmitir.disabled = false;
            
            let badge = document.getElementById('statusCarregamento');
            if(badge) { badge.className = "badge bg-success"; badge.innerText = "✅ Pronto para emitir"; }
        }
    });
}

function abrirModalReenvio(vendaId) {
    document.getElementById('modalVendaIdTexto').innerText = vendaId;
    document.getElementById('formDadosNf').reset();
    document.getElementById('vendaId').value = vendaId;

    let cIE = document.getElementById('containerIE'); if(cIE) cIE.style.display = 'none';
    let cIM = document.getElementById('containerIM'); if(cIM) cIM.style.display = 'none';
    let sFis = document.getElementById('spacerFisica'); if(sFis) sFis.style.display = 'block';
    let dTrans = document.getElementById('divDadosTransportadora'); if(dTrans) dTrans.style.display = 'none';
    
    document.getElementById('btnConfirmarReenvio').disabled = true;

    let btnCorrigir = document.getElementById(`btn-corrigir-${vendaId}`);
    let motivoErro = btnCorrigir ? btnCorrigir.getAttribute('data-motivo-erro') : null;
    let divAlertaErro = document.getElementById('alertaRejeicaoSefaz');
    
    if(divAlertaErro) {
        if(motivoErro && motivoErro !== 'null') {
            document.getElementById('textoRejeicaoSefaz').innerText = motivoErro;
            divAlertaErro.classList.remove('d-none');
        } else {
            divAlertaErro.classList.add('d-none');
        }
    }

    let tbody = document.getElementById('tabelaProdutosModal');
    tbody.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-primary"><span class="spinner-border spinner-border-sm me-2"></span> Carregando itens...</td></tr>`;
    
    modalReenvio.show();

    fetch(`/api/fiscal/detalhes-venda/?venda_id=${vendaId}`)
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
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
                document.getElementById('seletorClienteModal').value = data.venda_cliente_id;
                carregarDadosDoClienteSelecionado(data.venda_cliente_id);
            }
        } else {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-danger">Erro: ${data.erro}</td></tr>`;
        }
    });
}

function confirmarReenvio() {
    let btn = document.getElementById('btnConfirmarReenvio');
    let vendaId = document.getElementById('vendaId').value;
    
    let tipoEmissaoCampo = document.getElementById('tipoEmissaoReenvio');
    let tipoNotaVal = tipoEmissaoCampo ? tipoEmissaoCampo.value : 'NFE'; // Padrão
    
    let docCliente = document.getElementById('destCpfCnpj').value.replace(/\D/g, '');
    if (docCliente.length === 0) {
        alert("⚠️ O CPF/CNPJ do destinatário é obrigatório!");
        document.getElementById('destCpfCnpj').focus();
        return;
    }

    if (tipoNotaVal === 'NFE') {
        let cep = document.getElementById('destCep').value.trim();
        let logradouro = document.getElementById('destLogradouro').value.trim();
        let numero = document.getElementById('destNumero').value.trim();
        let bairro = document.getElementById('destBairro').value.trim();
        let municipio = document.getElementById('destMunicipio').value.trim();
        let estado = document.getElementById('destEstado').value.trim();
        
        if (!cep || !logradouro || !numero || !bairro || !municipio || !estado) {
            alert("⚠️ OPERAÇÃO BLOQUEADA: Para a NF-e, o Endereço Completo do cliente é obrigatório.");
            return;
        }
    }

    btn.innerHTML = '⏳ Transmitindo Correção...';
    btn.disabled = true;
    
    let elCompl = document.getElementById('destComplemento');
    let fPag = document.getElementById('formaPagamento');
    let elIe = document.getElementById('destIe');
    
    let payload = {
        'venda_id': vendaId,
        'cliente_id': document.getElementById('seletorClienteModal').value,
        'tipo_nota': tipoNotaVal,
        'natureza_operacao': document.getElementById('naturezaOperacao').value,
        'cfop': document.getElementById('cfop').value,
        'consumidor_final': document.getElementById('consumidorFinal').value,
        'indicador_presenca': document.getElementById('indicadorPresenca').value,
        'info_complementar': document.getElementById('infoComplementar').value,
        'modalidade_frete': document.getElementById('modalidadeFreteModal').value,
        'pis_cst': document.getElementById('pisCst').value,
        'cofins_cst': document.getElementById('cofinsCst').value,
        
        'dest_nome': document.getElementById('destNome').value,
        'dest_cpf_cnpj': docCliente, 
        'dest_ie': elIe ? elIe.value : '',
        'dest_cep': document.getElementById('destCep').value,
        'dest_logradouro': document.getElementById('destLogradouro').value,
        'dest_numero': document.getElementById('destNumero').value,
        'dest_complemento': elCompl ? elCompl.value : '',
        'dest_bairro': document.getElementById('destBairro').value,
        'dest_estado': document.getElementById('destEstado').value,
        'dest_municipio': document.getElementById('destMunicipio').value,
        
        'transp_cnpj': document.getElementById('transpCnpj') ? document.getElementById('transpCnpj').value : '',
        'transp_nome': document.getElementById('transpNome') ? document.getElementById('transpNome').value : '',
        'transp_placa': document.getElementById('transpPlaca') ? document.getElementById('transpPlaca').value : '',
        'transp_uf': document.getElementById('transpUf') ? document.getElementById('transpUf').value : '',
        'transp_qtd': document.getElementById('transpQtd') ? document.getElementById('transpQtd').value : '',
        'transp_peso': document.getElementById('transpPeso') ? document.getElementById('transpPeso').value : ''
    };
    
    if(fPag) payload['forma_pagamento'] = fPag.value;

    fetch('/api/fiscal/acionar-emissao/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            alert("🚀 Operação executada com sucesso! Monitorize o status na tabela.");
            modalReenvio.hide();
            consultarStatusNfe(vendaId);
        } else {
            alert("❌ Falha: " + data.erro);
            btn.innerHTML = '🚀 Corrigir e Reenviar';
            btn.disabled = false;
        }
    });
}

function abrirModalDevolucao(vendaId, chaveAcesso) {
    if (!chaveAcesso || chaveAcesso === 'null' || chaveAcesso.trim() === '') {
        alert("⚠️ Esta nota ainda não possui Chave de Acesso válida para estorno/devolução.");
        return;
    }
    document.getElementById('formDevolucao').reset();
    document.getElementById('devVendaId').value = vendaId;
    document.getElementById('devChaveOriginal').value = chaveAcesso;
    document.getElementById('btnConfirmarDevolucao').disabled = false;
    document.getElementById('btnConfirmarDevolucao').innerHTML = '🚀 Emitir NF-e de Retorno';

    let tbody = document.getElementById('tabelaItensDevolucao');
    tbody.innerHTML = `<tr><td colspan="4" class="text-center py-3"><span class="spinner-border spinner-border-sm me-2"></span> Buscando transações...</td></tr>`;
    
    modalDevolucao.show();

    fetch(`/api/fiscal/detalhes-venda/?venda_id=${vendaId}`)
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            tbody.innerHTML = '';
            let badge = document.getElementById('badgePagamentoNfce') || document.getElementById('badgePagamentoNfe');
            let formaPagto = data.forma_pagamento ? data.forma_pagamento : "Não informada";
            if(badge) badge.innerText = "💰 Meio de Pagamento Original do PDV: " + formaPagto;
            
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
        } else {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Erro: ${data.erro}</td></tr>`;
        }
    });
}

function confirmarDevolucao() {
    let vendaId = document.getElementById('devVendaId').value;
    let items = [];
    document.querySelectorAll('.item-check-devolucao:checked').forEach(chk => {
        let cod = chk.value;
        items.push({ 'cod_interno': cod, 'quantidade': parseFloat(document.getElementById(`qtdDev_${cod}`).value) });
    });

    if (items.length === 0) { alert("⚠️ Você precisa selecionar pelo menos um produto para devolver."); return; }

    let btn = document.getElementById('btnConfirmarDevolucao');
    btn.innerHTML = '⏳ Gerando NF-e de Retorno...'; btn.disabled = true;

    fetch('/api/fiscal/emitir-devolucao/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            'venda_id': vendaId,
            'chave_original': document.getElementById('devChaveOriginal').value,
            'cfop_devolucao': document.getElementById('devCfop').value,
            'justificativa': document.getElementById('devJustificativa').value,
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
            btn.innerHTML = '🚀 Emitir NF-e de Retorno'; btn.disabled = false;
        }
    });
}

// ==========================================
// 🏢 FUNÇÕES EXCLUSIVAS DA FILA DE EMISSÃO
// ==========================================
function filtrarFila(filtro) {
    let btnPendentes = document.getElementById('btn-pendentes');
    if(!btnPendentes) return; // Se não estiver na tela de Fila, ignora
    
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

    let msgFiltroVazio = document.getElementById('msg-filtro-vazio');
    if (msgFiltroVazio) msgFiltroVazio.style.display = (qtdVisivel === 0 && linhas.length > 0) ? '' : 'none';
}

function abrirModalFiscal(tipoNota, vendaId) {
    document.getElementById('modalVendaIdTexto').innerText = vendaId;
    document.getElementById('modalTipoNotaTexto').innerText = tipoNota;
    document.getElementById('formDadosNf').reset();
    document.getElementById('vendaId').value = vendaId;
    document.getElementById('tipoEmissao').value = tipoNota;

    document.getElementById('containerIE').style.display = 'none';
    document.getElementById('containerIM').style.display = 'none';
    document.getElementById('spacerFisica').style.display = 'block';
    let divTransp = document.getElementById('divDadosTransportadora');
    if(divTransp) divTransp.style.display = 'none';
    
    document.getElementById('btnConfirmar').disabled = true;
    document.getElementById('alertaRejeicaoSefaz').classList.add('d-none'); 
    
    let badge = document.getElementById('statusCarregamento');
    badge.className = "badge bg-warning text-dark"; badge.innerText = "⏳ Lendo carrinho...";

    document.getElementById('tabelaProdutosModal').innerHTML = `<tr><td colspan="5" class="text-center py-3 text-primary"><span class="spinner-border spinner-border-sm me-2"></span> Carregando itens...</td></tr>`;
    modalFiscal.show();

    fetch(`/api/fiscal/detalhes-venda/?venda_id=${vendaId}`)
    .then(response => response.json())
    .then(data => {
        let tbody = document.getElementById('tabelaProdutosModal');
        if (data.sucesso) {
            tbody.innerHTML = '';
            data.itens.forEach(item => {
                tbody.innerHTML += `
                    <tr>
                        <td class="ps-3 fw-bold text-muted">${item.cod_interno}</td>
                        <td class="fw-bold">${item.descricao}</td>
                        <td class="text-center">${item.quantidade}</td>
                        <td class="text-end">R$ ${item.valor_unitario}</td>
                        <td class="text-end pe-3 text-success fw-bold">R$ ${item.total}</td>
                    </tr>`;
            });
            if (data.venda_cliente_id) {
                document.getElementById('seletorClienteModal').value = data.venda_cliente_id;
                carregarDadosDoClienteSelecionado(data.venda_cliente_id);
            } else {
                badge.className = "badge bg-info"; badge.innerText = "👤 Selecione o cliente";
            }
        } else {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-danger">Erro: ${data.erro}</td></tr>`;
        }
    });
}

function confirmarEmissao() {
    let tipoEmissao = document.getElementById('tipoEmissao').value;
    if (tipoEmissao === 'NFE') {
        let cep = document.getElementById('destCep').value.trim();
        let logradouro = document.getElementById('destLogradouro').value.trim();
        let numero = document.getElementById('destNumero').value.trim();
        let bairro = document.getElementById('destBairro').value.trim();
        let municipio = document.getElementById('destMunicipio').value.trim();
        let estado = document.getElementById('destEstado').value.trim();
        
        if (!cep || !logradouro || !numero || !bairro || !municipio || !estado) {
            alert("⚠️ OPERAÇÃO BLOQUEADA: Para emitir uma NF-e, o Endereço Completo do cliente é obrigatório.");
            return;
        }
    }

    let btn = document.getElementById('btnConfirmar');
    btn.innerHTML = '⏳ Transmitindo...'; btn.disabled = true;

    let payload = {
        'venda_id': document.getElementById('vendaId').value,
        'cliente_id': document.getElementById('seletorClienteModal').value,
        'tipo_nota': document.getElementById('tipoEmissao').value,
        'natureza_operacao': document.getElementById('naturezaOperacao').value,
        'cfop': document.getElementById('cfop').value,
        'consumidor_final': document.getElementById('consumidorFinal').value,
        'indicador_presenca': document.getElementById('indicadorPresenca').value,
        'info_complementar': document.getElementById('infoComplementar').value,
        'modalidade_frete': document.getElementById('modalidadeFreteModal').value,
        'pis_cst': document.getElementById('pisCst').value,
        'cofins_cst': document.getElementById('cofinsCst').value,
        'transp_cnpj': document.getElementById('transpCnpj').value,
        'transp_nome': document.getElementById('transpNome').value,
        'transp_placa': document.getElementById('transpPlaca').value,
        'transp_uf': document.getElementById('transpUf').value,
        'transp_qtd': document.getElementById('transpQtd').value,
        'transp_peso': document.getElementById('transpPeso').value
    };

    fetch('/api/fiscal/acionar-emissao/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) { alert("🚀 " + data.mensagem); modalFiscal.hide(); location.reload(); } 
        else {
            document.getElementById('textoRejeicaoSefaz').innerText = data.erro;
            document.getElementById('alertaRejeicaoSefaz').classList.remove('d-none');
            btn.innerHTML = '🚀 Confirmar e Emitir Nota'; btn.disabled = false;
        }
    });
}

// ==========================================
// 🛠️ FERRAMENTAS CONTÁBEIS (Apenas NF-e)
// ==========================================
function sincronizarLote() {
    let btn = document.getElementById('btnSyncLote');
    if(!btn) return;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Sincronizando...'; btn.disabled = true;
    fetch('/api/fiscal/sincronizar-lote/', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) { window.location.reload(); } 
        else { alert("❌ Falha na sincronização: " + data.erro); btn.innerHTML = '🔄 Sincronizar Fila'; btn.disabled = false; }
    });
}

function abrirModalInutilizacao() { document.getElementById('formInutilizacao').reset(); modalInutilizacao.show(); }
function confirmarInutilizacao() {
    let btn = document.getElementById('btnConfirmarInutilizacao');
    let payload = {
        'modelo': document.getElementById('inutModelo').value,
        'numero_inicial': document.getElementById('inutNumInicial').value,
        'numero_final': document.getElementById('inutNumFinal').value,
        'justificativa': document.getElementById('inutJustificativa').value
    };
    if(payload.justificativa.length < 15) return alert("A justificativa técnica deve ter no mínimo 15 caracteres.");
    btn.innerHTML = '⏳ Transmitindo...'; btn.disabled = true;

    fetch('/api/fiscal/inutilizar/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    .then(response => response.json())
    .then(data => {
        if(data.sucesso) { alert("✅ " + data.mensagem); modalInutilizacao.hide(); } 
        else { alert("❌ Erro: " + data.erro); }
        btn.innerHTML = 'Transmitir Inutilização'; btn.disabled = false;
    });
}

function abrirModalExportacao() {
    let hoje = new Date(); document.getElementById('exportAno').value = hoje.getFullYear();
    document.getElementById('exportMes').value = (hoje.getMonth() + 1).toString().padStart(2, '0');
    modalExportacao.show();
}
function confirmarExportacao() {
    let btn = document.getElementById('btnConfirmarExportacao');
    btn.innerHTML = '⏳ Gerando ZIP...'; btn.disabled = true;
    fetch('/api/fiscal/exportar-zip/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({'mes': document.getElementById('exportMes').value, 'ano': document.getElementById('exportAno').value}) 
    })
    .then(response => response.json())
    .then(data => {
        if(data.sucesso) { alert("✅ " + data.mensagem); modalExportacao.hide(); } 
        else { alert("❌ Erro: " + data.erro); }
        btn.innerHTML = 'Solicitar Backup ZIP'; btn.disabled = false;
    });
}

function abrirModalCce(vendaId) { document.getElementById('cceVendaId').value = vendaId; document.getElementById('textoCce').value = ''; modalCce.show(); }
function confirmarCce() {
    let btn = document.getElementById('btnConfirmarCce');
    let payload = { 'venda_id': document.getElementById('cceVendaId').value, 'correcao': document.getElementById('textoCce').value };
    if(payload.correcao.length < 15) return alert("A correção deve ter no mínimo 15 caracteres.");
    btn.innerHTML = '⏳ Anexando CC-e...'; btn.disabled = true;

    fetch('/api/fiscal/emitir-cce/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    .then(response => response.json())
    .then(data => {
        if(data.sucesso) { alert("✅ " + data.mensagem); modalCce.hide(); } 
        else { alert("❌ Erro: " + data.erro); }
        btn.innerHTML = 'Transmitir CC-e à SEFAZ'; btn.disabled = false;
    });
}
