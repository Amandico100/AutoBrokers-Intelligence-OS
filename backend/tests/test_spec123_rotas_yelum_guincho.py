"""SPEC-123 F6 · yelum/auto/guincho — a assistência aberta nas últimas 72 h.

O FIO, elo a elo, pelo MOTOR (CLAUDE.md §9.4 — nada de regex próprio):

```
tela real da URA (acervo versionado, ou a cópia datada abaixo)
  → insurer_dispatch_service.handle_insurer_message
      → corridor_playbooks.match_ura_step       acompanhar_identificacao / acompanhar_qual_solicitacao
      → render_reply → _identificador_do_caso / _solicitacao_do_caso_na_lista
  → a tela seguinte ("A solicitação de GUINCHO está concluída") → handoff (SPEC-120)
```

📊 Antes (30/09, `simular_corredor.py --todas`): yelum/auto/guincho = FALTA CAPTURA,
2 telas órfãs, ambas da sessão `75400aad` (as duas telas abaixo). Depois: ATENDE
SOZINHO.

⚠️ As duas telas de `75400aad` vêm ESCRITAS aqui (cópia do acervo versionado no
commit 80f1234, já mascarada): com a janela de consulta da família
(`zonas_do_acervo`, F6) a regeração trocou a sessão por outras de mesma forma —
`dc1a0808` (a tela do identificador) e `30b3219e` (a das 72 h, com DOIS
guinchos). Essas duas são lidas do acervo; a de `75400aad` é a única com
`GUINCHO` + `MTA`, que prova a escolha positiva.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "scripts"))

os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

import app.services.corridor_playbooks as CP            # noqa: E402
import app.services.insurer_dispatch_service as D        # noqa: E402
import zonas_do_acervo as Z                              # noqa: E402

CORPUS = os.path.join(AQUI, "corpus", "telas_reais")
REF = "yelum-auto-whatsapp@v3"

# 📊 yelum 75400aad (28/04), acervo versionado em 80f1234 — mascarada.
TELA_IDENTIFICADOR = ("Para seguir, por favor me informe o número da sua *assistência*, "
                      "*placa* ou *CPF*.")
TELA_72H = ("{NOME} - {CORRETORA}, identifiquei que a assistência *{NUMERO}* foi aberta "
            "dentro das últimas 72h. Selecione abaixo sobre qual solicitação você quer "
            "falar:\nGUINCHO\nSolicitação: {VALOR}\nMTA - MEIO DE TRANSPORTE\n"
            "Solicitação: {VALOR}")
TELA_CONCLUIDA = ("A solicitação de *GUINCHO* está concluída.\n\nPor favor, selecione abaixo "
                  "o assunto que você deseja falar.\nQuestionar atraso\nSelecione esta opção "
                  "se o GUINCHO ainda não chegou para te atender.\nQuestionar entrega\n"
                  "Selecione esta opção se precisa de informação sobre a entrega do veiculo\n"
                  "Alterar endereço\nSelecione esta opção se deseja informar um novo "
                  "endereço de destino.\nOutro\nVoltar\nEncerrar conversa")

SLOTS = {"titular_cpf": "11122233344", "veiculo_placa": "ABC1D23",
         "local_atual": "Rua Um, 10, Centro, Canoas - RS", "problema_descricao": "não liga",
         "quando": "agora", "telefone_contato": "51999990000",
         "local_destino": "Rua Dois, 20, Canoas - RS", "veiculo_em_garagem": "não",
         "situacao_risco_opcao": "Nenhuma das anteriores", "pessoa_no_local": "Ana"}


def _pb():
    return CP.get_playbook(REF)


def _telas(seguradora_ramo: str, sid: str):
    with open(os.path.join(CORPUS, seguradora_ramo + ".jsonl"), encoding="utf-8") as fh:
        return [json.loads(l)["text"] for l in fh
                if l.strip() and json.loads(l)["session_id"] == sid]


def _sessao(sub: str):
    s = D.new_dispatch_session(case_id="c", company_id="co", playbook_ref=REF,
                               subservice=sub, slots=dict(SLOTS))
    s["state"] = "ura"
    return s


def _responder(s, tela):
    antes = len([t for t in s["transcript"] if t["direction"] == "out"])
    s = D.handle_insurer_message(s, tela)
    return s, [(t["text"], t.get("step")) for t in s["transcript"] if t["direction"] == "out"][antes:]


# ── O FIO ────────────────────────────────────────────────────────────────────
def test_FIO_o_guincho_com_assistencia_recente_chega_a_pessoa_sem_tela_calada():
    s = _sessao("guincho")
    s, o1 = _responder(s, TELA_IDENTIFICADOR)
    assert o1 == [("ABC1D23", "acompanhar_identificacao")]
    s, o2 = _responder(s, TELA_72H)
    assert o2 == [("GUINCHO", "acompanhar_qual_solicitacao")]
    s, o3 = _responder(s, TELA_CONCLUIDA)
    assert o3 == [] and s["state"] == "needs_human"
    assert str(s.get("reason") or "").startswith("handoff_trigger:")


def test_CONTROLE_servico_do_caso_fora_da_lista_nao_chuta():
    """Bateria numa lista GUINCHO/MTA: ninguém escolhe a solicitação de outro."""
    s = _sessao("bateria")
    s, _ = _responder(s, TELA_IDENTIFICADOR)
    s, o = _responder(s, TELA_72H)
    assert o == []
    assert s["state"] == "needs_human" and "sem_chute" in str(s.get("reason"))


# ── os passos, pelo MOTOR, sobre o acervo VERSIONADO ─────────────────────────
def test_a_tela_do_identificador_do_acervo_casa_o_passo_e_responde_a_placa():
    tela = [t for t in _telas("yelum-auto", "dc1a0808") if "número da sua" in t]
    assert tela, "a tela do identificador saiu do acervo"
    passo = CP.match_ura_step(_pb(), tela[0], "guincho")
    assert passo and passo["step"] == "acompanhar_identificacao"
    assert CP.render_reply(passo, SLOTS) == {"ok": True, "missing": [], "reply": "ABC1D23"}


def test_a_lista_com_DOIS_guinchos_iguais_do_acervo_vira_sem_chute():
    """📊 30b3219e: 'GUINCHO / GUINCHO' — duas solicitações com o mesmo nome."""
    tela = [t for t in _telas("yelum-auto", "30b3219e") if "72h" in t]
    assert tela
    passo = CP.match_ura_step(_pb(), tela[0], "guincho")
    assert passo and passo["step"] == "acompanhar_qual_solicitacao" and passo.get("sem_chute")
    slots = {**SLOTS, "assistencia_aberta_opcao": "GUINCHO"}
    assert CP.render_reply(passo, slots)["ok"] is False


def test_CONTROLE_as_telas_vizinhas_nao_casam_os_passos_novos():
    novos = {"acompanhar_identificacao", "acompanhar_qual_solicitacao"}
    for vizinha in ("Para começar, me informe somente o *CPF ou CNPJ* do títular da apólice.",
                    "Por favor, me informe o seu nome ou como gostaria de ser chamado.",
                    TELA_CONCLUIDA,
                    "{NOME} identifiquei que a assistência *{NUMERO}* está aberta."):
        p = CP.match_ura_step(_pb(), vizinha, "guincho")
        assert not p or p["step"] not in novos, (vizinha[:40], p and p["step"])


def test_os_passos_novos_nao_colidem_com_nenhuma_outra_tela_do_acervo():
    """Varredura dos 16 corpora: os dois passos só casam as DUAS formas de tela."""
    novos = {"acompanhar_identificacao", "acompanhar_qual_solicitacao"}
    fora = []
    for nome in sorted(os.listdir(CORPUS)):
        if not nome.endswith(".jsonl"):
            continue
        seg, ramo = nome[:-6].split("-", 1)
        ref = CP.resolve_playbook_ref(seg, ramo)
        pb = CP.get_playbook(ref) if ref else None
        if not pb:
            continue
        for l in open(os.path.join(CORPUS, nome), encoding="utf-8"):
            d = json.loads(l)
            p = CP.match_ura_step(pb, d["text"], d.get("servico"))
            if p and p["step"] in novos:
                forma = ("número da sua *assistência*" in d["text"]
                         or "foi aberta dentro das últimas 72h" in d["text"])
                if not forma:
                    fora.append((nome, d["session_id"], d["text"][:50]))
    assert fora == []


# ── a janela de consulta da família (zonas_do_acervo) ────────────────────────
def _ev(seq):
    return [{"direction": d, "text": t} for d, t in seq]


def test_a_janela_da_familia_tira_a_consulta_e_deixa_a_porta():
    ev = _ev([("in", TELA_IDENTIFICADOR), ("out", "{PLACA}"), ("in", TELA_72H),
              ("out", "GUINCHO"), ("in", TELA_CONCLUIDA), ("out", "Outro"),
              ("in", "{NOME}, identificamos que você deseja falar sobre seu atendimento de Guincho.")])
    dentro = Z.consulta_de_pedido_existente(ev, "yelum")
    assert 2 not in dentro and 0 not in dentro          # a porta e o identificador ficam
    assert {4, 6} <= dentro                              # a consulta sai


def test_CONTROLE_pedir_outro_servico_fecha_a_janela_da_familia():
    abertura = "Pode me dizer o que aconteceu? Para isso *selecione* uma das opções."
    ev = _ev([("in", TELA_CONCLUIDA.replace("Questionar atraso", "Pedir outro serviço\nQuestionar atraso")),
              ("out", "Pedir outro serviço"), ("in", abertura)])
    dentro = Z.consulta_de_pedido_existente(ev, "hdi")
    assert 0 in dentro and 2 not in dentro


def test_o_acervo_regerado_nao_tem_mais_a_tela_concluida():
    """O gerador oficial rodou com a janela: a tela de acompanhamento saiu."""
    for nome in ("yelum-auto.jsonl", "hdi-auto.jsonl"):
        textos = [json.loads(l)["text"] for l in open(os.path.join(CORPUS, nome), encoding="utf-8")]
        assert not [t for t in textos if "está concluída" in t and "A solicitação de" in t], nome


def test_o_simulador_da_ATENDE_SOZINHO_para_yelum_auto_guincho():
    import regua_motor as M
    import simular_corredor as SC
    rota = [r for r in M.rotas() if (r.seguradora, r.ramo, r.servico) == ("yelum", "auto", "guincho")]
    sim = SC.simular_todas(rota)[0]
    assert (sim.faixa, len(sim.replay.orfas_funcionais)) == (SC.FAIXA_ATENDE, 0), sim.motivo
