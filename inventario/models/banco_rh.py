from django.db import models
from django.utils import timezone

class PontoEletronico(models.Model):
    # Nota de Segurança: Não criptografado pois participa de uma restrição 'unique_together'. 
    # Criptografar campos de índice quebra a verificação nativa do banco de dados.
    colaborador_login = models.CharField(max_length=100)
    data = models.DateField(default=timezone.now)
    
    entrada_1 = models.TimeField(null=True, blank=True)
    saida_1 = models.TimeField(null=True, blank=True)
    entrada_2 = models.TimeField(null=True, blank=True)
    saida_2 = models.TimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('colaborador_login', 'data')
        verbose_name = 'Ponto Eletrônico'
        verbose_name_plural = 'Pontos Eletrônicos'
        
    def __str__(self):
        return f"Ponto de {self.colaborador_login} - {self.data.strftime('%d/%m/%Y')}"


class JustificativaPonto(models.Model):
    """
    Armazena o histórico de auditoria de alterações no ponto eletrônico.
    Centraliza Férias, Faltas, Abonos e Ajustes de Batida para consulta do motor de saldo.
    """
    TIPO_CHOICES = [
        ('FERIAS', 'Férias / Licença'),
        ('FALTA', 'Falta Justificada / Atestado'),
        ('ABONO', 'Abono Parcial'),
        ('AJUSTE', 'Ajuste de Batida'),
    ]

    # Identificação do colaborador que sofreu a alteração
    colaborador_login = models.CharField(max_length=50)
    
    # Define o tipo da ação (Férias, Falta, Abono ou Ajuste)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    
    # Define o período afetado (data_final é usada apenas para ações de múltiplos dias, como férias)
    data_inicial = models.DateField()
    data_final = models.DateField(null=True, blank=True)
    
    # Guarda qual relógio foi ajustado (ex: 'e1', 's1') e a nova hora, usado apenas em Ajustes Diretos
    batida_ajustada = models.CharField(max_length=2, null=True, blank=True)
    hora_nova = models.TimeField(null=True, blank=True)
    hora_final = models.TimeField(null=True, blank=True) # 🚀 NOVO CAMPO: Para guardar o fim do Abono
    
    
    # Texto descritivo para auditoria e marcador de atestado médico
    motivo = models.TextField(null=True, blank=True)
    possui_atestado = models.BooleanField(default=False)
    
    # Assinatura digital que registra o login do gestor que validou a operação
    gerente_autorizador = models.CharField(max_length=50)
    
    # Timestamp automático de quando o registro foi salvo
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rh_justificativas'
        