from django.db import models

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
    
    # 🚀 NOVA COLUNA ADICIONADA PARA OS AVISOS DE REAJUSTE DE PREÇO
    aviso_estoque = models.CharField(max_length=255, blank=True, null=True) 
    
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

    ncm = models.CharField(max_length=15, default='32091010') 
    cst_csosn = models.CharField(max_length=10, default='0102') 
    cest = models.CharField(max_length=10, blank=True, null=True)
    origem = models.CharField(max_length=1, default='0')
    aliquota_icms = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    unidade_tributavel = models.CharField(max_length=10, default='UN')

    def __str__(self): 
        return f"{self.cod_interno} - {self.nome}"

    def save(self, *args, **kwargs):
        if not self.cod_interno:
            ultimo = Produtos.objects.all().order_by('id').last()
            self.cod_interno = str(int(ultimo.cod_interno) + 1).zfill(6) if ultimo and ultimo.cod_interno and ultimo.cod_interno.isdigit() else "000001"
        super().save(*args, **kwargs)
        