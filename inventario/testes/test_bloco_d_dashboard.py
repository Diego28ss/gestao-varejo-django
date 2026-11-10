import json
from django.test import TestCase
from django.utils import timezone
from inventario.models import Usuarios, Clientes
from inventario.models.vendas import Vendas
from inventario.services.dashboard.dashboard_service import obter_dados_painel

class BlocoDDashboardTestCase(TestCase):
    def setUp(self):
        # Criação de um utilizador de teste
        self.usuario = Usuarios.objects.create(
            login='admin.dashboard', 
            senha='123', 
            perfil='Gerente', 
            status='ATIVO'
        )

    def test_01_dashboard_soma_vendas_validas(self):
        """ Fase 17: Garante que vendas faturadas entram no somatório do gráfico de hoje """
        Vendas.objects.create(
            vendedor=self.usuario.login,
            valor_total=250.00,
            status='VENDA',
            data_venda=timezone.now()
        )
        
        dados = obter_dados_painel()
        
        # O último dia da lista graf_valores representa "hoje"
        self.assertEqual(dados['graf_valores'][-1], 250.0)

    def test_02_dashboard_ignora_orcamentos(self):
        """ Fase 17: Garante que Orçamentos e Cancelamentos não inflam o gráfico de vendas """
        Vendas.objects.create(
            vendedor=self.usuario.login,
            valor_total=500.00,
            status='ORCAMENTO',
            data_venda=timezone.now()
        )
        Vendas.objects.create(
            vendedor=self.usuario.login,
            valor_total=300.00,
            status='CANCELADA',
            data_venda=timezone.now()
        )
        
        dados = obter_dados_painel()
        
        # O gráfico de hoje deve estar a zeros
        self.assertEqual(dados['graf_valores'][-1], 0.0)

    def test_03_dashboard_estrutura_retorno_valida(self):
        """ Fase 17: Verifica se o serviço entrega as listas de labels e valores prontas """
        dados = obter_dados_painel()
        
        self.assertIn('graf_labels', dados)
        self.assertIn('graf_valores', dados)
        self.assertIsInstance(dados['graf_labels'], list)
        self.assertIsInstance(dados['graf_valores'], list)
        self.assertEqual(len(dados['graf_labels']), 7) # Exatamente 7 dias

    def test_04_clientes_armazenamento_pontos(self):
        """ Fase 18: Verifica se o saldo de pontos Fidelidade é gravado de forma íntegra no modelo """
        cliente_teste = Clientes.objects.create(
            nome='João Pintor de Teste',
            cpf='11122233344',
            tipo='PINTOR',
            pontos=150
        )
        
        # Recarrega do banco para validar persistência
        cliente_db = Clientes.objects.get(id=cliente_teste.id)
        self.assertEqual(cliente_db.pontos, 150)
        self.assertEqual(cliente_db.tipo, 'PINTOR')
        