// ==========================================
// 📦 MÓDULO DE ESTOQUE E LOGÍSTICA
// Ficheiro unificado para: Controle de Produtos e Entrada de Carga (Bipador)
// ==========================================

let meuModalProduto;
let tagsFiltroAtivas = [];
let itensEntrada = [];

// VARIÁVEL GLOBAL PARA OS DROPDOWNS (LUPAS)
let dropdownFiltros = {
    familia: '',
    marca: '',
    status: ''
};

document.addEventListener("DOMContentLoaded", function() {
    let elProduto = document.getElementById('modalProduto');
    if(elProduto) meuModalProduto = new bootstrap.Modal(elProduto);

    // ========================================================
    // 🚀 ESCUTA ENCOMENDAS DA TELA DE NFE (CRIAR NOVO PRODUTO)
    // ========================================================
    let dadosNfeStr = sessionStorage.getItem('nfe_novo_produto');
    
    if (dadosNfeStr) {
        let dadosNfe = JSON.parse(dadosNfeStr);
        sessionStorage.removeItem('nfe_novo_produto');

        setTimeout(() => {
            abrirModalNovo(); 
            
            setTimeout(() => {
                let formNome = document.getElementById('formNome');
                if (formNome) formNome.value = dadosNfe.nome || '';
                
                // 🚀 LÓGICA INTELIGENTE DO CÓDIGO DE BARRAS
                let formCodBarras = document.getElementById('formCodBarras');
                if (formCodBarras) {
                    if (dadosNfe.cod_barras && dadosNfe.cod_barras.toUpperCase() !== 'SEM GTIN') {
                        formCodBarras.value = dadosNfe.cod_barras;
                        document.getElementById('chkSemGtin').checked = false;
                        formCodBarras.readOnly = false;
                        formCodBarras.classList.remove('bg-light');
                    } else {
                        document.getElementById('chkSemGtin').checked = true;
                        formCodBarras.value = 'SEM GTIN';
                        formCodBarras.readOnly = true;
                        formCodBarras.classList.add('bg-light');
                    }
                }
                
                let formPrecoCusto = document.getElementById('formPrecoCusto');
                if (formPrecoCusto) formPrecoCusto.value = dadosNfe.custo || '';
                
                // 🚀 PREENCHE O NCM AUTOMATICAMENTE
                let formNcm = document.getElementById('formNcm');
                if (formNcm && dadosNfe.ncm) formNcm.value = dadosNfe.ncm;
                
                let selectUn = document.getElementById('formUnidade');
                if(selectUn && dadosNfe.unidade) {
                    for(let i = 0; i < selectUn.options.length; i++) {
                        if(selectUn.options[i].value.toUpperCase() === dadosNfe.unidade.toUpperCase()) {
                            selectUn.selectedIndex = i;
                            break;
                        }
                    }
                }

                let selectCsosn = document.getElementById('formCsosn');
                if(selectCsosn && dadosNfe.csosn) {
                    for(let i = 0; i < selectCsosn.options.length; i++) {
                        if(selectCsosn.options[i].value.includes(dadosNfe.csosn)) {
                            selectCsosn.selectedIndex = i;
                            break;
                        }
                    }
                }

                if (typeof window.mostrarAviso === "function") {
                    window.mostrarAviso('Dados da NFe importados! Complete a Marca e Família para salvar.', 'sucesso');
                }
                
            }, 400); 
        }, 500); 
    }
});


// ==========================================
// 🏭 CONTROLE DE PRODUTOS
// ==========================================

function toggleSemGtin() {
    let chk = document.getElementById('chkSemGtin');
    let inputBarras = document.getElementById('formCodBarras');
    if (!chk || !inputBarras) return;

    if (chk.checked) {
        inputBarras.value = 'SEM GTIN';
        inputBarras.readOnly = true;
        inputBarras.classList.add('bg-light');
    } else {
        if (inputBarras.value === 'SEM GTIN') inputBarras.value = '';
        inputBarras.readOnly = false;
        inputBarras.classList.remove('bg-light');
    }
}

function toggleCamposTintometrico() {
    let chkBase = document.getElementById('chkProdutoBase');
    let divBase = document.getElementById('divCamposTintometrico');
    if (!chkBase || !divBase) return;
    
    if (chkBase.checked) {
        divBase.style.display = 'block';
        document.getElementById('formBaseTintometrica').required = true;
        document.getElementById('formTamanhoTintometrico').required = true;
        
        document.getElementById('chkProdutoCorante').checked = false;
        toggleCamposCorante(true); 
    } else {
        divBase.style.display = 'none';
        document.getElementById('formBaseTintometrica').required = false;
        document.getElementById('formTamanhoTintometrico').required = false;
    }
}

function toggleCamposCorante(preventLoop = false) {
    let chkCorante = document.getElementById('chkProdutoCorante');
    let divCorante = document.getElementById('divCamposCorante');
    if (!chkCorante || !divCorante) return;
    
    if (chkCorante.checked) {
        divCorante.style.display = 'block';
        document.getElementById('formCoranteTintometrico').required = true;
        
        if (!preventLoop) {
            document.getElementById('chkProdutoBase').checked = false;
            toggleCamposTintometrico();
        }
    } else {
        divCorante.style.display = 'none';
        document.getElementById('formCoranteTintometrico').required = false;
    }
}

// ==========================================
// 🔍 MOTOR DE PESQUISA E FILTRAGEM
// ==========================================
function gerenciarEnterPesquisa(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        let input = document.getElementById('pesquisaPdv');
        let valor = input.value.toUpperCase().trim();

        if (valor !== "" && !tagsFiltroAtivas.includes(valor)) {
            tagsFiltroAtivas.push(valor);
            renderizarTagsNaTela();
            input.value = "";
            executarFiltragemCombinada();
        }
    }
}

function renderizarTagsNaTela() {
    let container = document.getElementById('containerTagsPdv');
    if (!container) return;
    container.innerHTML = "";
    tagsFiltroAtivas.forEach(function(tag, index) {
        container.innerHTML += `
            <span class="badge text-white px-2 py-2 shadow-sm d-flex align-items-center gap-2" 
                  style="background-color: #0D1B4C; font-size: 0.85rem; border-left: 4px solid #1565C0;">
                🔍 ${tag}
                <button type="button" class="btn-close btn-close-white" style="font-size: 0.65rem;" 
                        onclick="removerTagFiltro(${index})"></button>
            </span>
        `;
    });
}

function removerTagFiltro(index) {
    tagsFiltroAtivas.splice(index, 1);
    renderizarTagsNaTela();
    executarFiltragemCombinada();
}

function aplicarFiltro(campo, valor) {
    dropdownFiltros[campo] = valor.toUpperCase();
    executarFiltragemCombinada();
}

function executarFiltragemCombinada() {
    let linhas = document.querySelectorAll('.linha-produto');
    let visiveis = 0;

    linhas.forEach(function(linha) {
        let btn = linha.querySelector('button[onclick="prepararEdicao(this)"]');
        if (!btn) return;

        let nome = (linha.getAttribute('data-busca-nome') || '').toUpperCase();
        let barras = (linha.getAttribute('data-busca-barras') || '').toUpperCase();
        let interno = (linha.getAttribute('data-busca-interno') || '').toUpperCase();
        let rowMarca = (linha.getAttribute('data-busca-marca') || '').toUpperCase();
        let rowFamilia = (linha.getAttribute('data-busca-familia') || '').toUpperCase();
        let rowStatus = (btn.getAttribute('data-status') || '').toUpperCase();

        let passaTags = true;
        if (tagsFiltroAtivas.length > 0) {
            passaTags = tagsFiltroAtivas.every(function(tag) {
                return nome.includes(tag) || barras.includes(tag) || interno.includes(tag) || rowMarca.includes(tag) || rowFamilia.includes(tag);
            });
        }

        let passaFamilia = dropdownFiltros.familia === '' || rowFamilia === dropdownFiltros.familia;
        let passaMarca = dropdownFiltros.marca === '' || rowMarca === dropdownFiltros.marca;
        let passaStatus = dropdownFiltros.status === '' || rowStatus === dropdownFiltros.status;

        if (passaTags && passaFamilia && passaMarca && passaStatus) {
            linha.style.display = "";
            visiveis++;
        } else {
            linha.style.display = "none";
        }
    });

    let linhaAviso = document.getElementById('linhaNenhumResultado');
    if (linhaAviso) linhaAviso.style.display = visiveis === 0 ? "" : "none";
}

function aplicarOrdenacao(campo, ordem) {
    let tbody = document.querySelector('#tabelaEstoque tbody');
    if (!tbody) return;

    let linhasArray = Array.from(tbody.querySelectorAll('.linha-produto'));

    linhasArray.sort((a, b) => {
        let btnA = a.querySelector('button[onclick="prepararEdicao(this)"]');
        let btnB = b.querySelector('button[onclick="prepararEdicao(this)"]');
        if (!btnA || !btnB) return 0;
        
        let valA = 0, valB = 0;

        if (campo === 'custo') {
            valA = parseFloat(btnA.getAttribute('data-custo').replace(',', '.')) || 0;
            valB = parseFloat(btnB.getAttribute('data-custo').replace(',', '.')) || 0;
        } else if (campo === 'venda') {
            valA = parseFloat(btnA.getAttribute('data-venda').replace(',', '.')) || 0;
            valB = parseFloat(btnB.getAttribute('data-venda').replace(',', '.')) || 0;
        } else if (campo === 'estoque') {
            valA = parseFloat(btnA.getAttribute('data-estoque')) || 0;
            valB = parseFloat(btnB.getAttribute('data-estoque')) || 0;
        }

        return ordem === 'asc' ? valA - valB : valB - valA;
    });

    linhasArray.forEach(linha => tbody.appendChild(linha));
    
    let linhaVazia = document.getElementById('linhaVazia');
    let linhaNenhum = document.getElementById('linhaNenhumResultado');
    if(linhaVazia) tbody.appendChild(linhaVazia);
    if(linhaNenhum) tbody.appendChild(linhaNenhum);
}

// ==========================================
// 💰 MODAIS E PRECIFICAÇÃO
// ==========================================
function calcularVenda() {
    let elCusto = document.getElementById('formPrecoCusto');
    let elMargem = document.getElementById('formMargemLucro');
    if(!elCusto || !elMargem) return;

    let custo = parseFloat(elCusto.value.replace(',', '.')) || 0;
    let margem = parseFloat(elMargem.value.replace(',', '.')) || 0;
    let venda = custo + (custo * (margem / 100));
    document.getElementById('formPrecoVenda').value = venda.toFixed(2).replace('.', ',');
}

function calcularMargem() {
    let elCusto = document.getElementById('formPrecoCusto');
    let elVenda = document.getElementById('formPrecoVenda');
    if(!elCusto || !elVenda) return;

    let custo = parseFloat(elCusto.value.replace(',', '.')) || 0;
    let venda = parseFloat(elVenda.value.replace(',', '.')) || 0;
    
    if (custo > 0) {
        let margem = ((venda - custo) / custo) * 100;
        document.getElementById('formMargemLucro').value = margem.toFixed(2).replace('.', ',');
    } else if (venda > 0 && custo === 0) {
        document.getElementById('formMargemLucro').value = "100,00";
    } else {
        document.getElementById('formMargemLucro').value = "0,00";
    }
}

function abrirModalNovo() {
    document.getElementById('modalTitulo').innerText = "📦 Novo Produto";
    document.getElementById('formId').value = "";
    document.getElementById('formNome').value = "";
    
    document.getElementById('formCodBarras').value = "";
    document.getElementById('chkSemGtin').checked = false;
    document.getElementById('formCodBarras').readOnly = false;
    document.getElementById('formCodBarras').classList.remove('bg-light');
    
    const campoCodInterno = document.getElementById('formCodInterno');
    campoCodInterno.value = "";
    campoCodInterno.placeholder = "Automático";
    campoCodInterno.readOnly = true;

    document.getElementById('formPrecoCusto').value = "0,00";
    document.getElementById('formMargemLucro').value = "0,00";
    document.getElementById('formPrecoVenda').value = "0,00";
    document.getElementById('formMarca').value = "";
    document.getElementById('formFamilia').value = "";
    document.getElementById('formStatus').value = "ATIVO";
    document.getElementById('formEstoque').value = "0";
    document.getElementById('formUnidade').value = "UN";

    document.getElementById('formOrigem').value = "0"; 
    document.getElementById('formCsosn').value = "102"; 
    document.getElementById('formNcm').value = "";
    document.getElementById('formCest').value = "";

    document.getElementById('chkProdutoBase').checked = false;
    document.getElementById('formBaseTintometrica').value = "";
    document.getElementById('formTamanhoTintometrico').value = "";
    toggleCamposTintometrico();
    
    document.getElementById('chkProdutoCorante').checked = false;
    document.getElementById('formCoranteTintometrico').value = "";
    toggleCamposCorante();

    if(meuModalProduto) meuModalProduto.show();
}

function prepararEdicao(botao) {
    document.getElementById('modalTitulo').innerText = "✏️ Editar Produto";

    document.getElementById('formId').value = botao.getAttribute('data-id');
    document.getElementById('formNome').value = botao.getAttribute('data-nome');
    
    let codBarras = botao.getAttribute('data-cod');
    document.getElementById('formCodBarras').value = codBarras;
    if (codBarras === 'SEM GTIN') {
        document.getElementById('chkSemGtin').checked = true;
        document.getElementById('formCodBarras').readOnly = true;
        document.getElementById('formCodBarras').classList.add('bg-light');
    } else {
        document.getElementById('chkSemGtin').checked = false;
        document.getElementById('formCodBarras').readOnly = false;
        document.getElementById('formCodBarras').classList.remove('bg-light');
    }
    
    let codInterno = botao.getAttribute('data-cod_interno');
    const campoCodInterno = document.getElementById('formCodInterno');
    campoCodInterno.value = codInterno || "---";
    campoCodInterno.readOnly = true;

    document.getElementById('formPrecoCusto').value = botao.getAttribute('data-custo').replace('.', ',');
    document.getElementById('formMargemLucro').value = botao.getAttribute('data-margem').replace('.', ',');
    document.getElementById('formPrecoVenda').value = botao.getAttribute('data-venda').replace('.', ',');
    document.getElementById('formMarca').value = botao.getAttribute('data-marca');
    document.getElementById('formFamilia').value = botao.getAttribute('data-familia');

    let status = botao.getAttribute('data-status');
    document.getElementById('formStatus').value = status ? status : "ATIVO";

    document.getElementById('formEstoque').value = botao.getAttribute('data-estoque');
    document.getElementById('formUnidade').value = botao.getAttribute('data-unidade');

    let origemProduto = botao.getAttribute('data-origem');
    document.getElementById('formOrigem').value = origemProduto ? origemProduto : "0";
    
    let csosn = botao.getAttribute('data-csosn');
    document.getElementById('formCsosn').value = csosn ? csosn : "102";
    document.getElementById('formNcm').value = botao.getAttribute('data-ncm');
    document.getElementById('formCest').value = botao.getAttribute('data-cest');

    // Integração com as variáveis injetadas pelo HTML
    if (window.MAPA_VINCULOS && codInterno) {
        let vinculoBase = window.MAPA_VINCULOS[codInterno];
        if (vinculoBase) {
            document.getElementById('chkProdutoBase').checked = true;
            document.getElementById('formBaseTintometrica').value = vinculoBase.base;
            document.getElementById('formTamanhoTintometrico').value = vinculoBase.tamanho;
        } else {
            document.getElementById('chkProdutoBase').checked = false;
            document.getElementById('formBaseTintometrica').value = "";
            document.getElementById('formTamanhoTintometrico').value = "";
        }
    }
    
    if (window.MAPA_VINCULOS_PIGMENTOS && codInterno) {
        let idFormulaCorante = window.MAPA_VINCULOS_PIGMENTOS[codInterno];
        if (idFormulaCorante) {
            document.getElementById('chkProdutoCorante').checked = true;
            document.getElementById('formCoranteTintometrico').value = idFormulaCorante;
        } else {
            document.getElementById('chkProdutoCorante').checked = false;
            document.getElementById('formCoranteTintometrico').value = "";
        }
    }
    
    toggleCamposTintometrico();
    toggleCamposCorante(true); 

    if(meuModalProduto) meuModalProduto.show();
}

// ==========================================
// 🚀 ENTRADA DE CARGA (BIPADOR)
// ==========================================
function processarBip(event, codigoBruto) {
    if (event.key === "Enter") {
        let codigoLimpo = codigoBruto.trim();
        if (codigoLimpo === "") return;

        let urlSegura = `/api/produto-por-codigo/?codigo=${codigoLimpo}&_nocache=${Date.now()}`;

        fetch(urlSegura)
            .then(res => {
                if (!res.ok) throw new Error("Erro na rota");
                return res.json();
            })
            .then(data => {
                if (data.status === 'ok') {
                    let item = itensEntrada.find(i => i.id === data.id);
                    if (item) {
                        item.qtd++;
                    } else {
                        itensEntrada.push({id: data.id, nome: data.nome, codigo: codigoLimpo, qtd: 1});
                    }
                    document.getElementById('bipador').value = '';
                    renderListaCarga();
                } else {
                    window.mostrarAviso(`O servidor não encontrou o produto! Código: "${codigoLimpo}"`, 'erro');
                    document.getElementById('bipador').value = '';
                }
            })
            .catch(error => window.mostrarAviso("Erro de conexão ao buscar o produto.", 'erro'));
    }
}

function renderListaCarga() {
    let html = '';
    itensEntrada.forEach(i => {
        html += `
        <tr>
            <td class="align-middle">${i.codigo}</td>
            <td class="text-start align-middle">${i.nome}</td>
            <td class="fw-bold text-success text-center align-middle" style="font-size: 1.2rem;">${i.qtd}</td>
            <td class="text-center align-middle">
                <button class="btn btn-sm btn-warning fw-bold shadow-sm me-1" onclick="editarQuantidadeCarga(${i.id}, '${i.nome.replace(/'/g, "\\'")}')" title="Editar Quantidade">✏️</button>
                <button class="btn btn-sm btn-danger fw-bold shadow-sm" onclick="removerItemCarga(${i.id}, '${i.nome.replace(/'/g, "\\'")}')" title="Excluir Produto">🗑️</button>
            </td>
        </tr>`;
    });
    document.getElementById('listaEntrada').innerHTML = html;
}

function editarQuantidadeCarga(idProduto, nomeProduto) {
    let item = itensEntrada.find(i => i.id === idProduto);
    if (item) {
        let novaQtd = prompt(`Digite a nova quantidade para:\n📦 ${nomeProduto}`, item.qtd);
        if (novaQtd !== null && novaQtd.trim() !== "") {
            let qtdConvertida = parseInt(novaQtd);
            if (qtdConvertida > 0) {
                item.qtd = qtdConvertida;
                renderListaCarga();
            } else {
                window.mostrarAviso("A quantidade deve ser maior que zero!", 'aviso');
            }
        }
    }
}


function removerItemCarga(idProduto, nomeProduto) {
    if (confirm(`Tem certeza que deseja remover "${nomeProduto}" da lista de entrada?`)) {
        itensEntrada = itensEntrada.filter(i => i.id !== idProduto);
        renderListaCarga();
    }
}

function prepararConferencia() {
    if(itensEntrada.length === 0) {
        window.mostrarAviso("Bipe algum produto antes de conferir!", 'aviso');
        return;
    }

    let html = '';
    let totalFisico = 0;

    itensEntrada.forEach(i => {
        html += `<tr><td>${i.codigo}</td><td class="text-start">${i.nome}</td><td class="fw-bold text-center">${i.qtd}</td></tr>`;
        totalFisico += i.qtd;
    });
    document.getElementById('listaConferencia').innerHTML = html;
    document.getElementById('totalItensBadge').innerText = totalFisico;

    let agora = new Date();
    document.getElementById('dataHoraAtual').innerText = agora.toLocaleString('pt-BR');

    var myModal = new bootstrap.Modal(document.getElementById('modalConferencia'));
    myModal.show();
}

function confirmarEfetivacao() {
    if(!window.CSRF_TOKEN) {
        window.mostrarAviso("Erro de segurança: Token CSRF não encontrado. Atualize a página e tente novamente.", 'erro');
        return;
    }

    let btn = document.getElementById('btnConfirmar');
    btn.disabled = true;
    btn.innerText = "⏳ Salvando...";

    let urlSeguraEfetivar = `/api/efetivar-entrada/?_nocache=${Date.now()}`;

    fetch(urlSeguraEfetivar, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
        body: JSON.stringify({itens: itensEntrada})
    })
    .then(res => res.json())
    .then(data => {
        if(data.status === 'sucesso') {
            window.mostrarAviso("Estoque atualizado com sucesso!", 'sucesso');

            itensEntrada = [];
            renderListaCarga();

            var modalEl = document.getElementById('modalConferencia');
            var modalObj = bootstrap.Modal.getInstance(modalEl);
            modalObj.hide();

            btn.disabled = false;
            btn.innerText = "✅ Confirmar Entrada no Estoque";
        } else {
            window.mostrarAviso("Erro ao salvar: " + data.mensagem, 'erro');
            btn.disabled = false;
            btn.innerText = "✅ Confirmar Entrada no Estoque";
        }
    })
    .catch(error => {
        window.mostrarAviso("Erro ao tentar salvar no banco de dados.", 'erro');
        btn.disabled = false;
        btn.innerText = "✅ Confirmar Entrada no Estoque";
    });
}
