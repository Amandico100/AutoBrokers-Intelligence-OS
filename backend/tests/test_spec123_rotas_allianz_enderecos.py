"""SPEC-123 F6 · Allianz residência — a lista com VÁRIOS endereços.

📊 O defeito (30/09, `handle_insurer_message` sobre as telas reais): a URA manda
o cabeçalho "Por favor, confirme o endereço para atendimento:" e, na bolha
seguinte, a lista. O passo do cabeçalho mandava "1" ANTES de a lista chegar —
com VÁRIOS endereços, o 1º, qualquer que fosse (prestador na casa errada,
CLAUDE.md §9.5 B); com UM endereço, um SEGUNDO "1" saía para a mesma pergunta.

O FIO (motor real; dublê nenhum — o envio é dry-run):
  tela → handle_insurer_message → match_ura_step → render_reply →
  `_endereco_do_caso_na_lista` (lê a tela) → a tecla, ou sem_chute.

Telas: o MOLDE vem do acervo versionado (`96f220ca`, `21610390`: o mascarador trocou
cada endereço por `{ENDERECO}`); os endereços no molde são 💭 FICTÍCIOS, escritos
com a máscara da própria Allianz (`#` = um caractere escondido, 📊 96f220ca).
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

import app.services.corridor_playbooks as CP            # noqa: E402
import app.services.insurer_dispatch_service as D        # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(AQUI, "corpus", "telas_reais", "allianz-residencial.jsonl")
REF = "allianz-residencial-whatsapp@v1"
CABECALHO = "Por favor, confirme o endereço para atendimento:"

# 💭 fictícios, na máscara da Allianz
A1 = "AV ### ##AUGOTT #####, ### - APTO 101 - ####IANÓP#### - SC"
A2 = "R. ##S F##RES, ### - APTO 301 - ####IANÓP#### - SC"
A3 = "R. ##S F##RES, ### - APTO 301 - ####IANÓP#### - SC"     # mesma parte visível
CASO = "Rua das Flores, 120, apto 301, Florianópolis - SC"

SLOTS = {"titular_cpf": "11122233344", "endereco_numero": "120",
         "telefone_contato": "48999998888", "problema_descricao": "tomada em curto",
         "periodo_preferido": "manhã", "risco_confirmado_sem_fumaca": "sim",
         "pessoa_no_local": "Ana", "local_atual": CASO,
         "qual_seguro_opcao": "1"}


def _pb():
    return CP.get_playbook(REF)


def _listas_do_acervo():
    out = []
    for l in open(CORPUS, encoding="utf-8"):
        d = json.loads(l)
        if d["text"].count("{ENDERECO}") >= 2 and "Voltar" in d["text"]:
            out.append((d["session_id"], d["text"]))
    return out


def _molde():
    sid, t = _listas_do_acervo()[0]
    return t


def _com(*enderecos):
    t = _molde()
    for e in enderecos:
        t = t.replace("{ENDERECO}", e, 1)
    return t


def _sessao():
    s = D.new_dispatch_session(case_id="c", company_id="co", playbook_ref=REF,
                               subservice="eletricista", slots=dict(SLOTS))
    s["state"] = "ura"
    return s


def _outs(s, tela):
    antes = len([t for t in s["transcript"] if t["direction"] == "out"])
    s = D.handle_insurer_message(s, tela)
    return s, [t["text"] for t in s["transcript"] if t["direction"] == "out"][antes:]


# ── O FIO ────────────────────────────────────────────────────────────────────
def test_FIO_varios_enderecos_uma_resposta_e_a_do_caso():
    s = _sessao()
    s, o1 = _outs(s, CABECALHO)
    s, o2 = _outs(s, _com(A1, A2, "AV #### #OITEUX ######, 9999 - ####IANÓP#### - SC"))
    assert o1 == [] and o2 == ["2"], (o1, o2)


def test_FIO_um_endereco_uma_resposta_so():
    """CONTROLE: a lista de UM endereço continua com o seu passo — e sai UM '1'."""
    s = _sessao()
    s, o1 = _outs(s, CABECALHO)
    s, o2 = _outs(s, "*1 -* {ENDERECO}\n*2 -* Voltar\n*3 -* Sair")
    assert o1 + o2 == ["1"], (o1, o2)


def test_FIO_duas_opcoes_com_a_mesma_parte_visivel_nao_chuta():
    s = _sessao()
    _outs(s, CABECALHO)
    s, o = _outs(s, _com(A1, A2, A3))
    assert o == [] and "sem_chute" in str(s.get("reason")), s.get("reason")


# ── o passo, pelo MOTOR, sobre as telas do acervo ───────────────────────────
def test_as_listas_do_acervo_casam_o_passo_e_nunca_respondem_1_as_cegas():
    listas = _listas_do_acervo()
    assert len({sid for sid, _ in listas}) >= 2, listas
    for sid, tela in listas:
        p = CP.match_ura_step(_pb(), tela, "eletricista")
        assert p and p["step"] == "escolher_endereco_do_caso", sid
        assert p.get("sem_chute") is True
        # o acervo mascara o endereço inteiro: nada visível → ninguém chuta
        assert CP.render_reply(p, SLOTS)["ok"] is False, sid


def test_CONTROLE_a_lista_de_um_endereco_e_o_cabecalho_nao_casam_o_passo_novo():
    for tela, esperado in (("*1 -* {ENDERECO}\n*2 -* Voltar\n*3 -* Sair", "escolher_endereco_da_lista"),
                           ("*1 -* R. {ENDERECO}\n*2 -* Voltar\n*3 -* Sair", "escolher_endereco_da_lista"),
                           (CABECALHO, "confirmar_endereco")):
        p = CP.match_ura_step(_pb(), tela, "eletricista")
        assert p and p["step"] == esperado, (tela[:30], p and p["step"])
    assert CP.match_ura_step(_pb(), CABECALHO, "eletricista").get("noop") is True


def test_o_formato_casa_so_o_endereco_do_caso():
    tela = _com(A1, A2, "AV #### #OITEUX ######, 9999 - ####IANÓP#### - SC")
    f = CP._endereco_do_caso_na_lista
    assert f(CASO, {}, tela) == "2"
    assert f("Avenida Brasil, 50, Curitiba - PR", {}, tela) is None      # nenhum casa
    assert f("", {}, tela) is None                                     # caso sem endereço
    # número visível divergente (apto 302 x 301) → não casa
    assert f("Rua das Flores, 120, apto 302, Florianópolis - SC", {}, tela) is None


def test_o_passo_novo_nao_colide_fora_das_listas_de_enderecos():
    fora = []
    for l in open(CORPUS, encoding="utf-8"):
        d = json.loads(l)
        p = CP.match_ura_step(_pb(), d["text"], d.get("servico"))
        if p and p["step"] == "escolher_endereco_do_caso":
            linhas = [x for x in d["text"].splitlines() if x.strip()]
            if not ("Voltar" in d["text"] and "Sair" in d["text"] and len(linhas) >= 4):
                fora.append((d["session_id"], d["text"][:50]))
    assert fora == []
