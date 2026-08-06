// ==========================================
// 🕒 MÓDULO DE PONTO ELETRÓNICO (RH)
// ==========================================

// 1. Função que converte os Minutos de Saldo para o formato HH:MM:SS
function formatarTempo(minutosTotais) {
    if (!minutosTotais || isNaN(minutosTotais)) return "00:00:00";
    
    // Verifica se o saldo é negativo
    let sinal = minutosTotais < 0 ? "-" : "";
    let absMinutos = Math.abs(minutosTotais);
    
    // Calcula as horas, minutos e segundos
    let horas = Math.floor(absMinutos / 60);
    let minutos = Math.floor(absMinutos % 60);
    let segundos = Math.floor((absMinutos * 60) % 60);

    // Garante que sempre fique com 2 dígitos. Ex: '9' vira '09'
    let hStr = String(horas).padStart(2, '0');
    let mStr = String(minutos).padStart(2, '0');
    let sStr = String(segundos).padStart(2, '0');

    return `${sinal}${hStr}:${mStr}:${sStr}`;
}

// 2. Função para garantir que os horários de batida tenham os segundos (Ex: 08:00 vira 08:00:00)
function formatarHora(horaStr) {
    if (!horaStr || horaStr === '--:--' || horaStr === '-') return '--:--:--';
    
    let partes = horaStr.split(':');
    if (partes.length === 2) {
        return `${horaStr}:00`;
    }
    return horaStr;
}

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
        
        // Aplicação das funções formatadoras nos horários e no saldo
        if (data.pontos && data.pontos.length > 0) {
            tbody.innerHTML = data.pontos.map(p => `<tr>
                <td>${p.data}</td>
                <td>${formatarHora(p.e1)}</td>
                <td>${formatarHora(p.s1)}</td>
                <td>${formatarHora(p.e2)}</td>
                <td>${formatarHora(p.s2)}</td>
                <td class="${p.saldo >= 0 ? 'text-success fw-bold' : 'text-danger fw-bold'}">
                    ${p.saldo > 0 ? '+' + formatarTempo(p.saldo) : formatarTempo(p.saldo)}
                </td>
            </tr>`).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="py-4 text-muted">Nenhum registo encontrado neste período.</td></tr>';
        }
        
        // Atualiza o Saldo Total no rodapé e aplica a cor dinamicamente
        let saldoTotalEl = document.getElementById('saldo_total');
        saldoTotalEl.innerText = data.saldo_total > 0 ? '+' + formatarTempo(data.saldo_total) : formatarTempo(data.saldo_total);
        
        if (data.saldo_total >= 0) {
            saldoTotalEl.className = "fw-bold fs-5 text-success";
        } else {
            saldoTotalEl.className = "fw-bold fs-5 text-danger";
        }

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
