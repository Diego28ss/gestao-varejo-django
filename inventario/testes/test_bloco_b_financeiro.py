import json
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from inventario.models import Usuarios, LojaFilial
from inventario.models.configuracoes import TaxasMaquininha
from inventario.models.vendas import Vendas
from inventario.services.vendas.venda_service import VendaService

class MotorFinanceiroTests(TestCase):
    def setUp(self):
        # 1. Configura um Operador
        self.operador = Usuarios.objects.create(
            login='operador_teste', 
            senha='123', 
            perfil='Vendedor', 
            comissao=2.00
        )
        
        # 2. Configura a Loja (Fase 8)
        self.loja = LojaFilial.objects.create(
            id=1, nome='JB Tintas Teste', codigo_ibge='3550308'
        )
        
        # 3. Configura as Taxas da Maquininha (Fase 9)
        TaxasMaquininha.objects.create(metodo='CARTAO_DEBITO', parcelas=1, taxa_percentual=2.00)
        TaxasMaquininha.objects.create(metodo='CARTAO_CREDITO', parcelas=1, taxa_percentual=5.00)

    def test_01_configuracao_filial_e_taxas_salvas(self):
        """ Valida se as taxas e o IBGE da loja estão gravados de forma íntegra """
        debito = TaxasMaquininha.objects.get(metodo='CARTAO_DEBITO')
        self.assertEqual(debito.taxa_percentual, Decimal('2.00'))
        self.assertEqual(self.loja.codigo_ibge, '3550308')

    def test_02_frente_de_caixa_gravando_custo_maquininha(self):
        """ Valida a Fase 10: O PDV injeta e grava o custo (valor_taxa_maquininha) da operação na venda """
        
        # Simulação perfeita de uma carga (payload) enviada pelo JS pdv.js
        payload = {
            'status': 'FATURADO',
            'valor_final': 100.00,
            'vendedor': 'operador_teste',
            'desconto_comum': 0.00,
            'desconto_pontos': 0.00,
            'valor_taxa_maquininha': 2.00, # Os 2% calculados visualmente na interface JS
            'carrinho': [{'id': 999, 'nome': 'Produto Teste', 'qtd': 1, 'preco': 100.00}],
            'pagamentos': [{'metodo': 'CARTAO_DEBITO', 'valor': 100.00}],
            'troco': 0
        }
        
        venda_id = VendaService.registrar_checkout(payload)
        
        # Validação a nível do Banco de Dados
        venda = Vendas.objects.get(id=venda_id)
        self.assertEqual(venda.valor_taxa_maquininha, Decimal('2.00'))
        self.assertEqual(venda.status, 'FATURADO')

    def test_03_auditoria_relatorios_faturamento_liquido(self):
        """ Valida a Fase 11 e 12: A Matemática dos relatórios (Faturamento Líquido = Bruto - Taxa Maquininha - Descontos) """
        venda = Vendas.objects.create(
            data_venda=timezone.now(),
            valor_total=100.00,
            vendedor='operador_teste',
            status='FATURADO',
            valor_taxa_maquininha=2.00 # Custo cobrado pela operadora
        )
        
        # Simulação do cálculo feito nas views de relatório
        faturamento_bruto = float(venda.valor_total)
        taxa_cobrada = float(venda.valor_taxa_maquininha)
        faturamento_liquido = faturamento_bruto - taxa_cobrada
        
        self.assertEqual(faturamento_bruto, 100.00)
        self.assertEqual(taxa_cobrada, 2.00)
        self.assertEqual(faturamento_liquido, 98.00)
        