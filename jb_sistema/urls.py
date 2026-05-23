from django.contrib import admin
from django.urls import path

# Importação dos módulos de visualização padrão
from inventario.views import (
    auth, core, pdv, estoque, clientes, 
    auxiliares, relatorios, equipe, fidelidade
)

# 🔥 IMPORTAÇÃO DIRETA: Buscando as funções cirurgicamente de dentro do arquivo correto
from inventario.views.tintometrico_v import tela_tintometrico, api_buscar_cores

urlpatterns = [
    path('admin/', admin.site.urls),

    # 🔐 Autenticação
    path('', auth.tela_login, name='login'),
    path('logout/', auth.logout, name='logout'),

    # 📊 Painel Principal
    path('painel/', core.painel_principal, name='painel_principal'),

    # 🛒 Frente de Caixa (PDV)
    path('pdv/', pdv.tela_pdv, name='tela_pdv'),
    path('api/consultar-pontos/', pdv.api_consultar_pontos, name='api_consultar_pontos'),
    path('api/salvar-venda/', pdv.api_salvar_venda, name='api_salvar_venda'),
    path('api/buscar-produtos/', pdv.api_buscar_produtos, name='api_buscar_produtos'),

    # 📦 Controle de Estoque
    path('estoque/', estoque.tela_estoque_produtos, name='tela_estoque_produtos'),
    path('estoque/salvar/', estoque.salvar_produto, name='salvar_produto'),
    path('estoque/excluir/<int:id>/', estoque.excluir_produto, name='excluir_produto'),
    path('entrada-carga/', estoque.tela_entrada_carga, name='tela_entrada_carga'),
    path('api/produto-por-codigo/', estoque.api_produto_por_codigo, name='api_produto_por_codigo'),
    path('api/efetivar-entrada/', estoque.api_efetivar_entrada, name='api_efetivar_entrada'),

    # 👥 Clientes
    path('clientes/', clientes.tela_consultar_clientes, name='tela_consultar_clientes'),
    path('clientes/editar/', clientes.salvar_edicao_cliente, name='salvar_edicao_cliente'),
    path('clientes/excluir/<int:id>/', clientes.excluir_cliente, name='excluir_cliente'),
    path('api/historico-cliente/', clientes.api_historico_cliente, name='api_historico_cliente'),

    # ⚙️ Gerência de Auxiliares
    path('gerencia/auxiliares/', auxiliares.tela_marcas, name='tela_gerencia_auxiliares'),
    path('gerencia/marcas/', auxiliares.tela_marcas, name='tela_marcas'),
    path('gerencia/familias/', auxiliares.tela_familias, name='tela_familias'),
    path('gerencia/auxiliares/marca/salvar/', auxiliares.salvar_marca, name='salvar_marca'),
    path('gerencia/auxiliares/marca/excluir/<int:id>/', auxiliares.excluir_marca, name='excluir_marca'),
    path('gerencia/auxiliares/familia/salvar/', auxiliares.salvar_familia, name='salvar_familia'),
    path('gerencia/auxiliares/familia/excluir/<int:id>/', auxiliares.excluir_familia, name='excluir_familia'),

    # 📄 Relatórios
    path('gerencia/relatorios/', relatorios.tela_relatorios, name='tela_relatorios'),
    path('venda/cupom/<int:id>/', relatorios.imprimir_cupom, name='imprimir_cupom'),
    path('gerencia/vendas/cancelar/', relatorios.cancelar_venda, name='cancelar_venda'),
    path('venda/cupom-a4/<int:id>/', relatorios.imprimir_cupom_a4, name='imprimir_cupom_a4'),

    # 👥 Gestão de Equipe e Fidelidade
    path('gerencia/colaboradores/', equipe.tela_colaboradores, name='tela_colaboradores'),
    path('gerencia/colaboradores/salvar/', equipe.salvar_colaborador, name='salvar_colaborador'),
    path('gerencia/colaboradores/excluir/<int:id>/', equipe.excluir_colaborador, name='excluir_colaborador'),
    path('gerencia/pontos/', fidelidade.tela_manutencao_pontos, name='tela_manutencao_pontos'),
    path('gerencia/pontos/salvar/', fidelidade.salvar_configuracao_pontos, name='salvar_configuracao_pontos'),
         
    # 🎨 Tintométrico (Chamando as funções diretamente, sem o prefixo do módulo)
    path('tintometrico/', tela_tintometrico, name='tela_tintometrico'),
    path('api/buscar-cores/', api_buscar_cores, name='api_buscar_cores'),
]
