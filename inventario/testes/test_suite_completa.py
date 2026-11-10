import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from inventario.models import (
    Usuarios, Clientes, Produtos, LojaFilial, 
    ControleCaixa, MovimentacaoCaixa, TaxasMaquininha, 
    AuditoriaEstoque, AlertaPreco
)
from inventario.models.vendas import Vendas

class SuiteCompletaValidacaoTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # 1. Credenciais base de teste (Gerente e Operador)
        self.gerente = Usuarios.objects.create(
            login='gerente.teste', senha='123', perfil='Gerente', status='ATIVO'
        )
        self.operador = Usuarios.objects.create(
            login='operador.teste', senha='123', perfil='Operador', status='ATIVO'
        )
        
        # 2. Sessão autenticada inicial
        session = self.client.session
        session['usuario_logado'] = self.gerente.login
        session['perfil_usuario'] = self.gerente.perfil
        session.save()

    # ==========================================
    # BLOCO A: Gestão de Caixa e PDV (Fases 1 a 6)
    # ==========================================
    def test_bloco_a_fluxo_caixa_e_lobby(self):
        """ Valida a abertura de caixa, status do lobby e rotas de impressão """
        # Teste Fase 1 & 4: Abertura de Caixa via API
        dados_abertura = {
            'lastro': 150.00,
            'operador_login': self.operador.login,
            'operador_senha': self.operador.senha,
            'gerente_login': self.gerente.login,
            'gerente_senha': self.gerente.senha
        }
        res = self.client.post(reverse('api_abrir_caixa'), data=json.dumps(dados_abertura), content_type='application/json')
        self.assertEqual(res.json()['status'], 'sucesso')
        
        caixa_id = res.json()['caixa_id']
        caixa = ControleCaixa.objects.get(id=caixa_id)
        self.assertEqual(caixa.status, 'ABERTO')
        self.assertEqual(float(caixa.lastro_inicial), 150.0)

        # Teste Fase 3 & 6: Acesso ao Lobby do PDV
        res_lobby = self.client.get(reverse('tela_painel_pdv'))
        self.assertEqual(res_lobby.status_code, 200)

        # Teste Fase 5: Rota de impressão de Abertura
        res_print = self.client.get(reverse('imprimir_comprovante_caixa', args=['abertura', caixa_id]))
        self.assertEqual(res_print.status_code, 200)

    # ==========================================
    # BLOCO B: Motor Financeiro (Fases 7 a 12)
    # ==========================================
    def test_bloco_b_taxas_maquininha_e_config(self):
        """ Valida o cadastro de taxas e o retorno correto da API de maquininha """
        # Teste Fase 7 & 9: Criação de taxa de cartão
        TaxasMaquininha.objects.create(
            metodo='CARTAO_CREDITO', parcelas=1, taxa_percentual=Decimal('2.99')
        )
        
        # Teste da API de Taxas da Maquininha (Fase 10)
        res = self.client.get(reverse('api_taxas_maquininha'), {'metodo': 'CARTAO_CREDITO', 'parcelas': 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['taxa'], 2.99)

        # Teste Fase 8: Loja com Código IBGE e Nome
        loja = LojaFilial.objects.create(nome_filial='Loja Matriz', codigo_ibge='3550308')
        self.assertEqual(loja.codigo_ibge, '3550308')

    # ==========================================
    # BLOCO C: Blindagem de Estoque e NFe (Fases 13 a 16)
    # ==========================================
    def test_bloco_c_auditoria_estoque(self):
        """ Valida a rastreabilidade da Caixa Preta e registos de auditoria """
        produto = Produtos.objects.create(
            nome='Tinta Acrílica Teste', preco_custo=50.00, preco_venda=100.00, estoque_atual=10
        )
        
        # Teste Fase 15 & 16: Registo manual na Auditoria de Estoque (perdas/ganhos)
        auditoria = AuditoriaEstoque.objects.create(
            produto=produto,
            operador=self.operador,
            tipo_movimento='AJUSTE_SAIDA',
            quantidade_variacao=-2,
            preco_custo_historico=produto.preco_custo,
            valor_perda=Decimal('100.00'), # 2 * 50.00
            valor_ganho=Decimal('0.00')
        )
        
        self.assertEqual(auditoria.valor_perda, Decimal('100.00'))
        self.assertEqual(auditoria.quantidade_variacao, -2)

    # ==========================================
    # BLOCO D: Dashboard e Polimentos (Fases 17 a 19)
    # ==========================================
    def test_bloco_d_fidelidade_e_vendas(self):
        """ Valida a persistência de pontos e o cálculo de receitas do dashboard """
        # Teste Fase 18: Cliente com pontos de fidelidade
        cliente = Clientes.objects.create(
            nome='Maria Pintora', cpf='99988877766', tipo='PINTOR', pontos=300
        )
        self.assertEqual(cliente.pontos, 300)

        # Teste Fase 17: Venda válida somando no faturamento
        Vendas.objects.create(
            vendedor=self.operador.login,
            valor_total=450.00,
            status='VENDA',
            data_venda=timezone.now()
        )
        
        # Simula a verificação do serviço de painel
        from inventario.services.dashboard.dashboard_service import obter_dados_painel
        dados_painel = obter_dados_painel()
        
        # O último valor da lista do gráfico (hoje) deve conter a venda de 450.00
        self.assertGreaterEqual(dados_painel['graf_valores'][-1], 450.0)
        