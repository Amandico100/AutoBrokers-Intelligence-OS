"""SPEC-061 §13 — a caixa mostra a causa, não o sintoma.

Por que este arquivo existe
---------------------------
Uma caixa de entrada operacional falha de três jeitos:

1. **repete a mesma causa** — oito rotinas quebradas pelo mesmo provider fora
   do ar viram oito cartões, o operador trata sintoma e o provider continua
   fora do ar;
2. **mostra o que a pessoa não pode ver** — o financeiro abre a caixa e lê
   resumo de sinal de corretora;
3. **fica vazia por erro** e parece limpa — a pior das três, porque não tem
   sintoma nenhum.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.control_plane", ("app", "services", "control_plane"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m


def carregar(nome: str):
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


carregar("app.services.control_plane.rbac")
carregar("app.services.control_plane.audit")
I = carregar("app.services.control_plane.inbox")

AGORA = datetime.now(timezone.utc)


class FakeQ:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self._filtros: list[tuple] = []

    def select(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self._filtros.append((c, v))
        return self

    def upsert(self, linha, **_k):
        self.banco.linhas.setdefault(self.tabela, []).append(dict(linha))
        return self

    def execute(self):
        if self.tabela in self.banco.quebradas:
            raise RuntimeError("tabela fora do ar")
        linhas = self.banco.linhas.get(self.tabela, [])
        for c, v in self._filtros:
            linhas = [l for l in linhas if str(l.get(c)) == str(v)]
        return types.SimpleNamespace(data=linhas)


class FakeDB:
    def __init__(self, quebradas=()):
        self.linhas: dict[str, list[dict]] = {}
        self.quebradas = set(quebradas)
        self.client = self

    def table(self, nome):
        return FakeQ(self, nome)


TODAS = {"approvals.read", "work_runs.read", "research.read",
         "intelligence.read", "knowledge.curate", "security.read"}


def teste_dedupe_por_causa():
    print("\n[1] Oito rotinas quebradas pelo mesmo provider são UM problema")
    itens = [I.ItemDaCaixa(
        fonte="work_run", chave=f"r{i}", titulo="Trabalho falhou",
        detalhe="bridge.routine.execute: provider_indisponivel",
        severidade="medium", company_id=f"empresa-{i % 3}",
        ocorrido_em=AGORA.isoformat(),
        metadata={"erro": "provider_indisponivel",
                  "workflow": "bridge.routine.execute"})
        for i in range(8)]

    agrupado = I.agrupar_por_causa(itens)
    checar(len(agrupado) == 1, "vira um cartão só", f"{len(agrupado)} cartões")
    if not agrupado:
        return
    c = agrupado[0]
    checar(c.itens_agrupados == 8, "que declara os 8 casos", str(c.itens_agrupados))
    checar(c.empresas_afetadas == 3, "e as 3 corretoras", str(c.empresas_afetadas))
    checar("3 corretora" in c.detalhe and "8 item" in c.detalhe,
           "o alcance aparece no texto — é o que faz tratar a causa", c.detalhe)
    checar(c.company_id is None,
           "sem corretora dona: o problema é de plataforma, não de uma delas")


def teste_causas_diferentes_nao_se_misturam():
    print("\n[2] Causas diferentes continuam separadas")
    itens = [
        I.ItemDaCaixa(fonte="work_run", chave="a", titulo="Trabalho falhou",
                      detalhe="x", metadata={"erro": "sem_credito"}),
        I.ItemDaCaixa(fonte="work_run", chave="b", titulo="Trabalho falhou",
                      detalhe="y", metadata={"erro": "timeout"}),
        I.ItemDaCaixa(fonte="approval", chave="c", titulo="Aprovação esperando decisão",
                      detalhe="z"),
    ]
    checar(len(I.agrupar_por_causa(itens)) == 3,
           "três causas, três cartões — juntar tudo esconderia dois problemas")


def teste_prioridade_poe_o_grave_no_topo():
    print("\n[3] O mais grave e mais amplo sobe")
    critico_amplo = I.ItemDaCaixa(
        fonte="incident", chave="i1", titulo="Incidente", detalhe="",
        severidade="critical", empresas_afetadas=5, itens_agrupados=5,
        ocorrido_em=AGORA.isoformat())
    baixo_isolado = I.ItemDaCaixa(
        fonte="knowledge", chave="k1", titulo="Curadoria", detalhe="",
        severidade="low", ocorrido_em=AGORA.isoformat())
    checar(critico_amplo.prioridade(AGORA) > baixo_isolado.prioridade(AGORA),
           "incidente crítico em 5 corretoras vence curadoria pendente",
           f"{critico_amplo.prioridade(AGORA)} vs {baixo_isolado.prioridade(AGORA)}")

    velho = I.ItemDaCaixa(fonte="work_run", chave="v", titulo="t", detalhe="",
                          severidade="high",
                          ocorrido_em=(AGORA - timedelta(days=3)).isoformat())
    novo = I.ItemDaCaixa(fonte="work_run", chave="n", titulo="t", detalhe="",
                         severidade="high", ocorrido_em=AGORA.isoformat())
    checar(novo.prioridade(AGORA) > velho.prioridade(AGORA),
           "o recente pesa mais")
    checar(velho.prioridade(AGORA) > 0,
           "mas o antigo não vira zero — não tratado continua importando")


def teste_permission_filtra_a_fonte():
    print("\n[4] Fonte que a pessoa não pode ler NÃO é consultada")
    db = FakeDB()
    db.linhas["intelligence_signals"] = [
        {"id": "s1", "company_id": "c1", "summary_redacted": "segredo comercial",
         "severity": "critical", "created_at": AGORA.isoformat(),
         "signal_type": "x"}]
    db.linhas["approval_requests"] = [
        {"id": "a1", "company_id": "c1", "status": "pending",
         "created_at": AGORA.isoformat(), "action_key": "enviar",
         "risk_level": "high"}]

    # Financeiro: tem approvals? não. Tem intelligence? não.
    r = I.CaixaDeEntrada(db).montar(admin_user_id="u",
                                    permissions={"finance.read"})
    checar(r["total"] == 0, "financeiro não vê nada disso", str(r["total"]))
    checar("Nada precisa" in r["mensagem"],
           "e a caixa DIZ que está vazia, em vez de ficar muda")

    r2 = I.CaixaDeEntrada(db).montar(admin_user_id="u",
                                     permissions={"intelligence.read"})
    checar(r2["total"] == 1, "quem pode ler inteligência vê o sinal")
    checar(all("segredo comercial" not in str(x.get("detalhe", ""))
               for x in r["itens"]),
           "e o conteúdo não vaza para quem não pode")


def teste_fonte_quebrada_nao_derruba_a_caixa():
    print("\n[5] Uma fonte fora do ar não zera a caixa inteira")
    db = FakeDB(quebradas={"approval_requests"})
    db.linhas["platform_incidents"] = [
        {"id": "i1", "incident_key": "k", "severity": "sev1", "status": "open",
         "scope": "platform", "summary": "provider caiu",
         "detected_at": AGORA.isoformat()}]

    r = I.CaixaDeEntrada(db).montar(
        admin_user_id="u", permissions={"approvals.read", "security.read"})
    checar(r["total"] == 1,
           "o incidente continua aparecendo mesmo com aprovações fora do ar",
           str(r["total"]))


def teste_dispensar_nao_muda_o_original():
    print("\n[6] §13.3 — dispensar tira da MINHA caixa e nada mais")
    db = FakeDB()
    db.linhas["approval_requests"] = [
        {"id": "a1", "company_id": "c1", "status": "pending",
         "created_at": AGORA.isoformat(), "action_key": "enviar",
         "risk_level": "low"}]
    db.linhas["admin_inbox_states"] = [
        {"admin_user_id": "u", "source_type": "approval", "source_id": "a1",
         "state": "dismissed", "snoozed_until": None}]

    r = I.CaixaDeEntrada(db).montar(admin_user_id="u",
                                    permissions={"approvals.read"})
    checar(r["total"] == 0, "some da caixa de quem dispensou")
    checar(db.linhas["approval_requests"][0]["status"] == "pending",
           "e a aprovação continua PENDENTE na autoridade dela")

    outro = I.CaixaDeEntrada(db).montar(admin_user_id="outro",
                                        permissions={"approvals.read"})
    checar(outro["total"] == 1,
           "outra pessoa continua vendo — o estado é pessoal")


def teste_adiar_exige_data():
    print("\n[7] Adiar sem data é dispensar com outro nome")
    db = FakeDB()
    caixa = I.CaixaDeEntrada(db)
    r = caixa.marcar(admin_user_id="u", fonte="approval", chave="a1",
                     estado="snoozed")
    checar(not r.get("ok"), "recusado", str(r.get("erro"))[:60])
    checar("até quando" in str(r.get("erro", "")),
           "com frase que diz o que fazer")

    r2 = caixa.marcar(admin_user_id="u", fonte="approval", chave="a1",
                      estado="snoozed",
                      adiar_ate=(AGORA + timedelta(days=1)).isoformat())
    checar(r2.get("ok"), "com data, aceito")

    r3 = caixa.marcar(admin_user_id="u", fonte="a", chave="b",
                      estado="inventado")
    checar(not r3.get("ok"), "estado desconhecido é recusado")


def teste_adiamento_vencido_traz_o_item_de_volta():
    print("\n[8] O que foi adiado volta quando o prazo acaba")
    db = FakeDB()
    db.linhas["approval_requests"] = [
        {"id": "a1", "company_id": "c1", "status": "pending",
         "created_at": AGORA.isoformat(), "action_key": "x", "risk_level": "low"}]
    db.linhas["admin_inbox_states"] = [
        {"admin_user_id": "u", "source_type": "approval", "source_id": "a1",
         "state": "snoozed",
         "snoozed_until": (AGORA - timedelta(hours=1)).isoformat()}]

    r = I.CaixaDeEntrada(db).montar(admin_user_id="u",
                                    permissions={"approvals.read"})
    checar(r["total"] == 1, "prazo vencido: o item reaparece")

    db.linhas["admin_inbox_states"][0]["snoozed_until"] = (
        AGORA + timedelta(hours=1)).isoformat()
    r2 = I.CaixaDeEntrada(db).montar(admin_user_id="u",
                                     permissions={"approvals.read"})
    checar(r2["total"] == 0, "dentro do prazo, continua escondido")


def teste_monitor_nao_afirma_que_nada_mudou():
    print("\n[9] Fonte ilegível não vira 'nada mudou'")
    db = FakeDB()
    db.linhas["research_monitors"] = [
        {"id": "m1", "company_id": "c1", "name": "SUSEP — normas",
         "health": "error", "health_reason": "página fora do ar",
         "last_run_at": AGORA.isoformat(), "is_active": True}]

    r = I.CaixaDeEntrada(db).montar(admin_user_id="u",
                                    permissions={"research.read"})
    checar(r["total"] == 1, "o monitor com falha aparece")
    detalhe = r["itens"][0]["detalhe"]
    checar("não consegui ler" in detalhe.lower(),
           "e o texto diz que NÃO conseguiu ler", detalhe)
    checar("nada mudou" not in detalhe.lower().replace("não afirmo que nada mudou", ""),
           "nunca afirmando que nada mudou")


def main() -> int:
    print("=" * 68)
    print("SPEC-061 §13 — A CAIXA MOSTRA A CAUSA, NÃO O SINTOMA")
    print("=" * 68)
    for teste in (
        teste_dedupe_por_causa,
        teste_causas_diferentes_nao_se_misturam,
        teste_prioridade_poe_o_grave_no_topo,
        teste_permission_filtra_a_fonte,
        teste_fonte_quebrada_nao_derruba_a_caixa,
        teste_dispensar_nao_muda_o_original,
        teste_adiar_exige_data,
        teste_adiamento_vencido_traz_o_item_de_volta,
        teste_monitor_nao_afirma_que_nada_mudou,
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
    print("A CAIXA PRIORIZA, AGRUPA E RESPEITA O QUE CADA UM PODE VER")
    return 0


if __name__ == "__main__":
    sys.exit(main())
