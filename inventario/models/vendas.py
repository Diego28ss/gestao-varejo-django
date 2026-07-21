from django.db import models
from django.utils import timezone
from .pessoas import Clientes

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
    
    # --- CAMPOS FISCAIS ---
    status_fiscal = models.CharField(max_length=50, default='SEM_NOTA')
    chave_acesso = models.CharField(max_length=50, blank=True, null=True)
    numero_nota = models.CharField(max_length=20, blank=True, null=True)
    motivo_erro = models.TextField(blank=True, null=True)
    modelo_fiscal = models.CharField(max_length=10, blank=True, null=True) 
    
    # Arquivos baixados e salvos localmente
    arquivo_pdf = models.FileField(upload_to='notas_fiscais/pdfs/', blank=True, null=True)
    arquivo_xml = models.FileField(upload_to='notas_fiscais/xmls/', blank=True, null=True)
    
    # --- INTEGRAÇÃO GERANDO NOTA FÁCIL ---
    id_transacao_api = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID Transação GNF")
    link_pdf = models.URLField(max_length=500, blank=True, null=True, verbose_name="Link DANFE Online")
    link_xml = models.URLField(max_length=500, blank=True, null=True, verbose_name="Link XML Online")

    class Meta: 
        db_table = 'inventario_vendas'
        
class DadosNF(models.Model):
    venda = models.OneToOneField(Vendas, on_delete=models.CASCADE, related_name='dados_nf')
    cliente = models.ForeignKey(Clientes, on_delete=models.SET_NULL, null=True, blank=True)

    TIPO_NOTA_CHOICES = [('SAIDA', 'Saída'), ('ENTRADA', 'Entrada')]
    tipo_nota = models.CharField(max_length=10, choices=TIPO_NOTA_CHOICES, default='SAIDA')
    natureza_operacao = models.CharField(max_length=100, default='Venda de mercadoria')
    cfop = models.CharField(max_length=5, default='5102')
    
    CONSUMIDOR_FINAL_CHOICES = [('1', '1 - Sim'), ('0', '0 - Não')]
    consumidor_final = models.CharField(max_length=1, choices=CONSUMIDOR_FINAL_CHOICES, default='1')
    data_emissao = models.DateTimeField(default=timezone.now)
    
    INDICADOR_PRESENCA_CHOICES = [
        ('0', '0 - Não se aplica'), ('1', '1 - Operação presencial'),
        ('2', '2 - Operação não presencial, pela Internet'),
        ('3', '3 - Operação não presencial, Teleatendimento'),
        ('4', '4 - NFC-e em operação com entrega a domicílio'),
        ('5', '5 - Operação presencial, fora do estabelecimento'),
    ]
    indicador_presenca = models.CharField(max_length=1, choices=INDICADOR_PRESENCA_CHOICES, default='1')
    informacoes_complementares = models.TextField(blank=True, null=True)

    pis_cst = models.CharField(max_length=5, default='07')
    cofins_cst = models.CharField(max_length=5, default='07')

    class Meta:
        db_table = 'dados_nf'

    def __str__(self):
        return f"Dados Fiscais - Venda #{self.venda.id}"
    