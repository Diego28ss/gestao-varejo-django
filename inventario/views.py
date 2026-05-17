# ==============================================================================
# MOTOR DO SISTEMA - LÓGICA DE NEGÓCIO E TELAS
# Projeto Integrador - UNIVESP | JB Tintas
# Desenvolvedor: Diego Santana dos Santos
# ==============================================================================
import json
from django.shortcuts import render, redirect
from django.db.models import Q, Sum
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction

from .models import Produtos, Clientes, Usuarios, Vendas, Marca, Familia, ConfiguracaoPontos
from .forms import ProdutoForm, ClienteForm, VendaForm, MarcaForm, FamiliaForm


# ==============================================================================
# SEGURANÇA E ACESSO
# ==============================================================================
def login_view(request):
    if request.method == 'POST':
        usuario_digitado = request.POST.get('login')
        senha_digitada = request.POST.get('senha')
        usuario = Usuarios.objects.filter(login=usuario_digitado, senha=senha_digitada).first()
        if usuario:
            request.session['usuario_logado'] = usuario.login
            request.session['perfil_usuario'] = usuario.perfil
            return redirect('painel_principal')
        else:
            messages.error(request, 'Login ou senha incorretos.')
    return render(request, 'inventario/login.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')


def painel_principal(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/index.html')


# ==============================================================================
# GERÊNCIA (MARCAS, FAMÍLIAS E PONTOS)
# ==============================================================================
def tela_gerencia_auxiliares(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    contexto = {
        'marcas': Marca.objects.all().order_by('nome'),
        'familias': Familia.objects.all().order_by('nome'),
    }
    return render(request, 'inventario/gerencia_auxiliares.html', contexto)


def salvar_marca(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip().upper()
        if nome:
            Marca.objects.get_or_create(nome=nome)
            messages.success(request, f"Marca '{nome}' cadastrada com sucesso!")
    return redirect('tela_gerencia_auxiliares')


def salvar_familia(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip().upper()
        if nome:
            Familia.objects.get_or_create(nome=nome)
            messages.success(request, f"Família '{nome}' cadastrada com sucesso!")
    return redirect('tela_gerencia_auxiliares')


# NOVO MENU: Tela isolada só para manutenção de pontos (Passo 2.3)
def tela_manutencao_pontos(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    conf_cliente, _ = ConfiguracaoPontos.objects.get_or_create(tipo_usuario='CLIENTE',
                                                               defaults={'pontos_necessarios_resgate': 30})
    conf_pintor, _ = ConfiguracaoPontos.objects.get_or_create(tipo_usuario='PINTOR',
                                                              defaults={'pontos_necessarios_resgate': 30})

    return render(request, 'inventario/manutencao_pontos.html', {
        'conf_cliente': conf_cliente, 'conf_pintor': conf_pintor
    })


def salvar_configuracao_pontos(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.method == 'POST':
        tipo = request.POST.get('tipo_usuario')
        pontos_resgate = request.POST.get('pontos_necessarios_resgate')
        if pontos_resgate:
            conf = ConfiguracaoPontos.objects.get(tipo_usuario=tipo)
            conf.pontos_necessarios_resgate = int(pontos_resgate)
            conf.save()
            messages.success(request, f"Regra de pontos para {tipo} atualizada!")
    return redirect('tela_manutencao_pontos')


# ==============================================================================
# FRENTE DE CAIXA (PDV)
# ==============================================================================
def tela_pdv(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    contexto = {
        'clientes': Clientes.objects.all().order_by('nome'),
        'vendedores': Usuarios.objects.all().order_by('login'),
        'pintores': Clientes.objects.filter(Q(tipo='PINTOR') | Q(tipo='CLIENTE E PINTOR')).order_by('nome')
    }
    return render(request, 'inventario/pdv.html', contexto)


def api_buscar_produtos(request):
    termo = request.GET.get('q', '').strip()

    # Passo 1.4: FILTRO INTELIGENTE - Mostra apenas ATIVOS no Caixa
    produtos = Produtos.objects.filter(status='ATIVO')

    if termo:
        for palavra in termo.split():
            produtos = produtos.filter(
                Q(nome__icontains=palavra) |
                Q(cod_barras__icontains=palavra) |
                Q(marca__nome__icontains=palavra)
            )

    lista = [{'id': p.id, 'cod_barras': p.cod_barras, 'nome': p.nome, 'preco': float(p.preco_venda),
              'estoque': p.estoque_atual} for p in produtos[:15]]
    return JsonResponse({'produtos': lista})


# Passo 3.1: API que consulta os pontos e calcula o valor em dinheiro silenciosamente
def api_consultar_pontos(request):
    nome_cliente = request.GET.get('cliente', '')
    if not nome_cliente: return JsonResponse({'pontos': 0, 'valor_reais': 0.0})

    cliente = Clientes.objects.filter(nome=nome_cliente).first()
    if not cliente or cliente.pontos <= 0:
        return JsonResponse({'pontos': 0, 'valor_reais': 0.0})

    # Puxa a regra definida pelo gerente
    tipo_regra = 'PINTOR' if 'PINTOR' in cliente.tipo else 'CLIENTE'
    conf = ConfiguracaoPontos.objects.filter(tipo_usuario=tipo_regra).first()

    if not conf or conf.pontos_necessarios_resgate <= 0:
        return JsonResponse({'pontos': cliente.pontos, 'valor_reais': 0.0})

    # Faz a matemática de conversão
    blocos = cliente.pontos // conf.pontos_necessarios_resgate
    valor_em_reais = float(blocos * float(conf.valor_resgate_reais))
    pontos_utilizaveis = blocos * conf.pontos_necessarios_resgate

    return JsonResponse({
        'pontos_totais': cliente.pontos,
        'pontos_utilizaveis': pontos_utilizaveis,
        'valor_reais': valor_em_reais
    })


@transaction.atomic
def api_salvar_venda(request):
    if request.method == 'POST':
        dados = json.loads(request.body)
        status_venda = dados.get('status', 'VENDA')
        pontos_resgatados = int(dados.get('pontos_resgatados', 0))  # Captura pontos gastos

        dados_venda = {
            'valor_total': dados.get('valor_final'),
            'valor_desconto': dados.get('desconto'),
            'vendedor': dados.get('vendedor'),
            'cliente': dados.get('cliente'),
            'indicante': dados.get('indicante'),
            'status': status_venda,
            'cupom_texto': json.dumps(dados.get('carrinho', []))
        }

        form = VendaForm(dados_venda)
        if form.is_valid():
            nova_venda = form.save()

            if status_venda == 'VENDA':
                # Baixa de estoque
                for item in dados.get('carrinho', []):
                    prod = Produtos.objects.get(id=item['id'])
                    prod.estoque_atual -= int(item['qtd'])
                    prod.save()

                nome_cliente = dados.get('cliente')
                nome_indicante = dados.get('indicante')

                # Passo 3.3: DÉBITO - Abater pontos utilizados como desconto
                if pontos_resgatados > 0 and nome_cliente:
                    cliente_obj = Clientes.objects.filter(nome=nome_cliente).first()
                    if cliente_obj and cliente_obj.pontos >= pontos_resgatados:
                        cliente_obj.pontos -= pontos_resgatados
                        cliente_obj.save()

                # CRÉDITO - Acumular pontos da nova compra
                valor_final_compra = float(dados.get('valor_final', 0))
                pontos_ganhos = int(valor_final_compra)

                if nome_cliente and nome_cliente.strip() != "":
                    cliente_obj = Clientes.objects.filter(nome=nome_cliente).first()
                    if cliente_obj:
                        cliente_obj.pontos += pontos_ganhos
                        cliente_obj.save()

                if nome_indicante and nome_indicante.strip() != "":
                    indicante_obj = Clientes.objects.filter(nome=nome_indicante).first()
                    if indicante_obj:
                        indicante_obj.pontos += pontos_ganhos
                        indicante_obj.save()

            return JsonResponse({'status': 'sucesso', 'venda_id': nova_venda.id})
        else:
            return JsonResponse({'status': 'erro', 'mensagem': 'Erro de validação nos dados.'})


# ==============================================================================
# ESTOQUE E PRODUTOS
# ==============================================================================
def tela_estoque_produtos(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    termo = request.GET.get('q', '').strip()
    marcas = Marca.objects.all().order_by('nome')
    familias = Familia.objects.all().order_by('nome')
    produtos = Produtos.objects.all().order_by('nome')

    if termo:
        for p in termo.split():
            produtos = produtos.filter(Q(nome__icontains=p) | Q(cod_barras__icontains=p) | Q(marca__nome__icontains=p))

    contexto = {'produtos': produtos[:100], 'query': termo, 'marcas_dropdown': marcas, 'familias_dropdown': familias}
    return render(request, 'inventario/estoque_produtos.html', contexto)


def salvar_produto(request):
    if request.method == 'POST':
        p_id = request.POST.get('produto_id')
        dados = request.POST.copy()

        dados['preco_custo'] = dados.get('preco_custo', '0').replace(',', '.')
        dados['margem_lucro'] = dados.get('margem_lucro', '0').replace(',', '.')
        dados['preco_venda'] = dados.get('preco_venda', '0').replace(',', '.')
        dados['nome'] = dados.get('nome', '').upper()

        # Passo 1.3: VALIDAÇÃO ESTRITA DE ESTOQUE
        estoque_digitado = str(dados.get('estoque_atual', '')).strip()
        unidade_digitada = str(dados.get('unidade', '')).strip()

        if not estoque_digitado:
            messages.error(request, "❌ ERRO: O campo 'Estoque Inicial/Atual' é OBRIGATÓRIO!")
            return redirect('tela_estoque_produtos')
        if not unidade_digitada:
            messages.error(request, "❌ ERRO: O campo 'Unidade' é OBRIGATÓRIO!")
            return redirect('tela_estoque_produtos')

        if p_id:
            instancia = Produtos.objects.get(id=p_id)
            form = ProdutoForm(dados, instance=instancia)
        else:
            form = ProdutoForm(dados)

        if form.is_valid():
            form.save()
            messages.success(request, 'Produto salvo com sucesso!')
        else:
            for campo, erros in form.errors.items():
                for erro in erros: messages.error(request, f"Erro ({campo}): {erro}")

    return redirect('tela_estoque_produtos')


# ==============================================================================
# ENTRADA DE CARGA (BIPADOR)
# ==============================================================================
def tela_entrada_carga(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/entrada_carga.html')


def api_produto_por_codigo(request):
    p = Produtos.objects.filter(cod_barras=request.GET.get('codigo', '')).first()
    if p:
        return JsonResponse(
            {'status': 'ok', 'id': p.id, 'nome': p.nome, 'preco': float(p.preco_venda), 'estoque': p.estoque_atual})
    return JsonResponse({'status': 'erro'})


@transaction.atomic
def api_efetivar_entrada(request):
    dados = json.loads(request.body)
    for item in dados.get('itens', []):
        p = Produtos.objects.get(id=item['id'])
        p.estoque_atual += int(item['qtd'])
        p.save()
    return JsonResponse({'status': 'sucesso'})


# ==============================================================================
# GESTÃO DE CLIENTES (CADASTRO, CONSULTA)
# ==============================================================================
def tela_cadastro(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.method == 'POST':
        telefone_digitado = request.POST.get('telefone', '').strip()
        cpf_digitado = request.POST.get('cpf', '').strip()

        # Passo 1.2: BLINDAGEM CONTRA DUPLICIDADE
        if telefone_digitado and Clientes.objects.filter(telefone=telefone_digitado).exists():
            messages.error(request, '❌ ERRO: Já existe um cliente cadastrado com este TELEFONE!')
            return render(request, 'inventario/cadastro.html')

        if cpf_digitado and Clientes.objects.filter(cpf=cpf_digitado).exists():
            messages.error(request, '❌ ERRO: Já existe um cliente cadastrado com este CPF!')
            return render(request, 'inventario/cadastro.html')

        tipo = "CLIENTE"
        if request.POST.get('check_cliente') and request.POST.get('check_pintor'):
            tipo = "CLIENTE E PINTOR"
        elif request.POST.get('check_pintor'):
            tipo = "PINTOR"

        rua, num, cep = request.POST.get('rua', ''), request.POST.get('numero', ''), request.POST.get('cep', '')
        endereco = f"{rua}, Nº {num} - CEP: {cep}" if rua else ""

        dados_cliente = request.POST.copy()
        dados_cliente['tipo'] = tipo
        dados_cliente['endereco'] = endereco
        dados_cliente['nome'] = dados_cliente.get('nome', '').upper()
        dados_cliente['pontos'] = 0

        form = ClienteForm(dados_cliente)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cliente cadastrado com sucesso!')
            return redirect('tela_cadastro')
        else:
            for campo, erros in form.errors.items():
                for erro in erros: messages.error(request, erro)

    return render(request, 'inventario/cadastro.html')


def tela_consultar_clientes(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    termo = request.GET.get('q', '').strip()
    clientes = Clientes.objects.all().order_by('nome')
    if termo:
        clientes = clientes.filter(Q(nome__icontains=termo) | Q(telefone__icontains=termo) | Q(cpf__icontains=termo))

    # Puxa regras de pontos para exibir cálculos na tela de consulta (Passo 2.2)
    conf_cliente = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()
    conf_pintor = ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()

    return render(request, 'inventario/consultar_clientes.html', {
        'clientes': clientes, 'query': termo, 'conf_cliente': conf_cliente, 'conf_pintor': conf_pintor
    })


def salvar_edicao_cliente(request):
    if request.method == 'POST':
        c_id = request.POST.get('cliente_id')
        cliente = Clientes.objects.get(id=c_id)
        telefone_digitado = request.POST.get('telefone', '').strip()
        cpf_digitado = request.POST.get('cpf', '').strip()

        # Blindagem na Edição (Ignora a si mesmo)
        if telefone_digitado and Clientes.objects.exclude(id=c_id).filter(telefone=telefone_digitado).exists():
            messages.error(request, '❌ ERRO: Já existe OUTRO cliente com este TELEFONE!')
            return redirect('tela_consultar_clientes')

        if cpf_digitado and Clientes.objects.exclude(id=c_id).filter(cpf=cpf_digitado).exists():
            messages.error(request, '❌ ERRO: Já existe OUTRO cliente com este CPF!')
            return redirect('tela_consultar_clientes')

        tipo = "CLIENTE"
        if request.POST.get('check_cliente') and request.POST.get('check_pintor'):
            tipo = "CLIENTE E PINTOR"
        elif request.POST.get('check_pintor'):
            tipo = "PINTOR"

        rua, num, cep = request.POST.get('rua', ''), request.POST.get('numero', ''), request.POST.get('cep', '')
        endereco = f"{rua}, Nº {num} - CEP: {cep}" if rua else cliente.endereco

        dados_cliente = request.POST.copy()
        dados_cliente['tipo'] = tipo
        dados_cliente['endereco'] = endereco
        dados_cliente['nome'] = dados_cliente.get('nome', '').upper()
        dados_cliente['pontos'] = cliente.pontos

        form = ClienteForm(dados_cliente, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ficha atualizada com sucesso!')
        else:
            for campo, erros in form.errors.items():
                for erro in erros: messages.error(request, f"Erro: {erro}")

    return redirect('tela_consultar_clientes')


def excluir_cliente(request, cliente_id):
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.method == 'POST':
        try:
            cliente = Clientes.objects.get(id=cliente_id)
            nome_apagado = cliente.nome
            cliente.delete()
            messages.success(request, f'Cadastro de {nome_apagado} excluído com sucesso!')
        except Exception as e:
            messages.error(request, f'Não foi possível excluir. Erro: {e}')
    return redirect('tela_consultar_clientes')


def api_historico_cliente(request):
    nome_cliente = request.GET.get('nome', '')
    vendas = Vendas.objects.filter(cliente=nome_cliente).order_by('-data_venda')
    lista = [{'id': v.id, 'data': v.data_venda.strftime('%d/%m/%Y %H:%M'), 'valor': float(v.valor_total),
              'vendedor': v.vendedor} for v in vendas]
    return JsonResponse({'historico': lista})


# ==============================================================================
# RELATÓRIOS E RH
# ==============================================================================
def tela_relatorios(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    vendedor_filtro = request.GET.get('vendedor', '')
    status_filtro = request.GET.get('status', '')

    movimentacoes = Vendas.objects.all().order_by('-data_venda')
    if vendedor_filtro: movimentacoes = movimentacoes.filter(vendedor=vendedor_filtro)
    if status_filtro: movimentacoes = movimentacoes.filter(status=status_filtro)

    vendas_reais = movimentacoes.filter(status='VENDA')
    orcamentos = movimentacoes.filter(status='ORCAMENTO')

    total_liq = vendas_reais.aggregate(s=Sum('valor_total'))['s'] or 0
    qtd_vendas = vendas_reais.count()
    qtd_orcamentos = orcamentos.count()

    contexto = {
        'vendas': movimentacoes[:100], 'vendedores': Usuarios.objects.all().order_by('login'),
        'filtros': {'vendedor': vendedor_filtro, 'status': status_filtro},
        'metricas': {'total_liquido': float(total_liq), 'qtd_vendas': qtd_vendas, 'qtd_orcamentos': qtd_orcamentos,
                     'ticket_medio': float(total_liq) / qtd_vendas if qtd_vendas > 0 else 0}
    }
    return render(request, 'inventario/relatorios.html', contexto)


def tela_colaboradores(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    equipe = []
    for u in Usuarios.objects.all():
        total_vendas = Vendas.objects.filter(vendedor=u.login, status='VENDA').aggregate(s=Sum('valor_total'))['s'] or 0
        valor_comissao = float(total_vendas) * (float(u.comissao or 0) / 100)
        equipe.append({'id': u.id, 'login': u.login, 'perfil': u.perfil, 'porcentagem': u.comissao or 0,
                       'total_vendido': total_vendas, 'valor_receber': valor_comissao})
    return render(request, 'inventario/colaboradores.html', {'equipe': equipe})


def salvar_colaborador(request):
    if request.method == 'POST':
        c_id = request.POST.get('colab_id')
        login = request.POST.get('login', '').upper()
        comis = float(request.POST.get('comissao', '0').replace(',', '.'))

        if c_id:
            u = Usuarios.objects.get(id=c_id)
            u.login = login
            u.comissao = comis
            u.perfil = request.POST.get('perfil')
            if request.POST.get('senha'): u.senha = request.POST.get('senha')
            u.save()
        else:
            Usuarios.objects.create(login=login, senha=request.POST.get('senha'), perfil=request.POST.get('perfil'),
                                    comissao=comis)
    return redirect('tela_colaboradores')


# ==============================================================================
# IMPRESSÃO DE DOCUMENTOS
# ==============================================================================
def imprimir_cupom(request, venda_id):
    venda = Vendas.objects.get(id=venda_id)
    try:
        itens = json.loads(venda.cupom_texto)
        for item in itens: item['total_linha'] = float(item['preco']) * int(item['qtd'])
    except:
        itens = []
    contexto = {'venda': venda, 'itens': itens, 'cliente': Clientes.objects.filter(nome=venda.cliente).first(),
                'subtotal_bruto': float(venda.valor_total) + float(venda.valor_desconto)}
    return render(request, 'inventario/cupom.html', contexto)


def imprimir_cupom_a4(request, venda_id):
    venda = Vendas.objects.get(id=venda_id)
    try:
        itens = json.loads(venda.cupom_texto)
        for item in itens: item['total_linha'] = float(item['preco']) * int(item['qtd'])
    except:
        itens = []
    contexto = {'venda': venda, 'itens': itens, 'cliente': Clientes.objects.filter(nome=venda.cliente).first(),
                'subtotal_bruto': float(venda.valor_total) + float(venda.valor_desconto)}
    return render(request, 'inventario/cupom_a4.html', contexto)