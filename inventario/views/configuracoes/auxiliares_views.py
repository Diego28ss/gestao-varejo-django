from django.shortcuts import render, redirect
from django.contrib import messages
from inventario.services.configuracoes import auxiliares_service

# ==========================================
# ⚙️ VIEWS DE AUXILIARES (THIN VIEWS)
# ==========================================

def tela_marcas(request):
    # Valida a sessão do usuário e renderiza a tela de marcas com dados do serviço
    if 'usuario_logado' not in request.session:
        return redirect('login')
    
    familias = auxiliares_service.listar_familias()
    marcas = auxiliares_service.listar_marcas()
    
    return render(request, 'inventario/gerencia_auxiliares.html', {
        'familias': familias, 'marcas': marcas, 'marcas_list': marcas, 'fabricantes': marcas, 'aba_ativa': 'marcas'
    })


def tela_familias(request):
    # Valida a sessão do usuário e renderiza a tela de famílias com dados do serviço
    if 'usuario_logado' not in request.session:
        return redirect('login')
        
    familias = auxiliares_service.listar_familias()
    marcas = auxiliares_service.listar_marcas()
    
    return render(request, 'inventario/gerencia_auxiliares.html', {
        'familias': familias, 'familias_list': familias, 'grupos': familias, 'marcas': marcas, 'aba_ativa': 'familias'
    })


def salvar_marca(request):
    # Recebe os dados via POST e delega a criação ou atualização da marca ao serviço
    if request.method == 'POST':
        marca_id = request.POST.get('marca_id')
        nome = request.POST.get('nome')
        
        marca, criado = auxiliares_service.processar_salvar_marca(marca_id, nome)
        
        if criado:
            messages.success(request, f"Marca '{nome}' cadastrada!")
        else:
            messages.success(request, f"Marca '{nome}' atualizada!")
            
    return redirect('tela_marcas')


def excluir_marca(request, id):
    # Envia o ID para o serviço excluir e utiliza o nome retornado para a mensagem
    nome_excluido = auxiliares_service.processar_excluir_marca(id)
    messages.success(request, f"Marca '{nome_excluido}' excluída!")
    return redirect('tela_marcas')


def salvar_familia(request):
    # Recebe os dados via POST e delega a criação ou atualização da família ao serviço
    if request.method == 'POST':
        familia_id = request.POST.get('familia_id')
        nome = request.POST.get('nome')
        
        familia, criado = auxiliares_service.processar_salvar_familia(familia_id, nome)
        
        if criado:
            messages.success(request, f"Família '{nome}' cadastrada!")
        else:
            messages.success(request, f"Família '{nome}' updated successfully!")
            
    return redirect('tela_familias')


def excluir_familia(request, id):
    # Envia o ID para o serviço excluir a família e exibe a mensagem de sucesso
    nome_excluido = auxiliares_service.processar_excluir_familia(id)
    messages.success(request, f"Família '{nome_excluido}' excluída!")
    return redirect('tela_familias')
