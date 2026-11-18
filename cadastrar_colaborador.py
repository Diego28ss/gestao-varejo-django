import sqlite3
import os
import re
import unicodedata

banco = 'dados/jb_tintas.db'

def gerar_login_tec(nome_completo, cursor):
    """ Gera o login automático no padrão do sistema (ex: diegos.tec) """
    nome_limpo = unicodedata.normalize('NFKD', nome_completo).encode('ASCII', 'ignore').decode('utf-8').lower()
    partes = nome_limpo.strip().split()
    
    if len(partes) == 0:
        base_login = "usuario"
    elif len(partes) == 1:
        base_login = partes[0]
    else:
        base_login = f"{partes[0]}{partes[-1][0]}"

    login_final = f"{base_login}.tec"
    
    # Checa no banco se já existe, garantindo unicidade
    contador = 2
    while True:
        cursor.execute("SELECT 1 FROM inventario_usuarios WHERE login = ?", (login_final,))
        if not cursor.fetchone():
            break
        login_final = f"{base_login}{contador}.tec"
        contador += 1
        
    return login_final

def main():
    if not os.path.exists(banco):
        print(f"⚠️ Banco {banco} não encontrado! Certifique-se de estar na pasta raiz do projeto.")
        return

    print("="*40)
    print(" 👔 FICHA DO COLABORADOR (TERMINAL) ")
    print("="*40)

    # 1. Validação do Nome (Usado APENAS para gerar o login)
    while True:
        nome = input("👤 Nome Completo (para gerar o login): ").strip()
        if re.match(r'^[A-Za-zÀ-ÿ\s]+$', nome) and len(nome) >= 3:
            break
        print("❌ Inválido! Use apenas letras e espaços (mínimo 3 caracteres).\n")

    # 2. Seleção de Perfil por Número Numérico
    perfis = {
        '1': 'VENDEDOR',
        '2': 'SUPERVISOR',
        '3': 'GERENTE',
        '4': 'DEV'
    }
    
    while True:
        print("\n📋 Perfis disponíveis:")
        print("  [1] Vendedor")
        print("  [2] Supervisor")
        print("  [3] Gerente")
        print("  [4] DEV (Acesso Total do Sistema)")
        
        opcao = input("⚙️  Escolha o número do Perfil: ").strip()
        
        if opcao in perfis:
            perfil = perfis[opcao]
            break
        print("❌ Opção inválida! Digite apenas o número (ex: 3).")

    # 3. Validação da Senha
    while True:
        senha = input("\n🔑 Senha para o sistema: ").strip()
        if len(senha) >= 4:
            break
        print("❌ A senha deve ter pelo menos 4 caracteres.")

    # 4. Gravação no Banco de Dados
    try:
        conn = sqlite3.connect(banco)
        cursor = conn.cursor()

        # Gera o login usando a inteligência de strings
        login_gerado = gerar_login_tec(nome, cursor)

        # 🚀 CORREÇÃO AQUI: Adicionado a coluna 'comissao' com o valor padrão 0.0
        cursor.execute("""
            INSERT INTO inventario_usuarios (login, senha, perfil, status, comissao) 
            VALUES (?, ?, ?, ?, ?)
        """, (login_gerado, senha, perfil, 'ATIVO', 0.0))
        
        conn.commit()
        
        print("\n" + "="*40)
        print(" 🎉 COLABORADOR CADASTRADO COM SUCESSO! ")
        print("="*40)
        print(f"Login Gerado: {login_gerado}")
        print(f"Senha:        {senha}")
        print(f"Perfil:       {perfil}")
        print("="*40)
        print("👉 Guarde essas credenciais, você as usará para acessar o sistema.")

    except sqlite3.Error as e:
        print(f"\n❌ Erro ao salvar no banco de dados: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()
    