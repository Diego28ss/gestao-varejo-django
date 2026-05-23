from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connections

# Importamos o serviço matemático
from inventario.services import tintometrico as tintometrico_service

# ==========================================
# 🎨 VIEWS DO TINTOMÉTRICO
# ==========================================

def api_buscar_cores(request):
    query = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0)) 
    
    if len(query) < 2:
        return JsonResponse({'cores': [], 'has_more': False})

    resultados_dict = {}
    
    with connections['tintometrico'].cursor() as cursor:
        cursor.execute("""
            SELECT TRIM(nome_busca), TRIM(codigo_tecnico) 
            FROM cores 
            WHERE nome_busca LIKE %s OR codigo_tecnico LIKE %s 
            ORDER BY nome_busca
            LIMIT 26 OFFSET %s
        """, [f"%{query}%", f"%{query}%", offset])
        
        cores_banco = cursor.fetchall()
        
        if not cores_banco:
            return JsonResponse({'cores': [], 'has_more': False})

        codigos_e_nomes_para_busca = []
        
        for nome, codigo in cores_banco:
            chave = f"{nome}_{codigo}"
            resultados_dict[chave] = {
                'nome': nome,
                'codigo': codigo,
                'combinacoes_validas': []
            }
            codigos_e_nomes_para_busca.extend([nome.upper(), codigo.upper()])

        placeholders = ', '.join(['%s'] * len(codigos_e_nomes_para_busca))
        
        cursor.execute(f"""
            SELECT UPPER(TRIM(codigo_cor)), id_linha, id_emb 
            FROM formulas 
            WHERE UPPER(TRIM(codigo_cor)) IN ({placeholders})
        """, codigos_e_nomes_para_busca)
        
        formulas_banco = cursor.fetchall()
        
        for codigo_cor_formula, id_linha, id_emb in formulas_banco:
            for chave, dados in resultados_dict.items():
                if dados['nome'].upper() == codigo_cor_formula or dados['codigo'].upper() == codigo_cor_formula:
                    dados['combinacoes_validas'].append({
                        'linha': str(id_linha),
                        'embalagem': str(id_emb)
                    })
                
    todas_cores = list(resultados_dict.values())
    has_more = len(todas_cores) > 25 
    resultados_finais = todas_cores[:25]
            
    return JsonResponse({'cores': resultados_finais, 'has_more': has_more})


def tela_tintometrico(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')
        
    context = {}
    
    linhas, embalagens = tintometrico_service.obter_linhas_e_embalagens()
    context['linhas'] = linhas
    context['embalagens'] = embalagens
    
    cor_busca = request.GET.get('cor', '')
    linha_id = request.GET.get('linha', '')
    embalagem_id = request.GET.get('embalagem', '')
    
    context['filtros'] = {'cor': cor_busca, 'linha': linha_id, 'embalagem': embalagem_id}
    
    if cor_busca and linha_id and embalagem_id:
        try:
            context['resultado'] = tintometrico_service.calcular_formula(cor_busca, linha_id, embalagem_id)
        except Exception as e:
            context['resultado'] = {'sucesso': False, 'erro': f"Erro interno: {str(e)}"}
            
        # 🔥 AQUI ESTÁ A NOSSA ARMADILHA PARA PEGAR O ERRO SILENCIOSO 🔥
        print(f"DEBUG DO RESULTADO: {context.get('resultado')}")
            
    return render(request, 'inventario/tintometrico.html', context) 