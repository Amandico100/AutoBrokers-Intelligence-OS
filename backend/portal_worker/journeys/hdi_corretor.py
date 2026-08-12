"""Journey HDI Digital — corretor (cobrança).

O que ela faz para a corretora
==============================
Entra no HDI Digital com o login da corretora, lê a tela **Parcela** filtrando
por período de vencimento, separa quem está **em atraso** e baixa a 2ª via do
boleto de cada um. Não envia nada — quem envia é o Auxiliar de Cobrança, depois,
em horário comercial e com o freio de vazão.

O método (SPEC-033), e onde a HDI difere da Allianz
===================================================
A regra de ouro continua: **falar a mesma língua que a tela fala por baixo, em
vez de clicar nela.** O que muda é o dialeto.

    Allianz     BFF moderno, JSON, Bearer JWT
    HDI         app legado, HTML iso-8859-1, sessão por query param

📊 Medido nas capturas do founder (10/08/2026). A cadeia tem 4 passos:

    1) POST /digital2/legado/dsp_parcelas_busca_2008/1/9?chaveUsuario=&tokenSec=
       devolve um <form> auto-submit com a IDENTIDADE do corretor:
       m_cod_corretor · m_cod_sucursal · c_pc · l_s · n_s · m_cpf_prdtor · tokenSec

    2) POST /web/hdidigital/dsp_parcelas_busca_2008.htm   (com esses campos)
       abre a tela de busca no app legado

    3) POST /web/hdidigital/dsp_parcelas_view_2008.htm
       + data_ini / data_fim / s_tipo  ->  A LISTA DE PARCELAS (HTML)

    4) o link "2ª via" de cada linha  ->  dsp_boleto.htm?p=<hash>
                                      ->  boletoPDF.jsp?...  ->  O PDF

Por que os passos 1 e 2 não podem ser pulados
---------------------------------------------
`c_pc`, `m_cod_corretor` e as sucursais **não são fixos** — 📊 o mesmo corretor
apareceu com `c_pc=K659709550002_4420` num passo e `G667095500029_4420` no
seguinte. São estado de sessão emitido pelo servidor. Chutar qualquer um deles é
o tipo de atalho que funciona no teste e falha no dia 3. Colhemos do HTML.

Débito automático não tem boleto — e isso é regra de negócio, não bug
---------------------------------------------------------------------
📊 Na captura, a única parcela EM ATRASO era débito automático, e a coluna
`Gerar` dizia *"Parcela diferente de Boleto Bancário."* em vez de *"2ª via"*.
Converter débito em boleto na HDI está atrás de **ALTERAÇÕES FINANCEIRAS**, que
escreve no contrato do segurado — proibido (§ `ACOES_PROIBIDAS`).

Então esse inadimplente sai da varredura **marcado**, com `sem_boleto` e o
motivo. Ele entra no relatório e no handoff; não vira silêncio nem falha.
"""
from __future__ import annotations

import base64
import html as html_lib
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, parse_qsl

from portal_worker.journeys import JourneyResult

HDI_LOGIN_URL = "https://www.hdi.com.br/hdidigital/"
HDI_HOME = "https://www.hdi.com.br/digital2/home"
HDI_BASE = "https://www.hdi.com.br"

# Passo 1 da cadeia. O `/1/9` é fixo: 9 = opção de menu "Parcela"
# (`m_cod_opcao_menu_2008=9` no form devolvido).
HDI_BRIDGE_PARCELAS = "/digital2/legado/dsp_parcelas_busca_2008/1/9"
HDI_BUSCA_PARCELAS = "/web/hdidigital/dsp_parcelas_busca_2008.htm"
HDI_VIEW_PARCELAS = "/web/hdidigital/dsp_parcelas_view_2008.htm"

# Campo "Tipo de Parcelas". 📊 Lido do <select> real do portal (12/08/2026)::
#
#     <option value="0">Todas</option>
#     <option value="1" selected>A vencer</option>
#     <option value="2">Quitadas</option>
#     <option value="3">Atrasadas</option>
#     <option value="4">Canceladas</option>
#
# **3 = Atrasadas.** O padrão da TELA é 1 (A vencer) — e era esse o valor que eu
# estava mandando, o que devolvia justamente quem NÃO interessa. Adivinhar o
# número custou uma rodada inteira; o `<select>` responde em três segundos.
S_TIPO_ATRASADAS = "3"
S_TIPO_TODAS = "0"

# Limite de período do portal. 📊 Lido da validação do próprio botão Buscar:
#     if (dat_final - dat_inicial > 2583600000) alert("Período não pode ser
#         superior a 30 dias...")
# 2.583.600.000 ms = 29,9 dias. Uma janela de 365 dias — que era o meu padrão —
# seria recusada. Varremos em BLOCOS de 30 dias.
JANELA_MAX_DIAS = 30

# Marca de "esta parcela não gera boleto". 📊 Vale para Débito E Crédito: a
# coluna `Gerar` traz esta frase no lugar do link em ambos. Casar por forma de
# pagamento deixaria o Crédito passar como se tivesse boleto.
MARCA_SEM_BOLETO = "parcela diferente de boleto"

# Botões que ESCREVEM no contrato do segurado. A journey nunca os toca, e o
# teste prova que nenhum deles aparece no código de clique.
ACOES_PROIBIDAS = (
    "REPROGRAMACAO DE PARCELA",
    "TERMO DE ADIMPLENCIA",
    "ANTECIPACAO DE PARCELAS",
    "ALTERACOES FINANCEIRAS",
)

_RE_DOCUMENTO = re.compile(r"\b(\d{2}\.\d{3}\.\d{3}\.\d{6}\.\d{6})\b")
_RE_PARCELA = re.compile(r"(\d{1,3})\s*de\s*(\d{1,3})", re.IGNORECASE)
_RE_DATA = re.compile(r"\b(\d{2}/\d{2}/\d{2,4})\b")
_RE_TAG = re.compile(r"<[^>]+>")
_RE_LINHA = re.compile(r"<tr\b.*?</tr>", re.IGNORECASE | re.DOTALL)
_RE_CELULA = re.compile(r"<t[dh]\b.*?</t[dh]>", re.IGNORECASE | re.DOTALL)
_RE_INPUT = re.compile(r"<input\b[^>]*>", re.IGNORECASE)
_RE_ATTR = re.compile(r"""(\w[\w:-]*)\s*=\s*["']([^"']*)["']""")
_RE_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


# --------------------------------------------------------------------------
# texto e números (locais de propósito — a biblioteca comum nasce quando DOIS
# portais comprovadamente usarem a mesma peça, não antes)
# --------------------------------------------------------------------------

def _norm(value: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(texto.split())


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _clean_text(value: Any) -> str:
    """Texto limpo, com as entidades HTML resolvidas.

    O app legado da HDI e iso-8859-1 e mistura acento cru com entidade
    (`D&eacute;bito`). Sem resolver, `_norm` nao acha "debito" e a parcela em
    debito automatico passa por boleto — que e exatamente o caso que precisa
    ser marcado. Por isso `html.unescape`, e nao uma lista de trocas.
    """
    texto = html_lib.unescape(str(value or "")).replace("\xa0", " ")
    return " ".join(texto.split())


def _sem_tags(html: str) -> str:
    return _clean_text(_RE_TAG.sub(" ", str(html or "")))


def _money_br(value: Any) -> Optional[float]:
    texto = re.sub(r"[^0-9,.-]", "", str(value or "").strip())
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return round(float(texto), 2)
    except ValueError:
        return None


def _data_iso(value: Any) -> str:
    """dd/mm/aa ou dd/mm/aaaa -> aaaa-mm-dd. Vazio quando não reconhece."""
    m = _RE_DATA.search(str(value or ""))
    if not m:
        return ""
    dia, mes, ano = m.group(1).split("/")
    if len(ano) == 2:
        ano = f"20{ano}"
    try:
        return datetime(int(ano), int(mes), int(dia)).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _hoje() -> datetime:
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))


# --------------------------------------------------------------------------
# parsers puros — testáveis sem navegador (é por isso que o fetch devolve texto
# e a leitura acontece aqui, e não dentro de um evaluate no browser)
# --------------------------------------------------------------------------

def extrair_campos_do_form(html: str) -> Dict[str, str]:
    """Colhe os <input hidden> do form auto-submit do passo 1.

    São a identidade da sessão (código do corretor, sucursal, c_pc, tokenSec).
    Nenhum deles é fixo — por isso colhemos em vez de fixar.
    """
    campos: Dict[str, str] = {}
    for tag in _RE_INPUT.findall(str(html or "")):
        attrs = {k.lower(): v for k, v in _RE_ATTR.findall(tag)}
        nome = attrs.get("name")
        if nome:
            campos[nome] = _clean_text(attrs.get("value", ""))
    return campos


def _celulas(linha_html: str) -> List[str]:
    return [_sem_tags(c) for c in _RE_CELULA.findall(linha_html)]


_RE_WINDOW_OPEN = re.compile(r"""window\.open\s*\(\s*['"]([^'"]*dsp_boleto[^'"]*)['"]""", re.IGNORECASE)


def _link_segunda_via(linha_html: str) -> str:
    """O alvo da 2ª via.

    📊 Na HDI **não existe `<a href>` para o boleto.** A célula `Gerar` é um
    `<td>` com::

        onclick="alerta_conjugado('');window.open('dsp_boleto.htm?p=<hash>', ...)"

    Procurar por `href` — que era o que esta função fazia — não acha nada, mesmo
    com a tabela lida corretamente. É preciso ler de dentro do `onclick`.

    E só o alvo do BOLETO é aceito. As outras células da mesma linha têm
    `onclick` para `reprogParcela`, `termoAdimplencia`, `checkAntecipa` e
    `checkAlterar` — os quatro que escrevem no contrato do segurado. Um
    casamento frouxo aqui seria o robô apertando um deles.
    """
    m = _RE_WINDOW_OPEN.search(str(linha_html or ""))
    alvo = _clean_text(html_lib.unescape(m.group(1))) if m else ""
    if not alvo:
        for href in _RE_HREF.findall(str(linha_html or "")):
            candidato = _clean_text(href)
            if "dsp_boleto" in candidato.lower():
                alvo = candidato
                break
    if not alvo:
        return ""
    if alvo.startswith("http"):
        return alvo
    if alvo.startswith("/"):
        return HDI_BASE + alvo
    # Caminho relativo: a tela legada mora em /web/hdidigital/
    return f"{HDI_BASE}/web/hdidigital/{alvo.lstrip('/')}"


def extrair_parcelas(html: str) -> List[Dict[str, Any]]:
    """Lê a tabela da tela Parcela.

    Casa por CONTEÚDO (documento, data, dinheiro, posição), não por posição de
    coluna nem por classe CSS: a HDI reordenar ou renomear coluna não quebra a
    leitura, e é a diferença entre um robô que sobrevive a um redesenho e um
    que precisa de gente toda vez.
    """
    out: List[Dict[str, Any]] = []
    vistos = set()
    for linha_html in _RE_LINHA.findall(str(html or "")):
        cels = [c for c in _celulas(linha_html) if c]
        if not cels:
            continue
        blob = " ".join(cels)
        doc = _RE_DOCUMENTO.search(blob)
        if not doc:
            continue  # cabeçalho, rodapé, legenda, linha de botões

        documento = doc.group(1)
        parcela_num = parcela_total = ""
        celula_doc = next((c for c in cels if documento in c), blob)
        mp = _RE_PARCELA.search(celula_doc)
        if mp:
            parcela_num, parcela_total = mp.group(1), mp.group(2)

        low = _norm(blob)
        em_atraso = "em atraso" in low
        posicao = "Parcela em Atraso" if em_atraso else ("Parcela a Vencer" if "a vencer" in low else "")

        # A 1ª data da linha é o vencimento; 'Limite sem Vistoria' vem depois.
        datas = _RE_DATA.findall(celula_doc) or _RE_DATA.findall(blob)
        vencimento = _data_iso(datas[0]) if datas else ""

        valor = None
        for c in cels:
            if c == celula_doc or _RE_DOCUMENTO.search(c):
                continue
            if re.fullmatch(r"[\d.]+,\d{2}", c.strip()):
                valor = _money_br(c)
                break

        cliente = ""
        for c in cels:
            texto = _clean_text(c)
            if len(texto) < 4 or _RE_DOCUMENTO.search(texto) or _RE_DATA.search(texto):
                continue
            if re.fullmatch(r"[\d.,\s]+", texto) or _norm(texto) in ("boleto", "debito"):
                continue
            if _norm(texto).startswith(("parcela ", "cobertura proporcional")):
                continue
            cliente = texto
            break

        # Forma de pagamento: a célula que traz exatamente uma destas palavras.
        # 📊 Vistas no HTML real: Boleto · Débito · Crédito.
        forma = ""
        for c in cels:
            n = _norm(c)
            if n in ("boleto", "debito", "credito", "debito em conta", "cartao de credito"):
                forma = n.split()[0]
                break

        link = _link_segunda_via(linha_html)
        if link:
            sem_boleto = ""
        elif MARCA_SEM_BOLETO in low:
            # A frase da própria HDI. Vale para Débito E Crédito — por isso o
            # motivo cita a forma lida, e não assume "débito".
            sem_boleto = (f"pagamento em {forma or 'forma diferente de boleto'} — "
                          "a HDI nao emite 2a via de boleto para esta parcela")
        else:
            sem_boleto = "linha sem link de 2a via"

        chave = (documento, parcela_num, vencimento)
        if chave in vistos:
            continue
        vistos.add(chave)

        out.append({
            "portal": "hdi_corretor",
            "documento": documento,
            "apolice_susep": _digits(documento),
            "recibo": f"{_digits(documento)}-{parcela_num or '0'}",
            "parcela": f"{parcela_num}/{parcela_total}" if parcela_num else "",
            "vencimento": vencimento,
            "valor": valor,
            "cliente_nome": cliente,
            "cpf_cnpj": "",  # a tela Parcela não traz documento do segurado
            "posicao": posicao,
            "em_atraso": em_atraso,
            "forma_pagamento": forma,
            "link_segunda_via": link,
            "sem_boleto_motivo": sem_boleto,
        })
    return out


def esta_processando(html: str) -> bool:
    """A HDI ainda está montando o resultado?

    📊 O PRIMEIRO POST da busca **nunca** devolve a tabela. Ele devolve::

        <p class="txt" title="Req:1331319740-Processando:1331272048">
           Por favor aguarde. Estamos processando a requisicao...</p>
        <script>tempo = setTimeout("document.f_requisicao.submit();",5000);</script>

    ...e um formulário `f_requisicao` que se reenvia sozinho 5 segundos depois.
    **É o reenvio que traz as parcelas.**

    Foi exatamente isto que fez a primeira tentativa ler zero linhas e quase
    concluir "nenhum inadimplente": o corpo tinha 4 KB, HTTP 200, tudo com cara
    de sucesso — e era a sala de espera.
    """
    baixo = _norm(_sem_tags(html))
    return "estamos processando a requisicao" in baixo or "por favor aguarde" in baixo


def formulario_de_reenvio(html: str) -> Dict[str, str]:
    """Os campos do `f_requisicao` — o que precisa ser reenviado para colher.

    Reenviar é literalmente o que o navegador faria; só não esperamos os 5 s
    ociosos do `setTimeout`, porque quem controla o ritmo aqui somos nós.
    """
    m = re.search(r"<form[^>]*name=[\"']f_requisicao[\"'].*?</form>", str(html or ""),
                  re.IGNORECASE | re.DOTALL)
    return extrair_campos_do_form(m.group(0)) if m else {}


def apenas_atrasados(parcelas: List[Dict[str, Any]], *, horas_minimas: int = 48,
                     agora: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Os que podem ser cobrados: em atraso **e** vencidos há mais que N horas.

    A carência existe porque boleto pago não baixa na hora — cobrar quem pagou
    ontem queima a corretora com o próprio cliente. 48 h é o padrão do produto.

    A ordem é do mais antigo para o mais novo: a dívida mais velha é a que corre
    mais risco de cancelamento, então é a primeira a sair.
    """
    agora = agora or _hoje()
    corte = (agora - timedelta(hours=int(horas_minimas))).strftime("%Y-%m-%d")
    elegiveis = [
        p for p in parcelas
        if p.get("em_atraso") and p.get("vencimento") and str(p["vencimento"]) <= corte
    ]
    return sorted(elegiveis, key=lambda p: (str(p.get("vencimento") or ""), str(p.get("documento") or "")))


def janelas_de_vencimento(*, dias_atras: int = 90, horas_minimas: int = 48,
                          agora: Optional[datetime] = None) -> List[Dict[str, str]]:
    """Os períodos a pesquisar, em blocos que o portal aceita.

    📊 A HDI recusa período maior que 30 dias — está na validação do próprio
    botão Buscar (`dat_final - dat_inicial > 2583600000`). Meu padrão anterior
    era 365 dias numa tacada, e teria sido recusado.

    A regra das 48 h vira o FIM do período mais recente: a carência passa a ser
    aplicada pelo próprio portal, e não só depois, na nossa peneira.

    Devolve do mais ANTIGO para o mais recente, para a fila de cobrança já sair
    na ordem certa sem depender de ordenação posterior.
    """
    agora = agora or _hoje()
    fim = agora - timedelta(hours=int(horas_minimas))
    inicio_total = agora - timedelta(days=int(dias_atras))
    blocos: List[Dict[str, str]] = []
    cursor = fim
    while cursor > inicio_total and len(blocos) < 24:  # teto de sanidade
        ini = max(inicio_total, cursor - timedelta(days=JANELA_MAX_DIAS - 1))
        blocos.append({"data_ini": ini.strftime("%d/%m/%Y"),
                       "data_fim": cursor.strftime("%d/%m/%Y")})
        cursor = ini - timedelta(days=1)
    return list(reversed(blocos))


def janela_de_vencimento(*, dias_atras: int = 30, horas_minimas: int = 48,
                         agora: Optional[datetime] = None) -> Dict[str, str]:
    """O bloco mais recente. Mantida porque é o caso de uma varredura só."""
    blocos = janelas_de_vencimento(dias_atras=min(int(dias_atras), JANELA_MAX_DIAS),
                                   horas_minimas=horas_minimas, agora=agora)
    return blocos[-1] if blocos else {"data_ini": "", "data_fim": ""}


def build_boleto_storage_path(*, company_id: str, job_id: str, portal_key: str,
                              recibo: str = "", **_ignorado: Any) -> str:
    """Caminho privado do boleto. Nome do segurado e CPF NUNCA entram no path."""
    def _tok(v: Any, padrao: str) -> str:
        t = re.sub(r"[^a-z0-9_-]+", "-", _norm(v)).strip("-")
        return t[:80] or padrao
    return (f"{_tok(company_id, 'company')}/{_tok(portal_key, 'portal')}/"
            f"{_tok(job_id, 'job')}/boleto-{_tok(recibo, 'boleto')}.pdf")


# --------------------------------------------------------------------------
# navegação
# --------------------------------------------------------------------------

_FALHA_LOGIN = ("usuario ou senha", "senha invalida", "usuario invalido",
                "credenciais invalidas", "dados incorretos", "nao autorizado",
                "acesso negado")
_HITL = ("captcha", "codigo de verificacao", "codigo de seguranca", "token de acesso",
         "otp", "autenticacao em duas etapas", "duas etapas", "2fa", "mfa")
_SINAIS_LOGADO = ("ola,", "sair", "nova cotacao", "quadro de avisos", "ultimas cotacoes",
                  "bem vindo a hdi", "bem-vindo ao hdi digital", "parcela", "renovacao")


def interpret_login(page_text: str, url: str = "") -> JourneyResult:
    """Classifica a tela pós-login sem nunca expor credencial."""
    texto = _norm(page_text)
    if any(t in texto for t in _FALHA_LOGIN):
        return JourneyResult(status="failed", message="credenciais rejeitadas pelo portal HDI")
    if any(t in texto for t in _HITL):
        return JourneyResult(status="needs_human", message="portal HDI pediu CAPTCHA/2FA")
    if "chaveusuario=" in _norm(url) or sum(1 for t in _SINAIS_LOGADO if t in texto) >= 2:
        return JourneyResult(status="done", captured={"logged_in": True, "portal": "hdi_corretor"})
    return JourneyResult(status="needs_human", message="tela pos-login HDI nao reconhecida")


def credenciais_de_sessao(url: str) -> Dict[str, str]:
    """`chaveUsuario` e `tokenSec` viajam na URL do portal (não é JWT).

    Só os NOMES aparecem em log/evidência; os valores ficam em memória.
    """
    out: Dict[str, str] = {}
    try:
        for chave, valor in parse_qsl(urlsplit(str(url or "")).query, keep_blank_values=False):
            if chave.lower() in ("chaveusuario", "tokensec") and valor:
                out[chave] = valor
    except Exception:  # noqa: BLE001
        return {}
    return out


async def _texto(page) -> str:
    try:
        return await page.inner_text("body", timeout=6000)
    except Exception:  # noqa: BLE001
        return ""


async def _fetch(page, url: str, *, metodo: str = "GET", corpo: str = "") -> Dict[str, Any]:
    """Chama o portal de DENTRO da página (mesma origem, cookies da sessão).

    Devolve texto — a leitura acontece em Python, onde dá para testar com
    fixture e sem navegador.
    """
    try:
        return await page.evaluate(
            """async ({url, metodo, corpo}) => {
              const init = {method: metodo, credentials: 'include', headers: {}};
              if (metodo === 'POST') {
                init.headers['Content-Type'] = 'application/x-www-form-urlencoded';
                init.body = corpo || '';
              }
              const r = await fetch(url, init);
              let t = '';
              try { t = await r.text(); } catch (e) { t = ''; }
              return {ok: r.ok, status: r.status, url: r.url, text: t};
            }""",
            {"url": url, "metodo": metodo, "corpo": corpo},
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": 0, "text": "", "erro": type(exc).__name__}


def _urlencode(campos: Dict[str, Any]) -> str:
    from urllib.parse import urlencode as _ue
    return _ue({k: ("" if v is None else str(v)) for k, v in campos.items()})


async def login_check(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """Login HDI Digital com a credencial de `portal_accounts`."""
    usuario = str(params.get("username") or "").strip()
    senha = str(params.get("password") or "")
    if not usuario or not senha:
        return JourneyResult(status="failed", message="username/password ausentes para HDI")

    await page.goto(str(params.get("login_url") or HDI_LOGIN_URL), wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)
    # O Akamai da HDI recusa o headless CLASSICO com "Access Denied" (📊 medido,
    # ver `worker._launch_kwargs`). Se cair aqui, o diagnostico precisa dizer
    # ISSO, e nao "campos de login nao encontrados" — que manda quem for depurar
    # procurar no lugar errado.
    if "access denied" in _norm(await _texto(page)):
        return JourneyResult(
            status="failed",
            message=("portal HDI recusou o navegador (Akamai 'Access Denied') — "
                     "o worker precisa de PORTAL_HEADLESS_MODE=new"),
        )

    if params.get("session_loaded"):
        atual = interpret_login(await _texto(page), getattr(page, "url", ""))
        if atual.status == "done" and not params.get("force_login"):
            evidence["session_reused"] = True
            evidence["hdi_sessao"] = sorted(credenciais_de_sessao(getattr(page, "url", "")))
            return atual

    # A tela de login da HDI tem DUAS camadas (📊 medido em 10/08/2026):
    #
    #   j_username / j_password ...... os campos REAIS do form (0x0, invisiveis)
    #   dois inputs SEM id e SEM name  o que o corretor enxerga e digita (295x40)
    #
    # Casar por id/name nao acha o campo visivel (ele nao tem nenhum dos dois), e
    # preencher so o escondido pode ser sobrescrito pelo JS da propria tela no
    # submit. Preenchemos as DUAS camadas: a visivel porque e o caminho que a
    # pagina espera, a escondida porque e o que o servidor le.
    #
    # E esperamos o campo visivel APARECER antes de digitar: com `wait 2s` fixo,
    # a tela ainda nao tinha montado e o robo concluia "campos nao encontrados"
    # — um falso negativo que parecia bloqueio de portal.
    try:
        await page.wait_for_function(
            "() => [...document.querySelectorAll('input')]"
            ".some(i => i.type === 'password' && i.getBoundingClientRect().width > 40)",
            timeout=int(params.get("form_timeout_ms") or 25000),
        )
    except Exception:  # noqa: BLE001
        pass

    preenchido = await page.evaluate(
        """({usuario, senha}) => {
          const grande = el => el.getBoundingClientRect().width > 40;
          const set = (el, v) => {
            if (!el) return false;
            const proto = (el.type || '').toLowerCase() === 'password'
              ? window.HTMLInputElement.prototype : window.HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
            try { el.focus(); } catch (e) {}
            if (setter) setter.call(el, v); else el.value = v;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            el.dispatchEvent(new Event('blur', {bubbles: true}));
            return true;
          };
          const todos = [...document.querySelectorAll('input')];
          const visiveis = todos.filter(grande);
          const passVis = visiveis.find(i => (i.type || '').toLowerCase() === 'password');
          const userVis = visiveis.find(i => (i.type || '').toLowerCase() !== 'password');
          // camada visivel — o caminho do corretor
          const u1 = set(userVis, usuario);
          const p1 = set(passVis, senha);
          // camada real — o que o servidor le (j_security_check classico)
          const u2 = set(todos.find(i => /j_username|cod_produtor/i.test(i.name || i.id || '')), usuario);
          const p2 = set(todos.find(i => /j_password/i.test(i.name || i.id || '')), senha);
          return {user: !!(u1 || u2), pass: !!(p1 || p2),
                  camada_visivel: !!(u1 && p1), camada_real: !!(u2 && p2)};
        }""",
        {"usuario": usuario, "senha": senha},
    )
    evidence["login_fields_found"] = preenchido
    if not (preenchido.get("user") and preenchido.get("pass")):
        return JourneyResult(status="needs_human", message="campos de login HDI nao encontrados")

    enviado = await page.evaluate(
        """() => {
          const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
          const norm = s => (s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
          const btns = [...document.querySelectorAll('button,input[type=submit],a')].filter(vis);
          const alvo = btns.find(b => /entrar|acessar|login|confirmar/.test(norm(b.innerText || b.value)));
          if (alvo) { alvo.click(); return true; }
          const form = document.querySelector('form');
          if (form) { form.submit(); return true; }
          return false;
        }"""
    )
    if not enviado:
        return JourneyResult(status="needs_human", message="botao de login HDI nao encontrado")

    try:
        await page.wait_for_url("**chaveUsuario=**", timeout=int(params.get("login_timeout_ms") or 45000))
    except Exception:  # noqa: BLE001
        pass
    await page.wait_for_timeout(2500)
    try:
        await page.wait_for_load_state("networkidle", timeout=12000)
    except Exception:  # noqa: BLE001
        pass

    url_atual = getattr(page, "url", "")
    sessao = credenciais_de_sessao(url_atual)
    evidence["hdi_sessao"] = sorted(sessao)  # só os NOMES das chaves
    evidence["url"] = re.sub(r"(?i)(chaveUsuario|tokenSec)=[^&]+", r"\1=<omitido>", url_atual)[:300]
    return interpret_login(await _texto(page), url_atual)


async def abrir_tela_parcelas(page, evidence: Dict[str, Any]) -> Dict[str, str]:
    """Passos 1 e 2: atravessa a ponte do shell novo para o app legado e colhe
    a identidade da sessão. Devolve os campos do formulário."""
    sessao = credenciais_de_sessao(getattr(page, "url", ""))
    if not sessao:
        await page.goto(HDI_HOME, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        sessao = credenciais_de_sessao(getattr(page, "url", ""))
    if not sessao:
        evidence.setdefault("notas", []).append("nao achei chaveUsuario/tokenSec na URL da sessao")
        return {}

    ponte = f"{HDI_BRIDGE_PARCELAS}?{_urlencode(sessao)}"
    r1 = await _fetch(page, ponte, metodo="POST")
    evidence["hdi_passo1"] = {"status": r1.get("status"), "bytes": len(r1.get("text") or "")}
    campos = extrair_campos_do_form(r1.get("text") or "")
    if not campos:
        evidence.setdefault("notas", []).append("passo 1 nao devolveu o formulario de identidade")
        return {}

    r2 = await _fetch(page, HDI_BUSCA_PARCELAS, metodo="POST", corpo=_urlencode(campos))
    evidence["hdi_passo2"] = {"status": r2.get("status"), "bytes": len(r2.get("text") or "")}
    # Marca só o que NÃO é segredo — nunca tokenSec/chaveUsuario.
    evidence["hdi_identidade"] = {
        k: campos.get(k, "") for k in
        ("m_cod_corretor", "m_cod_sucursal", "n_s", "m_cod_opcao_menu_2008", "c_pc")
    }
    return campos


async def listar_parcelas(page, campos: Dict[str, str], *, data_ini: str, data_fim: str,
                          s_tipo: str, evidence: Dict[str, Any],
                          tentativas_reenvio: int = 6) -> List[Dict[str, Any]]:
    """Passo 3: a busca — que são DUAS chamadas, não uma.

        POST com os critérios  ->  "aguarde, processando" + form f_requisicao
        POST do f_requisicao   ->  a tabela

    Sem a segunda, o parser lê uma sala de espera e conclui que não há
    inadimplente. É o defeito mais perigoso que este arquivo teve, porque
    falhava dizendo `done`.
    """
    corpo = {
        "isRevamp": "true",
        "m_cod_opcao_menu_2008": campos.get("m_cod_opcao_menu_2008") or "9",
        "t_prd": campos.get("t_prd") or "C",
        "t_prd_orig": campos.get("t_prd_orig") or "C",
        "c_pc": campos.get("c_pc") or "",
        "c_pc_orig": campos.get("c_pc_orig") or campos.get("c_pc") or "",
        "cpf_usuario": campos.get("m_cpf_prdtor") or campos.get("m_nome_user_web") or "",
        "m_cpf_prdtor": campos.get("m_cpf_prdtor") or "",
        "l_s": campos.get("l_s") or campos.get("m_cod_sucursal") or "",
        "n_s": campos.get("n_s") or "",
        "s_cod_sucursal": campos.get("m_cod_sucursal") or campos.get("l_s") or "",
        "m_empresa": "01",
        "tokenSec": campos.get("tokenSec") or "",
        "m_pag_anterior": "hdidigital/dsp_parcelas_busca_2008.htm",
        "m_frame_hdidigital": "1",
        "versao_login": "", "m_nm_dbname": "",
        "cod_empresa": "", "cod_sucursal": "", "cod_carteira": "", "seq_docum": "",
        "m_numapolicesusep": "", "nome": "", "cpf": "", "cnpj": "", "placa": "", "chassi": "",
        "data_ini": data_ini,
        "data_fim": data_fim,
        "s_tipo": str(s_tipo),
    }
    r = await _fetch(page, HDI_VIEW_PARCELAS, metodo="POST", corpo=_urlencode(corpo))
    html = r.get("text") or ""
    reenvios = 0

    # A sala de espera. O portal manda o navegador reenviar em 5s; nós fazemos o
    # mesmo, com uma folga menor — e desistimos depois de N voltas em vez de
    # ficar preso, porque um `while` sem teto num portal é como se derruba um.
    while esta_processando(html) and reenvios < int(tentativas_reenvio):
        reenvio = formulario_de_reenvio(html)
        if not reenvio:
            break
        await page.wait_for_timeout(2500)
        r = await _fetch(page, HDI_VIEW_PARCELAS, metodo="POST", corpo=_urlencode(reenvio))
        html = r.get("text") or ""
        reenvios += 1

    parcelas = extrair_parcelas(html)
    evidence.setdefault("hdi_buscas", []).append({
        "s_tipo": str(s_tipo), "data_ini": data_ini, "data_fim": data_fim,
        "status": r.get("status"), "bytes": len(html), "linhas": len(parcelas),
        "reenvios": reenvios,
        "ainda_processando": esta_processando(html),
        "em_atraso": sum(1 for p in parcelas if p.get("em_atraso")),
    })
    return parcelas


async def baixar_boleto(page, item: Dict[str, Any], params: Dict[str, Any],
                        evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Passo 4: segue o link da 2ª via até o PDF e guarda no bucket privado."""
    link = str(item.get("link_segunda_via") or "").strip()
    if not link:
        return {"ok": False, "reason": item.get("sem_boleto_motivo") or "sem link de 2a via"}

    alvo = link
    for _ in range(3):  # dsp_boleto.htm -> boletoPDF.jsp (1 salto na prática)
        r = await _fetch(page, alvo, metodo="GET")
        texto = r.get("text") or ""
        if texto.lstrip().startswith("%PDF"):
            break
        proximo = ""
        for href in _RE_HREF.findall(texto):
            if "boletopdf" in href.lower() or href.lower().endswith(".pdf"):
                proximo = href if href.startswith("http") else HDI_BASE + ("" if href.startswith("/") else "/") + href.lstrip("/")
                break
        if not proximo:
            m = re.search(r"""(?i)(?:location(?:\.href)?\s*=\s*|window\.open\s*\()\s*["']([^"']+)["']""", texto)
            if m:
                bruto = m.group(1)
                proximo = bruto if bruto.startswith("http") else HDI_BASE + ("" if bruto.startswith("/") else "/") + bruto.lstrip("/")
        if not proximo or proximo == alvo:
            break
        alvo = proximo

    # O corpo pode ser binário — `fetch().text()` estraga bytes. Reler como base64.
    b64 = await page.evaluate(
        """async (url) => {
          const r = await fetch(url, {credentials: 'include'});
          if (!r.ok) return {status: r.status, b64: ''};
          const buf = new Uint8Array(await r.arrayBuffer());
          let s = ''; for (const b of buf) s += String.fromCharCode(b);
          return {status: r.status, b64: btoa(s)};
        }""",
        alvo,
    )
    try:
        dados = base64.b64decode((b64 or {}).get("b64") or "")
    except Exception:  # noqa: BLE001
        dados = b""
    if not dados.startswith(b"%PDF"):
        return {"ok": False, "reason": f"conteudo nao e PDF (http {(b64 or {}).get('status')})"}

    caminho = build_boleto_storage_path(
        company_id=str(params.get("_company_id") or "company"),
        job_id=str(params.get("_job_id") or "job"),
        portal_key=str(params.get("_portal_key") or "hdi_corretor"),
        recibo=str(item.get("recibo") or ""),
    )
    upload = params.get("_upload_blob")
    evidence.setdefault("notas", []).append(f"boleto HDI baixado — {len(dados)} bytes")
    if callable(upload):
        salvo = await upload(caminho, dados, "application/pdf")
        return {"ok": bool(salvo), "storage_path": salvo or caminho, "bytes": len(dados), "via": "dsp_boleto"}
    return {"ok": True, "storage_path": caminho, "bytes": len(dados), "via": "dsp_boleto", "not_uploaded": True}


async def cobranca_sweep(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """Colheita HDI: entra, lista os atrasados e baixa os boletos. NÃO envia.

    Termina `done` mesmo com colheita parcial. Inadimplente sem boleto (débito
    automático) sai marcado — quem decide o que fazer com ele é o Auxiliar, que
    tem o handoff. Aqui, esconder seria pior que reportar.
    """
    login = await login_check(page, params, evidence)
    if login.status != "done":
        return login
    evidence["logged_in"] = True

    campos = await abrir_tela_parcelas(page, evidence)
    if not campos:
        return JourneyResult(
            status="needs_human",
            captured={"logged_in": True, "stage": "tela_parcelas_nao_abriu"},
            message="nao consegui abrir a tela Parcela da HDI",
        )

    horas = int(params.get("horas_minimas_atraso") or 48)
    s_tipo = str(params.get("s_tipo") or S_TIPO_ATRASADAS)
    blocos = janelas_de_vencimento(dias_atras=int(params.get("dias_retroativos") or 90),
                                   horas_minimas=horas)
    evidence["hdi_s_tipo"] = s_tipo
    evidence["hdi_blocos"] = len(blocos)

    # Um POST por bloco de 30 dias (o teto do portal), do mais antigo ao mais
    # recente. Deduplicado por documento+parcela: a mesma parcela pode aparecer
    # em dois blocos se a borda cair em cima dela.
    parcelas: List[Dict[str, Any]] = []
    vistos = set()
    for bloco in blocos:
        for p in await listar_parcelas(page, campos, s_tipo=s_tipo, evidence=evidence, **bloco):
            chave = (p.get("documento"), p.get("parcela"), p.get("vencimento"))
            if chave in vistos:
                continue
            vistos.add(chave)
            parcelas.append(p)

    atrasados = apenas_atrasados(parcelas, horas_minimas=horas)
    evidence["parcelas_lidas"] = len(parcelas)
    evidence["inadimplentes_count"] = len(atrasados)
    evidence["inadimplentes_sample"] = [
        {k: p.get(k) for k in ("recibo", "apolice_susep", "vencimento", "valor",
                               "cliente_nome", "posicao", "forma_pagamento")}
        for p in atrasados[:5]
    ]

    if not atrasados:
        # "NENHUM INADIMPLENTE" E UMA AFIRMACAO, e ela so pode ser feita quando
        # a tela foi de fato LIDA. Se o servidor devolveu corpo e o parser nao
        # extraiu uma linha sequer, nao sabemos se a carteira esta em dia ou se
        # o HTML mudou — e as duas coisas se parecem exatamente igual daqui.
        #
        # Dizer `done: nenhuma em atraso` nesse caso e o pior desfecho possivel:
        # a corretora le "esta tudo certo" e para de olhar. Entao paramos nos, e
        # pedimos gente.
        maior_resposta = max((int(b.get("bytes") or 0) for b in evidence.get("hdi_buscas") or []), default=0)
        if not parcelas and maior_resposta > 800:
            return JourneyResult(
                status="needs_human",
                captured={"logged_in": True, "stage": "lista_nao_lida"},
                message=("a HDI respondeu a busca, mas nao consegui ler nenhuma linha da tabela "
                         "— NAO afirmo que a carteira esta em dia; a tela precisa ser conferida"),
            )
        return JourneyResult(
            status="done",
            captured={"logged_in": True, "portal": "hdi_corretor", "inadimplentes": [], "boletos": []},
            message=f"HDI: {len(parcelas)} parcela(s) no periodo, nenhuma em atraso ha mais de {horas}h",
        )

    try:
        teto = max(1, int(params.get("max_boletos") or params.get("max_boletos_por_execucao") or 50))
    except (TypeError, ValueError):
        teto = 50

    boletos: List[Dict[str, Any]] = []
    for item in atrasados[:teto]:
        resultado = {"recibo": item.get("recibo"), "ok": False}
        try:
            resultado.update(await baixar_boleto(page, item, params, evidence))
        except Exception as exc:  # noqa: BLE001
            resultado["reason"] = f"{type(exc).__name__}: {str(exc)[:140]}"
        boletos.append(resultado)

    ok = sum(1 for b in boletos if b.get("ok"))
    sem_boleto = sum(1 for p in atrasados if not p.get("link_segunda_via"))
    evidence["boletos_download_ok"] = ok
    evidence["boletos_download_attempts"] = len(boletos)
    evidence["inadimplentes_sem_boleto"] = sem_boleto

    recado = f"HDI: {len(atrasados)} inadimplente(s), {ok} boleto(s)"
    if sem_boleto:
        recado += f", {sem_boleto} em debito automatico (a HDI nao emite 2a via para esses)"
    return JourneyResult(
        status="done",
        captured={"logged_in": True, "portal": "hdi_corretor",
                  "inadimplentes": atrasados, "boletos": boletos},
        message=recado,
    )
