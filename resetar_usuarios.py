import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jb_sistema.settings')
django.setup()

from inventario.models import Usuarios

caminho_banco = os.path.join('dados', 'jb_tintas.db')
conn = sqlite3.connect(caminho_banco)
cursor = conn.cursor()

print("Limpando utilizadores corrompidos...")
cursor.execute("DELETE FROM inventario_usuarios")
conn.commit()
conn.close()

# Cria um utilizador administrador novo e limpo (o Django vai criptografar a senha nativamente)
admin_user = Usuarios.objects.create(
    login="admin",
    senha="123",
    perfil="DEV",
    comissao=0.00
)

print("✅ Utilizador 'admin' (senha: '123') recriado com sucesso com criptografia válida!")
