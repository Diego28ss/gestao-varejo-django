import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect
from django.db.models import Q
from inventario.models import Vendas, Produtos, Usuarios, Clientes


# Importação dos modelos e serviços especializados
from inventario.models import Produtos, Clientes, Usuarios, RupturaEstoque
from inventario.services import fidelidade
from inventario.services.vendas import VendaService

# ==========================================
# 🛒 FRENTE DE CAIXA (PDV) - SKINNY VIEWS
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

    resultados = [{
        'id': p.id,
        'nome': p.nome,
        'preco_venda': float(p.preco_venda),
        'preco_custo': float(p.preco_custo) if getattr(p, 'preco_custo', None) else 0.0,
        'estoque_atual': p.estoque_atual,
        'cod_barras': p.cod_barras or ''
    } for p in produtos]
    
    return JsonResponse({'produtos': resultados})


def api_salvar_venda(request):
    """
    Controlador Magro: Recebe o pacote JSON da tela e delega toda a validação, 
    cálculo matemático e transação de banco de dados para a Camada de Serviço.
    """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            venda_id = VendaService.registrar_checkout(dados)
            return JsonResponse({'status': 'sucesso', 'venda_id': venda_id})
            
        except ValueError as e:
            # Captura travas de segurança (Carrinho Vazio, Preço Negativo, etc.)
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
            
        except Exception as e:
            # Captura falhas de Banco de Dados ou Código
            return JsonResponse({'status': 'erro', 'mensagem': f"Erro interno no PDV: {str(e)}"})

    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})


# ==========================================
# 🚨 GESTÃO DE RUPTURA (FALTA DE ESTOQUE)
# ==========================================

def api_registrar_ruptura(request):
    """
    Recebe o alerta do botão de falta no PDV e registra no banco
    para orientar a tela de Suprir Estoque nas próximas compras.
    """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            produto_id = dados.get('produto_id')
            quantidade = int(dados.get('quantidade_perdida', 1))

            produto = Produtos.objects.get(id=produto_id)

            # Grava a Venda Perdida silenciosamente no banco de dados
            RupturaEstoque.objects.create(
                produto=produto,
                quantidade_perdida=quantidade
            )

            return JsonResponse({'status': 'sucesso', 'mensagem': 'Ruptura registrada com sucesso.'})
            
        except Produtos.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'Produto não encontrado na base.'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})

    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_consultar_situacao_estoque(request, produto_id):
    """Retorna a situação atual de estoque e encomendas de um produto para o PDV."""
    try:
        produto = Produtos.objects.get(id=produto_id)
        
        # Formata a data se existir
        data_formatada = None
        if produto.data_previsao_chegada:
            data_formatada = produto.data_previsao_chegada.strftime('%d/%m/%Y')

        return JsonResponse({
            'status': 'sucesso',
            'estoque_atual': produto.estoque_atual,
            'qtd_em_transito': produto.qtd_em_transito,
            'data_previsao': data_formatada
        })
    except Produtos.DoesNotExist:
        return JsonResponse({'status': 'erro', 'mensagem': 'Produto não encontrado.'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'mensagem': str(e)})
