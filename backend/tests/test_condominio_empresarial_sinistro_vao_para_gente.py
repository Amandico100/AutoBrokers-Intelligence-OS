# -*- coding: utf-8 -*-
"""BATERIA 5 — condomínio · empresarial · sinistro vão a uma PESSOA, com dossiê.

> ## 🧑 O Founder, 27/09/2026: *"esses três nunca são tentados sozinhos."*

E o robô os tentava. 📊 Medido em 27/09/2026 com
`python backend/scripts/simular_corredor.py --bateria-5`, sobre as telas REAIS do
acervo versionado:

```
menu_qual_seguro_tres_opcoes   allianz-residencial, sessões c6b63f95 e be8e3f8d
   com a apólice de condomínio no caso, `qual_seguro_opcao` nasce "Condomínio"
   (`new_dispatch_session` → `rotulo_do_ramo_da_apolice`), `resolver_tecla`
   traduzia para "2" e o robô SEGUIA — para dentro do galho de áreas comuns
cnpj_condominio                respondia `{titular_cnpj}` sozinho na tela que
   PROVA que o caso é de áreas comuns
```

⚠️ **O defeito não era a tecla errada.** O "2" estava certo, e havia teste
provando que estava (`test_o_menu_numerado_recebe_numero`). 🔴 O defeito é que a
regra do Founder é sobre o CASO: um chamado de áreas comuns tem cobertura,
prestador e responsável diferentes. Uma tecla certa que abre o chamado errado é o
CLAUDE.md §9.5 pela nona vez.

## O que este arquivo prova

```
[1] CONDOMÍNIO · EMPRESARIAL     o MOTOR para, na tela REAL, com o CASO real
[2] SINISTRO                     as telas que PEDEM algo sobre sinistro param
[3] O DOSSIÊ                     tem o que a pessoa precisa, em português, e
                                 ZERO nome de chave
[4] O SEGURADO                   ouve uma frase de gente, e ela não promete
                                 pessoa que não existe
[5] AS LINHAS DE CONTROLE        a apólice RESIDENCIAL segue sozinha · a
                                 pergunta do PRÉDIO não é a da apólice · o menu
                                 que só LISTA sinistro não para
```

🔴 **[5] é o que dá direito à conclusão** (CLAUDE.md §9.2). Sem ela, uma trava que
mandasse TUDO para uma pessoa passaria em [1] a [4] — e tiraria o produto do ar.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")

from app.services import corridor_playbooks as CP   # noqa: E402
from app.services import insurer_dispatch_service as D  # noqa: E402

CORPUS = RAIZ / "tests" / "corpus" / "telas_reais"
REF_RESID = "allianz-residencial-whatsapp@v1"


def telas(nome: str):
    with open(CORPUS / f"{nome}.jsonl", encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def uma_tela(nome: str, padrao: str, extra: str = ""):
    """A primeira tela REAL do acervo que casa o padrão, com o `session_id`."""
    for l in telas(nome):
        n = CP._norm(l["text"])
        if re.search(padrao, n, re.IGNORECASE | re.DOTALL) and (
                not extra or re.search(extra, n, re.IGNORECASE | re.DOTALL)):
            return l
    return None


#: 🔴 Os slots de um caso residencial COMPLETO — o que faz a conversa chegar à
#: tela da apólice de verdade. Nada de PII: são valores de teste (§13.9).
SLOTS_BASE = {
    "titular_cpf": "11122233344", "telefone_contato": "48900000000",
    "problema_descricao": "vazamento na coluna", "endereco_numero": "100",
    "periodo_preferido": "tarde", "titular_cnpj": "11222333000144",
}


def sessao(**extra):
    s = D.new_dispatch_session(case_id="b5", company_id="co-b5",
                               playbook_ref=REF_RESID, subservice="encanador",
                               slots={**SLOTS_BASE, **extra})
    s["state"] = "ura"
    return s


def saidas(s):
    return [t["text"] for t in s["transcript"] if t["direction"] == "out"]


# ═════════════════════════════════════════════════════════════════════════════
# [1] CONDOMÍNIO E EMPRESARIAL — o motor para, na tela real, com o caso real
# ═════════════════════════════════════════════════════════════════════════════

TELA_APOLICE = uma_tela("allianz-residencial", r"qual seguro deseja utilizar",
                        r"condominio")
TELA_CNPJ_AREAS_COMUNS = uma_tela("allianz-residencial",
                                  r"exclusivamente a servicos nas[\s\S]{0,4}areas comuns")


def test_o_acervo_tem_as_telas_pelo_id():
    """📊 CONTROLE ZERO: sem a tela real, tudo abaixo mediria imaginação."""
    assert TELA_APOLICE, "a tela que ESCOLHE a apólice saiu do acervo"
    assert TELA_CNPJ_AREAS_COMUNS, "a tela do CNPJ do galho de condomínio saiu do acervo"
    assert len(D.opcoes_numeradas(TELA_APOLICE["text"])) == 3, \
        f"a tela da apólice deixou de ter 3 opções: {D.opcoes_numeradas(TELA_APOLICE['text'])}"


@pytest.mark.parametrize("ramo_da_apolice,rotulo", [
    ("Condomínio", "Condomínio"),
    ("condominio", "Condomínio"),
    ("Empresarial", "Empresarial"),
    ("empresa", "Empresarial"),
])
def test_a_apolice_de_areas_comuns_para_o_robo(ramo_da_apolice, rotulo):
    """🔴 O caso é de condomínio/empresa → NADA sai, e uma pessoa assume.

    ⚠️ O `ramo_da_apolice` é o caminho REAL: `new_dispatch_session` traduz o ramo
    da apólice para o rótulo do menu (`rotulo_do_ramo_da_apolice`). Passar
    `qual_seguro_opcao` à mão mediria meio caminho.
    """
    s = D.handle_insurer_message(sessao(ramo_da_apolice=ramo_da_apolice),
                                 TELA_APOLICE["text"])
    assert saidas(s) == [], f"o robô respondeu {saidas(s)} a um caso de {rotulo}"
    assert s["state"] == "needs_human", s["state"]
    assert s["reason"] == "apolice_de_condominio_ou_empresa", s["reason"]


def test_o_motor_LEU_o_menu_antes_de_parar():
    """🔴 Parar não é desistir: o motor sabe QUAL opção era, e diz qual.

    Um mapa `{"2": "condomínio"}` acertaria nesta tela e mentiria na de DUAS
    opções em que "1" é *"Residência, Condomínio ou Empresa"* — que existe no
    mesmo corredor (`menu_qual_seguro`). O rótulo sai da TELA.
    """
    passo = next(p for p in CP.get_playbook(REF_RESID)["ura_steps"]
                 if p.get("step") == "menu_qual_seguro_tres_opcoes")
    tecla = D.resolver_tecla(CP.get_playbook(REF_RESID), passo,
                             {"slots": {"qual_seguro_opcao": "Condomínio"}},
                             TELA_APOLICE["text"])
    assert tecla["destino"] == "humano"
    assert tecla["rotulo"] == "Condomínio", tecla
    assert tecla["valor"] == "2", ("a tradução da tecla continua certa — é o que "
                                   "prova que a parada é uma DECISÃO, não um erro de "
                                   f"leitura: {tecla}")


def test_a_porta_do_galho_de_areas_comuns_tambem_para():
    """🔴 A segunda porta: a URA pode entrar no galho sem passar pelo menu.

    Ela guarda o documento do último atendimento (ver `cpf_anterior`, cuja 5ª
    tela do acervo diz só `CNPJ` justamente por ser o galho do condomínio).
    """
    s = D.handle_insurer_message(sessao(), TELA_CNPJ_AREAS_COMUNS["text"])
    assert saidas(s) == [], f"o robô respondeu {saidas(s)} à tela de áreas comuns"
    assert s["state"] == "needs_human"
    assert s["reason"].startswith("handoff_trigger:"), s["reason"]


def test_nenhum_passo_responde_a_tela_de_areas_comuns():
    """🔴 E O GUARDA QUE FECHA A PORTA: um passo que casa responde ANTES do
    gatilho (`handle_insurer_message`). Se alguém reescrever `cnpj_condominio`,
    o gatilho volta a ser um guarda atrás de uma porta trancada."""
    passo = CP.match_ura_step(CP.get_playbook(REF_RESID),
                              TELA_CNPJ_AREAS_COMUNS["text"], subservice="encanador")
    assert passo is None or not str(passo.get("reply") or "").strip(), (
        f"🔴 o passo `{(passo or {}).get('step')}` voltou a responder "
        f"{(passo or {}).get('reply')!r} na tela que prova o caso de áreas comuns")


# ═════════════════════════════════════════════════════════════════════════════
# [2] SINISTRO — as telas que PEDEM algo sobre sinistro param
# ═════════════════════════════════════════════════════════════════════════════

SINISTROS_REAIS = [
    # (arquivo, padrão sobre `_norm`, ramo do corredor)
    ("mapfre-auto", r"o que voce gostaria de fazer\?[\s\S]{0,60}abrir sinistro", "auto"),
    ("mapfre-auto", r"abertura de \*?sinistro de automovel", "auto"),
    ("porto-auto", r"preencher o formulario\*? de sinistro", "auto"),
    ("allianz-residencial", r"avisar ou acompanhar um sinistro", "residencial"),
]


@pytest.mark.parametrize("arquivo,padrao,ramo", SINISTROS_REAIS)
def test_a_tela_que_pede_algo_sobre_sinistro_nao_e_respondida(arquivo, padrao, ramo):
    """🔴 Pelo MOTOR, sobre a tela REAL: ou dispara gatilho, ou nada sai."""
    linha = uma_tela(arquivo, padrao)
    assert linha, f"a tela de sinistro saiu de {arquivo}.jsonl"
    seg = arquivo.split("-")[0]
    pb = CP.get_playbook(CP.resolve_playbook_ref(seg, ramo))
    gatilho = CP.detect_handoff_trigger(pb, linha["text"])
    passo = CP.match_ura_step(pb, linha["text"], subservice=linha.get("servico"))
    responde = bool(passo and str(passo.get("reply") or "").strip()
                    and not passo.get("noop"))
    assert gatilho or not responde, (
        f"🔴 {arquivo} sessão {linha['session_id']}: o passo "
        f"`{(passo or {}).get('step')}` responde {(passo or {}).get('reply')!r} a "
        f"uma tela de sinistro, e nenhum gatilho dispara")


# ═════════════════════════════════════════════════════════════════════════════
# [3] O DOSSIÊ — o que a pessoa precisa, em português
# ═════════════════════════════════════════════════════════════════════════════

def _dossie_de_condominio():
    s = D.handle_insurer_message(sessao(ramo_da_apolice="Condomínio"),
                                 TELA_APOLICE["text"])
    return s, D.build_handoff_dossier(s, s.get("reason") or "")


def test_o_dossie_diz_o_que_aconteceu_em_portugues():
    """🔴 A pessoa que abre o cartão tem de saber POR QUE ele chegou nela."""
    _s, dossie = _dossie_de_condominio()
    frase = D.motivo_em_portugues("apolice_de_condominio_ou_empresa")
    assert frase in dossie, f"o motivo não chegou ao dossiê:\n{dossie}"
    for pedaco in ("condomínio", "áreas comuns", "uma pessoa"):
        assert pedaco in frase.lower(), f"a frase não diz {pedaco!r}: {frase}"


def test_o_dossie_leva_os_dados_do_caso_e_o_link():
    """A pessoa não pode ter de reentrevistar o segurado."""
    s, dossie = _dossie_de_condominio()
    assert "ATENDIMENTO PRECISA DE VOCÊ" in dossie
    assert "Dados do caso:" in dossie
    assert SLOTS_BASE["problema_descricao"] in dossie, "o problema não foi junto"
    assert "Serviço:" in dossie and D.rotulo_do_servico("encanador") in dossie
    link = D.link_do_caso(s)
    if link:
        assert link in dossie, "o link do painel não foi junto"


def test_o_dossie_nao_vaza_nome_de_chave():
    """🔴 P-092 de novo: nome interno num cartão lido com o segurado esperando."""
    _s, dossie = _dossie_de_condominio()
    proibidos = ("qual_seguro_opcao", "titular_cnpj", "titular_cpf", "ramo_da_apolice",
                 "apolice_de_condominio_ou_empresa", "needs_human", "_opcao")
    achados = [p for p in proibidos if p in dossie]
    assert not achados, f"nome de chave no dossiê: {achados}\n{dossie}"


def test_o_dossie_imprime_o_telefone_inteiro_e_clicavel():
    """⚠️ MIGRADA EM 28/09/2026 — SPEC-120 D15. Era *"o cartão é reencaminhável e
    fica no histórico do grupo para sempre"*; o Founder decidiu que a atendente
    precisa do número inteiro para tocar e abrir a conversa com o segurado."""
    s, _ = _dossie_de_condominio()
    s["client_phone"] = "5548900000000"
    dossie = D.build_handoff_dossier(s, s.get("reason") or "")
    assert "https://wa.me/5548900000000" in dossie, dossie
    assert D.telefone_curto("5548900000000") not in dossie, "a máscara antiga sobrou"


def test_o_dossie_diz_a_verdade_sobre_o_aviso_ao_segurado():
    """🔴 SPEC-085 B.4: quem lê "já foi avisado" continua de onde parou; quem lê
    "NÃO foi avisado" fala com o segurado primeiro — que é o certo."""
    s, _ = _dossie_de_condominio()
    s["client_notified_handoff"] = False
    assert "AINDA NÃO foi avisado" in D.build_handoff_dossier(s, s["reason"])
    s["client_notified_handoff"] = True
    assert "JÁ foi avisado" in D.build_handoff_dossier(s, s["reason"])


# ═════════════════════════════════════════════════════════════════════════════
# [4] O SEGURADO — a frase que ele ouve é de gente
# ═════════════════════════════════════════════════════════════════════════════

def test_o_segurado_ouve_portugues_de_gente():
    aviso = D.aviso_de_handoff(True)
    assert "colega da equipe" in aviso
    for feio in ("condomínio", "apólice", "handoff", "needs_human", "_opcao",
                 "empresarial", "áreas comuns"):
        assert feio not in aviso.lower(), (
            f"🔴 {feio!r} na frase ao segurado: ele não precisa saber do ramo da "
            f"apólice, e dizer que 'a apólice é de condomínio' soa a recusa")
    assert len(aviso.split()) >= 20, "a frase é curta demais para explicar algo"


def test_o_segurado_nao_ouve_promessa_de_pessoa_que_nao_existe():
    """🔴 CONTROLE: sem dossiê entregue, a frase MUDA — e diz o caminho dele."""
    sem_ninguem = D.aviso_de_handoff(False)
    assert sem_ninguem != D.aviso_de_handoff(True)
    assert "colega" not in sem_ninguem.lower()
    assert "24h" in sem_ninguem or "assistência" in sem_ninguem.lower()


def test_o_caso_de_condominio_vai_direto_ao_humano_e_nao_retoma():
    """Retomar seria desobedecer a regra do dono do produto."""
    assert D.politica_de_retomada("apolice_de_condominio_ou_empresa") == D.DIRETO_AO_HUMANO
    assert not D.pode_retomar({"reason": "apolice_de_condominio_ou_empresa"})


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 [5] AS LINHAS DE CONTROLE — o que TEM de seguir sozinho, e segue
# ═════════════════════════════════════════════════════════════════════════════

def test_controle_a_apolice_residencial_segue_sozinha():
    """🔴 Sem esta linha, uma trava que mandasse TUDO a uma pessoa passaria em
    todos os testes acima — e tiraria `allianz/residencial/*` do ar (9 rotas)."""
    s = D.handle_insurer_message(sessao(ramo_da_apolice="Residencial"),
                                 TELA_APOLICE["text"])
    assert saidas(s) == ["1"], f"a apólice residencial parou: {s.get('reason')}"
    assert s["state"] == "ura"


def test_controle_a_pergunta_do_predio_nao_e_a_da_apolice():
    """🔴 Um apartamento é "condomínio" nesta tela e **Residencial** na apólice.

    📊 As duas redações reais, hdi-residencial 26c0546f · yelum-residencial
    af3b817e: *"Sua residência é uma casa individual ou está localizada em um
    condomínio? Botão 1: Casa Botão 2: Condomínio"*. Tratá-la como a pergunta da
    apólice tiraria `hdi/residencial/*` e `yelum/residencial/*` do ar — 10 rotas
    — para proteger um caso que não existe.
    """
    achou = 0
    for base in ("hdi-residencial", "yelum-residencial"):
        seg, ramo = base.split("-")
        pb = CP.get_playbook(CP.resolve_playbook_ref(seg, ramo))
        for l in telas(base):
            if not re.search(r"casa (?:individual )?ou (?:est[áa]|fica)",
                             CP._norm(l["text"])):
                continue
            achou += 1
            assert CP.detect_handoff_trigger(pb, l["text"]) is None, (
                f"🔴 {base} sessão {l['session_id']}: a pergunta do PRÉDIO virou "
                f"handoff")
            passo = CP.match_ura_step(pb, l["text"], subservice=l.get("servico"))
            assert passo and passo.get("step") == "casa_ou_condominio", (
                f"{base} sessão {l['session_id']}: a tela do prédio perdeu o passo "
                f"— {(passo or {}).get('step')}")
    assert achou >= 2, f"as telas do PRÉDIO saíram do acervo ({achou})"


def test_controle_o_menu_que_so_LISTA_sinistro_continua_respondido():
    """🔴 `corridor_playbooks.py` registra que o gatilho `sinistro` CRU derrubava
    *"mais da metade das sessões boas"*: menus LISTAM "Sinistro" como opção
    vizinha, e isso não significa que o caso é sinistro.

    📊 O menu raiz da Porto (sessões 67296ad9, d0d64bfc, a9560e3a, b1ff65f2)
    continua respondido com "Serviços para veículo" — e o próprio passo diz por
    que em `constante_justificada`.
    """
    pb = CP.get_playbook(CP.resolve_playbook_ref("porto", "auto"))
    menus = [l for l in telas("porto-auto")
             if CP._norm(l["text"]).startswith("como eu posso te ajudar")
             and "sinistro" in CP._norm(l["text"])]
    assert menus, "o menu raiz da Porto saiu do acervo"
    for l in menus:
        passo = CP.match_ura_step(pb, l["text"], subservice=l.get("servico"))
        assert passo and passo.get("step") == "menu_como_ajudar", (
            f"sessão {l['session_id']}: o menu raiz da Porto perdeu o passo — "
            f"4 rotas saem do ar")
        assert passo.get("constante_justificada"), (
            "a constante que escolhe entre alternativas de conteúdo precisa dizer "
            "por que está certa, escrito ao lado dela (CLAUDE.md §9.5)")


def test_controle_a_tela_de_agenda_do_condominio_nao_arrasta_o_residencial():
    """🔴 O padrão `áreas comuns` é ESTREITO: a tela que só AVISA a regra de
    cobertura segue `noop` (ela informa, não pede nada).

    📊 As duas redações diferem em três palavras — *"exclusivamente A SERVIÇOS NAS
    áreas comuns"* (a porta, que para) × *"exclusivamente DESTINADOS ÀS áreas
    comuns"* (o aviso, que segue). Um padrão largo calaria a tela que só avisa.
    """
    aviso = uma_tela("allianz-residencial",
                     r"exclusivamente destinados as[\s\S]{0,4}areas comuns")
    assert aviso, "a tela de AVISO de áreas comuns saiu do acervo"
    pb = CP.get_playbook(REF_RESID)
    passo = CP.match_ura_step(pb, aviso["text"], subservice="encanador")
    assert passo and passo.get("step") == "aviso_areas_comuns" and passo.get("noop"), (
        f"a tela de aviso perdeu o `noop`: {passo}")
