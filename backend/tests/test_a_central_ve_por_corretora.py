# -*- coding: utf-8 -*-
"""A CENTRAL VÊ POR CORRETORA — e os números de uma nunca entram na outra.

> **O TESTE DO PRODUTO:** *"Perdi alguma mensagem? E a corretora A está lenta
> por causa da corretora B?"* — as duas perguntas que a Central não respondia.

```
① duas corretoras, números DIFERENTES, conferidos contra uma contagem feita À MÃO
② duas integrações da MESMA corretora SOMAM — a fila dela é a soma das linhas dela
③ integração sem corretora conhecida vira LINHA PRÓPRIA, nunca some em silêncio
④ Redis fora → os campos de fila viram None + aviso, e o bloco NÃO quebra
⑤ o aviso ao dono da fila longa: desligado por padrão, UM por janela, sem Redis nenhum
```

🔴 **A LENTE DO DADO, dentro do próprio guarda.** Os `p95`/`mediana` não são
comparados com o que a função devolveu para si mesma: o teste recalcula a
mediana por um caminho INDEPENDENTE (ordenar a lista à mão e pegar o meio) e
compara número com número. Um agrupamento que fundisse as duas corretoras
passaria por uma conferência interna; não passa por esta.

⚠️ **Os dublês FILTRAM de verdade.** Um PostgREST de mentira que ignora `.eq()`
deixaria o guarda da corretora vizinha verde por permissão — e o bloco [0]
prova que este consegue separar antes de qualquer outra coisa ser medida.

⛔ Sem rede, sem banco, sem Redis, sem mensagem enviada. Zero PII: ids
sintéticos, nenhum nome de corretora ou pessoa real (CLAUDE.md §13.9).
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

# 🔴 O PostgREST de mentira que FILTRA de verdade, reusado (CLAUDE.md §5).
import test_a_atendente_fala_e_o_robo_cala as H  # noqa: E402

# Ids sintéticos. ⛔ Nenhum nome de corretora entra em código ou teste (§13.9).
CORRETORA_A = "corretora-de-teste-a"
CORRETORA_B = "corretora-de-teste-b"
INTEGRACAO_A1 = "integracao-a-1"
INTEGRACAO_A2 = "integracao-a-2"
INTEGRACAO_B1 = "integracao-b-1"
INTEGRACAO_ORFA = "integracao-sem-dono"

_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print("  OK  %s%s" % (o_que, ("  (%s)" % evidencia) if evidencia else ""))
    else:
        print("  X   %s%s" % (o_que, ("  (%s)" % evidencia) if evidencia else ""))
        _PROBLEMAS.append(o_que)


def par(acusou: bool, o_que: str, evidencia: str = "") -> None:
    checar(acusou, "CONTROLE — " + o_que, evidencia)


# ===========================================================================
# O MUNDO SINTÉTICO — duas corretoras, números diferentes de propósito
# ===========================================================================
#
# 📊 Os tempos são escolhidos para que a mediana e o p95 de A e de B sejam
# DIFERENTES entre si e diferentes da mistura das duas. Se fossem parecidos, um
# agrupamento quebrado ficaria verde por sorte.

TEMPOS_A = [1000, 1200, 1400, 1600, 90000]     # uma cauda longa só dela
TEMPOS_B = [4000, 4100, 4200]                  # devagar e parelho


def _agora_iso(segundos_atras: float = 60.0) -> str:
    return (datetime.now(timezone.utc)
            - timedelta(seconds=segundos_atras)).isoformat()


def _banco_das_duas() -> "H.BancoFalso":
    b = H.BancoFalso()
    b.semear("companies", [
        {"id": CORRETORA_A, "company_name": "Corretora de teste A"},
        {"id": CORRETORA_B, "company_name": "Corretora de teste B"},
    ])
    b.semear("integrations", [
        {"id": INTEGRACAO_A1, "company_id": CORRETORA_A},
        {"id": INTEGRACAO_A2, "company_id": CORRETORA_A},
        {"id": INTEGRACAO_B1, "company_id": CORRETORA_B},
    ])
    b.semear("conversations", [
        {"id": "conv-a-1", "company_id": CORRETORA_A, "last_message_at": _agora_iso()},
        {"id": "conv-b-1", "company_id": CORRETORA_B, "last_message_at": _agora_iso()},
        # ⚠️ Uma conversa VELHA da corretora A: fora da janela de 24 h. Ela existe
        #    para o filtro de tempo ter o que recusar.
        {"id": "conv-a-velha", "company_id": CORRETORA_A,
         "last_message_at": _agora_iso(3 * 86400)},
    ])
    linhas = []
    for ms in TEMPOS_A:
        linhas.append({"conversation_id": "conv-a-1", "role": "assistant",
                       "created_at": _agora_iso(),
                       "payload": {"origem": "agente", "direcao": "out",
                                   "turn": {"status": "complete", "total_ms": ms}}})
    for ms in TEMPOS_B:
        linhas.append({"conversation_id": "conv-b-1", "role": "assistant",
                       "created_at": _agora_iso(),
                       "payload": {"origem": "agente", "direcao": "out",
                                   "turn": {"status": "complete", "total_ms": ms}}})
    # ⚠️ Ruído de propósito: a mensagem do SEGURADO (role=user) e uma resposta
    #    sem relógio. Nenhuma das duas pode virar um turno medido.
    linhas.append({"conversation_id": "conv-a-1", "role": "user",
                   "created_at": _agora_iso(), "content": "oi",
                   "payload": {"turn": {"total_ms": 999999}}})
    linhas.append({"conversation_id": "conv-b-1", "role": "assistant",
                   "created_at": _agora_iso(),
                   "payload": {"origem": "agente", "direcao": "out"}})
    # ⚠️ E uma resposta VELHA, de 3 dias: fora da janela.
    linhas.append({"conversation_id": "conv-a-velha", "role": "assistant",
                   "created_at": _agora_iso(3 * 86400),
                   "payload": {"turn": {"status": "complete", "total_ms": 777777}}})
    b.semear("messages", linhas)
    return b


def _contadores(*, com_orfa: bool = True) -> dict:
    """Os HASHes `isolamento_escopo:{escopo}` como o Redis os devolve: TEXTO."""
    dados = {
        INTEGRACAO_A1: {"em_execucao": "2", "em_espera": "5", "expiradas": "0",
                        "timeouts": "1", "ultimo_motivo": "cota",
                        "ultimo_motivo_em": "2026-09-21T10:00:00"},
        INTEGRACAO_A2: {"em_execucao": "1", "em_espera": "3", "expiradas": "0",
                        "timeouts": "0", "ultimo_motivo": "turno",
                        "ultimo_motivo_em": "2026-09-21T09:00:00"},
        INTEGRACAO_B1: {"em_execucao": "1", "em_espera": "0", "expiradas": "2",
                        "timeouts": "0", "ultimo_motivo": "breaker",
                        "ultimo_motivo_em": "2026-09-21T10:30:00"},
    }
    if com_orfa:
        dados[INTEGRACAO_ORFA] = {"em_execucao": "1", "em_espera": "7",
                                  "expiradas": "3", "timeouts": "0",
                                  "ultimo_motivo": "cota",
                                  "ultimo_motivo_em": "2026-09-21T11:00:00"}
    return dados


def _bloco(*, contadores, banco=None) -> list:
    """Chama o MOTOR da Central — `montar_atendimento_por_corretora`, a função
    que a rota de verdade usa — com o mundo lido dos dublês."""
    import app.core.central_de_agentes as C
    import app.core.database as _database

    b = banco if banco is not None else _banco_das_duas()
    antes = _database.get_supabase_client
    _database.get_supabase_client = lambda: b
    try:
        bruto = C._ler_atendimento_sincrono()
    finally:
        _database.get_supabase_client = antes
    return C.montar_atendimento_por_corretora(
        bruto=bruto, contadores=contadores,
        breaker={"anthropic": "fechado", "openai": "aberto"}, cota=4)


def _por_empresa(linhas: list) -> dict:
    return {str(l.get("company_id") or "__sem__"): l for l in linhas}


# ===========================================================================
# [0] O DUBLÊ CONSEGUE SEPARAR — antes de medir qualquer coisa com ele
# ===========================================================================

def teste_o_duble_filtra_de_verdade():
    print("\n[0] O DUBLÊ — ele CONSEGUE separar as duas corretoras?")
    b = _banco_das_duas()
    so_a = b.table("conversations").select("id").eq("company_id", CORRETORA_A).execute().data
    so_b = b.table("conversations").select("id").eq("company_id", CORRETORA_B).execute().data
    par(len(so_a) == 2 and len(so_b) == 1 and so_a != so_b,
        "o PostgREST de mentira filtra `company_id` de verdade",
        "A=%d conversa(s) · B=%d conversa(s)" % (len(so_a), len(so_b)))
    corte = _agora_iso(86400)
    recentes = b.table("messages").select("*").gte("created_at", corte).execute().data
    par(len(recentes) < len(b.linhas("messages")),
        "e recusa o que está fora da janela de 24 h",
        "%d de %d linhas" % (len(recentes), len(b.linhas("messages"))))


# ===========================================================================
# ① ② ③ OS NÚMEROS, CONFERIDOS À MÃO
# ===========================================================================

def _mediana_a_mao(valores: list) -> int:
    """A LENTE DO DADO: o caminho independente. Lista ímpar → o do meio; par →
    a média dos dois do meio. ⛔ Não chama `percentil`."""
    v = sorted(valores)
    meio = len(v) // 2
    return v[meio] if len(v) % 2 else int(round((v[meio - 1] + v[meio]) / 2))


def teste_as_duas_corretoras_aparecem_com_numeros_proprios():
    print("\n[1] DUAS CORRETORAS — os números de A não são os de B")
    linhas = _bloco(contadores=_contadores())
    por = _por_empresa(linhas)

    checar(CORRETORA_A in por and CORRETORA_B in por,
           "as duas corretoras aparecem no bloco",
           ", ".join(sorted(por)))

    a, b = por[CORRETORA_A], por[CORRETORA_B]
    checar(a["turnos_24h"] == len(TEMPOS_A) and b["turnos_24h"] == len(TEMPOS_B),
           "a contagem de turnos bate com o que foi semeado — e o ruído "
           "(mensagem do segurado, resposta sem relógio, resposta de 3 dias) "
           "ficou de fora",
           "A=%s (esperado %d) · B=%s (esperado %d)"
           % (a["turnos_24h"], len(TEMPOS_A), b["turnos_24h"], len(TEMPOS_B)))

    # 🔬 A LENTE: mediana recalculada por caminho independente.
    checar(a["mediana_ms_24h"] == _mediana_a_mao(TEMPOS_A),
           "a mediana de A bate com a conta feita à mão",
           "%s vs %s" % (a["mediana_ms_24h"], _mediana_a_mao(TEMPOS_A)))
    checar(b["mediana_ms_24h"] == _mediana_a_mao(TEMPOS_B),
           "a mediana de B bate com a conta feita à mão",
           "%s vs %s" % (b["mediana_ms_24h"], _mediana_a_mao(TEMPOS_B)))

    # 🔴 O CORAÇÃO DO GATE: a mediana da MISTURA não é a de nenhuma das duas.
    misturada = _mediana_a_mao(TEMPOS_A + TEMPOS_B)
    par(misturada != a["mediana_ms_24h"] and misturada != b["mediana_ms_24h"],
        "e a mediana das duas MISTURADAS seria outro número",
        "misturada=%d · A=%s · B=%s"
        % (misturada, a["mediana_ms_24h"], b["mediana_ms_24h"]))

    checar(a["p95_ms_24h"] > b["p95_ms_24h"],
           "o p95 de A é maior — a cauda longa é DELA, e não vaza para B",
           "A=%s · B=%s" % (a["p95_ms_24h"], b["p95_ms_24h"]))
    checar(a["p95_ms_24h"] <= max(TEMPOS_A) and b["p95_ms_24h"] <= max(TEMPOS_B),
           "e nenhum p95 ultrapassa o pior tempo da própria corretora",
           "A≤%d · B≤%d" % (max(TEMPOS_A), max(TEMPOS_B)))


def teste_duas_integracoes_da_mesma_corretora_somam():
    print("\n[2] SOMA — duas integrações da MESMA corretora são UMA fila")
    por = _por_empresa(_bloco(contadores=_contadores()))
    a = por[CORRETORA_A]
    checar(a["em_execucao"] == 2 + 1 and a["em_espera"] == 5 + 3,
           "a fila de A é a soma das duas integrações dela",
           "em_execucao=%s (2+1) · em_espera=%s (5+3)"
           % (a["em_execucao"], a["em_espera"]))
    checar(a["integracoes"] == 2,
           "e a linha diz quantas integrações somou", repr(a["integracoes"]))
    checar(a["ultimo_motivo_de_espera"] == "cota",
           "o motivo é o MAIS RECENTE das duas (10:00 vence 09:00), não o último lido",
           repr(a["ultimo_motivo_de_espera"]))
    checar(a["timeouts_acumulados"] == 1 and a["expiradas_acumuladas"] == 0,
           "os acumulados também somam", "timeouts=%s" % a["timeouts_acumulados"])

    b = por[CORRETORA_B]
    par(b["em_espera"] == 0 and b["expiradas_acumuladas"] == 2,
        "e B, com UMA integração, não herda nada de A",
        "em_espera=%s · expiradas=%s" % (b["em_espera"], b["expiradas_acumuladas"]))


def teste_a_integracao_sem_dono_nao_some():
    print("\n[3] ÓRFÃ — integração sem corretora conhecida vira linha própria")
    linhas = _bloco(contadores=_contadores(com_orfa=True))
    orfas = [l for l in linhas if l.get("sem_corretora")]
    checar(len(orfas) == 1 and orfas[0]["company_id"] is None,
           "a integração sem dono aparece marcada, e não somada a ninguém",
           "%d linha(s) órfã(s)" % len(orfas))
    checar(orfas[0]["em_espera"] == 7,
           "com os números dela, à vista", repr(orfas[0]["em_espera"]))

    sem = _bloco(contadores=_contadores(com_orfa=False))
    par(not [l for l in sem if l.get("sem_corretora")],
        "sem órfã no Redis, não nasce linha órfã do nada",
        "o guarda [3] consegue ficar dos dois jeitos")

    a_com = _por_empresa(linhas)[CORRETORA_A]
    a_sem = _por_empresa(sem)[CORRETORA_A]
    par(a_com["em_espera"] == a_sem["em_espera"],
        "e a órfã NÃO entrou na conta de A",
        "%s nos dois casos" % a_com["em_espera"])


def teste_o_nome_dos_acumulados_nao_mente():
    print("\n[3b] O NOME — `acumulado` não se disfarça de janela de 24 h")
    linha = _por_empresa(_bloco(contadores=_contadores()))[CORRETORA_A]
    checar("expiradas_24h" not in linha and "timeouts_24h" not in linha,
           "não existe `expiradas_24h`: o contador NÃO é janela deslizante "
           "(HINCRBY com TTL renovado a cada escrita)",
           ", ".join(k for k in linha if "expirad" in k or "timeout" in k))
    checar(isinstance(linha.get("janela"), dict)
           and "contadores" in linha["janela"] and "tempos" in linha["janela"],
           "e a linha CARREGA a explicação das duas janelas, escrita",
           str(linha["janela"])[:70] + "…")
    checar(str(linha["janela"]["contadores"]).find("24 horas") >= 0,
           "que diz em português quando o acumulado volta a zero")


def teste_redis_fora_nao_quebra_o_bloco():
    print("\n[4] REDIS FORA — os campos de fila viram None, e a rota responde")
    linhas = _bloco(contadores=None)
    por = _por_empresa(linhas)
    checar(CORRETORA_A in por and CORRETORA_B in por,
           "as corretoras continuam aparecendo (os tempos vêm do banco)",
           "%d linha(s)" % len(linhas))
    a = por[CORRETORA_A]
    checar(a["em_execucao"] is None and a["em_espera"] is None
           and a["expiradas_acumuladas"] is None,
           "e os campos de fila dizem NÃO SEI — nunca zero",
           "em_execucao=%r" % a["em_execucao"])
    checar(bool(a["aviso"]),
           "com um aviso em português ao lado", a["aviso"][:52] + "…")
    checar(a["mediana_ms_24h"] == _mediana_a_mao(TEMPOS_A),
           "os tempos medidos continuam valendo", repr(a["mediana_ms_24h"]))
    par(_por_empresa(_bloco(contadores=_contadores()))[CORRETORA_A]["aviso"] == "",
        "com Redis de pé, o aviso NÃO aparece",
        "o guarda [4] consegue ficar dos dois jeitos")


def teste_a_rota_continua_cega_para_conteudo():
    print("\n[2b] PRIVACIDADE — nada de conversa atravessa")
    linhas = _bloco(contadores=_contadores())
    texto = str(linhas)
    checar("oi" not in [str(l.get("nome")) for l in linhas]
           and "content" not in texto and "user_phone" not in texto,
           "o bloco não carrega conteúdo, telefone nem texto de mensagem",
           "%d chaves por linha" % len(linhas[0]))
    checar(all(set(l) == set(linhas[0]) for l in linhas),
           "e todas as linhas têm exatamente as mesmas chaves",
           ", ".join(sorted(linhas[0])))


# ===========================================================================
# ⑤ O AVISO AO DONO — pronto e DESLIGADO (proposta §8.3)
# ===========================================================================

class _RedisDeMentira:
    """Só o que o aviso usa: `set(..., nx=True, ex=…)` e `get`."""

    def __init__(self):
        self.dados: dict = {}
        self.sets: list = []

    async def set(self, chave, valor, nx=False, ex=None):
        self.sets.append((chave, nx, ex))
        if nx and chave in self.dados:
            return None
        self.dados[chave] = valor
        return True

    async def get(self, chave):
        return self.dados.get(chave)


class _RedisFora:
    async def set(self, *_a, **_k):
        raise RuntimeError("redis fora")

    async def get(self, *_a, **_k):
        raise RuntimeError("redis fora")


def _avisar(*, ligado: bool, espera_s: float, redis, vezes: int = 1,
            company_id: str = CORRETORA_A) -> list:
    """Chama `avisar_dono_se_fila_longa` de verdade, com o envio dublado."""
    import app.services.aviso_de_fila_longa as A

    enviados: list = []

    async def _envio_falso(_db, **k):
        enviados.append({"company_id": k.get("company_id"), "tipo": k.get("tipo"),
                         "texto": k.get("texto")})
        return {"enviado": True, "calado": False}

    antes_env = A._enviar_ao_grupo
    antes_redis = A._redis
    antes_flag = os.environ.get("ISOLAMENTO_AVISO_AO_DONO")
    A._enviar_ao_grupo = _envio_falso

    async def _da_vez():
        return redis

    A._redis = _da_vez
    if ligado:
        os.environ["ISOLAMENTO_AVISO_AO_DONO"] = "1"
    else:
        os.environ.pop("ISOLAMENTO_AVISO_AO_DONO", None)
    try:
        for _ in range(vezes):
            asyncio.run(A.avisar_dono_se_fila_longa(
                None, company_id=company_id, em_espera=9,
                esperando_ha_s=espera_s))
    finally:
        A._enviar_ao_grupo = antes_env
        A._redis = antes_redis
        if antes_flag is None:
            os.environ.pop("ISOLAMENTO_AVISO_AO_DONO", None)
        else:
            os.environ["ISOLAMENTO_AVISO_AO_DONO"] = antes_flag
    return enviados


def teste_o_aviso_ao_dono_nasce_desligado():
    print("\n[5] AVISO AO DONO — fail-closed: sem a chave, ninguém é avisado")
    saiu = _avisar(ligado=False, espera_s=600, redis=_RedisDeMentira())
    checar(not saiu, "flag ausente → ZERO envios", "%d envio(s)" % len(saiu))

    par(len(_avisar(ligado=True, espera_s=600, redis=_RedisDeMentira())) == 1,
        "com a flag ligada, o MESMO cenário avisa UMA vez",
        "é a flag que segura — e ela não está ligada em produção")


def teste_o_aviso_sai_uma_vez_por_janela():
    print("\n[5b] JANELA — dez varreduras, um aviso")
    redis = _RedisDeMentira()
    saiu = _avisar(ligado=True, espera_s=600, redis=redis, vezes=10)
    checar(len(saiu) == 1,
           "10 varreduras na mesma janela → UM aviso",
           "%d envio(s) em %d tentativas de trava" % (len(saiu), len(redis.sets)))
    checar(all(nx and ex for _c, nx, ex in redis.sets),
           "e a trava é `SET NX EX` — uma réplica só avisa, e ela expira sozinha",
           repr(redis.sets[0]))
    checar(saiu and CORRETORA_A not in str(saiu[0]["texto"]),
           "o texto não carrega id nem nome fixo de corretora (§13.9)",
           repr(saiu[0]["texto"])[:70] + "…")

    par(len(_avisar(ligado=True, espera_s=1, redis=_RedisDeMentira())) == 0,
        "abaixo do limiar de espera, nem o primeiro aviso sai",
        "é a espera que dispara, não a varredura")


def teste_sem_redis_o_aviso_nao_sai():
    print("\n[5c] SEM REDIS — é envio, logo é fail-closed")
    saiu = _avisar(ligado=True, espera_s=600, redis=_RedisFora())
    checar(not saiu,
           "Redis fora → ZERO envios (sem trava não há 'um por janela')",
           "%d envio(s)" % len(saiu))


def main() -> int:
    print("=" * 72)
    print("A CENTRAL VÊ POR CORRETORA")
    print("=" * 72)
    teste_o_duble_filtra_de_verdade()
    teste_as_duas_corretoras_aparecem_com_numeros_proprios()
    teste_duas_integracoes_da_mesma_corretora_somam()
    teste_a_rota_continua_cega_para_conteudo()
    teste_a_integracao_sem_dono_nao_some()
    teste_o_nome_dos_acumulados_nao_mente()
    teste_redis_fora_nao_quebra_o_bloco()
    teste_o_aviso_ao_dono_nasce_desligado()
    teste_o_aviso_sai_uma_vez_por_janela()
    teste_sem_redis_o_aviso_nao_sai()

    print("\n" + "=" * 72)
    if _PROBLEMAS:
        print("%d PROBLEMA(S):" % len(_PROBLEMAS))
        for p in _PROBLEMAS:
            print("  - %s" % p)
        return 1
    print("TUDO VERDE — cada corretora tem os SEUS números, e ninguém some.")
    return 0


def test_a_central_ve_por_corretora():
    """A porta do pytest — o mesmo roteiro, uma asserção só."""
    assert main() == 0, _PROBLEMAS


if __name__ == "__main__":
    sys.exit(main())
