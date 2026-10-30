from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt

from inventario.models import RelacaoEmbalagensTintometrico, Produtos
from inventario.services import tintometrico as tintometrico_service

# 🔥 IMPORTAÇÃO ATUALIZADA (Caso o formulário seja utilizado nesta view)
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

    # Geração do contexto da view (combinações e produtos já integrados no serviço originalmente)
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
    context['linhas'], context['embalagens'] = tintometrico_service.obter_linhas_e_embalagens()
    
    cor_busca, linha, embalagem = request.GET.get('cor', ''), request.GET.get('linha', ''), request.GET.get('embalagem', '')
    if cor_busca and linha and embalagem:
        try:
            context['resultado'] = tintometrico_service.calcular_formula(cor_busca, linha, embalagem)
        except Exception as e:
            context['resultado'] = {'sucesso': False, 'erro': str(e)}
            
    return render(request, 'inventario/tintometrico.html', context)
