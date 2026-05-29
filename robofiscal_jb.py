import time
import requests
import os

# URL do seu servidor Django (Nuvem)
URL_NUVEM = "http://127.0.0.1:8000/api/fiscal/tarefas-robo/"

# Memória temporária para evitar que o robô repita a mesma nota no teste
notas_processadas = []

# ==========================================
# CONFIGURAÇÃO DE PASTAS DO ACBR
# ==========================================
# O robô vai criar estas pastas automaticamente no seu C: para fazermos os testes
PASTA_ENTRADA = r"C:\JB_SAT\Entrada"
PASTA_SAIDA = r"C:\JB_SAT\Saida"

os.makedirs(PASTA_ENTRADA, exist_ok=True)
os.makedirs(PASTA_SAIDA, exist_ok=True)

def gerar_arquivo_acbr(v_id, tipo, cliente, valor):
    """
    Cria o ficheiro de texto que o ACBrMonitor vai ler para emitir a nota.
    """
    caminho_arquivo = os.path.join(PASTA_ENTRADA, f"ENT_{v_id}.txt")
    
    # Aqui montamos o comando que o ACBr entende
    if tipo == 'SAT':
        comando = f'SAT.CriarEnviarCfe("[Identificacao]\nNumeroCaixa=001\n[Destinatario]\nNome={cliente}\n[Total]\nValor={valor}")'
    else:
        comando = f'NFE.CriarEnviarNfe("[Identificacao]\nNaturezaOperacao=VENDA\n[Destinatario]\nNome={cliente}\n[Total]\nValor={valor}")'
        
    # Salva o arquivo no disco do Windows
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        f.write(comando)
        
    print(f"✅ Arquivo fiscal gerado com sucesso em: {caminho_arquivo}")


def verificar_fila():
    try:
        resposta = requests.get(URL_NUVEM)
        dados = resposta.json()
        
        if dados.get('tem_tarefa'):
            v_id = dados['venda_id']
            tipo = dados['tipo_nota']
            cliente = dados['cliente']
            valor = dados['valor_total']
            
            if v_id not in notas_processadas:
                print(f"\n🔥 ALERTA: Ordem recebida da Nuvem!")
                print(f"👉 Preparando emissão de {tipo} para Venda #{v_id} (Cliente: {cliente} | R$ {valor})")
                
                # ⚙️ Manda o robô gerar o arquivo físico!
                gerar_arquivo_acbr(v_id, tipo, cliente, valor)
                
                notas_processadas.append(v_id)
                
        else:
            print("💤 Fila vazia. O balcão aguarda novas notas...          ", end="\r")
            
    except Exception as e:
        print(f"❌ Erro de ligacao a nuvem. Tentando reconectar... ({e})", end="\r")

if __name__ == "__main__":
    print("=========================================")
    print(" 🤖 ROBO FISCAL JB TINTAS INICIADO ")
    print("=========================================")
    
    while True:
        verificar_fila()
        time.sleep(3)
        