# -*- coding: utf-8 -*-
"""SPEC-116 U12 — o corpus da bancada: sem PII, carregável, versionado.

⛔ O corpus vai para o repositório. Nenhum CPF, CNPJ, telefone, placa ou e-mail
entra em texto: o caso guarda MARCADORES (``{{CPF:A1}}``) e o carregador
materializa valores SINTÉTICOS na hora. Nome de corretora ou de pessoa real
também não entra (CLAUDE.md §13.9) — e para o guarda não virar, ele mesmo, uma
lista de nomes reais, ele compara HASHES.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402

CORPUS = Path(RAIZ) / "tests" / "corpus" / "bancada"

PADROES_PII = {
    "CPF": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "CNPJ": re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
    "telefone": re.compile(r"(?<!\d)(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?!\d)"),
    "placa": re.compile(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b"),
    "e-mail": re.compile(r"\b[\w.+-]+@(?!exemplo\.invalid\b)[\w-]+\.[\w.]{2,}\b"),
}

#: Nomes do piloto que NÃO podem aparecer — guardados em rot13 e comparados por
#: sha256. Guardar em claro faria o próprio guarda virar uma constante com nome
#: de cliente (CLAUDE.md §13.9).
def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


_SEMENTES = ("erfhygn", "nznaqhf", "nhgbsyrrg", "znepvb", "ensnry", "fnvbanen", "xbrevpu", "ynpnh")


def _rot13(s: str) -> str:
    return s.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz", "nopqrstuvwxyzabcdefghijklm"))


HASHES_PROIBIDOS = {_hash(_rot13(s)) for s in _SEMENTES}


def _arquivos_de_texto():
    return [p for p in CORPUS.rglob("*") if p.is_file() and p.suffix in (".jsonl", ".json", ".md")]


def varrer_pii(texto: str) -> list:
    achados = []
    for nome, padrao in PADROES_PII.items():
        for m in padrao.finditer(texto):
            achados.append((nome, m.group(0)))
    import unicodedata

    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    for tok in set(re.findall(r"[a-z]{4,}", plano)):
        if _hash(tok) in HASHES_PROIBIDOS:
            achados.append(("nome-proibido", "<hash>"))
    return achados


def test_varredura_consegue_ficar_vermelha():
    """CONTROLE (§9.3): o guarda tem de ACHAR o que se planta nele."""
    materializado = D.materializar("{{CPF:X}} {{FONE:X}} {{PLACA:X}} {{CNPJ:X}}") + " fulano@gmail.com"
    tipos = {t for t, _ in varrer_pii(materializado)}
    assert {"CPF", "telefone", "placa", "CNPJ", "e-mail"} <= tipos, tipos
    assert varrer_pii("atendimento da " + _rot13("erfhygn").upper()), "nome proibido plantado não foi achado"


def test_corpus_sem_pii():
    assert _arquivos_de_texto(), "corpus vazio"
    sujos = {}
    for p in _arquivos_de_texto():
        achados = varrer_pii(p.read_text(encoding="utf-8"))
        if achados:
            sujos[str(p.relative_to(CORPUS))] = achados[:5]
    assert not sujos, f"PII no corpus: {sujos}"


def test_marcadores_materializam_deterministico_e_sem_sobra():
    for papel in B.PAPEIS:
        for caso in B.carregar_casos(papel):
            m1, m2 = D.materializar(caso), D.materializar(caso)
            assert m1 == m2
            assert "{{" not in json.dumps(m1, ensure_ascii=False), caso["chave"]


CAMPOS = ("chave", "versao", "papel", "nivel", "critico", "tenant", "entrada", "ferramentas_disponiveis",
          "efeitos_permitidos", "efeitos_proibidos", "oraculo", "falhas_injetadas", "orcamento_turnos", "origem")

#: 📊 o que o corpus v1 entrega (contagem medida em 23/09/2026) — o guarda
#: impede que ele ENCOLHA sem alguém ver.
MINIMOS = {("atendimento", "N1"): 30, ("atendimento", "N2"): 10, ("chat_principal", "N1"): 30,
           ("chat_principal", "N2"): 8, ("cobranca", "N1"): 10, ("dispatch", "N1"): 15,
           ("portal_decisao", "N1"): 15, ("memoria", "N1"): 15, ("visao", "N1"): 10,
           ("hyde", "N1"): 3, ("extrator_planos", "N1"): 3, ("juiz", "N1"): 3, ("transcricao", "N1"): 3}


def test_corpus_carrega_com_o_formato_e_a_contagem():
    chaves = set()
    contagem = {}
    for papel in B.PAPEIS:
        assert (CORPUS / papel / "LEIAME.md").exists(), f"{papel} sem LEIAME"
        for caso in B.carregar_casos(papel):
            for campo in CAMPOS:
                assert campo in caso, (caso.get("chave"), campo)
            assert caso["papel"] == papel and caso["nivel"] in ("N1", "N2")
            assert caso["tenant"] in B.TENANTS
            assert str(caso["origem"]).strip(), caso["chave"]
            assert caso["chave"] not in chaves, f"chave repetida {caso['chave']}"
            chaves.add(caso["chave"])
            contagem[(papel, caso["nivel"])] = contagem.get((papel, caso["nivel"]), 0) + 1
    for k, n in MINIMOS.items():
        assert contagem.get(k, 0) >= n, (k, contagem.get(k, 0), n)


def test_cada_dominio_do_agente_tem_falha_injetada_e_dois_tenants():
    for papel in ("atendimento", "chat_principal"):
        casos = B.carregar_casos(papel)
        assert any(c["falhas_injetadas"] for c in casos), papel
        assert any((c["oraculo"] or {}).get("dados_do_outro_tenant") for c in casos), papel
    assert any(c["falhas_injetadas"] for c in B.carregar_casos("portal_decisao"))


def test_carregar_corpus_na_eval_fabric_e_idempotente():
    banco = D.SupabaseDuble()
    um = B.carregar_corpus(gravar=True, cliente=banco, papeis=["atendimento", "dispatch"])
    assert um["atendimento"]["novos"] == um["atendimento"]["casos"] >= 40
    assert banco.tabelas["eval_dataset_versions"][0]["congelada_em"]
    dois = B.carregar_corpus(gravar=True, cliente=banco, papeis=["atendimento", "dispatch"])
    assert dois["atendimento"]["novos"] == 0 and dois["atendimento"]["divergentes"] == 0
    assert len(banco.tabelas["eval_datasets"]) == 2
    slugs = {d["slug"] for d in banco.tabelas["eval_datasets"]}
    assert slugs == {"bancada-atendimento", "bancada-dispatch"}
    # nenhum caso carrega company_id real (os tenants são fictícios)
    assert all(c.get("company_id") is None for c in banco.tabelas["eval_cases"])


def test_imagens_da_visao_existem_e_sao_sinteticas():
    for caso in B.carregar_casos("visao"):
        img = CORPUS / caso["entrada"]["imagem"]
        assert img.exists() and img.stat().st_size < 200_000, img
        assert "SINTÉTICO" in caso["origem"]
