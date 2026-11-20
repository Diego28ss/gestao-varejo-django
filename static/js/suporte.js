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

    // Injeta CSS da animação de destaque (Highlight Visual na tela)
    if (!document.getElementById("estiloHighlightSuporteIA")) {
        const style = document.createElement("style");
        style.id = "estiloHighlightSuporteIA";
        style.textContent = `
            @keyframes pulsoDestaqueIA {
                0%   { box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.95); transform: scale(1.03); }
                50%  { box-shadow: 0 0 0 14px rgba(255, 193, 7, 0); transform: scale(1.06); }
                100% { box-shadow: 0 0 0 0 rgba(255, 193, 7, 0); transform: scale(1.03); }
            }
            .tecvarejo-destaque-ia {
                outline: 3px solid #FFC107 !important;
                outline-offset: 3px !important;
                animation: pulsoDestaqueIA 1.1s infinite !important;
                position: relative !important;
                z-index: 9999 !important;
                transition: all 0.3s ease !important;
            }
        `;
        document.head.appendChild(style);
    }

    // Procura o botão ou link na tela pelo texto e faz ele piscar por 5 segundos
    function destacarElementoNaTela(textoAlvo) {
        if (!textoAlvo) return;
        const termo = textoAlvo.trim().toLowerCase();
        const candidatos = document.querySelectorAll("button, a, input[type='submit'], .btn");

        for (const el of candidatos) {
            // Ignora elementos dentro do próprio chat de suporte
            if (janelaChat.contains(el) || btnAbrir.contains(el)) continue;

            const textoEl = (el.innerText || el.value || el.title || "").trim().toLowerCase();
            if (textoEl && textoEl.includes(termo) && el.offsetParent !== null) {
                el.scrollIntoView({ behavior: "smooth", block: "center" });
                el.classList.add("tecvarejo-destaque-ia");
                setTimeout(() => {
                    el.classList.remove("tecvarejo-destaque-ia");
                }, 5500);
                break;
            }
        }
    }

    // Converte Markdown simples e extrai comando [[DESTACAR:...]]
    function processarTextoIA(textoBruto) {
        let textoLimpo = textoBruto;
        let alvoDestaque = null;

        const matchDestaque = textoLimpo.match(/\[\[DESTACAR:(.*?)\]\]/i);
        if (matchDestaque) {
            alvoDestaque = matchDestaque[1].trim();
            textoLimpo = textoLimpo.replace(matchDestaque[0], "").trim();
        }

        let html = textoLimpo
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

        html = html.replace(/(^|\s|\()(\/[a-zA-Z0-9_\-\/]+)(?=[\s\)\.,;!?]|$)/g, function (match, prefixo, rota) {
            if (rota.length < 3 || rota.startsWith("//")) return match;
            return `${prefixo}<a href="${rota}" class="fw-bold text-decoration-underline" style="color: #1565C0;" title="Ir para esta tela">${rota} <i class="bi bi-box-arrow-up-right small"></i></a>`;
        });

        html = html.replace(/\n/g, "<br>");
        return { html, alvoDestaque, textoLimpo };
    }

    async function enviarFeedback(logId, voto, containerBotoes) {
        if (!logId) return;
        try {
            await fetch("/api/suporte-ia/feedback/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": window.CSRF_TOKEN_GLOBAL || ""
                },
                body: JSON.stringify({ log_id: logId, voto: voto })
            });
            containerBotoes.innerHTML = voto === "UTIL"
                ? `<span class="text-success small fw-semibold"><i class="bi bi-check-circle-fill"></i> Obrigado pelo feedback!</span>`
                : `<span class="text-muted small"><i class="bi bi-journal-check"></i> Registrado para melhoria do manual.</span>`;
        } catch (e) {
            console.error("Erro ao enviar feedback:", e);
        }
    }

    function adicionarBalao(autor, texto, salvar = true, logId = null, executarDestaque = false) {
        const divWrapper = document.createElement("div");
        divWrapper.className = autor === "usuario"
            ? "d-flex justify-content-end mb-2"
            : "d-flex flex-column align-items-start mb-2";

        const balao = document.createElement("div");
        balao.className = "p-2 px-3 rounded-3 shadow-sm";
        balao.style.maxWidth = "88%";
        balao.style.fontSize = "0.88rem";
        balao.style.lineHeight = "1.4";

        if (autor === "usuario") {
            balao.style.backgroundColor = "#1565C0";
            balao.style.color = "#FFFFFF";
            balao.textContent = texto;
            divWrapper.appendChild(balao);
        } else {
            balao.style.backgroundColor = "#FFFFFF";
            balao.style.color = "#0D1B4C";
            balao.style.border = "1px solid #dee2e6";

            const { html, alvoDestaque, textoLimpo } = processarTextoIA(texto);
            balao.innerHTML = html;
            divWrapper.appendChild(balao);

            if (alvoDestaque && executarDestaque) {
                setTimeout(() => destacarElementoNaTela(alvoDestaque), 300);
            }

            // Barra discreta de feedback 👍 / 👎 quando houver logId
            if (logId) {
                const barraFb = document.createElement("div");
                barraFb.className = "d-flex align-items-center gap-2 mt-1 ps-1";
                barraFb.style.fontSize = "0.75rem";
                barraFb.innerHTML = `
                    <span class="text-muted">Ajudou?</span>
                    <button type="button" class="btn btn-sm py-0 px-1 btn-outline-success border-0 btn-fb-util" title="Sim, ajudou">
                        <i class="bi bi-hand-thumbs-up"></i>
                    </button>
                    <button type="button" class="btn btn-sm py-0 px-1 btn-outline-danger border-0 btn-fb-ruim" title="Não ajudou">
                        <i class="bi bi-hand-thumbs-down"></i>
                    </button>
                `;
                barraFb.querySelector(".btn-fb-util").addEventListener("click", () => enviarFeedback(logId, "UTIL", barraFb));
                barraFb.querySelector(".btn-fb-ruim").addEventListener("click", () => enviarFeedback(logId, "NAO_AJUDOU", barraFb));
                divWrapper.appendChild(barraFb);
            }

            texto = textoLimpo;
        }

        corpoMensagens.appendChild(divWrapper);
        corpoMensagens.scrollTop = corpoMensagens.scrollHeight;

        if (salvar) {
            historico.push({ autor, texto, logId });
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(historico));
        }
    }

    function renderizarHistoricoInicial() {
        corpoMensagens.innerHTML = "";
        adicionarBalao(
            "ia",
            "Olá! Sou o **Assistente TecVarejo 24h**. Posso tirar dúvidas, consultar estoque/pontos ou diagnosticar erros na nota fiscal. Como posso ajudar?",
            false
        );
        historico.forEach(item => adicionarBalao(item.autor, item.texto, false, item.logId || null, false));
    }

    function mostrarDigitando() {
        const div = document.createElement("div");
        div.id = "indicadorDigitandoIA";
        div.className = "d-flex justify-content-start mb-2";
        div.innerHTML = `
            <div class="p-2 px-3 rounded-3 bg-white border text-muted small fst-italic shadow-sm">
                <span class="spinner-border spinner-border-sm text-info me-1" role="status"></span>
                Consultando sistema e base de dados...
            </div>
        `;
        corpoMensagens.appendChild(div);
        corpoMensagens.scrollTop = corpoMensagens.scrollHeight;
    }

    function removerDigitando() {
        const el = document.getElementById("indicadorDigitandoIA");
        if (el) el.remove();
    }

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
                    historico: historico.slice(0, -1),
                    rota_atual: window.location.pathname
                })
            });

            const data = await response.json();
            removerDigitando();

            if (data.sucesso) {
                adicionarBalao("ia", data.resposta, true, data.log_id || null, true);
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

    renderizarHistoricoInicial();
    if (sessionStorage.getItem(ESTADO_KEY) === "true") {
        janelaChat.classList.remove("d-none");
    }
});
