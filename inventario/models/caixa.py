from django.db import models

# Modelo responsável por gerenciar a abertura, fechamento e status do caixa
class ControleCaixa(models.Model):
    STATUS_CHOICES = [
        ('ABERTO', 'Aberto'),
        ('FECHADO_TEMP', 'Fechado Temporariamente'),
        ('FECHADO', 'Fechado Permanentemente'),
    ]

    # Vínculo com os usuários responsáveis pela operação e autorização
    operador = models.ForeignKey('inventario.Usuarios', on_delete=models.PROTECT, related_name='caixas_operados')
    gerente_abertura = models.ForeignKey('inventario.Usuarios', on_delete=models.PROTECT, related_name='aberturas_autorizadas')
    gerente_fechamento = models.ForeignKey('inventario.Usuarios', on_delete=models.PROTECT, related_name='fechamentos_autorizados', null=True, blank=True)
    
    # Registro de tempo da jornada do caixa
    data_hora_abertura = models.DateTimeField(auto_now_add=True)
    data_hora_fechamento = models.DateTimeField(null=True, blank=True)
    
    # Fundo de troco inicial
    lastro_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Valores informados no fechamento cego pelo operador
    dinheiro_declarado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cartao_declarado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Situação atual do caixa
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTO')

    class Meta:
        db_table = 'inventario_controlecaixa'

# Modelo responsável por registrar retiradas (sangrias) e entradas (suprimentos) de dinheiro
class MovimentacaoCaixa(models.Model):
    TIPO_CHOICES = [
        ('SANGRIA', 'Sangria (Retirada)'),
        ('SUPRIMENTO', 'Suprimento (Entrada)'),
    ]

    # Vínculo obrigatório com um caixa aberto
    caixa = models.ForeignKey(ControleCaixa, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    motivo = models.CharField(max_length=255)
    
    data_hora = models.DateTimeField(auto_now_add=True)
    
    # Vínculo com quem realizou e quem autorizou a movimentação
    operador = models.ForeignKey('inventario.Usuarios', on_delete=models.PROTECT, related_name='movimentacoes_realizadas')
    gerente_autorizador = models.ForeignKey('inventario.Usuarios', on_delete=models.PROTECT, related_name='movimentacoes_autorizadas')

    class Meta:
        db_table = 'inventario_movimentacaocaixa'
        