// ==========================================
// 👥 MÓDULO DE PESSOAS (CLIENTES E COLABORADORES)
// ==========================================

let modalColaborador, mEdit, mHist;

document.addEventListener("DOMContentLoaded", function () {
    let elRH = document.getElementById('modalRH');
    if (elRH) modalColaborador = new bootstrap.Modal(elRH);

    let elEdit = document.getElementById('modalEditar');
    if (elEdit) mEdit = new bootstrap.Modal(elEdit);

    let elHist = document.getElementById('modalHist');
    if (elHist) mHist = new bootstrap.Modal(elHist);

    let formCadastro = document.getElementById('formCadastroCliente');
    if (formCadastro) {
        formCadastro.addEventListener('submit', function (e) {
            let tel = document.getElementById('edit_telefone').value.replace(/\D/g, '');
            if (tel.length !== 11) {
                e.preventDefault();
                window.mostrarAviso("O número de Celular/WhatsApp deve conter exatamente o DDD (2 números) + 9 dígitos.", 'erro');
                document.getElementById('edit_telefone').focus();
                return;
            }

            let currentId = document.getElementById('edit_id').value;
            // 🚀 MODIFICADO: Pega o tipo de pessoa selecionado em tempo real
            let tipoObj = document.querySelector('input[name="tipo_pessoa"]:checked');
            let tipo = tipoObj ? tipoObj.value : 'PF';
            let docDigitado = tipo === 'PF' ? document.getElementById('edit_cpf').value : document.getElementById('edit_cnpj').value;

            if (window.DOCS_CADASTRADOS && docDigitado && window.DOCS_CADASTRADOS[docDigitado]) {
                if (window.DOCS_CADASTRADOS[docDigitado] !== currentId) {
                    e.preventDefault();
                    window.mostrarAviso(`O ${tipo === 'PF' ? 'CPF' : 'CNPJ'} ${docDigitado} já está registrado no sistema para outro cliente!`, 'erro');
                }
            }
        });
    }
});


// ==========================================
// MÁSCARAS DE INPUT E INTEGRAÇÕES
// ==========================================
window.aplicarMascara = function (input, tipo) {
    let v = input.value.replace(/\D/g, '');
    if (tipo === 'cpf') {
        v = v.replace(/(\d{3})(\d)/, '$1.$2');
        v = v.replace(/(\d{3})(\d)/, '$1.$2');
        v = v.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    } else if (tipo === 'cnpj') {
        v = v.replace(/^(\d{2})(\d)/, '$1.$2');
        v = v.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
        v = v.replace(/\.(\d{3})(\d)/, '.$1/$2');
        v = v.replace(/(\d{4})(\d)/, '$1-$2');
    } else if (tipo === 'tel') {
        v = v.replace(/^(\d{2})(\d)/g, '($1) $2');
        v = v.replace(/(\d{5})(\d)/, '$1-$2');
    } else if (tipo === 'cep') {
        v = v.replace(/(\d{5})(\d)/, '$1-$2');
    }
    input.value = v;
}

// 🚀 O ESPIÃO INTELIGENTE DE CEP (Captura IBGE Invisível e Preenche o Endereço)
window.buscarCEPSeguro = function(cepOriginal) {
    let cepLimpo = cepOriginal.replace(/\D/g, '');
    
    // Reseta o status visual e o campo oculto assim que apaga ou muda o CEP
    let endInput = document.getElementById('edit_endereco');
    let ibgeInput = document.getElementById('edit_ibge');
    let statusIbge = document.getElementById('ibge_status');
    
    if (ibgeInput) ibgeInput.value = '';
    if (statusIbge) statusIbge.style.display = 'none';

    if (cepLimpo.length === 8) {
        if (endInput) endInput.value = "Buscando...";
        
        fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`)
            .then(res => res.json())
            .then(data => {
                if (!data.erro) {
                    if (endInput) endInput.value = data.logradouro || '';
                    if (document.getElementById('edit_bairro')) document.getElementById('edit_bairro').value = data.bairro || '';
                    if (document.getElementById('edit_cidade')) document.getElementById('edit_cidade').value = data.localidade || '';
                    if (document.getElementById('edit_estado')) document.getElementById('edit_estado').value = data.uf || '';
                    
                    // O SEGREDO DO IBGE (GRAVA O CÓDIGO E MOSTRA O SELO VERDE)
                    if (ibgeInput && data.ibge) {
                        ibgeInput.value = data.ibge;
                        if (statusIbge) statusIbge.style.display = 'block';
                    }
                    
                    if (document.getElementById('edit_numero')) document.getElementById('edit_numero').focus();
                } else {
                    if (endInput) endInput.value = "CEP não encontrado";
                }
            })
            .catch(error => {
                console.error("Erro ao consultar o ViaCEP:", error);
                if (endInput) endInput.value = "";
            });
    }
}

window.buscarCNPJ = function (cnpj, prefix = '') {
    let cnpjLimpo = cnpj.replace(/\D/g, '');
    if (cnpjLimpo.length === 14) {
        let campoBairro = document.getElementById(prefix + 'bairro');
        let bairroOriginal = campoBairro ? campoBairro.value : '';
        if (campoBairro) campoBairro.value = "Buscando dados...";

        fetch(`https://publica.cnpj.ws/cnpj/${cnpjLimpo}`)
            .then(response => {
                if (!response.ok) throw new Error('Falha na consulta');
                return response.json();
            })
            .then(data => {
                let estab = data.estabelecimento;

                if (document.getElementById(prefix + 'nome')) document.getElementById(prefix + 'nome').value = data.razao_social || '';
                if (document.getElementById(prefix + 'razao_social')) document.getElementById(prefix + 'razao_social').value = data.razao_social || '';

                // Captura da Inscrição Estadual (IE)
                let inputIe = document.getElementById(prefix + 'ie');
                if (inputIe && estab.inscricoes_estaduais && estab.inscricoes_estaduais.length > 0) {
                    inputIe.value = estab.inscricoes_estaduais[0].inscricao_estadual || '';
                }

                let cepInput = document.getElementById(prefix + 'cep');
                if (cepInput) {
                    cepInput.value = estab.cep || '';
                    aplicarMascara(cepInput, 'cep');
                    // 🚀 APÓS PREENCHER O CEP DO CNPJ.ws, CHAMA O VIACEP PARA PEGAR O IBGE
                    buscarCEPSeguro(estab.cep);
                }
                
                if (document.getElementById(prefix + 'endereco')) document.getElementById(prefix + 'endereco').value = (estab.tipo_logradouro + ' ' + estab.logradouro).trim();
                if (document.getElementById(prefix + 'numero')) document.getElementById(prefix + 'numero').value = estab.numero || '';
                if (document.getElementById(prefix + 'complemento')) document.getElementById(prefix + 'complemento').value = estab.complemento || '';
                if (document.getElementById(prefix + 'bairro')) document.getElementById(prefix + 'bairro').value = estab.bairro || '';
                if (document.getElementById(prefix + 'cidade')) document.getElementById(prefix + 'cidade').value = estab.cidade.nome || '';
                if (document.getElementById(prefix + 'estado')) document.getElementById(prefix + 'estado').value = estab.estado.sigla || '';
                if (document.getElementById(prefix + 'email')) document.getElementById(prefix + 'email').value = estab.email || '';

                let telInput = document.getElementById(prefix + 'telefone');
                if (telInput && estab.ddd1 && estab.telefone1) {
                    telInput.value = `(${estab.ddd1}) ${estab.telefone1}`;
                }
            })
            .catch(error => {
                console.error("Erro no CNPJ:", error);
                if (campoBairro) campoBairro.value = bairroOriginal;
                if (typeof window.mostrarAviso === 'function') window.mostrarAviso("Não foi possível buscar o CNPJ. Preencha manualmente.", 'aviso');
            });
    }
}


window.confirmarExclusao = function (id, nome) {
    if (confirm(`Tem certeza que deseja apagar o cadastro de ${nome}?`)) {
        let form = document.getElementById('formExcluir');
        form.action = `/clientes/excluir/${id}/`;
        form.submit();
    }
}


// ==========================================
// 🚀 LÓGICA DE INTERFACE INTEGRADA E SEGURA (MODAIS)
// ==========================================
window.abrirModalEdicaoSegura = function(btn) {
    document.getElementById('tituloModalCliente').innerText = "✏️ Editar Cadastro";
    
    document.getElementById('edit_id').value = btn.dataset.id;
    document.getElementById('edit_nome').value = btn.dataset.nome;
    document.getElementById('edit_telefone').value = btn.dataset.telefone;
    document.getElementById('edit_email').value = btn.dataset.email;
    document.getElementById('edit_cpf').value = btn.dataset.cpf;
    document.getElementById('edit_cnpj').value = btn.dataset.cnpj;
    document.getElementById('edit_razao_social').value = btn.dataset.razao;
    document.getElementById('edit_ie').value = btn.dataset.ie;
    document.getElementById('edit_cep').value = btn.dataset.cep;
    document.getElementById('edit_endereco').value = btn.dataset.endereco;
    document.getElementById('edit_numero').value = btn.dataset.numero;
    document.getElementById('edit_complemento').value = btn.dataset.complemento;
    document.getElementById('edit_bairro').value = btn.dataset.bairro;
    document.getElementById('edit_cidade').value = btn.dataset.cidade;
    document.getElementById('edit_estado').value = btn.dataset.estado;
    
    // Dados Fiscais Sefaz
    document.getElementById('edit_ind_ie').value = btn.dataset.ind_ie || '9';
    document.getElementById('edit_ibge').value = btn.dataset.ibge || '';
    
    // Controla o visual do selo de sucesso do IBGE
    let statusIbge = document.getElementById('ibge_status');
    if(statusIbge) {
        statusIbge.style.display = btn.dataset.ibge ? 'block' : 'none';
    }

    let tipoStr = btn.dataset.tipo || '';
    document.getElementById('edit_c').checked = tipoStr.includes('CLIENTE');
    document.getElementById('edit_p').checked = tipoStr.includes('PINTOR');

    if(btn.dataset.tipo_pessoa === 'PJ') {
        document.getElementById('radio_pj').checked = true;
        toggleTipoSeguro('PJ');
    } else {
        document.getElementById('radio_pf').checked = true;
        toggleTipoSeguro('PF');
    }

    if(mEdit) mEdit.show();
}

window.abrirModalNovoClienteSeguro = function() {
    document.getElementById('tituloModalCliente').innerText = "✨ Novo Cadastro";
    document.getElementById('formCadastroCliente').reset();
    document.getElementById('edit_id').value = "";
    
    // Zera o IBGE oculto
    document.getElementById('edit_ibge').value = "";
    let statusIbge = document.getElementById('ibge_status');
    if(statusIbge) statusIbge.style.display = 'none';
    
    document.getElementById('radio_pf').checked = true;
    toggleTipoSeguro('PF');
    
    if(mEdit) mEdit.show();
}

window.toggleTipoSeguro = function(tipo) {
    let divPF = document.getElementById('div_pf');
    let divPJ = document.getElementById('div_pj');
    let inputCpf = document.getElementById('edit_cpf');
    let inputCnpj = document.getElementById('edit_cnpj');
    let inputRazao = document.getElementById('edit_razao_social');
    let indIe = document.getElementById('edit_ind_ie');

    if (tipo === 'PJ') {
        if(divPF) divPF.style.display = 'none';
        if(divPJ) divPJ.style.display = 'block';
        if(inputCpf) inputCpf.required = false;
        if(inputCnpj) inputCnpj.required = true;
        if(inputRazao) inputRazao.required = true;
        
        // Se for PJ e estiver marcado como "9", sugere ser contribuinte "1"
        if(indIe && indIe.value === '9'){
            indIe.value = '1';
        }
    } else {
        if(divPJ) divPJ.style.display = 'none';
        if(divPF) divPF.style.display = 'block';
        if(inputCnpj) inputCnpj.required = false;
        if(inputRazao) inputRazao.required = false;
        if(inputCpf) inputCpf.required = true;
        
        // 🚀 PROTEÇÃO: Força Indicador IE = 9 (Não Contribuinte) se for Pessoa Física!
        if(indIe) indIe.value = '9';
    }
}

// ==========================================
// TELA DE HISTÓRICO DE COMPRAS
// ==========================================
function abrirHistorico(clienteId) {
    fetch(`/api/clientes/${clienteId}/historico/`)
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('tabelaHistoricoCliente') || document.getElementById('listaHist');
            tbody.innerHTML = '';
            if (data.historico.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4">Nenhuma compra finalizada encontrada.</td></tr>';
            } else {
                data.historico.forEach(venda => {
                    tbody.innerHTML += `<tr>
                    <td>#${venda.codigo_venda}</td>
                    <td>${venda.data}</td>
                    <td><span class="badge bg-success">Faturado</span></td>
                    <td class="fw-bold text-success">R$ ${venda.valor_total.replace('.', ',')}</td>
                </tr>`;
                });
            }

            if (typeof mHist !== 'undefined') mHist.show();
            else new bootstrap.Modal(document.getElementById('modalHistorico')).show();
        }).catch(e => {
            const tbody = document.getElementById('tabelaHistoricoCliente') || document.getElementById('listaHist');
            tbody.innerHTML = "<tr><td colspan='4' class='text-danger text-center py-4'>Erro ao buscar histórico.</td></tr>";
        });
}

window.verHistorico = function (id, nome) {
    document.getElementById('tituloHist').innerText = `🛒 Compras de ${nome}`;
    abrirHistorico(id);
}


// =========================================================
// TELA DE COLABORADORES E ESCALA DE PONTO (RH)
// =========================================================
const diasSemana = [
    { id: 'seg', nome: 'Segunda-feira' },
    { id: 'ter', nome: 'Terça-feira' },
    { id: 'qua', nome: 'Quarta-feira' },
    { id: 'qui', nome: 'Quinta-feira' },
    { id: 'sex', nome: 'Sexta-feira' },
    { id: 'sab', nome: 'Sábado' },
    { id: 'dom', nome: 'Domingo' }
];

window.renderizarDias = function () {
    const container = document.getElementById('dias-container');
    if (!container) return;

    container.innerHTML = '';

    diasSemana.forEach(dia => {
        container.innerHTML += `
            <div class="row g-2 mb-2 align-items-center py-1 border-bottom border-light" id="row-${dia.id}">
                <div class="col-md-3 fw-bold text-secondary small">${dia.nome}</div>
                <div class="col-md-2"><input type="time" class="form-control form-control-sm dia-ent" data-dia="${dia.id}"></div>
                <div class="col-md-2"><input type="time" class="form-control form-control-sm dia-alm" data-dia="${dia.id}"></div>
                <div class="col-md-2"><input type="time" class="form-control form-control-sm dia-sai" data-dia="${dia.id}"></div>
                <div class="col-md-3">
                    <div class="form-check form-switch mt-1 ms-2">
                        <input class="form-check-input" type="checkbox" id="folga-${dia.id}" onchange="alternarFolga('${dia.id}')">
                        <label class="form-check-label small text-muted fw-bold" for="folga-${dia.id}">Folga</label>
                    </div>
                </div>
            </div>
        `;
    });
}

window.alternarFolga = function (diaId) {
    const isFolga = document.getElementById(`folga-${diaId}`).checked;
    const row = document.getElementById(`row-${diaId}`);

    row.querySelectorAll('input[type="time"]').forEach(input => {
        input.disabled = isFolga;
        if (isFolga) input.value = '';
    });

    if (isFolga) {
        row.style.opacity = '0.5';
        row.style.backgroundColor = '#f8f9fa';
    } else {
        row.style.opacity = '1';
        row.style.backgroundColor = 'transparent';
    }
}

window.aplicarMassa = function () {
    const ent = document.getElementById('fast_ent').value;
    const alm = document.getElementById('fast_alm').value;
    const sai = document.getElementById('fast_sai').value;

    document.querySelectorAll('.chk-dia:checked').forEach(chk => {
        const diaId = chk.value;
        const row = document.getElementById(`row-${diaId}`);

        const folgaChk = document.getElementById(`folga-${diaId}`);
        if (folgaChk.checked) {
            folgaChk.checked = false;
            alternarFolga(diaId);
        }

        row.querySelector('.dia-ent').value = ent;
        row.querySelector('.dia-alm').value = alm;
        row.querySelector('.dia-sai').value = sai;
    });
}

window.limparEscala = function () {
    diasSemana.forEach(dia => {
        const row = document.getElementById(`row-${dia.id}`);
        if (row) {
            row.querySelector('.dia-ent').value = '';
            row.querySelector('.dia-alm').value = '';
            row.querySelector('.dia-sai').value = '';
            document.getElementById(`folga-${dia.id}`).checked = false;
            alternarFolga(dia.id);
        }
    });

    if (document.getElementById('fast_ent')) {
        document.getElementById('fast_ent').value = '';
        document.getElementById('fast_alm').value = '';
        document.getElementById('fast_sai').value = '';
    }
}

window.editarRH = function (id, login, perfil, comis, btnElement) {
    document.getElementById('rh_id').value = id;
    document.getElementById('rh_login').value = login;

    let selectPerfil = document.getElementById('rh_perfil');
    if (perfil) { selectPerfil.value = perfil; }

    let valorComissao = comis ? String(comis).replace(',', '.') : "0";
    document.getElementById('rh_comis').value = valorComissao;

    limparEscala();

    if (btnElement) {
        try {
            let escalaRaw = btnElement.getAttribute('data-escala');
            if (escalaRaw && escalaRaw !== 'None' && escalaRaw !== '{}') {
                const escala = JSON.parse(escalaRaw.replace(/'/g, '"'));

                diasSemana.forEach(dia => {
                    if (escala[dia.id]) {
                        const dados = escala[dia.id];
                        const row = document.getElementById(`row-${dia.id}`);

                        if (dados.folga) {
                            document.getElementById(`folga-${dia.id}`).checked = true;
                            alternarFolga(dia.id);
                        } else {
                            row.querySelector('.dia-ent').value = dados.ent || '';
                            row.querySelector('.dia-alm').value = dados.alm || '';
                            row.querySelector('.dia-sai').value = dados.sai || '';
                        }
                    }
                });
            }
        } catch (e) {
            console.error("Erro ao carregar escala:", e);
        }
    }

    if (modalColaborador) modalColaborador.show();
}

window.abrirModalRH = function () {
    document.getElementById('rh_id').value = '';
    document.getElementById('rh_login').value = '';
    document.getElementById('rh_perfil').value = 'Vendedor';
    document.getElementById('rh_comis').value = '0';

    limparEscala();

    if (modalColaborador) modalColaborador.show();
}

document.addEventListener("DOMContentLoaded", function () {
    renderizarDias();

    const formRH = document.querySelector('#modalRH form');
    if (formRH) {
        formRH.addEventListener('submit', function () {
            let escalaFinal = {};
            diasSemana.forEach(dia => {
                const row = document.getElementById(`row-${dia.id}`);
                if (row) {
                    let ent = row.querySelector('.dia-ent').value;
                    let alm = row.querySelector('.dia-alm').value;
                    let sai = row.querySelector('.dia-sai').value;
                    let isChecked = document.getElementById(`folga-${dia.id}`).checked;

                    let isFolga = isChecked || (!ent && !sai);

                    escalaFinal[dia.id] = {
                        folga: isFolga,
                        ent: isFolga ? '' : ent,
                        alm: isFolga ? '' : alm,
                        sai: isFolga ? '' : sai
                    };
                }
            });
            document.getElementById('escala_json').value = JSON.stringify(escalaFinal);
        });
    }
});
