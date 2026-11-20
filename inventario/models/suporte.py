from django.db import models
from django.utils import timezone


class LogSuporteIA(models.Model):
    FEEDBACK_CHOICES = [
        ('PENDENTE', 'Sem Avaliação'),
        ('UTIL', 'Útil (👍)'),
        ('NAO_AJUDOU', 'Não Ajudou (👎)'),
    ]

    data_hora = models.DateTimeField(default=timezone.now)
    usuario = models.CharField(max_length=100, blank=True, null=True)
    perfil = models.CharField(max_length=50, blank=True, null=True)
    rota_origem = models.CharField(max_length=255, blank=True, null=True, help_text="Tela onde o usuário abriu o chat")
    
    pergunta = models.TextField()
    resposta = models.TextField()
    
    usou_ferramenta_banco = models.BooleanField(default=False)
    feedback = models.CharField(max_length=20, choices=FEEDBACK_CHOICES, default='PENDENTE')

    class Meta:
        db_table = 'inventario_log_suporte_ia'
        ordering = ['-data_hora']

    def __str__(self):
        return f"[{self.feedback}] {self.usuario}: {self.pergunta[:45]}..."
    