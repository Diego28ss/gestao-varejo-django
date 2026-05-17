#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

# ==============================================================================
# O GERENTE DO SISTEMA (O faz-tudo)
# Este é o ficheiro principal que usamos no terminal (a tela preta).
# Ele não é o site em si, mas é a ferramenta que liga o site, cria o banco de
# dados e faz as atualizações. Sempre que digitamos "python manage.py [comando]",
# estamos a dar uma ordem a este ficheiro.
# ==============================================================================

import os
import sys


def main():
    """Run administrative tasks."""

    # ==============================================================================
    # 1. MOSTRANDO ONDE ESTÃO AS REGRAS (O Manual da Loja)
    # A primeira coisa que o Gerente faz ao acordar é olhar para o ficheiro de
    # configurações (settings.py). Assim ele sabe onde está o banco de dados e as senhas.
    # ==============================================================================
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jb_sistema.settings')

    try:
        # ==============================================================================
        # 2. CHAMANDO O MOTOR DO DJANGO
        # Aqui o Gerente tenta ligar o motor principal do Django para executar
        # a ordem que você deu no terminal (ex: ligar o servidor com 'runserver').
        # ==============================================================================
        from django.core.management import execute_from_command_line

    except ImportError as exc:
        # Se der erro aqui, é porque o computador da loja não tem o Python ou o
        # Django instalados corretamente. Ele avisa o usuário com a mensagem abaixo.
        raise ImportError(
            "Não foi possível importar o Django. Tem a certeza de que ele está "
            "instalado e disponível? Esqueceu-se de ativar o ambiente virtual?"
        ) from exc

    # ==============================================================================
    # 3. EXECUTANDO A ORDEM
    # Pega naquilo que o utilizador digitou no terminal (sys.argv) e faz acontecer!
    # Se digitou 'runserver', ele liga a loja. Se digitou 'migrate', ele arruma o banco de dados.
    # ==============================================================================
    execute_from_command_line(sys.argv)


# Este é apenas um gatilho do Python. Diz que se alguém executar este ficheiro
# diretamente, ele deve rodar a função "main()" que criámos acima.
if __name__ == '__main__':
    main()