"""Reparear o WhatsApp NÃO baixa de novo o que já foi baixado. SPEC-063.

O pedido do Founder, literal
----------------------------
> "Eu quero primeiro conectar os WhatsApps da Regina e da Saionara. NÃO QUERO
>  QUE AS CONVERSAS QUE JÁ FORAM BAIXADAS SEJAM DUPLICADAS. Quero apenas
>  conversas novas sendo baixadas."

O que está em jogo
------------------
O `history_sync` do WhatsApp reentrega o histórico INTEIRO a cada pareamento.
📊 Medido em 04/08/2026 no projeto dcajcvlzcjbmyapmklil:

    attendance_transcripts   69.150 linhas   (Resulta 59.168 · AutoFleet 9.982)
    observed_events          17.651 linhas

Se a deduplicação falhar, esses 86.801 registros voltam em dobro.

Por que este teste tem um banco falso em vez de olhar o código
--------------------------------------------------------------
Deduplicação não é uma propriedade do texto do programa: é o resultado de um
acordo entre o `on_conflict` que o código pede e o índice único que o banco
tem. Um teste que só lê o fonte aprova as duas metades separadas e não percebe
quando elas param de se encaixar — que é exatamente o defeito possível aqui.

Então o banco falso abaixo honra a semântica real do Postgres:

    ON CONFLICT (a,b,c) DO NOTHING   com índice (a,b,c)  -> ignora a repetida
    ON CONFLICT (a,b,c) DO NOTHING   sem   índice (a,b,c)-> ERRO 42P10
    conflito em OUTRO índice único                       -> ERRO 23505
    coluna NULA na chave                                 -> nunca conflita

E as três configurações de índice são testadas, porque o produto passa pelas
três: a de hoje, a da migration, e a de depois da limpeza.

Os CONTROLES
------------
Um dedupe que rejeita tudo passaria em qualquer teste de "não duplicou". Por
isso toda afirmação aqui vem com o seu par:

    [2] mensagem GENUINAMENTE nova   -> tem de criar linha
    [3] mesma mensagem em DUAS corretoras -> tem de criar DUAS linhas
    [5] mensagem do histórico nunca vista ao vivo -> tem de criar linha

Sem eles, um `return` no lugar errado passaria por sucesso.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

EMPRESA_A = "04b5cdbc-0000-4000-8000-000000000001"   # 💭 papel de Resulta
EMPRESA_B = "6c9c55e2-0000-4000-8000-000000000002"   # 💭 papel de AutoFleet

CHAVE_LEGADA = ("observer_number", "message_id")
CHAVE_TENANT = ("company_id", "observer_number", "message_id")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# ------------------------------------------------------------------ #
# O banco falso — fiel ao que o Postgres faz, não ao que seria cômodo
# ------------------------------------------------------------------ #
class ErroPostgres(Exception):
    def __init__(self, codigo: str, msg: str = "") -> None:
        super().__init__(f"{codigo} {msg}")
        self.codigo = codigo


class Consulta:
    def __init__(self, banco: "BancoFalso", tabela: str) -> None:
        self.banco, self.tabela = banco, tabela
        self._filtros: list[tuple] = []
        self._acao = None
        self._carga = None
        self._ordem: list = []      # lista: o código encadeia .order() duas vezes
        self._faixa = None

    # --- escrita ---------------------------------------------------
    def upsert(self, record, on_conflict="", ignore_duplicates=False):
        self._acao, self._carga = "upsert", (record, on_conflict, ignore_duplicates)
        return self

    def insert(self, record):
        self._acao, self._carga = "insert", record
        return self

    def update(self, campos):
        self._acao, self._carga = "update", campos
        return self

    # --- leitura ---------------------------------------------------
    def select(self, *_cols):
        self._acao = self._acao or "select"
        return self

    def eq(self, coluna, valor):
        self._filtros.append((coluna, valor))
        return self

    def order(self, coluna, desc=False):
        self._ordem.append((coluna, desc))
        return self

    def limit(self, n):
        self._faixa = (0, n - 1)
        return self

    def range(self, inicio, fim):
        self._faixa = (inicio, fim)
        return self

    def _casa(self, linha) -> bool:
        return all(str(linha.get(c)) == str(v) for c, v in self._filtros)

    def execute(self):
        linhas = self.banco.dados.setdefault(self.tabela, [])
        if self._acao == "upsert":
            self.banco._upsert(self.tabela, *self._carga)
            return types.SimpleNamespace(data=[])
        if self._acao == "insert":
            return types.SimpleNamespace(data=[self.banco._insert(self.tabela, self._carga)])
        if self._acao == "update":
            atingidas = [l for l in linhas if self._casa(l)]
            for l in atingidas:
                l.update(self._carga)
            return types.SimpleNamespace(data=atingidas)
        achadas = [l for l in linhas if self._casa(l)]
        # Ordena da última chave para a primeira (sort estável = ordem composta),
        # que é o que o Postgres faz com `ORDER BY a, b`.
        for coluna, desc in reversed(self._ordem):
            achadas.sort(key=lambda l: str(l.get(coluna) or ""), reverse=desc)
        if self._faixa:
            ini, fim = self._faixa
            achadas = achadas[ini:fim + 1]
        return types.SimpleNamespace(data=achadas)


class BancoFalso:
    """Guarda linhas e faz valer os índices únicos que lhe forem declarados."""

    def __init__(self, indices: dict) -> None:
        self.indices = indices           # {tabela: {(colunas...), ...}}
        self.dados: dict = {}

    def table(self, nome):
        return Consulta(self, nome)

    def _viola(self, tabela, chave, record):
        """Existe linha com os mesmos valores nesta chave? NULO nunca conflita."""
        valores = [record.get(c) for c in chave]
        if any(v is None for v in valores):
            return False
        return any(
            all(str(l.get(c)) == str(record.get(c)) for c in chave)
            for l in self.dados.setdefault(tabela, [])
        )

    def _upsert(self, tabela, record, on_conflict, ignore_duplicates):
        arbitro = tuple(c.strip() for c in on_conflict.split(",") if c.strip())
        indices = self.indices.get(tabela, set())
        # O Postgres exige que a cláusula case com um índice único existente.
        if arbitro not in indices:
            raise ErroPostgres("42P10", "no unique or exclusion constraint "
                                        "matching the ON CONFLICT specification")
        if self._viola(tabela, arbitro, record):
            return                      # DO NOTHING
        # Conflito em OUTRO índice único NÃO é engolido pela cláusula.
        for outro in indices:
            if outro != arbitro and self._viola(tabela, outro, record):
                raise ErroPostgres("23505", f"duplicate key violates {outro}")
        self.dados.setdefault(tabela, []).append(dict(record))

    def _insert(self, tabela, record):
        for chave in self.indices.get(tabela, set()):
            if self._viola(tabela, chave, record):
                raise ErroPostgres("23505", f"duplicate key violates {chave}")
        linha = dict(record)
        linha.setdefault("id", f"id-{len(self.dados.setdefault(tabela, []))}")
        self.dados.setdefault(tabela, []).append(linha)
        return linha


def _banco_com(*chaves) -> BancoFalso:
    """Um banco cujas tabelas têm exatamente as chaves únicas informadas."""
    return BancoFalso({t: set(chaves) for t in
                       ("observed_events", "attendance_transcripts")})


# ------------------------------------------------------------------ #
# Carga isolada — sem levantar o app inteiro
# ------------------------------------------------------------------ #
_BANCO_ATUAL: list = [None]


def _preparar_modulos():
    for nome in ("app", "app.services", "app.services.atlas",
                 "app.services.whatsapp", "app.core"):
        if nome not in sys.modules:
            mod = types.ModuleType(nome)
            mod.__path__ = []            # marca como pacote
            sys.modules[nome] = mod

    db = types.ModuleType("app.core.database")
    db.get_supabase_client = lambda: types.SimpleNamespace(client=_BANCO_ATUAL[0])
    sys.modules["app.core.database"] = db

    reg = types.ModuleType("app.services.insurer_registry")
    reg.INSURER_REGISTRY = {}            # nenhuma seguradora: tudo vai ao Espelho
    sys.modules["app.services.insurer_registry"] = reg

    def _carregar(dotted, *partes):
        caminho = os.path.join(RAIZ, *partes)
        spec = importlib.util.spec_from_file_location(dotted, caminho)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[dotted] = mod
        spec.loader.exec_module(mod)
        return mod

    _carregar("app.services.whatsapp.evolution_inbound",
              "app", "services", "whatsapp", "evolution_inbound.py")
    _carregar("app.services.atlas.attendance_capture",
              "app", "services", "atlas", "attendance_capture.py")
    oi = _carregar("app.services.atlas.observer_intake",
                   "app", "services", "atlas", "observer_intake.py")
    hi = _carregar("app.services.atlas.history_ingest",
                   "app", "services", "atlas", "history_ingest.py")
    return oi, hi


OI, HI = _preparar_modulos()


def _iso_de(epoch: int) -> str:
    """O mesmo instante que o histórico vai calcular, vindo da mesma fonte."""
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _msg(texto: str, ts: int, from_me: bool = False) -> dict:
    """Um item de histórico no shape que o evolution-go entrega."""
    return {"Message": {"key": {"fromMe": from_me, "id": f"wa-{ts}"},
                        "message": {"conversation": texto},
                        "messageTimestamp": ts}}


def _ingerir(banco, empresa, msgs, observador="045041", counterparty="5547999990001",
             ja_ao_vivo=None) -> int:
    _BANCO_ATUAL[0] = banco
    return asyncio.run(HI._ingest_conversation(
        empresa, observador, counterparty, None, msgs,
        events_table="attendance_transcripts", sessions_table="attendance_sessions",
        ja_ao_vivo=ja_ao_vivo))


def _linhas(banco) -> list:
    return banco.dados.get("attendance_transcripts", [])


# ================================================================== #
# [1] A MESMA MENSAGEM, REENTREGUE, NÃO CRIA SEGUNDA LINHA
# ================================================================== #
def teste_reentrega_nao_duplica():
    print("\n[1] O history_sync reentrega tudo — e nada é gravado duas vezes")
    conversa = [_msg("Bom dia, preciso do meu boleto", 1767117860),
                _msg("Claro! Já envio", 1767117870, from_me=True),
                _msg("Obrigada", 1767117880)]

    for rotulo, banco in (("índice de hoje (sem corretora)", _banco_com(CHAVE_LEGADA)),
                          ("depois da migration (os dois)", _banco_com(CHAVE_LEGADA, CHAVE_TENANT)),
                          ("depois da limpeza (só o novo)", _banco_com(CHAVE_TENANT))):
        _ingerir(banco, EMPRESA_A, conversa)          # 1º pareamento
        depois_do_primeiro = len(_linhas(banco))
        _ingerir(banco, EMPRESA_A, conversa)          # repareamento
        _ingerir(banco, EMPRESA_A, conversa)          # e mais um, por garantia
        checar(depois_do_primeiro == 3,
               f"{rotulo}: o primeiro pareamento grava as 3 mensagens",
               f"gravou {depois_do_primeiro}")
        checar(len(_linhas(banco)) == 3,
               f"{rotulo}: reparear duas vezes NÃO cria cópia",
               f"ficou com {len(_linhas(banco))} linhas")

    # A tolerância que faz a ordem do deploy não importar: com o índice antigo
    # sozinho, o código pede a chave nova, leva 42P10 e ainda assim grava.
    banco = _banco_com(CHAVE_LEGADA)
    _ingerir(banco, EMPRESA_A, conversa)
    checar(len(_linhas(banco)) == 3,
           "com o índice novo AINDA não aplicado, a ingestão grava mesmo assim",
           "sem a reserva, o histórico gravaria ZERO linha em silêncio")


# ================================================================== #
# [2] CONTROLE — mensagem genuinamente nova PRECISA entrar
# ================================================================== #
def teste_controle_mensagem_nova_entra():
    print("\n[2] CONTROLE: conversa NOVA continua sendo baixada")
    # Sem este caso, um dedupe que recusasse tudo passaria no teste [1].
    banco = _banco_com(CHAVE_TENANT)
    conversa = [_msg("Bom dia", 1767117860)]
    _ingerir(banco, EMPRESA_A, conversa)
    antes = len(_linhas(banco))

    nova = conversa + [_msg("Chegou meu boleto?", 1767204260)]
    _ingerir(banco, EMPRESA_A, nova)
    checar(len(_linhas(banco)) == antes + 1,
           "a mensagem que ainda não existia foi gravada",
           f"antes {antes}, depois {len(_linhas(banco))}")

    # E o mesmo texto em OUTRO instante é outra mensagem — não é cópia.
    _ingerir(banco, EMPRESA_A, nova + [_msg("Bom dia", 1767290660)])
    checar(len(_linhas(banco)) == antes + 2,
           "o mesmo texto num outro dia é outra mensagem",
           "confundir os dois apagaria conversa real")


# ================================================================== #
# [3] CONTROLE DE TENANT — duas corretoras, duas linhas
# ================================================================== #
def teste_controle_duas_corretoras():
    print("\n[3] CONTROLE: a mesma mensagem em DUAS corretoras são DUAS conversas")
    # 📊 Hoje o índice é (observer_number, message_id), sem company_id, e
    # `observer_number` tem fallbacks literais ('unknown' em 167 eventos,
    # 'attendance-channel' em 1 transcrição). Duas corretoras caindo no mesmo
    # literal colapsariam numa linha só — e a linha perdida não aparece em log.
    conversa = [_msg("Bom dia", 1767117860)]
    resultados = {}
    for rotulo, banco in (("hoje", _banco_com(CHAVE_LEGADA)),
                          ("transição", _banco_com(CHAVE_LEGADA, CHAVE_TENANT)),
                          ("alvo", _banco_com(CHAVE_TENANT))):
        # MESMO observer_number nas duas — é o caso do literal compartilhado.
        _ingerir(banco, EMPRESA_A, conversa, observador="unknown")
        _ingerir(banco, EMPRESA_B, conversa, observador="unknown")
        resultados[rotulo] = len(_linhas(banco))

    checar(resultados["alvo"] == 2,
           "com a corretora na chave, as duas conversas existem",
           f"ficou com {resultados['alvo']} linha(s) — colapsar é perda silenciosa")

    # E A PROVA DE QUE O GUARDA CONSEGUE FALHAR (CLAUDE.md §9.3).
    # Se as três configurações dessem o mesmo número, este teste não estaria
    # medindo o índice — estaria medindo outra coisa qualquer.
    checar(resultados["hoje"] == 1,
           "e o índice de HOJE realmente colapsa as duas",
           f"esperado 1, veio {resultados['hoje']} — se não colapsa, "
           f"este teste não prova nada sobre o índice")
    checar(resultados["transição"] == 1,
           "na transição ainda colapsa — o índice antigo é o mais estrito",
           "é o preço aceito por não quebrar o deploy; o DROP vem depois")


# ================================================================== #
# [4] O CRUZAMENTO live × history_sync
# ================================================================== #
def teste_o_que_ja_chegou_ao_vivo_nao_volta():
    print("\n[4] O que o Observador já viu ao vivo não é baixado de novo")
    # 📊 04/08/2026: as duas fontes usam famílias de id INCOMPATÍVEIS —
    # history_sync grava `hist-…` (100% das 85.766 linhas) e o caminho ao vivo
    # grava o id do WhatsApp (100% das 1.035). O índice único não tem como
    # perceber que são a mesma mensagem: a chave nunca colide.
    banco = _banco_com(CHAVE_TENANT)
    _BANCO_ATUAL[0] = banco

    # A corretora já capturou isto ao vivo, hoje de manhã.
    banco.dados["attendance_transcripts"] = [{
        "company_id": EMPRESA_A, "observer_number": "045041",
        "counterparty": "5547999990001", "direction": "in", "msg_type": "text",
        "text": "Bom dia, preciso do meu boleto",
        # Derivado do epoch, NUNCA escrito à mão: a primeira versão deste teste
        # trazia um ISO de um mês diferente e o caso falhou — o guarda estava
        # certo, o fixture é que mentia. Data escrita à mão é fonte de falso
        # vermelho, e falso vermelho ensina a desconfiar do teste.
        "wa_timestamp": _iso_de(1767117860),
        "message_id": "3EB0C767D1", "source": "live",
    }]
    vivos = asyncio.run(HI._impressoes_ao_vivo(EMPRESA_A, "attendance_transcripts"))
    checar(len(vivos) == 1, "a impressão do que já chegou ao vivo é lida",
           f"leu {len(vivos)}")

    _ingerir(banco, EMPRESA_A, [_msg("Bom dia, preciso do meu boleto", 1767117860)],
             ja_ao_vivo=vivos)
    checar(len(_linhas(banco)) == 1,
           "o histórico NÃO regrava a mensagem que já veio ao vivo",
           f"ficou com {len(_linhas(banco))} linhas — a segunda é a duplicata")

    # E sem o cruzamento a duplicata aparece: prova de que o guarda é o que
    # está segurando, e não uma coincidência do id.
    banco2 = _banco_com(CHAVE_TENANT)
    banco2.dados["attendance_transcripts"] = list(banco.dados["attendance_transcripts"][:1])
    _ingerir(banco2, EMPRESA_A, [_msg("Bom dia, preciso do meu boleto", 1767117860)],
             ja_ao_vivo=None)
    checar(len(_linhas(banco2)) == 2,
           "e sem o cruzamento ela realmente duplicaria",
           "se não duplicasse, o guarda do caso acima não seria o responsável")


# ================================================================== #
# [5] CONTROLE — o histórico que nunca foi visto ao vivo TEM de entrar
# ================================================================== #
def teste_controle_historico_novo_entra():
    print("\n[5] CONTROLE: histórico nunca visto ao vivo continua entrando")
    banco = _banco_com(CHAVE_TENANT)
    _BANCO_ATUAL[0] = banco
    banco.dados["attendance_transcripts"] = [{
        "company_id": EMPRESA_A, "observer_number": "045041",
        "counterparty": "5547999990001", "direction": "in", "msg_type": "text",
        "text": "Bom dia, preciso do meu boleto",
        "wa_timestamp": "2026-01-30T18:04:20+00:00",
        "message_id": "3EB0C767D1", "source": "live",
    }]
    vivos = asyncio.run(HI._impressoes_ao_vivo(EMPRESA_A, "attendance_transcripts"))

    # Conversa de 2024 que só existe no histórico — é o material que o
    # pareamento vem buscar, e ele não pode ser confundido com cópia.
    _ingerir(banco, EMPRESA_A,
             [_msg("Preciso renovar o seguro do Gol", 1726600000),
              _msg("A apólice vence dia 20", 1726600060)],
             ja_ao_vivo=vivos)
    checar(len(_linhas(banco)) == 3,
           "as duas mensagens antigas foram baixadas",
           f"ficou com {len(_linhas(banco))} — o guarda não pode recusar tudo")

    # Mídia não tem identidade por conteúdo: na dúvida a mensagem FICA.
    marca = HI._impressao("5547999990001", 1767117860, "in", "audio", None)
    checar(marca is None,
           "áudio/foto não entram no cruzamento",
           "sem texto não há identidade segura — perder áudio é irreversível")


# ================================================================== #
# [6] A MIGRATION — o que ela promete e o que ela NÃO faz
# ================================================================== #
def teste_a_migration_e_expand_first():
    print("\n[6] A migration adiciona, e não tira nada de baixo do código vivo")
    caminho = os.path.join(RAIZ, "supabase", "migrations",
                           "20260804_03_o_repareamento_nao_duplica.sql")
    checar(os.path.exists(caminho), "a migration existe")
    sql = open(caminho, encoding="utf-8").read()

    for marca in ("APPLY:", "VERIFY:", "ROLLBACK:"):
        checar(marca in sql, f"o cabeçalho tem {marca}")
    checar("EXPAND-FIRST: sim" in sql, "declara expand-first")
    checar("DESTRUTIVA:   nao" in sql, "declara não destrutiva")

    corpo = "\n".join(l for l in sql.split("\n") if not l.strip().startswith("--"))
    checar("DROP INDEX" not in corpo.upper(),
           "nenhum DROP no corpo executável",
           "dropar o índice antigo aqui faria a ingestão do histórico gravar "
           "ZERO linha até o deploy chegar")

    # COMANDOS, não palavras. A primeira versão desta checagem procurava a
    # string "UPDATE " em qualquer lugar e acusou o texto
    # `'... do connection.update '` dentro de um COMMENT — um falso vermelho
    # que, repetido, ensina a ignorar o teste.
    import re as _re
    # Os literais saem ANTES de separar por `;`, porque há ponto-e-vírgula
    # DENTRO de texto de COMMENT ("NULL = o provedor nao informou; nunca
    # deduzir..."). Separar sem isso parte uma frase no meio e o pedaço vira um
    # "comando desconhecido" — segundo falso vermelho deste mesmo teste.
    sem_literais = _re.sub(r"'(?:[^']|'')*'", "''", corpo)
    comandos = [c.strip().upper() for c in sem_literais.split(";") if c.strip()]
    for proibido in ("DROP TABLE", "DROP COLUMN", "TRUNCATE", "DELETE FROM", "UPDATE"):
        achados = [c[:60] for c in comandos
                   if _re.match(rf"^{proibido}\b", c) or _re.search(rf";\s*{proibido}\b", c)]
        checar(not achados, f"nenhum comando {proibido} no corpo executável",
               str(achados[:1]))
    checar(all(_re.match(r"^(ALTER TABLE|CREATE (UNIQUE )?INDEX|COMMENT ON)\b", c)
               for c in comandos),
           "só existem ALTER TABLE, CREATE INDEX e COMMENT",
           str([c[:40] for c in comandos
                if not _re.match(r"^(ALTER TABLE|CREATE (UNIQUE )?INDEX|COMMENT ON)\b", c)]))

    for indice in ("ux_attendance_transcripts_dedupe_tenant",
                   "uq_observed_events_msg_tenant",
                   "idx_observed_sessions_lookup_tenant"):
        checar(indice in corpo, f"cria {indice}")
    checar(corpo.count("company_id, observer_number, message_id") >= 2,
           "as duas chaves de dedupe passam a ter a corretora")
    for coluna in ("paired_jid", "paired_phone_e164", "paired_at"):
        checar(f"ADD COLUMN IF NOT EXISTS {coluna}" in corpo,
               f"integrations ganha {coluna}, de forma idempotente")


# ================================================================== #
# [7] O `observer_number` NÃO virou telefone — e o telefone tem casa
# ================================================================== #
def teste_o_observer_number_continua_estavel():
    print("\n[7] A chave de dedupe não mudou de significado")
    # Trocar o valor de `observer_number` faria as linhas novas nascerem com
    # `5547…` e as 86.801 antigas seguirem com `045041`/`6955221`. A chave
    # deixaria de casar e o repareamento regravaria o acervo INTEIRO.
    checar(OI._observer_number_of({"identifier": "ab-obs-6c9c55e22f-1"}) == "6955221",
           "AutoFleet continua sendo 6955221",
           "📊 são as 9.982 transcrições dela que dependem disso")
    checar(OI._observer_number_of({"identifier": "ab-obs-04b5cdbc04-1"}) == "045041",
           "Resulta continua sendo 045041",
           "📊 são as 59.168 transcrições dela")

    # O fallback literal, esse sim, tinha de morrer: era compartilhado por
    # todas as corretoras sem dígito no identifier.
    a = OI._observer_number_of({"identifier": "autobrokers-go", "company_id": EMPRESA_A})
    b = OI._observer_number_of({"identifier": "autobrokers-go", "company_id": EMPRESA_B})
    checar(a != b, "duas corretoras sem dígito no identifier não colidem mais",
           f"ambas deram {a}")
    checar("unknown" not in (a, b), "o literal 'unknown' não é mais gerado")

    # E o telefone de verdade tem onde morar, sem inventar quando não sabe.
    fonte = open(os.path.join(RAIZ, "app", "services", "whatsapp",
                              "numero_pareado.py"), encoding="utf-8").read()
    checar("def dados_de_pareamento" in fonte, "existe um lugar só que lê o JID pareado")
    sys.path.insert(0, RAIZ)
    spec = importlib.util.spec_from_file_location(
        "_np", os.path.join(RAIZ, "app", "services", "whatsapp", "numero_pareado.py"))
    np = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(np)

    checar(np.identidade_pareada({"data": {"jid": "554796274743:12@s.whatsapp.net"}})
           == ("554796274743:12@s.whatsapp.net", "+554796274743"),
           "o sufixo de dispositivo sai do telefone",
           "sem isso, trocar de aparelho viraria uma linha nova")
    checar(np.identidade_pareada({"data": {"LoggedIn": True}}) == (None, None),
           "sem JID a resposta é None — não um palpite",
           "número errado gravado como 'o WhatsApp da Regina' é pior que vazio")
    checar(np.telefone_e164("ab-obs-6c9c55e22f-1@s.whatsapp.net") is None,
           "o nome da instância nunca vira telefone",
           "foi exatamente esse engano que criou o `6955221`")
    checar(np.dados_de_pareamento({"data": {}}, "agora") == {},
           "silêncio do provedor não apaga o telefone já gravado")
    checar(np.mascarar("+5547988087463") == "5547*****463",
           "o telefone aparece mascarado", np.mascarar("+5547988087463"))


def teste_o_nome_da_instancia_nao_vem_do_pedido():
    """A porta que faria o acervo inteiro regravar, aberta por um campo do corpo.

    📊 `admin_atlas.py` montava o nome da instância com
    `_obs_instance_name(company_id, int(body.get("seq") or 1))` — e `seq` vem do
    CORPO DA REQUISIÇÃO.

    `seq: 2` gera `ab-obs-<10>-2`, cujos dígitos são outros. E `observer_number`
    — metade da chave de deduplicação — é derivado justamente do nome da
    instância. 📊 69.150 transcrições e 17.651 eventos deixariam de casar, e o
    pareamento seguinte regravaria tudo.

    O caminho normal cravava `-1`, então o defeito nunca apareceu. Mas **um
    defeito que só não acontece porque ninguém tentou continua sendo um
    defeito** — e este teste existe para que tentar não funcione.

    Nome de instância é IDENTIDADE DE ACERVO: quem já tem, mantém.
    """
    import ast

    print("\n[8] O nome da instância REUSA o que a corretora já tem")
    caminho = os.path.join(RAIZ, "app", "api", "admin_atlas.py")
    fonte = open(caminho, encoding="utf-8").read()
    comandos = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("_instancia_de_observador_ja_existente" in comandos,
           "existe uma busca pela instância já usada")
    # E ela vem ANTES do nome calculado — senão o `or` a ignora.
    i_reuso = comandos.find("_instancia_de_observador_ja_existente(")
    i_novo = comandos.find("_obs_instance_name(company_id, int(body.get")
    checar(0 < i_reuso < i_novo,
           "o reuso vem ANTES do nome novo",
           f"reuso={i_reuso} novo={i_novo} — depois, o `seq` do corpo voltaria a mandar")

    arvore = ast.parse(fonte)
    busca = next((n for n in ast.walk(arvore)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and n.name == "_instancia_de_observador_ja_existente"), None)
    checar(busca is not None, "a busca existe como função")
    if busca is None:
        return

    trecho = ast.get_source_segment(fonte, busca) or ""
    # 🔴 Ela NÃO pode filtrar `is_active`: desconectar é pausa, não recomeço —
    # e é justamente a corretora desconectada que vai reparear.
    filtros = [a.args[0].value for a in ast.walk(busca)
               if isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute)
               and a.func.attr == "eq" and a.args and isinstance(a.args[0], ast.Constant)]
    checar("is_active" not in filtros,
           "e ela NÃO filtra por linha ligada",
           f"filtra por {filtros} — a corretora que vai reparear está DESLIGADA")
    checar("company_id" in filtros and "purpose" in filtros,
           "CONTROLE — mas continua filtrando corretora e propósito",
           f"filtra por {filtros} — sem isso, uma corretora herdaria o acervo de outra")

    # CONTRAPROVA — o `seq` do corpo, sozinho, produz nome DIFERENTE. É o que
    # torna este guarda necessário; se produzisse o mesmo, não haveria risco.
    sys.path.insert(0, os.path.join(RAIZ))
    nome1 = f"ab-obs-{'6c9c55e22f'}-1"
    nome2 = f"ab-obs-{'6c9c55e22f'}-2"
    checar(nome1 != nome2 and _digitos_de(nome1) != _digitos_de(nome2),
           "CONTRAPROVA — `seq` diferente muda os dígitos, e a chave com eles",
           f"{_digitos_de(nome1)} × {_digitos_de(nome2)}")


def _digitos_de(nome: str) -> str:
    return "".join(c for c in nome if c.isdigit())


def main() -> int:
    print("=" * 70)
    print("REPAREAR NÃO BAIXA DE NOVO O QUE JÁ FOI BAIXADO")
    print("=" * 70)
    for teste in (teste_reentrega_nao_duplica,
                  teste_controle_mensagem_nova_entra,
                  teste_controle_duas_corretoras,
                  teste_o_que_ja_chegou_ao_vivo_nao_volta,
                  teste_controle_historico_novo_entra,
                  teste_a_migration_e_expand_first,
                  teste_o_observer_number_continua_estavel,
                  teste_o_nome_da_instancia_nao_vem_do_pedido):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O REPAREAMENTO TRAZ CONVERSA NOVA — E SÓ CONVERSA NOVA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
