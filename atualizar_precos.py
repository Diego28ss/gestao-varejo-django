import csv
import os
from inventario.models import Produtos

caminho_csv = 'Produtos.csv'

if not os.path.exists(caminho_csv):
    print("❌ ERRO: O arquivo CSV não foi encontrado na pasta do projeto.")
else:
    print("⏳ Iniciando a atualização de códigos de barras e preços de venda...")
    
    produtos_atualizados = 0
    produtos_nao_encontrados = 0

    with open(caminho_csv, mode='r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader, None) # Pula a primeira linha (cabeçalho)
        
        for linha in reader:
            # O CSV tem 4 colunas: [Vazio, Código, Cód Barras, Preço de Venda]
            if len(linha) < 4:
                continue
                
            cod_interno_csv = linha[1].strip()
            cod_barras_csv = linha[2].strip()
            preco_venda_csv = linha[3].strip()
            
            # Se não houver código interno na linha, ignora
            if not cod_interno_csv:
                continue
                
            # Tratamento do preço (substitui vírgula por ponto para o Python entender)
            preco_venda_tratado = 0.00
            if preco_venda_csv:
                try:
                    preco_venda_tratado = float(preco_venda_csv.replace(',', '.'))
                except ValueError:
                    preco_venda_tratado = 0.00
                    
            # Tratamento do Código de Barras (Limpa o texto 'SEM GTIN' para não sujar o banco)
            if cod_barras_csv.upper() == 'SEM GTIN':
                cod_barras_csv = ''

            # Busca o produto no banco e atualiza
            produto = Produtos.objects.filter(cod_interno=cod_interno_csv).first()
            if produto:
                produto.cod_barras = cod_barras_csv
                produto.preco_venda = preco_venda_tratado
                # Salva apenas os campos alterados para ser mais rápido
                produto.save(update_fields=['cod_barras', 'preco_venda'])
                produtos_atualizados += 1
            else:
                produtos_nao_encontrados += 1

    print("-" * 50)
    print("✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
    print(f" 🔄 Produtos Atualizados: {produtos_atualizados}")
    print(f" ⚠️ Códigos Não Encontrados no Banco: {produtos_nao_encontrados}")
    print("-" * 50)
    