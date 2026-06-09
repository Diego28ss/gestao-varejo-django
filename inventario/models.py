from django.db import models
from django.utils import timezone

# ==============================================================================
# CONFIGURAÇÃO DO EMISSOR (JB TINTAS)
# ==============================================================================
class ConfiguracaoEmissor(models.Model):
    razao_social = models.CharField(max_length=255, default="JB TINTAS")
    cnpj = models.CharField(max_length=20)
    inscricao_estadual = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True) # Adicionado para contabilidade
    cep = models.CharField(max_length=10)
    endereco = models.CharField(max_length=255)
    numero = models.CharField(max_length=20)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    codigo_ibge = models.CharField(max_length=15)
    telefone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.razao_social} - {self.cnpj}"

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
# TABELA DE PRODUTOS (ATUALIZADA COM CAMPOS FISCAIS COMPLETOS)
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
    es_base_tintometrica = models.BooleanField(default=False)

    # DADOS FISCAIS
    ncm = models.CharField(max_length=15, default='32091010') 
    cfop = models.CharField(max_length=10, default='5102')    
    cst_csosn = models.CharField(max_length=10, default='0102') 
    
    # NOVOS CAMPOS FISCAIS AVANÇADOS
    cest = models.CharField(max_length=10, blank=True, null=True)
    origem = models.CharField(max_length=1, default='0') # 0=Nacional, 1=Importado
    aliquota_icms = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    unidade_tributavel = models.CharField(max_length=10, default='UN')

    def __str__(self): 
        return f"{self.cod_interno} - {self.nome}"

    def save(self, *args, **kwargs):
        if not self.cod_interno:
            ultimo = Produtos.objects.all().order_by('id').last()
            self.cod_interno = str(int(ultimo.cod_interno) + 1).zfill(6) if ultimo and ultimo.cod_interno and ultimo.cod_interno.isdigit() else "000001"
        super().save(*args, **kwargs)

# ==============================================================================
# CLIENTES, USUÁRIOS, VENDAS E TINTOMÉTRICO (SEM ALTERAÇÕES)
# ==============================================================================
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
    class Meta: db_table = 'inventario_clientes'

class Usuarios(models.Model):
    login = models.CharField(max_length=100, unique=True)
    senha = models.CharField(max_length=100)
    perfil = models.CharField(max_length=50, default='Colaborador')
    comissao = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

class Vendas(models.Model):
    data_venda = models.DateTimeField(default=timezone.now)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, default='VENDA')
    troco = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pagamentos_texto = models.TextField(blank=True, null=True)
    cliente = models.CharField(max_length=255, blank=True, null=True)
    indicante = models.CharField(max_length=255, blank=True, null=True)
    vendedor = models.CharField(max_length=100, blank=True, null=True)
    cupom_texto = models.TextField(blank=True, null=True)
    status_fiscal = models.CharField(max_length=50, default='SEM_NOTA')
    chave_acesso = models.CharField(max_length=50, blank=True, null=True)
    numero_nota = models.CharField(max_length=20, blank=True, null=True)
    motivo_erro = models.TextField(blank=True, null=True)
    arquivo_pdf = models.FileField(upload_to='notas_fiscais/pdfs/', blank=True, null=True)
    arquivo_xml = models.FileField(upload_to='notas_fiscais/xmls/', blank=True, null=True)
    class Meta: db_table = 'inventario_vendas'

class ConfiguracaoPontos(models.Model):
    tipo_usuario = models.CharField(max_length=20, unique=True)
    pontos_por_real = models.IntegerField(default=1)
    pontos_necessarios_resgate = models.IntegerField(default=30)
    valor_resgate_reais = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)

class RelacaoEmbalagensTintometrico(models.Model):
    codigo_base_tintometrico = models.CharField(max_length=100)
    tamanho_codigo = models.CharField(max_length=20)
    produto_cod_interno = models.ForeignKey(
        Produtos, to_field='cod_interno', on_delete=models.DO_NOTHING,  
        db_column='produto_cod_interno', db_constraint=False           
    )
    class Meta:
        db_table = 'relacao_embalagens_tintometrico'
        unique_together = ('codigo_base_tintometrico', 'tamanho_codigo')
        
# ==============================================================================
# TABELA DE DADOS FISCAIS (NF-e / NFC-e)
# ==============================================================================
class DadosNF(models.Model):
    # Liga esta nota diretamente a uma Venda específica
    venda = models.OneToOneField(Vendas, on_delete=models.CASCADE, related_name='dados_nf')
    
    # Liga ao Cliente para puxarmos o endereço, CPF, etc.
    cliente = models.ForeignKey(Clientes, on_delete=models.SET_NULL, null=True, blank=True)

    # --------------------------------------------------
    # BLOCO 1: CABEÇALHO DA NOTA
    # --------------------------------------------------
    TIPO_NOTA_CHOICES = [
        ('SAIDA', 'Saída'),
        ('ENTRADA', 'Entrada'),
    ]
    tipo_nota = models.CharField(max_length=10, choices=TIPO_NOTA_CHOICES, default='SAIDA')
    
    # Ex: Venda de mercadoria, Devolução, etc.
    natureza_operacao = models.CharField(max_length=100, default='Venda de mercadoria')
    
    # Ex: 5102, 5101, etc.
    cfop = models.CharField(max_length=5, default='5102')
    
    CONSUMIDOR_FINAL_CHOICES = [
        ('1', '1 - Sim'),
        ('0', '0 - Não'),
    ]
    consumidor_final = models.CharField(max_length=1, choices=CONSUMIDOR_FINAL_CHOICES, default='1')
    
    data_emissao = models.DateTimeField(default=timezone.now)
    
    INDICADOR_PRESENCA_CHOICES = [
        ('0', '0 - Não se aplica'),
        ('1', '1 - Operação presencial'),
        ('2', '2 - Operação não presencial, pela Internet'),
        ('3', '3 - Operação não presencial, Teleatendimento'),
        ('4', '4 - NFC-e em operação com entrega a domicílio'),
        ('5', '5 - Operação presencial, fora do estabelecimento'),
    ]
    indicador_presenca = models.CharField(max_length=1, choices=INDICADOR_PRESENCA_CHOICES, default='1')
    
    informacoes_complementares = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'dados_nf'

    def __str__(self):
        return f"Dados Fiscais - Venda #{self.venda.id}"