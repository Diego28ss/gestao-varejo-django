from django.db import models

class ConfiguracaoEmissor(models.Model):
    razao_social = models.CharField(max_length=255, default="JB TINTAS")
    cnpj = models.CharField(max_length=20)
    inscricao_estadual = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True) 
    cep = models.CharField(max_length=10)
    endereco = models.CharField(max_length=255)
    numero = models.CharField(max_length=20)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    codigo_ibge = models.CharField(max_length=15)
    telefone = models.CharField(max_length=20, blank=True, null=True)

    # --- NOVAS CREDENCIAIS: GERANDO NOTA FÁCIL ---
    token_gnf = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Token Gerando Nota Fácil",
        help_text="Insira o Token de Acesso gerado no painel da API."
    )
    
    AMBIENTE_CHOICES = (
        ('producao', 'Produção'),
        ('homologacao', 'Homologação (Testes)'),
    )
    ambiente_gnf = models.CharField(
        max_length=20, 
        choices=AMBIENTE_CHOICES, 
        default='homologacao',
        verbose_name="Ambiente de Emissão"
    )

    def __str__(self):
        return f"{self.razao_social} - {self.cnpj}"

    class Meta:
        verbose_name = "Configuração do Emissor"
        verbose_name_plural = "Configurações do Emissor"

class ConfiguracaoPontos(models.Model):
    tipo_usuario = models.CharField(max_length=20, unique=True)
    pontos_por_real = models.IntegerField(default=1)
    pontos_necessarios_resgate = models.IntegerField(default=30)
    valor_resgate_reais = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)