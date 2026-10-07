# -*- coding: utf-8 -*-
"""SPEC-130-A.1 F3 — o "mínimo do mínimo" (4º cálculo `minima`, D-130A1-05) do preset à "Mais em conta" (G6 · G7).

A mínima = a econômica (franquia normal, vidros básicos, assistência básica, terceiros/APP intactos) SEM carro reserva
(`carroReserva: 0` no corpo do `calcularV2`), com a comissão NORMAL. Só o canal a pede; ela mostra a MAIOR economia
possível e NUNCA é a recomendada nem entra no ranking da completa.

O que se afirma é o comportamento dos MOTORES reais (CLAUDE.md §9.4): `presets.coberturas_de`, a PORTA
(`MulticalculoProvider.calcular` com os presets REAIS), o MOTOR, o robô REAL (`agger_robo` + `montador.js` num
Chromium) contra o Agger dublê, `porta.consultar`, `comparacao.comparar` e `comparacao.opcoes`. O dublê fica só na
borda (o banco PostgREST, o Agger — e a seguradora devolve as rodadas REAIS do acervo para o corpo que PEDIU 0).

⛔ Dado FICTÍCIO; nenhum nome de corretora (§13.9).
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec130a1_minima.py -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec129b_a_porta as TP  # noqa: E402
import test_spec129b_o_motor as TM  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture)
from test_spec130a_completa_mais import _porta_real, mundo_fio  # noqa: E402,F401  (fixture)
from app.services.multicalculo import comparacao as CMP  # noqa: E402
from app.services.multicalculo import porta as PORTA  # noqa: E402
from app.services.multicalculo.config import PADRAO_DO_PRODUTO  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402
from portal_worker.multicalculo import presets as P  # noqa: E402

MIGRATION = BACKEND / "supabase" / "migrations" / "20261006_04_spec130a1_minima.sql"
MONTADOR = BACKEND / "portal_worker" / "multicalculo" / "montador.js"
FIXTURE_AGGER = BACKEND / "tests" / "fixtures" / "agger" / "vivo_conta_b.json"
QUATRO = ("padrao", "economica", "completa_mais", "minima")
DO_CANAL = ("padrao", "economica", "minima")


# =====================================================================================================================
# G6 · o preset — a econômica SEM carro reserva, e NADA mais
# =====================================================================================================================
def test_o_preset_da_minima_e_a_economica_sem_carro_reserva():
    mi, eco = P.coberturas_de("minima"), P.coberturas_de("economica")
    assert set(mi) == set(P.CHAVES_DE_COBERTURA) == set(eco), "o montador aplica exatamente as 15 chaves"
    # 🔴 o 0 é INTEIRO (o código medido), nunca False/None — o Agger lê o número
    assert mi["carroReserva"] == 0 and type(mi["carroReserva"]) is int
    assert eco["carroReserva"] == 1, "CONTROLE: a econômica manda 7 dias (as duas diferem)"
    assert {k: v for k, v in mi.items() if v != eco[k]} == {"carroReserva": 0}, "só o carro reserva muda"
    # vidros FICAM básicos (📊 sem vidros a Allianz recusa) e terceiros/APP intactos (📊 RCF 0 → recusas)
    assert mi["vidros"] == 1 and mi["tipoFranquia"] == 2 and mi["assist24hs"] == 4
    assert (mi["isDanosMateriais"], mi["isDanosCorporais"], mi["isDanosMorais"], mi["isAppMorte"]) == \
        (200000, 200000, 20000, 5000)
    assert "percComissao" not in mi, "a comissão é a NORMAL (a da conta / da negociação), nunca do preset"
    mi["carroReserva"] = 2
    assert P.coberturas_de("minima")["carroReserva"] == 0, "a cópia contaminou o próximo pedido"


def test_o_zero_do_pedido_e_o_nao_contratar_da_seguradora():
    """§9.5: a constante que escolhe conteúdo diz por que está certa — e o teste reconfere a evidência no acervo."""
    fx = json.loads(FIXTURE_AGGER.read_text(encoding="utf-8"))
    pares, ofertantes = {}, 0
    for c in fx["calculos"]:
        for r in c["rodadas"]:
            for it in (r["corpo"] or []):
                if not isinstance(it, dict) or it.get("carroReserva") != 0:
                    continue
                for o in it.get("resultados") or []:
                    s = (o.get("coberturas") or {}).get("carroReserva")
                    if s is not None:
                        pares[s] = pares.get(s, 0) + 1
    assert pares == {"Não contratar": 90}, pares          # 📊 TODA oferta que respondeu ao 0 diz "Não contratar"
    zero = [c for c in fx["calculos"] if c["rodadas"]
            and all(i.get("carroReserva") == 0 for i in c["pedido"]["corpo"]["cotacao"]["calculos"])]
    assert len(zero) == 1
    ofertantes = sum(1 for i in zero[0]["rodadas"][-1]["corpo"] if i.get("resultados"))
    assert ofertantes == 16, "📊 16/16 seguradoras devolveram oferta com o carro reserva 0 (nenhuma recusou)"
    # e o leitor da comparação entende as três formas de "não" que o acervo tem como 0 dias
    for rotulo in ("Não contratar", "Não desejo contratar", "Não"):
        assert CMP.dias_de_carro_reserva({"carroReserva": rotulo}) == 0, rotulo
    assert CMP.dias_de_carro_reserva({"carroReserva": "15 Dias"}) == 15            # CONTROLE
    assert CMP.dias_de_carro_reserva({}) is None                                   # não informou ≠ zero


# =====================================================================================================================
# G6 · porta, presets e motor dizem as mesmas opções; a mínima é a ÚLTIMA antes do ajuste
# =====================================================================================================================
def test_porta_presets_e_motor_dizem_as_quatro_opcoes_e_a_minima_por_ultimo():
    assert PORTA.OPCOES == P.ORDEM == QUATRO
    assert set(P.PRESETS) == set(PORTA.OPCOES)
    ordem = MOT._ORDEM_DA_OPCAO
    assert ordem["padrao"] < ordem["economica"] < ordem["completa_mais"] < ordem["minima"] < ordem["ajuste"]
    # a carteira NÃO gasta o 4º cálculo: o default continua o da 129-B; só o canal pede a mínima
    assert PORTA.OPCOES_PADRAO == ("padrao", "economica") and "minima" not in PORTA.OPCOES_PADRAO
    assert PORTA.OPCOES_DO_CANAL == DO_CANAL
    assert set(PORTA.OPCOES_DO_CANAL) <= set(PORTA.OPCOES)


def test_a_migration_aceita_a_minima_nas_duas_checks_e_nada_mais():
    sql = MIGRATION.read_text(encoding="utf-8")
    corpo = "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))
    pedidos = re.search(r"opcoes <@ array\[([^\]]*)\]::text\[\]", corpo)
    calculos = re.search(r"check \(opcao in \(([^)]*)\)\)", corpo)
    assert pedidos and calculos
    # as listas do APPLY são EXATAMENTE as da porta (+ o ajuste no cálculo): o gêmeo da porta é o banco
    assert tuple(re.findall(r"'([a-z_]+)'", pedidos.group(1))) == PORTA.OPCOES
    assert tuple(re.findall(r"'([a-z_]+)'", calculos.group(1))) == PORTA.OPCOES + ("ajuste",)
    assert "cardinality(opcoes) >= 1" in corpo
    assert corpo.count("do $$") == 1 and corpo.count("like '%''minima''%'") == 2, "idempotência pelo texto atual"
    assert not re.search(r"\b(update|delete|insert|truncate|drop table|drop column)\b", corpo, re.I)
    for secao in ("-- APPLY:", "-- VERIFY (read-only", "-- VERIFY comportamental", "-- ROLLBACK"):
        assert secao in sql, secao
    verify = sql[sql.index("-- VERIFY comportamental"):sql.index("-- ROLLBACK")]
    # o VERIFY tem CONTROLE (o que valia continua) e a RECUSA do desconhecido
    for caso in ("pedido_com_minima=aceito", "pedido_tres=aceito", "pedido_desconhecida=recusado",
                 "calculo_minima=aceito", "calculo_desconhecida=recusado", "minima_com_origem=recusado",
                 "calculo_completa_mais=aceito", "ajuste=aceito"):
        assert caso in verify, caso
    rollback = sql[sql.index("-- ROLLBACK"):]
    assert "opcao = 'minima'" in rollback and "'minima' = any(opcoes)" in rollback
    assert "array['padrao', 'economica', 'completa_mais']::text[]" in rollback
    assert "('padrao', 'economica', 'completa_mais', 'ajuste')" in rollback
    appends = [l for l in sql.splitlines() if "res := res ||" in l]
    assert appends and all(l.rstrip().endswith(")::text;") for l in appends), appends


def test_o_manifesto_registra_a_minima_aplicada_com_o_verify():
    """§9.3: nasceu afirmando NÃO APLICADA; o gerente aplicou em 07/10 — o guarda passa a exigir a versão e a saída real."""
    texto = (BACKEND / "supabase" / "migrations" / "MANIFEST.md").read_text(encoding="utf-8")
    linha = next(l for l in texto.splitlines() if "20261006_04_spec130a1_minima.sql" in l)
    assert "**APLICADA**" in linha and "NÃO APLICADA" not in linha and "20261007040359" in linha
    assert "1 · 1 · 2 · 1" in linha and "VERIFY 20261006_04 OK" in linha and "comportamental `OK:" in linha


def test_a_porta_aceita_a_minima_e_grava_o_carro_reserva_zero():
    db = TP._mundo()
    porta = _porta_real(db)
    aberto = TM.rodar(porta.calcular(company_id=TP.A, pedido=TP._pedido(), opcoes=("minima", "padrao", "economica"),
                                     origem="auxiliar"))
    assert list(db.linhas("multicalculo_pedidos")[0]["opcoes"]) == list(DO_CANAL)
    calcs = db.linhas("multicalculo_calculos")
    assert [c["opcao"] for c in calcs] == list(DO_CANAL) and len(aberto.calculos) == 3
    mi = next(c for c in calcs if c["opcao"] == "minima")
    assert mi["coberturas"] == P.coberturas_de("minima") and mi["coberturas"]["carroReserva"] == 0
    assert "minima" in porta.capacidades()["opcoes"]
    with pytest.raises(ValueError, match="opções aceitas"):
        TM.rodar(porta.calcular(company_id=TP.A, pedido=TP._pedido(), opcoes=("minimo",), origem="auxiliar"))


def test_o_motor_dispara_a_minima_no_mesmo_negocio_depois_da_completa_mais(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    TM.robo(amb, a)
    _pid, ids = TM.pedido(amb, a, [a], opcoes=("minima", "completa_mais", "economica", "padrao"))
    TM.rodar(TM.motor(amb, "motor-1").uma_volta())
    assert [p[3] for p in amb.mundo.posts] == list(QUATRO), "a mínima não saiu por último"
    assert {p[1] for p in amb.mundo.posts} == {"NEG-1"}, "a mínima abriu outro negócio"
    por = {TM.calc(amb, c)["opcao"]: TM.calc(amb, c) for c in ids}
    assert por["minima"]["status"] == "fechado" and por["minima"]["versao"] == 4


# =====================================================================================================================
# 🔴 o MONTADOR não engole o 0 (JS: `0 || x` e `if (0)` são falsos)
# =====================================================================================================================
def _montar_no_node(cob):
    node = shutil.which("node")
    if not node:
        pytest.skip("node ausente (o FIO no Chromium cobre o mesmo elo)")
    script = (
        "const fs=require('fs');globalThis.window={};(0,eval)(fs.readFileSync(process.argv[1],'utf8'));"
        # a CONFIG da conta tem carroReserva 2 (o que vazaria se o 0 fosse engolido) e mais duas seguradoras
        "const segs=[{ativo:true,seguradora:4,nomeSeguradora:'S4',idIntegracao:'c4',carroReserva:2,vidros:2},"
        "{ativo:true,seguradora:8,nomeSeguradora:'S8',idIntegracao:'c8',carroReserva:2,vidros:2}];"
        "const cob=JSON.parse(process.argv[2]);"
        "process.stdout.write(JSON.stringify(window.__abM.montarCalculos(segs,cob,null,null)));")
    out = subprocess.run([node, "-e", script, str(MONTADOR), json.dumps(cob)], capture_output=True, text=True,
                         timeout=60, check=True)
    return json.loads(out.stdout)


def test_o_montador_manda_o_carro_reserva_zero_e_nao_o_da_conta():
    itens = _montar_no_node(P.coberturas_de("minima"))
    assert itens and {i["carroReserva"] for i in itens} == {0}, [i["carroReserva"] for i in itens]
    assert {i["vidros"] for i in itens} == {1}
    # CONTROLE: com a econômica (7 dias = 1) sai o 1 — o montador aplica o preset, não a config da conta (2)
    assert {i["carroReserva"] for i in _montar_no_node(P.coberturas_de("economica"))} == {1}


# =====================================================================================================================
# G7 · a comparação — a mínima pode ser a "Mais em conta", NUNCA a 1ª nem do ranking da completa
# =====================================================================================================================
COR = "c0000000-0000-4000-8000-0000000000c1"


def _of(oid, calc, seg, premio, reserva, *, franquia=3000.0, vidros="Vidros básico"):
    return {"id": oid, "calculo_id": calc, "corretora_company_id": COR, "seguradora": seg, "seguradora_codigo": None,
            "pacote": "Auto", "premio_total": premio, "franquia_valor": franquia, "franquia_tipo": "Normal",
            "parcelamentos": [], "coberturas": {"tipoPadronizado": "Compreensiva", "casco": 100,
                                                "carroReserva": reserva, "vidros": vidros,
                                                "isDanosMateriais": 200000, "isDanosCorporais": 200000}}


ESTADOS = [{"calculo_id": "k-pad", "opcao": "padrao", "corretora_company_id": COR},
           {"calculo_id": "k-eco", "opcao": "economica", "corretora_company_id": COR},
           {"calculo_id": "k-min", "opcao": "minima", "corretora_company_id": COR}]


def _quadro(minima_premio=2600.0, reserva_minima="Não contratar", com_minima=True):
    ofertas = [_of("p1", "k-pad", "Seguradora Um", 3000.0, "15 dias", franquia=2000.0, vidros="Vidros completo"),
               _of("p2", "k-pad", "Seguradora Dois", 3200.0, "15 dias", franquia=2000.0, vidros="Vidros completo"),
               _of("e1", "k-eco", "Seguradora Um", 2800.0, "7 dias")]
    if com_minima:
        ofertas.append(_of("m1", "k-min", "Seguradora Um", minima_premio, reserva_minima))
    return CMP.comparar(ofertas, estados=ESTADOS if com_minima else ESTADOS[:2])


def test_a_minima_mais_barata_vira_a_mais_em_conta_e_diz_o_que_deixa_de_cobrir():
    q = _quadro()
    ops = CMP.opcoes(q, situacao="novo_sem_apolice", incluir_minima=True)
    assert ops[0]["id"] == "recomendada" and ops[0]["premio_anual"] == 3000.0, "a 1ª é SEMPRE a menor completa"
    barata = next(o for o in ops if o["id"] == "mais_em_conta")
    assert barata["premio_anual"] == 2600.0 and barata["rotulo"] == "Mais em conta"
    assert "Sem carro reserva" in barata["o_que_muda"], barata["o_que_muda"]
    assert any("Vidros" in t for t in barata["o_que_muda"]) and any("Franquia" in t for t in barata["o_que_muda"])
    assert not [o for o in ops if o["premio_anual"] == 2800.0], "a econômica (mais cara que a mínima) ficou também"
    # 🔴 G7: a mínima NUNCA no ranking da completa nem na vencedora entre corretoras
    assert all(r["opcao"] == "padrao" for r in q.ranking()) and [r["premio_anual"] for r in q.ranking()] == \
        [3000.0, 3200.0]
    assert q.entre_corretoras[0]["melhor_completa"] == 3000.0 and q.resumo["com_preco_comparavel"] == 2


def test_sem_incluir_a_minima_tudo_como_antes():
    q = _quadro()
    ops = CMP.opcoes(q, situacao="novo_sem_apolice")
    barata = next(o for o in ops if o["id"] == "mais_em_conta")
    assert barata["premio_anual"] == 2800.0, "a carteira usou a mínima sem pedir"
    assert ops == CMP.opcoes(_quadro(com_minima=False), situacao="novo_sem_apolice"), \
        "o cálculo mínimo no quadro mudou a proposta da carteira"
    # e com incluir_minima mas SEM cálculo mínimo: idêntico
    assert CMP.opcoes(_quadro(com_minima=False), situacao="novo_sem_apolice", incluir_minima=True) == \
        CMP.opcoes(_quadro(com_minima=False), situacao="novo_sem_apolice")


def test_a_minima_mais_cara_que_a_economica_nao_entra():
    ops = CMP.opcoes(_quadro(minima_premio=2900.0), situacao="novo_sem_apolice", incluir_minima=True)
    barata = next(o for o in ops if o["id"] == "mais_em_conta")
    assert barata["premio_anual"] == 2800.0, "escolheu a que cobre MENOS sendo mais cara"
    # empate de preço: vence a econômica (cobre mais pelo mesmo preço)
    ops = CMP.opcoes(_quadro(minima_premio=2800.0), situacao="novo_sem_apolice", incluir_minima=True)
    assert "Sem carro reserva" not in next(o for o in ops if o["id"] == "mais_em_conta")["o_que_muda"]


def test_a_minima_mais_barata_que_tudo_nunca_e_a_primeira():
    ops = CMP.opcoes(_quadro(minima_premio=900.0), situacao="novo_sem_apolice", incluir_minima=True)
    assert ops[0]["id"] == "recomendada" and ops[0]["premio_anual"] == 3000.0
    assert [o["premio_anual"] for o in ops].index(900.0) > 0


def test_o_que_muda_da_minima_conforme_o_que_a_seguradora_devolveu():
    # não informou o carro reserva: a mínima foi PEDIDA sem — dizer "sem" é a leitura que cobre MENOS (nunca a mais)
    ops = CMP.opcoes(_quadro(reserva_minima=None), situacao="novo_sem_apolice", incluir_minima=True)
    assert "Sem carro reserva" in next(o for o in ops if o["id"] == "mais_em_conta")["o_que_muda"]
    # a seguradora DEU carro reserva mesmo pedindo 0: não se diz "sem"
    ops = CMP.opcoes(_quadro(reserva_minima="7 dias"), situacao="novo_sem_apolice", incluir_minima=True)
    muda = next(o for o in ops if o["id"] == "mais_em_conta")["o_que_muda"]
    assert "Sem carro reserva" not in muda and any("7 dias" in t for t in muda), muda


def test_so_a_minima_sem_completa_nao_vira_proposta():
    q = CMP.comparar([_of("m1", "k-min", "Seguradora Um", 2600.0, "Não contratar")], estados=ESTADOS)
    assert q.ranking() == [] and CMP.opcoes(q, situacao="novo_sem_apolice", incluir_minima=True) == []


# =====================================================================================================================
# 🔴 O FIO — porta (presets REAIS) → banco → motor → robô REAL + montador.js (Chromium) → o CORPO com carroReserva 0
#            → a seguradora devolve as rodadas REAIS do acervo pedidas com 0 → porta.consultar → comparar → opcoes
# =====================================================================================================================
def _seguradora_responde_ao_corpo(d):
    """A BORDA: a seguradora devolve o que o corpo PEDIU. A versão cujo POST levou `carroReserva: 0` em TODO item
    recebe as rodadas REAIS do cálculo do acervo pedido com 0 (📊 vivo_conta_b, 16/16 seguradoras, "Não contratar");
    as outras, o que o dublê já servia. Se o montador engolisse o 0, a mínima receberia o quadro comum."""
    fx = d.fx["calculos"]
    zero = [c for c in fx if c["rodadas"]
            and all(i.get("carroReserva") == 0 for i in c["pedido"]["corpo"]["cotacao"]["calculos"])]
    assert len(zero) == 1
    rodadas_zero = [r["corpo"] for r in zero[0]["rodadas"]]
    original = d._rodadas_da_versao

    def rodadas(versao):
        for neg in d.negocios.values():
            for v in neg["versoes"]:
                if v["versao"] == versao and v["calculos"] and all(c.get("carroReserva") == 0 for c in v["calculos"]):
                    return rodadas_zero
        return original(versao)

    d._rodadas_da_versao = rodadas


def _lente_menor_completa(ofertas, estados, opcao):
    """🔬 independente de `comparacao`: compreensiva + casco 100 + não assinatura, direto das ofertas gravadas."""
    op = {e["calculo_id"]: e["opcao"] for e in estados}
    ps = [float(o["premio_total"]) for o in ofertas if op.get(o["calculo_id"]) == opcao
          and str((o.get("coberturas") or {}).get("tipoPadronizado") or "") == "Compreensiva"
          and (o.get("coberturas") or {}).get("casco") == 100 and "assinatura" not in str(o["seguradora"]).lower()]
    return min(ps) if ps else None


def test_o_fio_a_minima_sai_sem_carro_reserva_e_vira_a_mais_em_conta(mundo_fio):
    import test_spec129b_o_fio as TF
    from app.services.multicalculo import PedidoDeCalculo

    m = mundo_fio

    async def tudo(d, novo_navegador):
        _seguradora_responde_ao_corpo(d)
        nav = await novo_navegador()
        aberto = await m.porta.calcular(company_id=m.a, pedido=PedidoDeCalculo.de_dict(TF.dados_do_pedido()),
                                        opcoes=PORTA.OPCOES_DO_CANAL, origem="auxiliar")
        mot = TF.motor(m, "motor-1", nav, d)
        await TF.ate_esvaziar(mot, m)
        try:
            calcs = {c["opcao"]: c for c in m.banco.linhas("multicalculo_calculos")}
            assert set(calcs) == set(DO_CANAL) and {c["status"] for c in calcs.values()} == {"fechado"}, \
                [(c["opcao"], c["status"], c["erro"]) for c in calcs.values()]
            assert calcs["minima"]["coberturas"]["carroReserva"] == 0
            assert len({c["negocio_ref"] for c in calcs.values()}) == 1
            assert [calcs[o]["versao"] for o in DO_CANAL] == [1, 2, 3], "a mínima não foi a última"
            posts = list(d.posts_calcular)
            assert len(posts) == 3
            itens = [p["cotacao"]["calculos"] for p in posts]
            # o CORPO que saiu: a mínima (3º POST) com carroReserva 0 em TODO item; padrão 2 e econômica 1
            reservas = [sorted({i.get("carroReserva") for i in its}, key=str) for its in itens]
            assert reservas == [[2], [1], [0]], f"o 0 da mínima não chegou ao corpo: {reservas}"
            for i_eco, i_min in zip(itens[1], itens[2]):
                diferentes = {k for k in P.CHAVES_DE_COBERTURA if i_eco.get(k) != i_min.get(k)}
                assert diferentes == {"carroReserva"}, diferentes
                assert i_eco.get("percComissao") == i_min.get("percComissao"), "a comissão da mínima não é a normal"

            # ---- a comparação, sobre o que a PORTA devolve do banco
            andamento = await m.porta.consultar(company_id=m.a, pedido_id=aberto.pedido_id)
            ofertas, estados = list(andamento.ofertas), list(andamento.estados)
            ofertas_min = [o for o in ofertas if o["calculo_id"] == calcs["minima"]["id"]]
            assert ofertas_min and {(o.get("coberturas") or {}).get("carroReserva") for o in ofertas_min} \
                <= {"Não contratar", None}, "a mínima não recebeu o quadro do corpo com 0"
            q = CMP.comparar(ofertas, andamento.eventos, estados=estados, config=PADRAO_DO_PRODUTO)
            ops = CMP.opcoes(q, situacao="novo_sem_apolice", incluir_minima=True, corretora=m.a)
            # 🔬 a lente independente
            l_pad = _lente_menor_completa(ofertas, estados, "padrao")
            l_eco = _lente_menor_completa(ofertas, estados, "economica")
            l_min = _lente_menor_completa(ofertas, estados, "minima")
            assert l_min is not None and l_min < l_pad and (l_eco is None or l_min < l_eco), (l_pad, l_eco, l_min)
            assert ops[0]["id"] == "recomendada" and ops[0]["premio_anual"] == round(l_pad, 2), \
                "G7: a 1ª opção deixou de ser a menor COMPLETA"
            barata = next(o for o in ops if o["id"] == "mais_em_conta")
            assert barata["premio_anual"] == round(l_min, 2), (barata["premio_anual"], l_min)
            assert "Sem carro reserva" in barata["o_que_muda"], barata["o_que_muda"]
            assert all(r["opcao"] == "padrao" for r in q.ranking()), "G7: a mínima entrou no ranking da completa"
            # CONTROLE: a carteira (sem incluir) não usa a mínima
            sem = CMP.opcoes(q, situacao="novo_sem_apolice", corretora=m.a)
            assert all(o["premio_anual"] != round(l_min, 2) for o in sem)
        finally:
            await mot.desligar()

    TM.rodar(TF.com_agger_e_navegador(tudo))
