import sqlite3
import os

caminho_banco = os.path.join('dados', 'jb_tintas.db')

try:
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    # Desvincula os produtos das sessões de estoque que foram apagadas
    cursor.execute("UPDATE inventario_produtos SET sessao_estoque_id = NULL")
    linhas = cursor.rowcount
    
    conn.commit()
    print(f"✅ Tabela 'inventario_produtos' corrigida! {linhas} produtos desvinculados de sessões fantasmas.")

except sqlite3.Error as e:
    print(f"❌ Erro na base de dados: {e}")
finally:
    if 'conn' in locals():
        conn.close()
        