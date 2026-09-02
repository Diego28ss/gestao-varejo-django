import json
from django.db import transaction
from django.db.models import F
from inventario.models import Clientes, Produtos, Vendas, ConfiguracaoPontos, Usuarios

class VendaService:

    @staticmethod
    def registrar_checkout(dados):
        status_venda = dados.get('status', 'VENDA')
        pontos_resgatados = int(dados.get('pontos_resgatados', 0))
        carrinho = dados.get('carrinho', [])
        valor_final = float(dados.get('valor_final', 0))
        nome_vendedor = dados.get('vendedor')

        if not carrinho or len(carrinho) == 0:
            raise ValueError("Bloqueio de Segurança: A operação não contém produtos.")
        if valor_final < 0:
            raise ValueError("Bloqueio de Segurança: O valor total da operação não pode ser negativo.")

        # 🚀 NOVO: Captura do ID e do Nome, dando prioridade absoluta ao Objeto do Banco
        cliente_id = dados.get('cliente_id')
        cliente_nome = dados.get('cliente', '').strip()
        cliente_obj = None

        if cliente_id and str(cliente_id).isdigit():
            cliente_obj = Clientes.objects.filter(id=cliente_id).first()
            if cliente_obj:
                cliente_nome = cliente_obj.nome
        elif cliente_nome:
            cliente_obj = Clientes.objects.filter(nome=cliente_nome).first()

        cliente_valido = cliente_nome if cliente_nome != "" else None

        indicante_id = dados.get('indicante_id')
        indicante_nome = dados.get('indicante', '').strip()
        indicante_obj = None

        if indicante_id and str(indicante_id).isdigit():
            indicante_obj = Clientes.objects.filter(id=indicante_id).first()
            if indicante_obj:
                indicante_nome = indicante_obj.nome
        elif indicante_nome:
            indicante_obj = Clientes.objects.filter(nome=indicante_nome).first()

        indicante_valido = indicante_nome if indicante_nome != "" else None

        comissao_em_reais = 0.00
        if nome_vendedor and status_venda != 'ORCAMENTO':
            usuario = Usuarios.objects.filter(login=nome_vendedor).first()
            if usuario and usuario.comissao > 0:
                comissao_em_reais = valor_final * (float(usuario.comissao) / 100.0)

        carrinho_tratado = []
        for item in carrinho:
            qtd = int(item.get('qtd', 0))
            if qtd <= 0:
                raise ValueError(f"O produto '{item.get('nome')}' está com quantidade inválida ({qtd}).")
            
            preco_desconto = float(item.get('preco_desconto', 0))
            if preco_desconto < 0:
                raise ValueError(f"O produto '{item.get('nome')}' está com preço negativo.")

            item_id_original = str(item.get('id', ''))
            
            if item_id_original.startswith('TINTA-') or not item_id_original.isdigit():
                cod_interno_real = item.get('id_real_estoque')
                if cod_interno_real:
                    produto_banco = Produtos.objects.filter(cod_interno=cod_interno_real).first()
                    if produto_banco:
                        item['id'] = produto_banco.id  
            
            carrinho_tratado.append(item)

        pagamentos_lista = dados.get('pagamentos', [])
        troco_valor = float(dados.get('troco', 0))

        # --- RAIO-X PARA O TERMINAL DO VS CODE ---
        print("\n==================================================")
        print(f"📦 INICIANDO CHECKOUT: {status_venda}")
        print(f"👤 ID do Cliente Recebido do PDV: {cliente_id}")
        print(f"👤 Cliente Encontrado no Banco: {cliente_obj.nome if cliente_obj else 'NENHUM'}")
        print("==================================================\n")

        with transaction.atomic():
            status_fiscal_definido = 'AGUARDANDO_EMISSAO' if cliente_valido else 'SEM_NOTA'

            venda = Vendas.objects.create(
                valor_total=valor_final,
                valor_desconto=float(dados.get('desconto', 0)),
                vendedor=nome_vendedor,
                valor_comissao=comissao_em_reais,
                cliente=cliente_valido, 
                cliente_link=cliente_obj, 
                indicante=indicante_valido,
                indicante_link=indicante_obj,
                status=status_venda,
                cupom_texto=json.dumps(carrinho_tratado),
                troco=troco_valor,
                pagamentos_texto=json.dumps(pagamentos_lista),
                status_fiscal=status_fiscal_definido
            )

            if status_venda == 'ORCAMENTO':
                return venda.id

            for item in carrinho_tratado:
                p_id = item.get('id') or item.get('produto_id')
                p_qtd = int(item.get('qtd', 0))
                cod_barras = str(item.get('cod_barras', ''))

                if p_id and p_qtd > 0:
                    if 'TINTO' in str(p_id) or cod_barras == 'TINTOMETRICO':
                        continue
                    
                    try:
                        produto = Produtos.objects.filter(id=p_id).first()
                        if produto:
                            produto.estoque_atual = F('estoque_atual') - p_qtd
                            produto.save()
                    except Exception as e:
                        print(f"Erro ao baixar estoque do produto {p_id}: {e}")
            
            # 🚀 ATUALIZAÇÃO DE FIDELIDADE (Blindada com Logs)
            if cliente_obj:
                pontos_atuais = int(cliente_obj.pontos) if cliente_obj.pontos else 0
                
                if pontos_resgatados > 0:
                    pontos_atuais = max(0, pontos_atuais - pontos_resgatados)

                config_cli = ConfiguracaoPontos.objects.filter(tipo_usuario='CLIENTE').first()
                if config_cli:
                    multiplicador = float(config_cli.pontos_por_real or 0)
                    novos_pontos = int(float(valor_final) * multiplicador)
                    cliente_obj.pontos = pontos_atuais + novos_pontos
                    print(f"✅ [FIDELIDADE] Cliente: {cliente_obj.nome} | Venda R$: {valor_final} | Ganhou: {novos_pontos} pts")
                else:
                    cliente_obj.pontos = pontos_atuais
                    print(f"⚠️ [FIDELIDADE] Nenhuma regra ativa de pontos encontrada para 'CLIENTE'. Zero pontos gerados.")
                
                # Força a gravação imediata apenas da coluna de pontos para evitar sobreposições
                cliente_obj.save(update_fields=['pontos'])

            if indicante_obj and indicante_obj != cliente_obj:
                pontos_atuais_pin = int(indicante_obj.pontos) if indicante_obj.pontos else 0
                config_pin = ConfiguracaoPontos.objects.filter(tipo_usuario='PINTOR').first()
                if config_pin:
                    multiplicador_pin = float(config_pin.pontos_por_real or 0)
                    pontos_indicacao = int(float(valor_final) * multiplicador_pin)
                    indicante_obj.pontos = pontos_atuais_pin + pontos_indicacao
                    print(f"✅ [FIDELIDADE] Pintor: {indicante_obj.nome} | Indicação R$: {valor_final} | Ganhou: {pontos_indicacao} pts")
                else:
                    indicante_obj.pontos = pontos_atuais_pin
                
                indicante_obj.save(update_fields=['pontos'])

            return venda.id
        