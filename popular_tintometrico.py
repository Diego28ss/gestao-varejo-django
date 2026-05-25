# popular_tintometrico.py
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jb_sistema.settings')
django.setup()

from inventario.models import RelacaoEmbalagensTintometrico

def criar_amarração_manual(base, tamanho, codigo_interno):
    obj, created = RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').get_or_create(
        codigo_base_tintometrico=base,
        tamanho_codigo=tamanho,
        defaults={'produto_cod_interno_id': codigo_interno}
    )
    if created:
        print(f"Sucesso: {base} ({tamanho}) criado com cod_interno {codigo_interno}")

if __name__ == "__main__":
    criar_amarração_manual('BASE_RENDEMUITO_PM', '3.2L', '002541')
    criar_amarração_manual('BASE_RENDEMUITO_PM', '800ML', '002542')
    