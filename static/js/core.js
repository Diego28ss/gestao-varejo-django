window.mostrarAviso = function(mensagem, tipo = 'erro') {
    let container = document.getElementById('toast-container-sistema');
    if (!container) return;

    let bgClass = tipo === 'sucesso' ? 'bg-success' : (tipo === 'aviso' ? 'bg-warning' : 'bg-danger');
    let textClass = tipo === 'aviso' ? 'text-dark' : 'text-white';
    let icon = tipo === 'sucesso' ? '✅' : (tipo === 'aviso' ? '⚠️' : '❌');

    let toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center ${textClass} ${bgClass} border-0 shadow-lg mb-2`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body fw-bold fs-6">
                ${icon} ${mensagem}
            </div>
            <button type="button" class="btn-close ${tipo === 'aviso' ? '' : 'btn-close-white'} me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    container.appendChild(toastEl);
    let toast = new bootstrap.Toast(toastEl, { delay: 5000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => { toastEl.remove(); });
};

window.verificarPermissao = function(event, urlDestino, perfisPermitidos, acaoDescricao = "acessar esta área") {
    if (!perfisPermitidos.includes(window.PERFIL_USUARIO)) {
        event.preventDefault();
        document.getElementById('acessoNegadoMensagem').innerText = `Seu perfil (${window.PERFIL_USUARIO}) não tem permissão para ${acaoDescricao}. O acesso é restrito aos cargos: ${perfisPermitidos.join(' ou ')}.`;
        new bootstrap.Modal(document.getElementById('modalAcessoNegado')).show();
        return false;
    }
    if(urlDestino) window.location.href = urlDestino;
    return true;
};

document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll('[data-perfis-permitidos]').forEach(el => {
        let perfis = el.getAttribute('data-perfis-permitidos').split(',');
        if (!perfis.includes(window.PERFIL_USUARIO)) {
            el.classList.add('disabled-link');
            el.onclick = function(e) {
                let desc = el.getAttribute('data-acao-desc') || "acessar esta área";
                verificarPermissao(e, null, perfis, desc);
            };
        }
    });
});
