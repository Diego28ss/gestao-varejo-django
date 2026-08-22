import json
import traceback
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

from inventario.models import Vendas, Produtos, Usuarios
from inventario.models.configuracoes import ConfiguracaoEmissor
from inventario.models.banco_rh import PontoEletronico

# ==========================================
# 📊 RELATÓRIOS E CANCELAMENTOS
# ==========================================

def tela_relatorios(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    queryset = Vendas.objects.all().order_by('-id')
    vendedores = Usuarios.objects.all()

    # Recebe os filtros da tela
    filtro_vendedor = request.GET.get('vendedor', '')
    filtro_status = request.GET.get('status', '')
    filtro_mes = request.GET.get('mes', '')

    # Aplica o filtro de vendedor
    if filtro_vendedor and filtro_vendedor.strip():
        queryset = queryset.filter(vendedor__icontains=filtro_vendedor.strip())
    
    # Aplica o filtro de status
    if filtro_status and filtro_status.strip():
        queryset = queryset.filter(status=filtro_status.strip())

    # Aplica o NOVO filtro de mês (baseado na data de venda)
    if filtro_mes and filtro_mes.isdigit():
        queryset = queryset.filter(data_venda__month=int(filtro_mes))

    # Cálculos Dinâmicos
    faturamento = queryset.filter(status='VENDA').aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    qtd_vendas = queryset.filter(status='VENDA').count()
    qtd_orcamentos = queryset.filter(status='ORCAMENTO').count()
    ticket_medio = (faturamento / qtd_vendas) if qtd_vendas > 0 else 0

    # Lista de meses para o menu suspenso no HTML
    lista_meses = [
        {'valor': 1, 'nome': 'Janeiro'}, {'valor': 2, 'nome': 'Fevereiro'},
        {'valor': 3, 'nome': 'Março'}, {'valor': 4, 'nome': 'Abril'},
        {'valor': 5, 'nome': 'Maio'}, {'valor': 6, 'nome': 'Junho'},
        {'valor': 7, 'nome': 'Julho'}, {'valor': 8, 'nome': 'Agosto'},
        {'valor': 9, 'nome': 'Setembro'}, {'valor': 10, 'nome': 'Outubro'},
        {'valor': 11, 'nome': 'Novembro'}, {'valor': 12, 'nome': 'Dezembro'}
    ]

    return render(request, 'inventario/relatorios.html', {
        'vendas': queryset,
        'vendedores': vendedores,
        'faturamento': faturamento,
        'qtd_vendas': qtd_vendas,
        'qtd_orcamentos': qtd_orcamentos,
        'ticket_medio': ticket_medio,
        'filtro_vendedor': filtro_vendedor,
        'filtro_status': filtro_status,
        'filtro_mes': filtro_mes,
        'lista_meses': lista_meses
    })


def imprimir_cupom(request, id=None):
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')
    
    venda = get_object_or_404(Vendas, id=id)
    itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    
    # Busca os dados da loja
    loja = ConfiguracaoEmissor.objects.first()
    
    return render(request, 'inventario/cupom.html', {'venda': venda, 'itens': itens, 'loja': loja})


def imprimir_cupom_a4(request, id=None):
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')

    venda = get_object_or_404(Vendas, id=id)
    itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    
    # Busca os dados da loja
    loja = ConfiguracaoEmissor.objects.first()
    
    return render(request, 'inventario/cupom_a4.html', {'venda': venda, 'itens': itens, 'loja': loja})


def cancelar_venda(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    if request.method == 'POST':
        venda_id = request.POST.get('venda_id')
        motivo = request.POST.get('motivo')

        if not venda_id or not str(venda_id).isdigit():
            messages.error(request, "ID de venda inválido.")
            return redirect('tela_relatorios')

        venda = get_object_or_404(Vendas, id=venda_id)

        if venda.status == 'CANCELADA':
            messages.warning(request, f"A venda #{venda_id} já está cancelada.")
            return redirect('tela_relatorios')

        venda.status = 'CANCELADA'
        venda.save()

        # Estorno de Estoque
        try:
            itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
            for item in itens:
                produto_id = item.get('id')
                if produto_id and str(produto_id).isdigit():
                    produto = Produtos.objects.filter(id=int(produto_id)).first()
                    if produto:
                        produto.estoque_atual += int(item.get('qtd', 0))
                        produto.save()
            messages.success(request, f"Venda #{venda_id} cancelada com sucesso.")
        except Exception as e:
            messages.error(request, f"Erro ao estornar estoque: {str(e)}")
        
    return redirect('tela_relatorios')

# ==========================================
# ⏰ RELATÓRIOS DE PONTO ELETRÔNICO (RH)
# ==========================================

def tela_relatorio_ponto(request):
    """Renderiza a tela de relatórios com filtro baseado no Cargo do usuário"""
    if 'usuario_logado' not in request.session:
        return redirect('login')
    
    usuario_logado = request.session.get('usuario_logado')
    perfil = request.session.get('perfil_usuario', '').upper()
    
    # Regra Inteligente: Gerentes/Supervisores veem todos, Vendedor vê apenas a si mesmo
    if perfil in ['GERENTE', 'SUPERVISOR', 'ADMINISTRADOR']:
        colaboradores = Usuarios.objects.all().order_by('login')
    else:
        colaboradores = Usuarios.objects.filter(login=usuario_logado)
        
    return render(request, 'inventario/relatorio_ponto.html', {'colaboradores': colaboradores})

def formatar_minutos_para_hhmmss(minutos_float):
    """Transforma um número de minutos (ex: 90.5) em string HH:MM:SS com sinal"""
    if not minutos_float:
        return "00:00:00"
    
    sinal = "-" if minutos_float < 0 else "+" if minutos_float > 0 else ""
    
    min_abs = abs(minutos_float)
    h = int(min_abs // 60)
    m = int(min_abs % 60)
    s = int(round((min_abs * 60) % 60))
    
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        h += 1
        
    return f"{sinal}{h:02d}:{m:02d}:{s:02d}"

def calcular_minutos_escala(escala_json, dia_semana_str):
    """Lê a escala em JSON e devolve os minutos esperados para um dia específico."""
    PADRAO_DIAS_UTEIS = 438 

    if not escala_json:
        return PADRAO_DIAS_UTEIS if dia_semana_str in ['seg', 'ter', 'qua', 'qui', 'sex'] else 0
          
    if isinstance(escala_json, str):
        try:
            escala_json = json.loads(escala_json.replace("'", '"'))
        except:
            return PADRAO_DIAS_UTEIS if dia_semana_str in ['seg', 'ter', 'qua', 'qui', 'sex'] else 0

    if dia_semana_str not in escala_json:
        return PADRAO_DIAS_UTEIS if dia_semana_str in ['seg', 'ter', 'qua', 'qui', 'sex'] else 0
        
    dados_dia = escala_json[dia_semana_str]
    if dados_dia.get('folga'):
        return 0
        
    try:
        ent_str = dados_dia.get('ent') or dados_dia.get('entrada') or '08:00'
        sai_str = dados_dia.get('sai') or dados_dia.get('saida') or '16:30'
        alm_str = dados_dia.get('alm') or dados_dia.get('almoco') or '01:12'
        
        ent = datetime.strptime(ent_str, '%H:%M')
        sai = datetime.strptime(sai_str, '%H:%M')
        alm = datetime.strptime(alm_str, '%H:%M') if alm_str else datetime.strptime('00:00', '%H:%M')
            
        minutos_trabalho = (sai - ent).total_seconds() / 60
        minutos_almoco = (alm.hour * 60) + alm.minute
            
        return max(0, minutos_trabalho - minutos_almoco)
    except:
        return PADRAO_DIAS_UTEIS if dia_semana_str in ['seg', 'ter', 'qua', 'qui', 'sex'] else 0
    
def gerar_dados_calendario_ponto(colaborador, data_ini, data_fim):
    """Função Helper: Constrói o calendário real dia a dia para identificar faltas e folgas"""
    data_inicio = datetime.strptime(data_ini, '%Y-%m-%d').date()
    data_final = datetime.strptime(data_fim, '%Y-%m-%d').date()
    delta = data_final - data_inicio
    lista_datas = [data_inicio + timedelta(days=i) for i in range(delta.days + 1)]
    
    pontos_bd = PontoEletronico.objects.using('rh_db').filter(
        colaborador_login=colaborador.login,
        data__range=[data_ini, data_fim]
    )
    
    pontos_dict = {}
    for p in pontos_bd:
        if isinstance(p.data, str):
            pontos_dict[p.data] = p
        else:
            pontos_dict[p.data.strftime('%Y-%m-%d')] = p

    resultado = []
    saldo_total_minutos = 0
    dias_map = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'}
    hoje = timezone.localtime().date()

    def format_time(t):
        if not t: return '--:--'
        if isinstance(t, str): return t[:5]
        return t.strftime('%H:%M')

    for dia_atual in lista_datas:
        dia_str_key = dia_atual.strftime('%Y-%m-%d')
        p = pontos_dict.get(dia_str_key)
        
        dia_semana_str = dias_map[dia_atual.weekday()]
        minutos_esperados = calcular_minutos_escala(colaborador.escala_semanal, dia_semana_str)
        minutos_trab = 0
        
        # Se for um dia no futuro, não debita horas e mostra vazio
        if dia_atual > hoje:
            resultado.append({
                'data': dia_atual.strftime('%d/%m/%Y'),
                'e1': '--:--',
                's1': '--:--',
                'e2': '--:--',
                's2': '--:--',
                'saldo': 0,
                'saldo_fmt': '00:00:00'
            })
            continue
        
        if p:
            try:
                if p.entrada_1 and p.saida_1:
                    e1 = datetime.strptime(p.entrada_1, '%H:%M:%S').time() if isinstance(p.entrada_1, str) else p.entrada_1
                    s1 = datetime.strptime(p.saida_1, '%H:%M:%S').time() if isinstance(p.saida_1, str) else p.saida_1
                    t1 = datetime.combine(dia_atual, s1) - datetime.combine(dia_atual, e1)
                    minutos_trab += t1.total_seconds() / 60
                    
                if p.entrada_2 and p.saida_2:
                    e2 = datetime.strptime(p.entrada_2, '%H:%M:%S').time() if isinstance(p.entrada_2, str) else p.entrada_2
                    s2 = datetime.strptime(p.saida_2, '%H:%M:%S').time() if isinstance(p.saida_2, str) else p.saida_2
                    t2 = datetime.combine(dia_atual, s2) - datetime.combine(dia_atual, e2)
                    minutos_trab += t2.total_seconds() / 60
            except Exception:
                pass
            
            saldo_dia = minutos_trab - minutos_esperados
            saldo_total_minutos += saldo_dia
            
            resultado.append({
                'data': dia_atual.strftime('%d/%m/%Y'),
                'e1': format_time(p.entrada_1),
                's1': format_time(p.saida_1),
                'e2': format_time(p.entrada_2),
                's2': format_time(p.saida_2),
                'saldo': round(saldo_dia),
                'saldo_fmt': formatar_minutos_para_hhmmss(saldo_dia)
            })
        else:
            # O colaborador não tem ponto. É folga ou falta?
            saldo_dia = 0 - minutos_esperados
            saldo_total_minutos += saldo_dia
            
            if minutos_esperados > 0:
                resultado.append({
                    'data': dia_atual.strftime('%d/%m/%Y'),
                    'e1': 'FALTA',
                    's1': '--:--',
                    'e2': '--:--',
                    's2': '--:--',
                    'saldo': round(saldo_dia),
                    'saldo_fmt': formatar_minutos_para_hhmmss(saldo_dia)
                })
            else:
                resultado.append({
                    'data': dia_atual.strftime('%d/%m/%Y'),
                    'e1': 'FOLGA',
                    's1': '--:--',
                    'e2': '--:--',
                    's2': '--:--',
                    'saldo': 0,
                    'saldo_fmt': '00:00:00'
                })
                
    return resultado, round(saldo_total_minutos)


def gerar_pdf_ponto(request):
    """Gera a folha A4 oficial baseada no usuário da sessão"""
    if 'usuario_logado' not in request.session:
        return HttpResponse("Usuário não logado.", status=401)

    if request.method == 'POST':
        colab_alvo = request.POST.get('colaborador')
        data_ini = request.POST.get('data_ini')
        data_fim = request.POST.get('data_fim')

        usuario_logado = request.session.get('usuario_logado')
        perfil = request.session.get('perfil_usuario', '').upper()

        if perfil not in ['GERENTE', 'SUPERVISOR', 'ADMINISTRADOR'] and usuario_logado != colab_alvo:
            return HttpResponse("Acesso Negado: Vendedores apenas podem imprimir o próprio ponto.", status=403)

        colaborador = Usuarios.objects.filter(login=colab_alvo).first()
        if not colaborador:
            return HttpResponse("Erro: Colaborador não encontrado.", status=404)
        
        resultado, saldo_total_minutos = gerar_dados_calendario_ponto(colaborador, data_ini, data_fim)

        data_ini_br = datetime.strptime(data_ini, '%Y-%m-%d').strftime('%d/%m/%Y')
        data_fim_br = datetime.strptime(data_fim, '%Y-%m-%d').strftime('%d/%m/%Y')

        contexto = {
            'colab_nome': colaborador.login.upper(),
            'data_ini': data_ini_br,
            'data_fim': data_fim_br,
            'pontos': resultado,
            'saldo_total': saldo_total_minutos,
            'saldo_total_fmt': formatar_minutos_para_hhmmss(saldo_total_minutos)
        }
        return render(request, 'inventario/relatorio_ponto_pdf.html', contexto)
    
    return HttpResponse("Método não permitido.", status=405)
    

def api_dados_ponto(request):
    """Calcula o saldo visual para a tela baseado no usuário da sessão"""
    if 'usuario_logado' not in request.session:
        return JsonResponse({'erro': 'Usuário não logado.'}, status=401)

    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            colab_alvo = dados.get('colaborador')
            data_ini = dados.get('data_ini')
            data_fim = dados.get('data_fim')
            
            usuario_logado = request.session.get('usuario_logado')
            perfil = request.session.get('perfil_usuario', '').upper()

            if perfil not in ['GERENTE', 'SUPERVISOR', 'ADMINISTRADOR'] and usuario_logado != colab_alvo:
                return JsonResponse({'erro': 'Acesso Negado: Vendedores apenas podem ver o próprio ponto.'}, status=403)
            
            colaborador = Usuarios.objects.filter(login=colab_alvo).first()
            if not colaborador:
                return JsonResponse({'erro': 'Colaborador alvo não encontrado.'}, status=404)
                    
            resultado, saldo_total_minutos = gerar_dados_calendario_ponto(colaborador, data_ini, data_fim)
                
            return JsonResponse({
                'sucesso': True,
                'pontos': resultado,
                'saldo_total': saldo_total_minutos,
                'saldo_total_fmt': formatar_minutos_para_hhmmss(saldo_total_minutos),
                'nome': colaborador.login.upper()
            })
            
        except Exception as e:
            erro_str = traceback.format_exc()
            print(erro_str)
            return JsonResponse({'erro': f'Erro Interno (Python): {str(e)}'}, status=500)
        