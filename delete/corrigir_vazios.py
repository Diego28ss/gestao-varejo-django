import sqlite3
import os

caminho_banco = os.path.join('dados', 'jb_tintas.db')

try:
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    # Mapeamento das tabelas e campos criptografados
    tabelas = {
        'inventario_clientes': ['telefone', 'email', 'cpf', 'cnpj'],
        'inventario_usuarios': ['senha'],
        'inventario_configuracaoemissor': ['token_gnf', 'csc_id', 'csc_token']
    }
    
    total_corrigidos = 0
    for tabela, campos in tabelas.items():
        for campo in campos:
            # Substitui strings vazias por NULL (None)
            cursor.execute(f"UPDATE {tabela} SET {campo} = NULL WHERE {campo} = ''")
            total_corrigidos += cursor.rowcount
            
    conn.commit()
    print(f"✅ Base de dados corrigida! {total_corrigidos} campos vazios foram transformados em NULL.")

except sqlite3.Error as e:
    print(f"❌ Erro na base de dados: {e}")
finally:
    if 'conn' in locals():
        conn.close()
        