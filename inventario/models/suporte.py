import unicodedata
from django.db import models
from django.utils import timezone


def normalizar_texto_pergunta(texto: str) -> str:
    txt = str(texto or '').strip().lower()
    txt = ''.join(
        c for c in unicodedata.normalize('NFD', txt)
        if unicodedata.category(c) != 'Mn'
    )
    txt = txt.rstrip('?.! ')
    return ' '.join(txt.split())[:255]


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
    pergunta_normalizada = models.CharField(max_length=255, db_index=True, blank=True, default='')
    resposta = models.TextField()

    usou_ferramenta_banco = models.BooleanField(default=False)
    feedback = models.CharField(max_length=20, choices=FEEDBACK_CHOICES, default='PENDENTE')
    resolvido_manual = models.BooleanField(default=False, help_text="True quando já foi adicionado ao manual")

    class Meta:
        db_table = 'inventario_log_suporte_ia'
        ordering = ['-data_hora']

    def save(self, *args, **kwargs):
        if not self.pergunta_normalizada and self.pergunta:
            self.pergunta_normalizada = normalizar_texto_pergunta(self.pergunta)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.feedback}] {self.usuario}: {self.pergunta[:45]}..."
    