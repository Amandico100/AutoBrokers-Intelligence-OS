"""SPEC-123 F6 · P-122-12 — a pergunta que vai ao SEGURADO fala com ele.

`_COMO_PERGUNTAR` é o vocabulário do DOSSIÊ da equipe ("qual servico o cliente
precisa"). Quando a frase vai ao segurado (`pergunta_para_o_segurado`: "me diga
…"), ela sai de `como_perguntar_ao_segurado`: 2ª pessoa e com acento.

O guarda varre TODAS as chaves que o produto sabe perguntar — chave nova escrita
em 3ª pessoa fica vermelha aqui (MUTAÇÃO: `test_MUTACAO_frase_em_3a_pessoa_fica_vermelha`).
"""

from __future__ import annotations

import re

import app.services.corridor_playbooks as CP
from app.services.dispatch_router import pergunta_para_o_segurado

#: 3ª pessoa (falar DO segurado) e as palavras que perdem o acento no dossiê.
_RX_3A_PESSOA = re.compile(
    r"\b(?:ele|ela|dele|dela|o cliente|do cliente|ao cliente|o segurado|do segurado|"
    r"ao segurado)\b", re.IGNORECASE)
_RX_SEM_ACENTO = re.compile(
    r"\b(?:servico|proximo|referencia|voce|numero|endereco|veiculo|apolice|nao|"
    r"esta|ate|tambem|horario|agua)\b", re.IGNORECASE)


def _defeitos(frases):
    return {k: v for k, v in frases.items()
            if v and (_RX_3A_PESSOA.search(v) or _RX_SEM_ACENTO.search(v))}


def _todas():
    chaves = set(CP._COMO_PERGUNTAR) | set(CP._COMO_PERGUNTAR_GRUPO)
    frases = {k: CP.como_perguntar_ao_segurado(k) for k in sorted(chaves)}
    frases.update({"resid:" + k: CP.como_perguntar_ao_segurado(k, RESID) for k in sorted(chaves)})
    return frases


RESID = "allianz-residencial-whatsapp@v1"
AUTO = "allianz-auto-whatsapp@v1"


def test_toda_frase_que_vai_ao_segurado_e_2a_pessoa_e_com_acento():
    assert _defeitos(_todas()) == {}


def test_CONTROLE_o_dossie_da_equipe_continua_como_era():
    """Separar, não trocar: a atendente segue lendo a frase dela."""
    assert "o cliente" in CP._COMO_PERGUNTAR["servico_texto"]
    assert CP.como_perguntar_ao_segurado("servico_texto") == "qual serviço você precisa, em uma frase"
    # o CONTROLE do guarda: a frase do dossiê É reprovada por ele
    assert _defeitos({"servico_texto": CP._COMO_PERGUNTAR["servico_texto"]})


def test_o_grupo_de_mesma_pergunta_tambem_fala_com_o_segurado():
    assert "você" in CP.como_perguntar_ao_segurado("local_seguro_opcao")


def test_a_mensagem_ao_segurado_sai_em_2a_pessoa():
    s = {"playbook_ref": "yelum-auto-whatsapp@v3"}
    msg = pergunta_para_o_segurado(s, CP.como_perguntar_ao_segurado("transporte_destino"))
    assert "você quer ser levado" in msg and not _RX_3A_PESSOA.search(msg)


def test_MUTACAO_frase_em_3a_pessoa_fica_vermelha(monkeypatch):
    monkeypatch.setitem(CP._COMO_PERGUNTAR_AO_SEGURADO, "data_agendamento",
                        "para que dia ele quer o agendamento")
    assert "data_agendamento" in _defeitos(_todas())


def test_no_residencial_o_CEP_e_da_casa_e_no_auto_e_do_carro():
    """📊 F3 (30/09): "Digite um novo CEP." na Allianz residencial (96f220ca)
    saía como "o CEP do lugar onde o carro está"."""
    resid = CP.como_perguntar_ao_segurado("local_cep", RESID)
    assert "serviço" in resid and "carro" not in resid
    # CONTROLE: o mesmo slot num corredor de AUTO continua falando do carro
    assert "carro" in CP.como_perguntar_ao_segurado("local_cep", AUTO)
    assert "carro" in CP.como_perguntar_ao_segurado("local_cep")
