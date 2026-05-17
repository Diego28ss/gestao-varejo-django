from django.urls import path
from inventario import views

urlpatterns = [
    # Login e Painel
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('painel/', views.painel_principal, name='painel_principal'),

    # PDV e Vendas
    path('pdv/', views.tela_pdv, name='tela_pdv'),
    path('api/buscar_produtos/', views.api_buscar_produtos, name='api_buscar_produtos'),
    path('api/salvar_venda/', views.api_salvar_venda, name='api_salvar_venda'),
    path('api/consultar_pontos/', views.api_consultar_pontos, name='api_consultar_pontos'),  # NOVA API DE RESGATE
    path('cupom/<int:venda_id>/', views.imprimir_cupom, name='imprimir_cupom'),
    path('cupom_a4/<int:venda_id>/', views.imprimir_cupom_a4, name='imprimir_cupom_a4'),

    # Cadastros e Gestão de Clientes
    path('cadastro/', views.tela_cadastro, name='tela_cadastro'),
    path('clientes/consultar/', views.tela_consultar_clientes, name='tela_consultar_clientes'),
    path('clientes/editar/', views.salvar_edicao_cliente, name='salvar_edicao_cliente'),
    path('api/historico_cliente/', views.api_historico_cliente, name='api_historico_cliente'),
    path('clientes/excluir/<int:cliente_id>/', views.excluir_cliente, name='excluir_cliente'),

    # Estoque e Carga
    path('estoque/produtos/', views.tela_estoque_produtos, name='tela_estoque_produtos'),
    path('salvar_produto/', views.salvar_produto, name='salvar_produto'),
    path('entrada_carga/', views.tela_entrada_carga, name='tela_entrada_carga'),
    path('api/produto_por_codigo/', views.api_produto_por_codigo, name='api_produto_por_codigo'),
    path('api/efetivar_entrada/', views.api_efetivar_entrada, name='api_efetivar_entrada'),

    # RH e Relatórios
    path('relatorios/', views.tela_relatorios, name='tela_relatorios'),
    path('colaboradores/', views.tela_colaboradores, name='tela_colaboradores'),
    path('salvar_colaborador/', views.salvar_colaborador, name='salvar_colaborador'),

    # Gerência (Marcas, Famílias e Regras de Fidelidade)
    path('gerencia-auxiliares/', views.tela_gerencia_auxiliares, name='tela_gerencia_auxiliares'),
    path('salvar-marca/', views.salvar_marca, name='salvar_marca'),
    path('salvar-familia/', views.salvar_familia, name='salvar_familia'),
    path('gerencia/manutencao-pontos/', views.tela_manutencao_pontos, name='tela_manutencao_pontos'),  # NOVA TELA ISOLADA
    path('gerencia/salvar-configuracao-pontos/', views.salvar_configuracao_pontos, name='salvar_configuracao_pontos'),  # SALVAR REGRA
]