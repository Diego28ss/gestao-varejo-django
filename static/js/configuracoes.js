function habilitarEdicao() {
    let input = document.getElementById('inputDias');
    let btnEditar = document.getElementById('btnEditarDias');
    let divSalvar = document.getElementById('divSalvar');

    // Destrava o input
    input.disabled = false;
    
    // Aplica o design de edição (Verde Destaque)
    input.style.backgroundColor = "#fffdf5"; 
    input.style.color = "#198754"; 
    input.style.borderColor = "#ffc107"; 
    
    input.focus();

    // Esconde o botão do lápis e mostra o botão de Salvar
    btnEditar.classList.add('d-none');
    divSalvar.classList.remove('d-none');
}

function cancelarEdicao() {
    let input = document.getElementById('inputDias');
    let btnEditar = document.getElementById('btnEditarDias');
    let divSalvar = document.getElementById('divSalvar');

    // Recupera o valor original que foi embutido pelo Django no HTML
    let valorOriginal = input.getAttribute('data-valor-original');

    // Volta o input ao normal
    input.value = valorOriginal;
    input.disabled = true;
    
    input.style.backgroundColor = "#e9ecef";
    input.style.color = "#6c757d";
    input.style.borderColor = "#ced4da";

    // Volta os botões originais
    btnEditar.classList.remove('d-none');
    divSalvar.classList.add('d-none');
}
