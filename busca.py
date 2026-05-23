import sqlite3

def verificar_tintometrico():
    # Agora sim, apontando para o banco correto!
    conn = sqlite3.connect('banco_tintometrico.db')
    cursor = conn.cursor()
    
    print("Buscando fórmulas para RM002 no banco_tintometrico.db...")
    cursor.execute("""
        SELECT f.id_linha, f.id_emb, f.dosagem 
        FROM formulas f
        WHERE f.codigo_cor = 'RM002'
    """)
    
    resultados = cursor.fetchall()
    if resultados:
        for r in resultados:
            print(f"-> Encontrada receita para: Linha ID {r[0]} | Embalagem ID {r[1]} | Dosagem: {r[2]}")
    else:
        print("-> NENHUMA receita cadastrada para RM002.")
        
    conn.close()

verificar_tintometrico()
