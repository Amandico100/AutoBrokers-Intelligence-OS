# -*- coding: utf-8 -*-
"""SPEC-131-A · F1 — a lista, a máquina de estados e a conferência.

    ① duas corretoras na MESMA madrugada, o MESMO nosnum: 0 linha cruzada (o repositório filtra; lido com e sem filtro)
    ② idempotência: 2 ticks = 1 run por passo; 2 preparações = 0 duplicata e 0 evento a mais
    ③ endosso que muda o fimvig: item novo e o velho `substituida` (com o evento)
    ④ CHECK de motivo: `pendente`/`falhou` sem motivo é recusado (pela máquina E pelo banco)
    ⑤ estados reservados: a máquina recusa todos; nenhum escritor do código os grava (AST)
    ⑥ a conferência NÃO importa o montador (AST) e relê a InfoCap: a esquecida → item + evento + dia VERMELHO
    ⑦ InfoCap fora na conferência → `sem_conexao` com contagens NULAS (nunca "0") + alerta
    ⑧ ausência: o aviso vai ao SUBSTITUTO; o cálculo segue com o dono
    ⑨ o estado é DERIVADO dos cálculos: a dona no próprio Agger → `aguardando_agger` → o desvio das 06:15 COM aviso

As MUTAÇÕES 1, 2 e 6 da SPEC §6 ficam vermelhas aqui (registradas no relatório da fatia; restauradas por cópia).
"""
from __future__ import annotations

import ast
import asyncio
import uuid
from datetime import timedelta
from pathlib import Path

import pytest

import test_spec131a_o_fio as FIO
from test_spec131a_o_fio import (DIA, M, R, CONF, PortaDuble, acordar, avisos, cinco_renovacoes, fechar_com_ofertas,  # noqa: F401
                                 itens, linha_renov, local, madrugada_inteira, montar_corretora, mundo, publicacoes,
                                 rodar, run_do_passo, runs_da_renovacao, tick)

BACKEND = Path(__file__).resolve().parents[1]


def _preparar(m, c):
    return asyncio.run(M.preparar_dia(m.db, c.id, DIA))


def _conferir(m, c):
    return asyncio.run(CONF.conferir_dia(m.db, c.id, DIA))


def _dia(m, c):
    (d,) = [x for x in m.banco.linhas("renovacao_dias") if x["company_id"] == c.id]
    return d


# ---------------------------------------------------------------------------------------------------------------------
# ① duas corretoras ao mesmo tempo
# ---------------------------------------------------------------------------------------------------------------------
def test_duas_corretoras_na_mesma_madrugada_zero_cruzamento(mundo):
    m = mundo
    a = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    b = montar_corretora(m, "token-b", renovacoes=cinco_renovacoes()[:3])   # o MESMO nosnum nas duas
    for hora, passo in (((0, 31), "preparar"), ((2, 1), "calcular"), ((5, 31), "conferir"), ((6, 16), "desvio"),
                        ((6, 46), "avisar")):
        tick(m, local(*hora))
        for c in (a, b):
            r = run_do_passo(m, c.id, passo)
            rodar(m, r["id"], c.id)
            if passo == "calcular":
                fechar_com_ofertas(m.banco, [x["pedido_id"] for x in itens(m, c.id) if x.get("pedido_id")])
                acordar(m, r["id"])
                rodar(m, r["id"], c.id)
            assert m.banco.run(r["id"])["status"] == "completed", (passo, m.banco.run(r["id"]).get("error_message"))

    # SEM o filtro: 8 linhas no banco; COM o filtro do repositório: 5 e 3, nenhuma da outra
    assert len(m.banco.linhas("renovacoes")) == 8
    ra, rb = R.RepositorioDeRenovacoes(m.db).listar(a.id), R.RepositorioDeRenovacoes(m.db).listar(b.id)
    assert (len(ra), len(rb)) == (5, 3)
    assert {x["company_id"] for x in ra} == {a.id} and {x["company_id"] for x in rb} == {b.id}
    with pytest.raises(R.NaoEncontrada):
        R.RepositorioDeRenovacoes(m.db).por_id(a.id, rb[0]["id"])
    # o pedido, os eventos, o dia e os avisos de cada uma são DELA
    pedidos = {p["id"]: p["company_id"] for p in m.banco.linhas("multicalculo_pedidos")}
    for x in m.banco.linhas("renovacoes"):
        if x.get("pedido_id"):
            assert pedidos[x["pedido_id"]] == x["company_id"]
    dono_da = {x["id"]: x["company_id"] for x in m.banco.linhas("renovacoes")}
    assert all(dono_da[e["renovacao_id"]] == e["company_id"] for e in m.banco.linhas("renovacao_eventos"))
    assert (_dia(m, a)["esperadas"], _dia(m, b)["esperadas"]) == (5, 3)
    assert {s["user_id"] for s in avisos(m, b.id)} <= {b.dono1, b.dono2, None}
    assert all(ch["company_id"] in (a.id, b.id) for ch in PortaDuble.chamadas)
    # o dono da corretora_b nunca veio do vínculo da corretora_a (mesmo nosnum, mesmo código de produtor)
    assert {x["dono_user_id"] for x in rb} <= {b.dono1, b.dono2}


# ---------------------------------------------------------------------------------------------------------------------
# ② idempotência
# ---------------------------------------------------------------------------------------------------------------------
def test_dois_ticks_um_run_por_passo_e_duas_preparacoes_zero_duplicata(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    for hora in ((0, 31), (0, 31), (0, 45), (2, 1), (2, 1), (2, 30)):
        tick(m, local(*hora))
    assert sorted(r["workflow_key"] for r in runs_da_renovacao(m, c.id)) == ["renovacao.calcular",
                                                                             "renovacao.preparar"]
    # fora da janela (1 h depois do horário) o tick não enfileira de novo, nem atrasado
    tick(m, local(3, 5))
    assert len(runs_da_renovacao(m, c.id)) == 2

    _preparar(m, c)
    linhas, eventos = len(m.banco.linhas("renovacoes")), len(m.banco.linhas("renovacao_eventos"))
    _preparar(m, c)
    assert (len(m.banco.linhas("renovacoes")), len(m.banco.linhas("renovacao_eventos"))) == (linhas, eventos)
    assert linhas == 5


# ---------------------------------------------------------------------------------------------------------------------
# ③ endosso
# ---------------------------------------------------------------------------------------------------------------------
def test_endosso_que_muda_o_fimvig_cria_item_novo_e_substitui_o_velho(mundo):
    m = mundo
    renov = cinco_renovacoes()
    c = montar_corretora(m, "token-a", renovacoes=renov)
    _preparar(m, c)
    (velho,) = [x for x in itens(m, c.id) if x["ramo_sigla"] == "AUTO"]
    renov[0]["fimvig"] = FIO.br(DIA + timedelta(days=12))     # o endosso mexeu no vencimento
    m.rede.cache.clear()
    _preparar(m, c)
    autos = [x for x in itens(m, c.id) if x["ramo_sigla"] == "AUTO"]
    assert len(autos) == 2
    velho = next(x for x in autos if x["id"] == velho["id"])
    novo = next(x for x in autos if x["id"] != velho["id"])
    assert velho["estado"] == "substituida" and novo["estado"] == "pronta"
    assert novo["fimvig"] == (DIA + timedelta(days=12)).isoformat()
    ev = [e for e in m.banco.linhas("renovacao_eventos") if e["renovacao_id"] == velho["id"]][-1]
    assert (ev["de"], ev["para"], ev["motivo"]) == ("pronta", "substituida", "endosso_mudou_o_fimvig")
    assert ev["dados"]["substituida_por"] == novo["id"]


# ---------------------------------------------------------------------------------------------------------------------
# ④ o motivo é obrigatório
# ---------------------------------------------------------------------------------------------------------------------
def test_pendente_e_falhou_sem_motivo_sao_recusados_pela_maquina_e_pelo_banco(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    _preparar(m, c)
    repo = R.RepositorioDeRenovacoes(m.db)
    pronta = next(x for x in itens(m, c.id) if x["estado"] == "pronta")
    for para in ("pendente", "falhou"):
        with pytest.raises(R.MotivoObrigatorio):
            repo.transicionar(c.id, pronta["id"], para, por="teste")
    # CONTROLE: com motivo passa
    assert repo.transicionar(c.id, pronta["id"], "pendente", por="teste", motivo="falta_dado")["estado"] == "pendente"
    # o banco (a trava da migration) também recusa — mesmo que um escritor fugisse da máquina
    with pytest.raises(Exception) as exc:
        m.db.table("renovacoes").update({"estado": "falhou", "motivo": None}).eq("id", pronta["id"]).execute()
    assert "ck_renovacoes_motivo" in str(exc.value)
    # transição fora da máquina
    with pytest.raises(R.TransicaoInvalida):
        repo.transicionar(c.id, pronta["id"], "enviada", por="teste")


# ---------------------------------------------------------------------------------------------------------------------
# ⑤ os estados reservados
# ---------------------------------------------------------------------------------------------------------------------
def test_estados_reservados_sao_recusados_pela_maquina(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    _preparar(m, c)
    repo = R.RepositorioDeRenovacoes(m.db)
    alvo = itens(m, c.id)[0]
    antes = (alvo["estado"], alvo["versao"])
    for estado in R.ESTADOS_RESERVADOS:
        with pytest.raises(R.EstadoReservado):
            repo.transicionar(c.id, alvo["id"], estado, por="teste", motivo="qualquer")
    alvo = next(x for x in itens(m, c.id) if x["id"] == alvo["id"])
    assert (alvo["estado"], alvo["versao"]) == antes
    assert len(R.ESTADOS_RESERVADOS) == 9 and set(R.ESTADOS_RESERVADOS).isdisjoint(R.ESTADOS_LIGADOS)
    # nenhuma transição da máquina CHEGA a um reservado
    assert not {p for destinos in R.TRANSICOES.values() for p in destinos} & set(R.ESTADOS_RESERVADOS)


def _arquivos_do_produto():
    for p in (BACKEND / "app").rglob("*.py"):
        texto = p.read_text(encoding="utf-8", errors="ignore")
        if "renovac" in texto:
            yield p, texto


def test_nenhum_escritor_do_codigo_grava_estado_reservado():
    """Por AST, em todo arquivo do produto que fala de renovação: nenhuma chamada `transicionar(…, '<reservado>')` e
    nenhum `{"estado": "<reservado>"}` — o caminho de escrita que fugiria da máquina."""
    reservados = set(R.ESTADOS_RESERVADOS)
    achados = []
    for p, texto in _arquivos_do_produto():
        arvore = ast.parse(texto)
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call) and getattr(no.func, "attr", getattr(no.func, "id", "")) == "transicionar":
                for arg in list(no.args) + [k.value for k in no.keywords if k.arg == "para"]:
                    if isinstance(arg, ast.Constant) and arg.value in reservados:
                        achados.append(f"{p.name}:{no.lineno} transicionar(…, {arg.value!r})")
            if isinstance(no, ast.Dict):
                for k, v in zip(no.keys, no.values):
                    if (isinstance(k, ast.Constant) and k.value == "estado" and isinstance(v, ast.Constant)
                            and v.value in reservados):
                        achados.append(f"{p.name}:{no.lineno} {{'estado': {v.value!r}}}")
    assert achados == [], achados
    # CONTROLE: o guarda consegue ficar vermelho (o mesmo AST sobre um escritor fora da máquina)
    ruim = ast.parse("repo.transicionar(cid, rid, 'vista', por='x')")
    assert any(isinstance(n, ast.Constant) and n.value in reservados for n in ast.walk(ruim))


# ---------------------------------------------------------------------------------------------------------------------
# ⑥ a conferência: outro caminho, a InfoCap de novo
# ---------------------------------------------------------------------------------------------------------------------
def test_a_conferencia_nao_importa_o_montador():
    caminho = BACKEND / "app" / "services" / "multicalculo" / "conferencia_da_renovacao.py"
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    importados = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados += [a.name for a in no.names]
        elif isinstance(no, ast.ImportFrom):
            importados += [f"{no.module}.{a.name}" for a in no.names]
    assert importados, "o guarda não leu nenhum import (ficaria verde sem olhar)"
    assert not [i for i in importados if "madrugada" in i], importados
    # e ela LÊ a InfoCap (o nome da leitura está no código dela)
    assert "renovacoes_cruas" in caminho.read_text(encoding="utf-8")


def test_a_conferencia_acha_a_renovacao_que_a_preparacao_esqueceu(mundo):
    """A InfoCap instável: às 00:30 ela devolveu 4; às 05:30, 5. A conferência relê, cria o item, grava o evento
    `esquecida_pela_preparacao` e o dia fica VERMELHO, com alerta à corretora."""
    m = mundo
    todas = cinco_renovacoes()
    c = montar_corretora(m, "token-a", renovacoes=todas[:4])
    _preparar(m, c)
    assert len(itens(m, c.id)) == 4
    m.rede.bancos["token-a"]["renov"] = todas
    m.rede.cache.clear()
    r = _conferir(m, c)
    assert (r["estado"], r["faltaram"]) == ("vermelho", 1)
    d = _dia(m, c)
    assert (d["estado"], d["esperadas"], d["faltaram"]) == ("vermelho", 5, 1)
    (nova,) = [x for x in itens(m, c.id) if x["ramo_sigla"] == "XYZW"]
    (ev,) = [e for e in m.banco.linhas("renovacao_eventos") if e["renovacao_id"] == nova["id"]]
    assert (ev["de"], ev["para"], ev["por"], ev["motivo"]) == (None, "listada", "conferencia",
                                                               "esquecida_pela_preparacao")
    alertas = publicacoes(m, c.id, "conferencia")
    assert len(alertas) == 1 and alertas[0]["briefing_type"] == "critical_alert" and alertas[0]["user_id"] is None
    # CONTROLE: com a InfoCap igual à lista, nada falta e o dia não é vermelho
    m2_itens = len(itens(m, c.id))
    r2 = _conferir(m, c)
    assert r2["faltaram"] == 0 and r2["estado"] != "vermelho" and len(itens(m, c.id)) == m2_itens


def test_infocap_fora_na_conferencia_e_sem_conexao_nunca_zero(mundo, monkeypatch):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    _preparar(m, c)

    def _quebrada(*_a, **_k):
        raise ConnectionError("rede fora")

    monkeypatch.setattr(c.fonte, "renovacoes_cruas", _quebrada)
    r = _conferir(m, c)
    d = _dia(m, c)
    assert r["estado"] == d["estado"] == "sem_conexao"
    assert d["esperadas"] is None and d["completude_pct"] is None and d["calculadas"] is None
    alertas = publicacoes(m, c.id, "conferencia")
    assert len(alertas) == 1 and alertas[0]["briefing_type"] == "critical_alert"


# ---------------------------------------------------------------------------------------------------------------------
# ⑧ ausência
# ---------------------------------------------------------------------------------------------------------------------
def test_ausencia_o_aviso_vai_ao_substituto_e_o_calculo_segue_com_o_dono(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    m.banco.semear("membro_ausencias", {"company_id": c.id, "user_id": c.dono2, "substituto_user_id": c.admin,
                                        "de": (DIA - timedelta(days=2)).isoformat(),
                                        "ate": (DIA + timedelta(days=5)).isoformat()})
    madrugada_inteira(m, c)
    (cond,) = [x for x in itens(m, c.id) if x["ramo_sigla"] == "COND"]
    assert (cond["dono_user_id"], cond["responsavel_user_id"], cond["estado"]) == (c.dono2, c.admin, "calculada")
    assert next(ch for ch in PortaDuble.chamadas if ch["ramo"] == 16)["dono_user_id"] == c.dono2
    assert {s["user_id"] for s in avisos(m, c.id)} == {c.dono1, c.admin, None}


# ---------------------------------------------------------------------------------------------------------------------
# ⑨ derivado, aguardando e o desvio
# ---------------------------------------------------------------------------------------------------------------------
def test_estado_derivado_dos_calculos():
    fechado = {"status": "fechado"}
    assert M.estado_derivado([], 0, False) == ("calculando", None)
    assert M.estado_derivado([fechado, fechado], 1, False) == ("calculada", None)
    assert M.estado_derivado([{"status": "falhou", "erro": "agger_da_pessoa_em_uso — a dona…"}], 0, False) == \
        ("falhou", "agger_da_pessoa_em_uso")
    assert M.estado_derivado([{"status": "expirado"}], 0, False) == ("falhou", "calculo_expirado")
    assert M.estado_derivado([fechado, {"status": "na_fila"}], 1, True) == ("aguardando_agger", None)
    assert M.estado_derivado([fechado, {"status": "calculando"}], 1, False) == ("calculando", None)


def test_a_dona_no_proprio_agger_vira_aguardando_e_o_desvio_vai_a_corretora_com_aviso(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    tick(m, local(0, 31))
    rodar(m, run_do_passo(m, c.id, "preparar")["id"], c.id)
    tick(m, local(2, 1))
    calc = run_do_passo(m, c.id, "calcular")
    rodar(m, calc["id"], c.id)
    (auto,) = [x for x in itens(m, c.id) if x["ramo_sigla"] == "AUTO"]
    pedido_da_dona = auto["pedido_id"]          # ⚠️ `itens` devolve a linha VIVA do banco dublê: guardar o valor
    outros = [x["pedido_id"] for x in itens(m, c.id) if x.get("pedido_id") and x["id"] != auto["id"]]
    fechar_com_ofertas(m.banco, outros)
    # o motor achou a dona no próprio Agger: o cálculo volta à fila com o evento (motor._vezes_da_pessoa_em_uso)
    for calc_linha in [x for x in m.banco.linhas("multicalculo_calculos") if x["pedido_id"] == pedido_da_dona]:
        m.banco.semear("multicalculo_eventos", {"calculo_id": calc_linha["id"], "pedido_id": pedido_da_dona,
                                                "company_id": c.id, "solicitante_company_id": c.id,
                                                "tipo": "agger_da_pessoa_em_uso", "chave": f"pessoa:{calc_linha['id']}"})
    acordar(m, calc["id"])
    rodar(m, calc["id"], c.id)
    assert next(x for x in itens(m, c.id) if x["id"] == auto["id"])["estado"] == "aguardando_agger"
    # 05:31: o calcular para de esperar (passou da conferência) sem inventar estado
    while m.banco.run(calc["id"])["status"] == "waiting_input":
        acordar(m, calc["id"])
        rodar(m, calc["id"], c.id)
    assert m.banco.run(calc["id"])["status"] == "completed"
    tick(m, local(5, 31))
    rodar(m, run_do_passo(m, c.id, "conferir")["id"], c.id)
    d = _dia(m, c)
    assert (d["calculadas"], d["pendentes"], d["estado"]) == (2, 2, "incompleto")   # aguardando NÃO conta como feito
    # 06:16 desvio: a porta recebe o pedido de forçar o Agger da corretora, e o dono recebe o aviso nomeado
    antes = len(PortaDuble.chamadas)
    tick(m, local(6, 16))
    desv = run_do_passo(m, c.id, "desvio")
    rodar(m, desv["id"], c.id)
    nova = PortaDuble.chamadas[antes:]
    assert len(nova) == 1 and nova[0]["forcar_corretora_motivo"] == M.MOTIVO_DO_DESVIO and nova[0]["ramo"] == 31
    item = next(x for x in itens(m, c.id) if x["id"] == auto["id"])
    assert item["estado"] == "calculando" and item["pedido_id"] != pedido_da_dona
    aviso = publicacoes(m, c.id, "desvio")
    assert len(aviso) == 1 and aviso[0]["user_id"] == c.dono1 and "Agger da CORRETORA" in aviso[0]["summary_text"]
    fechar_com_ofertas(m.banco, [item["pedido_id"]])
    acordar(m, desv["id"])
    rodar(m, desv["id"], c.id)
    assert next(x for x in itens(m, c.id) if x["id"] == auto["id"])["estado"] == "calculada"


def test_renovacao_nunca_pede_economica_nem_minima():
    assert R.parametros({"servicos": {"renovacao": {"opcoes": ["economica", "minima", "anterior"]}}})["opcoes"] == \
        ["anterior"]
    assert R.parametros({})["opcoes"] == ["anterior", "franquia_reduzida", "completa_mais"]
    assert R.parametros({})["antecedencia_dias"] == 10


def test_documento_so_mascarado_e_nome_so_o_primeiro():
    assert R.mascarar_documento("000.000.000-00") == "***.***.***-00"
    assert R.mascarar_documento("00.000.000/0000-00") == "**.***.***/****-00"
    assert R.primeiro_nome("CLIENTE FICTICIO DE TESTE") == "Cliente"
    assert R.primeiro_nome("  ") is None


# ---------------------------------------------------------------------------------------------------------------------
# ⑩ o FUSO da corretora (BLOCO 0 A8: `tick._janela` é UTC — a madrugada não pode ser)
# ---------------------------------------------------------------------------------------------------------------------
def test_o_horario_e_o_dia_sao_do_fuso_da_corretora(mundo):
    from datetime import datetime, timezone

    m = mundo
    sp = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    mao = montar_corretora(m, "token-b", renovacoes=cinco_renovacoes()[:2])
    m.banco.semear("briefing_profiles", {"company_id": mao.id, "cadence": "daily", "is_active": True,
                                         "timezone": "America/Manaus", "schedule_spec": {"time": "08:00"}})
    # 03:15 UTC = 00:15 em São Paulo: ainda NÃO prepara
    tick(m, datetime(2026, 10, 13, 3, 15, tzinfo=timezone.utc))
    assert runs_da_renovacao(m) == []
    # 03:31 UTC = 00:31 em São Paulo (prepara) = 23:31 de ONTEM em Manaus (não prepara)
    tick(m, datetime(2026, 10, 13, 3, 31, tzinfo=timezone.utc))
    assert [r["idempotency_key"] for r in runs_da_renovacao(m)] == [f"renov:preparar:{sp.id}:2026-10-13"]
    # 04:31 UTC = 00:31 em Manaus: a de Manaus prepara, com o dia LOCAL dela
    tick(m, datetime(2026, 10, 13, 4, 31, tzinfo=timezone.utc))
    assert sorted(r["idempotency_key"] for r in runs_da_renovacao(m, mao.id)) ==         [f"renov:preparar:{mao.id}:2026-10-13"]
    # o passo é de UM dia local: 03:00 UTC do dia 14 = 00:00 local do 14 em SP → nada (antes das 00:30)
    tick(m, datetime(2026, 10, 14, 3, 0, tzinfo=timezone.utc))
    assert len(runs_da_renovacao(m, sp.id)) == 1


# ---------------------------------------------------------------------------------------------------------------------
# ⑪ o PICO (D-131-33): teto por conta por noite + antecipação; a vencida nunca é cortada
# ---------------------------------------------------------------------------------------------------------------------
def _pronta(dono, calcular_em, n):
    return {"id": f"x{n}", "dono_user_id": dono, "calcular_em": calcular_em.isoformat(),
            "fimvig": (calcular_em + timedelta(days=10)).isoformat(), "ramo_agger": 2, "nosnum": str(n)}


def test_o_teto_por_conta_antecipa_a_sobra_e_nunca_corta_a_vencida():
    a, b = "dono-a", "dono-b"
    vencidas_a = [_pronta(a, DIA - timedelta(days=k % 2), k) for k in range(15)]       # 15 > teto 12
    futuras_a = [_pronta(a, DIA + timedelta(days=3), 100 + k) for k in range(5)]
    futuras_b = [_pronta(b, DIA + timedelta(days=d), 200 + d) for d in range(1, 11)]   # dia+1 … dia+10
    escolhidos, conta = M.escolher_da_noite(vencidas_a + futuras_a + futuras_b, DIA, teto=12, antecipar_ate_dias=7)
    ids = [x["id"] for x in escolhidos]
    assert all(x["id"] in ids for x in vencidas_a), "uma vencida foi cortada pelo teto"
    assert not any(x["id"] in ids for x in futuras_a), "antecipou numa conta que já passou do teto"
    assert [x["id"] for x in escolhidos if x["dono_user_id"] == b] == [f"x{200 + d}" for d in range(1, 8)]
    assert conta == {"vencidas": 15, "antecipadas": 7, "acima_do_teto": 3}
    assert ids[:15] == [x["id"] for x in sorted(vencidas_a, key=lambda x: (x["fimvig"], 2, x["nosnum"]))]
    # CONTROLE: com teto folgado a sobra da conta A também é antecipada
    _, folgado = M.escolher_da_noite(vencidas_a + futuras_a, DIA, teto=30, antecipar_ate_dias=7)
    assert folgado == {"vencidas": 15, "antecipadas": 5, "acima_do_teto": 0}


def test_a_antecipada_sai_esta_noite_mas_nao_e_cobrada_pela_conferencia(mundo):
    m = mundo
    hoje = [linha_renov(930001, "AUTO", DIA + timedelta(days=10)), linha_renov(930002, "RESI", DIA + timedelta(days=10))]
    adiante = [linha_renov(930003, "COND", DIA + timedelta(days=13)), linha_renov(930004, "AUTO", DIA + timedelta(days=16))]
    c = montar_corretora(m, "token-a", renovacoes=hoje + adiante)
    _preparar(m, c)
    assert sorted(x["estado"] for x in itens(m, c.id)) == ["pronta"] * 4
    r = asyncio.run(M.calcular_dia(m.db, c.id, DIA))
    assert (r["vencidas"], r["antecipadas"], r["acima_do_teto"], r["disparados"]) == (2, 2, 0, 4)
    fechar_com_ofertas(m.banco, [x["pedido_id"] for x in itens(m, c.id) if x.get("pedido_id")])
    M.acompanhar(m.db, c.id, por="teste")
    conf = _conferir(m, c)
    d = _dia(m, c)
    assert (d["esperadas"], d["calculadas"], float(d["completude_pct"])) == (2, 2, 100.0)
    assert conf["estado"] == "completo"
    M.avisar_dia(m.db, c.id, DIA)
    (geral,) = [p for p in avisos(m, c.id) if p["user_id"] is None]
    assert "4 prontas no Agger" in geral["summary_text"] and "2 antecipada(s)" in geral["summary_text"]


def test_a_conferencia_acusa_o_item_que_o_montador_deixou_cair(mundo):
    """O ELO da SPEC (mutação 1): a InfoCap é a MESMA nas duas leituras; se o MONTADOR perder um item, quem acusa é a
    conferência (dia VERMELHO, faltaram = 1) — não um teste do montador. Sem a mutação: 0 faltou, dia não vermelho."""
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    _preparar(m, c)
    m.rede.cache.clear()
    r = _conferir(m, c)
    assert (r["faltaram"], r["estado"] == "vermelho") == (0, False), \
        f"a conferência achou {r['faltaram']} renovação(ões) que a lista do dia esqueceu (dia {r['estado']})"
