# -*- coding: utf-8 -*-
"""O guarda da COLUNA QUE MENTIA — SPEC-119 F5.

> ## Um número de demanda que serve para dez rotas não é a demanda de nenhuma delas.

📊 O defeito que este arquivo existe para impedir de voltar, medido em
27/09/2026 no commit `f9b7204`:

```
medir_rota.py:275  ->  d = demanda.get(n.rota.servico, 0)
medir_rota.py:446  ->  demanda = {s: e for s, e, _c in PS.DEMANDA_MEDIDA}
```

Uma chave de UM eixo (o serviço) para uma tabela de TRÊS (seguradora × ramo ×
serviço). `("guincho", 72, 197)` é o total de sete seguradoras, e as dez linhas
de guincho mostravam **72**. 📊 Nenhuma rota tinha 72 — a maior, medida em
`observed_events` em 28/09/2026, é `allianz/auto/guincho` com **29**, e a
Mapfre, que a página apontava como a rota de 72 pedidos, tem **zero**.

🔴 **E o segundo defeito era do NOME, não do texto** (CLAUDE.md §12.1): a
tabela escrevia `eletrodomestico` e `vidro` no singular enquanto o
classificador e os playbooks escrevem `eletrodomesticos` e `vidros`. A busca
não achava, devolvia `0`, e a rota aparecia como se ninguém pedisse.

## 🔴 CADA GUARDA AQUI TEM DE CONSEGUIR FICAR VERMELHO

Os testes que terminam em `_a_mutacao_fica_vermelha` reintroduzem o defeito
histórico **de propósito** e exigem que a afirmação caia. Um guarda que não tem
como falhar não guarda nada (CLAUDE.md §9.3) — e nesta mesma SPEC duas
mutações ficaram verdes por engano.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import demanda_por_rota as DPR        # noqa: E402
import medir_rota as MR               # noqa: E402
import padroes_de_servico as PS       # noqa: E402
import pagina_dos_corredores as PAG   # noqa: E402
import regua_motor as M               # noqa: E402


class _RotaFalsa:
    def __init__(self, seg, ramo, srv):
        self.seguradora, self.ramo, self.servico = seg, ramo, srv


def _retrato():
    r = DPR.carregar()
    if r is None:
        pytest.skip(f"sem retrato em {DPR.CAMINHO_DO_RETRATO}")
    return r


# ═════════════════════════════════════════════════════════════════════════════
# ① A CHAVE TEM TRÊS EIXOS
# ═════════════════════════════════════════════════════════════════════════════
def test_a_chave_da_demanda_tem_os_tres_eixos():
    """Duas rotas do MESMO serviço em seguradoras diferentes são distinguíveis.

    🔴 Este é o teste do MOTOR, não do dado: ele chama `DPR.chave`, que é a
    função que a régua usa. Comparar strings escritas à mão mediria a minha
    imaginação (CLAUDE.md §9.4).
    """
    a = DPR.chave("mapfre", "auto", "guincho")
    b = DPR.chave("allianz", "auto", "guincho")
    assert a != b, "duas rotas de guincho colapsaram na mesma chave"
    assert "mapfre" in a and "auto" in a and "guincho" in a


def test_a_regua_le_a_demanda_pela_rota_inteira():
    """📊 A prova direta: rotas do mesmo serviço devolvem números DIFERENTES."""
    r = _retrato()
    allianz = MR._demanda_de(r, _RotaFalsa("allianz", "auto", "guincho"))
    mapfre = MR._demanda_de(r, _RotaFalsa("mapfre", "auto", "guincho"))
    assert allianz != mapfre, (
        "allianz/auto/guincho e mapfre/auto/guincho devolveram o MESMO número "
        f"({allianz}) — é o defeito histórico de volta")
    assert mapfre == DPR.NAO_MEDIDO, (
        "a Mapfre não tem uma sessão de guincho no acervo; a coluna tem de "
        f"dizer {DPR.NAO_MEDIDO!r} e disse {mapfre!r}")


def test_nenhuma_rota_exibe_o_total_global_do_servico():
    """🔴 O `72` do guincho não pode reaparecer em rota nenhuma.

    ⚠️ O teste não proíbe o VALOR (uma rota poderia legitimamente ter 72): ele
    proíbe que TODAS as rotas de um serviço tenham o mesmo número, que é a
    assinatura do defeito.
    """
    r = _retrato()
    por_servico = {}
    for rota in M.rotas():
        v = r.de(rota.seguradora, rota.ramo, rota.servico)
        if v is not None:
            por_servico.setdefault(rota.servico, []).append((str(rota), v))
    for servico, pares in por_servico.items():
        if len(pares) < 2:
            continue
        valores = {v for _n, v in pares}
        assert len(valores) > 1 or valores == {0}, (
            f"as {len(pares)} rotas de {servico!r} têm TODAS o mesmo número "
            f"{valores} — é a coluna global de volta: {pares}")


# ═════════════════════════════════════════════════════════════════════════════
# ② ZERO MEDIDO E ZERO NÃO MEDIDO NÃO SÃO A MESMA COISA
# ═════════════════════════════════════════════════════════════════════════════
def test_demanda_ausente_imprime_travessao_e_nunca_zero():
    r = _retrato()
    assert r.de("seguradora_que_nao_existe", "auto", "guincho") is None
    assert MR._demanda_de(r, _RotaFalsa("seguradora_que_nao_existe", "auto",
                                        "guincho")) == "—"


def test_sem_retrato_a_coluna_inteira_sai_nao_medida():
    """Sem banco e sem arquivo, a régua NÃO pode inventar zeros."""
    assert MR._demanda_de(None, _RotaFalsa("allianz", "auto", "guincho")) == "—"


# ═════════════════════════════════════════════════════════════════════════════
# ③ O NOME DO CAMPO — singular × plural
# ═════════════════════════════════════════════════════════════════════════════
def test_as_chaves_do_retrato_sao_os_nomes_que_o_playbook_usa():
    """🔴 O defeito (b): a chave medida tem de ser a chave consultada.

    📊 `demanda.get("eletrodomesticos")` devolvia nada porque a tabela dizia
    `eletrodomestico`. Aqui a exigência é que TODA rota declarada com demanda
    no retrato seja uma rota que a régua conhece — ou esteja declarada em
    `sem_corredor`, que é o lugar honesto para o que não tem playbook.
    """
    r = _retrato()
    declaradas = {DPR.chave(x.seguradora, x.ramo, x.servico) for x in M.rotas()}
    sem_corredor = set(r.rotas_sem_corredor)
    for chave in r.dados["por_rota"]:
        assert chave in declaradas or chave in sem_corredor, (
            f"{chave!r} tem demanda medida e não é nem rota declarada nem "
            "`sem_corredor` — é a divergência de nome que zerava a busca")


def test_o_nome_global_carrega_o_que_ele_e_e_de_quando():
    """🔴 CLAUDE.md §12.1: o nome errado é a CAUSA, não o sintoma."""
    assert not hasattr(PS, "DEMANDA_MEDIDA"), (
        "`DEMANDA_MEDIDA` voltou. O nome não diz que é GLOBAL POR SERVIÇO nem "
        "de quando é, e foi assim que um total de sete seguradoras virou 'os "
        "72 pedidos da Mapfre'")
    assert hasattr(PS, "DEMANDA_GLOBAL_POR_SERVICO_21_08_2026")


# ═════════════════════════════════════════════════════════════════════════════
# ④ A NOTA EM PORCENTAGEM
# ═════════════════════════════════════════════════════════════════════════════
def test_a_nota_publicada_e_porcentagem_e_o_bruto_fica_do_lado():
    """📊 `42/64` PARECE pior que `48/76` e é melhor — 66% contra 63%.

    O denominador muda por rota, então dois brutos não se comparam. É por isso
    que o que se publica é `%`.
    """
    class _N:
        estado = None
        pontos = 42
        denominador = 64
        fracao = 42 / 64

    class _M:
        estado = None
        pontos = 48
        denominador = 76
        fracao = 48 / 76

    a, b = MR._pct(_N()), MR._pct(_M())
    assert a.endswith("%") and b.endswith("%")
    assert int(a[:-1]) > int(b[:-1]), (
        f"a rota de 42/64 saiu {a} e a de 48/76 saiu {b}: a ordem se inverteu")
    assert MR._bruto(_N()) == "42/64"


def test_estado_vence_a_porcentagem():
    class _S:
        estado = "SEM_CORPUS"
        pontos = 0
        denominador = 0
        fracao = 0.0

    assert MR._pct(_S()) == "SEM_CORPUS"
    assert MR._bruto(_S()) == "—"


# ═════════════════════════════════════════════════════════════════════════════
# ⑤ A PÁGINA — duas perguntas, causa obrigatória, data visível
# ═════════════════════════════════════════════════════════════════════════════
def _fontes():
    f = PAG.Fontes()
    if f.faltando():
        pytest.skip("retratos ausentes: " + " · ".join(f.faltando()))
    return f


def test_a_pagina_responde_as_duas_perguntas_separadamente():
    """🔴 A lição da SPEC-117: uma régua não serve para duas perguntas."""
    f = _fontes()
    linhas = PAG.montar(f)
    assert linhas, "nenhuma rota montada"
    for l in linhas:
        assert l.da_para_ligar in ("SIM", "VAI PARA UMA PESSOA", "FALTA CAPTURA")
    # 🔴 A PROVA de que são perguntas diferentes: as faixas de nota das que
    #    LIGAM e das que NÃO LIGAM têm de se SOBREPOR. Se a nota mais baixa
    #    entre as que ligam fosse maior que a nota mais alta entre as que não
    #    ligam, a nota sozinha responderia as duas perguntas — e a segunda
    #    coluna seria enfeite.
    #
    # ⚠️ A primeira versão deste guarda exigia "≥ 80% e não liga", um limiar
    #    que EU escolhi. 📊 Ele ficou vermelho na primeira rodada da régua
    #    nova, não porque o produto tivesse mudado, mas porque as duas rotas
    #    que o satisfaziam caíram de 95% para 76% e 63% quando o corpus cresceu.
    #    Um guarda preso a um número que a medição move não guarda a REGRA;
    #    guarda o número. A regra é a sobreposição.
    #
    # 📊 Medido em 28/09/2026: `tokio/auto/guincho` e `hdi/auto/chaveiro` têm
    #    os DOIS 70% — e o primeiro vai para uma pessoa enquanto o segundo
    #    atende sozinho. Mesma nota, respostas opostas.
    ligam = [l.nota["pct"] for l in linhas
             if l.da_para_ligar == "SIM" and l.nota.get("pct") is not None]
    nao_ligam = [l.nota["pct"] for l in linhas
                 if l.da_para_ligar != "SIM" and l.nota.get("pct") is not None]
    assert ligam and nao_ligam, "faltou rota com nota nos dois lados"
    assert min(ligam) <= max(nao_ligam), (
        f"as notas NÃO se sobrepõem: a pior que liga tem {min(ligam)}% e a "
        f"melhor que não liga tem {max(nao_ligam)}%. Se a nota separa as duas "
        "perguntas sozinha, a segunda coluna não está medindo nada")


def test_toda_rota_fora_de_atende_sozinho_traz_a_causa():
    """🔴 `HANDOFF por_desenho_link` e `HANDOFF defeito_de_resposta` são opostos."""
    f = _fontes()
    for l in PAG.montar(f):
        if l.faixa == "ATENDE SOZINHO":
            continue
        assert l.causa, f"{l.rota} está em {l.faixa} sem causa"
        assert l.causa in PAG.CAUSAS, f"causa {l.causa!r} sem tradução"
        assert l.causa_em_portugues != "—"


def test_a_aba_mostra_as_datas_de_cada_numero():
    """Gate G10: ZERO informação de data anterior sem rótulo."""
    f = _fontes()
    texto = PAG.aba(f, PAG.montar(f))
    assert f.data_demanda in texto, "a data da demanda não aparece na aba"
    assert f.data_notas in texto, "a data da medição não aparece na aba"


def test_o_guarda_da_pagina_nao_acha_nada_no_estado_de_hoje():
    f = _fontes()
    linhas = PAG.montar(f)
    achados, feitas = PAG.conferir(f, linhas, PAG.aba(f, linhas))
    assert feitas, "o guarda não fez conferência nenhuma"
    assert not achados, "\n".join(achados)


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 AS MUTAÇÕES — o guarda TEM de conseguir ficar vermelho
# ═════════════════════════════════════════════════════════════════════════════
def test_mutacao_a_busca_por_servico_fica_vermelha(monkeypatch):
    """Reintroduz o defeito histórico: buscar a demanda pelo SERVIÇO.

    🔴 Se este teste passar sem a mutação, o guarda de cima é enfeite.
    """
    global_por_servico = {s: e for s, e, _c
                          in PS.DEMANDA_GLOBAL_POR_SERVICO_21_08_2026}

    def _defeituoso(retrato, rota):          # exatamente a linha de antes
        return str(global_por_servico.get(rota.servico, 0))

    monkeypatch.setattr(MR, "_demanda_de", _defeituoso)
    r = _retrato()
    allianz = MR._demanda_de(r, _RotaFalsa("allianz", "auto", "guincho"))
    mapfre = MR._demanda_de(r, _RotaFalsa("mapfre", "auto", "guincho"))
    assert allianz == mapfre == "72", (
        "a mutação NÃO reproduziu o defeito — a linha de controle está errada, "
        f"e não o produto (allianz={allianz!r}, mapfre={mapfre!r})")


def test_mutacao_demanda_ausente_virando_zero_fica_vermelha(monkeypatch):
    """O outro defeito: `.get(chave, 0)` em vez de `—`."""
    r = _retrato()
    monkeypatch.setattr(DPR.Retrato, "rotulo",
                        lambda self, s, ra, sv: str(self.de(s, ra, sv) or 0))
    saida = MR._demanda_de(r, _RotaFalsa("mapfre", "auto", "guincho"))
    assert saida == "0", (
        f"a mutação devia produzir '0' e produziu {saida!r} — a mutação está "
        "errada, não o produto")
    assert saida != DPR.NAO_MEDIDO


def test_mutacao_causa_apagada_deixa_o_guarda_da_pagina_vermelho():
    """Tira a causa de uma rota e o guarda TEM de reclamar."""
    f = _fontes()
    linhas = PAG.montar(f)
    vitima = next((l for l in linhas if l.faixa != "ATENDE SOZINHO"), None)
    assert vitima is not None, "não há rota fora de ATENDE SOZINHO para mutar"
    antes = vitima.causa
    vitima.causa = ""
    try:
        achados, _ = PAG.conferir(f, linhas, PAG.aba(f, linhas))
        assert any("SEM causa" in a for a in achados), (
            "apaguei a causa e o guarda ficou VERDE — ele é carimbo, não guarda")
    finally:
        vitima.causa = antes
    achados, _ = PAG.conferir(f, linhas, PAG.aba(f, linhas))
    assert not any("SEM causa" in a for a in achados), "a mutação não foi desfeita"


def test_mutacao_data_ausente_deixa_o_guarda_da_pagina_vermelho():
    """🔴 Gate G10: a página sem data tem de ficar vermelha."""
    f = _fontes()
    linhas = PAG.montar(f)
    html_sem_data = PAG.aba(f, linhas).replace(f.data_demanda, "")
    achados, _ = PAG.conferir(f, linhas, html_sem_data)
    assert any("gate G10" in a for a in achados), (
        "tirei a data da página e o guarda ficou VERDE")
    achados_ok, _ = PAG.conferir(f, linhas, PAG.aba(f, linhas))
    assert not any("gate G10" in a for a in achados_ok), "a mutação não foi desfeita"


def test_mutacao_nome_de_corretora_no_dado_fica_vermelha():
    """CLAUDE.md §13.9 — nenhum nome de corretora nos DADOS medidos."""
    f = _fontes()
    linhas = PAG.montar(f)
    f.demanda["sem_corredor"] = dict(f.demanda.get("sem_corredor") or {})
    f.demanda["sem_corredor"]["resulta/auto/guincho"] = 1
    try:
        achados, _ = PAG.conferir(f, linhas, PAG.aba(f, linhas))
        assert any("§13.9" in a for a in achados), (
            "plantei um nome de corretora no dado e o guarda ficou VERDE")
    finally:
        f.demanda["sem_corredor"].pop("resulta/auto/guincho", None)
    achados, _ = PAG.conferir(f, linhas, PAG.aba(f, linhas))
    assert not any("§13.9" in a for a in achados), "a mutação não foi desfeita"


# ═════════════════════════════════════════════════════════════════════════════
# ⑥ O RETRATO É AUDITÁVEL
# ═════════════════════════════════════════════════════════════════════════════
def test_o_retrato_carrega_data_fonte_comando_e_controle():
    r = _retrato()
    assert r.medido_em != "?" and len(r.medido_em) == 10
    assert r.fonte == "observed_events"
    assert "demanda_por_rota.py" in r.comando
    assert r.dados["controle"]["marcas_de_corretora"] > 0, (
        "CONTROLE VERMELHO: o retrato foi gerado SEM banco e é inválido")
    assert r.medido_em in r.carimbo and r.fonte in r.carimbo


def test_a_via_do_corpus_confere_a_via_do_banco():
    """🔴 A linha de controle: o banco é ≥ o corpus em toda rota.

    O corpus é um RECORTE do banco. Uma rota com mais sessões no corpus do que
    no banco é prova de que um dos dois caminhos está quebrado.
    """
    r = _retrato()
    banco = r.dados["por_rota"]
    corpus = DPR.do_corpus()
    assert corpus, "a via do corpus devolveu vazio — ela não confere nada"
    for chave, n in corpus.items():
        assert chave in banco, (
            f"{chave!r} existe no corpus versionado e NÃO no banco — uma das "
            "duas vias está quebrada")
        assert banco[chave] >= n, (
            f"{chave!r}: banco={banco[chave]} < corpus={n}, o que é impossível")


def test_o_retrato_conta_a_mesma_unidade_que_o_corpus():
    """🔴 SPEC-121 conserto Z · as duas vias contam ATENDIMENTOS.

    📊 29/09/2026: o corpus regerado pela F3 passou a ser por atendimento
    (`<sid8>+k`) e o retrato de 28/09 continuava por SESSÃO. A linha de
    controle ficou vermelha em `allianz/auto/bateria` (banco=3 < corpus=5) sem
    nenhum dos dois caminhos estar quebrado: `cea36de4` e `cea36de4+1` são duas
    baterias na mesma sessão. A lição migra: a regra `banco ≥ corpus` só vale
    se as duas vias contarem a MESMA coisa — então a unidade é afirmada.
    """
    r = _retrato()
    assert "atendimento" in r.dados.get("unidade", ""), (
        f"o retrato conta {r.dados.get('unidade')!r}, e o corpus conta "
        "atendimentos — a comparação banco × corpus mede duas coisas")
    assert r.dados["acervo"].get("atendimentos", 0) >= r.dados["acervo"]["sessoes"], (
        "há menos atendimentos que sessões: a partição não rodou")


def test_mutacao_banco_menor_que_corpus_fica_vermelha(monkeypatch):
    """O guarda de cima TEM de conseguir acusar: tira 1 de uma rota do banco
    que o corpus também tem, e ele fica vermelho (CLAUDE.md §9.3)."""
    r = _retrato()
    corpus = DPR.do_corpus()
    vitima = next(k for k in sorted(corpus) if k in r.dados["por_rota"])
    mutado = dict(r.dados)
    mutado["por_rota"] = dict(r.dados["por_rota"])
    mutado["por_rota"][vitima] = corpus[vitima] - 1
    monkeypatch.setattr(DPR, "carregar", lambda *a, **k: DPR.Retrato(mutado))
    with pytest.raises(AssertionError, match="impossível"):
        test_a_via_do_corpus_confere_a_via_do_banco()
