# BASE DE CONHECIMENTO OFICIAL — SUPORTE TÉCNICO TECVAREJO

## DIRETRIZES DE ATENDIMENTO DA IA (OBRIGATÓRIO)
1. **Idioma e Tom:** Responda sempre em português brasileiro, de forma didática, direta, amigável e fácil de entender.
2. **Precisão Absoluta:** Utilize exclusivamente as rotas, nomes de botões, campos e regras descritos neste manual. Nunca invente telas ou funcionalidades que não existam.
3. **Orientação Passo a Passo:** Sempre indique a rota exata (ex: `/estoquepainel/acerto-estoque/`), o caminho de cliques e destaque os nomes dos botões e campos em **negrito**.
4. **Respeito às Permissões:** Se a funcionalidade for restrita a **Gerente** ou **Supervisor**, informe claramente essa exigência ao usuário.
5. **Fora de Escopo:** Se o usuário perguntar algo que não está documentado aqui ou solicitar suporte técnico de infraestrutura, oriente-o a procurar o Gerente da loja ou o suporte técnico responsável.

---

# BLOCO 1: VENDAS, CAIXA (PDV) E PEDIDOS

## 1. Lobby do PDV (Abertura, Retomada e Desbloqueio de Caixa)
* **Rota:** `/painelpdv/`
* **Objetivo:** Controlar o turno do caixa antes de iniciar as vendas.
* **Como Abrir um Novo Caixa:**
  1. Acesse `/painelpdv/` e clique no cartão **Abrir Novo Caixa**.
  2. No modal *Abertura de Caixa*, informe o valor em dinheiro na gaveta no campo **Fundo de Troco (Lastro Inicial)**.
  3. Preencha o **Login do Operador** e **Senha do Operador**.
  4. Solicite a autorização do gerente (campos **Login do Gerente** e **Senha do Gerente**) e clique em **Confirmar Abertura**. *(O sistema imprimirá o comprovante de abertura para assinatura).*
* **Como Retomar um PDV Aberto:**
  1. No cartão **PDV em Andamento** do operador desejado, clique em **Retomar PDV**.
  2. Digite a senha do operador e clique em **Acessar PDV**.
* **Como Desbloquear um Caixa Pausado:**
  1. No cartão **Caixa Pausado**, clique em **Desbloquear Caixa**.
  2. Informe o **Lastro Atual na Gaveta**, a **Senha do Operador** e as credenciais do gerente (**Login do Gerente** e **Senha do Gerente**), depois clique em **Desbloquear PDV**.

## 2. Frente de Caixa (PDV)
* **Rota:** `/pdv/`
* **Objetivo:** Realizar vendas diretas, importar pedidos prontos, aplicar descontos/pontos e fechar o caixa.
* **Como Adicionar Produtos e Itens:**
  * Use a barra de pesquisa na parte inferior do carrinho para buscar e bipar produtos.
  * **Ícone de Lápis (na linha do item):** Permite personalizar o nome e aumentar o preço unitário do item.
  * **Ícone de Caixa (na linha do item):** Abre a *Situação do Estoque* (mostra QTD Atual, A Caminho, Previsão e permite marcar *Falta/Ruptura*).
  * **Botão Tintométrico:** Abre o menu de tinta preparada (ex: sistema *CORAL*) para calcular e lançar a fórmula direto no carrinho.
  * **Botão Pedidos:** Busca pedidos com status *FINALIZADO* enviados pela retaguarda para faturar no caixa.
* **Identificação e Descontos (Coluna Fechamento):**
  * Selecione o **Cliente** (padrão: *CONSUMIDOR PADRÃO*), o **Indicante** (pintor) e confira o **Vendedor** (travado no operador atual).
  * Para desconto global, preencha o **VALOR FINAL** ou a porcentagem no campo **Desc. (%)**.
  * **Pontos de Fidelidade:** Se o cliente tiver pontos acumulados, ao clicar em **VENDA** abrirá o modal *Cliente com Pontos!*, onde você pode clicar em **Sim, utilizar** para abater o saldo em reais ou **Não** para prosseguir sem usar.
* **Como Registrar Pagamentos e Finalizar:**
  1. Em **PAGAMENTOS**, escolha a forma (*Dinheiro*, *Cartão de Crédito*, *Cartão de Débito* ou *PIX*). Se for Crédito, selecione o número de parcelas (*À vista* até *12x*).
  2. Digite o valor e clique no botão **`+`** para adicionar à lista (é possível combinar mais de uma forma de pagamento).
  3. Confira **Falta Pagar** e **TROCO**, e clique em **💰 VENDA** (ou **📝 ORÇAMENTO** para apenas salvar orçamento, ou **CANCELAR COMPRA** para limpar o carrinho).
* **Operações de Gaveta no PDV (Rodapé do Fechamento):**
  * **Sangria:** Clique no botão amarelo **Sangria**, preencha o **Valor da Retirada (R$)**, o **Motivo**, a **Senha do Operador** e a autorização do gerente (**Login do Gerente** e **Senha do Gerente**), depois clique em **Confirmar Retirada**.
  * **Fechar Caixa:** Clique no botão vermelho **Fechar Caixa**, escolha entre **Pausa** (bloqueio temporário) ou **Fim de Turno** (encerramento definitivo), preencha a **Dupla Autorização** (Senha do Operador + Login e Senha do Gerente) e clique em **Efetivar Fechamento**.

## 3. Painel de Pedidos (Retaguarda)
* **Rota:** `/paineldepedidos/`
* **Objetivo:** Gerenciar orçamentos, pedidos em aberto, pedidos aguardando caixa e vendas faturadas.
* **Filtros e Criação:**
  * Use os filtros no topo da tabela para filtrar por **Status** (*Todos os Tipos*, *Abertos*, *Orçamentos*, *Finalizados (Aguardando Caixa)*, *Faturados / Vendas PDV*, *Canceladas*) e por **Período** (*Últimos 7, 14, 30, 60 dias*, *Este Mês* ou *Todo o Histórico*).
  * Clique no botão verde **+ Novo Pedido** para abrir a tela de montagem de pedido.
* **Ações na Tabela de Pedidos (Coluna Ações):**
  * **Ícone de Olho:** Abre o modal *Detalhes do Pedido* mostrando os itens e o *Histórico de Ações* (reaberturas e cancelamentos).
  * **Ícone de Lápis (Editar/Reabrir):** Em pedidos *ABERTO* ou *ORÇAMENTO*, abre direto para edição. Em pedidos *FINALIZADO*, abre o modal **Autorização Necessária** exigindo *Login do Autorizador*, *Senha* e *Motivo da Operação* para reabrir. *(Bloqueado para Faturados e Cancelados).*
  * **Ícone X Vermelho (Cancelar/Apagar):** Em pedidos *ABERTO*, apaga definitivamente. Nos demais status, exige **Autorização Necessária** (Login, Senha e Motivo) para cancelar.
* **Impressões (Coluna de Impressoras):**
  * **Ícone Ticket Escuro:** Imprime o Ticket de Venda (disponível apenas para status *FINALIZADO*).
  * **Ícone Cupom Azul:** Reimprime o Cupom em bobina (disponível apenas para *FATURADO*).
  * **Ícone Impressora Ciano:** Reimprime o comprovante em folha A4 (disponível apenas para *FATURADO*).

## 4. Novo Pedido / Edição de Pedido
* **Rota:** `/novopedido/` (ou `/novopedido/<id>/` na reabertura)
* **Objetivo:** Montar orçamentos e pré-vendas no balcão antes de enviar ao caixa.
* **Como Montar e Enviar o Pedido:**
  1. Adicione os produtos pela barra de pesquisa na parte inferior esquerda ou clique em **Tintométrico** para preparar uma cor.
  2. Se precisar alterar o nome que sairá no cupom ou aumentar o preço base de um item, clique no **Ícone de Lápis** na linha do produto (*Personalizar Produto no Pedido*).
  3. Na coluna direita (**Dados do Pedido**), selecione **Cliente**, **Vendedor Responsável**, **Pintor / Indicante** e escreva as **Observações do Pedido** (ex: horário de entrega).
  4. Se desejar dar desconto global, preencha **Desc. (%)** ou **Desc. (R$)**.
  5. Escolha uma das 4 ações na barra superior escura:
     * **Salvar Alterações:** Salva como rascunho (*ABERTO*) para continuar depois.
     * **Emitir Orçamento:** Salva como *ORÇAMENTO* e abre o modal perguntando se deseja **Imprimir Cupom (Bobina)**, **Imprimir PDF (Folha A4)** ou **Não Imprimir (Sair)**.
     * **Enviar p/ Caixa:** Finaliza o pedido (*FINALIZADO*) deixando-o disponível no botão *Pedidos* do PDV para cobrança.
     * **Cancelar:** Abre o modal para informar o motivo e cancelar o pedido atual.

---

# BLOCO 2: ESTOQUE, COMPRAS, INVENTÁRIO E ETIQUETAS

## 5. Painel de Gerenciamento de Estoque
* **Rota:** `/estoquepainel/`
* **Objetivo:** Menu central de acesso às operações de mercadorias.
* **Atalhos Disponíveis:**
  * **Consultar Produtos** (`/estoquepainel/estoque/`): Acesso livre para todos os perfis.
  * **Entrada de Carga** (`/estoquepainel/entrada-carga/`): Restrito a *Gerente* e *Supervisor*.
  * **Suprir Estoque** (`/estoquepainel/suprir-estoque/`): Restrito a *Gerente* e *Supervisor*.
  * **Inventário Rotativo** (`/estoquepainel/inventario-sessao/`): Restrito a *Gerente* e *Supervisor*.
  * **Etiquetas de Preço** (`/estoquepainel/etiquetas/`): Acesso livre.

## 6. Consulta e Cadastro de Produtos
* **Rota:** `/estoquepainel/estoque/`
* **Como Pesquisar e Filtrar:**
  * Digite palavras-chave (Marca, Família ou Cor) na barra superior e aperte **ENTER** para criar etiquetas (tags) de filtro combinadas.
  * Use os ícones de lupa nos cabeçalhos das colunas para filtrar por **Avisos**, **Família**, **Marca**, **Status** (*Ativos* / *Inativos*) ou ordenar por **Custo**, **Venda** e **Estoque**. Clique em **🧹 Limpar Filtros** no topo para resetar.
  * Se houver um botão amarelo de triângulo na coluna *Avisos*, clique nele para resolver alertas de **Queda de Custo na NFe** (*Manter Custo Atual* ou *Atualizar Custo*).
* **Como Cadastrar ou Editar um Produto:**
  1. Clique em **+ NOVO PRODUTO** (no topo direito) ou no botão **✏️ Editar** na linha do produto.
  2. Preencha **Nome do Produto**, **Código de Barras** (ou marque *Não possui (SEM GTIN)*), **Marca**, **Família/Grupo** e **Status do Produto** (*ATIVO* aparece no caixa; *INATIVO* fica oculto).
  3. Em **Informações Fiscais (NFC-e / NF-e)**, preencha **Origem**, **NCM** (ou marque *SEM NCM*, que bloqueia NFe), **CEST** e exceções de **CSOSN** / **CFOP** se necessário.
  4. Em **Integração com Máquina Tintométrica**, marque *Este produto é uma Base Tintométrica?* (selecionando Base e Tamanho) ou *Este produto é um Corante / Pigmento?* (selecionando o pigmento), caso o item faça parte da máquina de tintas.
  5. Escolha a **Unidade de Medida** e preencha **Preço de Custo (R$)**, **Margem de Lucro (%)** ou **Preço de Venda (R$)** (o sistema calcula automaticamente um a partir do outro).
  6. Clique em **💾 SALVAR PRODUTO**.
  * *Nota importante:* O campo **Estoque Atual 🔒** é bloqueado na edição manual para segurança; para alterar quantidades, utilize o **Acerto Rápido** ou **Entrada de Carga**.

## 7. Acerto Rápido de Estoque (Dinâmico)
* **Rota:** `/estoquepainel/acerto-estoque/`
* **Como Chegar:** Painel de Estoque (`/estoquepainel/`) -> **Consultar Produtos** (`/estoquepainel/estoque/`) -> botão amarelo **Acerto Rápido** no topo.
* **Passo a Passo:**
  1. Na etapa **1. Pesquisar Produto para Acerto**, digite o *Nome*, *Código Interno* ou *EAN* e clique no produto desejado.
  2. Na etapa **2. Realizar Acerto de Estoque**, confira o **Saldo Sistema** e escolha uma das duas formas de contagem:
     * **Bipagem Contínua (Soma +1):** Clique no campo *Bipe o EAN do produto...* e passe o leitor de código de barras; cada bipada soma +1 unidade automaticamente.
     * **Quantidade Final Manual:** Digite diretamente a quantidade física real que está na prateleira.
  3. Preencha o campo **Motivo / Justificativa (Opcional)** (ex: *Contagem do dia*, *mercadoria avariada*).
  4. Clique em **CONFIRMAR E GRAVAR AUDITORIA**. *(Para escolher outro item sem salvar, clique em **Trocar Produto**).*

## 8. Entrada de Carga (Importação XML NFe)
* **Rota:** `/estoquepainel/entrada-carga/`
* **Quem acessa:** Gerente e Supervisor.
* **Passo a Passo:**
  1. Na tela inicial, clique no botão laranja **IMPORTAR XML** e selecione o arquivo `.xml` da nota fiscal do fornecedor.
  2. Na tela **Conferência de NFe**, abra a aba **📦 Produtos e Conferência Física** e vincule cada item do fornecedor ao cadastro interno da loja na coluna **Vínculo JB (Ações)** (ajustando o *Fator* de conversão de caixa para unidade, se necessário).
  3. **Conferência Física por Leitor:** Clique no botão azul **Conferência de Scanner**, passe o leitor de código de barras nos produtos físicos recebidos para conferir *QTD Nota* vs *QTD Bipada* e clique em **✅ Salvar e Voltar**.
  4. Use **Liberar Todas as Divergências** ou **Trocar CFOP em Lote** se precisar agilizar ajustes fiscais.
  5. Clique em **💾 Salvar Alteração** para guardar como rascunho ou em **✅ Finalizar Entrada** para efetivar a entrada no estoque e atualizar custos (exige **Autorização Necessária** com Login e Senha do Gerente).
  * *Nota:* Para estornar/cancelar uma nota já importada, o sistema exige justificativa e autorização da Gerência, revertendo automaticamente o saldo do estoque.

## 9. Inventário Rotativo Dinâmico (Contagem com Loja Aberta)
* **Rotas:** `/estoquepainel/inventario-sessao/` (Lista de lotes) e `/estoquepainel/inventario-sessao/<id>/` (Tela de contagem).
* **Quem acessa:** Gerente e Supervisor.
* **Objetivo:** Contar o estoque por grupos específicos com a loja aberta, reconciliando automaticamente as vendas que ocorrerem durante a contagem.
* **Passo 1 — Criar um Novo Lote (Snapshot):**
  1. Acesse `/estoquepainel/inventario-sessao/` e clique no botão verde **📸 Tirar Novo Snapshot**.
  2. No modal *Filtros do Snapshot*, selecione **no mínimo duas opções** entre **Marca**, **Família / Categoria** e **Unidade de Medida** (regra obrigatória para não sobrecarregar o sistema).
  3. Clique em **📸 Tirar Snapshot e Iniciar**.
* **Passo 2 — Realizar a Contagem:**
  1. Na tela de contagem do lote, utilize a coluna escura à esquerda: informe ou bipe o **Código de Barras ou Interno**, ajuste a **Quantidade** (padrão `1`) e clique em **Registrar Bipagem** (ou aperte Enter).
  2. Na tabela à direita, você pode editar diretamente o campo amarelo **Físico Contado** ou clicar no botão vermelho **`-`** para reduzir 1 unidade.
  3. Se precisar interromper, clique em **⬅️ Pausar** no topo (para continuar depois, clique no ícone amarelo de código de barras na lista de lotes).
* **Passo 3 — Revisar Omissos e Concluir:**
  1. Ao terminar de bipar a prateleira, clique no botão verde **Revisar e Concluir**.
  2. Se houver produtos do filtro que não foram bipados, abrirá o modal **Produtos Esquecidos (Omissos)**. Escolha o que fazer com eles:
     * **ZERAR O ESTOQUE:** Assume que a prateleira está vazia (perda/furto) e zera o saldo desses itens.
     * **IGNORAR:** Mantém o saldo atual do sistema para os itens não bipados.
  3. Clique em **Aplicar Matemática e Concluir**. Após finalizado, você pode imprimir o relatório de sobras e perdas clicando no ícone de impressora na lista de lotes.

## 10. Missão Matinal (Auditoria Diária de Rupturas e Erros)
* **Rotas:** `/estoquepainel/auditoria-diaria/` e `/estoquepainel/relatorio-auditoria/` (Histórico de acertos manuais).
* **Objetivo:** Resolver rupturas de gôndola reportadas pelos vendedores no PDV e corrigir estoques negativos.
* **Passo a Passo:**
  1. Acesse `/estoquepainel/auditoria-diaria/` e clique no botão vermelho **Gerar Missão de Hoje** para compilar todas as rupturas e divergências pendentes em uma lista de contagem.
  2. Clique no ícone amarelo de código de barras na missão criada para abrir a tela de contagem e conferir/bipar os itens na prateleira.
  3. Finalize a missão em **Revisar e Concluir** para atualizar os saldos e gerar o relatório de impacto financeiro.

## 11. Suprir Estoque e Carrinho de Pedidos de Compra
* **Rotas:** `/estoquepainel/suprir-estoque/` e `/estoquepainel/carrinho-pedido/`
* **Quem acessa:** Gerente e Supervisor.
* **Objetivo:** Calcular sugestões de reposição com base nas vendas dos últimos 14 dias, rupturas registradas no caixa e dias de segurança.
* **Passo a Passo:**
  1. Acesse `/estoquepainel/suprir-estoque/` e analise as colunas **Vendidos (14d)**, **Rupturas de Caixa**, **Estoque Atual**, **QTD Recomendada** e **QTD A Pedir**.
  2. Para encomendar um produto, clique no **ícone de carrinho azul (`+`)** na coluna *Ações* da linha do item.
  3. No modal **Adicionar ao Pedido**, informe a **QTD a Pedir** e a **Previsão de Chegada**, depois clique em **Colocar no Carrinho**. *(Para imprimir a lista de sugestões em PDF, clique no botão amarelo **Imprimir**)*.
  4. Para revisar e concluir a encomenda, clique no botão azul **Ver Pedido** no topo direito (`/estoquepainel/carrinho-pedido/`).
  5. Na tela **Carrinho de Pedidos (Retaguarda)**, confira os itens, quantidades e datas de previsão e clique no botão verde **Finalizar Compra e Enviar** (isso atualiza o status *A Caminho* e *Previsão* visível para os vendedores no PDV), ou clique em **Cancelar Compra** para descartar.

## 12. Impressão de Etiquetas de Preço
* **Rota:** `/estoquepainel/etiquetas/`
* **Quem acessa:** Acesso livre (todos os perfis).
* **Passo a Passo:**
  1. Na coluna esquerda (**1. Formato da Etiqueta**), escolha entre **Pequena** (`4cm x 5cm`, ideal para trilhos de gôndola), **Média** (`6cm x 10cm`, padrão para prateleiras) ou **Cartaz Grande** (`Folha A4 Completa`, ideal para paletes e promoções).
  2. Na coluna direita (**2. Fila de Impressão**), bipe ou digite o *Código de barras, interno ou nome* no campo **Adicionar Produto** e clique em **Adicionar**. *(Códigos inexistentes ficam listados no botão amarelo **Não Encontrados**)*.
  3. Ajuste a **Qtd de Etiquetas** de cada item na tabela.
  4. Clique no botão verde **GERAR PDF PARA IMPRESSÃO** para baixar o arquivo formatado para folha A4.

## 13. Atualização de Etiquetas de Gôndola (Alertas de Preço)
* **Rota:** `/estoquepainel/alertas-preco/`
* **Objetivo:** Listar produtos que tiveram reajuste de preço (via entrada de XML ou edição manual) e precisam ter a etiqueta trocada na prateleira.
* **Passo a Passo:**
  1. Confira o comparativo **Custo (De -> Para)** e **Preço Venda (De -> Para)** na tabela.
  2. Clique em **Imprimir** para gerar a etiqueta atualizada do item.
  3. Após colocar a etiqueta nova na gôndola da loja, clique no botão verde **Resolvido** para retirar o alerta da lista.

---

# BLOCO 3: SISTEMA TINTOMÉTRICO E MÓDULO FISCAL

## 14. Central Tintométrica e Calculadora de Cores
* **Rotas:** `/tintometricopainel/` (Seleção de Marca) e `/tintometricopainel/<marca>/` (Calculadora, ex: `/tintometricopainel/coral/`).
* **Objetivo:** Calcular a fórmula exata de pigmentos e base para preparar tintas personalizadas e lançar no carrinho.
* **Passo a Passo:**
  1. Acesse `/tintometricopainel/` e clique em **Acessar Sistema** no cartão da marca desejada (ex: **Sistema Coral**).
  2. Na tela **Produção Tintométrica**, preencha os 3 filtros no topo:
     * **Cor (Busca):** Digite o nome ou código técnico da cor e selecione na lista.
     * **Produto (Linha):** Selecione a linha da tinta (ex: Rende Muito, Acrílico Fosco, etc.).
     * **Embalagem:** Selecione o tamanho da lata (ex: 0,9L, 3,6L, 18L).
  3. Clique no botão azul **Calcular**.
  4. O sistema exibirá dois painéis:
     * **Detalhes da Base (Esquerda):** Mostra a *Base Exigida*, o tamanho, o *Cód. Barras*, o *Cód. Interno*, o *Saldo em Estoque* e os valores. *(Se quiser usar outra lata compatível do estoque, clique em **Mudar Base** no cabeçalho do cartão)*.
     * **Pigmentos / Corantes (Direita):** Lista cada pigmento exigido, a quantidade na máquina e em ML, o custo (com ícone de olho para exibir/ocultar) e o **Preço Total Final**.
  5. Se a base estiver devidamente vinculada, clique no botão verde **Enviar para PDV** (ou se você abriu o tintométrico por dentro do PDV/Novo Pedido, a tinta preparada vai direto para o carrinho).

## 15. Vínculo de Bases e Embalagens Tintométricas
* **Rota:** `/cadastrar-vinculo/`
* **Objetivo:** Ligar cada base e embalagem do catálogo da máquina tintométrica ao respectivo produto cadastrado no estoque da loja.
* **Passo a Passo:**
  1. Acesse `/cadastrar-vinculo/` para abrir a **Grade de Vínculos: Bases & Embalagens**.
  2. Na coluna **Produto no Estoque (Cód. Interno)**, digite ou selecione o código interno do produto correspondente àquela Base e Tamanho. *(A linha fica verde com ícone de check quando vinculada).*
  3. Clique no botão verde **Salvar Todas as Modificações** no rodapé.

## 16. Centro Fiscal e Fila de Emissão (NF-e / NFC-e)
* **Rotas:** `/gerenciapainel/centrofiscal/` (Menu Fiscal) e `/gerenciapainel/emitirnota/` (Fila de Emissão).
* **Atalhos do Centro Fiscal:** **Fila Fiscal** (`/gerenciapainel/emitirnota/`), **Consultar NF-e** (`/gerenciapainel/consultanfe/`), **Consultar NFC-e** (`/gerenciapainel/consultanfce/`) e **Devoluções** (`/gerenciapainel/devolucoes/`).
* **Como Emitir Nota de uma Venda:**
  1. Acesse `/gerenciapainel/emitirnota/` (use as abas **⏳ Apenas Sem Nota** ou **📋 Todas as Vendas** para filtrar).
  2. Na linha da venda desejada, clique em **🖨️ Emitir NFC-e (Cupom)** (Modelo 65) ou **📄 Emitir NF-e (A4)** (Modelo 55).
  3. No modal **Configurar e Emitir Documento Fiscal**, revise as 5 seções:
     * *1. Dados Gerais da Nota:* CFOP (ex: `5102`, `5405`), Natureza da Operação e Indicador de Presença.
     * *2. Dados do Destinatário:* Escolha o cliente em **Selecionar Destinatário Cadastrado** para preencher CPF/CNPJ, IE e endereço automaticamente.
     * *3. Itens do Pedido* e *4. Transporte da Nota Fiscal* (Modalidade do Frete: `9 - Retirada no Balcão`, `0 - CIF`, `1 - FOB`).
     * *5. Informações Fiscais e Pagamento:* CST PIS/COFINS (os pagamentos do PDV são puxados automaticamente).
  4. Clique em **🚀 Confirmar e Emitir Nota**.

## 17. Consulta, Correção, Devolução e Contabilidade (NF-e e NFC-e)
* **Rotas:** `/gerenciapainel/consultanfe/` (NF-e Modelo 55), `/gerenciapainel/consultanfce/` (NFC-e Modelo 65) e `/gerenciapainel/devolucoes/` (Histórico de Devoluções).
* **Ações Disponíveis nas Notas Autorizadas:**
  * **🖨️ PDF / Cupom:** Visualiza ou imprime o DANFE (A4) ou cupom térmico.
  * **📦 XML:** Baixa o arquivo XML autorizado.
  * **📧 Email:** Envia a nota por e-mail para o cliente.
  * **📝 CC-e (Apenas NF-e):** Emite Carta de Correção Eletrônica (mínimo 15 caracteres; permite corrigir transportadora, endereço sem mudar cidade/UF ou observações, mas **proíbe** alterar valores, impostos ou CPF/CNPJ).
  * **🔄 Devolver:** Abre o modal para selecionar os produtos e quantidades a estornar, informando a justificativa e gerando uma **NF-e de Entrada Reversa (CFOP 1202/2202)** que devolve os itens ao estoque.
  * **❌ Cancelar:** Cancela o documento fiscal junto à SEFAZ dentro do prazo legal.
* **Histórico e Correção de Devoluções (`/gerenciapainel/devolucoes/`):**
  * Exibe todas as NF-es de devolução emitidas, permitindo clicar em **🔄 Atualizar** para sincronizar com a SEFAZ, baixar **🖨️ DANFE** e **📦 XML**. Se uma devolução falhar, clique em **🛠️ Resolver Erro** e depois em **🗑️ Excluir Rascunho e Liberar Nova Tentativa** para corrigir o cadastro e emitir novamente.
* **Se a Nota de Venda der Erro ou Rejeição na SEFAZ:**
  * Leia o alerta vermelho no topo e clique no botão amarelo **🛠️ Reenviar Nota à SEFAZ** (ou **🛠️ Reenviar**), corrija os dados cadastrais/fiscais no modal e clique em **🚀 Corrigir e Reenviar Nota**.
* **Ferramentas Contábeis (Topo da tela Consultar NF-e):**
  * **📦 Exportação em Lote (ZIP):** Seleciona Mês e Ano e baixa um arquivo ZIP com todos os XMLs e PDFs para o contador.
  * **🚫 Inutilizar Numeração:** Comunica à SEFAZ uma sequência de números pulados (informando Modelo 55 ou 65, Número Inicial, Número Final e Justificativa Técnica).

---

# BLOCO 4: RH, PONTO ELETRÔNICO E FIDELIDADE

## 18. Bater Ponto Eletrônico
* **Rota:** `/ponto/`
* **Quem acessa:** Todos os colaboradores.
* **Passo a Passo:**
  1. Acesse `/ponto/` (onde aparece o relógio digital em tempo real).
  2. Digite seu **USUÁRIO** (ex: `diego`) e sua **SENHA**.
  3. Clique no botão turquesa **BATER PONTO** para registrar a entrada, saída para almoço, retorno do almoço ou saída final.

## 19. Gestão de Equipe e Colaboradores
* **Rota:** `/gerencia/colaboradores/`
* **Quem acessa:** Gerente (para criar, editar e excluir) e demais colaboradores (apenas visualizam seus próprios dados e comissões).
* **Como Cadastrar um Novo Colaborador:**
  1. Clique no botão verde **+ NOVO COLABORADOR** no topo direito.
  2. Preencha o **Nome Completo (Apenas Letras)** — o sistema gerará automaticamente o **Login de Acesso** no padrão `.tec` (ex: `diegos.tec`).
  3. Escolha o **Perfil de Acesso**: *Vendedor (PDV e Clientes)*, *Supervisor (Acesso ao Estoque)* ou *Gerente (Acesso Total)*.
  4. Selecione o **Local de Trabalho (Filial)** — o código IBGE da filial escolhida é usado para calcular faltas e feriados locais automaticamente no ponto.
  5. Defina a senha nos campos **Mudar Senha** e **Confirmar Nova Senha**, e informe a **Comissão de Vendas (%)**.
  6. Configure a **Escala Semanal Dinâmica**: você pode usar o **Preenchimento Rápido** informando *Entrada*, *Almoço (Tempo)*, *Saída*, marcando os dias (*Seg* a *Dom*) e clicando em **⬇️ Aplicar aos dias**, ou ajustar dia por dia manualmente.
  7. Clique em **💾 Salvar Ficha**.
* **Como Editar ou Excluir:** Clique em **✏️ Editar** na linha do colaborador (o login não pode ser alterado, mas senha, comissão, filial e escala podem) ou no ícone de lixeira vermelha **🗑️** para excluir.

## 20. Consulta e Justificativas de Ponto Eletrônico
* **Rota:** `/gerenciapainel/relatoriospainel/relatorioponto/`
* **Como Consultar o Espelho de Ponto:**
  1. Selecione o **Colaborador**, a **Data Inicial** e a **Data Final**, depois clique em **Pesquisar**.
  2. A tabela exibirá *Data*, *H. Entrada*, *Saída Alm.*, *Ret. Alm.*, *H. Saída*, *Saldo Diário* e, no rodapé, o **Saldo Total no Período**.
  3. Clique em **Gerar PDF** para imprimir ou baixar o espelho de ponto.
* **Como Lançar Férias, Faltas, Abonos ou Ajustes (Exclusivo Gerente):**
  1. Clique no botão amarelo **Justificar** no cabeçalho da tabela.
  2. No modal **Auditoria e Justificativa de Ponto**, escolha o **Tipo de Ação**:
     * **🌴 Férias / Licença Prolongada:** Informe *Data Inicial* e *Data Final*.
     * **🚑 Falta Justificada / Atestado:** Informe *Data Inicial*, *Data Final* e marque a chave *Possui Atestado* se houver.
     * **⏳ Abono Parcial (Declaração de Horas):** Informe a *Data da Ocorrência*, *Hora Inicial Abonada* e *Hora Final Abonada*.
     * **✏️ Ajuste Direto de Batida (Esquecimento):** Escolha a *Data do Ajuste*, *Qual batida?* (*Entrada 1*, *Saída Almoço*, *Retorno Almoço* ou *Saída Final*) e a *Nova Hora Correta*.
  3. Escreva o **Motivo / Justificativa Legal**.
  4. Preencha a **Dupla Assinatura Digital Necessária** (**Senha do Gerente** + **Senha do Colaborador** dando ciência) e clique em **Registrar Auditoria**. *(Os registros auditados podem ser conferidos clicando no ícone de olho na tabela).*

## 21. Manutenção de Fidelidade (Pontos de Clientes e Pintores)
* **Rota:** `/gerencia/pontos/`
* **Quem acessa:** Gerente.
* **Como Configurar:**
  1. Na coluna **Porcentagem de Retorno (%)**, defina quantos pontos são gerados a cada `R$ 1,00` gasto **Para o CLIENTE** e a cada `R$ 1,00` indicado **Para o PINTOR**.
  2. O sistema trabalha travado no **Fator 100** (**100 Pontos = R$ 1,00** de desconto), portanto o número de pontos configurado por real equivale diretamente à porcentagem de cashback.
  3. Clique em **💾 Salvar Regras de Fidelidade**.

---

# BLOCO 5: GERÊNCIA, CLIENTES, RELATÓRIOS E CONFIGURAÇÕES

## 22. Painel de Gerência
* **Rota:** `/gerenciapainel/`
* **Objetivo:** Central de administração do sistema.
* **Atalhos Disponíveis:**
  * **Pontos** (`/gerencia/pontos/`): Exclusivo Gerente.
  * **Colaboradores** (`/gerencia/colaboradores/`): Acesso à equipe.
  * **Centro Fiscal** (`/gerenciapainel/centrofiscal/`): Emissão e consulta de notas.
  * **Relatórios** (`/gerenciapainel/relatoriospainel/`): Painel de relatórios de vendas, ponto e comissões.
  * **Configurações** (`/gerenciapainel/configuracoes/`): Exclusivo Gerente.

## 23. Consulta e Cadastro de Clientes e Pintores (CRM)
* **Rota:** `/clientes/`
* **Objetivo:** Cadastrar consumidores e pintores/indicantes, consultar saldo de pontos e histórico de compras.
* **Como Pesquisar:** Digite *Nome*, *CPF/CNPJ* ou *Celular* na barra de busca superior e clique em **Buscar** (ou **Limpar** para ver todos).
* **Como Cadastrar ou Editar:**
  1. Clique no botão verde **+ NOVO CADASTRO** (ou no botão de lápis **✏️** na linha do cliente).
  2. Escolha o **Tipo de Registro**: **👤 Física** (CPF) ou **🏢 Jurídica** (CNPJ, Inscrição Estadual e Razão Social).
  3. Selecione o **Indicador de IE (Obrigatório SEFAZ)**: `9 - Não Contribuinte`, `1 - Contribuinte ICMS` ou `2 - Contribuinte Isento`.
  4. Preencha **Nome Completo / Fantasia**, **Telefone / WhatsApp** e **E-mail**.
  5. Na coluna direita (**Endereço ViaCEP**), digite o **CEP** para preencher automaticamente Rua, Bairro, Cidade, UF e capturar o **Código IBGE Sefaz** (necessário para emissão de NF-e).
  6. Em **Categoria no Sistema**, marque **Consumidor Padrão** e/ou **Pintor / Indicante** (um mesmo cadastro pode ter ambas as categorias).
  7. Clique em **💾 GRAVAR FICHA**.
* **Outras Ações na Lista:**
  * **Ícone Carrinho Azul (`🛒`):** Abre o *Histórico de Compras* mostrando número da venda, data/hora, vendedor e valor total.
  * **Coluna Pontos (Fidelidade):** Exibe o saldo atual de pontos e quanto ele vale em desconto (`R$`).

## 24. Relatórios de Vendas e Extrato de Comissões
* **Relatório Geral de Vendas (`/gerencia/relatorios/`):**
  * Exibe indicadores consolidados: **Faturamento Bruto**, **Faturamento Líquido Real**, **Quantidade de Vendas**, **Ticket Médio**, **Valor Descontado da Maquininha**, **Desconto Comum** e **Desconto por Ponto**.
  * Permite filtrar por **Vendedor** e **Mês Referência** clicando em **Filtrar Relatório**.
  * Na tabela inferior, mostra cada venda faturada com detalhamento de taxas e descontos, além dos botões de reimpressão de **Bobina** e **PDF A4**. *(Para cancelar uma venda faturada, clique no botão **Cancelar Vendas no Painel de Pedidos**).*
* **Extrato Detalhado de Comissões (`/gerenciapainel/relatoriospainel/comissao/`):**
  * Filtre por **Colaborador**, **Mês** e **Ano** e clique em **Extrair Relatório**.
  * Exibe **Total Bruto Vendido**, **Custo Total das Taxas (Maquininha)** e **Comissão Total a Pagar Líquida**, além do cálculo pedido a pedido descontando taxas e abatimentos.

## 25. Configurações do Sistema (Exclusivo Gerente)
* **Rota Principal:** `/gerenciapainel/configuracoes/`
* **Submenus Disponíveis:**
  * **Dados da Loja (`/gerenciapainel/configuracoes/loja/`):** Define o **Nome da Filial / Loja** e o **Código IBGE do Município** (usado pelo motor de RH para reconhecer automaticamente feriados locais e bloquear dias não úteis no ponto).
  * **Fidelidade (`/gerenciapainel/configuracoes/fidelidade/`):** Chaves de ativação para **Ativar Pontuação para Clientes** e **Ativar Pontuação para Pintores / Indicantes**. *(As porcentagens por real são ajustadas em `/gerencia/pontos/`)*.
  * **Estoque (`/gerenciapainel/configuracoes/estoque/`):** Define os **Dias de Cobertura (Segurança) do Estoque**, usado como base no cálculo de sugestão de compras da tela *Suprir Estoque*.
  * **Tabelas Auxiliares (`/gerenciapainel/configuracoes/auxiliares/`):** Permite cadastrar (`+ NOVO`), editar (ícone lápis) e excluir (ícone lixeira) **Famílias**, **Marcas** e **Unidades de Medida (UN)** utilizadas no cadastro de produtos.
  * **Taxas da Maquininha (`/gerenciapainel/configuracoes/maquininha/`):**
    * **Cartão de Débito:** Define a **Taxa de Débito (%)** à vista.
    * **Cartão de Crédito - Regras de Parcelamento:** Tabela de **1x (À Vista)** até **12x**, onde você configura a **Taxa (%)** descontada pela operadora e o **Valor Compra De (R$)** (valor mínimo do pedido necessário para liberar aquela quantidade de parcelas no PDV).

## 26. Guia Rápido de Solução de Problemas (FAQ para a IA)
* **"Não consigo editar o estoque direto na ficha do produto":** O campo *Estoque Atual* é bloqueado por segurança. Para ajustar quantidades manualmente ou bipando, vá em `/estoquepainel/estoque/` -> **Acerto Rápido** (`/estoquepainel/acerto-estoque/`), ou dê entrada via XML em `/estoquepainel/entrada-carga/`.
* **"O parcelamento em X vezes não aparece no PDV":** Verifique o valor total da venda e as regras em **Configurações -> Taxas da Maquininha** (`/gerenciapainel/configuracoes/maquininha/`), pois cada parcela exige um *Valor Compra De (R$)* mínimo.
* **"Não consigo emitir NF-e para um cliente":** Verifique no cadastro do cliente (`/clientes/`) se o **CEP** foi preenchido para capturar o **Código IBGE Sefaz** e se o **Indicador de IE** está selecionado corretamente.
* **"O botão Enviar para PDV no Tintométrico está bloqueado (Aguardando Vínculo)":** A base exigida para aquela embalagem ainda não foi ligada a um produto do estoque. Acesse `/cadastrar-vinculo/` e preencha o código interno do produto correspondente.
* **"Como cancelar uma venda já faturada?":** Vá ao **Painel de Pedidos** (`/paineldepedidos/`), localize a venda e clique no ícone vermelho **X** na coluna *Ações* (exige login, senha de autorização e motivo).
* **"Deu erro ao emitir uma NF-e de devolução, como refazer?":** Acesse `/gerenciapainel/devolucoes/`, clique em **🛠️ Resolver Erro** na linha da devolução com falha e depois em **🗑️ Excluir Rascunho e Liberar Nova Tentativa** para limpar a tentativa anterior e emitir novamente.

## 27. Dicionário de Erros Comuns da SEFAZ (Como Resolver no TecVarejo)
Sempre que uma NF-e (Modelo 55) ou NFC-e (Modelo 65) retornar rejeição na fila `/gerenciapainel/emitirnota/`, identifique o código abaixo e oriente o operador:

- **Rejeição 204 (Duplicidade de NF-e):** A nota já foi autorizada anteriormente na SEFAZ com essa mesma numeração. Vá em `/gerenciapainel/consultanfe/` ou `/gerenciapainel/consultanfce/` para verificar se ela já consta como autorizada.
- **Rejeição 225 / 215 (Falha no Schema XML):** Algum campo obrigatório ficou vazio ou com caractere inválido (geralmente endereço sem número, CEP incompleto ou nome do produto com símbolos estranhos). Corrija o cadastro do cliente em `/clientes/` ou do produto em `/estoquepainel/estoque/` e reenvie.
- **Rejeição 232 / 233 (IE do Destinatário não informada ou inválida):** O cliente é Pessoa Jurídica contribuinte, mas está sem Inscrição Estadual válida. Edite o cliente em `/clientes/` e preencha a IE correta ou altere o **Indicador de IE** para `2 - Isento` ou `9 - Não Contribuinte`.
- **Rejeição 301 / 302 (Uso Denegado):** O CNPJ/IE do destinatário está bloqueado na Receita Estadual. Não é possível emitir NF-e para esse CNPJ enquanto ele não regularizar a situação na SEFAZ.
- **Rejeição 508 / 509 (CST incompatível com Não Contribuinte / CRT):** O regime tributário da loja (Simples Nacional) exige CSOSN (ex: `102`, `500`) e não CST de Regime Normal. Ajuste o CSOSN do produto em `/estoquepainel/estoque/` ou nas configurações fiscais em `/gerenciapainel/configfiscal/`.
- **Rejeição 528 (Valor do ICMS difere do produto BC e Alíquota):** Alíquota ou base de cálculo inconsistente no cadastro do produto. Verifique a alíquota de ICMS do item em `/estoquepainel/estoque/`.
- **Rejeição 539 (Duplicidade com diferença na Chave de Acesso):** Já existe uma nota autorizada com esse número em outra data/hora. Contate o Gerente ou DEV para ajustar a numeração sequencial da série fiscal em `/gerenciapainel/configfiscal/`.
- **Rejeição 610 / 611 (Total da NF difere do somatório dos itens / pagamentos):** Diferença de centavos entre o desconto aplicado e o total pago. Reabra a configuração da nota e confira a aba **5. Informações Fiscais e Pagamento**.
- **Rejeição 694 (Não informado grupo de ICMS para UF de destino - DIFAL):** Venda interestadual para consumidor final não contribuinte exige preenchimento de DIFAL ou CFOP interestadual (`6102` / `6108`).
- **Rejeição 778 (Informado NCM inexistente):** O código NCM de 8 dígitos cadastrado no produto foi extinto pela Receita Federal. Edite o produto em `/estoquepainel/estoque/` e atualize o campo **NCM** (ex: tintas à base de polímeros acrílicos/vinílicos costumam usar `32091010`).
- **Rejeição 806 (Operação com ICMS-ST sem informação do CEST):** O produto usa CFOP/CSOSN de Substituição Tributária (`5405` / `500`), mas está sem o código **CEST** de 7 dígitos preenchido no cadastro do produto.

## 28. Regras Internas e Políticas Operacionais da Loja
- **Descontos no Balcão (PDV e Pedidos):** Vendedores possuem autonomia para descontos padrão dentro do limite configurado no sistema. Descontos acima do teto exigem senha/autorização presencial do **Gerente** ou **Supervisor** no modal de liberação.
- **Troca ou Devolução de Tinta Tintométrica (Tinta Batida na Máquina):** Tintas pigmentadas sob encomenda no sistema tintométrico (Coral/Suvinil) **não possuem troca por arrependimento de cor**, pois são preparadas exclusivamente para o cliente. Trocas ocorrem apenas em caso de defeito de fabricação ou erro operacional comprovado da loja, mediante autorização da gerência em `/gerenciapainel/devolucoes/`.
- **Programa de Fidelidade (Pontos):** A conversão no PDV segue o **Fator 100** (**100 Pontos = R$ 1,00** de desconto), conforme as porcentagens de retorno definidas em `/gerencia/pontos/`.
- **Retirada e Entrega:** Para vendas com entrega em domicílio, sempre selecione a modalidade de frete adequada na emissão da NF-e e registre o endereço completo com CEP válido no cadastro do cliente.
