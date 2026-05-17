import sqlite3

conn = sqlite3.connect('jb_tintas.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE produtos ADD COLUMN preco_custo decimal NOT NULL DEFAULT 0")
    print("✅ Gaveta 'Preco de Custo' instalada com sucesso!")
except Exception as e:
    print("Aviso Custo:", e)

try:
    cursor.execute("ALTER TABLE produtos ADD COLUMN margem_lucro decimal NOT NULL DEFAULT 0")
    print("✅ Gaveta 'Margem de Lucro' instalada com sucesso!")
except Exception as e:
    print("Aviso Lucro:", e)

conn.commit()
conn.close()
print("🚀 Cirurgia finalizada! O banco está 100% pronto.")