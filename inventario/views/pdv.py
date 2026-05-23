import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Q

# Importação dos modelos necessários
from inventario.models import Produtos, Clientes, Usuarios

# 🔥 AQUI ESTÁ A CORREÇÃO PRINCIPAL: Adicionamos o 'tintometrico' na importação!
from inventario.services import fidelidade, vendas, tintometrico

# ==========================================
# 🛒 FRENTE DE CAIXA (PDV)
# ==========================================

def tela_pdv(request):
    if 'usuario_logado' not in request.session:
        return redirect('login')

    produtos = Produtos.objects.exclude(status='INATIVO')
    vendedores = Usuarios.objects.all()
    clientes = Clientes.objects.all()

    context = {
        'produtos': produtos,
        'vendedores': vendedores,
        'vendedores_list': vendedores,
        'clientes': clientes,
        'pintores': clientes.filter(tipo__icontains='PINTOR'),
    }
    return render(request, 'inventario/pdv.html', context)


def api_consultar_pontos(request):
    nome_cliente = request.GET.get('cliente', '')
    resultado = fidelidade.calcular_resgate_pontos(nome_cliente)
    return JsonResponse(resultado)


def api_buscar_produtos(request):
    query = request.GET.get('q', '').strip()
    produtos = Produtos.objects.exclude(status='INATIVO')

    if query:
        palavras = query.split()
        for palavra in palavras:
            produtos = produtos.filter(
                Q(nome__icontains=palavra) |
                Q(cod_barras__icontains=palavra)
            )

    produtos = produtos[:50]
    resultados = []
    for p in produtos:
        resultados.append({
            'id': p.id,
            'nome': p.nome,
            'preco_venda': float(p.preco_venda),
            'estoque_atual': p.estoque_atual,
            'cod_barras': p.cod_barras or ''
        })
    return JsonResponse({'produtos': resultados})


def api_salvar_venda(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            status_venda = dados.get('status', 'VENDA')
            pontos_resgatados = int(dados.get('pontos_resgatados', 0))
            carrinho = dados.get('carrinho', [])

            dados_venda = {
                'valor_total': dados.get('valor_final'),
                'valor_desconto': dados.get('desconto'),
                'vendedor': dados.get('vendedor'),
                'cliente': dados.get('cliente'),
                'indicante': dados.get('indicante'),
                'status': status_venda,
                'cupom_texto': json.dumps(carrinho)
            }

            venda_id = vendas.processar_nova_venda(dados_venda, carrinho, status_venda, pontos_resgatados=pontos_resgatados)
            return JsonResponse({'status': 'sucesso', 'venda_id': venda_id})

        except ValueError as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
        except Exception as e:
            print(f"Erro ao salvar venda: {e}")
            return JsonResponse({'status': 'erro', 'mensagem': 'Erro interno ao processar venda no servidor.'})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})


# ==========================================
# 🎨 MÁQUINA TINTOMÉTRICA (NOVO)
# ==========================================

from django.db import connections

def api_buscar_cores(request):
    query = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0)) 
    
    if len(query) < 2:
        return JsonResponse({'cores': [], 'has_more': False})

    resultados_dict = {}
    
    with connections['tintometrico'].cursor() as cursor:
        # 1. BUSCA ULTRA-RÁPIDA (Só nas cores, sem cruzar tabelas)
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

        # Prepara uma lista só com as 26 cores encontradas para usar na segunda busca
        codigos_e_nomes_para_busca = []
        
        for nome, codigo in cores_banco:
            chave = f"{nome}_{codigo}"
            resultados_dict[chave] = {
                'nome': nome,
                'codigo': codigo,
                'combinacoes_validas': []
            }
            # Guarda o nome e o código em maiúsculas para procurar as fórmulas
            codigos_e_nomes_para_busca.extend([nome.upper(), codigo.upper()])

        # 2. BUSCA DE FÓRMULAS DIRECIONADA (Pergunta só pelas 26 cores)
        # Cria os espaços (%s) dependendo de quantas cores encontrámos
        placeholders = ', '.join(['%s'] * len(codigos_e_nomes_para_busca))
        
        cursor.execute(f"""
            SELECT UPPER(TRIM(codigo_cor)), id_linha, id_emb 
            FROM formulas 
            WHERE UPPER(TRIM(codigo_cor)) IN ({placeholders})
        """, codigos_e_nomes_para_busca)
        
        formulas_banco = cursor.fetchall()
        
        # 3. JUNTA AS PEÇAS NO PYTHON (Ocorre em milissegundos)
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
    
    # Preenche os menus com os dados reais do banco 'banco_tintometrico.db'
    linhas, embalagens = tintometrico.obter_linhas_e_embalagens()
    context['linhas'] = linhas
    context['embalagens'] = embalagens
    
    # Captura a pesquisa do vendedor (se ele clicou em "Calcular Fórmula")
    cor_busca = request.GET.get('cor', '')
    linha_id = request.GET.get('linha', '')
    embalagem_id = request.GET.get('embalagem', '')
    
    # Devolve o que foi pesquisado para manter os menus selecionados
    context['filtros'] = {'cor': cor_busca, 'linha': linha_id, 'embalagem': embalagem_id}
    
    # Roda a matemática se os 3 campos estiverem preenchidos
    if cor_busca and linha_id and embalagem_id:
        try:
            context['resultado'] = tintometrico.calcular_formula(cor_busca, linha_id, embalagem_id)
        except Exception as e:
            context['resultado'] = {'sucesso': False, 'erro': f"Erro interno: {str(e)}"}
            
    return render(request, 'inventario/tintometrico.html', context)

