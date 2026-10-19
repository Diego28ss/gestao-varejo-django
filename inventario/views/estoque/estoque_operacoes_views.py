import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from inventario.models import AlertaPreco

from inventario.services.estoque.estoque_operacoes_service import (
    gerar_auditoria_aleatoria,
    resolver_alerta_gondola,
    buscar_produto_para_etiqueta
)

# ==========================================
# MISSÃO MATINAL / AUDITORIA DIÁRIA
# ==========================================
def tela_auditoria_diaria(request):
    """ Painel visual do Histórico de Auditorias Diárias """
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor', 'Dev']:
        messages.error(request, "Acesso restrito a Gerentes, Supervisores e Desenvolvedores.")
        return redirect('painel_principal')

    status_filtro = request.GET.get('status', 'TODOS')
    from inventario.models import InventarioSessao
    
    # 🚀 RESTAURADO: Busca o inventário real no banco de dados usando o filtro AUDITORIA
    auditorias_db = InventarioSessao.objects.filter(filtro_unidade='AUDITORIA').select_related('criado_por').order_by('-id')
    if status_filtro != 'TODOS':
        auditorias_db = auditorias_db.filter(status=status_filtro)

    lista_auditorias = []
    for aud in auditorias_db:
        lista_auditorias.append({
            'id': aud.id,
            'data_inicio': aud.data_inicio.strftime('%d/%m/%Y %H:%M'),
            'criado_por': aud.criado_por.login.upper() if aud.criado_por else 'SISTEMA',
            'qtd_contados': aud.qtd_itens_contados(),
            'qtd_esperados': aud.qtd_itens_esperados(),
            'status': aud.status,
            'valor_sobra': aud.valor_sobra, 
            'valor_perda': aud.valor_perda  
        })

    return render(request, 'inventario/inventario_auditoria_painel.html', {
        'inventarios': lista_auditorias, 
        'filtro_atual': status_filtro
    })

def gerar_missao_matinal(request):
    """ Coleta Rupturas Pendentes e Estoques Negativos e cria um lote instantâneo """
    if 'usuario_logado' not in request.session: return redirect('login')
    if request.session.get('perfil_usuario') not in ['Gerente', 'Supervisor', 'Dev']:
        messages.error(request, "Acesso restrito.")
        return redirect('painel_principal')

    if request.method == 'POST':
        from inventario.models import Usuarios, InventarioSessao, InventarioItem, Produtos, RupturaEstoque
        
        # 🚀 RESTAURADO: A verdadeira matemática do seu legado!
        ids_ruptura = list(RupturaEstoque.objects.filter(resolvido=False).values_list('produto_id', flat=True))
        ids_negativos = list(Produtos.objects.filter(estoque_atual__lt=0, status='ATIVO').values_list('id', flat=True))
        ids_problematicos = list(set(ids_ruptura + ids_negativos))
        
        if not ids_problematicos:
            messages.success(request, "Loja impecável! Não há rupturas pendentes ou estoques negativos para contar.")
            return redirect('tela_auditoria_diaria')

        produtos_em_contagem = InventarioItem.objects.filter(
            sessao__status='ABERTO', 
            produto_id__in=ids_problematicos
        ).values_list('produto_id', flat=True)
        
        ids_finais = [pid for pid in ids_problematicos if pid not in produtos_em_contagem]
        
        if not ids_finais:
            messages.warning(request, "Os itens problemáticos já estão sendo contados em outro Inventário em andamento!")
            return redirect('tela_auditoria_diaria')

        auditorias_abertas = InventarioSessao.objects.filter(status='ABERTO', filtro_unidade='AUDITORIA')
        if auditorias_abertas.exists():
            lote_aberto = auditorias_abertas.first()
            messages.warning(request, f"A Missão Matinal #{lote_aberto.id} já está em andamento. Conclua-a primeiro!")
            return redirect('tela_auditoria_diaria')

        usuario_logado = Usuarios.objects.filter(login=request.session.get('usuario_logado')).first()
        novo_lote = InventarioSessao.objects.create(
            criado_por=usuario_logado, status='ABERTO', filtro_unidade='AUDITORIA'
        )

        produtos_alvo = Produtos.objects.filter(id__in=ids_finais)
        
        itens_snapshot = [
            InventarioItem(sessao=novo_lote, produto=p, saldo_sistema=p.estoque_atual, saldo_fisico=0, contado=False)
            for p in produtos_alvo
        ]
        InventarioItem.objects.bulk_create(itens_snapshot)
        
        messages.success(request, f"Missão Matinal #{novo_lote.id} gerada! Existem {len(itens_snapshot)} itens problemáticos para contar.")
        return redirect('tela_contagem_dinamica', sessao_id=novo_lote.id)
            
    return redirect('tela_auditoria_diaria')

# ==========================================
# ALERTAS DE PREÇO E CUSTO
# ==========================================
def tela_alertas_preco(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    
    # 🚀 CORREÇÃO DO ERRO DO DJANGO: 'data_alteracao' em vez de 'data_criacao'
    alertas_pendentes = AlertaPreco.objects.filter(resolvido=False).select_related('produto').order_by('-data_alteracao')
    return render(request, 'inventario/alertas_preco.html', {'alertas': alertas_pendentes})

def api_resolver_alerta_preco(request, alerta_id):
    if request.method == 'POST':
        try:
            resolver_alerta_gondola(alerta_id)
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

# ==========================================
# IMPRESSÃO DE ETIQUETAS
# ==========================================
def tela_imprimir_etiquetas(request):
    if 'usuario_logado' not in request.session: return redirect('login')
    return render(request, 'inventario/etiquetas_preco.html')

def api_buscar_produto_etiqueta(request):
    if request.method == 'GET':
        try:
            codigo = request.GET.get('codigo', '')
            produto = buscar_produto_para_etiqueta(codigo)
            return JsonResponse({
                'status': 'sucesso',
                'produto': {
                    'id': produto.id,
                    'nome': produto.nome,
                    'cod_interno': produto.cod_interno or produto.cod_barras,
                    'preco': f"{produto.preco_venda:.2f}".replace('.', ',')
                }
            })
        except ValueError as ve:
            return JsonResponse({'status': 'erro', 'mensagem': str(ve)})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': f"Erro interno: {str(e)}"})
            
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_gerar_pdf_etiquetas(request):
    """ Prepara e renderiza os itens faturados na fila para o formato de impressão """
    if request.method == 'POST':
        try:
            # Lida tanto com envio via JSON (AJAX) quanto Form Data normal
            body_unicode = request.body.decode('utf-8')
            dados = json.loads(body_unicode) if body_unicode else request.POST
            
            itens = dados.get('itens', [])
            if not itens:
                return JsonResponse({'status': 'erro', 'mensagem': 'Nenhum item adicionado para impressão.'})
            
            return render(request, 'inventario/etiquetas_pdf.html', {'itens': itens})
            
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
            
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def api_resolver_alerta_custo(request):
    """ View Fina: Resolve alertas gerados automaticamente por divergência de custo nas NFes """
    if request.method == 'POST':
        try:
            # Lida com requisição JSON ou POST normal
            body_unicode = request.body.decode('utf-8')
            dados = json.loads(body_unicode) if body_unicode else request.POST
            alerta_id = dados.get('alerta_id') or request.POST.get('alerta_id')
            
            resolver_alerta_gondola(alerta_id) # Usa o service que criámos na Fase 5
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})

def desenhar_etiqueta(c, x, y, w, h, produto, modelo):
    """ Desenha o conteúdo de uma única etiqueta com códigos maiores e visíveis """
    from reportlab.lib import colors
    from reportlab.lib.utils import simpleSplit
    from reportlab.lib.units import mm
    
    # Borda da etiqueta para guiar o corte
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.lightgrey)
    c.rect(x, y, w, h)
    
    nome_completo = produto.get('nome', '').upper()
    preco = str(produto.get('preco', '0,00'))
    codigo_barras = str(produto.get('codigo', ''))
    cod_interno = str(produto.get('cod_interno', ''))

    c.setFillColor(colors.black)

    if modelo == 'PEQUENO':
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + w/2, y + h - 4*mm, "JB TINTAS")
        
        c.setFont("Helvetica", 6)
        c.drawCentredString(x + w/2, y + h - 7.5*mm, "SUA CASA DE TINTAS")
        
        c.setFont("Helvetica-Bold", 7)
        linhas_nome = simpleSplit(nome_completo, "Helvetica-Bold", 7, w - 4*mm)
        y_nome = y + h - 11.5*mm
        for linha in linhas_nome[:2]:
            c.drawCentredString(x + w/2, y_nome, linha)
            y_nome -= 3.5*mm
        
        # Preço em destaque negrito
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(x + w/2, y + 12*mm, f"R$ {preco}")
        
        # Códigos maiores e mais visíveis no rodapé
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(x + w/2, y + 6.5*mm, codigo_barras)
        
        c.setFont("Helvetica-BoldOblique", 6.5)
        c.drawCentredString(x + w/2, y + 2*mm, f"Cód Interno: {cod_interno or '---'}")

    elif modelo == 'MEDIO':
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(x + w/2, y + h - 7*mm, "JB TINTAS")
        
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + w/2, y + h - 11.5*mm, "SUA CASA DE TINTAS")
        
        c.setFont("Helvetica-Bold", 9)
        linhas_nome = simpleSplit(nome_completo, "Helvetica-Bold", 9, w - 6*mm)
        y_nome = y + h - 17.5*mm
        for linha in linhas_nome[:3]:
            c.drawCentredString(x + w/2, y_nome, linha)
            y_nome -= 4.5*mm
        
        c.setFont("Helvetica-Bold", 34)
        c.drawCentredString(x + w/2, y + h/2 - 4*mm, f"R$ {preco}")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x + w/2, y + 9.5*mm, codigo_barras)
        
        c.setFont("Helvetica-BoldOblique", 8.5)
        c.drawCentredString(x + w/2, y + 3.5*mm, f"Cód Interno: {cod_interno or '---'}")
        
    elif modelo == 'GRANDE':
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(x + w/2, y + h - 18*mm, "JB TINTAS")
        
        c.setFont("Helvetica", 14)
        c.drawCentredString(x + w/2, y + h - 25*mm, "SUA CASA DE TINTAS")
        
        c.setFont("Helvetica-Bold", 20)
        linhas_nome = simpleSplit(nome_completo, "Helvetica-Bold", 20, w - 20*mm)
        y_nome = y + h - 40*mm
        for linha in linhas_nome[:4]: 
            c.drawCentredString(x + w/2, y_nome, linha)
            y_nome -= 8*mm
        
        c.setFont("Helvetica-Bold", 110)
        c.drawCentredString(x + w/2, y + h/2 - 15*mm, f"R$ {preco}")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(x + w/2, y + 18*mm, f"CÓDIGO DE BARRAS: {codigo_barras}")
        
        c.setFont("Helvetica-BoldOblique", 13)
        c.drawCentredString(x + w/2, y + 9*mm, f"CÓDIGO INTERNO: {cod_interno or '---'}")
        
def api_gerar_pdf_etiquetas(request):
    """ Recebe a fila de impressão e gera o PDF final fatiado em A4 usando ReportLab """
    if request.method == 'POST':
        try:
            import json
            import io
            from django.http import HttpResponse
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm

            payload = request.POST.get('payload')
            if payload:
                dados = json.loads(payload)
            else:
                dados = json.loads(request.body)
                
            modelo = dados.get('modelo', 'PEQUENO')
            produtos_req = dados.get('produtos', [])

            fila = []
            for p in produtos_req:
                qtd = int(p.get('qtd', 1))
                for _ in range(qtd):
                    fila.append(p)

            if not fila:
                return HttpResponse("Fila vazia", status=400)

            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width_a4, height_a4 = A4

            if modelo == 'PEQUENO':
                lbl_w, lbl_h = 50*mm, 40*mm
                cols, rows = 4, 7  
            elif modelo == 'MEDIO':
                lbl_w, lbl_h = 100*mm, 60*mm
                cols, rows = 2, 4  
            else: 
                lbl_w, lbl_h = 190*mm, 277*mm
                cols, rows = 1, 1  

            margin_x = (width_a4 - (cols * lbl_w)) / 2.0
            margin_y = (height_a4 - (rows * lbl_h)) / 2.0

            idx_fila = 0
            
            while idx_fila < len(fila):
                for r in range(rows):
                    for col in range(cols):
                        if idx_fila >= len(fila):
                            break
                        
                        produto = fila[idx_fila]
                        x = margin_x + (col * lbl_w)
                        y = height_a4 - margin_y - ((r + 1) * lbl_h) 

                        desenhar_etiqueta(c, x, y, lbl_w, lbl_h, produto, modelo)
                        idx_fila += 1
                        
                    if idx_fila >= len(fila):
                        break
                
                if idx_fila < len(fila):
                    c.showPage() 
            
            c.save()
            buffer.seek(0)
            
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="etiquetas_{modelo.lower()}_JB.pdf"'
            return response
            
        except Exception as e:
            from django.http import JsonResponse
            return JsonResponse({'status': 'erro', 'mensagem': str(e)})
            
    from django.http import JsonResponse
    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido.'})
