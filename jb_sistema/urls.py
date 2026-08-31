from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

# Módulos de Views
from inventario.views import (
    auth, core, estoque, pdv, clientes, auxiliares, 
    relatorios, equipe, gerencia, ponto, fidelidade, pedidos, tintometrico_v
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', auth.tela_login, name='login'),
    path('logout/', auth.logout, name='logout'),
    path('painel/', core.painel_principal, name='painel_principal'),

    # PDV e Frente de Caixa
    path('pdv/', pdv.tela_pdv, name='tela_pdv'),
    path('api/consultar-pontos/', pdv.api_consultar_pontos, name='api_consultar_pontos'),
    path('api/salvar-venda/', pdv.api_salvar_venda, name='api_salvar_venda'),
    path('api/buscar-produtos/', pdv.api_buscar_produtos, name='api_buscar_produtos'),
    path('api/registrar-ruptura/', pdv.api_registrar_ruptura, name='api_registrar_ruptura'),

    # Controle de Estoque
    path('api/pesquisar-produto-nfe/', estoque.api_pesquisar_produto_nfe, name='api_pesquisar_produto_nfe'),
    path('estoquepainel/', estoque.tela_painel_estoque, name='tela_painel_estoque'),
    path('estoquepainel/estoque/', estoque.tela_estoque_produtos, name='tela_estoque_produtos'),
    path('estoquepainel/entrada-carga/', estoque.tela_entrada_carga, name='tela_entrada_carga'),
    path('estoque/salvar/', estoque.salvar_produto, name='salvar_produto'),
    path('estoque/excluir/<int:id>/', estoque.excluir_produto, name='excluir_produto'),
    path('api/produto-por-codigo/', estoque.api_produto_por_codigo, name='api_produto_por_codigo'),
    path('api/importar-xml/', estoque.api_importar_xml, name='api_importar_xml'),
    path('api/efetivar-entrada/', estoque.api_efetivar_entrada, name='api_efetivar_entrada'),
    path('api/efetivar-nfe/', estoque.api_efetivar_nfe, name='api_efetivar_nfe'),
    path('api/resolver-ruptura/<int:produto_id>/', estoque.api_resolver_ruptura, name='api_resolver_ruptura'),
    path('api/registrar-encomenda/<int:produto_id>/', estoque.api_registrar_encomenda, name='api_registrar_encomenda'),
    path('api/situacao-estoque/<int:produto_id>/', pdv.api_consultar_situacao_estoque, name='api_consultar_situacao_estoque'),
    
    path('estoquepainel/carrinho-pedido/', estoque.tela_carrinho_pedido, name='tela_carrinho_pedido'),
    path('api/finalizar-carrinho-gerente/', estoque.api_finalizar_carrinho_gerente, name='api_finalizar_carrinho_gerente'),

    # 🚀 ROTAS DE INVENTÁRIO ROTATIVO E CONTAGEM (WMS)
    path('estoquepainel/inventario-sessao/', estoque.tela_inventario_sessao, name='tela_inventario_sessao'),
    path('estoquepainel/inventario-sessao/novo/', estoque.criar_novo_inventario, name='criar_novo_inventario'),
    path('estoquepainel/inventario-sessao/<int:sessao_id>/', estoque.tela_contagem_inventario, name='tela_contagem_inventario'),
    path('api/inventario/bipar/', estoque.api_bipar_item_inventario, name='api_bipar_item_inventario'),
    path('api/inventario/finalizar/<int:sessao_id>/', estoque.api_finalizar_inventario, name='api_finalizar_inventario'),
    
    # 🚀 TRATAMENTO DE ALERTAS (INTRUSOS) E AÇÕES EM MASSA
    path('api/inventario/autorizar/<int:item_id>/', estoque.api_autorizar_intruso, name='api_autorizar_intruso'),
    path('api/inventario/remover/<int:item_id>/', estoque.api_remover_item, name='api_remover_item'),
    path('api/inventario/autorizar-todos/<int:sessao_id>/', estoque.api_autorizar_todos_intrusos, name='api_autorizar_todos_intrusos'),
    path('api/inventario/excluir/<int:sessao_id>/', estoque.api_excluir_inventario, name='api_excluir_inventario'),
    
    # 🚀 RELATÓRIOS DO INVENTÁRIO (WMS)
    path('estoquepainel/inventario-sessao/relatorio/<int:sessao_id>/', estoque.tela_relatorio_inventario, name='tela_relatorio_inventario'),
    path('estoquepainel/inventario-sessao/pdf/<int:sessao_id>/', estoque.gerar_pdf_inventario, name='gerar_pdf_inventario'),

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
    path('gerencia/vendas/cancelar/', relatorios.cancelar_venda, name='cancelar_venda'),
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
    path('api/fiscal/consultar-status/', gerencia.api_consultar_status_nfe, name='api_consultar_status_nfe'),
    path('api/fiscal/cancelar-nota/', gerencia.api_cancelar_nota, name='api_cancelar_nota'),
    path('api/fiscal/imprimir-danfe/<int:venda_id>/', gerencia.imprimir_danfe_nfe, name='imprimir_danfe_nfe'),
    path('api/fiscal/baixar-xml/<int:venda_id>/', gerencia.baixar_xml_nfe, name='baixar_xml_nfe'),
    path('api/fiscal/enviar-email-nota/', gerencia.api_enviar_email_nota, name='api_enviar_email_nota'),
    path('api/fiscal/emitir-devolucao/', gerencia.api_emitir_devolucao, name='api_emitir_devolucao'),
    path('api/fiscal/exportar-xmls/', gerencia.api_exportar_xmls, name='api_exportar_xmls'),
    path('gerenciapainel/configuracoes/', gerencia.tela_configuracoes_sistema, name='tela_configuracoes_sistema'),
    path('gerenciapainel/configuracoes/salvar/', gerencia.salvar_configuracoes_sistema, name='salvar_configuracoes_sistema'),
    
    path('estoquepainel/suprir-estoque/pdf/', estoque.gerar_pdf_suprimentos, name='gerar_pdf_suprimentos'),
    path('estoquepainel/suprir-estoque/', estoque.tela_suprir_estoque, name='tela_suprir_estoque'),
    
    path('api/auxiliares/', gerencia.api_gerenciar_auxiliares, name='api_gerenciar_auxiliares'),
    path('api/webhook-notaas/', gerencia.api_webhook_notaas, name='webhook_notaas'),

    # Ponto Eletrônico
    path('ponto/', ponto.tela_ponto, name='tela_ponto'),
    path('ponto/registrar/', ponto.registrar_batida, name='registrar_batida'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    