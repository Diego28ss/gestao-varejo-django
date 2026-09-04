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
        
        acumulo_cliente = request.POST.get('acumulo_cliente', 1)
        acumulo_pintor = request.POST.get('acumulo_pintor', 1)
        resgate_universal = request.POST.get('resgate_universal', 50)

        # 🚀 Salva a regra do CLIENTE (Ele guarda o seu próprio acúmulo e a MOEDA UNIVERSAL)
        conf_cli, _ = ConfiguracaoPontos.objects.get_or_create(tipo_usuario='CLIENTE')
        conf_cli.pontos_por_real = acumulo_cliente
        conf_cli.pontos_necessarios_resgate = resgate_universal
        conf_cli.valor_resgate_reais = 1.00
        conf_cli.save()

        # 🚀 Salva a regra do PINTOR (Ele só guarda a sua própria taxa de acúmulo, mas herda a Moeda Universal)
        conf_pin, _ = ConfiguracaoPontos.objects.get_or_create(tipo_usuario='PINTOR')
        conf_pin.pontos_por_real = acumulo_pintor
        conf_pin.pontos_necessarios_resgate = resgate_universal 
        conf_pin.valor_resgate_reais = 1.00
        conf_pin.save()

        messages.success(request, "Regras de Fidelidade atualizadas com sucesso!")
        
    return redirect('tela_manutencao_pontos')
