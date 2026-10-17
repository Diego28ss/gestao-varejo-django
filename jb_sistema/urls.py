from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from inventario.views import dev as views_dev

# Módulos de Views Gerais (SEM auth e core!)
from inventario.views import (
    pdv, clientes, auxiliares, 
    relatorios, equipe, gerencia, ponto, fidelidade, pedidos, tintometrico_v,
    dev
)

# 🚀 NOVOS MÓDULOS DE VIEWS DO ESTOQUE
from inventario.views.estoque import (
    estoque_entrada_views, 
    estoque_inventario_views, 
    estoque_catalogo_views,
    estoque_compras_views,
    estoque_operacoes_views
)

# 🚀 NOVOS MÓDULOS DE VIEWS DA FASE 6 (BLOCO 1)
from inventario.views.auth import auth_views
from inventario.views.dashboard import dashboard_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 🚀 FASE 6: AUTENTICAÇÃO E DASHBOARD
    path('', auth_views.tela_login, name='login'),
    path('logout/', auth_views.logout, name='logout'),
    path('painel/', dashboard_views.painel_principal, name='painel_principal'),

    # ==========================================
    # ÁREA DE DESENVOLVEDOR
    # ==========================================
    path('dev/painel/', dev.tela_painel_dev, name='tela_painel_dev'),
    path('dev/loja/salvar/', dev.salvar_loja, name='salvar_loja'),
    path('dev/loja/excluir/<int:loja_id>/', dev.excluir_loja, name='excluir_loja'),

    # PDV e Frente de Caixa
    path('pdv/', pdv.tela_pdv, name='tela_pdv'),
    path('api/consultar-pontos/', pdv.api_consultar_pontos, name='api_consultar_pontos'),
    path('api/salvar-venda/', pdv.api_salvar_venda, name='api_salvar_venda'),
    path('api/buscar-produtos/', pdv.api_buscar_produtos, name='api_buscar_produtos'),
    path('api/registrar-ruptura/', pdv.api_registrar_ruptura, name='api_registrar_ruptura'),
    path('api/situacao-estoque/<int:produto_id>/', pdv.api_consultar_situacao_estoque, name='api_consultar_situacao_estoque'),

    # 🚀 FASE 3: CATÁLOGO DE PRODUTOS E PAINEL
    path('estoquepainel/', estoque_catalogo_views.tela_painel_estoque, name='tela_painel_estoque'),
    path('estoquepainel/estoque/', estoque_catalogo_views.tela_estoque_produtos, name='tela_estoque_produtos'),
    path('estoque/salvar/', estoque_catalogo_views.salvar_produto, name='salvar_produto'),
    path('estoque/excluir/<int:id>/', estoque_catalogo_views.excluir_produto, name='excluir_produto'),
    path('api/produto-por-codigo/', estoque_catalogo_views.api_produto_por_codigo, name='api_produto_por_codigo'),
    
    # 🚀 FASE 1: ENTRADA DE NFe E CARGAS
    path('estoquepainel/entrada-carga/', estoque_entrada_views.tela_entrada_carga, name='tela_entrada_carga'),
    path('api/importar-xml/', estoque_entrada_views.api_importar_xml, name='api_importar_xml'),
    path('api/pesquisar-produto-nfe/', estoque_entrada_views.api_pesquisar_produto_nfe, name='api_pesquisar_produto_nfe'),
    path('api/efetivar-nfe/', estoque_entrada_views.api_efetivar_nfe, name='api_efetivar_nfe'),
    path('api/estornar-nfe/', estoque_entrada_views.api_estornar_nfe, name='api_estornar_nfe'),
    
    # 🚀 FASE 2: INVENTÁRIO ROTATIVO DINÂMICO
    path('estoquepainel/inventario-sessao/', estoque_inventario_views.tela_inventario_dinamico, name='tela_inventario_dinamico'),
    path('estoquepainel/inventario-sessao/novo/', estoque_inventario_views.criar_novo_inventario_dinamico, name='criar_novo_inventario_dinamico'),
    path('estoquepainel/inventario-sessao/<int:sessao_id>/', estoque_inventario_views.tela_contagem_dinamica, name='tela_contagem_dinamica'),
    path('api/inventario/bipar-dinamico/', estoque_inventario_views.api_bipar_item_dinamico, name='api_bipar_item_dinamico'),
    path('api/inventario/revisao-omissos/<int:sessao_id>/', estoque_inventario_views.api_revisao_omissos, name='api_revisao_omissos'),
    path('api/inventario/atualizar-qtd-dinamico/', estoque_inventario_views.api_atualizar_quantidade_dinamico, name='api_atualizar_quantidade_dinamico'),
    path('api/inventario/reduzir-dinamico/', estoque_inventario_views.api_reduzir_item_dinamico, name='api_reduzir_item_dinamico'),
    path('api/inventario/finalizar-dinamico/<int:sessao_id>/', estoque_inventario_views.api_finalizar_inventario_dinamico, name='api_finalizar_inventario_dinamico'),
    path('api/inventario/excluir/<int:sessao_id>/', estoque_inventario_views.api_excluir_inventario, name='api_excluir_inventario'),
    path('estoquepainel/inventario-sessao/relatorio/<int:sessao_id>/', estoque_inventario_views.tela_relatorio_inventario, name='tela_relatorio_inventario'),
    path('estoquepainel/inventario-sessao/pdf/<int:sessao_id>/', estoque_inventario_views.gerar_pdf_inventario, name='gerar_pdf_inventario'),

    # 🚀 FASE 4: COMPRAS, VMD E RUPTURAS
    path('estoquepainel/suprir-estoque/', estoque_compras_views.tela_suprir_estoque, name='tela_suprir_estoque'),
    path('estoquepainel/suprir-estoque/pdf/', estoque_compras_views.gerar_pdf_suprimentos, name='gerar_pdf_suprimentos'),
    path('estoquepainel/carrinho-pedido/', estoque_compras_views.tela_carrinho_pedido, name='tela_carrinho_pedido'),
    path('api/resolver-ruptura/<int:produto_id>/', estoque_compras_views.api_resolver_ruptura, name='api_resolver_ruptura'),
    path('api/registrar-encomenda/<int:produto_id>/', estoque_compras_views.api_registrar_encomenda, name='api_registrar_encomenda'),
    path('api/finalizar-carrinho-gerente/', estoque_compras_views.api_finalizar_carrinho_gerente, name='api_finalizar_carrinho_gerente'),

    # 🚀 FASE 5: OPERAÇÕES (AUDITORIA, ALERTAS E ETIQUETAS)
    path('estoquepainel/auditoria-diaria/', estoque_operacoes_views.tela_auditoria_diaria, name='tela_auditoria_diaria'),
    path('estoquepainel/auditoria-diaria/gerar/', estoque_operacoes_views.gerar_missao_matinal, name='gerar_missao_matinal'),
    path('estoquepainel/alertas-preco/', estoque_operacoes_views.tela_alertas_preco, name='tela_alertas_preco'),
    path('api/inventario/resolver-alerta-preco/<int:alerta_id>/', estoque_operacoes_views.api_resolver_alerta_preco, name='api_resolver_alerta_preco'),
    path('api/resolver-alerta-custo/', estoque_operacoes_views.api_resolver_alerta_custo, name='api_resolver_alerta_custo'), 
    path('estoquepainel/etiquetas/', estoque_operacoes_views.tela_imprimir_etiquetas, name='tela_imprimir_etiquetas'),
    path('api/etiquetas/buscar-produto/', estoque_operacoes_views.api_buscar_produto_etiqueta, name='api_buscar_produto_etiqueta'),
    path('api/etiquetas/gerar-pdf/', estoque_operacoes_views.api_gerar_pdf_etiquetas, name='api_gerar_pdf_etiquetas'),

    # Pedidos (Retaguarda)
    path('paineldepedidos/', pedidos.tela_painel_pedidos, name='painel_pedidos'),
    path('gerarpedido/', pedidos.gerar_novo_pedido, name='gerar_novo_pedido'),
    path('novopedido/', pedidos.tela_novo_pedido, name='tela_novo_pedido'),
    path('novopedido/<int:pedido_id>/', pedidos.tela_novo_pedido, name='tela_novo_pedido_reabrir'),
    path('api/pdv/cancelar-pedido/<int:pedido_id>/', pedidos.api_cancelar_pedido, name='api_cancelar_pedido'),
    path('api/pdv/pedidos-pendentes/', pedidos.api_pedidos_pendentes, name='api_pedidos_pendentes'),
    path('api/pdv/importar-pedido/<int:pedido_id>/', pedidos.api_importar_pedido, name='api_importar_pedido'),
    path('api/pdv/faturar-pedido/<int:pedido_id>/', pedidos.api_faturar_pedido, name='api_faturar_pedido'),
    path('api/pedidos/cancelar/<int:pedido_id>/', pedidos.api_cancelar_pedido, name='api_cancelar_pedido_painel'),
    path('api/pedidos/reabrir/<int:pedido_id>/', pedidos.api_reabrir_pedido, name='api_reabrir_pedido'),
    path('api/pedidos/estornar/<int:pedido_id>/', pedidos.api_estornar_faturamento, name='api_estornar_faturamento'),
    path('venda/ticket-pedido/<int:pedido_id>/', pedidos.imprimir_ticket_pedido, name='imprimir_ticket_pedido'),
    
    # Clientes
    path('clientes/', clientes.tela_consultar_clientes, name='tela_consultar_clientes'),
    path('clientes/editar/', clientes.salvar_edicao_cliente, name='salvar_edicao_cliente'),
    path('clientes/excluir/<int:id>/', clientes.excluir_cliente, name='excluir_cliente'),
    path('api/historico-cliente/', clientes.api_historico_cliente, name='api_historico_cliente'),
    path('api/clientes/<str:cliente_id>/historico/', clientes.api_historico_cliente, name='api_historico_cliente_legado'),
    
    # Auxiliares
    path('gerencia/auxiliares/', auxiliares.tela_marcas, name='tela_gerencia_auxiliares'),
    path('gerencia/marcas/', auxiliares.tela_marcas, name='tela_marcas'),
    path('gerencia/familias/', auxiliares.tela_familias, name='tela_familias'),
    path('gerencia/auxiliares/marca/salvar/', auxiliares.salvar_marca, name='salvar_marca'),
    path('gerencia/auxiliares/marca/excluir/<int:id>/', auxiliares.excluir_marca, name='excluir_marca'),
    path('gerencia/auxiliares/family/salvar/', auxiliares.salvar_familia, name='salvar_familia'),
    path('gerencia/auxiliares/family/excluir/<int:id>/', auxiliares.excluir_familia, name='excluir_familia'),

    # Gerência e Fiscal
    path('gerenciapainel/', gerencia.tela_painel_gerencia, name='tela_painel_gerencia'),
    path('gerenciapainel/centrofiscal/', gerencia.tela_centro_fiscal, name='tela_centro_fiscal'),
    path('gerenciapainel/relatoriospainel/', gerencia.tela_relatorios_painel, name='tela_relatorios_painel'),
    path('api/relatorio-ponto/pdf/', relatorios.gerar_pdf_ponto, name='gerar_pdf_ponto'),
    path('gerencia/relatorios/', relatorios.tela_relatorios, name='tela_relatorios'),
    path('venda/cupom/<int:id>/', relatorios.imprimir_cupom, name='imprimir_cupom'),
    
    path('venda/cupom-a4/<int:id>/', relatorios.imprimir_cupom_a4, name='imprimir_cupom_a4'),
    path('cupom_a4/<int:id>/', relatorios.imprimir_cupom_a4, name='atalho_cupom_a4'),
    path('gerenciapainel/relatoriospainel/relatorioponto/', relatorios.tela_relatorio_ponto, name='tela_relatorio_ponto'),
    path('api/relatorio-ponto/dados/', relatorios.api_dados_ponto, name='api_dados_ponto'),
    path('gerenciapainel/relatoriospainel/comissao/', gerencia.relatorio_comissao, name='relatorio_comissao'),
    path('gerencia/colaboradores/', equipe.tela_colaboradores, name='tela_colaboradores'),
    path('gerencia/colaboradores/salvar/', equipe.salvar_colaborador, name='salvar_colaborador'),
    path('gerencia/colaboradores/excluir/<int:id>/', equipe.excluir_colaborador, name='excluir_colaborador'),
    path('gerencia/pontos/', fidelidade.tela_manutencao_pontos, name='tela_manutencao_pontos'),
    path('gerencia/pontos/salvar/', fidelidade.salvar_configuracao_pontos, name='salvar_configuracao_pontos'),

    # Tintométrico
    path('tintometricopainel/', tintometrico_v.tela_painel_tintometrico, name='painel_tintometrico'),
    path('tintometricopainel/<str:marca>/', tintometrico_v.tela_tintometrico, name='tela_tintometrico'),
    path('api/buscar-cores/', tintometrico_v.api_buscar_cores, name='api_buscar_cores'),
    path('consultar-dados-embalagem/', tintometrico_v.consultar_dados_embalagem, name='consultar_dados_embalagem'),
    path('cadastrar-vinculo/', tintometrico_v.cadastrar_tintometrico, name='lista_tintometrico'),
    path('api/buscar-detalhes-base/', tintometrico_v.api_buscar_detalhes_base, name='api_buscar_detalhes_base'),
    path('api/pesquisar-base-alternativa/', tintometrico_v.api_pesquisar_base_alternativa, name='api_pesquisar_base_alternativa'),

    # Motor Fiscal e Integrações
    path('gerenciapainel/emitirnota/', gerencia.emitir_notas, name='emitir_notas'),
    path('gerenciapainel/consultanfe/', gerencia.tela_consulta_nfe, name='tela_consulta_nfe'),
    path('gerenciapainel/consultanfce/', gerencia.tela_consulta_nfce, name='tela_consulta_nfce'), 
    path('gerenciapainel/devolucoes/', gerencia.tela_devolucoes, name='tela_devolucoes'),
    path('api/fiscal/acionar-emissao/', gerencia.api_acionar_emissao, name='api_acionar_emissao'),
    path('api/fiscal/detalhes-venda/', gerencia.api_detalhes_venda, name='api_detalhes_venda'),
    path('api/fiscal/buscar-cliente/', gerencia.api_buscar_cliente, name='api_buscar_cliente'),
    path('api/fiscal/consultar-status/', gerencia.api_fiscal_consultar_status if hasattr(gerencia, 'api_fiscal_consultar_status') else gerencia.api_consultar_status_nfe, name='api_consultar_status_nfe'),
    path('api/fiscal/cancelar-nota/', gerencia.api_cancelar_nota, name='api_cancelar_nota'),
    path('api/fiscal/imprimir-danfe/<int:venda_id>/', gerencia.imprimir_danfe_nfe, name='imprimir_danfe_nfe'),
    path('api/fiscal/baixar-xml/<int:venda_id>/', gerencia.baixar_xml_nfe, name='baixar_xml_nfe'),
    path('api/fiscal/enviar-email-nota/', gerencia.api_enviar_email_nota, name='api_enviar_email_nota'),
    path('api/fiscal/emitir-devolucao/', gerencia.api_emitir_devolucao, name='api_emitir_devolucao'),
    path('api/fiscal/exportar-xmls/', gerencia.api_exportar_xmls, name='api_exportar_xmls'),
    
    # 🚀 NOVAS ROTAS DO DASHBOARD DE CONFIGURAÇÕES ERP
    path('gerenciapainel/configuracoes/', gerencia.tela_configuracoes_sistema, name='tela_configuracoes_sistema'),
    path('gerenciapainel/configuracoes/salvar/', gerencia.salvar_configuracoes_sistema, name='salvar_configuracoes_sistema'),
    path('gerenciapainel/configuracoes/loja/', gerencia.config_loja, name='config_loja'),
    path('gerenciapainel/configuracoes/fidelidade/', gerencia.config_fidelidade, name='config_fidelidade'),
    path('gerenciapainel/configuracoes/estoque/', gerencia.config_estoque, name='config_estoque'),
    path('gerenciapainel/configuracoes/auxiliares/', gerencia.config_auxiliares, name='config_auxiliares'),
    path('gerenciapainel/configuracoes/fiscal/', gerencia.config_fiscal, name='config_fiscal'),

    path('dev/painel/salvar-ambientes/', views_dev.salvar_ambientes_dev, name='salvar_ambientes_dev'),
    path('api/auxiliares/', gerencia.api_gerenciar_auxiliares, name='api_gerenciar_auxiliares'),
    path('api/webhook-notaas/', gerencia.api_webhook_notaas, name='webhook_notaas'),

    # Ponto Eletrônico
    path('ponto/', ponto.tela_ponto, name='tela_ponto'),
    path('ponto/registrar/', ponto.registrar_batida, name='registrar_batida'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    