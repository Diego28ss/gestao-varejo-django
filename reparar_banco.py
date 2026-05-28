import sqlite3

# Caminho do seu banco (ajuste se necessário)
db_path = 'jb_tintas.db' 

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Cria uma tabela temporária sem a coluna 'pontos' e sem restrições estranhas
cursor.execute("""
CREATE TABLE inventario_clientes_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(255),
    telefone VARCHAR(20),
    email VARCHAR(254),
    cpf VARCHAR(20),
    cnpj VARCHAR(20),
    razao_social VARCHAR(255),
    inscricao_estadual VARCHAR(50),
    cep VARCHAR(10),
    endereco VARCHAR(255),
    numero VARCHAR(20),
    complemento VARCHAR(100),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    estado VARCHAR(2),
    tipo_pessoa VARCHAR(2),
    tipo VARCHAR(50),
    data_cadastro DATETIME
);
""")

# 2. Copia os dados da antiga para a nova (ignora a coluna pontos)
cursor.execute("""
INSERT INTO inventario_clientes_new 
(id, nome, telefone, email, cpf, cnpj, razao_social, inscricao_estadual, cep, endereco, numero, complemento, bairro, cidade, estado, tipo_pessoa, tipo, data_cadastro)
SELECT id, nome, telefone, email, cpf, cnpj, razao_social, inscricao_estadual, cep, endereco, numero, complemento, bairro, cidade, estado, tipo_pessoa, tipo, data_cadastro
FROM inventario_clientes;
""")

# 3. Remove a antiga e renomeia a nova
cursor.execute("DROP TABLE inventario_clientes;")
cursor.execute("ALTER TABLE inventario_clientes_new RENAME TO inventario_clientes;")

conn.commit()
conn.close()
print("✅ Tabela reconstruída com sucesso, livre de erros de integridade!")
