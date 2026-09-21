from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
# Importando a tabela de Lojas que criamos no passo anterior
from inventario.models.configuracoes import LojaFilial 
from inventario.models import ConfiguracaoEmissor

def tela_painel_dev(request):
    # 🚀 SEGURANÇA MÁXIMA: Só o DEV entra aqui.
    if request.session.get('perfil_usuario') != 'DEV':
        messages.error(request, "⚠️ Acesso Negado: Área de sistema restrita a Desenvolvedores.")
        return redirect('painel_principal')
        
    lojas = LojaFilial.objects.all().order_by('id')
    return render(request, 'inventario/painel_dev.html', {'lojas': lojas})

def salvar_loja(request):
    if request.method == 'POST':
        # Trava dupla de segurança no POST
        if request.session.get('perfil_usuario') != 'DEV':
            return redirect('painel_principal')
            
        loja_id = request.POST.get('loja_id')
        nome = request.POST.get('nome', '').strip()
        codigo_ibge = request.POST.get('codigo_ibge', '').strip()
        
        try:
            if loja_id:
                loja = get_object_or_404(LojaFilial, id=loja_id)
                loja.nome = nome
                loja.codigo_ibge = codigo_ibge
                loja.save()
                messages.success(request, f"Loja '{nome}' atualizada com sucesso!")
            else:
                LojaFilial.objects.create(nome=nome, codigo_ibge=codigo_ibge)
                messages.success(request, f"Nova filial '{nome}' cadastrada! O robô já pode buscar os feriados pelo IBGE {codigo_ibge}.")
        except Exception as e:
            messages.error(request, f"Erro ao salvar loja: {str(e)}")
            
    return redirect('tela_painel_dev')

def excluir_loja(request, loja_id):
    if request.session.get('perfil_usuario') != 'DEV':
        return redirect('painel_principal')
        
    try:
        loja = get_object_or_404(LojaFilial, id=loja_id)
        nome = loja.nome
        loja.delete()
        messages.success(request, f"Loja '{nome}' e todos os seus vínculos de feriados foram removidos do sistema.")
    except Exception as e:
        messages.error(request, f"Erro ao excluir loja: {str(e)}")
        
    return redirect('tela_painel_dev')

def salvar_ambientes_dev(request):
    if request.method == 'POST':
        ambiente_nfe = request.POST.get('ambiente_nfe', 'homologacao')
        ambiente_nfce = request.POST.get('ambiente_nfce', 'homologacao')
        
        # Puxa o cofre atual ou cria um se não existir
        emissor = ConfiguracaoEmissor.objects.first()
        if not emissor:
            emissor = ConfiguracaoEmissor()
            
        emissor.ambiente_nfe = ambiente_nfe
        emissor.ambiente_nfce = ambiente_nfce
        emissor.save()
        
        messages.success(request, f"Ambientes fiscais atualizados! NF-e: {ambiente_nfe.upper()} | NFC-e: {ambiente_nfce.upper()}")
        
    # Redireciona de volta para o painel de desenvolvedor
    return redirect('tela_painel_dev')
