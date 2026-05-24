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
    """Calcula a base, corantes e valores escalando a partir da fórmula de 800ml (DNA)"""
    resultado = {
        'sucesso': False, 'erro': None, 'cor_encontrada': None, 
        'nome_base': None, 'preco_base': 0.0, 'corantes': [], 
        'custo_corantes': 0.0, 'valor_total': 0.0,
        'multiplicador_usado': 1.0 # Guardamos para debug se precisar
    }

    try:
        linha_id = int(linha_id)
        embalagem_id = int(embalagem_id)
    except (ValueError, TypeError):
        resultado['erro'] = "Os filtros de Linha ou Embalagem são inválidos."
        return resultado

    with connections['tintometrico'].cursor() as cursor:
        
        # ==========================================================
        # PASSO 1: DESCOBRIR O VOLUME DA EMBALAGEM E O MULTIPLICADOR
        # ==========================================================
        cursor.execute("SELECT tamanho FROM embalagens WHERE id_emb = %s LIMIT 1", [embalagem_id])
        emb_row = cursor.fetchone()
        tamanho_str = emb_row[0].upper() if emb_row else "800ML"
        
        # Extrai os números do texto (Ex: "16L" -> 16.0 | "3,6L" -> 3.6 | "800ML" -> 800)
        numeros = re.findall(r"[\d.,]+", tamanho_str)
        volume_desejado = 0.8 # Padrão de segurança
        
        if numeros:
            val = float(numeros[0].replace(',', '.'))
            if 'ML' in tamanho_str:
                volume_desejado = val / 1000.0  # Converte ML para Litros
            else:
                volume_desejado = val           # Já está em Litros
                
        # A Regra de Ouro:
        multiplicador = volume_desejado / 0.8
        resultado['multiplicador_usado'] = multiplicador

        # ==========================================================
        # PASSO 2: BUSCA A COR
        # ==========================================================
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
        
        # ==========================================================
        # PASSO 3: BUSCA A FÓRMULA DNA (SEMPRE id_emb = 1)
        # ==========================================================
        # Note que forçamos o id_emb = 1 na query para sempre puxar o DNA de 800ml
        cursor.execute("""
            SELECT id_base, dosagem FROM formulas 
            WHERE (UPPER(TRIM(codigo_cor)) = UPPER(TRIM(%s)) OR UPPER(TRIM(codigo_cor)) = UPPER(TRIM(%s))) 
            AND id_linha = %s AND id_emb = 1 LIMIT 1
        """, [codigo_tecnico, nome_encontrado, linha_id])
        
        formula = cursor.fetchone()
        if not formula:
            resultado['erro'] = "Fórmula base de referência (DNA 800ml) não encontrada para gerar proporção."
            return resultado
        
        id_base, dosagem_str = formula
        
        # ==========================================================
        # PASSO 4: BASE E PREÇO PROPORCIONAL
        # ==========================================================
        cursor.execute("""
            SELECT b.nome_base, p.custo_unitario 
            FROM bases b 
            LEFT JOIN precos_custo p ON p.id_referencia = b.id_base AND UPPER(TRIM(p.tipo_item)) = 'BASE'
            WHERE b.id_base = %s LIMIT 1
        """, [id_base])
        
        base_info = cursor.fetchone()
        if base_info:
            resultado['nome_base'] = base_info[0]
            # O preço da base também escala! (Uma lata de 16L custa mais que uma de 800ml)
            resultado['preco_base'] = float(base_info[1] or 0.0) * multiplicador
        else:
            resultado['nome_base'] = "Base Desconhecida"

        # ==========================================================
        # PASSO 5: MAGIA TINTOMÉTRICA (APLICANDO O MULTIPLICADOR NOS PIGMENTOS)
        # ==========================================================
        custo_total_corantes = 0.0
        
        if dosagem_str:
            partes = [p.strip() for p in str(dosagem_str).split(',')]
            
            for i in range(0, len(partes), 2):
                if i + 1 < len(partes):
                    letra = partes[i] # ID Interno
                    qtd_str = partes[i+1]
                    
                    try:
                        qtd_dna = float(qtd_str.replace(',', '.'))
                    except ValueError:
                        continue 
                    
                    # 🔥 AQUI OCORRE A CONVERSÃO MATEMÁTICA 🔥
                    qtd_final_multiplicada = qtd_dna * multiplicador
                    
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
                        
                        # O custo calcula em cima da quantidade final que a máquina vai derramar
                        custo_parcial = qtd_final_multiplicada * custo_ml
                        custo_total_corantes += custo_parcial
                        
                        resultado['corantes'].append({
                            'letra_codigo': letra_real, 
                            'nome': nome_pigmento, 
                            'quantidade': qtd_final_multiplicada, 
                            'custo_parcial': custo_parcial
                        })
        
        resultado['custo_corantes'] = custo_total_corantes
        custo_bruto = resultado['preco_base'] + custo_total_corantes
        resultado['valor_total'] = custo_bruto * 1.35  # Aplicando Margem de 35%
        resultado['sucesso'] = True

    return resultado
