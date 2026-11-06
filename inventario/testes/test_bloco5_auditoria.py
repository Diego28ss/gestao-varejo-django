import json
from django.test import TestCase, Client
from inventario.models import Produtos, Usuarios, AuditoriaEstoque

class Bloco5AuditoriaTests(TestCase):
    def setUp(self):
        """ Configuração inicial antes de cada teste rodar """
        self.client = Client()
        
        # 1. Cria um usuário Gerente de teste
        self.usuario = Usuarios.objects.create(
            login='gerente_teste', 
            perfil='Gerente', 
            senha='123'
        )
        
        # 2. Cria um Produto de teste com 10 unidades
        self.produto = Produtos.objects.create(
            nome='Lata de Tinta Teste',
            cod_interno='000999',
            estoque_atual=10,
            preco_custo=50.00,
            preco_venda=100.00
        )

    def test_bloqueio_tela_acerto_sem_login(self):
        """ Testa se a tela bloqueia o acesso e redireciona (Regra de Negócio) """
        # Tenta acessar sem sessão ativa
        response = self.client.get('/estoquepainel/acerto-estoque/')
        # Deve ser redirecionado para a tela de login (Código 302)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/') 

    def test_api_processar_acerto_e_auditoria(self):
        """ Testa a API de Acerto e a gravação na Caixa Preta (Fases 11 e 12) """
        
        # Simula o login na sessão para validar a API
        session = self.client.session
        session['usuario_logado'] = 'gerente_teste'
        session['perfil_usuario'] = 'Gerente'
        session.save()
        
        payload = {
            'itens': [
                {
                    'id': self.produto.id, 
                    'nova_qtd': 15, # Subindo de 10 para 15 (+5)
                    'motivo': 'Teste Automatizado de Entrada'
                }
            ]
        }

        response = self.client.post(
            '/api/processar-acerto-estoque/', 
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # 1. Verifica se a API respondeu Sucesso
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'sucesso')
        
        # 2. Verifica se o estoque do produto foi atualizado no banco
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, 15)
        
        # 3. Verifica se a Caixa Preta (Auditoria) gravou corretamente
        auditoria = AuditoriaEstoque.objects.filter(produto=self.produto).first()
        self.assertIsNotNone(auditoria, "O registro de auditoria não foi criado!")
        self.assertEqual(auditoria.tipo_operacao, 'ACERTO_MANUAL')
        self.assertEqual(auditoria.variacao, 5)
        self.assertEqual(auditoria.saldo_anterior, 10)
        self.assertEqual(auditoria.saldo_novo, 15)
        self.assertEqual(auditoria.motivo, 'Teste Automatizado de Entrada')
        self.assertEqual(auditoria.usuario, self.usuario)

    def test_api_rejeitar_acerto_sem_login(self):
        """ Garante que a API não processa acertos sem usuário logado """
        
        # Payload com dados válidos, mas sessão vazia
        payload = {'itens': [{'id': self.produto.id, 'nova_qtd': 50}]}
        response = self.client.post(
            '/api/processar-acerto-estoque/', 
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Deve rejeitar a operação e proteger o banco
        self.assertEqual(response.json()['status'], 'erro')
        self.assertEqual(response.json()['mensagem'], 'Usuário inválido ou sessão expirada.')
        