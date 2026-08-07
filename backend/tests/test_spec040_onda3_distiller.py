# -*- coding: utf-8 -*-
"""SPEC-040 Onda 3 - Destilador do Espelho de Atendimento.

Cobre: mascaramento de PII ANTES da LLM, extracao por sessao (braçal Sonnet),
sintese de playbook com modelo FORTE (Opus default), cards com filtro de PII
em 2 camadas + dedupe, publicacao de card aprovado no RAG global (chunk
atomico), idempotencia (2a rodada sem custo), resiliencia de ERP no prompt do
atendente e fiacao no scheduler. Standalone (stubs, sem pytest).
"""

import asyncio
import importlib.util
import json
import os
import sys
import types

# A partir de 29/07/2026 `distill_once` não gasta nada sem um teto explícito
# (`DESTILADOR_TETO_POR_RODADA`, padrão 0). Este teste exercita justamente o
# caminho AUTORIZADO — ler conversas e sintetizar playbook —, então ele declara
# o teto como a produção declarará. Sem esta linha o teste passaria a validar o
# silêncio da trava, e não a destilação. Ver test_teto_de_gasto.py.
os.environ["DESTILADOR_TETO_POR_RODADA"] = "500"
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = FAIL = 0
FAILURES = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def _load(dotted, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


class _Result:
    def __init__(self, data=None):
        self.data = data or []


def _valor_em(linha, coluna):
    """Le `summary->distilled->>ramo` como o PostgREST le.

    O falso comparava `linha.get("summary->distilled->>ramo")`, que nunca
    existe, e devolvia lista vazia em silencio. Foi assim que a sintese de
    playbook passou no teste enquanto estava quebrada em producao.
    """
    if "->" not in coluna:
        return linha.get(coluna)
    partes = coluna.replace("->>", "->").split("->")
    atual = linha
    for parte in partes:
        if not isinstance(atual, dict):
            return None
        atual = atual.get(parte.strip())
    return atual


class _Table:
    def __init__(self, store, name):
        self.store, self.name = store, name
        self._mode = None
        self._payload = None
        self._on_conflict = None
        self._eq = []
        self._order = None
        self._desc = True
        self._limit = None
        self._range = None

    def select(self, *_a, **_k): self._mode = "select"; return self
    def insert(self, payload): self._mode = "insert"; self._payload = payload; return self

    def upsert(self, payload, on_conflict=None, ignore_duplicates=False):
        self._mode = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def update(self, payload): self._mode = "update"; self._payload = payload; return self
    def eq(self, col, val): self._eq.append((col, val)); return self

    def order(self, col, desc=True):
        self._order, self._desc = col, desc
        return self

    def limit(self, n): self._limit = n; return self

    def range(self, inicio, fim):
        """Paginação, como o PostgREST de verdade.

        O falso não tinha `range` e o Destilador quebrava com
        `'_Table' object has no attribute 'range'` — enquanto em produção
        rodava. Um falso que não sabe fazer o que o real faz esconde exatamente
        o defeito que a paginação existe para evitar: o corte silencioso em
        1.000 linhas.
        """
        self._range = (int(inicio), int(fim))
        return self

    def _rows(self):
        rows = list(self.store.get(self.name, []))
        for col, val in self._eq:
            rows = [r for r in rows if str(_valor_em(r, col)) == str(val)]
        if self._order:
            rows.sort(key=lambda r: str(r.get(self._order) or ""), reverse=self._desc)
        if self._limit:
            rows = rows[: self._limit]
        if self._range:
            inicio, fim = self._range
            rows = rows[inicio:fim + 1]
        return rows

    def execute(self):
        self.store.setdefault(self.name, [])
        if self._mode == "upsert" and self._on_conflict:
            key = self._on_conflict
            for r in self.store[self.name]:
                if r.get(key) == self._payload.get(key):
                    return _Result([])  # duplicado: ignorado
        if self._mode in ("insert", "upsert"):
            row = dict(self._payload)
            row.setdefault("id", f"{self.name}-{len(self.store[self.name]) + 1}")
            self.store[self.name].append(row)
            return _Result([row])
        if self._mode == "update":
            hit = self._rows()
            for r in hit:
                r.update(self._payload)
            return _Result(hit)
        return _Result(self._rows())


class _Supabase:
    def __init__(self, store):
        self.client = self
        self._store = store

    def table(self, name):
        return _Table(self._store, name)


class _Redis:
    def __init__(self):
        self.kv = {}

    async def set(self, key, val, ex=None): self.kv[key] = val
    async def get(self, key): return self.kv.get(key)


class _QdrantRec:
    def __init__(self):
        self.inserted = []

    def insert_embeddings(self, **kw):
        self.inserted.append(kw)
        return True


STAGE1 = {
    "tipo": "assistencia", "ramo": "auto", "servico": "guincho", "seguradora": "porto",
    "resumo_conduta": ["acolheu com empatia", "identificou pelo CPF", "coletou endereco"],
    "perguntas_na_ordem": ["onde o carro esta?", "para onde levar?"],
    "fatos_reutilizaveis": [
        "Porto oferece taxi para o cliente apos o guincho ser acionado",
        "Cliente com CPF 123.456.789-00 possui dois carros na Porto",
    ],
    "score": 82, "flags": [],
}
PLAYBOOK = {
    "objetivo": "acionar guincho sem friccao",
    "acolhimento": "Sinto muito pelo transtorno! Vou resolver isso agora com voce.",
    "ficha_coleta": [
        {"campo": "endereco_atual", "como_pedir": "Onde o carro esta agora?",
         "quando": "apos entender o problema", "ja_temos_na_apolice": False},
        {"campo": "placa", "como_pedir": "so confirmar", "quando": "antes de acionar",
         "ja_temos_na_apolice": True},
    ],
    "pre_checks": ["lembrar de retirar pertences do veiculo"],
    "sensibilidade": "cliente pode estar em rodovia: seguranca primeiro",
    "encerramento": "acompanhar ate o prestador chegar",
    "frases_exemplo": ["Ja estou acionando, fica tranquilo!"],
}


def _bootstrap():
    store, redis, qdrant = {}, _Redis(), _QdrantRec()
    for name in ("app", "app.core", "app.services", "app.services.atlas",
                 "app.factories", "langchain_core"):
        m = sys.modules.setdefault(name, types.ModuleType(name))
        m.__path__ = []

    db = types.ModuleType("app.core.database")
    db.get_supabase_client = lambda: _Supabase(store)
    sys.modules["app.core.database"] = db

    red = types.ModuleType("app.core.redis")

    async def _get_redis():
        return redis

    red.get_async_redis_client = _get_redis
    sys.modules["app.core.redis"] = red

    cfg = types.ModuleType("app.core.config")
    cfg.settings = types.SimpleNamespace(OPENAI_API_KEY="k")
    sys.modules["app.core.config"] = cfg

    utils = types.ModuleType("app.core.utils")
    utils.get_api_key_for_provider = lambda p, m: "key"
    sys.modules["app.core.utils"] = utils

    lcm = types.ModuleType("langchain_core.messages")

    class _Msg:
        def __init__(self, content):
            self.content = content

    lcm.SystemMessage = _Msg
    lcm.HumanMessage = _Msg
    sys.modules["langchain_core.messages"] = lcm

    lf = types.ModuleType("app.factories.llm_factory")

    class LLMFactory:
        calls = []

        @staticmethod
        def create_llm(company_config, agent_data, api_key, company_id=None, agent_id=None):
            model = agent_data.get("llm_model")

            class _LLM:
                async def ainvoke(self, msgs):
                    system, user = msgs[0].content, msgs[1].content
                    LLMFactory.calls.append({"model": model, "system": system, "user": user})
                    if "treinador" in system:
                        return types.SimpleNamespace(content=json.dumps(PLAYBOOK, ensure_ascii=False))
                    return types.SimpleNamespace(content=json.dumps(STAGE1, ensure_ascii=False))

            return _LLM()

    lf.LLMFactory = LLMFactory
    sys.modules["app.factories.llm_factory"] = lf

    lco = types.ModuleType("langchain_openai")

    class _Emb:
        def __init__(self, **_k): pass

        def embed_documents(self, chunks):
            return [[0.1, 0.2] for _ in chunks]

    lco.OpenAIEmbeddings = _Emb
    sys.modules["langchain_openai"] = lco

    qd = types.ModuleType("app.services.qdrant_service")
    qd.get_qdrant_service = lambda: qdrant
    sys.modules["app.services.qdrant_service"] = qd

    _load("app.core.heartbeat", "app/core/heartbeat.py")
    _load("app.services.atlas.templater", "app/services/atlas/templater.py")
    # A regra de identidade de mensagem. O Destilador a usa para nao mandar
    # a mesma linha duas vezes para a LLM; sem ela registrada aqui, TODAS as
    # sessoes falham com ModuleNotFoundError — foi o que aconteceu quando o
    # filtro de copias entrou, em 28/07/2026.
    _load("app.services.atlas.mensagem", "app/services/atlas/mensagem.py")
    # A curadoria das cartas roda dentro da rodada do Destilador. Sem
    # registrar aqui, o `except` engole um ModuleNotFoundError e o teste
    # concorda com uma publicacao que nunca acontece.
    #
    # E a curadoria chama `corridor_playbooks` para saber QUEM E SEGURADORA
    # (05/08/2026). A primeira rodada com a decisao nova falhou exatamente
    # assim: `ModuleNotFoundError (app.services.corridor_playbooks)` nas tres
    # sessoes, zero cartas gravadas — a mesma classe de 28/07/2026, e o teste
    # pegou de novo. A tabela de apelidos e uma so, entao a dependencia e real
    # e o lugar dela e aqui.
    _load("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
    _load("app.services.curadoria_cartas", "app/services/curadoria_cartas.py")
    _load("app.services.knowledge_scope", "app/services/knowledge_scope.py")
    dist = _load("app.services.attendance_distiller", "app/services/attendance_distiller.py")
    return dist, store, redis, qdrant, lf.LLMFactory


def _seed_sessions(store):
    from datetime import datetime, timedelta, timezone
    base = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
    store["attendance_sessions"] = []
    store["attendance_transcripts"] = []
    for i in range(3):
        sid = f"s{i + 1}"
        store["attendance_sessions"].append({
            "id": sid, "company_id": "c1", "observer_number": "5548911112222",
            "counterparty": f"554799911223{i}", "status": "closed",
            "started_at": (base + timedelta(hours=i)).isoformat(), "summary": {}})
        store["attendance_transcripts"] += [
            {"session_id": sid, "direction": "in", "msg_type": "text",
             "text": "Meu carro quebrou, meu CPF e 123.456.789-00, preciso de guincho por favor",
             "wa_timestamp": (base + timedelta(hours=i)).isoformat()},
            {"session_id": sid, "direction": "out", "msg_type": "text",
             "text": "Sinto muito! Ja estou verificando aqui, me diz onde o carro esta agora?",
             "wa_timestamp": (base + timedelta(hours=i, minutes=1)).isoformat()},
            {"session_id": sid, "direction": "in", "msg_type": "text",
             "text": "Rua das Flores 123, Palhoca. Pode levar para a oficina do centro",
             "wa_timestamp": (base + timedelta(hours=i, minutes=2)).isoformat()},
        ]


def run():
    print("== SPEC-040 Onda 3 - Destilador do Espelho ==\n")
    dist, store, redis, qdrant, factory = _bootstrap()
    _seed_sessions(store)

    stats = asyncio.run(dist.distill_once(force=True))

    # 1) estagio 1: todas as sessoes destiladas com score (baseline humano)
    check("3 sessoes destiladas", stats["sessions"] == 3, stats)
    d0 = (store["attendance_sessions"][0].get("summary") or {}).get("distilled") or {}
    check("summary com tipo/ramo/servico/score", d0.get("servico") == "guincho"
          and d0.get("score") == 82 and d0.get("ramo") == "auto", d0)

    # 2) PII mascarada ANTES da LLM (a LLM nunca ve o CPF real)
    stage1_calls = [c for c in factory.calls if "treinador" not in c["system"]]
    check("LLM recebeu transcript mascarado ({CPF})",
          stage1_calls and "{CPF}" in stage1_calls[0]["user"]
          and "123.456.789-00" not in stage1_calls[0]["user"],
          stage1_calls[0]["user"][:200] if stage1_calls else "sem chamadas")

    # 3) cards: limpo -> pending_review; com PII -> rejected_pii; dedupe por hash
    cards = store.get("knowledge_cards", [])
    pend = [c for c in cards if c.get("status") in ("pending_review", "published")]
    rej = [c for c in cards if c.get("status") == "rejected_pii"]
    # O card limpo nao PARA em pending_review: a mesma rodada ja o publica.
    # Verificar que ele "fica pendente" testaria o gargalo que foi removido.
    limpos = [c for c in cards if c.get("status") in ("pending_review", "published")]
    check("card limpo passou pelo filtro e foi publicado",
          len(limpos) == 1 and "taxi" in limpos[0]["card_text"]
          and limpos[0]["status"] == "published", cards)
    check("card com CPF rejeitado (rejected_pii)", len(rej) == 1, cards)
    check("dedupe: 3 sessoes iguais nao triplicam cards", len(cards) == 2, len(cards))

    # 4) playbook: sintetizado com o modelo FORTE (default claude-opus-5)
    pbs = store.get("conduct_playbooks", [])
    check("playbook draft criado", len(pbs) == 1 and pbs[0]["status"] == "draft"
          and pbs[0]["servico"] == "guincho", pbs)
    check("playbook usa modelo forte", pbs and pbs[0].get("model_used") == "claude-opus-5",
          pbs[0].get("model_used") if pbs else None)
    strong_calls = [c for c in factory.calls if "treinador" in c["system"]]
    check("sintese chamou o modelo forte", strong_calls
          and strong_calls[0]["model"] == "claude-opus-5",
          [c["model"] for c in strong_calls])
    check("playbook manda confirmar (nao perguntar) o que ja temos",
          any(f.get("ja_temos_na_apolice") for f in (pbs[0]["content"].get("ficha_coleta") or [])))

    # 4b) o playbook nasce mesmo quando a rodada NAO tocou o grupo.
    #
    # Com o historico inteiro ja destilado, quase nenhuma rodada toca grupo
    # nenhum. Se a sintese so olhasse os grupos tocados, os playbooks nunca
    # apareceriam — foi o que aconteceu em producao: 7.620 sessoes destiladas
    # e ZERO playbooks, com grupos de 152, 72 e 69 atendimentos parados.
    faltando = dist._grupos_sem_playbook_sync(5)
    check("varredura acha grupo com material e sem playbook",
          isinstance(faltando, list), faltando)
    # 🔴 O FATO MUDOU EM 07/08/2026, E A LIÇÃO MIGROU COM ELE (CLAUDE.md §9.3).
    #
    # Antes: QUALQUER playbook naquele par bloqueava a síntese para sempre —
    # inclusive um rascunho que ninguém aprovou. 📊 `auto/sinistro` ficou preso
    # em 30 conversas enquanto 1.405 eram destiladas: 2,1% do material, e nunca
    # mais. Não era o agente que piorava; era o agente que não podia melhorar.
    #
    # Agora só playbook **ativo** bloqueia. O guarda continua existindo — o que
    # ele guarda é outra coisa: que a rodada não reescreva de graça, no modelo
    # mais caro, um playbook que já está valendo.
    #
    # O playbook recém-sintetizado nasce `draft`, então o grupo VOLTA a ser
    # candidato — é exatamente isso que destrava a versão 2.
    check("grupo que acabou de ganhar playbook NAO volta na mesma rodada",
          ("auto", "guincho") not in faltando,
          "sem material novo nao ha o que aprender; refazer seria pagar para "
          "reescrever a mesma coisa no modelo mais caro")
    fonte_refresh = (ROOT / "app/services/attendance_distiller.py").read_text(encoding="utf-8")
    check("e a porta da versao 2 existe, medida em material novo",
          "DISTILLER_PLAYBOOK_REFRESH_MIN" in fonte_refresh
          and "novas_desde" in fonte_refresh,
          "quando chegar material suficiente DEPOIS do playbook, o grupo volta")

    # E o custo por rodada tem teto: cada playbook e uma chamada ao modelo mais
    # caro, e sem teto a primeira rodada tentaria sintetizar todos de uma vez.
    fonte_d = (ROOT / "app/services/attendance_distiller.py").read_text(encoding="utf-8")
    check("teto de playbooks por rodada", "DISTILLER_PLAYBOOKS_PER_RUN" in fonte_d)
    check("e a busca do grupo e feita pelo BANCO, nao filtrando em Python",
          'eq("summary->distilled->>ramo"' in fonte_d,
          "ler as 300 mais recentes e filtrar depois deu zero durante toda a "
          "recuperacao, que processa da mais antiga para a mais nova")

    # 5) idempotencia: 2a rodada nao gasta LLM
    calls_before = len(factory.calls)
    stats2 = asyncio.run(dist.distill_once(force=True))
    check("2a rodada: zero sessao nova, zero LLM",
          stats2["sessions"] == 0 and len(factory.calls) == calls_before, stats2)

    # 6) publicacao: acontece NA RODADA, nao num clique
    #
    # Este caso pegava `pend[0]` e publicava a mao. Com a publicacao dentro do
    # Destilador, `pending_review` fica VAZIO depois da rodada — o teste falhou
    # com IndexError, e falhou dizendo a verdade: o card ja tinha sido
    # publicado sozinho, que e exatamente o comportamento novo.
    publicados = [c for c in store.get("knowledge_cards", []) if c.get("status") == "published"]
    check("card publicado sozinho na rodada do Destilador",
          len(publicados) >= 1 and len(qdrant.inserted) >= 1,
          f"publicados={len(publicados)} chunks={len(qdrant.inserted)}")
    check("e o assunto entra no texto do chunk (busca hibrida casa por termo)",
          any("cobranca" in (ch or "") or "assistencia" in (ch or "")
              or "sinistro" in (ch or "") or "processo" in (ch or "")
              for kw in qdrant.inserted for ch in (kw.get("chunks") or [])),
          [kw.get("chunks") for kw in qdrant.inserted][:1])
    if qdrant.inserted:
        kw = qdrant.inserted[0]
        check("publicacao: colecao global + escopo publicado",
              kw.get("collection_name") == "autobrokers_global"
              and (kw.get("knowledge_extras") or {}).get("scope") == "global_autobrokers", kw)
        check("card e chunk atomico (1 chunk)", len(kw.get("chunks") or []) == 1)
    bad = dict((publicados or store.get("knowledge_cards", []))[0])
    bad["card_text"] = "Cliente CPF 123.456.789-00 tem dois carros"
    check("card com PII NUNCA publica", dist.publish_card_sync(bad) is False)

    # 7) heartbeat do Espelho pulsou na destilacao
    hb = redis.kv.get("spec034:heartbeat:espelho_atendimento")
    check("heartbeat espelho_atendimento pulsou", hb is not None and "last_run" in str(hb))

    # 8) resiliencia de ERP no prompt do atendente + fiacao no scheduler
    prompts_src = (ROOT / "app/core/prompts.py").read_text(encoding="utf-8")
    check("prompt: sistema fora do ar nunca trava o atendimento",
          "SISTEMA LENTO OU FORA DO AR" in prompts_src and "nunca trave" in prompts_src.lower())
    sched_src = (ROOT / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    check("scheduler: destilador agendado", "attendance_distiller_check" in sched_src)
    admin_src = (ROOT / "app/api/admin_atlas.py").read_text(encoding="utf-8")
    check("admin: endpoints do espelho (resumo/cards/playbooks/run)",
          "/espelho/resumo" in admin_src and "/espelho/cards" in admin_src
          and "/espelho/playbooks" in admin_src and "/espelho/run" in admin_src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
