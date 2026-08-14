"""Journey MAPFRE — Portal MAPFRE Negócios (cobrança).

O que ela faz para a corretora
==============================
Entra no portal, **escolhe a corretora certa**, lê as parcelas vencidas e baixa
o boleto de cada uma. Não envia nada — quem envia é o Auxiliar de Cobrança,
depois, com o freio de vazão da SPEC-063.

📊 Tudo abaixo foi medido em 13/08/2026, numa sessão real da AutoFleet.

🔴 O CROSS-TENANT É O CORAÇÃO DESTA JOURNEY
============================================
O mesmo login enxerga **duas corretoras**, e trocar UM campo do corpo da busca
troca a empresa inteira:

    brokerId=55744776  ->  59 parcelas, 21 clientes   (AUTO FLEET)
    brokerId=12542146  ->   8 parcelas,  4 clientes   (RESULTA)
    clientes em comum  ->   ZERO

Não é "quase certo" quando erra: é a empresa errada inteira. Por isso o
`brokerId` **nunca** é fixo no código e **nunca** é o que o portal deixou
selecionado. Ele nasce de:

    GET /distributor/{did}/brokers
    -> [{"brokerId": "...", "brokerDesc": "RESULTA CORRETORA DE SEGUROS L"}, …]

casado com o `account_label` da conta, exigindo **exatamente uma** linha. Zero
ou duas: `needs_human`. É dado, não leitura de tela — e por isso é testável
offline com fixture.

> Resulta e AutoFleet são do mesmo dono, separadas por ramo. Isso explica o
> login compartilhado, mas **não** relaxa a regra: cada corretora entra com a
> credencial dela, e a varredura confirma onde está antes de ler.

A cadeia, com os corpos reais
=============================
    1) POST /distributor/{did}/receipts
       body {brokerId, dateFrom, dateTo, receiptStatusCode: "02", pageSize, …}
       -> {"version":"2.0", "total": N, "list": [...]}
          receipt.receiptId = {apólice}_{endosso}_{parcela}
          client.naturalPerson.identityDocumentNumber = o CPF, JÁ AQUI

    2) GET /policy/document/BO_{receiptId}
       -> documentData.documentContent = o PDF em Base64

Duas chamadas. 📊 Mais simples que a Yelum, que precisava de uma terceira só
para achar o documento do cliente.

🔴 TRÊS ARMADILHAS que só a medição pegou
==========================================

**1. O modal de política de privacidade cobre o formulário.**
Um `<ion-modal class="privacy-policy-modal">` com iframe nasce por cima e
**intercepta todo clique**. Não tem botão "Aceitar": fecha por um ícone
`<ion-buttons class="custom-close-button">`. É quase certamente a "tela branca"
que o founder enfrentou ao capturar à mão.

**2. O Ionic não escuta quem preenche o campo por fora.**
`fill()` escreve no `<input>` nativo mas não dispara o `ionInput` que o Angular
ouve: o modelo continua vazio, o botão **Entrar** fica `disabled` e o clique
estoura por timeout — **sem nunca tentar o login**. Tem de ser digitado, tecla
a tecla.

**3. São TRÊS tokens, e o certo é o mais novo.**

    1.481 chars  carga inicial      /broker/* e /desk   — 401 em /receipts
    4.710 chars  depois do login    sem corretora ainda — 500 em /receipts
    7.049 chars  após /brokerCode   ESTE é o de /receipts e do boleto

O `Authorization` **cresce** conforme o contexto entra nele. Uma journey que
capturasse o *primeiro* — como a da Yelum faz, e lá está certo — receberia HTTP
500 sem explicação. Aqui se guarda **o mais longo visto**, e só depois da
corretora escolhida.

Outras medições que mudaram o desenho
=====================================
📊 **A janela não tem teto.** 30 · 45 · 90 · 365 · 730 dias, todas HTTP 200. O
limite de 31 dias é validação **da tela**, não da API. Uma chamada cobre tudo.

📊 **A testemunha do portal mente.** O painel devolve `pendingReceipts: "0"`
enquanto a lista traz 2 vencidas. Então a testemunha aqui é a **contagem por
status da própria lista**, não o cartão do dashboard.

📊 **Existe uma quarta forma de pagamento que a tela não mostra.** O
`<ion-select>` oferece `1` cartão, `2` débito, `4` boleto. Os dados contêm
também `5 = DÉBITO EM CONTA`. Por isso a regra é **lista de permissão**: só o
`4` gera boleto. Uma regra "retém se for 1 ou 2" deixaria o `5` passar e falhar
calado — o defeito exato que a CLAUDE.md §9.3 proíbe.

📊 **O boleto é regerado a cada pedido.** A mesma parcela baixada em dois dias
dá o mesmo tamanho e **hash diferente** — os encargos são do dia. Não se
espera estabilidade de bytes, e não se recalcula juros: o PDF é o documento
oficial, o valor da lista é o da parcela.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from portal_worker.journeys import JourneyResult

MAPFRE_BASE = "https://negocios.mapfre.com.br"
MAPFRE_LOGIN = MAPFRE_BASE + "/acesso"
MAPFRE_HOME = MAPFRE_BASE + "/tela-principal"
API = "https://dwwngb2iz4xom.cloudfront.net/api/1.0.0"

EP_BROKERS = "/distributor/{did}/brokers"
EP_RECEIPTS = "/distributor/{did}/receipts"
EP_DOCUMENTO = "/policy/document/BO_{recibo}"

# 📊 Do `<ion-select>` real da tela de Parcelas dos Clientes.
STATUS_PAGO = "00"
STATUS_A_VENCER = "01"
STATUS_VENCIDA = "02"
STATUS_CANCELADA = "99"

# 🔴 LISTA DE PERMISSÃO, nunca de exclusão — ver a docstring do módulo.
FORMA_COM_BOLETO = "4"

# 📊 A API aceitou 730 dias numa chamada. O teto de 31 é da tela.
JANELA_PADRAO_DIAS = 365
# 📊 `pageSize=200` devolveu as 59 linhas de uma vez, com `total` conferindo.
PAGINA_TAMANHO = 200
PAGINAS_MAXIMO = 25

MARCA_REGRA = "nao emite 2a via de boleto"

# 🚫 O que ESCREVE no contrato do segurado. A journey nunca chama.
# 📊 O endpoint `/actions` só RESPONDE o que seria permitido
# (`allowChangePaymentMethod`, `allowReschedule`) — mas é a porta de entrada
# dessas duas ações, então fica de fora junto com elas.
ROTAS_PROIBIDAS = (
    "/actions",                 # consulta que antecede reprogramar/trocar forma
    "changepaymentmethod",      # trocar forma de pagamento
    "reschedule",               # reprogramar parcela — 📊 pode custar R$ 50
    "/receipts/export",         # dispara exportação/e-mail em lote
)


# --------------------------------------------------------------------------
# texto, números e datas — parsers PUROS, testáveis fora do navegador
# --------------------------------------------------------------------------
def _norm(t: Any) -> str:
    s = unicodedata.normalize("NFKD", str(t or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower()


def _digits(v: Any) -> str:
    return re.sub(r"\D+", "", str(v or ""))


def _valor(t: Any) -> Optional[float]:
    """📊 A MAPFRE devolve `294.35` (ponto decimal) no `receiptTotFinalAmn`, e
    `294,35` no arquivo exportado. As duas formas viram o mesmo float — ler
    `1.672,62` como 1,67 é errar mil vezes num valor de cobrança."""
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
    """`2026-07-26T00:00:00Z` -> `2026-07-26`.

    📊 A MAPFRE manda meia-noite em Z (a Yelum manda 03:00Z). Cortar em 10
    caracteres preserva o DIA que o portal mostra em ambos os casos — converter
    fuso moveria a data um dia."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(t or ""))
    return m.group(1) if m else ""


def data_br(d: datetime) -> str:
    """A API quer `dd/mm/aaaa`. 📊 Confirmado no corpo real da busca."""
    return d.strftime("%d/%m/%Y")


def janela_de_busca(dias: int = JANELA_PADRAO_DIAS,
                    *, agora: Optional[datetime] = None) -> Dict[str, str]:
    """📊 Sem teto medido até 730 dias. Amplo de propósito: a janela padrão do
    portal (15 dias) devolvia `total: 0` no MESMO dia em que 30 dias devolviam
    2 vencidas reais — afirmar "carteira em dia" ali seria mentira."""
    ref = (agora or datetime.now(timezone.utc)).astimezone(timezone(timedelta(hours=-3)))
    return {"de": data_br(ref - timedelta(days=max(1, int(dias)))),
            "ate": data_br(ref)}


def vencido_ha_mais_de(venc_iso: str, horas: int,
                       *, agora: Optional[datetime] = None) -> bool:
    if not venc_iso:
        return False
    try:
        v = datetime.strptime(venc_iso[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    ref = (agora or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return v <= ref - timedelta(hours=max(0, int(horas)))


# --------------------------------------------------------------------------
# 🔴 O GATE CROSS-TENANT — uma função pura, e é ela que segura tudo
# --------------------------------------------------------------------------
def escolher_broker(brokers: Any, account_label: Any) -> Tuple[str, str]:
    """Devolve `(brokerId, erro)`. Com erro preenchido, a varredura PARA.

    🔴 Exige **exatamente uma** correspondência exata (ignorando caixa e
    acento). Nunca "a primeira que serve", nunca "a que estiver selecionada":

        zero linhas  -> este login não alcança essa corretora
        duas linhas  -> ambíguo, e escolher seria adivinhar de quem é o dado
        uma linha    -> é essa, e o `brokerId` dela vai no corpo da busca

    📊 Sem isso, um `brokerId` errado traz a carteira inteira da outra empresa —
    medido: 59 parcelas de uma, 8 da outra, zero clientes em comum.
    """
    alvo = _norm(account_label)
    if not alvo:
        return "", ("a conta nao tem account_label — sem ele nao da para saber "
                    "QUAL corretora varrer, e o padrao do portal nao serve")
    if not isinstance(brokers, list) or not brokers:
        return "", "o portal nao devolveu a lista de corretoras deste login"

    batem = [b for b in brokers
             if isinstance(b, dict) and _norm(b.get("brokerDesc")) == alvo]
    if not batem:
        vistos = ", ".join(sorted({str(b.get("brokerDesc") or "?")
                                   for b in brokers if isinstance(b, dict)})) or "nenhuma"
        return "", (f"este login nao enxerga a corretora '{account_label}' "
                    f"— o portal ofereceu: {vistos}")
    if len(batem) > 1:
        return "", (f"o portal devolveu {len(batem)} corretoras com o mesmo nome "
                    f"'{account_label}' — escolher seria adivinhar de quem e o dado")

    broker_id = str(batem[0].get("brokerId") or "").strip()
    if not broker_id:
        return "", f"a corretora '{account_label}' veio sem brokerId"
    return broker_id, ""


def conferir_broker_dos_itens(itens: List[Dict[str, Any]], broker_id: str) -> str:
    """A segunda tranca: cada linha lida declara o broker dela. Se alguma vier
    de outro, a leitura inteira é descartada.

    📊 `brokerProductionKey.broker.brokerId` vem preenchido em toda linha —
    então dá para conferir o que voltou, e não só o que foi pedido."""
    fora = sorted({str(i.get("broker_id") or "") for i in itens
                   if str(i.get("broker_id") or "") != str(broker_id)})
    fora = [f for f in fora if f]
    if fora:
        return (f"a lista trouxe parcela(s) de outro(s) broker(s) {fora} quando eu "
                f"pedi {broker_id} — NAO gravo nada desta leitura")
    return ""


# --------------------------------------------------------------------------
# leitura pura das respostas
# --------------------------------------------------------------------------
def _documento_do_cliente(cliente: Dict[str, Any]) -> Tuple[str, str]:
    """(documento, nome). 📊 Pessoa física vem em `naturalPerson`; a jurídica
    em `legalPerson`. Ler só a primeira deixaria empresa sem documento — e sem
    documento o WhatsApp não é achado na gestão."""
    pf = cliente.get("naturalPerson") or {}
    pj = cliente.get("legalPerson") or {}
    fonte = pf or pj
    doc = _digits(fonte.get("identityDocumentNumber"))
    nome = ((fonte.get("personName") or {}).get("name")
            or fonte.get("companyName") or "")
    return (doc if len(doc) in (11, 14) else ""), str(nome).strip()


def extrair_inadimplentes(resposta: Any) -> List[Dict[str, Any]]:
    itens: List[Dict[str, Any]] = []
    for r in (resposta or {}).get("list") or []:
        if not isinstance(r, dict):
            continue
        rec = r.get("receipt") or {}
        recibo = str(rec.get("receiptId") or "").strip()
        if not recibo:
            continue
        doc, nome = _documento_do_cliente(r.get("client") or {})
        forma = str(rec.get("paymentMethodTypeCode") or "").strip()
        itens.append({
            "portal": "mapfre_corretor",
            "recibo": recibo,                       # {apólice}_{endosso}_{parcela}
            "numero_apolice": str(rec.get("policyNumber") or ""),
            "apolice_susep": _digits(rec.get("policyNumber")),
            "endosso": str(rec.get("endorsementNumber") or ""),
            "parcela": str(rec.get("receiptNumber") or ""),
            "cliente_nome": nome,
            "cpf_cnpj": doc,
            "vencimento": _data_iso(rec.get("dueDate")),
            "valor": _valor(rec.get("receiptTotFinalAmn")),
            "status_portal": str(rec.get("receiptStatusCode") or ""),
            "forma_pagamento": forma,
            "forma_pagamento_desc": str(rec.get("paymentMethodTypeDesc") or ""),
            "produto": str(rec.get("productDesc") or ""),
            "produto_codigo": str(rec.get("productCode") or ""),
            "policy_id": str(rec.get("policyId") or ""),
            "broker_id": str(((r.get("brokerProductionKey") or {})
                              .get("broker") or {}).get("brokerId") or ""),
            "gera_boleto": forma == FORMA_COM_BOLETO,
        })
    return itens


def motivo_para_reter(item: Dict[str, Any]) -> str:
    """Por que ESTE item não vira cobrança automática. '' = pode."""
    if not item.get("gera_boleto"):
        forma = (item.get("forma_pagamento_desc")
                 or item.get("forma_pagamento") or "?")
        return f"{MARCA_REGRA} — forma de pagamento {forma}"
    if not item.get("cpf_cnpj"):
        return f"{MARCA_REGRA} — sem CPF/CNPJ na lista do portal"
    return ""


def caminho_do_documento(item: Dict[str, Any]) -> str:
    """📊 `BO_` + o `receiptId` da lista. Sem passo intermediário: por isso
    baixar o boleto da MAPFRE é **leitura**, não ação."""
    return EP_DOCUMENTO.format(recibo=str(item.get("recibo") or ""))


def pdf_do_documento(resposta: Any) -> Tuple[bytes, str]:
    """(bytes, erro). Exige `%PDF` — 📊 o `documentMetadata.size` MENTE
    (dizia 67.548 para um PDF de 19.985 bytes), então validar por ele
    reprovaria documento bom e aprovaria lixo."""
    b64 = (((resposta or {}).get("documentData") or {}).get("documentContent")) or ""
    if not b64:
        return b"", "a resposta do documento veio sem documentContent"
    try:
        dados = base64.b64decode(b64)
    except (binascii.Error, ValueError):
        return b"", "documentContent nao e base64 valido"
    if not dados.startswith(b"%PDF"):
        return b"", f"o documento nao e um PDF (comeca com {dados[:8]!r})"
    return dados, ""


def build_boleto_storage_path(*, company_id: str, job_id: str, portal_key: str,
                              recibo: str) -> str:
    seguro = re.sub(r"[^A-Za-z0-9._-]+", "-", str(recibo or "boleto")).strip("-") or "boleto"
    return f"{company_id}/{portal_key}/{job_id}/boleto-{seguro}.pdf"


def corpo_da_busca(*, broker_id: str, de: str, ate: str,
                   status: str = STATUS_VENCIDA, pagina: int = 1,
                   tamanho: int = PAGINA_TAMANHO) -> Dict[str, Any]:
    """🔴 `brokerId` vazio devolve HTTP 500, e `clientTypeCode` vazio devolve
    400 — os dois são obrigatórios. 📊 `clientTypeCode` 01 e 02 devolvem o
    MESMO resultado (não filtra pessoa física/jurídica), então mandamos o `01`
    que o app manda e lemos os dois tipos na resposta."""
    return {"identityDocumentNumber": "", "pageSize": str(tamanho),
            "pageIndex": str(pagina), "clientTypeCode": "01", "name": "",
            "policyTypeCode": "", "policyNumber": "", "paymentMethodTypeCode": "",
            "dateFrom": de, "dateTo": ate, "brokerId": str(broker_id),
            "productionKey": "", "firstReceipt": "false", "isRescheduled": "false",
            "receiptStatusCode": status}


def leitura_incompleta(declarado: Any, lidos: int) -> str:
    """A testemunha desta seguradora é o próprio `total` da resposta.

    📊 O cartão do painel NÃO serve: ele devolveu `pendingReceipts: "0"` no
    mesmo momento em que a lista trazia 2 vencidas. Uma testemunha que mente é
    pior que nenhuma."""
    try:
        n = int(declarado)
    except (TypeError, ValueError):
        return ""
    if n > lidos:
        return (f"a busca declara {n} parcela(s) e eu li {lidos} — falta paginar "
                "antes de afirmar qualquer coisa sobre a carteira")
    return ""


# --------------------------------------------------------------------------
# chamadas
# --------------------------------------------------------------------------
async def _api(page, token: str, caminho: str, *, metodo: str = "GET",
               corpo: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Chama a API de dentro da página, com o token que o app emprestou.

    ⚠️ `credentials: 'omit'` de propósito: 📊 o preflight libera a origem mas
    **não** manda `Access-Control-Allow-Credentials` — com `include` o
    navegador recusa antes de sair. Mesma armadilha da Yelum.

    ⚠️ O `Authorization` vai **cru**, sem `Bearer` — 📊 é assim que o app manda.
    """
    if any(p in caminho.lower() for p in ROTAS_PROIBIDAS):
        return {"status": 0, "json": None,
                "erro": f"rota proibida para esta journey: {caminho}"}
    try:
        r = await page.evaluate(
            """async ({api, caminho, metodo, corpo, token}) => {
              const init = {method: metodo, credentials: 'omit',
                            headers: {'Authorization': token,
                                      'Accept': 'application/json'}};
              if (corpo !== null) {
                init.headers['Content-Type'] = 'application/json';
                init.body = JSON.stringify(corpo);
              }
              const r = await fetch(api + caminho, init);
              let t = ''; try { t = await r.text(); } catch (e) { t = ''; }
              return {ok: r.ok, status: r.status, text: t};
            }""",
            {"api": API, "caminho": caminho, "metodo": metodo,
             "corpo": corpo, "token": token},
        )
    except Exception as exc:  # noqa: BLE001
        return {"status": 0, "json": None, "erro": type(exc).__name__}
    texto = r.get("text") or ""
    try:
        r["json"] = json.loads(texto) if texto.lstrip()[:1] in ("{", "[") else None
    except (ValueError, IndexError):
        r["json"] = None
    r.pop("text", None)
    return r


# --------------------------------------------------------------------------
# a porta
# --------------------------------------------------------------------------
async def _fechar_politica(page, evidence: Dict[str, Any]) -> bool:
    """🔴 O modal de proteção de dados cobre o formulário e intercepta TODO
    clique. 📊 Ele não tem botão de texto: fecha por um ícone no canto
    (`ion-buttons.custom-close-button`). Sem isso, o login nem é tentado."""
    try:
        await page.wait_for_timeout(2200)
        aberto = await page.evaluate(
            """() => document.querySelectorAll('ion-modal.show-modal').length""")
    except Exception:  # noqa: BLE001
        return True
    if not aberto:
        return True

    for sel in ("ion-modal.show-modal ion-buttons.custom-close-button",
                "ion-modal.show-modal .icon-CLOSE",
                "ion-modal.show-modal [class*=close]"):
        try:
            a = page.locator(sel).first
            if await a.count():
                await a.click(timeout=8000)
                await page.wait_for_timeout(1200)
                break
        except Exception:  # noqa: BLE001
            continue
    try:
        restam = await page.evaluate(
            """() => document.querySelectorAll('ion-modal.show-modal').length""")
    except Exception:  # noqa: BLE001
        restam = 0
    evidence["mapfre_politica_fechada"] = not restam
    return not restam


async def _opcoes_abertas(page) -> List[Dict[str, Any]]:
    """As opções de um `<select-whith-filter>` já aberto. O nome do componente
    é da própria MAPFRE, com o typo (`whith`) — não é engano nosso."""
    try:
        return await page.evaluate("""() => {
          const sel = ['ion-popover ion-item', 'ion-list ion-item', '[role=option]',
                       'ion-radio', 'ion-select-option'].join(',');
          const vistos = new Set(); const saida = [];
          for (const e of document.querySelectorAll(sel)) {
            const r = e.getBoundingClientRect();
            if (r.width < 5 || r.height < 5) continue;
            const t = (e.innerText || e.textContent || '').trim();
            if (!t || t.length > 90 || vistos.has(t)) continue;
            vistos.add(t);
            saida.push({txt: t, x: Math.round(r.x + r.width / 2),
                        y: Math.round(r.y + r.height / 2)});
          }
          return saida.slice(0, 40);
        }""")
    except Exception:  # noqa: BLE001
        return []


async def _escolher_no_modal(page, indice: int, casa) -> Tuple[bool, List[str]]:
    """Abre o campo `indice` do modal e clica na opção que `casa(texto)` aprova."""
    try:
        await page.locator("select-whith-filter").nth(indice).click(timeout=15000)
        await page.wait_for_timeout(1800)
    except Exception:  # noqa: BLE001
        return False, []
    opcoes = await _opcoes_abertas(page)
    rotulos = [o["txt"] for o in opcoes]
    alvo = next((o for o in opcoes if casa(o["txt"])), None)
    if not alvo:
        return False, rotulos
    try:
        await page.mouse.click(alvo["x"], alvo["y"])
        await page.wait_for_timeout(1800)
    except Exception:  # noqa: BLE001
        return False, rotulos
    return True, rotulos


async def login_check(page, params: Dict[str, Any],
                      evidence: Dict[str, Any]) -> JourneyResult:
    usuario = _digits(params.get("username"))
    senha = str(params.get("password") or "")
    rotulo = str(params.get("account_label") or "").strip()
    if not usuario or not senha:
        return JourneyResult(status="failed",
                             message="username/password ausentes para MAPFRE")
    if not rotulo:
        # 🔴 Sem o rótulo não há como saber QUAL corretora varrer, e o padrão
        # do portal é escolha dele, não nossa.
        return JourneyResult(
            status="needs_human",
            message="a conta MAPFRE nao tem account_label com o nome exato da "
                    "corretora — sem ele eu nao sei qual das duas varrer")

    await page.goto(MAPFRE_LOGIN, wait_until="domcontentloaded", timeout=90000)
    try:
        await page.wait_for_selector("input[type=password]", state="visible",
                                     timeout=45000)
    except Exception:  # noqa: BLE001
        return JourneyResult(status="needs_human",
                             message="o formulario de login da MAPFRE nao apareceu")

    if not await _fechar_politica(page, evidence):
        return JourneyResult(
            status="needs_human",
            message="o modal de protecao de dados da MAPFRE nao fechou — ele "
                    "intercepta todo clique, entao nem adianta tentar entrar")

    # 🔴 DIGITADO, não preenchido — ver a docstring do módulo.
    try:
        u = page.locator("input[type=text]:visible").first
        await u.click(timeout=15000)
        await u.press_sequentially(usuario, delay=55, timeout=40000)
        s = page.locator("input[type=password]:visible").first
        await s.click(timeout=15000)
        await s.press_sequentially(senha, delay=55, timeout=40000)
        await page.wait_for_timeout(800)
    except Exception:  # noqa: BLE001
        return JourneyResult(status="needs_human",
                             message="nao consegui digitar nos campos de login da MAPFRE")

    try:
        estado = await page.evaluate("""() => {
          const b = Array.from(document.querySelectorAll('button, ion-button'))
            .find(e => (e.textContent || '').trim().toLowerCase().startsWith('entrar'));
          return {achou: !!b,
                  desabilitado: b ? (b.disabled === true ||
                                     b.getAttribute('disabled') !== null) : null};
        }""")
    except Exception:  # noqa: BLE001
        estado = {}
    evidence["mapfre_botao_entrar"] = estado
    if estado.get("desabilitado"):
        return JourneyResult(
            status="needs_human",
            message="o botao Entrar da MAPFRE continuou desabilitado depois de "
                    "digitar — o formulario nao aceitou o que foi escrito")

    for sel in ("ion-button:has-text('Entrar')", "button:has-text('Entrar')",
                "button[type=submit]"):
        try:
            a = page.locator(sel).first
            if await a.count():
                await a.click(timeout=12000)
                break
        except Exception:  # noqa: BLE001
            continue

    try:
        await page.wait_for_load_state("networkidle", timeout=45000)
    except Exception:  # noqa: BLE001
        pass
    await page.wait_for_timeout(4000)

    texto = _norm(await _texto(page))
    if "autenticacao invalida" in texto or "usuario ou senha" in texto:
        return JourneyResult(status="failed",
                             message="a MAPFRE recusou a credencial (autenticacao invalida)")
    if "bloquead" in texto or "desbloquear usuario" in texto and "seja bem-vindo" in texto:
        # a tela de login sempre tem o link "Desbloquear usuário"; só conta como
        # bloqueio se vier junto com a palavra bloqueado.
        if "bloquead" in texto:
            return JourneyResult(status="needs_human",
                                 message="a MAPFRE indicou usuario bloqueado")

    # ---- 🔴 O MODAL DA CORRETORA: o gate cross-tenant na tela ----
    try:
        await page.wait_for_selector("select-whith-filter", state="visible",
                                     timeout=30000)
    except Exception:  # noqa: BLE001
        if "tela-principal" in str(getattr(page, "url", "")):
            evidence["mapfre_modal_corretora"] = "nao apareceu (sessao ja escolhida)"
            return JourneyResult(status="done",
                                 captured={"logged_in": True, "portal": "mapfre_corretor"})
        return JourneyResult(status="needs_human",
                             message="entrei na MAPFRE mas a tela de escolha da "
                                     "corretora nao apareceu")

    alvo_norm = _norm(rotulo)
    ok, ofertadas = await _escolher_no_modal(
        page, 0, lambda t: _norm(t) == alvo_norm)
    evidence["mapfre_corretoras_ofertadas"] = ofertadas
    if not ok:
        return JourneyResult(
            status="needs_human",
            captured={"logged_in": True, "stage": "corretora_nao_encontrada"},
            message=(f"a corretora '{rotulo}' nao esta entre as que este login "
                     f"enxerga ({ofertadas or 'nenhuma'}) — NAO varro o que estiver "
                     "selecionado"))

    ok_cod, codigos = await _escolher_no_modal(
        page, 1, lambda t: _norm(t).startswith("todos"))
    if not ok_cod and codigos:
        ok_cod, _ = await _escolher_no_modal(page, 1, lambda t: True)
    evidence["mapfre_codigos_internos"] = codigos

    for sel in ("ion-modal.show-modal ion-button:has-text('Salvar')",
                "ion-button:has-text('Salvar')"):
        try:
            a = page.locator(sel).first
            if await a.count():
                await a.click(timeout=12000)
                break
        except Exception:  # noqa: BLE001
            continue
    try:
        await page.wait_for_load_state("networkidle", timeout=45000)
    except Exception:  # noqa: BLE001
        pass
    await page.wait_for_timeout(4000)

    return JourneyResult(status="done",
                         captured={"logged_in": True, "portal": "mapfre_corretor"})


async def _texto(page) -> str:
    try:
        return await page.inner_text("body", timeout=6000)
    except Exception:  # noqa: BLE001
        return ""


async def capturar_token(page, evidence: Dict[str, Any],
                         timeout_ms: int = 30000) -> str:
    """Escuta o app e pega emprestado o `Authorization` que ELE manda.

    🔴 Guarda **o mais longo visto**, não o primeiro. 📊 São três tokens, e só
    o de contexto completo (o mais longo, emitido depois do `/brokerCode`)
    responde em `/receipts` — os outros dão 401 e 500. Ver a docstring do
    módulo.
    """
    achados: Dict[int, str] = {}

    def espiar(req) -> None:
        if "dwwngb2iz4xom" not in req.url:
            return
        cab = req.headers.get("authorization")
        if cab:
            achados[len(cab)] = cab

    page.on("request", espiar)
    try:
        try:
            await page.goto(MAPFRE_HOME, wait_until="domcontentloaded", timeout=60000)
        except Exception:  # noqa: BLE001
            pass
        alvo = datetime.now(timezone.utc) + timedelta(milliseconds=timeout_ms)
        while datetime.now(timezone.utc) < alvo:
            await page.wait_for_timeout(1500)
            # já vi um token grande o bastante para ser o de contexto completo
            if achados and max(achados) > 5000:
                break
    finally:
        try:
            page.remove_listener("request", espiar)
        except Exception:  # noqa: BLE001
            pass

    token = achados[max(achados)] if achados else ""
    # Só o FORMATO vai para a evidência. O token é credencial — nunca é logado.
    evidence["mapfre_token"] = {"capturado": bool(token), "chars": len(token),
                               "tamanhos_vistos": sorted(achados)}
    return token


# --------------------------------------------------------------------------
# a varredura
# --------------------------------------------------------------------------
async def _listar_pagina(page, token: str, did: str, corpo: Dict[str, Any]):
    return await _api(page, token, EP_RECEIPTS.format(did=did),
                      metodo="POST", corpo=corpo)


async def baixar_boleto(page, token: str, item: Dict[str, Any],
                        params: Dict[str, Any],
                        evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Um GET que devolve JSON com o PDF em Base64. Sem gerar, sem prorrogar."""
    r = await _api(page, token, caminho_do_documento(item))
    if r.get("status") != 200:
        return {"ok": False,
                "reason": f"o portal recusou o documento (http {r.get('status')})"}
    dados, erro = pdf_do_documento(r.get("json"))
    if erro:
        return {"ok": False, "reason": erro}

    caminho = build_boleto_storage_path(
        company_id=str(params.get("_company_id") or "company"),
        job_id=str(params.get("_job_id") or "job"),
        portal_key=str(params.get("_portal_key") or "mapfre_corretor"),
        recibo=str(item.get("recibo") or ""))
    evidence.setdefault("notas", []).append(
        f"boleto MAPFRE baixado — {len(dados)} bytes")
    upload = params.get("_upload_blob")
    if callable(upload):
        salvo = await upload(caminho, dados, "application/pdf")
        return {"ok": bool(salvo), "storage_path": salvo or caminho,
                "bytes": len(dados), "via": "policy/document"}
    return {"ok": True, "storage_path": caminho, "bytes": len(dados),
            "via": "policy/document", "not_uploaded": True}


async def cobranca_sweep(page, params: Dict[str, Any],
                         evidence: Dict[str, Any]) -> JourneyResult:
    entrada = await login_check(page, params, evidence)
    if entrada.status != "done":
        return entrada
    evidence["logged_in"] = True

    token = await capturar_token(page, evidence)
    if not token:
        return JourneyResult(
            status="needs_human", captured={"logged_in": True, "stage": "sem_token"},
            message="entrei na MAPFRE mas o app nao fez nenhuma chamada com "
                    "Authorization — sem ele a API nao responde")

    # ---- quem sou eu, e de quem e o dado que vou ler ----
    did = ""
    m = re.search(r'"distributorId"\s*:\s*"(\d+)"', token)
    if m:
        did = m.group(1)
    if not did:
        # 📊 O distributorId viaja no customPayload do próprio token; se não
        # vier de lá, pergunta-se ao app pela URL que ele acabou de chamar.
        try:
            did = await page.evaluate(
                """() => (window.performance.getEntriesByType('resource') || [])
                     .map(e => (e.name.match(/\\/distributor\\/(\\d+)/) || [])[1])
                     .filter(Boolean).pop() || ''""")
        except Exception:  # noqa: BLE001
            did = ""
    evidence["mapfre_distributor"] = did or "nao identificado"
    if not did:
        return JourneyResult(
            status="needs_human", captured={"logged_in": True, "stage": "sem_distributor"},
            message="nao consegui identificar o distributorId da sessao MAPFRE")

    r_brokers = await _api(page, token, EP_BROKERS.format(did=did))
    brokers = r_brokers.get("json")
    broker_id, erro = escolher_broker(brokers, params.get("account_label"))
    evidence["mapfre_brokers"] = {
        "http": r_brokers.get("status"),
        "quantas": len(brokers) if isinstance(brokers, list) else None,
        "rotulos": sorted({str(b.get("brokerDesc")) for b in brokers
                           if isinstance(b, dict)}) if isinstance(brokers, list) else [],
        "escolhido": broker_id or None}
    if erro:
        # 🔴 Único desfecho aceitável quando a corretora não confere.
        return JourneyResult(
            status="needs_human",
            captured={"logged_in": True, "stage": "corretora_nao_confere"},
            message=erro)

    # ---- a lista, paginada ate fechar com o total declarado ----
    try:
        janela_dias = max(1, int(params.get("janela_dias") or JANELA_PADRAO_DIAS))
    except (TypeError, ValueError):
        janela_dias = JANELA_PADRAO_DIAS
    j = janela_de_busca(janela_dias)

    itens: List[Dict[str, Any]] = []
    declarado: Any = None
    pagina = 1
    while pagina <= PAGINAS_MAXIMO:
        r = await _listar_pagina(page, token, did, corpo_da_busca(
            broker_id=broker_id, de=j["de"], ate=j["ate"], pagina=pagina))
        if r.get("status") != 200:
            return JourneyResult(
                status="needs_human",
                captured={"logged_in": True, "stage": "lista_recusada"},
                message=f"a MAPFRE recusou a busca de parcelas (http {r.get('status')}) "
                        "— NAO afirmo que a carteira esta em dia")
        corpo = r.get("json")
        if not isinstance(corpo, dict):
            return JourneyResult(
                status="needs_human",
                captured={"logged_in": True, "stage": "resposta_ilegivel"},
                message="a MAPFRE respondeu 200 mas o corpo nao deu para ler — "
                        "corpo ilegivel NAO e carteira em dia")
        declarado = corpo.get("total")
        novos = extrair_inadimplentes(corpo)
        itens.extend(novos)
        if not novos or len(itens) >= int(declarado or 0):
            break
        pagina += 1

    evidence["mapfre_lista"] = {"total_declarado": declarado, "lidos": len(itens),
                                "paginas": pagina, "janela_dias": janela_dias,
                                "de": j["de"], "ate": j["ate"],
                                "broker_id": broker_id}

    falta = leitura_incompleta(declarado, len(itens))
    if falta:
        return JourneyResult(
            status="needs_human",
            captured={"logged_in": True, "stage": "leitura_incompleta"},
            message=falta)

    # 🔴 A segunda tranca: conferir de quem sao as linhas que voltaram.
    intruso = conferir_broker_dos_itens(itens, broker_id)
    if intruso:
        return JourneyResult(
            status="needs_human",
            captured={"logged_in": True, "stage": "broker_divergente"},
            message=intruso)

    try:
        horas = int(params.get("horas_minimas_atraso") or 48)
    except (TypeError, ValueError):
        horas = 48
    atrasados = [i for i in itens
                 if vencido_ha_mais_de(i.get("vencimento") or "", horas)]
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
            captured={"logged_in": True, "portal": "mapfre_corretor",
                      "inadimplentes": [], "boletos": [],
                      "corretora": params.get("account_label"),
                      "broker_id": broker_id},
            message=(f"MAPFRE: {len(itens)} parcela(s) vencida(s) na janela de "
                     f"{janela_dias} dias, nenhuma vencida ha mais de {horas}h"))

    try:
        teto = max(1, int(params.get("max_boletos")
                          or params.get("max_boletos_por_execucao") or 50))
    except (TypeError, ValueError):
        teto = 50

    boletos: List[Dict[str, Any]] = []
    for item in a_baixar[:teto]:
        resultado = {"recibo": item.get("recibo"), "ok": False}
        try:
            resultado.update(await baixar_boleto(page, token, item, params, evidence))
        except Exception as exc:  # noqa: BLE001
            resultado["reason"] = f"{type(exc).__name__}: {str(exc)[:140]}"
        boletos.append(resultado)

    # Quem tentou e não trouxe PDF vira tarefa humana COM o motivo — nunca
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

    recado = f"MAPFRE: {len(atrasados)} inadimplente(s), {ok} boleto(s)"
    if retidos:
        recado += f", {len(retidos)} retido(s) para a equipe humana"
    return JourneyResult(
        status="done",
        captured={"logged_in": True, "portal": "mapfre_corretor",
                  "inadimplentes": atrasados, "boletos": boletos,
                  "corretora": params.get("account_label"),
                  "broker_id": broker_id},
        message=recado)
