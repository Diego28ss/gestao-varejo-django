from django.db import models
from inventario.models import Usuarios # Importe para vincular quem criou o inventário

# 🚀 NOVA TABELA: ENDEREÇAMENTO INTELIGENTE (WMS)
class SessaoEstoque(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

class Marca(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

class Familia(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

class Produtos(models.Model):
    nome = models.CharField(max_length=255)
    cod_barras = models.CharField(max_length=255, blank=True, null=True)
    cod_forn = models.CharField(max_length=100, blank=True, null=True)
    aviso_estoque = models.CharField(max_length=255, blank=True, null=True) 
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    margem_lucro = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estoque_atual = models.IntegerField(default=0)
    qtd_em_transito = models.IntegerField(default=0)
    data_previsao_chegada = models.DateField(blank=True, null=True)
    unidade = models.CharField(max_length=10, default='UN')
    cod_interno = models.CharField(max_length=50, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, default='ATIVO')
    cor = models.CharField(max_length=100, blank=True, null=True)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True)
    familia = models.ForeignKey(Familia, on_delete=models.SET_NULL, null=True, blank=True)
    
    # 🚀 VÍNCULO DE APRENDIZADO: Onde este produto fica guardado?
    sessao_estoque = models.ForeignKey('SessaoEstoque', on_delete=models.SET_NULL, null=True, blank=True, related_name="produtos")
    
    es_base_tintometrica = models.BooleanField(default=False)
    ncm = models.CharField(max_length=15, default='32091010') 
    cst_csosn = models.CharField(max_length=50, default='0102')
    cest = models.CharField(max_length=10, blank=True, null=True)
    origem = models.CharField(max_length=1, default='0')
    aliquota_icms = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    unidade_tributavel = models.CharField(max_length=10, default='UN')

    def __str__(self): return f"{self.cod_interno} - {self.nome}"

    def save(self, *args, **kwargs):
        if not self.cod_interno:
            ultimo = Produtos.objects.all().order_by('id').last()
            self.cod_interno = str(int(ultimo.cod_interno) + 1).zfill(6) if ultimo and ultimo.cod_interno and ultimo.cod_interno.isdigit() else "000001"
        super().save(*args, **kwargs)

# ==========================================
# 🚀 NOVA TABELA: GESTÃO DE RUPTURA DE ESTOQUE
# ==========================================
class RupturaEstoque(models.Model):
    produto = models.ForeignKey(Produtos, on_delete=models.CASCADE, related_name="rupturas")
    quantidade_perdida = models.IntegerField(default=1)
    data_registro = models.DateTimeField(auto_now_add=True)
    resolvido = models.BooleanField(default=False) 

    def __str__(self):
        return f"Ruptura: {self.produto.nome} ({self.quantidade_perdida} {self.produto.unidade})"

# ==========================================
# 🚀 NOVAS TABELAS: INVENTÁRIO POR SESSÃO
# ==========================================
class InventarioSessao(models.Model):
    STATUS_CHOICES = [
        ('ABERTO', 'Aberto (Em Contagem)'),
        ('FINALIZADO', 'Finalizado (Auditado)')
    ]
    
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_finalizacao = models.DateTimeField(null=True, blank=True)
    criado_por = models.ForeignKey('Usuarios', on_delete=models.SET_NULL, null=True, related_name="inventarios_criados")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTO')
    
    # 🚀 O LOTE INTEIRO FICA AMARRADO À SESSÃO ESCOLHIDA
    sessao_estoque = models.ForeignKey('SessaoEstoque', on_delete=models.CASCADE, null=True, blank=True)

    def qtd_itens_contados(self):
        return self.itens_contados.count()

    def __str__(self):
        return f"Inventário #{self.id} - {self.status}"

class InventarioItem(models.Model):
    sessao = models.ForeignKey(InventarioSessao, on_delete=models.CASCADE, related_name="itens_contados")
    produto = models.ForeignKey(Produtos, on_delete=models.CASCADE)
    
    # Congela o estoque que o sistema achava que tinha no momento da bipagem
    saldo_sistema = models.IntegerField(default=0) 
    
    # Quantidade real que o operador contou na prateleira
    saldo_fisico = models.IntegerField(default=0)
    
    data_contagem = models.DateTimeField(auto_now_add=True)

    @property
    def divergencia(self):
        return self.saldo_fisico - self.saldo_sistema

    def __str__(self):
        return f"{self.produto.nome} | Físico: {self.saldo_fisico} vs Sis: {self.saldo_sistema}"
    