from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from inventario.models import Vendas

class Command(BaseCommand):
    help = 'Exclui pedidos ABERTOS com mais de 7 dias'

    def handle(self, *args, **kwargs):
        # 1. Calcula qual era a data exatamente 7 dias atrás
        limite_data = timezone.now() - timedelta(days=7)
        
        # 2. Busca os pedidos que são 'ABERTO' E que a data seja anterior (menor ou igual) ao limite
        pedidos_antigos = Vendas.objects.filter(
            status='ABERTO',
            data_venda__lte=limite_data
        )
        
        # 3. Conta quantos achou para mostrar no log e depois deleta
        quantidade = pedidos_antigos.count()
        pedidos_antigos.delete()
        
        # 4. Mensagem de sucesso no terminal
        self.stdout.write(self.style.SUCCESS(f'Limpeza concluída: {quantidade} pedidos abandonados foram apagados.'))
        