# -*- coding: utf-8 -*-
"""🔴 O TESTE DO FIO — SPEC-EXTRA-001.10, protocolo AAA v13 §5 ②.

O que ele faz, e por que ele é a primeira entrega
=================================================
Ele atravessa o fio INTEIRO — do nome da seguradora ao desfecho que o portal
decidiu — com o **motor real**: `abrir_atendimento_api`, a `SessaoVidros` de
verdade (não uma `SessaoFalsa`), o `PortalActionGuard` de verdade com
checkpoint em memória, `vidros_estado` e `vidros_questionario`.

**O único dublê é a BORDA**: uma `page` cujo `evaluate` devolve o corpo que o
portal respondeu de verdade, lido do HAR em tempo de execução por
`trafego.importar_har` — e que REGISTRA cada chamada que o motor faz.

A pergunta que este arquivo responde não é "o código está lá?". É:

    quais escritas SAÍRAM, nesta ordem, com que corpo — e quais NÃO saíram?

Três replays, três desfechos opostos, mesma seguradora nos três primeiros:

    G1   lataria (categoria L)      → loja direta, sem questionário nenhum
    G1b  para-brisa (categoria V)   → loja direta, com reparo aceito
    G1c  vidro de porta (cat. V)    → AGENDA com 1 loja

🔴 G6 vive aqui também, e é o par que prova o ELO: invertendo **só** a resposta
de `opcoes-disponiveis` no dublê da lataria, o motor passa a devolver `agenda`.
Se houvesse um `if categoria == "L"` escondido, o desfecho não mudaria.

⛔ PII: nenhum valor pessoal entra em código, asserção ou saída. Ver
`_replay_vidros.py`. Sem os HAR (intake, fora do Git) o arquivo dá SKIP.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import _replay_vidros as RV                              # noqa: E402
from portal_worker import guardrails as G                # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF  # noqa: E402
from portal_worker.journeys import vidros_estado as ST   # noqa: E402

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:300] if extra else ""))


class RuntimeDeReplay:
    """O que o worker injeta em `params["_runtime"]`: guard + checkpoint."""

    def __init__(self, *, liberado=True):
        self.gravacoes: list = []
        self.guard = G.PortalActionGuard(material_liberado=liberado,
                                         _checkpoint=self.checkpoint)

    async def checkpoint(self, patch):
        self.gravacoes.append(patch)


def rodar(nome, *, extra=None, liberado=True):
    """Replay de um HAR com o MOTOR real. Devolve (resultado, evidence, page)."""
    chamadas = RV.carregar(nome)
    page = RV.PaginaDeReplay(chamadas)
    params = RV.params_do_har(chamadas, extra=extra)
    params["_runtime"] = RuntimeDeReplay(liberado=liberado)
    evidence: dict = {}
    resultado = asyncio.run(AF.abrir_atendimento_api(page, params, evidence))
    return resultado, evidence, page, chamadas


# ==========================================================================
try:
    RV.carregar("LAT")
except RV.HarAusente as e:
    print("\n[SKIP] " + str(e))
    print("\nO teste do fio precisa do acervo de HAR (docs/intake/, fora do Git).")
    sys.exit(0)

# ==========================================================================
print("\n[G1] LATARIA — as 5 escritas contratadas, na ordem, e as 2 fora NAO saem")
# ==========================================================================
r1, ev1, p1, har1 = rodar("LAT")

CONTRATADAS = [
    ("POST", "/atendimentos"),
    ("PUT", "/atendimentos/corretores"),
    ("POST", "/solicitantes"),
    ("PATCH", "/atendimentos"),
    ("POST", "/atendimentos/emitir-atendimento-formalizado/{codigo}"),
]
emitidas = [RV._chave(m, c) for m, c in p1.escritas()]
check("G1: as 5 escritas saíram exatamente nesta ordem",
      emitidas == [RV._chave(m, c) for m, c in CONTRATADAS], emitidas)
check("G1: `vistorias-previas/processar` NAO saiu",
      p1.quantas("POST", "/atendimentos/{codigo}/vistorias-previas/processar") == 0)
check("G1: `corretores-reclamacoes` NAO saiu",
      p1.quantas("POST", "/corretores-reclamacoes") == 0)
# 📊 Na captura de lataria não há UMA chamada a /questionarios — o que confirma
# que o PATCH é a fronteira material dessa categoria.
check("G1: ZERO chamadas a /questionarios*",
      not [c for m, c in p1.emitidas() if c.startswith("/questionarios")],
      [c for m, c in p1.emitidas() if c.startswith("/questionarios")])
check("G1: nenhuma chamada ficou sem resposta no acervo", not p1.sem_resposta,
      p1.sem_resposta)

# ---- o corpo do PATCH, conferido contra o HAR por um caminho INDEPENDENTE --
patch_do_har = RV.primeira(har1, "PATCH", "/atendimentos", requisicao=True)
patch_do_motor = p1.corpo_de("PATCH", "/atendimentos") or {}
check("G1: o PATCH tem exatamente 8 chaves", len(patch_do_motor) == 8,
      sorted(patch_do_motor))
check("G1: e são as MESMAS chaves, na MESMA ordem que o portal recebeu",
      list(patch_do_motor.keys()) == list(patch_do_har.keys()),
      (list(patch_do_motor.keys()), list(patch_do_har.keys())))
check("G1: `CodigoZona` viaja como null (presente, e None)",
      "CodigoZona" in patch_do_motor and patch_do_motor["CodigoZona"] is None)
check("G1: `ItemRemovido`/`EventoComposto`/`PolimentoFarol` NAO estao no corpo",
      not ({"ItemRemovido", "EventoComposto", "PolimentoFarol"} & set(patch_do_motor)))
for campo in ("CodigoItemCoberto", "CodigoCidade", "CodigoObjetoCausa",
              "PerimetroDano"):
    check(f"G1: {campo} igual ao medido no HAR",
          patch_do_motor.get(campo) == patch_do_har.get(campo),
          (campo, patch_do_motor.get(campo)))
check("G1: `ServicosMartelinhoLataria` com os 2 servicos medidos",
      patch_do_motor.get("ServicosMartelinhoLataria")
      == patch_do_har.get("ServicosMartelinhoLataria"),
      patch_do_motor.get("ServicosMartelinhoLataria"))
check("G1: a categoria da peca e L", ev1.get("peca", {}).get("categoria") == "L")

# 🔴 `DataSinistro` — o portal recebe um INSTANTE, e o motor manda o MESMO que
# o portal recebeu. 📊 `AAAA-MM-DD` tem zero exercícios nas 4 capturas.
abertura_do_har = RV.primeira(har1, "POST", "/atendimentos", requisicao=True) or {}
abertura_do_motor = p1.corpo_de("POST", "/atendimentos") or {}
check("G1: `DataSinistro` sai no formato MEDIDO (instante ISO com Z)",
      abertura_do_motor.get("DataSinistro") == abertura_do_har.get("DataSinistro"),
      (abertura_do_motor.get("DataSinistro"), abertura_do_har.get("DataSinistro")))
check("G1: e o offset e DERIVADO do fuso, nao escrito "
      "(2018 tinha horario de verao e da outro instante)",
      AF.API.instante_do_sinistro("2018-01-15").endswith("T02:00:00.000Z")
      and AF.API.instante_do_sinistro("2026-01-15").endswith("T03:00:00.000Z"),
      (AF.API.instante_do_sinistro("2018-01-15"),
       AF.API.instante_do_sinistro("2026-01-15")))

# ---- o desfecho --------------------------------------------------------
d1 = ev1.get("desfecho") or {}
check("G1: o desfecho e loja_direta", d1.get("tipo") == ST.DESFECHO_LOJA_DIRETA,
      d1.get("tipo"))
check("G1: e ele traz a loja que o portal atribuiu",
      bool((d1.get("loja") or {}).get("nome")))
check("G1: NAO oferece lista de lojas (o portal nao deu escolha)",
      d1.get("lojas") == [])
check("G1: NAO pede escolha do segurado (nem loja, nem domicilio)",
      getattr(r1, "captured", {}).get("customer_choice_needed") is False,
      getattr(r1, "captured", {}))
check("G1: o resultado e `done`", getattr(r1, "status", "") == "done",
      getattr(r1, "message", r1))
check("G1: e o comprovante foi emitido", d1.get("comprovante_emitido") is True)
# 📊 O roteador é o que explica o desfecho, e ele vai para a evidência inteiro.
check("G1: o roteador ficou registrado para o dossie",
      len(d1.get("roteador") or {}) >= 10, len(d1.get("roteador") or {}))

# ==========================================================================
print("\n[G6] o ELO: invertendo SO o roteador, a MESMA lataria vira agenda")
# ==========================================================================
# 🔴 Este é o par que prova que o desfecho vem do PORTAL. Nada muda no params,
# na peça ou na categoria: muda a resposta de `opcoes-disponiveis`. Se houvesse
# um `if categoria == "L"` escondido, o desfecho continuaria `loja_direta`.
LOJA_INVENTADA = {
    "CodigoCliente": 999999, "CodigoProduto": 111111, "NomeLoja": "LOJA DE TESTE",
    "Abreviacao": "XX00", "Cidade": "CIDADE DE TESTE", "Bairro": "BAIRRO",
    "SiglaUF": "SC", "Endereco": "RUA DE TESTE, 1", "Cep": "00000000",
    "DisponibilizaAgenda": "S", "TipoCredenciado": 0, "IdLoja": 0,
    "Latitude": "0", "Longitude": "0",
}


class PaginaComRoteadorInvertido(RV.PaginaDeReplay):
    """Só `opcoes-disponiveis` muda; todo o resto é o HAR real."""

    async def evaluate(self, js, arg):
        r = await super().evaluate(js, arg)
        caminho = str(arg.get("url") or "")
        if "/agendamentos/opcoes-disponiveis" in caminho:
            import json as _json
            corpo = _json.loads(r["text"])
            corpo["IrParaConclusaoDeAtendimento"] = False
            corpo["ExisteOrdemServico"] = False
            corpo["DisponibilizarAgendamento"] = True
            corpo["OpcoesAgendamento"] = [LOJA_INVENTADA]
            r["text"] = _json.dumps(corpo)
        return r


chamadas_g6 = RV.carregar("LAT")
page_g6 = PaginaComRoteadorInvertido(chamadas_g6)
params_g6 = RV.params_do_har(chamadas_g6)
params_g6["_runtime"] = RuntimeDeReplay()
ev_g6: dict = {}
r_g6 = asyncio.run(AF.abrir_atendimento_api(page_g6, params_g6, ev_g6))
d_g6 = ev_g6.get("desfecho") or {}
check("G6: com o roteador invertido, a MESMA lataria vira `agenda`",
      d_g6.get("tipo") == ST.DESFECHO_AGENDA, d_g6.get("tipo"))
check("G6: e a loja que o portal ofereceu aparece na lista",
      [x.get("nome") for x in (d_g6.get("lojas") or [])] == ["LOJA DE TESTE"],
      d_g6.get("lojas"))
check("G6 CONTROLE: sem inverter, a mesma peca deu loja_direta — os dois DIFEREM",
      d1.get("tipo") == ST.DESFECHO_LOJA_DIRETA
      and d_g6.get("tipo") == ST.DESFECHO_AGENDA)
check("G6: e o comprovante NAO e emitido quando ha agenda a escolher",
      d_g6.get("comprovante_emitido") is None)

# ==========================================================================
print("\n[G1b] PARA-BRISA — questionario, reparo e a loja lida DEPOIS do roteador")
# ==========================================================================
r2, ev2, p2, har2 = rodar("NOVO", extra={"especificos": {"aceita_reparo": "sim"}})

check("G1b: nenhuma chamada ficou sem resposta no acervo", not p2.sem_resposta,
      p2.sem_resposta)
# 📊 3 perguntas + o 204 = 4 chamadas a /questionarios/perguntas.
check("G1b: o questionario rodou 3 vezes e recebeu o 204 (4 chamadas)",
      p2.quantas("POST", "/questionarios/perguntas") == 4,
      p2.quantas("POST", "/questionarios/perguntas"))
check("G1b: `regras-reparo` saiu ANTES da fronteira B",
      -1 < p2.ordem_de("POST", "/questionarios/regras-reparo")
      < p2.ordem_de("POST", "/questionarios"),
      (p2.ordem_de("POST", "/questionarios/regras-reparo"),
       p2.ordem_de("POST", "/questionarios")))
check("G1b: `POST /questionarios` saiu uma vez",
      p2.quantas("POST", "/questionarios") == 1)
# As respostas que o motor acumulou têm de ser as MESMAS que o portal recebeu —
# é o que prova que o casamento por texto funcionou, e não só que algo saiu.
check("G1b: o acumulado enviado e IGUAL ao que o portal recebeu",
      p2.corpo_de("POST", "/questionarios")
      == RV.primeira(har2, "POST", "/questionarios", requisicao=True),
      p2.corpo_de("POST", "/questionarios"))
check("G1b: `alterar-reparo` saiu com {'Reparo': True}",
      p2.corpo_de("PUT", "/atendimentos/alterar-reparo") == {"Reparo": True},
      p2.corpo_de("PUT", "/atendimentos/alterar-reparo"))
check("G1b: e ele saiu DEPOIS do POST /questionarios",
      p2.ordem_de("PUT", "/atendimentos/alterar-reparo")
      > p2.ordem_de("POST", "/questionarios"))
# 🔴 A ordem que o G1b existe para guardar.
i_opcoes = p2.ordem_de("GET", "/agendamentos/opcoes-disponiveis")
i_leitura = max(i for i, (m, c) in enumerate(p2.emitidas())
                if (m, c.split("?")[0]) == ("GET", "/atendimentos"))
check("G1b: o `GET /atendimentos` que vale foi lido DEPOIS de opcoes-disponiveis",
      -1 < i_opcoes < i_leitura, (i_opcoes, i_leitura))

d2 = ev2.get("desfecho") or {}
check("G1b: o desfecho e loja_direta", d2.get("tipo") == ST.DESFECHO_LOJA_DIRETA,
      d2.get("tipo"))
loja2 = d2.get("loja") or {}
for campo in ("nome", "endereco", "telefone"):
    check(f"G1b: a loja veio com {campo} do ScriptFinalizacao", bool(loja2.get(campo)))
check("G1b: e a orientacao do telefone nao gruda no numero",
      "(Entre" not in loja2.get("telefone", ""), loja2.get("telefone", "")[:4])
# 📊 3 linhas de franquia: troca · desconto para reparo · valor para reparo.
check("G1b: a franquia veio com 3 linhas", len(d2.get("franquias") or []) == 3,
      [f.get("titulo") for f in (d2.get("franquias") or [])])
check("G1b: `reparo` e True", d2.get("reparo") is True)
check("G1b: o titulo do portal e o da CONCLUSAO, nao o do analista",
      "analista" not in (d2.get("titulo_portal") or "").lower(),
      d2.get("titulo_portal"))
check("G1b: o resultado e `done`", getattr(r2, "status", "") == "done",
      getattr(r2, "message", r2))

# ==========================================================================
print("\n[G1b CONTROLE] sem a decisao do segurado, o motor PARA antes da fronteira B")
# ==========================================================================
# `regras-reparo` é LEITURA e roda antes da fronteira B: dá para descobrir que
# falta a decisão e parar **sem ter materializado nada**.
r3, ev3, p3, _ = rodar("NOVO")   # sem `aceita_reparo`
check("CONTROLE: o motor parou em `decidir_reparo`",
      getattr(r3, "captured", {}).get("stage") == "decidir_reparo",
      getattr(r3, "captured", {}).get("stage"))
check("CONTROLE: e NENHUM POST /questionarios saiu",
      p3.quantas("POST", "/questionarios") == 0, p3.escritas())
check("CONTROLE: nem o alterar-reparo",
      p3.quantas("PUT", "/atendimentos/alterar-reparo") == 0)
check("CONTROLE: o resultado e needs_human", getattr(r3, "status", "") == "needs_human")
check("CONTROLE: e o par difere — com a resposta, o POST saiu",
      p2.quantas("POST", "/questionarios") == 1
      and p3.quantas("POST", "/questionarios") == 0)
check("CONTROLE: o portal REALMENTE ofereceu reparo nos dois casos",
      (ev3.get("reparo") or {}).get("portal_oferece") is True)

# ==========================================================================
print("\n[G1c] VIDRO DE PORTA — o portal deu AGENDA, e o motor nao agenda")
# ==========================================================================
r4, ev4, p4, har4 = rodar("ANT")
d4 = ev4.get("desfecho") or {}
check("G1c: nenhuma chamada ficou sem resposta no acervo", not p4.sem_resposta,
      p4.sem_resposta)
check("G1c: o desfecho e agenda", d4.get("tipo") == ST.DESFECHO_AGENDA,
      d4.get("tipo"))
check("G1c: com exatamente 1 loja", len(d4.get("lojas") or []) == 1,
      len(d4.get("lojas") or []))
loja4 = (d4.get("lojas") or [{}])[0]
check("G1c: a loja tem endereco", bool(loja4.get("endereco")))
check("G1c: e distancia lida do portal", bool(loja4.get("distancia")),
      loja4.get("distancia"))
check("G1c: e os dias com agenda", bool(loja4.get("dias")),
      [m.get("mes") for m in (loja4.get("dias") or [])])
check("G1c: NENHUM POST /agendamentos saiu",
      p4.quantas("POST", "/agendamentos") == 0, p4.escritas())
check("G1c: NENHUM POST /direcionamentos saiu",
      p4.quantas("POST", "/direcionamentos") == 0)
check("G1c: e o motor NAO cancelou",
      p4.quantas("PUT", "/atendimentos/cancelar") == 0)
check("G1c: o segurado precisa escolher",
      getattr(r4, "captured", {}).get("customer_choice_needed") is True)
check("G1c: `consultar-distancias` e LEITURA e saiu",
      p4.quantas("POST", "/lojas/consultar-distancias") == 1)
check("G1c: o portal NAO ofereceu reparo aqui (par de controle do G1b)",
      (ev4.get("reparo") or {}).get("portal_oferece") is False,
      (ev4.get("reparo") or {}).get("portal_oferece"))

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
