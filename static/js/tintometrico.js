// ==========================================
// 🎨 MÓDULO TINTOMÉTRICO INDUSTRIAL
// Gestão de busca de cores, bases e envio para o PDV
// ==========================================

// 🚀 AQUI ESTÁ A CHAVE: Dizemos para a Busca Universal usar a rota especializada em Bases!
window.URL_BUSCA_CUSTOMIZADA = '/api/pesquisar-base-alternativa/?q=';

// Variáveis Globais de Operação
let produtoRealCodInterno = 'TINTOMETRICO';
let produtoRealCodBarras = 'TINTOMETRICO';
let produtoRealEstoque = 0;
let produtoRealPrecoFinal = 0;
let produtoRealNcm = '';
let produtoRealCsosn = '';
let produtoTamanhoFinal = '';
let baseAtualNomeExibicao = '';
let modalTrocaBase;
let timerBuscaCor;
let currentOffset = 0;
let currentQuery = '';

document.addEventListener("DOMContentLoaded", function () {
    if (window.self !== window.top) {
        let menuNavegacao = document.querySelector('nav');
        if (menuNavegacao) {
            menuNavegacao.style.display = 'none';
        }
        document.body.style.paddingTop = '0';
        document.body.style.marginTop = '0';
    }

    let elTrocaBase = document.getElementById('modalTrocaBase');
    if (elTrocaBase) modalTrocaBase = new bootstrap.Modal(elTrocaBase);

    if (window.TINTOMETRICO_CONFIG && window.TINTOMETRICO_CONFIG.sucesso) {
        baseAtualNomeExibicao = window.TINTOMETRICO_CONFIG.nomeBase;
        let embalagemSelect = document.getElementById('selectEmbalagem');
        let tamanhoBase = "";

        let idEmbalagemUrl = new URLSearchParams(window.location.search).get('embalagem');
        if (idEmbalagemUrl) {
            let optionCorreta = Array.from(embalagemSelect.options).find(opt => opt.value === idEmbalagemUrl);
            if (optionCorreta) tamanhoBase = optionCorreta.text.trim();
        }
        if (!tamanhoBase || tamanhoBase.includes("--")) {
            tamanhoBase = embalagemSelect.options[embalagemSelect.selectedIndex].text.trim();
        }

        produtoTamanhoFinal = tamanhoBase;

        fetch(`/api/buscar-detalhes-base/?base=${encodeURIComponent(baseAtualNomeExibicao)}&tamanho=${encodeURIComponent(tamanhoBase)}`)
            .then(response => response.json())
            .then(data => aplicarDadosBaseNaTela(data))
            .catch(error => console.error("Erro na ligação com a API:", error));
    }
});

// ==========================================
// 🔌 CONEXÃO COM A BUSCA UNIVERSAL (VINCULAÇÃO RÁPIDA)
// ==========================================
function abrirModalTrocaBase() {
    if (typeof BuscaUniversal !== 'undefined') BuscaUniversal.limpar(true);
    modalTrocaBase.show();
    setTimeout(() => {
        let inp = document.getElementById('inputBuscaUniversal');
        if (inp) inp.focus();
    }, 500);
}

// 🚀 AQUI O COMPORTAMENTO MUDA: Agora ele vincula a base permanentemente ao clicar no modal!
window.aoSelecionarProdutoBusca = function (botao) {
    let codInterno = botao.getAttribute('data-cod-interno');

    if (typeof BuscaUniversal !== 'undefined') BuscaUniversal.limpar(true);
    if (modalTrocaBase) modalTrocaBase.hide();

    let displayNome = document.getElementById('nomeBaseDisplay');
    if (displayNome) {
        displayNome.innerText = "⏳ VINCULANDO BASE...";
        displayNome.className = "fw-bold fs-6 text-warning";
    }

    let btnPdv = document.getElementById('btnEnviarPdv');
    btnPdv.disabled = true;
    btnPdv.className = "btn btn-secondary w-100 fw-bold shadow-sm p-3 fs-5";
    document.getElementById('textoBtnPdv').innerText = "Atualizando o banco de dados...";

    // Efetiva a vinculação no banco Tintométrico!
    fetch(`/api/vincular-base/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nome_base: baseAtualNomeExibicao,
            tamanho: produtoTamanhoFinal, // 🚀 CORREÇÃO: Envia a string "3.60 L"
            cod_interno: codInterno
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'sucesso') {
                if (typeof window.mostrarAviso === 'function') {
                    window.mostrarAviso("Base vinculada com sucesso! Recarregando dados...", "sucesso");
                }
                // Como a vinculação deu certo, recarregamos a página para ele refazer o cálculo financeiro perfeitamente
                setTimeout(() => { window.location.reload(); }, 1500);
            } else {
                if (typeof window.mostrarAviso === 'function') window.mostrarAviso(data.mensagem, "erro");
                document.getElementById('nomeBaseDisplay').innerText = baseAtualNomeExibicao + " ❌ FALHA";
                document.getElementById('nomeBaseDisplay').className = "fw-bold fs-6 text-danger";
            }
        })
        .catch(error => {
            console.error("Erro na vinculação:", error);
            if (typeof window.mostrarAviso === 'function') window.mostrarAviso("Falha ao vincular produto.", "erro");
        });
};


function desvincularBaseAtual() {
    if (!confirm(`Deseja desvincular o produto Int: ${produtoRealCodInterno} desta base? Você precisará pesquisar e vincular outro produto para usar esta fórmula.`)) return;

    let btnPdv = document.getElementById('btnEnviarPdv');
    btnPdv.disabled = true;
    btnPdv.className = "btn btn-secondary w-100 fw-bold shadow-sm p-3 fs-5";
    document.getElementById('textoBtnPdv').innerText = "Desvinculando...";

    fetch(`/api/desvincular-base/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nome_base: baseAtualNomeExibicao,
            tamanho: produtoTamanhoFinal // 🚀 CORREÇÃO: Envia a string "3.60 L"
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'sucesso') {
                window.location.reload();
            } else {
                if (typeof window.mostrarAviso === 'function') window.mostrarAviso(data.mensagem, "erro");
            }
        })
        .catch(error => {
            console.error("Erro na desvinculação:", error);
        });
}



// ==========================================
// ⚙️ MATEMÁTICA E RENDERIZAÇÃO
// ==========================================
function aplicarDadosBaseNaTela(data) {
    let btnPdv = document.getElementById('btnEnviarPdv');

    function gerirVisualizacaoCusto(idElementoValor, idContainer, prefixo = "R$ ") {
        let container = document.getElementById(idContainer);
        let elValor = document.getElementById(idElementoValor);

        if (!container || !elValor) return;

        let valorReal = elValor.innerText.replace(prefixo, '').trim();
        if (valorReal && valorReal !== '***') {
            elValor.dataset.valorReal = valorReal;
        }

        let btnOlho = container.querySelector('.btn-toggle-custo');
        if (!btnOlho) {
            btnOlho = document.createElement('i');
            btnOlho.className = 'bi bi-eye-slash-fill ms-2 text-muted btn-toggle-custo';
            btnOlho.style.cursor = 'pointer';
            btnOlho.title = 'Mostrar/Ocultar Custo';

            btnOlho.onclick = function () {
                if (elValor.innerText === '***') {
                    elValor.innerText = prefixo + elValor.dataset.valorReal;
                    btnOlho.className = 'bi bi-eye-fill ms-2 text-primary btn-toggle-custo';
                } else {
                    elValor.innerText = '***';
                    btnOlho.className = 'bi bi-eye-slash-fill ms-2 text-muted btn-toggle-custo';
                }
            };
            container.appendChild(btnOlho);
        }

        if (elValor.dataset.valorReal) {
            elValor.innerText = '***';
            btnOlho.className = 'bi bi-eye-slash-fill ms-2 text-muted btn-toggle-custo';
        }
    }

    // 🚀 SUCESSO = BASE ESTÁ VINCULADA
    if (data.status === 'sucesso') {
        // Mostra o botão vermelho de desvincular!
        document.getElementById('codInternoDisplay').innerHTML = `
            <button class="btn btn-sm btn-outline-danger fw-bold" onclick="desvincularBaseAtual()" title="Desvincular Base Atual">
                <i class="bi bi-x-circle-fill"></i> ${data.dados.cod_interno}
            </button>
        `;
        document.getElementById('codBarrasDisplay').innerText = data.dados.cod_barras;

        let qtdEstoque = data.dados.estoque_atual;
        let classeEstoque = qtdEstoque > 0 ? "fw-bold text-success" : "fw-bold text-danger";
        document.getElementById('estoqueDisplay').innerHTML = `<i class="bi bi-box-seam"></i> ${qtdEstoque} ${data.dados.unidade}`;
        document.getElementById('estoqueDisplay').className = classeEstoque;

        let precoCustoBaseBanco = parseFloat(data.dados.preco_custo) || 0;
        let precoVendaBaseBanco = parseFloat(data.dados.preco_venda) || 0;

        document.getElementById('custoBaseDisplay').innerText = "R$ " + precoCustoBaseBanco.toFixed(2).replace('.', ',');
        document.getElementById('vendaBaseDisplay').innerText = "R$ " + precoVendaBaseBanco.toFixed(2).replace('.', ',');

        let vendaCorantes = window.TINTOMETRICO_CONFIG ? parseFloat(window.TINTOMETRICO_CONFIG.vendaCorantes) : 0;
        let custoCorantes = window.TINTOMETRICO_CONFIG ? parseFloat(window.TINTOMETRICO_CONFIG.custoCorantes) : 0;

        document.getElementById('vendaCorantesDisplay').innerText = "R$ " + vendaCorantes.toFixed(2).replace('.', ',');

        produtoRealPrecoFinal = precoVendaBaseBanco + vendaCorantes;
        let custoTotal = precoCustoBaseBanco + custoCorantes;
        let lucroReais = produtoRealPrecoFinal - custoTotal;

        let margemLucro = produtoRealPrecoFinal > 0 ? (lucroReais / produtoRealPrecoFinal) * 100 : 0;

        document.getElementById('precoTotalFinalDisplay').innerText = "R$ " + produtoRealPrecoFinal.toFixed(2).replace('.', ',');

        let elCustoTotal = document.getElementById('custoTotalDisplay');
        if (elCustoTotal) elCustoTotal.innerText = "R$ " + custoTotal.toFixed(2).replace('.', ',');

        let elLucro = document.getElementById('lucroDisplay');
        if (elLucro) {
            elLucro.innerText = "R$ " + lucroReais.toFixed(2).replace('.', ',') + " (" + margemLucro.toFixed(1).replace('.', ',') + "%)";
            if (lucroReais < 0) {
                elLucro.className = "fw-bold text-danger fs-5";
            } else {
                elLucro.className = "fw-bold text-success fs-5";
            }
        }

        let paiCustoBase = document.getElementById('custoBaseDisplay') ? document.getElementById('custoBaseDisplay').parentNode : null;
        if (paiCustoBase) {
            if (!paiCustoBase.id) paiCustoBase.id = 'containerCustoBase';
            gerirVisualizacaoCusto('custoBaseDisplay', paiCustoBase.id);
        }

        let paiCustoTotal = document.getElementById('custoTotalDisplay') ? document.getElementById('custoTotalDisplay').parentNode : null;
        if (paiCustoTotal) {
            if (!paiCustoTotal.id) paiCustoTotal.id = 'containerCustoTotal';
            gerirVisualizacaoCusto('custoTotalDisplay', paiCustoTotal.id);
        }

        let paiLucro = document.getElementById('lucroDisplay') ? document.getElementById('lucroDisplay').parentNode : null;
        if (paiLucro) {
            if (!paiLucro.id) paiLucro.id = 'containerLucro';
            gerirVisualizacaoCusto('lucroDisplay', paiLucro.id);
        }

        produtoRealCodInterno = data.dados.cod_interno;
        produtoRealCodBarras = data.dados.cod_barras;
        produtoRealEstoque = data.dados.estoque_atual;
        produtoRealNcm = data.dados.ncm || '';
        produtoRealCsosn = data.dados.csosn || '';

        btnPdv.disabled = false;
        btnPdv.className = "btn btn-success w-100 fw-bold shadow-sm p-3 fs-5";
        document.getElementById('textoBtnPdv').innerText = "Enviar para o PDV";

    } else {
        // 🚀 ERRO = BASE NÃO VINCULADA: Exibe o botão de VINCULAR!

        document.getElementById('codInternoDisplay').innerHTML = `
            <button class="btn btn-sm text-white fw-bold shadow-sm" style="background-color: var(--varejo-primary);" onclick="abrirModalTrocaBase()">
                <i class="bi bi-link"></i> VINCULAR BASE DO ESTOQUE
            </button>
        `;
        document.getElementById('codBarrasDisplay').innerText = "SEM VÍNCULO";
        document.getElementById('codBarrasDisplay').className = "fw-bold text-danger";

        document.getElementById('estoqueDisplay').innerText = "Bloqueado";
        document.getElementById('estoqueDisplay').className = "fw-bold text-danger";

        document.getElementById('custoBaseDisplay').innerText = "---";
        document.getElementById('vendaBaseDisplay').innerText = "---";

        let elCustoTotal = document.getElementById('custoTotalDisplay');
        if (elCustoTotal) elCustoTotal.innerText = "R$ 0,00";
        let elLucro = document.getElementById('lucroDisplay');
        if (elLucro) elLucro.innerText = "R$ 0,00 (0,0%)";

        document.getElementById('precoTotalFinalDisplay').innerText = "R$ 0,00";

        btnPdv.disabled = true;
        btnPdv.className = "btn btn-danger w-100 fw-bold shadow-sm p-3 fs-5";
        document.getElementById('textoBtnPdv').innerText = "Falta Vincular a Base!";

        if (typeof window.mostrarAviso === 'function') {
            window.mostrarAviso("Este tamanho de base ainda não está vinculado ao estoque! Clique em 'Vincular Base' para associá-lo.", "aviso");
        }
    }
}

// ==========================================
// 🔍 BUSCA DE FÓRMULAS DE CORES 
// ==========================================
function buscarCoresAoDigitar(texto) {
    let divResultados = document.getElementById('resultadosBuscaCor');
    clearTimeout(timerBuscaCor);
    if (texto.length < 2) {
        divResultados.style.display = 'none';
        return;
    }
    currentQuery = texto;
    currentOffset = 0;
    timerBuscaCor = setTimeout(() => { carregarResultadosCores(false); }, 300);
}

function carregarResultadosCores(isAppend = false) {
    let divResultados = document.getElementById('resultadosBuscaCor');
    fetch(`/api/buscar-cores/?q=${encodeURIComponent(currentQuery)}&offset=${currentOffset}`)
        .then(res => res.json())
        .then(data => {
            let btnAntigo = document.getElementById('btnCarregarMais');
            if (btnAntigo) btnAntigo.remove();

            if (!isAppend && data.cores.length === 0) {
                divResultados.innerHTML = '<div class="list-group-item text-muted small">Cor não encontrada</div>';
                divResultados.style.display = 'block';
                return;
            }

            let html = '';
            data.cores.forEach((c) => {
                let combinacoesJSON = JSON.stringify(c.combinacoes_validas).replace(/"/g, '&quot;');
                html += `<button type="button" class="list-group-item list-group-item-action py-2" onclick="selecionarCor('${c.nome}', '${combinacoesJSON}')">
                            <strong>${c.nome}</strong> <small class="text-muted">(${c.codigo})</small>
                         </button>`;
            });

            if (data.has_more) {
                html += `<button type="button" id="btnCarregarMais" class="list-group-item list-group-item-action text-center fw-bold py-2 shadow-sm" style="background-color: #e9ecef; color: #444;" onclick="carregarMaisCores(event)">
                            <i class="bi bi-arrow-down-circle"></i> Carregar mais resultados...
                         </button>`;
            }

            if (isAppend) {
                divResultados.innerHTML += html;
            } else {
                divResultados.innerHTML = html;
                divResultados.style.display = 'block';
            }
        });
}

function carregarMaisCores(event) {
    if (event) event.stopPropagation();
    let btnCarregarMais = document.getElementById('btnCarregarMais');
    if (btnCarregarMais) {
        btnCarregarMais.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> A carregar...';
        btnCarregarMais.disabled = true;
    }
    currentOffset += 25;
    carregarResultadosCores(true);
}

function selecionarCor(nome, combinacoesJSON) {
    document.getElementById('inputBuscaCor').value = nome;
    document.getElementById('resultadosBuscaCor').style.display = 'none';

    let combinacoes = JSON.parse(combinacoesJSON);
    let selectLinha = document.querySelector('select[name="linha"]');
    let linhasValidas = new Set(combinacoes.map(c => c.linha));

    Array.from(selectLinha.options).forEach(opt => {
        if (opt.value !== "") {
            if (!linhasValidas.has(opt.value)) {
                opt.disabled = true;
                opt.text = opt.text.replace(' ❌', '') + ' ❌';
                opt.style.color = '#ccc';
            } else {
                opt.disabled = false;
                opt.text = opt.text.replace(' ❌', '');
                opt.style.color = '#000';
            }
        }
    });

    if (selectLinha.options[selectLinha.selectedIndex]?.disabled) {
        selectLinha.value = "";
    }
}

document.addEventListener('click', function (event) {
    let inputBuscaCor = document.getElementById('inputBuscaCor');
    let resultadosBuscaCor = document.getElementById('resultadosBuscaCor');
    if (inputBuscaCor && resultadosBuscaCor && !inputBuscaCor.contains(event.target)) {
        resultadosBuscaCor.style.display = 'none';
    }
});

// ==========================================
// 🛒 LÓGICA DE TRANSFERÊNCIA PARA O PDV
// ==========================================
function enviarParaPDV() {
    let config = window.TINTOMETRICO_CONFIG;
    if (!config) return;

    let nomeCor = config.corEncontrada;
    let codigoTecnico = config.codigoTecnico;

    let selectLinha = document.querySelector('select[name="linha"]');
    let nomeLinha = "";
    if (selectLinha.selectedIndex > 0) {
        nomeLinha = selectLinha.options[selectLinha.selectedIndex].text.replace(' ❌', '').trim();
    }

    let nomeProdutoFinal = `${baseAtualNomeExibicao} - ${nomeCor} (Cód: ${codigoTecnico})`;

    let idVirtualUnico = "TINTA-" + new Date().getTime();

    let produtoTintometrico = {
        id: idVirtualUnico,
        id_real_estoque: produtoRealCodInterno,
        nome: nomeProdutoFinal,
        preco_venda: produtoRealPrecoFinal,
        preco: produtoRealPrecoFinal,
        preco_desconto: produtoRealPrecoFinal,
        qtd: 1,
        estoque_atual: produtoRealEstoque,
        cod_barras: produtoRealCodBarras,
        ncm: produtoRealNcm,
        csosn: produtoRealCsosn
    };

    let carrinho = JSON.parse(localStorage.getItem('carrinho')) || [];
    carrinho.push(produtoTintometrico);
    localStorage.setItem('carrinho', JSON.stringify(carrinho));

    if (window.parent && window.parent !== window) {
        if (typeof window.parent.receberTintaDoIframe === 'function') {
            window.parent.receberTintaDoIframe();
        } else {
            window.parent.location.reload();
        }
    } else {
        window.location.href = config.urlPdv;
    }
}

function toggleCustoStatic(icone, idElemento, prefixo) {
    let el = document.getElementById(idElemento);
    if (el.innerText === '***') {
        el.innerText = prefixo + el.dataset.valorReal;
        icone.className = 'bi bi-eye-fill ms-2 text-primary';
    } else {
        el.innerText = '***';
        icone.className = 'bi bi-eye-slash-fill ms-2 text-muted';
    }
}
