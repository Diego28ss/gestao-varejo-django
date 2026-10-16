import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from inventario.models import Produtos

# Importa a inteligência do novo serviço
from inventario.services.estoque.estoque_nfe_service import processar_xml_nfe, efetivar_lote_nfe, estornar_lote_nfe

def tela_entrada_carga(request):
    """ View Fina: Apenas renderiza a tela com controle de segurança """
    if 'usuario_logado' not in request.session: 
        return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor']:
        messages.error(request, "Acesso restrito a Gerentes e Supervisores.")
        return redirect('tela_estoque_produtos')
        
    return render(request, 'inventario/entrada_carga.html')

def api_importar_xml(request):
    """ View Fina: Recebe o arquivo e delega o processamento ao Service """
    if request.method == 'POST' and request.FILES.get('xml_file'):
        try:
            dados_nfe = processar_xml_nfe(request.FILES['xml_file'])
            return JsonResponse({'sucesso': True, 'nota': dados_nfe})
        except Exception as e:
            return JsonResponse({'erro': f'Erro ao ler o ficheiro XML: {str(e)}'}, status=500)
            
    return JsonResponse({'erro': 'Nenhum ficheiro enviado.'}, status=400)

def api_efetivar_nfe(request):
    """ View Fina: Recebe o JSON de confirmação e manda o Service salvar """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            qtd_processada = efetivar_lote_nfe(dados.get('itens', []))
            return JsonResponse({
                'sucesso': True, 
                'mensagem': f'{qtd_processada} produtos processados! Verifique o Estoque caso haja baixa de custo.'
            })
        except ValueError as ve:
            return JsonResponse({'erro': str(ve)}, status=400)
        except Exception as e:
            return JsonResponse({'erro': f'Erro Interno: {str(e)}'}, status=500)
            
    return JsonResponse({'erro': 'Método inválido.'}, status=400)

def api_estornar_nfe(request):
    """ View Fina: Aciona o estorno no Service """
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            qtd_estornada = estornar_lote_nfe(dados.get('itens', []))
            return JsonResponse({
                'sucesso': True, 
                'mensagem': f'Estoque estornado com sucesso para {qtd_estornada} produtos!'
            })
        except ValueError as ve:
            return JsonResponse({'erro': str(ve)}, status=400)
        except Exception as e:
            return JsonResponse({'erro': f'Erro Interno: {str(e)}'}, status=500)
            
    return JsonResponse({'erro': 'Método inválido.'}, status=400)

def api_pesquisar_produto_nfe(request):
    """ Auxiliar da Tela: Busca de produtos para vínculo """
    q = request.GET.get('q', '').strip()
    if not q: return JsonResponse({'produtos': []})

    produtos = Produtos.objects.filter(status='ATIVO')
    termos = q.split()
    for termo in termos:
        produtos = produtos.filter(
            Q(nome__icontains=termo) | 
            Q(cod_barras__icontains=termo) | 
            Q(cod_interno__icontains=termo)
        )

    produtos = produtos[:15]
    resultado = [{'id': p.id, 'nome': p.nome, 'cod_interno': p.cod_interno or p.cod_barras or str(p.id)} for p in produtos]
    return JsonResponse({'produtos': resultado})
