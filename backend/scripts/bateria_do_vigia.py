# -*- coding: utf-8 -*-
"""SPEC-119 F4 · BATERIA 4 — VIGIA → SENTINELA → CÉREBRO, com um travamento FORÇADO.

🔴 POR QUE ESTA BATERIA EXISTE
==============================
📊 Os três nunca rodaram com tráfego real, e a SPEC-119 §2 marca o elo ⑦ como o
que *"NUNCA rodou"*. Existem guardas de `diagnose` e da escada, mas **nenhum
atravessa o laço inteiro com o CÉREBRO de verdade do outro lado** — e é o cérebro
que decide se o acionamento desentrava ou se o segurado espera uma pessoa.

⛔ **NUNCA se roda isto com tráfego real.** O laço varre `dispatch:active:*` no
Redis de produção; aqui o Redis é um dublê com UMA sessão, a que este script
travou de propósito. Nenhuma sessão real é lida, nenhuma mensagem sai.

O QUE É REAL E O QUE É BORDA
----------------------------
```
REAL   dispatch_watchdog.check_dispatch_watchdog   o LAÇO, do scan ao beat
REAL   dispatch_watchdog.diagnose                  quem decide que travou
REAL   dispatch_watchdog._sentinela_recover        a ESCADA (tentativa por tela
                                                   e teto de sessão)
REAL   dispatch_watchdog._adaptive_reply           o CÉREBRO — rota `dispatch`
                                                   (📊 anthropic:claude-opus-5-5),
                                                   com `invocar_com_reserva`
REAL   insurer_dispatch_service.build_human_phase_messages   o PROMPT do produto
REAL   insurer_dispatch_service.guard_human_phase_reply      o fiscal da resposta
REAL   insurer_dispatch_service.build_handoff_dossier        o dossiê do handoff
REAL   a TELA que trava: vem de tests/corpus/telas_reais/*.jsonl e é escolhida
       PELO MOTOR — `match_ura_step` não a reconhece (§9.4: acervo, não imaginação)

BORDA  Redis (uma sessão) · WhatsApp (`send_message` vira lista) ·
       `save_active_dispatch` · `_anotar_vigia` · `_ato_do_vigia` /
       `_ato_do_sentinela` · `registrar_ato_do_agente` · `_support_alert` ·
       `beat` · `check_cartographer_stalls`
```

🔴 **E O LEDGER NÃO É TOCADO COMO PRODUTO.** O braço é construído pela fábrica do
produto e passado por `evals/bancada.isolar_do_produto` — a MESMA função que a
bancada usa (⛔ nunca uma isolação nova): sai o `RelogioDoModeloCallback`, que
escreve no disjuntor de PRODUÇÃO, e o custo vai como `service_type='bancada'` com
`company_id` NULO. Sem isso, uma medição fecharia o breaker do atendimento.

AS LINHAS DE CONTROLE (CLAUDE.md §9.2) — três
---------------------------------------------
```
A  🔴 A ATENDENTE NA CONVERSA: a mesma sessão travada, com a pausa humana aberta.
   `diagnose` tem de devolver None, o laço tem de tomar ZERO ações e o cérebro
   NÃO pode ser chamado — 📊 conferido pelo contador de chamadas E pelo GASTO,
   que tem de ser US$ 0,00. É o controle mais forte: ele custa dinheiro se falhar.
B  🔴 O TETO: a mesma tela, com as tentativas já gastas. O cérebro NÃO é chamado
   e o caso vai a `needs_human` com `reason='sentinela_stall'` e dossiê.
C  🔴 O CÉREBRO RECUSADO: com um cérebro DUBLÊ que responde uma frase que o
   fiscal reprova (promete protocolo), NADA sai para a seguradora e a tentativa
   é consumida. Prova que o fiscal está no caminho, e não ao lado dele.
```

⚠️ NÃO-DETERMINISMO: o cérebro é um modelo, e varia. Este arquivo é um SCRIPT, e
de propósito: ele NÃO entra no `pytest`, porque teste que chama API quebra sozinho
e queima crédito. `--k` repete o cenário; o script imprime tentativa a tentativa.

    cd backend
    # de graça (cérebro dublê, nenhuma API):
    python scripts/bateria_do_vigia.py --cerebro duble
    # o cérebro REAL da rota `dispatch`:
    python scripts/bateria_do_vigia.py --cerebro real --teto-usd 1.00
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")   # armadilha nº 2 do pacote

#: A rota cujo playbook trava. 📊 `yelum-auto-whatsapp@v3` é uma das duas
#: seguradoras com `socorro_mecanico` e tem 79 sessões no acervo.
REF = "yelum-auto-whatsapp@v3"
SUB = "guincho"
CORPUS = "yelum-auto.jsonl"
#: A rota da cena ②: a tela que a F3 manda a UMA PESSOA. 📊 As 19 telas de
#: `escolhe_o_servico` e as 18 de `aceite_de_custo` do acervo estão na allianz.
REF_HANDOFF = "allianz-auto-whatsapp@v1"
CORPUS_HANDOFF = "allianz-auto.jsonl"
#: ⛔ Números NOSSOS, de teste. Nenhum telefone de pessoa (CLAUDE.md §13.9).
TEL_SEGURADORA = "5500000000000"
#: Tenant FICTÍCIO — o mesmo desenho da bancada (`evals/bancada.TENANTS`).
COMPANY = "00000000-0000-4000-8000-0000000000a1"


# ═════════════════════════════════════════════════════════════════════════════
# A TELA QUE TRAVA — do ACERVO, escolhida pelo MOTOR
# ═════════════════════════════════════════════════════════════════════════════
def tela_que_o_corredor_nao_conhece() -> Dict[str, Any]:
    """Uma tela REAL que pede algo e que `match_ura_step` NÃO reconhece.

    🔴 É o travamento que o produto vive: a URA falou, o corredor não soube
    responder, e o transcript fica com a última entrada `in`. Quem escolhe é o
    motor — se o acervo deixar de ter uma tela assim, o script ACUSA em vez de
    inventar uma frase que a Yelum nunca escreveu (CLAUDE.md §9.4).
    """
    from app.services.corridor_playbooks import get_playbook, match_ura_step

    caminho = os.path.join(RAIZ, "tests", "corpus", "telas_reais", CORPUS)
    pb = get_playbook(REF)
    candidatas = []
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            if not linha.strip():
                continue
            d = json.loads(linha)
            texto = str(d.get("text") or "")
            if len(texto) < 40 or "?" not in texto:
                continue                      # sem pergunta não é travamento
            if match_ura_step(pb, texto, SUB):
                continue                      # o corredor conhece: não trava
            candidatas.append(d)
    if not candidatas:
        raise AssertionError(
            f"nenhuma tela de {CORPUS} pede algo e escapa de `match_ura_step` — "
            "o travamento FORÇADO não tem como ser forçado sobre o acervo")
    # A mais curta: o prompt do cérebro fica legível no relatório e a conta menor.
    return min(candidatas, key=lambda d: len(str(d.get("text") or "")))


def tela_que_a_F3_manda_a_uma_pessoa() -> Dict[str, Any]:
    """Uma tela REAL que o corredor não conhece e que a F3 manda A UMA PESSOA.

    🔴 É A COSTURA QUE A F4 EXISTE PARA FAZER. A F3 criou a classe de passo
    (`insurer_dispatch_service.classe_da_tela`) e duas famílias dela têm
    `handoff: True` — `escolhe_o_servico` e `aceite_de_custo`. 📊 Medido em
    27/09/2026 sobre o acervo: 19 telas de `escolhe_o_servico` e 18 de
    `aceite_de_custo` escapam de `match_ura_step`.

    A pergunta desta cena: **o SENTINELA honra essa decisão?** Ele é o outro
    caminho que fala com a seguradora, e `grep -n classe_da_tela` acha UM
    chamador — dentro de `handle_insurer_message`. O Sentinela não passa por lá.
    """
    from app.services.corridor_playbooks import get_playbook, match_ura_step
    from app.services.insurer_dispatch_service import classe_da_tela

    caminho = os.path.join(RAIZ, "tests", "corpus", "telas_reais", CORPUS_HANDOFF)
    pb = get_playbook(REF_HANDOFF)
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            if not linha.strip():
                continue
            d = json.loads(linha)
            texto = str(d.get("text") or "")
            if len(texto) < 30 or match_ura_step(pb, texto, SUB):
                continue
            classe = classe_da_tela(pb, texto, slots={})
            if classe.get("handoff"):
                d["_classe"] = classe
                return d
    raise AssertionError(
        f"nenhuma tela de {CORPUS_HANDOFF} é classificada com `handoff: True` — "
        "a costura da F3 não tem como ser conferida sobre o acervo")


def sessao_travada(tela: str, *, gastas_na_tela: int = 0,
                   com_atendente: bool = False) -> Dict[str, Any]:
    """A sessão que o Redis dublê entrega — travada HÁ QUANTO TEMPO IMPORTA.

    🔴 `state='ura'`, última entrada `direction='in'`, idade acima de
    `URA_UNANSWERED_S`. É exatamente a forma que `diagnose` classifica como
    `stall_unanswered` — e ela é montada com os campos do PRODUTO, não com um
    dicionário conveniente.
    """
    from app.tasks.dispatch_watchdog import URA_UNANSWERED_S

    agora = datetime.now(timezone.utc)
    travou_em = (agora - timedelta(seconds=URA_UNANSWERED_S + 30)).isoformat()
    s: Dict[str, Any] = {
        "case_id": "b4-travamento", "company_id": COMPANY,
        "playbook_ref": REF, "subservice": SUB,
        "state": "ura", "live": True,
        "created_at": (agora - timedelta(minutes=4)).isoformat(),
        "slots": {
            "titular_cpf": "52998224725",
            "veiculo_placa": "ABC1D23",
            "local_atual": "R. Exemplo Um, 0, Centro, Florianopolis - SC, 88000-000",
            "local_destino": "Oficina Central, Rua B, 50, Sao Jose - SC",
            "problema_descricao": "o carro nao liga",
            "telefone_contato": "48991234567",
        },
        "transcript": [
            {"direction": "out", "text": "Ola, aqui e a corretora. Preciso de guincho.",
             "at": (agora - timedelta(minutes=3)).isoformat()},
            {"direction": "in", "text": tela, "at": travou_em},
        ],
    }
    if gastas_na_tela:
        from app.services.insurer_dispatch_service import id_da_tela
        s["tentativas_por_tela"] = {id_da_tela(tela): gastas_na_tela}
        s["sentinela_attempts"] = gastas_na_tela
    if com_atendente:
        # 🔴 A PAUSA HUMANA, escrita pelo PRODUTO — não um campo inventado aqui.
        #    `uma_fala_da_atendente` é a única porta que a abre
        #    (`insurer_dispatch_service.py:563`), e ela escreve `pausa_humana`
        #    E `silencio_deliberado_ate` juntos, que é o par que o Vigia honra.
        from app.services.insurer_dispatch_service import uma_fala_da_atendente
        veredito = uma_fala_da_atendente(s)
        if veredito != "aberta":     # PAUSA_HUMANA_S=0 desligaria a pausa
            raise AssertionError(
                f"a pausa humana não abriu ({veredito!r}) — o CONTROLE A não tem "
                "como ser exercitado; confira PAUSA_HUMANA_S")
    return s


# ═════════════════════════════════════════════════════════════════════════════
# A BORDA — Redis, WhatsApp, banco. Tudo o que DECIDE fica real.
# ═════════════════════════════════════════════════════════════════════════════
class RedisDeUmaSessao:
    """`scan_iter` + `get` sobre UMA chave. ⛔ Nenhuma sessão real é lida."""

    def __init__(self, chave: str, payload: str) -> None:
        self.chave, self.payload = chave, payload
        self.lidas = 0

    async def scan_iter(self, match: str = "*"):
        pref = match.rstrip("*")
        if self.chave.startswith(pref):
            yield self.chave.encode()

    async def get(self, k):
        self.lidas += 1
        return self.payload.encode()


class WhatsAppDeMentira:
    def __init__(self) -> None:
        self.enviadas: List[Dict[str, Any]] = []

    def send_message(self, to, text, integration=None):
        self.enviadas.append({"para": to, "texto": text})
        return {"ok": True}


class IntegracoesDeMentira:
    def get_integration_by_channel(self, *_a, **_k):
        return {"id": "int-teste", "provider": "evolution_go", "is_active": True}

    def __getattr__(self, _nome):     # qualquer outro getter devolve o mesmo
        return lambda *_a, **_k: {"id": "int-teste", "provider": "evolution_go",
                                  "is_active": True}


class Contador:
    """Quantas vezes o CÉREBRO foi chamado, e quanto custou — pela conta do produto."""

    def __init__(self) -> None:
        self.chamadas = 0
        self.tokens_in = self.tokens_out = 0
        self.respostas: List[str] = []
        self.cru: List[str] = []   # o `.content` CRU, para o relatório comparar

    def custo_usd(self, modelo: str) -> float:
        """📊 `usage_service.calculate_cost` — a MESMA conta do ledger."""
        if not (self.tokens_in or self.tokens_out):
            return 0.0
        from app.services.usage_service import get_usage_service
        return float(get_usage_service().calculate_cost(
            modelo, self.tokens_in, self.tokens_out, 0, 0, 0))


def _cerebro_duble(texto: str):
    """Um cérebro que responde SEMPRE a mesma frase. Nenhuma API, custo zero."""
    async def _fn(_company_id, _session, _insurer_text):
        return texto
    return _fn


def _isolar_a_fabrica(contador: Contador):
    """O braço REAL, pela fábrica do produto, ISOLADO do produto.

    ⛔ Não é uma fábrica nova (CLAUDE.md §5): é `LLMFactory.create_llm` com os
    rótulos da bancada e `evals/bancada.isolar_do_produto` por cima — a função
    que já existe para isto. Ela tira o `RelogioDoModeloCallback` (que escreve no
    disjuntor de PRODUÇÃO) e CONFERE que o custo sai como `service_type='bancada'`
    com `company_id` NULO.
    """
    from app.factories.llm_factory import LLMFactory
    from app.services.evals.bancada import (MAX_TOKENS_DA_BANCADA,
                                            SERVICE_TYPE_DA_BANCADA,
                                            isolar_do_produto)

    real = LLMFactory.create_llm

    def _criar(*a, **kw):
        kw = {**kw, "company_id": None, "agent_id": None,
              "service_type": SERVICE_TYPE_DA_BANCADA}
        try:
            llm = real(*a, **kw, max_tokens=MAX_TOKENS_DA_BANCADA)
        except TypeError:
            llm = real(*a, **kw)
        llm = isolar_do_produto(llm)
        return _MedidoPorFora(llm, contador)

    LLMFactory.create_llm = staticmethod(_criar)
    return real


class _MedidoPorFora:
    """Conta chamadas e tokens do braço. Não decide nada."""

    def __init__(self, interno, contador: Contador) -> None:
        self._interno, self._c = interno, contador

    def __getattr__(self, nome):
        return getattr(self._interno, nome)

    async def ainvoke(self, *a, **kw):
        self._c.chamadas += 1
        out = await self._interno.ainvoke(*a, **kw)
        uso = getattr(out, "usage_metadata", None) or {}
        self._c.tokens_in += int(uso.get("input_tokens") or 0)
        self._c.tokens_out += int(uso.get("output_tokens") or 0)
        # 🔴 DUAS LINHAS, e a diferença entre elas é o defeito da SPEC-119 F4b:
        #    `content` CRU é a lista de blocos que o modelo devolveu; `texto` é o
        #    que o PRODUTO passou a usar (`agents/utils.extract_text_from_content`).
        #    Imprimir só o cru faria este script mentir sobre o conserto dele.
        from app.agents.utils import extract_text_from_content

        cru = getattr(out, "content", "")
        self._c.respostas.append(extract_text_from_content(cru).strip()[:400])
        self._c.cru.append(str(cru)[:160])
        return out


# ═════════════════════════════════════════════════════════════════════════════
# O LAÇO, RODADO DE VERDADE
# ═════════════════════════════════════════════════════════════════════════════
async def rodar_o_laco(sessao: Dict[str, Any], *, cerebro: str,
                       contador: Contador, resposta_do_duble: str = "") -> Dict[str, Any]:
    """`check_dispatch_watchdog()` REAL sobre UMA sessão. Devolve o diário."""
    import app.tasks.dispatch_watchdog as WD
    from app.core import heartbeat as HB
    from app.core import redis as REDIS
    from app.services import cartographer_runner as CART
    from app.services import dispatch_router as ROUTER
    from app.services import integration_service as INTEG
    from app.services import whatsapp_service as WAS

    chave = f"dispatch:active:{COMPANY}:{TEL_SEGURADORA}"
    redis = RedisDeUmaSessao(chave, json.dumps(sessao, ensure_ascii=False))
    wa = WhatsAppDeMentira()
    diario: Dict[str, Any] = {"gravadas": [], "anotacoes": [], "atos": [],
                             "alertas": [], "beats": []}

    async def _salvar(company_id, phone, s):
        diario["gravadas"].append(json.loads(json.dumps(s, ensure_ascii=False)))

    async def _anotar(company_id, finding, s, label):
        diario["anotacoes"].append({"finding": finding, "label": label})

    async def _ato_vigia(company_id, s, finding):
        diario["atos"].append({"agente": "vigia", "finding": finding})

    async def _ato_sent(company_id, s, desfecho, payload=None):
        diario["atos"].append({"agente": "sentinela", "desfecho": desfecho,
                               "payload": payload})

    async def _alerta(company_id, text, *_a, **_k):
        diario["alertas"].append(text[:160])
        return True

    async def _beat(nome, n=0):
        diario["beats"].append({"nome": nome, "acoes": n})

    async def _dossie(company_id, s, dossier, _wa, _integration):
        diario["dossies"] = diario.get("dossies", []) + [str(dossier)[:400]]
        return True

    async def _avisa(s, _wa, _integration):
        diario["avisos_ao_segurado"] = diario.get("avisos_ao_segurado", 0) + 1
        return True

    async def _cart():
        return 0

    async def _ler(*_a, **_k):
        return None

    async def _ato_agente(*_a, **_k):
        diario["atos"].append({"agente": "registrar_ato_do_agente"})

    guardados: Dict[str, Any] = {}
    fabrica_real = None
    try:
        for mod, nome, novo in (
            (REDIS, "get_async_redis_client", lambda: _coro(redis)),
            (WAS, "get_whatsapp_service", lambda: wa),
            (INTEG, "get_integration_service", lambda: IntegracoesDeMentira()),
            (ROUTER, "save_active_dispatch", _salvar),
            (ROUTER, "_ler_do_redis", _ler),
            (ROUTER, "registrar_ato_do_agente", _ato_agente),
            (WD, "_anotar_vigia", _anotar),
            (WD, "_ato_do_vigia", _ato_vigia),
            (WD, "_ato_do_sentinela", _ato_sent),
            (WD, "_support_alert", _alerta),
            (WD, "_entregar_dossie_com_marcador", _dossie),
            (WD, "_avisar_o_segurado", _avisa),
            (HB, "beat", _beat),
            (CART, "check_cartographer_stalls", _cart),
        ):
            guardados[f"{mod.__name__}.{nome}"] = (mod, nome, getattr(mod, nome, None))
            setattr(mod, nome, novo)

        if cerebro == "duble":
            guardados["WD._adaptive_reply"] = (WD, "_adaptive_reply", WD._adaptive_reply)
            WD._adaptive_reply = _cerebro_duble(resposta_do_duble)
        else:
            fabrica_real = _isolar_a_fabrica(contador)

        t0 = time.perf_counter()
        diario["acoes"] = await WD.check_dispatch_watchdog()
        diario["relogio_s"] = round(time.perf_counter() - t0, 2)
    finally:
        for _k, (mod, nome, antigo) in guardados.items():
            if antigo is not None:
                setattr(mod, nome, antigo)
        if fabrica_real is not None:
            from app.factories.llm_factory import LLMFactory
            LLMFactory.create_llm = staticmethod(fabrica_real)

    diario["enviadas_para_a_seguradora"] = wa.enviadas
    diario["leituras_do_redis"] = redis.lidas
    return diario


async def _coro(valor):
    return valor


# ═════════════════════════════════════════════════════════════════════════════
# OS CENÁRIOS
# ═════════════════════════════════════════════════════════════════════════════
def _resumo(diario: Dict[str, Any]) -> Dict[str, Any]:
    final = (diario.get("gravadas") or [{}])[-1] if diario.get("gravadas") else {}
    return {
        "acoes": diario.get("acoes"),
        "estado_final": final.get("state"),
        "motivo_final": str(final.get("reason") or ""),
        "destravado_por": final.get("destravado_por"),
        "enviou_a_seguradora": [e["texto"][:90] for e in diario["enviadas_para_a_seguradora"]],
        "tentativas_por_tela": final.get("tentativas_por_tela"),
        "dossier_sent": final.get("dossier_sent"),
        "atos": [a.get("desfecho") or a.get("finding") or a.get("agente") for a in diario["atos"]],
        "dossies": len(diario.get("dossies") or []),
        "avisos_ao_segurado": diario.get("avisos_ao_segurado", 0),
        "relogio_s": diario.get("relogio_s"),
    }


async def cenarios(cerebro: str, teto_usd: float, k: int) -> int:
    from app.tasks.dispatch_watchdog import (MAX_TENTATIVAS_NA_SESSAO,
                                             MAX_TENTATIVAS_POR_TELA,
                                             URA_UNANSWERED_S, diagnose)

    tela_d = tela_que_o_corredor_nao_conhece()
    tela = str(tela_d["text"])
    print("=" * 112)
    print("BATERIA 4 · VIGIA → SENTINELA → CÉREBRO, com um travamento FORÇADO")
    print("=" * 112)
    print(f"rota ................ {REF} · {SUB}")
    print(f"cérebro ............. {cerebro}")
    print(f"tetos da escada ..... {MAX_TENTATIVAS_POR_TELA} por tela · "
          f"{MAX_TENTATIVAS_NA_SESSAO} na sessão · trava em {URA_UNANSWERED_S}s")
    print(f"tela do acervo ...... {CORPUS} · sessão {str(tela_d.get('session_id'))[:8]} · "
          f"serviço {tela_d.get('servico')}")
    print(f"  📊 e `match_ura_step` NÃO a reconhece — é por isso que ela trava")
    print(f"  TEXTO: {tela[:200]!r}")

    s0 = sessao_travada(tela)
    print(f"\ndiagnose(sessão travada) = {diagnose(s0)!r}   "
          f"← tem de ser 'stall_unanswered', senão nada abaixo acontece")

    falhas = 0
    gasto_total = 0.0
    modelo = ""
    if cerebro == "real":
        from app.factories.llm_factory import LLMFactory
        r = LLMFactory.resolver_para({}, {}, papel="dispatch")
        modelo = r.model
        print(f"braço REAL da rota `dispatch` = {r.provider}:{r.model}"
              + (f" (reserva {r.reserva.provider}:{r.reserva.model})" if r.reserva else ""))

    # ── ① O TRAVAMENTO ──────────────────────────────────────────────────────
    for tentativa in range(1, k + 1):
        c = Contador()
        d = await rodar_o_laco(sessao_travada(tela), cerebro=cerebro, contador=c,
                               resposta_do_duble="1")
        custo = c.custo_usd(modelo) if modelo else 0.0
        gasto_total += custo
        r = _resumo(d)
        print(f"\n① TRAVAMENTO FORÇADO (tentativa {tentativa}/{k})  custo US$ {custo:.6f}")
        for ch, v in r.items():
            print(f"     {ch:26s} {v}")
        if c.respostas or c.cru:
            print(f"     {'.content CRU do modelo':26s} {(c.cru or [''])[0]!r}")
            print(f"     {'o que o PRODUTO usou':26s} {(c.respostas or [''])[0]!r}")
        destravou = bool(r["enviou_a_seguradora"]) and r["estado_final"] == "ura"
        print(f"     {'DESENTRAVOU?':26s} {'✅ SIM' if destravou else '🔴 NÃO'}")
        if not destravou:
            falhas += 1
        if gasto_total > teto_usd:
            print(f"\n⛔ TETO DE GASTO ATINGIDO (US$ {gasto_total:.4f} > {teto_usd:.2f}) — paro aqui")
            break

    # ── ② A COSTURA DA F3 · a tela que o corredor manda a uma PESSOA ────────
    tela_h = tela_que_a_F3_manda_a_uma_pessoa()
    th = str(tela_h["text"])
    ch = Contador()
    dh = await rodar_o_laco(sessao_travada(th), cerebro=cerebro, contador=ch,
                            resposta_do_duble="1")
    rh = _resumo(dh)
    custo_h = ch.custo_usd(modelo) if modelo else 0.0
    gasto_total += custo_h
    print("")
    print(f"② A COSTURA DA F3 — a tela é `{tela_h['_classe']['chave']}` "
          f"(handoff=True para o corredor)   custo US$ {custo_h:.6f}")
    print(f"     acervo ................... {CORPUS_HANDOFF} · sessão "
          f"{str(tela_h.get('session_id'))[:8]} · serviço {tela_h.get('servico')}")
    print(f"     TEXTO .................... {th[:160]!r}")
    print(f"     porque (F3) .............. {tela_h['_classe']['porque'][:120]}")
    for cchave in ("estado_final", "motivo_final", "enviou_a_seguradora",
                   "dossies", "avisos_ao_segurado"):
        print(f"     {cchave:26s} {rh[cchave]}")
    if ch.respostas or ch.cru:
        print(f"     {'o que o PRODUTO usou':26s} {(ch.respostas or [''])[0]!r}")
    honrou = not rh["enviou_a_seguradora"]
    print(f"     🔴 O SENTINELA HONRA O HANDOFF DA F3? "
          f"{'✅ SIM' if honrou else '🔴 NÃO — ele respondeu uma tela que o corredor manda a uma PESSOA'}")

    # ── ③ CONTROLE A · a atendente na conversa ──────────────────────────────
    ca = Contador()
    sa = sessao_travada(tela, com_atendente=True)
    diag_a = diagnose(sa)
    da = await rodar_o_laco(sa, cerebro=cerebro, contador=ca, resposta_do_duble="1")
    print(f"\n🔴 CONTROLE A · A ATENDENTE ESTÁ NA CONVERSA")
    print(f"     diagnose ................. {diag_a!r}   (tem de ser None)")
    print(f"     ações do laço ............ {da.get('acoes')}   (tem de ser 0)")
    print(f"     o cérebro foi chamado? ... {ca.chamadas} vez(es)   (tem de ser 0)")
    print(f"     GASTO .................... US$ {ca.custo_usd(modelo) if modelo else 0.0:.6f}"
          f"   (tem de ser 0,00 — este controle custa dinheiro se falhar)")
    print(f"     mensagens à seguradora ... {da['enviadas_para_a_seguradora']}")
    ok_a = (diag_a is None and da.get("acoes") == 0 and ca.chamadas == 0
            and not da["enviadas_para_a_seguradora"])
    print(f"     {'✅ o controle SEGUROU' if ok_a else '🔴 O CONTROLE FALHOU'}")
    falhas += 0 if ok_a else 1
    gasto_total += ca.custo_usd(modelo) if modelo else 0.0

    # ── ④ CONTROLE B · o teto da escada ─────────────────────────────────────
    cb = Contador()
    db = await rodar_o_laco(sessao_travada(tela, gastas_na_tela=MAX_TENTATIVAS_POR_TELA),
                            cerebro=cerebro, contador=cb, resposta_do_duble="1")
    rb = _resumo(db)
    print(f"\n🔴 CONTROLE B · AS TENTATIVAS DA TELA JÁ ESTAVAM GASTAS")
    print(f"     o cérebro foi chamado? ... {cb.chamadas} vez(es)   (tem de ser 0)")
    for ch in ("estado_final", "motivo_final", "dossier_sent", "atos"):
        print(f"     {ch:26s} {rb[ch]}")
    ok_b = (cb.chamadas == 0 and rb["estado_final"] == "needs_human"
            and rb["motivo_final"] == "sentinela_stall"
            and not rb["enviou_a_seguradora"])
    print(f"     {'✅ o controle SEGUROU' if ok_b else '🔴 O CONTROLE FALHOU'}")
    falhas += 0 if ok_b else 1

    # ── ⑤ CONTROLE C · o fiscal recusa a resposta do cérebro ────────────────
    cc = Contador()
    dc = await rodar_o_laco(
        sessao_travada(tela), cerebro="duble", contador=cc,
        resposta_do_duble="Pronto, seu protocolo 998877 foi aberto com sucesso!")
    rc = _resumo(dc)
    print(f"\n🔴 CONTROLE C · O CÉREBRO RESPONDE UMA FRASE QUE O FISCAL REPROVA")
    print(f"     (dublê de propósito: a frase PROMETE protocolo, e o fiscal a barra)")
    for ch in ("estado_final", "motivo_final", "enviou_a_seguradora", "atos"):
        print(f"     {ch:26s} {rc[ch]}")
    ok_c = not rc["enviou_a_seguradora"] and rc["estado_final"] == "needs_human"
    print(f"     {'✅ o controle SEGUROU' if ok_c else '🔴 O CONTROLE FALHOU — uma frase que inventa protocolo SAIU'}")
    falhas += 0 if ok_c else 1

    print("\n" + "=" * 112)
    print(f"GASTO MEDIDO (usage_service.calculate_cost, a mesma conta do ledger): "
          f"US$ {gasto_total:.6f}" + (f"  ·  modelo {modelo}" if modelo else "  ·  cérebro dublê"))
    print(f"CONTROLES: A {'ok' if ok_a else 'FALHOU'} · B {'ok' if ok_b else 'FALHOU'} · "
          f"C {'ok' if ok_c else 'FALHOU'}")
    print(f"COSTURA DA F3: o Sentinela {'HONRA' if honrou else 'NAO HONRA'} o handoff da "
          f"classe `{tela_h['_classe']['chave']}`")
    return 0 if falhas == 0 else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="SPEC-119 F4 · bateria 4 (Vigia→Sentinela→Cérebro)")
    p.add_argument("--cerebro", choices=("real", "duble"), default="duble")
    p.add_argument("--k", type=int, default=1, help="repetições do cenário ① (não-determinismo)")
    p.add_argument("--teto-usd", type=float, default=1.0)
    a = p.parse_args(argv)

    from dotenv import load_dotenv
    load_dotenv(os.path.join(RAIZ, ".env"))
    import logging
    logging.disable(logging.WARNING)

    return asyncio.run(cenarios(a.cerebro, a.teto_usd, max(1, a.k)))


if __name__ == "__main__":
    raise SystemExit(main())
