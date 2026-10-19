from inventario.models import Familia, Marca
from inventario.models.configuracoes import ConfiguracaoSistema, ConfiguracaoEmissor
from django.db import connections

def obter_dados_auxiliares():
    """ Busca marcas, famílias e unidades para a tela de configurações """
    familias = Familia.objects.all().order_by('nome')
    marcas = Marca.objects.all().order_by('nome')
    unidades = []
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT id, nome FROM inventario_un ORDER BY nome")
            unidades = [{'id': row[0], 'nome': row[1]} for row in cursor.fetchall()]
    except Exception:
        pass
    return familias, marcas, unidades

def processar_salvamento_configuracoes(origem, dados):
    """ Centraliza a lógica de atualização das tabelas de configuração """
    if origem == 'loja':
        loja, _ = ConfiguracaoEmissor.objects.get_or_create(id=1)
        loja.razao_social = dados.get('razao_social')
        loja.cnpj = dados.get('cnpj')
        loja.endereco = dados.get('endereco')
        loja.telefone = dados.get('telefone')
        loja.save()

    elif origem == 'fiscal':
        loja, _ = ConfiguracaoEmissor.objects.get_or_create(id=1)
        loja.ambiente_nfe = dados.get('ambiente_nfe', 'homologacao')
        loja.ambiente_nfce = dados.get('ambiente_nfce', 'homologacao')
        loja.crt = dados.get('crt')
        loja.natureza_operacao_padrao = dados.get('natureza_operacao_padrao', '').strip().upper()
        loja.csosn_padrao = dados.get('csosn_padrao', '').strip()
        loja.cfop_padrao_interno = dados.get('cfop_padrao_interno', '').strip()
        loja.cfop_padrao_externo = dados.get('cfop_padrao_externo', '').strip()
        loja.token_gnf = dados.get('token_gnf', '').strip()
        loja.csc_id = dados.get('csc_id', '').strip()
        loja.csc_token = dados.get('csc_token', '').strip()
        loja.save()

    elif origem in ['fidelidade', 'estoque']:
        config, _ = ConfiguracaoSistema.objects.get_or_create(id=1)
        dias = dados.get('dias_seguranca')
        if dias: 
            config.dias_seguranca_estoque = int(dias)
            
        if 'pontuacao_cliente' in dados or 'pontuacao_pintor' in dados or origem == 'fidelidade':
            config.modulo_pontuacao_cliente_ativo = dados.get('pontuacao_cliente') == 'on'
            config.modulo_pontuacao_pintor_ativo = dados.get('pontuacao_pintor') == 'on'
        config.save()
        