import os
import shutil
from datetime import datetime

# ==============================================================================
# O CARRO-FORTE (SISTEMA DE BACKUP AUTOMÁTICO LOCAL)
# Faz uma cópia de segurança do banco de dados com a data e hora do momento.
# Integra perfeitamente com a sincronização do Google Drive (Aplicativo Windows)
# ==============================================================================

def executar_backup():
    ficheiro_banco = 'jb_tintas.db' # Nome do banco atual
    pasta_backups = 'backups_seguranca'

    print("Iniciando rotina de Backup da JB Tintas...")

    # 1. Verifica se o ficheiro do banco de dados existe
    if not os.path.exists(ficheiro_banco):
        print(f"❌ ERRO CRÍTICO: O arquivo do banco '{ficheiro_banco}' não foi encontrado.")
        return

    # 2. Cria a pasta de backups se ela ainda não existir
    if not os.path.exists(pasta_backups):
        os.makedirs(pasta_backups)
        print(f"📁 Pasta de segurança '{pasta_backups}' criada.")

    # 3. Gera o nome do novo ficheiro com a data e hora atuais (Selo temporal)
    # Formato final: backup_jb_tintas_2026-05-14_17-30-00.db
    data_hora_atual = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nome_backup = f"backup_jb_tintas_{data_hora_atual}.db"
    caminho_completo = os.path.join(pasta_backups, nome_backup)

    # 4. Faz a cópia exata do ficheiro
    try:
        shutil.copy2(ficheiro_banco, caminho_completo)
        print("\n==================================================")
        print(f"✅ SUCESSO! Cópia de segurança realizada com sucesso.")
        print(f"🔒 Ficheiro guardado em: {caminho_completo}")
        print("==================================================\n")
    except Exception as e:
        print(f"❌ Ocorreu um erro ao tentar copiar o ficheiro: {e}")

if __name__ == '__main__':
    executar_backup()