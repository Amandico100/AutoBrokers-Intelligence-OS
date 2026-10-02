# -*- coding: utf-8 -*-
r"""SPEC-125 · ENDURECIMENTO FINAL — as duas causas em CÓDIGO que as rodadas mediram e não explicavam.

```
P-125-04  a apresentação no 2º turno (Sol C1/C4/C7/C15) — e a orientação de segurança que não chegava
          CAUSA: `invoke_agent` entrega só o texto do ÚLTIMO AIMessage; o que o modelo escreveu JUNTO
          da ferramenta (a apresentação, "fique longe dos fios, ligue 193") se perdia. A ficha
          continuava pedindo a apresentação (J5: só conta a que SAIU) → ela aparecia no turno 2.
          📊 nos JSON gravados do Sol: todo 1º turno com ferramenta saiu SEM apresentação, e o motivo
          do handoff dizia "Orientado a…" sobre um texto que o segurado não recebeu (C10: "as
          orientações que te passei").
P-125-03  "cadê o guincho?" (C8) vai a pessoa
          CAUSA: num caso JÁ ACIONADO (`protocolo`/`dispatch_state` na ficha) a segunda chance da
          SPEC-123 era pulada SEMPRE ("a R9 decide") — sem perguntar à R9. A fala do C8 é `N` na R9.
          Na bancada não aparecia: lá a ferramenta de pessoa é um dublê.
```

O que se afirma é o MOTOR (§9.4): o grafo REAL com o `_build_initial_state` real pela bancada N3
(o modelo é um dublê com roteiro), e o `HumanHandoffTool._arun` REAL com a borda da SPEC-123 sobre os
MOTIVOS GRAVADOS da rodada Z (`conversa_z_luna_k2.json`). Cada bloco tem a reprodução (vermelha
antes) e a linha de CONTROLE.

⛔ Sem rede, sem banco real, sem LLM, nada enviado. Dados sintéticos/mascarados; nenhum nome de
corretora (§13.9).

Rodar (de `backend/`):
    PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_spec125_endurecimento.py -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402

from app.agents import nodes as N  # noqa: E402
from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402

# a borda da SPEC-123 (banco/Redis/WhatsApp/grupo/diário dublês; a ferramenta e o diário REAIS)
from test_spec123_atendimento_segunda_chance import (  # noqa: E402,F401
    ENVIOS, X, _banco, _conversa, _diario, _linha, _pedir, borda)

CORPUS = Path(AQUI) / "corpus" / "bancada"
Z_LUNA = CORPUS / "RESULTADOS" / "conversa_z_luna_k2.json"
Z_SOL = CORPUS / "RESULTADOS" / "conversa_z_sol_v2.json"
DEPOIS_SOL_V2 = CORPUS / "RESULTADOS" / "conversa_depois_sol_v2.json"


def _cenario(id_: str) -> dict:
    for linha in (CORPUS / "conversa" / "casos.jsonl").read_text(encoding="utf-8").splitlines():
        if linha.strip():
            c = json.loads(linha)
            if c.get("id") == id_:
                return D.materializar(c)
    raise AssertionError(f"cenário {id_} fora do corpus")


def _gravado(arquivo: Path, chave: str, tentativa: int = 1) -> dict:
    d = json.loads(arquivo.read_text(encoding="utf-8"))
    for r in d["resultados"]:
        if r["chave"] == chave and r["tentativa"] == tentativa:
            return r
    raise AssertionError(f"{chave} t{tentativa} fora de {arquivo.name}")


# ===========================================================================
# A BANCADA N3 com o modelo-dublê (o mesmo desenho de `test_spec125_conserto_z`)
# ===========================================================================
class _Modelo:
    def __init__(self, papel, vistos, roteiro):
        self.papel, self.vistos, self.roteiro = papel, vistos, roteiro
        self.model_name = f"fake:{papel}"
        self.callbacks = []

    def bind_tools(self, tools, **_k):
        return self

    async def ainvoke(self, msgs, config=None, **_k):
        msgs = msgs if isinstance(msgs, list) else [msgs]
        if self.papel.startswith("agente"):
            sistema = next((D._texto_de(m.content) for m in msgs if D._tipo(m) == "system"), "")
            self.vistos.setdefault("sistemas", []).append(sistema)
            texto, calls = self.roteiro(msgs, self.vistos)
        else:
            sistema = D._texto_de(msgs[0].content)
            if sistema.startswith("Você avalia"):
                texto, calls = json.dumps({"criterios": [], "tom_humano": 4,
                                           "entendeu_o_obvio": 4, "comentario": "ok"}), []
            else:
                texto, calls = json.dumps({"mensagens": ["valeu"], "encerrar": True}), []
        return AIMessage(content=texto, tool_calls=calls,
                         usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
                         response_metadata={"model_name": self.model_name})


def _call(nome, args, n=[0]):
    n[0] += 1
    return [{"name": nome, "args": args, "id": f"call_{nome}_{n[0]}", "type": "tool_call"}]


def _rodar(caso, roteiro):
    vistos = {}

    def construir(resolvido, _cb):
        return _Modelo(B._campo(resolvido, "model"), vistos, roteiro)

    def resolver(papel, *, override, **_k):
        return {"papel": papel, "provider": override["provider"], "model": override["model"],
                "effort": None, "api_surface": "teste", "capacidades": {"tools": True, "max_output": 512}}

    rel = B.rodar_bancada("conversa", ["fake:agente"], casos=[caso], k=1, nivel="N3",
                          construir_llm=construir, resolver=resolver,
                          precos=lambda b: {"entrada": 1.0, "saida": 4.0}, teto_usd=50.0,
                          segunda="fake:segurado")
    assert not rel.parada, rel.parada
    r = rel.resultados[0]
    assert r.erro is None, r.erro
    return r, vistos


def _caso(cen: dict, *, dubles_extra: dict = None) -> dict:
    gab = dict(cen.get("gabarito") or {})
    dubles = B._resolver_dubles(cen)
    dubles.update(dubles_extra or {})
    return {"chave": cen["chave"], "id": cen["id"], "papel": "conversa", "nivel": "N3", "critico": False,
            "tenant": "A",
            "entrada": {**{k: cen.get(k) for k in ("persona", "objetivo", "comportamento", "fatos", "roteiro",
                                                   "historico", "ficha", "telefone")},
                        "dubles": dubles},
            "oraculo": {"efeitos_exatos": gab.get("efeitos_exatos") or {}, "conversa": gab},
            "origem": "teste endurecimento", "falhas_injetadas": [], "efeitos_proibidos": []}


#: O C1 do corpus, com DOIS turnos fixos — o 1º é o relato, o 2º a resposta à pergunta de segurança.
CEN_C1 = {**_cenario("C1"), "chave": "conv-teste-endurecimento-c1",
          "roteiro": {"falas_fixas": [["derrapei na chuva e bati num poste agora, ninguem se machucou"],
                                      ["to fora da pista, nao vi fio caido"]], "max_turnos": 2}}

PEDIDO_DE_APRESENTACAO = "APRESENTAÇÃO: apresente-se agora"
APRESENTACAO_CALADA = "NÃO se apresente"
ORIENTACAO = "Se houver fio caído encostando no carro, fique dentro dele e ligue 193."
FINAL_DO_HANDOFF = "Nossa equipe de sinistro já recebeu o que você contou. Você está em um lugar seguro?"


def _frase_de_apresentacao(sistema: str) -> str:
    m = re.search(r'APRESENTAÇÃO: apresente-se agora, UMA vez, numa frase curta \("([^"]+)"\)', sistema)
    assert m, "a linha APRESENTAÇÃO do prompt real mudou de forma"
    return m.group(1)


def _roteiro_do_sol(onde_apresenta: str):
    """O que o Sol fez nas conversas gravadas: no turno do sinistro, ele escreve a apresentação e a
    orientação de segurança JUNTO da chamada a `request_human_agent` (`onde_apresenta='junto'`); o
    texto depois da ferramenta só confirma a passagem. CONTROLES: `'final'` (apresenta no texto final)
    e `'nunca'` (não se apresenta)."""
    def roteiro(msgs, vistos):
        ultima = msgs[-1]
        humanas = [D._texto_de(m.content) for m in msgs if D._tipo(m) == "human"]
        h = (humanas[-1] if humanas else "").lower()
        if D._tipo(ultima) == "tool":
            if onde_apresenta == "final":
                return _frase_de_apresentacao(vistos["sistemas"][-1]) + " " + FINAL_DO_HANDOFF, []
            return FINAL_DO_HANDOFF, []
        if "poste" in h:
            junto = (_frase_de_apresentacao(vistos["sistemas"][-1]) + " Sinto muito pelo susto. " + ORIENTACAO
                     if onde_apresenta == "junto" else "")
            return junto, _call("request_human_agent", {"reason": "sinistro — colisão com poste, sem feridos"})
        return "Que bom. Fique longe do poste enquanto a equipe te chama por aqui.", []
    return roteiro


# ===========================================================================
# P-125-04 · o que foi dito junto da ferramenta chega ao segurado
# ===========================================================================
def test_reproducao_os_json_do_sol_o_turno_com_ferramenta_saia_sem_apresentacao_e_sem_a_orientacao():
    """📊 O acervo gravado (sem LLM): nos 1ºs turnos do Sol com ferramenta, nenhuma apresentação — e o
    motivo do handoff diz que o segurado foi ORIENTADO, numa resposta que não tem a orientação."""
    def apresenta(t):
        return "assistente virtual" in t.lower() or "aqui é" in t.lower()

    sem, depois = [], []
    for arq in (Z_SOL, DEPOIS_SOL_V2):
        for r in json.loads(arq.read_text(encoding="utf-8"))["resultados"]:
            trans = r["rastro"]["estado"]["transcricao"]
            if trans[0]["tools"]:
                sem.append(not apresenta(trans[0]["agente"]))
                depois += [apresenta(t["agente"]) for t in trans[1:2]]
    assert sem and all(sem), sem
    assert any(depois), "o grave 3: a apresentação aparece no turno 2"
    c10 = _gravado(DEPOIS_SOL_V2, "conv-c10-risco-a-vida-fumaca")["rastro"]["estado"]["transcricao"][0]
    assert "193" in json.dumps(c10["tool_args"], ensure_ascii=False) and "Orientado" in json.dumps(
        c10["tool_args"], ensure_ascii=False)
    assert "193" not in c10["agente"], "a orientação do motivo não está no texto que saiu"


def test_pelo_motor_a_apresentacao_e_a_orientacao_dita_junto_da_ferramenta_saem_no_turno_1():
    """🔴 (vermelho antes) o turno 1 entrega a apresentação e a orientação de segurança escritas JUNTO
    do `request_human_agent`; a ficha a confirma e o turno 2 NÃO se apresenta de novo."""
    r, vistos = _rodar(_caso(CEN_C1), _roteiro_do_sol("junto"))
    trans = r.rastro["estado"]["transcricao"]
    assert len(trans) == 2 and trans[0]["tools"] == ["request_human_agent"]
    t1 = trans[0]["agente"]
    frase = _frase_de_apresentacao(vistos["sistemas"][0])
    assert t1.startswith(frase), t1
    assert ORIENTACAO in t1, t1
    assert FINAL_DO_HANDOFF in t1, "o texto depois da ferramenta continua saindo"
    assert t1.count(frase) == 1
    # o 2º turno: o prompt REAL não pede mais a apresentação — e nenhuma aparece
    assert PEDIDO_DE_APRESENTACAO in vistos["sistemas"][0]
    assert APRESENTACAO_CALADA in vistos["sistemas"][-1], vistos["sistemas"][-1][-600:]
    assert "assistente virtual" not in trans[1]["agente"].lower()


def test_controle_apresentou_no_texto_final_o_turno_2_tambem_cala():
    """CONTROLE: o caminho que já funcionava (apresentação no texto FINAL) continua igual."""
    r, vistos = _rodar(_caso(CEN_C1), _roteiro_do_sol("final"))
    t1 = r.rastro["estado"]["transcricao"][0]["agente"]
    assert t1.startswith(_frase_de_apresentacao(vistos["sistemas"][0]))
    assert APRESENTACAO_CALADA in vistos["sistemas"][-1]


def test_controle_nao_se_apresentou_o_turno_2_pede_de_novo_j5():
    """CONTROLE (J5, o lado seguro): sem apresentação nenhuma, o turno 2 ainda pede — prova que a
    comparação do teste principal CONSEGUE dar diferente (§9.3)."""
    _r, vistos = _rodar(_caso(CEN_C1), _roteiro_do_sol("nunca"))
    assert PEDIDO_DE_APRESENTACAO in vistos["sistemas"][-1]


def test_o_dito_junto_da_ferramenta_passa_pelo_fiscal_da_honestidade():
    """⛔ O texto de antes da ferramenta não escapa dos fiscais: "já passei para a equipe" escrito
    JUNTO de um `request_human_agent` que NÃO passou (segunda chance) é reescrito."""
    from app.agents.tools.human_handoff import SEGUNDA_CHANCE_DO_HANDOFF

    def roteiro(msgs, vistos):
        if D._tipo(msgs[-1]) == "tool":
            return "Me conta: o carro está fora da pista?", []
        if any("poste" in D._texto_de(m.content).lower() for m in msgs if D._tipo(m) == "human"):
            return ("Já passei seu caso para a nossa equipe.",
                    _call("request_human_agent", {"reason": "não sei"}))
        return "Certo.", []

    cen = {**CEN_C1, "roteiro": {"falas_fixas": [CEN_C1["roteiro"]["falas_fixas"][0]], "max_turnos": 1}}
    caso = _caso(cen, dubles_extra={"request_human_agent": {"resposta": SEGUNDA_CHANCE_DO_HANDOFF,
                                                            "efeito": False}})
    r, _v = _rodar(caso, roteiro)
    t1 = r.rastro["estado"]["transcricao"][0]["agente"]
    assert "Já passei seu caso" not in t1, t1
    # o fiscal reescreveu o texto INTEIRO (o dito antes + o final) para a forma honesta dele
    assert "Ainda não consegui confirmar" in t1, t1


def test_so_o_turno_corrente_e_sem_repetir():
    """PURA: o texto junto de ferramenta de um turno ANTERIOR não volta; trecho que o final já tem
    não se repete; sem ferramenta, o texto final é o mesmo objeto de antes."""
    msgs = [HumanMessage(content="turno velho"),
            AIMessage(content="dito no turno velho", tool_calls=_call("x", {})),
            HumanMessage(content="turno novo"),
            AIMessage(content=[{"type": "text", "text": "Oi! Aqui é a assistente."}],
                      tool_calls=_call("y", {})),
            ToolMessage(content="ok", tool_call_id="t", name="y"),
            AIMessage(content="Repetido.", tool_calls=_call("z", {})),
            ToolMessage(content="ok", tool_call_id="t2", name="z")]
    assert N.falas_ditas_junto_da_ferramenta(msgs) == ["Oi! Aqui é a assistente.", "Repetido."]
    assert N.com_o_que_foi_dito_antes_da_ferramenta("Repetido. E mais.", msgs) == \
        "Oi! Aqui é a assistente.\n\nRepetido. E mais."
    assert N.com_o_que_foi_dito_antes_da_ferramenta("só o final", msgs[:3]) == "só o final"


# ===========================================================================
# P-125-03 · "cadê o guincho?" num caso acionado ganha a segunda chance (a R9 decide de verdade)
# ===========================================================================
def _motivos_gravados_do_c8() -> list:
    out = []
    for t in (1, 2):
        r = _gravado(Z_LUNA, "conv-c8-irritado-sem-pedir-pessoa", t)
        out += [c["args"]["reason"] for c in r["rastro"]["tool_calls"] if c["name"] == "request_human_agent"]
    assert len(out) == 2, out
    return out


def _falas_do_c8() -> list:
    cen = _cenario("C8")
    falas = [m["texto"] for m in cen["historico"] if m["de"] == "segurado"]
    return (falas + cen["roteiro"]["falas_fixas"][0])[-4:]


FICHA_ACIONADA = {"fase": "acionado", "subservice": "guincho", "dispatch_state": "monitoring",
                  "protocolo": "900000001"}


@pytest.mark.parametrize("motivo", _motivos_gravados_do_c8())
def test_reproducao_c8_o_motivo_gravado_num_caso_acionado_ganha_a_segunda_chance(motivo):
    """🔴 (vermelho antes: "o caso já foi acionado…") os DOIS motivos que a Luna escreveu na rodada Z,
    com as falas do cenário e a ficha de um caso acionado de verdade."""
    from app.agents.tools.human_handoff import por_que_vai_direto_a_pessoa
    from app.atendimento.pos_acionamento import classificar_turno

    assert classificar_turno(_falas_do_c8()) not in ("K1", "K2", "K3", "J", "L", "P", "Z")
    caso = {"ficha_atendimento": dict(FICHA_ACIONADA), "mensagens": _falas_do_c8()}
    assert por_que_vai_direto_a_pessoa(motivo, caso=caso) == ""


@pytest.mark.parametrize("fala", [
    "o guincho nao chegou e to no acostamento",          # K1
    "isso é um absurdo",                                  # K2
    "quero cancelar o pedido",                            # K3
    "vcs cobram a seguradora pra mim?",                   # J
    "quando vou receber a indenização?",                  # L
    "quero falar com uma pessoa",                         # P
])
def test_controle_o_que_a_r9_manda_a_pessoa_continua_indo_direto(fala):
    from app.agents.tools.human_handoff import por_que_vai_direto_a_pessoa

    caso = {"ficha_atendimento": dict(FICHA_ACIONADA), "mensagens": [fala]}
    assert por_que_vai_direto_a_pessoa("cliente cobrando o guincho", caso=caso), fala


def test_controle_sem_fala_para_ler_continua_direto():
    from app.agents.tools.human_handoff import por_que_vai_direto_a_pessoa

    assert por_que_vai_direto_a_pessoa("não sei", caso={"ficha_atendimento": dict(FICHA_ACIONADA)})


def test_pela_ferramenta_real_o_c8_acionado_ganha_uma_chance_e_so_uma(borda):
    """O `HumanHandoffTool._arun` REAL (borda da SPEC-123): o motivo gravado da Luna, a conversa com o
    caso acionado e as falas do C8 em `messages` → 1ª vez a segunda chance (nada marcado, ninguém
    avisado); 2ª vez a pessoa, como sempre."""
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    motivo = _motivos_gravados_do_c8()[0]
    cid = "c-c8-acionado-01"
    b = _banco(_conversa(cid, preview=_falas_do_c8()[-1], ficha=dict(FICHA_ACIONADA)))
    for i, fala in enumerate(_falas_do_c8()):
        b.tabelas["messages"].append({"conversation_id": cid, "role": "user", "content": fala,
                                      "created_at": "2026-10-02T10:%02d:00+00:00" % i})
    r1 = _pedir(H, b, cid, motivo)
    assert r1 == H.SEGUNDA_CHANCE_DO_HANDOFF, r1
    assert _linha(b, cid)["status"] == "open" and ENVIOS == []
    assert len(_diario(b, cid)) == 1
    r2 = _pedir(H, b, cid, motivo)
    assert r2 == SUCESSO_DO_HANDOFF, r2
    assert _linha(b, cid)["status"] == "HUMAN_REQUESTED"


def test_controle_pela_ferramenta_real_o_k1_acionado_vai_na_primeira(borda):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    cid = "c-c8-acionado-k1"
    b = _banco(_conversa(cid, preview="o guincho nao chegou e to no acostamento",
                         ficha=dict(FICHA_ACIONADA)))
    b.tabelas["messages"].append({"conversation_id": cid, "role": "user",
                                  "content": "o guincho nao chegou e to no acostamento",
                                  "created_at": "2026-10-02T10:00:00+00:00"})
    assert _pedir(H, b, cid, _motivos_gravados_do_c8()[0]) == SUCESSO_DO_HANDOFF
    assert _diario(b, cid) == [] or all(l["acao"] == "chamou_pessoa" for l in _diario(b, cid))


def test_o_prompt_v2_nao_manda_agir_com_ferramenta_quando_nenhuma_avanca():
    """O texto v2 de ACOMPANHAR (a Luna citava "cobrar a seguradora" como ação dela): a ferramenta é a
    que AVANÇA; "cadê o guincho?" → estado + oferta. ⛔ v1 intacta (o sha da S4)."""
    import hashlib

    from app.core.prompts import ATTENDANCE_BASE_PROMPT_V1, ATTENDANCE_BASE_PROMPT_V2

    linha = next(l for l in ATTENDANCE_BASE_PROMPT_V2.splitlines() if l.startswith("- **NÃO CHEGOU"))
    assert "AJA (ferramenta na mesma resposta)" not in linha
    assert "AVANÇA" in linha and "cadê o guincho?" in linha and "OFEREÇA" in linha
    assert hashlib.sha256(ATTENDANCE_BASE_PROMPT_V1.encode("utf-8")).hexdigest().startswith("2713eee75b689c7b")
