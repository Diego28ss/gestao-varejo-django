from django.db import models
from django.utils import timezone

class Noticias(models.Model):
    titulo = models.CharField(max_length=200)
    resumo = models.CharField(max_length=300, blank=True, null=True, help_text="Um texto curto para aparecer no painel")
    conteudo = models.TextField(help_text="O texto completo da atualização")
    data_publicacao = models.DateTimeField(default=timezone.now)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'noticias'
        