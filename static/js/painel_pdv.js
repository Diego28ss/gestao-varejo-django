// Recupera o token de segurança do Django
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

// Abre o Modal de Novo Caixa
function abrirModalNovoCaixa() {
    var modal = new bootstrap.Modal(document.getElementById('modalAberturaCaixa'));
    modal.show();
}

// Processa a abertura chamando a nova API
document.getElementById('btnConfirmarAbertura').addEventListener('click', function () {
    const lastro = document.getElementById('inputLastro').value;
    const loginOp = document.getElementById('authLoginOperador').value;
    const senhaOp = document.getElementById('authSenhaOperador').value;
    const loginGer = document.getElementById('authLoginAbertura').value;
    const senhaGer = document.getElementById('authSenhaAbertura').value;

    if (!loginOp || !senhaOp || !loginGer || !senhaGer) {
        alert('Todas as credenciais (Operador e Gerente) são obrigatórias!');
        return;
    }

    const btn = document.getElementById('btnConfirmarAbertura');
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Validando...';
    btn.disabled = true;

    fetch('/api/abrir-caixa/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
        body: JSON.stringify({
            'lastro': lastro,
            'operador_login': loginOp,
            'operador_senha': senhaOp,
            'gerente_login': loginGer,
            'gerente_senha': senhaGer
        })
    })
        .then(r => r.json()).then(data => {
            if (data.status === 'sucesso') {
                alert('Caixa aberto! Imprimindo comprovante...');
                // Dispara a impressão do cupom térmico e ao fechar o alerta, envia para o PDV
                window.open(`/imprimir-cupom/abertura/${data.caixa_id}/`, '_blank');
                window.location.href = configPDV.urlPDV;
            } else {
                alert("Erro: " + data.mensagem);
                btn.innerHTML = 'Confirmar Abertura';
                btn.disabled = false;
            }
        }).catch(e => {
            alert("Erro no servidor.");
            btn.innerHTML = 'Confirmar Abertura';
            btn.disabled = false;
        });
});


// Lógica para renderizar os cards baseados no status passado pelo Django
window.onload = function () {
    const containerCaixa = document.getElementById('cardCaixaAtual');
    const statusAtual = configPDV.statusCaixa;

    if (statusAtual === 'ABERTO') {
        containerCaixa.innerHTML = `
            <div class="card h-100 shadow-sm card-lobby status-ocupado bg-white text-center cursor-pointer" onclick="window.location.href='${configPDV.urlPDV}'">
                <div class="card-body d-flex flex-column justify-content-center align-items-center py-5">
                    <i class="bi bi-cart-check-fill mb-3" style="font-size: 4rem; color: #3498db;"></i>
                    <h4 class="fw-bold" style="color: var(--azul-escuro);">Caixa em Andamento</h4>
                    <p class="text-muted small mt-2">Clique para retomar suas vendas.</p>
                </div>
            </div>
        `;
    } else if (statusAtual === 'FECHADO_TEMP') {
        containerCaixa.innerHTML = `
            <div class="card h-100 shadow-sm card-lobby status-bloqueado bg-white text-center cursor-pointer" onclick="alert('Funcionalidade de desbloqueio será ativada nas próximas fases!')">
                <div class="card-body d-flex flex-column justify-content-center align-items-center py-5">
                    <i class="bi bi-lock-fill mb-3" style="font-size: 4rem; color: #f39c12;"></i>
                    <h4 class="fw-bold" style="color: var(--azul-escuro);">Caixa Pausado</h4>
                    <p class="text-muted small mt-2">Requer senha do supervisor para desbloquear.</p>
                </div>
            </div>
        `;
    } else {
        containerCaixa.innerHTML = `
            <div class="card h-100 shadow-sm card-lobby bg-light text-center" style="opacity: 0.6; cursor: not-allowed;">
                <div class="card-body d-flex flex-column justify-content-center align-items-center py-5">
                    <i class="bi bi-dash-circle mb-3" style="font-size: 4rem; color: #95a5a6;"></i>
                    <h4 class="fw-bold" style="color: var(--azul-escuro);">Nenhum Caixa</h4>
                    <p class="text-muted small mt-2">Você não possui caixas em andamento.</p>
                </div>
            </div>
        `;
    }
};

function abrirModalRetomarCaixa(login) {
    document.getElementById('retomarLogin').value = login;
    document.getElementById('spanLoginRetomar').innerText = login;
    document.getElementById('retomarSenha').value = '';
    new bootstrap.Modal(document.getElementById('modalRetomarCaixa')).show();
}

document.getElementById('btnConfirmarRetomar').addEventListener('click', function () {
    const loginOp = document.getElementById('retomarLogin').value;
    const senhaOp = document.getElementById('retomarSenha').value;

    if (!senhaOp) { alert("A senha é obrigatória!"); return; }

    fetch('/api/retomar-caixa/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
        body: JSON.stringify({ 'operador_login': loginOp, 'operador_senha': senhaOp })
    })
        .then(r => r.json()).then(data => {
            if (data.status === 'sucesso') {
                window.location.href = configPDV.urlPDV;
            } else {
                alert("Erro: " + data.mensagem);
            }
        });
});
