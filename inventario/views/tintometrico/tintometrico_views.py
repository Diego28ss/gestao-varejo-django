import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt

from inventario.models import RelacaoEmbalagensTintometrico, Produtos
from inventario.services.tintometrico import tintometrico_service
from inventario.forms.tintometrico_forms import TintometricoForm

# ==========================================
# 🎨 VIEWS DO TINTOMÉTRICO (THIN VIEWS)
# ==========================================

def api_buscar_detalhes_base(request):
    if request.method != "GET":
        return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido. Use GET.'})
        
    cod_interno = request.GET.get('cod_interno', '').strip()
    base = request.GET.get('base', '').strip()
    tamanho = request.GET.get('tamanho', '').strip()
    
    resultado = tintometrico_service.buscar_detalhes_base(cod_interno, base, tamanho)
    return JsonResponse(resultado)


def api_pesquisar_base_alternativa(request):
    query = request.GET.get('q', '').strip()
    produtos = tintometrico_service.pesquisar_base_alternativa(query)
    return JsonResponse({'produtos': produtos})


def cadastrar_tintometrico(request):
    if request.method == 'POST':
        bases = request.POST.getlist('base[]')
        tamanhos = request.POST.getlist('tamanho[]')
        produtos_cods = request.POST.getlist('produto[]')
        
        try:
            salvos, falhas = tintometrico_service.processar_salvamento_lote(bases, tamanhos, produtos_cods)
            for falha in falhas:
                messages.warning(request, f"Aviso: Produto {falha} não encontrado.")
            messages.success(request, f"✅ {salvos} vínculos foram atualizados/salvos com sucesso!")
            return redirect('lista_tintometrico')
        except Exception as e:
            messages.error(request, f"❌ Erro crítico ao salvar lote: {str(e)}")

    todas_combinacoes = tintometrico_service.obter_todas_bases_tamanhos()
    vinculos = RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').all()
    mapa_vinculos = {f"{v.codigo_base_tintometrico}_{v.tamanho_codigo}": v.produto_cod_interno_id for v in vinculos}
    
    grade = [{
        'base': c['base'], 'tamanho': c['tamanho'], 
        'produto_vinculado': mapa_vinculos.get(f"{c['base']}_{c['tamanho']}", '')
    } for c in todas_combinacoes]
    
    return render(request, 'inventario/cadastro_tintometrico.html', {
        'grade': grade, 'produtos_estoque': Produtos.objects.all()
    })


def consultar_dados_embalagem(request):
    base = request.GET.get('base', '').strip()
    tamanho = request.GET.get('tamanho', '').strip()

    try:
        produto = tintometrico_service.obter_vinculo_embalagem(base, tamanho)
        if produto:
            return JsonResponse({
                'sucesso': True,
                'cod_interno': produto.cod_interno,
                'cod_barras': getattr(produto, 'cod_barras', "SEM GTIN") or "SEM GTIN",
                'estoque': produto.estoque_atual,
                'unidade': getattr(produto, 'unidade', 'UN')
            })
        return JsonResponse({'sucesso': False, 'mensagem': f'Base "{base}" no Tamanho "{tamanho}" não vinculada.'})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})


def api_buscar_cores(request):
    query = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0))
    cores, has_more = tintometrico_service.executar_pesquisa_cores(query, offset)
    return JsonResponse({'cores': cores, 'has_more': has_more})


@xframe_options_exempt
def tela_painel_tintometrico(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/tintometrico_painel.html')


@xframe_options_exempt
def tela_tintometrico(request, marca=None):
    if 'usuario_logado' not in request.session: return redirect('login')
        
    context = {'marca_selecionada': marca.upper() if marca else 'CORAL'}
    linhas, embalagens = tintometrico_service.obter_linhas_e_embalagens()
    context['linhas'] = linhas
    context['embalagens'] = embalagens
    
    cor_busca = request.GET.get('cor', '')
    linha = request.GET.get('linha', '')
    embalagem_id = request.GET.get('embalagem', '')
    
    # 🚀 Recupera o nome exato da embalagem (ex: "3,2L") para injetar no HTML
    tamanho_texto = ""
    if embalagem_id:
        for emb in embalagens:
            if str(emb.get('id', '')) == str(embalagem_id):
                tamanho_texto = emb.get('tamanho', '')
                break
                
    context['filtros'] = {
        'cor': cor_busca,
        'linha': linha,
        'embalagem': embalagem_id,
        'tamanho': tamanho_texto
    }
    
    if cor_busca and linha and embalagem_id:
        try:
            context['resultado'] = tintometrico_service.calcular_formula(cor_busca, linha, embalagem_id)
        except Exception as e:
            context['resultado'] = {'sucesso': False, 'erro': str(e)}
            
    return render(request, 'inventario/tintometrico.html', context)


# ==========================================
# 🚀 APIS DE VINCULAÇÃO RÁPIDA (Fase 10)
# ==========================================
@csrf_exempt
def api_vincular_base(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            nome_base = dados.get('nome_base', '').strip()
            # 🚀 CORREÇÃO: Agora recebe o nome em texto (ex: "3.60 L") e não o ID
            tamanho = dados.get('tamanho', '').strip() 
            cod_interno = dados.get('cod_interno', '').strip()

            if not nome_base or not tamanho or not cod_interno:
                return JsonResponse({'status': 'erro', 'mensagem': 'Dados incompletos para vinculação.'})

            produto = Produtos.objects.filter(cod_interno=cod_interno).first()
            if not produto:
                return JsonResponse({'status': 'erro', 'mensagem': f'Produto de código "{cod_interno}" não encontrado no estoque.'})

            # Atualiza ou cria o vínculo oficial no banco tintométrico usando a string
            RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').update_or_create(
                codigo_base_tintometrico=nome_base,
                tamanho_codigo=tamanho,
                defaults={'produto_cod_interno_id': cod_interno}
            )

            return JsonResponse({
                'status': 'sucesso', 
                'cod_interno': produto.cod_interno,
                'cod_barras': getattr(produto, 'cod_barras', 'SEM GTIN') or 'SEM GTIN',
                'estoque': float(produto.estoque_atual) if produto.estoque_atual else 0.0
            })
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

@csrf_exempt
def api_desvincular_base(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            nome_base = dados.get('nome_base', '').strip()
            # 🚀 CORREÇÃO: Recebe o nome em texto
            tamanho = dados.get('tamanho', '').strip()

            RelacaoEmbalagensTintometrico.objects.using('tintometrico_db').filter(
                codigo_base_tintometrico=nome_base,
                tamanho_codigo=tamanho
            ).delete()

            return JsonResponse({'status': 'sucesso', 'mensagem': 'Base desvinculada com sucesso.'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

    