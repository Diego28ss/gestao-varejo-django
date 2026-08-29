from django.shortcuts import render, redirect
from django.contrib import messages
from inventario.models import ConfiguracaoPontos

# ==========================================
# REGRAS DE FIDELIDADE (PONTUAÇÃO)
# ==========================================
def tela_manutencao_pontos(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
        
    # 🚀 TRAVA: Apenas Gerente
    if request.session.get('perfil_usuario') != 'Gerente':
        messages.error(request, "Acesso restrito exclusivamente ao cargo Gerente.")
        return redirect('painel_principal')
        
    return render(request, 'inventario/manutencao_pontos.html', {
        'conf_cliente': ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first(),
        'conf_pintor': ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()
    })

def salvar_configuracao_pontos(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
        
    # 🚀 TRAVA: Apenas Gerente
    if request.session.get('perfil_usuario') != 'Gerente':
        messages.error(request, "Acesso restrito exclusivamente ao cargo Gerente.")
        return redirect('painel_principal')
        
    if request.method == 'POST':
        tipo = request.POST.get('tipo_usuario')
        pontos_raw = request.POST.get('pontos_necessarios_resgate', '1')
        try:
            pontos = int(pontos_raw) if pontos_raw.strip() != "" else 1
        except ValueError:
            pontos = 1
            
        config, created = ConfiguracaoPontos.objects.get_or_create(tipo_usuario=tipo)
        config.pontos_necessarios_resgate = pontos
        config.valor_resgate_reais = 1.00
        config.save()
        messages.success(request, f"Regras de pontuação para {tipo.lower()} salvas com sucesso!")
        
    return redirect('tela_manutencao_pontos')
