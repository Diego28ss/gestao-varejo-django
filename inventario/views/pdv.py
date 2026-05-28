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
            # ADICIONAMOS O PREÇO DE CUSTO AQUI (com validação caso esteja vazio no banco)
            'preco_custo': float(p.preco_custo) if getattr(p, 'preco_custo', None) else 0.0,
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
            valor_final = float(dados.get('valor_final', 0))

            # 🛡️ TRAVA DE SEGURANÇA 1: Carrinho Vazio
            if not carrinho or len(carrinho) == 0:
                raise ValueError("Bloqueio de Segurança: A operação não contém produtos.")

            # 🛡️ TRAVA DE SEGURANÇA 2: Valor Total Negativo
            if valor_final < 0:
                raise ValueError("Bloqueio de Segurança: O valor total da operação não pode ser negativo.")

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
                
                # 🛡️ TRAVA DE SEGURANÇA 3: Quantidades e Preços Absurdos
                qtd = int(item.get('qtd', 0))
                if qtd <= 0:
                    raise ValueError(f"O produto '{item.get('nome')}' está com quantidade inválida ({qtd}). A quantidade deve ser maior que zero.")
                
                preco_desconto = float(item.get('preco_desconto', 0))
                if preco_desconto < 0:
                    raise ValueError(f"O produto '{item.get('nome')}' está com preço negativo (R$ {preco_desconto}). Valores negativos não são permitidos.")

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

            # 🔥 CAPTURA DOS NOVOS DADOS DE PAGAMENTO E TROCO
            pagamentos_lista = dados.get('pagamentos', [])
            troco_valor = float(dados.get('troco', 0))

            dados_venda = {
                'valor_total': valor_final,
                'valor_desconto': float(dados.get('desconto', 0)),
                'vendedor': dados.get('vendedor'),
                'cliente': cliente_valido,       # Injeta o valor tratado (String ou None)
                'indicante': indicante_valido,   # Injeta o valor tratado (String ou None)
                'status': status_venda,
                'cupom_texto': json.dumps(carrinho_tratado),
                # 🔥 ADICIONA AO PACOTE DE DADOS PARA GRAVAR NO BANCO:
                'troco': troco_valor,
                'pagamentos_texto': json.dumps(pagamentos_lista)
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
