import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jb_sistema.settings') # Certifique-se de que jb_sistema é o nome da sua pasta principal
django.setup()

with connection.cursor() as cursor:
    cursor.execute("DELETE FROM django_migrations WHERE app = 'inventario';")
    print("✅ Histórico do 'inventario' limpo com sucesso.")
    