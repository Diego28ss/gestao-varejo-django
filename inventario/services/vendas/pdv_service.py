from django.db.models import Q
from inventario.models import Produtos, RupturaEstoque

class PDVService:
    @staticmethod
    def buscar_produtos(query, offset=0, limit=10):
        if not query:
            return [], False

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

        queryset = Produtos.objects.filter(filtros).exclude(status='INATIVO')
        total_resultados = queryset.count()
        produtos = queryset[offset:offset+limit]

        resultados = [{
            'id': p.id,
            'nome': p.nome,
            'preco_venda': float(p.preco_venda),
            'preco_custo': float(p.preco_custo) if getattr(p, 'preco_custo', None) else 0.0,
            'estoque_atual': p.estoque_atual,
            'cod_barras': p.cod_barras or ''
        } for p in produtos]
        
        has_more = (offset + limit) < total_resultados
        return resultados, has_more

    @staticmethod
    def registrar_ruptura(produto_id, quantidade):
        produto = Produtos.objects.get(id=produto_id)
        RupturaEstoque.objects.create(produto=produto, quantidade_perdida=quantidade)

    @staticmethod
    def consultar_situacao(produto_id):
        produto = Produtos.objects.get(id=produto_id)
        data_formatada = produto.data_previsao_chegada.strftime('%d/%m/%Y') if produto.data_previsao_chegada else None
        return {
            'estoque_atual': produto.estoque_atual,
            'qtd_em_transito': produto.qtd_em_transito,
            'data_previsao': data_formatada
        }
    