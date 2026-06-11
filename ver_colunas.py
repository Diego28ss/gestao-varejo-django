import os
import django

# Conecta o script ao ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jb_sistema.settings')
django.setup()

from inventario.models import ConfiguracaoEmissor

def listar_campos():
    print("📋 Colunas encontradas na tabela ConfiguracaoEmissor:")
    print("-" * 45)
    # Pega todos os campos do modelo
    campos = ConfiguracaoEmissor._meta.get_fields()
    for campo in campos:
        # Exibe o nome do campo e o tipo de dado
        print(f"Campo: {campo.name:25} | Tipo: {type(campo).__name__}")
    print("-" * 45)

if __name__ == '__main__':
    listar_campos()
    