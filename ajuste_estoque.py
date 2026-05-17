import sqlite3

# Ligar ao banco de dados da JB Tintas
conn = sqlite3.connect('jb_tintas.db')
cursor = conn.cursor()

print("Iniciando a cirurgia nas tabelas de estoque...")

try:
    # 1. Criar a tabela de Marcas (caso não exista)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marcas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome VARCHAR(100) NOT NULL UNIQUE
        )
    """)
    print("✅ Tabela 'marcas' verificada/criada.")

    # 2. Criar a tabela de Famílias (caso não exista)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS familias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome VARCHAR(100) NOT NULL UNIQUE
        )
    """)
    print("✅ Tabela 'familias' verificada/criada.")

    # 3. Adicionar a coluna marca_id na tabela produtos
    try:
        cursor.execute("ALTER TABLE produtos ADD COLUMN marca_id INTEGER REFERENCES marcas(id)")
        print("✅ Coluna 'marca_id' instalada em produtos.")
    except Exception as e:
        print("Aviso Marca:", e)

    # 4. Adicionar a coluna familia_id na tabela produtos
    try:
        cursor.execute("ALTER TABLE produtos ADD COLUMN familia_id INTEGER REFERENCES familias(id)")
        print("✅ Coluna 'familia_id' instalada em produtos.")
    except Exception as e:
        print("Aviso Família:", e)

    conn.commit()
    print("\n🚀 BANCO DE DADOS SINCRONIZADO! Agora o Django vai reconhecer os campos.")

except Exception as e:
    print("❌ Erro fatal na cirurgia:", e)
finally:
    conn.close()
