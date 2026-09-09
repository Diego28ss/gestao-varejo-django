from django.db import models
from django.utils import timezone

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

class ConfiguracaoSistema(models.Model):
    dias_seguranca_estoque = models.IntegerField(default=15, verbose_name="Dias de Segurança do Estoque")
    
    # NOVOS CAMPOS PARA CONTROLE DE PONTUAÇÃO
    modulo_pontuacao_cliente_ativo = models.BooleanField(default=True, verbose_name="Ativar Pontuação para Clientes")
    modulo_pontuacao_pintor_ativo = models.BooleanField(default=True, verbose_name="Ativar Pontuação para Pintores/Indicantes")

    class Meta:
        verbose_name = "Configuração do Sistema"
        verbose_name_plural = "Configurações do Sistema"

class LojaFilial(models.Model):
    nome = models.CharField(max_length=100, unique=True, help_text="Ex: JB Tintas Tatuapé")
    codigo_ibge = models.CharField(max_length=10, help_text="Ex: 3550308")
    
    # O "Cofre" do Robô: O sistema olha para essa data. Se fizer mais de 90 dias, ele busca na API de novo.
    ultima_busca_feriados = models.DateField(null=True, blank=True)

    def precisa_atualizar_feriados(self):
        if not self.ultima_busca_feriados:
            return True
        dias_passados = (timezone.now().date() - self.ultima_busca_feriados).days
        return dias_passados >= 90 # Gatilho de 3 meses

    def __str__(self):
        return self.nome

class FeriadoLocal(models.Model):
    loja = models.ForeignKey(LojaFilial, on_delete=models.CASCADE, related_name="feriados")
    data = models.DateField()
    nome = models.CharField(max_length=150)
    tipo = models.CharField(max_length=50) # Ex: Nacional, Estadual, Municipal

    class Meta:
        unique_together = ('loja', 'data') # Impede duplicar o mesmo feriado na mesma loja

    def __str__(self):
        return f"{self.data.strftime('%d/%m/%Y')} - {self.nome} ({self.loja.nome})"
    