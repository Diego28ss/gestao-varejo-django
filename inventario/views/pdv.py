import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q

# Importação dos modelos necessários
from inventario.models import Produtos, Clientes, Usuarios

# Importação dos serviços de negócio
from inventario.services import fidelidade, vendas

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
    if not query:
        return JsonResponse({'produtos': []})

    termos = query.split()
    filtros = Q()
    for termo in termos:
        filtros &= (
            Q(nome__icontains=termo) |
            Q(cod_barras__icontains=termo) |
            Q(cod_interno__icontains=termo) |
            Q(marca__nome__icontains=termo) |
            Q(familia__nome__icontains=termo)
        )

    produtos = Produtos.objects.filter(filtros).exclude(status='INATIVO')[:10]

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

            # 🚀 FASE 1: RESOLUÇÃO DO CONSUMIDOR PADRÃO
            # Se o cliente vier vazio (""), transformamos em None para aceitar no banco como nulo
            cliente_nome = dados.get('cliente', '').strip()
            cliente_valido = cliente_nome if cliente_nome != "" else None

            indicante_nome = dados.get('indicante', '').strip()
            indicante_valido = indicante_nome if indicante_nome != "" else None

            # 🚀 FASE 2: TRATAMENTO DOS IDS VIRTUAIS DO TINTOMÉTRICO
            # Ajustamos o carrinho antes de enviar para o motor de vendas para que ele ache a lata real
            carrinho_tratado = []
            for item in carrinho:
                item_id_original = str(item.get('id', ''))
                
                # Se o ID começar com 'TINTA-', significa que é uma mistura com ID virtual
                if item_id_original.startswith('TINTA-') or not item_id_original.isdigit():
                    # Buscamos a propriedade escondida que passamos pelo Javascript do botão
                    cod_interno_real = item.get('id_real_estoque')
                    
                    if cod_interno_real:
                        # Localizamos o ID numérico sequencial correspondente no banco do estoque principal
                        produto_banco = Produtos.objects.filter(cod_interno=cod_interno_real).first()
                        if produto_banco:
                            item['id'] = produto_banco.id  # Atribui o ID numérico correto para dar baixa no estoque
                
                carrinho_tratado.append(item)

            dados_venda = {
                'valor_total': dados.get('valor_final'),
                'valor_desconto': dados.get('desconto'),
                'vendedor': dados.get('vendedor'),
                'cliente': cliente_valido,       # Injeta o valor tratado (String ou None)
                'indicante': indicante_valido,   # Injeta o valor tratado (String ou None)
                'status': status_venda,
                'cupom_texto': json.dumps(carrinho_tratado)
            }

            venda_id = vendas.processar_nova_venda(
                dados_venda, 
                carrinho_tratado, 
                status_venda, 
                pontos_resgatados=pontos_resgatados
            )
            return JsonResponse({'status': 'sucesso', 'venda_id': venda_id})

        except ValueError as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': f"Erro interno no PDV: {str(e)}"})

    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})
