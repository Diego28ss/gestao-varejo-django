import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from inventario.models import Vendas, Produtos, Usuarios

class RetaguardaService:
    
    @staticmethod
    def listar_pedidos(filtro_status, filtro_periodo):
        agora = timezone.now()
        hoje = agora.date()
        query = Q()

        if filtro_periodo == '7d': query &= Q(data_venda__gte=agora - timedelta(days=7))
        elif filtro_periodo == '14d': query &= Q(data_venda__gte=agora - timedelta(days=14))
        elif filtro_periodo == '30d': query &= Q(data_venda__gte=agora - timedelta(days=30))
        elif filtro_periodo == '60d': query &= Q(data_venda__gte=agora - timedelta(days=60))
        elif filtro_periodo == 'este_mes': query &= Q(data_venda__year=hoje.year, data_venda__month=hoje.month)

        if filtro_status == 'FATURADO': query &= Q(status__in=['FATURADO', 'VENDA'])
        elif filtro_status != 'TODOS': query &= Q(status=filtro_status)

        return Vendas.objects.filter(query).order_by('-id')

    @staticmethod
    def cancelar_pedido(pedido_id):
        venda = Vendas.objects.get(id=pedido_id)

        status_fiscais_bloqueados = ['AUTORIZADO', 'PROCESSANDO_NUVEM', 'ENVIANDO', 'CANCELANDO']
        if venda.status_fiscal in status_fiscais_bloqueados:
            raise ValueError(f"Operação Bloqueada: Esta venda possui uma Nota Fiscal na SEFAZ (Status: {venda.status_fiscal}). "
                             "Você deve ir ao 'Painel Gerencial > Emitir Nota' e Cancelar a Nota primeiro.")

        if venda.status == 'CANCELADA':
            raise ValueError("Este pedido já se encontra cancelado.")

        with transaction.atomic():
            if venda.status in ['FATURADO', 'FINALIZADO'] and venda.cupom_texto:
                try:
                    carrinho = json.loads(venda.cupom_texto)
                    if isinstance(carrinho, str): carrinho = json.loads(carrinho)
                        
                    for item in carrinho:
                        if isinstance(item, dict):
                            item_id = str(item.get('id', '')).strip()
                            qtd = float(item.get('qtd', item.get('quantidade', 0)))
                            if qtd > 0:
                                prod = Produtos.objects.filter(id=int(item_id)).first() if item_id.isdigit() else Produtos.objects.filter(cod_interno=item_id).first()
                                if prod:
                                    prod.estoque_atual = float(prod.estoque_atual or 0) + qtd
                                    prod.save(update_fields=['estoque_atual'])
                except Exception as e:
                    print(f"Erro ao reverter estoque no cancelamento da venda {pedido_id}: {e}")

            venda.status = 'CANCELADA'
            venda.status_fiscal = 'SEM_NOTA' 
            venda.save(update_fields=['status', 'status_fiscal'])

    @staticmethod
    def reabrir_pedido(pedido_id, login, senha, motivo):
        autorizador = Usuarios.objects.filter(login=login, senha=senha, perfil__in=['Gerente', 'Supervisor', 'ADMINISTRADOR', 'DEV']).first()
        if not autorizador:
            raise ValueError("Acesso negado: Login ou senha inválidos, ou utilizador sem privilégios de gerência.")
        
        pedido = Vendas.objects.get(id=pedido_id)
        
        if pedido.status in ['FATURADO', 'FINALIZADO', 'VENDA']:
            # Importar de forma preguiçosa (Lazy) para evitar dependência circular caso exista
            from inventario.services.vendas.venda_service import VendaService
            VendaService.estornar_fidelidade_e_estoque(pedido)
            
        pedido.status = 'ABERTO'
        obs_atual = pedido.observacoes or ""
        nova_obs = f"REABERTO por {autorizador.login.upper()} ({timezone.localtime().strftime('%d/%m %H:%M')}): {motivo}"
        pedido.observacoes = f"{obs_atual}\n{nova_obs}" if obs_atual else nova_obs
        pedido.save()
        return pedido

    @staticmethod
    def estornar_faturamento(pedido_id):
        pedido = Vendas.objects.get(id=pedido_id)
        pedido.status = 'ABERTO'
        obs_atual = pedido.observacoes or ""
        nova_obs = f"ESTORNO DE CAIXA ({timezone.localtime().strftime('%d/%m %H:%M')})"
        pedido.observacoes = f"{obs_atual}\n{nova_obs}" if obs_atual else nova_obs
        pedido.save()
        