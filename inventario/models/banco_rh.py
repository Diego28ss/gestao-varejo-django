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
    