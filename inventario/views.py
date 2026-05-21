import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from .models import Produtos, Clientes, Vendas, Familia, Marca, ConfiguracaoPontos, Usuarios
from . import services
from django.contrib import messages  # Certifique-se de que o import de mensagens existe no topo do arquivo
from django.shortcuts import render, redirect
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

# ==========================================
# 🔐 AUTENTICAÇÃO (LOGIN / LOGOUT)
# ==========================================

def tela_login(request):
    # Proteção: Se o usuário já estiver logado, manda direto para o painel principal
    if 'usuario_logado' in request.session:
        return redirect('painel_principal')

    if request.method == 'POST':
        login_input = request.POST.get('login', '').strip()
        senha_input = request.POST.get('senha', '').strip()

        try:
            # Busca o colaborador no banco de dados
            colaborador = Usuarios.objects.filter(login=login_input, senha=senha_input).first()

            if colaborador:
                # Registra as credenciais na sessão com segurança
                request.session['usuario_logado'] = colaborador.login
                request.session['perfil_usuario'] = colaborador.perfil

                messages.success(request, f"Bem-vindo de volta, {colaborador.login}!")
                return redirect('painel_principal')
            else:
                messages.error(request, "Usuário ou senha incorretos.")

        except Exception as e:
            print(f"Erro crítico no login: {e}")
            messages.error(request, "Ocorreu um erro interno ao tentar realizar o login. Tente novamente.")

    return render(request, 'inventario/login.html')


def logout(request):
    # Limpa toda a sessão do usuário com segurança
    request.session.flush()
    # Manda de volta para a tela de login
    return redirect('login')



# ==========================================
# 📊 PAINEL PRINCIPAL
# ==========================================

def painel_principal(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    return render(request, 'inventario/index.html')


# ==========================================
# 🛒 FRENTE DE CAIXA (PDV)
# ==========================================

def tela_pdv(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    produtos = Produtos.objects.exclude(status='INATIVO')
    vendedores = Usuarios.objects.all()
    clientes = Clientes.objects.all()

    context = {
        'produtos': produtos,
        'vendedores': vendedores,
        'vendedores_list': vendedores,
        'clientes': clientes,
        'pintores': clientes.filter(tipo__icontains='PINTOR'),
    }
    return render(request, 'inventario/pdv.html', context)


def api_consultar_pontos(request):
    nome_cliente = request.GET.get('cliente', '')
    resultado = services.calcular_resgate_pontos(nome_cliente)
    return JsonResponse(resultado)


def api_buscar_produtos(request):
    query = request.GET.get('q', '').strip()
    produtos = Produtos.objects.exclude(status='INATIVO')

    if query:
        palavras = query.split()
        for palavra in palavras:
            produtos = produtos.filter(
                Q(nome__icontains=palavra) |
                Q(cod_barras__icontains=palavra)
            )

    produtos = produtos[:50]
    resultados = []
    for p in produtos:
        resultados.append({
            'id': p.id,
            'nome': p.nome,
            'preco_venda': float(p.preco_venda),
            'estoque_atual': p.estoque_atual,
            'cod_barras': p.cod_barras or ''
        })
    return JsonResponse({'produtos': resultados})


def api_salvar_venda(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            status_venda = dados.get('status', 'VENDA')
            pontos_resgatados = int(dados.get('pontos_resgatados', 0))
            carrinho = dados.get('carrinho', [])

            dados_venda = {
                'valor_total': dados.get('valor_final'),
                'valor_desconto': dados.get('desconto'),
                'vendedor': dados.get('vendedor'),
                'cliente': dados.get('cliente'),
                'indicante': dados.get('indicante'),
                'status': status_venda,
                'cupom_texto': json.dumps(carrinho)
            }

            venda_id = services.processar_nova_venda(dados_venda, carrinho, status_venda, pontos_resgatados)
            return JsonResponse({'status': 'sucesso', 'venda_id': venda_id})

        except ValueError as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': 'Erro interno ao processar venda no servidor.'})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})


# ==========================================
# 📦 CONTROLE DE ESTOQUE E CARGAS
# ==========================================

def tela_estoque_produtos(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    query = request.GET.get('q', '')
    produtos = Produtos.objects.all()

    if query:
        produtos = produtos.filter(
            Q(nome__icontains=query) |
            Q(cod_barras__icontains=query) |
            Q(marca__nome__icontains=query) |
            Q(familia__nome__icontains=query)
        )

    marcas = Marca.objects.all().order_by('nome')
    familias = Familia.objects.all().order_by('nome')

    context = {
        'produtos': produtos,
        'query': query,
        'marcas': marcas,
        'marcas_list': marcas,
        'fabricantes': marcas,
        'familias': familias,
        'familias_list': familias,
        'grupos': familias,
    }
    return render(request, 'inventario/estoque_produtos.html', context)


def salvar_produto(request):
    if request.method == 'POST':
        produto_id = request.POST.get('produto_id')

        nome = request.POST.get('nome')
        cod_barras = request.POST.get('cod_barras', '')
        preco_custo = request.POST.get('preco_custo', '0').replace(',', '.')
        preco_venda = request.POST.get('preco_venda', '0').replace(',', '.')
        estoque_atual = request.POST.get('estoque_atual', 0)

        marca_id = request.POST.get('marca')
        familia_id = request.POST.get('familia')

        marca_obj = Marca.objects.filter(id=marca_id).first() if marca_id else None
        familia_obj = Familia.objects.filter(id=familia_id).first() if familia_id else None

        if produto_id and produto_id.strip():
            produto = get_object_or_404(Produtos, id=produto_id)
            produto.nome = nome
            produto.cod_barras = cod_barras
            produto.preco_custo = preco_custo
            produto.preco_venda = preco_venda
            produto.estoque_atual = estoque_atual
            produto.marca = marca_obj
            produto.familia = familia_obj
            produto.save()
            messages.success(request, f"Produto '{nome}' atualizado com sucesso!")
        else:
            Produtos.objects.create(
                nome=nome,
                cod_barras=cod_barras,
                preco_custo=preco_custo,
                preco_venda=preco_venda,
                estoque_atual=estoque_atual,
                marca=marca_obj,
                familia=familia_obj,
                status='ATIVO'
            )
            messages.success(request, f"Produto '{nome}' cadastrado com sucesso!")

    return redirect('tela_estoque_produtos')


def excluir_produto(request, id):
    produto = get_object_or_404(Produtos, id=id)
    nome = produto.nome
    produto.delete()
    messages.success(request, f"Produto '{nome}' excluído!")
    return redirect('tela_estoque_produtos')


def tela_entrada_carga(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    return render(request, 'inventario/entrada_carga.html')


def api_produto_por_codigo(request):
    codigo = request.GET.get('codigo', '').strip()
    produto = Produtos.objects.filter(cod_barras=codigo).first()
    if produto:
        return JsonResponse({
            'status': 'ok',
            'id': produto.id,
            'nome': produto.nome
        })
    return JsonResponse({'status': 'erro', 'mensagem': 'Produto não cadastrado!'})


def api_efetivar_entrada(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            itens = dados.get('itens', [])

            with transaction.atomic():
                for item in itens:
                    produto_id = item.get('id')
                    qtd_a_entrar = int(item.get('qtd', 0))

                    if qtd_a_entrar > 0:
                        produto = get_object_or_404(Produtos, id=produto_id)
                        produto.estoque_atual += qtd_a_entrar
                        produto.save()

            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})


# ==========================================
# 👥 GESTÃO DE CLIENTES
# ==========================================

def tela_consultar_clientes(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    query = request.GET.get('q', '')
    clientes = Clientes.objects.all()

    if query:
        clientes = clientes.filter(
            Q(nome__icontains=query) |
            Q(cpf__icontains=query) |
            Q(telefone__icontains=query)
        )

    conf_cliente = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()
    conf_pintor = ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()

    context = {
        'clientes': clientes,
        'query': query,
        'conf_cliente': conf_cliente,
        'conf_pintor': conf_pintor
    }
    return render(request, 'inventario/consultar_clientes.html', context)


def salvar_edicao_cliente(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')

        if cliente_id and cliente_id.strip():
            cliente = get_object_or_404(Clientes, id=cliente_id)
        else:
            cliente = Clientes()

        cliente.nome = request.POST.get('nome', '')
        cliente.telefone = request.POST.get('telefone', '')
        cliente.cpf = request.POST.get('cpf', '')

        cliente.cep = request.POST.get('cep', '')
        cliente.rua = request.POST.get('rua', '')
        cliente.numero = request.POST.get('numero', '')
        cliente.complemento = request.POST.get('complemento', '')

        tipos = []
        if request.POST.get('check_cliente'): tipos.append("CLIENTE")
        if request.POST.get('check_pintor'): tipos.append("PINTOR")
        cliente.tipo = ", ".join(tipos) if tipos else "CLIENTE"

        cliente.save()
        messages.success(request, f"Ficha de {cliente.nome} salva com sucesso!")
    return redirect('tela_consultar_clientes')


def api_historico_cliente(request):
    nome_cliente = request.GET.get('nome', '')
    vendas = Vendas.objects.filter(cliente=nome_cliente, status='VENDA').order_by('-id')

    historico = []
    for v in vendas:
        historico.append({
            'id': v.id,
            'data': v.data_venda.strftime('%d/%m/%Y %H:%M'),
            'vendedor': v.vendedor,
            'valor': float(v.valor_total)
        })
    return JsonResponse({'historico': historico})


def excluir_cliente(request, id):
    # Proteção: só permite excluir se estiver logado
    if 'usuario_logado' not in request.session:
        return redirect('login')

    try:
        # Busca o cliente pelo ID e exclui
        # (Se o seu modelo se chamar apenas 'Cliente' no singular, mude abaixo)
        cliente = Clientes.objects.get(id=id)
        cliente.delete()
    except Exception as e:
        print(f"Erro ao excluir cliente: {e}")

    # Redireciona de volta para a tela de clientes após excluir
    return redirect('tela_consultar_clientes')


# ==========================================
# ⚙️ SUBMENUS AUXILIARES SEPARADOS
# ==========================================

def tela_marcas(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    familias = Familia.objects.all().order_by('nome')
    marcas = Marca.objects.all().order_by('nome')
    return render(request, 'inventario/gerencia_auxiliares.html', {
        'familias': familias, 'marcas': marcas, 'marcas_list': marcas, 'fabricantes': marcas, 'aba_ativa': 'marcas'
    })


def tela_familias(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    familias = Familia.objects.all().order_by('nome')
    marcas = Marca.objects.all().order_by('nome')
    return render(request, 'inventario/gerencia_auxiliares.html', {
        'familias': familias, 'familias_list': familias, 'grupos': familias, 'marcas': marcas, 'aba_ativa': 'familias'
    })


def salvar_marca(request):
    if request.method == 'POST':
        marca_id = request.POST.get('marca_id')
        nome = request.POST.get('nome')
        if marca_id:
            marca = get_object_or_404(Marca, id=marca_id)
            marca.nome = nome
            marca.save()
            messages.success(request, f"Marca '{nome}' atualizada!")
        else:
            Marca.objects.create(nome=nome)
            messages.success(request, f"Marca '{nome}' cadastrada!")
    return redirect('tela_marcas')


def excluir_marca(request, id):
    marca = get_object_or_404(Marca, id=id)
    nome = marca.nome
    marca.delete()
    messages.success(request, f"Marca '{nome}' excluída!")
    return redirect('tela_marcas')


def salvar_familia(request):
    if request.method == 'POST':
        familia_id = request.POST.get('familia_id')
        nome = request.POST.get('nome')
        if familia_id:
            familia = get_object_or_404(Familia, id=familia_id)
            familia.nome = nome
            familia.save()
            messages.success(request, f"Família '{nome}' updated successfully!")
        else:
            Familia.objects.create(nome=nome)
            messages.success(request, f"Família '{nome}' cadastrada!")
    return redirect('tela_familias')


def excluir_familia(request, id):
    familia = get_object_or_404(Familia, id=id)
    nome = familia.nome
    familia.delete()
    messages.success(request, f"Família '{nome}' excluída!")
    return redirect('tela_familias')


# ==========================================
# 📊 RELATÓRIOS FINANCEIROS CALCULADOS
# ==========================================

def tela_relatorios(request):
    # Proteção de acesso: se não estiver logado, vai para o login
    if 'usuario_logado' not in request.session:
        return redirect('login')

    # Captura os filtros que vieram do formulário da tela
    vendedor_filtro = request.GET.get('vendedor', '')
    status_filtro = request.GET.get('status', '')

    # Começa trazendo todas as vendas ordenadas pelas mais recentes
    vendas_todas = Vendas.objects.all().order_by('-id')

    # Aplica os filtros apenas se o usuário escolheu alguma opção na tela
    if vendedor_filtro:
        vendas_todas = vendas_todas.filter(vendedor__iexact=vendedor_filtro) # __iexact ignora maiúsculas/minúsculas
    if status_filtro:
        vendas_todas = vendas_todas.filter(status=status_filtro)

    # Separa o que é Venda Finalizada e o que é Orçamento para as métricas
    vendas_confirmadas = vendas_todas.filter(status='VENDA')
    orcamentos_todos = vendas_todas.filter(status='ORCAMENTO')

    # Faz a soma do faturamento direto no banco de dados (muito mais rápido e seguro)
    resultado_soma = vendas_confirmadas.aggregate(total=Sum('valor_total'))
    faturamento = float(resultado_soma['total'] or 0.0)

    # Contagem dos cards de métricas
    qtd_vendas = vendas_confirmadas.count()
    qtd_orcamentos = orcamentos_todos.count()

    # Cálculo do ticket médio prevenindo divisão por zero
    ticket_medio = faturamento / qtd_vendas if qtd_vendas > 0 else 0.0

    # Monta o contexto para enviar os dados corrigidos para o HTML
    context = {
        'vendas': vendas_todas,
        'vendedores': Usuarios.objects.all(),
        'filtros': {
            'vendedor': vendedor_filtro,  # CORREÇÃO: Removido o 'seller_filter' que causava NameError
            'status': status_filtro,
        },
        'metricas': {
            'total_liquido': faturamento,
            'qtd_vendas': qtd_vendas,
            'qtd_orcamentos': qtd_orcamentos,
            'ticket_medio': ticket_medio,
        }
    }
    return render(request, 'inventario/relatorios.html', context)


def imprimir_cupom(request, id):
    venda = get_object_or_404(Vendas, id=id)

    try:
        carrinho = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    except (ValueError, TypeError):
        carrinho = []

    subtotal_bruto = 0.0

    # Faz o cálculo matemático para cada item do carrinho antes de enviar para a tela
    for item in carrinho:
        preco = float(item.get('preco', 0))
        qtd = int(item.get('qtd', 1))

        # Cria a variável 'total_linha' que o HTML está pedindo
        item['total_linha'] = preco * qtd

        # Soma tudo para gerar o 'subtotal_bruto'
        subtotal_bruto += item['total_linha']

    contexto = {
        'venda': venda,
        'carrinho': carrinho,
        'itens': carrinho,
        'subtotal_bruto': subtotal_bruto  # Enviamos o subtotal calculado!
    }
    return render(request, 'inventario/cupom.html', contexto)


def imprimir_cupom_a4(request, id):
    venda = get_object_or_404(Vendas, id=id)

    try:
        carrinho = json.loads(venda.cupom_texto) if venda.cupom_texto else []
    except (ValueError, TypeError):
        carrinho = []

    subtotal_bruto = 0.0

    # Faz o cálculo matemático para cada item do carrinho antes de enviar para a tela A4
    for item in carrinho:
        preco = float(item.get('preco', 0))
        qtd = int(item.get('qtd', 1))

        # Cria a variável 'total_linha' que o HTML A4 está pedindo
        item['total_linha'] = preco * qtd

        # Soma tudo para gerar o 'subtotal_bruto' A4
        subtotal_bruto += item['total_linha']

    contexto = {
        'venda': venda,
        'carrinho': carrinho,
        'itens': carrinho,
        'subtotal_bruto': subtotal_bruto  # Enviamos o subtotal calculado!
    }
    return render(request, 'inventario/cupom_a4.html', contexto)


def cancelar_venda(request):
    if request.method == 'POST':
        venda_id = request.POST.get('venda_id')
        login_auth = request.POST.get('login_autorizador', '').strip()
        senha_auth = request.POST.get('senha_autorizador', '').strip()
        motivo = request.POST.get('motivo', '').strip()

        # 1. Verifica no banco de dados se o usuário e a senha estão corretos
        autorizador = Usuarios.objects.filter(login=login_auth, senha=senha_auth).first()

        if autorizador:
            try:
                # 2. Encontra a venda e muda o status
                venda = Vendas.objects.get(id=venda_id)
                venda.status = 'CANCELADA'
                venda.save()

                # Mensagem de sucesso registrando quem cancelou e o motivo
                messages.success(request, f"✅ Venda #{venda_id} cancelada por {autorizador.login}. Motivo: {motivo}")
            except Exception as e:
                messages.error(request, f"Erro ao cancelar o documento: {e}")
        else:
            # Se a senha estiver errada, bloqueia a ação
            messages.error(request, "❌ Cancelamento Negado: Login ou Senha do autorizador estão incorretos.")

    return redirect('tela_relatorios')



# ==========================================
# 👥 GESTÃO DE EQUIPE E COMISSÕES
# ==========================================

def tela_colaboradores(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    lista_equipe = Usuarios.objects.all()

    for colaborador in lista_equipe:
        vendas_do_vendedor = Vendas.objects.filter(vendedor=colaborador.login, status='VENDA')

        total_vendido = 0.0
        for v in vendas_do_vendedor:
            try:
                total_vendido += float(v.valor_total)
            except (ValueError, TypeError):
                pass

        try:
            percentual_comissao = float(colaborador.comissao)
        except (ValueError, TypeError):
            percentual_comissao = 0.0

        comissao_a_pagar = (total_vendido * percentual_comissao) / 100

        colaborador.total_vendido = total_vendido
        colaborador.comissao_a_pagar = comissao_a_pagar

    context = {
        'equipe': lista_equipe,
    }
    return render(request, 'inventario/colaboradores.html', context)


def salvar_colaborador(request):
    if request.method == 'POST':
        colaborador_id = request.POST.get('colaborador_id')
        login = request.POST.get('login', '').strip()
        senha_nova = request.POST.get('senha', '').strip()
        perfil = request.POST.get('perfil', 'Colaborador')
        comissao = request.POST.get('comissao', '0.00').replace(',', '.')

        try:
            if colaborador_id and colaborador_id.strip() and colaborador_id != 'None':
                colaborador = get_object_or_404(Usuarios, id=colaborador_id)

                if Usuarios.objects.filter(login=login).exclude(id=colaborador.id).exists():
                    messages.error(request, f"Erro: O login '{login}' já está em uso por outra pessoa!")
                    return redirect('tela_colaboradores')

                colaborador.login = login

                if senha_nova:
                    colaborador.senha = senha_nova

                colaborador.perfil = perfil
                colaborador.comissao = comissao
                colaborador.save()
                messages.success(request, f"Colaborador '{login}' atualizado com sucesso!")

            else:
                colaborador_existente = Usuarios.objects.filter(login=login).first()
                if colaborador_existente:
                    if senha_nova:
                        colaborador_existente.senha = senha_nova

                    colaborador_existente.perfil = perfil
                    colaborador_existente.comissao = comissao
                    colaborador_existente.save()
                    messages.success(request, f"Colaborador '{login}' atualizado com sucesso!")
                else:
                    Usuarios.objects.create(login=login, senha=senha_nova, perfil=perfil, comissao=comissao)
                    messages.success(request, f"Colaborador '{login}' cadastrado com sucesso!")

        except Exception as e:
            messages.error(request, f"Erro inesperado ao salvar alterações: {str(e)}")

    return redirect('tela_colaboradores')


def excluir_colaborador(request, id):
    colaborador = get_object_or_404(Usuarios, id=id)
    login = colaborador.login
    colaborador.delete()
    messages.success(request, f"Colaborador '{login}' removido com sucesso!")
    return redirect('tela_colaboradores')


# ==========================================
# ⚙️ REGRAS DE FIDELIDADE (PONTUAÇÃO)
# ==========================================

def tela_manutencao_pontos(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
    return render(request, 'inventario/manutencao_pontos.html', {
        'conf_cliente': ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first(),
        'conf_pintor': ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()
    })


def salvar_configuracao_pontos(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo_usuario')

        # Captura o valor do POST com segurança. Se vier vazio, assume 1 como padrão.
        pontos_raw = request.POST.get('pontos_necessarios_resgate', '1')
        try:
            pontos = int(pontos_raw) if pontos_raw.strip() != "" else 1
        except ValueError:
            pontos = 1

        # Busca a configuração existente ou cria uma nova para o tipo de usuário
        config, created = ConfiguracaoPontos.objects.get_or_create(tipo_usuario=tipo)

        # CORREÇÃO: Variável ajustada de 'points' para 'pontos' (sem linhas duplicadas)
        config.pontos_necessarios_resgate = pontos
        config.valor_resgate_reais = 1.00
        config.save()

        # Mensagem de sucesso para o operador
        messages.success(request, f"Regras de pontuação para {tipo.lower()} salvas com sucesso!")

    return redirect('tela_manutencao_pontos')