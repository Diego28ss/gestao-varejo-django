document.addEventListener("DOMContentLoaded", function() {
    const container = document.getElementById('containerTagsPdv');
    let htmlTags = '';

    if (window.FILTROS_SALVOS.busca) {
        htmlTags += `<span class="badge bg-primary px-3 py-2 shadow-sm d-flex align-items-center gap-2" style="font-size: 0.85rem;"><i class="bi bi-funnel-fill"></i> ${window.FILTROS_SALVOS.busca.toUpperCase()} <a href="?limpar=true" class="text-white ms-1 text-decoration-none">&times;</a></span>`;
    }
    if (window.FILTROS_SALVOS.familia) {
        htmlTags += `<span class="badge bg-primary px-3 py-2 shadow-sm d-flex align-items-center gap-2" style="font-size: 0.85rem;"><i class="bi bi-folder-fill"></i> ${window.FILTROS_SALVOS.familia.toUpperCase()} <a href="?limpar=true" class="text-white ms-1 text-decoration-none">&times;</a></span>`;
    }
    if (window.FILTROS_SALVOS.marca) {
        htmlTags += `<span class="badge bg-primary px-3 py-2 shadow-sm d-flex align-items-center gap-2" style="font-size: 0.85rem;"><i class="bi bi-tags-fill"></i> ${window.FILTROS_SALVOS.marca.toUpperCase()} <a href="?limpar=true" class="text-white ms-1 text-decoration-none">&times;</a></span>`;
    }
    if (window.FILTROS_SALVOS.status) {
        htmlTags += `<span class="badge bg-primary px-3 py-2 shadow-sm d-flex align-items-center gap-2" style="font-size: 0.85rem;"><i class="bi bi-lightning-fill"></i> ${window.FILTROS_SALVOS.status.toUpperCase()} <a href="?limpar=true" class="text-white ms-1 text-decoration-none">&times;</a></span>`;
    }
    if (window.FILTROS_SALVOS.aviso) {
        let textoAviso = window.FILTROS_SALVOS.aviso === 'COM_AVISO' ? 'COM AVISO PENDENTE' : 'SEM AVISOS';
        htmlTags += `<span class="badge bg-warning text-dark px-3 py-2 shadow-sm d-flex align-items-center gap-2" style="font-size: 0.85rem;"><i class="bi bi-bell-fill"></i> ${textoAviso} <a href="?limpar=true" class="text-dark ms-1 text-decoration-none">&times;</a></span>`;
    }
    if(container) container.innerHTML = htmlTags;

    let chkSemNcm = document.getElementById('chkSemNcm');
    let inputNcm = document.getElementById('formNcm');

    if (chkSemNcm && inputNcm) {
        chkSemNcm.addEventListener('change', function() {
            if(this.checked) {
                inputNcm.value = 'N/A';
                inputNcm.readOnly = true;
                inputNcm.classList.add('bg-warning');
            } else {
                inputNcm.value = '';
                inputNcm.readOnly = false;
                inputNcm.classList.remove('bg-warning');
            }
        });
    }

    if (window.PERFIL_USUARIO && window.PERFIL_USUARIO !== 'Gerente' && window.PERFIL_USUARIO !== 'Supervisor' && window.PERFIL_USUARIO !== 'DEV') {
        let btnNovo = document.querySelector('button[onclick="abrirModalNovo()"]');
        if (btnNovo) btnNovo.style.display = 'none';

        document.querySelectorAll('button[onclick="prepararEdicao(this)"]').forEach(btn => {
            btn.classList.add('disabled-link');
            btn.classList.replace('text-white', 'text-dark');
            btn.style.opacity = '0.4';
            btn.onclick = function(e) {
                window.verificarPermissao(e, null, ['Gerente', 'Supervisor'], 'editar ou criar produtos');
            };
        });
    }
    
    const observer = new MutationObserver(() => {
        if (inputNcm.value === 'N/A') {
            chkSemNcm.checked = true;
            inputNcm.readOnly = true;
            inputNcm.classList.add('bg-warning');
        } else {
            chkSemNcm.checked = false;
            inputNcm.readOnly = false;
            inputNcm.classList.remove('bg-warning');
        }
    });
    
    let modalProduto = document.getElementById('modalProduto');
    if (modalProduto) {
        observer.observe(modalProduto, { attributes: true, attributeFilter: ['class'] });
    }
});
