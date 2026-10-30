from django.shortcuts import render, redirect
from django.contrib import messages
from inventario.models import ConfiguracaoPontos

# ==========================================
# REGRAS DE FIDELIDADE (PONTUAÇÃO)
# ==========================================

def tela_manutencao_pontos(request):
    """ Função que renderiza o HTML da tela de regras """
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
    """ Função que processa o formulário e salva no banco de dados """
    if request.method == 'POST':
        from inventario.models import ConfiguracaoPontos
        
        acumulo_cliente = request.POST.get('acumulo_cliente', 1)
        acumulo_pintor = request.POST.get('acumulo_pintor', 1)
        
        # 🚀 TRAVA DE SEGURANÇA: O divisor é engessado em 100, transformando pontos em %.
        resgate_universal = 100

        # Salva a regra do CLIENTE
        conf_cli, _ = ConfiguracaoPontos.objects.get_or_create(tipo_usuario='CLIENTE')
        conf_cli.pontos_por_real = acumulo_cliente
        conf_cli.pontos_necessarios_resgate = resgate_universal
        conf_cli.valor_resgate_reais = 1.00
        conf_cli.save()

        # Salva a regra do PINTOR
        conf_pin, _ = ConfiguracaoPontos.objects.get_or_create(tipo_usuario='PINTOR')
        conf_pin.pontos_por_real = acumulo_pintor
        conf_pin.pontos_necessarios_resgate = resgate_universal 
        conf_pin.valor_resgate_reais = 1.00
        conf_pin.save()

        messages.success(request, "Regras de Fidelidade atualizadas com sucesso!")
        
    return redirect('tela_manutencao_pontos')

