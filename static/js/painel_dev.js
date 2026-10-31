function editarLoja(id, nome, ibge) {
    document.getElementById('loja_id').value = id;
    document.getElementById('loja_nome').value = nome;
    document.getElementById('loja_ibge').value = ibge;
    new bootstrap.Modal(document.getElementById('modalLoja')).show();
}
