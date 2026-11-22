// Dicionário Central de Diagnóstico e Solução Didática para todas as telas do TecVarejo
const DICIONARIO_SOLUCOES_TECVAREJO = [
    {
        padrao: /falta pagar|valor pago|pagamento.*insuficiente/i,
        solucao: "Escolha a forma de pagamento (Dinheiro, PIX, Crédito ou Débito) no painel direito, clique no botão '+' para lançar o valor e depois clique em VENDA."
    },
    {
        padrao: /carrinho vazio|nenhum produto|adicione pelo menos um item/i,
        solucao: "Bipe o código de barras ou pesquise o nome do produto na barra inferior antes de prosseguir."
    },
    {
        padrao: /parcela|parcelamento|valor mínimo/i,
        solucao: "O valor total da compra não atingiu o mínimo exigido para essa quantidade de parcelas (verifique as regras em Configurações > Taxas da Maquininha)."
    },
    {
        padrao: /selecione um cliente|cliente obrigatório|destinatário/i,
        solucao: "Selecione um cliente cadastrado na lista ou deixe como CONSUMIDOR PADRÃO para vendas simples no balcão."
    },
    {
        padrao: /estoque negativado|estoque negativo/i,
        solucao: "Não é permitido dar entrada de NFe em produto com saldo negativo. Abra /estoquepainel/acerto-estoque/, ajuste o saldo do produto para 0 (ou a quantidade física real) e depois finalize a nota."
    },
    {
        padrao: /estoque insuficiente|saldo negativo|sem estoque/i,
        solucao: "Confira o saldo físico na prateleira. Se houver divergência, faça um Acerto Rápido em /estoquepainel/acerto-estoque/."
    },
    {
        padrao: /mínimo.*2|duas opções|filtro.*snapshot/i,
        solucao: "No Inventário Rotativo, selecione pelo menos 2 filtros (ex: Marca + Família ou Marca + Unidade) antes de tirar o Snapshot."
    },
    {
        padrao: /vínculo|não vinculado|aguardando vínculo/i,
        solucao: "Associe o item ao produto interno do estoque (no Tintométrico use /cadastrar-vinculo/; na Entrada XML use a coluna Vínculo JB)."
    },
    {
        padrao: /cep|ibge|inscrição estadual|ie.*inválida|rejeição|sefaz/i,
        solucao: "Abra o cadastro do cliente em /clientes/, preencha o CEP para capturar o Código IBGE automaticamente e confira o Indicador de IE."
    },
    {
        padrao: /utilizador ou senha incorretos|usuário ou senha incorretos|senha incorreta/i,
        solucao: "Confira se o Caps Lock está desligado e digite seu login exatamente como cadastrado (ex: diegos.tec). Se esqueceu a senha, peça ao Gerente para redefinir em /gerencia/colaboradores/."
    },
    {
        padrao: /senha.*gerente|autorização|permissão|acesso negado/i,
        solucao: "Esta operação exige autorização presencial (Login e Senha) de um usuário com perfil Gerente ou Supervisor."
    },
    {
        padrao: /caixa fechado|nenhum caixa aberto/i,
        solucao: "Acesse /painelpdv/ e clique em 'Abrir Novo Caixa' ou 'Retomar PDV' antes de registrar vendas."
    }
];

function buscarSolucaoDidatica(mensagem) {
    const texto = String(mensagem || "");
    for (const item of DICIONARIO_SOLUCOES_TECVAREJO) {
        if (item.padrao.test(texto)) {
            return item.solucao;
        }
    }
    return null;
}

window.acionarAjudaIAErro = function (mensagemErro) {
    const btnAbrir = document.getElementById("btnFlutuanteSuporte");
    const janelaChat = document.getElementById("janelaChatSuporte");
    const inputPergunta = document.getElementById("inputPerguntaSuporte");
    const formChat = document.getElementById("formChatSuporte");

    if (!janelaChat || !inputPergunta || !formChat) return;

    if (janelaChat.classList.contains("d-none") && btnAbrir) {
        btnAbrir.click();
    }

    inputPergunta.value = `Deu este erro na tela: "${mensagemErro}". Como eu resolvo?`;
    formChat.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
};

window.mostrarAviso = function (mensagem, tipo = 'erro') {
    let container = document.getElementById('toast-container-sistema');
    if (!container) return;

    let bgClass = tipo === 'sucesso' ? 'bg-success' : (tipo === 'aviso' ? 'bg-warning' : 'bg-danger');
    let textClass = tipo === 'aviso' ? 'text-dark' : 'text-white';
    let icon = tipo === 'sucesso' ? '✅' : (tipo === 'aviso' ? '⚠️' : '❌');

    let solucaoDidatica = (tipo === 'erro' || tipo === 'aviso') ? buscarSolucaoDidatica(mensagem) : null;
    let tempoExibicao = (tipo === 'erro' || solucaoDidatica) ? 8500 : 5000;

    let toastEl = document.createElement('div');
    toastEl.className = `toast ${textClass} ${bgClass} border-0 shadow-lg mb-2`;
    toastEl.style.minWidth = "340px";
    toastEl.style.maxWidth = "460px";
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    const msgEscapada = String(mensagem).replace(/"/g, '&quot;');

    let blocoSolucaoHtml = solucaoDidatica
        ? `<div class="mt-2 pt-2 border-top border-light border-opacity-25 small fw-normal">
               <strong>💡 Como resolver:</strong> ${solucaoDidatica}
           </div>`
        : "";

    let botaoIAHtml = (tipo === 'erro' || tipo === 'aviso')
        ? `<div class="mt-2 text-end">
               <button type="button" class="btn btn-sm btn-light fw-bold py-0 px-2 shadow-sm btn-pedir-ajuda-ia" style="font-size: 0.78rem; color: #0D1B4C;">
                   ✨ Resolver com IA
               </button>
           </div>`
        : "";

    toastEl.innerHTML = `
        <div class="d-flex p-2">
            <div class="toast-body fw-bold" style="font-size: 0.92rem; line-height: 1.35; flex: 1;">
                <div>${icon} ${mensagem}</div>
                ${blocoSolucaoHtml}
                ${botaoIAHtml}
            </div>
            <button type="button" class="btn-close ${tipo === 'aviso' ? '' : 'btn-close-white'} ms-2 mt-1" data-bs-dismiss="toast"></button>
        </div>
    `;

    const btnAjuda = toastEl.querySelector(".btn-pedir-ajuda-ia");
    if (btnAjuda) {
        btnAjuda.addEventListener("click", function () {
            window.acionarAjudaIAErro(msgEscapada);
        });
    }

    container.appendChild(toastEl);
    let toast = new bootstrap.Toast(toastEl, { delay: tempoExibicao });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => { toastEl.remove(); });
};

window.verificarPermissao = function (event, urlDestino, perfisPermitidos, acaoDescricao = "acessar esta área") {
    if (!perfisPermitidos.includes(window.PERFIL_USUARIO)) {
        event.preventDefault();
        document.getElementById('acessoNegadoMensagem').innerText = `Seu perfil (${window.PERFIL_USUARIO}) não tem permissão para ${acaoDescricao}. O acesso é restrito aos cargos: ${perfisPermitidos.join(' ou ')}.`;
        new bootstrap.Modal(document.getElementById('modalAcessoNegado')).show();
        return false;
    }
    if (urlDestino) window.location.href = urlDestino;
    return true;
};

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('[data-perfis-permitidos]').forEach(el => {
        let perfis = el.getAttribute('data-perfis-permitidos').split(',');
        if (!perfis.includes(window.PERFIL_USUARIO)) {
            el.classList.add('disabled-link');
            el.onclick = function (e) {
                let desc = el.getAttribute('data-acao-desc') || "acessar esta área";
                verificarPermissao(e, null, perfis, desc);
            };
        }
    });

    // Padroniza mensagens do Django (ex: /ponto/ "Utilizador ou senha incorretos.") no Toast Didático Global
    document.querySelectorAll('.alert.alert-danger, .alert.alert-warning').forEach(alertaEl => {
        if (alertaEl.id === 'alerta-estoque-negativo-nfe') return;
        const textoAlerta = alertaEl.innerText.replace(/×/g, '').trim();
        if (textoAlerta && typeof window.mostrarAviso === 'function') {
            const tipo = alertaEl.classList.contains('alert-warning') ? 'aviso' : 'erro';
            alertaEl.style.display = 'none';
            window.mostrarAviso(textoAlerta, tipo);
        }
    });
});
