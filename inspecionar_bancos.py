import sqlite3
import os

bancos = [
    'dados/jb_tintas.db', 
    'dados/banco_rh.db', 
    'dados/banco_tintometrico.db'
]

for caminho in bancos:
    print(f"\n{'='*40}\nLendo: {caminho}")
    
    if not os.path.exists(caminho):
        print("Arquivo não encontrado no diretório!")
        continue
        
    try:
        conexao = sqlite3.connect(caminho)
        cursor = conexao.cursor()
        
        # Busca o nome de todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tabelas = [linha[0] for linha in cursor.fetchall()]
        
        print(f"Total de tabelas encontradas: {len(tabelas)}")
        
        # Verifica onde nossa tabela foi parar
        if 'rh_justificativas' in tabelas:
            print("✅ SUCESSO: A tabela 'rh_justificativas' ESTÁ NESTE BANCO!")
            
            # Lista as colunas para confirmar a estrutura
            cursor.execute("PRAGMA table_info(rh_justificativas);")
            colunas = cursor.fetchall()
            print("Colunas da tabela:")
            for col in colunas:
                print(f" - {col[1]} ({col[2]})")
        else:
            print("❌ A tabela 'rh_justificativas' NÃO existe neste banco.")
            
        conexao.close()
    except Exception as e:
        print(f"Erro ao ler banco de dados: {e}")
        