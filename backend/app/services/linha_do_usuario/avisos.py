"""modelo: claude-opus-5-5 · SPEC-131-0-B2 · L4-A — OS AVISOS DO SISTEMA PELA LINHA DO USUÁRIO, prontos e DESLIGADOS.

D-132F-04 / D-1310B2-06: renovações calculadas, licença do Agger e falha de conexão podem chegar no WhatsApp da PRÓPRIA
pessoa, na conversa consigo mesmo ("Mensagem para você"). Isto NÃO é um publicador: é o DESTINO `linha_do_usuario` do
`DeliveryExecutor` (o publicador que existe — CLAUDE.md §5); o executor chama `avisar` e este módulo decide se sai.

A CHAVE — `AVISOS_WHATSAPP_LIGADO` (ligar é do Founder, POR TIPO):

    ausente / vazia                          NADA sai. Cada aviso grava 1 linha em `linha_avisos_registro`
                                             (enviado=false, motivo='avisos_desligados' = "teria enviado")
    "renovacoes_calculadas,licenca_do_agger" só os tipos LISTADOS saem (vírgula, ponto e vírgula ou espaço)
    "1" / "true" / "todos"                   NÃO liga nada — não é tipo. Um liga-tudo por engano é exatamente o
                                             defeito que a chave existe para evitar.

OS TIPOS: `TIPOS`. ⛔ "WhatsApp desconectado" NUNCA sai pela linha — foi ela que caiu; esse aviso é só do central da
132-C e da faixa na tela (SPEC §4) → `so_pelo_central`, sem ler nem gravar nada, mesmo se alguém o listar na chave.

A ORDEM DA DECISÃO (todo aviso válido termina com UM registro; nunca levanta):

    1. tipo conhecido? company_id e user_id são uuid?           não → recusa; nada lido, nada gravado
    2. a linha CONECTADA do dono NESTA corretora                não → 'sem_linha'
       (`estado.linha_do_dono`: filtro company_id + purpose + dono no banco, reconferido aqui em Python)
    3. o tipo está na chave?                                    não → 'avisos_desligados' ("teria enviado")
    4. envia pela linha (o contrato da L2, abaixo)              0 enviadas / exceção → 'falha_no_envio'
                                                                L2 não instalada      → 'envio_indisponivel'
                                                                sem resposta a tempo  → 'envio_sem_resposta'
    ⚠️ 2 antes de 3 DE PROPÓSITO: "teria enviado" só é verdade se havia por onde enviar — o registro mede o que ligar
       a chave mudaria, não quantos avisos nasceram.
    🔴 o envio só existe no ramo 4, e o ramo 4 só se alcança com o tipo na chave (a MUTAÇÃO 6 da SPEC tira essa linha).

O CONTRATO COM A L2 (ela escreve `entrada.py` em paralelo — import TARDIO, dentro da função, nunca no topo):

    from app.services.linha_do_usuario.entrada import enviar_pela_linha
    async def enviar_pela_linha(db, linha: dict, texto_markdown: str) -> dict      # {"enviadas": int, "ids": [...]}

    `linha` = o dict de `estado.linha_do_dono(db, company_id, user_id)`. A função da L2 PÕE o prefixo
    "▸ AutoBrokers\\n" e grava o anti-eco (`linha_mensagens_do_sistema`, id + hash) — aqui o texto vai COMO VEIO, sem
    prefixo (senão sairia duas vezes). Ela passa pelo cinto único `atalho/envio.enviar`, com a exceção exata
    "destino = a própria linha que envia". Nada vai a cliente: o destino é sempre a própria conta do dono.

O REGISTRO nunca leva o texto (nem hash, nem telefone, nem id de mensagem): company_id, user_id, tipo, enviado, motivo.
O log também não: só o tipo, o motivo e o NOME da exceção (CLAUDE.md §13.3).

A LIMPEZA DO ANTI-ECO (P-132C-04) — `limpar_anti_eco(db, dias=7)`: apaga de `linha_mensagens_do_sistema` o que tem mais
de 7 dias. ⛔ Nenhum scheduler novo (CLAUDE.md §5). ONDE LIGAR (o gerente liga — arquivo de outra fatia): o job diário
de retenção que existe, `check_attendance_purge` em `backend/app/services/atlas/attendance_capture.py` (agendado em
`backend/app/tasks/buffer_processor.py:1680`, id `attendance_purge_check`, de hora em hora com marcador Redis 1x/dia),
logo depois de `deleted = await asyncio.to_thread(purge_expired_sync, None)` (attendance_capture.py:427), dentro do
mesmo `try`:

    from app.services.linha_do_usuario.avisos import limpar_anti_eco
    await asyncio.to_thread(limpar_anti_eco, None)

(`db=None` → o cliente de serviço, como o `purge_expired_sync`; nunca levanta, então não derruba a retenção de lá.)
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional

logger = logging.getLogger(__name__)

CHAVE = "AVISOS_WHATSAPP_LIGADO"
#: os avisos que PODEM sair pela linha (cada um ligado por nome na chave)
TIPOS = ("renovacoes_calculadas", "licenca_do_agger", "falha_de_conexao")
#: o aviso que NUNCA sai pela linha: ela é que caiu (só o central e a faixa da tela)
TIPO_SO_PELO_CENTRAL = "whatsapp_desconectado"

TABELA_REGISTRO = "linha_avisos_registro"
TABELA_ANTI_ECO = "linha_mensagens_do_sistema"
#: P-132C-04 — quanto o anti-eco durável guarda (o hash do enviado vale 10 min; o id, enquanto o eco puder chegar)
DIAS_DO_ANTI_ECO = 7
#: 💭 quanto o aviso espera o envio da L2 (abaixo dos 30 s do `DeliveryExecutor._esperar`)
TEMPO_DO_ENVIO_S = 25.0

#: a seção que `multicalculo.renovacao.registrar_aviso` publica (`SECAO_DO_AVISO`; o teste confere que é a mesma)
SECAO_DA_RENOVACAO = "renovacao"

#: o motivo de cada aviso que não saiu → a frase que o `DeliveryExecutor` grava no `delivery_detail` (para humano)
FRASES = {
    "avisos_desligados": f"avisos pelo WhatsApp desligados ({CHAVE}) — registrado como 'teria enviado'",
    "sem_linha": "a pessoa não tem o WhatsApp dela conectado ao AutoBrokers — não há por onde avisar",
    "falha_no_envio": "a linha está conectada, mas a mensagem não saiu",
    "envio_indisponivel": "o envio pela linha do usuário ainda não está instalado",
    "envio_sem_resposta": "o envio pela linha não respondeu a tempo — pode ter saído",
    "so_pelo_central": "'WhatsApp desconectado' não sai pela linha que caiu — só pelo central e pela tela",
    "tipo_desconhecido": "tipo de aviso desconhecido",
    "identidade_invalida": "corretora ou pessoa inválida",
    "texto_vazio": "aviso sem texto",
}

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_SEPARADOR = re.compile(r"[\s,;]+")


# ---------------------------------------------------------------------------------------------------------------------
# miúdos
# ---------------------------------------------------------------------------------------------------------------------
def _t(db: Any, tabela: str) -> Any:
    cliente = db if hasattr(db, "table") else getattr(db, "client", db)
    return cliente.table(tabela)


def _uuid(v: Any) -> Optional[str]:
    s = str(v or "").strip().lower()
    return s if _UUID.match(s) else None


def _mesma(a: Any, b: str) -> bool:
    return str(a or "").strip().lower() == b


def tipos_ligados() -> frozenset:
    """Os tipos que a chave liga — só nomes de `TIPOS`; o resto (inclusive "true", "1", "todos") é ignorado."""
    bruto = str(os.getenv(CHAVE) or "").strip().lower()
    return frozenset(t for t in _SEPARADOR.split(bruto) if t in TIPOS)


def frase_do_motivo(motivo: Any) -> str:
    return FRASES.get(str(motivo or ""), "o aviso não saiu")


def tipo_da_publicacao(publicacao: Mapping[str, Any], perfil: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    """Que aviso é esta publicação do briefing? O `perfil.aviso_tipo` explícito vence; sem ele, a seção da renovação
    (`renovacao.registrar_aviso`) → `renovacoes_calculadas`. Nada casa → None (o canal diz o motivo e não avisa)."""
    explicito = str((perfil or {}).get("aviso_tipo") or "").strip().lower()
    if explicito in TIPOS:
        return explicito
    payload = (publicacao or {}).get("payload") if isinstance(publicacao, Mapping) else None
    secoes = (payload or {}).get("sections") if isinstance(payload, Mapping) else None
    for secao in secoes or []:
        if isinstance(secao, Mapping) and secao.get("key") == SECAO_DA_RENOVACAO:
            return "renovacoes_calculadas"
    return None


def _saida(tipo: Optional[str], enviado: bool, motivo: Optional[str], registrado: bool) -> Dict[str, Any]:
    return {"ok": enviado, "tipo": tipo, "enviado": enviado, "motivo": motivo, "registrado": registrado}


# ---------------------------------------------------------------------------------------------------------------------
# a linha, o registro e o envio
# ---------------------------------------------------------------------------------------------------------------------
def _linha_conectada(db: Any, cid: str, uid: str) -> Optional[Dict[str, Any]]:
    """A linha ATIVA e CONECTADA deste dono NESTA corretora — ou None. O filtro está no banco (`linha_do_dono`) E é
    reconferido aqui: um filtro esquecido não vira aviso pela linha de outra pessoa ou de outra corretora."""
    from app.services.linha_do_usuario.estado import linha_do_dono

    linha = linha_do_dono(db, cid, uid)
    if not linha or not _mesma(linha.get("company_id"), cid) or not _mesma(linha.get("owner_user_id"), uid):
        return None
    if linha.get("ativa") is not True or str(linha.get("channel_status") or "") != "connected":
        return None
    return linha


def _registrar(db: Any, cid: str, uid: str, tipo: str, enviado: bool, motivo: Optional[str]) -> bool:
    """UMA linha no registro — nunca o texto. A FK composta (user_id, company_id) → company_members recusa quem não é
    membro desta corretora: vira False, nunca exceção."""
    try:
        _t(db, TABELA_REGISTRO).insert({"company_id": cid, "user_id": uid, "tipo": tipo, "enviado": bool(enviado),
                                        "motivo_nao_enviado": None if enviado else motivo}).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("[LINHA-AVISO] registro nao gravado (%s, %s): %s", tipo, motivo or "enviado", type(exc).__name__)
        return False


async def _enviar(db: Any, linha: Dict[str, Any], texto: str) -> Optional[str]:
    """Pela linha, pelo contrato da L2. None = saiu; senão, o motivo."""
    try:
        from app.services.linha_do_usuario.entrada import enviar_pela_linha
    except Exception as exc:  # noqa: BLE001 — a L2 ausente (ou quebrada no import) não derruba o aviso
        logger.error("[LINHA-AVISO] envio pela linha indisponivel: %s", type(exc).__name__)
        return "envio_indisponivel"
    try:
        r = await asyncio.wait_for(enviar_pela_linha(db, linha, texto), timeout=TEMPO_DO_ENVIO_S)
    except asyncio.TimeoutError:
        logger.error("[LINHA-AVISO] envio pela linha sem resposta em %.0f s", TEMPO_DO_ENVIO_S)
        return "envio_sem_resposta"
    except Exception as exc:  # noqa: BLE001
        logger.error("[LINHA-AVISO] envio pela linha falhou: %s", type(exc).__name__)
        return "falha_no_envio"
    try:
        enviadas = int((r or {}).get("enviadas") or 0) if isinstance(r, Mapping) else 0
    except (TypeError, ValueError):
        enviadas = 0
    return None if enviadas > 0 else "falha_no_envio"


# ---------------------------------------------------------------------------------------------------------------------
# a porta
# ---------------------------------------------------------------------------------------------------------------------
async def avisar(db: Any, *, company_id: Any, user_id: Any, tipo: Any, texto_markdown: Any) -> Dict[str, Any]:
    """Avisa a pessoa (company_id, user_id) pela linha DELA — se o `tipo` estiver ligado na chave. Senão, só registra.

    Devolve `{ok, tipo, enviado, motivo, registrado}` — nunca o texto. Nunca levanta. Async porque o envio da L2 é;
    o `DeliveryExecutor` (síncrono) o espera pelo `_esperar` que já tem."""
    t = str(tipo or "").strip().lower()
    if t == TIPO_SO_PELO_CENTRAL:
        return _saida(t, False, "so_pelo_central", False)
    if t not in TIPOS:
        return _saida(None, False, "tipo_desconhecido", False)
    cid, uid = _uuid(company_id), _uuid(user_id)
    if not cid or not uid:
        return _saida(t, False, "identidade_invalida", False)
    texto = str(texto_markdown or "").strip()
    if not texto:
        return _saida(t, False, "texto_vazio", False)
    tipo = t

    try:
        linha = await asyncio.to_thread(_linha_conectada, db, cid, uid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[LINHA-AVISO] linha ilegivel (%s): %s", tipo, type(exc).__name__)
        linha = None

    motivo: Optional[str]
    if not linha:
        motivo = "sem_linha"
    elif tipo not in tipos_ligados():
        motivo = "avisos_desligados"
    else:
        motivo = await _enviar(db, linha, texto)

    enviado = motivo is None
    registrado = await asyncio.to_thread(_registrar, db, cid, uid, tipo, enviado, motivo)
    logger.info("[LINHA-AVISO] %s: %s", tipo, "enviado" if enviado else motivo)
    return _saida(tipo, enviado, motivo, registrado)


# ---------------------------------------------------------------------------------------------------------------------
# a limpeza do anti-eco (P-132C-04)
# ---------------------------------------------------------------------------------------------------------------------
def limpar_anti_eco(db: Any = None, dias: Any = DIAS_DO_ANTI_ECO) -> int:
    """Apaga de `linha_mensagens_do_sistema` o que foi enviado há mais de `dias` (padrão 7). Devolve quantas.

    É retenção do SERVIDOR (todas as corretoras), filtrada SÓ por data — não lê conteúdo (a tabela só tem id e hash) e
    não escolhe corretora; por isso não há filtro de `company_id` aqui. `dias` < 1 ou inválido → o padrão: um parâmetro
    errado nunca apaga o anti-eco dos últimos minutos (o que impede a resposta do sistema de voltar como pergunta).
    `db=None` → o cliente de serviço. Nunca levanta (roda dentro do job de retenção que existe)."""
    try:
        d = int(dias)
    except (TypeError, ValueError):
        d = DIAS_DO_ANTI_ECO
    if isinstance(dias, bool) or d < 1:
        d = DIAS_DO_ANTI_ECO
    try:
        if db is None:
            from app.core.database import get_supabase_client

            db = get_supabase_client()
        corte = (datetime.now(timezone.utc) - timedelta(days=d)).isoformat()
        r = _t(db, TABELA_ANTI_ECO).delete().lt("enviada_em", corte).execute()
        n = len(getattr(r, "data", None) or [])
        if n:
            logger.info("[LINHA-AVISO] anti-eco: %d registro(s) com mais de %d dias apagado(s)", n, d)
        return n
    except Exception as exc:  # noqa: BLE001
        logger.warning("[LINHA-AVISO] limpeza do anti-eco falhou: %s", type(exc).__name__)
        return 0


__all__ = [
    "CHAVE", "TIPOS", "TIPO_SO_PELO_CENTRAL", "DIAS_DO_ANTI_ECO", "SECAO_DA_RENOVACAO", "FRASES",
    "tipos_ligados", "frase_do_motivo", "tipo_da_publicacao", "avisar", "limpar_anti_eco",
]
