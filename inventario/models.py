from django.db import models
from django.utils import timezone

# ==============================================================================
# TABELAS AUXILIARES
# ==============================================================================
class Marca(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

class Familia(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

# ==============================================================================
# TABELA DE PRODUTOS
# ==============================================================================
class Produtos(models.Model):
    nome = models.CharField(max_length=255)
    cod_barras = models.CharField(max_length=255, blank=True, null=True)
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    margem_lucro = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estoque_atual = models.IntegerField(default=0)
    unidade = models.CharField(max_length=10, default='UN')
    cod_interno = models.CharField(max_length=50, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, default='ATIVO')
    cor = models.CharField(max_length=100, blank=True, null=True)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True)
    familia = models.ForeignKey(Familia, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self): return f"{self.cod_interno} - {self.nome}"

    def save(self, *args, **kwargs):
        if not self.cod_interno:
            ultimo = Produtos.objects.all().order_by('id').last()
            self.cod_interno = str(int(ultimo.cod_interno) + 1).zfill(6) if ultimo and ultimo.cod_interno and ultimo.cod_interno.isdigit() else "000001"
        super().save(*args, **kwargs)

# ==============================================================================
# CLIENTES E USUÁRIOS
# ==============================================================================
class Clientes(models.Model):
    nome = models.CharField(max_length=255)
    cpf = models.CharField(max_length=20, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    tipo = models.CharField(max_length=50, default='CLIENTE')
    pontos = models.IntegerField(default=0)
    def __str__(self): return self.nome

class Usuarios(models.Model):
    login = models.CharField(max_length=100, unique=True)
    senha = models.CharField(max_length=100)
    perfil = models.CharField(max_length=50, default='Colaborador')
    comissao = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    def __str__(self): return self.login

# ==============================================================================
# VENDAS E PONTOS
# ==============================================================================
class Vendas(models.Model):
    data_venda = models.DateTimeField(default=timezone.now)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, default='VENDA')
    cliente = models.ForeignKey(Clientes, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self): return f"Venda {self.id}"

class ConfiguracaoPontos(models.Model):
    tipo_usuario = models.CharField(max_length=20, unique=True)
    pontos_por_real = models.IntegerField(default=1)
    pontos_necessarios_resgate = models.IntegerField(default=30)
    valor_resgate_reais = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    def __str__(self): return f"Regra {self.tipo_usuario}"

# ==============================================================================
# SISTEMA TINTOMÉTRICO (NOVA TABELA)
# ==============================================================================
class RelacaoEmbalagensTintometrico(models.Model):
    codigo_base_tintometrico = models.CharField(max_length=100)
    tamanho_codigo = models.CharField(max_length=20)
    produto_cod_interno = models.ForeignKey(
        Produtos, 
        to_field='cod_interno', 
        on_delete=models.DO_NOTHING,  
        db_column='produto_cod_interno',
        db_constraint=False           
    )
    class Meta:
        db_table = 'relacao_embalagens_tintometrico'
        unique_together = ('codigo_base_tintometrico', 'tamanho_codigo')
        