# -*- coding: utf-8 -*-
"""A tela que não aceita texto, e o freio que não disparava.

Dois defeitos medidos em 03/08/2026, os dois na família HDI/Yelum — o MESMO bot
white-label, o MESMO `flow_id`, as MESMAS telas.

F.1 · O formulário nativo trava 100% dos acionamentos recentes
--------------------------------------------------------------
📊 Desde 18/06/2026 a HDI trocou as telas de condição do veículo por um
**WhatsApp Flow** (um aplicativo dentro do WhatsApp). A mensagem que o abre é
sempre a mesma, e ela não tem botão nenhum:

    "Para que a remoção do veículo ocorra sem imprevistos, precisamos entender
     o local e as condições do veículo."

📊 `observed_events` (banco de produção, consultado em 03/08/2026): a frase
aparece **4 vezes** — hdi 18/06, hdi 15/07, hdi 18/07 e yelum 18/07 — e são os 4
acionamentos mais recentes da família. **Todos param nela.** O parser marca
`[FORMULARIO NATIVO]`, o corredor casa o `handoff_trigger` e o caso vira
`needs_human`. Nenhum chegou ao protocolo.

O que faltava não era vontade: era o **schema**. Responder um flow exige o id
exato de cada opção, e ele nunca esteve no corredor. Estava no banco: 📊 o
clique humano de 18/07/2026 (`msg_type='flow_reply'`, `source='live'`) trouxe,
dentro de `wa_flow_response_params.response_message`, o formulário inteiro — 3
telas, 5 componentes, cada opção com id e título.

Este teste prova que o schema virou dado do corredor e que a resposta é montável
por código, **offline**, sem chutar campo nenhum.

F.2 · O freio residencial estava furado pela falta de uma preposição
--------------------------------------------------------------------
A âncora de finalização era literal::

    r"atendimento para agora ou prefere agendar"

📊 A mesma pergunta tem TRÊS redações reais no banco:

    "Você está solicitando o atendimento *para* agora ou prefere agendar…"  hdi 9
    "Você quer o atendimento *para* agora ou prefere agendar…"       hdi 2 · yelum 17
    "Você precisa do atendimento agora ou prefere agendar…"          hdi 1 · yelum 4

A terceira **não tem o "para"**. 📊 A ocorrência da HDI (02/06/2026, sessão
`26c0546f`) é RESIDENCIAL — a mesma sessão traz "Para esse CPF localizamos o
serviço de *ENCANADOR*".

E esse é o único ponto de não-retorno da família: responder Agora/Agendar
**abre o serviço na hora**. Freio furado ali não é um teste que falha — é um
prestador despachado no modo teste.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(RAIZ, "backend")
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


for _nome in ("app", "app.services"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, os.path.join(BACKEND, rel))
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PB = _carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")

HDI_AUTO = "hdi-auto-whatsapp@v1"
YELUM_AUTO = "yelum-auto-whatsapp@v3"
HDI_RESID = "hdi-residencial-whatsapp@v1"
FLOW_ID = "857030507196739"

# ---------------------------------------------------------------------------
# A captura REAL (📊 observed_events, hdi, flow_reply, live, 18/07/2026 21:51Z)
# ---------------------------------------------------------------------------
# O `paramsJSON` que o humano enviou, sem os campos de transporte (`flow_token`
# é da sessão e `wa_flow_response_params` é o eco do schema). É contra ISTO que
# a função é medida: se ela monta outra coisa, ela está errada.
RESPOSTA_REAL = {
    "rb_EmGaragemOuEstacionamento": "1",
    "rb_NivelDaRua": "4",
    "ckb_SituacoesVeiculo": ["nenhuma_opcoes"],
    "rb_InformacoesLocal": "6",
    "rb_Ocupantes": "1",
}

# As TRÊS redações reais do ponto de não-retorno (📊 `observed_events`,
# ILIKE '%prefere agendar%', 03/08/2026). Texto integral, como a URA manda.
AGENDAR_V1 = ("Você está solicitando o atendimento para agora ou prefere agendar para um outro momento?\n"
              "Botão 1: Agora\nBotão 2: Agendar\nBotão 3: Voltar")
AGENDAR_V2 = ("Você quer o atendimento para agora ou prefere agendar para outro momento?\n"
              "Botão 1: Agora\nBotão 2: Agendar\nBotão 3: Voltar")
AGENDAR_V3_SEM_PARA = ("Você precisa do atendimento agora ou prefere agendar para outro momento?\n"
                       "Botão 1: Agora\nBotão 2: Agendar\nBotão 3: Voltar")


def _flow():
    return PB.native_flow(PB.get_playbook(HDI_AUTO), FLOW_ID)


def _campo(flow, nome):
    return next((c for _s, c in PB._flow_components(flow) if c["name"] == nome), None)


def teste_o_schema_mora_no_corredor():
    print("\n[F1] O schema do formulário é DADO do corredor, indexado por flow_id")
    hdi, yelum = PB.get_playbook(HDI_AUTO), PB.get_playbook(YELUM_AUTO)

    checar(FLOW_ID in (hdi.get("native_flows") or {}),
           "HDI declara o flow pelo id 857030507196739")
    checar(FLOW_ID in (yelum.get("native_flows") or {}),
           "Yelum declara o MESMO id")
    # "Um registro, duas referências": `is`, não `==`. Dois dicionários iguais
    # hoje divergem no dia em que a HDI mudar uma opção e alguém editar só um.
    checar(hdi["native_flows"] is yelum["native_flows"],
           "é o MESMO objeto nos dois corredores (`is`), não uma cópia",
           "HDI e Yelum são o mesmo bot white-label — duplicar o schema é criar "
           "dois donos para a mesma verdade")
    checar(PB.native_flow(hdi, FLOW_ID) is PB.native_flow(yelum, FLOW_ID),
           "e `native_flow()` devolve o mesmo schema pelos dois corredores")
    checar(PB.native_flow(hdi, "000000") is None,
           "flow_id desconhecido devolve None (nunca 'o primeiro que houver')")

    flow = _flow()
    telas = [s["id"] for s in flow["screens"]]
    checar(telas == ["scr_SituacaoVeiculo", "scr_InformacoesLocal", "scr_IdentificacaoOcupantes"],
           "as 3 telas, na ordem da captura", str(telas))
    campos = [c["name"] for _s, c in PB._flow_components(flow)]
    checar(campos == ["rb_EmGaragemOuEstacionamento", "rb_NivelDaRua", "ckb_SituacoesVeiculo",
                      "rb_InformacoesLocal", "rb_Ocupantes"],
           "os 5 componentes, na ordem da captura", str(campos))

    # Os ids das opções, um por um: é o que a seguradora lê.
    def ids(nome):
        return [o["id"] for o in _campo(flow, nome)["options"]]

    checar(ids("rb_EmGaragemOuEstacionamento") == ["1", "0"], "garagem: 1=Sim 0=Não")
    checar(ids("rb_NivelDaRua") == ["1", "2", "3", "4"],
           "nível da rua: 1=Subsolo 2=Acima 3=com restrição 4=acesso livre")
    checar(ids("ckb_SituacoesVeiculo") == ["cambio_travado", "veiculo_rebaixado", "veiculo_blindado",
                                           "eletrico_hibrido", "nenhuma_opcoes"],
           "situações do veículo: ids são PALAVRAS, não números")
    checar(ids("rb_InformacoesLocal") == ["6", "2", "3"],
           "local: 6=Seguro 2=escuro 3=pouca circulação (o 6 vem PRIMEIRO na lista real)")
    checar(ids("rb_Ocupantes") == ["2", "3", "4", "5", "6", "1"],
           "ocupantes: 2=Criança 3=Idoso 4=? 5=PcD 6=Cirurgia 1=Nenhuma")

    # 📊 A captura trouxe {"id":"4","title":""}. O título VAZIO ficou vazio.
    # Escrever "Gestante" aqui seria inventar rótulo de menu — o defeito que
    # este repositório proíbe — e ninguém reconferiria depois.
    op4 = next(o for o in _campo(flow, "rb_Ocupantes")["options"] if o["id"] == "4")
    checar(op4.get("title") == "" and op4.get("titulo_ausente") is True,
           "a opção 4 continua SEM título, e marcada como tal",
           "o título veio vazio na única captura que existe")
    checar(all(c.get("required") for _s, c in PB._flow_components(flow)),
           "os 5 campos são `required` no schema real")


def teste_o_caso_completo_reconstroi_a_resposta_real():
    print("\n[F2] Caso completo monta o paramsJSON REAL, id por id")
    flow = _flow()
    # Os slots como o corretor/atendente os coleta — palavras, não ids.
    caso = {
        "veiculo_em_garagem": "sim",
        "veiculo_nivel_rua": "acesso livre",
        "veiculo_situacoes": "nenhuma",
        "local_situacao": "Local Seguro",
        "ocupantes_particularidade": "nenhuma",
    }
    r = PB.montar_resposta_de_flow(flow, caso)
    checar(r["ok"] is True, "monta", str(r["missing"]))
    checar(r["params"] == RESPOSTA_REAL,
           "o objeto é IGUAL ao que o humano enviou em 18/07/2026",
           f"montou {r['params']}")
    checar(list(r["params"].keys()) == list(RESPOSTA_REAL.keys()),
           "e na mesma ordem de campos da captura")
    checar(isinstance(r["params"]["ckb_SituacoesVeiculo"], list),
           "checkbox sai como LISTA; radio sai como string",
           "trocar os dois é resposta malformada")
    checar("flow_token" not in r["params"] and "wa_flow_response_params" not in r["params"],
           "o token da sessão NÃO sai daqui",
           "ele muda a cada conversa — quem injeta é o transporte, no envio")
    checar(r["flow_id"] == FLOW_ID, "a resposta carrega o flow_id que está respondendo")

    # O mesmo caso, escrito por quem já fala em ids do flow: mesmo resultado.
    r2 = PB.montar_resposta_de_flow(flow, dict(RESPOSTA_REAL))
    checar(r2["ok"] and r2["params"] == RESPOSTA_REAL,
           "slots já em id do flow também são aceitos (idempotente)")


def teste_sem_dado_confiavel_ele_recusa():
    print("\n[F3] Campo obrigatório sem valor: RECUSA, e diz o que falta")
    flow = _flow()
    r = PB.montar_resposta_de_flow(flow, {})
    checar(r["ok"] is False, "caso vazio não monta")
    checar(r["params"] is None,
           "e NÃO devolve resposta parcial",
           "formulário meio preenchido despacha o equipamento errado — "
           "é pior que não responder")
    checar("rb_EmGaragemOuEstacionamento" in r["missing"] and "rb_InformacoesLocal" in r["missing"],
           "lista os campos sem padrão", str(r["missing"]))
    checar("ckb_SituacoesVeiculo" not in r["missing"] and "rb_Ocupantes" not in r["missing"],
           "e NÃO lista os que têm padrão seguro")
    det = {d["campo"]: d for d in r["missing_detail"]}
    checar(det["rb_InformacoesLocal"]["pergunta"] == "Qual é a situação do local onde você está?",
           "o detalhe traz a PERGUNTA da seguradora, para o humano responder")
    checar([o["id"] for o in det["rb_InformacoesLocal"]["opcoes"]] == ["6", "2", "3"],
           "e as opções, com id")
    checar(det["rb_InformacoesLocal"]["motivo"] == "sem_valor", "com o motivo escrito")

    # Um campo só faltando ainda é recusa: não existe "quase completo".
    quase = {"veiculo_em_garagem": "não", "veiculo_situacoes": "nenhuma",
             "ocupantes_particularidade": "nenhuma"}
    r2 = PB.montar_resposta_de_flow(flow, quase)
    checar(r2["ok"] is False and r2["params"] is None and r2["missing"] == ["rb_InformacoesLocal"],
           "faltando UM campo, ainda assim recusa", str(r2["missing"]))


def teste_o_padrao_seguro_cobre_ausencia_e_so_ela():
    print("\n[F4] Padrão seguro existe onde não muda equipamento — e não vira rede")
    flow = _flow()
    caso = {"veiculo_em_garagem": "não", "local_situacao": "seguro"}
    r = PB.montar_resposta_de_flow(flow, caso)
    checar(r["ok"] is True, "com garagem e local respondidos, monta", str(r["missing"]))
    checar(r["params"]["rb_Ocupantes"] == "1",
           "ocupantes sem informacao vira 'Nenhuma das anteriores' (1)")
    checar(r["params"]["ckb_SituacoesVeiculo"] == ["nenhuma_opcoes"],
           "situacoes do veiculo sem informacao vira nenhuma_opcoes")
    checar(sorted(r["defaults_used"]) == ["ckb_SituacoesVeiculo", "rb_Ocupantes"],
           "e a resposta declara QUAIS campos saíram de padrão",
           "padrão usado às escondidas é chute com outro nome")

    checar(_campo(flow, "rb_InformacoesLocal").get("default") is None,
           "`rb_InformacoesLocal` NÃO tem padrão — muda a prioridade do atendimento")
    checar(_campo(flow, "rb_NivelDaRua").get("default") is None,
           "`rb_NivelDaRua` NÃO tem padrão — escolhe o EQUIPAMENTO enviado")
    checar(_campo(flow, "rb_EmGaragemOuEstacionamento").get("default") is None,
           "`rb_EmGaragemOuEstacionamento` também não",
           "é ele que decide se o nível da rua chega a ser perguntado; chutá-lo "
           "seria a porta dos fundos da regra acima")

    # A regra que protege quem está na estrada: valor presente e NÃO reconhecido
    # nunca cai no padrão. 📊 'Gestante' é o caso real — o título da opção 4 veio
    # vazio na captura, então a palavra não casa com nada.
    r2 = PB.montar_resposta_de_flow(flow, {**caso, "ocupantes_particularidade": "gestante"})
    checar(r2["ok"] is False, "'gestante' não monta resposta")
    checar("rb_Ocupantes" in r2["missing"],
           "vira FALTANTE",
           "cair no padrão aqui rebaixaria, em silêncio, uma gestante para "
           "'Nenhuma das anteriores'")
    det = {d["campo"]: d for d in r2["missing_detail"]}
    checar(det["rb_Ocupantes"]["motivo"] == "valor_nao_reconhecido"
           and det["rb_Ocupantes"]["valor_recebido"] == "gestante",
           "com o motivo e o valor que chegou, para o humano clicar certo")

    # E o que É reconhecido resolve, sem depender de escrever igual à seguradora.
    r3 = PB.montar_resposta_de_flow(flow, {**caso, "ocupantes_particularidade": "idoso",
                                           "veiculo_situacoes": ["rebaixado", "blindado"]})
    checar(r3["ok"] and r3["params"]["rb_Ocupantes"] == "3", "'idoso' vira 3")
    checar(r3["params"]["ckb_SituacoesVeiculo"] == ["veiculo_rebaixado", "veiculo_blindado"],
           "checkbox aceita várias e traduz cada uma",
           str(r3["params"]["ckb_SituacoesVeiculo"]))


def teste_campo_que_a_tela_nao_mostra_nao_e_exigido():
    print("\n[F5] Visibilidade condicional: só se responde o que a tela mostra")
    flow = _flow()
    # 📊 No JSON real: rb_NivelDaRua tem
    #    visible: `${form.rb_EmGaragemOuEstacionamento} == '1'`
    cond = _campo(flow, "rb_NivelDaRua").get("visible_if") or {}
    checar(cond.get("kind") == "form" and cond.get("field") == "rb_EmGaragemOuEstacionamento"
           and cond.get("equals") == "1",
           "a condição do nível da rua está transcrita do JSON real", str(cond))

    fora = PB.montar_resposta_de_flow(flow, {"veiculo_em_garagem": "não", "local_situacao": "seguro"})
    checar(fora["ok"] is True, "veículo na rua: monta")
    checar("rb_NivelDaRua" not in (fora["params"] or {}),
           "e o nível da rua NÃO entra na resposta",
           "a tela não aparece quando o veículo não está em garagem")
    checar("rb_NivelDaRua" not in fora["missing"],
           "nem entra na lista de faltantes")

    dentro = PB.montar_resposta_de_flow(flow, {"veiculo_em_garagem": "sim", "local_situacao": "seguro"})
    checar(dentro["ok"] is False and "rb_NivelDaRua" in dentro["missing"],
           "veículo em garagem: aí sim o nível é obrigatório", str(dentro["missing"]))

    # Garagem desconhecida = visibilidade INDETERMINADA. O caso já está travado
    # pela garagem; pedir o nível junto entrega a pergunta inteira de uma vez.
    indef = PB.montar_resposta_de_flow(flow, {"local_situacao": "seguro"})
    det = {d["campo"]: d for d in indef["missing_detail"]}
    checar("rb_NivelDaRua" in indef["missing"] and det["rb_NivelDaRua"]["condicional"] is True,
           "garagem sem resposta: o nível é pedido, marcado como condicional",
           str(indef["missing"]))


def teste_o_freio_residencial_dispara_nas_tres_variantes():
    print("\n[F6] O ponto de não-retorno é pego nas TRÊS redações reais")
    for ref, rotulo in ((HDI_RESID, "HDI residencial"), (HDI_AUTO, "HDI auto"),
                        (YELUM_AUTO, "Yelum auto")):
        pb = PB.get_playbook(ref)
        for texto, nome in ((AGENDAR_V1, "'está solicitando o atendimento PARA agora'"),
                            (AGENDAR_V2, "'quer o atendimento PARA agora'"),
                            (AGENDAR_V3_SEM_PARA, "'precisa do atendimento agora' (SEM o 'para')")):
            checar(PB.detect_finalize_anchor(pb, texto) is not None,
                   f"{rotulo}: freia em {nome}",
                   "responder Agora/Agendar ABRE o serviço na hora")

    # E o corredor sabe RESPONDER a mesma tela em modo LIVE — a âncora do passo
    # é a mesma constante, então as três variantes também casam com o passo.
    for texto in (AGENDAR_V1, AGENDAR_V2, AGENDAR_V3_SEM_PARA):
        passo = PB.match_ura_step(PB.get_playbook(HDI_AUTO), texto, subservice="guincho")
        checar((passo or {}).get("step") == "quando_agora",
               f"e o passo `quando_agora` casa: {texto[:34]}…",
               str((passo or {}).get("step")))

    # A frase do Bradesco é OUTRA pergunta, no meio do fluxo (📊 'envie a
    # assistência agora ou prefere agendar' é COLETA, não freio). Afrouxar o
    # 'para' não pode ter atravessado a fronteira do corredor vizinho.
    bradesco = PB.get_playbook("bradesco-auto-whatsapp@v1")
    checar(PB.detect_finalize_anchor(
        bradesco, "E como prefere fazer, quer que envie a assistência agora ou prefere agendar?") is None,
        "e o freio do Bradesco continua NÃO disparando na pergunta de coleta dele",
        "afrouxar uma âncora não pode vazar para o corredor do lado")


def main() -> int:
    print("=" * 68)
    print("FORMULARIO NATIVO — RESPONDER O APP, E FREAR ANTES DE ABRIR")
    print("=" * 68)
    for t in (teste_o_schema_mora_no_corredor,
              teste_o_caso_completo_reconstroi_a_resposta_real,
              teste_sem_dado_confiavel_ele_recusa,
              teste_o_padrao_seguro_cobre_ausencia_e_so_ela,
              teste_campo_que_a_tela_nao_mostra_nao_e_exigido,
              teste_o_freio_residencial_dispara_nas_tres_variantes):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O CORREDOR RESPONDE O FORMULARIO, RECUSA O INCOMPLETO E FREIA A TEMPO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
