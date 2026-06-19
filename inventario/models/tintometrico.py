from django.db import models
from .produtos import Produtos

class RelacaoEmbalagensTintometrico(models.Model):
    codigo_base_tintometrico = models.CharField(max_length=100)
    tamanho_codigo = models.CharField(max_length=20)
    produto_cod_interno = models.ForeignKey(
        Produtos, to_field='cod_interno', on_delete=models.DO_NOTHING,  
        db_column='produto_cod_interno', db_constraint=False           
    )
    class Meta:
        db_table = 'relacao_embalagens_tintometrico'
        unique_together = ('codigo_base_tintometrico', 'tamanho_codigo')
        