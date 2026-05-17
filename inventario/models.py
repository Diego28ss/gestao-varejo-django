from django.db import models
from django.utils import timezone


# ==============================================================================
# TABELAS AUXILIARES
# ==============================================================================
class Marca(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome


class Familia(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome


# ==============================================================================
# TABELA DE PRODUTOS (ATUALIZADA: O RETORNO DO STATUS)
# ==============================================================================
class Produtos(models.Model):
    nome = models.CharField(max_length=255)
    cod_barras = models.CharField(max_length=100, blank=True, null=True)
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    margem_lucro = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estoque_atual = models.IntegerField(default=0)
    unidade = models.CharField(max_length=10, default='UN')

    # NOVO: O campo status voltou para esconder os inativos do PDV (Passo 1.1 e 1.4)
    status = models.CharField(max_length=20, default='ATIVO')

    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True)
    familia = models.ForeignKey(Familia, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.nome


# ==============================================================================
# TABELA DE CLIENTES (E PINTORES)
# ==============================================================================
class Clientes(models.Model):
    nome = models.CharField(max_length=255)
    cpf = models.CharField(max_length=20, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    tipo = models.CharField(max_length=50, default='CLIENTE')  # CLIENTE, PINTOR, CLIENTE E PINTOR

    # NÃO PODEMOS PERDER ESTA COLUNA (Sistema de Fidelidade)
    pontos = models.IntegerField(default=0)

    # NOVOS CAMPOS DE ENDEREÇO (Opcionais)
    cep = models.CharField(max_length=20, blank=True, null=True)
    rua = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=50, blank=True, null=True)
    complemento = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nome

# ==============================================================================
# TABELA DE COLABORADORES DA JB TINTAS
# ==============================================================================
class Usuarios(models.Model):
    login = models.CharField(max_length=100, unique=True)
    senha = models.CharField(max_length=100)
    perfil = models.CharField(max_length=50, default='Colaborador')
    comissao = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def __str__(self):
        return self.login


# ==============================================================================
# TABELA DE VENDAS E ORÇAMENTOS
# ==============================================================================
class Vendas(models.Model):
    STATUS_CHOICES = [
        ('VENDA', 'Venda Finalizada'),
        ('ORCAMENTO', 'Orçamento'),
    ]

    data_venda = models.DateTimeField(default=timezone.now)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vendedor = models.CharField(max_length=100, blank=True, null=True)
    cliente = models.CharField(max_length=255, blank=True, null=True)
    indicante = models.CharField(max_length=255, blank=True, null=True)
    cupom_texto = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='VENDA')

    def __str__(self):
        return f"{self.status} {self.id} - {self.cliente}"


# ==============================================================================
# TABELA DE CONFIGURAÇÃO DE PONTOS
# ==============================================================================
class ConfiguracaoPontos(models.Model):
    TIPO_CHOICES = [
        ('CLIENTE', 'Cliente Regular'),
        ('PINTOR', 'Pintor / Indicante'),
    ]
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_CHOICES, unique=True)
    pontos_por_real = models.IntegerField(default=1)
    pontos_necessarios_resgate = models.IntegerField(default=30)
    valor_resgate_reais = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)

    def __str__(self):
        return f"Regra {self.tipo_usuario}: {self.pontos_necessarios_resgate}pts = R$ {self.valor_resgate_reais}"