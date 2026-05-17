from django.contrib import admin
from django.urls import path
from inventario import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # 🔐 Autenticação
    path('', views.tela_login, name='login'),
    path('logout/', views.logout, name='logout'),

    # 📊 Painel Principal
    path('painel/', views.painel_principal, name='painel_principal'),

    # 🛒 PDV e APIs de Venda
    path('pdv/', views.tela_pdv, name='tela_pdv'),
    path('api/consultar_pontos/', views.api_consultar_pontos, name='api_consultar_pontos'),
    path('api/salvar_venda/', views.api_salvar_venda, name='api_salvar_venda'),
    path('api/buscar_produtos/', views.api_buscar_produtos, name='api_buscar_produtos'),

    # 📦 Controle de Estoque
    path('estoque/', views.tela_estoque_produtos, name='tela_estoque_produtos'),
    path('estoque/salvar/', views.salvar_produto, name='salvar_produto'),
    path('estoque/excluir/<int:id>/', views.excluir_produto, name='excluir_produto'),
    path('entrada-carga/', views.tela_entrada_carga, name='tela_entrada_carga'),

    # 👥 Clientes e Fidelidade
    path('clientes/', views.tela_consultar_clientes, name='tela_consultar_clientes'),
    path('clientes/editar/', views.salvar_edicao_cliente, name='salvar_edicao_cliente'),
    path('api/historico_cliente/', views.api_historico_cliente, name='api_historico_cliente'),

    # ⚙️ Gerência de Auxiliares SEPARADAS (Marcas / Fabricantes vs Famílias / Grupos)
    path('gerencia/auxiliares/', views.tela_marcas, name='tela_gerencia_auxiliares'),  # Compatibilidade de link antigo
    path('gerencia/marcas/', views.tela_marcas, name='tela_marcas'),
    path('gerencia/familias/', views.tela_familias, name='tela_familias'),
    path('gerencia/auxiliares/marca/salvar/', views.salvar_marca, name='salvar_marca'),
    path('gerencia/auxiliares/marca/excluir/<int:id>/', views.excluir_marca, name='excluir_marca'),
    path('gerencia/auxiliares/familia/salvar/', views.salvar_familia, name='salvar_familia'),
    path('gerencia/auxiliares/familia/excluir/<int:id>/', views.excluir_familia, name='excluir_familia'),

    # ⚙️ Fidelidade, Relatórios e Equipe
    path('gerencia/pontos/', views.tela_manutencao_pontos, name='tela_manutencao_pontos'),
    path('gerencia/pontos/salvar/', views.salvar_configuracao_pontos, name='salvar_configuracao_pontos'),
    path('gerencia/relatorios/', views.tela_relatorios, name='tela_relatorios'),
    path('gerencia/relatorios/imprimir/<int:id>/', views.imprimir_cupom, name='imprimir_cupom'),
    path('gerencia/relatorios/imprimir_a4/<int:id>/', views.imprimir_cupom_a4, name='imprimir_cupom_a4'),
    path('gerencia/colaboradores/', views.tela_colaboradores, name='tela_colaboradores'),
    path('gerencia/colaboradores/salvar/', views.salvar_colaborador, name='salvar_colaborador'),
    path('gerencia/colaboradores/excluir/<int:id>/', views.excluir_colaborador, name='excluir_colaborador'),
]