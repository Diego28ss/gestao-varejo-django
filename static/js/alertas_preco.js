function resolverAlerta(id) {
    if(confirm("Confirmar que a nova etiqueta com o novo preço já foi colocada na gôndola?")) {
        fetch(`/api/inventario/resolver-alerta-preco/${id}/`, {
            method: 'POST',
            headers: {'X-CSRFToken': window.CSRF_TOKEN}
        }).then(res => res.json()).then(data => {
            if(data.status === 'sucesso') {
                let linha = document.getElementById(`linha-alerta-${id}`);
                linha.style.transition = "opacity 0.5s ease";
                linha.style.opacity = "0";
                setTimeout(() => linha.remove(), 500);
                window.mostrarAviso("Etiqueta atualizada com sucesso!", "sucesso");
            } else {
                window.mostrarAviso(data.mensagem, 'erro');
            }
        });
    }
}

function imprimirEtiqueta(nomeProduto) {
    alert(`Imprimindo etiqueta para: ${nomeProduto}\n(Em breve: Envio direto para a impressora térmica)`);
}
