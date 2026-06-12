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

        if cliente_id and cliente_id.strip():
            cliente = get_object_or_404(Clientes, id=cliente_id)
        else:
            cliente = Clientes()

        # Dados Básicos e Tipo de Pessoa
        cliente.tipo_pessoa = request.POST.get('tipo_pessoa', 'PF') # 'PF' ou 'PJ'
        cliente.nome = request.POST.get('nome', '') # Nome ou Nome Fantasia
        cliente.telefone = request.POST.get('telefone', '')
        cliente.email = request.POST.get('email', '')

        # Se for Pessoa Física
        if cliente.tipo_pessoa == 'PF':
            cliente.cpf = request.POST.get('cpf', '')
            cliente.cnpj = None
            cliente.razao_social = None
            cliente.inscricao_estadual = None
        
        # Se for Pessoa Jurídica
        else:
            cliente.cnpj = request.POST.get('cnpj', '')
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

def api_historico_cliente(request):
    nome_cliente = request.GET.get('nome', '')
    vendas = Vendas.objects.filter(cliente=nome_cliente, status='VENDA').order_by('-id')

    historico = []
    for v in vendas:
        historico.append({
            'id': v.id,
            # Aplicamos o localtime() aqui para converter de UTC para o horário de SP!
            'data': localtime(v.data_venda).strftime('%d/%m/%Y %H:%M'),
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
        cliente = Clientes.objects.get(id=id)
        cliente.delete()
    except Exception as e:
        print(f"Erro ao excluir cliente: {e}")

    # Redireciona de volta para a tela de clientes após excluir
    return redirect('tela_consultar_clientes')
