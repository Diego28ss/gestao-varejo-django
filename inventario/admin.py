from django.contrib import admin
from .models import RelacaoEmbalagensTintometrico, Produtos

@admin.register(RelacaoEmbalagensTintometrico)
class RelacaoEmbalagensAdmin(admin.ModelAdmin):
    list_display = ('codigo_base_tintometrico', 'tamanho_codigo', 'produto_cod_interno')
    list_filter = ('codigo_base_tintometrico',)
    # Isso permite buscar pelo nome do produto ou código interno na hora de cadastrar
    autocomplete_fields = ['produto_cod_interno'] 

@admin.register(Produtos)
class ProdutosAdmin(admin.ModelAdmin):
    search_fields = ['nome', 'cod_interno'] # Necessário para o autocomplete funcionar
    