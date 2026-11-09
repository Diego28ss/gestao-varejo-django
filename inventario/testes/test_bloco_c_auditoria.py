import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from inventario.models import Usuarios

class BlocoCAuditoriaTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # 1. Criação de um Gerente (Autorizado)
        self.gerente = Usuarios.objects.create(
            login='gerente.nfe', 
            senha='123', 
            perfil='Gerente', 
            status='ATIVO'
        )
        
        # 2. Criação de um Operador Comum (Não Autorizado)
        self.operador = Usuarios.objects.create(
            login='operador.nfe', 
            senha='123', 
            perfil='Vendedor', 
            status='ATIVO'
        )
        
        # Loga o operador na sessão para simular o uso normal do sistema
        session = self.client.session
        session['usuario_logado'] = self.operador.login
        session['perfil_usuario'] = self.operador.perfil
        session.save()

    @patch('inventario.views.estoque.estoque_entrada_views.efetivar_lote_nfe')
    def test_01_efetivar_nfe_sem_gerente_falha(self, mock_efetivar):
        """ Fase 13: Valida se o sistema bloqueia a entrada de NFe se a senha do gerente estiver errada """
        dados = {
            'itens': [{'codigo_interno': '123', 'qtd_final': 10}],
            'gerente_login': self.gerente.login,
            'gerente_senha': 'senha_errada'
        }
        
        resposta = self.client.post(reverse('api_efetivar_nfe'), data=json.dumps(dados), content_type='application/json')
        
        self.assertEqual(resposta.status_code, 401)
        self.assertIn('Credenciais da gerência inválidas', resposta.json()['erro'])
        mock_efetivar.assert_not_called() # Garante que a NFe NÃO foi salva

    @patch('inventario.views.estoque.estoque_entrada_views.efetivar_lote_nfe')
    def test_02_efetivar_nfe_com_operador_falha(self, mock_efetivar):
        """ Fase 13: Valida se o sistema bloqueia caso tentem usar um login válido, mas que não é gerente """
        dados = {
            'itens': [{'codigo_interno': '123', 'qtd_final': 10}],
            'gerente_login': self.operador.login,
            'gerente_senha': self.operador.senha
        }
        
        resposta = self.client.post(reverse('api_efetivar_nfe'), data=json.dumps(dados), content_type='application/json')
        
        self.assertEqual(resposta.status_code, 403)
        self.assertIn('não possui perfil de Gerência', resposta.json()['erro'])
        mock_efetivar.assert_not_called()

    @patch('inventario.views.estoque.estoque_entrada_views.efetivar_lote_nfe')
    def test_03_efetivar_nfe_com_gerente_sucesso(self, mock_efetivar):
        """ Fase 13: Valida se o sistema permite salvar a NFe com credenciais corretas do Gerente """
        mock_efetivar.return_value = 1 # Simula que 1 produto foi processado com sucesso
        
        dados = {
            'itens': [{'codigo_interno': '123', 'qtd_final': 10, 'custo_unitario': 5.00}],
            'gerente_login': self.gerente.login,
            'gerente_senha': self.gerente.senha
        }
        
        resposta = self.client.post(reverse('api_efetivar_nfe'), data=json.dumps(dados), content_type='application/json')
        
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()['sucesso'])
        mock_efetivar.assert_called_once() # Garante que o serviço de salvar no banco foi chamado

    @patch('inventario.views.estoque.estoque_entrada_views.estornar_lote_nfe')
    def test_04_cancelar_nfe_com_gerente_sucesso(self, mock_estornar):
        """ Fase 13: Valida a segurança no estorno (cancelamento) da NFe """
        mock_estornar.return_value = 1
        
        dados = {
            'itens': [{'codigo_interno': '123', 'qtd_final': 10}],
            'gerente_login': self.gerente.login,
            'gerente_senha': self.gerente.senha
        }
        
        resposta = self.client.post(reverse('api_estornar_nfe'), data=json.dumps(dados), content_type='application/json')
        
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()['sucesso'])
        mock_estornar.assert_called_once()
        