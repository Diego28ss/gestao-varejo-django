import sqlite3

try:
    conn_rh = sqlite3.connect('dados/banco_rh.db')
    cursor_rh = conn_rh.cursor()
    # Adiciona a nova coluna na tabela existente
    cursor_rh.execute("ALTER TABLE rh_justificativas ADD COLUMN hora_final time NULL;")
    conn_rh.commit()
    conn_rh.close()
    print("✅ Coluna 'hora_final' adicionada com sucesso no banco_rh.db!")
except Exception as e:
    print(f"Erro ao atualizar a tabela: {e}")
    