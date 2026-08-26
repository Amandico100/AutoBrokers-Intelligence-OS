# -*- coding: utf-8 -*-
"""A pergunta de terça-feira — SPEC-090, BLOCO D.

> **O TESTE DO PRODUTO:** *"Terça de manhã. O Founder abre o chat e escreve 'o
> que aconteceu ontem?' — e recebe: quantos atendimentos, quantos travaram, em
> que telas, quem destravou, quanto tempo, e o que a Regina anotou."*

## 🔴 O gate ③ é o que mata relatório: o teto silencioso

📊 A própria SPEC registra o caso em P-090-03: `conversation_auditor.py` tem
`limit(200)` e uma trava de 1×/dia, **e nada no resultado diz que houve corte**.

⛔ Um relatório que trunca em silêncio conta uma história menor **e parece
completo** — que é pior que não contar história nenhuma, porque ninguém revisa
um número que parece certo.

⚠️ E o teto não é escolha do código: 📊 **o PostgREST devolve no máximo 1.000
linhas por chamada, com ou sem `.limit()`.** Um `.limit(5000)` não aumenta
nada — ele só faz a chamada parecer que pediu mais.
"""
from __future__ import annotations

import asyncio
import importlib.util as _u
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _carregar(rel: str, nome: str):
    spec = _u.spec_from_file_location(nome, RAIZ / rel)
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DIA = _carregar("app/services/o_dia_de_ontem.py", "_dia_090D")

EMPRESA_1 = "11111111-1111-1111-1111-111111111111"
EMPRESA_2 = "22222222-2222-2222-2222-222222222222"
RUN_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


# =============================================================================
# 🔴 UM BANCO DE MENTIRA QUE SABE MENTIR — e que ANOTA o que foi filtrado
# =============================================================================

class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros = {}
        self.faixa = None
        self.teto = None
        self.conta_exata = False

    def select(self, *a, **k):
        self.conta_exata = k.get("count") == "exact"
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def in_(self, campo, valores):
        self.filtros[campo] = list(valores)
        return self

    def gte(self, campo, valor):
        self.filtros[f"{campo}>="] = valor
        return self

    def lte(self, campo, valor):
        self.filtros[f"{campo}<="] = valor
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        # 🔴 O `.limit()` TEM DE TRUNCAR, e a bateria provou por quê.
        #
        # 📊 Ignorá-lo deixava a mutação "o total vem da PÁGINA" ficar VERDE:
        # a consulta real usa `.limit(1)`, então `len(data)` seria 1 e o teste
        # pegaria. Com o `.limit()` de mentira devolvendo as 2.500 linhas,
        # `len(data)` também dava 2.500 — e o teste passava pelo motivo errado.
        #
        # ⚠️ Um banco de mentira que não respeita o contrato do de verdade não
        # testa o código: testa a mentira.
        self.teto = n
        return self

    def range(self, i, f):
        self.faixa = (i, f)
        return self

    async def execute(self):
        self.banco.consultas.append((self.tabela, dict(self.filtros)))
        if self.banco.explode.get(self.tabela):
            raise RuntimeError(f"banco fora do ar em {self.tabela}")

        linhas = [x for x in self.banco.dados.get(self.tabela, [])
                  if all(x.get(c) == v for c, v in self.filtros.items()
                         if not c.endswith((">=", "<=")) and not isinstance(v, list))
                  and all(str(x.get(c)) in v for c, v in self.filtros.items()
                          if isinstance(v, list))]
        total = len(linhas)
        if self.faixa:
            i, f = self.faixa
            linhas = linhas[i:f + 1]
        if self.teto is not None:
            linhas = linhas[:self.teto]

        class R:
            pass
        r = R()
        r.data = linhas
        # 🔴 `count` é o total NO BANCO, como o PostgREST devolve — nunca o
        #    tamanho da página. É o que o gate ③ mede.
        r.count = total if self.conta_exata else None
        return r


class _Banco:
    def __init__(self, dados=None, explode=None):
        self.dados = dados or {}
        self.explode = explode or {}
        self.consultas = []
        self.client = self

    def table(self, nome):
        return _Consulta(self, nome)


def _aberto(run, quando, id_, empresa=EMPRESA_1, rota="porto-auto", tela="placa"):
    return {"id": id_, "company_id": empresa, "work_run_id": run,
            "event_type": "travamento.aberto", "created_at": quando,
            "payload_redacted": {"rota": rota, "tela": tela, "motivo": "cega"}}


def _destravado(run, quando, id_, por="robo", empresa=EMPRESA_1, segundos=None):
    carga = {"rota": "porto-auto", "tela": "placa", "por": por}
    if segundos is not None:
        carga["segundos_travado"] = segundos
    return {"id": id_, "company_id": empresa, "work_run_id": run,
            "event_type": "travamento.destravado", "created_at": quando,
            "payload_redacted": carga}


def _nota(id_, origem="painel", empresa=EMPRESA_1, quando="2026-08-25T10:00:00+00:00"):
    return {"id": id_, "company_id": empresa, "texto": "o robô pediu duas vezes",
            "origem": origem, "rota": "porto-auto", "tela": "placa",
            "conversation_id": None, "created_at": quando}


# =============================================================================
# 🔴 CONTROLE DE CARGA — e do próprio banco de mentira
# =============================================================================

def test_CONTROLE_o_modulo_carregou():
    assert callable(DIA.o_que_aconteceu_ontem)
    assert callable(DIA.faixa_do_dia)
    assert DIA._TETO_DO_POSTGREST == 1000


def test_CONTROLE_o_banco_de_mentira_FILTRA_de_verdade():
    """§9.3 — *"prove que as duas coisas CONSEGUEM ser diferentes"*.

    ⛔ Um `_Banco` que devolvesse tudo sempre faria o teste de dois tenants
    passar por acidente, e ele é o gate ④.
    """
    banco = _Banco({"x": [{"company_id": EMPRESA_1, "v": 1},
                          {"company_id": EMPRESA_2, "v": 2}]})
    r = asyncio.run(banco.client.table("x").select("*").eq("company_id", EMPRESA_1).execute())
    assert [i["v"] for i in r.data] == [1], f"o filtro não filtrou: {r.data}"
    r2 = asyncio.run(banco.client.table("x").select("*").eq("company_id", EMPRESA_2).execute())
    assert [i["v"] for i in r2.data] == [2]


def test_CONTROLE_o_count_do_banco_de_mentira_e_o_TOTAL_nao_a_pagina():
    """🔴 As DUAS propriedades que o gate ③ mede, e elas têm de ser diferentes.

    ⚠️ `count` é o total no banco; `data` é a página. 📊 A bateria de mutação
    pegou este banco de mentira ignorando o `.limit()` — e com ele ignorado as
    duas coisas davam o mesmo número, então a mutação *"o total vem da PÁGINA"*
    ficava VERDE. **Um banco de mentira que não respeita o contrato do de
    verdade não testa o código: testa a mentira.**
    """
    banco = _Banco({"x": [{"company_id": EMPRESA_1} for _ in range(2500)]})
    r = asyncio.run(banco.client.table("x").select("id", count="exact")
                    .eq("company_id", EMPRESA_1).limit(1).execute())
    assert r.count == 2500, f"o count veio {r.count} — o gate ③ não tem como falhar"
    assert len(r.data) == 1, (
        f"a página veio com {len(r.data)} linhas — o `.limit(1)` foi ignorado, e "
        "com ele ignorado `count` e `len(data)` viram o mesmo número")

    # e a paginação por `range` corta na faixa pedida
    r2 = asyncio.run(banco.client.table("x").select("id")
                     .eq("company_id", EMPRESA_1).range(0, 999).execute())
    assert len(r2.data) == 1000


# =============================================================================
# ① a consulta responde com número
# =============================================================================

def test_o_dia_responde_os_numeros_do_produto():
    banco = _Banco({
        "conversations": [{"id": f"c{i}", "company_id": EMPRESA_1} for i in range(12)],
        "work_events": [
            _aberto(RUN_A, "2026-08-25T10:00:00+00:00", 1),
            _destravado(RUN_A, "2026-08-25T10:05:00+00:00", 2, por="humano", segundos=300),
            _aberto(RUN_A, "2026-08-25T14:00:00+00:00", 3),
        ],
        "work_runs": [{"id": RUN_A, "company_id": EMPRESA_1, "conversation_id": "conv-1"}],
        "notas_da_atendente": [_nota("n1"), _nota("n2", origem="whatsapp")],
    })
    r = asyncio.run(DIA.o_que_aconteceu_ontem(banco, EMPRESA_1, "2026-08-25"))

    assert r["atendimentos"] == 12
    assert r["travamentos"] == 2
    assert r["ainda_travados"] == 1
    assert r["segundos_mediano"] == 300
    assert r["quem_destravou"] == {"humano": 1}
    assert len(r["notas"]) == 2
    assert r["notas_por_origem"] == {"painel": 1, "whatsapp": 1}
    assert r["truncado"] == [], f"disse que truncou sem truncar: {r['truncado']}"
    # 🔴 a conversa do BLOCO A chega na trajetória
    assert r["trajetoria"][0]["conversation_id"] == "conv-1"


def test_as_TRES_telas_que_mais_travaram_saem_ordenadas():
    eventos = []
    for i in range(4):
        eventos.append(_aberto(RUN_A, f"2026-08-25T0{i}:00:00+00:00", i,
                               rota="zurich-auto", tela="Informe a placa"))
    for i in range(6):
        eventos += [_aberto(RUN_A, f"2026-08-25T1{i}:00:00+00:00", 10 + i * 2,
                            rota="allianz-auto", tela="menu"),
                    _destravado(RUN_A, f"2026-08-25T1{i}:30:00+00:00", 11 + i * 2)]
    r = asyncio.run(DIA.o_que_aconteceu_ontem(
        _Banco({"work_events": eventos}), EMPRESA_1, "2026-08-25"))
    assert len(r["telas"]) <= 3
    assert r["telas"][0]["tela"] == "Informe a placa", (
        f"a lista começa por {r['telas'][0]} — a que trava mais VEZES veio antes "
        "da que deixa gente esperando")
    assert r["telas"][0]["sem_destravar"] == 4


# =============================================================================
# ② dia sem atendimento → ZEROS, não erro
# =============================================================================

def test_dia_VAZIO_da_zeros_e_nao_erro():
    r = asyncio.run(DIA.o_que_aconteceu_ontem(_Banco(), EMPRESA_1, "2026-08-25"))
    assert r["atendimentos"] == 0
    assert r["travamentos"] == 0
    assert r["ainda_travados"] == 0
    assert r["notas"] == []
    assert r["telas"] == []
    assert r["truncado"] == []
    assert r["segundos_mediano"] is None, (
        "um dia sem travamento devolveu mediana 0 — 'zero minutos de travamento' "
        "e 'não houve travamento' contam histórias diferentes")


def test_o_BANCO_FORA_DO_AR_vira_zero_DECLARADO_e_nao_zero_silencioso():
    """🔴 A diferença entre *"não aconteceu nada"* e *"não consegui olhar"*."""
    banco = _Banco(explode={"work_events": True, "conversations": True,
                            "notas_da_atendente": True})
    r = asyncio.run(DIA.o_que_aconteceu_ontem(banco, EMPRESA_1, "2026-08-25"))
    assert r["travamentos"] == 0
    assert r["truncado"], (
        "o banco caiu inteiro e o relatório saiu com zeros LIMPOS — é a mentira "
        "mais cara que este módulo pode contar")
    assert any("atendimentos" in t for t in r["truncado"])


def test_SEM_company_id_nao_consulta_NADA():
    """⚠️ §7 — sem dono, um SELECT devolveria o dia de todas as corretoras."""
    banco = _Banco({"conversations": [{"id": "c1", "company_id": EMPRESA_1}]})
    r = asyncio.run(DIA.o_que_aconteceu_ontem(banco, "", "2026-08-25"))
    assert r["atendimentos"] == 0
    assert banco.consultas == [], f"consultou mesmo sem corretora: {banco.consultas}"
    assert r["truncado"]


# =============================================================================
# ③ 🔴 O TOTAL NUNCA É MAIOR QUE O QUE EXISTE — nem menor em silêncio
# =============================================================================

def test_o_total_de_atendimentos_vem_do_BANCO_e_nao_da_PAGINA():
    """🔴 Gate ③. 📊 O PostgREST devolve no máximo 1.000 linhas — um total lido
    de `len(data)` diria **1.000** num dia de 2.500 atendimentos."""
    banco = _Banco({"conversations": [{"id": f"c{i}", "company_id": EMPRESA_1}
                                      for i in range(2500)]})
    r = asyncio.run(DIA.o_que_aconteceu_ontem(banco, EMPRESA_1, "2026-08-25"))
    assert r["atendimentos"] == 2500, (
        f"o total veio {r['atendimentos']} — se for 1.000, ele é o tamanho da "
        "página e não o número do dia")


def test_a_paginacao_PERCORRE_alem_de_uma_pagina():
    """⚠️ 2.400 eventos = 1.200 travamentos. Sem paginar, sairiam 500."""
    eventos = []
    for i in range(1200):
        eventos += [_aberto(f"run-{i}", "2026-08-25T10:00:00+00:00", i * 2),
                    _destravado(f"run-{i}", "2026-08-25T10:05:00+00:00", i * 2 + 1)]
    r = asyncio.run(DIA.o_que_aconteceu_ontem(
        _Banco({"work_events": eventos}), EMPRESA_1, "2026-08-25"))
    assert r["travamentos"] == 1200, (
        f"contou {r['travamentos']} de 1.200 — a paginação parou na 1ª página")
    assert r["truncado"] == []


def test_ALEM_do_teto_de_paginas_o_corte_e_DECLARADO():
    """🔴 O teto existe. **Ele não pode ser silencioso.**"""
    limite = DIA._PAGINAS_MAXIMAS * DIA._TETO_DO_POSTGREST
    eventos = [_aberto(f"run-{i}", "2026-08-25T10:00:00+00:00", i)
               for i in range(limite + 500)]
    r = asyncio.run(DIA.o_que_aconteceu_ontem(
        _Banco({"work_events": eventos}), EMPRESA_1, "2026-08-25"))
    assert r["truncado"], (
        f"leu {r['travamentos']} de {limite + 500} eventos e NÃO declarou corte — "
        "é exatamente o defeito da P-090-03")
    assert any("travamentos" in t for t in r["truncado"])


def test_CONTROLE_o_truncado_fica_VAZIO_quando_tudo_coube():
    """§9.3 — sem esta linha, um `truncado` sempre cheio passaria acima, e o
    campo viraria ruído que ninguém lê."""
    r = asyncio.run(DIA.o_que_aconteceu_ontem(
        _Banco({"work_events": [_aberto(RUN_A, "2026-08-25T10:00:00+00:00", 1)]}),
        EMPRESA_1, "2026-08-25"))
    assert r["truncado"] == [], f"declarou corte sem cortar: {r['truncado']}"


# =============================================================================
# ④ 🔴 DOIS TENANTS
# =============================================================================

def test_dois_tenants_NAO_se_misturam_em_nenhuma_das_consultas():
    """🔴 Gate ④, e o filtro é o que protege — a RLS não, porque o backend usa
    service role e atravessa ela inteira."""
    banco = _Banco({
        "conversations": [{"id": "c1", "company_id": EMPRESA_1},
                          {"id": "c2", "company_id": EMPRESA_2},
                          {"id": "c3", "company_id": EMPRESA_2}],
        "work_events": [
            _aberto(RUN_A, "2026-08-25T10:00:00+00:00", 1, empresa=EMPRESA_1),
            _aberto("run-b", "2026-08-25T11:00:00+00:00", 2, empresa=EMPRESA_2),
            _aberto("run-b", "2026-08-25T12:00:00+00:00", 3, empresa=EMPRESA_2),
        ],
        "notas_da_atendente": [_nota("n1", empresa=EMPRESA_1),
                               _nota("n2", empresa=EMPRESA_2)],
    })
    r1 = asyncio.run(DIA.o_que_aconteceu_ontem(banco, EMPRESA_1, "2026-08-25"))
    r2 = asyncio.run(DIA.o_que_aconteceu_ontem(banco, EMPRESA_2, "2026-08-25"))

    assert (r1["atendimentos"], r1["travamentos"], len(r1["notas"])) == (1, 1, 1)
    assert (r2["atendimentos"], r2["travamentos"], len(r2["notas"])) == (2, 2, 1)
    assert r1["notas"][0]["id"] == "n1" and r2["notas"][0]["id"] == "n2"


def test_TODA_consulta_carrega_o_filtro_de_corretora():
    """⚠️ Uma só consulta sem `.eq("company_id")` já vaza o dia inteiro."""
    banco = _Banco({
        "conversations": [{"id": "c1", "company_id": EMPRESA_1}],
        "work_events": [_aberto(RUN_A, "2026-08-25T10:00:00+00:00", 1)],
        "work_runs": [{"id": RUN_A, "company_id": EMPRESA_1, "conversation_id": "x"}],
        "notas_da_atendente": [_nota("n1")],
    })
    asyncio.run(DIA.o_que_aconteceu_ontem(banco, EMPRESA_1, "2026-08-25"))
    assert banco.consultas, "nenhuma consulta foi feita — o teste é vácuo"
    for tabela, filtros in banco.consultas:
        assert filtros.get("company_id") == EMPRESA_1, (
            f"🔴 a consulta a `{tabela}` NÃO filtra por corretora: {filtros}")


# =============================================================================
# ⑤ a faixa do dia, e o fuso declarado
# =============================================================================

def test_a_faixa_cobre_o_dia_inteiro():
    de, ate = DIA.faixa_do_dia("2026-08-25")
    assert de == "2026-08-25T00:00:00+00:00"
    assert ate.startswith("2026-08-25T23:59:59")
    assert de < ate


def test_a_faixa_ignora_hora_colada_no_dia():
    de, _ = DIA.faixa_do_dia("2026-08-25T13:45:00+00:00")
    assert de == "2026-08-25T00:00:00+00:00"


def test_o_FUSO_esta_DECLARADO_no_codigo():
    """📊 §12.1 — *"ontem"* em Florianópolis (UTC−3) termina às 03h00 UTC de hoje.

    ⚠️ Escolher um fuso aqui sem o Founder decidir seria inventar a resposta.
    O que **não** pode é a escolha ficar implícita: quem lê o relatório precisa
    saber que o dia é UTC.
    """
    fonte = (RAIZ / "app" / "services" / "o_dia_de_ontem.py").read_text("utf-8")
    corpo = fonte.split("def faixa_do_dia", 1)[1].split("\nasync def ", 1)[0]
    assert "UTC" in corpo and "P-090-06" in corpo, (
        "o fuso não está declarado — um relatório de fuso implícito engana quem "
        "compara com o WhatsApp da atendente")


# =============================================================================
# ⑥ o que NÃO pode acontecer
# =============================================================================

def test_a_leitura_NUNCA_levanta():
    fonte = (RAIZ / "app" / "services" / "o_dia_de_ontem.py").read_text("utf-8")
    corpo = fonte.split("async def o_que_aconteceu_ontem", 1)[1]
    corpo = corpo.split("\nasync def ", 1)[0]
    sem_doc = '"""'.join(corpo.split('"""')[::2])
    sem_comentario = "\n".join(l.split("#", 1)[0] for l in sem_doc.splitlines())
    assert "raise" not in sem_comentario, (
        "a leitura pode levantar — um relatório que estoura no meio não é lido")


def test_o_modulo_NAO_escreve_em_lugar_nenhum():
    """⛔ *"É UMA LEITURA, NÃO UM MOTOR."* — e a bateria confere.

    ⚠️ Um `insert` aqui seria um segundo escritor ao lado dos que já existem
    (`dispatch_router`, `tela_cega`, o webhook), que é o motor paralelo que a
    §5 proíbe.
    """
    fonte = (RAIZ / "app" / "services" / "o_dia_de_ontem.py").read_text("utf-8")
    sem_doc = '"""'.join(fonte.split('"""')[::2])
    sem_comentario = "\n".join(l.split("#", 1)[0] for l in sem_doc.splitlines())

    # ⚠️ A PROPRIEDADE É "não escreve no BANCO", não "não usa a palavra update".
    #    📊 A primeira versão deste guarda reprovava `resposta.update({...})` —
    #    um dicionário local — e ficava vermelha sem defeito nenhum. Um guarda
    #    que falha por engano é desligado por quem vier depois.
    for escrita in (".insert(", ".upsert(", ".delete("):
        assert escrita not in sem_comentario, (
            f"🔴 `{escrita}` num módulo que é só leitura")

    # e nenhum `.update(` pendurado numa consulta ao banco
    for m in re.finditer(r"\.table\(", sem_comentario):
        cadeia = sem_comentario[m.start():m.start() + 600]
        cadeia = cadeia.split(".execute()", 1)[0]
        for escrita in (".insert(", ".update(", ".upsert(", ".delete("):
            assert escrita not in cadeia, (
                f"🔴 `{escrita}` numa cadeia `.table(...)`: {cadeia[:120]}")


def test_CONTROLE_o_guarda_de_ESCRITA_consegue_flagrar():
    """§9.3 — 📊 a bateria de mutação injeta um `insert` neste módulo. Se o
    guarda não pegasse, a mutação ficaria verde e ninguém saberia."""
    falso = 'x = 1\nawait db.client.table("notas").insert({}).execute()\n'
    achou = False
    for m in re.finditer(r"\.table\(", falso):
        if ".insert(" in falso[m.start():m.start() + 600].split(".execute()", 1)[0]:
            achou = True
    assert achou, "o guarda não flagra um insert encadeado — ele não guarda nada"
    # e a linha de controle: um dicionário local NÃO é flagrado
    honesto = 'resposta.update({"a": 1})\n'
    assert not any(".update(" in honesto[m.start():m.start() + 600]
                   for m in re.finditer(r"\.table\(", honesto))


def test_o_modulo_NAO_imprime_dado_de_pessoa():
    fonte = (RAIZ / "app" / "services" / "o_dia_de_ontem.py").read_text("utf-8")
    for chamada in re.findall(r"logger\.\w+\((?:[^()]|\([^()]*\))*\)", fonte):
        assert not re.search(r'logger\.\w+\(\s*f["\']', chamada), (
            f"f-string em log — ela interpola sempre: {chamada[:90]}")
        for nome in ("texto", "telefone", "counterparty", "user_phone", "notas"):
            assert f"{{{nome}" not in chamada, f"vaza `{nome}`: {chamada[:90]}"


# =============================================================================
# 🔴 OS DOIS BURACOS QUE A BATERIA PEGOU — a lição migra (§9.3)
# =============================================================================

def test_SO_os_travamentos_falhando_o_corte_AINDA_e_declarado():
    """🔴 A falha no meio da paginação é CORTE, não FIM.

    ⚠️ **O guarda anterior não separava as causas.** Ele derrubava o banco
    INTEIRO e conferia que `truncado` não estava vazio — mas `truncado` já vinha
    cheio pela seção de atendimentos, então a metade dos travamentos passava sem
    ninguém olhar. 📊 A mutação *"a falha vira FIM em vez de CORTE"* ficava
    VERDE por causa disso.

    ⛔ Aqui só `work_events` cai. Se o corte não for declarado, o relatório diz
    *"nenhum travamento"* num dia em que ninguém conseguiu olhar.
    """
    banco = _Banco({"conversations": [{"id": "c1", "company_id": EMPRESA_1}]},
                   explode={"work_events": True})
    r = asyncio.run(DIA.o_que_aconteceu_ontem(banco, EMPRESA_1, "2026-08-25"))

    assert r["atendimentos"] == 1, "a seção que funciona tem de continuar funcionando"
    assert r["travamentos"] == 0
    assert r["truncado"], (
        "🔴 `work_events` caiu e o relatório saiu com 'nenhum travamento' LIMPO — "
        "é a diferença entre 'não aconteceu nada' e 'não consegui olhar'")
    assert not any("atendimentos" in t for t in r["truncado"]), (
        "o aviso veio da seção errada — este teste ficaria verde sem provar nada")


def test_SO_as_NOTAS_falhando_o_corte_e_declarado():
    """A mesma prova, na terceira seção — e as notas são o BLOCO C inteiro."""
    banco = _Banco({"conversations": [{"id": "c1", "company_id": EMPRESA_1}],
                    "work_events": [_aberto(RUN_A, "2026-08-25T10:00:00+00:00", 1)]},
                   explode={"notas_da_atendente": True})
    r = asyncio.run(DIA.o_que_aconteceu_ontem(banco, EMPRESA_1, "2026-08-25"))
    assert r["travamentos"] == 1, "a seção que funciona continua funcionando"
    assert r["notas"] == []
    assert any("notas" in t for t in r["truncado"]), (
        f"as notas caíram e ninguém avisou: {r['truncado']}")


def test_CONTROLE_com_TUDO_de_pe_nenhuma_secao_declara_corte():
    """§9.3 — sem esta linha, um `truncado` sempre cheio passaria nos três
    testes acima, e o campo viraria ruído que ninguém lê."""
    banco = _Banco({"conversations": [{"id": "c1", "company_id": EMPRESA_1}],
                    "work_events": [_aberto(RUN_A, "2026-08-25T10:00:00+00:00", 1)],
                    "notas_da_atendente": [_nota("n1")]})
    r = asyncio.run(DIA.o_que_aconteceu_ontem(banco, EMPRESA_1, "2026-08-25"))
    assert r["truncado"] == [], f"declarou corte com tudo de pé: {r['truncado']}"
    assert (r["atendimentos"], r["travamentos"], len(r["notas"])) == (1, 1, 1)
