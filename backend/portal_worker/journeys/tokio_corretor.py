"""Journey Tokio Marine — Portal Parceiros (cobrança).

O que ela faz para a corretora
==============================
Entra no Portal Parceiros com o login da corretora, lê o relatório **Clientes
inadimplentes**, separa quem está em atraso e baixa o boleto de cada um. Não
envia nada — quem envia é o Auxiliar de Cobrança, depois, em horário comercial
e com o freio de vazão da SPEC-063.

A Tokio é a mais limpa das três — e por quê
===========================================
📊 Medido no HAR do founder (12/08/2026). Allianz e HDI obrigaram a raspar HTML.
A Tokio não: por baixo da tela existe um **BFF com GraphQL e REST em JSON**.

    Allianz     BFF moderno, JSON, Bearer JWT
    HDI         app legado, HTML iso-8859-1, sessão por query param
    Tokio       BFF GraphQL + REST JSON, sessão por COOKIE  ← esta

A cadeia inteira, com os corpos reais medidos:

    1) POST /portais/bff/v1/clientes/graphql   {buscarUsuario}
       -> codigoInterno (o código do corretor, 67828)

    2) POST /portais/bff/v1/clientes/graphql   {buscarRamos}
       -> os ~280 códigos de ramo que o relatório EXIGE receber

    3) POST /portais/bff/v1/clientes/reports/parcelas/xml
       -> O RELATÓRIO INTEIRO, em XML, com a TESTEMUNHA embutida

    4) GET  /portais/visao-cliente-corretor/detalhe/apolice/<doc>/<idePol>
       -> HTML do detalhe; dele sai o `numeroTitulo` de cada parcela

    5) POST /portais/bff/v1/consulta-unica/financeiro/prorrogacao
       {numeroTitulo, numeroParcela}  -> datas permitidas + juros/multa de cada

    6) POST /portais/bff/v1/consulta-unica/financeiro/boleto
       {numeroTitulo, dataNovoVencimento}  -> `cUrlCSF` = a URL do PDF

    7) GET  cUrlCSF  (outro host: portal.tokiomarine.com.br)  -> o PDF

Por que o passo 3 vale mais que a tela
---------------------------------------
O XML vem com **os totais no mesmo documento**:

    <quantidadeClientes>5</quantidadeClientes>
    <quantidadeParcelas>5</quantidadeParcelas>

📊 Se o parser ler 4 registros e o documento disser 5, ele **sabe** que perdeu
um. Na HDI isso só deu para aproximar por heurística de bytes. Aqui a própria
seguradora entrega a conferência — e a SPEC-070 §2 proíbe seguradora que cai em
silêncio. Ela é conferida em `_conferir_testemunha`.

E o XML não tem notação científica. O GraphQL devolve `idepol: 7.5104431E7` e
`apolice: 3.6731739E7` — números JS. O XML devolve `75104431` e `36731739`,
texto. Um `int(float(...))` a mais é um lugar a mais para perder dígito.

🔴 Débito automático: nós NUNCA geramos boleto
-----------------------------------------------
📊 Texto literal do modal do portal:

    "Se você está solicitando o boleto para uma apólice com forma de pagamento
     débito em conta / cartão. Esta alteração é permitida SOMENTE UMA VEZ
     durante a vigência do seguro. Se desejar alterar as demais parcelas para
     boleto, deverá ser realizado o ENDOSSO de alteração da forma de pagamento."

Clicar ali muda a forma de pagamento da parcela, **consome** um direito que não
volta e é irreversível sem endosso. É ação transacional — SPEC-033 manda parar
antes de finalizar. Vai para tarefa humana.

E a regra de negócio do founder (12/08/2026) é ainda mais restritiva:

    As atendentes AGUARDAM todas as tentativas de débito se esgotarem — na
    Tokio e em qualquer outra seguradora. Só depois disso mandam boleto.

Por isso `repique = S` ("a Tokio ainda vai tentar debitar de novo") não é só um
aviso: é motivo de segurar. Cobrar hoje quem será debitado amanhã é constranger
o segurado por um problema que não existe mais.

🔴 O telefone do portal não serve para WhatsApp
------------------------------------------------
📊 O mesmo segurado, medido nas duas telas em 12/08/2026:

    XML do relatório     numeroTelefone1 = 99381576    numeroTelefone3 = 991314388
    tela de detalhe      Tel. Fixo       = 99381576    Tel. Celular    = 999381576

`999381576` é literalmente `9 + numeroTelefone1` — a tela CALCULA o celular
prefixando um 9 no fixo. E `991314388`, que o relatório traz como terceiro
telefone, é **outro número**. As duas telas discordam sobre o mesmo cliente.

Então nenhum dos dois vira destinatário. O que a journey entrega é o
`cpf_cnpj` — e o WhatsApp sai do sistema de gestão da corretora (InfoCap,
Quiver), por `_resolve_customer_phone`, que é de onde as atendentes já tiram
hoje. Os telefones do portal ficam guardados só como pista para a tarefa humana.
"""
from __future__ import annotations

import base64
import html as html_lib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from portal_worker.journeys import JourneyResult

TOKIO_BASE = "https://portalparceiros.tokiomarine.com.br"
TOKIO_LOGIN_URL = TOKIO_BASE + "/"
TOKIO_HOME = TOKIO_BASE + "/group/portal-corretor"

BFF_GRAPHQL = "/portais/bff/v1/clientes/graphql"
BFF_RELATORIO_XML = "/portais/bff/v1/clientes/reports/parcelas/xml"
BFF_PRORROGACAO = "/portais/bff/v1/consulta-unica/financeiro/prorrogacao"
BFF_BOLETO = "/portais/bff/v1/consulta-unica/financeiro/boleto"
BFF_PIX_VALIDAR = "/portais/bff/v1/consulta-unica/pix/validar"
DETALHE_APOLICE = "/portais/visao-cliente-corretor/detalhe/apolice"

# 📊 O relatório aceita data no formato DD-MM-YYYY e a tela manda `01-01-1901`
# como início — ou seja, "desde sempre". Mantemos: quem decide o recorte de
# atraso é o serviço (48 h), não a janela do portal.
DATA_INICIO_TUDO = "01-01-1901"

# Formas de pagamento que NÃO geram boleto por regra da seguradora (§ docstring).
# 📊 Valores lidos do campo `formaPagto` do relatório: FICHA · DÉBITO.
# Cartão aparece em relatório separado, mas o nome é normalizado aqui do mesmo
# jeito para o dia em que aparecer nesta lista.
FORMAS_SEM_BOLETO = ("debito", "cartao", "credito")
FORMA_COM_BOLETO = "ficha"

# Marca que o serviço de cobrança reconhece para tirar o item da fila de envio
# e transformá-lo em tarefa humana (billing_collection.MARCA_REGRA_DA_SEGURADORA).
MARCA_REGRA = "nao emite 2a via de boleto"

# 🚫 Telas que ESCREVEM. A journey nunca as chama, e o teste prova que nenhuma
# aparece no código.
ROTAS_PROIBIDAS = (
    "/corp/conta-corrente-front",          # transferir, recuperar, migrar modelo
    "/massificados/auto/varejo/endosso",   # endosso
    "/EndossoRDService",
    "/reports/parcelas/email",             # dispara e-mail de verdade
)

_RE_TAG = re.compile(r"<[^>]+>")
# O botão de boleto de cada parcela carrega numeroTitulo e numeroParcela.
# 📊 Do HTML real, e repare nas aspas::
#
#     onclick="VisaoUnicaClienteJS.carregarVencimentoPermitidoBoleto(
#              &#39;7231787615&#39;,&#39;3&#39;,&#39;null&#39;,...)"
#
# Dentro de um atributo `onclick` as aspas simples vêm **como entidade HTML**.
# Um padrão que só aceita `'` casa zero linhas — e o sintoma é "não achei a
# parcela", que se parece com carteira em dia. Aceita as duas formas.
_ASPA = r"""(?:['"]|&#0*39;|&#x0*27;|&apos;|&quot;)"""
_RE_BOTAO_BOLETO = re.compile(
    rf"""carregarVencimentoPermitidoBoleto\s*\(\s*{_ASPA}(\d+){_ASPA}\s*,\s*{_ASPA}(\d+){_ASPA}""")
# Cada linha da tabela de parcelas: <tr id="tr-parcela-3" data-numerotitulo="7231787615">
_RE_LINHA_PARCELA = re.compile(
    r"""<tr\b[^>]*id\s*=\s*["']tr-parcela-(\d+)["'][^>]*data-numerotitulo\s*=\s*["'](\d+)["'](.*?)</tr>""",
    re.IGNORECASE | re.DOTALL)
_RE_CELULA = re.compile(r"<td\b.*?</td>", re.IGNORECASE | re.DOTALL)
_RE_DATA_BR = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")


# --------------------------------------------------------------------------
# texto, números e datas
# --------------------------------------------------------------------------
def _norm(texto: Any) -> str:
    s = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower()


def _digits(valor: Any) -> str:
    return re.sub(r"\D+", "", str(valor or ""))


def _sem_tags(fragmento: str) -> str:
    return html_lib.unescape(_RE_TAG.sub(" ", fragmento or "")).strip()


def _valor_num(texto: Any) -> Optional[float]:
    """`1191.89` (XML) e `R$ 1.191,89` (tela) viram o mesmo float."""
    bruto = str(texto or "").strip()
    if not bruto:
        return None
    limpo = re.sub(r"[^\d,.\-]", "", bruto)
    if "," in limpo:  # formato brasileiro
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return None


def _data_br_para_iso(texto: Any) -> str:
    m = _RE_DATA_BR.search(str(texto or ""))
    if not m:
        return ""
    d, mth, a = m.group(1).split("/")
    return f"{a}-{mth}-{d}"


def _hoje_ddmmaaaa() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%d-%m-%Y")


def vencido_ha_mais_de(vencimento_iso: str, horas: int, *, agora: Optional[datetime] = None) -> bool:
    """A carência de 48 h, aplicada sobre a data ISO já normalizada."""
    if not vencimento_iso:
        return False
    try:
        venc = datetime.strptime(vencimento_iso[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    ref = (agora or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return venc <= ref - timedelta(hours=max(0, int(horas)))


# --------------------------------------------------------------------------
# o relatório XML — leitura pura, testável com fixture
# --------------------------------------------------------------------------
def _texto_tag(bloco: str, tag: str) -> str:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", bloco, re.IGNORECASE | re.DOTALL)
    return html_lib.unescape(m.group(1)).strip() if m else ""


def extrair_inadimplentes(xml: str) -> List[Dict[str, Any]]:
    """Cada `<clientesInadimplentes>` vira um item — sem julgar nada ainda."""
    itens: List[Dict[str, Any]] = []
    for bloco in re.findall(r"<clientesInadimplentes>(.*?)</clientesInadimplentes>",
                            xml or "", re.IGNORECASE | re.DOTALL):
        campo = {t: _texto_tag(bloco, t) for t in (
            "idePol", "cpfCnpjCliente", "nmCliente", "cdApoliceTmsr", "cdEndosso",
            "cdRamo", "cdRamoTmsr", "codModuloProduto", "codigoNegocio", "dtVencimento",
            "dtVigenciaProporcional", "formaPagto", "motivo", "nroParcela",
            "premioParcela", "comissaoParcela", "repique", "tipo", "tipoApolice",
            "cdCorretor", "nomeCorretor", "numCert", "numOper", "ideFact", "linha",
            "dddTelefone1", "numTelefone1", "dddTelefone2", "numTelefone2",
            "dddTelefone3", "numTelefone3",
        )}
        if not campo["idePol"]:
            continue
        forma = _norm(campo["formaPagto"])
        vencimento = _data_br_para_iso(campo["dtVencimento"])
        itens.append({
            "portal": "tokiomarine_corretor",
            "ide_pol": campo["idePol"],
            "cpf_cnpj": _digits(campo["cpfCnpjCliente"]),
            "cliente_nome": campo["nmCliente"],
            "apolice_susep": _digits(campo["cdApoliceTmsr"]),
            "endosso": campo["cdEndosso"],
            "ramo": campo["cdRamo"],
            "codigo_modulo_produto": campo["codModuloProduto"],
            "codigo_negocio": campo["codigoNegocio"],
            "vencimento": vencimento,
            "vigencia_proporcional": _data_br_para_iso(campo["dtVigenciaProporcional"]),
            "forma_pagamento": campo["formaPagto"],
            "motivo_portal": campo["motivo"],
            "parcela": campo["nroParcela"],
            "valor": _valor_num(campo["premioParcela"]),
            "comissao": _valor_num(campo["comissaoParcela"]),
            "repique": (campo["repique"] or "").strip().upper(),
            "tipo_apolice": campo["tipoApolice"],
            "codigo_corretor": campo["cdCorretor"],
            # 🔴 telefones do portal: PISTA para a tarefa humana, NUNCA destinatário.
            # O WhatsApp sai do sistema de gestão, por cpf_cnpj (§ docstring).
            "telefones_portal": [t for t in (
                (campo["dddTelefone1"] + campo["numTelefone1"]) if campo["numTelefone1"] else "",
                (campo["dddTelefone2"] + campo["numTelefone2"]) if campo["numTelefone2"] else "",
                (campo["dddTelefone3"] + campo["numTelefone3"]) if campo["numTelefone3"] else "",
            ) if t],
            # `recibo` é a chave estável do item na fila de cobrança e no bucket.
            "recibo": f"{_digits(campo['cdApoliceTmsr'])}-{campo['nroParcela'] or '0'}",
            "gera_boleto": forma.startswith(FORMA_COM_BOLETO),
        })
    return itens


def totais_do_relatorio(xml: str) -> Dict[str, Any]:
    """A testemunha: o que a PRÓPRIA Tokio diz que mandou."""
    return {
        "clientes": _texto_tag(xml, "quantidadeClientes"),
        "parcelas": _texto_tag(xml, "quantidadeParcelas"),
        "premios": _valor_num(_texto_tag(xml, "valorPremios")),
        "comissao_nao_recebida": _valor_num(_texto_tag(xml, "comissaoNaoRecebida")),
        "primeira_parcela_pendente": _texto_tag(xml, "primeiraParcelaPendente"),
        "demais_parcelas_pendentes": _texto_tag(xml, "demaisParcelasPendentes"),
    }


def _conferir_testemunha(xml: str, itens: List[Dict[str, Any]]) -> Optional[str]:
    """Devolve o RECADO do problema, ou None se o número bate.

    Ler menos linhas do que o documento declara é perder inadimplente **em
    silêncio** — o pecado que a SPEC-070 §2 proíbe. Aqui dá para provar.
    """
    declarado = _digits(totais_do_relatorio(xml).get("parcelas"))
    if not declarado:
        return None  # sem testemunha não há o que conferir; não inventamos falha
    if int(declarado) != len(itens):
        return (f"o relatorio da Tokio declara {declarado} parcela(s) e eu li {len(itens)} "
                "— NAO afirmo nada sobre a carteira ate isso bater")
    return None


def motivo_para_reter(item: Dict[str, Any]) -> str:
    """Por que ESTE item não pode virar cobrança automática. '' = pode."""
    if not item.get("gera_boleto"):
        return (f"{MARCA_REGRA} — forma de pagamento {item.get('forma_pagamento') or '?'}"
                + (f"; {item['motivo_portal']}" if item.get("motivo_portal") else ""))
    if item.get("repique") == "S":
        # 📊 Decisão do founder (12/08/2026): as atendentes esperam TODAS as
        # tentativas de débito se esgotarem antes de mandar boleto.
        return "a Tokio ainda vai tentar debitar de novo (repique = S) — aguardar esgotar"
    return ""


# --------------------------------------------------------------------------
# a tela de detalhe — só dela sai o numeroTitulo
# --------------------------------------------------------------------------
def url_detalhe(cpf_cnpj: str, ide_pol: str) -> str:
    """📊 Do HAR real: /detalhe/apolice/00861449959/75111063?cdpn=null

    O documento vai **sem pontuação e com os zeros à esquerda** (11 dígitos para
    CPF). ❓ O caso CNPJ (14 dígitos) ainda não foi medido — o formato é o mesmo
    aqui, e o teste de fumaça da Fase 4 confirma.
    """
    return f"{DETALHE_APOLICE}/{_digits(cpf_cnpj)}/{_digits(ide_pol)}?cdpn=null"


def extrair_parcelas_do_detalhe(html: str) -> List[Dict[str, Any]]:
    """Lê a tabela `Dados Parcela`: nº, título, vencimento, situação, botão."""
    linhas: List[Dict[str, Any]] = []
    for numero, titulo, corpo in _RE_LINHA_PARCELA.findall(html or ""):
        celulas = [_sem_tags(c) for c in _RE_CELULA.findall(corpo)]
        texto = " ".join(celulas)
        botao = _RE_BOTAO_BOLETO.search(corpo)
        linhas.append({
            "parcela": numero,
            "numero_titulo": titulo,
            "vencimento": _data_br_para_iso(texto),
            "situacao": next((c for c in celulas if _norm(c) in ("pago", "pendente", "cancelado")), ""),
            "tem_botao_boleto": bool(botao),
            "titulo_do_botao": botao.group(1) if botao else "",
        })
    return linhas


def linha_da_parcela(linhas: List[Dict[str, Any]], numero_parcela: Any) -> Optional[Dict[str, Any]]:
    """A linha, exista botão ou não. Serve para EXPLICAR a ausência."""
    alvo = _digits(numero_parcela)
    return next((l for l in linhas if l.get("parcela") == alvo), None)


def porque_sem_boleto(linhas: List[Dict[str, Any]], numero_parcela: Any,
                      dias_atraso: Optional[int]) -> str:
    """Traduz a ausência do botão para uma frase que a atendente usa.

    🔴 As duas ausências são coisas MUITO diferentes, e "não achei a parcela"
    escondia as duas:

        a linha nem existe      → a tela mudou, ou o relatório e o detalhe
                                  discordam. É defeito nosso, e alguém precisa
                                  olhar.
        a linha existe sem botão → **a Tokio não emite mais 2ª via para essa
                                  parcela**. Não é defeito: é a seguradora
                                  dizendo não. A atendente tem de negociar.

    📊 Medido em 12/08/2026, na mesma apólice, no mesmo instante:

        parcela 11 · venceu 17/07 · 26 dias de atraso · Pendente · SEM botão
        parcela 12 · vence  19/08 · a vencer          · Pendente · COM botão

    💭 A causa provável é o prazo que o próprio boleto imprime —
    `NÃO RECEBER APÓS 15 DIAS DO VENCIMENTO`. Um ponto além do limite e outro
    dentro (7 dias, com botão) **são compatíveis** com essa explicação, mas não
    a provam: falta um caso entre 15 e 26 dias. Por isso a frase abaixo diz o
    FATO (dias de atraso, sem 2ª via) e não a hipótese.
    """
    linha = linha_da_parcela(linhas, numero_parcela)
    if linha is None:
        return (f"a parcela {numero_parcela} do relatorio nao aparece na tela de detalhe "
                "— o portal precisa ser conferido")
    quanto = f" (vencida ha {dias_atraso} dias)" if isinstance(dias_atraso, int) else ""
    return (f"{MARCA_REGRA} — a Tokio nao oferece 2a via para a parcela "
            f"{numero_parcela}{quanto}; a equipe precisa tratar com a seguradora")


def escolher_parcela(linhas: List[Dict[str, Any]], numero_parcela: Any) -> Optional[Dict[str, Any]]:
    """A parcela do relatório — não "qualquer uma pendente".

    🔴 Isto existe por causa de um caso real. 📊 KELLY tinha as parcelas 3 E 4
    com situação `Pendente` em 12/08/2026: a 3 vencia em 10/08 (atrasada) e a 4
    em 10/09 (ainda a vencer). Pegar "a primeira pendente" acerta às vezes;
    pegar "a última" acerta às vezes. Só o número que veio do relatório acerta
    sempre — e foi por não fazer isso que o boleto saiu da parcela errada.
    """
    alvo = _digits(numero_parcela)
    for linha in linhas:
        if linha.get("parcela") == alvo and linha.get("tem_botao_boleto"):
            return linha
    return None


def escolher_vencimento(prorrogacao: Dict[str, Any]) -> Dict[str, Any]:
    """A data mais próxima da lista = o menor acréscimo possível.

    📊 O que o portal devolve, para uma parcela ainda a vencer::

        {"DataVencimentoOriginal": "10/09/2026",
         "LinhaDigitavel": "03399.53465 54100.072310 78760.701017 1 ...",
         "ListaVencimentosProrrogacao": [
            {"dataComparacao": "2026-09-10", "valorJuros": 0, "valorMulta": 0,
             "valorTotalProrrogacao": 343.53}],
         "ValorOriginal": 343.53}

    Para parcela **já vencida** a lista traz só datas FUTURAS — a data original,
    que passou, não é opção. Ou seja: para quem já está em atraso **não existe
    boleto sem multa e sem juros no portal**. O que existe é a data mais
    próxima, que é a de menor acréscimo. É essa que pegamos.

    E não recalculamos nada: multa e juros são o número que a Tokio imprime.
    Reproduzir a fórmula seria criar um segundo motor de cálculo financeiro —
    errar centavos numa cobrança é pior do que não mandar (CLAUDE.md §12.1).
    """
    lista = prorrogacao.get("ListaVencimentosProrrogacao") or []
    validas = [d for d in lista if isinstance(d, dict) and d.get("dataComparacao")]
    if not validas:
        return {}
    return sorted(validas, key=lambda d: str(d.get("dataComparacao")))[0]


# --------------------------------------------------------------------------
# chamadas ao portal
# --------------------------------------------------------------------------
async def _fetch_json(page, caminho: str, *, metodo: str = "POST",
                      corpo: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Chama o BFF de DENTRO da página (mesma origem, cookie da sessão)."""
    try:
        r = await page.evaluate(
            """async ({url, metodo, corpo}) => {
              const init = {method: metodo, credentials: 'include',
                            headers: {'Accept': 'application/json'}};
              if (corpo !== null) {
                init.headers['Content-Type'] = 'application/json';
                init.body = JSON.stringify(corpo);
              }
              const r = await fetch(url, init);
              let t = '';
              try { t = await r.text(); } catch (e) { t = ''; }
              return {ok: r.ok, status: r.status, text: t};
            }""",
            {"url": caminho, "metodo": metodo, "corpo": corpo},
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": 0, "text": "", "erro": type(exc).__name__}
    texto = r.get("text") or ""
    try:
        r["json"] = json.loads(texto) if texto.lstrip()[:1] in ("{", "[") else None
    except (ValueError, IndexError):
        r["json"] = None
    return r


async def _graphql(page, operacao: str, query: str,
                   variaveis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    r = await _fetch_json(page, BFF_GRAPHQL, corpo={
        "operationName": operacao, "variables": variaveis or {}, "query": query})
    return ((r.get("json") or {}).get("data") or {}) if r.get("ok") else {}


Q_USUARIO = ("query BuscarUsuario {\n  buscarUsuario {\n    codigoInterno\n"
             "    codigoParceiroNegocioPrimario\n    tipoUsuario\n    nome\n"
             "    nomeParceiroNegocioPrimario\n    __typename\n  }\n}\n")
Q_RAMOS = "query buscarRamos {\n  buscarRamos {\n    codigo\n    nome\n    grupo\n    __typename\n  }\n}\n"


async def _codigo_na_tela(page) -> str:
    """Reserva: o código também está escrito no topo do portal.

    📊 `<span title="67828 - AUTO FLEET R CORRETORA DE SEGUROS LTDA EPP">`. Se o
    BFF não responder, isto ainda permite pedir o relatório — e, mais
    importante, permite dizer QUAL das duas coisas falhou.
    """
    for seletor in (".info-corretor span[title]", ".info-corretor span",
                    "input#codigoInterno"):
        try:
            alvo = page.locator(seletor).first
            if not await alvo.count():
                continue
            bruto = (await alvo.get_attribute("title")
                     or await alvo.get_attribute("value")
                     or await alvo.inner_text()) or ""
            m = re.match(r"\s*(\d{3,8})", bruto.strip())
            if m:
                return m.group(1)
        except Exception:  # noqa: BLE001
            continue
    return ""


async def identificar_corretor(page, evidence: Dict[str, Any]) -> Dict[str, Any]:
    resposta = await _fetch_json(page, BFF_GRAPHQL, corpo={
        "operationName": "BuscarUsuario", "variables": {}, "query": Q_USUARIO})
    dados = (((resposta.get("json") or {}).get("data") or {}).get("buscarUsuario")) or {}
    evidence["tokio_usuario"] = {
        "codigo_interno": dados.get("codigoInterno"),
        "tipo": dados.get("tipoUsuario"),
        "corretora": dados.get("nomeParceiroNegocioPrimario"),
    }
    if not dados.get("codigoInterno"):
        # Diz POR QUE falhou, em vez de deixar a hipótese aberta: HTTP recusado
        # é uma coisa; HTTP 200 com corpo de login é outra bem diferente.
        evidence["tokio_usuario_falhou"] = {
            "status": resposta.get("status"),
            "bytes": len(resposta.get("text") or ""),
            "inicio": (resposta.get("text") or "")[:160],
            "url_atual": str(getattr(page, "url", ""))[:160],
        }
        na_tela = await _codigo_na_tela(page)
        if na_tela:
            evidence["tokio_usuario"]["codigo_interno"] = na_tela
            evidence["tokio_usuario"]["origem"] = "topo da tela (BFF nao respondeu)"
            return {"codigoInterno": na_tela}
    return dados


async def listar_ramos(page, evidence: Dict[str, Any]) -> List[str]:
    """O relatório EXIGE a lista de ramos. Ela é lida, nunca chutada.

    Fixar ~280 códigos aqui dentro significaria que uma seguradora que criar um
    ramo novo some da varredura sem avisar — e essa é exatamente a falha que a
    SPEC-070 proíbe. O portal publica a lista; nós lemos a dele.
    """
    ramos = (await _graphql(page, "buscarRamos", Q_RAMOS)).get("buscarRamos") or []
    codigos = [str(r.get("codigo")) for r in ramos
               if isinstance(r, dict) and str(r.get("codigo") or "").strip()]
    evidence["tokio_ramos"] = len(codigos)
    return codigos


async def baixar_relatorio(page, corretor: str, ramos: List[str],
                           evidence: Dict[str, Any]) -> str:
    corpo = {
        "corretores": [str(corretor).zfill(6)],
        "dataInicio": DATA_INICIO_TUDO,
        "dataFim": _hoje_ddmmaaaa(),
        "parceiros": [],
        "ramos": ramos,
    }
    r = await _fetch_json(page, BFF_RELATORIO_XML, corpo=corpo)
    xml = r.get("text") or ""
    evidence["tokio_relatorio"] = {"status": r.get("status"), "bytes": len(xml),
                                   "corretor": corpo["corretores"][0]}
    return xml


async def numero_titulo_da_parcela(page, item: Dict[str, Any],
                                   evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Abre o detalhe da apólice e devolve a linha da parcela do relatório."""
    r = await _fetch_json(page, url_detalhe(item.get("cpf_cnpj"), item.get("ide_pol")),
                          metodo="GET", corpo=None)
    html = r.get("text") or ""
    linhas = extrair_parcelas_do_detalhe(html)
    escolhida = escolher_parcela(linhas, item.get("parcela"))
    nota = {"recibo": item.get("recibo"), "status": r.get("status"),
            "linhas": len(linhas), "achou_parcela": bool(escolhida)}
    if not escolhida:
        # "Não achei" é diagnóstico pela metade — e cada hipótese custa uma
        # visita, num portal que trava depois de ~4. Guarda só número de parcela
        # e situação: nenhum dado do segurado.
        dias = _dias_de_atraso(item.get("vencimento"))
        nota["pedi_a_parcela"] = str(item.get("parcela") or "")
        nota["dias_de_atraso"] = dias
        nota["linhas_lidas"] = [{"n": l["parcela"], "situacao": l["situacao"],
                                 "botao": l["tem_botao_boleto"]} for l in linhas]
        evidence.setdefault("tokio_detalhes", []).append(nota)
        return {"_porque": porque_sem_boleto(linhas, item.get("parcela"), dias)}
    evidence.setdefault("tokio_detalhes", []).append(nota)
    return escolhida


def _dias_de_atraso(vencimento_iso: Any) -> Optional[int]:
    try:
        venc = datetime.strptime(str(vencimento_iso)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    return (datetime.now(timezone.utc) - venc).days


async def baixar_boleto(page, item: Dict[str, Any], params: Dict[str, Any],
                        evidence: Dict[str, Any]) -> Dict[str, Any]:
    """prorrogação -> boleto -> PDF. Três chamadas, nenhuma delas escreve."""
    linha = await numero_titulo_da_parcela(page, item, evidence)
    titulo = str(linha.get("numero_titulo") or "").strip()
    if not titulo:
        return {"ok": False, "reason": linha.get("_porque")
                or "nao achei a parcela do relatorio na tela de detalhe"}

    r1 = await _fetch_json(page, BFF_PRORROGACAO, corpo={
        "numeroTitulo": titulo, "numeroParcela": str(item.get("parcela") or "")})
    prorrogacao = r1.get("json") or {}
    if not prorrogacao.get("FlagSucesso"):
        return {"ok": False, "reason": str(prorrogacao.get("MensagemErro") or
                                           f"prorrogacao recusada (http {r1.get('status')})")[:180]}

    escolha = escolher_vencimento(prorrogacao)
    if not escolha:
        return {"ok": False, "reason": "a Tokio nao ofereceu nenhuma data de vencimento"}

    r2 = await _fetch_json(page, BFF_BOLETO, corpo={
        "numeroTitulo": titulo, "dataNovoVencimento": str(escolha.get("dataComparacao"))})
    boleto = r2.get("json") or {}
    url_pdf = str(boleto.get("cUrlCSF") or "").strip()
    if not url_pdf:
        return {"ok": False, "reason": str(boleto.get("cDescRetCode") or
                                           f"boleto sem URL de PDF (http {r2.get('status')})")[:180]}

    dados = await _bytes_do_pdf(page, url_pdf)
    if not dados.startswith(b"%PDF"):
        return {"ok": False, "reason": "o download nao devolveu um PDF"}

    caminho = build_boleto_storage_path(
        company_id=str(params.get("_company_id") or "company"),
        job_id=str(params.get("_job_id") or "job"),
        portal_key=str(params.get("_portal_key") or "tokiomarine_corretor"),
        recibo=str(item.get("recibo") or ""),
    )
    # A linha digitável vem de graça na resposta e o cliente paga pelo app do
    # banco sem abrir anexo. Guardamos; quem decide usar é o serviço de envio.
    extra = {
        "linha_digitavel": prorrogacao.get("LinhaDigitavel") or "",
        "vencimento_boleto": escolha.get("dataComparacao"),
        "valor_original": prorrogacao.get("ValorOriginal"),
        "valor_cobrado": escolha.get("valorTotalProrrogacao"),
        "multa": escolha.get("valorMulta"),
        "juros": escolha.get("valorJuros"),
    }
    upload = params.get("_upload_blob")
    evidence.setdefault("notas", []).append(f"boleto Tokio baixado — {len(dados)} bytes")
    if callable(upload):
        salvo = await upload(caminho, dados, "application/pdf")
        return {"ok": bool(salvo), "storage_path": salvo or caminho,
                "bytes": len(dados), "via": "bff_json", **extra}
    return {"ok": True, "storage_path": caminho, "bytes": len(dados),
            "via": "bff_json", "not_uploaded": True, **extra}


async def _bytes_do_pdf(page, url: str) -> bytes:
    """O PDF mora em OUTRO host (portal.tokiomarine.com.br).

    `fetch` de dentro da página seria cross-origin e o navegador barraria. O
    contexto de requisição do Playwright não passa por CORS e carrega os mesmos
    cookies — é o caminho certo aqui. O `fetch` fica como reserva para o dia em
    que a Tokio mover o arquivo para o mesmo domínio.
    """
    try:
        r = await page.request.get(url, timeout=45000)
        if r.ok:
            return await r.body()
    except Exception:  # noqa: BLE001
        pass
    try:
        b64 = await page.evaluate(
            """async (url) => {
              const r = await fetch(url, {credentials: 'include'});
              if (!r.ok) return '';
              const buf = new Uint8Array(await r.arrayBuffer());
              let s = ''; for (const b of buf) s += String.fromCharCode(b);
              return btoa(s);
            }""", url)
        return base64.b64decode(b64 or "")
    except Exception:  # noqa: BLE001
        return b""


def build_boleto_storage_path(*, company_id: str, job_id: str, portal_key: str,
                              recibo: str) -> str:
    seguro = re.sub(r"[^A-Za-z0-9._-]+", "-", str(recibo or "boleto")).strip("-") or "boleto"
    return f"{company_id}/{portal_key}/{job_id}/boleto-{seguro}.pdf"


# --------------------------------------------------------------------------
# login
# --------------------------------------------------------------------------
async def _texto(page) -> str:
    try:
        return await page.inner_text("body", timeout=6000)
    except Exception:  # noqa: BLE001
        return ""


async def _fechar_cookies(page) -> None:
    """A tarja de cookies cobre a parte de baixo e intercepta cliques."""
    for seletor in ("#agreed-cookie", "button#agreed-cookie", "#lgdp-close-desktop"):
        try:
            alvo = page.locator(seletor).first
            if await alvo.count() and await alvo.is_visible():
                await alvo.click(timeout=3000)
                return
        except Exception:  # noqa: BLE001
            continue


async def _entrar_como_corretor(page, evidence: Dict[str, Any]) -> bool:
    """🔴 Depois da senha existe MAIS UMA TELA.

    📊 A Tokio não cai no portal direto: cai num seletor com o card `Corretor`
    e o link `Sair`. Um robô que assume "logou = estou dentro" fica parado nessa
    tela para sempre, e o sintoma é "a varredura não achou ninguém" — que é
    indistinguível de carteira em dia. Por isso ela é um passo explícito.
    """
    for seletor in ("a[href*='/group/portal-corretor']", "text=/^\\s*Corretor\\s*$/",
                    "a:has-text('Corretor')"):
        try:
            alvo = page.locator(seletor).first
            if not await alvo.count():
                continue
            await alvo.click(timeout=8000)
            # Esperar a MARCA de dentro, não o relógio: o clique dispara uma
            # navegação que pode levar segundos e passar por redirect de SSO.
            for marca in MARCAS_DE_DENTRO:
                try:
                    await page.wait_for_selector(marca, state="attached", timeout=25000)
                    evidence["tokio_seletor_portais"] = seletor
                    return True
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            continue
    return False


# 🔴 As marcas que SÓ existem DENTRO do portal. Nenhuma delas aparece no
# seletor de portais nem na tela do SSO.
#
# 📊 A primeira versão deste guarda procurava `a[href*='/group/portal-corretor']`
# — e passou na tela errada, porque **o card "Corretor" do seletor é justamente
# um link para essa URL**. O guarda foi enganado pela própria coisa que ele
# existia para pegar: a varredura seguiu adiante achando que estava dentro, e o
# BFF devolveu vazio. Um marco de chegada não pode ser algo que a porta também
# tem (CLAUDE.md §9.3).
MARCAS_DE_DENTRO = (
    "ul.listaNav a[data-page]",       # o menu de topo (PRODUTOS · FINANCEIRO · …)
    "div.labelSelecaoCorretor",       # a caixa "Código/Corretor"
    "input#codigoInterno",            # o campo escondido das telas internas
)


async def _dentro_do_portal(page) -> bool:
    for seletor in MARCAS_DE_DENTRO:
        try:
            if await page.locator(seletor).count():
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _esperar_formulario(page, timeout: int = 30000) -> bool:
    """🔴 A tela de login é uma SPA — os campos NÃO existem no HTML inicial.

    📊 `portalparceiros` redireciona para um **SSO ForgeRock OpenAM** em outro
    host: `ssoportais3.tokiomarine.com.br/openam/XUI/?realm=TOKIOLFR`. O XUI
    monta o formulário por JavaScript **depois** do `domcontentloaded`.

    Preencher logo após o `goto` encontra zero campos — e o worker devolve
    "campos de login nao encontrados" como se a credencial fosse o problema.
    📊 Foi o que aconteceu na primeira visita real (12/08/2026). Esperar tempo
    fixo também não serve: espera-se o CAMPO, não o relógio.
    """
    for seletor in ("input#idToken2", "input[name='callback_1']", "input[type='password']"):
        try:
            await page.wait_for_selector(seletor, state="visible", timeout=timeout)
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def login_check(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    usuario = str(params.get("username") or "").strip()
    senha = str(params.get("password") or "")
    if not usuario or not senha:
        return JourneyResult(status="failed", message="username/password ausentes para Tokio")

    await page.goto(TOKIO_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    await _fechar_cookies(page)

    if await _dentro_do_portal(page):
        evidence["session_reused"] = True
        return JourneyResult(status="done", captured={"logged_in": True, "portal": "tokiomarine_corretor"})

    evidence["login_form_pronto"] = await _esperar_formulario(page)

    preenchido = 0
    # `idToken1/2` são os ids do OpenAM XUI; `callback_0/1` são os names que ele
    # posta. Os genéricos ficam para o dia em que a Tokio trocar de SSO.
    for seletor in ("input#idToken1", "input[name='callback_0']",
                    "input[name='j_username']", "input[name='username']",
                    "input[type='text']:visible"):
        try:
            alvo = page.locator(seletor).first
            if await alvo.count():
                await alvo.fill(usuario, timeout=8000)
                preenchido += 1
                break
        except Exception:  # noqa: BLE001
            continue
    for seletor in ("input#idToken2", "input[name='callback_1']",
                    "input[name='j_password']", "input[name='password']",
                    "input[type='password']:visible"):
        try:
            alvo = page.locator(seletor).first
            if await alvo.count():
                await alvo.fill(senha, timeout=8000)
                preenchido += 1
                break
        except Exception:  # noqa: BLE001
            continue
    evidence["login_fields_found"] = preenchido
    if preenchido < 2:
        return JourneyResult(status="needs_human", message="campos de login Tokio nao encontrados")

    for seletor in ("input#loginButton_0", "input[name='callback_2']",
                    "button[type='submit']", "input[type='submit']",
                    "button:has-text('Entrar')"):
        try:
            alvo = page.locator(seletor).first
            if await alvo.count():
                await alvo.click(timeout=8000)
                break
        except Exception:  # noqa: BLE001
            continue

    # 🔴 Sair do SSO é o marco, não o `networkidle`. A tela do OpenAM ESCREVE
    # "Acesse os Portais da Tokio Marine" — o mesmo título do seletor de portais
    # que vem depois. Procurar esse texto sem antes checar o host confunde a
    # porta com a sala e clica no lugar errado.
    try:
        await page.wait_for_url(lambda u: "ssoportais" not in str(u), timeout=45000)
    except Exception:  # noqa: BLE001
        pass
    try:
        await page.wait_for_load_state("networkidle", timeout=25000)
    except Exception:  # noqa: BLE001
        pass
    await _fechar_cookies(page)
    evidence["url_pos_login"] = re.sub(r"(?i)(token|goto)=[^&]+", r"\1=<omitido>",
                                       str(getattr(page, "url", "")))[:220]

    texto = _norm(await _texto(page))
    no_sso = "ssoportais" in str(getattr(page, "url", ""))
    if not no_sso and not await _dentro_do_portal(page):
        await _entrar_como_corretor(page, evidence)
        await _fechar_cookies(page)
        texto = _norm(await _texto(page))

    if "senha invalida" in texto or "usuario ou senha" in texto or "credenciais" in texto:
        return JourneyResult(status="failed", message="credenciais rejeitadas pelo portal Tokio")
    if "captcha" in texto:
        return JourneyResult(status="needs_human", message="portal Tokio pediu CAPTCHA/2FA")
    if await _dentro_do_portal(page):
        return JourneyResult(status="done", captured={"logged_in": True, "portal": "tokiomarine_corretor"})
    return JourneyResult(status="needs_human", message="tela pos-login Tokio nao reconhecida")


# --------------------------------------------------------------------------
# a varredura
# --------------------------------------------------------------------------
async def cobranca_sweep(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    entrada = await login_check(page, params, evidence)
    if entrada.status != "done":
        return entrada
    evidence["logged_in"] = True

    usuario = await identificar_corretor(page, evidence)
    corretor = _digits(usuario.get("codigoInterno"))
    if not corretor:
        return JourneyResult(
            status="needs_human", captured={"logged_in": True, "stage": "sem_codigo_corretor"},
            message="entrei na Tokio mas o portal nao devolveu o codigo do corretor")

    # 🔴 GATE DE IDENTIDADE — SPEC-073.
    # `nomeParceiroNegocioPrimario` já era capturado em `evidence` e nunca
    # comparado com o `account_label`: o dado para fechar o gate estava na mão,
    # de graça, desde sempre. Conferir depois do login e antes de baixar
    # qualquer relatório é o momento mais barato de descobrir que se entrou na
    # empresa errada.
    from portal_worker.identidade import conferir_corretora_da_sessao, rotulo_e_generico

    rotulo_tk = str(params.get("account_label") or "")
    lida_tk = str(usuario.get("nomeParceiroNegocioPrimario")
                  or (evidence.get("tokio_usuario") or {}).get("corretora") or "")
    erro_id = conferir_corretora_da_sessao(lida_tk, rotulo_tk, portal="tokio")
    evidence["identidade_corretora"] = {
        "lida": bool(lida_tk),
        "esperado_nomeado": not rotulo_e_generico(rotulo_tk),
        "verificado": not erro_id and not rotulo_e_generico(rotulo_tk),
    }
    if erro_id:
        return JourneyResult(
            status="needs_human",
            captured={"logged_in": True, "stage": "corretora_divergente"},
            message=erro_id)

    ramos = await listar_ramos(page, evidence)
    if not ramos:
        return JourneyResult(
            status="needs_human", captured={"logged_in": True, "stage": "sem_ramos"},
            message="a Tokio nao devolveu a lista de ramos — o relatorio nao pode ser pedido sem ela")

    xml = await baixar_relatorio(page, corretor, ramos, evidence)
    itens = extrair_inadimplentes(xml)
    evidence["tokio_totais"] = totais_do_relatorio(xml)
    evidence["parcelas_lidas"] = len(itens)

    if not itens and len(xml) < 200:
        return JourneyResult(
            status="needs_human", captured={"logged_in": True, "stage": "relatorio_vazio"},
            message="a Tokio nao devolveu o relatorio — NAO afirmo que a carteira esta em dia")

    divergencia = _conferir_testemunha(xml, itens)
    if divergencia:
        return JourneyResult(
            status="needs_human",
            captured={"logged_in": True, "stage": "testemunha_nao_bate", "totais": evidence["tokio_totais"]},
            message=divergencia)

    try:
        horas = int(params.get("horas_minimas_atraso") or 48)
    except (TypeError, ValueError):
        horas = 48

    atrasados = [i for i in itens if vencido_ha_mais_de(i.get("vencimento") or "", horas)]
    evidence["inadimplentes_count"] = len(atrasados)

    # Nada some: quem não pode virar cobrança automática sai MARCADO, com motivo.
    for item in atrasados:
        motivo = motivo_para_reter(item)
        if motivo:
            item["sem_boleto_motivo"] = motivo

    a_baixar = [i for i in atrasados if not i.get("sem_boleto_motivo")]
    retidos = [i for i in atrasados if i.get("sem_boleto_motivo")]
    evidence["inadimplentes_sem_boleto"] = len(retidos)
    evidence["inadimplentes_sample"] = [
        {k: i.get(k) for k in ("recibo", "vencimento", "valor", "parcela",
                               "forma_pagamento", "repique", "sem_boleto_motivo")}
        for i in atrasados[:5]]

    if not atrasados:
        return JourneyResult(
            status="done",
            captured={"logged_in": True, "portal": "tokiomarine_corretor",
                      "inadimplentes": [], "boletos": [], "totais": evidence["tokio_totais"]},
            message=(f"Tokio: {len(itens)} parcela(s) no relatorio, "
                     f"nenhuma em atraso ha mais de {horas}h"))

    try:
        teto = max(1, int(params.get("max_boletos") or params.get("max_boletos_por_execucao") or 50))
    except (TypeError, ValueError):
        teto = 50

    boletos: List[Dict[str, Any]] = []
    for item in a_baixar[:teto]:
        resultado = {"recibo": item.get("recibo"), "ok": False}
        try:
            resultado.update(await baixar_boleto(page, item, params, evidence))
        except Exception as exc:  # noqa: BLE001
            resultado["reason"] = f"{type(exc).__name__}: {str(exc)[:140]}"
        boletos.append(resultado)

    ok = sum(1 for b in boletos if b.get("ok"))
    evidence["boletos_download_ok"] = ok
    evidence["boletos_download_attempts"] = len(boletos)

    # Quem tentou e não trouxe PDF vira tarefa humana AQUI, com o motivo do
    # portal. Deixar só o `ok: false` no relatório fazia o item seguir para a
    # fila de envio e o segurado receber "Segue o boleto abaixo" sem anexo.
    falhou = {str(b.get("recibo")): str(b.get("reason") or "download nao concluido")
              for b in boletos if not b.get("ok")}
    for item in atrasados:
        motivo = falhou.get(str(item.get("recibo")))
        if motivo and not item.get("sem_boleto_motivo"):
            # `porque_sem_boleto` já traz a marca; um erro técnico ainda não.
            item["sem_boleto_motivo"] = (motivo if MARCA_REGRA in motivo
                                         else f"{MARCA_REGRA} — {motivo}")
            retidos.append(item)
    evidence["inadimplentes_sem_boleto"] = len(retidos)

    recado = f"Tokio: {len(atrasados)} inadimplente(s), {ok} boleto(s)"
    if retidos:
        recado += f", {len(retidos)} retido(s) para a equipe humana"
    return JourneyResult(
        status="done",
        captured={"logged_in": True, "portal": "tokiomarine_corretor",
                  "inadimplentes": atrasados, "boletos": boletos,
                  "totais": evidence["tokio_totais"]},
        message=recado)
