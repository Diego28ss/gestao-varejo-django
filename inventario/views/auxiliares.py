from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

# Importação dos modelos necessários para a gestão de auxiliares
from inventario.models import Familia, Marca

# ==========================================
# ⚙️ SUBMENUS AUXILIARES SEPARADOS
# ==========================================

def tela_marcas(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    familias = Familia.objects.all().order_by('nome')
    marcas = Marca.objects.all().order_by('nome')
    return render(request, 'inventario/gerencia_auxiliares.html', {
        'familias': familias, 'marcas': marcas, 'marcas_list': marcas, 'fabricantes': marcas, 'aba_ativa': 'marcas'
    })


def tela_familias(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    familias = Familia.objects.all().order_by('nome')
    marcas = Marca.objects.all().order_by('nome')
    return render(request, 'inventario/gerencia_auxiliares.html', {
        'familias': familias, 'familias_list': familias, 'grupos': familias, 'marcas': marcas, 'aba_ativa': 'familias'
    })


def salvar_marca(request):
    if request.method == 'POST':
        marca_id = request.POST.get('marca_id')
        nome = request.POST.get('nome')
        if marca_id:
            marca = get_object_or_404(Marca, id=marca_id)
            marca.nome = nome
            marca.save()
            messages.success(request, f"Marca '{nome}' atualizada!")
        else:
            Marca.objects.create(nome=nome)
            messages.success(request, f"Marca '{nome}' cadastrada!")
    return redirect('tela_marcas')


def excluir_marca(request, id):
    marca = get_object_or_404(Marca, id=id)
    nome = marca.nome
    marca.delete()
    messages.success(request, f"Marca '{nome}' excluída!")
    return redirect('tela_marcas')


def salvar_familia(request):
    if request.method == 'POST':
        familia_id = request.POST.get('familia_id')
        nome = request.POST.get('nome')
        if familia_id:
            familia = get_object_or_404(Familia, id=familia_id)
            familia.nome = nome
            familia.save()
            messages.success(request, f"Família '{nome}' updated successfully!")
        else:
            Familia.objects.create(nome=nome)
            messages.success(request, f"Família '{nome}' cadastrada!")
    return redirect('tela_familias')


def excluir_familia(request, id):
    familia = get_object_or_404(Familia, id=id)
    nome = familia.nome
    familia.delete()
    messages.success(request, f"Família '{nome}' excluída!")
    return redirect('tela_familias')
