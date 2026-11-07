import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from inventario.models import Produtos, Clientes, Usuarios
from inventario.services import fidelidade
from inventario.services.vendas.venda_service import VendaService
from inventario.services.vendas.pdv_service import PDVService
from inventario.models import Usuarios, ControleCaixa
from inventario.models import MovimentacaoCaixa
from django.db.models import Sum
from decimal import Decimal

from inventario.models.vendas import Vendas
from django.utils import timezone

def tela_pdv(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    usuario = Usuarios.objects.get(login=request.session['usuario_logado'])
    caixa_atual = ControleCaixa.objects.filter(operador=usuario, status__in=['ABERTO', 'FECHADO_TEMP']).first()
    
    if not caixa_atual: 
        return redirect('tela_painel_pdv')

    clientes = Clientes.objects.all()
    return render(request, 'inventario/pdv.html', {
        'produtos': Produtos.objects.exclude(status='INATIVO'),
        'vendedores': Usuarios.objects.exclude(perfil='DEV'),
        'vendedores_list': Usuarios.objects.exclude(perfil='DEV'),
        'clientes': clientes,
        'pintores': clientes.filter(tipo__icontains='PINTOR'),
        'caixa_atual': caixa_atual,
        'operador_atual': usuario.login
    })


def api_consultar_pontos(request):
    nome_cliente = request.GET.get('cliente', '')
    return JsonResponse(fidelidade.calcular_resgate_pontos(nome_cliente))

def api_buscar_produtos(request):
    query = request.GET.get('q', '').strip()
    try: offset = int(request.GET.get('offset', 0))
    except ValueError: offset = 0
    
    resultados, has_more = PDVService.buscar_produtos(query, offset)
    return JsonResponse({'produtos': resultados, 'has_more': has_more})

def api_salvar_venda(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            if dados.get('cpf_rapido'): dados['dest_cpf_cnpj'] = dados['cpf_rapido']
            venda_id = VendaService.registrar_checkout(dados)
            return JsonResponse({'status': 'sucesso', 'venda_id': venda_id})
        except ValueError as e: return JsonResponse({'status': 'erro', 'mensagem': str(e)})
        except Exception as e: return JsonResponse({'status': 'erro', 'mensagem': f"Erro interno no PDV: {str(e)}"})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_registrar_ruptura(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            PDVService.registrar_ruptura(dados.get('produto_id'), int(dados.get('quantidade_perdida', 1)))
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Ruptura registrada com sucesso.'})
        except Produtos.DoesNotExist: return JsonResponse({'status': 'erro', 'mensagem': 'Produto não encontrado na base.'})
        except Exception as e: return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_consultar_situacao_estoque(request, produto_id):
    try:
        return JsonResponse({'status': 'sucesso', **PDVService.consultar_situacao(produto_id)})
    except Produtos.DoesNotExist: return JsonResponse({'status': 'erro', 'mensagem': 'Produto não encontrado.'})
    except Exception as e: return JsonResponse({'status': 'erro', 'mensagem': str(e)})

def tela_painel_pdv(request):
    """ Renderiza o Lobby do PDV mostrando TODOS os caixas abertos no sistema """
    login_usuario = request.session.get('usuario_logado')
    if not login_usuario:
        return redirect('login')
        
    # Busca TODOS os caixas que estão em andamento ou pausados, independente de qual operador está usando o PC
    caixas_abertos = ControleCaixa.objects.filter(
        status__in=['ABERTO', 'FECHADO_TEMP']
    ).order_by('-data_hora_abertura')
    
    return render(request, 'inventario/painel_pdv.html', {'caixas_abertos': caixas_abertos})

def api_abrir_caixa(request):
    """ 
    Processa a abertura de um novo caixa verificando explicitamente as 
    credenciais digitadas no modal, independentemente da sessão atual. 
    """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            lastro = dados.get('lastro', 0.00)
            
            login_operador = dados.get('operador_login')
            senha_operador = dados.get('operador_senha')
            
            login_gerente = dados.get('gerente_login')
            senha_gerente = dados.get('gerente_senha')
            
            # 1. Validação explícita da Autenticação do Operador (O que foi digitado)
            try:
                operador = Usuarios.objects.get(login=login_operador, senha=senha_operador)
            except Usuarios.DoesNotExist:
                return JsonResponse({'status': 'erro', 'mensagem': 'Credenciais do Operador inválidas.'})
            
            # 2. Verifica se o Operador DIGITADO já tem um caixa (Ignora a sessão do navegador)
            if ControleCaixa.objects.filter(operador=operador, status__in=['ABERTO', 'FECHADO_TEMP']).exists():
                return JsonResponse({'status': 'erro', 'mensagem': f'O operador {operador.login} já possui um caixa em andamento.'})
            
            # 3. Validação explícita da Autenticação do Gerente
            try:
                gerente = Usuarios.objects.get(login=login_gerente, senha=senha_gerente)
                if gerente.perfil not in ['Gerente', 'Supervisor']:
                    return JsonResponse({'status': 'erro', 'mensagem': 'O usuário autorizador não possui perfil de Gerência.'})
            except Usuarios.DoesNotExist:
                return JsonResponse({'status': 'erro', 'mensagem': 'Credenciais do Gerente/Supervisor inválidas.'})
            
            # 4. Criação do caixa
            novo_caixa = ControleCaixa.objects.create(
                operador=operador,
                gerente_abertura=gerente,
                lastro_inicial=lastro,
                status='ABERTO'
            )
            
            # 5. ATUALIZA A SESSÃO: Substitui a sessão do navegador para o novo operador
            request.session['usuario_logado'] = operador.login
            request.session['perfil_usuario'] = operador.perfil
            
            return JsonResponse({'status': 'sucesso', 'caixa_id': novo_caixa.id})
            
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    
    return JsonResponse({'status': 'erro', 'mensagem': 'Método de requisição inválido.'})

def imprimir_comprovante_caixa(request, tipo, id_operacao):
    """ Renderiza o layout de impressão do cupom térmico e calcula os movimentos """
    contexto = {}
    
    if tipo == 'abertura':
        caixa = ControleCaixa.objects.get(id=id_operacao)
        contexto = {
            'tipo_comprovante': 'Abertura',
            'data_hora': caixa.data_hora_abertura.strftime("%d/%m/%Y %H:%M"),
            'caixa_id': caixa.id,
            'operador_nome': caixa.operador.login,
            'autorizador_nome': caixa.gerente_abertura.login,
            'valor': caixa.lastro_inicial
        }
    
    elif tipo == 'sangria':
        mov = MovimentacaoCaixa.objects.get(id=id_operacao)
        contexto = {
            'tipo_comprovante': 'Sangria',
            'data_hora': mov.data_hora.strftime("%d/%m/%Y %H:%M"),
            'caixa_id': mov.caixa.id,
            'operador_nome': mov.operador.login,
            'autorizador_nome': mov.gerente_autorizador.login,
            'valor': mov.valor,
            'motivo': mov.motivo
        }
        
    elif tipo == 'fechamento':
        caixa = ControleCaixa.objects.get(id=id_operacao)
        
        # 1. Recupera as Vendas Feitas Durante o Caixa Aberto
        vendas = Vendas.objects.filter(
            vendedor=caixa.operador.login, 
            data_venda__gte=caixa.data_hora_abertura,
            data_venda__lte=caixa.data_hora_fechamento
        )
        
        total_dinheiro_bruto = Decimal('0.00')
        total_credito = Decimal('0.00')
        total_debito = Decimal('0.00')
        total_pix = Decimal('0.00')
        total_trocos = Decimal('0.00')
        
        # 2. Processa o Histórico em Texto dos Pagamentos e os Trocos devolvidos
        for venda in vendas:
            total_trocos += Decimal(str(venda.troco))
            if venda.pagamentos_texto:
                # Carrega o JSON com a lista de pagamentos efetuados naquela compra
                pagamentos = json.loads(venda.pagamentos_texto)
                for p in pagamentos:
                    valor = Decimal(str(p.get('valor', 0)))
                    metodo = p.get('metodo', '')
                    
                    if metodo == 'DINHEIRO': total_dinheiro_bruto += valor
                    elif metodo == 'CARTAO_CREDITO': total_credito += valor
                    elif metodo == 'CARTAO_DEBITO': total_debito += valor
                    elif metodo == 'PIX': total_pix += valor
        
        # 3. Processa o Total das Retiradas de Sangria do mesmo período
        sangrias_resultado = MovimentacaoCaixa.objects.filter(
            caixa=caixa, tipo='SANGRIA'
        ).aggregate(total=Sum('valor'))
        
        total_sangria = Decimal(str(sangrias_resultado['total'] or 0.00))
        
        # 4. Cálculo Real em Gaveta: (Lastro) + (Dinheiro Bruto Entregue) - (Trocos Devolvidos) - (Dinheiro Retirado em Sangria)
        dinheiro_esperado = Decimal(str(caixa.lastro_inicial)) + total_dinheiro_bruto - total_trocos - total_sangria
        total_cartoes = total_credito + total_debito
        
        contexto = {
            'tipo_comprovante': 'Fechamento de Sistema',
            'data_hora': caixa.data_hora_fechamento.strftime("%d/%m/%Y %H:%M"),
            'caixa_id': caixa.id,
            'operador_nome': caixa.operador.login,
            'autorizador_nome': caixa.gerente_fechamento.login,
            
            # Resumo do Movimento
            'lastro': caixa.lastro_inicial,
            'total_sangrias': total_sangria,
            'trocos': total_trocos,
            
            # Formas de Pagamento
            'pix': total_pix,
            'credito': total_credito,
            'debito': total_debito,
            
            # Conclusão do Caixa
            'dinheiro_esperado': dinheiro_esperado,
            'cartao_total': total_cartoes
        }
        
    return render(request, 'inventario/cupom_caixa.html', contexto)


def api_fechar_caixa(request):
    """ Processa o fechamento validando o Operador e o Gerente (Sem declarar gaveta) """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            caixa_id = dados.get('caixa_id')
            tipo_fechamento = dados.get('tipo_fechamento')
            
            # Validação Dupla
            try:
                operador = Usuarios.objects.get(login=dados.get('operador_login'), senha=dados.get('operador_senha'))
            except Usuarios.DoesNotExist:
                return JsonResponse({'status': 'erro', 'mensagem': 'Senha do Operador incorreta.'})

            try:
                gerente = Usuarios.objects.get(login=dados.get('gerente_login'), senha=dados.get('gerente_senha'))
                if gerente.perfil not in ['Gerente', 'Supervisor']:
                    return JsonResponse({'status': 'erro', 'mensagem': 'Usuário sem permissão de Gerência.'})
            except Usuarios.DoesNotExist:
                return JsonResponse({'status': 'erro', 'mensagem': 'Credenciais do Gerente inválidas.'})
                
            caixa = ControleCaixa.objects.get(id=caixa_id)
            
            # Atualiza o Caixa (o cálculo dos valores será feito na view de impressão)
            caixa.status = tipo_fechamento
            caixa.gerente_fechamento = gerente
            caixa.data_hora_fechamento = timezone.now()
            # Deixa a declaração zerada pois agora o sistema assume a responsabilidade
            if tipo_fechamento == 'FECHADO':
                caixa.dinheiro_declarado = 0.00
                caixa.cartao_declarado = 0.00
                
            caixa.save()
            return JsonResponse({'status': 'sucesso', 'caixa_id': caixa.id, 'tipo': 'fechamento'})
            
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})


def api_sangria_caixa(request):
    """ Processa a retirada de dinheiro validando Operador e Gerente """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            caixa_id = dados.get('caixa_id')
            
            try:
                operador = Usuarios.objects.get(login=dados.get('operador_login'), senha=dados.get('operador_senha'))
            except Usuarios.DoesNotExist:
                return JsonResponse({'status': 'erro', 'mensagem': 'Senha do Operador incorreta.'})

            try:
                gerente = Usuarios.objects.get(login=dados.get('gerente_login'), senha=dados.get('gerente_senha'))
                if gerente.perfil not in ['Gerente', 'Supervisor']:
                    return JsonResponse({'status': 'erro', 'mensagem': 'Usuário sem permissão de Gerência.'})
            except Usuarios.DoesNotExist:
                return JsonResponse({'status': 'erro', 'mensagem': 'Credenciais do Gerente inválidas.'})

            caixa = ControleCaixa.objects.get(id=caixa_id)
            mov = MovimentacaoCaixa.objects.create(
                caixa=caixa,
                tipo='SANGRIA',
                valor=dados.get('valor'),
                motivo=dados.get('motivo'),
                operador=operador,
                gerente_autorizador=gerente
            )
            
            return JsonResponse({'status': 'sucesso', 'mov_id': mov.id, 'tipo': 'sangria'})
            
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_retomar_caixa(request):
    """ Valida a senha do operador para retomar a tela do PDV do Lobby """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            login_op = dados.get('operador_login')
            senha_op = dados.get('operador_senha')
            
            try:
                operador = Usuarios.objects.get(login=login_op, senha=senha_op)
                request.session['usuario_logado'] = operador.login
                request.session['perfil_usuario'] = operador.perfil
                return JsonResponse({'status': 'sucesso'})
            except Usuarios.DoesNotExist:
                return JsonResponse({'status': 'erro', 'mensagem': 'Senha do operador incorreta.'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

