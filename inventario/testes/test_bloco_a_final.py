import json
from django.test import TestCase, Client
from django.urls import reverse
from inventario.models import Usuarios
from inventario.models.caixa import ControleCaixa

class BlocoAFinalTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Criação do Gerente
        self.gerente = Usuarios.objects.create(
            login='gerente.teste', senha='123', perfil='Gerente', status='ATIVO'
        )
        
        # Criação de Dois Operadores
        self.operador1 = Usuarios.objects.create(
            login='paollal.tec', senha='123', perfil='Vendedor', status='ATIVO'
        )
        self.operador2 = Usuarios.objects.create(
            login='teste2.tec', senha='123', perfil='Vendedor', status='ATIVO'
        )

        # Loga o gerente na sessão inicial para permitir exclusão no RH
        session = self.client.session
        session['usuario_logado'] = self.gerente.login
        session['perfil_usuario'] = self.gerente.perfil
        session.save()
        
    def test_abertura_multiplos_caixas(self):
        """ Valida se dois operadores diferentes podem abrir caixa na mesma máquina """
        dados_op1 = {
            'lastro': 100.00, 'operador_login': self.operador1.login, 'operador_senha': self.operador1.senha,
            'gerente_login': self.gerente.login, 'gerente_senha': self.gerente.senha
        }
        dados_op2 = {
            'lastro': 50.00, 'operador_login': self.operador2.login, 'operador_senha': self.operador2.senha,
            'gerente_login': self.gerente.login, 'gerente_senha': self.gerente.senha
        }
        
        # Abre o caixa 1
        resp1 = self.client.post(reverse('api_abrir_caixa'), data=json.dumps(dados_op1), content_type='application/json')
        self.assertEqual(resp1.json()['status'], 'sucesso')
        
        # Abre o caixa 2
        resp2 = self.client.post(reverse('api_abrir_caixa'), data=json.dumps(dados_op2), content_type='application/json')
        self.assertEqual(resp2.json()['status'], 'sucesso')
        
        # Verifica no banco se existem 2 caixas abertos
        caixas_abertos = ControleCaixa.objects.filter(status='ABERTO').count()
        self.assertEqual(caixas_abertos, 2)

    def test_bloqueio_caixa_duplicado(self):
        """ Valida se o sistema impede o mesmo operador de ter 2 caixas abertos """
        ControleCaixa.objects.create(operador=self.operador1, gerente_abertura=self.gerente, lastro_inicial=100.00, status='ABERTO')
        
        dados_duplicados = {
            'lastro': 50.00, 'operador_login': self.operador1.login, 'operador_senha': self.operador1.senha,
            'gerente_login': self.gerente.login, 'gerente_senha': self.gerente.senha
        }
        
        resposta = self.client.post(reverse('api_abrir_caixa'), data=json.dumps(dados_duplicados), content_type='application/json')
        self.assertEqual(resposta.json()['status'], 'erro')
        self.assertIn('já possui um caixa em andamento', resposta.json()['mensagem'])

    def test_retomar_caixa_senha_correta(self):
        """ Valida se a rota de retomar caixa com dupla autenticação funciona e atualiza a sessão """
        ControleCaixa.objects.create(operador=self.operador1, gerente_abertura=self.gerente, lastro_inicial=100.00, status='FECHADO_TEMP')
        
        # 🚀 CORREÇÃO: O teste agora envia a dupla autenticação e o lastro obrigatórios
        dados = {
            'operador_login': self.operador1.login, 
            'operador_senha': self.operador1.senha,
            'gerente_login': self.gerente.login,
            'gerente_senha': self.gerente.senha,
            'lastro': 100.00
        }
        
        resposta = self.client.post(reverse('api_retomar_caixa'), data=json.dumps(dados), content_type='application/json')
        
        self.assertEqual(resposta.json()['status'], 'sucesso')
        self.assertEqual(self.client.session['usuario_logado'], self.operador1.login)

    def test_soft_delete_rh(self):
        """ Valida se um operador com histórico de caixa é inativado em vez de excluído """
        # Cria um histórico para amarrar o usuário
        ControleCaixa.objects.create(operador=self.operador1, gerente_abertura=self.gerente, lastro_inicial=100.00, status='FECHADO')
        
        # Tenta excluir a Paolla pelo RH
        resposta = self.client.get(reverse('excluir_colaborador', args=[self.operador1.id]))
        
        # A resposta deve redirecionar (302) e o usuário deve estar INATIVO no banco, não apagado
        self.assertEqual(resposta.status_code, 302)
        self.operador1.refresh_from_db()
        self.assertEqual(self.operador1.status, 'INATIVO')
