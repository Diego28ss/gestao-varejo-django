// ==========================================
// 🎨 MÓDULO TINTOMÉTRICO INDUSTRIAL
// Gestão de busca de cores, bases e envio para o PDV
// ==========================================

// Variáveis Globais de Operação
let produtoRealCodInterno = 'TINTOMETRICO';
let produtoRealCodBarras = 'TINTOMETRICO';
let produtoRealEstoque = 0;
let produtoRealPrecoFinal = 0;
let produtoTamanhoFinal = ''; 
let baseAtualNomeExibicao = ''; 
let modalTrocaBase;
let timerBuscaNovaBase;
let timerBuscaCor;
let currentOffset = 0; 
let currentQuery = ''; 

document.addEventListener("DOMContentLoaded", function() {
    let elTrocaBase = document.getElementById('modalTrocaBase');
    if(elTrocaBase) modalTrocaBase = new bootstrap.Modal(elTrocaBase);
    
    // 🛡️ Lógica de Inicialização Segura: Lê as variáveis passadas pelo Django na tela
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

        // Chamada inicial para buscar a base padrão da receita no estoque
        fetch(`/api/buscar-detalhes-base/?base=${encodeURIComponent(baseAtualNomeExibicao)}&tamanho=${encodeURIComponent(tamanhoBase)}`)
            .then(response => response.json())
            .then(data => aplicarDadosBaseNaTela(data))
            .catch(error => console.error("Erro na ligação com a API:", error));
    }
});

function aplicarDadosBaseNaTela(data) {
    let btnPdv = document.getElementById('btnEnviarPdv');
    
    if(data.status === 'sucesso') {
        document.getElementById('codInternoDisplay').innerText = data.dados.cod_interno;
        document.getElementById('codInternoDisplay').className = "badge bg-success";
        document.getElementById('codBarrasDisplay').innerText = data.dados.cod_barras;
        
        let qtdEstoque = data.dados.estoque_atual;
        let classeEstoque = qtdEstoque > 0 ? "fw-bold text-success" : "fw-bold text-danger";
        document.getElementById('estoqueDisplay').innerHTML = `<i class="bi bi-box-seam"></i> ${qtdEstoque} ${data.dados.unidade}`;
        document.getElementById('estoqueDisplay').className = classeEstoque;

        let precoCustoBaseBanco = data.dados.preco_custo;
        let precoVendaBaseBanco = data.dados.preco_venda;
        
        document.getElementById('custoBaseDisplay').innerText = "R$ " + precoCustoBaseBanco.toFixed(2).replace('.', ',');
        document.getElementById('vendaBaseDisplay').innerText = "R$ " + precoVendaBaseBanco.toFixed(2).replace('.', ',');

        // Puxa o custo dos corantes da variável global injetada
        let vendaCorantes = window.TINTOMETRICO_CONFIG ? window.TINTOMETRICO_CONFIG.vendaCorantes : 0;
        document.getElementById('vendaCorantesDisplay').innerText = "R$ " + vendaCorantes.toFixed(2).replace('.', ',');

        produtoRealPrecoFinal = precoVendaBaseBanco + vendaCorantes;
        document.getElementById('precoTotalFinalDisplay').innerText = "R$ " + produtoRealPrecoFinal.toFixed(2).replace('.', ',');

        produtoRealCodInterno = data.dados.cod_interno;
        produtoRealCodBarras = data.dados.cod_barras;
        produtoRealEstoque = data.dados.estoque_atual;
        
        if (data.dados.nome_substituto) {
            baseAtualNomeExibicao = data.dados.nome_substituto;
            document.getElementById('nomeBaseDisplay').innerText = baseAtualNomeExibicao + " (SUBSTITUÍDA)";
            document.getElementById('nomeBaseDisplay').classList.replace("text-danger", "text-primary");
        }

        btnPdv.disabled = false;
        btnPdv.className = "btn btn-success w-100 fw-bold shadow-sm p-3 fs-5";
        document.getElementById('textoBtnPdv').innerText = "Enviar para o PDV";

    } else {
        document.getElementById('codInternoDisplay').innerText = "NÃO VINCULADO";
        document.getElementById('codInternoDisplay').className = "badge bg-danger";
        document.getElementById('codBarrasDisplay').innerText = "Vá em Estoque > Editar > Vincular Base";
        document.getElementById('estoqueDisplay').innerText = "Bloqueado";
        document.getElementById('estoqueDisplay').className = "fw-bold text-danger";
        
        document.getElementById('custoBaseDisplay').innerText = "---";
        document.getElementById('vendaBaseDisplay').innerText = "---";
        document.getElementById('precoTotalFinalDisplay').innerText = "R$ 0,00";

        btnPdv.disabled = true;
        btnPdv.className = "btn btn-danger w-100 fw-bold shadow-sm p-3 fs-5";
        document.getElementById('textoBtnPdv').innerText = "Produto Não Vinculado no Estoque!";
    }
}

// ==========================================
// 🔍 SISTEMA DE BUSCA DE CORES E BASES (AUTOCOMPLETE)
// ==========================================
function abrirModalTrocaBase() {
    document.getElementById('inputPesquisaNovaBase').value = "";
    document.getElementById('listaNovasBases').innerHTML = '<div class="list-group-item text-center text-muted py-4">Digite para pesquisar um produto no estoque principal...</div>';
    modalTrocaBase.show();
    setTimeout(() => document.getElementById('inputPesquisaNovaBase').focus(), 500);
}

function pesquisarNovaBase(texto) {
    clearTimeout(timerBuscaNovaBase);
    let divResultados = document.getElementById('listaNovasBases');
    
    if (texto.length < 3) {
        divResultados.innerHTML = '<div class="list-group-item text-center text-muted py-4">Digite pelo menos 3 caracteres...</div>';
        return;
    }

    timerBuscaNovaBase = setTimeout(() => {
        divResultados.innerHTML = '<div class="list-group-item text-center py-4"><span class="spinner-border text-primary" role="status"></span> Buscando...</div>';
        
        fetch(`/api/pesquisar-base-alternativa/?q=${encodeURIComponent(texto)}`)
            .then(res => res.json())
            .then(data => {
                if (data.produtos.length === 0) {
                    divResultados.innerHTML = '<div class="list-group-item text-center text-danger fw-bold py-4">Nenhum produto encontrado.</div>';
                    return;
                }

                let html = '';
                data.produtos.forEach(p => {
                    html += `
                        <button type="button" class="list-group-item list-group-item-action py-3" onclick="confirmarTrocaBase('${p.cod_interno}')">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong style="color: #101820; font-size: 1.1rem;">${p.nome}</strong><br>
                                    <small class="text-muted">Cód: ${p.cod_barras} | Int: ${p.cod_interno}</small>
                                </div>
                                <div class="text-end">
                                    <span class="badge ${p.estoque > 0 ? 'bg-success' : 'bg-danger'} fs-6">${p.estoque} UN</span><br>
                                    <strong class="text-success">R$ ${p.preco_venda.toFixed(2).replace('.', ',')}</strong>
                                </div>
                            </div>
                        </button>
                    `;
                });
                divResultados.innerHTML = html;
            }).catch(err => {
                divResultados.innerHTML = '<div class="list-group-item text-center text-danger py-4">Erro ao buscar produtos.</div>';
            });
    }, 400);
}

function confirmarTrocaBase(codigoInterno) {
    modalTrocaBase.hide();
    fetch(`/api/buscar-detalhes-base/?cod_interno=${codigoInterno}`)
        .then(response => response.json())
        .then(data => aplicarDadosBaseNaTela(data))
        .catch(error => console.error("Erro na troca de base:", error));
}

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
    if(event) event.stopPropagation();
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
        if(opt.value !== "") {
            if(!linhasValidas.has(opt.value)) {
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
    
    if(selectLinha.options[selectLinha.selectedIndex]?.disabled) {
        selectLinha.value = "";
    }
}

document.addEventListener('click', function(event) {
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
    if(!config) return;

    let nomeCor = config.corEncontrada;
    let codigoTecnico = config.codigoTecnico;

    let selectLinha = document.querySelector('select[name="linha"]');
    let nomeLinha = "";
    if(selectLinha.selectedIndex > 0) {
        nomeLinha = selectLinha.options[selectLinha.selectedIndex].text.replace(' ❌', '').trim();
    }

    let nomeProdutoFinal = `${baseAtualNomeExibicao} - ${nomeLinha} ${nomeCor} ${produtoTamanhoFinal} (Cód: ${codigoTecnico})`;

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
        cod_barras: produtoRealCodBarras
    };

    let carrinho = JSON.parse(localStorage.getItem('carrinho')) || [];
    carrinho.push(produtoTintometrico);
    localStorage.setItem('carrinho', JSON.stringify(carrinho));

    // Redireciona para o ecrã do PDV
    if (window.parent && window.parent !== window) {
        window.parent.location.reload();
    } else {
        window.location.href = config.urlPdv;
    }
}
