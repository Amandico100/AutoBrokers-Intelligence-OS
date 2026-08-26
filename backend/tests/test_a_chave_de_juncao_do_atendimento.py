# -*- coding: utf-8 -*-
"""A chave de junção — SPEC-090, BLOCO A.

> **O TESTE DO PRODUTO:** *"o cliente escreveu X, o robô abriu o chamado, travou
> na tela Y"* tem de ser reconstruível. Hoje `work_runs` não tinha NENHUMA
> coluna de conversa — 📊 medido em 26/08: 50 colunas, nenhuma delas.

## 🔴 O QUE O BLOCO 0 DERRUBOU DA PRÓPRIA SPEC

A SPEC abre com *"as três ilhas não se falam"*:

```
attendance_transcripts .... 152.300 com session_id
   que casam com conversations.id ................. 0
   que casam com observed_sessions.id ............. 0
```

📊 Os dois zeros estão certos. ⚠️ **E são irrelevantes** — a SPEC testou contra
duas tabelas que nunca foram o alvo. Medido no mesmo banco, no mesmo dia:

```
session_id casa `attendance_sessions.id` ................ 95 de 95   100,0%
(company_id, counterparty) casa `conversations`
   por (company_id, user_phone) ......................... 63 de 63   100,0%
```

🔴 **A camada de resolução de identidade que a SPEC diz faltar já existe.** O
que faltava era durabilidade em UM lugar: `work_runs`.

📊 E o backfill que a SPEC orça como o trabalho que domina as ~4h tem **QUATRO
LINHAS** de alvo — 4 `acionamento.seguradora` em 2.778 runs (0,1%).

## ⚠️ E o que eu errei, e a medição me corrigiu

Eu tinha descartado a *"janela de tempo"* da regra de evidência como
sobre-engenharia para quatro linhas. 📊 **Errado:** os quatro acionamentos têm
DOIS candidatos cada — o mesmo telefone tem a conversa do agente interno (04/07
a 15/07) e a do Espelho (17/08 a 20/08). Só por telefone, os quatro ficam
ambíguos e nulos. **Com a janela, os quatro resolvem.**
"""
from __future__ import annotations

import importlib.util as _u
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MIGRATION = (RAIZ / "supabase" / "migrations"
             / "20260826_02_spec090_blocoA_work_runs_conversation_id.sql")
BACKFILL = RAIZ / "scripts" / "backfill_spec090_work_runs_conversation.py"
ROTEADOR_PY = RAIZ / "app" / "services" / "dispatch_router.py"


def _carregar(rel: str, nome: str):
    """Por CAMINHO — `app/services/__init__.py` arrasta `fastembed`, que não
    existe em toda máquina. O módulo em si não depende de nada."""
    spec = _u.spec_from_file_location(nome, RAIZ / rel)
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


JUNCAO = _carregar("app/services/o_dia_de_ontem.py", "_juncao_090")


# =============================================================================
# 🔴 SÓ O CÓDIGO — a prosa não conta como prova
# =============================================================================
#
# 📊 A bateria de mutação deste bloco pegou DOIS guardas verdes, e os dois eram
# o mesmo defeito meu: a asserção casava contra o **comentário**, não contra o
# código.
#
#   · `.eq("company_id"` apagado da consulta → o teste continuava PASSANDO,
#     porque a docstring da própria função diz *"esquecer o `.eq("company_id")`"*.
#   · `UNIQUE (id, company_id)` virando `UNIQUE (id)` no `ALTER TABLE` → também
#     PASSAVA, porque o bloco VERIFY repete a frase num comentário `--`.
#
# ⚠️ Nos dois casos o guarda estava lendo a explicação de por que o código
# deveria existir, e concluindo que ele existia. §9.3: *um guarda que não tem
# como falhar não guarda nada.*


def _so_o_codigo_sql(sql: str) -> str:
    """O SQL sem os comentários `--`. ⛔ O bloco VERIFY inteiro é comentário."""
    return "\n".join(linha.split("--", 1)[0] for linha in sql.splitlines())


def _corpo_sem_docstring(fonte: str, assinatura: str) -> str:
    """O corpo de uma função, **sem a docstring** — só o que executa."""
    trecho = fonte.split(assinatura, 1)[1].split("\nasync def ", 1)[0].split("\ndef ", 1)[0]
    # a docstring é o primeiro literal triplo do corpo
    partes = trecho.split('"""')
    return partes[0] + "".join(partes[2:]) if len(partes) >= 3 else trecho


# =============================================================================
# 🔴 CONTROLE DE CARGA — §9.3: um guarda que não carrega não guarda nada
# =============================================================================

def test_CONTROLE_o_modulo_carregou_de_verdade():
    """📊 Na SPEC-087 um arquivo inteiro passou por IGNORÂNCIA: o import falhou,
    o `except` engoliu, e as asserções ficaram verdes sobre um caminho morto.

    ⛔ Se este teste falhar, **nenhum outro deste arquivo vale nada.**
    """
    assert callable(JUNCAO.decidir_conversa_do_run)
    assert callable(JUNCAO.telefone_do_caso)
    assert JUNCAO.WORKFLOWS_COM_CONVERSA == ("acionamento.seguradora",)


# =============================================================================
# ① o telefone sai do case_id — e NÃO É ADIVINHADO
# =============================================================================

def test_o_telefone_sai_do_case_id():
    assert JUNCAO.telefone_do_caso("wa-554788087000") == "554788087000"
    assert JUNCAO.telefone_do_caso("WA-5511999998888") == "5511999998888"


def test_o_case_id_QUE_NAO_E_TELEFONE_devolve_vazio():
    """⛔ Não adivinha. A P-262 nasceu de um padrão sem fronteira que comeu
    dígitos dentro de um sha256 e **corrompeu uma linha de produção**."""
    for entrada in ("", None, "wa-", "wa-abc", "caso-554788087000",
                    "wa-554788087000-retry", "  wa-554788087000  ".strip() + "!",
                    "wa-123", "wa-1234567890123456"):
        assert JUNCAO.telefone_do_caso(entrada) == "", f"adivinhou em {entrada!r}"


def test_o_hash_com_digitos_NAO_vira_telefone():
    """🔴 A lição da P-262, migrada (§9.3): um sha256 tem corridas de 10+ dígitos."""
    sha = "a1b2c355478808700012345678901234abcdef0123456789abcdef0123456789"
    assert JUNCAO.telefone_do_caso(sha) == ""
    assert JUNCAO.telefone_do_caso(f"wa-{sha}") == ""


# =============================================================================
# ② 🔴 A JANELA — e é o guarda que a SPEC manda ficar vermelho na mutação
# =============================================================================

_JULHO = {"id": "11111111-1111-1111-1111-111111111111",
          "created_at": "2026-07-04T21:42:21+00:00",
          "last_message_at": "2026-07-15T12:13:58+00:00"}
_AGOSTO = {"id": "22222222-2222-2222-2222-222222222222",
           "created_at": "2026-08-17T17:28:59+00:00",
           "last_message_at": "2026-08-20T17:16:19+00:00"}
_RUN = "2026-08-18T01:48:35+00:00"


def test_A_JANELA_escolhe_a_conversa_VIVA_e_ignora_a_morta():
    """🔴 O caso REAL, com os dados REAIS de produção (26/08).

    ⚠️ **A mutação que a SPEC manda:** afrouxe a regra para "só telefone, sem
    janela" e este teste tem de ficar VERMELHO. Sem janela há duas candidatas,
    e duas candidatas viram NULO — o run de agosto perde a conversa dele.

    ⛔ E "a mais recente" é pior ainda: ela sempre devolve alguém, inclusive
    quando as duas estão vivas ao mesmo tempo — que é exatamente o caso em que
    a resposta não existe.
    """
    escolhida, porque = JUNCAO.decidir_conversa_do_run([_JULHO, _AGOSTO], _RUN)
    assert escolhida == _AGOSTO["id"], (
        f"escolheu {escolhida!r} (motivo {porque!r}) — a conversa de julho estava "
        "morta havia 34 dias quando o run nasceu")
    assert porque == JUNCAO.LIGADA


def test_CONTROLE_a_ordem_das_candidatas_nao_muda_a_resposta():
    """§9.3 — sem esta linha, o teste acima passaria com um `return primeira`."""
    a, _ = JUNCAO.decidir_conversa_do_run([_JULHO, _AGOSTO], _RUN)
    b, _ = JUNCAO.decidir_conversa_do_run([_AGOSTO, _JULHO], _RUN)
    assert a == b == _AGOSTO["id"], (
        f"a ordem mudou a resposta: {a!r} vs {b!r} — a regra virou 'a primeira'")


def test_CONTROLE_um_run_de_JULHO_escolhe_a_conversa_de_JULHO():
    """🔴 A linha que dá direito à conclusão.

    ⚠️ Sem ela, uma regra degenerada — *"devolve sempre a mais recente"* —
    passaria em todos os testes acima. Este é o mesmo alvo, a mesma lista, e a
    resposta tem de ser **a outra**.
    """
    escolhida, porque = JUNCAO.decidir_conversa_do_run(
        [_JULHO, _AGOSTO], "2026-07-10T09:00:00+00:00")
    assert escolhida == _JULHO["id"], (
        f"devolveu {escolhida!r} para um run de julho — a regra é 'a mais "
        "recente', não 'a que estava viva'")


# =============================================================================
# ③ 🔴 O QUE NÃO DÁ PARA PROVAR FICA NULO — o gate mais importante do bloco
# =============================================================================

def test_DUAS_conversas_vivas_ao_mesmo_tempo_ficam_NULAS():
    """⛔ Ninguém sabe a resposta, e o produto diz isso.

    📊 A ambiguidade não é hipotética: medido em 26/08 sobre as 671 conversas,
    **2 pares (corretora, telefone) têm mais de uma, e o pior caso tem 57**.
    """
    outra = dict(_AGOSTO, id="33333333-3333-3333-3333-333333333333")
    escolhida, porque = JUNCAO.decidir_conversa_do_run([_AGOSTO, outra], _RUN)
    assert escolhida is None, (
        f"escolheu {escolhida!r} entre DUAS conversas vivas ao mesmo tempo — "
        "isso é inventar, e um conversation_id errado produz relatório "
        "confiante e falso")
    assert porque == JUNCAO.AMBIGUA


def test_NENHUMA_conversa_viva_fica_NULA():
    escolhida, porque = JUNCAO.decidir_conversa_do_run([_JULHO], _RUN)
    assert escolhida is None
    assert porque == JUNCAO.SEM_CONVERSA


def test_lista_vazia_e_run_sem_hora_ficam_NULOS():
    assert JUNCAO.decidir_conversa_do_run([], _RUN)[0] is None
    assert JUNCAO.decidir_conversa_do_run([_AGOSTO], "")[0] is None
    assert JUNCAO.decidir_conversa_do_run([_AGOSTO], None)[0] is None


def test_conversa_SEM_last_message_at_cai_para_created_at():
    """⚠️ Uma conversa sem nenhuma mensagem viveu um instante — e um instante
    não cobre um run de outro dia. ⛔ Tratar o vazio como "até sempre" faria
    toda conversa recém-criada engolir todo run futuro."""
    nova = {"id": "44444444-4444-4444-4444-444444444444",
            "created_at": "2026-08-17T17:28:59+00:00", "last_message_at": None}
    assert JUNCAO.decidir_conversa_do_run([nova], _RUN)[0] is None
    # e no instante exato ela vale
    assert JUNCAO.decidir_conversa_do_run([nova], nova["created_at"])[0] == nova["id"]


def test_conversa_SEM_created_at_e_ignorada_e_nao_derruba():
    quebrada = {"id": "55555555-5555-5555-5555-555555555555",
                "created_at": None, "last_message_at": "2026-08-20T00:00:00+00:00"}
    escolhida, _ = JUNCAO.decidir_conversa_do_run([quebrada, _AGOSTO], _RUN)
    assert escolhida == _AGOSTO["id"]


# =============================================================================
# ④ 🔴 DOIS TENANTS — e aqui o guarda é do BANCO, não do código
# =============================================================================

def test_a_migration_tem_FK_COMPOSTA_com_company_id():
    """🔴 O isolamento entre corretoras vira constraint do banco.

    ⚠️ `CLAUDE.md` §7: o backend usa service role e atravessa a RLS inteira. A
    única proteção real é o filtro no código — e um filtro é uma linha que
    alguém pode esquecer numa refatoração de terça.

    ⛔ Uma FK **simples** para `conversations(id)` provaria que a conversa
    existe, não que ela é da mesma corretora. É a diferença entre o guarda e a
    aparência dele.
    """
    # 🔴 SÓ O CÓDIGO. 📊 A mutação `UNIQUE (id, company_id)` → `UNIQUE (id)`
    #    ficava VERDE porque o bloco VERIFY repete a frase num comentário.
    sql = _so_o_codigo_sql(MIGRATION.read_text(encoding="utf-8"))
    assert "FOREIGN KEY (conversation_id, company_id)" in sql, (
        "a FK não é composta — ela não sabe conferir a corretora")
    assert "REFERENCES public.conversations (id, company_id)" in sql
    assert "UNIQUE (id, company_id)" in sql, (
        "sem a UNIQUE composta em `conversations`, o Postgres RECUSA criar a FK")
    assert "ON DELETE SET NULL" in sql, (
        "apagar a conversa não pode apagar o histórico do trabalho")


def test_a_migration_e_idempotente_e_expand_first():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS conversation_id" in sql
    assert "CREATE INDEX IF NOT EXISTS" in sql
    assert sql.count("IF NOT EXISTS (") >= 2, (
        "as constraints precisam do guarda `IF NOT EXISTS` — `ALTER TABLE ADD "
        "CONSTRAINT` não tem essa forma e explode na segunda rodada")
    for destrutivo in ("DROP TABLE", "DELETE FROM", "TRUNCATE", "DROP COLUMN"):
        assert destrutivo not in sql.split("-- ROLLBACK")[0].upper().replace(
            "DROP COLUMN IF EXISTS", ""), f"{destrutivo} no APPLY"


def test_o_VERIFY_da_migration_tem_LINHA_DE_CONTROLE():
    """§9.2 — *"a linha de controle é o que dá direito à conclusão"*.

    ⚠️ Provar que o banco RECUSA cross-tenant não vale nada sozinho: ele podia
    estar recusando TUDO. 📊 E não é hipótese — na primeira rodada deste VERIFY
    os três inserts falharam com `23502` e `23514`, por `NOT NULL` e por um
    CHECK de formato de `thread_id`, **nada a ver com a FK**. Sem a linha de
    controle, eu teria creditado a recusa ao guarda errado.
    """
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "mesma corretora ACEITO" in sql or "mesma corretora" in sql
    assert "cross-tenant" in sql.lower()


# =============================================================================
# ⑤ o escritor grava NULO na dúvida — nunca deixa a FK ser quem recusa
# =============================================================================

def test_o_escritor_confere_a_corretora_ANTES_de_gravar():
    """🔴 A FK é a SEGUNDA linha de defesa, não a primeira.

    ⛔ Deixar o banco recusar custaria o acionamento inteiro: o `INSERT` do run
    é um só, e se ele falha por causa desta coluna o run não nasce, o segurado
    fica esperando, e o produto perde a corrida por causa de um campo de
    relatório.
    """
    fonte = ROTEADOR_PY.read_text(encoding="utf-8")
    assert "_conversa_provada_da_sessao" in fonte
    # 🔴 SEM A DOCSTRING. 📊 Com ela, apagar o `.eq("company_id")` da consulta
    #    deixava este teste VERDE — a própria docstring diz a frase.
    corpo = _corpo_sem_docstring(fonte, "async def _conversa_provada_da_sessao")
    assert '.eq("company_id"' in corpo, (
        "🔴 o escritor NÃO filtra por corretora — é o filtro do §7 que protege, "
        "e sem ele a FK vira a primeira linha e derruba o acionamento")
    assert 'session.get("mirror_conversation_id")' in corpo, (
        "o dado já está na mão do dispatch — `dispatch_mirror.py:55-60`")
    assert "return None" in corpo


def test_CONTROLE_o_cortador_de_docstring_realmente_corta():
    """§9.3 — *"prove que as duas coisas CONSEGUEM ser diferentes"*.

    ⛔ Se `_corpo_sem_docstring` devolvesse o texto inteiro, os dois testes
    acima voltariam a passar por causa da prosa, e ninguém notaria.
    """
    fonte = ROTEADOR_PY.read_text(encoding="utf-8")
    inteiro = fonte.split("async def _conversa_provada_da_sessao", 1)[1].split("\nasync def ", 1)[0]
    corpo = _corpo_sem_docstring(fonte, "async def _conversa_provada_da_sessao")
    assert len(corpo) < len(inteiro), "o cortador não cortou nada"
    alvo = "POR QUE ESTA FUNÇÃO CONFERE A CORRETORA"
    assert alvo in inteiro, "a frase-sentinela sumiu da docstring — troque-a"
    assert alvo not in corpo, (
        "a docstring sobreviveu ao corte — os guardas acima voltam a ler prosa")


def test_CONTROLE_o_cortador_de_comentario_SQL_realmente_corta():
    """§9.3 — a mesma prova, do outro lado."""
    sql = MIGRATION.read_text(encoding="utf-8")
    limpo = _so_o_codigo_sql(sql)
    assert len(limpo) < len(sql) * 0.6, "o cortador de comentário mal cortou"
    alvo = "cross-tenant recusado"
    assert alvo in sql, "a frase-sentinela sumiu do VERIFY — troque-a"
    assert alvo not in limpo, "o cortador deixou comentario passar"


def test_o_escritor_recusa_company_id_que_NAO_e_uuid():
    """📊 O simulador de acionamento usa `company_id="sim"` — a SPEC-087 já
    pagou por confiar na forma do texto (o gancho da tela cega disparava dentro
    do simulador)."""
    fonte = ROTEADOR_PY.read_text(encoding="utf-8")
    assert "_UUID" in fonte
    trecho = fonte.split("async def _conversa_provada_da_sessao", 1)[1].split("\nasync def ", 1)[0]
    assert "_UUID.match(str(company_id" in trecho, (
        "o escritor aceita company_id que não é UUID — `sim` passaria")


def test_o_run_grava_conversation_id_no_ATO():
    """Gate ① — *"acionamento novo → `conversation_id` preenchido no ato"*."""
    fonte = ROTEADOR_PY.read_text(encoding="utf-8")
    linha = fonte.split("    linha = {", 1)[1].split("\n    }", 1)[0]
    assert "conversation_id" in linha, (
        "o run nasce SEM a coluna — o backfill teria de rodar para sempre")
    assert "_conversa_provada_da_sessao" in linha


# =============================================================================
# ⑥ o backfill não escreve uma SEGUNDA regra ao lado da do produto
# =============================================================================

def test_o_backfill_USA_a_regra_do_produto_e_nao_a_copia():
    """🔴 A lição da SPEC-087, migrada (§9.3, §5).

    📊 Lá o backfill tinha uma cópia da função do escritor. O escritor ganhou
    uma exclusão no conserto do painel; **a cópia não ganhou** — e o script que
    já corrompeu uma `signature` em produção prometia idempotência (P-262).
    """
    fonte = BACKFILL.read_text(encoding="utf-8")
    assert "o_dia_de_ontem" in fonte, "o backfill não importa a regra do produto"
    assert "decidir_conversa_do_run" in fonte
    # ⛔ e não redefine a regra localmente
    assert not re.search(r"^def decidir_conversa_do_run", fonte, re.M), (
        "o backfill REDEFINE a regra — duas regras que precisam concordar divergem")
    assert not re.search(r"^_TELEFONE_DO_CASO\s*=", fonte, re.M), (
        "o backfill tem a própria regex de telefone — é a P-262 de novo")


def test_o_backfill_reporta_os_NULOS_separados_por_motivo():
    """Gate ③ — *"o número de NULOs é REPORTADO"*, e a SPEC avisa que
    *"backfill 100%" é a resposta suspeita, não a boa*."""
    fonte = BACKFILL.read_text(encoding="utf-8")
    assert "FICARAM NULAS" in fonte
    assert "suspeito" in fonte.lower(), (
        "o script não avisa que 100% é o número suspeito")
    assert "motivo.most_common()" in fonte, (
        "os NULOS não são separados por motivo — três causas diferentes pedem "
        "três consertos diferentes")


def test_o_backfill_so_toca_em_quem_ainda_esta_NULO():
    """⛔ Idempotente. 📊 Provado em produção: 2ª rodada = `0 de 0`."""
    fonte = BACKFILL.read_text(encoding="utf-8")
    assert '.is_("conversation_id", "null")' in fonte


def test_o_backfill_filtra_por_corretora_no_UPDATE():
    """🔴 §7 — o `.eq("id")` sozinho já é único, mas o filtro por corretora é o
    que sobrevive a uma refatoração que troque o `id` por outra chave."""
    fonte = BACKFILL.read_text(encoding="utf-8")
    trecho = fonte.split('.table("work_runs").update(', 1)[1][:220]
    assert '.eq("company_id", empresa)' in trecho


def test_o_backfill_NUNCA_imprime_telefone():
    """⛔ A trava do Founder. O script imprime id curto e veredito — nunca o
    telefone, nem o texto."""
    fonte = BACKFILL.read_text(encoding="utf-8")
    for chamada in re.findall(r"print\(f?\"[^\"]*\"", fonte):
        assert "{tel" not in chamada, f"o telefone vaza em: {chamada[:80]}"
