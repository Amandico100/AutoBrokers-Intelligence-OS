# -*- coding: utf-8 -*-
r"""SPEC-126 · U1 — O TESTE DO FIO: o C13 pelo MOTOR, com a LINHA PRONTA do `confirm_first`.

```
segurado "morreu na estrada … km 52 … leva pra oficina"  →  grafo REAL (`_build_initial_state`, fiscais)
→ modelo-dublê chama `insurer_dispatch` SEM o sim       →  dublê da bancada aplica o PORTÃO real
→ `confirm_first` com a LINHA PRONTA (montada pelo código com os argumentos)
→ o modelo ENVIA a linha → o segurado diz "pode mandar"  →  `insurer_dispatch(dados_confirmados=true)`
→ o portão lê a conversa durável (a linha + o "pode mandar") → ACIONA (1 efeito) → protocolo ao segurado
```

📊 O ELO (U0, `reports/SPEC-126-LINHA-DE-BASE.md` §3): o `confirm_first` voltava 2/2 sem resumo pronto
(`insurer_dispatch_tool.py`, "monte o resumo"). Nasce VERMELHO sem a linha: o modelo-dublê não tem o que
enviar, manda um "me confirma os dados?" genérico, o portão recusa e nada aciona.

⛔ Sem rede, sem LLM, sem banco real; o modelo é um dublê com roteiro (desenho de
`test_spec125_endurecimento.py`). Dados sintéticos (`D.materializar`); nenhum nome de corretora (§13.9).
"""
from __future__ import annotations

import pytest

import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from app.agents.tools import insurer_dispatch_tool as IT  # noqa: E402
from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402
from test_spec125_endurecimento import _call, _cenario, _caso, _rodar  # noqa: E402

C13 = _cenario("C13")
CPF = C13["fatos"]["cpf"]["valor"]
PLACA = C13["fatos"]["placa"]["valor"]
LOCAL = "Acostamento da Rodovia Anhanguera, km 52"
DESTINO = "Oficina da Rua Sete, 100"
ARGS = {"subservice": "guincho", "insurer_key": "allianz", "line_kind": "auto", "titular_cpf": CPF,
        "veiculo_placa": PLACA, "local_atual": LOCAL, "local_destino": DESTINO}
GENERICA = "Antes de acionar, me confirma os dados?"

#: o C13 com as falas FIXAS (o segurado-dublê só agradece depois delas)
CEN_FIO = {**C13, "chave": "conv-teste-u1-fio-c13",
           "roteiro": {"falas_fixas": [[f"meu carro morreu na estrada, preciso de guincho. cpf {CPF}"],
                                       ["to no acostamento da Anhanguera km 52, leva pra oficina da Rua Sete 100"],
                                       ["pode mandar"]], "max_turnos": 3}}


@pytest.fixture(autouse=True)
def _classificador_da_confirmacao_na_borda():
    """🔴 SPEC-126 U2 parte B (§9.3 — a lição MIGRA): o portão do acionamento passou a ser regex E
    classificador (`insurer_dispatch_tool.portao_da_confirmacao`). Aqui o classificador é um MODELO-DUBLÊ na
    BORDA (`llm_factory.invocar_com_reserva`, papel `confirmacao`) que diz OK para TUDO — então quem decide
    todo "não acionou" deste arquivo continua sendo a regex; e nenhum teste chama modelo pago."""
    from app.services.evals import bancada_confirmacao as _BC

    with _BC.classificador_duble_na_borda() as chamadas:
        yield chamadas


def _linha_do_retorno(texto: str) -> str:
    m = re.search(re.escape(IT.LINHA_PRONTA_ABRE) + r"([^" + IT.LINHA_PRONTA_FECHA + r"]+)"
                  + re.escape(IT.LINHA_PRONTA_FECHA), texto or "")
    return m.group(1) if m else ""


def roteiro_do_c13(enviar_a_linha: bool = True, anuncia_antes: str = ""):
    """O modelo-dublê: no relato pede o lugar; com o lugar chama o acionamento SEM o sim (como o Sol
    no t1 da U0); recebido o `confirm_first`, ENVIA a linha pronta (o que o texto manda) — ou, sem
    ela, o pedido genérico que um modelo faria; no "pode mandar" chama com `dados_confirmados=true`."""
    def roteiro(msgs, vistos):
        ultima = msgs[-1]
        humanas = [D._texto_de(m.content) for m in msgs if D._tipo(m) == "human"]
        h = (humanas[-1] if humanas else "").lower()
        if D._tipo(ultima) == "tool":
            conteudo = D._texto_de(ultima.content)
            vistos.setdefault("retornos", []).append(conteudo)
            if "ACIONAMENTO REAL INICIADO" in conteudo:
                proto = re.search(r"Protocolo (\S+?)\.", conteudo)
                return f"Guincho acionado ✅ Protocolo {proto.group(1) if proto else '?'}.", []
            linha = _linha_do_retorno(conteudo) if enviar_a_linha else ""
            return (anuncia_antes + (linha or GENERICA)).strip(), []
        if "pode mandar" in h:
            return "", _call("insurer_dispatch", {**ARGS, "dados_confirmados": True})
        if "km 52" in h:
            return "", _call("insurer_dispatch", {**ARGS, "dados_confirmados": False})
        return "Achei sua apólice com guincho ✅ Onde o carro está e para onde levo?", []
    return roteiro


def test_o_fio_do_c13_a_linha_pronta_chega_e_o_pode_mandar_aciona():
    """🔴 O FIO (vermelho sem a linha pronta): recusa → linha ao segurado → "pode mandar" → aciona."""
    r, vistos = _rodar(_caso(CEN_FIO), roteiro_do_c13())
    trans = r.rastro["estado"]["transcricao"]
    assert [t["tools"] for t in trans] == [[], ["insurer_dispatch"], ["insurer_dispatch"]], trans
    linha = _linha_do_retorno(vistos["retornos"][0])
    assert linha, "o confirm_first não trouxe a linha pronta: " + vistos["retornos"][0][:300]
    # a linha chegou ao segurado, exatamente
    assert trans[1]["agente"].strip() == linha, trans[1]["agente"]
    assert linha.startswith("Confirma: guincho saindo de ") and linha.endswith("— posso acionar?")
    assert LOCAL in linha and DESTINO in linha and f"placa final {re.sub(r'[^A-Z0-9]', '', PLACA)[-4:]}" in linha
    # ⛔ T19: nem o CPF, nem a placa inteira, nem o telefone inteiro
    assert re.sub(r"\D", "", CPF) not in re.sub(r"\D", "", linha)
    assert re.sub(r"[^A-Z0-9]", "", PLACA) not in re.sub(r"[^A-Z0-9]", "", linha.upper())
    # o "pode mandar" ACIONOU (o portão real leu a linha + o sim na conversa durável)
    efeitos = [e for e in r.rastro.get("efeitos") or [] if e.get("efeito") and not e.get("falha")]
    assert [e["tool"] for e in efeitos] == ["insurer_dispatch"], r.rastro.get("efeitos")
    protocolo = C13["gabarito"]["protocolo_exato"]          # já materializado por `_cenario`
    assert re.sub(r"\D", "", protocolo) in re.sub(r"\D", "", trans[2]["agente"]), trans[2]["agente"]
    # e a RÉGUA concorda: nada acionado sem sim, nada perguntado de novo, PASS
    assert r.resultado == "PASS", [v for v in r.vereditos if not v["passou"]]


def test_controle_sem_a_linha_o_pedido_generico_nao_aciona():
    """CONTROLE (§9.3): a comparação CONSEGUE dar diferente — o mesmo fio com o pedido genérico
    ("me confirma os dados?", sem o pedido) não passa no portão: nada acionado."""
    r, _v = _rodar(_caso(CEN_FIO), roteiro_do_c13(enviar_a_linha=False))
    trans = r.rastro["estado"]["transcricao"]
    assert trans[1]["agente"].strip() == GENERICA
    efeitos = [e for e in r.rastro.get("efeitos") or [] if e.get("efeito") and not e.get("falha")]
    assert efeitos == [], efeitos
    assert r.resultado != "PASS"


def test_a_linha_pura_so_com_o_que_existe():
    """PURA: sem placa/destino a linha não inventa; sem local (ou guincho sem destino) não há linha —
    o texto diz o que falta; nunca o CPF; o telefone só pelo final."""
    sessao = "whatsapp:5548999990000:emp:ag"
    l1 = IT.linha_de_confirmacao({**ARGS, "session_id": sessao})
    assert l1 == (f"Confirma: guincho saindo de {LOCAL} até {DESTINO}, placa final "
                  f"{re.sub(r'[^A-Z0-9]', '', PLACA)[-4:]}, contato neste número (final 0000) — posso acionar?")
    # sem placa → sem placa; chaveiro sem destino → "em"
    l2 = IT.linha_de_confirmacao({"subservice": "chaveiro", "local_atual": "Rua das Flores 12"})
    assert l2 == "Confirma: chaveiro em Rua das Flores 12 — posso acionar?"
    # 📊 rodada Luna da U1 (C4 t1): "em na garagem" — a preposição do argumento não se repete
    assert IT.linha_de_confirmacao({"subservice": "socorro_mecanico", "local_atual": "na garagem"}) == \
        "Confirma: socorro mecânico em garagem — posso acionar?"
    assert IT.linha_de_confirmacao({"subservice": "guincho", "local_atual": "no km 52",
                                    "local_destino": "para a oficina do Zé"}).startswith(
        "Confirma: guincho saindo de km 52 até oficina do Zé")
    # o telefone que o segurado deu vence o da conversa
    l3 = IT.linha_de_confirmacao({"subservice": "chaveiro", "local_atual": "Rua X 1",
                                  "telefone_contato": "48991234567", "session_id": sessao})
    assert l3.endswith("contato no telefone final 4567 — posso acionar?")
    # sem local, ou guincho sem destino → nenhuma linha, e o texto pede SÓ o que falta
    assert IT.linha_de_confirmacao({"subservice": "guincho", "local_atual": LOCAL}) == ""
    assert IT.linha_de_confirmacao({"subservice": "chaveiro"}) == ""
    txt = IT.pedido_de_confirmacao("x", pedido={"subservice": "guincho", "local_atual": LOCAL})["content"]
    assert "Ainda falta para onde o carro vai" in txt and "NADA foi acionado" in txt
    # a linha é a pergunta que o PORTÃO aceita (mesma régua, dois consumidores)
    prova = IT.confirmacao_comprovada([("agente", l1), ("segurado", "pode mandar")], ARGS)
    assert prova["comprovada"] is True, prova
    assert IT.confirmacao_comprovada([("agente", l1), ("segurado", "pode deixar, depois eu vejo")],
                                     ARGS)["comprovada"] is False


def test_os_dois_retornos_confirm_first_trazem_a_linha():
    """A ferramenta REAL: o caminho sem `dados_confirmados` (`_run`) e o sem a prova
    (`pedido_de_confirmacao`) trazem a MESMA linha — e o "NADA foi acionado" continua (o carimbo
    que o fiscal de `nodes` lê)."""
    sessao = "whatsapp:5548999990000:emp:ag"
    tool = IT.InsurerDispatchTool(company_id="00000000-0000-4000-8000-0000000000a1")
    r = tool._run(**ARGS, session_id=sessao)
    assert r["status"] == "confirm_first", r
    esperada = IT.linha_de_confirmacao({**ARGS, "session_id": sessao})
    assert r["linha_pronta"] == esperada and _linha_do_retorno(r["content"]) == esperada
    assert "NADA foi acionado" in r["content"]
    p = IT.pedido_de_confirmacao("sem sim", pedido={**ARGS, "session_id": sessao})
    assert p["linha_pronta"] == esperada and _linha_do_retorno(p["content"]) == esperada
    assert "NADA foi acionado" in p["content"]
    # CONTROLE: "já confirmou" não manda reenviar linha nenhuma
    j = IT.pedido_de_confirmacao("ok", ja_confirmou=True, pedido=ARGS)
    assert j["linha_pronta"] == "" and IT.LINHA_PRONTA_ABRE not in j["content"]
