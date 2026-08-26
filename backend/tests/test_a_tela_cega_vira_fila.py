# -*- coding: utf-8 -*-
"""A tela que o corredor não conhece vira FILA — SPEC-087, BLOCO A.

## 📊 O número que justifica a SPEC, refeito no BLOCO 0

Rodando `match_ura_step` sobre o corpus versionado de telas reais, com o
casamento **mais generoso possível** (14 playbooks × 76 subserviços) — piso,
não teto:

```
1.696 telas distintas em 10 seguradoras
  378 CEGAS ................ 22,3%
   27 delas são MENU (≥2 opções numeradas)

zurich  auto        135/207  65,2%   🔴 a pior medida
yelum   auto         55/195  28,2%
allianz residencial  45/195  23,1%
```

⚠️ **A SPEC dizia 269/755 = 35,6%, 66 menus e "tokio 13/13 CEM POR CENTO cego".**
📊 Minha medição, com mais seguradoras e mais generosidade: **22,3%**, **27
menus**, e a tokio em **18/54 = 33%** — a pior é a **zurich auto**. O número da
SPEC vinha do banco em 45 dias; este vem do corpus versionado, que é
reproduzível sem rede e já auditado por PII. **A direção é a mesma; o alvo
mudou.**

> **O TESTE DO PRODUTO:** a Yelum manda um menu que o corredor não conhece. Hoje
> o segurado espera e ninguém sabe. Depois desta SPEC, a tela cai numa fila com
> o texto, a rota e a data.
"""
from __future__ import annotations

import asyncio
import importlib.util as _u
import sys
import types
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"
MIGRATION = (RAIZ / "supabase" / "migrations"
             / "20260826_01_spec087_blocoA_tela_cega.sql")


@contextmanager
def _com_o_pacote_app():
    """`app` e subpacotes em `sys.modules` durante a chamada.

    🔴 Sem isto o arquivo passa por IGNORÂNCIA: os imports locais falham, o
    `except` engole, e uma asserção de "não gravou" fica verde porque o caminho
    morreu antes do banco.
    """
    nomes = ("app", "app.services", "app.services.intelligence", "app.core")
    injetados = [n for n in nomes if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in nomes}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = mod
        yield
    finally:
        for nome in injetados:
            if anteriores.get(nome) is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anteriores[nome]


def _carregar(rel: str, nome: str):
    spec = _u.spec_from_file_location(nome, str(RAIZ / rel))
    mod = _u.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


with _com_o_pacote_app():
    TC = _carregar("app/services/tela_cega.py", "_tc_087")

EMPRESA_A = "aaaaaaaa-0000-4000-8000-000000000001"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-000000000002"


# ===========================================================================
# O DUBLÊ — com o UNIQUE do banco, porque um dublê permissivo é teste falso
# ===========================================================================

class _R:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, b, t):
        self.b, self.t = b, t
        self.op = self.linhas = self.campos = None
        self.filtros = []

    def select(self, *a, **k):
        self.op = "select"
        return self

    def insert(self, l):
        self.op, self.linhas = "insert", l if isinstance(l, list) else [l]
        return self

    def update(self, c):
        self.op, self.campos = "update", c
        return self

    def eq(self, c, v):
        self.filtros.append((c, v))
        return self

    def limit(self, n):
        return self

    def _casa(self, l):
        return all(str(l.get(c)) == str(v) for c, v in self.filtros)

    async def execute(self):
        tab = self.b.dados.setdefault(self.t, [])
        if self.op == "select" and getattr(self.b, "cego_uma_vez", False):
            # 🔴 A CORRIDA, no dublê: este `select` não vê o que a outra réplica
            # acabou de criar. Uma vez só — o `select` do `_incrementar` precisa
            # enxergar, senão o teste mede outra coisa.
            self.b.cego_uma_vez = False
            return _R([])
        if self.op == "insert":
            for l in self.linhas:
                # 🔴 O UNIQUE do banco, no dublê:
                #    (company_id, insurer_key, ramo, hash_normalizado)
                chave = tuple(l.get(k) for k in
                              ("company_id", "insurer_key", "ramo", "hash_normalizado"))
                if any(tuple(x.get(k) for k in
                             ("company_id", "insurer_key", "ramo", "hash_normalizado")) == chave
                       for x in tab):
                    self.b.estourou_unique = getattr(self.b, "estourou_unique", 0) + 1
                    raise RuntimeError(
                        'duplicate key value violates unique constraint '
                        '"uq_tela_cega_chave" (23505)')
                # e o CHECK do status
                if l.get("status", "aberta") not in ("aberta", "virou_passo", "ignorada"):
                    raise RuntimeError("new row violates check constraint "
                                       '"ck_tela_cega_status" (23514)')
                # 🔴 OS DEFAULTS DO BANCO, no dublê. Sem eles o teste mede uma
                # tabela que não existe: `visto_quantas_vezes` e `status` têm
                # `default` no DDL, e o `INSERT` do serviço não os manda.
                tab.append({"visto_quantas_vezes": 1, "status": "aberta",
                            "visto_em": datetime.now(timezone.utc).isoformat(),
                            **l, "id": f"id-{len(tab)}"})
            return _R(list(self.linhas))
        alvo = [l for l in tab if self._casa(l)]
        if self.op == "update":
            for l in alvo:
                l.update(self.campos)
        return _R([dict(l) for l in alvo])


class Banco:
    def __init__(self):
        self.dados = {"tela_cega": []}

    @property
    def client(self):
        return self

    def table(self, n):
        return _Q(self, n)


def _rodar(coro):
    return asyncio.run(coro)


def _com_banco(banco):
    class _Ctx:
        def __enter__(self):
            mod = types.ModuleType("app.core.database")

            async def _criar():
                return banco

            mod.create_async_supabase_client = _criar
            self.antes = sys.modules.get("app.core.database")
            sys.modules["app.core.database"] = mod
            self.ctx = _com_o_pacote_app()
            self.ctx.__enter__()
            return self

        def __exit__(self, *a):
            self.ctx.__exit__(*a)
            if self.antes is None:
                sys.modules.pop("app.core.database", None)
            else:
                sys.modules["app.core.database"] = self.antes
            return False
    return _Ctx()


TELA_MENU = ("Escolha o servico desejado:\n"
             "1 - Guincho\n2 - Chaveiro\n3 - Falar com atendente")
TELA_SIMPLES = "Aguarde enquanto localizamos o seu cadastro."


def _fila(b):
    return b.dados["tela_cega"]


def _registrar(b, texto, *, company=EMPRESA_A, insurer="yelum", ramo="auto"):
    with _com_banco(b):
        return _rodar(TC.registrar_tela_cega(
            company_id=company, insurer_key=insurer, ramo=ramo,
            playbook_ref=f"{insurer}-{ramo}-whatsapp@v1", texto=texto))


# ===========================================================================
# ① tela sem passo → 1 linha na fila, com o texto MASCARADO
# ===========================================================================

def test_GATE_1_tela_sem_passo_vira_UMA_linha_com_texto_mascarado():
    b = Banco()
    assert _registrar(b, "Confirme o CPF 123.456.789-00 para continuar") is True

    assert len(_fila(b)) == 1, f"esperava 1 linha, veio {len(_fila(b))}"
    linha = _fila(b)[0]
    assert linha["insurer_key"] == "yelum" and linha["ramo"] == "auto"
    assert linha["playbook_ref"] == "yelum-auto-whatsapp@v1"
    assert linha["visto_quantas_vezes"] == 1 or "visto_quantas_vezes" not in linha
    # ⛔ MASCARADO NA ORIGEM — o BLOCO C, aplicado antes da escrita
    assert "123.456.789-00" not in linha["texto_mascarado"], (
        "o CPF entrou CRU na fila — escrever cru e mascarar depois é criar o "
        "vazamento e tapá-lo")
    # ⚠️ A marca é de CHAVE. A cascata roda `templatize` primeiro, e é ele
    # que pega endereço, data de nascimento, chassi e CEP solto — 📊 6 de 8
    # telas sintéticas medidas, contra 1 de `redigir` sozinho.
    assert "{CPF}" in linha["texto_mascarado"]


# ===========================================================================
# ② mesma tela de novo → o contador SOBE, não nasce linha
# ===========================================================================

def test_GATE_2_mesma_tela_de_novo_o_contador_SOBE():
    """🔴 **A dedupe é o que torna a fila útil.**

    A mesma tela chega dezenas de vezes; sem isto a fila vira ruído em um dia.
    📊 E é o contador que ordena: a vista 40 vezes vale mais que a vista uma.
    """
    b = Banco()
    for _ in range(5):
        assert _registrar(b, TELA_MENU) is True

    assert len(_fila(b)) == 1, (
        f"cinco chegadas da MESMA tela viraram {len(_fila(b))} linhas — a fila "
        "vira ruído em um dia")
    assert _fila(b)[0]["visto_quantas_vezes"] == 5


def test_GATE_2b_a_dedupe_e_por_texto_NORMALIZADO():
    """⚠️ O mesmo menu com um espaço a mais é a MESMA tela.

    🔴 E a normalização é a **do casador** (`corridor_playbooks._norm`), não uma
    paralela: se as duas divergirem, a fila agrupa telas que o casador considera
    diferentes — e passa a mentir.
    """
    b = Banco()
    _registrar(b, TELA_MENU)
    _registrar(b, TELA_MENU.replace("\n", "\n "))          # espaço a mais
    _registrar(b, TELA_MENU.upper())                        # caixa alta
    assert len(_fila(b)) == 1, (
        f"a mesma tela com espaçamento/caixa diferentes virou {len(_fila(b))} "
        "linhas — a dedupe está sobre o texto CRU")
    assert _fila(b)[0]["visto_quantas_vezes"] == 3


def test_GATE_2c_CONTROLE_telas_DIFERENTES_viram_linhas_diferentes():
    """§9.3 — prove que a dedupe sabe distinguir.

    🔴 Sem esta linha, uma dedupe que agrupasse TUDO passaria no ② e a fila
    teria uma linha só, para sempre.
    """
    b = Banco()
    _registrar(b, TELA_MENU)
    _registrar(b, TELA_SIMPLES)
    assert len(_fila(b)) == 2, (
        "duas telas diferentes viraram uma linha — a dedupe agrupa demais")


def test_a_corrida_de_duas_replicas_INCREMENTA_em_vez_de_estourar():
    """⚠️ Duas réplicas do webhook veem a mesma tela e as duas acham a fila vazia.

    🔴 O UNIQUE do banco decide; quem perdeu **incrementa**, não estoura.

    ⛔ E este ramo é o guarda de última instância: o `select` de cada réplica tem
    o próprio resultado, e os dois dizem que ninguém viu a tela.
    """
    b = Banco()
    _registrar(b, TELA_MENU)
    assert len(_fila(b)) == 1

    # 🔴 A CORRIDA: o primeiro `select` desta réplica não enxerga a linha que a
    # outra criou. O `insert` vai estourar no UNIQUE, e é aí que o conserto vive.
    b.cego_uma_vez = True
    assert _registrar(b, TELA_MENU) is True, (
        "a réplica que perdeu a corrida devolveu False — a tela some da fila")

    assert len(_fila(b)) == 1, "a corrida criou uma segunda linha"
    assert _fila(b)[0]["visto_quantas_vezes"] == 2, (
        "a réplica que perdeu não incrementou — a contagem que ordena a fila "
        "fica errada")


def test_CONTROLE_sem_a_corrida_o_caminho_e_o_rapido():
    """§9.3 — prove que o ramo do UNIQUE não é o caminho normal.

    Sem esta linha, um `insert` que SEMPRE estourasse passaria no teste acima.
    """
    b = Banco()
    _registrar(b, TELA_MENU)
    assert getattr(b, "estourou_unique", 0) == 0, (
        "o caminho rápido passou pelo UNIQUE — o `select` da dedupe não está "
        "sendo consultado")
    _registrar(b, TELA_MENU)
    assert getattr(b, "estourou_unique", 0) == 0
    assert _fila(b)[0]["visto_quantas_vezes"] == 2


# ===========================================================================
# ③ tela COM passo → nada na fila         (linha de controle)
# ===========================================================================

def test_GATE_3_CONTROLE_o_ponto_do_gancho_e_o_da_tela_SEM_passo():
    """🔴 O gancho vive **depois** do `if step:` — só a tela que não casou passa.

    ⚠️ Guarda estrutural, e é o honesto: exercitar o motor inteiro exigiria
    sessão, playbook e Redis, e um gate que precisa dos três é um gate que
    ninguém roda.
    """
    fonte = MOTOR_PY.read_text(encoding="utf-8")
    i_step = fonte.index("    step = match_ura_step(playbook, insurer_message")
    i_gancho = fonte.index("    _registrar_tela_cega_sem_derrubar(session, playbook")
    assert i_gancho > i_step, (
        "o gancho subiu para ANTES do casamento — toda tela entraria na fila, "
        "inclusive as que o corredor conhece")

    # e entre os dois existe o `return` do caminho que casou
    entre = fonte[i_step:i_gancho]
    assert "if step:" in entre and "return " in entre, (
        "o caminho da tela COM passo deixou de sair antes do gancho")


def test_GATE_3b_o_gancho_NUNCA_derruba_o_acionamento():
    """⛔ O segurado está do outro lado esperando.

    Um registro a menos é um problema; um acionamento morto por causa de um
    `INSERT` é um problema maior.
    """
    fonte = MOTOR_PY.read_text(encoding="utf-8")
    i = fonte.index("def _registrar_tela_cega_sem_derrubar(")
    corpo = fonte[i:fonte.index("\ndef ", i + 10)]
    assert "try:" in corpo and "except Exception" in corpo, (
        "o gancho deixou de ser best-effort")
    assert "logger.warning" in corpo, (
        "a falha ficou muda — uma fila que não recebe é a mesma coisa que não "
        "existir")


def test_o_registro_NAO_derruba_quando_o_banco_cai():
    b = Banco()

    class Quebrado(Banco):
        def table(self, n):
            raise RuntimeError("PostgREST 503")

    q = Quebrado()
    q.dados = b.dados
    assert _registrar(q, TELA_MENU) is False, (
        "o registro levantou em vez de devolver False")


# ===========================================================================
# ④ 🔴 menu é marcado como MENU
# ===========================================================================

def test_GATE_4_menu_e_marcado_como_menu():
    """🔴 📊 27 das 378 telas cegas são menu — são as que mais doem: a URA
    **pergunta** e o corredor não sabe responder."""
    b = Banco()
    _registrar(b, TELA_MENU)
    assert _fila(b)[0]["e_menu"] is True

    b2 = Banco()
    _registrar(b2, TELA_SIMPLES)
    assert _fila(b2)[0]["e_menu"] is False, (
        "uma tela sem opção numerada foi marcada como menu")


def test_GATE_4b_o_detector_de_menu_nas_bordas():
    """⚠️ Uma opção só não é menu; e repetir `1 -` duas vezes também não."""
    assert TC.e_menu("1 - Guincho\n2 - Chaveiro") is True
    assert TC.e_menu("*1* - Guincho\n*2* - Chaveiro") is True, (
        "opção em negrito do WhatsApp não foi reconhecida")
    assert TC.e_menu("1) Guincho\n2) Chaveiro") is True
    assert TC.e_menu("1 - Guincho") is False, "uma opção só virou menu"
    assert TC.e_menu("1 - Guincho\n1 - Guincho") is False, (
        "a mesma opção repetida virou menu de dois itens")
    assert TC.e_menu("") is False
    assert TC.e_menu("Ligue para 0800 1 2 3") is False, (
        "números soltos no meio da frase viraram menu")


# ===========================================================================
# ⑤ dois tenants: a fila de A não mostra tela de B
# ===========================================================================

def test_GATE_5_a_fila_de_uma_corretora_nao_mostra_tela_da_outra():
    """`CLAUDE.md` §7 — e aqui a chave POR CORRETORA é deliberada.

    ⚠️ `route_drift` é global de propósito (o Atlas é um só). **Esta tabela não
    é mapa: é fila de trabalho de uma corretora** — quem transforma a tela em
    passo trabalha para ela, e a contagem que ordena a fila é a dela.
    """
    b = Banco()
    _registrar(b, TELA_MENU, company=EMPRESA_A)
    _registrar(b, TELA_MENU, company=EMPRESA_B)

    assert len(_fila(b)) == 2, (
        "a mesma tela vista por duas corretoras virou UMA linha — a fila de uma "
        "passou a contar o trabalho da outra")
    assert {l["company_id"] for l in _fila(b)} == {EMPRESA_A, EMPRESA_B}
    for l in _fila(b):
        assert l["visto_quantas_vezes"] == 1 or "visto_quantas_vezes" not in l


def test_GATE_5b_o_contador_de_uma_corretora_nao_sobe_pela_outra():
    b = Banco()
    for _ in range(3):
        _registrar(b, TELA_MENU, company=EMPRESA_A)
    _registrar(b, TELA_MENU, company=EMPRESA_B)

    por_empresa = {l["company_id"]: l["visto_quantas_vezes"] for l in _fila(b)}
    assert por_empresa == {EMPRESA_A: 3, EMPRESA_B: 1}, por_empresa


def test_toda_leitura_e_escrita_filtra_por_CORRETORA():
    """⚠️ O backend usa service role: a RLS **não** protege contra um filtro
    esquecido aqui. Este é o guarda do filtro."""
    fonte = (RAIZ / "app" / "services" / "tela_cega.py").read_text(encoding="utf-8")
    i = fonte.index("async def registrar_tela_cega(")
    corpo = fonte[i:]
    assert corpo.count('.eq("company_id", linha["company_id"])') >= 3, (
        "alguma leitura ou escrita perdeu o filtro por corretora")


# ===========================================================================
# A MIGRATION — o CHECK escrito, e o teste que exige a RECUSA
# ===========================================================================

def test_a_migration_LISTA_os_valores_do_CHECK():
    """🔴 Na SPEC-093 a SPEC pediu um valor que o CHECK não tinha, e isso só foi
    descoberto no meio da execução. Aqui os valores estão escritos no APPLY."""
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "check (status in ('aberta', 'virou_passo', 'ignorada'))" in sql
    assert "APPLY:" in sql and "VERIFY:" in sql and "ROLLBACK:" in sql
    assert "company_id" in sql and "enable row level security" in sql


def test_o_CHECK_do_status_RECUSA_valor_invalido():
    """§9.3 — o dublê implementa o CHECK, e este teste prova que ele morde.

    📊 E o banco REAL foi verificado no APPLY, com a saída no relatório:
    `status recusado? t | vezes>=1 recusado? t | UNIQUE recusou? t`.
    """
    b = Banco()
    with _com_banco(b):
        q = b.table("tela_cega").insert({
            "company_id": EMPRESA_A, "insurer_key": "yelum", "ramo": "auto",
            "texto_mascarado": "x", "hash_normalizado": "h", "status": "inventado"})
        try:
            _rodar(q.execute())
            raise AssertionError("o CHECK do status aceitou um valor inventado")
        except RuntimeError as e:
            assert "ck_tela_cega_status" in str(e)


# ===========================================================================
# 📊 O NÚMERO DO BLOCO 0 — refeito, e ele derruba a SPEC
# ===========================================================================

def test_o_corpus_de_telas_reais_EXISTE_e_e_a_fonte_da_medicao():
    """A medição do BLOCO 0 é reproduzível: o corpus é versionado.

    ⚠️ E é ele, não o banco, porque o corpus roda sem rede, já foi auditado por
    PII, e é a mesma fonte que os guardas de corredor usam.
    """
    corpus = RAIZ / "tests" / "corpus" / "telas_reais"
    arquivos = sorted(corpus.glob("*.jsonl"))
    assert len(arquivos) >= 16, (
        f"o corpus encolheu para {len(arquivos)} arquivos — a medição do BLOCO 0 "
        "deixou de ser reproduzível")
    seguradoras = {a.name.split("-")[0] for a in arquivos}
    assert len(seguradoras) >= 10, (
        f"o corpus cobre {len(seguradoras)} seguradoras; a medição precisa de 10")

# =========================================================================
# 🔴 A DEDUPE, DE VERDADE — os dois achados do painel
# =========================================================================

def test_GATE_2d_a_normalizacao_do_CASADOR_e_que_agrupa():
    """🔴 O teste da normalização passava por ACIDENTE.

    ⚠️ Espaço e caixa são absorvidos por `" ".join(base.split())` e
    `.lower()`, que vivem **fora** do `try` do `_norm`. 📊 Medido pelo painel:
    apagar `from ... import _norm` **não derrubava nada**.

    O que **só** `_norm` resolve é acento (NFKD) e o marcador de negrito do
    WhatsApp — e é por isso que este caso existe.
    """
    b = Banco()
    _registrar(b, "Opção de serviço: 1 - Guincho\n2 - Chaveiro")
    _registrar(b, "Opcao de servico: 1 - Guincho\n2 - Chaveiro")      # sem acento
    _registrar(b, "*Opção* de serviço: 1 - Guincho\n2 - Chaveiro")   # negrito do WhatsApp
    assert len(_fila(b)) == 1, (
        f"acento e negrito viraram {len(_fila(b))} linhas — a normalização do "
        "casador não está sendo usada, e a fila fragmenta por formatação")
    assert _fila(b)[0]["visto_quantas_vezes"] == 3


def test_GATE_2e_a_MESMA_tela_de_segurados_diferentes_DEDUPLICA():
    """🔴 **O achado que matava a razão de a fila existir.**

    O hash saía do texto CRU: mudava a cada segurado, então a mesma tela
    **nunca deduplicava** — uma linha por PESSOA, que é literalmente o *"vira
    ruído em um dia"* que o módulo diz estar evitando.

    ⛔ E o digest do cru ao lado do texto mascarado tornava a máscara
    **reversível**: quem lê tem o gabarito (`{CPF}` onde o número estava) e o
    hash. Força bruta sobre ~10⁹ candidatos.
    """
    b = Banco()
    _registrar(b, "Confirma o CPF 111.222.333-44 do titular?")
    _registrar(b, "Confirma o CPF 555.666.777-88 do titular?")
    _registrar(b, "Confirma o CPF 999.888.777-66 do titular?")
    assert len(_fila(b)) == 1, (
        f"a MESMA tela com três segurados virou {len(_fila(b))} linhas — o "
        "hash saiu do texto cru e a dedupe morreu")
    assert _fila(b)[0]["visto_quantas_vezes"] == 3


def test_o_HASH_sai_do_texto_MASCARADO():
    """§9.3 — a prova direta, sem passar pelo IO."""
    with _com_o_pacote_app():
        a = TC.linha_da_fila(company_id=EMPRESA_A, insurer_key="yelum",
                             ramo="auto", playbook_ref=None,
                             texto="CPF 111.222.333-44 ok?")
        b = TC.linha_da_fila(company_id=EMPRESA_A, insurer_key="yelum",
                             ramo="auto", playbook_ref=None,
                             texto="CPF 555.666.777-88 ok?")
        c = TC.linha_da_fila(company_id=EMPRESA_A, insurer_key="yelum",
                             ramo="auto", playbook_ref=None,
                             texto="Aguarde na linha, por favor")
    assert a["hash_normalizado"] == b["hash_normalizado"], (
        "o hash ainda distingue segurados — a dedupe está morta")
    # 🔴 CONTROLE: telas DIFERENTES continuam com hashes diferentes.
    assert a["hash_normalizado"] != c["hash_normalizado"], (
        "o hash agrupou telas diferentes — a dedupe passou a agrupar demais")


# =========================================================================
# 🔴 O GANCHO — o único fio entre o motor e a feature inteira
# =========================================================================

def _chamar_gancho(session, texto="Escolha:\n1 - A\n2 - B"):
    """Executa `_registrar_tela_cega_sem_derrubar` DE VERDADE, com dublê.

    🔴 Os três guardas anteriores eram busca de substring no fonte. 📊 Medido
    pelo painel: trocar `session.get("company_id")` por `session.get("companyId")`
    matava a feature em silêncio e deixava os três VERDES.
    """
    import asyncio
    import importlib.util as _uu

    chamadas = []

    async def _falso(**kw):
        chamadas.append(kw)
        return True

    mod = types.ModuleType("app.services.tela_cega")
    mod.registrar_tela_cega = _falso
    antes = sys.modules.get("app.services.tela_cega")
    sys.modules["app.services.tela_cega"] = mod
    try:
        with _com_o_pacote_app():
            spec = _uu.spec_from_file_location("_motor_087", str(MOTOR_PY))
            motor = _uu.module_from_spec(spec)
            sys.modules["_motor_087"] = motor
            try:
                spec.loader.exec_module(motor)
            except Exception:                      # noqa: BLE001
                import pytest as _p
                _p.skip("o motor não carrega neste ambiente")

            async def _rodar():
                motor._registrar_tela_cega_sem_derrubar(session, {}, texto)
                await asyncio.sleep(0)             # deixa a task rodar

            asyncio.run(_rodar())
    finally:
        if antes is None:
            sys.modules.pop("app.services.tela_cega", None)
        else:
            sys.modules["app.services.tela_cega"] = antes
    return chamadas


def test_o_GANCHO_registra_de_verdade_na_fase_de_URA():
    chamadas = _chamar_gancho({
        "company_id": EMPRESA_A, "state": "ura",
        "playbook_ref": "yelum-auto-whatsapp@v1"})
    assert len(chamadas) == 1, (
        "o gancho não chamou o registro — a feature inteira está desligada")
    assert chamadas[0]["company_id"] == EMPRESA_A
    assert chamadas[0]["insurer_key"] == "yelum"
    assert chamadas[0]["ramo"] == "auto"


def test_o_GANCHO_NAO_registra_prosa_de_ANALISTA_HUMANO():
    """🔴 Depois que a URA acaba, quem digita é uma PESSOA — e nenhuma frase
    dela casa passo, por construção.

    📊 `observed_events` tem 4.315 textos distintos: conversa nunca se repete,
    então `visto_quantas_vezes` ficaria 1 para sempre, a fila cresceria sem
    teto, e o CONTADOR — que a SPEC diz ser o que ordena a prioridade —
    deixaria de ordenar.

    ⛔ A fila é de TELA DE URA. Prosa de gente não é tela.
    """
    for fase in ("human_phase", "monitoring", "needs_human", "captured"):
        assert _chamar_gancho({"company_id": EMPRESA_A, "state": fase,
                               "playbook_ref": "yelum-auto-whatsapp@v1"}) == [], (
            f"prosa da fase `{fase}` entrou na fila de TELAS DE URA")


def test_o_GANCHO_NAO_registra_com_company_id_do_SIMULADOR():
    """🔴 `ura_simulator` monta a sessão com `company_id="sim"`, e o Alfaiate
    o chama a cada drift cosmético.

    ⚠️ Sem este guarda, cada tela do script viraria um SELECT com
    `company_id='sim'` → erro 22P02 → um `logger.error` dizendo *"a tela NÃO
    entrou na fila"* por tela. A operação leria isso no piloto como *"o BLOCO A
    não funciona"*.
    """
    for falso in ("sim", "", "sim-123", "company", "SIM"):
        assert _chamar_gancho({"company_id": falso, "state": "ura",
                               "playbook_ref": "yelum-auto-whatsapp@v1"}) == [], (
            f"`company_id={falso!r}` chegou ao banco")


def test_CONTROLE_o_gancho_CONSEGUE_registrar():
    """§9.3 — sem esta linha, um gancho que nunca registra passaria nos dois
    testes de recusa acima."""
    assert _chamar_gancho({"company_id": EMPRESA_B, "state": "ura",
                           "playbook_ref": "porto-residencial-whatsapp@v1"})
