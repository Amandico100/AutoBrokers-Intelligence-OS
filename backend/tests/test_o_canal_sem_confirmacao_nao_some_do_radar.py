"""O canal que ninguém conseguiu medir não some do radar — nem vira queda falsa.

P-38. `unknown` estava fora das duas listas, e por isso não gerava nada.
----------------------------------------------------------------------
O heartbeat da SPEC-063 Bloco V demove para `unknown` o canal que afirmava
`connected`/`connecting` e que ninguém confirma há mais de 15 minutos. A palavra
está CERTA e é deliberada — `channel_state.decidir_heartbeat`, regra 3::

    Vira `unknown`, não `disconnected` — não confirmamos queda nenhuma,
    só perdemos o direito de dizer "Conectado".

E é por isso que `unknown` não pode entrar em `ESTADOS_RUINS`: aquela lista é de
queda MEDIDA, e anunciar queda que ninguém mediu é o mesmo pecado do outro lado.

Só que ficar de fora das duas listas significava **silêncio**. O detector de
conexão do briefing (`conexoes.canais_com_problema`) exigia estar em
`ESTADOS_RUINS`. Resultado: o canal demovido parava de mentir na tela e não
aparecia em lugar nenhum como problema. **Ele saía do radar exatamente quando
passava a merecer atenção.**

O que a demoção realmente significa
------------------------------------
📊 Medido em 03/08/2026 no banco de produção (``SELECT id, purpose, is_active,
channel_status, last_seen_at, now() - last_seen_at FROM integrations``)::

    observer   6c9c55e2…  connected    último sinal 29/07 18:49   4 dias
    observer   04b5cdbc…  connected    último sinal 29/07 18:48   4 dias
    observer   3aa75902…  connecting   último sinal 28/07 13:39   5 dias

Três canais ATIVOS afirmando um estado que ninguém confirmava havia quatro e
cinco dias. Com o heartbeat, os três viram `unknown` — e antes deste conserto,
os três sumiriam do briefing na mesma hora.

A saída: sinal PRÓPRIO, mais fraco
-----------------------------------
Mesmo `signal_type` (esconder num tipo novo tiraria de quem já olha
`connection_health`), mesma chave de deduplicação, e força menor em tudo:
severidade, confiança, urgência. E o texto diz a verdade — *"não conseguimos
confirmar"*, nunca *"está indisponível"*.

O `trust_tier` faz o trabalho pesado sozinho: `TIER_ANALISE` está fora de
`TIERS_QUE_SUSTENTAM_ALERTA_CRITICO`, então a própria SPEC-059 **recusa** um
`critical` vindo daqui. A fraqueza do sinal deixa de depender de alguém lembrar
dela na próxima calibragem.

Por que a distinção não é preciosismo
--------------------------------------
Se os dois casos dissessem "a conexão está indisponível", o corretor aprenderia
a desconfiar dos dois. No dia em que a queda for real, ele já terá aprendido a
não olhar — e alarme falso é o caminho mais curto para o corretor desligar os
avisos.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
FALHAS: list[str] = []


def _pacote(nome: str, *partes: str, executar_init: bool = False) -> None:
    if nome in sys.modules:
        return
    caminho = os.path.join(RAIZ, *partes)
    m = types.ModuleType(nome)
    m.__path__ = [caminho]
    m.__package__ = nome
    sys.modules[nome] = m
    if executar_init:
        init = os.path.join(caminho, "__init__.py")
        spec = importlib.util.spec_from_file_location(
            nome, init, submodule_search_locations=[caminho])
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[nome] = modulo
        spec.loader.exec_module(modulo)


for _nome, _partes, _init in (
    ("app", ("app",), False),
    ("app.services", ("app", "services"), False),
    ("app.services.intelligence", ("app", "services", "intelligence"), False),
    ("app.services.intelligence.detectors",
     ("app", "services", "intelligence", "detectors"), True),
):
    _pacote(_nome, *_partes, executar_init=_init)


def carregar(nome: str):
    if nome in sys.modules and hasattr(sys.modules[nome], "__file__"):
        return sys.modules[nome]
    caminho = os.path.join(RAIZ, *nome.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


CX = carregar("app.services.intelligence.detectors.conexoes")
SCHEMAS = carregar("app.services.intelligence.schemas")
DET = sys.modules["app.services.intelligence.detectors"]

AGORA = datetime(2026, 8, 3, 20, 25, tzinfo=timezone.utc)
EMPRESA = "11111111-1111-1111-1111-111111111111"


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# --------------------------------------------------------------------------- #
# Banco de mentira, com a gramática do cliente Supabase síncrono
# --------------------------------------------------------------------------- #

class _Resposta:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Consulta:
    def __init__(self, linhas):
        self._linhas = linhas

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _Resposta(self._linhas, count=len(self._linhas))


class _Banco:
    def __init__(self, integracoes, rotinas=0, auxiliares=0):
        self._t = {
            "tenant_connections": [],
            "integrations": integracoes,
            "routines": [{"id": f"r{i}"} for i in range(rotinas)],
            "tenant_auxiliaries": [{"id": f"a{i}"} for i in range(auxiliares)],
        }

    def table(self, nome):
        return _Consulta(self._t.get(nome, []))


def _sinais(integracoes, rotinas=0, auxiliares=0):
    ctx = DET.ContextoDeDeteccao(
        company_id=EMPRESA, db=_Banco(integracoes, rotinas, auxiliares),
        agora=AGORA, rule_key="conexoes.conexao_degradada", rule_version="1.0.0")
    return CX.conexao_degradada(ctx)


# Os três canais medidos em 03/08/2026, depois de o heartbeat os demover.
DEMOVIDOS = [
    {"id": "6c9c55e2", "provider": "evolution-go", "purpose": "observer",
     "is_active": True, "channel_status": "unknown"},
    {"id": "04b5cdbc", "provider": "evolution-go", "purpose": "observer",
     "is_active": True, "channel_status": "unknown"},
]
CAIDO = {"id": "viva", "provider": "evolution-go", "purpose": "attendance",
         "is_active": True, "channel_status": "close"}
APOSENTADO = {"id": "velha", "provider": "evolution", "purpose": "attendance",
              "is_active": False, "channel_status": "unknown"}
CONECTANDO = {"id": "transitorio", "provider": "evolution-go", "purpose": "observer",
              "is_active": True, "channel_status": "connecting"}


# --------------------------------------------------------------------------- #
# Casos
# --------------------------------------------------------------------------- #

def teste_unknown_deixa_de_ser_silencio():
    print("\n[1] O canal demovido volta ao radar")
    achados = CX.canais_com_problema(DEMOVIDOS + [CAIDO, APOSENTADO, CONECTANDO])
    por_id = {a["id"]: a for a in achados}

    checar(set(por_id) == {"6c9c55e2", "04b5cdbc", "viva"},
           "os dois demovidos E o caido sao detectados",
           f"detectados: {sorted(por_id)}")
    checar("velha" not in por_id,
           "e canal DESLIGADO com unknown continua fora",
           "canal aposentado e decisao da corretora, nao defeito — e a regra "
           "de 'ligado E em estado ruim' nao pode ter afrouxado por tabela")
    checar("transitorio" not in por_id,
           "e 'connecting' continua sendo transicao, nao problema")


def teste_unknown_nao_e_tratado_como_queda():
    print("\n[2] Mas ele NAO e uma queda — sao classes diferentes")
    por_id = {a["id"]: a for a in CX.canais_com_problema(DEMOVIDOS + [CAIDO])}
    checar(por_id["viva"]["classe"] == CX.CLASSE_QUEDA,
           "o caido e classificado como queda MEDIDA",
           str(por_id["viva"]))
    checar(por_id["6c9c55e2"]["classe"] == CX.CLASSE_SEM_CONFIRMACAO,
           "e o demovido, como AUSENCIA DE CONFIRMACAO",
           str(por_id["6c9c55e2"]))

    checar("unknown" not in CX.ESTADOS_RUINS,
           "unknown NAO entrou em ESTADOS_RUINS",
           "aquela lista e de queda medida; nao medimos queda nenhuma aqui")
    checar("unknown" in CX.ESTADOS_SEM_CONFIRMACAO,
           "ele tem lista propria")


def teste_o_texto_nao_afirma_o_que_nao_foi_medido():
    print("\n[3] A frase diz o que e verdade, e nada alem")
    dependentes = {"rotinas": 2, "auxiliares": 1}
    queda = CX.descrever_impacto("evolution-go (attendance)", dependentes)
    duvida = CX.descrever_sem_confirmacao("evolution-go (observer)", dependentes)

    checar("está indisponível" in queda, "a queda medida diz 'esta indisponivel'", queda)
    checar("está indisponível" not in duvida,
           "e a ausencia de confirmacao NAO diz isso",
           f"{duvida!r} — se as duas dissessem o mesmo, o corretor aprenderia "
           "a desconfiar das duas, e no dia da queda real ja nao olharia")
    checar("confirmar" in duvida, "ela diz que nao conseguimos CONFIRMAR", duvida)
    checar("pode estar" in duvida, "e trata a queda como possibilidade, nao fato", duvida)
    checar(duvida != queda, "as duas frases sao mesmo diferentes")

    # Sem dependentes, nenhuma das duas inventa consequência.
    sozinha = CX.descrever_sem_confirmacao("canal", {"rotinas": 0, "auxiliares": 0})
    checar("dependem" not in sozinha,
           "sem dependentes, nao inventa consequencia", sozinha)
    checar("Rotina" in duvida and "Auxiliar" in duvida,
           "com dependentes, diz quem depende", duvida)


def teste_o_sinal_e_mais_fraco_em_tudo_que_importa():
    print("\n[4] O sinal da duvida nao compete de igual para igual")
    fraco = _sinais([DEMOVIDOS[0]], rotinas=2, auxiliares=1)
    forte = _sinais([CAIDO], rotinas=2, auxiliares=1)
    checar(len(fraco) == 1 and len(forte) == 1,
           "cada canal gera exatamente um sinal", f"{len(fraco)} / {len(forte)}")
    if not (fraco and forte):
        return
    f, F = fraco[0], forte[0]

    checar(f.severity == "medium" and F.severity == "critical",
           "severidade menor com os MESMOS dependentes",
           f"duvida={f.severity} queda={F.severity}")
    checar(f.confidence < F.confidence,
           "confianca menor — o que sabemos e que NAO sabemos",
           f"{f.confidence} vs {F.confidence}")
    checar(f.urgency_score < F.urgency_score,
           "urgencia menor", f"{f.urgency_score} vs {F.urgency_score}")
    checar(f.impact_score < F.impact_score,
           "impacto menor", f"{f.impact_score} vs {F.impact_score}")
    checar(f.signal_type == F.signal_type == "connection_health",
           "e o MESMO tipo de sinal",
           "tipo novo o esconderia de quem ja olha connection_health")

    checar(f.metadata.get("confirmado") is False,
           "o metadado diz que nao foi confirmado", str(f.metadata))
    checar(F.metadata.get("confirmado") is True,
           "e a queda medida diz que foi", str(F.metadata))


def teste_a_spec_recusa_critico_para_o_que_nao_foi_medido():
    print("\n[5] A fraqueza nao depende de alguem lembrar dela")
    fraco = _sinais([DEMOVIDOS[0]], rotinas=2, auxiliares=1)[0]
    checar(fraco.trust_tier == SCHEMAS.TIER_ANALISE,
           "o sinal da duvida nasce em TIER_ANALISE", str(fraco.trust_tier))
    checar(SCHEMAS.TIER_ANALISE not in SCHEMAS.TIERS_QUE_SUSTENTAM_ALERTA_CRITICO,
           "e TIER_ANALISE esta FORA dos tiers que sustentam alerta critico",
           "e isto que faz a propria SPEC-059 recusar um 'critical' daqui")

    # A prova de que a trava morde: forçar `critical` neste tier é INVÁLIDO.
    fraco.severity = "critical"
    ok, motivo = fraco.valido()
    checar(not ok,
           "forcar 'critical' num sinal nao medido e RECUSADO pelo schema",
           f"valido={ok} motivo={motivo!r}")

    # E o sinal legítimo, como nasce, é válido.
    for s in _sinais(DEMOVIDOS + [CAIDO], rotinas=1, auxiliares=0):
        ok, motivo = s.valido()
        checar(ok, f"o sinal de {s.metadata.get('conexao')} e valido como nasce", motivo)


def teste_o_guarda_tem_como_falhar():
    print("\n[6] CONTROLE — a regra de ANTES reprova")
    # A verificação de antes: só `ESTADOS_RUINS` contava.
    ESTADOS_RUINS_ANTES = ("expired", "degraded", "error", "disconnected",
                           "revoked", "failed", "close", "closed")

    def detectava_antes(integracao) -> bool:
        if not bool(integracao.get("is_active")):
            return False
        estado = str(integracao.get("channel_status") or "").lower()
        if estado in CX.ESTADOS_TRANSITORIOS:
            return False
        return estado in ESTADOS_RUINS_ANTES

    checar(detectava_antes(CAIDO),
           "a regra de ANTES e mesmo a regra — ela pega o canal caido",
           "se nem isso ela pegasse, o controle nao provaria nada")
    checar(not detectava_antes(DEMOVIDOS[0]),
           "e ela NAO pega o canal demovido — era o silencio de P-38",
           "se este caso ficar vermelho, o caso [1] passaria com ou sem o "
           "conserto e nao guarda nada (CLAUDE.md §9.3)")

    hoje = {a["id"] for a in CX.canais_com_problema([DEMOVIDOS[0], CAIDO])}
    checar(hoje == {"6c9c55e2", "viva"},
           "e a regra de hoje pega os dois — os lados conseguem ser diferentes",
           f"hoje={sorted(hoje)}")


def main() -> int:
    print("=" * 74)
    print("O CANAL SEM CONFIRMACAO NAO SOME DO RADAR — P-38")
    print("=" * 74)

    for teste in (teste_unknown_deixa_de_ser_silencio,
                  teste_unknown_nao_e_tratado_como_queda,
                  teste_o_texto_nao_afirma_o_que_nao_foi_medido,
                  teste_o_sinal_e_mais_fraco_em_tudo_que_importa,
                  teste_a_spec_recusa_critico_para_o_que_nao_foi_medido,
                  teste_o_guarda_tem_como_falhar):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("NEM SILENCIO, NEM QUEDA INVENTADA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
