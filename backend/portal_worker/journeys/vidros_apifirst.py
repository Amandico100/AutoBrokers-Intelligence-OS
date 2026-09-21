# -*- coding: utf-8 -*-
"""A journey API-first do portal de vidros — SPEC-074 + EXTRA-001.10, atrás de flag.

Como ela entra sem arriscar o que funciona
==========================================
`PORTAL_VIDROS_API_FIRST` nasce **false**. Com a flag desligada,
`vidros_lanternas.abrir_atendimento` segue exatamente o caminho de hoje —
`_select_insurer_start` → passo 1 → modal → `run_adaptive`. Nenhuma linha muda.

Com a flag ligada, este módulo assume o fluxo INTEIRO, do nome da seguradora ao
desfecho que o portal decidiu, e devolve o controle ao DOM **apenas antes** da
primeira escrita.

🔴 A ordem das operações NÃO é a da tela
========================================
📊 Medido nos 4 HAR de 20/09/2026 (`trafego.importar_har`), idêntico em 4 de 4:

    GET  /seguradoras/          a lista AO VIVO — o slug sai daqui, não do código
    GET  /apolices              preflight — read-only, decide se PODE escrever
    ────────────── fronteira A ──────────────
    POST /atendimentos          NumeroProtocolo + Token · IRREVERSÍVEL
    PUT  /atendimentos/corretores   ← e é daqui em diante que o token viaja
    POST /solicitantes
    GET  /apolices/itens-cobertos · /motivos-dano · /ufs · /cidades · /clientes/cidades
    ─── [L] fronteira B AQUI ───
    PATCH /atendimentos         grava peça, causa, local
    ─── [V] segue ───
    POST /questionarios/perguntas ×N   (leitura! não persiste)
    POST /questionarios/regras-reparo  (leitura! diz se o portal vai oferecer reparo)
    ─── [V] fronteira B ───
    POST /questionarios         CodigoAtendimento nasce · IRREVERSÍVEL
    PUT  /atendimentos/alterar-reparo  (quando o segurado decidiu)
    GET  /agendamentos/opcoes-disponiveis   🔴 O ROTEADOR: quem decide o desfecho
    GET  /atendimentos          ← só AGORA o ScriptFinalizacao traz a loja

🔴 A regra de ouro de segurança
===============================
**Depois da fronteira A nada cai para o DOM e nada é reexecutado.** Toda parada
é `needs_human` com `business_state` e o que falta; toda resposta fora do
contrato grava `evidence["tela_desconhecida"]` com as CHAVES, nunca os valores.

Antes da fronteira A, devolver `None` continua sendo a resposta certa: nada
aconteceu, e o navegador é a autoridade de último recurso.

O que este módulo NÃO faz
=========================
Não escolhe loja, não agenda, não direciona, não cancela, não abandona, não
finaliza. Ele APRESENTA o que o portal ofereceu — lojas, distâncias, dias e
horários — e a escolha continua sendo do segurado.
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from portal_worker.journeys import JourneyResult
from portal_worker.journeys import vidros_api as API
from portal_worker.journeys import vidros_estado as ST
from portal_worker.journeys import vidros_questionario as QZ
from portal_worker.journeys.vidros_sessao import SessaoVidros

logger = logging.getLogger(__name__)

# Teto de leitura da agenda. 📊 A única captura com agenda trouxe 1 loja; 6
# cobre uma cidade grande e ainda impede que uma lista inesperada de 40 lojas
# queime o teto de 150 chamadas da sessão em consultas de rota.
MAX_LOJAS_CONSULTADAS = 6


def api_first_habilitado() -> bool:
    """A flag nasce DESLIGADA. So um `true`/`1` explicito liga."""
    return str(os.getenv("PORTAL_VIDROS_API_FIRST", "") or "").strip().lower() in ("1", "true", "yes", "on")


def data_iso(valor: Any) -> str:
    """`DD/MM/AAAA` (o formato que a conversa produz) → `AAAA-MM-DD`.

    Devolve `""` para qualquer coisa que não seja uma data reconhecível — e o
    vazio faz o preflight desistir e cair para o DOM, que é o comportamento
    certo: adivinhar a data do dano é escolher a data errada.
    """
    txt = str(valor or "").strip()
    if not txt:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", txt):
        return txt
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", txt)
    if not m:
        return ""
    d, mes, ano = m.groups()
    try:
        datetime(int(ano), int(mes), int(d))
    except ValueError:
        return ""  # 31/02 não é data; melhor cair para o DOM do que mentir
    return f"{ano}-{int(mes):02d}-{int(d):02d}"


def _norm(txt: Any) -> str:
    s = unicodedata.normalize("NFKD", str(txt or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


# --------------------------------------------------------------------------
# 🔴 Casar UM item de um catálogo do portal — e parar quando não dá
# --------------------------------------------------------------------------
def casar_unico(texto: Any, itens: Any, campos: Tuple[str, ...]) -> Dict[str, Any]:
    """`{"item", "candidatos", "motivo"}`. `item=None` quando não há UM só.

    🔴 A regra que esta função existe para impedir: **escolher por posição**.
    📊 A mesma pergunta veio com as opções em ordem diferente entre duas
    seguradoras (`vidros_questionario`, docstring do módulo) — pegar "o
    primeiro" troca a porta do motorista pela do carona, e o portal não deixa
    corrigir depois.

    Zero candidatos e dois candidatos são desfechos DIFERENTES e os dois param:
    um pede a família da peça, o outro pede a desambiguação. Quem pergunta é a
    conversa, com a lista real na mão.
    """
    alvo = _norm(texto)
    reais = [i for i in (itens or []) if isinstance(i, dict)]
    if not alvo:
        return {"item": None, "candidatos": reais, "motivo": "nada a casar"}

    def textos(i: Dict[str, Any]) -> List[str]:
        return [_norm(i.get(c)) for c in campos if i.get(c) not in (None, "")]

    exatos = [i for i in reais if alvo in textos(i)]
    if len(exatos) == 1:
        return {"item": exatos[0], "candidatos": exatos, "motivo": "texto exato"}
    if len(exatos) > 1:
        return {"item": None, "candidatos": exatos, "motivo": "mais de um item com o mesmo texto"}

    contidos = [i for i in reais
                if any(t and (alvo in t or t in alvo) for t in textos(i))]
    if len(contidos) == 1:
        return {"item": contidos[0], "candidatos": contidos, "motivo": "continencia"}
    if len(contidos) > 1:
        return {"item": None, "candidatos": contidos,
                "motivo": f"{len(contidos)} itens candidatos"}
    return {"item": None, "candidatos": [], "motivo": "nenhum item do catalogo casou"}


def _rotulos(itens: Any, campo: str, teto: int = 20) -> List[str]:
    return [str(i.get(campo) or "") for i in (itens or [])
            if isinstance(i, dict)][:teto]


# --------------------------------------------------------------------------
# O contato que vai ao portal — D-E00110-01
# --------------------------------------------------------------------------
# 📊 Medido em 4 de 4 capturas: `RelacaoTitular` é STRING (`"1"`, `"5"`, `"6"`),
# `TermoAceito` é `false` nas quatro, e `EmailTitularAplice` (sic, sem o `o`) só
# aparece quando `EmailCorretor` é `true` — 2 de 4.
#
# 🔴 A nossa escolha é sempre `"6"` (Corretor): quem abre é a corretora, e
# declarar "O Próprio" seria declaração falsa. O CONTATO, porém, é o segurado —
# 📊 3 de 4 capturas gravaram o telefone como `Tipo 21 = CELULAR CORRETOR`, e
# nessas o portal marcou `PossuiTelefoneRecebeWhatsapp: false`: o segurado não
# recebe nada e a loja liga para a corretora.
RELACAO_CORRETOR = "6"
TIPO_TELEFONE_POR_DONO = {
    "segurado": "CELULAR SEGURADO",
    "corretora": "CELULAR CORRETOR",
}


def _contato_de(params: Dict[str, Any]) -> Dict[str, Any]:
    """O bloco `params["contato"]` do contrato A↔C, com defaults compatíveis.

    Se `contato` não vier, cai para o `solicitante`/`segurado` que a tool já
    monta hoje — assim a fatia C pode chegar depois sem derrubar a A.
    """
    c = dict(params.get("contato") or {})
    sol = dict(params.get("solicitante") or {})
    seg = dict(params.get("segurado") or {})
    return {
        "relacao": str(c.get("relacao") or RELACAO_CORRETOR),
        "telefone": str(c.get("telefone") or seg.get("telefone")
                        or sol.get("telefone") or "").strip(),
        "tipo_telefone": str(c.get("tipo_telefone")
                             or ("segurado" if seg.get("telefone") else "corretora")),
        "email_segurado": str(c.get("email_segurado") or seg.get("email") or "").strip(),
        "email_corretora": str(c.get("email_corretora") or sol.get("email") or "").strip(),
        "nome_solicitante": str(c.get("nome_solicitante") or sol.get("nome") or "").strip(),
        "documento_corretor": str(c.get("documento_corretor")
                                  or sol.get("cpf_cnpj") or "").strip(),
    }


def _codigo_do_tipo_de_telefone(tipos: Any, dono: str) -> Optional[int]:
    """Do NOME para o código. 📊 `[{Codigo:20,Descricao:"CELULAR SEGURADO"},…]`.

    🔴 Nunca o número decorado: `20` e `21` estão a um dígito de distância e
    significam pessoas diferentes. Se a lista não trouxer o nome, a resposta é
    `None` e quem chamou para — gravar o tipo errado manda o SMS do portal para
    o telefone errado.
    """
    alvo = _norm(TIPO_TELEFONE_POR_DONO.get(str(dono or "").strip().lower(), ""))
    if not alvo:
        return None
    for t in (tipos or []):
        if isinstance(t, dict) and _norm(t.get("Descricao")) == alvo:
            try:
                return int(t.get("Codigo"))
            except (TypeError, ValueError):
                return None
    return None


def _corpo_do_solicitante(contato: Dict[str, Any], *,
                          codigo_tipo_telefone: int) -> Dict[str, Any]:
    """O corpo do `POST /solicitantes`, na ordem medida."""
    tem_email_corretora = bool(contato["email_corretora"])
    corpo: Dict[str, Any] = {
        "RelacaoTitular": str(contato["relacao"]),
        "EmailSegurado": contato["email_segurado"],
    }
    if tem_email_corretora:
        # 📊 A chave chega escrita assim no portal, sem o `o` de "Apolice".
        # Corrigir a grafia faria o campo não existir para o servidor.
        corpo["EmailTitularAplice"] = contato["email_corretora"]
    corpo["NomeSolicitante"] = contato["nome_solicitante"] or None
    corpo["CpfCnpjSolicitante"] = contato["documento_corretor"] or None
    corpo["EmailCorretor"] = True if tem_email_corretora else None
    corpo["Telefones"] = ([{"Numero": contato["telefone"],
                            "Tipo": codigo_tipo_telefone}]
                          if contato["telefone"] else [])
    corpo["TermoExibido"] = True
    # 🔴 `false` em 4 de 4 capturas. Não se inventa `true` num termo que
    # ninguém exibiu a ninguém.
    corpo["TermoAceito"] = False
    return corpo


# --------------------------------------------------------------------------
# Guard e checkpoint
# --------------------------------------------------------------------------
def _guard_do(params: Dict[str, Any]):
    """O guard da SPEC-073 — e, sem ele, uma porta FECHADA.

    🔴 A versão anterior desta função devolvia
    `PortalActionGuard(material_liberado=bool(params.get("confirm")))` quando o
    runtime não vinha nos params. Isso era fail-OPEN, e abria justamente o
    buraco que a SPEC-073 existe para fechar:

    `guard.armar()` só persiste `phase=armed` se tiver um checkpoint durável
    (`_gravar` faz `if self._checkpoint is not None`). Um guard construído solto
    não tem nenhum. Então, com `confirm=True` e sem runtime, o `POST
    /atendimentos` saía **sem que o banco soubesse que havia um POST em curso**
    -- e uma queda logo depois deixaria um atendimento existindo na seguradora
    sem uma linha de evidência. É o `maybe_committed` sem ninguém para
    reconciliar.

    Em produção o worker sempre injeta `params["_runtime"]`. Mas "sempre" é uma
    suposição sobre outro módulo, e fronteira material não se apoia em
    suposição: se a injeção quebrar um dia, o certo é o pedido NÃO sair.
    """
    rt = params.get("_runtime")
    g = getattr(rt, "guard", None)
    if g is not None:
        return g
    from portal_worker.guardrails import PortalActionGuard

    # Sem checkpoint durável não há fronteira material. Leitura continua livre.
    return PortalActionGuard(material_liberado=False)


async def _checkpoint(params: Dict[str, Any], patch: Dict[str, Any]) -> None:
    rt = params.get("_runtime")
    if rt is not None and hasattr(rt, "checkpoint"):
        await rt.checkpoint(patch)


def _tela_desconhecida(evidence: Dict[str, Any], *, onde: str,
                       resposta: Dict[str, Any]) -> None:
    """Grava o dossiê de uma resposta fora do contrato. **Chaves, nunca valores.**

    📊 A API do portal devolve nome, CPF, placa e telefone dentro dos agregados.
    O dossiê existe para ensinar o sistema o que ele não conhecia; para isso
    bastam o endereço, o status e a FORMA da resposta.
    """
    corpo = resposta.get("json")
    if isinstance(corpo, dict):
        resumo: Any = sorted(corpo.keys())[:40]
    elif isinstance(corpo, list):
        primeiro = corpo[0] if corpo and isinstance(corpo[0], dict) else {}
        resumo = {"lista": len(corpo), "chaves_do_item": sorted(primeiro.keys())[:40]}
    else:
        resumo = {"tipo": type(corpo).__name__}
    evidence["tela_desconhecida"] = {
        "onde": onde,
        "status": int(resposta.get("status") or 0),
        "erro": str(resposta.get("erro") or ""),
        "resumo": resumo,
    }


# --------------------------------------------------------------------------
# A journey
# --------------------------------------------------------------------------
async def abrir_atendimento_api(page, params: Dict[str, Any],
                                evidence: Dict[str, Any]) -> Optional[JourneyResult]:
    """O fluxo API-first, do nome da seguradora ao desfecho.

    `None` = devolve ao caminho DOM, e **só acontece antes da fronteira A**.
    """
    estado = ST.EstadoDoAtendimento()
    sessao = SessaoVidros(page=page)
    guard = _guard_do(params)
    guard.acao_material_esperada = ST.FRONTEIRA_ABRIR
    dano = dict(params.get("dano") or {})
    local = dict(params.get("local") or {})
    especificos = dict(params.get("especificos") or {})
    contato = _contato_de(params)

    def desistir(motivo: str, **extra: Any) -> None:
        evidence["api_first"] = {"usado": False, "motivo": motivo, **extra}

    def parar(stage: str, mensagem: str, **capturado: Any) -> JourneyResult:
        """🔴 Toda parada DEPOIS da fronteira A é esta função: `needs_human`,
        com o estado de negócio e o que falta. Nunca `None`, que voltaria ao DOM
        e abriria um segundo pedido."""
        evidence["vidros_estado"] = estado.para_evidencia()
        evidence["api_first"] = {"usado": True, "parou_em": stage,
                                 **sessao.resumo_para_evidencia()}
        return JourneyResult(
            status="needs_human",
            captured={"stage": stage, "business_state": estado.estado,
                      "protocolo": estado.codigo_atendimento or estado.numero_protocolo,
                      **capturado},
            message=mensagem)

    # ======================================================================
    # 1. A SEGURADORA SAI DA LISTA AO VIVO — P0-4
    # ======================================================================
    rs = await sessao.seguradoras()
    lista_seguradoras = rs.get("json")
    if not rs.get("ok") or not isinstance(lista_seguradoras, list):
        desistir("nao consegui ler a lista de seguradoras do portal")
        return None

    achada = API.resolver_seguradora(params.get("_seguradora_slug")
                                     or params.get("insurer_name"),
                                     lista_seguradoras)
    if achada is None:
        # 🔴 `None` é resposta legítima: não dá para PROVAR de qual seguradora
        # ele falou. O DOM assume, que é quem sabe navegar a tela de seleção.
        desistir("a seguradora informada nao casa com UMA das publicadas hoje",
                 publicadas=len(lista_seguradoras))
        return None

    seguradora = achada["slug"]
    evidence["seguradora"] = {"slug": seguradora, "codigo": achada["codigo"],
                              "nome_de_tela": achada["nome_de_tela"]}
    if seguradora in API.FORA_DO_API_FIRST:
        # D-PILOTO-17: ela existe, é exibível, e a escrita automática não sai.
        desistir(f"{seguradora} esta fora do API-first por decisao de produto")
        return None

    # ======================================================================
    # 2. TUDO O QUE DÁ PARA SABER SEM ESCREVER — a lista de paradas precoces
    # ======================================================================
    cpf = str(params.get("cpf_cnpj") or "").strip()
    placa = str(params.get("placa") or "").strip().upper()
    data = (str(params.get("_data_iso") or "").strip()
            or data_iso(params.get("data_dano")))
    relato = str(dano.get("descricao") or "").strip()
    faltou = [n for n, v in (
        ("cpf", cpf), ("placa", placa), ("data", data),
        ("dano.peca", dano.get("peca")), ("dano.como", dano.get("como")),
        ("local.cidade_servico", local.get("cidade_servico")),
        ("contato.documento_corretor", contato["documento_corretor"]),
        ("contato.telefone", contato["telefone"]),
    ) if not v]
    if relato and len(relato) < API.MINIMO_AVALIACAO_DANO:
        # 📊 O portal exige relato com no mínimo 30 caracteres. Descobrir isso
        # aqui custa uma pergunta; descobrir no PATCH custa um pedido aberto e
        # travado.
        faltou.append(f"dano.descricao (o portal exige {API.MINIMO_AVALIACAO_DANO} caracteres)")
    elif not relato:
        faltou.append("dano.descricao")
    if faltou:
        desistir("faltam dados que o portal exige ANTES de qualquer escrita",
                 faltou=faltou)
        return None

    # ---- PREFLIGHT — read-only, e o único portão para a fronteira A --------
    tipo = API.tipo_atendimento_para(seguradora, dano.get("peca"))
    r = await sessao.buscar_apolice(seguradora=seguradora, cpf_cnpj=cpf,
                                    placa=placa, data_sinistro=data,
                                    tipo_atendimento=tipo)
    veredito = API.classificar_preflight(r.get("status") or 0, r.get("json"))
    evidence["preflight"] = {k: v for k, v in veredito.items()
                             if k != "mensagem_portal"}
    evidence["vidros_estado"] = estado.para_evidencia()

    if veredito["estado"] == API.COVERAGE_ABSENT:
        # 📊 Detectado ANTES de qualquer escrita. Nenhum atendimento nasceu, e
        # nenhum vai nascer — repetir com outra cobertura seria adivinhar.
        return JourneyResult(
            status="needs_human",
            captured={"stage": "coverage_absent", "escopo": veredito.get("escopo", ""),
                      "business_state": ST.PRE_PROTOCOLO},
            message=("a apolice nao tem a cobertura necessaria para este item "
                     f"({veredito.get('escopo') or 'cobertura nao contratada'}). "
                     "Nenhum atendimento foi aberto."))

    if not veredito["pode_escrever"]:
        # policy_not_found · policy_ambiguous · regra desconhecida · erro.
        desistir(f"preflight={veredito['estado']}")
        return None

    apolice = r.get("json") or {}
    chassi = str(params.get("chassi") or apolice.get("Chassi") or "").strip()

    # ======================================================================
    # 3. FRONTEIRA A — a partir daqui existe registro na seguradora
    # ======================================================================
    from portal_worker.guardrails import AcaoBloqueada, MATERIAL_SIDE_EFFECT

    corpo = {
        "Seguradora": seguradora,
        "NumeroDaApolice": str(apolice.get("NumeroDaApolice") or ""),
        "DataSinistro": data,
        "PlacaInformada": placa,
        "SufixoChassi": None,
        "CpfCnpjSegurado": cpf,
        "TipoAtendimento": tipo,
    }
    try:
        await guard.before(action=ST.FRONTEIRA_ABRIR,
                           action_class=MATERIAL_SIDE_EFFECT,
                           details={"idempotency_key":
                                    str(params.get("_idempotency_key") or "")},
                           origem="journey")
    except AcaoBloqueada as e:
        # `confirm=false` chega aqui. É a trava funcionando, não uma falha.
        evidence["vidros_estado"] = estado.para_evidencia()
        return JourneyResult(
            status="needs_human",
            captured={"stage": "pronto_para_abrir", "business_state": ST.PRE_PROTOCOLO},
            message=("tudo conferido e a apolice tem cobertura — falta a "
                     f"autorizacao para abrir o pedido ({e})"))

    ra = await sessao.criar_atendimento(corpo)
    if not ra.get("ok"):
        # 🔴 A chamada saiu e não sabemos se o servidor a processou. Este é o
        # `maybe_committed`, e é o estado que existe para impedir o retry.
        estado.transitar(ST.DESCONHECIDO,
                         motivo=f"POST /atendimentos devolveu {ra.get('status')}")
        await guard.incerto(motivo="POST /atendimentos sem resposta de sucesso")
        evidence["vidros_estado"] = estado.para_evidencia()
        return JourneyResult(
            status="needs_human",
            captured={"stage": "maybe_committed", "business_state": ST.DESCONHECIDO},
            message=("a chamada que cria o atendimento saiu e nao consegui "
                     "confirmar o resultado. NAO reexecute: consulte antes."))

    dados = ra.get("json") or {}
    protocolo = str(dados.get("NumeroProtocolo") or "")
    estado.transitar(ST.PROTOCOLO_CRIADO, motivo="POST /atendimentos 200",
                     numero_protocolo=protocolo)
    await guard.submetido(receipt=protocolo)
    # 🔴 `evidence["protocolo"]` é escrito AQUI, e não só no fim.
    # `guardrails.tem_prova_de_efeito` procura exatamente esta chave — é o que a
    # journey DOM sempre gravou, e é o que o `portal_tool` consulta para decidir
    # se um job `failed` esconde um pedido vivo. Escrever só depois da fronteira
    # B deixava uma janela em que o pedido JÁ EXISTIA na seguradora e a evidência
    # dizia que não havia prova de nada — a janela exata em que um retry abriria
    # o segundo atendimento, pago, no nome do mesmo segurado.
    if protocolo:
        evidence["protocolo"] = protocolo
    evidence["vidros_estado"] = estado.para_evidencia()
    await _checkpoint(params, {"vidros_estado": estado.para_evidencia(),
                               "protocolo": protocolo})

    # ---- corretor e solicitante — P0-2, obrigatórios em 4 de 4 ------------
    rc = await sessao.registrar_corretor(contato["documento_corretor"])
    if not rc.get("ok"):
        _tela_desconhecida(evidence, onde=API.EP_CORRETORES, resposta=rc)
        return parar("corretor_recusado",
                     "o pedido foi aberto e o portal recusou o vinculo do "
                     "corretor. NAO reexecute: o atendimento ja existe.")

    rt_tel = await sessao.tipos_de_telefone()
    codigo_tipo = _codigo_do_tipo_de_telefone(rt_tel.get("json"),
                                              contato["tipo_telefone"])
    if codigo_tipo is None:
        _tela_desconhecida(evidence, onde=API.EP_TIPOS_TELEFONE, resposta=rt_tel)
        return parar("tipo_de_telefone_desconhecido",
                     "o pedido foi aberto e a lista de tipos de telefone do "
                     "portal nao trouxe o tipo esperado. NAO reexecute.")

    rsol = await sessao.registrar_solicitante(
        _corpo_do_solicitante(contato, codigo_tipo_telefone=codigo_tipo))
    if not rsol.get("ok"):
        _tela_desconhecida(evidence, onde=API.EP_SOLICITANTES, resposta=rsol)
        return parar("solicitante_recusado",
                     "o pedido foi aberto e o portal recusou os dados de "
                     "contato. NAO reexecute: o atendimento ja existe.")
    evidence["contato_no_portal"] = {"relacao": contato["relacao"],
                                     "tipo_telefone": contato["tipo_telefone"],
                                     "codigo_tipo_telefone": codigo_tipo,
                                     "termo_aceito": False}

    # ======================================================================
    # 4. O CATÁLOGO DESTA APÓLICE — só existe depois do token
    # ======================================================================
    ritens = await sessao.itens_cobertos(seguradora)
    itens = ritens.get("json")
    if not ritens.get("ok") or not isinstance(itens, list) or not itens:
        _tela_desconhecida(evidence, onde=API.EP_ITENS_COBERTOS, resposta=ritens)
        return parar("catalogo_indisponivel",
                     "o pedido foi aberto e o catalogo de pecas desta apolice "
                     "nao veio. NAO reexecute.")

    achado = casar_unico(dano.get("peca"), itens,
                         ("Descricao", "DescricaoSimples"))
    if achado["item"] is None and especificos:
        # A família casou com várias linhas do catálogo; o que separa uma da
        # outra é o ESPECÍFICO que o segurado já respondeu (capa com pisca,
        # farol de LED, vidro fixo × sobe-e-desce).
        for resposta in especificos.values():
            if not isinstance(resposta, str) or not resposta.strip():
                continue
            refinado = casar_unico(f"{dano.get('peca')} {resposta}",
                                   achado["candidatos"] or itens,
                                   ("Descricao", "DescricaoSimples"))
            if refinado["item"] is not None:
                achado = refinado
                break
    if achado["item"] is None:
        return parar("peca_ambigua",
                     "o pedido foi aberto e a peca precisa ser escolhida na "
                     "lista real desta apolice: " + achado["motivo"],
                     opcoes=_rotulos(achado["candidatos"] or itens, "Descricao"))

    item = achado["item"]
    codigo_item = str(item.get("CodigoItemCoberto") or "")
    partes = API.partes_do_item_coberto(codigo_item)
    if not partes:
        return parar("item_com_formato_desconhecido",
                     "o pedido foi aberto e a chave da peca veio num formato "
                     "que nao conheco. NAO reexecute.")
    evidence["peca"] = {"codigo": codigo_item, "categoria": partes["categoria"],
                        "descricao": str(item.get("Descricao") or "")}

    # ---- a causa do dano, da lista DAQUELA peça --------------------------
    rmot = await sessao.motivos_dano(codigo_item)
    motivos = rmot.get("json")
    if not rmot.get("ok") or not isinstance(motivos, list) or not motivos:
        _tela_desconhecida(evidence, onde=API.EP_MOTIVOS_DANO, resposta=rmot)
        return parar("motivos_indisponiveis",
                     "o pedido foi aberto e a lista de causas desta peca nao "
                     "veio. NAO reexecute.")
    causa = casar_unico(dano.get("como"), motivos, ("DescricaoObjetoCausa",))
    if causa["item"] is None:
        return parar("motivo_ambiguo",
                     "o pedido foi aberto e a causa do dano precisa ser "
                     "escolhida na lista real: " + causa["motivo"],
                     opcoes=_rotulos(causa["candidatos"] or motivos,
                                     "DescricaoObjetoCausa"))
    codigo_causa = causa["item"].get("CodigoObjetoCausa")

    # ---- as peças da LATARIA (multi-peça) — P1-5 -------------------------
    servicos_lataria: List[Dict[str, Any]] = []
    if partes["categoria"] == API.CATEGORIA_LATARIA:
        rserv = await sessao.servicos_itens(
            codigo_script=partes["codigo_script"],
            codigo_tipo_script=partes["codigo_tipo_script"])
        catalogo_pecas = rserv.get("json") if isinstance(rserv.get("json"), list) else []
        pedidas = [p for p in (dano.get("pecas_lataria") or []) if str(p).strip()]
        if not pedidas:
            return parar("pecas_de_lataria_ausentes",
                         "o pedido foi aberto e a lista de pecas amassadas nao "
                         "veio. Quais pecas o reparo cobre?",
                         opcoes=_rotulos(catalogo_pecas, "Descricao"))
        for peca in pedidas:
            casado = casar_unico(peca, catalogo_pecas, ("Descricao",))
            if casado["item"] is None:
                return parar("peca_de_lataria_ambigua",
                             f"o pedido foi aberto e a peca {peca!r} precisa ser "
                             "escolhida na lista real: " + casado["motivo"],
                             opcoes=_rotulos(casado["candidatos"] or catalogo_pecas,
                                             "Descricao"))
            servicos_lataria.append({"CodigoServico": casado["item"].get("Codigo"),
                                     "CodigoObjetoCausa": codigo_causa})

    # ---- a cidade do serviço — e se ela tem REDE -------------------------
    cidade_pedida = local.get("cidade_servico") or {}
    uf = str(cidade_pedida.get("uf") or "").strip().upper()
    nome_cidade = str(cidade_pedida.get("cidade") or "").strip()
    rufs = await sessao.ufs()
    ufs_validas = {str(u.get("UF") or "").upper()
                   for u in (rufs.get("json") or []) if isinstance(u, dict)}
    if ufs_validas and uf not in ufs_validas:
        return parar("uf_desconhecida",
                     f"o pedido foi aberto e o estado {uf!r} nao esta na lista "
                     "do portal.", opcoes=sorted(ufs_validas))
    rcid = await sessao.cidades(uf)
    cidades = rcid.get("json") if isinstance(rcid.get("json"), list) else []
    achada_cidade = casar_unico(nome_cidade, cidades, ("Nome", "Cidade"))
    if achada_cidade["item"] is None:
        return parar("cidade_ambigua",
                     f"o pedido foi aberto e a cidade {nome_cidade!r} nao casou "
                     "com uma da lista do portal: " + achada_cidade["motivo"],
                     opcoes=_rotulos(achada_cidade["candidatos"], "Nome"))
    codigo_cidade = achada_cidade["item"].get("Codigo")

    rrede = await sessao.cidade_atendida(
        chassi=chassi, codigo_cidade=codigo_cidade,
        codigo_script=partes["codigo_script"],
        codigo_tipo_script=partes["codigo_tipo_script"])
    rede = rrede.get("json")
    if not rrede.get("ok") or not isinstance(rede, dict) or not rede.get("Codigo"):
        # 🔴 Esta é uma parada que SÓ dá para descobrir depois da fronteira A:
        # a consulta exige o token, que nasce no `POST /atendimentos`.
        _tela_desconhecida(evidence, onde=API.EP_CLIENTES_CIDADES, resposta=rrede)
        return parar("cidade_sem_rede",
                     f"o pedido foi aberto e {nome_cidade}/{uf} nao tem rede "
                     "para esta peca. Ha outra cidade onde o servico possa ser "
                     "feito?")

    # ======================================================================
    # 5. A FRONTEIRA MATERIAL DEPENDE DA CATEGORIA — P0-3
    # ======================================================================
    # 🔴 Nenhuma constante fixa aqui: a fronteira é CALCULADA a partir da peça.
    fronteira_b = ST.fronteira_materializar_de(codigo_item)
    evidence["fronteira_material"] = {"peca": codigo_item,
                                      "categoria": partes["categoria"],
                                      "fronteira": fronteira_b}

    corpo_patch = API.corpo_de_atualizacao(
        codigo_item_coberto=codigo_item,
        codigo_cidade=codigo_cidade,
        codigo_objeto_causa=codigo_causa,
        avaliacao_dano=relato,
        perimetro_dano=str(dano.get("onde") or local.get("perimetro") or "N"),
        cep=str(local.get("cep") or params.get("cep") or ""),
        servicos_martelinho_lataria=servicos_lataria,
        item_removido=especificos.get("item_removido"),
        evento_composto=especificos.get("evento_composto"),
        polimento_farol=especificos.get("polimento_farol"),
    )

    if fronteira_b == ST.FRONTEIRA_ATUALIZAR:
        # Categoria `L` (e toda categoria que não sabemos ler): o PATCH é que
        # materializa. Arma ANTES dele.
        guard.acao_material_esperada = ST.FRONTEIRA_ATUALIZAR
        try:
            await guard.before(action=ST.FRONTEIRA_ATUALIZAR,
                               action_class=MATERIAL_SIDE_EFFECT, origem="journey")
        except AcaoBloqueada as e:
            return parar("pronto_para_materializar",
                         f"os dados estao completos, falta autorizacao ({e})")

    rpatch = await sessao.atualizar_atendimento(corpo_patch)
    if not rpatch.get("ok"):
        if fronteira_b == ST.FRONTEIRA_ATUALIZAR:
            estado.transitar(ST.DESCONHECIDO,
                             motivo=f"PATCH /atendimentos devolveu {rpatch.get('status')}")
            await guard.incerto(motivo="PATCH /atendimentos sem sucesso")
        _tela_desconhecida(evidence, onde=API.EP_ATENDIMENTOS, resposta=rpatch)
        return parar("maybe_committed" if fronteira_b == ST.FRONTEIRA_ATUALIZAR
                     else "patch_recusado",
                     "gravei a peca e o local e nao confirmei. NAO reexecute.")

    # ======================================================================
    # 6. O QUESTIONÁRIO E O REPARO — só para vidraçaria
    # ======================================================================
    reparo_decidido: Optional[bool] = None
    if fronteira_b == ST.FRONTEIRA_MATERIALIZAR:
        resultado = await QZ.rodar_questionario(
            sessao,
            respostas_do_segurado=dict(especificos),
            relato=relato)
        evidence["questionario"] = resultado.para_evidencia()

        if not resultado.completo:
            estado.transitar(ST.PROTOCOLO_CRIADO, motivo=resultado.motivo)
            pendente = resultado.pergunta_pendente
            return parar("questionario_incompleto",
                         "o pedido foi aberto e o questionario parou: "
                         + resultado.motivo,
                         pergunta=pendente.texto if pendente else "",
                         opcoes=pendente.textos_das_opcoes if pendente else [])

        # ---- `regras-reparo` é LEITURA e roda ANTES da fronteira B --------
        # 🔴 É esta ordem que permite descobrir que falta a decisão do segurado
        # sem ter materializado nada.
        rreg = await sessao.regras_reparo(resultado.respostas)
        oferece = bool((rreg.get("json") or {}).get("ExibirDialogDeReparo")) \
            if isinstance(rreg.get("json"), dict) else False
        evidence["reparo"] = {"portal_oferece": oferece,
                              "previsto_pelo_questionario": resultado.reparo_previsto}
        if oferece:
            dito = _norm(especificos.get("aceita_reparo"))
            if dito in ("sim", "s", "aceito", "true"):
                reparo_decidido = True
            elif dito in ("nao", "n", "recuso", "false"):
                reparo_decidido = False
            else:
                # 🔴 PARA AQUI, antes da fronteira B: nada materializado, e a
                # decisão é do segurado. 💭 "A seguradora pode consertar sem
                # trocar o vidro — leva uns 30 minutos e costuma sair mais
                # barato para você. Quer tentar o reparo?"
                return parar("decidir_reparo",
                             "o portal ofereceu REPARO em vez de troca, e essa "
                             "escolha e do segurado. Nada foi materializado.",
                             opcoes=["tentar o reparo", "trocar a peca"])

        # ---- FRONTEIRA B ------------------------------------------------
        guard.acao_material_esperada = ST.FRONTEIRA_MATERIALIZAR
        try:
            await guard.before(action=ST.FRONTEIRA_MATERIALIZAR,
                               action_class=MATERIAL_SIDE_EFFECT, origem="journey")
        except AcaoBloqueada as e:
            return parar("pronto_para_materializar",
                         f"questionario completo, falta autorizacao para gravar ({e})")

        rq = await sessao.gravar_questionario(resultado.respostas)
        if not rq.get("ok"):
            estado.transitar(ST.DESCONHECIDO,
                             motivo=f"POST /questionarios devolveu {rq.get('status')}")
            await guard.incerto(motivo="POST /questionarios sem sucesso")
            return parar("maybe_committed",
                         "gravei o questionario e nao confirmei. NAO reexecute.")

        if reparo_decidido is not None:
            rrep = await sessao.alterar_reparo(reparo_decidido)
            evidence["reparo"] = {**evidence.get("reparo", {}),
                                  "gravado": bool(rrep.get("ok")),
                                  "valor": reparo_decidido}

    # ======================================================================
    # 7. O DESFECHO — quem decide é o PORTAL, e ele diz por escrito
    # ======================================================================
    ropc = await sessao.opcoes_de_agendamento()
    if not ropc.get("ok") or not isinstance(ropc.get("json"), dict):
        _tela_desconhecida(evidence, onde=API.EP_OPCOES_DISPONIVEIS, resposta=ropc)
        return parar("roteador_ilegivel",
                     "o pedido existe e o portal nao disse o desfecho. NAO "
                     "reexecute: consulte o atendimento.")

    # 🔴 O `GET /atendimentos` vem DEPOIS de `opcoes-disponiveis`, e a ordem é
    # o ponto inteiro: 📊 o `ScriptFinalizacao` reescreve a si mesmo, e só aqui
    # ele traz a loja. Lido antes, diz "aguarde o analista".
    rg = await sessao.ler_atendimento()
    agregado = rg.get("json") if isinstance(rg.get("json"), dict) else {}
    estado = ST.ler_estado_do_agregado(agregado, tinha_protocolo=bool(protocolo))
    estado.numero_protocolo = protocolo

    desfecho = ST.ler_desfecho(ropc.get("json"), agregado)
    desfecho["reparo"] = reparo_decidido
    evidence["desfecho"] = desfecho

    if estado.codigo_atendimento:
        await guard.confirmado(receipt=estado.codigo_atendimento)
        # 📊 O número que a tela mostra e que o segurado anota é este.
        evidence["protocolo"] = estado.codigo_atendimento
    if desfecho["franquias"]:
        evidence["franquia"] = desfecho["franquias"][0].get("valor", "")
    vistoria = API.vistoria_do_atendimento(agregado)
    if vistoria.get("tem_link"):
        evidence["link_vistoria"] = vistoria["link"]

    if desfecho["tipo"] == ST.DESFECHO_DESCONHECIDO:
        _tela_desconhecida(evidence, onde=API.EP_OPCOES_DISPONIVEIS, resposta=ropc)
        return parar("desfecho_desconhecido",
                     "o pedido existe e o portal decidiu por um caminho que eu "
                     "nao sei ler: " + str(desfecho.get("motivo") or ""))

    # ---- agenda: ler lojas, distância, dias e horários (LEITURA) — P1-1 ---
    if desfecho["tipo"] == ST.DESFECHO_AGENDA:
        await _enriquecer_agenda(sessao, desfecho, agregado=agregado,
                                 codigo_atendimento=estado.codigo_atendimento)

    # ---- conclusão: o COMPROVANTE — P1-5 --------------------------------
    if desfecho["tipo"] in (ST.DESFECHO_LOJA_DIRETA, ST.DESFECHO_ANALISTA) \
            and estado.codigo_atendimento:
        rf = await sessao.emitir_formalizado(estado.codigo_atendimento)
        desfecho["comprovante_emitido"] = bool(rf.get("ok"))

    estado.transitar(ST.AGUARDANDO_ESCOLHA if desfecho["tipo"] == ST.DESFECHO_AGENDA
                     else ST.ATENDIMENTO_MATERIALIZADO,
                     motivo=str(desfecho.get("motivo") or ""))
    evidence["vidros_estado"] = estado.para_evidencia()
    evidence["api_first"] = {"usado": True, **sessao.resumo_para_evidencia()}
    await _checkpoint(params, {"vidros_estado": estado.para_evidencia(),
                               "desfecho": desfecho})

    return JourneyResult(
        status="done",
        captured={"business_state": estado.estado,
                  "protocolo": estado.codigo_atendimento,
                  "tipo": desfecho["tipo"],
                  "franquia": (desfecho["franquias"] or [{}])[0].get("valor", ""),
                  "link_vistoria": vistoria.get("link", ""),
                  "customer_choice_needed": desfecho["tipo"] == ST.DESFECHO_AGENDA},
        message=("atendimento aberto"
                 + (f" — n {estado.codigo_atendimento}" if estado.codigo_atendimento else "")
                 + f" · desfecho: {desfecho['tipo']}"))


async def _enriquecer_agenda(sessao: Any, desfecho: Dict[str, Any], *,
                             agregado: Dict[str, Any],
                             codigo_atendimento: str) -> None:
    """Distância, dias e horários de cada loja. **Só leitura.**

    🔴 Isto é o que elimina a razão de sortear loja. 📊 `adaptive.py` explica,
    com três motivos medidos, por que o robô não escolhe: *"a lista de lojas só
    existe NESTA tela. O segurado nunca a viu."* Aqui a lista passa a existir na
    conversa — e a decisão continua sendo dele.

    ⚠️ `POST /lojas/consultar-distancias` é POST e **não** é escrita de negócio:
    calcula rota. Não passa pelo guard como fronteira material.
    """
    ano = datetime.now().year
    for loja in desfecho.get("lojas", [])[:MAX_LOJAS_CONSULTADAS]:
        rd = await sessao.consultar_distancia({
            "CodigoAtendimento": str(codigo_atendimento or ""),
            "Cep": str(agregado.get("Cep") or ""),
            "Uf": str(agregado.get("EstadoRealizacaoServico") or loja.get("uf") or ""),
            "Cidade": str(agregado.get("CidadeRealizacaoServico") or loja.get("cidade") or ""),
            "Logradouro": "",
            "Bairro": str(loja.get("bairro") or ""),
        })
        distancia = rd.get("json") if isinstance(rd.get("json"), dict) else {}
        loja["distancia"] = str(distancia.get("Distancia") or "")
        loja["tempo"] = str(distancia.get("TempoDuracao") or "")

        if not loja.get("tem_agenda"):
            # 📊 `DisponibilizaAgenda` diferente de `"S"`: a loja não publica
            # agenda. Perguntar datas a ela seria inventar uma opção que o
            # segurado não tem.
            continue
        rdias = await sessao.datas_disponiveis(
            codigo_cliente=loja.get("codigo_cliente"),
            codigo_produto=loja.get("codigo_produto"), ano=ano)
        meses = rdias.get("json") if isinstance(rdias.get("json"), list) else []
        loja["dias"] = [{"mes": m.get("Mes"), "dias": list(m.get("Dias") or [])}
                        for m in meses if isinstance(m, dict)]

        primeira = _primeira_data(meses, ano)
        if not primeira:
            continue
        rhor = await sessao.horarios_disponiveis(
            codigo_cliente=loja.get("codigo_cliente"),
            codigo_produto=loja.get("codigo_produto"),
            data_agendamento=primeira)
        horarios = rhor.get("json") if isinstance(rhor.get("json"), dict) else {}
        # 📊 `Blocos` veio **vazio** na única captura. Lista vazia não é erro: é
        # o que a loja publicou naquele dia, e dizer "sem horários para o dia X"
        # é mais honesto do que inventar um.
        loja["horarios"] = {primeira: [b for b in (horarios.get("Blocos") or [])]}
        loja["tempo_servico"] = horarios.get("TempoServico")
        loja["tempo_permanencia"] = horarios.get("TempoPermanencia")


def _primeira_data(meses: Any, ano: int) -> str:
    """📊 `[{"Mes": 8, "Dias": [15,17,…]}, …]` → `"2026-08-15"`."""
    for m in (meses or []):
        if not isinstance(m, dict):
            continue
        dias = [d for d in (m.get("Dias") or []) if isinstance(d, int)]
        if dias:
            return f"{ano}-{int(m.get('Mes') or 0):02d}-{min(dias):02d}"
    return ""
