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
    
    # 🔥 A NOVA COLUNA PARA O NOSSO CHECKBOX:
    es_base_tintometrica = models.BooleanField(default=False)

    def __str__(self): 
        return f"{self.cod_interno} - {self.nome}"

    def save(self, *args, **kwargs):
        if not self.cod_interno:
            ultimo = Produtos.objects.all().order_by('id').last()
            self.cod_interno = str(int(ultimo.cod_interno) + 1).zfill(6) if ultimo and ultimo.cod_interno and ultimo.cod_interno.isdigit() else "000001"
        super().save(*args, **kwargs)


# ==============================================================================
# CLIENTES E USUÁRIOS
# ==============================================================================
class Clientes(models.Model):
    # Escolha de tipo de pessoa
    TIPO_PESSOA_CHOICES = [
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
    ]
    tipo_pessoa = models.CharField(max_length=2, choices=TIPO_PESSOA_CHOICES, default='PF')
    
    # Dados Gerais (Usados por ambos)
    nome = models.CharField(max_length=255)  # Nome completo (PF) ou Nome Fantasia (PJ)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Dados Específicos: Pessoa Física
    cpf = models.CharField(max_length=20, blank=True, null=True)
    
    # Dados Específicos: Pessoa Jurídica
    cnpj = models.CharField(max_length=20, blank=True, null=True)
    razao_social = models.CharField(max_length=255, blank=True, null=True)
    inscricao_estadual = models.CharField(max_length=50, blank=True, null=True)
    
    # Campos de Endereço (Preparados para o ViaCEP)
    cep = models.CharField(max_length=10, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)  # Rua/Logradouro
    numero = models.CharField(max_length=20, blank=True, null=True)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    
    # Controle do Sistema
    tipo = models.CharField(max_length=50, default='CONSUMIDOR PADRÃO') # Consumidor, Pintor, etc.
    data_cadastro = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.nome

    class Meta:
        db_table = 'inventario_clientes' # Boa prática para garantir o nome da tabela

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
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, default='VENDA')
    
    # NOVOS CAMPOS:
    troco = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pagamentos_texto = models.TextField(blank=True, null=True)
    
    # 🔥 CORREÇÃO: Voltou para CharField para aceitar texto do PDV e não dar erro no banco
    cliente = models.CharField(max_length=255, blank=True, null=True)
    
    indicante = models.CharField(max_length=255, blank=True, null=True)
    vendedor = models.CharField(max_length=100, blank=True, null=True)
    cupom_texto = models.TextField(blank=True, null=True)

    def __str__(self): return f"Venda {self.id}"

    class Meta:
        db_table = 'inventario_vendas'

    indicante = models.CharField(max_length=255, blank=True, null=True)
    vendedor = models.CharField(max_length=100, blank=True, null=True)
    cupom_texto = models.TextField(blank=True, null=True)

    def __str__(self): return f"Venda {self.id}"

    class Meta:
        db_table = 'inventario_vendas' # Garante que ele use esta tabela

class ConfiguracaoPontos(models.Model):
    tipo_usuario = models.CharField(max_length=20, unique=True)
    pontos_por_real = models.IntegerField(default=1)
    pontos_necessarios_resgate = models.IntegerField(default=30)
    valor_resgate_reais = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    def __str__(self): return f"Regra {self.tipo_usuario}"

# ==============================================================================
# SISTEMA TINTOMÉTRICO
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
        