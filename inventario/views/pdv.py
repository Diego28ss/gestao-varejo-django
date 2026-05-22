import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Q

# Importação dos modelos necessários
from inventario.models import Produtos, Clientes, Usuarios

# 🔥 AQUI ESTÁ A CORREÇÃO PRINCIPAL: Adicionamos o 'tintometrico' na importação!
from inventario.services import fidelidade, vendas, tintometrico

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
    resultado = fidelidade.calcular_resgate_pontos(nome_cliente)
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

            venda_id = vendas.processar_nova_venda(dados_venda, carrinho, status_venda, pontos_resgatados=pontos_resgatados)
            return JsonResponse({'status': 'sucesso', 'venda_id': venda_id})

        except ValueError as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
        except Exception as e:
            print(f"Erro ao salvar venda: {e}")
            return JsonResponse({'status': 'erro', 'mensagem': 'Erro interno ao processar venda no servidor.'})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})


# ==========================================
# 🎨 MÁQUINA TINTOMÉTRICA (NOVO)
# ==========================================

def tela_tintometrico(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
        
    context = {}
    
    # Preenche os menus com os dados reais do banco 'banco_tintometrico.db'
    linhas, embalagens = tintometrico.obter_linhas_e_embalagens()
    context['linhas'] = linhas
    context['embalagens'] = embalagens
    
    # Captura a pesquisa do vendedor (se ele clicou em "Calcular Fórmula")
    cor_busca = request.GET.get('cor', '')
    linha_id = request.GET.get('linha', '')
    embalagem_id = request.GET.get('embalagem', '')
    
    # Devolve o que foi pesquisado para manter os menus selecionados
    context['filtros'] = {'cor': cor_busca, 'linha': linha_id, 'embalagem': embalagem_id}
    
    # Roda a matemática se os 3 campos estiverem preenchidos
    if cor_busca and linha_id and embalagem_id:
        try:
            context['resultado'] = tintometrico.calcular_formula(cor_busca, linha_id, embalagem_id)
        except Exception as e:
            context['resultado'] = {'sucesso': False, 'erro': f"Erro interno: {str(e)}"}
            
    return render(request, 'inventario/tintometrico.html', context)
