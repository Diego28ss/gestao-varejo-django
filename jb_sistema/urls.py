from django.contrib import admin
from django.urls import path
from inventario import views

urlpatterns = [
    # Admin do Django
    path('admin/', admin.site.urls),

    # 🔐 Autenticação
    path('', views.tela_login, name='login'),
    path('logout/', views.logout, name='logout'),

    # 📊 Painel Principal
    path('painel/', views.painel_principal, name='painel_principal'),

    # 🛒 Frente de Caixa (PDV) e APIs de Venda
    path('pdv/', views.tela_pdv, name='tela_pdv'),
    path('api/consultar-pontos/', views.api_consultar_pontos, name='api_consultar_pontos'),
    path('api/salvar-venda/', views.api_salvar_venda, name='api_salvar_venda'),
    path('api/buscar-produtos/', views.api_buscar_produtos, name='api_buscar_produtos'),

    # 📦 Controle de Estoque
    path('estoque/', views.tela_estoque_produtos, name='tela_estoque_produtos'),
    path('estoque/salvar/', views.salvar_produto, name='salvar_produto'),
    path('estoque/excluir/<int:id>/', views.excluir_produto, name='excluir_produto'),
    path('entrada-carga/', views.tela_entrada_carga, name='tela_entrada_carga'),
    path('api/produto-por-codigo/', views.api_produto_por_codigo, name='api_produto_por_codigo'),
    path('api/efetivar-entrada/', views.api_efetivar_entrada, name='api_efetivar_entrada'),

    # 👥 Clientes
    path('clientes/', views.tela_consultar_clientes, name='tela_consultar_clientes'),
    path('clientes/editar/', views.salvar_edicao_cliente, name='salvar_edicao_cliente'),

    # --- A LINHA NOVA ENTRA AQUI ---
    path('clientes/excluir/<int:id>/', views.excluir_cliente, name='excluir_cliente'),

    path('api/historico-cliente/', views.api_historico_cliente, name='api_historico_cliente'),

    # ⚙️ Gerência de Auxiliares
    path('gerencia/auxiliares/', views.tela_marcas, name='tela_gerencia_auxiliares'),
    path('gerencia/marcas/', views.tela_marcas, name='tela_marcas'),
    path('gerencia/familias/', views.tela_familias, name='tela_familias'),
    path('gerencia/auxiliares/marca/salvar/', views.salvar_marca, name='salvar_marca'),
    path('gerencia/auxiliares/marca/excluir/<int:id>/', views.excluir_marca, name='excluir_marca'),
    path('gerencia/auxiliares/familia/salvar/', views.salvar_familia, name='salvar_familia'),
    path('gerencia/auxiliares/familia/excluir/<int:id>/', views.excluir_familia, name='excluir_familia'),

    # 📄 Relatórios e Impressão
    path('gerencia/relatorios/', views.tela_relatorios, name='tela_relatorios'),
    path('venda/cupom/<int:id>/', views.imprimir_cupom, name='imprimir_cupom'),
    path('gerencia/vendas/cancelar/', views.cancelar_venda, name='cancelar_venda'),
    path('venda/cupom-a4/<int:id>/', views.imprimir_cupom_a4, name='imprimir_cupom_a4'), # <-- VÍRGULA ADICIONADA AQUI

    # 🔄 ROTAS DE COMPATIBILIDADE (Fallbacks e Soluções de Cache)
    path('cupom/<int:id>/', views.imprimir_cupom),
    path('cupom_a4/<int:id>/', views.imprimir_cupom_a4),

    # --- AQUI ESTÁ A MAGIA QUE RESOLVE O SEU PROBLEMA ---
    # Aceitamos os pedidos com underline para enganar o cache do navegador!
    path('api/produto_por_codigo/', views.api_produto_por_codigo),
    path('api/efetivar_entrada/', views.api_efetivar_entrada),

    path('gerencia/colaboradores/', views.tela_colaboradores, name='tela_colaboradores'),
    path('gerencia/colaboradores/salvar/', views.salvar_colaborador, name='salvar_colaborador'),
    path('gerencia/colaboradores/excluir/<int:id>/', views.excluir_colaborador, name='excluir_colaborador'),
    path('gerencia/pontos/', views.tela_manutencao_pontos, name='tela_manutencao_pontos'),
    path('gerencia/pontos/salvar/', views.salvar_configuracao_pontos, name='salvar_configuracao_pontos'),
]
