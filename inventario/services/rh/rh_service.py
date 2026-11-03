import json
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum
from inventario.models import Usuarios, Vendas
from inventario.models.configuracoes import LojaFilial, FeriadoLocal
from inventario.models.banco_rh import PontoEletronico, JustificativaPonto

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
        # Busca todas as vendas faturadas/finalizadas do mês
        vendas_mes = Vendas.objects.filter(
            vendedor=colab.login, 
            status__in=['FATURADO', 'VENDA'],
            data_venda__month=agora.month, 
            data_venda__year=agora.year
        )
        
        total_bruto = 0.00
        comissao_exata_mes = 0.00
        
        # 🚀 LÓGICA FINANCEIRA - FASE 7
        # Calcula a comissão venda a venda, sobre o VALOR LÍQUIDO, com a % travada na hora da venda
        for v in vendas_mes:
            valor_bruto_venda = float(v.valor_total) or 0.00
            total_bruto += valor_bruto_venda
            
            desc_comum = float(v.desconto_comum) if getattr(v, 'desconto_comum', None) else 0.00
            desc_pontos = float(v.desconto_pontos) if getattr(v, 'desconto_pontos', None) else 0.00
            perc_comissao = float(v.percentual_comissao) if getattr(v, 'percentual_comissao', None) else 0.00
            
            valor_liquido = valor_bruto_venda - desc_comum - desc_pontos
            if valor_liquido < 0: valor_liquido = 0
            
            comissao_exata_mes += valor_liquido * (perc_comissao / 100)
        
        colab.total_vendido = round(total_bruto, 2)
        colab.comissao_a_pagar = round(comissao_exata_mes, 2)
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
# MOTOR DE RELATÓRIOS E HORAS
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

    justificativas_bd = JustificativaPonto.objects.using('rh_db').filter(
        colaborador_login=colaborador.login, 
        data_inicial__lte=data_fim
    )
    
    mapa_auditoria = {}
    mapa_ferias = set()
    mapa_faltas_justificadas = {} 
    mapa_abono = {} 
    
    for just in justificativas_bd:
        if just.tipo == 'FERIAS' and just.data_final:
            inicio = max(just.data_inicial, d_ini)
            fim = min(just.data_final, d_fim)
            dias_ferias = [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]
            for d in dias_ferias:
                mapa_ferias.add(d.strftime('%Y-%m-%d'))
                
        elif just.tipo == 'FALTA':
            inicio = max(just.data_inicial, d_ini)
            fim = min(just.data_final or just.data_inicial, d_fim)
            dias_falta = [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]
            for d in dias_falta:
                mapa_faltas_justificadas[d.strftime('%Y-%m-%d')] = {'is_atestado': just.possui_atestado}

        elif just.tipo == 'ABONO' and just.data_inicial >= d_ini and just.data_inicial <= d_fim:
            dia_str = just.data_inicial.strftime('%Y-%m-%d')
            minutos_abonados = 0
            if just.hora_nova and just.hora_final:
                h_ini = datetime.combine(just.data_inicial, just.hora_nova)
                h_fim = datetime.combine(just.data_inicial, just.hora_final)
                minutos_abonados = (h_fim - h_ini).total_seconds() / 60
                
            mapa_abono[dia_str] = {'minutos': minutos_abonados}
            mapa_auditoria[dia_str] = {
                'has_ajuste': True,
                'auditoria_gerente': just.gerente_autorizador,
                'auditoria_motivo': just.motivo,
                'auditoria_original': f"Abono Parcial: {just.hora_nova.strftime('%H:%M')} às {just.hora_final.strftime('%H:%M')}" if (just.hora_nova and just.hora_final) else "Abono Parcial Aplicado"
            }
            
        elif just.tipo == 'AJUSTE' and just.data_inicial >= d_ini and just.data_inicial <= d_fim:
            dia_str = just.data_inicial.strftime('%Y-%m-%d')
            mapa_auditoria[dia_str] = {
                'has_ajuste': True,
                'auditoria_gerente': just.gerente_autorizador,
                'auditoria_motivo': just.motivo,
                'auditoria_original': "Visualizar batida original no sistema legado"
            }

    resultado, saldo_total = [], 0
    dias_map = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'}
    hoje = timezone.localtime().date()

    def format_time(t): return '--:--' if not t else (t[:5] if isinstance(t, str) else t.strftime('%H:%M'))

    for dia_atual in lista_datas:
        dia_str = dia_atual.strftime('%Y-%m-%d')
        p, feriado = pontos_dict.get(dia_str), mapa_feriados.get(dia_str)
        
        eh_ferias = dia_str in mapa_ferias
        eh_falta_justificada = dia_str in mapa_faltas_justificadas
        eh_abono = dia_str in mapa_abono
        
        min_esperados = 0 if (feriado or eh_ferias or eh_falta_justificada) else calcular_minutos_escala(colaborador.escala_semanal, dias_map[dia_atual.weekday()])
        min_trab = 0
        
        if dia_atual > hoje:
            resultado.append({'data': dia_atual.strftime('%d/%m/%Y'), 'e1': '--:--', 's1': '--:--', 'e2': '--:--', 's2': '--:--', 'saldo': 0, 'saldo_fmt': '00:00:00'})
            continue
        
        audit_info = mapa_auditoria.get(dia_str, {'has_ajuste': False})
        
        if p and not eh_ferias and not eh_falta_justificada:
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
            
            if eh_abono and saldo_dia < 0:
                credito = mapa_abono[dia_str]['minutos']
                saldo_dia += credito
                if saldo_dia > 0: saldo_dia = 0
                
            saldo_total += saldo_dia
            
            dados_dia = {
                'data': dia_atual.strftime('%d/%m/%Y'), 'e1': format_time(p.entrada_1), 's1': format_time(p.saida_1),
                'e2': format_time(p.entrada_2), 's2': format_time(p.saida_2),
                'saldo': round(saldo_dia), 'saldo_fmt': formatar_minutos_para_hhmmss(saldo_dia)
            }
            dados_dia.update(audit_info)
            resultado.append(dados_dia)
            
        else:
            saldo_dia = 0 - min_esperados
            saldo_total += saldo_dia
            
            linha_vazia = {
                'data': dia_atual.strftime('%d/%m/%Y'), 'e1': '--:--', 's1': '--:--', 'e2': '--:--', 's2': '--:--', 
                'saldo': round(saldo_dia), 'saldo_fmt': formatar_minutos_para_hhmmss(saldo_dia)
            }
            linha_vazia.update(audit_info)
            
            if feriado:
                linha_vazia.update({'e1': 'FERIADO', 'saldo': 0, 'saldo_fmt': '00:00:00', 'nota': feriado.nome})
            elif eh_ferias:
                linha_vazia.update({'e1': 'FÉRIAS', 'saldo': 0, 'saldo_fmt': '00:00:00'})
            elif eh_falta_justificada:
                texto_falta = 'ATESTADO' if mapa_faltas_justificadas[dia_str]['is_atestado'] else 'FALTA JUSTIFICADA'
                linha_vazia.update({'e1': texto_falta, 'saldo': 0, 'saldo_fmt': '00:00:00'})
            elif min_esperados > 0:
                linha_vazia.update({'e1': 'FALTA'})
            else:
                linha_vazia.update({'e1': 'FOLGA', 'saldo': 0, 'saldo_fmt': '00:00:00'})
                
            resultado.append(linha_vazia)
                
    return resultado, round(saldo_total), formatar_minutos_para_hhmmss(saldo_total)


def registrar_justificativa_ponto(dados):
    gerente_login = dados.get('auth_gerente_login')
    gerente_senha = dados.get('auth_gerente_senha')
    colab_login = dados.get('auth_colab_login')
    colab_senha = dados.get('auth_colab_senha')
    tipo_acao = dados.get('tipo_justificativa')

    if not tipo_acao:
        raise ValueError("O tipo de ação é obrigatório.")
    
    if tipo_acao in ['AJUSTE', 'ABONO']:
        gerente = Usuarios.objects.filter(login=gerente_login, senha=gerente_senha).first()
        if not gerente or gerente.perfil not in ['Gerente', 'Supervisor', 'Administrador', 'DEV']:
            raise ValueError("Falha na assinatura: Credenciais de gerente inválidas ou sem permissão.")
        
        colab = Usuarios.objects.filter(login=colab_login, senha=colab_senha).first()
        if not colab:
            raise ValueError("Falha na assinatura: Senha do colaborador incorreta.")

    data_inicial = dados.get('just_ferias_ini') if tipo_acao == 'FERIAS' else dados.get('data_alvo')
    
    if not data_inicial:
        raise ValueError("A data alvo da justificativa não foi informada.")

    just = JustificativaPonto(
        colaborador_login=colab_login,
        tipo=tipo_acao,
        data_inicial=datetime.strptime(data_inicial, '%Y-%m-%d').date(),
        gerente_autorizador=gerente_login
    )

    if tipo_acao == 'FERIAS':
        just.data_final = datetime.strptime(dados.get('just_ferias_fim'), '%Y-%m-%d').date()
        just.motivo = "Férias / Licença registrada no sistema"
    
    elif tipo_acao == 'FALTA':
        data_fim_alvo = dados.get('data_fim_alvo')
        if data_fim_alvo:
            just.data_final = datetime.strptime(data_fim_alvo, '%Y-%m-%d').date()
        else:
            just.data_final = just.data_inicial
            
        just.possui_atestado = dados.get('chk_atestado', False)
        just.motivo = dados.get('just_motivo', "Falta Justificada")
        
    elif tipo_acao == 'ABONO':
        h_ini_str = dados.get('just_abono_ini')
        h_fim_str = dados.get('just_abono_fim')
        if not h_ini_str or not h_fim_str:
            raise ValueError("Para o abono, as horas inicial e final são obrigatórias.")
            
        just.hora_nova = datetime.strptime(h_ini_str, '%H:%M').time()
        just.hora_final = datetime.strptime(h_fim_str, '%H:%M').time()
        just.motivo = dados.get('just_motivo', "Declaração de Horas")
        
    elif tipo_acao == 'AJUSTE':
        just.batida_ajustada = dados.get('just_ajuste_tipo')
        just.hora_nova = datetime.strptime(dados.get('just_ajuste_hora'), '%H:%M').time()
        just.motivo = dados.get('just_motivo', "Ajuste manual de relógio")
        
        ponto, created = PontoEletronico.objects.using('rh_db').get_or_create(
            colaborador_login=colab_login, data=just.data_inicial
        )
        if just.batida_ajustada == 'e1': ponto.entrada_1 = just.hora_nova
        elif just.batida_ajustada == 's1': ponto.saida_1 = just.hora_nova
        elif just.batida_ajustada == 'e2': ponto.entrada_2 = just.hora_nova
        elif just.batida_ajustada == 's2': ponto.saida_2 = just.hora_nova
        ponto.save(using='rh_db')

    just.save(using='rh_db')
    return "Auditoria registada com sucesso!"
