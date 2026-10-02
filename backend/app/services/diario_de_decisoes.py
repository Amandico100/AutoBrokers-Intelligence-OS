# -*- coding: utf-8 -*-
"""O DIÁRIO DE DECISÕES — SPEC-123 F4.

Toda decisão que o agente toma SOZINHO para destravar um acionamento (ou, na
SPEC-124, um portal) vira UMA linha em `public.diario_de_decisoes`, escrita em
português de gente (D7 do Founder): o que a seguradora perguntou, o que o agente
fez, por quê, com que certeza — e, depois, o que aconteceu. A corretora marca
"certo" ou "errado" (+ "o certo era…") na tela `/dashboard/atendimentos/decisoes`;
"errado" vira caso pendente de bancada (`scripts/diario_para_bancada.py`) e, se o
master achar que é regra, rascunho de carta com `status='proposta_diario'`
(`propor_carta_sync`) — que NENHUM publicador automático lê.

## Quem chama
- `destravador.destravar` (F1a) → `registrar_decisao` a cada decisão (on ou sombra);
- o roteador/sentinela, quando o acionamento termina → `marcar_resultado`.

## As regras desta peça (CLAUDE.md)
- §7: filtro `company_id` NO CÓDIGO em toda leitura/escrita — a RLS da tabela é só a rede.
- §5: é tabela própria porque `work_events` é append-only (o veredito é ATUALIZAÇÃO);
  na linha do tempo fica só o evento curto `cerebro.decisao` com o `diario_id`.
- Nunca levanta: é um registro ao lado do trabalho, não o trabalho. Falha → log + None.
- Nenhum dado de pessoa: tela, valor, motivo e a frase passam por
  `acao_do_cerebro.higienizar_para_o_rastro` antes de gravar.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

TABELA = "diario_de_decisoes"
EVENTO = "cerebro.decisao"

# 🔴 As listas fechadas são as MESMAS dos CHECKs da migration
#    `20260930_04_spec123_diario_de_decisoes.sql`. O teste
#    `test_spec123_diario_fio.py::test_as_listas_batem_com_o_banco` as confere contra o catálogo.
ORIGENS = ("acionamento", "atendimento", "portal")
CLASSES = ("conduzir", "responder_com_dado", "deduzir", "perguntar_ao_segurado", "nunca_sozinho")
#: SPEC-124 F1: `respondeu_portal` — o destravador continuou o MESMO pedido do portal de vidros com um dado
#: do caso (migration 20261001_04, `ck_diario_acao`). A lista é a do CHECK do banco, na mesma ordem.
#: SPEC-125 S6: `respondeu_segurado` — o agente de ATENDIMENTO respondeu sozinho ao segurado
#: (migration 20261001_05, `ck_diario_acao`).
ACOES = ("respondeu_ura", "perguntou_segurado", "chamou_pessoa", "nao_agiu", "respondeu_portal",
         "respondeu_segurado")
MODOS = ("on", "sombra")
RESULTADOS_FINAIS = ("protocolo_saiu", "seguradora_recusou", "humano_corrigiu", "ura_fechou")
#: SPEC-125 D7 — os sinais de ERRO LEVE da conversa: chegam sozinhos logo depois de um julgamento e
#: fecham a linha (`fechar_como_erro_leve`). Mesma lista do `ck_diario_resultado` (migration 20261001_05).
SINAIS_DE_ERRO_LEVE = ("segurado_corrigiu", "segurado_repetiu", "segurado_pediu_pessoa",
                       "agente_repetiu_pergunta")

#: SPEC-125 D7 — os QUATRO momentos de julgamento do agente de atendimento (e só eles: o diário não
#: é uma linha por mensagem). Cada momento → (classe da política, ação). 🔴 Por quê, um por um:
#:   deduziu            → `deduzir`: tirou um dado do que o segurado disse em vez de perguntar;
#:   respondeu_regra    → `responder_com_dado`: respondeu cobertura/regra com a FONTE (apólice ou carta);
#:   nao_chamou_pessoa  → `conduzir`: seguiu conduzindo a conversa onde a regra antiga mandava a uma pessoa;
#:   chamou_pessoa      → `nunca_sozinho` + `chamou_pessoa`: o grave (sinistro, risco, pedido…) foi a pessoa.
MOMENTOS = {
    "deduziu": ("deduzir", "respondeu_segurado"),
    "respondeu_regra": ("responder_com_dado", "respondeu_segurado"),
    "nao_chamou_pessoa": ("conduzir", "respondeu_segurado"),
    "chamou_pessoa": ("nunca_sozinho", "chamou_pessoa"),
}

#: Status da carta que nasce do diário. ⛔ NUNCA `pending_review`: esse status é
#: PUBLICADO SOZINHO por `curadoria_cartas.publicar_lote_sync` (o destilador).
#: `proposta_diario` só sai da gaveta pela mão do master no /admin/espelho.
STATUS_DA_CARTA_DO_DIARIO = "proposta_diario"

# Tetos de texto (o diário é para ler, não para arquivar a conversa).
_TETO_TELA = 2000
_TETO_VALOR = 500
_TETO_MOTIVO = 400
_TETO_FRASE = 900


# ─────────────────────────────────────────────────────────────────────────────
# A borda: o banco
# ─────────────────────────────────────────────────────────────────────────────
async def _cliente():
    """O MESMO cliente durável que o acionamento usa (`dispatch_router._db`).

    Import tardio: `dispatch_router` → `destravador` → este módulo; importar no topo
    faria o ciclo. `None` quando não há banco (teste/offline) — nunca derruba nada.
    """
    try:
        from app.services import dispatch_router as R

        return await R._db()
    except Exception as e:  # noqa: BLE001
        logger.error("[DIARIO] banco indisponível (%s)", type(e).__name__)
        return None


def _cliente_sync():
    """Cliente síncrono (rotas do admin e o script da bancada, via `asyncio.to_thread`)."""
    from app.core.database import get_supabase_client

    return get_supabase_client()


async def _evento_curto(db: Any, company_id: str, run_id: str, diario_id: str) -> None:
    """A linha do tempo do acionamento ganha só o PONTEIRO para o diário."""
    try:
        from app.services import dispatch_router as R

        await R._evento(db, company_id, run_id, EVENTO,
                        "O agente decidiu sozinho para destravar o atendimento; "
                        "a decisão está no diário de decisões.",
                        payload={"diario_id": diario_id}, ator="agent")
    except Exception as e:  # noqa: BLE001
        logger.warning("[DIARIO] evento curto não registrado (%s)", type(e).__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Máscara
# ─────────────────────────────────────────────────────────────────────────────
def _mascarar(texto: Any, sessao: Optional[Dict[str, Any]], teto: int) -> str:
    from app.services.acao_do_cerebro import higienizar_para_o_rastro

    return higienizar_para_o_rastro(str(texto or ""), sessao)[:teto]


def _tela_hash(tela: str) -> str:
    return hashlib.sha256(" ".join(str(tela or "").split()).encode("utf-8")).hexdigest()[:16]


def _chave(chave: str, *partes: Any) -> str:
    """A chave de idempotência cabe no CHECK (8–200). Curta ou vazia → hash das partes."""
    c = str(chave or "").strip()
    if 8 <= len(c) <= 200:
        return c
    base = "|".join(str(p or "") for p in (c, *partes))
    return "diario:" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]


# ─────────────────────────────────────────────────────────────────────────────
# A frase para GENTE (D7)
# ─────────────────────────────────────────────────────────────────────────────
#: Por quê, em uma linha, por classe. Cada frase diz a RAZÃO da classe, não o nome dela.
_POR_QUE = {
    "conduzir": "porque era só um passo para seguir em frente na conversa",
    "responder_com_dado": "porque a resposta é um dado do próprio caso",
    "deduzir": "porque deduziu pelo que o segurado contou",
    "perguntar_ao_segurado": "porque só o segurado sabe essa resposta",
    "nunca_sozinho": ("porque essa decisão não pode ser tomada sem uma pessoa "
                      "(custo, abertura de sinistro ou cancelamento)"),
}

#: Um "motivo" do modelo que parece código (`sem_chute`, `a:b`, `{PLACA}` sozinho) não
#: entra na frase: D7 proíbe nome de variável na tela da corretora.
_PARECE_CODIGO = re.compile(r"\w+_\w+|[{}<>\[\]=:]|\b[A-Z]{2,}_")


_MARCA = re.compile(r"\{([A-Z][A-Z_]*)(?::[\w-]+)?\}")


def humanizar_marcas(texto: str) -> str:
    """`{PLACA}` → `[placa]`: a marca do mascarador vira palavra (D7: nada de nome de variável)."""
    return _MARCA.sub(lambda m: "[" + m.group(1).lower().replace("_", " ") + "]", str(texto or ""))


def _nome_da_seguradora(seguradora: str) -> str:
    try:
        from app.services.dispatch_mirror import insurer_label_from_ref

        return insurer_label_from_ref(seguradora)
    except Exception:  # noqa: BLE001
        s = str(seguradora or "").strip()
        return s.capitalize() if s else "A seguradora"


def _a_pergunta(tela: str) -> str:
    """A pergunta da tela: a última linha com "?", senão a primeira linha com texto."""
    linhas = [" ".join(l.replace("*", "").replace("_", " ").split())
              for l in str(tela or "").splitlines()]
    linhas = [l for l in linhas if l]
    if not linhas:
        return ""
    com_pergunta = [l for l in linhas if "?" in l]
    escolhida = com_pergunta[-1] if com_pergunta else linhas[0]
    return escolhida if len(escolhida) <= 160 else escolhida[:157].rstrip() + "…"


_OPCAO = re.compile(r"^\s*\*?\s*(\d{1,2})\s*\*?\s*[-–.)]\s*\*?\s*(.+?)\s*\*?\s*$")


def _com_rotulo(valor: str, tela: str) -> str:
    """'2' vira '"2" (Elétrica)': a tecla sozinha não diz nada a quem lê."""
    v = " ".join(str(valor or "").split())[:160]
    if not re.fullmatch(r"\d{1,2}", v):
        return f'"{v}"'
    for linha in str(tela or "").splitlines():
        m = _OPCAO.match(linha)
        if m and m.group(1) == v:
            return f'"{v}" ({m.group(2).replace("*", "").strip()[:80]})'
    return f'"{v}"'


def frase_para_gente(*, seguradora: str, tela: str, classe: str, acao: str, valor: str,
                     nota: Any, segunda_opiniao: Optional[Dict[str, Any]], motivo: str) -> str:
    """Ex.: 'A Porto Seguro perguntou "Qual a amperagem da bateria?". O agente respondeu "60A"
    porque a resposta é um dado do próprio caso (certeza 88%, a segunda opinião concordou).'"""
    nome = _nome_da_seguradora(seguradora)
    pergunta = _a_pergunta(tela)
    v = " ".join(str(valor or "").split())[:160]
    partes = []
    partes.append(f'{nome} perguntou "{pergunta}".' if pergunta else f"{nome} mandou uma mensagem.")

    if acao == "respondeu_ura":
        feito = f"O agente respondeu {_com_rotulo(v, tela)}" if v else "O agente respondeu"
    elif acao == "perguntou_segurado":
        feito = (f'O agente perguntou ao segurado: "{v}"' if v
                 else "O agente fez uma pergunta ao segurado")
    elif acao == "respondeu_portal":
        feito = (f'O agente respondeu ao portal "{v}"' if v
                 else "O agente respondeu ao portal")
    elif acao == "chamou_pessoa":
        feito = "O agente chamou uma pessoa da corretora"
    else:  # nao_agiu — sombra: decidiu, mas nada saiu
        feito = ("O agente apenas observou, sem responder nada"
                 + (f"; se estivesse ligado, teria respondido {_com_rotulo(v, tela)}" if v else ""))
    por_que = _POR_QUE.get(classe, "")
    frase = feito + (f" {por_que}" if por_que else "")

    certeza = []
    try:
        if nota is not None and str(nota).strip() != "":
            certeza.append(f"certeza {int(nota)}%")
    except (TypeError, ValueError):
        pass
    if isinstance(segunda_opiniao, dict) and "concordou" in segunda_opiniao:
        certeza.append("a segunda opinião concordou" if segunda_opiniao.get("concordou")
                       else "a segunda opinião discordou")
    if certeza:
        frase += f" ({', '.join(certeza)})"
    partes.append(frase + ".")

    m = " ".join(str(motivo or "").split())
    if m and not _PARECE_CODIGO.search(m):
        partes.append(f"Explicação do agente: {m[:200]}")
    return humanizar_marcas(" ".join(partes))[:_TETO_FRASE]


# ─────────────────────────────────────────────────────────────────────────────
# Escrever
# ─────────────────────────────────────────────────────────────────────────────
async def registrar_decisao(*, company_id: str, origem: str, work_run_id: Optional[str],
                            conversation_id: Optional[str], seguradora: str, ramo: str, rota: str,
                            servico: str, tela: str, classe: str, acao: str, valor: str,
                            nota: Optional[int], limiar: Optional[int], motivo: str,
                            explicacao_para_gente: str, modelo: str,
                            segunda_opiniao: Optional[Dict[str, Any]], modo: str, gatilho: str,
                            chave_idempotencia: str,
                            sessao: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Uma linha no diário (+ o evento curto `cerebro.decisao`). Idempotente por
    (company_id, chave_idempotencia). Nunca levanta. Devolve o id, ou None."""
    try:
        return await _registrar(
            company_id=company_id, origem=origem, work_run_id=work_run_id,
            conversation_id=conversation_id, seguradora=seguradora, ramo=ramo, rota=rota,
            servico=servico, tela=tela, classe=classe, acao=acao, valor=valor, nota=nota,
            limiar=limiar, motivo=motivo, explicacao_para_gente=explicacao_para_gente,
            modelo=modelo, segunda_opiniao=segunda_opiniao, modo=modo, gatilho=gatilho,
            chave_idempotencia=chave_idempotencia, sessao=sessao)
    except Exception as e:  # noqa: BLE001 — o diário nunca derruba o acionamento
        logger.error("[DIARIO] decisão NÃO registrada (%s)", type(e).__name__)
        return None


def _nota(n: Any, minimo: int = 0) -> Optional[int]:
    try:
        v = int(n)
    except (TypeError, ValueError):
        return None
    return v if minimo <= v <= 100 else None


def _segunda(s: Any, sessao: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(s, dict):
        return None
    return {"modelo": str(s.get("modelo") or "")[:80],
            "valor": _mascarar(s.get("valor"), sessao, 300),
            "concordou": bool(s.get("concordou")),
            "nota": _nota(s.get("nota"))}


async def _registrar(**k: Any) -> Optional[str]:
    cid = str(k["company_id"] or "").strip()
    origem, classe, acao, modo = (str(k[c] or "").strip() for c in ("origem", "classe", "acao", "modo"))
    if not cid:
        logger.warning("[DIARIO] sem corretora — a decisão não é registrada")
        return None
    # Lista fechada: o que o banco recusaria, recusamos antes, com o motivo no log.
    for nome, valor, lista in (("origem", origem, ORIGENS), ("classe", classe, CLASSES),
                               ("acao", acao, ACOES), ("modo", modo, MODOS)):
        if valor not in lista:
            logger.warning("[DIARIO] %s fora da lista (%r) — não registrado", nome, valor[:40])
            return None
    if k.get("momento") and (origem != "atendimento" or k["momento"] not in MOMENTOS):
        logger.warning("[DIARIO] momento %r fora da conversa/lista — não registrado", str(k["momento"])[:40])
        return None
    if modo == "sombra" and acao != "nao_agiu":
        # Em sombra nada saiu: a linha que diz "respondeu" mentiria (CHECK ck_diario_sombra_nao_agiu).
        acao = "nao_agiu"

    sessao = k.get("sessao")
    tela = str(k.get("tela") or "")
    run_id = str(k.get("work_run_id") or "").strip() or None
    conversa = str(k.get("conversation_id") or "").strip() or None
    chave = _chave(k.get("chave_idempotencia"), cid, run_id, k.get("gatilho"), _tela_hash(tela))
    nota = _nota(k.get("nota"))
    limiar = _nota(k.get("limiar"), minimo=70)
    motivo_m = _mascarar(k.get("motivo"), sessao, _TETO_MOTIVO)
    valor_m = _mascarar(k.get("valor"), sessao, _TETO_VALOR)
    tela_m = _mascarar(tela, sessao, _TETO_TELA)
    segunda = _segunda(k.get("segunda_opiniao"), sessao)
    frase = str(k.get("explicacao_para_gente") or "").strip() or frase_para_gente(
        seguradora=str(k.get("seguradora") or ""), tela=tela_m, classe=classe, acao=acao,
        valor=valor_m, nota=nota, segunda_opiniao=segunda, motivo=motivo_m)
    frase = humanizar_marcas(_mascarar(frase, sessao, _TETO_FRASE))
    if len(frase.strip()) < 10:
        frase = frase_para_gente(seguradora=str(k.get("seguradora") or ""), tela=tela_m,
                                 classe=classe, acao=acao, valor=valor_m, nota=nota,
                                 segunda_opiniao=segunda, motivo=motivo_m)

    linha = {
        "company_id": cid, "work_run_id": run_id, "conversation_id": conversa,
        "chave_idempotencia": chave, "origem": origem,
        "seguradora": str(k.get("seguradora") or "")[:40].lower(),
        "ramo": str(k.get("ramo") or "")[:40].lower(),
        "rota": str(k.get("rota") or "")[:180], "servico": str(k.get("servico") or "")[:120],
        "gatilho": str(k.get("gatilho") or "")[:200], "tela_hash": _tela_hash(tela),
        "tela_mascarada": tela_m, "classe": classe, "acao": acao, "valor_mascarado": valor_m,
        "nota": nota, "limiar": limiar, "motivo": motivo_m, "explicacao_para_gente": frase,
        "modelo": str(k.get("modelo") or "")[:80], "segunda_opiniao": segunda, "modo": modo,
        # SPEC-125 S6 — o texto COMPLETO, para a corretora dona ler (ordem do Founder, 01/10).
        # ⛔ Só a tela do diário o lê; log, evento, bancada e carta usam as colunas mascaradas.
        "tela_completa": tela[:_TETO_TELA] or None,
        "valor_completo": str(k.get("valor") or "")[:_TETO_VALOR] or None,
    }
    if k.get("momento"):
        linha["momento"] = str(k["momento"])

    db = await _cliente()
    if db is None:
        return None
    ja = await _achar(db, cid, chave)
    if ja:
        return ja                                  # idempotente: a mesma decisão não vira duas linhas
    try:
        res = await db.client.table(TABELA).insert(linha).execute()
    except Exception as e:  # noqa: BLE001
        ja = await _achar(db, cid, chave)          # corrida: outro processo gravou primeiro
        if ja:
            return ja
        if run_id or conversa:
            # FK composta recusou (acionamento/conversa de outra corretora, ou apagado):
            # a decisão fica registrada SEM o ponteiro — nunca com o ponteiro errado.
            logger.warning("[DIARIO] ponteiro recusado (%s) — gravando sem acionamento/conversa",
                           type(e).__name__)
            linha.update(work_run_id=None, conversation_id=None)
            run_id = None
            res = await db.client.table(TABELA).insert(linha).execute()
        else:
            raise
    diario_id = str(((res.data or [{}])[0]).get("id") or "") or None
    if diario_id and run_id:
        await _evento_curto(db, cid, run_id, diario_id)
    return diario_id


async def _achar(db: Any, company_id: str, chave: str) -> Optional[str]:
    try:
        r = await (db.client.table(TABELA).select("id")
                   .eq("company_id", company_id)
                   .eq("chave_idempotencia", chave).limit(1).execute())
        return str((r.data or [{}])[0].get("id") or "") or None
    except Exception:  # noqa: BLE001
        return None


async def marcar_resultado(*, company_id: str, work_run_id: str, resultado: str) -> int:
    """O que aconteceu depois, nas linhas `pendente` DAQUELE acionamento DAQUELA corretora.
    Devolve quantas mudaram. Nunca levanta."""
    try:
        cid = str(company_id or "").strip()
        run = str(work_run_id or "").strip()
        if not cid or not run or resultado not in RESULTADOS_FINAIS:
            return 0
        db = await _cliente()
        if db is None:
            return 0
        r = await (db.client.table(TABELA)
                   .update({"resultado": resultado,
                            "resultado_em": datetime.now(timezone.utc).isoformat()})
                   .eq("company_id", cid)
                   .eq("work_run_id", run)
                   .eq("resultado", "pendente").execute())
        return len(r.data or [])
    except Exception as e:  # noqa: BLE001
        logger.warning("[DIARIO] resultado não marcado (%s)", type(e).__name__)
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# "Virar rascunho de carta" — o botão do master (/admin/decisoes)
# ─────────────────────────────────────────────────────────────────────────────
def texto_da_carta(linha: Dict[str, Any]) -> str:
    """A regra que a corretora ensinou, em prosa de carta. Sem nome de corretora, sem pessoa."""
    nome = _nome_da_seguradora(str(linha.get("seguradora") or ""))
    ramo = str(linha.get("ramo") or "").strip()
    pergunta = _a_pergunta(str(linha.get("tela_mascarada") or ""))
    certo = " ".join(str(linha.get("o_certo_era") or "").split())
    onde = f"{nome}" + (f" ({ramo})" if ramo and ramo != "todos" else "")
    if pergunta:
        return f'No acionamento pela {onde}, quando a central pergunta "{pergunta}": {certo}'
    return f"No acionamento pela {onde}: {certo}"


def propor_carta_sync(diario_id: str, *, db: Any = None) -> Dict[str, Any]:
    """Cria (ou reaproveita) a carta `proposta_diario` de uma linha "errado" e grava o ponteiro.

    O caminho é o do escritor oficial de cartas (`attendance_distiller._store_card_sync`):
    a MESMA régua de tamanho (`fora_do_tamanho`), o MESMO mascarador (`veredito_de_pii` —
    o texto guardado é o mascarado), a MESMA seguradora do fato (`seguradora_do_fato`), o
    MESMO assunto (`assunto_da_carta`) e o MESMO `card_hash` (md5 do texto minúsculo; é o
    UNIQUE da tabela — a P-121-04 falhou por não mandá-lo). Só o status muda: `proposta_diario`.
    ⚠️ Não chama `_store_card_sync` porque ele carimba `pending_review`, que o destilador publica
    sozinho. Devolve {"ok", "carta_id", "motivo"}.
    """
    from app.services.curadoria_cartas import (assunto_da_carta, fora_do_tamanho,
                                               seguradora_do_fato, veredito_de_pii)

    db = db or _cliente_sync()
    rows = (db.client.table(TABELA)
            .select("id, company_id, seguradora, ramo, tela_mascarada, o_certo_era, veredito, "
                    "carta_rascunho_id")
            .eq("id", str(diario_id)).limit(1).execute().data) or []
    if not rows:
        return {"ok": False, "motivo": "decisao_nao_encontrada"}
    linha = rows[0]
    if linha.get("veredito") != "errado":
        return {"ok": False, "motivo": "so_decisao_errada_vira_carta"}
    if linha.get("carta_rascunho_id"):
        return {"ok": True, "carta_id": str(linha["carta_rascunho_id"]), "motivo": "ja_existia"}

    bruto = " ".join(texto_da_carta(linha).split())
    tamanho = fora_do_tamanho(bruto)
    if tamanho:
        return {"ok": False, "motivo": f"tamanho: {tamanho}"}
    texto, achados = veredito_de_pii(bruto)
    chave, prestadora = seguradora_do_fato(texto, linha.get("seguradora"))
    marcas: Dict[str, Any] = {"deterministic": not achados, "origem": "diario_de_decisoes",
                              "diario_id": str(linha["id"])}
    if achados:
        marcas["pii_achada"] = achados
    if texto != bruto:
        marcas["mascarado"] = True
    if prestadora:
        marcas["prestadora"] = prestadora
    card_hash = hashlib.md5(texto.lower().encode("utf-8")).hexdigest()
    carta = {"card_hash": card_hash, "card_text": texto, "category": assunto_da_carta(texto),
             "ramo": (str(linha.get("ramo") or "") or None), "insurer_key": chave,
             "status": STATUS_DA_CARTA_DO_DIARIO, "pii_check": marcas}
    res = (db.client.table("knowledge_cards")
           .upsert(carta, on_conflict="card_hash", ignore_duplicates=True).execute())
    carta_id = str(((res.data or [{}])[0]).get("id") or "")
    motivo = "criada"
    if not carta_id:
        # O MESMO texto já existe no acervo (publicado ou não): liga-se a ele, sem duplicar.
        ex = (db.client.table("knowledge_cards").select("id, status")
              .eq("card_hash", card_hash).limit(1).execute().data) or []
        if not ex:
            return {"ok": False, "motivo": "carta_nao_gravada"}
        carta_id = str(ex[0]["id"])
        motivo = f"ja_existia_no_acervo:{ex[0].get('status')}"
    (db.client.table(TABELA).update({"carta_rascunho_id": carta_id})
     .eq("id", str(linha["id"])).eq("company_id", str(linha["company_id"]))
     .is_("carta_rascunho_id", "null").execute())
    return {"ok": True, "carta_id": carta_id, "motivo": motivo}


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-125 S6 — o diário da CONVERSA (só os momentos de julgamento, D7)
# ─────────────────────────────────────────────────────────────────────────────
def _trecho(texto: str, teto: int = 160) -> str:
    t = " ".join(str(texto or "").split())
    return t if len(t) <= teto else t[: teto - 1].rstrip() + "…"


def frase_da_conversa(*, momento: str, fala: str, valor: str, motivo: str, fonte: str = "",
                      nota: Any = None) -> str:
    """A linha que a corretora lê (D7): o que o segurado disse, o que o agente fez, por quê, com que
    certeza. Sem jargão, sem nome de variável. Ex.: 'O segurado escreveu "derrapei na chuva na BR".
    O agente entendeu que o local foi uma rodovia, sem perguntar de novo (certeza 85%).'"""
    f = _trecho(fala)
    v = _trecho(valor, 200)
    m = " ".join(str(motivo or "").split())
    m = "" if (not m or _PARECE_CODIGO.search(m)) else m[:200]
    partes = [f'O segurado escreveu "{f}".' if f else "O segurado mandou uma mensagem."]
    if momento == "deduziu":
        feito = (f"O agente entendeu que {v}, sem perguntar de novo" if v
                 else "O agente deduziu a resposta sem perguntar de novo")
    elif momento == "respondeu_regra":
        feito = (f'O agente respondeu sozinho, sem chamar ninguém: "{v}"' if v
                 else "O agente respondeu sozinho a dúvida, sem chamar ninguém")
        if fonte and not _PARECE_CODIGO.search(str(fonte)):
            feito += f" (com base em: {_trecho(fonte, 80)})"
    elif momento == "nao_chamou_pessoa":
        feito = ("Antes, isto iria para uma pessoa da corretora; o agente continuou o atendimento sozinho"
                 + (f' e respondeu "{v}"' if v else ""))
    else:  # chamou_pessoa
        feito = "O agente chamou uma pessoa da corretora"
    if m:
        feito += f", porque {m[0].lower() + m[1:]}"
    try:
        if nota is not None and str(nota).strip() != "":
            feito += f" (certeza {int(nota)}%)"
    except (TypeError, ValueError):
        pass
    partes.append(feito + ".")
    return humanizar_marcas(" ".join(partes))[:_TETO_FRASE]


async def registrar_julgamento_da_conversa(*, company_id: str, conversation_id: Optional[str],
                                           momento: str, fala_do_segurado: str, valor: str = "",
                                           motivo: str = "", fonte: str = "", nota: Optional[int] = None,
                                           seguradora: str = "", ramo: str = "", servico: str = "",
                                           modelo: str = "", modo: str = "on",
                                           chave_idempotencia: str = "",
                                           sessao: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """SPEC-125 D7 — UMA linha por momento de JULGAMENTO do agente de atendimento (a S4 chama):
    `deduziu` · `respondeu_regra` · `nao_chamou_pessoa` · `chamou_pessoa`. Nunca uma linha por mensagem
    (💭 1–3 por atendimento). Idempotente por (corretora, chave). Nunca levanta. Devolve o id ou None."""
    try:
        if momento not in MOMENTOS:
            logger.warning("[DIARIO] momento da conversa desconhecido (%r) — não registrado", str(momento)[:40])
            return None
        classe, acao = MOMENTOS[momento]
        fala_m = _mascarar(fala_do_segurado, sessao, _TETO_TELA)
        valor_m = _mascarar(valor, sessao, _TETO_VALOR)
        motivo_m = _mascarar(motivo, sessao, _TETO_MOTIVO)
        frase = frase_da_conversa(momento=momento, fala=fala_m, valor=valor_m, motivo=motivo_m,
                                  fonte=_mascarar(fonte, sessao, 200), nota=nota)
        chave = _chave(chave_idempotencia, company_id, conversation_id, momento,
                       _tela_hash(fala_do_segurado), _tela_hash(valor))
        return await _registrar(
            company_id=company_id, origem="atendimento", work_run_id=None,
            conversation_id=conversation_id, seguradora=seguradora, ramo=ramo, rota="",
            servico=servico, tela=fala_do_segurado, classe=classe, acao=acao, valor=valor, nota=nota,
            limiar=None, motivo=motivo, explicacao_para_gente=frase, modelo=modelo,
            segunda_opiniao=None, modo=modo, gatilho=f"conversa:{momento}",
            chave_idempotencia=chave, sessao=sessao, momento=momento)
    except Exception as e:  # noqa: BLE001 — o diário nunca derruba o atendimento
        logger.error("[DIARIO] julgamento da conversa NÃO registrado (%s)", type(e).__name__)
        return None


async def fechar_como_erro_leve(*, company_id: str, conversation_id: str, sinal: str) -> int:
    """O segurado corrigiu, repetiu ou pediu pessoa LOGO DEPOIS (ou o fiscal da repetição disparou):
    fecha a ÚLTIMA linha `pendente` daquela conversa daquela corretora com o sinal. Devolve 0 ou 1.
    Nunca levanta."""
    try:
        cid = str(company_id or "").strip()
        conversa = str(conversation_id or "").strip()
        if not cid or not conversa or sinal not in SINAIS_DE_ERRO_LEVE:
            return 0
        db = await _cliente()
        if db is None:
            return 0
        r = await (db.client.table(TABELA).select("id")
                   .eq("company_id", cid)
                   .eq("conversation_id", conversa)
                   .eq("origem", "atendimento")
                   .eq("resultado", "pendente")
                   .order("created_at", desc=True).limit(1).execute())
        alvo = (r.data or [{}])[0].get("id")
        if not alvo:
            return 0
        u = await (db.client.table(TABELA)
                   .update({"resultado": sinal, "resultado_em": datetime.now(timezone.utc).isoformat()})
                   .eq("id", str(alvo))
                   .eq("company_id", cid)
                   .eq("resultado", "pendente").execute())
        return len(u.data or [])
    except Exception as e:  # noqa: BLE001
        logger.warning("[DIARIO] erro leve não marcado (%s)", type(e).__name__)
        return 0
