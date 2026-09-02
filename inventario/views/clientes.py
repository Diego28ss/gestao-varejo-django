from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.utils.timezone import localtime

# Importação dos modelos necessários para a gestão de clientes e histórico
from inventario.models import Clientes, ConfiguracaoPontos, Vendas

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
        # --- 🛡️ INÍCIO DA BARREIRA DE FERRO FISCAL ---
        cep_teste = request.POST.get('cep', '').strip()
        numero_teste = request.POST.get('numero', '').strip()

        if not cep_teste or not numero_teste:
            messages.error(request, "⚠️ Operação bloqueada: O CEP e o Número são obrigatórios para emissão de Nota Fiscal.")
            return redirect('tela_consultar_clientes')
        # --- FIM DA BARREIRA DE FERRO FISCAL ---

        cliente_id = request.POST.get('cliente_id')
        tipo_pessoa = request.POST.get('tipo_pessoa', 'PF')
        cpf_digitado = request.POST.get('cpf', '').strip()
        cnpj_digitado = request.POST.get('cnpj', '').strip()

        # --- 🛡️ TRAVA 5: ANTI-DUPLICIDADE DE CPF / CNPJ ---
        if tipo_pessoa == 'PF' and cpf_digitado:
            query = Clientes.objects.filter(cpf=cpf_digitado)
            if cliente_id:
                query = query.exclude(id=cliente_id) # Ignora o próprio cliente na edição
                
            cliente_existente = query.first()
            if cliente_existente:
                messages.error(request, f"⚠️ Erro de Duplicidade: O CPF {cpf_digitado} já está associado ao cliente '{cliente_existente.nome}'.")
                return redirect('tela_consultar_clientes')
                
        elif tipo_pessoa == 'PJ' and cnpj_digitado:
            query = Clientes.objects.filter(cnpj=cnpj_digitado)
            if cliente_id:
                query = query.exclude(id=cliente_id)
                
            cliente_existente = query.first()
            if cliente_existente:
                messages.error(request, f"⚠️ Erro de Duplicidade: O CNPJ {cnpj_digitado} já está associado à empresa '{cliente_existente.nome}'.")
                return redirect('tela_consultar_clientes')
        # --- FIM DA TRAVA ANTI-DUPLICIDADE ---

        if cliente_id and cliente_id.strip():
            cliente = get_object_or_404(Clientes, id=cliente_id)
        else:
            cliente = Clientes()

        # Dados Básicos e Tipo de Pessoa
        cliente.tipo_pessoa = tipo_pessoa
        cliente.nome = request.POST.get('nome', '') # Nome ou Nome Fantasia
        cliente.telefone = request.POST.get('telefone', '')
        cliente.email = request.POST.get('email', '')

        # Se for Pessoa Física
        if cliente.tipo_pessoa == 'PF':
            cliente.cpf = cpf_digitado
            cliente.cnpj = None
            cliente.razao_social = None
            cliente.inscricao_estadual = None
        
        # Se for Pessoa Jurídica
        else:
            cliente.cnpj = cnpj_digitado
            cliente.razao_social = request.POST.get('razao_social', '')
            cliente.inscricao_estadual = request.POST.get('inscricao_estadual', '')
            cliente.cpf = None # Limpa caso tenha mudado de PF para PJ

        # Endereço (ViaCEP)
        cliente.cep = request.POST.get('cep', '')
        cliente.endereco = request.POST.get('endereco', '') # Rua
        cliente.numero = request.POST.get('numero', '')
        cliente.complemento = request.POST.get('complemento', '')
        cliente.bairro = request.POST.get('bairro', '')
        cliente.cidade = request.POST.get('cidade', '')
        cliente.estado = request.POST.get('estado', '')

        # Categoria (Pintor/Cliente)
        tipos = []
        if request.POST.get('check_cliente'): tipos.append("CLIENTE")
        if request.POST.get('check_pintor'): tipos.append("PINTOR")
        cliente.tipo = ", ".join(tipos) if tipos else "CLIENTE"

        cliente.save()
        messages.success(request, f"Ficha de {cliente.nome} salva com sucesso!")
        
    return redirect('tela_consultar_clientes')


def api_historico_cliente(request, cliente_id=None):
    try:
        # 1. Identifica se o navegador mandou a informação na Rota Antiga ou Nova
        termo_busca = ""
        if cliente_id:
            termo_busca = str(cliente_id).strip()
        else:
            termo_busca = request.GET.get('nome', '').strip()

        # 2. Verifica se o que chegou foi um Número (ID) ou Texto (Nome)
        if termo_busca.isdigit():
            historico = Vendas.objects.filter(
                cliente_id=termo_busca, 
                status__iexact='FATURADO'
            ).order_by('-data_venda')
        else:
            historico = Vendas.objects.filter(
                cliente__nome__iexact=termo_busca, 
                status__iexact='FATURADO'
            ).order_by('-data_venda')

        # 3. Monta o pacote de dados com travas de segurança
        dados = []
        for v in historico:
            # Trava de segurança: converte o vendedor para texto simples.
            # O seu modelo Usuarios usa 'login' e não 'username'
            nome_vendedor = 'SISTEMA'
            if v.vendedor:
                nome_vendedor = getattr(v.vendedor, 'login', str(v.vendedor))

            dados.append({
                'data': v.data_venda.strftime('%d/%m/%Y') if v.data_venda else '--/--/----',
                'valor_total': f"{v.valor_total:.2f}" if v.valor_total else "0.00",
                'codigo_venda': v.id,
                'vendedor': nome_vendedor.upper()
            })

        return JsonResponse({'status': 'sucesso', 'historico': dados})
    
    except Exception as e:
        print(f"Erro na API de Histórico: {str(e)}")
        # Se ocorrer qualquer erro, devolve para o Javascript sem derrubar o servidor
        return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)


def excluir_cliente(request, id):
    # Proteção: só permite excluir se estiver logado
    if 'usuario_logado' not in request.session:
        return redirect('login')

    try:
        # Busca o cliente pelo ID e exclui
        cliente = Clientes.objects.get(id=id)
        cliente.delete()
    except Exception as e:
        print(f"Erro ao excluir cliente: {e}")

    # Redireciona de volta para a tela de clientes após excluir
    return redirect('tela_consultar_clientes')
