from django import forms
from .models import Vendas, Produtos  # <-- Adicionado o 'Produtos' aqui na importação
from .models import RelacaoEmbalagensTintometrico

class VendaForm(forms.ModelForm):
    class Meta:
        model = Vendas
        fields = '__all__'

from django import forms
from .models import RelacaoEmbalagensTintometrico

from django import forms
from .models import RelacaoEmbalagensTintometrico, Produtos

class TintometricoForm(forms.ModelForm):
    # Campo de busca manual para o código interno
    produto_cod_interno = forms.CharField(
        widget=forms.TextInput(attrs={'list': 'produtos-list', 'class': 'form-control', 'placeholder': 'Digite o código do produto...'})
    )
    
    # Campo de tamanho fixo ou buscado dinamicamente
    tamanho_codigo = forms.ChoiceField(
        choices=[('3.2L', '3.2L'), ('800ML', '800ML'), ('900ML', '900ML'), ('18L', '18L')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = RelacaoEmbalagensTintometrico
        fields = ['codigo_base_tintometrico', 'tamanho_codigo', 'produto_cod_interno']

    def clean_produto_cod_interno(self):
        cod = self.cleaned_data.get('produto_cod_interno')
        try:
            # 🔥 A MÁGICA ESTÁ AQUI: Retornamos o OBJETO, não o texto!
            produto = Produtos.objects.get(cod_interno=cod)
            return produto
        except Produtos.DoesNotExist:
            raise forms.ValidationError("Produto não encontrado no estoque!")
        

# A classe ProdutoForm fica separada, totalmente alinhada à esquerda
class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produtos
        fields = [
            'nome', 'cod_barras', 'cod_interno', 'preco_custo', 
            'margem_lucro', 'preco_venda', 'estoque_atual', 'unidade', 'status'
        ]
        
        widgets = {
            # Usando forms.TextInput em vez de models.TextInput
            'cod_interno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 001622'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cod_barras': forms.TextInput(attrs={'class': 'form-control'}),
            'preco_custo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'margem_lucro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_venda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estoque_atual': forms.NumberInput(attrs={'class': 'form-control'}),
            'unidade': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        