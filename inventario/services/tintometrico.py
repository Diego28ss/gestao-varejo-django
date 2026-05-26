import re
from django.db import connections
# 👇 IMPORTAÇÃO NOVA E NECESSÁRIA PARA LER O ESTOQUE PRINCIPAL
from inventario.models import Produtos 

def obter_todas_bases_tamanhos():
    """
    Gera a grelha cruzando as Bases (garantidas pela tabela de formulas)
    com os Tamanhos de embalagens permitidos.
    """
    combinacoes = []
    ordem_embalagens = [1, 2, 3, 7, 8, 39, 21, 32, 9, 10, 28, 29, 30, 35, 36, 37, 38]

    with connections['tintometrico_db'].cursor() as cursor:
        # 1. Puxar Bases garantidas
        cursor.execute("""
            SELECT DISTINCT b.nome_base 
            FROM formulas f
            JOIN bases b ON f.id_base = b.id_base
            WHERE b.nome_base IS NOT NULL AND TRIM(b.nome_base) != ''
            ORDER BY b.nome_base
        """)
        bases = [str(row[0]).strip() for row in cursor.fetchall() if row[0]]

        # 2. Puxar Tamanhos
        placeholders = ', '.join(['%s'] * len(ordem_embalagens))
        cursor.execute(f"SELECT id_emb, tamanho FROM embalagens WHERE id_emb IN ({placeholders})", ordem_embalagens)
        embalagens_banco = {row[0]: str(row[1]).strip() for row in cursor.fetchall() if row[1]}

        tamanhos = []
        for id_emb in ordem_embalagens:
            if id_emb in embalagens_banco:
                tamanhos.append(embalagens_banco[id_emb])

        # 3. Criar a grelha
        for base in bases:
            for tamanho in tamanhos:
                combinacoes.append({
                    'base': base,
                    'tamanho': tamanho
                })

    return combinacoes


def obter_linhas_e_embalagens():
    """Puxa do banco de dados as opções, filtrando e ordenando as embalagens de forma customizada"""
    linhas, embalagens = [], []
    ordem_embalagens = [1, 2, 3, 7, 8, 39, 21, 32, 9, 10, 28, 29, 30, 35, 36, 37, 38]
    
    with connections['tintometrico_db'].cursor() as cursor:
        cursor.execute("SELECT id_linha, nome_produto FROM linhas ORDER BY nome_produto")
        for row in cursor.fetchall():
            linhas.append({'id': row[0], 'nome': row[1]})
            
        placeholders = ', '.join(['%s'] * len(ordem_embalagens))
        cursor.execute(f"SELECT id_emb, tamanho FROM embalagens WHERE id_emb IN ({placeholders})", ordem_embalagens)
        embalagens_banco = {row[0]: row[1] for row in cursor.fetchall()}
        
        for id_emb in ordem_embalagens:
            if id_emb in embalagens_banco:
                embalagens.append({'id': id_emb, 'tamanho': embalagens_banco[id_emb]})
                
    return linhas, embalagens


def calcular_formula(cor_busca, linha_id, embalagem_id):
    """Calcula a base, corantes e valores escalando a partir da fórmula de 800ml (DNA)"""
    resultado = {
        'sucesso': False, 'erro': None, 'cor_encontrada': None, 
        'nome_base': None, 'preco_base': 0.0, 'corantes': [], 
        'custo_corantes': 0.0, 'valor_total': 0.0,
        'multiplicador_usado': 1.0 
    }

    try:
        linha_id = int(linha_id)
        embalagem_id = int(embalagem_id)
    except (ValueError, TypeError):
        resultado['erro'] = "Os filtros de Linha ou Embalagem são inválidos."
        return resultado

    with connections['tintometrico_db'].cursor() as cursor:
        
        # ==========================================================
        # PASSO 1: DESCOBRIR O VOLUME DA EMBALAGEM E O MULTIPLICADOR
        # ==========================================================
        cursor.execute("SELECT tamanho FROM embalagens WHERE id_emb = %s LIMIT 1", [embalagem_id])
        emb_row = cursor.fetchone()
        tamanho_str = emb_row[0].upper() if emb_row else "800ML"
        
        numeros = re.findall(r"[\d.,]+", tamanho_str)
        volume_desejado = 0.8 
        
        if numeros:
            val = float(numeros[0].replace(',', '.'))
            if 'ML' in tamanho_str:
                volume_desejado = val / 1000.0  
            else:
                volume_desejado = val           
                
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
        # PASSO 3: BUSCA A FÓRMULA DNA
        # ==========================================================
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
        # PASSO 4: BASE
        # ==========================================================
        cursor.execute("SELECT nome_base FROM bases WHERE id_base = %s LIMIT 1", [id_base])
        base_info = cursor.fetchone()
        
        if base_info:
            resultado['nome_base'] = base_info[0]
            # O preço da base agora é lido pelo JavaScript na view, portanto aqui iniciamos a 0.0
            resultado['preco_base'] = 0.0 
        else:
            resultado['nome_base'] = "Base Desconhecida"

        # ==========================================================
        # PASSO 5: MAGIA TINTOMÉTRICA (INTEGRAÇÃO COM O ESTOQUE FÍSICO) 🚀
        # ==========================================================
        custo_total_corantes = 0.0
        
        if dosagem_str:
            partes = [p.strip() for p in str(dosagem_str).split(',')]
            
            for i in range(0, len(partes), 2):
                if i + 1 < len(partes):
                    letra = partes[i] 
                    qtd_str = partes[i+1]
                    
                    try:
                        qtd_dna = float(qtd_str.replace(',', '.'))
                    except ValueError:
                        continue 
                    
                    qtd_final_multiplicada = qtd_dna * multiplicador
                    
                    # 1️⃣ Traz o Corante e descobre qual é o Código Interno dele
                    cursor.execute("""
                        SELECT nome_pigmento, letra_codigo, produto_cod_interno 
                        FROM corantes 
                        WHERE id_formula = %s OR UPPER(TRIM(letra_codigo)) = UPPER(TRIM(%s)) LIMIT 1
                    """, [letra, letra])
                    
                    corante_info = cursor.fetchone()
                    if corante_info:
                        nome_pigmento, letra_real, cod_interno_corante = corante_info
                        custo_ml = 0.0
                        
                        # 2️⃣ Vai ao banco Principal (Estoque) ver quanto custa o Frasco na vida real
                        if cod_interno_corante:
                            produto_estoque = Produtos.objects.using('default').filter(cod_interno=cod_interno_corante).first()
                            if produto_estoque and produto_estoque.preco_custo:
                                preco_frasco = float(produto_estoque.preco_custo)
                                # 3️⃣ A MATEMÁTICA: (Preço do Frasco / 946ml)
                                custo_ml = preco_frasco / 946.0
                        
                        # 4️⃣ Calcula o custo deste corante para esta lata e soma ao total
                        custo_parcial = qtd_final_multiplicada * custo_ml
                        custo_total_corantes += custo_parcial
                        
                        resultado['corantes'].append({
                            'letra_codigo': letra_real, 
                            'nome': nome_pigmento, 
                            'quantidade': qtd_final_multiplicada, 
                            'custo_parcial': custo_parcial
                        })
        
        resultado['custo_corantes'] = custo_total_corantes
        
        # O total final financeiro é agora somado pelo seu Javascript no ecrã 
        # (pois o preço de venda da base também é injetado pelo Javascript).
        # Aqui, enviamos apenas o custo bruto dos corantes e preparamos a variável.
        resultado['valor_total'] = 0.0 
        resultado['sucesso'] = True

    return resultado
