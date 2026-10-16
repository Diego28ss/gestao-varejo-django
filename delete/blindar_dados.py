import os
import django
import sqlite3

# Inicializa o ambiente do Django para termos acesso aos modelos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jb_sistema.settings')
django.setup()

from inventario.models import Usuarios, Clientes, ConfiguracaoEmissor

# Conecta diretamente ao SQLite para ler os textos "puros" sem usar a leitura do Django
# (Isso evita que o erro 'Signature is not valid' estoure)
caminho_banco = os.path.join('dados', 'jb_tintas.db')
conn = sqlite3.connect(caminho_banco)
cursor = conn.cursor()

print("1/3 - Blindando senhas dos Usuários...")
cursor.execute("SELECT id, senha FROM inventario_usuarios")
for user_id, senha in cursor.fetchall():
    # Os tokens de criptografia segura (Fernet) começam sempre por 'gAAAAA'. 
    # Se não começar por isso, é porque é a senha antiga em texto puro.
    if senha and not str(senha).startswith('gAAAAA'):
        # O .update() aciona o motor de criptografia e grava embaralhado
        Usuarios.objects.filter(id=user_id).update(senha=senha)

print("2/3 - Blindando dados sensíveis dos Clientes (LGPD)...")
cursor.execute("SELECT id, telefone, email, cpf, cnpj FROM inventario_clientes")
for cli_id, telefone, email, cpf, cnpj in cursor.fetchall():
    qs = Clientes.objects.filter(id=cli_id)
    if telefone and not str(telefone).startswith('gAAAAA'): qs.update(telefone=telefone)
    if email and not str(email).startswith('gAAAAA'): qs.update(email=email)
    if cpf and not str(cpf).startswith('gAAAAA'): qs.update(cpf=cpf)
    if cnpj and not str(cnpj).startswith('gAAAAA'): qs.update(cnpj=cnpj)

print("3/3 - Blindando chaves Fiscais e Sefaz (Configurações)...")
cursor.execute("SELECT id, token_gnf, csc_id, csc_token FROM inventario_configuracaoemissor")
for conf_id, token_gnf, csc_id, csc_token in cursor.fetchall():
    qs = ConfiguracaoEmissor.objects.filter(id=conf_id)
    if token_gnf and not str(token_gnf).startswith('gAAAAA'): qs.update(token_gnf=token_gnf)
    if csc_id and not str(csc_id).startswith('gAAAAA'): qs.update(csc_id=csc_id)
    if csc_token and not str(csc_token).startswith('gAAAAA'): qs.update(csc_token=csc_token)

conn.close()
print("✅ Concluído! Todos os dados antigos agora estão criptografados na base de dados.")
