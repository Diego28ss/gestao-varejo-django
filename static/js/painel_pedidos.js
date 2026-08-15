let pedidoSelecionadoId = null;
let objModalReabrir = null;
let objModalCancelar = null;

document.addEventListener("DOMContentLoaded", function() {
    objModalReabrir = new bootstrap.Modal(document.getElementById('modalReabrir'));
    objModalCancelar = new bootstrap.Modal(document.getElementById('modalCancelar'));
    
    // Limpa os erros ao fechar os modais para a próxima vez que abrir
    document.getElementById('modalReabrir').addEventListener('hidden.bs.modal', function () {
        document.getElementById('alertaReabrir').classList.add('d-none');
    });
    document.getElementById('modalCancelar').addEventListener('hidden.bs.modal', function () {
        document.getElementById('alertaCancelar').classList.add('d-none');
    });
});

function mostrarErro(idElemento, mensagem) {
    const divErro = document.getElementById(idElemento);
    divErro.innerText = mensagem;
    divErro.classList.remove('d-none');
}

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
            // 👉 Agora o JS usa a URL oficial devolvida pelo Python
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

