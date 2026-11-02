import sqlite3

# 1. Excluir a tabela do banco errado
try:
    conn_default = sqlite3.connect('dados/jb_tintas.db')
    cursor_default = conn_default.cursor()
    cursor_default.execute("DROP TABLE IF EXISTS rh_justificativas;")
    conn_default.commit()
    conn_default.close()
    print("✅ Tabela excluída do jb_tintas.db com sucesso!")
except Exception as e:
    print(f"Erro ao excluir: {e}")

# 2. Criar a tabela no banco correto
try:
    conn_rh = sqlite3.connect('dados/banco_rh.db')
    cursor_rh = conn_rh.cursor()
    cursor_rh.execute("""
        CREATE TABLE IF NOT EXISTS rh_justificativas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_login varchar(50) NOT NULL,
            tipo varchar(10) NOT NULL,
            data_inicial date NOT NULL,
            data_final date NULL,
            batida_ajustada varchar(2) NULL,
            hora_nova time NULL,
            motivo TEXT NULL,
            possui_atestado bool NOT NULL,
            gerente_autorizador varchar(50) NOT NULL,
            criado_em datetime NOT NULL
        );
    """)
    conn_rh.commit()
    conn_rh.close()
    print("✅ Tabela criada no banco_rh.db com sucesso!")
except Exception as e:
    print(f"Erro ao criar: {e}")
    