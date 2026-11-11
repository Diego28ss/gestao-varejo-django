from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.db import connections
from inventario.models import Familia, Marca, LojaFilial
from inventario.models.configuracoes import ConfiguracaoSistema, ConfiguracaoEmissor, TaxasMaquininha
from inventario.services.configuracoes.configuracoes_service import obter_dados_auxiliares, processar_salvamento_configuracoes

def verifica_acesso_gerente(request):
    if 'usuario_logado' not in request.session: return False
    if request.session.get('perfil_usuario') != 'Gerente':
        messages.error(request, "Acesso restrito exclusivamente ao cargo Gerente.")
        return False
    return True

def tela_configuracoes_sistema(request):
    if not verifica_acesso_gerente(request): return redirect('painel_principal')
    return render(request, 'inventario/configuracoes_sistema.html')

def config_loja(request):
    if not verifica_acesso_gerente(request): return redirect('painel_principal')
    loja, _ = LojaFilial.objects.get_or_create(id=1, defaults={'nome': 'JB Tintas (Matriz)'})
    return render(request, 'inventario/config_loja.html', {'loja': loja})

def config_fidelidade(request):
    if not verifica_acesso_gerente(request): return redirect('painel_principal')
    config, _ = ConfiguracaoSistema.objects.get_or_create(id=1)
    return render(request, 'inventario/config_fidelidade.html', {'config': config})

def config_estoque(request):
    if not verifica_acesso_gerente(request): return redirect('painel_principal')
    config, _ = ConfiguracaoSistema.objects.get_or_create(id=1)
    return render(request, 'inventario/config_estoque.html', {'config': config})

def config_fiscal(request):
    if not verifica_acesso_gerente(request): return redirect('painel_principal')
    loja, _ = ConfiguracaoEmissor.objects.get_or_create(id=1)
    return render(request, 'inventario/config_fiscal.html', {'loja': loja})

def config_auxiliares(request):
    if not verifica_acesso_gerente(request): return redirect('painel_principal')
    familias, marcas, unidades = obter_dados_auxiliares()
    return render(request, 'inventario/config_auxiliares.html', {
        'familias': familias, 'marcas': marcas, 'unidades': unidades
    })

# 🚀 ROTA BLOCO B: MAQUININHAS
def config_maquininha(request):
    if not verifica_acesso_gerente(request): return redirect('painel_principal')
    
    taxas = {}
    
    # Carrega taxa de Débito (sempre 1 parcela)
    debito, _ = TaxasMaquininha.objects.get_or_create(metodo='CARTAO_DEBITO', parcelas=1)
    taxas['debito'] = debito
    
    # Carrega taxas de Crédito (de 1 a 12 vezes)
    credito = {}
    for i in range(1, 13):
        taxa_credito, _ = TaxasMaquininha.objects.get_or_create(metodo='CARTAO_CREDITO', parcelas=i)
        credito[f'p{i}'] = taxa_credito
        
    taxas['credito'] = credito
    
    return render(request, 'inventario/configuracoes_maquininha.html', {'taxas': taxas})

def salvar_configuracoes_sistema(request):
    if not verifica_acesso_gerente(request): return redirect('painel_principal')
        
    if request.method == 'POST':
        origem = request.POST.get('origem') 
        try:
            if origem == 'loja':
                loja = LojaFilial.objects.get(id=1)
                loja.nome = request.POST.get('nome', loja.nome)
                loja.codigo_ibge = request.POST.get('codigo_ibge', loja.codigo_ibge)
                loja.save()
                
            elif origem == 'maquininha':
                # Salva Débito
                debito = TaxasMaquininha.objects.get(metodo='CARTAO_DEBITO', parcelas=1)
                val_deb = request.POST.get('taxa_debito', '0').strip().replace(',', '.')
                debito.taxa_percentual = val_deb if val_deb else '0'
                debito.save()
                
                # 🚀 FASE 22.1: Salva Crédito apenas com o Valor Mínimo (A Partir de)
                for i in range(1, 13):
                    credito = TaxasMaquininha.objects.get(metodo='CARTAO_CREDITO', parcelas=i)
                    
                    val_cred = request.POST.get(f'taxa_credito_{i}', '0').strip().replace(',', '.')
                    val_min = request.POST.get(f'min_credito_{i}', '0').strip().replace(',', '.')
                    
                    credito.taxa_percentual = val_cred if val_cred else '0'
                    credito.valor_minimo = val_min if val_min else '0'
                    credito.valor_maximo = None # Limpa qualquer valor máximo antigo para evitar conflitos
                        
                    credito.save()
            else:
                processar_salvamento_configuracoes(origem, request.POST)
                
            messages.success(request, "Configurações atualizadas com sucesso!")
            
            if origem == 'loja': return redirect('config_loja')
            if origem == 'fiscal': return redirect('config_fiscal')
            if origem == 'fidelidade': return redirect('config_fidelidade')
            if origem == 'estoque': return redirect('config_estoque')
            if origem == 'maquininha': return redirect('config_maquininha')
            
        except Exception as e:
            messages.error(request, f"Erro ao salvar configurações: {e}")
            
    return redirect('tela_configuracoes_sistema')



@csrf_exempt
def api_gerenciar_auxiliares(request):
    """ API chamada via AJAX pela tela de Auxiliares (Marcas, Famílias, Unidades) """
    if 'usuario_logado' not in request.session:
        return JsonResponse({'sucesso': False, 'erro': 'Acesso negado.'}, status=403)
        
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            acao = dados.get('acao')
            tabela = dados.get('tabela')
            item_id = dados.get('id')
            novo_nome = dados.get('nome', '').strip()

            if acao in ['adicionar', 'editar'] and not novo_nome:
                return JsonResponse({'sucesso': False, 'erro': 'O nome não pode ficar vazio.'})

            if tabela == 'familia':
                if acao == 'adicionar': Familia.objects.create(nome=novo_nome)
                elif acao == 'editar' and item_id:
                    f = Familia.objects.get(id=item_id)
                    f.nome = novo_nome
                    f.save()
                elif acao == 'excluir' and item_id: Familia.objects.filter(id=item_id).delete()

            elif tabela == 'marca':
                if acao == 'adicionar': Marca.objects.create(nome=novo_nome)
                elif acao == 'editar' and item_id:
                    m = Marca.objects.get(id=item_id)
                    m.nome = novo_nome
                    m.save()
                elif acao == 'excluir' and item_id: Marca.objects.filter(id=item_id).delete()

            elif tabela == 'un':
                with connections['default'].cursor() as cursor:
                    if acao == 'adicionar': cursor.execute("INSERT INTO inventario_un (nome) VALUES (%s)", [novo_nome])
                    elif acao == 'editar' and item_id: cursor.execute("UPDATE inventario_un SET nome = %s WHERE id = %s", [novo_nome, item_id])
                    elif acao == 'excluir' and item_id: cursor.execute("DELETE FROM inventario_un WHERE id = %s", [item_id])
            else:
                return JsonResponse({'sucesso': False, 'erro': 'Tabela desconhecida.'})

            return JsonResponse({'sucesso': True, 'mensagem': 'Operação realizada com sucesso!'})
        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': str(e)})
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido.'})
