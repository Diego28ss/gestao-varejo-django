import json
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum
from inventario.models import Usuarios, Vendas
from inventario.models.configuracoes import LojaFilial, FeriadoLocal
from inventario.models.banco_rh import PontoEletronico

# ==========================================
# GESTÃO DA EQUIPE E BATIDA DE PONTO
# ==========================================
def obter_lista_equipe(perfil, login_usuario):
    if perfil == 'DEV':
        lista = Usuarios.objects.all().order_by('login')
    elif perfil in ['Gerente', 'Supervisor', 'Administrador']:
        lista = Usuarios.objects.exclude(perfil='DEV').order_by('login')
    else:
        lista = Usuarios.objects.filter(login=login_usuario)
        
    agora = timezone.now()
    for colab in lista:
        vendas = Vendas.objects.filter(
            vendedor=colab.login, status='VENDA',
            data_venda__month=agora.month, data_venda__year=agora.year
        ).aggregate(total_vendido=Sum('valor_total'), comissao_total=Sum('valor_comissao'))
        
        colab.total_vendido = vendas['total_vendido'] or 0.00
        colab.comissao_a_pagar = vendas['comissao_total'] or 0.00
        colab.escala_json_str = json.dumps(colab.escala_semanal) if colab.escala_semanal else "{}"
        
    lojas = LojaFilial.objects.all().order_by('nome')
    return lista, lojas

def salvar_membro_equipe(dados, perfil_logado, login_logado):
    colaborador_id = dados.get('colaborador_id')
    login = dados.get('login', '').strip()
    senha_nova = dados.get('senha', '').strip()
    senha_conf = dados.get('senha_confirmacao', '').strip()
    perfil_post = dados.get('perfil', 'Vendedor')
    comissao = dados.get('comissao', '0.00').replace(',', '.')
    
    loja_id = dados.get('loja_id')
    loja_obj = LojaFilial.objects.filter(id=loja_id).first() if loja_id else None

    if perfil_post == 'DEV' and perfil_logado != 'DEV': raise ValueError("Segurança: Apenas o Desenvolvedor pode atribuir o cargo DEV.")
    if senha_nova and senha_nova != senha_conf: raise ValueError("As senhas não conferem.")
        
    try: escala_semanal = json.loads(dados.get('escala_json', '{}'))
    except: escala_semanal = {}

    if colaborador_id and str(colaborador_id).strip() and str(colaborador_id) != 'None':
        colab = Usuarios.objects.get(id=colaborador_id)
        if colab.perfil == 'DEV' and perfil_logado != 'DEV': raise ValueError("Acesso negado para editar a conta de Desenvolvedor.")
        if perfil_logado not in ['Gerente', 'DEV'] and login_logado != colab.login: raise ValueError("Você não tem permissão para editar outros usuários.")
        
        if perfil_logado in ['Gerente', 'DEV']:
            if Usuarios.objects.filter(login=login).exclude(id=colab.id).exists(): raise ValueError(f"O login '{login}' já está em uso.")
            colab.login = login
            colab.perfil = perfil_post
            colab.comissao = comissao
            colab.escala_semanal = escala_semanal
            colab.loja = loja_obj

        if senha_nova: colab.senha = senha_nova
        colab.save()
        return f"Colaborador '{colab.login}' atualizado!"
    else:
        if perfil_logado not in ['Gerente', 'DEV']: raise ValueError("Apenas Gerentes podem criar usuários.")
        colab_existente = Usuarios.objects.filter(login=login).first()
        if colab_existente:
            if senha_nova: colab_existente.senha = senha_nova
            colab_existente.perfil, colab_existente.comissao, colab_existente.escala_semanal, colab_existente.loja = perfil_post, comissao, escala_semanal, loja_obj
            colab_existente.save()
            return f"Colaborador '{login}' atualizado."
        else:
            Usuarios.objects.create(login=login, senha=senha_nova, perfil=perfil_post, comissao=comissao, escala_semanal=escala_semanal, loja=loja_obj)
            return f"Colaborador '{login}' cadastrado!"

def excluir_membro_equipe(colaborador_id, perfil_logado):
    if perfil_logado not in ['Gerente', 'DEV']: raise ValueError("Apenas Gerentes podem excluir usuários.")
    colab = Usuarios.objects.get(id=colaborador_id)
    if colab.perfil == 'DEV' and perfil_logado != 'DEV': raise ValueError("Ninguém pode excluir a conta de Desenvolvedor.")
    login = colab.login
    colab.delete()
    return login

def registrar_ponto(usuario_digitado, senha_digitada):
    user = Usuarios.objects.filter(login__exact=usuario_digitado, senha__exact=senha_digitada).first()
    if not user: raise ValueError("Utilizador ou senha incorretos.")
    if user.perfil == 'DEV': return "DEV", "O Perfil DEV não necessita de registro de ponto."

    agora = timezone.localtime()
    hora_atual = agora.time()
    ponto, _ = PontoEletronico.objects.get_or_create(colaborador_login=user.login, data=agora.date())

    if not ponto.entrada_1: ponto.entrada_1, msg = hora_atual, "Entrada"
    elif not ponto.saida_1: ponto.saida_1, msg = hora_atual, "Saída para almoço"
    elif not ponto.entrada_2: ponto.entrada_2, msg = hora_atual, "Retorno do almoço"
    elif not ponto.saida_2: ponto.saida_2, msg = hora_atual, "Fim de expediente"
    else: return "ESGOTADO", f"{user.login.upper()}, a sua jornada já foi concluída."

    ponto.save()
    return "SUCESSO", f"{msg} registada às {hora_atual.strftime('%H:%M')}!"

# ==========================================
# MOTOR DE RELATÓRIOS E HORAS (FASE 10)
# ==========================================
def formatar_minutos_para_hhmmss(minutos_float):
    if not minutos_float: return "00:00:00"
    sinal = "-" if minutos_float < 0 else "+" if minutos_float > 0 else ""
    min_abs = abs(minutos_float)
    h, m, s = int(min_abs // 60), int(min_abs % 60), int(round((min_abs * 60) % 60))
    if s == 60: s, m = 0, m + 1
    if m == 60: m, h = 0, h + 1
    return f"{sinal}{h:02d}:{m:02d}:{s:02d}"

def calcular_minutos_escala(escala_json, dia_semana_str):
    PADRAO = 438 
    if not escala_json: return PADRAO if dia_semana_str in ['seg', 'ter', 'qua', 'qui', 'sex'] else 0
    if isinstance(escala_json, str):
        try: escala_json = json.loads(escala_json.replace("'", '"'))
        except: return PADRAO if dia_semana_str in ['seg', 'ter', 'qua', 'qui', 'sex'] else 0

    if dia_semana_str not in escala_json: return PADRAO if dia_semana_str in ['seg', 'ter', 'qua', 'qui', 'sex'] else 0
    dados_dia = escala_json[dia_semana_str]
    if dados_dia.get('folga'): return 0
        
    try:
        ent = datetime.strptime(dados_dia.get('ent') or dados_dia.get('entrada') or '08:00', '%H:%M')
        sai = datetime.strptime(dados_dia.get('sai') or dados_dia.get('saida') or '16:30', '%H:%M')
        alm_str = dados_dia.get('alm') or dados_dia.get('almoco') or '01:12'
        alm = datetime.strptime(alm_str, '%H:%M') if alm_str else datetime.strptime('00:00', '%H:%M')
        return max(0, ((sai - ent).total_seconds() / 60) - ((alm.hour * 60) + alm.minute))
    except:
        return PADRAO if dia_semana_str in ['seg', 'ter', 'qua', 'qui', 'sex'] else 0

def sincronizar_feriados_api(loja):
    ano_atual = timezone.now().year
    try:
        response = requests.get(f"https://brasilapi.com.br/api/feriados/v1/{ano_atual}", timeout=5)
        if response.status_code == 200:
            for f in response.json():
                FeriadoLocal.objects.get_or_create(
                    loja=loja, data=datetime.strptime(f['date'], '%Y-%m-%d').date(), defaults={'nome': f['name'], 'tipo': 'Nacional'}
                )
            loja.ultima_busca_feriados = timezone.now().date()
            loja.save()
    except Exception:
        pass

def gerar_dados_calendario_ponto(colaborador, data_ini, data_fim):
    loja, mapa_feriados = colaborador.loja, {}
    if loja:
        if loja.precisa_atualizar_feriados(): sincronizar_feriados_api(loja)
        mapa_feriados = {f.data.strftime('%Y-%m-%d'): f for f in FeriadoLocal.objects.filter(loja=loja, data__range=[data_ini, data_fim])}

    d_ini, d_fim = datetime.strptime(data_ini, '%Y-%m-%d').date(), datetime.strptime(data_fim, '%Y-%m-%d').date()
    lista_datas = [d_ini + timedelta(days=i) for i in range((d_fim - d_ini).days + 1)]
    
    pontos_bd = PontoEletronico.objects.using('rh_db').filter(colaborador_login=colaborador.login, data__range=[data_ini, data_fim])
    pontos_dict = {p.data if isinstance(p.data, str) else p.data.strftime('%Y-%m-%d'): p for p in pontos_bd}

    resultado, saldo_total = [], 0
    dias_map = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'}
    hoje = timezone.localtime().date()

    def format_time(t): return '--:--' if not t else (t[:5] if isinstance(t, str) else t.strftime('%H:%M'))

    for dia_atual in lista_datas:
        dia_str = dia_atual.strftime('%Y-%m-%d')
        p, feriado = pontos_dict.get(dia_str), mapa_feriados.get(dia_str)
        min_esperados = 0 if feriado else calcular_minutos_escala(colaborador.escala_semanal, dias_map[dia_atual.weekday()])
        min_trab = 0
        
        if dia_atual > hoje:
            resultado.append({'data': dia_atual.strftime('%d/%m/%Y'), 'e1': '--:--', 's1': '--:--', 'e2': '--:--', 's2': '--:--', 'saldo': 0, 'saldo_fmt': '00:00:00'})
            continue
        
        if p:
            try:
                if p.entrada_1 and p.saida_1:
                    t1 = datetime.combine(dia_atual, datetime.strptime(p.saida_1, '%H:%M:%S').time() if isinstance(p.saida_1, str) else p.saida_1) - datetime.combine(dia_atual, datetime.strptime(p.entrada_1, '%H:%M:%S').time() if isinstance(p.entrada_1, str) else p.entrada_1)
                    min_trab += t1.total_seconds() / 60
                if p.entrada_2 and p.saida_2:
                    t2 = datetime.combine(dia_atual, datetime.strptime(p.saida_2, '%H:%M:%S').time() if isinstance(p.saida_2, str) else p.saida_2) - datetime.combine(dia_atual, datetime.strptime(p.entrada_2, '%H:%M:%S').time() if isinstance(p.entrada_2, str) else p.entrada_2)
                    min_trab += t2.total_seconds() / 60
            except: pass
            
            saldo_dia = min_trab - min_esperados
            if -10 <= saldo_dia <= 10: saldo_dia = 0 # Tolerância CLT
            saldo_total += saldo_dia
            
            resultado.append({
                'data': dia_atual.strftime('%d/%m/%Y'), 'e1': format_time(p.entrada_1), 's1': format_time(p.saida_1),
                'e2': format_time(p.entrada_2), 's2': format_time(p.saida_2),
                'saldo': round(saldo_dia), 'saldo_fmt': formatar_minutos_para_hhmmss(saldo_dia)
            })
        else:
            saldo_dia = 0 - min_esperados
            saldo_total += saldo_dia
            if feriado:
                resultado.append({'data': dia_atual.strftime('%d/%m/%Y'), 'e1': 'FERIADO', 's1': '--:--', 'e2': '--:--', 's2': '--:--', 'saldo': 0, 'saldo_fmt': '00:00:00', 'nota': feriado.nome})
            elif min_esperados > 0:
                resultado.append({'data': dia_atual.strftime('%d/%m/%Y'), 'e1': 'FALTA', 's1': '--:--', 'e2': '--:--', 's2': '--:--', 'saldo': round(saldo_dia), 'saldo_fmt': formatar_minutos_para_hhmmss(saldo_dia)})
            else:
                resultado.append({'data': dia_atual.strftime('%d/%m/%Y'), 'e1': 'FOLGA', 's1': '--:--', 'e2': '--:--', 's2': '--:--', 'saldo': 0, 'saldo_fmt': '00:00:00'})
                
    return resultado, round(saldo_total), formatar_minutos_para_hhmmss(saldo_total)
