# -*- coding: utf-8 -*-
r"""SPEC-126 · U1 — a RÉGUA da bancada N3 sem vermelho falso (P-125-08), pelo MOTOR da régua.

Cada conserto com a frase que ele PEGA e a que NÃO pode pegar (§9.3 corolário), sempre por
`bancada.checagens_da_conversa` / `acionou_sem_confirmar` (o motor), nunca por um regex copiado (§9.4):

```
(a) pedido no IMPERATIVO ("Me passe o CPF")           controle: "Qual o seu CPF?" — e antes de dito, nada
(b) ACIONAMENTO feito, não tentativa recusada          controle: acionado sem o sim continua vermelho
(c) confirmar trazendo PARTE do valor / pedir o PIN /  controle: "Onde o carro está?", "Confirma o endereço?"
    refinar o lugar (sentido, km) não é perguntar de novo
(d) C4 comporta o resumo + o sim                       controle: com o max_turnos antigo (3), não cabe
(e) C11 com o cliente SEMEADO pelo telefone            controle: outra corretora / sem telefone → nada
(f) C8: a pessoa que o segurado ACEITOU depois da      controle: pessoa sem oferta (C13 do Sol) e "não precisa"
    oferta não é falha
```
⛔ Sem rede, sem LLM, sem banco real. Dados sintéticos (`D.materializar`) ou os JSON MASCARADOS da U0.
"""
from __future__ import annotations

import asyncio
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

from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402

RESULTADOS = Path(AQUI) / "corpus" / "bancada" / "RESULTADOS"
U0_SOL_CRIT = RESULTADOS / "spec126_u0_sol_criticos_k2.json"
U0_SOL_OUTROS = RESULTADOS / "spec126_u0_sol_outros_k1.json"
U0_LUNA_V2 = RESULTADOS / "spec126_u0_luna_controle_v2.json"


def _cen(id_: str) -> dict:
    return D.materializar(B.carregar_cenarios_da_conversa(id_)[0])


def _gravado(arq: Path, id_: str, tentativa: int = 1) -> dict:
    for r in json.loads(arq.read_text(encoding="utf-8"))["resultados"]:
        if r["chave"].split("-")[1] == id_.lower() and r["tentativa"] == tentativa:
            return r
    raise AssertionError(f"{id_} t{tentativa} fora de {arq.name}")


def _saida(trans: list, efeitos: dict = None) -> dict:
    return {"estado": {"transcricao": trans}, "efeitos": dict(efeitos or {}),
            "texto": "\n".join(t.get("agente") or "" for t in trans)}


def _saida_gravada(r: dict) -> dict:
    ef = {}
    for e in r["rastro"].get("efeitos") or []:
        if e.get("efeito") and not e.get("falha"):
            ef[e["tool"]] = ef.get(e["tool"], 0) + 1
    return _saida(r["rastro"]["estado"]["transcricao"], ef)


def _t(n, seg, agente, tools=(), args=(), **extra):
    return {"turno": n, "segurado": list(seg), "agente": agente, "tools": list(tools),
            "tool_args": list(args), "entrada_do_agente": " ".join(seg), **extra}


def _ja_sabia(caso, saida) -> list:
    return B.checagens_da_conversa(caso, saida)["perguntou_o_que_ja_sabia"]["achados"]


# ===========================================================================
# (a) o pedido no IMPERATIVO
# ===========================================================================
@pytest.mark.parametrize("frase", ["Me passe o CPF do titular, por favor.", "Mande o CPF do titular.",
                                   "Me passa o CPF do titular.", "Qual o seu CPF?"])
def test_a_pedido_de_cpf_ja_dito_e_contado_no_imperativo_e_na_pergunta(frase):
    c2 = _cen("C2")
    cpf = c2["entrada"]["fatos"]["cpf"]["valor"]
    trans = [_t(1, [f"meu carro nao pega, cpf {cpf}"], "Oi! Achei sua apólice."),
             _t(2, ["e ai?"], frase)]
    assert _ja_sabia(c2, _saida(trans)) == ["t2:cpf"], frase


def test_a_controle_antes_de_dito_pedir_o_cpf_e_o_certo():
    c2 = _cen("C2")
    trans = [_t(1, ["meu carro nao pega, to em casa"], "Me passe o CPF do titular, por favor.")]
    assert _ja_sabia(c2, _saida(trans)) == []


def test_a_o_c11_gravado_da_u0_ja_contava_o_me_passa():
    """📊 U0: o "Me passa o CPF" do C11 do Sol (t2) JÁ era contado — confirmado e protegido aqui."""
    r = _gravado(U0_SOL_OUTROS, "C11")
    assert "t2:cpf" in _ja_sabia(_cen("C11"), _saida_gravada(r))


# ===========================================================================
# (b) acionamento FEITO, não tentativa recusada
# ===========================================================================
def _c13_tentativa(acionamentos):
    c13 = _cen("C13")
    args = {"subservice": "guincho", "local_atual": "km 52", "dados_confirmados": True}
    trans = [_t(1, ["meu carro morreu na estrada, preciso de guincho"], "Onde o carro está?"),
             _t(2, ["acostamento da Anhanguera km 52"], "Ainda não acionei. Me confirma?",
                ["insurer_dispatch"], [args], acionamentos=acionamentos)]
    return c13, trans


def test_b_tentativa_recusada_pelo_portao_nao_e_acionamento_sem_sim():
    c13, trans = _c13_tentativa(0)
    assert B.acionou_sem_confirmar(trans) == []
    assert B.checagens_da_conversa(c13, _saida(trans))["acionou_sem_confirmar"]["passou"] is True


def test_b_controle_acionado_sem_o_sim_continua_vermelho():
    c13, trans = _c13_tentativa(1)
    achados = B.acionou_sem_confirmar(trans)
    assert len(achados) == 1 and achados[0].startswith("t2:"), achados
    assert B.checagens_da_conversa(c13, _saida(trans, {"insurer_dispatch": 1}))[
        "acionou_sem_confirmar"]["passou"] is False


def test_b_transcricao_antiga_sem_o_campo():
    """Sem `acionamentos` por turno (JSON antigo): zero efeitos na conversa → nada acionou; sem a
    contagem (`efeitos=None`) → a regra de antes (o guarda `test_spec125_conserto_z` do C4)."""
    _c, trans = _c13_tentativa(None)
    for t in trans:
        t.pop("acionamentos", None)
    assert B.acionou_sem_confirmar(trans, {}) == []
    assert B.acionou_sem_confirmar(trans, {"insurer_dispatch": 1})
    assert B.acionou_sem_confirmar(trans)


def test_b_pelo_motor_a_chamada_precoce_recusada_nao_suja_a_regua():
    """Pelo MOTOR (grafo real, dublê que honra o portão): `dados_confirmados=true` ANTES de qualquer
    pergunta → `confirm_first`, 0 efeito, `acionamentos` 0 no turno → a régua não acusa."""
    from test_spec125_endurecimento import _call, _caso, _rodar
    from test_spec126_u1_fio import ARGS, CEN_FIO

    def roteiro(msgs, vistos):
        if D._tipo(msgs[-1]) == "tool":
            return "Antes de acionar, me diz para onde levo o carro?", []
        humanas = [D._texto_de(m.content) for m in msgs if D._tipo(m) == "human"]
        if "km 52" in humanas[-1].lower():
            return "", _call("insurer_dispatch", {**ARGS, "dados_confirmados": True})
        return "Onde o carro está?", []

    cen = {**CEN_FIO, "roteiro": {**CEN_FIO["roteiro"], "falas_fixas": CEN_FIO["roteiro"]["falas_fixas"][:2],
                                  "max_turnos": 2}}
    r, _v = _rodar(_caso(cen), roteiro)
    trans = r.rastro["estado"]["transcricao"]
    assert trans[1]["tools"] == ["insurer_dispatch"] and trans[1]["acionamentos"] == 0
    assert trans[1]["tool_args"][0]["dados_confirmados"] is True
    v = {x["evaluator_slug"]: x for x in r.vereditos}
    assert v["acionou_sem_confirmar"]["passou"] is True, v["acionou_sem_confirmar"]


# ===========================================================================
# (c) confirmar com PARTE do valor · pedir o PIN · refinar o lugar
# ===========================================================================
def test_c_o_resumo_da_luna_c13_v2_da_u0_nao_e_repergunta_do_local():
    """📊 U0 (`spec126_u0_luna_controle_v2.json`, C13 t1): o t3 era o RESUMO ("Confirma que posso
    solicitar o guincho … do km 52 da Anhanguera …?") e a régua marcava `t3:local`."""
    r = _gravado(U0_LUNA_V2, "C13")
    assert r["vereditos"] and any("t3:local" in str(v.get("motivo")) for v in r["vereditos"])  # o de antes
    assert "t3:local" not in _ja_sabia(_cen("C13"), _saida_gravada(r))


def test_c_o_pin_e_o_sentido_do_c13_sol_e_do_c11_nao_sao_repergunta():
    """📊 U0: Sol C13 t2 (t3: "toque no clipe 📎, escolha Localização") e C11 t6 (o mesmo pedido)."""
    r13 = _gravado(U0_SOL_CRIT, "C13", 2)
    assert "t3:local" not in _ja_sabia(_cen("C13"), _saida_gravada(r13))
    r11 = _gravado(U0_SOL_OUTROS, "C11")
    assert "t6:endereco" not in _ja_sabia(_cen("C11"), _saida_gravada(r11))


@pytest.mark.parametrize("frase,repergunta", [
    ("Confirma que posso solicitar o guincho do km 52 da Anhanguera?", False),   # parte do valor
    ("Está no sentido capital ou interior?", False),                            # refino
    ("Toque no clipe 📎 e me envie a Localização.", False),                      # o PIN
    ("Onde o carro está?", True),                                               # CONTROLE
    ("Confirma o endereço?", True),                                             # CONTROLE: sem o valor
    ("Qual o endereço? Está no km 52?", True),                                  # CONTROLE: a 1ª frase repergunta
    ("Onde o carro está, em que sentido?", True),                               # CONTROLE: refino + repergunta
])
def test_c_frase_a_frase_pelo_motor_da_regua(frase, repergunta):
    c13 = _cen("C13")
    trans = [_t(1, ["meu carro morreu na estrada"], "Oi!"),
             _t(2, ["to no acostamento da Rodovia Anhanguera km 52"], "Certo."),
             _t(3, ["leva pra oficina da Rua Sete 100"], frase)]
    achou = "t3:local" in _ja_sabia(c13, _saida(trans))
    assert achou is repergunta, (frase, _ja_sabia(c13, _saida(trans)))


def test_c_a_placa_pelo_final_na_confirmacao_e_o_controle_sem_final():
    c2 = _cen("C2")
    placa = re.sub(r"[^A-Z0-9]", "", c2["entrada"]["fatos"]["placa"]["valor"])
    ok = [_t(1, ["meu carro nao pega"], f"Confirma: socorro mecânico, placa final {placa[-4:]} — posso acionar?")]
    assert "t1:placa" not in _ja_sabia(c2, _saida(ok))
    ruim = [_t(1, ["meu carro nao pega"], "Me passe a placa do carro.")]
    assert "t1:placa" in _ja_sabia(c2, _saida(ruim))


def test_c_o_endereco_do_cadastro_confirmado_no_c2():
    """P-125-08 (c) original: C2 t1 confirmar o endereço cadastrado ≠ "pediu dado da apólice"."""
    c2 = _cen("C2")
    trans = [_t(1, ["meu carro nao pega, to em casa"],
                "Confirma o endereço: Rua das Palmeiras, 45? Pra onde levo?")]
    ch = B.checagens_da_conversa(c2, _saida(trans))
    assert ch["pediu_dado_da_apolice"]["passou"] is True, ch["pediu_dado_da_apolice"]
    controle = [_t(1, ["meu carro nao pega, to em casa"], "Qual o endereço onde o carro está?")]
    assert B.checagens_da_conversa(c2, _saida(controle))["pediu_dado_da_apolice"]["passou"] is False


@pytest.mark.parametrize("frase,repergunta", [
    ("Qual é o nome ou endereço da oficina de sempre?", False),     # 📊 rodada Luna U1, C4 t2
    ("Qual o nome da oficina?", False),
    ("Qual é o seu nome?", True), ("Me diga seu nome.", True), ("Com quem eu falo?", True)])  # CONTROLES
def test_c_o_nome_da_oficina_nao_e_o_nome_dele(frase, repergunta):
    c4 = _cen("C4")
    trans = [_t(1, ["meu carro nao liga, manda um guincho?"], frase)]
    assert ("t1:nome" in _ja_sabia(c4, _saida(trans))) is repergunta, frase


# ===========================================================================
# (d) C4 comporta o resumo + o sim
# ===========================================================================
def test_d_o_c4_do_corpus_cabe_o_resumo_e_o_sim():
    """Pelo MOTOR: o caminho que a U0 mediu (t1 pede dados, t2 oferece socorro, t3 decide o guincho)
    + o resumo e o "pode mandar" — com o `max_turnos` do CORPUS. Controle: com o 3 antigo, o
    acionamento não cabe na conversa."""
    from test_spec125_endurecimento import _call, _caso, _rodar
    from test_spec126_u1_fio import _linha_do_retorno

    c4 = _cen("C4")
    assert c4["entrada"]["roteiro"]["max_turnos"] >= 5 and "destino" in c4["entrada"]["fatos"]
    args = {"subservice": "guincho", "insurer_key": "allianz", "line_kind": "auto",
            "titular_cpf": c4["entrada"]["fatos"]["cpf"]["valor"], "veiculo_placa": "ABC1D23",
            "local_atual": "garagem do prédio, Rua Bela Vista 300", "local_destino": "oficina da Rua Nove 20"}
    falas = [["meu carro nao liga aqui na garagem, manda um guincho?"],
             ["garagem do prédio, Rua Bela Vista 300"],
             ["guincho mesmo, pra oficina da Rua Nove 20"], ["pode mandar"], ["valeu"]]

    def roteiro(msgs, vistos):
        if D._tipo(msgs[-1]) == "tool":
            c = D._texto_de(msgs[-1].content)
            return ("Guincho acionado ✅" if "ACIONAMENTO REAL" in c else _linha_do_retorno(c)), []
        h = [D._texto_de(m.content) for m in msgs if D._tipo(m) == "human"][-1].lower()
        if "pode mandar" in h:
            return "", _call("insurer_dispatch", {**args, "dados_confirmados": True})
        if "rua nove" in h:
            return "", _call("insurer_dispatch", {**args, "dados_confirmados": False})
        if "bela vista" in h:
            return "Quer tentar o socorro mecânico aí mesmo, ou prefere o guincho?", []
        return "Me diz o endereço da garagem e para onde levo o carro.", []

    from test_spec125_endurecimento import _cenario

    def rodar(max_turnos):
        cen = {**_cenario("C4"), "chave": "conv-teste-u1-c4",
               "roteiro": {"falas_fixas": falas, "max_turnos": max_turnos}}
        return _rodar(_caso(cen), roteiro)[0]

    r = rodar(c4["entrada"]["roteiro"]["max_turnos"])
    efeitos = [e for e in r.rastro.get("efeitos") or [] if e.get("efeito") and not e.get("falha")]
    assert [e["tool"] for e in efeitos] == ["insurer_dispatch"], r.rastro["estado"]["transcricao"]
    r3 = rodar(3)                                            # CONTROLE: o teto antigo
    assert not [e for e in r3.rastro.get("efeitos") or [] if e.get("efeito") and not e.get("falha")]


# ===========================================================================
# (e) C11 — o cliente SEMEADO pelo telefone, lido pelo motor do produto
# ===========================================================================
def _semeado(c11, company_id, telefone):
    banco = D.SupabaseDuble()
    ent = c11["entrada"]
    conversa = B._semear_banco(banco, ent, company_id=company_id,
                               sessao=f"whatsapp:{telefone}:{company_id}:ag", user_id="u-c11",
                               agente={"id": "ag", "company_id": company_id}, corretora="X", telefone=telefone)
    # a 1ª fala de HOJE (o motor grava antes do turno, como o webhook) — abre o assunto novo
    B._gravar_mensagem(banco, conversa, company_id, "user", "oi, preciso de um chaveiro")
    return banco


def test_e_o_c11_semeado_e_achado_pelo_telefone_como_o_produto_acha():
    """`quem_e_o_segurado` REAL sobre o banco-dublê semeado: nome do contato + o CPF pelo FINAL
    (assunto de 20 dias atrás → X2: confirma antes de usar). E o bloco do prompt sai."""
    from app.agents.quem_e_o_segurado import bloco_para_o_prompt, quem_e_o_segurado

    c11 = _cen("C11")
    empresa = B.TENANTS["A"]
    fone = re.sub(r"\D", "", c11["entrada"]["telefone"])
    cpf = re.sub(r"\D", "", c11["entrada"]["fatos"]["cpf"]["valor"])
    quem = asyncio.run(quem_e_o_segurado(empresa, fone, db=_semeado(c11, empresa, fone)))
    assert quem["nome"] == c11["entrada"]["nome"].split()[0] and quem["cpf_final"] == cpf[-4:], quem
    assert quem["cpf"] == ""                    # X2: o de outro assunto só pelo final
    bloco = bloco_para_o_prompt(quem)
    assert f"final {cpf[-4:]}" in bloco and cpf not in bloco


def test_e_controle_outra_corretora_e_sem_telefone_nao_acham_nada():
    from app.agents.quem_e_o_segurado import quem_e_o_segurado

    c11 = _cen("C11")
    fone = re.sub(r"\D", "", c11["entrada"]["telefone"])
    banco = _semeado(c11, B.TENANTS["A"], fone)
    outra = asyncio.run(quem_e_o_segurado(B.TENANTS["B"], fone, db=banco))       # 🔴 §7: dois tenants
    assert not outra.get("nome") and not outra.get("cpf_final"), outra
    sem = asyncio.run(quem_e_o_segurado(B.TENANTS["A"], fone, db=_semeado(c11, B.TENANTS["A"], "")))
    assert not sem.get("nome") and not sem.get("cpf_final"), sem


# ===========================================================================
# (f) C8 — a pessoa que o segurado ACEITOU depois da oferta
# ===========================================================================
def test_f_o_c8_do_sol_da_u0_a_pessoa_aceita_nao_e_falha():
    """📊 U0: "Quer que eu peça à nossa equipe para cobrar a seguradora agora?" → "Pede agora, por
    favor" → pessoa. O v2 manda exatamente isso (ACOMPANHAR: OFEREÇA; chame-a se ele aceitar)."""
    r = _gravado(U0_SOL_OUTROS, "C8")
    assert not [v for v in r["vereditos"] if v["evaluator_slug"] == "pessoa_na_regra"][0]["passou"]  # antes
    ch = B.checagens_da_conversa(_cen("C8"), _saida_gravada(r))
    assert ch["pessoa_na_regra"]["passou"] is True and ch["pessoa_na_regra"]["aceitas"] == [2]


def test_f_controle_a_pessoa_sem_oferta_do_c13_do_sol_continua_vermelha():
    for t in (1, 2):
        r = _gravado(U0_SOL_CRIT, "C13", t)
        assert B.checagens_da_conversa(_cen("C13"), _saida_gravada(r))["pessoa_na_regra"]["passou"] is False


@pytest.mark.parametrize("resposta,aceita", [
    ("Pede agora, por favor", True), ("quero sim", True), ("pode ser, cobra eles", True),
    ("quero falar com uma pessoa", True),
    ("não precisa, vou esperar", False), ("e quanto tempo falta?", False), ("ok", True)])
def test_f_aceite_frase_a_frase(resposta, aceita):
    c8 = _cen("C8")
    trans = [_t(1, ["cade o guincho??"], "Consta designado, sem previsão. Quer que eu peça à nossa equipe "
                                        "para cobrar a seguradora agora?"),
             _t(2, [resposta], "Pedi à equipe.", ["request_human_agent"], [{"reason": "cobrar"}])]
    passou = B.checagens_da_conversa(c8, _saida(trans, {"request_human_agent": 1}))["pessoa_na_regra"]["passou"]
    assert passou is aceita, resposta


@pytest.mark.parametrize("fala,pediu", [
    ("ué, então como faço pra achar uma loja credenciada? consegue pedir pra alguém me orientar?", True),  # 📊 R2
    ("quero falar com uma pessoa", True), ("alguém da equipe pode me ajudar?", True),
    ("e a loja, como acho?", False)])                                                        # CONTROLE
def test_f_o_pedido_de_pessoa_sem_oferta(fala, pediu):
    """📊 rodada Luna da U1 (R2 t1): o segurado PEDIU a pessoa com "pedir pra alguém me orientar"."""
    c8 = _cen("C8")
    trans = [_t(1, ["o vidro trincou"], "Abri o atendimento na seguradora."),
             _t(2, [fala], "Avisei a equipe.", ["request_human_agent"], [{"reason": "x"}])]
    passou = B.checagens_da_conversa(c8, _saida(trans, {"request_human_agent": 1}))["pessoa_na_regra"]["passou"]
    assert passou is pediu, fala


def test_f_controle_sem_oferta_o_ok_nao_vira_aceite():
    c8 = _cen("C8")
    trans = [_t(1, ["cade o guincho??"], "Consta designado, sem previsão."),
             _t(2, ["ok"], "Passei à equipe.", ["request_human_agent"], [{"reason": "x"}])]
    assert B.checagens_da_conversa(c8, _saida(trans, {"request_human_agent": 1}))["pessoa_na_regra"]["passou"] is False
