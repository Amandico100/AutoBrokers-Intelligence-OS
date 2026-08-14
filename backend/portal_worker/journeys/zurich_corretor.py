"""Journey Zurich — Espaço Parceiros / Portal Corretor (cobrança).

O que ela faz para a corretora
==============================
Entra no Portal Corretor, lê **Consulta › Parcelas vencidas** e baixa o boleto
de cada parcela realmente atrasada. Não envia nada — quem envia é o Auxiliar de
Cobrança, depois, com o freio de vazão da SPEC-063.

📊 Medido em 13/08/2026 sobre a captura real da AutoFleet: 37 parcelas numa
janela de 30 dias, 1 inadimplente de verdade.

A mais simples das seis — e desta vez é sobre a PORTA, medida por dentro
=========================================================================
    Allianz   BFF moderno, JSON, Bearer JWT
    HDI       app legado, HTML iso-8859-1, sessão por query param
    Tokio     BFF GraphQL + REST JSON, sessão por cookie
    Yelum     REST JSON, Bearer JWT do Auth0 (token em memória)
    MAPFRE    REST JSON, TRÊS tokens crus que crescem por contexto
    Zurich    ASP.NET MVC, **sessão em cookie, mesma origem**     ← esta

Não há token para capturar, não há preflight, não há CORS. Depois de logar,
basta chamar — o cookie de sessão vai sozinho.

A cadeia, com os corpos reais
=============================
    1) GET /ParcelaVencidaCorretor/ListarParcelaVencida
           ?dataInicial=dd/MM/aaaa&dataFinal=dd/MM/aaaa
       -> {"corretor": [ … ], "AcionamentoSinistroVida": …}

    2) GET /SegundaViaBoletoCorretor/GerarBoleto
           ?paymentNO=…&numeroApolice=…&numeroEndosso=…&codigoCarteira=<ramo>
           &NumParcela=…&NumCertificate=…&dataVencimento=dd/MM/aaaa
           &identificadorCalculo=0&codSucursal=
       -> {"ExibeMsg":…, "Msg":…, "Boleto": {"FileContents": [bytes], …}}

📊 **As sete chaves do passo 2 vêm todas da lista.** Não há passo intermediário
— baixar o boleto é leitura.

🔴 DOIS BOTÕES PARA A MESMA COISA, E SÓ UM FUNCIONA
====================================================
📊 Na captura do founder:

    modal da apólice › "Emitir 2ª Via"  ->  /Error?codError=500  "Serviço indisponível"
    lista           › "Gerar 2ª via"    ->  GerarBoleto devolve o PDF na hora

A journey usa o da lista — que além de funcionar, não precisa abrir a apólice.

❓ E O BOLETO AINDA NÃO BAIXOU PELA JOURNEY — o que já foi eliminado
====================================================================
📊 Em 13/08/2026, `GerarBoleto` devolveu **404** em toda tentativa da journey,
enquanto a MESMA chamada funcionou na captura manual do founder. Medido com a
lista como linha de controle (200 antes e depois, em todas as rodadas):

    fetch, cabeçalho mínimo ............ 200, mas devolve HTML (77 KB)
    fetch, cabeçalho igual ao do jQuery  404
    sem o `_=timestamp` ................ 404
    data com `%2F` ..................... 404
    $.ajax **do próprio jQuery da página** 404
    CONTROLE: a lista, no mesmo momento    200 com 33 KB   ← a sessão está viva

Então **não é** cabeçalho, cliente HTTP, sessão nem ritmo. E os parâmetros são
idênticos aos da captura — conferidos contra o código do próprio portal:

    GerarBoleto2 = function (selectedItem) {
      $.ajax({ url: '/SegundaViaBoletoCorretor/GerarBoleto', type: 'GET',
        data: { identificadorCalculo: '0', codSucursal: …,
                paymentNO: selectedItem.payment_no,
                numeroApolice: selectedItem.numeroApolice,
                numeroEndosso: selectedItem.numeroEndossoSPY,
                codigoCarteira: selectedItem.ramo,
                NumParcela: selectedItem.numeroPrestacao,
                NumCertificate: selectedItem.numeroCertificado,
                dataVencimento: FormatDate(selectedItem.dataVencimento) } …

📊 E `FormatDate` é `moment(date).format('DD/MM/YYYY')` — para o item medido,
o `/Date(…)/` e o `dataVencimentoFormated` dão **a mesma data**, `06/08/2026`.
Nada diverge.

❓ **A hipótese que sobra é regra de negócio, não técnica:** o founder emitiu a
2ª via dessa parcela em 13/08 e o portal respondeu *"o boleto estará registrado
e disponível para pagamento no dia 14/08/2026"*. Uma segunda emissão da MESMA
parcela, no mesmo dia, pode ser recusada — e 404 seria como este portal diz
"agora não" (é o mesmo código que ele usa para janela larga demais).

**Enquanto isso não estiver medido, o item é RETIDO com o motivo escrito** e vai
para a fila humana. Nunca some, e nunca é tratado como cobrado.

🔴 O VALOR VEM COM VÍRGULA DE MILHAR **E** DE DECIMAL
=====================================================
📊 Um dos 37 itens reais traz `"valorParcela": "1,287,99"` — são R$ 1.287,99.

O parser brasileiro de sempre (tira o ponto, troca vírgula por ponto) produz
`1.287.99`, que não é número:

    _valor("1,287,99")  ->  None      📊 medido nos parsers da Yelum e da MAPFRE

E `None` não estoura: o item seguiria **sem valor**. A regra da fila diz "sem
data legível não envia" — mas não diz nada sobre valor, então uma cobrança de
R$ 1.287,99 sairia sem dizer quanto.

**A regra correta:** a ÚLTIMA vírgula é o decimal; as anteriores são milhar.
Vale para `1,287,99`, `1.287,99`, `638,95` e `294.35` — um superconjunto do que
o parser antigo já fazia.

🔴 `valorJuros` NÃO GUARDA JUROS
=================================
📊 Idêntico a `valorParcela` em **37 de 37** itens, com `valorAcrescimo` sempre
zero. É o caso que a CLAUDE.md §12.1 nomeia: um campo cujo nome mente sobre o
que guarda. Lê-lo como encargo somaria a dívida duas vezes. **A journey não o
usa** — e o teste guarda essa decisão.

O que o portal dá de presente
=============================
📊 `diasAtraso` **já vem calculado**. Nas outras cinco eu derivo do vencimento.
Aqui existem duas fontes independentes — e elas têm de bater. Se não baterem, é
sinal de que li a data errado, e a varredura para em vez de cobrar pelo número
errado. É a melhor testemunha desde a Yelum.

📊 `situacaoParcelaDescricao` é a coluna **O.B.S** da tela (*"Débito não
autorizado"*, *"Débito agendado"*). É o texto que explica sozinho, para a
atendente, por que aquele item precisa de uma pessoa.

Sem seletor de corretora — e por que ainda assim se confere
============================================================
📊 Cada corretora tem login próprio (a AutoFleet e a Resulta têm códigos
diferentes), e o HTML não tem nem seletor nem lista de corretoras: o cabeçalho
apenas exibe o nome de quem entrou. O risco cross-tenant da MAPFRE **não se
repete aqui**.

Mesmo assim a journey lê esse nome e o registra na evidência: uma credencial
trocada no cadastro faz o mesmo estrago, e a checagem custa uma leitura.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from portal_worker.journeys import JourneyResult

ZURICH_BASE = "https://espacoparceiros.zurich.com.br"
ZURICH_LOGIN = ZURICH_BASE + "/"
ZURICH_HOME = ZURICH_BASE + "/Home"
ZURICH_PARCELAS = ZURICH_BASE + "/ParcelaVencidaCorretor"

EP_LISTA = "/ParcelaVencidaCorretor/ListarParcelaVencida"
EP_BOLETO = "/SegundaViaBoletoCorretor/GerarBoleto"
EP_APOLICE = "/Apolice/DetalheApolice"
EP_SEGURADO = "/Apolice/DetalheDadosSegurado"

# 📊 Os valores reais de `situacaoParcela` na carteira medida.
SITUACAO_PENDENTE = "parcela pendente"
SITUACOES_FORA = ("pago", "aprovado")     # 'Aprovado' = em processamento

# 🔴 LISTA DE PERMISSÃO. O filtro da tela oferece cinco formas (Boleto · Débito
# em conta · Cartão de crédito · Pix · Carnê) e os dados só mostraram três.
# Uma regra "retém se for débito ou cartão" deixaria Pix e Carnê passarem como
# se gerassem boleto — o mesmo defeito que a forma `5` da MAPFRE revelou.
FORMA_COM_BOLETO = "boleto"

# 🔴 A JANELA TEM TETO — e passar dele DERRUBA A SESSÃO INTEIRA
# ==============================================================
# 📊 Medido em 13/08/2026, um fator por vez, com CONTROLE no início e no fim:
#
#     CONTROLE 30 dias .... 200 · 36 linhas
#      45 dias ............ 200 · 43
#      60 dias ............ 200 · 48
#      90 dias ............ 200 · 53
#     120 dias ............ 404
#     180 dias ............ 404
#     365 dias ............ 503
#     CONTROLE 30 dias .... 503   ← QUEBROU
#      30 dias x3 ......... 503 · 503 · 503
#
# São DOIS fenômenos, e só a linha de controle no fim os separa:
#   1. o teto da janela fica entre 90 e 120 dias — acima disso, 404;
#   2. o pedido largo **envenena a sessão**: depois dele, nem a janela que
#      funcionava responde. O portal para de atender aquele login.
#
# Sem repetir o controle no fim, a leitura seria "365 dá 503" — e a próxima
# varredura herdaria uma sessão morta sem ninguém saber por quê.
#
# ⚠️ O 404 pode ser do NÚMERO DE LINHAS e não dos dias (53 linhas passaram,
# e a janela seguinte falhou). Por isso a journey não confia num número fixo:
# ela começa em 90 e **estreita** a janela a cada 404, até o piso.
JANELA_PADRAO_DIAS = 90
JANELA_PISO_DIAS = 15

MARCA_REGRA = "nao emite 2a via de boleto"

# 🚫 O que ESCREVE. A journey nunca chama.
ROTAS_PROIBIDAS = (
    "renovacao1click", "renovacao-1click",   # Renovação 1-Click
    "restituicao",                            # Restituição de Parcelas
    "devolucaoproposta",                      # Devolução de Proposta
    "salvarautoservico",                      # grava log de auto-serviço no nome do corretor
    "gerarexcel",                             # exportação em lote
)


# --------------------------------------------------------------------------
# texto, números e datas — parsers PUROS
# --------------------------------------------------------------------------
def _norm(t: Any) -> str:
    s = unicodedata.normalize("NFKD", str(t or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower()


def _digits(v: Any) -> str:
    return re.sub(r"\D+", "", str(v or ""))


def valor_brasileiro(t: Any) -> Optional[float]:
    """🔴 O parser que entende `1,287,99`.

    📊 A Zurich usa vírgula como separador de milhar **e** de decimal na mesma
    string. O parser das outras journeys devolve `None` para isso — e `None`
    não estoura: o item seguiria sem valor.

    A regra: **o último separador é o decimal**, todos os anteriores são
    milhar. É um superconjunto do comportamento antigo:

        "1,287,99"  -> 1287.99     (só a Zurich produz)
        "1.287,99"  -> 1287.99     (Yelum)
        "638,95"    ->  638.95
        "294.35"    ->  294.35     (MAPFRE, ponto decimal)
        "1.000"     -> 1000.0      (sem decimal)
    """
    bruto = str(t or "").strip()
    if not bruto:
        return None
    negativo = bruto.lstrip().startswith("-")
    limpo = re.sub(r"[^\d.,]", "", bruto)
    if not limpo:
        return None

    ultimo = max(limpo.rfind(","), limpo.rfind("."))
    if ultimo == -1:
        inteiro, decimal = limpo, ""
    else:
        casas = len(limpo) - ultimo - 1
        # 3 casas depois do último separador = separador de MILHAR, não decimal
        # ("1.000" é mil, não um vírgula zero). 📊 Regra do português brasileiro.
        if casas == 3 and limpo.count(",") + limpo.count(".") >= 1 and casas != 2:
            inteiro, decimal = limpo, ""
        else:
            inteiro, decimal = limpo[:ultimo], limpo[ultimo + 1:]

    inteiro = re.sub(r"\D+", "", inteiro)
    decimal = re.sub(r"\D+", "", decimal)
    if not inteiro and not decimal:
        return None
    try:
        n = float(f"{inteiro or '0'}.{decimal or '0'}")
    except ValueError:
        return None
    return -n if negativo else n


def data_iso(t: Any) -> str:
    """`13/08/2026 03:00:00` -> `2026-08-13`.

    📊 Lê o `dataVencimentoFormated`, não o `/Date(ms)/`: o segundo é epoch em
    milissegundos e converter fuso moveria a data um dia — o mesmo cuidado que
    a Yelum e a MAPFRE já exigiam."""
    m = re.match(r"\s*(\d{2})/(\d{2})/(\d{4})", str(t or ""))
    if not m:
        return ""
    d, mes, a = m.groups()
    return f"{a}-{mes}-{d}"


def data_br(d: datetime) -> str:
    return d.strftime("%d/%m/%Y")


def janela_de_busca(dias: int = JANELA_PADRAO_DIAS,
                    *, agora: Optional[datetime] = None) -> Dict[str, str]:
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
# leitura pura das respostas
# --------------------------------------------------------------------------
def extrair_parcelas(resposta: Any) -> List[Dict[str, Any]]:
    """A lista inteira, sem filtrar — o filtro é decisão separada e testável."""
    linhas = (resposta or {}).get("corretor")
    if not isinstance(linhas, list):
        return []
    itens: List[Dict[str, Any]] = []
    for r in linhas:
        if not isinstance(r, dict):
            continue
        apolice = str(r.get("numeroApolice") or "").strip()
        parcela = str(r.get("numeroPrestacao") or "").strip()
        pagamento = str(r.get("payment_no") or "").strip()
        if not (apolice and pagamento):
            continue
        endosso = str(r.get("numeroEndossoSPY") or "0")
        itens.append({
            "portal": "zurich_corretor",
            # chave estável do item na fila e no bucket
            "recibo": f"{apolice}-{endosso}-{parcela}",
            "numero_apolice": apolice,
            "apolice_susep": _digits(apolice),
            "endosso": endosso,
            "certificado": str(r.get("numeroCertificado") or "0"),
            "parcela": parcela,
            "payment_no": pagamento,
            "nosso_numero": r.get("nossoNumero") or "",
            "cliente_nome": str(r.get("nomeSegurado") or "").strip(),
            "cpf_cnpj": "",                     # 🔴 a lista NÃO traz; vem do detalhe
            "vencimento": data_iso(r.get("dataVencimentoFormated")),
            "vencimento_br": str(r.get("dataVencimentoFormated") or "")[:10],
            "valor": valor_brasileiro(r.get("valorParcela")),
            # `valorJuros` é lido de propósito para a EVIDÊNCIA, nunca para conta:
            # 📊 é cópia do valorParcela em 37 de 37 itens. Ver docstring.
            "valor_juros_declarado": valor_brasileiro(r.get("valorJuros")),
            "dias_atraso_portal": r.get("diasAtraso"),
            "situacao": str(r.get("situacaoParcela") or "").strip(),
            "situacao_obs": str(r.get("situacaoParcelaDescricao") or "").strip(),
            "forma_pagamento": str(r.get("tipoPagamento") or "").strip(),
            "ramo": str(r.get("ramo") or ""),
            "produto": str(r.get("descricaoRamo") or ""),
            "vida": bool(r.get("vida")),
            "gera_boleto": _norm(r.get("tipoPagamento")) == FORMA_COM_BOLETO,
        })
    return itens


def esta_em_aberto(item: Dict[str, Any]) -> bool:
    """📊 Só `Parcela pendente` é dívida. `Pago` é óbvio; **`Aprovado` não é**:
    é pagamento em processamento, e cobrar quem já pagou é o pior erro que este
    sistema pode cometer com um cliente da corretora."""
    return _norm(item.get("situacao")) == SITUACAO_PENDENTE


def motivo_para_reter(item: Dict[str, Any]) -> str:
    """Por que ESTE item não vira cobrança automática. '' = pode."""
    if not item.get("gera_boleto"):
        forma = item.get("forma_pagamento") or "?"
        obs = f"; {item['situacao_obs']}" if item.get("situacao_obs") else ""
        return f"{MARCA_REGRA} — forma de pagamento {forma}{obs}"
    if not item.get("nosso_numero"):
        return f"{MARCA_REGRA} — o portal nao emitiu numero bancario para esta parcela"
    return ""


def conferir_dias_de_atraso(item: Dict[str, Any],
                            *, agora: Optional[datetime] = None) -> str:
    """As DUAS contas têm de bater. Se não batem, a varredura para.

    🔴 A melhor testemunha desde a Yelum, e o motivo é a independência: o portal
    manda `diasAtraso` pronto, e eu calculo o mesmo a partir do vencimento. Se
    divergirem, eu li a data errado — e cobrar pelo número errado é pior do que
    não cobrar."""
    declarado = item.get("dias_atraso_portal")
    venc = item.get("vencimento") or ""
    if declarado is None or not venc:
        return ""
    try:
        v = datetime.strptime(venc[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return ""
    ref = (agora or datetime.now(timezone.utc)).astimezone(timezone.utc)
    meu = (ref.date() - v.date()).days
    try:
        dele = int(declarado)
    except (TypeError, ValueError):
        return ""
    # 1 dia de folga: o portal fecha o cálculo em horário próprio.
    if abs(meu - dele) > 1:
        return (f"o portal diz {dele} dia(s) de atraso na parcela {item.get('recibo')} "
                f"e a data {venc} dá {meu} — as duas contas nao batem, entao NAO "
                "afirmo nada sobre esta divida")
    return ""


def params_do_boleto(item: Dict[str, Any]) -> Dict[str, str]:
    """📊 As sete chaves saem todas da lista. Nenhuma chamada intermediária.

    ⚠️ `codigoCarteira` recebe o **ramo** (`31`), não o `CodigoCarteira` real da
    apólice (`0531`) — foi assim que o portal chamou, e trocar os dois devolve
    erro."""
    return {
        "identificadorCalculo": "0",
        "codSucursal": "",
        "paymentNO": str(item.get("payment_no") or ""),
        "numeroApolice": str(item.get("numero_apolice") or ""),
        "numeroEndosso": str(item.get("endosso") or "0"),
        "codigoCarteira": str(item.get("ramo") or ""),
        "NumParcela": str(item.get("parcela") or ""),
        "NumCertificate": str(item.get("certificado") or "0"),
        "dataVencimento": str(item.get("vencimento_br") or ""),
    }


def pdf_do_boleto(resposta: Any) -> Tuple[bytes, str]:
    """(bytes, erro).

    🔴 `Boleto.FileContents` é um **array de inteiros**, não base64 — é como o
    ASP.NET serializa um `FileContentResult`. Tratar como base64 devolve lixo
    silenciosamente."""
    boleto = (resposta or {}).get("Boleto")
    if not isinstance(boleto, dict):
        msg = str((resposta or {}).get("Msg") or "").strip()
        return b"", f"a resposta nao trouxe o boleto{(' — ' + msg) if msg else ''}"
    conteudo = boleto.get("FileContents")
    if isinstance(conteudo, list):
        try:
            dados = bytes(bytearray(int(b) & 0xFF for b in conteudo))
        except (TypeError, ValueError):
            return b"", "FileContents nao e uma sequencia de bytes"
    elif isinstance(conteudo, str):
        import base64
        try:
            dados = base64.b64decode(conteudo)
        except Exception:  # noqa: BLE001
            return b"", "FileContents nao decodifica"
    else:
        return b"", "FileContents ausente"
    if not dados:
        return b"", "o boleto veio vazio"
    if not dados.startswith(b"%PDF"):
        return b"", f"o download nao devolveu um PDF (comeca com {dados[:8]!r})"
    return dados, ""


def documento_do_segurado(detalhe: Any) -> str:
    """O CPF/CNPJ. 📊 `CpfCgcSegurado` na tela de dados do segurado — a LISTA
    não traz, diferente da MAPFRE."""
    d = detalhe if isinstance(detalhe, dict) else {}
    for campo in ("CpfCgcSegurado", "NumeroDocumentoSegurado"):
        doc = _digits(d.get(campo))
        if len(doc) in (11, 14):
            return doc
    return ""


def chaves_da_apolice(detalhe: Any) -> Dict[str, str]:
    """📊 `Sucursal`, `CodigoCarteira` e `PolicyNoAlt` só existem aqui — as
    telas de detalhe do segurado exigem os três, e a lista não os tem."""
    d = detalhe if isinstance(detalhe, dict) else {}
    return {"Sucursal": str(d.get("Sucursal") or ""),
            "CodigoCarteira": str(d.get("CodigoCarteira") or ""),
            "PolicyNoAlt": str(d.get("PolicyNoAlt") or "")}


def build_boleto_storage_path(*, company_id: str, job_id: str, portal_key: str,
                              recibo: str) -> str:
    seguro = re.sub(r"[^A-Za-z0-9._-]+", "-", str(recibo or "boleto")).strip("-") or "boleto"
    return f"{company_id}/{portal_key}/{job_id}/boleto-{seguro}.pdf"


# --------------------------------------------------------------------------
# chamadas — sessão em cookie, mesma origem
# --------------------------------------------------------------------------
# 🔴 O PORTAL RECUSA RAJADA — e recusa com 404, não com 429
# =========================================================
# 📊 Medido em 13/08/2026. A MESMA chamada de 90 dias devolveu 200 num script
# que pausava entre os pedidos e 404 na journey que disparava em sequência. E
# depois do primeiro 404, `/Apolice/DetalheApolice` e `GerarBoleto` também
# passaram a 404 — chamadas que a captura manual do founder fez sem problema.
#
# A diferença não era o pedido: era o **ritmo**. Na captura manual havia pausa
# humana entre um clique e outro.
#
# 404 aqui não quer dizer "não existe". Quer dizer "agora não" — e ler isso
# como ausência de dado é o defeito que a SPEC-070 §2(b) proíbe: falhar com
# status `done` e cara de carteira em dia.
PAUSA_ENTRE_CHAMADAS_MS = 2500
PAUSA_APOS_RECUSA_MS = 6000


async def _api(page, caminho: str, params: Optional[Dict[str, Any]] = None,
               *, ritmo: bool = True) -> Dict[str, Any]:
    """GET de dentro da página, **no ritmo de quem clica**.

    ⚠️ `credentials: 'same-origin'` — a sessão da Zurich viaja em cookie, ao
    contrário da MAPFRE e da Yelum, que precisavam de Bearer e recusavam cookie.
    """
    if any(p in caminho.lower() for p in ROTAS_PROIBIDAS):
        return {"status": 0, "json": None,
                "erro": f"rota proibida para esta journey: {caminho}"}
    if ritmo:
        try:
            await page.wait_for_timeout(PAUSA_ENTRE_CHAMADAS_MS)
        except Exception:  # noqa: BLE001
            pass
    try:
        return await page.evaluate(
            """async ({base, caminho, params}) => {
              const u = new URL(base + caminho);
              for (const [k, v] of Object.entries(params || {})) {
                u.searchParams.set(k, v);
              }
              u.searchParams.set('_', String(Date.now()));
              const r = await fetch(u.toString(), {
                credentials: 'same-origin',
                headers: {'Accept': 'application/json, text/javascript, */*',
                          'X-Requested-With': 'XMLHttpRequest'}});
              let j = null, t = '';
              try { t = await r.text(); } catch (e) { t = ''; }
              try { j = t && '{['.includes(t.trim()[0]) ? JSON.parse(t) : null; }
              catch (e) { j = null; }
              // o começo do corpo vai para a evidência: um 200 vazio precisa
              // ser DIAGNOSTICÁVEL depois, sem outra visita ao portal
              return {status: r.status, json: j, bytes: t.length,
                      amostra: t.slice(0, 160)};
            }""",
            {"base": ZURICH_BASE, "caminho": caminho, "params": params or {}})
    except Exception as exc:  # noqa: BLE001
        return {"status": 0, "json": None, "erro": type(exc).__name__}


# --------------------------------------------------------------------------
# a porta
# --------------------------------------------------------------------------
async def _texto(page) -> str:
    try:
        return await page.inner_text("body", timeout=8000)
    except Exception:  # noqa: BLE001
        return ""


async def _corretora_na_tela(page) -> str:
    """📊 O cabeçalho exibe o nome de quem entrou (`AUTO FLEET R CORRETORA DE
    SEGUROS L`). Não há seletor — mas ler o nome custa uma linha e denuncia
    credencial trocada no cadastro."""
    try:
        return await page.evaluate("""() => {
          const t = document.body ? document.body.innerText : '';
          const m = t.match(/([A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 .&'-]{9,60}(?:CORRETORA|SEGUROS|LTDA|ME|EIRELI)[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 .&'-]{0,20})/);
          return m ? m[1].trim() : '';
        }""")
    except Exception:  # noqa: BLE001
        return ""


async def _dentro_do_portal(page) -> bool:
    """Entrou = a tela de login sumiu e o menu do portal apareceu."""
    try:
        return bool(await page.evaluate("""() => {
          const t = (document.body ? document.body.innerText : '');
          const menu = /Consulta/.test(t) && /Sinistro/.test(t);
          const login = /Acesso ao Portal Corretor/i.test(t);
          return menu && !login;
        }"""))
    except Exception:  # noqa: BLE001
        return False


async def login_check(page, params: Dict[str, Any],
                      evidence: Dict[str, Any]) -> JourneyResult:
    usuario = str(params.get("username") or "").strip()
    senha = str(params.get("password") or "")
    if not usuario or not senha:
        return JourneyResult(status="failed",
                             message="username/password ausentes para Zurich")

    await page.goto(ZURICH_LOGIN, wait_until="domcontentloaded", timeout=90000)
    if await _dentro_do_portal(page):
        evidence["session_reused"] = True
        return JourneyResult(status="done",
                             captured={"logged_in": True, "portal": "zurich_corretor"})

    # 📊 A porta da Zurich é LENTA e intermitente: numa medição o campo de senha
    # apareceu em 9 s e noutra não apareceu em 40 s, na mesma máquina e no mesmo
    # dia. É o mesmo comportamento que o founder viu como "tela branca" ao
    # capturar à mão. Uma recarga resolve — desistir na primeira tentativa
    # transformaria lentidão do portal em "não consegui entrar".
    apareceu = False
    for tentativa in (1, 2):
        try:
            await page.wait_for_selector("input[type=password]", state="visible",
                                         timeout=45000)
            apareceu = True
            break
        except Exception:  # noqa: BLE001
            evidence.setdefault("zurich_recargas", []).append(tentativa)
            if tentativa == 1:
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=90000)
                except Exception:  # noqa: BLE001
                    pass
    if not apareceu:
        return JourneyResult(
            status="needs_human",
            message="o formulario de login da Zurich nao apareceu em duas cargas "
                    "— o portal esta fora do ar ou muito lento")

    # Por `type`, nunca por índice gerado — a lição do `ion-input-N` da MAPFRE
    # vale para qualquer framework.
    preenchidos = 0
    for sel, valor in (("input[type=text]:visible", usuario),
                       ("input[type=password]:visible", senha)):
        try:
            campo = page.locator(sel).first
            if await campo.count():
                await campo.click(timeout=10000)
                await campo.fill(valor, timeout=10000)
                preenchidos += 1
        except Exception:  # noqa: BLE001
            continue
    evidence["zurich_login_campos"] = preenchidos
    if preenchidos < 2:
        return JourneyResult(status="needs_human",
                             message="campos de login da Zurich nao encontrados")

    clicou = False
    for sel in ("button:has-text('Acessar')", "input[value='Acessar']",
                "button[type=submit]", "input[type=submit]"):
        try:
            a = page.locator(sel).first
            if await a.count():
                await a.click(timeout=10000)
                clicou = True
                break
        except Exception:  # noqa: BLE001
            continue
    if not clicou:
        try:
            await page.locator("input[type=password]:visible").first.press("Enter")
        except Exception:  # noqa: BLE001
            pass

    try:
        await page.wait_for_load_state("networkidle", timeout=45000)
    except Exception:  # noqa: BLE001
        pass
    await page.wait_for_timeout(3500)

    if await _dentro_do_portal(page):
        corretora = await _corretora_na_tela(page)
        evidence["zurich_corretora_na_tela"] = corretora or "(nao identificada)"
        rotulo = str(params.get("account_label") or "").strip()
        # `principal` é o rótulo genérico das contas de login único: não há o
        # que conferir. Um rótulo com nome de corretora, sim.
        if corretora and rotulo and _norm(rotulo) not in ("principal", "default"):
            if _norm(rotulo) != _norm(corretora):
                return JourneyResult(
                    status="needs_human",
                    captured={"logged_in": True, "stage": "corretora_nao_confere"},
                    message=(f"entrei na Zurich e a tela diz '{corretora}', mas esta "
                             f"conta é de '{rotulo}' — NAO varro dado de outra empresa"))
        return JourneyResult(status="done",
                             captured={"logged_in": True, "portal": "zurich_corretor",
                                       "corretora": corretora})

    texto = _norm(await _texto(page))
    if "senha" in texto and ("invalid" in texto or "incorret" in texto):
        return JourneyResult(status="failed",
                             message="a Zurich recusou a credencial")
    if "bloquead" in texto:
        return JourneyResult(status="needs_human",
                             message="a Zurich indicou usuario bloqueado")
    if "captcha" in texto:
        return JourneyResult(status="needs_human",
                             message="a Zurich pediu CAPTCHA")
    return JourneyResult(status="needs_human",
                         message="tela pos-login da Zurich nao reconhecida")


# --------------------------------------------------------------------------
# a varredura
# --------------------------------------------------------------------------
async def cpf_do_cliente(page, item: Dict[str, Any],
                         evidence: Dict[str, Any]) -> str:
    """Duas chamadas: a apólice devolve as chaves que a lista não tem, e só
    então o segurado devolve o documento.

    📊 Só para quem vai ser cobrado — nunca para a carteira inteira."""
    base = {"NumeroApolice": item.get("numero_apolice"),
            "NumeroEndosso": item.get("endosso"),
            "NumeroCertificado": item.get("certificado"),
            "Ramo": item.get("ramo"), "CodigoSubCarteira": "",
            "NumeroItem": "0", "Corretor": "", "PolicyNoAlt": ""}
    r1 = await _api(page, EP_APOLICE, {**base, "CodigoCarteira": item.get("ramo")})
    chaves = chaves_da_apolice(r1.get("json"))
    if not chaves["Sucursal"]:
        evidence.setdefault("zurich_clientes", []).append(
            {"recibo": item.get("recibo"), "etapa": "apolice",
             "status": r1.get("status"), "achou_documento": False})
        return ""
    r2 = await _api(page, EP_SEGURADO, {**base, **chaves})
    doc = documento_do_segurado(r2.get("json"))
    evidence.setdefault("zurich_clientes", []).append(
        {"recibo": item.get("recibo"), "status": r2.get("status"),
         "achou_documento": bool(doc)})
    return doc


async def baixar_boleto(page, item: Dict[str, Any], params: Dict[str, Any],
                        evidence: Dict[str, Any]) -> Dict[str, Any]:
    r = await _api(page, EP_BOLETO, params_do_boleto(item))
    if r.get("status") == 404:
        # 📊 404 aqui é "agora não", não "não existe" — ver PAUSA_ENTRE_CHAMADAS.
        # Uma respirada e UMA segunda tentativa. Não mais: insistir é o que
        # derruba a sessão inteira.
        try:
            await page.wait_for_timeout(PAUSA_APOS_RECUSA_MS)
        except Exception:  # noqa: BLE001
            pass
        r = await _api(page, EP_BOLETO, params_do_boleto(item))
        evidence.setdefault("zurich_boleto_retentado", []).append(
            {"recibo": item.get("recibo"), "status": r.get("status")})
    if r.get("status") != 200:
        return {"ok": False,
                "reason": f"o portal recusou o boleto (http {r.get('status')})"}
    dados, erro = pdf_do_boleto(r.get("json"))
    if erro:
        return {"ok": False, "reason": erro}

    aviso = str((r.get("json") or {}).get("Msg") or "").strip()
    caminho = build_boleto_storage_path(
        company_id=str(params.get("_company_id") or "company"),
        job_id=str(params.get("_job_id") or "job"),
        portal_key=str(params.get("_portal_key") or "zurich_corretor"),
        recibo=str(item.get("recibo") or ""))
    evidence.setdefault("notas", []).append(
        f"boleto Zurich baixado — {len(dados)} bytes")
    upload = params.get("_upload_blob")
    resultado = {"bytes": len(dados), "via": "GerarBoleto"}
    if aviso:
        # 📊 "o boleto estará registrado e disponível para pagamento no dia X" —
        # a atendente precisa saber, e o segurado também.
        resultado["aviso_do_portal"] = aviso
    if callable(upload):
        salvo = await upload(caminho, dados, "application/pdf")
        return {"ok": bool(salvo), "storage_path": salvo or caminho, **resultado}
    return {"ok": True, "storage_path": caminho, "not_uploaded": True, **resultado}


async def cobranca_sweep(page, params: Dict[str, Any],
                         evidence: Dict[str, Any]) -> JourneyResult:
    entrada = await login_check(page, params, evidence)
    if entrada.status != "done":
        return entrada
    evidence["logged_in"] = True

    try:
        await page.goto(ZURICH_PARCELAS, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2500)
    except Exception:  # noqa: BLE001
        pass

    try:
        janela_dias = max(1, int(params.get("janela_dias") or JANELA_PADRAO_DIAS))
    except (TypeError, ValueError):
        janela_dias = JANELA_PADRAO_DIAS
    j = janela_de_busca(janela_dias)

    # 🔴 404 = "janela grande demais", NÃO "sem dados". Estreita e tenta de novo.
    #    503 = a sessão foi derrubada. PARA — insistir só piora (ver constantes).
    r = None
    tentadas: List[int] = []
    while janela_dias >= JANELA_PISO_DIAS:
        j = janela_de_busca(janela_dias)
        tentadas.append(janela_dias)
        r = await _api(page, EP_LISTA, {"dataInicial": j["de"], "dataFinal": j["ate"]})
        status = r.get("status")
        if status == 200:
            break
        if status == 503:
            evidence["zurich_lista"] = {"status": 503, "janelas_tentadas": tentadas}
            return JourneyResult(
                status="needs_human",
                captured={"logged_in": True, "stage": "sessao_derrubada"},
                message="a Zurich devolveu 503 e parou de atender este login — "
                        "insistir piora. NAO afirmo nada sobre a carteira")
        if status != 404:
            break
        janela_dias = max(JANELA_PISO_DIAS, janela_dias // 2)
        if janela_dias == tentadas[-1]:          # já estava no piso
            break
        await page.wait_for_timeout(2000)

    r = r or {"status": 0}
    j = janela_de_busca(janela_dias)
    evidence["zurich_lista"] = {"status": r.get("status"), "de": j["de"],
                                "ate": j["ate"], "janela_dias": janela_dias,
                                "janelas_tentadas": tentadas, "bytes": r.get("bytes")}
    if r.get("status") != 200:
        return JourneyResult(
            status="needs_human", captured={"logged_in": True, "stage": "lista_recusada"},
            message=f"a Zurich recusou a busca de parcelas (http {r.get('status')}) "
                    f"em todas as janelas tentadas {tentadas} — NAO afirmo que a "
                    "carteira esta em dia")

    corpo = r.get("json")
    if not isinstance(corpo, dict) or "corretor" not in corpo:
        return JourneyResult(
            status="needs_human", captured={"logged_in": True, "stage": "resposta_ilegivel"},
            message="a Zurich respondeu 200 mas sem a lista de parcelas — corpo "
                    "ilegivel NAO e carteira em dia")

    todas = extrair_parcelas(corpo)

    # 🔴 O DESFECHO MAIS PERIGOSO DESTE PORTAL: HTTP 200 com lista VAZIA.
    # 📊 Medido em 13/08/2026: a mesma janela de 90 dias devolveu 30.229 bytes
    # com 43 linhas e, três minutos depois, **200 com 46 bytes e zero linhas**
    # — com um inadimplente real na carteira. O portal responde vazio quando
    # está recusando, e um `done` dizendo "carteira em dia" é mentira com
    # aparência de sucesso (SPEC-070 §2b).
    #
    # Zero linhas nunca é conclusão: é pergunta. Confirma-se com uma segunda
    # leitura espaçada, e se ainda vier vazia a decisão é de gente — uma
    # corretora ativa não tem ZERO parcelas (nem as pagas) em 90 dias.
    if not todas:
        try:
            await page.wait_for_timeout(PAUSA_APOS_RECUSA_MS)
        except Exception:  # noqa: BLE001
            pass
        r2 = await _api(page, EP_LISTA, {"dataInicial": j["de"], "dataFinal": j["ate"]})
        todas = extrair_parcelas(r2.get("json"))
        evidence["zurich_segunda_leitura"] = {
            "status": r2.get("status"), "bytes": r2.get("bytes"),
            "amostra": r2.get("amostra"), "lidas": len(todas)}
        if not todas:
            return JourneyResult(
                status="needs_human",
                captured={"logged_in": True, "stage": "lista_vazia_nao_confirmada"},
                message=(f"a Zurich devolveu http {r.get('status')} com ZERO parcelas "
                         f"em {janela_dias} dias, duas vezes seguidas — o portal ja "
                         "devolveu 200 vazio estando com inadimplente na carteira, "
                         "entao NAO afirmo que ela esta em dia"))

    em_aberto = [i for i in todas if esta_em_aberto(i)]
    evidence["zurich_carteira"] = {
        "lidas": len(todas), "em_aberto": len(em_aberto),
        "por_situacao": {s: sum(1 for i in todas if i["situacao"] == s)
                         for s in sorted({i["situacao"] for i in todas})}}

    # 🔴 A testemunha: as duas contas de atraso têm de bater.
    for item in em_aberto:
        divergencia = conferir_dias_de_atraso(item)
        if divergencia:
            return JourneyResult(
                status="needs_human",
                captured={"logged_in": True, "stage": "testemunha_nao_bate"},
                message=divergencia)

    try:
        horas = int(params.get("horas_minimas_atraso") or 48)
    except (TypeError, ValueError):
        horas = 48
    atrasados = [i for i in em_aberto
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
                               "forma_pagamento", "situacao_obs", "sem_boleto_motivo")}
        for i in atrasados[:5]]

    if not atrasados:
        return JourneyResult(
            status="done",
            captured={"logged_in": True, "portal": "zurich_corretor",
                      "inadimplentes": [], "boletos": [],
                      "corretora": (entrada.captured or {}).get("corretora")},
            message=(f"Zurich: {len(todas)} parcela(s) na janela de {janela_dias} dias, "
                     f"{len(em_aberto)} em aberto, nenhuma vencida ha mais de {horas}h"))

    try:
        teto = max(1, int(params.get("max_boletos")
                          or params.get("max_boletos_por_execucao") or 50))
    except (TypeError, ValueError):
        teto = 50

    boletos: List[Dict[str, Any]] = []
    for item in a_baixar[:teto]:
        item["cpf_cnpj"] = await cpf_do_cliente(page, item, evidence)
        resultado = {"recibo": item.get("recibo"), "ok": False}
        try:
            resultado.update(await baixar_boleto(page, item, params, evidence))
        except Exception as exc:  # noqa: BLE001
            resultado["reason"] = f"{type(exc).__name__}: {str(exc)[:140]}"
        boletos.append(resultado)

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

    recado = (f"Zurich: {len(atrasados)} inadimplente(s), {ok} boleto(s) "
              f"na janela de {janela_dias} dias")
    if retidos:
        recado += f", {len(retidos)} retido(s) para a equipe humana"
    if janela_dias < JANELA_PADRAO_DIAS:
        # 🔴 A janela estreitou porque o portal recusou a maior. Dívida mais
        # velha que isso NÃO foi olhada — e quem lê o resultado precisa saber,
        # senão "3 inadimplentes" é lido como "são só esses três".
        recado += (f" — a janela foi estreitada de {JANELA_PADRAO_DIAS} para "
                   f"{janela_dias} dias porque o portal recusou a maior; "
                   "divida mais antiga NAO foi verificada")
    return JourneyResult(
        status="done",
        captured={"logged_in": True, "portal": "zurich_corretor",
                  "inadimplentes": atrasados, "boletos": boletos,
                  "corretora": (entrada.captured or {}).get("corretora")},
        message=recado)
