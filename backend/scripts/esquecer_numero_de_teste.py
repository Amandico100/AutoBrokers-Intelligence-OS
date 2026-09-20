# -*- coding: utf-8 -*-
"""O número de teste volta a ser um desconhecido — sem apagar o que é prova.

O Founder usa um celular dele como "cliente de teste". Depois de dezenas de
conversas, o agente **lembra** dele: chama pelo nome, retoma o assunto, pula a
apresentação. Para medir a PRIMEIRA mensagem de um cliente novo, essa memória
precisa sair do caminho.

```
python scripts/esquecer_numero_de_teste.py --telefone 55DDD9XXXXXXX            # ENSAIO (padrão): só conta
python scripts/esquecer_numero_de_teste.py --telefone 55DDD9XXXXXXX --executar # escreve
python scripts/esquecer_numero_de_teste.py --restaurar CAMINHO_DO_BACKUP.json  # desfaz
```

🔴 **Três travas, nesta ordem:**

1. o telefone tem de estar em `BILLING_CANARIO_ALLOWLIST` ou em `CANARIO_TESTE_B`
   — a mesma regra que `app/main.py::_sinais_do_codigo` publica no `/health`.
   Número de cliente real **não passa**;
2. `--ensaio` é o PADRÃO. Escrever exige `--executar` escrito à mão;
3. o backup JSON é gravado **antes** da primeira escrita, FORA do repositório
   (`%USERPROFILE%/autobrokers-backups/`). Sem backup gravado, nada é apagado.

⚠️ **O que este script NÃO toca**, de propósito:

| tabela | por quê |
|---|---|
| `platform_sends`, `billing_sent_log` | ledger financeiro. O agente não lê nenhum dos dois para "lembrar" de alguém — `platform_outbound` os usa como trava de envio, não como memória. |
| `work_events`, `work_attempts`, `work_steps` | auditoria. Ficam; o que sai é só o VÍNCULO que o agente lê (`work_runs.conversation_id` → `NULL`). |
| `agent_memories` | é memória por PAPEL (`agent_task`/`block_key`), agregada, sem telefone. |

⛔ Nunca imprime telefone, nome de pessoa nem conteúdo de mensagem: só contagens
por tabela × corretora.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

try:  # pragma: no cover - conveniência de console
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


# ===========================================================================
# 1. AS VARIANTES DO TELEFONE — o motor que o produto já tem
# ===========================================================================
#
# 🔴 §9.4: o casamento é o do MOTOR, não de um regex reescrito aqui.
# `_variantes_do_telefone` devolve o número SEM o `55` e com/sem o nono dígito.
# O banco guarda as duas formas (`user_phone` costuma vir com `55`,
# `contraparte` sem), então a lista final precisa das quatro grafias mais o JID.

def _variantes_base(telefone: Any) -> set:
    from app.services.o_fim_do_atendimento import _variantes_do_telefone

    return set(_variantes_do_telefone(telefone))


def variantes(telefone: Any) -> List[str]:
    """Todas as grafias do mesmo número: com/sem `55`, com/sem o nono dígito."""
    base = _variantes_base(telefone)
    out: set = set()
    for d in base:
        out.add(d)
        out.add("55" + d)
    return sorted(out)


def variantes_jid(telefone: Any) -> List[str]:
    """As grafias de `user_id`: dígitos crus e os JID do WhatsApp."""
    out: set = set(variantes(telefone))
    for d in list(out):
        out.add(f"{d}@s.whatsapp.net")
        out.add(f"{d}@c.us")
    return sorted(out)


def digitos(telefone: Any) -> str:
    import re

    return re.sub(r"\D", "", str(telefone or ""))


def apelido(telefone: Any) -> str:
    """Um apelido estável e ANÔNIMO do número, para nome de arquivo e log."""
    return hashlib.sha256(digitos(telefone).encode()).hexdigest()[:8]


# ===========================================================================
# 2. A TRAVA — só número de teste do ambiente
# ===========================================================================

ENV_ALLOWLIST = "BILLING_CANARIO_ALLOWLIST"
ENV_DESTINO = "CANARIO_TESTE_B"


def numeros_de_teste_do_ambiente(env: Optional[Dict[str, str]] = None) -> List[str]:
    fonte = env if env is not None else os.environ
    brutos: List[str] = []
    brutos += str(fonte.get(ENV_ALLOWLIST, "") or "").split(",")
    brutos.append(str(fonte.get(ENV_DESTINO, "") or ""))
    return [b.strip() for b in brutos if b and b.strip()]


def e_numero_de_teste(telefone: Any, env: Optional[Dict[str, str]] = None) -> bool:
    """Falha para o lado do NÃO: ambiente vazio = nenhum número é de teste."""
    alvo = _variantes_base(telefone)
    if not alvo:
        return False
    for item in numeros_de_teste_do_ambiente(env):
        if _variantes_base(item) & alvo:
            return True
    return False


# ===========================================================================
# 3. O CLIENTE — uma superfície pequena o bastante para ter dublê
# ===========================================================================
#
# Quatro operações e um dialeto de condição. O dublê do teste implementa as
# MESMAS quatro, e `_casa` (puro) é o que decide em ambos — é por isso que o
# teste prova o motor, e não uma cópia do motor.

Clausula = Tuple[str, str, Any]  # (coluna, operador, valor)
OPS = ("eq", "in", "ilike_any", "ou")


def _texto(v: Any) -> str:
    return "" if v is None else str(v)


def _ilike(valor: Any, padrao: str) -> bool:
    import re as _re

    alvo = _texto(valor).lower()
    rx = "^" + ".*".join(_re.escape(p) for p in padrao.lower().split("%")) + "$"
    return bool(_re.match(rx, alvo))


def _casa(linha: Dict[str, Any], clausulas: Sequence[Clausula]) -> bool:
    """A condição, aplicada a UMA linha. Pura. É o mesmo julgamento do SQL."""
    for coluna, op, valor in clausulas:
        if op == "ou":
            if not any(_casa(linha, [c]) for c in valor):
                return False
        elif op == "eq":
            if _texto(linha.get(coluna)) != _texto(valor):
                return False
        elif op == "in":
            alvos = {_texto(v) for v in valor}
            if _texto(linha.get(coluna)) not in alvos:
                return False
        elif op == "ilike_any":
            if not any(_ilike(linha.get(coluna), p) for p in valor):
                return False
        elif op == "nao_nulo":
            if linha.get(coluna) is None:
                return False
        else:  # pragma: no cover - operador novo sem tradução é defeito
            raise ValueError(f"operador desconhecido: {op}")
    return True


def _sql(clausulas: Sequence[Clausula]) -> Tuple[str, List[Any]]:
    partes: List[str] = []
    params: List[Any] = []
    for coluna, op, valor in clausulas:
        if op == "ou":
            subs = [_sql([c]) for c in valor]
            partes.append("(" + " OR ".join(s for s, _ in subs) + ")")
            for _, p in subs:
                params += p
        elif op == "eq":
            partes.append(f"{coluna}::text = %s")
            params.append(_texto(valor))
        elif op == "in":
            partes.append(f"{coluna}::text = ANY(%s)")
            params.append([_texto(v) for v in valor])
        elif op == "ilike_any":
            partes.append(f"{coluna}::text ILIKE ANY(%s)")
            params.append(list(valor))
        elif op == "nao_nulo":
            partes.append(f"{coluna} IS NOT NULL")
        else:  # pragma: no cover
            raise ValueError(f"operador desconhecido: {op}")
    return (" AND ".join(partes) or "TRUE"), params


class ClientePg:
    """O cliente real. Só SELECT/DELETE/UPDATE parametrizados."""

    def __init__(self, dsn: str):
        import psycopg
        from psycopg.rows import dict_row

        self._conn = psycopg.connect(dsn, connect_timeout=30, prepare_threshold=None,
                                     autocommit=True, row_factory=dict_row)

    def tabela_existe(self, tabela: str) -> bool:
        cur = self._conn.execute(
            "select 1 from information_schema.tables where table_schema='public' and table_name=%s",
            (tabela,))
        return cur.fetchone() is not None

    def linhas(self, tabela: str, clausulas: Sequence[Clausula]) -> List[Dict[str, Any]]:
        onde, params = _sql(clausulas)
        return list(self._conn.execute(f"select * from {tabela} where {onde}", params).fetchall())

    def contar(self, tabela: str, clausulas: Sequence[Clausula]) -> int:
        """O ENSAIO conta no banco. 📊 `attendance_transcripts` tem 172.442
        linhas: trazer tudo para contar em Python levava minutos."""
        onde, params = _sql(clausulas)
        return int(self._conn.execute(
            f"select count(*) as n from {tabela} where {onde}", params).fetchone()["n"])

    def apagar(self, tabela: str, clausulas: Sequence[Clausula]) -> int:
        onde, params = _sql(clausulas)
        return self._conn.execute(f"delete from {tabela} where {onde}", params).rowcount

    def anular(self, tabela: str, coluna: str, clausulas: Sequence[Clausula]) -> int:
        onde, params = _sql(clausulas)
        return self._conn.execute(
            f"update {tabela} set {coluna} = NULL where {onde}", params).rowcount

    def revincular(self, tabela: str, coluna: str, valor: Any,
                   clausulas: Sequence[Clausula]) -> int:
        onde, params = _sql(clausulas)
        return self._conn.execute(
            f"update {tabela} set {coluna} = %s where {onde}", [valor] + params).rowcount

    def inserir(self, tabela: str, linhas: Sequence[Dict[str, Any]]) -> int:
        n = 0
        for linha in linhas:
            cols = list(linha.keys())
            marc = ", ".join(["%s"] * len(cols))
            vals = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in linha.values()]
            n += self._conn.execute(
                f"insert into {tabela} ({', '.join(cols)}) values ({marc}) on conflict do nothing",
                vals).rowcount
        return n

    def corretoras(self) -> List[Dict[str, Any]]:
        return list(self._conn.execute(
            "select id::text as id, company_name from companies order by company_name").fetchall())


# ===========================================================================
# 4. O PLANO — onde mora a memória, tabela por tabela
# ===========================================================================
#
# Cada entrada diz: (tabela, o que o agente lê dali, como achar as linhas).
# `APAGA` sai; `ANULA` fica e perde só o vínculo que o agente lê.

APAGA, ANULA, MANTEM = "APAGA", "ANULA", "MANTEM"


def alvos_da_corretora(company_id: str, telefone: Any,
                       ids_das_conversas: Sequence[str],
                       com_acervo: bool = False) -> List[Dict[str, Any]]:
    v = variantes(telefone)
    vj = variantes_jid(telefone)
    ids = [str(i) for i in ids_das_conversas]
    # `thread_id` do LangGraph = "{company_id}:whatsapp:{phone}:{company_id}:{sufixo}"
    # (graph.py:1753 + webhook.py:1055). É a memória que sobrevive a apagar
    # `messages` — sem ela o agente continua lembrando.
    fios = [f"{company_id}:whatsapp:{d}:%" for d in v]

    def _conv(coluna: str = "conversation_id") -> List[Clausula]:
        return [(coluna, "in", ids)]

    plano: List[Dict[str, Any]] = [
        # --- filhas primeiro (FK) -------------------------------------------
        {"tabela": "messages", "acao": APAGA, "onde": _conv(),
         "le": "o histórico que vira o contexto do LLM (core/database.py:279)"},
        {"tabela": "saudacoes_enviadas", "acao": APAGA, "onde": _conv(),
         "le": "o marcador de 'já cumprimentei este' (saudacao_do_religamento.py:298)"},
        {"tabela": "conversation_scorecards", "acao": APAGA, "onde": _conv(),
         "le": "nota da conversa anterior"},
        {"tabela": "work_waits", "acao": APAGA, "onde": _conv(),
         "le": "espera pendente presa à conversa"},
        {"tabela": "notas_da_atendente", "acao": APAGA,
         "onde": [("__ou__", "ou", [("conversation_id", "in", ids),
                                    ("autor_telefone", "in", v)])],
         "le": "nota livre da atendente sobre o contato"},
        # --- o vínculo que o agente lê sai; a auditoria FICA -----------------
        {"tabela": "work_runs", "acao": ANULA, "coluna": "conversation_id", "onde": _conv(),
         "le": "liga o run à conversa; `work_events` inteiro permanece"},
        {"tabela": "attendance_sessions", "acao": ANULA, "coluna": "conversation_id",
         "onde": _conv(),
         "le": "liga a sessão de acionamento à conversa do segurado"},
        # --- a conversa ------------------------------------------------------
        {"tabela": "conversations", "acao": APAGA, "onde": [("id", "in", ids)],
         "le": "user_name, ficha_atendimento, resolvido_em — o 'quem é você'"},
        # --- memória declarada -----------------------------------------------
        {"tabela": "user_memories", "acao": APAGA,
         "onde": [("company_id", "eq", company_id), ("user_id", "in", vj)],
         "le": "perfil e fatos do contato (memory_service.py:1193)"},
        {"tabela": "session_summaries", "acao": APAGA,
         "onde": [("company_id", "eq", company_id), ("user_id", "in", vj)],
         "le": "resumo das sessões anteriores (memory_service.py:1223)"},
        {"tabela": "conversation_logs", "acao": APAGA,
         "onde": [("company_id", "eq", company_id), ("user_id", "in", vj)],
         "le": "pergunta/resposta anteriores por user_id"},
        # --- o checkpoint do LangGraph ---------------------------------------
        {"tabela": "checkpoint_writes", "acao": APAGA, "onde": [("thread_id", "ilike_any", fios)],
         "le": "estado do grafo por thread"},
        {"tabela": "checkpoint_blobs", "acao": APAGA, "onde": [("thread_id", "ilike_any", fios)],
         "le": "blobs do estado do grafo"},
        {"tabela": "checkpoints", "acao": APAGA, "onde": [("thread_id", "ilike_any", fios)],
         "le": "🔴 a memória que SOBREVIVE a apagar `messages`"},
    ]
    # --- o acervo do observador: FORA por padrão ----------------------------
    #
    # 🔴 `attendance_*` é o corpus que a medição do piloto conta e de onde saem
    # os padrões de URA. O agente NÃO o lê para "lembrar" do segurado — quem o
    # lê é `dispatch_followup`, e só de um caso EM ANDAMENTO. Apagá-lo não é
    # necessário para a impressão de cliente novo, e é irreversível para a
    # medição. 📊 Um único número de teste soma 4.457 transcripts numa
    # corretora real. Só sai com `--com-acervo` escrito à mão.
    if com_acervo:
        plano += [
            {"tabela": "attendance_transcripts", "acao": APAGA,
             "onde": [("company_id", "eq", company_id), ("counterparty", "in", v)],
             "le": "telas e falas trocadas com esta contraparte"},
            {"tabela": "attendance_sessions", "acao": APAGA,
             "onde": [("company_id", "eq", company_id), ("counterparty", "in", v)],
             "le": "sessão de atendimento desta contraparte"},
        ]
    return plano


# As que NÃO entram no plano, e o porquê — escrito, para não virar esquecimento.
DEIXADAS = {
    "platform_sends": "ledger de envio da plataforma; o agente não o lê para lembrar",
    "billing_sent_log": "ledger financeiro (recibo/apólice)",
    "work_events": "auditoria — fica inteira; só o vínculo de `work_runs` sai",
    "agent_activities": "sem chave de telefone; é atividade por corretora",
    "agent_memories": "memória por papel (agent_task/block_key), não por contato",
    "company_memories": "memória da corretora, não do contato",
}


# ===========================================================================
# 5. REDIS — o transitório que também faz o agente "continuar de onde parou"
# ===========================================================================

def padroes_do_redis(telefone: Any, company_id: Optional[str] = None) -> List[str]:
    v = variantes(telefone)
    pads: List[str] = []
    for d in v:
        pads += [
            f"whatsapp_buffer:*:{d}", f"whatsapp_buffer:*:{d}@*",
            f"dispatch:active:*:{d}", f"dispatch:queue:*:{d}",
            f"carto:active:{d}",
            f"pausa_humana:*:{d}",
            f"platform_gate:*{d}*", f"platform_queue:*{d}*",
        ]
    return pads


async def _chaves_do_redis(padroes: Sequence[str]) -> List[str]:
    from app.core.redis import get_async_redis_client

    r = await get_async_redis_client()
    achadas: set = set()
    for p in padroes:
        async for k in r.scan_iter(match=p, count=500):
            achadas.add(k.decode() if isinstance(k, bytes) else str(k))
    return sorted(achadas)


async def _apagar_do_redis(chaves: Sequence[str]) -> int:
    from app.core.redis import get_async_redis_client

    r = await get_async_redis_client()
    n = 0
    for k in chaves:
        n += int(await r.delete(k) or 0)
    return n


# ===========================================================================
# 6. O CENSO E A EXECUÇÃO
# ===========================================================================

def _ids_das_conversas(cliente, company_id: str, telefone: Any) -> List[str]:
    v, vj = variantes(telefone), variantes_jid(telefone)
    onde: List[Clausula] = [
        ("company_id", "eq", company_id),
        ("__ou__", "ou", [("user_phone", "in", v), ("user_id", "in", vj),
                          ("contraparte", "in", v)]),
    ]
    return [str(l["id"]) for l in cliente.linhas("conversations", onde)]


def censo(cliente, telefone: Any, corretoras: Sequence[Dict[str, Any]],
          *, com_acervo: bool = False) -> Dict[str, Any]:
    """O que existe hoje, por tabela × corretora. NÃO escreve nada."""
    out: Dict[str, Any] = {"corretoras": [], "total": 0}
    for c in corretoras:
        cid, nome = str(c["id"]), c.get("company_name") or "?"
        ids = _ids_das_conversas(cliente, cid, telefone)
        linhas: List[Dict[str, Any]] = []
        for alvo in alvos_da_corretora(cid, telefone, ids, com_acervo):
            if not cliente.tabela_existe(alvo["tabela"]):
                continue
            onde = list(alvo["onde"])
            if alvo["acao"] == ANULA:
                onde.append((alvo["coluna"], "nao_nulo", None))
            n = cliente.contar(alvo["tabela"], onde)
            if n:
                linhas.append({"tabela": alvo["tabela"], "acao": alvo["acao"],
                               "n": n, "le": alvo["le"], "coluna": alvo.get("coluna")})
        n = sum(l["n"] for l in linhas if l["acao"] == APAGA)
        out["corretoras"].append({"id": cid, "nome": nome, "conversas": len(ids),
                                  "linhas": linhas})
        out["total"] += n
    return out


def _pasta_de_backup() -> str:
    base = os.environ.get("AUTOBROKERS_BACKUP_DIR") or os.path.join(
        os.path.expanduser("~"), "autobrokers-backups")
    os.makedirs(base, exist_ok=True)
    return base


def executar(cliente, telefone: Any, corretoras: Sequence[Dict[str, Any]],
             *, pasta: Optional[str] = None, com_acervo: bool = False) -> Dict[str, Any]:
    """🔴 Grava o backup ANTES da primeira escrita. Sem backup, nada sai."""
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino = os.path.join(pasta or _pasta_de_backup(),
                           f"esquecer-{carimbo}-{apelido(telefone)}.json")

    pacote: Dict[str, Any] = {"versao": 1, "quando": carimbo,
                              "telefone_apelido": apelido(telefone), "corretoras": []}
    trabalho: List[Tuple[str, Dict[str, Any], List[Dict[str, Any]]]] = []

    for c in corretoras:
        cid, nome = str(c["id"]), c.get("company_name") or "?"
        ids = _ids_das_conversas(cliente, cid, telefone)
        bloco: Dict[str, Any] = {"id": cid, "nome": nome, "tabelas": {}, "anulados": {}}
        for alvo in alvos_da_corretora(cid, telefone, ids, com_acervo):
            if not cliente.tabela_existe(alvo["tabela"]):
                continue
            achadas = cliente.linhas(alvo["tabela"], alvo["onde"])
            if alvo["acao"] == ANULA:
                achadas = [l for l in achadas if l.get(alvo["coluna"]) is not None]
                if achadas:
                    bloco["anulados"].setdefault(alvo["tabela"], []).extend(
                        [{"id": str(l.get("id")), alvo["coluna"]: str(l.get(alvo["coluna"]))}
                         for l in achadas])
            elif achadas:
                bloco["tabelas"].setdefault(alvo["tabela"], []).extend(achadas)
            if achadas:
                trabalho.append((cid, alvo, achadas))
        pacote["corretoras"].append(bloco)

    with open(destino, "w", encoding="utf-8") as f:
        json.dump(pacote, f, ensure_ascii=False, default=str, indent=1)
    if not os.path.exists(destino) or os.path.getsize(destino) <= 0:
        raise RuntimeError("backup não foi gravado — nada será apagado")

    feito: Dict[str, int] = {}
    for cid, alvo, achadas in trabalho:
        chave = f"{alvo['tabela']}:{alvo['acao']}"
        if alvo["acao"] == ANULA:
            n = cliente.anular(alvo["tabela"], alvo["coluna"], alvo["onde"])
        else:
            n = cliente.apagar(alvo["tabela"], alvo["onde"])
        feito[chave] = feito.get(chave, 0) + int(n or 0)
    return {"backup": destino, "escritas": feito}


def restaurar(cliente, caminho: str) -> Dict[str, int]:
    """Desfaz o que dá para desfazer: reinsere as linhas do backup.

    ⚠️ Reinsere PAIS antes de FILHAS. O que a FK apagou em cascata é
    reinserido daqui; o que ela pôs em `NULL` volta pelo bloco `anulados`.
    """
    with open(caminho, encoding="utf-8") as f:
        pacote = json.load(f)
    ordem = ["conversations", "messages", "saudacoes_enviadas", "conversation_scorecards",
             "work_waits", "notas_da_atendente", "user_memories", "session_summaries",
             "conversation_logs", "checkpoints", "checkpoint_blobs", "checkpoint_writes",
             "attendance_sessions", "attendance_transcripts"]
    feito: Dict[str, int] = {}
    for bloco in pacote.get("corretoras", []):
        tabelas = bloco.get("tabelas", {})
        for t in ordem + [t for t in tabelas if t not in ordem]:
            linhas = tabelas.get(t) or []
            if linhas and cliente.tabela_existe(t):
                feito[t] = feito.get(t, 0) + cliente.inserir(t, linhas)
        # e o vínculo anulado volta — as linhas reinseridas têm os MESMOS ids
        for t, marcas in (bloco.get("anulados") or {}).items():
            if not cliente.tabela_existe(t):
                continue
            for m in marcas:
                coluna = [k for k in m if k != "id"][0]
                feito[f"{t}.{coluna}"] = feito.get(f"{t}.{coluna}", 0) + cliente.revincular(
                    t, coluna, m[coluna], [("id", "eq", m["id"])])
    return feito


# ===========================================================================
# 7. A LINHA DE COMANDO
# ===========================================================================

def _imprimir(censo_: Dict[str, Any]) -> None:
    print(f"{'corretora':<26} {'tabela':<26} {'ação':<7} {'linhas':>7}  o que o agente lê dali")
    print("-" * 110)
    for c in censo_["corretoras"]:
        if not c["linhas"]:
            print(f"{c['nome'][:25]:<26} {'(nada casa)':<26} {'-':<7} {0:>7}")
            continue
        for i, l in enumerate(c["linhas"]):
            nome = c["nome"][:25] if i == 0 else ""
            print(f"{nome:<26} {l['tabela']:<26} {l['acao']:<7} {l['n']:>7}  {l['le']}")
    print("-" * 110)
    print(f"total de linhas que SAEM: {censo_['total']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="O número de teste volta a ser um desconhecido")
    ap.add_argument("--telefone", help="o número de teste (nunca vai para arquivo nem log)")
    ap.add_argument("--corretora", default=None,
                    help="nome ou id da corretora (padrão: TODAS onde o número aparece)")
    ap.add_argument("--executar", action="store_true", help="escreve de verdade")
    ap.add_argument("--ensaio", action="store_true", help="só conta (é o PADRÃO)")
    ap.add_argument("--restaurar", default=None, help="caminho do backup JSON a reinserir")
    ap.add_argument("--com-acervo", action="store_true",
                    help="também apaga attendance_sessions/transcripts (corpus do piloto)")
    ap.add_argument("--sem-redis", action="store_true", help="não toca nas chaves do Redis")
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv(os.path.join(RAIZ, ".env"))
    dsn = os.getenv("SUPABASE_DB_URL")
    if not dsn:
        print("⛔ SUPABASE_DB_URL ausente."); return 2

    cliente = ClientePg(dsn)

    if args.restaurar:
        print(json.dumps(restaurar(cliente, args.restaurar), ensure_ascii=False, indent=1))
        return 0

    telefone = args.telefone or os.getenv(ENV_DESTINO, "")
    if not digitos(telefone):
        print(f"⛔ passe --telefone (ou defina {ENV_DESTINO} no ambiente)."); return 2

    # 🔴 TRAVA 1
    if not e_numero_de_teste(telefone):
        print(f"⛔ RECUSADO: este número não está em {ENV_ALLOWLIST} nem em {ENV_DESTINO}.")
        print("   Só número de TESTE pode ser esquecido. Nada foi lido nem escrito.")
        return 3

    todas = cliente.corretoras()
    if args.corretora:
        alvo = str(args.corretora).strip().lower()
        todas = [c for c in todas
                 if alvo in (c.get("company_name") or "").lower() or alvo == str(c["id"])]
        if not todas:
            print("⛔ nenhuma corretora casa com --corretora."); return 2

    print(f"telefone: …{apelido(telefone)} (apelido) · corretoras: {len(todas)}")
    censo_ = censo(cliente, telefone, todas, com_acervo=args.com_acervo)
    _imprimir(censo_)

    if not args.sem_redis:
        import asyncio
        try:
            chaves = asyncio.run(_chaves_do_redis(padroes_do_redis(telefone)))
            print(f"redis: {len(chaves)} chave(s) casam os padrões do buffer/sessão/pausa")
        except Exception as e:  # noqa: BLE001
            chaves = []
            print(f"redis: indisponível daqui ({type(e).__name__}) — rode dentro do contêiner")

    if not args.executar:
        print("\nENSAIO (padrão). Nada foi escrito. Para valer: acrescente --executar")
        return 0

    # 🔴 TRAVA 3 — o backup vem antes
    r = executar(cliente, telefone, todas, com_acervo=args.com_acervo)
    print(f"\nbackup: {r['backup']}")
    print(json.dumps(r["escritas"], ensure_ascii=False, indent=1))
    if not args.sem_redis and chaves:
        import asyncio
        print(f"redis apagadas: {asyncio.run(_apagar_do_redis(chaves))}")
    print("\n✅ feito. Para desfazer: --restaurar " + r["backup"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
