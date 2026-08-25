# -*- coding: utf-8 -*-
"""O ensaio: a travessia inteira, e a linha de controle — SPEC-085, BLOCO G.

> **Este arquivo não conserta nada. Ele prova que os outros consertaram.**

Cada bloco tem o guarda dele. O que só este arquivo faz é passar **um caso
inteiro** pelos dez pontos, na ordem, e — 🔴 a metade que importa — passar um
caso que **deu certo** e exigir que nada aconteça.

    §G.2, literal: *"sem esta segunda passada, o ensaio prova só que o sistema
    faz barulho — não que ele distingue."*

## As travas, e o que elas permitem

    ⛔ agentes attendance DESLIGADOS · INSURER_DISPATCH_LIVE FECHADO
    ⛔ nenhuma mensagem sai · nenhuma entrada em portal
    ⛔ só SELECT fora das migrations desta SPEC

Por isso o ensaio é **puro**: ele percorre as funções que decidem
(`decidir_travamento`, `retrato_para_humano`, `status_duravel_da_fase`,
`politica_de_retomada`, `pode_retomar`, `aviso_de_handoff`) sem banco, sem
Redis e sem rede. Os pontos que exigem banco — a linha nascer, sobreviver ao
TTL, e o isolamento entre corretoras — são provados por
`test_acionamento_sobrevive`, que tem o dublê completo.

⚠️ **E o que este arquivo NÃO prova, dito na cara:** o ensaio LIVE contra o
tenant da AMANDUS, com linhas de verdade no banco, **não foi feito** — ele
escreve, e a trava é SELECT. Ele precisa do Founder.

## 🔴 O caminho C entra por igual (§G.1b)

O roteiro roda DUAS vezes: entrando por `missing_slots` (caminho B) e por
`sentinela_stall` (caminho C). Sem a segunda, dá para fechar o ensaio verde
tendo pulado o BLOCO B.0 inteiro — e o caminho C é o único com prova em
produção.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

CPF_FALSO = "529.982.247-25"
FONE_FALSO = "5547988000001"


def _carregar(nome: str, rel: str):
    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services")}
    injetados = [n for n in anteriores if n not in sys.modules]
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location(nome, str(RAIZ / rel))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


M = _carregar("_g_motor", "app/services/insurer_dispatch_service.py")
PII = _carregar("_g_pii", "app/services/pii_da_sessao.py")
ROT = _carregar("_g_router", "app/services/dispatch_router.py")


def _sessao(reason: str, *, dossie_saiu: bool, suporte=None) -> dict:
    """Uma sessão do corredor que deu certo — allianz-residencial, máquina de
    lavar —, travada pelo motivo pedido."""
    s = {
        "case_id": f"wa:{FONE_FALSO}",
        "state": "needs_human",
        "reason": reason,
        "playbook_ref": "allianz-residencial-whatsapp@v1",
        "subservice": "maquina_de_lavar",
        "client_phone": FONE_FALSO,
        "insurer_phone": "551140901444",
        "missing_slots": ["titular_cpf"],
        "retry_count": 0,
        "captured": {},
        "dossier_sent": dossie_saiu,
        "client_notified_handoff": False,
        "mirror_conversation_id": "6f1a0c2e-0000-4000-8000-000000000001",
        "slots": {"titular_cpf": CPF_FALSO, "telefone_contato": FONE_FALSO,
                  "titular_nome": "Fulano de Tal", "eletrodomestico_opcao": "3"},
        "transcript": [{"direction": "out", "text": "oi"}],
    }
    if suporte:
        s["suporte_indisponivel"] = suporte
    return s


# ---------------------------------------------------------------------------
# G.1 — A TRAVESSIA, pelos DOIS caminhos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("caminho,reason", [
    ("B · o corredor de URA", "missing_slots:titular_cpf"),
    ("C · o Vigia (a única com prova em produção)", "sentinela_stall"),
])
def test_a_travessia_inteira(caminho, reason):
    sessao = _sessao(reason, dossie_saiu=True)

    # 2. a linha durável nasce (FASE 0)
    assert ROT.decidir_travamento(sessao["state"], "ura") == "travado", (
        f"[{caminho}] o travamento não vira linha")

    # 3. o CPF nela está mascarado (FASE 1)
    retrato = PII.retrato_para_humano(sessao)
    bruto = json.dumps(retrato, ensure_ascii=False)
    assert CPF_FALSO not in bruto and FONE_FALSO not in bruto, (
        f"[{caminho}] o retrato para humano leva PII")

    # 4. o work_run NÃO diz `completed` (BLOCO A)
    assert M.status_duravel_da_fase(sessao["state"]) == "waiting_input", (
        f"[{caminho}] o travamento sai do banco como sucesso")

    # 6. o segurado ouve a mensagem certa PARA O CASO (BLOCO C)
    assert M.aviso_de_handoff(True) != M.aviso_de_handoff(False)

    # 7. o motivo é classificado (BLOCO D)
    veredito = M.politica_de_retomada(reason)
    assert veredito in (M.RETOMA, M.DIRETO_AO_HUMANO, M.NAO_RETOMA)
    assert veredito != M.RETOMA, (
        f"[{caminho}] `{reason}` foi classificado como retomável — nem "
        "`missing_slots` nem `sentinela_stall` podem tentar de novo sozinhos")

    # e o retrato continua servindo para TRIAR
    for pista in ("allianz-residencial-whatsapp@v1", "maquina_de_lavar"):
        assert pista in bruto, f"[{caminho}] sumiu do retrato: {pista}"
    assert retrato["missing_slots"] == ["titular_cpf"], (
        f"[{caminho}] o retrato não diz QUAIS slots faltaram")


def test_a_mensagem_ao_segurado_muda_com_o_desfecho():
    """§G.1 item 6, e é o ponto do BLOCO C: 'para o caso', não 'sempre'."""
    com = M.aviso_de_handoff(True)
    sem = M.aviso_de_handoff(False)
    assert "colega" in com.lower() and "colega" not in sem.lower()


@pytest.mark.parametrize("estado", ["ausente", "recusado", "envio_falhou"])
def test_sem_destino_o_estado_DIZ_qual_e(estado):
    """§G.1 item 5: *"o suporte é avisado, OU o estado diz que não há destino"*.
    E os três são estados diferentes porque dão instruções diferentes."""
    retrato = PII.retrato_para_humano(_sessao("missing_slots:x", dossie_saiu=False,
                                              suporte=estado))
    assert retrato.get("suporte_indisponivel") == estado, (
        "o estado de suporte não sobrevive ao mascarador — a Fila do BLOCO E "
        "não tem o que ler, e a corretora não descobre que está surda")


# ---------------------------------------------------------------------------
# 🔴 G.2 — A LINHA DE CONTROLE. Sem ela, nada acima prova coisa alguma.
# ---------------------------------------------------------------------------

def test_CONTROLE_o_acionamento_que_DEU_CERTO_nao_produz_nada():
    """📊 A travessia do `work_run e5279497` — allianz-residencial, máquina de
    lavar, 19/08/2026 — o único acionamento ponta a ponta da história do
    produto. 🔴 **NÃO SE REGRIDE DISSO.**

    Nenhuma marca de travamento, nenhum estado de espera, nenhum aviso.
    """
    travessia = ["preparing", "ready_to_send", "ura", "human_phase", "ura",
                 "captured", "monitoring"]
    anterior = ""
    marcas = []
    for fase in travessia:
        if ROT.decidir_travamento(fase, anterior):
            marcas.append(f"{anterior or '(início)'} → {fase}")
        anterior = fase
    assert not marcas, f"o caso que deu certo recebeu marca de travamento: {marcas}"

    # ⚠️ E O QUE ESTE CONTROLE **NÃO** PODE AFIRMAR — errei aqui na primeira
    # escrita, e a medição corrigiu: `monitoring` também é `waiting_input`, e
    # está CERTO. O motor documenta por quê: ali *"o trabalho existe, não
    # terminou, e depende de algo de fora"* — a seguradora ainda vai mandar
    # updates do prestador. `waiting_input` não é sinônimo de travado.
    #
    # 🔴 O que separa um do outro é o `unblock_state`, e é ele que a linha
    # acima já provou estar NULO. O desfecho final, sim, fecha:
    assert M.status_duravel_da_fase("resolvido") == "completed"
    assert M.status_duravel_da_fase("monitoring") == "waiting_input", (
        "`monitoring` deixou de ser espera — o follow-up do prestador depende "
        "de a seguradora falar, e isso é entrada de fora")


def test_CONTROLE_um_caso_bom_nao_tem_o_que_mascarar_nem_o_que_avisar():
    """O retrato de um caso sem PII sai igual ao que entrou — o mascarador
    distingue, não apaga. E não há aviso a mandar."""
    limpo = {"case_id": "sem-pii", "state": "monitoring",
             "playbook_ref": "allianz-residencial-whatsapp@v1",
             "subservice": "maquina_de_lavar",
             "slots": {"eletrodomestico_opcao": "3"}}
    retrato = PII.retrato_para_humano(limpo)
    assert retrato["slots"]["eletrodomestico_opcao"] == "3"
    assert retrato["playbook_ref"] == "allianz-residencial-whatsapp@v1"
    assert ROT.decidir_travamento("monitoring", "captured") is None


def test_CONTROLE_a_travessia_CONSEGUE_produzir_marca():
    """🔴 §9.3. Um `decidir_travamento` que devolvesse sempre `None` faria o
    controle acima passar com o produto inteiro morto."""
    assert ROT.decidir_travamento("needs_human", "ura") == "travado"
    assert ROT.decidir_travamento("ura", "needs_human") == "retomado_pelo_robo"


# ---------------------------------------------------------------------------
# G.4 — o guarda que a SPEC nomeia
# ---------------------------------------------------------------------------

def test_o_guarda_central_saiu_da_quarentena():
    """§G.4: `test_handoff_chega_em_alguem` sai do vermelho, e o relatório diz
    se foi defeito de produto ou asserção vencida.

    📊 Foi **asserção vencida**, nas duas: uma procurava o literal *"Não
    consegui abrir a transferência"* (hoje é a constante `FALHA_DO_HANDOFF`), a
    outra o rótulo *"Últimas mensagens"* (que a reescrita do dossiê de 14/08
    substituiu por `*CONVERSA*`).
    """
    meta = (RAIZ / "tests" / "test_todos_os_guardas_script_rodam.py").read_text(
        encoding="utf-8")
    quarentena = meta.split("QUARENTENA = {", 1)[-1].split("\n}", 1)[0]
    assert '"test_handoff_chega_em_alguem"' not in quarentena, (
        "o guarda central do G.4 voltou para a quarentena")
    assert (RAIZ / "tests" / "test_handoff_chega_em_alguem.py").exists()
