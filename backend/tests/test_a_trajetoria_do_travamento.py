# -*- coding: utf-8 -*-
"""A trajetória do travamento — SPEC-090, BLOCO B.

> **O TESTE DO PRODUTO:** *"por travamento: rota · tela · motivo · quem
> destravou · quanto tempo ficou"*, e **quantos ficaram sem destravar** — porque
> um travamento que nunca destravou é um segurado que nunca foi atendido.

## 📊 O estado medido em 26/08/2026

```
work_events ................................. 28.286 linhas
  `travamento.aberto` + `travamento.destravado` ....  0
```

⚠️ **Não falta código — falta o piloto rodar.** A SPEC-093 já gravou o gravador
e ele está na `main`. Estes guardas testam a LEITURA contra eventos construídos
à mão, exatamente com a forma que `eventos_do_travamento` produz.

🔴 **E é por isso que eles importam agora:** na segunda-feira a tabela enche com
dados reais, e uma leitura errada só apareceria depois — no relatório de
terça-feira, que é o entregável desta SPEC.
"""
from __future__ import annotations

import importlib.util as _u
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ROTEADOR_PY = RAIZ / "app" / "services" / "dispatch_router.py"


def _carregar(rel: str, nome: str):
    spec = _u.spec_from_file_location(nome, RAIZ / rel)
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LEITURA = _carregar("app/services/o_dia_de_ontem.py", "_leitura_090B")

RUN_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
RUN_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
EMPRESA_1 = "11111111-1111-1111-1111-111111111111"
EMPRESA_2 = "22222222-2222-2222-2222-222222222222"


def _aberto(run, quando, *, id_=1, rota="porto-auto", tela="Informe a placa",
            motivo="tela desconhecida", empresa=EMPRESA_1):
    return {"id": id_, "company_id": empresa, "work_run_id": run,
            "event_type": "travamento.aberto", "created_at": quando,
            "payload_redacted": {"rota": rota, "tela": tela, "motivo": motivo,
                                 "fase_anterior": "ura"}}


def _destravado(run, quando, *, id_=2, por="robo", rota="porto-auto",
                tela="Informe a placa", segundos=None, canal=None,
                empresa=EMPRESA_1):
    carga = {"rota": rota, "tela": tela, "por": por, "fase": "ura"}
    if segundos is not None:
        carga["segundos_travado"] = segundos
    if canal:
        carga["canal"] = canal
    return {"id": id_, "company_id": empresa, "work_run_id": run,
            "event_type": "travamento.destravado", "created_at": quando,
            "payload_redacted": carga}


# =============================================================================
# 🔴 CONTROLE DE CARGA
# =============================================================================

def test_CONTROLE_o_modulo_carregou():
    assert callable(LEITURA.trajetoria_dos_travamentos)
    assert callable(LEITURA.resumo_dos_travamentos)
    assert LEITURA.ABERTO == "travamento.aberto"
    assert LEITURA.DESTRAVADO == "travamento.destravado"


def test_CONTROLE_a_leitura_usa_OS_MESMOS_nomes_que_o_escritor():
    """🔴 §9.3 e §5 — duas listas que precisam concordar divergem.

    ⚠️ Se `dispatch_router` renomear o evento ou a chave do payload, esta
    leitura fica em silêncio: ela não acha nada e devolve `[]`, que é
    indistinguível de *"não travou nada ontem"*. **O silêncio é o defeito.**
    """
    fonte = ROTEADOR_PY.read_text(encoding="utf-8")
    assert f'"tipo": "{LEITURA.ABERTO}"' in fonte, (
        f"o escritor não emite {LEITURA.ABERTO!r} — a leitura ficaria muda")
    assert f'"tipo": "{LEITURA.DESTRAVADO}"' in fonte
    # as chaves que a leitura lê do payload
    for chave in ('"rota"', '"tela"', '"motivo"', '"por"'):
        assert chave in fonte, f"o escritor não grava {chave} no payload"
    assert '"segundos_travado"' in fonte or "segundos_travado" in fonte


# =============================================================================
# ① os cinco campos
# =============================================================================

def test_um_travamento_fechado_traz_os_CINCO_campos():
    t = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00"),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", por="humano", segundos=300),
    ])
    assert len(t) == 1
    (t0,) = t
    assert t0["rota"] == "porto-auto"
    assert t0["tela"] == "Informe a placa"
    assert t0["motivo"] == "tela desconhecida"
    assert t0["quem_destravou"] == "humano"
    assert t0["segundos"] == 300
    assert t0["ainda_travado"] is False


def test_o_tempo_MEDIDO_vence_o_deduzido_e_a_fonte_e_declarada():
    """📊 §12.1 aplicado a número calculado.

    ⚠️ `payload.segundos_travado` sai de `travado_desde`; os `created_at` são a
    hora em que a LINHA foi escrita. Não são a mesma coisa, e quem lê o
    relatório precisa saber qual dos dois está vendo.
    """
    t, = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00"),
        # 📊 os eventos dizem 600 s; o escritor mediu 412
        _destravado(RUN_A, "2026-08-25T10:10:00+00:00", segundos=412),
    ])
    assert t["segundos"] == 412, "o tempo deduzido venceu o medido"
    assert t["fonte_do_tempo"] == LEITURA.TEMPO_MEDIDO


def test_SEM_o_medido_o_tempo_e_DEDUZIDO_e_marcado_como_tal():
    t, = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00"),
        _destravado(RUN_A, "2026-08-25T10:10:00+00:00"),
    ])
    assert t["segundos"] == 600
    assert t["fonte_do_tempo"] == LEITURA.TEMPO_DEDUZIDO, (
        "um tempo deduzido passando por medido dá firmeza falsa ao relatório")


# =============================================================================
# ② destravado por HUMANO diz `humano`, não `robo`
# =============================================================================

def test_destravado_por_HUMANO_nao_vira_robo():
    """Gate ② — 🔴 é o crédito do trabalho da Regina e da Saionara.

    ⚠️ Na SPEC-093 este exato campo já foi lido errado uma vez: um conserto
    creditava humano a partir de `assumido_por_humano`, que é STICKY — e todo
    destrave posterior daquele run virava trabalho humano (P-259).
    """
    t, = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00"),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", por="humano"),
    ])
    assert t["quem_destravou"] == "humano"


def test_CONTROLE_destravado_pelo_ROBO_diz_robo():
    """§9.3 — sem esta linha, um `return "humano"` fixo passaria acima."""
    t, = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00"),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", por="robo"),
    ])
    assert t["quem_destravou"] == "robo"


def test_cada_destravador_da_093_chega_inteiro_na_trajetoria():
    """🔴 Os cinco valores que a SPEC-093 grava, sem tradução no caminho."""
    roteador = ROTEADOR_PY.read_text(encoding="utf-8")
    assert 'DESTRAVADORES = ("humano", "cerebro", "sentinela", "vigia", "robo")' in roteador
    for por in ("humano", "cerebro", "sentinela", "vigia", "robo"):
        t, = LEITURA.trajetoria_dos_travamentos([
            _aberto(RUN_A, "2026-08-25T10:00:00+00:00"),
            _destravado(RUN_A, "2026-08-25T10:05:00+00:00", por=por),
        ])
        assert t["quem_destravou"] == por, f"{por} virou {t['quem_destravou']}"


# =============================================================================
# ③ 🔴 O QUE NUNCA DESTRAVOU — o gate mais importante do bloco
# =============================================================================

def test_travamento_que_NUNCA_destravou_APARECE():
    """🔴 Gate ③, e a SPEC diz que é o mais importante.

    ⛔ Uma leitura que só emparelhasse `aberto` com `destravado` faria estes
    SUMIREM — e o relatório da terça diria *"3 travamentos, todos resolvidos"*
    num dia em que quatro pessoas ficaram esperando.

    **O travamento aberto é o número que importa, não o caso de borda.**
    """
    t = LEITURA.trajetoria_dos_travamentos(
        [_aberto(RUN_A, "2026-08-25T10:00:00+00:00")],
        agora_iso="2026-08-25T12:00:00+00:00")
    assert len(t) == 1, "o travamento aberto SUMIU da trajetória"
    assert t[0]["ainda_travado"] is True
    assert t[0]["quem_destravou"] is None
    assert t[0]["segundos"] == 7200
    assert t[0]["fonte_do_tempo"] == LEITURA.TEMPO_ABERTO


def test_dois_ABERTOS_seguidos_o_primeiro_nao_some():
    """⚠️ Um `aberto` sem fechamento seguido de outro `aberto`: o produto travou
    duas vezes, e a leitura tem de contar duas."""
    t = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00", id_=1),
        _aberto(RUN_A, "2026-08-25T11:00:00+00:00", id_=2, tela="Digite o CPF"),
    ], agora_iso="2026-08-25T12:00:00+00:00")
    assert len(t) == 2, f"contou {len(t)} — um travamento sumiu"
    assert all(x["ainda_travado"] for x in t)
    assert [x["tela"] for x in t] == ["Informe a placa", "Digite o CPF"]


def test_DESTRAVADO_orfao_tambem_entra():
    """⚠️ O par partido pela JANELA DE LEITURA: travou 23h50 de ontem, destravou
    00h10 de hoje. ⛔ Descartar seria sumir com um travamento que existiu — a
    mesma família de erro do gate ③."""
    t = LEITURA.trajetoria_dos_travamentos([
        _destravado(RUN_A, "2026-08-25T00:10:00+00:00", por="humano")])
    assert len(t) == 1
    assert t[0]["aberto_em"] is None
    assert t[0]["quem_destravou"] == "humano"
    assert t[0]["segundos"] is None, "inventou um tempo sem saber quando começou"
    assert t[0]["ainda_travado"] is False


def test_travou_destravou_e_travou_DE_NOVO_conta_DUAS_vezes():
    """🔴 A razão de a SPEC-093 gravar EVENTO e não coluna.

    📊 `work_runs.unblock_state` é uma coluna: as duas primeiras vezes somem.
    """
    t = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00", id_=1),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", id_=2, por="cerebro"),
        _aberto(RUN_A, "2026-08-25T11:00:00+00:00", id_=3, tela="Digite o CPF"),
        _destravado(RUN_A, "2026-08-25T11:30:00+00:00", id_=4, por="humano"),
    ])
    assert len(t) == 2
    assert [x["quem_destravou"] for x in t] == ["cerebro", "humano"]
    assert [x["segundos"] for x in t] == [300, 1800]


def test_o_resumo_NAO_dilui_o_aberto_na_mediana():
    """⚠️ O aberto ainda está contando: ele sobe sozinho a cada hora, e a
    mediana de segunda-feira mudaria a cada vez que o relatório fosse aberto."""
    r = LEITURA.resumo_dos_travamentos(LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00", id_=1),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", id_=2, segundos=300),
        _aberto(RUN_B, "2026-08-25T09:00:00+00:00", id_=3),
    ], agora_iso="2026-08-25T23:00:00+00:00"))
    assert r["travamentos"] == 2
    assert r["destravados"] == 1
    assert r["ainda_travados"] == 1
    assert r["segundos_mediano"] == 300, (
        "as 14 horas do travamento ABERTO entraram na mediana")
    assert r["tempos_considerados"] == 1


def test_a_lista_de_conserto_poe_o_ABERTO_na_frente():
    """🔴 *"as que mais travam — é a lista de conserto do dia seguinte"*.

    ⚠️ Uma rota que trava 10 vezes e destrava sozinha nas 10 dói MENOS que uma
    que trava 3 e deixa as 3 pessoas esperando. Ordenar só pelo total manda
    consertar a errada.
    """
    eventos = []
    for i in range(10):  # rota barulhenta, mas sempre destrava
        eventos += [_aberto(RUN_A, f"2026-08-25T1{i}:00:00+00:00", id_=i * 2,
                            rota="allianz-auto", tela="menu"),
                    _destravado(RUN_A, f"2026-08-25T1{i}:01:00+00:00", id_=i * 2 + 1,
                                rota="allianz-auto", tela="menu")]
    for i in range(3):  # rota que DEIXA GENTE ESPERANDO
        eventos.append(_aberto(RUN_B, f"2026-08-25T0{i}:00:00+00:00", id_=100 + i,
                               rota="zurich-auto", tela="Informe a placa"))
    rotas = LEITURA.as_rotas_que_mais_travam(
        LEITURA.trajetoria_dos_travamentos(eventos, agora_iso="2026-08-26T00:00:00+00:00"))
    assert rotas[0]["rota"] == "zurich-auto", (
        f"a lista começa por {rotas[0]['rota']} — a rota que trava mais vezes "
        "veio antes da que deixa gente esperando")
    assert rotas[0]["sem_destravar"] == 3
    assert rotas[1]["travou"] == 10 and rotas[1]["sem_destravar"] == 0


# =============================================================================
# ④ 🔴 DOIS TENANTS
# =============================================================================

def test_dois_tenants_nao_se_misturam_no_mesmo_run():
    """⚠️ O `work_run_id` é a chave de emparelhamento, e ele é único no banco —
    mas a leitura não pode DEPENDER disso: se dois eventos de corretoras
    diferentes chegarem com o mesmo run, o travamento sai com uma corretora
    só, e o relatório de uma corretora conta o travamento da outra."""
    t = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00", id_=1, empresa=EMPRESA_1),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", id_=2, empresa=EMPRESA_1),
    ])
    assert t[0]["company_id"] == EMPRESA_1


def test_a_trajetoria_carrega_a_corretora_em_TODA_linha():
    """🔴 Sem `company_id` na saída, quem chama não tem como conferir o §7 — e
    um relatório que perde o dono do dado é um vazamento esperando acontecer."""
    t = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00", empresa=EMPRESA_2)],
        agora_iso="2026-08-25T11:00:00+00:00")
    assert t[0]["company_id"] == EMPRESA_2
    assert all("company_id" in x for x in t)


# =============================================================================
# ⑤ a conversa vem de QUEM CHAMA — o campo não se inventa
# =============================================================================

def test_a_conversa_vem_do_mapa_e_nao_de_um_campo_inexistente():
    """📊 `work_events` tem 12 colunas e NENHUMA é de conversa (medido).

    ⛔ Ler `e.get("conversation_id")` devolveria `None` sempre — um campo que
    nasce vazio e parece que só não foi preenchido ainda. Quem sabe é
    `work_runs.conversation_id`, que o BLOCO A criou.
    """
    conversa = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    t = LEITURA.trajetoria_dos_travamentos(
        [_aberto(RUN_A, "2026-08-25T10:00:00+00:00")],
        agora_iso="2026-08-25T11:00:00+00:00",
        conversa_por_run={RUN_A: conversa})
    assert t[0]["conversation_id"] == conversa


def test_SEM_o_mapa_a_conversa_e_NULA_e_nao_um_engano():
    t = LEITURA.trajetoria_dos_travamentos(
        [_aberto(RUN_A, "2026-08-25T10:00:00+00:00")],
        agora_iso="2026-08-25T11:00:00+00:00")
    assert t[0]["conversation_id"] is None


# =============================================================================
# ⑥ o que NÃO derruba a leitura
# =============================================================================

def test_evento_de_OUTRO_tipo_e_ignorado_sem_derrubar():
    """📊 `work_events` tem 28.286 linhas e as mais recentes são `step.completed`,
    `run.started`, `run.leased` — a leitura passa por elas todo dia."""
    t = LEITURA.trajetoria_dos_travamentos([
        {"id": 9, "company_id": EMPRESA_1, "work_run_id": RUN_A,
         "event_type": "run.started", "created_at": "2026-08-25T09:00:00+00:00",
         "payload_redacted": {}},
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00"),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00"),
    ])
    assert len(t) == 1


def test_payload_que_nao_e_dict_nao_derruba():
    e = _aberto(RUN_A, "2026-08-25T10:00:00+00:00")
    e["payload_redacted"] = "isto nao e um dict"
    t = LEITURA.trajetoria_dos_travamentos([e], agora_iso="2026-08-25T11:00:00+00:00")
    assert len(t) == 1 and t[0]["rota"] == ""


def test_hora_quebrada_nao_derruba_e_nao_inventa_tempo():
    t = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "hora invalida"),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00"),
    ])
    assert len(t) == 1
    assert t[0]["segundos"] is None, "inventou um tempo a partir de hora inválida"


def test_lista_vazia_devolve_lista_vazia_e_resumo_ZERADO():
    """Gate ② do BLOCO D — *"dia sem atendimento → zeros, não erro"*."""
    assert LEITURA.trajetoria_dos_travamentos([]) == []
    r = LEITURA.resumo_dos_travamentos([])
    assert r["travamentos"] == 0 and r["ainda_travados"] == 0
    assert r["segundos_mediano"] is None, (
        "um dia sem travamento devolveu um número de mediana — zero minutos de "
        "travamento e 'mediana 0' contam histórias diferentes")
    assert r["rotas"] == []


def test_a_mediana_de_DOIS_tempos_e_a_media_dos_dois():
    r = LEITURA.resumo_dos_travamentos(LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00", id_=1),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", id_=2, segundos=100),
        _aberto(RUN_B, "2026-08-25T11:00:00+00:00", id_=3),
        _destravado(RUN_B, "2026-08-25T11:05:00+00:00", id_=4, segundos=300),
    ]))
    assert r["segundos_mediano"] == 200
    assert r["fontes_do_tempo"] == {LEITURA.TEMPO_MEDIDO: 2}


# =============================================================================
# 🔴 OS DOIS DEFEITOS QUE A PRIMEIRA RODADA PEGOU — a lição migra (§9.3)
# =============================================================================

def test_TODA_linha_da_trajetoria_tem_AS_MESMAS_chaves():
    """🔴 O órfão nascia com SEIS chaves em vez de doze.

    ⚠️ Um consumidor que fizesse `t["segundos"]` levava `KeyError` exatamente na
    linha mais rara — a que só aparece na virada da meia-noite, quando o par
    abre/fecha é partido pela janela de leitura. **É a forma que ninguém testa
    à mão.**
    """
    normal, = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00"),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", segundos=300),
    ])
    orfao, = LEITURA.trajetoria_dos_travamentos([
        _destravado(RUN_B, "2026-08-25T00:10:00+00:00")])
    aberto, = LEITURA.trajetoria_dos_travamentos(
        [_aberto(RUN_B, "2026-08-25T10:00:00+00:00")],
        agora_iso="2026-08-25T11:00:00+00:00")

    assert set(normal) == set(orfao) == set(aberto), (
        "as três formas de travamento têm chaves diferentes:\n"
        f"  só no normal: {set(normal) - set(orfao) - set(aberto)}\n"
        f"  só no órfão:  {set(orfao) - set(normal)}\n"
        f"  só no aberto: {set(aberto) - set(normal)}")
    # e o resumo consegue percorrer as três sem levantar
    LEITURA.resumo_dos_travamentos([normal, orfao, aberto])


def test_hora_ILEGIVEL_nao_reordena_os_eventos():
    """🔴 Com `created_at` na frente da ordenação, UM travamento virava DOIS.

    📊 A ordenação era por texto: `"hora invalida"` começa com `h` e vai **depois**
    de `"2026-…"`. O `aberto` caía atrás do `destravado`, e a leitura produzia um
    órfão de fechamento MAIS um aberto que nunca fechou.

    ⛔ **Um relatório que inventa um travamento é tão ruim quanto um que
    esconde** — e este inventava justamente na direção que assusta.
    """
    t = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "hora invalida", id_=1),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", id_=2, por="humano"),
    ])
    assert len(t) == 1, (
        f"a hora ilegível virou {len(t)} travamentos — a ordenação por texto "
        "pôs o fechamento antes da abertura")
    assert t[0]["quem_destravou"] == "humano"
    assert t[0]["segundos"] is None


def test_CONTROLE_a_ordem_por_id_ainda_respeita_a_sequencia():
    """§9.3 — prove que a ordenação **consegue** distinguir duas ordens.

    ⛔ Sem esta linha, um `sorted` que devolvesse a lista intocada passaria em
    todos os testes acima.
    """
    embaralhado = [
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", id_=2, por="cerebro"),
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00", id_=1),
    ]
    t, = LEITURA.trajetoria_dos_travamentos(embaralhado)
    assert t["aberto_em"] == "2026-08-25T10:00:00+00:00", (
        "a lista embaralhada não foi reordenada — o `sorted` não está fazendo nada")
    assert t["quem_destravou"] == "cerebro"
    assert t["segundos"] == 300


def test_duracao_NEGATIVA_vira_None_e_nao_um_numero_absurdo():
    """🔴 *"destravou cinco minutos ANTES de travar"* não é um número, é um erro.

    ⚠️ **E com a ordenação por `id`, isto é possível de verdade.** Os dois
    eventos são escritos por chamadas diferentes: um ajuste de relógio entre
    elas — NTP, contêiner reiniciado, réplica com deriva — inverte os
    `created_at` sem inverter os ids.

    ⛔ O `-300` entraria na mediana e a puxaria para baixo em silêncio. `None`
    faz o travamento contar como fato e não contar como tempo, que é
    exatamente o que se sabe sobre ele.
    """
    t, = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:05:00+00:00", id_=1),
        _destravado(RUN_A, "2026-08-25T10:00:00+00:00", id_=2),   # 5 min ANTES
    ])
    assert t["segundos"] is None, (
        f"a duração saiu {t['segundos']} — um número negativo entra na mediana e "
        "a puxa para baixo sem ninguém ver")
    assert t["fonte_do_tempo"] is None
    assert t["quem_destravou"] == "robo", "o FATO do destrave continua valendo"

    # e ele não estraga o resumo
    r = LEITURA.resumo_dos_travamentos([t])
    assert r["destravados"] == 1
    assert r["segundos_mediano"] is None
    assert r["tempos_considerados"] == 0
    assert r["fontes_do_tempo"] == {"sem_tempo": 1}


def test_CONTROLE_a_duracao_POSITIVA_continua_valendo():
    """§9.3 — prove que o guarda **consegue** deixar passar."""
    t, = LEITURA.trajetoria_dos_travamentos([
        _aberto(RUN_A, "2026-08-25T10:00:00+00:00", id_=1),
        _destravado(RUN_A, "2026-08-25T10:05:00+00:00", id_=2),
    ])
    assert t["segundos"] == 300
    assert t["fonte_do_tempo"] == LEITURA.TEMPO_DEDUZIDO
