from django import forms
from .models import Produtos, Clientes, Vendas, Marca, Familia

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produtos
        fields = '__all__'

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Clientes
        fields = '__all__'

class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = '__all__'

class FamiliaForm(forms.ModelForm):
    class Meta:
        model = Familia
        fields = '__all__'

class VendaForm(forms.ModelForm):
    class Meta:
        model = Vendas
        # O Django agora sabe que deve aceitar o campo "status" e "indicante" quando salvarmos a venda
        fields = ['valor_total', 'valor_desconto', 'vendedor', 'cliente', 'indicante', 'cupom_texto', 'status']