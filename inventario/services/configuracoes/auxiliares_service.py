from django.shortcuts import get_object_or_404
from inventario.models import Familia, Marca

def listar_marcas():
    # Retorna todas as marcas do banco de dados ordenadas alfabeticamente
    return Marca.objects.all().order_by('nome')


def listar_familias():
    # Retorna todas as famílias do banco de dados ordenadas alfabeticamente
    return Familia.objects.all().order_by('nome')


def processar_salvar_marca(marca_id, nome):
    # Atualiza a marca se o ID existir, caso contrário, cria uma nova marca
    if marca_id:
        marca = get_object_or_404(Marca, id=marca_id)
        marca.nome = nome
        marca.save()
        return marca, False  # False indica que foi apenas atualizado
    else:
        marca = Marca.objects.create(nome=nome)
        return marca, True   # True indica que um novo registro foi criado


def processar_excluir_marca(marca_id):
    # Exclui a marca identificada pelo ID e retorna o nome para exibição na mensagem
    marca = get_object_or_404(Marca, id=marca_id)
    nome = marca.nome
    marca.delete()
    return nome


def processar_salvar_familia(familia_id, nome):
    # Atualiza a família se o ID existir, caso contrário, cria uma nova família
    if familia_id:
        familia = get_object_or_404(Familia, id=familia_id)
        familia.nome = nome
        familia.save()
        return familia, False
    else:
        familia = Familia.objects.create(nome=nome)
        return familia, True


def processar_excluir_familia(familia_id):
    # Exclui a família identificada pelo ID e retorna o nome para exibição na mensagem
    familia = get_object_or_404(Familia, id=familia_id)
    nome = familia.nome
    familia.delete()
    return nome
