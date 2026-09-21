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
    
    # --- NOVO: Indicador da Inscrição Estadual (Obrigatório SEFAZ NF-e 55) ---
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
    
    # Obrigatório SEFAZ caso haja endereço completo (NF-e Mod. 55)
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
    senha = models.CharField(max_length=100)
    perfil = models.CharField(max_length=50, choices=PERFIL_CHOICES, default='Vendedor')
    comissao = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    escala_semanal = models.JSONField(null=True, blank=True)
    loja = models.ForeignKey('inventario.LojaFilial', on_delete=models.SET_NULL, null=True, blank=True, related_name="funcionarios")

    class Meta:
        db_table = 'inventario_usuarios'
        