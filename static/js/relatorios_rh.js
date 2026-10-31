function formatarMinutos(minutosTotais) {
    let sinal = minutosTotais < 0 ? "-" : "+ ";
    let absMin = Math.abs(minutosTotais);
    let horas = Math.floor(absMin / 60);
    let minutos = absMin % 60;
    return `${sinal}${String(horas).padStart(2, '0')}:${String(minutos).padStart(2, '0')}:00`;
}

function buscarPonto() {
    let colab = document.getElementById('sel_colaborador').value;
    let dIni = document.getElementById('data_ini').value;
    let dFim = document.getElementById('data_fim').value;

    document.getElementById('tabela-ponto').innerHTML = '<tr><td colspan="6" class="py-5"><span class="spinner-border text-primary"></span> Buscando dados...</td></tr>';

    fetch(window.URL_API_DADOS, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN},
        body: JSON.stringify({colaborador: colab, data_ini: dIni, data_fim: dFim})
    })
    .then(res => res.json())
    .then(data => {
        if(data.erro) {
            window.mostrarAviso(data.erro, 'erro');
            document.getElementById('tabela-ponto').innerHTML = `<tr><td colspan="6" class="text-danger fw-bold py-4">${data.erro}</td></tr>`;
            return;
        }

        document.getElementById('colab_nome').innerText = data.nome;
        
        let saldoElement = document.getElementById('saldo_total');
        saldoElement.innerText = formatarMinutos(data.saldo_total);
        
        if(data.saldo_total < 0) {
            saldoElement.className = "fw-bold fs-4 text-danger";
        } else {
            saldoElement.className = "fw-bold fs-4 text-success";
        }

        let html = '';
        data.pontos.forEach(p => {
            let colorClass = p.saldo < 0 ? 'text-danger' : (p.saldo > 0 ? 'text-success' : 'text-muted');
            html += `<tr>
                <td class="fw-bold" style="color: var(--azul-escuro);">${p.data}</td>
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
        {name: 'csrfmiddlewaretoken', value: window.CSRF_TOKEN},
        {name: 'colaborador', value: colab},
        {name: 'data_ini', value: dIni},
        {name: 'data_fim', value: dFim}
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
