// ==========================================
// 🔄 MÓDULO DE DEVOLUÇÕES (LOGÍSTICA REVERSA)
// ==========================================

let modalErroDev;

document.addEventListener("DOMContentLoaded", function() {
    let elModalErro = document.getElementById('modalErroDevolucao');
    if(elModalErro) modalErroDev = new bootstrap.Modal(elModalErro);
});

function abrirModalErro(vendaId) {
    let btnCorrigir = document.getElementById(`btn-corrigir-${vendaId}`);
    let motivoSalvo = btnCorrigir ? btnCorrigir.getAttribute('data-motivo-erro') : null;
    
    let textoErro = document.getElementById('textoErroSefaz');
    document.getElementById('inputIdDevolucaoFalha').value = vendaId;
    
    if(modalErroDev) modalErroDev.show();

    // Se o erro já estiver carregado na memória do botão, exibe logo.
    if (motivoSalvo && motivoSalvo !== 'null' && motivoSalvo !== '') {
        textoErro.innerText = motivoSalvo;
    } else {
        // Se a página acabou de abrir, o modal faz a pesquisa na SEFAZ
        textoErro.innerHTML = '<span class="spinner-border spinner-border-sm text-danger me-2"></span> Buscando o motivo exato na SEFAZ...';
        
        fetch(`/api/fiscal/consultar-status/?venda_id=${vendaId}`)
        .then(response => response.json())
        .then(data => {
            if (data.sucesso && data.motivo) {
                textoErro.innerText = data.motivo;
                if(btnCorrigir) btnCorrigir.setAttribute('data-motivo-erro', data.motivo); // Guarda na memória
            } else if (data.sucesso && data.status_fiscal.includes('ERRO')) {
                textoErro.innerText = data.motivo || "A SEFAZ rejeitou o documento, mas não detalhou um motivo específico.";
            } else {
                textoErro.innerText = "Erro desconhecido. Você pode excluir este rascunho em segurança e tentar novamente.";
            }
        })
        .catch(() => {
            textoErro.innerText = "⚠️ Falha de comunicação com a SEFAZ neste momento. Mas você pode excluir o rascunho.";
        });
    }
}

function confirmarExclusaoErro() {
    let vendaId = document.getElementById('inputIdDevolucaoFalha').value;
    let btn = document.getElementById('btnConfirmarExclusaoErro');
    
    btn.innerHTML = '⏳ Processando exclusão...';
    btn.disabled = true;

    fetch('/api/fiscal/cancelar-nota/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 'venda_id': vendaId, 'justificativa': 'Exclusão de rascunho de devolução com falha.' })
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            window.mostrarAviso(data.mensagem, 'sucesso');
            if(modalErroDev) modalErroDev.hide();
            setTimeout(() => { window.location.reload(); }, 1000);
        } else {
            window.mostrarAviso("Erro ao limpar rascunho: " + data.erro, 'erro');
            btn.innerHTML = '🗑️ Excluir Rascunho e Liberar Nova Tentativa';
            btn.disabled = false;
        }
    });
}

