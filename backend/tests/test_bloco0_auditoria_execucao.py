"""Bloco 0 da SPEC-061 — a execução deixa rastro auditável.

Por que este arquivo existe
---------------------------
O Bloco 0 abriu o banco de produção e encontrou, com 43 Work Runs concluídos e
o produto em uso:

    work_attempts    = 0
    tool_invocations = 0

Duas causas diferentes, as duas reais:

* **`work_attempts`** não tinha writer nenhum. A docstring de `executar_passo`
  dizia "registrando início, fim, **tentativa** e progresso" e a tentativa
  nunca era gravada.
* **`tool_invocations`** tinha writer — `ToolGateway.registrar_invocacao` — e
  **ninguém o chamava**. O Gateway decidia quais ferramentas o agente recebia e
  depois perdia a chamada de vista.

O custo é o mesmo nos dois casos: um trabalho que só passou na quarta tentativa
é indistinguível de um que passou de primeira, e uma ferramenta que falhou é
indistinguível de uma que o modelo nunca chamou. Quem paga esse custo é quem
precisa diagnosticar — o Founder olhando um trabalho lento, e o Admin da
SPEC-061, que governa exatamente estes objetos.

Estes testes falham se os writers sumirem de novo.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
FALHAS: list[str] = []


def _pacote(nome: str, *partes: str) -> None:
    if nome in sys.modules:
        return
    m = types.ModuleType(nome)
    m.__path__ = [os.path.join(RAIZ, *partes)]
    m.__package__ = nome
    sys.modules[nome] = m


for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.work", ("app", "services", "work")),
               ("app.services.skills", ("app", "services", "skills")),
               ("app.agents", ("app", "agents"))):
    _pacote(_n, *_p)


def carregar(nome: str):
    if nome in sys.modules and hasattr(sys.modules[nome], "__file__"):
        return sys.modules[nome]
    caminho = os.path.join(RAIZ, *nome.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# ==========================================================================
# Banco de mentira: guarda o que foi escrito, para o teste inspecionar.
# ==========================================================================


# Copiadas do banco de produção (consultadas em 27/07/2026). Se uma delas cair
# no schema, este teste continua verde e mente — por isso ficam nomeadas aqui,
# e não implícitas.
UNICAS: dict[str, tuple[tuple[str, ...], ...]] = {
    "work_steps": (("work_run_id", "step_key"),
                   ("company_id", "idempotency_key")),
    "work_attempts": (("work_step_id", "attempt_number"),),
    "tool_invocations": (("company_id", "invocation_key"),),
}


class FakeQuery:
    def __init__(self, banco: "FakeDB", tabela: str):
        self.banco, self.tabela = banco, tabela
        self._linhas = list(banco.dados.get(tabela, []))
        self._op = None
        self._payload = None
        self._filtros: list[tuple] = []

    def insert(self, linha):
        self._op, self._payload = "insert", linha
        return self

    def update(self, campos):
        self._op, self._payload = "update", campos
        return self

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def eq(self, campo, valor):
        self._filtros.append((campo, valor))
        self._linhas = [l for l in self._linhas if str(l.get(campo)) == str(valor)]
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        if self._op == "insert":
            linha = dict(self._payload)
            if self.banco.falhar_em == self.tabela:
                raise RuntimeError("insert recusado (simulado)")
            # As UNIQUEs que existem de verdade no banco. Sem elas aqui, o
            # teste seria mais frouxo que o schema — e passaria em cima de um
            # comportamento que a produção recusa. Um duplo insert de etapa é
            # exatamente o caso de retomada, e é onde a tentativa importa.
            for campos in UNICAS.get(self.tabela, ()):
                if any(linha.get(c) is None for c in campos):
                    continue
                for existente in self.banco.dados.get(self.tabela, []):
                    if all(str(existente.get(c)) == str(linha.get(c)) for c in campos):
                        raise RuntimeError(
                            f"duplicate key value violates unique constraint "
                            f"({', '.join(campos)})")
            linha.setdefault("id", f"{self.tabela}-{len(self.banco.dados.get(self.tabela, []))+1}")
            self.banco.dados.setdefault(self.tabela, []).append(linha)
            return types.SimpleNamespace(data=[linha])
        if self._op == "update":
            alvo = self.banco.dados.get(self.tabela, [])
            for linha in alvo:
                if all(str(linha.get(c)) == str(v) for c, v in self._filtros):
                    linha.update(self._payload)
            return types.SimpleNamespace(data=alvo)
        return types.SimpleNamespace(data=self._linhas)


class FakeDB:
    def __init__(self, falhar_em: str | None = None):
        self.dados: dict[str, list[dict]] = {}
        self.falhar_em = falhar_em
        self.client = self

    def table(self, nome: str) -> FakeQuery:
        return FakeQuery(self, nome)


class FakeRuns:
    def __init__(self):
        self.eventos: list[tuple] = []

    def evento(self, company_id, run_id, tipo, mensagem, **_k):
        self.eventos.append((tipo, mensagem))

    def marcar_progresso(self, *_a, **_k):
        return None


def contexto(db, runs):
    return {"db": db, "runs": runs, "company_id": "empresa-1",
            "run_id": "run-1", "payload": {}, "cancelado": lambda: False}


# ==========================================================================


def teste_tentativa_e_gravada():
    print("\n[1] Toda etapa grava a tentativa")
    wf = carregar("app.services.work.workflows")
    db, runs = FakeDB(), FakeRuns()

    async def trabalho():
        return "pronto"

    r = asyncio.run(wf.executar_passo(
        contexto(db, runs), step_key="passo", ordinal=1, nome="Fazer algo",
        step_type="analysis", fn=trabalho))

    checar(r == "pronto", "o resultado da etapa continua chegando a quem chamou")

    tentativas = db.dados.get("work_attempts", [])
    checar(len(tentativas) == 1, "a tentativa foi gravada", f"{len(tentativas)} linha(s)")
    if not tentativas:
        return
    t = tentativas[0]
    checar(t.get("attempt_number") == 1, "numerada a partir de 1", str(t.get("attempt_number")))
    checar(t.get("status") == "succeeded", "fechada como sucesso", str(t.get("status")))
    checar(bool(t.get("work_step_id")), "amarrada à etapa — não solta no run")
    checar(bool(t.get("work_run_id")), "e ao trabalho")
    checar(str(t.get("company_id")) == "empresa-1", "com a corretora dona")
    checar(bool(t.get("worker_id")), "e com o processador que executou")
    checar(isinstance(t.get("metrics"), dict) and "duracao_ms" in (t.get("metrics") or {}),
           "carrega a duração — é o que revela etapa lenta",
           str(t.get("metrics")))
    checar(t.get("finished_at") is not None, "e o instante em que terminou")


def teste_falha_fecha_a_tentativa():
    print("\n[2] Etapa que falha não deixa tentativa aberta para sempre")
    wf = carregar("app.services.work.workflows")
    db, runs = FakeDB(), FakeRuns()

    async def quebra():
        raise ConnectionError("provider fora do ar em https://x.com?api_key=abc123")

    try:
        asyncio.run(wf.executar_passo(
            contexto(db, runs), step_key="passo", ordinal=1, nome="Tentar",
            step_type="analysis", fn=quebra))
        checar(False, "a exceção continua subindo para quem chamou")
    except ConnectionError:
        checar(True, "a exceção continua subindo para quem chamou")

    t = (db.dados.get("work_attempts") or [{}])[0]
    checar(t.get("status") == "failed", "a tentativa fecha como falha", str(t.get("status")))
    checar(t.get("error_class") == "ConnectionError", "com a classe do erro",
           str(t.get("error_class")))
    checar(t.get("retryable") is True, "erro de rede é retentável")

    msg = str(t.get("error_message_redacted") or "")
    checar("abc123" not in msg,
           "e a chave que veio dentro da mensagem do erro NÃO chega ao banco", msg)
    checar("[redigido]" in msg, "o trecho é substituído, não apagado em silêncio", msg)


def teste_erro_de_programacao_nao_e_retentavel():
    print("\n[3] Repetir um TypeError produz o mesmo TypeError")
    wf = carregar("app.services.work.workflows")
    db, runs = FakeDB(), FakeRuns()

    async def bug():
        raise TypeError("faltou argumento")

    try:
        asyncio.run(wf.executar_passo(
            contexto(db, runs), step_key="p", ordinal=1, nome="x",
            step_type="analysis", fn=bug))
    except TypeError:
        pass

    t = (db.dados.get("work_attempts") or [{}])[0]
    checar(t.get("retryable") is False,
           "erro de programação é marcado como NÃO retentável — senão queima a fila",
           str(t.get("retryable")))


def teste_retomada_numera_a_segunda_tentativa():
    print("\n[4] Na retomada, a segunda tentativa é a de número 2")
    wf = carregar("app.services.work.workflows")
    db, runs = FakeDB(), FakeRuns()

    async def trabalho():
        return "ok"

    ctx = contexto(db, runs)
    asyncio.run(wf.executar_passo(ctx, step_key="passo", ordinal=1, nome="Fazer",
                                  step_type="analysis", fn=trabalho))
    # Segunda passagem no mesmo step_key: é o que acontece quando o worker
    # morre e outro assume o run.
    asyncio.run(wf.executar_passo(ctx, step_key="passo", ordinal=1, nome="Fazer",
                                  step_type="analysis", fn=trabalho))

    tentativas = db.dados.get("work_attempts", [])
    numeros = sorted(int(t.get("attempt_number") or 0) for t in tentativas)
    checar(numeros == [1, 2],
           "duas tentativas, numeradas 1 e 2 — a UNIQUE do banco depende disso",
           str(numeros))
    passos = db.dados.get("work_steps", [])
    checar(len(passos) == 1,
           "e a etapa continua sendo UMA — retomada não duplica etapa",
           f"{len(passos)} etapa(s)")


def teste_falha_de_auditoria_nao_derruba_o_trabalho():
    print("\n[5] Contabilidade quebrada não pode custar o trabalho do corretor")
    wf = carregar("app.services.work.workflows")
    db, runs = FakeDB(falhar_em="work_attempts"), FakeRuns()

    async def trabalho():
        return "entregue"

    try:
        r = asyncio.run(wf.executar_passo(
            contexto(db, runs), step_key="p", ordinal=1, nome="x",
            step_type="analysis", fn=trabalho))
        checar(r == "entregue",
               "com o registro de tentativa falhando, a etapa ainda entrega")
    except Exception as exc:  # noqa: BLE001
        checar(False, "com o registro de tentativa falhando, a etapa ainda entrega",
               f"{type(exc).__name__}: {exc}")


def teste_invocacao_de_ferramenta_e_registrada():
    print("\n[6] Toda chamada de ferramenta vira uma invocação")
    rec = carregar("app.services.skills.invocation_recorder")

    db = FakeDB()
    db.dados["tool_definitions"] = [
        {"id": "def-1", "tool_key": "knowledge.search",
         "capability_key": "knowledge.tenant.search", "is_active": True}]
    db.dados["tool_releases"] = [
        {"id": "rel-1", "tool_id": "def-1", "status": "published", "is_default": True}]
    rec._CATALOGO.clear()

    with rec.RegistroDeInvocacao(db, company_id="empresa-1",
                                 nome_da_tool="knowledge_base_search",
                                 argumentos={"query": "cobertura de vidros"}) as r:
        r.ok("achei 3 documentos")

    inv = db.dados.get("tool_invocations", [])
    checar(len(inv) == 1, "a invocação foi gravada", f"{len(inv)} linha(s)")
    if not inv:
        return
    i = inv[0]
    checar(i.get("capability_key") == "knowledge.tenant.search",
           "com a capability que a autorizou", str(i.get("capability_key")))
    checar(i.get("tool_release_id") == "rel-1",
           "e a release exata que rodou", str(i.get("tool_release_id")))
    checar(i.get("status") == "succeeded", "fechada como sucesso", str(i.get("status")))
    checar(bool(i.get("input_fingerprint")), "com a identidade da entrada")
    checar(isinstance(i.get("latency_ms"), int), "e a latência")


def teste_invocacao_nao_guarda_dado_do_segurado():
    print("\n[7] O registro guarda a forma da chamada, não o conteúdo")
    rec = carregar("app.services.skills.invocation_recorder")

    argumentos = {"cpf": "111.222.333-44", "telefone": "47999998888",
                  "consulta": "quero ver minha apólice", "limite": 5}
    resumo = rec.resumo_da_entrada(argumentos)

    checar(resumo.get("cpf") == "[omitido]", "CPF não entra", str(resumo.get("cpf")))
    checar(resumo.get("telefone") == "[omitido]", "telefone não entra")
    checar(resumo.get("limite") == 5, "número simples pode entrar — não identifica ninguém")
    checar(isinstance(resumo.get("consulta"), dict)
           and "tamanho" in resumo["consulta"],
           "texto vira tamanho, não conteúdo", str(resumo.get("consulta")))

    saida = rec._resumo_da_saida("um texto qualquer com o nome do segurado")
    checar("segurado" not in str(saida),
           "e a saída também vira forma, não conteúdo", str(saida))

    a = rec.fingerprint({"x": 1, "y": 2})
    b = rec.fingerprint({"y": 2, "x": 1})
    checar(a == b, "a identidade da entrada não muda com a ordem das chaves")
    checar(a != rec.fingerprint({"x": 1, "y": 3}), "e muda quando a entrada muda")


def teste_invocacao_sem_registry_nao_quebra():
    print("\n[8] Ferramenta fora do Registry não derruba a conversa")
    rec = carregar("app.services.skills.invocation_recorder")

    db = FakeDB()
    rec._CATALOGO.clear()
    with rec.RegistroDeInvocacao(db, company_id="empresa-1",
                                 nome_da_tool="ferramenta_inexistente",
                                 argumentos={}) as r:
        r.ok("resultado")

    checar(not db.dados.get("tool_invocations"),
           "nada é gravado para o que o Registry não conhece")
    checar(True, "e nenhuma exceção sobe — a ferramenta rodou")


def teste_invocacao_aberta_sempre_fecha():
    print("\n[9] Invocação que abre e não fecha polui toda contagem")
    rec = carregar("app.services.skills.invocation_recorder")

    db = FakeDB()
    db.dados["tool_definitions"] = [
        {"id": "d", "tool_key": "knowledge.search",
         "capability_key": "knowledge.tenant.search", "is_active": True}]
    db.dados["tool_releases"] = [
        {"id": "r", "tool_id": "d", "status": "published", "is_default": True}]
    rec._CATALOGO.clear()

    try:
        with rec.RegistroDeInvocacao(db, company_id="empresa-1",
                                     nome_da_tool="knowledge_base_search",
                                     argumentos={}):
            raise RuntimeError("a ferramenta explodiu")
    except RuntimeError:
        pass

    i = (db.dados.get("tool_invocations") or [{}])[0]
    checar(i.get("status") == "failed",
           "exceção fecha a invocação como falha", str(i.get("status")))

    db2 = FakeDB()
    db2.dados["tool_definitions"] = db.dados["tool_definitions"]
    db2.dados["tool_releases"] = db.dados["tool_releases"]
    rec._CATALOGO.clear()
    with rec.RegistroDeInvocacao(db2, company_id="empresa-1",
                                 nome_da_tool="knowledge_base_search",
                                 argumentos={}):
        pass  # sai sem ok() e sem exceção

    i2 = (db2.dados.get("tool_invocations") or [{}])[0]
    checar(i2.get("status") == "failed",
           "sair sem confirmar também fecha — nunca fica 'running' eterno",
           str(i2.get("status")))


def teste_nomes_das_tools_estao_no_mapa():
    print("\n[10] Toda ferramenta anexada tem chave no Registry")
    cut = carregar("app.agents.gateway_cutover")

    # Se um nome não estiver no mapa, `chave_de_registro` devolve o próprio
    # nome — e o cutover conta a ferramenta como "só no legado", errando para
    # baixo justamente a métrica que decide virar a chave do Gateway.
    esperado = {
        "knowledge_base_search": "knowledge.search",
        "pesquisar_na_web": "research.search_web",
        "monitorar_fonte": "research.create_monitor",
        "analisar_site": "research.site_audit",
        "briefing_da_corretora": "intelligence.briefing",
        "prioridades_da_corretora": "intelligence.findings",
        "gerar_relatorio": "artifacts.generate_report",
    }
    for nome, chave in esperado.items():
        obtido = cut.NOME_PARA_CHAVE.get(nome)
        checar(obtido == chave, f"'{nome}' → {chave}", f"obtido: {obtido}")


def main() -> int:
    print("=" * 68)
    print("BLOCO 0 — A EXECUÇÃO DEIXA RASTRO AUDITÁVEL")
    print("=" * 68)
    for teste in (
        teste_tentativa_e_gravada,
        teste_falha_fecha_a_tentativa,
        teste_erro_de_programacao_nao_e_retentavel,
        teste_retomada_numera_a_segunda_tentativa,
        teste_falha_de_auditoria_nao_derruba_o_trabalho,
        teste_invocacao_de_ferramenta_e_registrada,
        teste_invocacao_nao_guarda_dado_do_segurado,
        teste_invocacao_sem_registry_nao_quebra,
        teste_invocacao_aberta_sempre_fecha,
        teste_nomes_das_tools_estao_no_mapa,
    ):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} GARANTIA(S) QUEBRADA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("A EXECUÇÃO DEIXA RASTRO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
