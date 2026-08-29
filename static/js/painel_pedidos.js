let pedidoSelecionadoId = null;
let objModalReabrir = null;
let objModalCancelar = null;
let objModalVisualizar = null;
let objModalEstornar = null;

document.addEventListener("DOMContentLoaded", function() {
    objModalReabrir = new bootstrap.Modal(document.getElementById('modalReabrir'));
    objModalCancelar = new bootstrap.Modal(document.getElementById('modalCancelar'));
    objModalVisualizar = new bootstrap.Modal(document.getElementById('modalVisualizar'));
    objModalEstornar = new bootstrap.Modal(document.getElementById('modalEstornar'));
    
    // Limpa os erros ao fechar os modais
    document.getElementById('modalReabrir').addEventListener('hidden.bs.modal', () => document.getElementById('alertaReabrir').classList.add('d-none'));
    document.getElementById('modalCancelar').addEventListener('hidden.bs.modal', () => document.getElementById('alertaCancelar').classList.add('d-none'));
    document.getElementById('modalEstornar').addEventListener('hidden.bs.modal', () => document.getElementById('alertaEstornar').classList.add('d-none'));
});

function mostrarErro(idElemento, mensagem) {
    const divErro = document.getElementById(idElemento);
    divErro.innerText = mensagem;
    divErro.classList.remove('d-none');
}

// ==========================================
// 👁️ VISUALIZAR PEDIDO (SOMENTE LEITURA)
// ==========================================
function abrirModalVisualizar(id, observacoes = '') {
    document.getElementById('txtVisuId').innerText = id;
    document.getElementById('tabelaVisualizar').innerHTML = '<tr><td colspan="4" class="py-4"><span class="spinner-border text-primary"></span> Carregando itens...</td></tr>';
    document.getElementById('txtVisuTotal').innerText = 'R$ 0,00';
    
    let areaObs = document.getElementById('areaObsVisualizar');
    // Adicionada verificação rigorosa para tratar "None" ou null vindos do Django
    if (observacoes && String(observacoes).trim() !== '' && String(observacoes).trim() !== 'None') {
        areaObs.innerHTML = `<i class="bi bi-info-circle-fill me-1"></i> <strong>Histórico/Motivo:</strong> ${observacoes}`;
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
    });
}


// ==========================================
// ↩️ ESTORNAR FATURAMENTO
// ==========================================
function abrirModalEstornar(id) {
    pedidoSelecionadoId = id;
    document.getElementById('txtEstornarId').innerText = id;
    document.getElementById('alertaEstornar').classList.add('d-none');
    objModalEstornar.show();
}

function confirmarEstorno() {
    const btn = document.getElementById('btnConfirmaEstorno');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Estornando...';

    fetch(`/api/pedidos/estornar/${pedidoSelecionadoId}/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') {
            location.reload(); // Recarrega a página para atualizar o status
        } else {
            mostrarErro('alertaEstornar', "Erro interno: " + data.mensagem);
            btn.disabled = false;
            btn.innerHTML = 'Sim, Estornar Pedido';
        }
    }).catch(err => {
        mostrarErro('alertaEstornar', "Falha de comunicação com o servidor.");
        btn.disabled = false;
        btn.innerHTML = 'Sim, Estornar Pedido';
    });
}

// ==========================================
// ✏️ REABRIR E CANCELAR (PADRÃO)
// ==========================================
function abrirModalReabrir(id) {
    pedidoSelecionadoId = id;
    document.getElementById('txtReabrirId').innerText = id;
    document.getElementById('motivoReabertura').value = '';
    document.getElementById('alertaReabrir').classList.add('d-none');
    objModalReabrir.show();
}

function abrirModalCancelar(id) {
    pedidoSelecionadoId = id;
    document.getElementById('txtCancelarId').innerText = id;
    document.getElementById('motivoCancelamento').value = '';
    document.getElementById('alertaCancelar').classList.add('d-none');
    objModalCancelar.show();
}

function confirmarReabertura() {
    const motivo = document.getElementById('motivoReabertura').value.trim();
    if (!motivo) {
        mostrarErro('alertaReabrir', "⚠ Por favor, digite o motivo da reabertura.");
        return;
    }

    const btn = document.getElementById('btnConfirmaReabrir');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processando...';

    fetch(`/api/pedidos/reabrir/${pedidoSelecionadoId}/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({motivo: motivo})
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') {
            window.location.href = data.url_redirecionamento;
        } else {
            mostrarErro('alertaReabrir', "Erro interno: " + data.mensagem);
            btn.disabled = false;
            btn.innerHTML = 'Reabrir Pedido';
        }
    }).catch(err => {
        mostrarErro('alertaReabrir', "Falha de comunicação com o servidor.");
        btn.disabled = false;
        btn.innerHTML = 'Reabrir Pedido';
    });
}

function confirmarCancelamento() {
    const motivo = document.getElementById('motivoCancelamento').value.trim();
    if (!motivo) {
        mostrarErro('alertaCancelar', "⚠ Por favor, digite o motivo do cancelamento.");
        return;
    }
    
    const btn = document.getElementById('btnConfirmaCancelar');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processando...';

    fetch(`/api/pedidos/cancelar/${pedidoSelecionadoId}/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({motivo: motivo})
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'sucesso') {
            location.reload();
        } else {
            mostrarErro('alertaCancelar', "Erro interno: " + data.mensagem);
            btn.disabled = false;
            btn.innerHTML = 'Confirmar Cancelamento';
        }
    }).catch(err => {
        mostrarErro('alertaCancelar', "Falha de comunicação com o servidor.");
        btn.disabled = false;
        btn.innerHTML = 'Confirmar Cancelamento';
    });
}
