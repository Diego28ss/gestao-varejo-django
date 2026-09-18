// ==========================================
// 🚀 INICIALIZAÇÃO DE MODAIS (Garantindo carregamento)
// ==========================================
let objModalVisualizar = null;
let objModalAutorizacao = null;
let objModalConfirmacao = null;
let objModalAviso = null;

document.addEventListener("DOMContentLoaded", function() {
    if (typeof bootstrap !== 'undefined') {
        const elVisu = document.getElementById('modalVisualizar');
        if (elVisu) objModalVisualizar = new bootstrap.Modal(elVisu);
        
        const elAuth = document.getElementById('modalAutorizacao');
        if (elAuth) {
            objModalAutorizacao = new bootstrap.Modal(elAuth);
            elAuth.addEventListener('hidden.bs.modal', () => {
                const alerta = document.getElementById('alertaAutorizacao');
                if (alerta) alerta.classList.add('d-none');
            });
        }

        const elConf = document.getElementById('modalConfirmacaoSistema');
        if (elConf) objModalConfirmacao = new bootstrap.Modal(elConf);

        const elAviso = document.getElementById('modalAvisoSistema');
        if (elAviso) objModalAviso = new bootstrap.Modal(elAviso);
    } else {
        console.error("Erro: Bootstrap não carregado.");
    }
});

// ==========================================
// 💡 FUNÇÕES AUXILIARES DE AVISO E CONFIRMAÇÃO
// ==========================================
function mostrarErro(idElemento, mensagem) {
    const divErro = document.getElementById(idElemento);
    if (divErro) {
        divErro.innerText = mensagem;
        divErro.classList.remove('d-none');
    }
}

function mostrarAvisoSistema(mensagem) {
    if(objModalAviso) {
        document.getElementById('textoAvisoSistema').innerText = mensagem;
        objModalAviso.show();
    } else {
        alert(mensagem); // Fallback caso ocorra um erro extremo
    }
}

function mostrarConfirmacaoSistema(titulo, texto, classeBotao, textoBotao, callbackConfirmacao) {
    if(!objModalConfirmacao) return;

    document.getElementById('tituloConfirmacaoSistema').innerHTML = `<i class="bi bi-question-circle-fill me-2"></i>${titulo}`;
    document.getElementById('textoConfirmacaoSistema').innerHTML = texto;
    
    let btnConfirmar = document.getElementById('btnConfirmacaoSistemaAcao');
    btnConfirmar.className = `btn fw-bold px-4 shadow-sm ${classeBotao}`;
    if (classeBotao === 'btn-warning') btnConfirmar.classList.add('text-dark');
    btnConfirmar.innerText = textoBotao;
    
    // Clona o botão para limpar eventos de clique anteriores (evita duplicação de chamadas)
    let novoBtn = btnConfirmar.cloneNode(true);
    btnConfirmar.parentNode.replaceChild(novoBtn, btnConfirmar);
    
    novoBtn.addEventListener('click', function() {
        novoBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Aguarde...';
        novoBtn.disabled = true;
        callbackConfirmacao();
    });
    
    objModalConfirmacao.show();
}

// ==========================================
// 👁️ VISUALIZAR PEDIDO E HISTÓRICO
// ==========================================
function abrirModalVisualizar(id, observacoes = '') {
    if (!objModalVisualizar) {
        console.error("Modal de visualização não inicializado!");
        return;
    }

    document.getElementById('txtVisuId').innerText = id;
    document.getElementById('tabelaVisualizar').innerHTML = '<tr><td colspan="4" class="py-4"><span class="spinner-border text-primary"></span> Carregando itens...</td></tr>';
    document.getElementById('txtVisuTotal').innerText = 'R$ 0,00';
    
    let areaObs = document.getElementById('areaObsVisualizar');
    
    if (observacoes && String(observacoes).trim() !== '' && String(observacoes).trim() !== 'None') {
        let historicoFormatado = String(observacoes).replace(/\n/g, '<br><i class="bi bi-arrow-right-short fw-bold fs-6"></i> ');
        areaObs.innerHTML = `<i class="bi bi-clock-history me-1"></i> <strong class="text-uppercase">Histórico de Ações:</strong><br>
                             <i class="bi bi-arrow-right-short fw-bold fs-6"></i> ${historicoFormatado}`;
        areaObs.className = 'alert alert-warning m-3 small text-dark border-warning shadow-sm';
        areaObs.classList.remove('d-none');
    } else {
        areaObs.classList.add('d-none');
    }

    objModalVisualizar.show();

    fetch(`/api/pdv/importar-pedido/${id}/`)
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') {
            let html = '';
            let totalPedido = 0;
            
            data.pedido.carrinho.forEach(item => {
                let precoFinal = item.preco_desconto !== undefined ? item.preco_desconto : (item.preco || 0);
                let totalLinha = precoFinal * item.qtd;
                totalPedido += totalLinha;
                let nomeExibicao = item.nome_customizado ? item.nome_customizado : item.nome;
                
                html += `<tr>
                    <td class="text-start fw-bold text-primary small ps-3">${nomeExibicao}</td>
                    <td class="fw-bold">${item.qtd}</td>
                    <td class="text-muted">R$ ${precoFinal.toFixed(2).replace('.', ',')}</td>
                    <td class="fw-bold text-success">R$ ${totalLinha.toFixed(2).replace('.', ',')}</td>
                </tr>`;
            });
            
            if(data.pedido.carrinho.length === 0) html = '<tr><td colspan="4" class="py-3 text-muted">Nenhum item salvo.</td></tr>';
            
            document.getElementById('tabelaVisualizar').innerHTML = html;
            document.getElementById('txtVisuTotal').innerText = `R$ ${totalPedido.toFixed(2).replace('.', ',')}`;
        }
    })
    .catch(err => console.error("Erro ao buscar detalhes:", err));
}

// ==========================================
// ✏️ AÇÕES DIRETAS (ABERTO E ORÇAMENTO)
// ==========================================
function confirmarExclusaoAberto(id) {
    mostrarConfirmacaoSistema(
        "Apagar Rascunho",
        `Tem a certeza que deseja APAGAR DEFINITIVAMENTE o pedido em rascunho #${id}?`,
        "btn-danger",
        "Sim, Apagar Definitivamente",
        function() {
            fetch(`/api/pedidos/cancelar/${id}/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ motivo: 'Apagado no Rascunho', login: '', senha: '' })
            })
            .then(r => r.json())
            .then(d => { window.location.reload(); });
        }
    );
}

function confirmarEdicaoSimples(id) {
    mostrarConfirmacaoSistema(
        "Editar Pedido",
        `Deseja abrir o Pedido #${id} para edição?`,
        "btn-warning",
        "Sim, Editar Pedido",
        function() {
            window.location.href = `/novopedido/${id}/`;
        }
    );
}

// ==========================================
// 🔐 SISTEMA DE AUTORIZAÇÃO (CANCELAR/REABRIR OFICIAL)
// ==========================================
function abrirModalAutorizacao(id, acao) {
    if (!objModalAutorizacao) {
        mostrarAvisoSistema("Erro ao carregar o sistema de autorização. Recarregue a página.");
        return; 
    }
    
    document.getElementById('authPedidoId').value = id;
    document.getElementById('authAcao').value = acao;
    document.getElementById('authLogin').value = '';
    document.getElementById('authSenha').value = '';
    document.getElementById('authMotivo').value = '';
    document.getElementById('alertaAutorizacao').classList.add('d-none');
    
    let texto = document.getElementById('authTextoDescritivo');
    let btn = document.getElementById('btnConfirmaAutorizacao');
    
    if (acao === 'CANCELAR') {
        texto.innerHTML = `O pedido <strong>#${id}</strong> será cancelado, as comissões e estoques serão estornados automaticamente.`;
        btn.className = 'btn btn-danger fw-bold shadow-sm';
        btn.innerText = 'Confirmar Cancelamento';
    } else if (acao === 'REABRIR') {
        texto.innerHTML = `O pedido <strong>#${id}</strong> será reaberto para edição. Estoque e comissões da venda finalizada serão removidos temporariamente.`;
        btn.className = 'btn btn-warning text-dark fw-bold shadow-sm';
        btn.innerText = 'Reabrir Pedido';
    }
    
    objModalAutorizacao.show();
}

function processarAutorizacao() {
    let id = document.getElementById('authPedidoId').value;
    let acao = document.getElementById('authAcao').value;
    let login = document.getElementById('authLogin').value;
    let senha = document.getElementById('authSenha').value;
    let motivo = document.getElementById('authMotivo').value;
    
    if(!login || !senha || !motivo) {
        mostrarErro('alertaAutorizacao', 'Por favor, preencha Login, Senha e Motivo!');
        return;
    }

    let endpoint = acao === 'CANCELAR' ? `/api/pedidos/cancelar/${id}/` : `/api/pedidos/reabrir/${id}/`;
    let btn = document.getElementById('btnConfirmaAutorizacao');
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processando...';
    btn.disabled = true;

    fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motivo: motivo, login: login, senha: senha })
    })
    .then(response => response.json())
    .then(data => {
        if(data.status === 'sucesso' || data.status === 'apagado') {
            if(data.url_redirecionamento) {
                window.location.href = data.url_redirecionamento;
            } else {
                window.location.reload();
            }
        } else {
            mostrarErro('alertaAutorizacao', data.mensagem || 'Acesso negado.');
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    })
    .catch(error => {
        mostrarErro('alertaAutorizacao', 'Falha de comunicação com o servidor.');
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}
