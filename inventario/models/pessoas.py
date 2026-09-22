from django.db import models
from django.utils import timezone
from django_cryptography.fields import encrypt # 🚀 Novo módulo de segurança

class Clientes(models.Model):
    TIPO_PESSOA_CHOICES = [('PF', 'Pessoa Física'), ('PJ', 'Pessoa Jurídica')]
    tipo_pessoa = models.CharField(max_length=2, choices=TIPO_PESSOA_CHOICES, default='PF')
    nome = models.CharField(max_length=255)
    
    # 🚀 DADOS SENSÍVEIS CRIPTOGRAFADOS (LGPD)
    telefone = encrypt(models.CharField(max_length=20, blank=True, null=True))
    email = encrypt(models.EmailField(blank=True, null=True))
    cpf = encrypt(models.CharField(max_length=20, blank=True, null=True))
    cnpj = encrypt(models.CharField(max_length=20, blank=True, null=True))
    
    razao_social = models.CharField(max_length=255, blank=True, null=True)
    
    IND_IE_CHOICES = [
        ('1', '1 - Contribuinte ICMS (Informar IE)'),
        ('2', '2 - Contribuinte Isento de Inscrição'),
        ('9', '9 - Não Contribuinte (Pessoa Física ou Sem IE)'),
    ]
    ind_ie = models.CharField(max_length=1, choices=IND_IE_CHOICES, default='9', verbose_name="Indicador de Inscrição Estadual")
    inscricao_estadual = models.CharField(max_length=50, blank=True, null=True)
    
    cep = models.CharField(max_length=10, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    
    codigo_ibge = models.CharField(max_length=15, blank=True, null=True, help_text="Código de 7 dígitos do Município")
    
    tipo = models.CharField(max_length=50, default='CONSUMIDOR PADRÃO')
    data_cadastro = models.DateTimeField(default=timezone.now)
    pontos = models.IntegerField(default=0)
    
    class Meta: 
        db_table = 'inventario_clientes'

class Usuarios(models.Model):
    PERFIL_CHOICES = [
        ('Vendedor', 'Vendedor'),
        ('Gerente', 'Gerente'),
        ('Supervisor', 'Supervisor'),
        ('DEV', 'Desenvolvedor'), 
    ]
    login = models.CharField(max_length=100, unique=True)
    
    # 🚀 SENHAS CRIPTOGRAFADAS (Protege o texto-plano)
    senha = encrypt(models.CharField(max_length=100))
    
    perfil = models.CharField(max_length=50, choices=PERFIL_CHOICES, default='Vendedor')
    comissao = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    escala_semanal = models.JSONField(null=True, blank=True)
    loja = models.ForeignKey('inventario.LojaFilial', on_delete=models.SET_NULL, null=True, blank=True, related_name="funcionarios")

    class Meta:
        db_table = 'inventario_usuarios'
        