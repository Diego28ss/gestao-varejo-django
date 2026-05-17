# ==============================================================================
# O COMUNICADOR COM A INTERNET (WSGI)
# WSGI significa "Web Server Gateway Interface". Pense neste arquivo como o 
# "Atendente" ou o "Porta-voz" da nossa loja na internet. 
# O código Python (que busca os dados) e o Servidor Web (que mostra o site) 
# falam línguas diferentes. Este arquivo é o tradutor que os faz conversar.
# Quando formos hospedar o sistema na nuvem, o servidor profissional vai 
# procurar exatamente este arquivo para conseguir "ligar" a loja online.
# ==============================================================================

# 1. Preparando as ferramentas
# Trazendo as ferramentas básicas do computador (os) e o "ligador" oficial do Django.
import os
from django.core.wsgi import get_wsgi_application

# ==============================================================================
# 2. MOSTRANDO ONDE ESTÁ O MANUAL DA LOJA
# Aqui dizemos para o servidor da internet: "Ei, antes de tentar abrir a loja 
# para os clientes, vá ler o arquivo 'settings.py' dentro da pasta 'jb_sistema'. 
# É lá que estão as senhas, o banco de dados e as regras de negócio."
# ==============================================================================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jb_sistema.settings')

# ==============================================================================
# 3. ABRINDO AS PORTAS PARA FUNCIONAR (O Motor)
# Esta variável 'application' é a loja aberta funcionando na prática.
# Quando alguém abre o Google Chrome e clica em "Buscar Produto", o Chrome 
# bate na porta desta 'application'. Ela entra na loja, pergunta pro banco de 
# dados se a tinta existe, pega a resposta e entrega de volta para o Chrome 
# mostrar na tela do balcão.
# ==============================================================================
application = get_wsgi_application()