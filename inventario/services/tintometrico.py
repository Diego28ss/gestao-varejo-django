import re
from django.db import connections

def obter_linhas_e_embalagens():
    """Puxa do banco de dados as opções para os menus dropdown"""
    linhas, embalagens = [], []
    # AGORA APONTA EXATAMENTE PARA O BANCO NOVO!
    with connections['tintometrico'].cursor() as cursor:
        # Puxa Linhas
        cursor.execute("SELECT id_linha, nome_produto FROM linhas ORDER BY nome_produto")
        for row in cursor.fetchall():
            linhas.append({'id': row[0], 'nome': row[1]})
            
        # Puxa Embalagens
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

    # CONECTANDO AO BANCO TINTOMÉTRICO
    with connections['tintometrico'].cursor() as cursor:
        # 1. Tenta achar a cor pelo Nome ou Código Técnico
        cursor.execute("""
            SELECT nome_busca, codigo_tecnico FROM cores 
            WHERE nome_busca LIKE %s OR codigo_tecnico LIKE %s LIMIT 1
        """, [f"%{cor_busca}%", f"%{cor_busca}%"])
        
        cor = cursor.fetchone()
        if not cor:
            resultado['erro'] = f"Cor '{cor_busca}' não foi encontrada no catálogo."
            return resultado
        
        resultado['cor_encontrada'] = cor[0] # nome_busca
        codigo_tecnico = cor[1]
        
        # 2. Busca a Receita Matemática
        cursor.execute("""
            SELECT id_base, dosagem FROM formulas 
            WHERE codigo_cor = %s AND id_linha = %s AND id_emb = %s LIMIT 1
        """, [codigo_tecnico, linha_id, embalagem_id])
        
        formula = cursor.fetchone()
        if not formula:
            resultado['erro'] = "Não existe fórmula para esta Cor na Linha e Embalagem selecionadas."
            return resultado
        
        id_base, dosagem_str = formula
        
        # 3. Descobre qual é a Base Exigida e o seu Preço de Custo
        cursor.execute("""
            SELECT b.nome_base, p.custo_unitario 
            FROM bases b 
            LEFT JOIN precos_custo p ON p.id_referencia = b.id_base AND p.tipo_item = 'BASE'
            WHERE b.id_base = %s LIMIT 1
        """, [id_base])
        
        base_info = cursor.fetchone()
        if base_info:
            resultado['nome_base'] = base_info[0]
            resultado['preco_base'] = float(base_info[1] or 0.0)
        else:
            resultado['nome_base'] = "Base Desconhecida"

        # 4. Magia Tintométrica: Lê a 'dosagem' (Ex: "P:12.50, A:4.20") e calcula custo do ML
        custo_total_corantes = 0.0
        
        if dosagem_str:
            # Expressão Regular para extrair Letras e Números automaticamente
            pares = re.findall(r'([A-Za-z0-9]+)\s*[:=-]\s*([\d\.,]+)', dosagem_str)
            
            for letra, qtd_str in pares:
                qtd = float(qtd_str.replace(',', '.'))
                
                cursor.execute("""
                    SELECT c.nome_pigmento, c.posicao_maquina, p.custo_unitario 
                    FROM corantes c
                    LEFT JOIN precos_custo p ON p.id_referencia = c.id_formula AND p.tipo_item = 'CORANTE'
                    WHERE c.letra_codigo = %s LIMIT 1
                """, [letra])
                
                corante_info = cursor.fetchone()
                if corante_info:
                    nome_pigmento, posicao, custo_ml = corante_info
                    custo_ml = float(custo_ml or 0.0)
                    
                    custo_parcial = qtd * custo_ml
                    custo_total_corantes += custo_parcial
                    
                    resultado['corantes'].append({
                        'letra': letra, 'nome': nome_pigmento, 'posicao': posicao,
                        'quantidade': qtd, 'custo_parcial': custo_parcial
                    })
                    
        resultado['custo_corantes'] = custo_total_corantes
        
        # 5. Fechamento Final (Aplicando margem de lucro de 35% como exemplo)
        custo_bruto = resultado['preco_base'] + custo_total_corantes
        resultado['valor_total'] = custo_bruto * 1.35 
        resultado['sucesso'] = True

    return resultado
