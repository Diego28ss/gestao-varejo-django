import sqlite3

# Conecta diretamente ao banco SQLite
conn = sqlite3.connect('jb_tintas.db')
cursor = conn.cursor()

cursor.execute("SELECT id, cod_interno FROM inventario_produtos")
linhas = cursor.fetchall()

codigos_vistos = set()
contador = 900000

for linha in linhas:
    id_prod = linha[0]
    cod = linha[1]
    
    # Se for nulo, vazio ou repetido, injeta um código novo
    if not cod or str(cod).strip() == "" or cod in codigos_vistos:
        novo_cod = str(contador)
        cursor.execute("UPDATE inventario_produtos SET cod_interno = ? WHERE id = ?", (novo_cod, id_prod))
        contador += 1
        codigos_vistos.add(novo_cod)
    else:
        codigos_vistos.add(cod)

conn.commit()
conn.close()
print("✅ Códigos corrigidos com sucesso absoluto!")
