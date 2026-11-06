import json
from django.test import TestCase, Client
from inventario.models import Produtos, Usuarios, Clientes, Vendas

class Blocos1e2Tests(TestCase):
    def setUp(self):
        """ Configuração inicial: Cria o ecossistema de uma Venda """
        self.client = Client()
        
        self.vendedor = Usuarios.objects.create(
            login='vendedor_teste', 
            perfil='Vendedor', 
            senha='123'
        )
        
        self.gerente = Usuarios.objects.create(
            login='gerente_teste', 
            perfil='Gerente', 
            senha='123'
        )

        self.produto = Produtos.objects.create(nome='Massa Corrida', estoque_atual=50, preco_venda=100.00)
        self.cliente = Clientes.objects.create(nome='João Teste', pontos=20)
        
        session = self.client.session
        session['usuario_logado'] = 'vendedor_teste'
        session['perfil_usuario'] = 'Vendedor'
        session.save()

    def test_pdv_separacao_descontos_e_congelamento_comissao(self):
        """ Bloco 2 (Fase 6): Testa se a API do PDV salva os descontos separados e congela a comissão """
        
        payload = {
            # 🚀 CORREÇÃO 1: A API espera a lista no campo 'carrinho' e não 'itens'
            'carrinho': [
                {
                    'id': self.produto.id, 
                    'nome': self.produto.nome,
                    'qtd': 1,               # 🚀 CORREÇÃO 2: Usa 'qtd' em vez de 'quantidade'
                    'preco_desconto': 85.00 # 🚀 CORREÇÃO 3: A API exige o campo 'preco_desconto'
                }
            ],
            'cliente': 'João Teste',
            'vendedor': 'vendedor_teste',
            'valor_final': 85.00,        # 🚀 CORREÇÃO 4: Usa 'valor_final' em vez de 'total_liquido'
            'desconto_comum': 10.00,     
            'desconto_pontos': 5.00,     
            'pagamento': 'PIX',          
            'observacoes': 'Teste de Venda Automatizada'
        }

        response = self.client.post(
            '/api/salvar-venda/', 
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        dados = response.json()
        
        # Armadilha de DEBUG
        self.assertEqual(dados['status'], 'sucesso', msg=f"Erro na API do PDV: {dados.get('mensagem')}")
        
        venda_salva = Vendas.objects.last()
        self.assertIsNotNone(venda_salva)
        self.assertEqual(float(venda_salva.desconto_comum), 10.00)
        self.assertEqual(float(venda_salva.desconto_pontos), 5.00)
        
        # Valida que o PDV congelou a comissão (ela não pode ser nula)
        self.assertIsNotNone(venda_salva.percentual_comissao)

    def test_retaguarda_trava_fiscal_cancelamento(self):
        """ Bloco 1 (Fase 2 e 3): Testa a Trava Fiscal que impede cancelamento de pedido faturado """
        
        # Cria um pedido no banco com os campos mínimos obrigatórios
        pedido_faturado = Vendas.objects.create(
            vendedor=self.vendedor,
            valor_total=200.00,
            status='FATURADO'  # O status universal que a Retaguarda entende para travar o cancelamento
        )
        
        payload_cancelamento = {
            'motivo': 'Cliente desistiu',
            'autorizador': 'gerente_teste'
        }

        response = self.client.post(
            f'/api/pedidos/cancelar/{pedido_faturado.id}/', 
            data=json.dumps(payload_cancelamento),
            content_type='application/json'
        )
        
        dados = response.json()
        
        # O sistema TEM que rejeitar (erro) o cancelamento
        self.assertEqual(dados['status'], 'erro', msg="Falha: O sistema permitiu cancelar um pedido faturado!")
        
        # Confirma no banco que o pedido não teve o seu status alterado para CANCELADO
        pedido_faturado.refresh_from_db()
        self.assertNotEqual(pedido_faturado.status, 'CANCELADO')
        