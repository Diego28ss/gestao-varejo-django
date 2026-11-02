function formatarMinutos(minutosTotais) {
    let sinal = minutosTotais < 0 ? "-" : "+ ";
    let absMin = Math.abs(minutosTotais);
    let horas = Math.floor(absMin / 60);
    let minutos = absMin % 60;
    return `${sinal}${String(horas).padStart(2, '0')}:${String(minutos).padStart(2, '0')}:00`;
}

// Variável global para controlar a instância do modal do Bootstrap
let modalJust = null;
let modalAuditoria = null;

function buscarPonto() {
    let colab = document.getElementById('sel_colaborador').value;
    let dIni = document.getElementById('data_ini').value;
    let dFim = document.getElementById('data_fim').value;

    document.getElementById('tabela-ponto').innerHTML = '<tr><td colspan="6" class="py-5"><span class="spinner-border text-primary"></span> Buscando dados...</td></tr>';

    fetch(window.URL_API_DADOS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN },
        body: JSON.stringify({ colaborador: colab, data_ini: dIni, data_fim: dFim })
    })
        .then(res => res.json())
        .then(data => {
            if (data.erro) {
                window.mostrarAviso(data.erro, 'erro');
                document.getElementById('tabela-ponto').innerHTML = `<tr><td colspan="6" class="text-danger fw-bold py-4">${data.erro}</td></tr>`;
                return;
            }

            document.getElementById('colab_nome').innerText = data.nome;

            let saldoElement = document.getElementById('saldo_total');
            saldoElement.innerText = formatarMinutos(data.saldo_total);

            if (data.saldo_total < 0) {
                saldoElement.className = "fw-bold fs-4 text-danger";
            } else {
                saldoElement.className = "fw-bold fs-4 text-success";
            }

            let html = '';
            data.pontos.forEach(p => {
                let colorClass = p.saldo < 0 ? 'text-danger' : (p.saldo > 0 ? 'text-success' : 'text-muted');

                // 🚀 LÓGICA DO OLHINHO: Atualizado para chamar o modal
                let iconeAuditoria = '';
                if (p.has_ajuste) {
                    iconeAuditoria = `<i class="bi bi-eye-fill text-warning ms-2" style="cursor:pointer;" 
                                     title="Ver Detalhes" 
                                     onclick="exibirModalAuditoria('${p.data}', '${p.auditoria_gerente}', '${p.auditoria_original}', '${p.auditoria_motivo}')"></i>`;
                }

                html += `<tr>
                <td class="text-start ps-3 fw-bold" style="color: var(--azul-escuro);">
                    ${p.data} ${iconeAuditoria}
                </td>
                <td class="fw-bold">${p.e1}</td>
                <td class="text-muted">${p.s1}</td>
                <td class="text-muted">${p.e2}</td>
                <td class="fw-bold">${p.s2}</td>
                <td class="fw-bold ${colorClass}">${formatarMinutos(p.saldo)}</td>
            </tr>`;
            });
            document.getElementById('tabela-ponto').innerHTML = html;
        }).catch(err => {
            window.mostrarAviso("Erro ao comunicar com o servidor.", 'erro');
            document.getElementById('tabela-ponto').innerHTML = `<tr><td colspan="6" class="text-danger fw-bold py-4">Erro de conexão.</td></tr>`;
        });
}


function gerarPDF() {
    let colab = document.getElementById('sel_colaborador').value;
    let dIni = document.getElementById('data_ini').value;
    let dFim = document.getElementById('data_fim').value;

    let form = document.createElement('form');
    form.method = 'POST';
    form.action = window.URL_GERAR_PDF;
    form.target = '_blank';

    let inputs = [
        { name: 'csrfmiddlewaretoken', value: window.CSRF_TOKEN },
        { name: 'colaborador', value: colab },
        { name: 'data_ini', value: dIni },
        { name: 'data_fim', value: dFim }
    ];

    inputs.forEach(item => {
        let input = document.createElement('input');
        input.type = 'hidden';
        input.name = item.name;
        input.value = item.value;
        form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
}


function abrirModalJustificativa() {
    let colab = document.getElementById('sel_colaborador').value;
    if (!colab) {
        window.mostrarAviso("Selecione um colaborador primeiro.", "aviso");
        return;
    }

    document.getElementById('auth_colab_login').value = colab;
    document.getElementById('tipo_justificativa').value = "";
    alternarCamposJustificativa();

    if (!modalJust) {
        modalJust = new bootstrap.Modal(document.getElementById('modalJustificativa'));
    }
    modalJust.show();
}


function alternarCamposJustificativa() {
    let tipo = document.getElementById('tipo_justificativa').value;

    document.querySelectorAll('.painel-acao').forEach(el => el.classList.add('d-none'));
    document.getElementById('btnSalvarJustificativa').disabled = true;

    if (tipo === "FERIAS") {
        document.getElementById('painelFerias').classList.remove('d-none');
        document.getElementById('btnSalvarJustificativa').disabled = false;
    }
    else if (tipo === "FALTA") {
        document.getElementById('painelFalta').classList.remove('d-none');
        document.getElementById('painelMotivo').classList.remove('d-none');
        document.getElementById('btnSalvarJustificativa').disabled = false;
    }
    else if (tipo === "ABONO") {
        document.getElementById('painelAbono').classList.remove('d-none');
        document.getElementById('painelMotivo').classList.remove('d-none');
        document.getElementById('painelAssinatura').classList.remove('d-none');
        document.getElementById('btnSalvarJustificativa').disabled = false;
    }
    else if (tipo === "AJUSTE") {
        document.getElementById('painelAjuste').classList.remove('d-none');
        document.getElementById('painelMotivo').classList.remove('d-none');
        document.getElementById('painelAssinatura').classList.remove('d-none');
        document.getElementById('btnSalvarJustificativa').disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    let btnSalvar = document.getElementById('btnSalvarJustificativa');
    if (btnSalvar) {
        btnSalvar.addEventListener('click', salvarJustificativa);
    }
});


document.addEventListener('DOMContentLoaded', function () {
    let btnSalvar = document.getElementById('btnSalvarJustificativa');
    if (btnSalvar) {
        btnSalvar.addEventListener('click', salvarJustificativa);
    }
});

function salvarJustificativa() {
    let tipo = document.getElementById('tipo_justificativa').value;
    let btnSalvar = document.getElementById('btnSalvarJustificativa');

    let payload = {
        tipo_justificativa: tipo,
        just_ferias_ini: document.getElementById('just_ferias_ini')?.value,
        just_ferias_fim: document.getElementById('just_ferias_fim')?.value,
        chk_atestado: document.getElementById('chk_atestado')?.checked,
        just_ajuste_tipo: document.getElementById('just_ajuste_tipo')?.value,
        just_ajuste_hora: document.getElementById('just_ajuste_hora')?.value,
        just_abono_ini: document.getElementById('just_abono_ini')?.value,
        just_abono_fim: document.getElementById('just_abono_fim')?.value,
        just_motivo: document.getElementById('just_motivo')?.value,
        auth_gerente_login: document.getElementById('auth_gerente_login')?.value,
        auth_gerente_senha: document.getElementById('auth_gerente_senha')?.value,
        auth_colab_login: document.getElementById('auth_colab_login')?.value,
        auth_colab_senha: document.getElementById('auth_colab_senha')?.value,
        data_alvo: "",
        data_fim_alvo: ""
    };

    if (tipo === "FALTA") {
        payload.data_alvo = document.getElementById('just_falta_ini')?.value;
        payload.data_fim_alvo = document.getElementById('just_falta_fim')?.value;
    } else if (tipo === "ABONO") {
        payload.data_alvo = document.getElementById('just_abono_data')?.value;
    } else if (tipo === "AJUSTE") {
        payload.data_alvo = document.getElementById('just_ajuste_data')?.value;
    }

    if (!tipo) {
        window.mostrarAviso("Selecione o tipo de ação.", "aviso");
        return;
    }

    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<span class="spinner-border spinner-border-sm text-dark"></span> Salvando...';

    fetch('/api/relatorio-ponto/justificar/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.CSRF_TOKEN
        },
        body: JSON.stringify(payload)
    })
        .then(res => res.json())
        .then(data => {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = '<i class="bi bi-hdd-fill"></i> Registrar Auditoria';

            if (data.erro) {
                window.mostrarAviso(data.erro, 'erro');
            } else {
                window.mostrarAviso(data.mensagem || "Registrado com sucesso!", 'sucesso');
                modalJust.hide();
                buscarPonto();
            }
        })
        .catch(err => {
            console.error(err);
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = '<i class="bi bi-hdd-fill"></i> Registrar Auditoria';
            window.mostrarAviso("Erro de comunicação com o servidor.", 'erro');
        });
}

function exibirModalAuditoria(data, gerente, acao, motivo) {
    if (!modalAuditoria) {
        modalAuditoria = new bootstrap.Modal(document.getElementById('modalVerAuditoria'));
    }
    document.getElementById('ver_audit_data').innerText = data;
    document.getElementById('ver_audit_gerente').innerText = gerente;
    document.getElementById('ver_audit_acao').innerText = acao;
    document.getElementById('ver_audit_motivo').innerText = motivo || "Sem motivo registrado.";

    modalAuditoria.show();
}
