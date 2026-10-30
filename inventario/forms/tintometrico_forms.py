from django import forms
from inventario.models import Produtos, RelacaoEmbalagensTintometrico

class TintometricoForm(forms.ModelForm):
    produto_cod_interno = forms.CharField(
        widget=forms.TextInput(attrs={'list': 'produtos-list', 'class': 'form-control', 'placeholder': 'Digite o código do produto...'})
    )
    
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
            return Produtos.objects.get(cod_interno=cod)
        except Produtos.DoesNotExist:
            raise forms.ValidationError("Produto não encontrado no estoque!")
        