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

🔴 O BOLETO: A CHAMADA RECONSTRUÍDA NÃO PASSA — A FUNÇÃO DA PÁGINA, SIM
========================================================================
📊 **Resolvido em 14/08/2026.** O download funciona chamando `GerarBoleto2`,
que é a **função do próprio portal**, com um objeto montado a partir da lista:

    ko.dataFor(document.querySelector('#inputI')).GerarBoleto2({
        payment_no, numeroApolice, numeroEndossoSPY, ramo,
        numeroPrestacao, numeroCertificado, dataVencimento })

    -> download de 107.288 bytes, %PDF     📊 medido

São os mesmos sete campos que a lista devolve. Quem monta o pedido passa a ser
o código do portal, com o estado dele (`SearchObject.Sucursal`), e não a minha
reconstrução da URL.

**A ordem da journey é:** chamada direta → `GerarBoleto2` → clique no botão.
A primeira é a mais barata; as outras duas são o fallback que a SPEC-033 prevê.

O que foi eliminado antes de chegar aqui
----------------------------------------
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

**A conclusão:** não adianta reconstruir a URL — alguma coisa no estado que o
portal monta não cabe numa query string reproduzida de fora. Chamar a função
dele resolve, e é mais honesto: se o portal mudar os parâmetros amanhã, a
função muda junto e a journey continua funcionando.

E o item que ainda assim não baixar é **RETIDO com o motivo escrito**, indo
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

    # 🔴 `input[type=text]:visible` + `.first` NÃO serve aqui.
    # 📊 A página de login tem **37 inputs** — caixa de busca do topo, campos de
    # modais escondidos, filtros. Pegar "o primeiro texto visível" acertou o
    # campo certo por ordem de DOM, e num carregamento diferente pegou outro:
    # o login falhou com "campos não encontrados" logo depois de ter funcionado.
    #
    # A âncora estável é o campo de SENHA — 📊 existe exatamente um na página.
    # A partir dele sobe-se até o container que tem UM campo de texto, e esse é
    # o usuário. Os dois ganham uma marca própria, e o Playwright usa a marca.
    marcados = await page.evaluate("""() => {
      document.querySelectorAll('[data-ab-login]').forEach(
        e => e.removeAttribute('data-ab-login'));
      const visivel = (e) => !!e.offsetParent;
      const senhas = Array.from(document.querySelectorAll('input[type=password]'))
                        .filter(visivel);
      if (senhas.length !== 1) return {ok: false, senhas: senhas.length};
      const pw = senhas[0];
      let no = pw.parentElement, usuario = null;
      while (no && no !== document.body) {
        const textos = Array.from(no.querySelectorAll('input[type=text]'))
                          .filter(visivel);
        if (textos.length === 1) { usuario = textos[0]; break; }
        if (textos.length > 1) { usuario = textos[textos.length - 1]; break; }
        no = no.parentElement;
      }
      if (!usuario) return {ok: false, senhas: 1, usuario: 0};
      usuario.setAttribute('data-ab-login', 'usuario');
      pw.setAttribute('data-ab-login', 'senha');
      return {ok: true, subiu_ate: no ? no.tagName : null};
    }""")
    evidence["zurich_login_ancora"] = marcados
    if not marcados.get("ok"):
        return JourneyResult(
            status="needs_human",
            message="nao consegui identificar o par usuario/senha na tela da Zurich "
                    f"({marcados})")

    preenchidos = 0
    for marca, valor in (("usuario", usuario), ("senha", senha)):
        try:
            campo = page.locator(f"input[data-ab-login={marca}]").first
            await campo.click(timeout=10000)
            await campo.fill(valor, timeout=10000)
            preenchidos += 1
        except Exception:  # noqa: BLE001
            continue
    evidence["zurich_login_campos"] = preenchidos
    if preenchidos < 2:
        return JourneyResult(status="needs_human",
                             message="campos de login da Zurich nao aceitaram o "
                                     "preenchimento")

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
        # 🔴 SPEC-073 — a versão anterior tinha DOIS fail-opens, e o segundo era
        # invisível:
        #
        #   1. `if corretora and ...` — não conseguir LER a corretora da tela
        #      pulava a conferência e devolvia `done`. Falha de leitura virava
        #      permissão, e é exatamente quando não se sabe que não se deve
        #      seguir.
        #   2. `principal` pulava a checagem. A premissa era "rótulo genérico =
        #      login único", mas 📊 `principal` é o DEFAULT que o dashboard
        #      grava (`portal-credentials/route.ts:67`) — ou seja, toda conta
        #      criada pela tela nascia com a revalidação desligada, e 14 das 16
        #      contas medidas estão assim.
        #
        # Agora: rótulo genérico continua sem ter o que comparar (é honesto),
        # mas isso fica REGISTRADO como não-verificado em vez de passar por
        # verificado. E rótulo nomeado com tela ilegível para.
        from portal_worker.identidade import (
            conferir_corretora_da_sessao, rotulo_e_generico,
        )

        erro_id = conferir_corretora_da_sessao(corretora, rotulo, portal="zurich")
        evidence["identidade_corretora"] = {
            "lida": bool(corretora),
            "esperado_nomeado": not rotulo_e_generico(rotulo),
            "verificado": not erro_id and not rotulo_e_generico(rotulo),
        }
        if erro_id:
            return JourneyResult(
                status="needs_human",
                captured={"logged_in": True, "stage": "corretora_nao_confere"},
                message=erro_id)
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


# 🔴 A pagina tem VARIAS tabelas (select2, widgets). 📊 `table tbody tr` contou
# 9 linhas com a busca vazia — contar assim daria "achei resultado" sem resultado.
# A tabela boa e a que tem "Segurado" no cabecalho.
_JS_TABELA_DO_RESULTADO = """() => {
  for (const t of document.querySelectorAll('table')) {
    const cab = (t.tHead ? t.tHead.innerText : '') || '';
    if (/Segurado/i.test(cab) && /Parcela/i.test(cab)) return t;
  }
  return null;
}"""

_JS_LINHAS_DO_RESULTADO = """() => {
  for (const t of document.querySelectorAll('table')) {
    const cab = (t.tHead ? t.tHead.innerText : '') || '';
    if (/Segurado/i.test(cab) && /Parcela/i.test(cab)) {
      return Array.from(t.querySelectorAll('tbody tr'))
               .filter(tr => tr.querySelectorAll('td').length > 3).length;
    }
  }
  return 0;
}"""


async def buscar_na_tela(page, de: str, ate: str,
                         evidence: Dict[str, Any]) -> int:
    """Faz a busca PELA TELA, como uma pessoa faz — e devolve quantas linhas vieram.

    📊 Serve a dois propósitos de uma vez:
      1. deixa a tabela renderizada, que é o que o botão `2ªVia` precisa;
      2. resolve o 200-com-lista-vazia sem truque: se vier zero, clica de novo
         em **Buscar** — foi o que o founder descreveu fazendo à mão.

    Os campos são `#inputI` e `#inputF` (Knockout: `SearchObject.DataInicial` /
    `DataFinal`), com máscara `dd/mm/aaaa`.
    """
    try:
        if "ParcelaVencidaCorretor" not in str(getattr(page, "url", "")):
            await page.goto(ZURICH_PARCELAS, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_selector("#inputI", state="visible", timeout=40000)
    except Exception:  # noqa: BLE001
        evidence["zurich_tela_busca"] = "formulario nao apareceu"
        return -1

    linhas = 0
    for tentativa in (1, 2, 3):
        try:
            # 🔴 Preencher e SEGUIR EM FRENTE não serve: 📊 o datepicker do
            # primeiro campo fica aberto por cima do segundo, o `fill` não pega,
            # e a busca sai com **a data final em branco** — foi exatamente o que
            # aconteceu, e a tela ficou vazia sem nenhum erro.
            #
            # Então cada campo é preenchido, o datepicker é fechado, e o valor é
            # CONFERIDO antes de clicar em Buscar.
            # 🔴 A MÁSCARA EMBARALHA O QUE É DIGITADO RÁPIDO.
            # 📊 Digitando `14/08/2026` no campo final, o portal guardou
            # `40/82/0261` — os dígitos rodados de uma posição. O primeiro campo
            # aceitava, o segundo não; e a busca saía com data inválida,
            # devolvendo tela vazia **sem erro nenhum**.
            #
            # Então o valor é posto por JS (o mask não intercepta atribuição) e
            # depois CONFERIDO por igualdade — não por "está preenchido".
            # 📊 Foi assim que `40/82/0261` passou: era não-vazio.
            for seletor, valor in (("#inputI", de), ("#inputF", ate)):
                for tentativa_campo in (1, 2, 3):
                    if tentativa_campo == 1:
                        await page.evaluate(
                            """({sel, v}) => {
                                 const e = document.querySelector(sel);
                                 if (!e) return;
                                 e.value = v;
                                 e.dispatchEvent(new Event('input', {bubbles: true}));
                                 e.dispatchEvent(new Event('change', {bubbles: true}));
                               }""", {"sel": seletor, "v": valor})
                        await page.wait_for_timeout(400)
                        if (await page.input_value(seletor, timeout=5000) or "") == valor:
                            break
                    campo = page.locator(seletor)
                    await campo.click(timeout=10000)
                    await campo.fill("", timeout=8000)
                    # devagar: o mask precisa de tempo entre as teclas
                    await campo.type(valor, delay=140, timeout=30000)
                    # 🔴 NUNCA `Escape` aqui. O datepicker do jQuery UI trata
                    # Escape como "fechar SEM selecionar" e **reverte o campo ao
                    # valor anterior** — comportamento documentado dele.
                    # 📊 Foi o que apagou as datas: com um Escape no fim, só a
                    # data final sumia; com um por campo, sumiam as duas. E a
                    # busca saía sem data, devolvendo tela vazia sem erro nenhum.
                    # Para fechar o calendário, clica-se FORA.
                    await page.evaluate(
                        """(sel) => {
                             const e = document.querySelector(sel);
                             if (!e) return;
                             e.dispatchEvent(new Event('change', {bubbles: true}));
                             e.blur();
                           }""", seletor)
                    try:
                        await page.locator("h1, h2, .filters-form-group__title").first.click(
                            timeout=5000)
                    except Exception:  # noqa: BLE001
                        pass
                    await page.wait_for_timeout(700)
                    if (await page.input_value(seletor, timeout=5000) or "") == valor:
                        break

            conferido = {s: (await page.input_value(s, timeout=5000) or "")
                         for s in ("#inputI", "#inputF")}
            evidence.setdefault("zurich_datas_na_tela", []).append(conferido)
            # 🔴 IGUALDADE, nao "preenchido". `40/82/0261` e nao-vazio e esta errado.
            if conferido["#inputI"] != de or conferido["#inputF"] != ate:
                raise RuntimeError(
                    f"o formulario nao aceitou as datas: pedi {de} a {ate}, "
                    f"ficou {conferido['#inputI']} a {conferido['#inputF']}")

            for sel in ("button:has-text('Buscar')", "a:has-text('Buscar')",
                        "input[value='Buscar']"):
                alvo = page.locator(sel).first
                if await alvo.count():
                    await alvo.click(timeout=12000)
                    break
            await page.wait_for_timeout(6000)
            linhas = await page.evaluate(_JS_LINHAS_DO_RESULTADO)
        except Exception as exc:  # noqa: BLE001
            evidence.setdefault("zurich_busca_erro", []).append(
                f"{type(exc).__name__}: {str(exc)[:90]}")
            linhas = 0
        evidence.setdefault("zurich_busca_na_tela", []).append(
            {"tentativa": tentativa, "linhas": linhas})
        if linhas:
            break
        # 🔴 zero linhas na tela = clicar em Buscar de novo. O portal e instavel
        # e devolve vazio de vez em quando; o founder descreveu exatamente isso.
        await page.wait_for_timeout(PAUSA_APOS_RECUSA_MS)
    return linhas


async def baixar_boleto_pela_pagina(page, item: Dict[str, Any],
                                    params: Dict[str, Any],
                                    evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Chama `GerarBoleto2` — a **função da própria página** — e pega o download.

    🔴 É o caminho que faltava, e ele dispensa tudo o que estava dando errado.

    📊 O botão `2ªVia` da lista faz exatamente isto: `data-bind="click:
    GerarBoleto2"`. A função está no view model do Knockout e lê **sete campos**
    do item que recebe:

        payment_no · numeroApolice · numeroEndossoSPY · ramo
        numeroPrestacao · numeroCertificado · dataVencimento

    Todos vêm da lista que a journey já leu. Então monta-se um objeto simples e
    chama-se a função — sem tabela renderizada, sem máscara de data, sem
    datepicker e sem clique.

    Por que isso é melhor que reproduzir a chamada:
    📊 Reproduzir a URL à mão devolveu **404** em todas as variações testadas —
    inclusive pelo `$.ajax` do próprio jQuery. Aqui quem monta o pedido é o
    código do portal, com o estado dele (`SearchObject.Sucursal`), e não a
    minha reconstrução.
    """
    dados = b""
    try:
        async with page.expect_download(timeout=90000) as espera:
            erro_js = await page.evaluate(
                """({item}) => {
                  if (!window.ko) return 'sem knockout na pagina';
                  const el = document.querySelector('#inputI');
                  if (!el) return 'a tela de parcelas nao esta aberta';
                  const vm = ko.dataFor(el);
                  if (!vm || typeof vm.GerarBoleto2 !== 'function')
                    return 'GerarBoleto2 nao existe neste view model';
                  vm.GerarBoleto2(item);
                  return '';
                }""",
                {"item": {
                    "payment_no": item.get("payment_no"),
                    "numeroApolice": item.get("numero_apolice"),
                    "numeroEndossoSPY": item.get("endosso"),
                    "ramo": item.get("ramo"),
                    "numeroPrestacao": item.get("parcela"),
                    "numeroCertificado": item.get("certificado"),
                    # 🔴 `GerarBoleto2` passa este campo por `FormatDate`, que é
                    # `moment(...).format('DD/MM/YYYY')` — e o moment entende
                    # tanto `/Date(ms)/` quanto `dd/MM/aaaa`.
                    "dataVencimento": item.get("vencimento_br"),
                }})
            if erro_js:
                return {"ok": False, "reason": erro_js}
        download = await espera.value
        caminho_tmp = await download.path()
        dados = open(caminho_tmp, "rb").read() if caminho_tmp else b""
    except Exception as exc:  # noqa: BLE001
        return {"ok": False,
                "reason": f"GerarBoleto2 nao produziu download: {type(exc).__name__}: "
                          f"{str(exc)[:120]}"}

    if not dados.startswith(b"%PDF"):
        return {"ok": False,
                "reason": f"o download nao e um PDF (comeca com {dados[:8]!r})"}

    caminho = build_boleto_storage_path(
        company_id=str(params.get("_company_id") or "company"),
        job_id=str(params.get("_job_id") or "job"),
        portal_key=str(params.get("_portal_key") or "zurich_corretor"),
        recibo=str(item.get("recibo") or ""))
    evidence.setdefault("notas", []).append(
        f"boleto Zurich baixado por GerarBoleto2 — {len(dados)} bytes")
    upload = params.get("_upload_blob")
    if callable(upload):
        salvo = await upload(caminho, dados, "application/pdf")
        return {"ok": bool(salvo), "storage_path": salvo or caminho,
                "bytes": len(dados), "via": "GerarBoleto2"}
    return {"ok": True, "storage_path": caminho, "bytes": len(dados),
            "via": "GerarBoleto2", "not_uploaded": True}


async def baixar_boleto_clicando(page, item: Dict[str, Any], params: Dict[str, Any],
                                 evidence: Dict[str, Any]) -> Dict[str, Any]:
    """O FALLBACK previsto na SPEC-033: navegação visual, depois da chamada direta.

    📊 O botão da lista é o único caminho que funciona à mão:

        <a class="btn btn--blue btn--small" data-bind="click: GerarBoleto2">2ªVia</a>

    Ele chama a mesma URL, mas por dentro da página, com o estado do Knockout —
    e o download nasce de um Blob (`saveByteArray`), que o navegador salva.
    """
    apolice = str(item.get("numero_apolice") or "")
    parcela = str(item.get("parcela") or "")
    try:
        # a tabela de resultado e a que tem "Segurado" no cabecalho — ver
        # `_JS_LINHAS_DO_RESULTADO`. Procurar em `table tbody tr` acharia linha
        # de outro widget.
        tabela = page.locator("table").filter(has_text="Segurado").filter(
            has_text="Vencimento").first
        if not await tabela.count():
            tabela = page.locator("table").filter(has_text="2ªVia").first
        linha = tabela.locator("tbody tr").filter(has_text=apolice).first
        if not await linha.count():
            return {"ok": False,
                    "reason": f"nao achei a linha da apolice {apolice} na tela"}
        botao = linha.locator("a:has-text('2ªVia')").first
        if not await botao.count():
            return {"ok": False,
                    "reason": f"a linha da apolice {apolice} nao tem botao de 2a via "
                              "(o portal so mostra para boleto)"}
        async with page.expect_download(timeout=60000) as espera:
            await botao.click(timeout=15000)
        download = await espera.value
        caminho_tmp = await download.path()
        dados = open(caminho_tmp, "rb").read() if caminho_tmp else b""
    except Exception as exc:  # noqa: BLE001
        return {"ok": False,
                "reason": f"o clique no 2a via falhou: {type(exc).__name__}: "
                          f"{str(exc)[:120]}"}

    if not dados.startswith(b"%PDF"):
        return {"ok": False,
                "reason": f"o clique baixou algo que nao e PDF ({dados[:8]!r})"}

    caminho = build_boleto_storage_path(
        company_id=str(params.get("_company_id") or "company"),
        job_id=str(params.get("_job_id") or "job"),
        portal_key=str(params.get("_portal_key") or "zurich_corretor"),
        recibo=str(item.get("recibo") or ""))
    evidence.setdefault("notas", []).append(
        f"boleto Zurich baixado pelo CLIQUE — {len(dados)} bytes")
    upload = params.get("_upload_blob")
    if callable(upload):
        salvo = await upload(caminho, dados, "application/pdf")
        return {"ok": bool(salvo), "storage_path": salvo or caminho,
                "bytes": len(dados), "via": "clique-2a-via", "parcela": parcela}
    return {"ok": True, "storage_path": caminho, "bytes": len(dados),
            "via": "clique-2a-via", "not_uploaded": True}


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
        # 🔴 A chamada direta não passou. SPEC-033: **navegação visual como
        # fallback**, depois de a cadeia direta falhar — e não em vez dela.
        evidence.setdefault("zurich_fallback", []).append(
            {"recibo": item.get("recibo"), "http_da_chamada_direta": r.get("status")})
        alternativa = await baixar_boleto_pela_pagina(page, item, params, evidence)
        if alternativa.get("ok"):
            return alternativa
        evidence.setdefault("zurich_fallback", []).append(
            {"recibo": item.get("recibo"), "GerarBoleto2": alternativa.get("reason")})
        return await baixar_boleto_clicando(page, item, params, evidence)
    dados, erro = pdf_do_boleto(r.get("json"))
    if erro:
        evidence.setdefault("zurich_fallback", []).append(
            {"recibo": item.get("recibo"), "motivo": erro})
        alternativa = await baixar_boleto_pela_pagina(page, item, params, evidence)
        if alternativa.get("ok"):
            return alternativa
        return await baixar_boleto_clicando(page, item, params, evidence)

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

    # ⚠️ `params.get(...) or 48` transformaria um **0 configurado** em 48, porque
    # zero e falso em Python — a corretora pediria "cobra no mesmo dia" e levaria
    # dois dias de carencia sem nenhum aviso. Config ignorada em silencio e a
    # mesma classe de defeito que esta SPEC persegue.
    bruto = params.get("horas_minimas_atraso")
    try:
        horas = int(bruto) if bruto is not None and str(bruto) != "" else 48
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

    # 📊 Deixa a TABELA renderizada antes de tentar baixar: o botão `2ªVia` só
    # existe na tela, e é ele o caminho que funciona quando a chamada direta
    # recusa. Fazer a busca aqui custa uma vez, não uma por boleto.
    if a_baixar:
        # 📊 Basta a TELA estar aberta: `GerarBoleto2` mora no view model dela e
        # nao depende da tabela renderizada. A busca visual so e tentada como
        # ultimo recurso, dentro de `baixar_boleto_clicando`.
        try:
            if "ParcelaVencidaCorretor" not in str(getattr(page, "url", "")):
                await page.goto(ZURICH_PARCELAS, wait_until="domcontentloaded",
                                timeout=60000)
            await page.wait_for_selector("#inputI", state="visible", timeout=40000)
            await page.wait_for_timeout(2500)
            evidence["zurich_tela_parcelas"] = "aberta"
        except Exception:  # noqa: BLE001
            evidence["zurich_tela_parcelas"] = "nao abriu"

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
