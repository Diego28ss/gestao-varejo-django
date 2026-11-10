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

// Função 2: Modal de Novo Caixa
function abrirModalNovoCaixa() {
    new bootstrap.Modal(document.getElementById('modalAberturaCaixa')).show();
}

// Função 3: Processa Abertura
document.getElementById('btnConfirmarAbertura').addEventListener('click', function () {
    const lastro = document.getElementById('inputLastro').value;
    const loginOp = document.getElementById('authLoginOperador').value;
    const senhaOp = document.getElementById('authSenhaOperador').value;
    const loginGer = document.getElementById('authLoginAbertura').value;
    const senhaGer = document.getElementById('authSenhaAbertura').value;

    if (!loginOp || !senhaOp || !loginGer || !senhaGer) {
        alert('Todas as credenciais são obrigatórias!');
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

// ==========================================
// 🚀 LÓGICA DE RETOMAR CAIXA (SIMPLES)
// ==========================================
function abrirModalRetomarCaixa(login) {
    document.getElementById('retomarLogin').value = login;
    document.getElementById('spanLoginRetomar').innerText = login;
    document.getElementById('retomarSenha').value = '';

    new bootstrap.Modal(document.getElementById('modalRetomarCaixa')).show();
    setTimeout(() => { document.getElementById('retomarSenha').focus(); }, 500);
}

document.getElementById('btnConfirmarRetomar').addEventListener('click', function () {
    const loginOp = document.getElementById('retomarLogin').value;
    const senhaOp = document.getElementById('retomarSenha').value;

    if (!senhaOp) {
        alert("A senha do operador é obrigatória!");
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
            'acao': 'retomar'
        })
    })
        .then(r => r.json()).then(data => {
            if (data.status === 'sucesso') {
                window.location.href = configPDV.urlPDV;
            } else {
                alert("Erro: " + data.mensagem);
                btn.innerHTML = 'Acessar PDV';
                btn.disabled = false;
            }
        }).catch(e => {
            alert("Erro no servidor.");
            btn.innerHTML = 'Acessar PDV';
            btn.disabled = false;
        });
});


// ==========================================
// 🚀 LÓGICA DE DESBLOQUEAR CAIXA (DUPLO)
// ==========================================
function abrirModalDesbloquearCaixa(login) {
    document.getElementById('desbloquearLoginOp').value = login;
    document.getElementById('spanLoginDesbloquear').innerText = login;
    document.getElementById('desbloquearSenhaOp').value = '';
    document.getElementById('desbloquearLoginGer').value = '';
    document.getElementById('desbloquearSenhaGer').value = '';
    document.getElementById('desbloquearLastro').value = '0.00';

    new bootstrap.Modal(document.getElementById('modalDesbloquearCaixa')).show();
    setTimeout(() => { document.getElementById('desbloquearSenhaOp').focus(); }, 500);
}

document.getElementById('btnConfirmarDesbloqueio').addEventListener('click', function () {
    const loginOp = document.getElementById('desbloquearLoginOp').value;
    const senhaOp = document.getElementById('desbloquearSenhaOp').value;
    const loginGer = document.getElementById('desbloquearLoginGer').value;
    const senhaGer = document.getElementById('desbloquearSenhaGer').value;
    const lastro = document.getElementById('desbloquearLastro').value;

    if (!senhaOp || !loginGer || !senhaGer) {
        alert("Todas as credenciais (Operador e Gerente) são obrigatórias!");
        return;
    }

    const btn = document.getElementById('btnConfirmarDesbloqueio');
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
            'lastro': lastro,
            'acao': 'desbloquear'
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
