import sqlite3
import os

caminho_banco = os.path.join('dados', 'jb_tintas.db')

try:
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    # Apaga a coluna manual para o Django poder criar a oficial
    cursor.execute("ALTER TABLE inventario_produtos DROP COLUMN cod_forn")
    
    print("✅ Coluna manual removida com sucesso! O caminho está livre para o Django.")
    
except Exception as e:
    print(f"❌ Erro: {e}")
finally:
    if 'conn' in locals():
        conn.commit()
        conn.close()
        