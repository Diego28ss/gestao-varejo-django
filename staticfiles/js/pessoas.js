// ==========================================
// 👥 MÓDULO DE PESSOAS (CLIENTES E COLABORADORES)
// ==========================================

let modalColaborador, mEdit, mHist;

document.addEventListener("DOMContentLoaded", function() {
    let elRH = document.getElementById('modalRH');
    if(elRH) modalColaborador = new bootstrap.Modal(elRH);

    let elEdit = document.getElementById('modalEditar');
    if(elEdit) mEdit = new bootstrap.Modal(elEdit);

    let elHist = document.getElementById('modalHist');
    if(elHist) mHist = new bootstrap.Modal(elHist);

    let formCadastro = document.getElementById('formCadastroCliente');
    if(formCadastro) {
        formCadastro.addEventListener('submit', function(e) {
            let tel = document.getElementById('edit_telefone').value.replace(/\D/g, '');
            if (tel.length !== 11) {
                e.preventDefault();
                window.mostrarAviso("O número de Celular/WhatsApp deve conter exatamente o DDD (2 números) + 9 dígitos.", 'erro');
                document.getElementById('edit_telefone').focus();
                return;
            }

            let currentId = document.getElementById('edit_id').value;
            let tipo = document.querySelector('input[name="tipo_pessoa"]:checked').value;
            let docDigitado = tipo === 'PF' ? document.getElementById('edit_cpf').value : document.getElementById('edit_cnpj').value;

            if (window.DOCS_CADASTRADOS && docDigitado && window.DOCS_CADASTRADOS[docDigitado]) {
                if (window.DOCS_CADASTRADOS[docDigitado] !== currentId) {
                    e.preventDefault();
                    window.mostrarAviso(`O ${tipo==='PF'?'CPF':'CNPJ'} ${docDigitado} já está registrado no sistema para outro cliente!`, 'erro');
                }
            }
        });
    }
});


// ==========================================
// MÁSCARAS DE INPUT E INTEGRAÇÕES
// ==========================================
window.aplicarMascara = function(input, tipo) {
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

window.toggleTipo = function(tipo, prefix = '') {
    let cpf = document.getElementById(prefix + 'cpf');
    let cnpj = document.getElementById(prefix + 'cnpj');
    let razao = document.getElementById(prefix + 'razao_social');
    let labelNome = document.getElementById('label_nome');

    if (tipo === 'PF') {
        document.getElementById('div_pf').style.display = 'block';
        document.getElementById('div_pj').style.display = 'none';
        let radio = document.getElementById(prefix === '' ? 'pf' : 'radio_pf');
        if(radio) radio.checked = true;
        if(labelNome) labelNome.innerText = "Nome Completo *";

        if(cpf) cpf.setAttribute('required', 'required');
        if(cnpj) cnpj.removeAttribute('required');
        if(razao) razao.removeAttribute('required');
    } else {
        document.getElementById('div_pf').style.display = 'none';
        document.getElementById('div_pj').style.display = 'block';
        let radio = document.getElementById(prefix === '' ? 'pj' : 'radio_pj');
        if(radio) radio.checked = true;
        if(labelNome) labelNome.innerText = prefix === '' ? "Razão Social / Nome Fantasia *" : "Nome Fantasia (Apelido) *";

        if(cpf) cpf.removeAttribute('required');
        if(cnpj) cnpj.setAttribute('required', 'required');
        if(razao) razao.setAttribute('required', 'required');
    }
}

window.buscarCEP = function(cepOriginal, prefix = '') {
    let cep = cepOriginal.replace(/\D/g, ''); 
    if (cep.length === 8) {
        let endInput = document.getElementById(prefix + 'endereco');
        if(endInput) endInput.value = "Buscando...";
        fetch(`https://viacep.com.br/ws/${cep}/json/`)
            .then(res => res.json())
            .then(data => {
                if (!data.erro) {
                    if(document.getElementById(prefix + 'endereco')) document.getElementById(prefix + 'endereco').value = data.logradouro || '';
                    if(document.getElementById(prefix + 'bairro')) document.getElementById(prefix + 'bairro').value = data.bairro || '';
                    if(document.getElementById(prefix + 'cidade')) document.getElementById(prefix + 'cidade').value = data.localidade || '';
                    if(document.getElementById(prefix + 'estado')) document.getElementById(prefix + 'estado').value = data.uf || '';
                    if(document.getElementById(prefix + 'numero')) document.getElementById(prefix + 'numero').focus(); 
                } else {
                    if(endInput) endInput.value = "CEP não encontrado";
                }
            });
    }
}

window.buscarCNPJ = function(cnpj, prefix = '') {
    let cnpjLimpo = cnpj.replace(/\D/g, '');
    if (cnpjLimpo.length === 14) {
        let campoBairro = document.getElementById(prefix + 'bairro');
        let bairroOriginal = campoBairro ? campoBairro.value : '';
        if(campoBairro) campoBairro.value = "Buscando dados...";

        fetch(`https://publica.cnpj.ws/cnpj/${cnpjLimpo}`)
            .then(response => {
                if (!response.ok) throw new Error('Falha na consulta');
                return response.json();
            })
            .then(data => {
                let estab = data.estabelecimento;
                
                if(document.getElementById(prefix + 'nome')) document.getElementById(prefix + 'nome').value = data.razao_social || '';
                if(document.getElementById(prefix + 'razao_social')) document.getElementById(prefix + 'razao_social').value = data.razao_social || '';
                
                let cepInput = document.getElementById(prefix + 'cep');
                if(cepInput) {
                    cepInput.value = estab.cep || '';
                    aplicarMascara(cepInput, 'cep');
                }
                if(document.getElementById(prefix + 'endereco')) document.getElementById(prefix + 'endereco').value = (estab.tipo_logradouro + ' ' + estab.logradouro).trim();
                if(document.getElementById(prefix + 'numero')) document.getElementById(prefix + 'numero').value = estab.numero || '';
                if(document.getElementById(prefix + 'complemento')) document.getElementById(prefix + 'complemento').value = estab.complemento || '';
                if(document.getElementById(prefix + 'bairro')) document.getElementById(prefix + 'bairro').value = estab.bairro || '';
                if(document.getElementById(prefix + 'cidade')) document.getElementById(prefix + 'cidade').value = estab.cidade.nome || '';
                if(document.getElementById(prefix + 'estado')) document.getElementById(prefix + 'estado').value = estab.estado.sigla || '';
                if(document.getElementById(prefix + 'email')) document.getElementById(prefix + 'email').value = estab.email || '';
                
                let telInput = document.getElementById(prefix + 'telefone');
                if(telInput && estab.ddd1 && estab.telefone1) {
                    telInput.value = `(${estab.ddd1}) ${estab.telefone1}`;
                }
            })
            .catch(error => {
                console.error("Erro no CNPJ:", error);
                if(campoBairro) campoBairro.value = bairroOriginal;
                window.mostrarAviso("Não foi possível buscar o CNPJ automaticamente. Por favor, preencha manualmente.", 'aviso');
            });
    }
}

window.confirmarExclusao = function(id, nome) {
    if(confirm(`Tem certeza que deseja apagar o cadastro de ${nome}?`)) {
        let form = document.getElementById('formExcluir');
        form.action = `/clientes/excluir/${id}/`;
        form.submit();
    }
}

window.verHistorico = function(nome) {
    document.getElementById('tituloHist').innerText = `🛒 Compras de ${nome}`;
    mHist.show();
    document.getElementById('listaHist').innerHTML = "<tr><td colspan='4'>Buscando compras...</td></tr>";
    fetch(`/api/historico-cliente/?nome=${encodeURIComponent(nome)}`)
        .then(r => r.json())
        .then(d => {
            let h = '';
            if(d.historico.length === 0) h = "<tr><td colspan='4' class='py-4'>Sem compras registradas.</td></tr>";
            else d.historico.forEach(v => h += `<tr><td>#${v.id}</td><td>${v.data}</td><td>${v.vendedor}</td><td class="fw-bold text-success">R$ ${v.valor.toFixed(2).replace('.', ',')}</td></tr>`);
            document.getElementById('listaHist').innerHTML = h;
        }).catch(e => document.getElementById('listaHist').innerHTML = "<tr><td colspan='4' class='text-danger'>Erro.</td></tr>");
}

window.abrirModalNovoCliente = function() {
    document.getElementById('tituloModalCliente').innerHTML = "✨ Novo Cadastro";
    document.getElementById('edit_id').value = "";
    
    let campos = ['nome', 'telefone', 'email', 'cpf', 'cnpj', 'ie', 'razao_social', 'cep', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'estado'];
    campos.forEach(c => {
        let el = document.getElementById('edit_' + c);
        if(el) el.value = "";
    });
    
    document.getElementById('edit_c').checked = true;
    document.getElementById('edit_p').checked = false;
    
    toggleTipo('PF', 'edit_');
    mEdit.show();
}

window.abrirModalEditar = function(id, tipo_pessoa, nome, tel, email, cpf, cnpj, razao, ie, tipo_cat, cep, end, num, comp, bairro, cidade, estado) {
    document.getElementById('tituloModalCliente').innerHTML = "✏️ Editar Ficha";
    document.getElementById('edit_id').value = id;
    
    document.getElementById('edit_nome').value = nome;
    document.getElementById('edit_telefone').value = tel;
    document.getElementById('edit_email').value = email;
    document.getElementById('edit_cpf').value = cpf;
    document.getElementById('edit_cnpj').value = cnpj;
    document.getElementById('edit_razao_social').value = razao;
    document.getElementById('edit_ie').value = ie;
    document.getElementById('edit_cep').value = cep;
    document.getElementById('edit_endereco').value = end;
    document.getElementById('edit_numero').value = num;
    document.getElementById('edit_complemento').value = comp;
    document.getElementById('edit_bairro').value = bairro;
    document.getElementById('edit_cidade').value = cidade;
    document.getElementById('edit_estado').value = estado;

    document.getElementById('edit_c').checked = tipo_cat.includes("CLIENTE");
    document.getElementById('edit_p').checked = tipo_cat.includes("PINTOR");

    toggleTipo(tipo_pessoa === 'PJ' ? 'PJ' : 'PF', 'edit_');
    mEdit.show();
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

window.renderizarDias = function() {
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

window.alternarFolga = function(diaId) {
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

window.aplicarMassa = function() {
    const ent = document.getElementById('fast_ent').value;
    const alm = document.getElementById('fast_alm').value;
    const sai = document.getElementById('fast_sai').value;

    document.querySelectorAll('.chk-dia:checked').forEach(chk => {
        const diaId = chk.value;
        const row = document.getElementById(`row-${diaId}`);
        
        const folgaChk = document.getElementById(`folga-${diaId}`);
        if(folgaChk.checked) {
            folgaChk.checked = false;
            alternarFolga(diaId);
        }

        row.querySelector('.dia-ent').value = ent;
        row.querySelector('.dia-alm').value = alm;
        row.querySelector('.dia-sai').value = sai;
    });
}

window.limparEscala = function() {
    diasSemana.forEach(dia => {
        const row = document.getElementById(`row-${dia.id}`);
        if(row) {
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

// O antigo "carteiro" e a lógica juntaram-se na mesma função
window.editarRH = function(id, login, perfil, comis, btnElement) {
    document.getElementById('rh_id').value = id;
    document.getElementById('rh_login').value = login;

    let selectPerfil = document.getElementById('rh_perfil');
    if (perfil) { selectPerfil.value = perfil; }

    let valorComissao = comis ? String(comis).replace(',', '.') : "0";
    document.getElementById('rh_comis').value = valorComissao;
    
    limparEscala();

    if (btnElement) {
        try {
            // A própria função extrai a string JSON do elemento clicado
            let escalaRaw = btnElement.getAttribute('data-escala');
            if (escalaRaw && escalaRaw !== 'None' && escalaRaw !== '{}') {
                const escala = JSON.parse(escalaRaw.replace(/'/g, '"')); 
                
                diasSemana.forEach(dia => {
                    if(escala[dia.id]) {
                        const dados = escala[dia.id];
                        const row = document.getElementById(`row-${dia.id}`);
                        
                        if(dados.folga) {
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
        } catch(e) {
            console.error("Erro ao carregar escala:", e);
        }
    }

    if(modalColaborador) modalColaborador.show();
}

window.abrirModalRH = function() {
    document.getElementById('rh_id').value = '';
    document.getElementById('rh_login').value = '';
    // Atualizado para a nova nomenclatura
    document.getElementById('rh_perfil').value = 'Vendedor';
    document.getElementById('rh_comis').value = '0';
    
    limparEscala();

    if(modalColaborador) modalColaborador.show();
}


document.addEventListener("DOMContentLoaded", function() {
    renderizarDias(); 

    const formRH = document.querySelector('#modalRH form');
    if (formRH) {
        formRH.addEventListener('submit', function() {
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
