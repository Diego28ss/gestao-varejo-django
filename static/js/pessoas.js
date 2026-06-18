// ==========================================
// 👥 MÓDULO DE PESSOAS (CLIENTES E COLABORADORES)
// ==========================================

let modalColaborador, mEdit, mHist;

document.addEventListener("DOMContentLoaded", function() {
    // Inicialização dos Modais
    let elRH = document.getElementById('modalRH');
    if(elRH) modalColaborador = new bootstrap.Modal(elRH);

    let elEdit = document.getElementById('modalEditar');
    if(elEdit) mEdit = new bootstrap.Modal(elEdit);

    let elHist = document.getElementById('modalHist');
    if(elHist) mHist = new bootstrap.Modal(elHist);

    // Validação de Duplicidade e Telefone (Apenas no ecrã de Consulta de Clientes)
    let formCadastro = document.getElementById('formCadastroCliente');
    if(formCadastro) {
        formCadastro.addEventListener('submit', function(e) {
            let tel = document.getElementById('edit_telefone').value.replace(/\D/g, '');
            if (tel.length !== 11) {
                e.preventDefault();
                alert("⚠️ ALERTA DE ERRO:\n\nO número de Celular/WhatsApp deve conter exatamente o DDD (2 números) + 9 dígitos.");
                document.getElementById('edit_telefone').focus();
                return;
            }

            let currentId = document.getElementById('edit_id').value;
            let tipo = document.querySelector('input[name="tipo_pessoa"]:checked').value;
            let docDigitado = tipo === 'PF' ? document.getElementById('edit_cpf').value : document.getElementById('edit_cnpj').value;

            // Usa o dicionário injetado pelo Django na tela
            if (window.DOCS_CADASTRADOS && docDigitado && window.DOCS_CADASTRADOS[docDigitado]) {
                if (window.DOCS_CADASTRADOS[docDigitado] !== currentId) {
                    e.preventDefault();
                    alert(`⚠️ ALERTA DE SEGURANÇA:\n\nO ${tipo==='PF'?'CPF':'CNPJ'} ${docDigitado} já está registado no sistema para outro cliente!`);
                }
            }
        });
    }
});

// ==========================================
// MÁSCARAS DE INPUT
// ==========================================
function aplicarMascara(input, tipo) {
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

// ==========================================
// INTEGRAÇÕES (VIACEP E CNPJ.WS)
// ==========================================
function toggleTipo(tipo, prefix = '') {
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

function buscarCEP(cepOriginal, prefix = '') {
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

function buscarCNPJ(cnpj, prefix = '') {
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

                let ie = '';
                if (estab.inscricoes_estaduais && estab.inscricoes_estaduais.length > 0) {
                    let ieAtiva = estab.inscricoes_estaduais.find(i => i.ativo === true);
                    ie = ieAtiva ? ieAtiva.inscricao_estadual : estab.inscricoes_estaduais[0].inscricao_estadual;
                }
                
                let campoIE = document.getElementById(prefix === '' ? 'inscricao_estadual' : 'edit_ie');
                if (campoIE) {
                    campoIE.value = ie;
                    if (!ie) campoIE.placeholder = "Isento / Não encontrada";
                }
            })
            .catch(error => {
                console.error("Erro no CNPJ:", error);
                if(campoBairro) campoBairro.value = bairroOriginal;
                alert("Não foi possível buscar o CNPJ automaticamente. Por favor, preencha manualmente.");
            });
    }
}

// ==========================================
// TELA DE CLIENTES (AÇÕES)
// ==========================================
function confirmarExclusao(id, nome) {
    if(confirm(`Tem certeza que deseja apagar o cadastro de ${nome}?`)) {
        let form = document.getElementById('formExcluir');
        form.action = `/clientes/excluir/${id}/`;
        form.submit();
    }
}

function verHistorico(nome) {
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

function abrirModalNovoCliente() {
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

function abrirModalEditar(id, tipo_pessoa, nome, tel, email, cpf, cnpj, razao, ie, tipo_cat, cep, end, num, comp, bairro, cidade, estado) {
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

// ==========================================
// TELA DE COLABORADORES
// ==========================================
function abrirModalRH() {
    document.getElementById('rh_id').value = "";
    document.getElementById('rh_login').value = "";
    document.getElementById('rh_perfil').value = "Colaborador";
    document.getElementById('rh_comis').value = "0";
    modalColaborador.show();
}

function editarRH(id, login, perfil, comis) {
    document.getElementById('rh_id').value = id;
    document.getElementById('rh_login').value = login;

    let selectPerfil = document.getElementById('rh_perfil');
    if (perfil) { selectPerfil.value = perfil; }

    let valorComissao = comis ? String(comis).replace(',', '.') : "0";
    document.getElementById('rh_comis').value = valorComissao;

    modalColaborador.show();
}
