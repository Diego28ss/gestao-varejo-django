from django.contrib import admin
from django.urls import path

# ==========================================
# IMPORTAÇÃO DOS MÓDULOS DE VISUALIZAÇÃO (VIEWS)
# Organização estrutural em blocos de contexto da JB Tintas
# ==========================================
from inventario.views import (
    auth, core, pdv, estoque, clientes, 
    auxiliares, relatorios, equipe, fidelidade, gerencia
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

# ==========================================
# DEFINIÇÃO DE ROTAS DO SISTEMA (URLPATTERNS)
# Mapeamento de endpoints para telas e APIs do ERP
# ==========================================
urlpatterns = [
    # Painel de Administração Nativo do Django
    path('admin/', admin.site.urls),

    # 🔐 MÓDULO DE AUTENTICAÇÃO E SESSÃO
    # Fluxo de controle de acesso de colaboradores e gerentes
    path('', auth.tela_login, name='login'),
    path('logout/', auth.logout, name='logout'),

    # 📊 DASHBOARD PRINCIPAL
    # Tela central de indicadores de desempenho comercial
    path('painel/', core.painel_principal, name='painel_principal'),

    # 🛒 FRENTE DE CAIXA (PDV OPERACIONAL)
    # Roteamento de checkout rápido e consultas do terminal de vendas
    path('pdv/', pdv.tela_pdv, name='tela_pdv'),
    path('api/consultar-pontos/', pdv.api_consultar_pontos, name='api_consultar_pontos'),
    path('api/salvar-venda/', pdv.api_salvar_venda, name='api_salvar_venda'),
    path('api/buscar-produtos/', pdv.api_buscar_produtos, name='api_buscar_produtos'),

    # 📦 MÓDULO E CONTROLE DE ESTOQUE
    # Gestão física de saldos, entradas por carga e manutenção de produtos
    path('estoquepainel/', estoque.tela_painel_estoque, name='tela_painel_estoque'),
    path('estoquepainel/estoque/', estoque.tela_estoque_produtos, name='tela_estoque_produtos'),
    path('estoquepainel/entrada-carga/', estoque.tela_entrada_carga, name='tela_entrada_carga'),
    path('estoque/salvar/', estoque.salvar_produto, name='salvar_produto'),
    path('estoque/excluir/<int:id>/', estoque.excluir_produto, name='excluir_produto'),
    path('api/produto-por-codigo/', estoque.api_produto_por_codigo, name='api_produto_por_codigo'),
    path('api/efetivar-entrada/', estoque.api_efetivar_entrada, name='api_efetivar_entrada'),

    # 👥 MÓDULO DE CLIENTES
    # Fichas cadastrais unificadas, histórico de compras e controle de CEP/Número
    path('clientes/', clientes.tela_consultar_clientes, name='tela_consultar_clientes'),
    path('clientes/editar/', clientes.salvar_edicao_cliente, name='salvar_edicao_cliente'),
    path('clientes/excluir/<int:id>/', clientes.excluir_cliente, name='excluir_cliente'),
    path('api/historico-cliente/', clientes.api_historico_cliente, name='api_historico_cliente'),

    # ⚙️ ATRIBUTOS E AUXILIARES DE PRODUTO
    # Configuração de tabelas de suporte para Marcas e Famílias de tintas
    path('gerencia/auxiliares/', auxiliares.tela_marcas, name='tela_gerencia_auxiliares'),
    path('gerencia/marcas/', auxiliares.tela_marcas, name='tela_marcas'),
    path('gerencia/familias/', auxiliares.tela_familias, name='tela_familias'),
    path('gerencia/auxiliares/marca/salvar/', auxiliares.salvar_marca, name='salvar_marca'),
    path('gerencia/auxiliares/marca/excluir/<int:id>/', auxiliares.excluir_marca, name='excluir_marca'),
    path('gerencia/auxiliares/family/salvar/', auxiliares.salvar_familia, name='salvar_familia'),
    path('gerencia/auxiliares/family/excluir/<int:id>/', auxiliares.excluir_familia, name='excluir_familia'),

    # 🏢 PAINEL ADMINISTRATIVO (GERÊNCIA)
    # Centralizador de controle e auditorias fiscais do estabelecimento
    path('gerenciapainel/', gerencia.tela_painel_gerencia, name='tela_painel_gerencia'),

    # 📄 RELATÓRIOS E DOCUMENTOS TÉRMICOS
    # Emissão de vias de conferência e gerenciamento de cancelamentos internos
    path('gerencia/relatorios/', relatorios.tela_relatorios, name='tela_relatorios'),
    path('venda/cupom/<int:id>/', relatorios.imprimir_cupom, name='imprimir_cupom'),
    path('gerencia/vendas/cancelar/', relatorios.cancelar_venda, name='cancelar_venda'),
    path('venda/cupom-a4/<int:id>/', relatorios.imprimir_cupom_a4, name='imprimir_cupom_a4'),
    path('cupom_a4/<int:id>/', relatorios.imprimir_cupom_a4, name='atalho_cupom_a4'),

    # 👥 GESTÃO DE EQUIPE E PROGRAMA DE FIDELIDADE
    # Configuração de comissões, perfis de colaboradores e cálculo de pontos com divisor 25
    path('gerencia/colaboradores/', equipe.tela_colaboradores, name='tela_colaboradores'),
    path('gerencia/colaboradores/salvar/', equipe.salvar_colaborador, name='salvar_colaborador'),
    path('gerencia/colaboradores/excluir/<int:id>/', equipe.excluir_colaborador, name='excluir_colaborador'),
    path('gerencia/pontos/', fidelidade.tela_manutencao_pontos, name='tela_manutencao_pontos'),
    path('gerencia/pontos/salvar/', fidelidade.salvar_configuracao_pontos, name='salvar_configuracao_pontos'),

          
    # 🎨 MÓDULO TINTOMÉTRICO INDUSTRIAL
    # Integração de catálogos de cores, fórmulas de pigmentação e vinculo com a máquina de tintas
    path('tintometricopainel/', tela_painel_tintometrico, name='painel_tintometrico'),
    path('tintometricopainel/<str:marca>/', tela_tintometrico, name='tela_tintometrico'),
    path('api/buscar-cores/', api_buscar_cores, name='api_buscar_cores'),
    path('consultar-dados-embalagem/', consultar_dados_embalagem, name='consultar_dados_embalagem'),
    path('cadastrar-vinculo/', cadastrar_tintometrico, name='lista_tintometrico'),
    path('api/buscar-detalhes-base/', api_buscar_detalhes_base, name='api_buscar_detalhes_base'),
    path('api/pesquisar-base-alternativa/', api_pesquisar_base_alternativa, name='api_pesquisar_base_alternativa'),

    # =========================================================
    # 🧾 ENGINE FISCAL (INTEGRAÇÃO FOCUS NFE VIA WEBHOOK/API)
    # Processamento, auditoria e logística reversa de documentos eletrónicos
    # =========================================================
    # Monitorização da Fila de Trabalho para emissões manuais pendentes
    path('gerenciapainel/emitirnota/', gerencia.emitir_notas, name='emitir_notas'),
    
    # Gestão Avançada de Notas Fiscais Grandes (Modelo 55 - Saídas)
    path('gerenciapainel/consultanfe/', gerencia.tela_consulta_nfe, name='tela_consulta_nfe'),
    
    # Gestão de Cupons Fiscais Eletrónicos do Consumidor (Modelo 65 - Balcão)
    path('gerenciapainel/consultanfce/', gerencia.tela_consulta_nfce, name='tela_consulta_nfce'), 
    
    # 🔄 NOVA ROTA: ARQUIVO HISTÓRICO DE NOTAS DE DEVOLUÇÃO (FASE 3)
    # Tela centralizadora para auditoria legal de notas de entrada (finalidade 4) e guarda de DANFEs
    path('gerenciapainel/devolucoes/', gerencia.tela_devolucoes, name='tela_devolucoes'),
    
    # Gateways de comunicação asíncrona com os servidores da Focus NFe e SEFAZ
    path('api/fiscal/acionar-emissao/', gerencia.api_acionar_emissao, name='api_acionar_emissao'),
    path('api/fiscal/detalhes-venda/', gerencia.api_detalhes_venda, name='api_detalhes_venda'),
    path('api/fiscal/buscar-cliente/', gerencia.api_buscar_cliente, name='api_buscar_cliente'),
    path('api/fiscal/consultar-status/', gerencia.api_consultar_status_nfe, name='api_consultar_status_nfe'),
    path('api/fiscal/cancelar-nota/', gerencia.api_cancelar_nota, name='api_cancelar_nota'),
    path('api/fiscal/imprimir-danfe/<int:venda_id>/', gerencia.imprimir_danfe_nfe, name='imprimir_danfe_nfe'),
    path('api/fiscal/baixar-xml/<int:venda_id>/', gerencia.baixar_xml_nfe, name='baixar_xml_nfe'),
    path('api/fiscal/enviar-email-nota/', gerencia.api_enviar_email_nota, name='api_enviar_email_nota'),
    path('api/fiscal/emitir-devolucao/', gerencia.api_emitir_devolucao, name='api_emitir_devolucao'),
]
