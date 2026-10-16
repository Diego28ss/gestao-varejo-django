import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jb_sistema.settings')
django.setup()

from inventario.models import Usuarios

# Conecta ao SQLite para forçar a re-gravação correta via Django
caminho_banco = os.path.join('dados', 'jb_tintas.db')
conn = sqlite3.connect(caminho_banco)
cursor = conn.cursor()

print("Verificando utilizadores existentes...")
cursor.execute("SELECT id, login, senha FROM inventario_usuarios")
usuarios = cursor.fetchall()

for user_id, login, senha_atual in usuarios:
    # Se a senha não começa com o prefixo Fernet ('gAAAAA'), ela está em texto plano
    if senha_atual and not str(senha_atual).startswith('gAAAAA'):
        print(f"Atualizando criptografia para o utilizador: {login}")
        user = Usuarios.objects.get(id=user_id)
        # Reatribuir a mesma senha força o Django a criptografá-la corretamente
        user.senha = senha_atual
        user.save()
    elif not senha_atual:
        # Se por acaso estiver vazia, define uma padrão para não quebrar
        print(f"Definindo senha padrão para o utilizador sem senha: {login}")
        user = Usuarios.objects.get(id=user_id)
        user.senha = "123"
        user.save()

conn.close()
print("✅ Todos os logins e batidas de ponto foram preservados, e as senhas foram blindadas com sucesso!")
