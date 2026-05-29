from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from inventario.models import Vendas

# ==========================================
# PAINEL DE GERÊNCIA PRINCIPAL
# ==========================================
def tela_painel_gerencia(request):
    """
    Controla o acesso à tela centralizadora do Painel de Gerência.
    """
    if 'usuario_logado' not in request.session:
        return redirect('login')
    
    # ESTA É A LINHA QUE ESTAVA FALTANDO E CAUSOU O ERRO!
    return render(request, 'inventario/painel_gerencia.html')


# ==========================================
# TELA: FILA FISCAL
# ==========================================
def emitir_notas(request):
    """
    Tela dedicada para o faturamento fiscal.
    Lista apenas vendas finalizadas com cliente que estão aguardando emissão.
    """
    # Filtra as vendas na fila, da mais recente para a mais antiga
    vendas_pendentes = Vendas.objects.filter(
        status_fiscal='AGUARDANDO_EMISSAO'
    ).order_by('-data_venda')
    
    contexto = {
        'vendas_pendentes': vendas_pendentes
    }
    
    return render(request, 'inventario/emitir_notas.html', contexto)


# ==========================================
# API: COMUNICAÇÃO COM O ROBÔ LOCAL (BOTÕES)
# ==========================================
@csrf_exempt
def api_acionar_emissao(request):
    """
    Recebe o clique do botão no painel e muda o status da venda
    para que o Robô do SAT no computador da loja saiba que tem de agir.
    """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda_id = dados.get('venda_id')
            tipo_nota = dados.get('tipo_nota') # 'SAT' ou 'NFE'

            venda = Vendas.objects.get(id=venda_id)
            
            # Muda o status para avisar o robô local!
            if tipo_nota == 'SAT':
                venda.status_fiscal = 'PROCESSANDO_SAT'
            else:
                venda.status_fiscal = 'PROCESSANDO_NFE'
                
            venda.save()

            return JsonResponse({'sucesso': True, 'mensagem': f'Ordem de {tipo_nota} enviada para a loja!'})
        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': str(e)})
            
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido'})
# ==========================================
# API: A PORTA PARA O ROBÔ DA LOJA LER A FILA
# ==========================================
@csrf_exempt
def api_tarefas_robo(request):
    """
    O robô local (no Windows da loja) chama esta URL a cada 5 segundos.
    Retorna a venda mais antiga que o gerente clicou para emitir.
    """
    if request.method == 'GET':
        # Procura a primeira venda que está PROCESSANDO (SAT ou NFE)
        venda = Vendas.objects.filter(
            status_fiscal__in=['PROCESSANDO_SAT', 'PROCESSANDO_NFE']
        ).order_by('data_venda').first()
        
        if venda:
            tipo = 'SAT' if venda.status_fiscal == 'PROCESSANDO_SAT' else 'NFE'
            
            # Mais tarde vamos colocar aqui os produtos, 
            # para já vamos passar só o básico para o teste!
            dados = {
                'tem_tarefa': True,
                'venda_id': venda.id,
                'tipo_nota': tipo,
                'cliente': venda.cliente,
                'valor_total': str(venda.valor_total)
            }
            return JsonResponse(dados)
        else:
            return JsonResponse({'tem_tarefa': False})
        