from django.contrib import admin
from django.urls import path
from inventario.views import ponto

# ==========================================
# IMPORTAÇÃO DOS MÓDULOS DE VISUALIZAÇÃO (VIEWS)
# Organização estrutural em blocos de contexto da JB Tintas
# ==========================================
from inventario.views import (
    auth, core, estoque, pdv, clientes, auxiliares, 
    relatorios, equipe, gerencia, tintometrico_v, ponto, fidelidade, pedidos
)

from inventario.views.tintometrico_v import (
    tela_tintometrico, 
    tela_painel_tintometrico,
    api_buscar_cores, 
    consultar_dados_embalagem,
    cadastrar_tintometrico,
    api_buscar_detalhes_base,
    api_pesquisar_base_alternativa
)

# 🌟 CORREÇÃO 3: Importações para servir ficheiros estáticos localmente
from django.conf import settings
from django.conf.urls.static import static

# ==========================================
# DEFINIÇÃO DE ROTAS DO SISTEMA (URLPATTERNS)
# Mapeamento de endpoints para telas e APIs do ERP
# ==========================================
urlpatterns = [
    # Painel de Administração Nativo do Django
    path('admin/', admin.site.urls),

    # 🔐 MÓDULO DE AUTENTICAÇÃO E SESSÃO
    path('', auth.tela_login, name='login'),
    path('logout/', auth.logout, name='logout'),

    # 📊 DASHBOARD PRINCIPAL
    path('painel/', core.painel_principal, name='painel_principal'),

    # 🛒 FRENTE DE CAIXA (PDV OPERACIONAL)
    path('pdv/', pdv.tela_pdv, name='tela_pdv'),
    path('api/consultar-pontos/', pdv.api_consultar_pontos, name='api_consultar_pontos'),
    path('api/salvar-venda/', pdv.api_salvar_venda, name='api_salvar_venda'),
    path('api/buscar-produtos/', pdv.api_buscar_produtos, name='api_buscar_produtos'),
    
    # 🚀 NOVA ROTA: GESTÃO DE RUPTURA (FALTA)
    path('api/registrar-ruptura/', pdv.api_registrar_ruptura, name='api_registrar_ruptura'),

    # 📦 MÓDULO E CONTROLE DE ESTOQUE
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
    
    # 🛒 ROTAS DO CARRINHO DE PEDIDOS DO GERENTE (RETAGUARDA)
    path('estoquepainel/carrinho-pedido/', estoque.tela_carrinho_pedido, name='tela_carrinho_pedido'),
    path('api/finalizar-carrinho-gerente/', estoque.api_finalizar_carrinho_gerente, name='api_finalizar_carrinho_gerente'),

    # 📋 MÓDULO DE PEDIDOS (RETAGUARDA DO VENDEDOR)
    path('paineldepedidos/', pedidos.tela_painel_pedidos, name='painel_pedidos'),
    path('gerarpedido/', pedidos.gerar_novo_pedido, name='gerar_novo_pedido'),
    path('novopedido/', pedidos.tela_novo_pedido, name='tela_novo_pedido'), # ✨ Adicione esta linha de volta!
    path('novopedido/<int:pedido_id>/', pedidos.tela_novo_pedido, name='tela_novo_pedido_reabrir'),
    path('api/pdv/cancelar-pedido/<int:pedido_id>/', pedidos.api_cancelar_pedido, name='api_cancelar_pedido'),
    path('api/pdv/pedidos-pendentes/', pedidos.api_pedidos_pendentes, name='api_pedidos_pendentes'),
    path('api/pdv/importar-pedido/<int:pedido_id>/', pedidos.api_importar_pedido, name='api_importar_pedido'),
    path('api/pdv/faturar-pedido/<int:pedido_id>/', pedidos.api_faturar_pedido, name='api_faturar_pedido'),
    
    
    # 👥 MÓDULO DE CLIENTES
    path('clientes/', clientes.tela_consultar_clientes, name='tela_consultar_clientes'),
    path('clientes/editar/', clientes.salvar_edicao_cliente, name='salvar_edicao_cliente'),
    path('clientes/excluir/<int:id>/', clientes.excluir_cliente, name='excluir_cliente'),
    path('api/historico-cliente/', clientes.api_historico_cliente, name='api_historico_cliente'),

    # ⚙️ ATRIBUTOS E AUXILIARES DE PRODUTO
    path('gerencia/auxiliares/', auxiliares.tela_marcas, name='tela_gerencia_auxiliares'),
    path('gerencia/marcas/', auxiliares.tela_marcas, name='tela_marcas'),
    path('gerencia/familias/', auxiliares.tela_familias, name='tela_familias'),
    path('gerencia/auxiliares/marca/salvar/', auxiliares.salvar_marca, name='salvar_marca'),
    path('gerencia/auxiliares/marca/excluir/<int:id>/', auxiliares.excluir_marca, name='excluir_marca'),
    path('gerencia/auxiliares/family/salvar/', auxiliares.salvar_familia, name='salvar_familia'),
    path('gerencia/auxiliares/family/excluir/<int:id>/', auxiliares.excluir_familia, name='excluir_familia'),

    # 🏢 PAINEL ADMINISTRATIVO (GERÊNCIA) E SUB-MENUS
    path('gerenciapainel/', gerencia.tela_painel_gerencia, name='tela_painel_gerencia'),
    path('gerenciapainel/centrofiscal/', gerencia.tela_centro_fiscal, name='tela_centro_fiscal'),
    path('gerenciapainel/relatoriospainel/', gerencia.tela_relatorios_painel, name='tela_relatorios_painel'),

    # 📄 RELATÓRIOS E DOCUMENTOS TÉRMICOS
    path('api/relatorio-ponto/pdf/', relatorios.gerar_pdf_ponto, name='gerar_pdf_ponto'),
    path('gerencia/relatorios/', relatorios.tela_relatorios, name='tela_relatorios'),
    path('venda/cupom/<int:id>/', relatorios.imprimir_cupom, name='imprimir_cupom'),
    path('gerencia/vendas/cancelar/', relatorios.cancelar_venda, name='cancelar_venda'),
    path('venda/cupom-a4/<int:id>/', relatorios.imprimir_cupom_a4, name='imprimir_cupom_a4'),
    path('cupom_a4/<int:id>/', relatorios.imprimir_cupom_a4, name='atalho_cupom_a4'),
    path('gerenciapainel/relatoriospainel/relatorioponto/', relatorios.tela_relatorio_ponto, name='tela_relatorio_ponto'),
    path('api/relatorio-ponto/dados/', relatorios.api_dados_ponto, name='api_dados_ponto'),
    
    # 🚀 NOVO: RELATÓRIO DE COMISSÕES
    path('gerenciapainel/relatoriospainel/comissao/', gerencia.relatorio_comissao, name='relatorio_comissao'),
    
    # 👥 GESTÃO DE EQUIPE E PROGRAMA DE FIDELIDADE
    path('gerencia/colaboradores/', equipe.tela_colaboradores, name='tela_colaboradores'),
    path('gerencia/colaboradores/salvar/', equipe.salvar_colaborador, name='salvar_colaborador'),
    path('gerencia/colaboradores/excluir/<int:id>/', equipe.excluir_colaborador, name='excluir_colaborador'),
    path('gerencia/pontos/', fidelidade.tela_manutencao_pontos, name='tela_manutencao_pontos'),
    path('gerencia/pontos/salvar/', fidelidade.salvar_configuracao_pontos, name='salvar_configuracao_pontos'),

    # 🎨 MÓDULO TINTOMÉTRICO INDUSTRIAL
    path('tintometricopainel/', tela_painel_tintometrico, name='painel_tintometrico'),
    path('tintometricopainel/<str:marca>/', tela_tintometrico, name='tela_tintometrico'),
    path('api/buscar-cores/', api_buscar_cores, name='api_buscar_cores'),
    path('consultar-dados-embalagem/', consultar_dados_embalagem, name='consultar_dados_embalagem'),
    path('cadastrar-vinculo/', cadastrar_tintometrico, name='lista_tintometrico'),
    path('api/buscar-detalhes-base/', api_buscar_detalhes_base, name='api_buscar_detalhes_base'),
    path('api/pesquisar-base-alternativa/', api_pesquisar_base_alternativa, name='api_pesquisar_base_alternativa'),

    # =========================================================
    # 🧾 ENGINE FISCAL (INTEGRAÇÃO NOTAAS VIA WEBHOOK/API)
    # =========================================================
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

    path('gerenciapainel/configuracoes/', gerencia.tela_configuracoes_sistema, name='tela_configuracoes_sistema'),
    path('gerenciapainel/configuracoes/salvar/', gerencia.salvar_configuracoes_sistema, name='salvar_configuracoes_sistema'),
    path('estoquepainel/suprir-estoque/', estoque.tela_suprir_estoque, name='tela_suprir_estoque'),

    path('api/auxiliares/', gerencia.api_gerenciar_auxiliares, name='api_gerenciar_auxiliares'),
    path('api/webhook-notaas/', gerencia.api_webhook_notaas, name='webhook_notaas'),

    # ⏱️ PONTO ELETRÔNICO
    path('ponto/', ponto.tela_ponto, name='tela_ponto'),
    path('ponto/registrar/', ponto.registrar_batida, name='registrar_batida'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    