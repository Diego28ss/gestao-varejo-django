// Função 1: Recupera o token de segurança do Django
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

// Função 2: Abre o Modal de Novo Caixa
function abrirModalNovoCaixa() {
    var modal = new bootstrap.Modal(document.getElementById('modalAberturaCaixa'));
    modal.show();
}

// Função 3: Processa a abertura chamando a nova API (Listener)
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

// Função 4: Abre o modal de retomar caixa já com o nome do operador
function abrirModalRetomarCaixa(login) {
    document.getElementById('retomarLogin').value = login;
    document.getElementById('spanLoginRetomar').innerText = login;
    document.getElementById('retomarSenha').value = '';
    document.getElementById('retomarLoginGerente').value = '';
    document.getElementById('retomarSenhaGerente').value = '';
    document.getElementById('retomarLastro').value = '0.00';
    new bootstrap.Modal(document.getElementById('modalRetomarCaixa')).show();
}

// Função 5: Valida a senha para desbloqueio chamando a API (Listener)
document.getElementById('btnConfirmarRetomar').addEventListener('click', function () {
    const loginOp = document.getElementById('retomarLogin').value;
    const senhaOp = document.getElementById('retomarSenha').value;
    const loginGer = document.getElementById('retomarLoginGerente').value;
    const senhaGer = document.getElementById('retomarSenhaGerente').value;
    const lastro = document.getElementById('retomarLastro').value;

    if (!senhaOp || !loginGer || !senhaGer) {
        alert("Todas as credenciais (Operador e Gerente) são obrigatórias!");
        return;
    }

    const btn = document.getElementById('btnConfirmarRetomar');
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Validando...';
    btn.disabled = true;

    fetch('/api/retomar-caixa/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
        body: JSON.stringify({
            'operador_login': loginOp,
            'operador_senha': senhaOp,
            'gerente_login': loginGer,
            'gerente_senha': senhaGer,
            'lastro': lastro
        })
    })
        .then(r => r.json()).then(data => {
            if (data.status === 'sucesso') {
                alert('Caixa desbloqueado! Imprimindo comprovante...');
                window.open(`/imprimir-cupom/desbloqueio/${data.caixa_id}/`, '_blank');
                window.location.href = configPDV.urlPDV;
            } else {
                alert("Erro: " + data.mensagem);
                btn.innerHTML = 'Desbloquear PDV';
                btn.disabled = false;
            }
        }).catch(e => {
            alert("Erro no servidor.");
            btn.innerHTML = 'Desbloquear PDV';
            btn.disabled = false;
        });
});

