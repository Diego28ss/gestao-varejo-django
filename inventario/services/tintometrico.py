import re
from django.db import connections

def obter_linhas_e_embalagens():
    """Puxa do banco de dados as opções para os menus dropdown"""
    linhas, embalagens = [], []
    with connections['tintometrico'].cursor() as cursor:
        cursor.execute("SELECT id_linha, nome_produto FROM linhas ORDER BY nome_produto")
        for row in cursor.fetchall():
            linhas.append({'id': row[0], 'nome': row[1]})
            
        cursor.execute("SELECT id_emb, tamanho FROM embalagens")
        for row in cursor.fetchall():
            embalagens.append({'id': row[0], 'tamanho': row[1]})
            
    return linhas, embalagens

def calcular_formula(cor_busca, linha_id, embalagem_id):
    """Calcula a base, corantes e valores finais da receita"""
    resultado = {
        'sucesso': False, 'erro': None, 'cor_encontrada': None, 
        'nome_base': None, 'preco_base': 0.0, 'corantes': [], 
        'custo_corantes': 0.0, 'valor_total': 0.0
    }

    try:
        linha_id = int(linha_id)
        embalagem_id = int(embalagem_id)
    except (ValueError, TypeError):
        resultado['erro'] = "Os filtros de Linha ou Embalagem são inválidos."
        return resultado

    with connections['tintometrico'].cursor() as cursor:
        # 1. Busca a cor
        cursor.execute("""
            SELECT TRIM(nome_busca), TRIM(codigo_tecnico) FROM cores 
            WHERE nome_busca LIKE %s OR codigo_tecnico LIKE %s LIMIT 1
        """, [f"%{cor_busca.strip()}%", f"%{cor_busca.strip()}%"])
        
        cor = cursor.fetchone()
        if not cor:
            resultado['erro'] = f"Cor '{cor_busca}' não foi encontrada no catálogo."
            return resultado
        
        nome_encontrado, codigo_tecnico = cor
        resultado['cor_encontrada'] = nome_encontrado
        
        # 2. Busca a fórmula
        cursor.execute("""
            SELECT id_base, dosagem FROM formulas 
            WHERE (UPPER(TRIM(codigo_cor)) = UPPER(TRIM(%s)) OR UPPER(TRIM(codigo_cor)) = UPPER(TRIM(%s))) 
            AND id_linha = %s AND id_emb = %s LIMIT 1
        """, [codigo_tecnico, nome_encontrado, linha_id, embalagem_id])
        
        formula = cursor.fetchone()
        if not formula:
            resultado['erro'] = "Fórmula não encontrada nesta configuração."
            return resultado
        
        id_base, dosagem_str = formula
        
        # 3. Busca a Base Exigida
        cursor.execute("""
            SELECT b.nome_base, p.custo_unitario 
            FROM bases b 
            LEFT JOIN precos_custo p ON p.id_referencia = b.id_base AND UPPER(TRIM(p.tipo_item)) = 'BASE'
            WHERE b.id_base = %s LIMIT 1
        """, [id_base])
        
        base_info = cursor.fetchone()
        if base_info:
            resultado['nome_base'] = base_info[0]
            resultado['preco_base'] = float(base_info[1] or 0.0)
        else:
            resultado['nome_base'] = "Base Desconhecida"

        # 4. Magia Tintométrica: Processando os IDs dos Corantes usando id_formula
        custo_total_corantes = 0.0
        
        if dosagem_str:
            partes = [p.strip() for p in str(dosagem_str).split(',')]
            
            for i in range(0, len(partes), 2):
                if i + 1 < len(partes):
                    letra = partes[i] # Aqui 'letra' é o ID interno no banco
                    qtd_str = partes[i+1]
                    
                    try:
                        qtd = float(qtd_str.replace(',', '.'))
                    except ValueError:
                        continue 
                    
                    # 🔥 CÓDIGO ATUALIZADO: Puxando a letra real e ocultando a posição
                    cursor.execute("""
                        SELECT c.nome_pigmento, p.custo_unitario, c.letra_codigo 
                        FROM corantes c
                        LEFT JOIN precos_custo p ON p.id_referencia = c.id_formula AND UPPER(TRIM(p.tipo_item)) = 'CORANTE'
                        WHERE c.id_formula = %s OR UPPER(TRIM(c.letra_codigo)) = UPPER(TRIM(%s)) LIMIT 1
                    """, [letra, letra])
                    
                    corante_info = cursor.fetchone()
                    if corante_info:
                        nome_pigmento, custo_ml, letra_real = corante_info
                        custo_ml = float(custo_ml or 0.0)
                        custo_parcial = qtd * custo_ml
                        custo_total_corantes += custo_parcial
                        
                        resultado['corantes'].append({
                            'letra_codigo': letra_real, # <--- A letra visível para a tela ('A', 'B', etc)
                            'nome': nome_pigmento, 
                            'quantidade': qtd, 
                            'custo_parcial': custo_parcial
                        })
        
        resultado['custo_corantes'] = custo_total_corantes
        custo_bruto = resultado['preco_base'] + custo_total_corantes
        resultado['valor_total'] = custo_bruto * 1.35  # Aplicando Margem
        resultado['sucesso'] = True

    return resultado
