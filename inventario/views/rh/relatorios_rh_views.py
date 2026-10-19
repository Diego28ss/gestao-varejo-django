import json
import traceback
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from inventario.models import Usuarios
from inventario.services.rh import rh_service

def tela_relatorio_ponto(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    usuario_logado = request.session.get('usuario_logado')
    perfil = request.session.get('perfil_usuario', '').upper()
    
    if perfil in ['GERENTE', 'SUPERVISOR', 'ADMINISTRADOR']:
        colaboradores = Usuarios.objects.exclude(perfil='DEV').order_by('login')
    else:
        colaboradores = Usuarios.objects.filter(login=usuario_logado)
        
    return render(request, 'inventario/relatorio_ponto.html', {'colaboradores': colaboradores})

def api_dados_ponto(request):
    if 'usuario_logado' not in request.session: return JsonResponse({'erro': 'Usuário não logado.'}, status=401)

    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            colab_alvo, data_ini, data_fim = dados.get('colaborador'), dados.get('data_ini'), dados.get('data_fim')
            
            perfil = request.session.get('perfil_usuario', '').upper()
            if perfil not in ['GERENTE', 'SUPERVISOR', 'ADMINISTRADOR'] and request.session.get('usuario_logado') != colab_alvo:
                return JsonResponse({'erro': 'Acesso Negado: Vendedores apenas podem ver o próprio ponto.'}, status=403)
            
            colaborador = Usuarios.objects.filter(login=colab_alvo).first()
            if not colaborador: return JsonResponse({'erro': 'Colaborador não encontrado.'}, status=404)
                    
            resultado, saldo_minutos, saldo_fmt = rh_service.gerar_dados_calendario_ponto(colaborador, data_ini, data_fim)
                
            return JsonResponse({
                'sucesso': True, 'pontos': resultado, 'saldo_total': saldo_minutos,
                'saldo_total_fmt': saldo_fmt, 'nome': colaborador.login.upper()
            })
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({'erro': f'Erro Interno: {str(e)}'}, status=500)

def gerar_pdf_ponto(request):
    if 'usuario_logado' not in request.session: return HttpResponse("Usuário não logado.", status=401)

    if request.method == 'POST':
        colab_alvo = request.POST.get('colaborador')
        data_ini = request.POST.get('data_ini')
        data_fim = request.POST.get('data_fim')

        perfil = request.session.get('perfil_usuario', '').upper()
        if perfil not in ['GERENTE', 'SUPERVISOR', 'ADMINISTRADOR'] and request.session.get('usuario_logado') != colab_alvo:
            return HttpResponse("Acesso Negado: Apenas pode imprimir o próprio ponto.", status=403)

        colaborador = Usuarios.objects.filter(login=colab_alvo).first()
        if not colaborador: return HttpResponse("Erro: Colaborador não encontrado.", status=404)
        
        resultado, saldo_minutos, saldo_fmt = rh_service.gerar_dados_calendario_ponto(colaborador, data_ini, data_fim)

        return render(request, 'inventario/relatorio_ponto_pdf.html', {
            'colab_nome': colaborador.login.upper(),
            'data_ini': datetime.strptime(data_ini, '%Y-%m-%d').strftime('%d/%m/%Y'),
            'data_fim': datetime.strptime(data_fim, '%Y-%m-%d').strftime('%d/%m/%Y'),
            'pontos': resultado, 'saldo_total': saldo_minutos, 'saldo_total_fmt': saldo_fmt
        })
    return HttpResponse("Método não permitido.", status=405)
