import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from inventario.models import Vendas, Produtos, Usuarios
from datetime import datetime, timedelta
from django.http import JsonResponse
from inventario.models.banco_rh import PontoEletronico
import traceback



# ==========================================
# 📊 RELATÓRIOS E CANCELAMENTOS
# ==========================================

def tela_relatorios(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    queryset = Vendas.objects.all().order_by('-id')
    vendedores = Usuarios.objects.all()

    filtro_vendedor = request.GET.get('vendedor', '')
    filtro_status = request.GET.get('status', '')

    if filtro_vendedor and filtro_vendedor.strip():
        queryset = queryset.filter(vendedor__icontains=filtro_vendedor.strip())
    
    if filtro_status and filtro_status.strip():
        queryset = queryset.filter(status=filtro_status.strip())

    # Cálculos Dinâmicos
    faturamento = queryset.filter(status='VENDA').aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    qtd_vendas = queryset.filter(status='VENDA').count()
    qtd_orcamentos = queryset.filter(status='ORCAMENTO').count()
    ticket_medio = (faturamento / qtd_vendas) if qtd_vendas > 0 else 0

    return render(request, 'inventario/relatorios.html', {
        'vendas': queryset,
        'vendedores': vendedores,
        'faturamento': faturamento,
        'qtd_vendas': qtd_vendas,
        'qtd_orcamentos': qtd_orcamentos,
        'ticket_medio': ticket_medio,
        'filtro_vendedor': filtro_vendedor,
        'filtro_status': filtro_status
    })

def imprimir_cupom(request, id=None):
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')
    
    venda = get_object_or_404(Vendas, id=id)
    itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    return render(request, 'inventario/cupom.html', {'venda': venda, 'itens': itens})

def imprimir_cupom_a4(request, id=None):
    if not id or not str(id).isdigit():
        messages.error(request, "ID de venda inválido.")
        return redirect('tela_relatorios')

    venda = get_object_or_404(Vendas, id=id)
    itens = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    return render(request, 'inventario/cupom_a4.html', {'venda': venda, 'itens': itens})

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

def tela_relatorio_ponto(request):
    """Renderiza a tela com o Modal de Bloqueio inicial"""
    if 'usuario_logado' not in request.session:
        return redirect('login')
    
    # Passamos a lista de utilizadores para preencher o select,
    # mas o acesso será validado via JavaScript após colocar a senha.
    colaboradores = Usuarios.objects.all().order_by('login')
    return render(request, 'inventario/relatorio_ponto.html', {'colaboradores': colaboradores})

def calcular_minutos_escala(escala_json, dia_semana_str):
    """Lê a escala em JSON e devolve os minutos esperados para um dia específico"""
    if not escala_json:
        return 0
        
    # PROTEÇÃO: Garante que a escala é um dicionário e não um texto preso do SQLite
    if isinstance(escala_json, str):
        try:
            escala_json = json.loads(escala_json.replace("'", '"'))
        except:
            return 0

    if dia_semana_str not in escala_json:
        return 0
    
    dados_dia = escala_json[dia_semana_str]
    if dados_dia.get('folga'):
        return 0
        
    try:
        ent = datetime.strptime(dados_dia['ent'], '%H:%M')
        sai = datetime.strptime(dados_dia['sai'], '%H:%M')
        alm = datetime.strptime(dados_dia['alm'], '%H:%M') if dados_dia['alm'] else datetime.strptime('00:00', '%H:%M')
        
        minutos_trabalho = (sai - ent).total_seconds() / 60
        minutos_almoco = (alm.hour * 60) + alm.minute
        
        return minutos_trabalho - minutos_almoco
    except:
        return 0
    
    
def gerar_pdf_ponto(request):
    # Aqui você pegaria os mesmos filtros (colaborador, data_ini, data_fim) 
    # e renderizaria o template acima
    contexto = {
        # ... carregar os mesmos dados da api_dados_ponto ...
    }
    return render(request, 'inventario/relatorio_ponto_pdf.html', contexto)

def api_dados_ponto(request):
    """Recebe as datas e a senha, valida o perfil e calcula o saldo"""
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            login = dados.get('login')
            senha = dados.get('senha')
            colab_alvo = dados.get('colaborador')
            data_ini = dados.get('data_ini')
            data_fim = dados.get('data_fim')
            
            # 1. Validação de Senha
            usuario_req = Usuarios.objects.filter(login__exact=login, senha__exact=senha).first()
            if not usuario_req:
                return JsonResponse({'erro': 'Senha incorreta ou utilizador não encontrado.'}, status=401)
                
            # 2. Regra de Negócio (Vendedor vs Gerente)
            if usuario_req.perfil != 'Administrador' and usuario_req.login != colab_alvo:
                return JsonResponse({'erro': 'Acesso Negado: Vendedores apenas podem ver o próprio ponto.'}, status=403)
                
            # 3. Busca de Dados
            colaborador = Usuarios.objects.filter(login=colab_alvo).first()
            if not colaborador:
                return JsonResponse({'erro': 'Colaborador alvo não encontrado.'}, status=404)
                
            # CORREÇÃO AQUI: Adicionado .using('rh_db') para procurar no banco isolado correto
            pontos = PontoEletronico.objects.using('rh_db').filter(
                colaborador_login=colab_alvo,
                data__range=[data_ini, data_fim]
            ).order_by('data')
            
            resultado = []
            saldo_total_minutos = 0
            
            dias_map = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'}
            
            for p in pontos:
                minutos_trab = 0
                
                # Try-Catch por linha, para que um dia defeituoso não quebre a tabela inteira
                try:
                    if p.entrada_1 and p.saida_1:
                        # SQLite em multi-db pode retornar como texto. Esta linha protege a conversão!
                        e1 = datetime.strptime(p.entrada_1, '%H:%M:%S').time() if isinstance(p.entrada_1, str) else p.entrada_1
                        s1 = datetime.strptime(p.saida_1, '%H:%M:%S').time() if isinstance(p.saida_1, str) else p.saida_1
                        t1 = datetime.combine(p.data, s1) - datetime.combine(p.data, e1)
                        minutos_trab += t1.total_seconds() / 60
                        
                    if p.entrada_2 and p.saida_2:
                        e2 = datetime.strptime(p.entrada_2, '%H:%M:%S').time() if isinstance(p.entrada_2, str) else p.entrada_2
                        s2 = datetime.strptime(p.saida_2, '%H:%M:%S').time() if isinstance(p.saida_2, str) else p.saida_2
                        t2 = datetime.combine(p.data, s2) - datetime.combine(p.data, e2)
                        minutos_trab += t2.total_seconds() / 60
                except Exception as loop_err:
                    print("Erro no loop de datas: ", loop_err)
                    pass
                    
                dia_str = dias_map[p.data.weekday()]
                minutos_esperados = calcular_minutos_escala(colaborador.escala_semanal, dia_str)
                
                saldo_dia = minutos_trab - minutos_esperados
                saldo_total_minutos += saldo_dia
                def format_time(t):
                    if not t: return '--:--'
                    if isinstance(t, str): return t[:5]
                    return t.strftime('%H:%M')
                
                resultado.append({
                    'data': p.data.strftime('%d/%m/%Y') if hasattr(p.data, 'strftime') else p.data,
                    'e1': format_time(p.entrada_1),
                    's1': format_time(p.saida_1),
                    'e2': format_time(p.entrada_2),
                    's2': format_time(p.saida_2),
                    'saldo': round(saldo_dia)
                })
                
            return JsonResponse({
                'sucesso': True,
                'pontos': resultado,
                'saldo_total': round(saldo_total_minutos),
                'nome': colaborador.login.upper()
            })
            
        except Exception as e:
            # ESCUDO DE PROTEÇÃO! Se algo explodir, devolvemos o erro visível em vez de HTML
            erro_str = traceback.format_exc()
            print(erro_str) # Guarda no log do terminal/Railway
            return JsonResponse({'erro': f'Erro Interno (Python): {str(e)}'}, status=500)
        
                
