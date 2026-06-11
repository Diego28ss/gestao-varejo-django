import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jb_sistema.settings')
django.setup()

from inventario.models import ConfiguracaoEmissor

def popular_emissor():
    # Limpa dados antigos
    ConfiguracaoEmissor.objects.all().delete()
    
    # Cria os dados oficiais
    emissor = ConfiguracaoEmissor.objects.create(
        razao_social="JACSON SANTANA DOS SANTOS", # Ajuste se o nome no CCMEI for diferente
        cnpj="36848840000156",
        inscricao_estadual="128791388115",
        cep="03817000",
        endereco="Rua Caicara do Rio do Vento",
        numero="617",
        bairro="Parque Cisper",
        cidade="São Paulo",
        estado="SP",
        codigo_ibge="3550308",
        email="jacson.santos.86@hotmail.com",
        telefone="1180650767"
    )
    print(f"✅ Empresa {emissor.razao_social} configurada com sucesso!")

if __name__ == '__main__':
    popular_emissor()
    