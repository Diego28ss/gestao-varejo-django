from django import forms
from inventario.models import Produtos

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produtos
        fields = [
            'nome', 'cod_barras', 'cod_interno', 'preco_custo', 
            'margem_lucro', 'preco_venda', 'estoque_atual', 'unidade', 
            'marca', 'familia', 'status', 'cor', 'es_base_tintometrica',
            'ncm', 'cest', 'cst_csosn', 'origem'
        ]
        
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cod_barras': forms.TextInput(attrs={'class': 'form-control'}),
            'cod_interno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 001622'}),
            'preco_custo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'margem_lucro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_venda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estoque_atual': forms.NumberInput(attrs={'class': 'form-control'}),
            'unidade': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.Select(attrs={'class': 'form-select'}),
            'familia': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'cor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Branco, Azul Profundo'}),
            'cst_csosn': forms.Select(attrs={'class': 'form-select'}),
            'ncm': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 32091010'}),
            'cest': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'}),
            'origem': forms.Select(attrs={'class': 'form-select fw-bold'}),
            'es_base_tintometrica': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        