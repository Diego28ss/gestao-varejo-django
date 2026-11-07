import unicodedata
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import ProtectedError
from inventario.models import Usuarios
from inventario.services.rh import rh_service

def tela_colaboradores(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    perfil = request.session.get('perfil_usuario', 'Vendedor')
    login_usuario = request.session.get('usuario_logado')
    
    equipe, lojas = rh_service.obter_lista_equipe(perfil, login_usuario)
    
    # 🚀 Filtro de Segurança: Só envia para a tela os colaboradores que NÃO estão Inativos
    equipe_ativa = [c for c in equipe if getattr(c, 'status', 'Ativo') != 'INATIVO']
    
    return render(request, 'inventario/colaboradores.html', {'equipe': equipe_ativa, 'lojas': lojas})

def gerar_login_tec(nome_completo):
    """
    Transforma 'Paolla dos Santos Lima' em 'paollal.tec'
    Garante unicidade automática (paollal2.tec, paollal3.tec...)
    """
    if not nome_completo:
        return "usuario.tec"
        
    # Remove acentos e joga tudo para minúsculo
    nome_limpo = unicodedata.normalize('NFKD', nome_completo).encode('ASCII', 'ignore').decode('utf-8').lower()
    partes = nome_limpo.strip().split()
    
    if len(partes) == 0:
        return "usuario.tec"
    elif len(partes) == 1:
        base_login = partes[0]
    else:
        primeiro_nome = partes[0]
        ultimo_nome_inicial = partes[-1][0]  # Primeira letra do último sobrenome
        base_login = f"{primeiro_nome}{ultimo_nome_inicial}"

    login_final = f"{base_login}.tec"
    
    # Validação de unicidade para evitar duplicidade de logins iguais
    contador = 2
    while Usuarios.objects.filter(login=login_final).exists():
        login_final = f"{base_login}{contador}.tec"
        contador += 1
        
    return login_final

def salvar_colaborador(request):
    if request.method == 'POST':
        try:
            dados_post = request.POST.copy()
            login_gerado = None
            
            # 1. Se NÃO tiver ID, significa que estamos criando um novo colaborador
            if not dados_post.get('colaborador_id'):
                nome_digitado = dados_post.get('nome_completo', '').strip()
                login_gerado = gerar_login_tec(nome_digitado)
                
                if 'login' in dados_post:
                    del dados_post['login']
                dados_post.setlist('login', [login_gerado])
            
            msg = rh_service.salvar_membro_equipe(
                dados_post, 
                request.session.get('perfil_usuario', ''), 
                request.session.get('usuario_logado', '')
            )
            
            # TRAVA DE SEGURANÇA INFALÍVEL
            if login_gerado:
                usuario_vazio = Usuarios.objects.filter(login="").last()
                if usuario_vazio:
                    usuario_vazio.login = login_gerado
                    usuario_vazio.save()
                    
            messages.success(request, msg)
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Erro inesperado ao salvar: {str(e)}")
            
    return redirect('tela_colaboradores')

def excluir_colaborador(request, id):
    if 'usuario_logado' not in request.session: return redirect('login')
    try:
        login = rh_service.excluir_membro_equipe(id, request.session.get('perfil_usuario', ''))
        messages.success(request, f"Colaborador '{login}' removido fisicamente com sucesso!")
        
    except Exception as e:
        erro_str = str(e).lower()
        # 🚀 PADRÃO ERP DE SOFT DELETE (Se estiver atrelado a caixa ou venda, inativa)
        if "protectederror" in str(type(e)).lower() or "foreign key" in erro_str or "protected" in erro_str:
            usuario = Usuarios.objects.get(id=id)
            usuario.status = 'INATIVO'
            
            # Se for aquele utilizador fantasma que ficou sem login
            if not usuario.login:
                usuario.login = f"inativo_{usuario.id}.tec"
                
            usuario.save()
            messages.warning(request, f"O colaborador possui histórico financeiro no Caixa. Para proteger as auditorias, ele foi INATIVADO em vez de apagado.")
        else:
            messages.error(request, f"Erro ao excluir: {str(e)}")
            
    return redirect('tela_colaboradores')
