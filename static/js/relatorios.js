// ==========================================
// 📊 MÓDULO DE RELATÓRIOS E INDICADORES
// ==========================================

let modalCancelar;

document.addEventListener("DOMContentLoaded", function() {
    let elCancelar = document.getElementById('modalCancelar');
    if(elCancelar) modalCancelar = new bootstrap.Modal(elCancelar);
});

function abrirModalCancelar(id) {
    let inputVendaId = document.getElementById('cancel_venda_id');
    let spanDisplay = document.getElementById('cancel_venda_display');
    
    if (inputVendaId && spanDisplay) {
        inputVendaId.value = id;
        spanDisplay.innerText = id;
        if(modalCancelar) modalCancelar.show();
    }
}
