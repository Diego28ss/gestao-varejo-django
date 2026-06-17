import csv
import re
import os
from inventario.models import Produtos, Marca, Familia

# Nome do arquivo CSV que está na pasta principal
caminho_csv = 'Saldos de Produtos no Período_.csv'

# Verifica se o arquivo existe antes de iniciar
if not os.path.exists(caminho_csv):
    print("❌ ERRO: O arquivo CSV não foi encontrado na pasta do projeto.")
else:
    print("⏳ Iniciando a importação de produtos...")
    
    produtos_criados = 0
    produtos_atualizados = 0

    # Abre o arquivo CSV (utf-8-sig para evitar caracteres estranhos no início)
    with open(caminho_csv, mode='r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.reader(f, delimiter=';')
        
        # Pula a primeira linha (cabeçalho)
        next(reader, None) 
        
        for linha in reader:
            # Ignora linhas vazias
            if not linha or not linha[0].strip():
                continue 
                
            try:
                # 1. MAPEAMENTO DAS COLUNAS
                nome_csv = linha[0].strip()
                cod_interno_csv = linha[1].strip()
                fabricante_csv = linha[2].strip() if len(linha) > 2 else ''
                familia_csv = linha[3].strip() if len(linha) > 3 else ''
                estoque_csv = linha[4].strip() if len(linha) > 4 else '0'
                unidade_csv = inline_u = linha[5].strip() if len(linha) > 5 else 'UN'
                status_csv = linha[6].strip().upper() if len(linha) > 6 else 'ATIVO'
                ncm_csv = linha[7].strip() if len(linha) > 7 else '32091010'
                classe_trib_csv = linha[8].strip() if len(linha) > 8 else ''
                
                # Só processa se tiver um código interno e um nome
                if not cod_interno_csv or not nome_csv:
                    continue

                # 2. TRATAMENTO DE MARCA (Fabricante)
                marca_obj = None
                if fabricante_csv:
                    marca_obj, _ = Marca.objects.get_or_create(nome=fabricante_csv[:100])
                    
                # 3. TRATAMENTO DE FAMÍLIA
                familia_obj = None
                if familia_csv:
                    familia_obj, _ = Familia.objects.get_or_create(nome=familia_csv[:100])
                    
                # 4. EXTRAÇÃO INTELIGENTE DO CSOSN
                csosn_tratado = '102' # Padrão
                if classe_trib_csv:
                    numeros = re.findall(r'\d+', classe_trib_csv)
                    if numeros:
                        csosn_tratado = numeros[-1]
                        
                # 5. TRATAMENTO DE ESTOQUE
                try:
                    estoque_int = int(float(estoque_csv))
                except ValueError:
                    estoque_int = 0
                    
                # 6. INSERÇÃO NO BANCO DE DADOS
                produto, criado = Produtos.objects.update_or_create(
                    cod_interno=cod_interno_csv,
                    defaults={
                        'nome': nome_csv,
                        'marca': marca_obj,
                        'familia': familia_obj,
                        'estoque_atual': estoque_int,
                        'unidade': unidade_csv if unidade_csv else 'UN',
                        'status': status_csv if status_csv else 'ATIVO',
                        'ncm': ''.join(filter(str.isdigit, ncm_csv)) if ncm_csv else '32091010',
                        'cst_csosn': csosn_tratado,
                        'preco_venda': 0.00,
                        'preco_custo': 0.00
                    }
                )
                
                if criado:
                    produtos_criados += 1
                else:
                    produtos_atualizados += 1
                    
            except Exception as e:
                print(f"⚠️ Erro ao processar a linha do produto '{linha[0] if linha else 'Desconhecido'}': {str(e)}")

    print("-" * 40)
    print("✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    print(f" 📦 Produtos Novos Inseridos: {produtos_criados}")
    print(f" 🔄 Produtos Atualizados: {produtos_atualizados}")
    print("-" * 40)
    