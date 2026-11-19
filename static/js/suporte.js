document.addEventListener("DOMContentLoaded", function () {
    const btnAbrir = document.getElementById("btnFlutuanteSuporte");
    const janelaChat = document.getElementById("janelaChatSuporte");
    const btnFechar = document.getElementById("btnFecharSuporte");
    const btnLimpar = document.getElementById("btnLimparSuporte");
    const formChat = document.getElementById("formChatSuporte");
    const inputPergunta = document.getElementById("inputPerguntaSuporte");
    const corpoMensagens = document.getElementById("corpoMensagensSuporte");

    if (!btnAbrir || !janelaChat) return;

    const STORAGE_KEY = "tecvarejo_suporte_historico";
    const ESTADO_KEY = "tecvarejo_suporte_aberto";

    let historico = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "[]");

    // Converte Markdown simples (**negrito**, quebras de linha e rotas /xxx/) em HTML clicável
    function formatarTextoIA(texto) {
        let html = texto
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Negrito **texto**
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

        // Transforma rotas internas como /estoquepainel/acerto-estoque/ em links clicáveis
        html = html.replace(/(^|\s|\()(\/[a-zA-Z0-9_\-\/]+)(?=[\s\)\.,;!?]|$)/g, function (match, prefixo, rota) {
            if (rota.length < 3 || rota.startsWith("//")) return match;
            return `${prefixo}<a href="${rota}" class="fw-bold text-decoration-underline" style="color: #1565C0;" title="Ir para esta tela">${rota} <i class="bi bi-box-arrow-up-right small"></i></a>`;
        });

        // Quebras de linha
        html = html.replace(/\n/g, "<br>");
        return html;
    }

    function adicionarBalao(autor, texto, salvar = true) {
        const divWrapper = document.createElement("div");
        divWrapper.className = autor === "usuario"
            ? "d-flex justify-content-end mb-2"
            : "d-flex justify-content-start mb-2";

        const balao = document.createElement("div");
        balao.className = "p-2 px-3 rounded-3 shadow-sm";
        balao.style.maxWidth = "85%";
        balao.style.fontSize = "0.88rem";
        balao.style.lineHeight = "1.4";

        if (autor === "usuario") {
            balao.style.backgroundColor = "#1565C0";
            balao.style.color = "#FFFFFF";
            balao.textContent = texto;
        } else {
            balao.style.backgroundColor = "#FFFFFF";
            balao.style.color = "#0D1B4C";
            balao.style.border = "1px solid #dee2e6";
            balao.innerHTML = formatarTextoIA(texto);
        }

        divWrapper.appendChild(balao);
        corpoMensagens.appendChild(divWrapper);
        corpoMensagens.scrollTop = corpoMensagens.scrollHeight;

        if (salvar) {
            historico.push({ autor, texto });
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(historico));
        }
    }

    function renderizarHistoricoInicial() {
        corpoMensagens.innerHTML = "";
        adicionarBalao(
            "ia",
            "Olá! Sou o **Assistente TecVarejo 24h**. Como posso ajudar você hoje? *(Ex: Como acertar o estoque de um produto?)*",
            false
        );
        historico.forEach(item => adicionarBalao(item.autor, item.texto, false));
    }

    function mostrarDigitando() {
        const div = document.createElement("div");
        div.id = "indicadorDigitandoIA";
        div.className = "d-flex justify-content-start mb-2";
        div.innerHTML = `
            <div class="p-2 px-3 rounded-3 bg-white border text-muted small fst-italic shadow-sm">
                <span class="spinner-border spinner-border-sm text-info me-1" role="status"></span>
                Consultando manual do sistema...
            </div>
        `;
        corpoMensagens.appendChild(div);
        corpoMensagens.scrollTop = corpoMensagens.scrollHeight;
    }

    function removerDigitando() {
        const el = document.getElementById("indicadorDigitandoIA");
        if (el) el.remove();
    }

    // Abrir / Fechar janela
    btnAbrir.addEventListener("click", function () {
        const estaOculto = janelaChat.classList.contains("d-none");
        if (estaOculto) {
            janelaChat.classList.remove("d-none");
            sessionStorage.setItem(ESTADO_KEY, "true");
            inputPergunta.focus();
            corpoMensagens.scrollTop = corpoMensagens.scrollHeight;
        } else {
            janelaChat.classList.add("d-none");
            sessionStorage.setItem(ESTADO_KEY, "false");
        }
    });

    btnFechar.addEventListener("click", function () {
        janelaChat.classList.add("d-none");
        sessionStorage.setItem(ESTADO_KEY, "false");
    });

    btnLimpar.addEventListener("click", function () {
        historico = [];
        sessionStorage.removeItem(STORAGE_KEY);
        renderizarHistoricoInicial();
    });

    // Envio da pergunta
    formChat.addEventListener("submit", async function (e) {
        e.preventDefault();
        const pergunta = inputPergunta.value.trim();
        if (!pergunta) return;

        inputPergunta.value = "";
        inputPergunta.disabled = true;

        adicionarBalao("usuario", pergunta, true);
        mostrarDigitando();

        try {
            const response = await fetch("/api/suporte-ia/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": window.CSRF_TOKEN_GLOBAL || ""
                },
                body: JSON.stringify({
                    pergunta: pergunta,
                    historico: historico.slice(0, -1)
                })
            });

            const data = await response.json();
            removerDigitando();

            if (data.sucesso) {
                adicionarBalao("ia", data.resposta, true);
            } else {
                adicionarBalao("ia", `⚠️ ${data.erro || "Não foi possível obter resposta."}`, false);
            }
        } catch (err) {
            removerDigitando();
            adicionarBalao("ia", "⚠️ Erro de conexão com o servidor. Verifique sua internet.", false);
        } finally {
            inputPergunta.disabled = false;
            inputPergunta.focus();
        }
    });

    // Inicializa
    renderizarHistoricoInicial();
    if (sessionStorage.getItem(ESTADO_KEY) === "true") {
        janelaChat.classList.remove("d-none");
    }
});
