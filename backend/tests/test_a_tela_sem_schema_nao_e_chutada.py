# -*- coding: utf-8 -*-
"""Uma tela sem schema não é chutada — SPEC-092, BLOCO E (o controle).

📊 **P-084-68:** o formulário `1579547063352571` (*"Automóvel - Informar
endereço V2"*, Yelum, 03/08/2026) não foi transcrito. E este é o formulário em
que errar tem endereço: **a resposta dele é para onde o guincho vai.**

## 🔴 O QUE MEDI, E POR QUE A TRANSCRIÇÃO NÃO COUBE AQUI

```
📊 a definição ESTÁ no payload      `data-source` aparece nos 4 formulários
📊 e NÃO é alcançável por JSON      viaja como repr de Python dentro de string
                                    escapada; nenhum caminhante de JSON a acha
📊 `data-source` tem DUAS formas    inline   [{'id':'1','title':'Sim'}]   (HDI)
                                    ligação  '${data.dt_TiposEndereco}'   (Yelum)
                                    a ligação resolve em screenState.data
📊 da tela de endereço recuperei    6 telas · 18 campos · nome e rótulo
                                    ZERO ocorrências de PII na definição
🔴 o que NÃO recuperei              os `id` das opções
```

> **Um componente sem os `id` das opções não pode ser respondido.** Escolher
> "Digitar endereço" exige saber que ela é o id `2` — e o título não o produz.

⚠️ **Por isso a transcrição virou pendência e este arquivo guarda o CONTROLE.**
Entregar meio schema seria pior que nenhum: `montar_resposta_de_flow` trataria
o campo como respondível e o produto mandaria um id inventado para uma tela que
decide **para onde o guincho vai**.

## O que este arquivo guarda, em uma frase

> **O que não se reconhece, não se responde — e se diz por quê.**
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"
PLAYBOOKS_PY = RAIZ / "app" / "services" / "corridor_playbooks.py"


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


M = _carregar("_spec092_motor_e", MOTOR_PY)
PB = _carregar("_spec092_pb_e", PLAYBOOKS_PY)

#: 📊 O formulário da P-084-68 — existe no acervo, não existe no playbook.
FLOW_ENDERECO = "1579547063352571"


def _playbook_yelum():
    return PB.YELUM_AUTO_WHATSAPP_V1


# ---------------------------------------------------------------------------
# 1. A TELA SEM SCHEMA NÃO É RESPONDIDA
# ---------------------------------------------------------------------------

def test_o_formulario_de_ENDERECO_ainda_NAO_tem_schema():
    """📊 A premissa deste arquivo, conferida em vez de suposta.

    ⚠️ 🔴 Este guarda fica VERMELHO no dia em que alguém transcrever a tela — e
    é exatamente o que se quer. Nesse dia, a história acima muda: a pendência
    fecha, e o controle passa a valer para OUTRA tela ainda não capturada
    (`CLAUDE.md` §9.3 — o fato muda, o teste muda com ele).
    """
    assert PB.native_flow(_playbook_yelum(), FLOW_ENDERECO) is None, (
        "a tela de endereço foi transcrita. Ótimo — agora migre este arquivo: "
        "troque o alvo por uma tela que ainda não tenha schema, e feche a "
        "P-084-68 com a prova")


def test_uma_tela_DESCONHECIDA_vira_needs_human_com_motivo():
    """⛔ Gate E, controle: sem schema, o caso vai para uma pessoa **com o
    motivo gravado** — nunca escorrega mudo."""
    sessao = {"state": "ura", "slots": {}}
    interativa = {"kind": "flow",
                  "flow": {"flow_id": FLOW_ENDERECO, "flow_token": "t:1:2",
                           "name": "galaxy_message", "cta": "Informar endereço"}}
    saida = M._responder_formulario_nativo(
        sessao, _playbook_yelum(), "[FORMULARIO NATIVO: Informar endereço]",
        interactive=interativa)
    assert saida is not None, "o formulário desconhecido escorregou como se não fosse um"
    assert saida["state"] == "needs_human", f"estado={saida['state']!r}"
    assert saida["reason"] == "formulario_nativo_desconhecido", (
        f"motivo={saida.get('reason')!r} — sem o motivo certo, quem tria não "
        "sabe que faltou schema, e a pendência nunca é fechada")


def test_o_id_de_opcao_NAO_e_inventado_a_partir_do_titulo():
    """🔴 A regra que impede o dano: `montar_resposta_de_flow` recusa valor que
    não casa opção, em vez de rebaixá-lo para um padrão.

    📊 As respostas do acervo mostram id opaco de servidor
    (`pd-dc-<ts>-<hash>-0`) — **não reconstruível a partir do título**. Um
    produto que "adivinhasse" o id mandaria o guincho para o lugar errado com
    a mesma confiança de quando acerta.
    """
    schema = {
        "flow_id": "9999", "flow_name": "teste",
        "screens": [{"id": "s1", "title": "t", "components": [{
            "name": "rb_Destino", "type": "RadioButtonsGroup",
            "label": "Para onde levar?", "required": True, "slot": "destino",
            "options": [{"id": "1", "title": "Oficina"},
                        {"id": "2", "title": "Residência"}]}]}],
    }
    montado = PB.montar_resposta_de_flow(schema, {"destino": "Concessionária"})
    assert montado["ok"] is False, (
        "um valor que NÃO é nenhuma das opções foi aceito — o produto acabou "
        "de escolher um destino que o segurado não pediu")
    assert montado["params"] is None, "resposta parcial não existe"
    assert "rb_Destino" in montado["missing"]


def test_CONTROLE_o_valor_que_CASA_e_aceito():
    """§9.3 — prove que a recusa acima é sobre o valor, e não sobre tudo.

    Sem esta linha, um montador que recusasse SEMPRE passaria no teste acima e
    o produto nunca responderia formulário nenhum.
    """
    schema = {
        "flow_id": "9999", "flow_name": "teste",
        "screens": [{"id": "s1", "title": "t", "components": [{
            "name": "rb_Destino", "type": "RadioButtonsGroup",
            "label": "Para onde levar?", "required": True, "slot": "destino",
            "options": [{"id": "1", "title": "Oficina"},
                        {"id": "2", "title": "Residência"}]}]}],
    }
    montado = PB.montar_resposta_de_flow(schema, {"destino": "Oficina"})
    assert montado["ok"] is True, f"o valor certo foi recusado: {montado['missing_detail']}"
    assert montado["params"] == {"rb_Destino": "1"}, (
        "a resposta não saiu como ÍNDICE — 📊 a captura mostra que a seguradora "
        "consome o id, nunca o texto da opção")


# ---------------------------------------------------------------------------
# 2. O QUE FALTA, NOMEADO — para a pendência não virar folclore
# ---------------------------------------------------------------------------

def test_as_telas_JA_transcritas_continuam_completas():
    """As três que existem têm opções com id. Se alguma perder, a transcrição
    regrediu e o corredor passa a pausar onde antes respondia."""
    pb = _playbook_yelum()
    for flow_id in ("857030507196739", "3206000179602236", "2887131368288279"):
        schema = PB.native_flow(pb, flow_id)
        assert schema, f"o schema {flow_id} sumiu do playbook da Yelum"
        for _, comp in PB._flow_components(schema):
            if str(comp.get("type", "")).lower().startswith(("radio", "checkbox")):
                opcoes = comp.get("options") or []
                assert opcoes, (
                    f"{flow_id}/{comp['name']} ficou SEM opções — um componente "
                    "de escolha sem opção não pode ser respondido")
                assert all(str(o.get("id", "")).strip() for o in opcoes), (
                    f"{flow_id}/{comp['name']} tem opção sem `id`; o título não "
                    "reconstrói o id")
