# -*- coding: utf-8 -*-
"""O atendimento termina — e o produto sabe. SPEC-086.

> **O TESTE DO PRODUTO:** *"Sexta-feira. A Regina abre a tela e pergunta: 'dos
> atendimentos desta semana, quantos terminaram, quantos ainda esperam alguém, e
> quantos morreram esperando?' — e a tela responde, com número."*

## 📊 O estado medido em 26/08/2026 — a SPEC acertou nos quatro números

```
conversations ..................... 671
  com `resolvido_em` preenchido ....  0
  com `resolucao_motivo` ...........  0
status em uso ............ open=614, active=57
work_waits ........................ NÃO EXISTIA
work_runs presos em `queued` ......  5   o mais velho há 29 dias
```

⚠️ **E dois achados que a SPEC não tem:**

1. 🔴 A **tubulação já estava inteira**: `attendance_ficha.gravar()` já escreve
   as duas colunas. Faltava quem decidisse.
2. ⚠️ Os cinco presos são **todos** `intelligence.detect_signals` — jobs de
   background, não atendimento. O buraco é real; a prova do atendimento é a
   conversa de 730 horas, não eles.
"""
from __future__ import annotations

import asyncio
import importlib.util as _u
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MIG_A = (RAIZ / "supabase" / "migrations"
         / "20260826_04_spec086_blocoA_a_conversa_tem_fim.sql")
MIG_B = (RAIZ / "supabase" / "migrations"
         / "20260826_05_spec086_blocoB_work_waits.sql")
VIGIA_PY = RAIZ / "app" / "tasks" / "handoff_watchdog.py"
ROTEADOR_PY = RAIZ / "app" / "services" / "dispatch_router.py"
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"
AGENDADOR_PY = RAIZ / "app" / "tasks" / "buffer_processor.py"


def _carregar(rel: str, nome: str):
    spec = _u.spec_from_file_location(nome, RAIZ / rel)
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FIM = _carregar("app/services/o_fim_do_atendimento.py", "_fim_086")

EMPRESA_1 = "11111111-1111-1111-1111-111111111111"
EMPRESA_2 = "22222222-2222-2222-2222-222222222222"
CONVERSA_1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
CONVERSA_2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def _so_o_codigo_sql(sql: str) -> str:
    """⛔ O bloco VERIFY inteiro é comentário — e nesta SPEC a prosa já enganou
    cinco asserções (SPEC-090)."""
    return "\n".join(l.split("--", 1)[0] for l in sql.splitlines())


def _so_o_codigo_py(fonte: str) -> str:
    sem_doc = '"""'.join(fonte.split('"""')[::2])
    return "\n".join(l.split("#", 1)[0] for l in sem_doc.splitlines())


def _so_o_codigo_ts(fonte: str) -> str:
    """O TypeScript sem `//` e sem `/* */`.

    🔴 **SEXTA vez nesta execução que a prosa engana uma asserção.** 📊 A
    mutação *"o painel APAGA o desfecho real"* ficava VERDE porque o
    comentário que eu mesmo escrevi acima do código cita
    `.is('resolvido_em', null)` — e o `in` achava o comentário.
    """
    import re as _re

    sem_bloco = _re.sub(r"/\*.*?\*/", " ", fonte, flags=_re.S)
    return "\n".join(l.split("//", 1)[0] for l in sem_bloco.splitlines())


# =============================================================================
# 🔴 UM BANCO DE MENTIRA QUE SABE MENTIR
# =============================================================================

class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.nulos, self.nao_nulos = {}, [], []
        self.teto = None
        self.campos = None
        self.op = "select"

    def select(self, *a, **k):
        return self

    def insert(self, linha):
        self.op, self.campos = "insert", linha
        return self

    def update(self, campos):
        self.op, self.campos = "update", campos
        return self

    def eq(self, c, v):
        self.filtros[c] = v
        return self

    def lte(self, c, v):
        self.filtros[f"{c}<="] = v
        return self

    def is_(self, c, v):
        self.nulos.append(c)
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        self.teto = n
        return self

    async def execute(self):
        b = self.banco
        b.chamadas.append((self.op, self.tabela, dict(self.filtros),
                           list(self.nulos), self.campos))
        if b.explode.get(self.tabela):
            raise RuntimeError("banco fora do ar")

        linhas = b.dados.setdefault(self.tabela, [])
        if self.op == "insert":
            # 🔴 O UNIQUE PARCIAL DE MENTIRA — e ele TEM de morder, senão o
            #    guarda de "dois waits ativos" não guarda nada.
            if self.tabela == "work_waits" and self.campos.get("status", "ativo") == "ativo":
                chave = (self.campos.get("company_id"),
                         self.campos.get("conversation_id"),
                         self.campos.get("scope", "default"))
                if any((w.get("company_id"), w.get("conversation_id"),
                        w.get("scope", "default")) == chave
                       and w.get("status") == "ativo" for w in linhas):
                    raise RuntimeError(
                        'duplicate key value violates unique constraint '
                        '"uq_work_waits_ativo_por_escopo"')
            linhas.append(dict(self.campos))
            r = type("R", (), {})()
            r.data = [dict(self.campos)]
            return r

        casadas = [x for x in linhas
                   if all(str(x.get(c)) == str(v) for c, v in self.filtros.items()
                          if not c.endswith("<="))
                   and all(str(x.get(c[:-2]) or "") <= str(v)
                           for c, v in self.filtros.items() if c.endswith("<="))
                   and all(x.get(c) in (None, "") for c in self.nulos)]
        if self.op == "update":
            for x in casadas:
                x.update(self.campos)
        if self.teto:
            casadas = casadas[:self.teto]
        r = type("R", (), {})()
        r.data = [dict(x) for x in casadas]
        return r


class _Banco:
    def __init__(self, dados=None, explode=None):
        self.dados = dados or {}
        self.explode = explode or {}
        self.chamadas = []
        self.client = self

    def table(self, nome):
        return _Consulta(self, nome)


def _conversa(id_=CONVERSA_1, empresa=EMPRESA_1, resolvido=None, motivo=None):
    return {"id": id_, "company_id": empresa,
            "resolvido_em": resolvido, "resolucao_motivo": motivo}


# =============================================================================
# 🔴 CONTROLE DE CARGA — e do banco de mentira
# =============================================================================

def test_CONTROLE_o_modulo_carregou():
    assert callable(FIM.marcar_fim)
    assert callable(FIM.abrir_espera)
    assert callable(FIM.contar_desfechos)
    assert len(FIM.MOTIVOS) == 5
    assert FIM.KINDS == ("esperando_cliente", "esperando_seguradora", "esperando_humano")


def test_CONTROLE_o_banco_de_mentira_FILTRA_e_o_UNIQUE_MORDE():
    """§9.3 — *"prove que as duas coisas CONSEGUEM ser diferentes"*.

    ⛔ Um `_Banco` que aceitasse tudo faria o gate ② do BLOCO B passar por
    vacuidade, e o gate ④ (dois tenants) também.
    """
    banco = _Banco()
    # o filtro filtra
    asyncio.run(banco.client.table("x").insert({"company_id": EMPRESA_1, "v": 1}).execute())
    asyncio.run(banco.client.table("x").insert({"company_id": EMPRESA_2, "v": 2}).execute())
    r = asyncio.run(banco.client.table("x").select("*").eq("company_id", EMPRESA_1).execute())
    assert [i["v"] for i in r.data] == [1], f"o filtro não filtrou: {r.data}"

    # e o UNIQUE parcial morde
    linha = {"company_id": EMPRESA_1, "conversation_id": CONVERSA_1,
             "scope": "default", "status": "ativo"}
    asyncio.run(banco.client.table("work_waits").insert(dict(linha)).execute())
    try:
        asyncio.run(banco.client.table("work_waits").insert(dict(linha)).execute())
        raise AssertionError("o UNIQUE de mentira NÃO mordeu — o gate ② é vácuo")
    except RuntimeError as erro:
        assert "uq_work_waits_ativo_por_escopo" in str(erro)


# =============================================================================
# BLOCO A · ① a conversa passa a ter FIM
# =============================================================================

def test_o_dispatch_RESOLVIDO_e_ENCAMINHADO_terminam_o_atendimento():
    """🔴 E são os DOIS desfechos de sucesso — a SPEC só via um."""
    assert FIM.motivo_do_estado_do_dispatch("resolvido") == FIM.ACIONAMENTO_CONCLUIDO
    assert FIM.motivo_do_estado_do_dispatch("encaminhado") == FIM.ENCAMINHADO


def test_needs_human_e_test_aborted_NAO_terminam_atendimento():
    """🔴 Estão em `FASES_ENCERRADAS`, e de propósito não terminam nada.

    ⛔ `needs_human`: o acionamento parou, **mas tem gente esperando**. Marcar
    resolvido aqui contaria como "terminou" um segurado que ninguém atendeu.
    ⛔ `test_aborted`: é simulação.
    """
    assert FIM.motivo_do_estado_do_dispatch("needs_human") is None
    assert FIM.motivo_do_estado_do_dispatch("test_aborted") is None
    for meio in ("ura", "human_phase", "captured", "monitoring", "queued", "", None):
        assert FIM.motivo_do_estado_do_dispatch(meio) is None, f"{meio!r} terminou"


def test_CONTROLE_os_dois_estados_estao_em_FASES_ENCERRADAS_do_motor():
    """§5 — duas listas que precisam concordar divergem.

    ⚠️ Se o motor renomear `encaminhado`, este módulo fica em silêncio: nada
    termina mais, e a sexta-feira reporta zero. **O silêncio é o defeito.**
    """
    motor = MOTOR_PY.read_text(encoding="utf-8")
    assert 'FASES_ENCERRADAS = ("needs_human", "test_aborted", "encaminhado", "resolvido")' in motor
    for estado in FIM.MOTIVO_DO_ESTADO:
        assert f'"{estado}"' in motor, f"o motor não conhece o estado {estado!r}"


def test_o_atendimento_e_marcado_com_data_E_motivo():
    banco = _Banco({"conversations": [_conversa()]})
    marcou, porque = asyncio.run(FIM.marcar_fim(
        banco, company_id=EMPRESA_1, motivo=FIM.ACIONAMENTO_CONCLUIDO,
        conversation_id=CONVERSA_1, quando_iso="2026-08-26T10:00:00+00:00"))
    assert marcou is True and porque == FIM.ACIONAMENTO_CONCLUIDO
    linha = banco.dados["conversations"][0]
    assert linha["resolvido_em"] == "2026-08-26T10:00:00+00:00"
    assert linha["resolucao_motivo"] == FIM.ACIONAMENTO_CONCLUIDO


def test_MOTIVO_FORA_DA_LISTA_nao_chega_ao_banco():
    """Gate ③ — 🔴 e o valor testado é o que a PRÓPRIA SPEC pedia.

    📊 A SPEC-093 aprendeu isso da pior forma: pediu `destravado_por_humano`, o
    banco recusou por CHECK, e o executor teve de escolher outro valor **no
    meio da execução**.
    """
    banco = _Banco({"conversations": [_conversa()]})
    marcou, porque = asyncio.run(FIM.marcar_fim(
        banco, company_id=EMPRESA_1, motivo="acionamento_aberto",
        conversation_id=CONVERSA_1))
    assert marcou is False and porque == "motivo_invalido"
    assert banco.chamadas == [], "chegou a consultar o banco com motivo inválido"
    assert banco.dados["conversations"][0]["resolvido_em"] is None


def test_a_migration_LISTA_os_valores_do_CHECK():
    """🔴 Exigência do protocolo. E os cinco valores estão escritos no APPLY."""
    sql = MIG_A.read_text(encoding="utf-8")
    codigo = _so_o_codigo_sql(sql)
    assert "resolucao_motivo IN (" in codigo
    for valor in FIM.MOTIVOS:
        assert f"'{valor}'" in codigo, f"o CHECK não conhece {valor!r}"
    # ⛔ e NÃO conhece o nome que a SPEC pedia
    assert "'acionamento_aberto'" not in codigo


def test_a_migration_exige_que_data_e_motivo_andem_JUNTOS():
    """⚠️ Uma conversa que acabou "por um motivo, em momento nenhum" some de
    toda consulta por período — que é a pergunta da sexta-feira."""
    codigo = _so_o_codigo_sql(MIG_A.read_text(encoding="utf-8"))
    assert "ck_conversations_resolucao_coerente" in codigo
    assert "resolvido_em IS NULL AND resolucao_motivo IS NULL" in codigo


def test_marcar_duas_vezes_marca_UMA(  ):
    """Gate ④ — idempotente, **pelo filtro** e não por leitura antes.

    ⚠️ O BLOCO C varre a cada 10 min e o dispatch escreve no instante do
    desfecho. Ler-e-depois-escrever teria janela.
    """
    banco = _Banco({"conversations": [_conversa()]})
    a, _ = asyncio.run(FIM.marcar_fim(banco, company_id=EMPRESA_1,
                                      motivo=FIM.ENCAMINHADO,
                                      conversation_id=CONVERSA_1))
    b, porque = asyncio.run(FIM.marcar_fim(banco, company_id=EMPRESA_1,
                                           motivo=FIM.EXPIROU,
                                           conversation_id=CONVERSA_1))
    assert a is True and b is False
    assert porque == "ja_resolvida_ou_de_outra_corretora"
    assert banco.dados["conversations"][0]["resolucao_motivo"] == FIM.ENCAMINHADO, (
        "o segundo motivo sobrescreveu o primeiro — o desfecho REAL foi apagado")
    # 🔴 e o `is_` do UPDATE é o que garante isso
    _, _, _, nulos, _ = banco.chamadas[1]
    assert "resolvido_em" in nulos


def test_dois_tenants_resolver_em_A_nao_toca_B():
    """Gate ⑤."""
    banco = _Banco({"conversations": [_conversa(CONVERSA_1, EMPRESA_1),
                                      _conversa(CONVERSA_2, EMPRESA_2)]})
    asyncio.run(FIM.marcar_fim(banco, company_id=EMPRESA_1,
                               motivo=FIM.FECHADO_POR_HUMANO,
                               conversation_id=CONVERSA_1))
    a, b = banco.dados["conversations"]
    assert a["resolucao_motivo"] == FIM.FECHADO_POR_HUMANO
    assert b["resolvido_em"] is None, "a corretora B foi tocada"


def test_a_conversa_de_OUTRA_corretora_nao_e_marcada():
    banco = _Banco({"conversations": [_conversa(CONVERSA_1, EMPRESA_1)]})
    marcou, _ = asyncio.run(FIM.marcar_fim(banco, company_id=EMPRESA_2,
                                           motivo=FIM.EXPIROU,
                                           conversation_id=CONVERSA_1))
    assert marcou is False
    assert banco.dados["conversations"][0]["resolvido_em"] is None


def test_o_dispatch_LIGA_o_marcador_no_checkpoint():
    """🔴 O escritor do BLOCO A — e ele é best-effort, por fora do `return`."""
    fonte = _so_o_codigo_py(ROTEADOR_PY.read_text(encoding="utf-8"))
    assert "_marcar_fim_do_atendimento" in fonte
    assert "await _marcar_fim_do_atendimento(db, company_id, session, fase)" in fonte
    corpo = fonte.split("async def _marcar_fim_do_atendimento", 1)[1].split("\nasync def ", 1)[0]
    assert "motivo_do_estado_do_dispatch" in corpo
    assert "mirror_conversation_id" in corpo
    assert "except Exception" in corpo, "uma falha aqui derrubaria o checkpoint"


# =============================================================================
# BLOCO B · a espera vira OBJETO
# =============================================================================

def test_abrir_espera_de_conversa_SEM_work_run_funciona():
    """🔴 Gate ①, e é o que faz o bloco existir.

    📊 A proposta original declarava `work_run_id NOT NULL`. **Conversa de
    WhatsApp não cria Work Run**: 4 runs de acionamento contra 671 conversas.
    Com `NOT NULL`, não haveria onde pendurar a espera do piloto.
    """
    banco = _Banco()
    abriu, porque = asyncio.run(FIM.abrir_espera(
        banco, company_id=EMPRESA_1, conversation_id=CONVERSA_1,
        kind=FIM.ESPERANDO_CLIENTE, vence_em_iso="2026-08-26T12:00:00+00:00"))
    assert abriu is True, porque
    linha = banco.dados["work_waits"][0]
    assert "work_run_id" not in linha, "gravou um run que não existe"
    assert linha["company_id"] == EMPRESA_1          # 🔴 §7
    assert linha["status"] == "ativo"


def test_a_migration_deixa_work_run_id_NULO():
    codigo = _so_o_codigo_sql(MIG_B.read_text(encoding="utf-8"))
    assert re.search(r"work_run_id\s+uuid REFERENCES", codigo), codigo[:400]
    assert not re.search(r"work_run_id\s+uuid\s+NOT NULL", codigo), (
        "🔴 `work_run_id NOT NULL` — o bloco não executa: não há onde pendurar "
        "a espera da conversa comum, que é o caso do piloto")
    assert "conversation_id   uuid NOT NULL" in codigo, (
        "a ÂNCORA é a conversa; uma espera sem dono não é varrível")


def test_DOIS_waits_ativos_no_mesmo_escopo_sao_RECUSADOS():
    """Gate ② — ⛔ senão o vencimento dispara duas vezes e a corretora recebe
    alerta em dobro."""
    banco = _Banco()
    a, _ = asyncio.run(FIM.abrir_espera(banco, company_id=EMPRESA_1,
                                        conversation_id=CONVERSA_1,
                                        kind=FIM.ESPERANDO_CLIENTE,
                                        vence_em_iso="2026-08-26T12:00:00+00:00"))
    b, porque = asyncio.run(FIM.abrir_espera(banco, company_id=EMPRESA_1,
                                             conversation_id=CONVERSA_1,
                                             kind=FIM.ESPERANDO_CLIENTE,
                                             vence_em_iso="2026-08-26T13:00:00+00:00"))
    assert a is True and b is False
    assert porque == "ja_existe_espera_ativa", (
        "o UNIQUE virou erro genérico — o chamador não consegue distinguir "
        "'já esperava' de 'o banco caiu'")
    assert len(banco.dados["work_waits"]) == 1


def test_CONTROLE_outro_ESCOPO_pode_esperar_ao_mesmo_tempo():
    """§9.3 — sem esta linha, um `abrir_espera` que recusasse tudo passaria."""
    banco = _Banco()
    asyncio.run(FIM.abrir_espera(banco, company_id=EMPRESA_1,
                                 conversation_id=CONVERSA_1,
                                 kind=FIM.ESPERANDO_CLIENTE,
                                 vence_em_iso="2026-08-26T12:00:00+00:00"))
    ok, _ = asyncio.run(FIM.abrir_espera(banco, company_id=EMPRESA_1,
                                         conversation_id=CONVERSA_1,
                                         kind=FIM.ESPERANDO_SEGURADORA,
                                         scope="acionamento",
                                         vence_em_iso="2026-08-26T12:00:00+00:00"))
    assert ok is True, "o UNIQUE virou global — a conversa não pode esperar duas coisas"
    assert len(banco.dados["work_waits"]) == 2


def test_a_migration_tem_UNIQUE_PARCIAL_e_nao_cheio():
    """⚠️ Um UNIQUE cheio impediria a MESMA conversa de esperar de novo depois —
    e esperar de novo é o normal: o cliente responde, some, volta."""
    codigo = _so_o_codigo_sql(MIG_B.read_text(encoding="utf-8"))
    assert "uq_work_waits_ativo_por_escopo" in codigo
    # 🔴 A DECLARAÇÃO INTEIRA, até o `;` — e não os N caracteres seguintes.
    #
    # 📊 A bateria pegou este guarda VERDE: `[:220]` alcançava o índice
    # `ix_work_waits_vencendo`, quatro linhas abaixo, que TAMBÉM tem
    # `WHERE status = 'ativo'`. O guarda lia o índice errado.
    decl = codigo.split("uq_work_waits_ativo_por_escopo", 1)[1].split(";", 1)[0]
    assert "WHERE status = 'ativo'" in decl, (
        "o UNIQUE não é parcial — a conversa nunca mais poderia esperar "
        f"depois da primeira vez.{chr(10)}  declaração: {decl[:160]}")


def test_CONTROLE_o_cortador_de_declaracao_isola_o_indice_certo():
    """§9.3 — prove que o corte separa os DOIS índices."""
    codigo = _so_o_codigo_sql(MIG_B.read_text(encoding="utf-8"))
    decl = codigo.split("uq_work_waits_ativo_por_escopo", 1)[1].split(";", 1)[0]
    assert "ix_work_waits_vencendo" not in decl, (
        "o corte alcançou o índice seguinte — é o defeito que ele conserta")


def test_kind_FORA_DA_LISTA_nao_chega_ao_banco():
    banco = _Banco()
    abriu, porque = asyncio.run(FIM.abrir_espera(
        banco, company_id=EMPRESA_1, conversation_id=CONVERSA_1,
        kind="esperando_o_correio", vence_em_iso="2026-08-26T12:00:00+00:00"))
    assert abriu is False and porque == "kind_invalido"
    assert banco.chamadas == []


def test_satisfazer_espera_muda_o_status_e_diz_QUEM():
    """Gate ③."""
    banco = _Banco()
    asyncio.run(FIM.abrir_espera(banco, company_id=EMPRESA_1,
                                 conversation_id=CONVERSA_1,
                                 kind=FIM.ESPERANDO_CLIENTE,
                                 vence_em_iso="2026-08-26T12:00:00+00:00"))
    quantas = asyncio.run(FIM.satisfazer_espera(
        banco, company_id=EMPRESA_1, conversation_id=CONVERSA_1, por="segurado"))
    assert quantas == 1
    w = banco.dados["work_waits"][0]
    assert w["status"] == FIM.SATISFEITO
    assert w["satisfeito_por"] == "segurado"
    assert w["satisfeito_em"]

    # ⛔ e satisfazer de novo não faz nada
    assert asyncio.run(FIM.satisfazer_espera(
        banco, company_id=EMPRESA_1, conversation_id=CONVERSA_1, por="x")) == 0


def test_satisfazer_espera_de_A_NAO_toca_a_de_B():
    """🔴 §7 — e a bateria pegou este buraco: nenhum guarda cobria o filtro
    de corretora em `satisfazer_espera`.

    ⛔ Sem ele, o segurado da corretora A respondendo fecharia a espera de um
    segurado da B — e o vigia da B pararia de cobrar uma conversa que ainda
    espera alguém.
    """
    banco = _Banco()
    for empresa, conversa in ((EMPRESA_1, CONVERSA_1), (EMPRESA_2, CONVERSA_2)):
        asyncio.run(FIM.abrir_espera(banco, company_id=empresa,
                                     conversation_id=conversa,
                                     kind=FIM.ESPERANDO_CLIENTE,
                                     vence_em_iso="2026-08-26T12:00:00+00:00"))

    # ⚠️ A corretora ERRADA, com o id de conversa CERTO da outra.
    quantas = asyncio.run(FIM.satisfazer_espera(
        banco, company_id=EMPRESA_2, conversation_id=CONVERSA_1, por="x"))
    assert quantas == 0, (
        "a corretora B fechou a espera de um segurado da A")
    assert banco.dados["work_waits"][0]["status"] == "ativo"

    # 🔴 linha de controle: a corretora CERTA fecha
    assert asyncio.run(FIM.satisfazer_espera(
        banco, company_id=EMPRESA_1, conversation_id=CONVERSA_1, por="x")) == 1


def test_dois_tenants_A_NAO_ENXERGA_a_espera_de_B_pelo_REPOSITORIO():
    """🔴 Gate ④ — *"pelo REPOSITÓRIO, não só pela RLS"*.

    ⚠️ §7: o backend usa service role e ATRAVESSA a RLS inteira. 📊 Precedente
    na casa: `work_effects` tem RLS ligada e ZERO policies.
    """
    banco = _Banco()
    for empresa, conversa in ((EMPRESA_1, CONVERSA_1), (EMPRESA_2, CONVERSA_2)):
        asyncio.run(FIM.abrir_espera(banco, company_id=empresa,
                                     conversation_id=conversa,
                                     kind=FIM.ESPERANDO_CLIENTE,
                                     vence_em_iso="2026-08-26T12:00:00+00:00"))
    de_a = asyncio.run(FIM.esperas_da_corretora(banco, EMPRESA_1))
    de_b = asyncio.run(FIM.esperas_da_corretora(banco, EMPRESA_2))
    assert len(de_a) == 1 and de_a[0]["conversation_id"] == CONVERSA_1
    assert len(de_b) == 1 and de_b[0]["conversation_id"] == CONVERSA_2


def test_SEM_corretora_o_repositorio_devolve_VAZIO_e_nao_TUDO():
    """⛔ Um repositório que esquece o filtro e devolve o banco inteiro é o
    vazamento entre corretoras que a RLS não impede."""
    banco = _Banco()
    for empresa, conversa in ((EMPRESA_1, CONVERSA_1), (EMPRESA_2, CONVERSA_2)):
        asyncio.run(FIM.abrir_espera(banco, company_id=empresa,
                                     conversation_id=conversa,
                                     kind=FIM.ESPERANDO_CLIENTE,
                                     vence_em_iso="2026-08-26T12:00:00+00:00"))
    assert asyncio.run(FIM.esperas_da_corretora(banco, "")) == []
    assert banco.chamadas[-1][1] == "work_waits", "o teste está lendo errado"
    # ⛔ a última chamada é a do insert, não um select sem filtro
    assert banco.chamadas[-1][0] == "insert"


def test_a_migration_tem_FK_COMPOSTA_e_RLS():
    codigo = _so_o_codigo_sql(MIG_B.read_text(encoding="utf-8"))
    assert "FOREIGN KEY (conversation_id, company_id)" in codigo
    assert "REFERENCES public.conversations (id, company_id)" in codigo
    assert "ENABLE ROW LEVEL SECURITY" in codigo


def test_a_migration_LISTA_os_valores_dos_DOIS_checks():
    codigo = _so_o_codigo_sql(MIG_B.read_text(encoding="utf-8"))
    for k in FIM.KINDS:
        assert f"'{k}'" in codigo
    for s in FIM.STATUS_DO_WAIT:
        assert f"'{s}'" in codigo
    assert "ck_work_waits_avisos" in codigo
    assert "ck_work_waits_satisfacao_coerente" in codigo


# =============================================================================
# BLOCO C · a espera vencida acorda alguém — ⛔ NUNCA o segurado
# =============================================================================

def test_o_VARREDOR_nao_tem_caminho_para_o_segurado():
    """🔴 Gate ②, e é a mutação obrigatória da SPEC.

    ⛔ *"Um watchdog que fala com o cliente é um robô que acorda às 3h da
    manhã."* O caminho de acordar o segurado existe, tem governador
    (`platform_outbound.py`) e é o BLOCO D da SPEC-093 — não este.
    """
    fonte = VIGIA_PY.read_text(encoding="utf-8")
    corpo = fonte.split("async def varrer_esperas_vencidas", 1)[1]
    codigo = _so_o_codigo_py(corpo)

    for proibido in ("send_message", "send_image", "send_audio",
                     "platform_outbound", "enviar_para_segurado",
                     "whatsapp_service"):
        assert proibido not in codigo, (
            f"🔴 `{proibido}` dentro do varredor — ele passa a falar com o cliente")

    # ✅ e o caminho que ELE usa é o da corretora
    assert "_avisar_suporte" in codigo, (
        "o varredor não avisa ninguém — a espera volta a apodrecer")


def test_o_varredor_usa_o_MESMO_avisador_e_nao_cria_escalonamento():
    """§5 — o destino sai de `_avisar_suporte`, que já recusa destino
    compartilhado entre corretoras (§7)."""
    codigo = _so_o_codigo_py(VIGIA_PY.read_text(encoding="utf-8"))
    corpo = codigo.split("async def varrer_esperas_vencidas", 1)[1]
    assert "HumanHandoffTool(db)._avisar_suporte" in corpo
    assert "resolver_destino" not in corpo, "resolvedor de destino próprio = §5"


def test_o_varredor_grava_evento_CONTAVEL():
    """Gate ① — *"1 `work_events` contável, com o tipo certo"*."""
    fonte = VIGIA_PY.read_text(encoding="utf-8")
    assert 'EVENTO_ESPERA_VENCIDA = "espera.vencida"' in fonte
    corpo = _so_o_codigo_py(fonte.split("async def varrer_esperas_vencidas", 1)[1])
    assert '"event_type": EVENTO_ESPERA_VENCIDA' in corpo
    assert '"company_id": empresa' in corpo, "🔴 o evento nasce sem dono (§7)"


def test_o_varredor_filtra_por_corretora_em_TODA_escrita():
    """🔴 §7 — a varredura é global; o que protege é o `company_id` da PRÓPRIA
    linha em cada ação."""
    corpo = _so_o_codigo_py(
        VIGIA_PY.read_text(encoding="utf-8").split("async def varrer_esperas_vencidas", 1)[1])
    for chamada in re.findall(r'\.table\("(work_waits|conversations)"\)'
                              r'(?:[^;]|\n){0,600}?\.execute\(\)', corpo):
        pass
    # cada `.table("work_waits").update` traz o filtro
    assert corpo.count('.eq("company_id", empresa)') >= 2, (
        f"só {corpo.count('.eq(\"company_id\", empresa)')} filtros de corretora "
        "no varredor — cada escrita precisa do seu")


def test_depois_de_N_avisos_a_conversa_EXPIRA():
    """Gate ④ — e é o motivo que separa *"terminou"* de *"morreu esperando"*."""
    assert FIM.AVISOS_ATE_EXPIRAR == 3
    assert FIM.deve_expirar_a_conversa({"avisos": 3}) is True
    assert FIM.deve_expirar_a_conversa({"avisos": 4}) is True
    assert FIM.deve_expirar_a_conversa({"avisos": 2}) is False
    assert FIM.deve_expirar_a_conversa({"avisos": 0}) is False
    assert FIM.deve_expirar_a_conversa({}) is False


def test_gate_3_espera_SATISFEITA_antes_de_vencer_nao_e_varrida():
    """Gate ③ — *"wait satisfeito antes de vencer → nada acontece"*."""
    ativas = [{"status": "ativo", "vence_em": "2026-08-26T09:00:00+00:00"},
              {"status": "satisfeito", "vence_em": "2026-08-26T08:00:00+00:00"},
              {"status": "cancelado", "vence_em": "2026-08-26T07:00:00+00:00"},
              {"status": "ativo", "vence_em": "2026-08-26T23:00:00+00:00"}]
    vencidas = FIM.esperas_vencidas(ativas, "2026-08-26T10:00:00+00:00")
    assert len(vencidas) == 1
    assert vencidas[0]["vence_em"] == "2026-08-26T09:00:00+00:00"


def test_CONTROLE_sem_hora_nada_vence():
    assert FIM.esperas_vencidas([{"status": "ativo", "vence_em": "x"}], "") == []


def test_o_varredor_ESTA_AGENDADO_ao_lado_do_outro():
    """⛔ Código que ninguém agenda é código que nunca roda — e a espera volta
    a apodrecer em silêncio."""
    codigo = _so_o_codigo_py(AGENDADOR_PY.read_text(encoding="utf-8"))
    assert "varrer_esperas_vencidas" in codigo
    assert 'id="espera_watchdog_check"' in codigo
    assert "max_instances=1" in codigo


def test_o_teto_da_passada_e_DECLARADO_e_nao_silencioso():
    """⚠️ A lição da P-090-03, migrada: um teto que trunca em silêncio conta
    uma história menor **e parece completo**."""
    corpo = VIGIA_PY.read_text(encoding="utf-8").split(
        "async def varrer_esperas_vencidas", 1)[1]
    assert "_MAX_WAITS_POR_PASSADA" in corpo
    assert "ENCHEU" in corpo or "encheu" in corpo, (
        "o teto da passada não avisa quando enche")


# =============================================================================
# BLOCO C.1 · o conserto de agosto virou OBSERVÁVEL
# =============================================================================

def test_o_alerta_de_handoff_passa_a_ser_CONTAVEL():
    """🔴 As três perguntas do C.1 não tinham resposta, e a causa está medida:
    📊 `_avisar_suporte` não gravava em lugar nenhum contável, e `platform_sends`
    tem 5 linhas na base inteira — todas de outra coisa, a mais recente de
    **19/08**, dois dias ANTES do conserto.
    """
    fonte = VIGIA_PY.read_text(encoding="utf-8")
    assert 'EVENTO_HANDOFF_REALERTADO = "handoff.realertado"' in fonte
    assert 'EVENTO_HANDOFF_NO_TETO = "handoff.teto_de_lembretes"' in fonte
    codigo = _so_o_codigo_py(fonte)
    assert "_anotar_no_diario(" in codigo
    # o alerta que SAI conta, e o teto atingido também
    assert codigo.count("_anotar_no_diario(") >= 3, (
        "o diário existe mas não é chamado nos dois pontos que a SPEC pergunta")

    # 🔴 E A CHAMADA TEM DE SER ALCANÇÁVEL. 📊 A bateria pegou este guarda
    #    VERDE: a mutação embrulhava a chamada num `if False:` e a CONTAGEM
    #    não mudava. **Contar ocorrência não é o mesmo que rodar.**
    assert "if False" not in codigo, (
        "há código desligado por `if False` neste arquivo — ele conta na "
        "leitura e não roda em produção")


def test_o_diario_NUNCA_derruba_a_varredura():
    corpo = VIGIA_PY.read_text(encoding="utf-8").split(
        "async def _anotar_no_diario", 1)[1].split("\nasync def ", 1)[0]
    assert "except Exception" in corpo
    codigo = _so_o_codigo_py(corpo)
    assert "raise" not in codigo


def test_o_diario_NAO_grava_dado_de_pessoa():
    """⛔ A trava do Founder."""
    fonte = VIGIA_PY.read_text(encoding="utf-8")
    # 🔴 OS DOIS ESCRITORES DE EVENTO, não só um. 📊 A bateria pegou este
    #    guarda VERDE: a mutação sujava o payload de `_anotar_no_diario`, e o
    #    teste só olhava o de `varrer_esperas_vencidas`.
    for onde in ("async def varrer_esperas_vencidas", "async def _anotar_no_diario"):
        corpo = fonte.split(onde, 1)[1].split("\nasync def ", 1)[0]
        if '"payload_redacted"' not in corpo:
            continue
        carga = corpo.split('"payload_redacted"', 1)[1][:400]
        for proibido in ("user_name", "user_phone", "phone", "cpf", "placa"):
            assert proibido not in carga, (
                f"vaza `{proibido}` no payload de {onde}: {carga[:150]}")


# =============================================================================
# BLOCO D · a pergunta da sexta-feira
# =============================================================================

def test_a_sexta_feira_responde_as_TRES_perguntas():
    """*"quantos terminaram, quantos ainda esperam, e quantos morreram
    esperando?"*"""
    r = FIM.contar_desfechos(
        conversas=[{"resolucao_motivo": FIM.ACIONAMENTO_CONCLUIDO},
                   {"resolucao_motivo": FIM.ENCAMINHADO},
                   {"resolucao_motivo": FIM.FECHADO_POR_HUMANO},
                   {"resolucao_motivo": FIM.EXPIROU},
                   {"resolucao_motivo": FIM.EXPIROU},
                   {"resolucao_motivo": None}],
        waits=[{"status": "ativo", "kind": FIM.ESPERANDO_CLIENTE},
               {"status": "ativo", "kind": FIM.ESPERANDO_CLIENTE},
               {"status": "ativo", "kind": FIM.ESPERANDO_HUMANO},
               {"status": "satisfeito", "kind": FIM.ESPERANDO_CLIENTE}])
    assert r["terminaram"] == 3
    assert r["morreram_esperando"] == 2
    assert r["ainda_esperam"] == 3
    assert r["por_kind"] == {FIM.ESPERANDO_CLIENTE: 2, FIM.ESPERANDO_HUMANO: 1}


def test_EXPIROU_nao_conta_como_TERMINOU():
    """🔴 Contá-lo junto faria a sexta-feira dizer *"12 terminaram"* num dia em
    que sete morreram esperando."""
    r = FIM.contar_desfechos([{"resolucao_motivo": FIM.EXPIROU}] * 7)
    assert r["terminaram"] == 0
    assert r["morreram_esperando"] == 7
    assert FIM.EXPIROU not in FIM.MOTIVOS_DE_SUCESSO


def test_periodo_VAZIO_da_zeros_e_nao_erro():
    """Gate ②."""
    r = FIM.contar_desfechos([], [])
    assert r == {"terminaram": 0, "ainda_esperam": 0, "morreram_esperando": 0,
                 "por_motivo": {}, "por_kind": {}}


def test_conversa_SEM_motivo_nao_entra_em_conta_nenhuma():
    """📊 São 671 hoje — e nenhuma delas terminou."""
    r = FIM.contar_desfechos([{"resolucao_motivo": None},
                              {"resolucao_motivo": ""},
                              {}])
    assert r["terminaram"] == 0 and r["morreram_esperando"] == 0
    assert r["por_motivo"] == {}


def test_o_painel_ao_FECHAR_deixa_marca():
    """🔴 📊 O botão gravava `status='closed'` e mais nada — então *"a atendente
    encerrou"* e *"o cliente desistiu"* eram o mesmo estado para o banco."""
    # 🔴 SÓ O CÓDIGO — SEXTA vez que a prosa engana. 📊 O comentário que eu
    #    mesmo escrevi acima do `update` cita `.is('resolvido_em', null)`, e a
    #    mutação que APAGAVA a linha ficava VERDE.
    rota = _so_o_codigo_ts((RAIZ.parent / "app" / "api" / "dashboard"
                            / "conversas" / "[id]"
                            / "route.ts").read_text(encoding="utf-8"))
    fecho = rota.split("if (action === 'close')", 1)[1].split("if (action === 'send')", 1)[0]
    assert "resolucao_motivo: 'fechado_por_humano'" in fecho
    assert "resolvido_em: agora" in fecho
    assert ".is('resolvido_em', null)" in fecho, (
        "fechar na tela apagaria o desfecho REAL de um atendimento que o robô "
        "já tinha concluído")
    assert ".eq('company_id', ctx.companyId)" in fecho     # 🔴 §7


def test_CONTROLE_o_cortador_de_TS_realmente_corta():
    """§9.3 — se `_so_o_codigo_ts` devolvesse a fonte intocada, o guarda do
    painel voltaria a ler o comentário e ninguém veria."""
    rota_bruta = (RAIZ.parent / "app" / "api" / "dashboard" / "conversas"
                  / "[id]" / "route.ts").read_text(encoding="utf-8")
    limpa = _so_o_codigo_ts(rota_bruta)
    assert len(limpa) < len(rota_bruta), "o cortador não cortou nada"

    alvo = "quem já terminou não termina de novo"
    assert alvo in rota_bruta, "a frase-sentinela sumiu — troque-a"
    assert alvo not in limpa, "o comentário sobreviveu ao corte"
    # ⛔ e não comeu código
    assert "resolucao_motivo: 'fechado_por_humano'" in limpa


def test_a_LISTA_DE_SUCESSO_e_a_MESMA_no_Python_no_TS_e_no_BANCO():
    """🔴 §5 — três cópias que precisam concordar divergem, e a que fica
    para trás conta a história errada na sexta-feira.

    ⚠️ As três existem por razões diferentes: o CHECK **governa** o que entra,
    o Python **decide** o que é sucesso, e o TS **conta** para a tela. Nenhuma
    pode ser apagada; o que dá para fazer é exigir que digam o mesmo.
    """
    rota = _so_o_codigo_ts((RAIZ.parent / "app" / "api" / "dashboard"
                            / "atendimentos"
                            / "route.ts").read_text(encoding="utf-8"))
    sql = _so_o_codigo_sql(MIG_A.read_text(encoding="utf-8"))

    # o TS conta como sucesso exatamente os quatro do Python
    bloco = rota.split("const SUCESSO = new Set([", 1)[1].split("]);", 1)[0]
    no_ts = {p.strip().strip("',\"") for p in bloco.replace(chr(10), " ").split(",")}
    no_ts = {x for x in no_ts if x}
    assert no_ts == set(FIM.MOTIVOS_DE_SUCESSO), (
        f"a lista do painel e a do Python discordam.{chr(10)}"
        f"  TS ....: {sorted(no_ts)}{chr(10)}"
        f"  Python : {sorted(FIM.MOTIVOS_DE_SUCESSO)}")

    # 🔴 e `expirou` NÃO está entre eles, nos dois lados
    assert FIM.EXPIROU not in no_ts
    assert "if (m === 'expirou') morreram += 1;" in rota, (
        "o painel deixou de separar quem MORREU esperando de quem terminou")

    # e o CHECK do banco conhece os cinco
    for motivo in FIM.MOTIVOS:
        assert f"'{motivo}'" in sql, f"o CHECK não conhece {motivo!r}"


def test_o_painel_filtra_por_corretora_nas_DUAS_consultas_novas():
    """🔴 §7 — uma só consulta sem `company_id` mostra a semana de TODAS as
    corretoras na tela de UMA."""
    rota = _so_o_codigo_ts((RAIZ.parent / "app" / "api" / "dashboard"
                            / "atendimentos"
                            / "route.ts").read_text(encoding="utf-8"))
    bloco = rota.split("const semana = new Date(", 1)[1].split("return NextResponse", 1)[0]
    assert bloco.count("eq('company_id', ctx.companyId)") == 2, (
        f"só {bloco.count(chr(34)+chr(34))} filtros — as DUAS consultas precisam do seu")


def test_o_painel_DECLARA_quando_os_contadores_nao_carregaram():
    """⛔ O zero silencioso de novo: sumir com os campos faria a tela mostrar
    "0 terminaram" num dia em que ninguém conseguiu olhar."""
    rota = _so_o_codigo_ts((RAIZ.parent / "app" / "api" / "dashboard"
                            / "atendimentos"
                            / "route.ts").read_text(encoding="utf-8"))
    assert "indisponivel: true" in rota
    assert "indisponivel: false" in rota
    assert "semana: semanaResumo" in rota
