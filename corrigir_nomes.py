import sqlite3

db_path = 'jb_tintas.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Identificar registros onde a coluna 'cliente' não é um número
    # O comando abaixo define como NULL qualquer coisa que não seja um número
    cursor.execute("""
        UPDATE inventario_vendas 
        SET cliente = NULL 
        WHERE typeof(cliente) = 'text' AND cliente NOT GLOB '[0-9]*';
    """)

    conn.commit()
    print("Correção concluída: Nomes de clientes removidos da coluna de IDs.")
    
except Exception as e:
    print(f"Erro: {e}")
finally:
    conn.close()
    