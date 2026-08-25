# -*- coding: utf-8 -*-
"""O `flow_id` ecoado é o da SEGURADORA — SPEC-092, BLOCO C.

📊 **P-084-69, e agora medido campo a campo (25/08/2026):** o MESMO formulário
tem id diferente em cada marca, e os campos são idênticos.

```
hdi   857030507196739   ckb_SituacoesVeiculo | rb_EmGaragemOuEstacionamento
                        | rb_InformacoesLocal | rb_NivelDaRua | rb_Ocupantes
yelum 3206000179602236  ckb_SituacoesVeiculo | rb_EmGaragemOuEstacionamento
                        | rb_InformacoesLocal | rb_NivelDaRua | rb_Ocupantes
```

🔴 **Um registro só, apontado pelos dois playbooks** — de propósito, para não
divergirem. E é isso que faz `montar_resposta_de_flow` devolver **sempre o id da
HDI**, inclusive respondendo à Yelum.

> **Se a Yelum validar, a resposta é descartada SEM ERRO, sem log, e a janela de
> 12 minutos queima com o segurado esperando.**

## 🔴 O CONTROLE É METADE DESTE ARQUIVO

A §Gate C é explícita: *"montar para HDI e Yelum e provar que os ids DIFEREM —
se saírem iguais, o bug está vivo e o teste não o vê."* Um teste que só
afirmasse *"a moldura tem flow_id"* ficaria verde com o defeito inteiro de pé.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"


def _carregar(nome: str, caminho: Path):
    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services")}
    injetados = [n for n in anteriores if n not in sys.modules]
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location(nome, str(caminho))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


M = _carregar("_spec092_motor_c", MOTOR_PY)

#: 📊 Os ids REAIS, medidos no acervo.
ID_HDI = "857030507196739"
ID_YELUM = "3206000179602236"
ID_YELUM_REDUZIDO = "2887131368288279"

#: O que `montar_resposta_de_flow` devolve — sempre o id do SCHEMA, que é o da
#: HDI, porque os dois playbooks apontam para o MESMO objeto.
MONTADO = {"flow_id": ID_HDI,
           "flow_name": "Automóvel - Detalhes do atendimento V2"}


def _sessao(flow_id_ativo: str, cta: str = "Informar condições") -> dict:
    return {"flow_id_ativo": flow_id_ativo, "flow_cta": cta}


# ---------------------------------------------------------------------------
# 1. O ECO
# ---------------------------------------------------------------------------

def test_responder_a_YELUM_ecoa_o_id_da_YELUM():
    moldura = M._moldura_da_resposta(_sessao(ID_YELUM), MONTADO)
    assert moldura["flow_id"] == ID_YELUM, (
        f"respondendo à Yelum, o produto ecoou {moldura['flow_id']!r} — é o id "
        "da HDI, e a Yelum descarta em silêncio")


def test_responder_a_HDI_ecoa_o_id_da_HDI():
    moldura = M._moldura_da_resposta(_sessao(ID_HDI), MONTADO)
    assert moldura["flow_id"] == ID_HDI


def test_CONTROLE_GATE_C_os_dois_ids_SAEM_DIFERENTES():
    """⛔ O controle que a §Gate C exige, escrito como ela pede.

    🔴 Se os dois saírem iguais, o defeito está vivo e nenhum teste acima o vê:
    os dois passariam com um produto que ecoasse sempre a mesma coisa, desde
    que essa coisa fosse o id certo por acaso.
    """
    hdi = M._moldura_da_resposta(_sessao(ID_HDI), MONTADO)["flow_id"]
    yelum = M._moldura_da_resposta(_sessao(ID_YELUM), MONTADO)["flow_id"]
    assert hdi != yelum, (
        f"HDI e Yelum saíram com o MESMO id ({hdi!r}) — a moldura voltou a "
        "sair do schema herdado, e o defeito da P-084-69 está de pé")
    assert {hdi, yelum} == {ID_HDI, ID_YELUM}


def test_o_TERCEIRO_formulario_da_yelum_tambem_ecoa_o_seu():
    """📊 `2887131368288279` é o mesmo formulário SEM a tela do veículo — dois
    campos em vez de cinco. Ele existe no acervo duas vezes (07 e 17/08)."""
    moldura = M._moldura_da_resposta(_sessao(ID_YELUM_REDUZIDO), MONTADO)
    assert moldura["flow_id"] == ID_YELUM_REDUZIDO


# ---------------------------------------------------------------------------
# 2. O TÍTULO — a quarta chave que a captura tem e o produto não mandava
# ---------------------------------------------------------------------------

def test_o_title_e_ECOADO_do_convite():
    """📊 A captura real da HDI traz `wa_flow_response_params` com QUATRO
    chaves: `flow_id`, `flow_name`, `response_message` e `title`. O produto
    mandava duas.

    O `title` é o rótulo do botão que abriu o formulário, e ele chega no
    convite como `flow_cta`. Ecoar é de graça; inventar seria adivinhar.
    """
    moldura = M._moldura_da_resposta(_sessao(ID_HDI, "Informar condições"), MONTADO)
    assert moldura.get("title") == "Informar condições"


def test_sem_cta_no_convite_o_title_NAO_e_inventado():
    """⛔ Nada se adivinha. Sem o rótulo no convite, o campo simplesmente não vai."""
    moldura = M._moldura_da_resposta(_sessao(ID_HDI, ""), MONTADO)
    assert "title" not in moldura, (
        "o produto inventou um título — e um rótulo errado é indistinguível de "
        "um certo até a seguradora descartar")


def test_o_response_message_continua_FORA_e_isso_e_deliberado():
    """⚠️ 📊 São 4.854 caracteres de eco das telas, e ninguém mediu se a
    seguradora exige. Mandar um campo grande INVENTADO é pior que omitir um que
    talvez seja decoração."""
    moldura = M._moldura_da_resposta(_sessao(ID_HDI), MONTADO)
    assert "response_message" not in moldura, (
        "alguém passou a mandar `response_message` — se foi por medição, "
        "troque este guarda e escreva a medição no lugar dele")


# ---------------------------------------------------------------------------
# 3. OS DESFECHOS DEGENERADOS
# ---------------------------------------------------------------------------

def test_sem_id_no_convite_cai_no_SCHEMA_em_vez_de_ir_vazio():
    """Convite sem `flow_id` acontece: 📊 `detect_native_flow` existe justamente
    para o caso em que só o corpo chegou. Aí o schema é a melhor informação que
    existe — melhor que campo vazio."""
    moldura = M._moldura_da_resposta({"flow_cta": "x"}, MONTADO)
    assert moldura["flow_id"] == ID_HDI


def test_moldura_TOTALMENTE_vazia_vira_None():
    """`montar_nfm_reply` só acrescenta a moldura `if flow_response_params`. Um
    dicionário vazio ali viraria uma chave vazia no `paramsJSON`, e o payload é
    comparado byte a byte."""
    assert M._moldura_da_resposta({}, {}) is None


def test_CONTROLE_a_moldura_CONSEGUE_ficar_diferente():
    """§9.3 — prove que a função distingue. Uma que devolvesse sempre o mesmo
    dicionário passaria em metade dos testes acima."""
    saidas = {
        tuple(sorted((M._moldura_da_resposta(_sessao(i, c), MONTADO) or {}).items()))
        for i, c in ((ID_HDI, "a"), (ID_YELUM, "b"), (ID_YELUM_REDUZIDO, "c"))
    }
    assert len(saidas) == 3, f"a moldura não distingue as entradas: {len(saidas)}"
