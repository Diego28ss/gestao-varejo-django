from rest_framework import serializers

class CancelamentoSerializer(serializers.Serializer):
    venda_id = serializers.IntegerField(required=True, error_messages={'required': 'ID da venda é obrigatório.'})
    justificativa = serializers.CharField(required=True, min_length=15, error_messages={'min_length': 'A justificativa deve ter no mínimo 15 caracteres.'})

class EmailSerializer(serializers.Serializer):
    venda_id = serializers.IntegerField(required=True)
    email = serializers.EmailField(required=True, error_messages={'invalid': 'Endereço de e-mail inválido.'})

class CorrecaoSerializer(serializers.Serializer):
    venda_id = serializers.IntegerField(required=True)
    correcao = serializers.CharField(required=True, min_length=15)

class ProdutoDevolucaoSerializer(serializers.Serializer):
    cod_interno = serializers.CharField(required=True)
    quantidade = serializers.FloatField(required=True)

class DevolucaoSerializer(serializers.Serializer):
    venda_id = serializers.IntegerField(required=True)
    chave_original = serializers.CharField(required=True)
    cfop_devolucao = serializers.CharField(required=True)
    justificativa = serializers.CharField(required=True)
    itens_devolvidos = ProdutoDevolucaoSerializer(many=True, allow_empty=False)

class InutilizacaoSerializer(serializers.Serializer):
    modelo = serializers.ChoiceField(choices=['55', '65'], default='55')
    numero_inicial = serializers.IntegerField(required=True)
    numero_final = serializers.IntegerField(required=True)
    justificativa = serializers.CharField(required=True, min_length=15)
    