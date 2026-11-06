import json
from django.test import TestCase, Client
from inventario.models import Produtos, Usuarios

class Blocos3e4Tests(TestCase):
    def setUp(self):
        """ Configuração inicial dos testes para Comissões e Tintométrico """
        self.client = Client()
        
        # Cria um Gerente de teste
        self.gerente = Usuarios.objects.create(
            login='gerente_teste', 
            perfil='Gerente', 
            senha='123'
        )
        
        # Cria um produto Base para testar o tintométrico
        self.produto_base = Produtos.objects.create(
            nome='Base Tinta Fosca', 
            estoque_atual=10, 
            preco_venda=50.00, 
            es_base_tintometrica=True
        )

    def test_bloco3_protecao_relatorio_comissao(self):
        """ Bloco 3 (Fase 8): Garante que o relatório de comissões está protegido contra acessos não autorizados """
        
        # Tenta acessar sem login (Deve ser bloqueado pela nossa regra de segurança)
        response_bloqueada = self.client.get('/gerenciapainel/relatoriospainel/comissao/')
        
        # Valida se o sistema bloqueou (302) e redirecionou para o login
        self.assertEqual(response_bloqueada.status_code, 302)
        self.assertEqual(response_bloqueada.url, '/') 

    def test_bloco4_protecao_api_tintometrico(self):
        """ Bloco 4 (Fase 10): Garante que a API de vinculação tintométrica tem validação de dados """
        
        session = self.client.session
        session['usuario_logado'] = 'gerente_teste'
        session['perfil_usuario'] = 'Gerente'
        session.save()
        
        # Envia um payload propositalmente VAZIO para testar a validação da API
        payload_invalido = {}
        
        response = self.client.post(
            '/api/vincular-base/', 
            data=json.dumps(payload_invalido), 
            content_type='application/json'
        )
        
        dados = response.json()
        
        # A API deve perceber que faltam dados e retornar um 'erro' de forma elegante
        self.assertEqual(response.status_code, 200)
        self.assertEqual(dados['status'], 'erro', msg="A API permitiu vincular uma base sem enviar os dados obrigatórios!")
        