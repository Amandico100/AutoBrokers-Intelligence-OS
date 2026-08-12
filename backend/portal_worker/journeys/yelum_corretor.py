"""Journey Yelum Seguros — Novo Meu Espaço Corretor (cobrança).

O que ela faz para a corretora
==============================
Entra no Novo MEC com o login da corretora, lê **Gestão de Parcelas** filtrando
por atrasadas, e baixa o boleto de cada uma. Não envia nada — quem envia é o
Auxiliar de Cobrança, depois, com o freio de vazão da SPEC-063.

A mais simples das quatro — e o motivo
======================================
📊 Medido no HAR do founder e em visita real (12/08/2026).

    Allianz   BFF moderno, JSON, Bearer JWT
    HDI       app legado, HTML iso-8859-1, sessão por query param
    Tokio     BFF GraphQL + REST JSON, sessão por cookie
    Yelum     REST JSON puro, Bearer JWT do Auth0        ← esta

E aqui **o boleto é um GET que já devolve `application/pdf`**. Não existe
"gerar 2ª via", não existe modal, não existe data para escolher. É leitura. Na
Tokio o mesmo resultado custava três chamadas e uma decisão de negócio.

A cadeia inteira, com os corpos reais:

    1) GET  /payment/installment/overdue?filter=count
       -> {"Total": N}     A TESTEMUNHA, e ela não tem filtro de data

    2) POST /payment/installment/search-by-brokerlist
            ?DueDate-gte=…&DueDate-lte=…&size=200&from=0&SearchType=3
            body {"brokerlist":[]}
       -> {"total": N, "response": [ … ]}

    3) POST /customer/searchCustomerPolicy   {"PolicyNumber": "…"}
       -> CustomerID = o CPF/CNPJ limpo, que é como o WhatsApp é achado

    4) GET  /printdoc/policy/{PolicyNumber}/issuance/{IssuanceID}
            ?installmentID={InstallmentID}
       -> o PDF do boleto

🔴 O token: NÃO está no armazenamento do navegador
---------------------------------------------------
📊 Depois do login eu varri `localStorage` e `sessionStorage` inteiros: 15
chaves, **nenhuma** com JWT. O Auth0 SPA guarda o access token **em memória**.

E o `Authorization` não aparece no HAR porque o Chrome o remove junto com os
cookies ao exportar. Quem denuncia que ele existe é o **preflight**:

    access-control-request-headers: authorization,content-type

📊 O que o app manda, medido interceptando a requisição dele:
`Authorization: Bearer <JWT de 1.758 caracteres>`.

Então a journey **não procura o token: ela escuta**. Abre a tela de parcelas,
deixa o app fazer a chamada dele, captura o cabeçalho e reusa. É o mesmo
princípio da SPEC-033 — falar a língua que a página já fala — só que aqui a
página também empresta a credencial.

> ⚠️ `credentials: 'include'` **quebra** estas chamadas. 📊 O preflight autoriza
> a origem mas **não** manda `Access-Control-Allow-Credentials`, então o
> navegador recusa com "Failed to fetch". Vai `credentials: 'omit'` + Bearer.

🔴 A janela de datas é limitada — e por isso a testemunha importa
------------------------------------------------------------------
📊 O seletor de datas da tela nasce com `min` de ~90 dias atrás e `max` de
ONTEM. Uma dívida mais velha que isso **não aparece na busca**.

Só que o passo 1 conta as atrasadas **sem filtro de data**. Se o total dele for
maior que o que a janela trouxe, nós **sabemos** que ficou gente para trás — e
paramos, em vez de afirmar que a carteira está em dia. É a melhor testemunha
das quatro seguradoras, porque as duas fontes são independentes.

🔴 Akamai também aqui — e eu tinha dito que não
------------------------------------------------
📊 Confirmado no HAR: `POST …/sensor_data` devolvendo `{"success": true}`, o
script de 560 KB com a marca `bmak`, e o mPulse (`go-mpulse.net`).

Eu havia afirmado ao founder que a Yelum não tinha trava nenhuma. **Estava
errado**: eu carreguei a página pública de marketing, não o app logado. O
mesmo erro de método de sempre — medir uma coisa vizinha da que se afirma.
O conserto já existia (`--headless=new` + UA limpo) e é o que faz esta journey
entrar.
"""
from __future__ import annotations

import base64
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from portal_worker.journeys import JourneyResult

YELUM_BASE = "https://novomeuespacocorretor.yelumseguros.com.br"
YELUM_LOGIN = YELUM_BASE + "/account/login"
YELUM_DASHBOARD = YELUM_BASE + "/dashboard"
YELUM_PARCELAS = YELUM_BASE + "/lp/payment-management"
API = "https://integracao.grupohdiseguros.com.br/agent-portal-brazil"

EP_CONTA_ATRASADAS = "/payment/installment/overdue?filter=count"
EP_LISTA = "/payment/installment/search-by-brokerlist"
EP_CLIENTE = "/customer/searchCustomerPolicy"
EP_PARCELAS = "/payment/getPaymentInstallments"
EP_BOLETO = "/printdoc/policy/{apolice}/issuance/{emissao}"

# 📊 Do `<select id="filters">` real da tela:
#     <option value="1">Quitadas</option>
#     <option value="2">A Vencer</option>
#     <option value="3">Atrasadas</option>
SEARCH_TYPE_ATRASADAS = "3"

# 📊 Do `simulatepaymentmethodchange`, que lista as formas que a Yelum aceita:
#     FB = Boleto bancário · DC = Débito em conta · CC = Cartão de crédito
#     PX = QR Code Pix
FORMA_COM_BOLETO = "FB"
FORMAS_SEM_BOLETO = ("DC", "CC")

# 📊 O seletor de datas nasce com ~90 dias de alcance e trava em ONTEM.
JANELA_PADRAO_DIAS = 89

MARCA_REGRA = "nao emite 2a via de boleto"

# 🚫 Telas que ESCREVEM. A journey nunca as chama.
ROTAS_PROIBIDAS = (
    "/payment/reschedule",              # reprogramar boleto
    "simulatepaymentmethodchange",      # trocar forma de pagamento
    "simulateinstalmentsettlement",     # quitar parcelas
    "/lp/invoice",                      # 2ª via em lote, dispara e-mail
)


# --------------------------------------------------------------------------
# texto, números e datas
# --------------------------------------------------------------------------
def _norm(t: Any) -> str:
    s = unicodedata.normalize("NFKD", str(t or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower()


def _digits(v: Any) -> str:
    return re.sub(r"\D+", "", str(v or ""))


def _valor(t: Any) -> Optional[float]:
    """`1.672,62` (lista) e `1672.62` (parcelas) viram o mesmo float.

    🔴 As duas formas vêm da MESMA API, em endpoints diferentes:
    `search-by-brokerlist` devolve `"1.672,62"` e `getPaymentInstallments`
    devolve `"1672.62"`. Um parser que só entende uma das duas lê 1,67 no lugar
    de 1.672,62 — erro de mil vezes num valor de cobrança.
    """
    bruto = str(t or "").strip()
    if not bruto:
        return None
    if "," in bruto:                       # formato brasileiro: 1.672,62
        bruto = bruto.replace(".", "").replace(",", ".")
    try:
        return float(re.sub(r"[^\d.\-]", "", bruto))
    except ValueError:
        return None


def _data_iso(t: Any) -> str:
    """`2026-08-08T03:00:00.000Z` -> `2026-08-08`.

    📊 A Yelum devolve meia-noite de Brasília como 03:00 UTC. Cortar em 10
    caracteres preserva o DIA que o portal mostra — converter o fuso moveria a
    data um dia para trás em toda parcela.
    """
    s = str(t or "")
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else ""


def vencido_ha_mais_de(venc_iso: str, horas: int, *, agora: Optional[datetime] = None) -> bool:
    if not venc_iso:
        return False
    try:
        v = datetime.strptime(venc_iso[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    ref = (agora or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return v <= ref - timedelta(hours=max(0, int(horas)))


def janela_de_busca(dias: int = JANELA_PADRAO_DIAS,
                    *, agora: Optional[datetime] = None) -> Dict[str, str]:
    """De `dias` atrás até ONTEM — que é o teto que a própria tela impõe."""
    ref = (agora or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "gte": (ref - timedelta(days=max(1, int(dias)))).strftime("%Y-%m-%dT00:00:00.000Z"),
        "lte": (ref - timedelta(days=1)).strftime("%Y-%m-%dT23:59:59.000Z"),
    }


# --------------------------------------------------------------------------
# leitura pura das respostas — testável com fixture
# --------------------------------------------------------------------------
def extrair_inadimplentes(lista: Dict[str, Any]) -> List[Dict[str, Any]]:
    itens: List[Dict[str, Any]] = []
    for r in (lista or {}).get("response") or []:
        if not isinstance(r, dict):
            continue
        apolice = str(r.get("PolicyNumber") or "").strip()
        emissao = str(r.get("IssuanceID") or "").strip()
        parcela = str(r.get("InstallmentID") or "").strip()
        if not (apolice and emissao and parcela):
            continue
        forma = str(r.get("PaymentModality") or "").strip().upper()
        itens.append({
            "portal": "yelum_corretor",
            "apolice_susep": _digits(apolice),
            "numero_apolice": apolice,
            "emissao": emissao,
            "parcela": parcela,
            "cliente_nome": r.get("CustomerName") or "",
            "cpf_cnpj": "",                     # vem do passo 3 (searchCustomerPolicy)
            "vencimento": _data_iso(r.get("DueDate")),
            "vencimento_original": _data_iso(r.get("OriginalDueDate")),
            "valor": _valor(r.get("Amount")),
            "valor_original": _valor(r.get("OriginalAmount")),
            "valor_corrigido": _valor(r.get("AmountCorrected")),
            "iof": _valor(r.get("Tax")),
            "status_portal": r.get("Status") or "",
            "forma_pagamento": forma,
            "forma_pagamento_desc": r.get("PaymentModalityDesc") or "",
            "produto": r.get("ProductName") or "",
            "corretora": r.get("BrokerName") or "",
            "contrato": r.get("ContractID"),
            "motivo_recusa": r.get("RejReason") or "",
            "data_recusa": _data_iso(r.get("RejDate")),
            # `recibo` é a chave estável do item na fila e no bucket.
            "recibo": f"{_digits(apolice)}-{emissao}-{parcela}",
            "gera_boleto": forma == FORMA_COM_BOLETO,
        })
    return itens


def conferir_testemunha(total_sem_filtro: Any, itens: List[Dict[str, Any]],
                        janela_dias: int) -> Optional[str]:
    """As DUAS fontes têm de bater. Se não batem, a varredura para.

    🔴 A melhor testemunha das quatro seguradoras, e o motivo é a independência:

        `/payment/installment/overdue?filter=count`   conta SEM filtro de data
        `search-by-brokerlist`                        traz só a janela pedida

    Se o contador diz 7 e a janela trouxe 4, os 3 que faltam existem — quase
    certamente vencidos antes do alcance da tela. Afirmar "carteira em dia"
    aqui seria a mentira que a SPEC-070 §2 proíbe.
    """
    total = _digits(total_sem_filtro)
    if not total:
        return None                    # sem testemunha não se inventa falha
    if int(total) > len(itens):
        return (f"o portal conta {total} parcela(s) atrasada(s) e a janela de "
                f"{janela_dias} dias trouxe {len(itens)} — as que faltam sao mais "
                "velhas que a busca alcanca; NAO afirmo nada sobre a carteira")
    return None


def motivo_para_reter(item: Dict[str, Any]) -> str:
    """Por que ESTE item não vira cobrança automática. '' = pode."""
    if not item.get("gera_boleto"):
        forma = item.get("forma_pagamento_desc") or item.get("forma_pagamento") or "?"
        extra = f"; {item['motivo_recusa']}" if item.get("motivo_recusa") else ""
        return f"{MARCA_REGRA} — forma de pagamento {forma}{extra}"
    return ""


def url_do_boleto(item: Dict[str, Any]) -> str:
    """📊 Do HAR: /printdoc/policy/672520250403934/issuance/2?installmentID=2

    As três chaves vêm todas da lista. Não há passo intermediário — e por isso
    baixar o boleto da Yelum é **leitura**, não ação.
    """
    return (EP_BOLETO.format(apolice=item.get("numero_apolice"), emissao=item.get("emissao"))
            + f"?installmentID={item.get('parcela')}")


# --------------------------------------------------------------------------
# chamadas
# --------------------------------------------------------------------------
async def _api(page, token: str, caminho: str, *, metodo: str = "GET",
               corpo: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Chama a API de dentro da página, com o Bearer que o app emprestou.

    `credentials: 'omit'` de propósito — ver a docstring do módulo.
    """
    try:
        r = await page.evaluate(
            """async ({api, caminho, metodo, corpo, token}) => {
              const init = {method: metodo, credentials: 'omit',
                            headers: {'Authorization': token, 'Accept': 'application/json'}};
              if (corpo !== null) {
                init.headers['Content-Type'] = 'application/json';
                init.body = JSON.stringify(corpo);
              }
              const r = await fetch(api + caminho, init);
              let t = ''; try { t = await r.text(); } catch (e) { t = ''; }
              return {ok: r.ok, status: r.status, text: t};
            }""",
            {"api": API, "caminho": caminho, "metodo": metodo, "corpo": corpo, "token": token},
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": 0, "text": "", "erro": type(exc).__name__}
    texto = r.get("text") or ""
    try:
        r["json"] = json.loads(texto) if texto.lstrip()[:1] in ("{", "[") else None
    except (ValueError, IndexError):
        r["json"] = None
    return r


async def cpf_do_cliente(page, token: str, item: Dict[str, Any],
                         evidence: Dict[str, Any]) -> str:
    """O CPF/CNPJ — que é por onde o sistema de gestão acha o WhatsApp.

    🔴 A lista de inadimplentes **não traz documento nem telefone**. E o que a
    Yelum tem de telefone vem vazio: 📊 `TelephoneAreaCode: ""` e
    `TelePhoneNumber: ""` no mesmo registro em que o e-mail está preenchido.
    Confirma a regra que já valia para Tokio e HDI: o WhatsApp sai do sistema
    de gestão da corretora, nunca do portal.
    """
    r = await _api(page, token, EP_CLIENTE, metodo="POST",
                   corpo={"PolicyNumber": item.get("numero_apolice")})
    linhas = ((r.get("json") or {}).get("response")) or []
    doc = _digits((linhas[0] if linhas else {}).get("CustomerID"))
    evidence.setdefault("yelum_clientes", []).append(
        {"recibo": item.get("recibo"), "status": r.get("status"), "achou_documento": bool(doc)})
    return doc if len(doc) in (11, 14) else ""


async def baixar_boleto(page, token: str, item: Dict[str, Any], params: Dict[str, Any],
                        evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Um GET. O PDF vem no corpo — sem gerar, sem prorrogar, sem escrever."""
    b64 = await page.evaluate(
        """async ({api, caminho, token}) => {
          const r = await fetch(api + caminho, {credentials: 'omit',
                    headers: {'Authorization': token, 'Accept': 'application/pdf'}});
          if (!r.ok) return {status: r.status, b64: ''};
          const buf = new Uint8Array(await r.arrayBuffer());
          let s = ''; for (const b of buf) s += String.fromCharCode(b);
          return {status: r.status, b64: btoa(s)};
        }""",
        {"api": API, "caminho": url_do_boleto(item), "token": token},
    )
    try:
        dados = base64.b64decode((b64 or {}).get("b64") or "")
    except Exception:  # noqa: BLE001
        dados = b""
    if not dados.startswith(b"%PDF"):
        return {"ok": False, "reason": f"o download nao devolveu um PDF (http {(b64 or {}).get('status')})"}

    caminho = build_boleto_storage_path(
        company_id=str(params.get("_company_id") or "company"),
        job_id=str(params.get("_job_id") or "job"),
        portal_key=str(params.get("_portal_key") or "yelum_corretor"),
        recibo=str(item.get("recibo") or ""))
    upload = params.get("_upload_blob")
    evidence.setdefault("notas", []).append(f"boleto Yelum baixado — {len(dados)} bytes")
    if callable(upload):
        salvo = await upload(caminho, dados, "application/pdf")
        return {"ok": bool(salvo), "storage_path": salvo or caminho,
                "bytes": len(dados), "via": "printdoc"}
    return {"ok": True, "storage_path": caminho, "bytes": len(dados),
            "via": "printdoc", "not_uploaded": True}


def build_boleto_storage_path(*, company_id: str, job_id: str, portal_key: str,
                              recibo: str) -> str:
    seguro = re.sub(r"[^A-Za-z0-9._-]+", "-", str(recibo or "boleto")).strip("-") or "boleto"
    return f"{company_id}/{portal_key}/{job_id}/boleto-{seguro}.pdf"


# --------------------------------------------------------------------------
# login e captura do token
# --------------------------------------------------------------------------
async def _texto(page) -> str:
    try:
        return await page.inner_text("body", timeout=6000)
    except Exception:  # noqa: BLE001
        return ""


async def _dentro_do_portal(page) -> bool:
    """📊 O Drupal marca o `<body>` com `user-logged-in` — só depois de entrar."""
    try:
        return bool(await page.evaluate(
            "() => document.body && document.body.className.includes('user-logged-in')"))
    except Exception:  # noqa: BLE001
        return False


async def login_check(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    usuario = str(params.get("username") or "").strip()
    senha = str(params.get("password") or "")
    if not usuario or not senha:
        return JourneyResult(status="failed", message="username/password ausentes para Yelum")

    await page.goto(YELUM_LOGIN, wait_until="domcontentloaded", timeout=60000)
    if await _dentro_do_portal(page):
        evidence["session_reused"] = True
        return JourneyResult(status="done", captured={"logged_in": True, "portal": "yelum_corretor"})

    # 🔴 O login é um Auth0 em OUTRO host, montado por JS. Esperar o CAMPO,
    # nunca o relógio — foi o que custou uma visita na Tokio.
    try:
        await page.wait_for_selector("input[type=password]", state="visible", timeout=40000)
    except Exception:  # noqa: BLE001
        return JourneyResult(status="needs_human", message="formulario de login Yelum nao apareceu")
    evidence["login_host"] = re.sub(r"(?i)(state|code|nonce)=[^&]+", r"\1=<omitido>",
                                    str(getattr(page, "url", "")))[:120]

    preenchido = 0
    for sel in ("input[name=username]", "input[type=text]:visible"):
        try:
            a = page.locator(sel).first
            if await a.count():
                await a.fill(usuario, timeout=8000); preenchido += 1; break
        except Exception:  # noqa: BLE001
            continue
    for sel in ("input[name=password]", "input[type=password]:visible"):
        try:
            a = page.locator(sel).first
            if await a.count():
                await a.fill(senha, timeout=8000); preenchido += 1; break
        except Exception:  # noqa: BLE001
            continue
    evidence["login_fields_found"] = preenchido
    if preenchido < 2:
        return JourneyResult(status="needs_human", message="campos de login Yelum nao encontrados")

    for sel in ("button[type=submit]", "button[name=submit]", "button:has-text('Continuar')"):
        try:
            a = page.locator(sel).first
            if await a.count():
                await a.click(timeout=8000); break
        except Exception:  # noqa: BLE001
            continue

    # Sair do Auth0 é o marco — não o `networkidle`.
    try:
        await page.wait_for_url(lambda u: "auth-broker" not in str(u), timeout=60000)
    except Exception:  # noqa: BLE001
        pass
    try:
        await page.wait_for_load_state("networkidle", timeout=25000)
    except Exception:  # noqa: BLE001
        pass

    if await _dentro_do_portal(page):
        return JourneyResult(status="done", captured={"logged_in": True, "portal": "yelum_corretor"})
    texto = _norm(await _texto(page))
    if "senha" in texto and ("incorret" in texto or "invalid" in texto):
        return JourneyResult(status="failed", message="credenciais rejeitadas pelo portal Yelum")
    if "captcha" in texto:
        return JourneyResult(status="needs_human", message="portal Yelum pediu CAPTCHA/2FA")
    return JourneyResult(status="needs_human", message="tela pos-login Yelum nao reconhecida")


async def capturar_token(page, evidence: Dict[str, Any], timeout_ms: int = 25000) -> str:
    """Escuta o app e pega emprestado o `Authorization` que ELE manda.

    Procurar o token seria adivinhação: 📊 ele não está em `localStorage` nem em
    `sessionStorage` (15 chaves varridas, nenhuma com JWT) — o Auth0 SPA guarda
    em memória. O que existe de certo é que o app o envia em toda chamada.
    Então abrimos uma tela que fala e escutamos.

    🔴 E a tela que se escuta é o **dashboard**, não a de parcelas.

    📊 Custou uma visita: `/lp/payment-management` abre dizendo *"Você ainda não
    realizou nenhuma busca"* — ela **não chama a API sozinha**, espera o clique
    em Buscar. Escutando ali, o token nunca aparece.

    O dashboard, sim: ele monta os cartões de pendência e para isso dispara
    `/policy/policiestoexpirecount`, `/payment/installment/overdue` e outros —
    📊 sete endpoints, todos com o `Authorization`. É a página que fala sem que
    ninguém peça.
    """
    achado: Dict[str, str] = {}

    def espiar(req) -> None:
        if "agent-portal-brazil" not in req.url or achado:
            return
        cab = req.headers.get("authorization")
        if cab and cab.lower().startswith("bearer "):
            achado["token"] = cab

    page.on("request", espiar)
    try:
        for tela in (YELUM_DASHBOARD, YELUM_PARCELAS):
            if achado:
                break
            try:
                await page.goto(tela, wait_until="domcontentloaded", timeout=60000)
            except Exception:  # noqa: BLE001
                continue
            alvo = datetime.now(timezone.utc) + timedelta(milliseconds=timeout_ms)
            while not achado and datetime.now(timezone.utc) < alvo:
                await page.wait_for_timeout(1000)
            evidence.setdefault("yelum_escutou", []).append(
                {"tela": tela.rsplit("/", 1)[-1], "achou": bool(achado)})
    finally:
        try:
            page.remove_listener("request", espiar)
        except Exception:  # noqa: BLE001
            pass
    token = achado.get("token", "")
    # Só o FORMATO vai para a evidência. O token é credencial — nunca é logado.
    evidence["yelum_token"] = {"capturado": bool(token), "chars": len(token),
                               "esquema": token.split(" ", 1)[0] if token else ""}
    return token


# --------------------------------------------------------------------------
# a varredura
# --------------------------------------------------------------------------
async def cobranca_sweep(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    entrada = await login_check(page, params, evidence)
    if entrada.status != "done":
        return entrada
    evidence["logged_in"] = True

    token = await capturar_token(page, evidence)
    if not token:
        return JourneyResult(
            status="needs_human", captured={"logged_in": True, "stage": "sem_token"},
            message="entrei na Yelum mas o app nao fez nenhuma chamada com Authorization "
                    "— sem ele a API nao responde")

    r_conta = await _api(page, token, EP_CONTA_ATRASADAS)
    total_portal = ((r_conta.get("json") or {}).get("Total"))
    evidence["yelum_contador"] = {"status": r_conta.get("status"), "total": total_portal}

    try:
        janela_dias = max(1, int(params.get("janela_dias") or JANELA_PADRAO_DIAS))
    except (TypeError, ValueError):
        janela_dias = JANELA_PADRAO_DIAS
    j = janela_de_busca(janela_dias)
    consulta = (f"{EP_LISTA}?&DueDate-gte={j['gte']}&DueDate-lte={j['lte']}"
                f"&size=200&from=0&SearchType={SEARCH_TYPE_ATRASADAS}")
    r_lista = await _api(page, token, consulta, metodo="POST", corpo={"brokerlist": []})
    lista = r_lista.get("json") or {}
    itens = extrair_inadimplentes(lista)
    evidence["yelum_lista"] = {"status": r_lista.get("status"), "total_declarado": lista.get("total"),
                               "lidos": len(itens), "janela_dias": janela_dias,
                               "de": j["gte"][:10], "ate": j["lte"][:10]}

    if r_lista.get("status") != 200:
        return JourneyResult(
            status="needs_human", captured={"logged_in": True, "stage": "lista_recusada"},
            message=f"a Yelum recusou a busca de parcelas (http {r_lista.get('status')}) "
                    "— NAO afirmo que a carteira esta em dia")

    # A lista também declara o próprio total: se ela pagina, precisamos saber.
    declarado = lista.get("total")
    if isinstance(declarado, int) and declarado > len(itens):
        return JourneyResult(
            status="needs_human", captured={"logged_in": True, "stage": "pagina_incompleta"},
            message=f"a busca declara {declarado} parcela(s) e eu li {len(itens)} "
                    "— falta paginar antes de afirmar qualquer coisa")

    divergencia = conferir_testemunha(total_portal, itens, janela_dias)
    if divergencia:
        return JourneyResult(
            status="needs_human",
            captured={"logged_in": True, "stage": "testemunha_nao_bate",
                      "contador": total_portal, "lidos": len(itens)},
            message=divergencia)

    try:
        horas = int(params.get("horas_minimas_atraso") or 48)
    except (TypeError, ValueError):
        horas = 48
    atrasados = [i for i in itens if vencido_ha_mais_de(i.get("vencimento") or "", horas)]
    evidence["inadimplentes_count"] = len(atrasados)

    for item in atrasados:
        motivo = motivo_para_reter(item)
        if motivo:
            item["sem_boleto_motivo"] = motivo

    a_baixar = [i for i in atrasados if not i.get("sem_boleto_motivo")]
    retidos = [i for i in atrasados if i.get("sem_boleto_motivo")]
    evidence["inadimplentes_sample"] = [
        {k: i.get(k) for k in ("recibo", "vencimento", "valor", "parcela",
                               "forma_pagamento_desc", "sem_boleto_motivo")}
        for i in atrasados[:5]]

    if not atrasados:
        return JourneyResult(
            status="done",
            captured={"logged_in": True, "portal": "yelum_corretor",
                      "inadimplentes": [], "boletos": [], "contador_portal": total_portal},
            message=(f"Yelum: {len(itens)} parcela(s) atrasada(s) na janela de {janela_dias} dias, "
                     f"nenhuma vencida ha mais de {horas}h"))

    try:
        teto = max(1, int(params.get("max_boletos") or params.get("max_boletos_por_execucao") or 50))
    except (TypeError, ValueError):
        teto = 50

    boletos: List[Dict[str, Any]] = []
    for item in a_baixar[:teto]:
        item["cpf_cnpj"] = await cpf_do_cliente(page, token, item, evidence)
        resultado = {"recibo": item.get("recibo"), "ok": False}
        try:
            resultado.update(await baixar_boleto(page, token, item, params, evidence))
        except Exception as exc:  # noqa: BLE001
            resultado["reason"] = f"{type(exc).__name__}: {str(exc)[:140]}"
        boletos.append(resultado)

    # Quem tentou e não trouxe PDF vira tarefa humana com o motivo — nunca
    # segue para a fila de envio (o defeito que a Tokio revelou em 12/08/2026).
    falhou = {str(b.get("recibo")): str(b.get("reason") or "download nao concluido")
              for b in boletos if not b.get("ok")}
    for item in atrasados:
        motivo = falhou.get(str(item.get("recibo")))
        if motivo and not item.get("sem_boleto_motivo"):
            item["sem_boleto_motivo"] = (motivo if MARCA_REGRA in motivo
                                         else f"{MARCA_REGRA} — {motivo}")
            retidos.append(item)

    ok = sum(1 for b in boletos if b.get("ok"))
    evidence["boletos_download_ok"] = ok
    evidence["boletos_download_attempts"] = len(boletos)
    evidence["inadimplentes_sem_boleto"] = len(retidos)

    recado = f"Yelum: {len(atrasados)} inadimplente(s), {ok} boleto(s)"
    if retidos:
        recado += f", {len(retidos)} retido(s) para a equipe humana"
    return JourneyResult(
        status="done",
        captured={"logged_in": True, "portal": "yelum_corretor",
                  "inadimplentes": atrasados, "boletos": boletos,
                  "contador_portal": total_portal},
        message=recado)
