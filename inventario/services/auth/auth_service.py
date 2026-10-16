from inventario.models import Usuarios

def autenticar_usuario(login, senha):
    """ Valida as credenciais na base de dados """
    colaborador = Usuarios.objects.filter(login=login).first()
    
    # Valida se o usuário existe e se a senha confere
    if colaborador and colaborador.senha == senha:
        return colaborador
        
    return None
