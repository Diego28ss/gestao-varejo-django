import sqlite3

try:
    conn = sqlite3.connect('dados/jb_tintas.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE inventario_vendas ADD COLUMN desconto_comum decimal(10, 2) NOT NULL DEFAULT 0;")
        print("Coluna desconto_comum adicionada.")
    except Exception as e:
        print(f"desconto_comum: {e}")
        
    try:
        cursor.execute("ALTER TABLE inventario_vendas ADD COLUMN desconto_pontos decimal(10, 2) NOT NULL DEFAULT 0;")
        print("Coluna desconto_pontos adicionada.")
    except Exception as e:
        print(f"desconto_pontos: {e}")
        
    try:
        cursor.execute("ALTER TABLE inventario_vendas ADD COLUMN percentual_comissao decimal(5, 2) NOT NULL DEFAULT 0;")
        print("Coluna percentual_comissao adicionada.")
    except Exception as e:
        print(f"percentual_comissao: {e}")

    conn.commit()
    conn.close()
    print("✅ Banco jb_tintas.db atualizado com sucesso!")
except Exception as e:
    print(f"Erro geral: {e}")
    