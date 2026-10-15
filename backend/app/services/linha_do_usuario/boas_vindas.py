# -*- coding: utf-8 -*-
"""SPEC-131-0-B2 · L2 — as BOAS-VINDAS da linha do usuário (SPEC §4): a primeira mensagem na conversa consigo mesmo,
logo depois de conectar, UMA vez.

    montar(db, linha) -> str                o texto (markdown; a saída o põe no formato do WhatsApp e no prefixo)
    o_que_esta_ligado(db, company_id)       quais itens da lista a corretora tem LIGADOS
    async enviar_boas_vindas(db, linha)     manda pela PRÓPRIA linha à PRÓPRIA conta — idempotente (24 h)

{primeiro_nome} e {corretora} vêm do BANCO por `owner_user_id` / `company_id` (CLAUDE.md §13.9 — nunca constante).

🔴 COMO SE SABE O QUE A CORRETORA TEM LIGADO (decisão desta fatia, D-1310B2-L2-01): pelas MESMAS fontes que decidem o
que o chat principal consegue fazer — nunca uma lista paralela (CLAUDE.md §5):
   · tudo exige um agente CORE ATIVO (`atalho.turno.agente_core`) — sem ele nenhum pedido é atendido, e a lista some;
   · *Cotação* ⇐ a capability `tenant.multicalculo.cotacao` ATIVA para o papel core no Capability Registry
     (`capability_resolver.resolve_active_capabilities`) — o MESMO portão que anexa a ferramenta em `agents/graph.py`;
   · *O seu dia* ⇐ o aplicativo de Renovação instalado e ativo (`multicalculo.madrugada.aplicativo_ligado`) — o
     exemplo da SPEC é "quais renovações ficaram prontas?";
   · *Dúvidas de seguro*, *Ler um documento* e *Números da corretora* ⇐ o core (a base de conhecimento, o
     `chat_anexos` do `/chat/stream` e os relatórios comerciais são anexados a TODO core — `agents/graph.py`).
   Registry ilegível → o item que depende dele SAI (prometer o que talvez não exista é pior que omitir).

🔴 UMA VEZ (D-1310B2-L2-02): a marca é uma linha em `linha_mensagens_do_sistema` com `message_id =
"boas_vindas:<conectada_em>"` (sem migration nova): (1) se já há marca nas últimas 24 h, não reenvia (reconectar não
repete); (2) a marca é gravada ANTES do envio — o índice único (integration_id, message_id) faz dois eventos de
conexão da MESMA conexão (Connected + PairSuccess) disputarem e só um mandar; (3) envio que falhou apaga a marca
(o próximo evento de conexão tenta de novo). O hash dela é o do texto inteiro — vale também como anti-eco.
⛔ Nenhum nome, telefone ou texto em log.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

#: 💭 a janela em que reconectar NÃO repete as boas-vindas
JANELA_SEM_REPETIR = timedelta(hours=24)
MARCA = "boas_vindas:"
CAPABILITY_DA_COTACAO = "tenant.multicalculo.cotacao"

#: (chave, item) na ordem da SPEC §4. Markdown: `**x**` vira o *negrito* do WhatsApp em `para_whatsapp`.
ITENS = (
    ("cotacao", "• **Cotação** — mande a placa, a foto do documento, a apólice atual em PDF ou um áudio contando o "
                "que o cliente quer."),
    ("duvidas", "• **Dúvidas de seguro** — \"a apólice do João cobre vidro?\", \"o que muda se ele tirar o carro "
                "reserva?\""),
    ("documento", "• **Ler um documento** — mande a foto ou o PDF e peça o resumo."),
    ("dia", "• **O seu dia** — \"o que tenho para hoje?\", \"quais renovações ficaram prontas?\""),
    ("numeros", "• **Números da corretora** — \"como está a produção do mês?\""),
)

ABERTURA = ("{saudacao} Pronto: esta conversa com você mesmo agora é o seu canal direto com o AutoBrokers da "
            "{corretora}.")
COMO_PEDIR = "É só escrever aqui, como escreveria para um colega. Você pode pedir:"
COMO_PEDIR_SEM_LISTA = "É só escrever aqui, como escreveria para um colega."
PRAZO = "Uma resposta leva alguns segundos; uma cotação, de 1 a 2 minutos, e chega aqui mesmo."
COMBINADOS = (
    "Combinados:\n"
    "• Eu só leio ESTA conversa. As suas outras conversas não são lidas nem guardadas.\n"
    "• Eu não mando nada para os seus clientes: quem envia é sempre você.\n"
    "• O que começa com ▸ AutoBrokers sou eu; o resto é você.\n"
    "• Para desligar: Meu perfil → Meu WhatsApp → Desconectar (ou Aparelhos conectados, no celular)."
)

_TRAVAS: Dict[str, asyncio.Lock] = {}


def _dados(r: Any) -> List[Dict[str, Any]]:
    return [x for x in list(getattr(r, "data", None) or []) if isinstance(x, dict)]


def _low(v: Any) -> str:
    return str(v or "").strip().lower()


def _t(db: Any, tabela: str) -> Any:
    cliente = db if hasattr(db, "table") else getattr(db, "client", db)
    return cliente.table(tabela)


# =====================================================================================================================
# o que está ligado
# =====================================================================================================================
def o_que_esta_ligado(db: Any, company_id: Any) -> Set[str]:
    """As chaves de `ITENS` que esta corretora tem ligadas (ver o cabeçalho). Nunca levanta."""
    from app.services.atalho import turno as T

    cid = _low(company_id)
    try:
        if not T.agente_core(db, cid):
            return set()
    except Exception as erro:  # noqa: BLE001
        logger.warning("[LINHA] agente core ilegivel (%s) — boas-vindas sem a lista", type(erro).__name__)
        return set()
    ligados = {"duvidas", "documento", "numeros"}
    try:
        from app.agents.capability_resolver import active_keys, resolve_active_capabilities

        if CAPABILITY_DA_COTACAO in active_keys(resolve_active_capabilities(db, cid, "core")):
            ligados.add("cotacao")
    except Exception as erro:  # noqa: BLE001
        logger.warning("[LINHA] registry ilegivel (%s) — a cotacao fica fora da lista", type(erro).__name__)
    try:
        from app.services.multicalculo.madrugada import aplicativo_ligado

        if aplicativo_ligado(db, cid):
            ligados.add("dia")
    except Exception as erro:  # noqa: BLE001
        logger.warning("[LINHA] aplicativos ilegiveis (%s) — o seu dia fica fora da lista", type(erro).__name__)
    return ligados


def _primeiro_nome(db: Any, user_id: str) -> str:
    try:
        from app.services.atalho.verificacao import _nomes_das_pessoas

        nome = _nomes_das_pessoas(db, [user_id]).get(user_id) or ""
    except Exception:  # noqa: BLE001
        nome = ""
    primeiro = nome.strip().split(" ")[0] if nome.strip() else ""
    return "" if primeiro == "Sem" and nome.strip() == "Sem nome" else primeiro


def _corretora(db: Any, company_id: str) -> str:
    try:
        from app.services.atalho.verificacao import _nomes_das_corretoras

        return _nomes_das_corretoras(db, [company_id]).get(company_id) or "sua corretora"
    except Exception:  # noqa: BLE001
        return "sua corretora"


def montar(db: Any, linha: Dict[str, Any], *, ligados: Optional[Set[str]] = None) -> str:
    """O texto da SPEC §4 (sem o prefixo — a saída põe), com os nomes do banco e só os itens ligados."""
    cid, uid = _low(linha.get("company_id")), _low(linha.get("owner_user_id"))
    primeiro = _primeiro_nome(db, uid)
    ligados = o_que_esta_ligado(db, cid) if ligados is None else ligados
    itens = [texto for chave, texto in ITENS if chave in ligados]
    partes = [ABERTURA.format(saudacao=f"Oi, {primeiro}!" if primeiro else "Oi!", corretora=_corretora(db, cid))]
    partes.append(COMO_PEDIR + "\n" + "\n".join(itens) if itens else COMO_PEDIR_SEM_LISTA)
    partes.append(PRAZO)
    partes.append(COMBINADOS)
    return "\n\n".join(partes)


# =====================================================================================================================
# o envio, UMA vez
# =====================================================================================================================
def _ja_mandou(db: Any, linha: Dict[str, Any]) -> bool:
    iid, cid = str(linha.get("integration_id") or ""), _low(linha.get("company_id"))
    desde = (datetime.now(timezone.utc) - JANELA_SEM_REPETIR).isoformat()
    linhas = _dados(_t(db, "linha_mensagens_do_sistema").select("id, integration_id, company_id, message_id, enviada_em")
                    .eq("integration_id", iid).eq("company_id", cid).gte("enviada_em", desde).limit(500).execute())
    return any(str(x.get("integration_id")) == iid and str(x.get("message_id") or "").startswith(MARCA)
               for x in linhas)


def _marcar(db: Any, linha: Dict[str, Any], hash_texto: str) -> Optional[str]:
    """Grava a marca ANTES do envio. Devolve o message_id da marca, ou None se outro evento já marcou."""
    iid, cid = str(linha.get("integration_id") or ""), _low(linha.get("company_id"))
    marca = MARCA + str(linha.get("conectada_em") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H"))[:64]
    existentes = _dados(_t(db, "linha_mensagens_do_sistema").select("id, integration_id, message_id")
                        .eq("integration_id", iid).eq("message_id", marca).limit(1).execute())
    if any(str(x.get("integration_id")) == iid for x in existentes):
        return None
    try:
        _t(db, "linha_mensagens_do_sistema").insert({
            "integration_id": iid, "company_id": cid, "message_id": marca, "hash_texto": hash_texto,
            "enviada_em": datetime.now(timezone.utc).isoformat()}).execute()
    except Exception as erro:  # noqa: BLE001 — o único (integration_id, message_id): outro evento marcou primeiro
        if "23505" in str(erro) or "duplicate" in str(erro).lower():
            return None
        raise
    return marca


def _desmarcar(db: Any, linha: Dict[str, Any], marca: str) -> None:
    try:
        (_t(db, "linha_mensagens_do_sistema").delete()
         .eq("integration_id", str(linha.get("integration_id") or "")).eq("company_id", _low(linha.get("company_id")))
         .eq("message_id", marca).execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[LINHA] marca das boas-vindas nao apagada (%s)", type(erro).__name__)


async def enviar_boas_vindas(db: Any, linha: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """As boas-vindas pela PRÓPRIA linha à PRÓPRIA conta, uma vez (ver o cabeçalho). Nunca levanta."""
    from app.services.linha_do_usuario import entrada as ENT

    try:
        linha = linha or {}
        iid = str(linha.get("integration_id") or "")
        if not iid or not linha.get("ativa") or not ENT.ligada_para(linha.get("owner_user_id")):
            return {"status": "ignorado"}
        trava = _TRAVAS.setdefault(iid, asyncio.Lock())
        async with trava:
            if await asyncio.to_thread(_ja_mandou, db, linha):
                return {"status": "ja_enviada"}
            texto = await asyncio.to_thread(montar, db, linha)
            primeira = ENT._em_mensagens_com_prefixo(texto)
            marca = await asyncio.to_thread(_marcar, db, linha, ENT._sha(primeira[0] if primeira else texto))
            if not marca:
                return {"status": "ja_enviada"}
            r = await ENT.enviar_pela_linha(db, linha, texto)
            if not r.get("enviadas"):
                await asyncio.to_thread(_desmarcar, db, linha, marca)
                return {"status": "nao_enviada", "motivo": r.get("motivo")}
            logger.info("[LINHA] boas-vindas enviadas (%d mensagem(ns))", r["enviadas"])
            return {"status": "enviada", "enviadas": r["enviadas"]}
    except Exception as erro:  # noqa: BLE001
        logger.error("[LINHA] boas-vindas falharam (%s)", type(erro).__name__)
        return {"status": "erro"}


__all__ = ("ITENS", "JANELA_SEM_REPETIR", "CAPABILITY_DA_COTACAO", "o_que_esta_ligado", "montar",
           "enviar_boas_vindas")
