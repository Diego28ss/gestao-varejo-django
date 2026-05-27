import sqlite3

# Nome do seu arquivo de banco
db_path = 'jb_tintas.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Vamos limpar a coluna 'cliente' (nome exato que o seu ver_banco.py mostrou)
    # O comando abaixo substitui valores vazios por NULL
    cursor.execute("UPDATE inventario_vendas SET cliente = NULL WHERE cliente = '';")
    
    # Também limpamos espaços em branco caso existam
    cursor.execute("UPDATE inventario_vendas SET cliente = NULL WHERE cliente = ' ';")
    
    conn.commit()
    print("Sucesso! O banco de dados foi limpo.")
    
except Exception as e:
    print(f"Erro ao acessar o banco: {e}")
finally:
    conn.close()
    