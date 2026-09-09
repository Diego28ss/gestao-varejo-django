from django.db import models
from django.utils import timezone

class Clientes(models.Model):
    TIPO_PESSOA_CHOICES = [('PF', 'Pessoa Física'), ('PJ', 'Pessoa Jurídica')]
    tipo_pessoa = models.CharField(max_length=2, choices=TIPO_PESSOA_CHOICES, default='PF')
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    cpf = models.CharField(max_length=20, blank=True, null=True)
    cnpj = models.CharField(max_length=20, blank=True, null=True)
    razao_social = models.CharField(max_length=255, blank=True, null=True)
    inscricao_estadual = models.CharField(max_length=50, blank=True, null=True)
    cep = models.CharField(max_length=10, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    codigo_ibge = models.CharField(max_length=15, blank=True, null=True)
    tipo = models.CharField(max_length=50, default='CONSUMIDOR PADRÃO')
    data_cadastro = models.DateTimeField(default=timezone.now)
    
    # 🚀 NOVA COLUNA: Sistema de Fidelidade
    pontos = models.IntegerField(default=0)
    
    class Meta: 
        db_table = 'inventario_clientes'

class Usuarios(models.Model):
    PERFIL_CHOICES = [
        ('Vendedor', 'Vendedor'),
        ('Gerente', 'Gerente'),
        ('Supervisor', 'Supervisor'),
        ('DEV', 'Desenvolvedor'), # 🚀 NOVO PERFIL INVISÍVEL
    ]

    login = models.CharField(max_length=100, unique=True)
    senha = models.CharField(max_length=100)
    perfil = models.CharField(max_length=50, choices=PERFIL_CHOICES, default='Vendedor')
    comissao = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    escala_semanal = models.JSONField(null=True, blank=True)

    # 🚀 NOVO VÍNCULO: O Local de Trabalho (Filial) do Colaborador
    loja = models.ForeignKey(
        'inventario.LojaFilial', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="funcionarios"
    )

    class Meta:
        db_table = 'inventario_usuarios'
        