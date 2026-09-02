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
        dados = []
        historico = []

        if cliente_id and str(cliente_id).isdigit():
            # 🚀 NOVO PADRÃO: Pesquisa absoluta pelo ID relacional
            historico = Vendas.objects.filter(
                cliente_link_id=cliente_id, 
                status__iexact='FATURADO'
            ).order_by('-data_venda')
            
            # 🔄 Fallback: Se o ID não trouxe nada, pode ser uma compra legada que só tinha o texto.
            # O sistema resgata o cliente para pegar o nome dele e buscar no texto antigo.
            if not historico.exists():
                cliente_banco = Clientes.objects.filter(id=cliente_id).first()
                if cliente_banco:
                    historico = Vendas.objects.filter(
                        cliente__iexact=cliente_banco.nome, 
                        status__iexact='FATURADO'
                    ).order_by('-data_venda')
        else:
            # Consulta legada (se vier pela rota via GET)
            termo_busca = request.GET.get('nome', '').strip()
            if termo_busca:
                historico = Vendas.objects.filter(
                    cliente__iexact=termo_busca, 
                    status__iexact='FATURADO'
                ).order_by('-data_venda')

        for v in historico:
            nome_vendedor = 'SISTEMA'
            if getattr(v, 'vendedor', None):
                nome_vendedor = getattr(v.vendedor, 'login', str(v.vendedor))

            dados.append({
                'data': v.data_venda.strftime('%d/%m/%Y') if getattr(v, 'data_venda', None) else '--/--/----',
                'valor_total': f"{v.valor_total:.2f}" if getattr(v, 'valor_total', None) else "0.00",
                'codigo_venda': v.id,
                'vendedor': nome_vendedor.upper()
            })

        return JsonResponse({'status': 'sucesso', 'historico': dados})
    
    except Exception as e:
        print(f"Erro na API de Histórico: {str(e)}")
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
