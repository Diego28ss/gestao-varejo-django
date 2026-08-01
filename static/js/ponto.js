// ==========================================
// 🕒 MÓDULO DE PONTO ELETRÓNICO (RH)
// ==========================================

document.addEventListener("DOMContentLoaded", function() {
    
    // --- LÓGICA DA TELA: BATER PONTO ---
    const relogio = document.getElementById('relogio-digital');
    if (relogio) {
        // Configura a data de hoje formatada
        const opcoesData = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        let dataFormatada = new Date().toLocaleDateString('pt-BR', opcoesData);
        document.getElementById('data-atual').textContent = dataFormatada.charAt(0).toUpperCase() + dataFormatada.slice(1);

        // Motor do Relógio
        function atualizarRelogio() {
            const agora = new Date();
            const hora = String(agora.getHours()).padStart(2, '0');
            const minuto = String(agora.getMinutes()).padStart(2, '0');
            const segundo = String(agora.getSeconds()).padStart(2, '0');
            relogio.textContent = `${hora}:${minuto}:${segundo}`;
        }
        setInterval(atualizarRelogio, 1000);
        atualizarRelogio();
    }

    // --- LÓGICA DA TELA: RELATÓRIO DE PONTO ---
    const modalAuthEl = document.getElementById('modalAuth');
    if (modalAuthEl) {
        new bootstrap.Modal(modalAuthEl).show();
    }
});

// Variáveis globais para a tela de Relatório
let creds = {login: '', senha: ''};

window.validarAuth = function() {
    creds.login = document.getElementById('auth_login').value;
    creds.senha = document.getElementById('auth_senha').value;
    
    // Tira o foco do botão para não irritar o Bootstrap (aria-hidden)
    if(document.activeElement) document.activeElement.blur(); 
    
    bootstrap.Modal.getInstance(document.getElementById('modalAuth')).hide();
};

window.buscarPonto = async function() {
    // Usa as variáveis definidas no HTML
    const urlApi = window.API_PONTO_URL;
    const token = window.CSRF_TOKEN;

    if(!urlApi || !token) {
        console.error("Variáveis de configuração da API não encontradas.");
        return;
    }

    try {
        const res = await fetch(urlApi, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json', 
                'X-CSRFToken': token
            },
            body: JSON.stringify({
                login: creds.login, 
                senha: creds.senha,
                colaborador: document.getElementById('sel_colaborador').value,
                data_ini: document.getElementById('data_ini').value,
                data_fim: document.getElementById('data_fim').value
            })
        });

        const data = await res.json();
        if(data.erro) {
            window.mostrarAviso(data.erro, 'erro');
            return;
        }
        
        document.getElementById('colab_nome').innerText = data.nome;
        let tbody = document.getElementById('tabela-ponto');
        
        if (data.pontos && data.pontos.length > 0) {
            tbody.innerHTML = data.pontos.map(p => `<tr>
                <td>${p.data}</td><td>${p.e1}</td><td>${p.s1}</td><td>${p.e2}</td><td>${p.s2}</td>
                <td class="${p.saldo >= 0 ? 'text-success fw-bold' : 'text-danger fw-bold'}">
                    ${p.saldo > 0 ? '+' + p.saldo : p.saldo}
                </td>
            </tr>`).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="py-4 text-muted">Nenhum registo encontrado neste período.</td></tr>';
        }
        
        document.getElementById('saldo_total').innerText = data.saldo_total + " min";
    } catch (e) {
        window.mostrarAviso("Ocorreu um erro ao comunicar com o servidor. Verifique a consola.", 'erro');
        console.error(e);
    }
};

window.gerarPDF = function() {
    if (!creds.login || !creds.senha) {
        window.mostrarAviso("Autenticação obrigatória. Por favor, pesquise o ponto primeiro antes de gerar o PDF.", 'aviso');
        return;
    }

    // Cria um formulário dinâmico e invisível para enviar os dados via POST para a aba de PDF
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/api/relatorio-ponto/pdf/';
    form.target = '_blank'; // Abre numa aba nova para não fechar o sistema

    // Adiciona a chave de segurança do Django
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = window.CSRF_TOKEN;
    form.appendChild(csrfInput);

    // Carrega as variáveis que estão na tela
    const params = {
        login: creds.login,
        senha: creds.senha,
        colaborador: document.getElementById('sel_colaborador').value,
        data_ini: document.getElementById('data_ini').value,
        data_fim: document.getElementById('data_fim').value
    };

    // Insere os parâmetros no formulário invisível
    for (const key in params) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = key;
        input.value = params[key];
        form.appendChild(input);
    }

    // Dispara o formulário e destrói-o a seguir
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
};

