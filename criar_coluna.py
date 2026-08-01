import sqlite3
import os

caminho_banco = os.path.join('dados', 'jb_tintas.db')

try:
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    # Adiciona a coluna cod_forn na tabela de inventário de produtos
    cursor.execute("ALTER TABLE inventario_produtos ADD COLUMN cod_forn VARCHAR(100)")
    
    print("✅ Sucesso! Coluna 'cod_forn' foi criada na tabela inventario_produtos.")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("⚠️ A coluna 'cod_forn' já existe no banco de dados!")
    else:
        print(f"❌ Erro no banco: {e}")
except Exception as e:
    print(f"❌ Erro: {e}")
finally:
    if 'conn' in locals():
        conn.commit()
        conn.close()