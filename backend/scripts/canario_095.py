# -*- coding: utf-8 -*-
"""O canário vivo da SPEC-095 — roda o produto de verdade e mostra o que gravou.

```
--simular   roda TUDO sobre um dublê em memória. Sem rede, sem banco, sem InfoCap.
            É o modo que prova a LÓGICA — e é o único que o builder roda.
(sem flag)  roda AO VIVO na corretora indicada: `_publicar` de verdade, banco de
            verdade, InfoCap de verdade. É o BLOCO F, e quem o roda é o orquestrador.
```

## Por que este script existe, e por que ele exporta a variável

🔴 SPEC-095 · B.3: todo canário de SPEC roda com `AUTOBROKERS_CANARIO=1`, e a
peça que ele publicar nasce com `tags = ['canario']` — para que a limpeza da
próxima SPEC não precise adivinhar pela hora do commit qual relatório foi teste
nosso (📊 §1.1: 100% dos relatórios `origin='chat'` da Resulta são execução de
SPEC, e `tags` estava preenchida em 0/136 peças).

⚠️ **E por que não no `test_o_canario_do_pulso_360.py`.** 📊 Aquele guarda
substitui `rel._publicar` por um capturador (`:573-580`, `:813-819`,
`:1089-1118`, `:1263-1270`) e monta a tool com um `SupabaseFalso()`: ele **nunca
executa o `_publicar` real**. Exportar a variável lá seria decorativo — o
caminho que a lê não roda. Quem a exporta tem de ser quem roda o caminho: este
arquivo, e ele a exporta **antes do primeiro `import app.`**, porque o valor é
lido no ato da publicação e um import que acontecesse antes não mudaria nada —
mas um leitor que visse a ordem invertida teria de provar isso de novo.

## O que ele mede, na ordem do BLOCO F

```
(a) "como estamos?" pelo caminho REAL da tool  → peça com tags, título = achado,
                                                  subject_ref.id, data_sources, data_as_of
(b) a MESMA pergunta de novo                    → o MESMO artifact_id, current_version = 2
(c) o briefing SEM GRAVAR                       → manchete, why_now/next_step, duplicados,
                                                  Work Runs `system`, a frase de trabalhos
(e) os SELECTs de prova, colados
(f) arquiva o que criou                         → nenhuma peça `canario` viva ao fim
```

⛔ **(c) não publica.** `BriefingService.gerar` é idempotente por período
(`publicar` → `_publicacao_existente`): gerar "hoje" devolveria `reaproveitado`
e gerar "amanhã" bloquearia o tick real do dia seguinte. Este script chama os
LEITORES do serviço e as funções puras `compor` + `compor_pecas` — a primeira
publicação real com a narrativa nova é a do tick das 08:00.
"""
from __future__ import annotations

import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# 🔴 ANTES de qualquer `import app.` — ver a docstring.
os.environ["AUTOBROKERS_CANARIO"] = "1"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

#: A corretora do canário. 💭 A Resulta é a que tem carteira de verdade na
#: InfoCap; as outras duas entram no relatório como controle de isolamento.
RESULTA = "b26b3e79-b551-4c17-bd85-c0d0e5eb1d2a"


#: Os dois pacotes cujo `__init__.py` arrasta o grafo inteiro do produto.
#: 📊 `app/services/__init__.py` → `ingestion_service` → `fastembed`;
#: `app/agents/__init__.py` → `graph` → `langgraph`. Nenhum dos dois é usado
#: por este script, e nenhum dos dois existe em toda máquina onde um canário
#: precisa rodar.
PACOTES_DE_NAMESPACE = ("app.services", "app.agents", "app.agents.tools")


def sem_o_init_pesado() -> None:
    """Deixa os módulos importáveis sem executar os `__init__.py` pesados.

    ⚠️ Registrar o NAMESPACE resolve sem tocar no produto: cada módulo continua
    sendo importado pelo nome completo, com o `__package__` certo, e os imports
    relativos de dentro dele continuam válidos. É o que permite a este script
    exercitar o código de PRODUÇÃO — que é a única coisa que ele prova.
    """
    import types

    for nome in PACOTES_DE_NAMESPACE:
        if nome in sys.modules:
            continue
        mod = types.ModuleType(nome)
        mod.__path__ = [os.path.join(RAIZ, *nome.split("."))]
        sys.modules[nome] = mod


# ==========================================================================
# O DUBLÊ — o mínimo de PostgREST que o caminho de publicação exerce
# ==========================================================================
#
# ⛔ Ele não é um segundo banco: é um gravador de chamadas com filtros. O que
# roda em cima dele é o código de PRODUÇÃO, sem uma linha de desvio — que é a
# única forma de o `--simular` provar alguma coisa (CLAUDE.md §5).


class _Resposta:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Consulta:
    def __init__(self, tabela: str, linhas: list, banco: "BancoDeMentira"):
        self.tabela, self.linhas, self.banco = tabela, linhas, banco
        self.filtros: list = []
        self.acao = "select"
        self.carga = None
        self._limite = None
        self._um_so = False
        self._ordem = None

    # --- filtros ---------------------------------------------------------
    def eq(self, campo, valor):
        self.filtros.append((campo, "eq", valor))
        return self

    def neq(self, campo, valor):
        self.filtros.append((campo, "neq", valor))
        return self

    def is_(self, campo, valor):
        self.filtros.append((campo, "is", valor))
        return self

    def in_(self, campo, valores):
        self.filtros.append((campo, "in", list(valores)))
        return self

    def lt(self, campo, valor):
        self.filtros.append((campo, "lt", valor))
        return self

    def gte(self, campo, valor):
        self.filtros.append((campo, "gte", valor))
        return self

    def limit(self, n):
        self._limite = int(n)
        return self

    def order(self, campo, desc=False):
        self._ordem = (campo, bool(desc))
        return self

    def maybe_single(self):
        self._um_so = True
        return self

    # --- ações -----------------------------------------------------------
    def select(self, *_a, **kw):
        self.acao = "select"
        self._contar = kw.get("count")
        return self

    def insert(self, linha):
        self.acao, self.carga = "insert", linha
        return self

    def update(self, linha):
        self.acao, self.carga = "update", linha
        return self

    def upsert(self, linha, **_kw):
        self.acao, self.carga = "upsert", linha
        return self

    # --- execução --------------------------------------------------------
    def _valor(self, linha: dict, campo: str):
        """Lê o campo, inclusive o caminho jsonb `coluna->>chave`.

        🔴 É este ramo que faz o dublê exercer a busca de identidade do B.1:
        `.eq("subject_ref->>id", "2026")`. Sem ele, o `--simular` provaria a
        versão de um filtro que a produção não usa.
        """
        if "->>" in campo:
            coluna, chave = campo.split("->>", 1)
            return (linha.get(coluna.strip()) or {}).get(chave.strip())
        return linha.get(campo)

    def _passa(self, linha: dict) -> bool:
        for campo, op, valor in self.filtros:
            atual = self._valor(linha, campo)
            if op == "eq" and str(atual) != str(valor):
                return False
            if op == "neq" and str(atual) == str(valor):
                return False
            if op == "is" and not (atual is None if valor == "null" else atual is valor):
                return False
            if op == "in" and atual not in valor:
                return False
            if op == "lt" and not (atual is not None and str(atual) < str(valor)):
                return False
            if op == "gte" and not (atual is not None and str(atual) >= str(valor)):
                return False
        return True

    def execute(self):
        if self.acao in ("insert", "upsert"):
            linha = dict(self.carga)
            linha.setdefault("id", self.banco.novo_id(self.tabela))
            linha.setdefault("created_at", self.banco.agora())
            self.linhas.append(linha)
            self.banco.escritas += 1
            return _Resposta([linha])

        casadas = [x for x in self.linhas if self._passa(x)]

        if self.acao == "update":
            for x in casadas:
                x.update(self.carga)
            self.banco.escritas += 1
            return _Resposta(casadas)

        if self._ordem:
            campo, desc = self._ordem
            casadas = sorted(casadas, key=lambda x: str(x.get(campo) or ""),
                             reverse=desc)
        if self._limite is not None:
            casadas = casadas[: self._limite]
        if self._um_so:
            return _Resposta(casadas[0] if casadas else None)
        return _Resposta(casadas, count=len(casadas))


class BancoDeMentira:
    """Tabelas em memória. Conta as escritas — é assim que o [B.e] mede."""

    def __init__(self):
        self.tabelas: dict = {}
        self.escritas = 0
        self._seq = 0

    def novo_id(self, tabela: str) -> str:
        # ⚠️ O id do dublê precisa ser distinguível nos 8 primeiros caracteres:
        # é assim que os passos o imprimem, e dois ids que aparecem iguais na
        # tela fazem o leitor concluir que houve uma peça onde houve duas.
        self._seq += 1
        return "%04d-%s" % (self._seq, tabela[:10])

    @staticmethod
    def agora() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    def table(self, nome: str) -> _Consulta:
        return _Consulta(nome, self.tabelas.setdefault(nome, []), self)


# ==========================================================================
# Os passos
# ==========================================================================


def _mostrar_peca(db, artifact_id: str, titulo_do_passo: str) -> None:
    """(e) Os SELECTs de prova. ⛔ Sem PII: título de relatório não é nome."""
    art = (db.table("artifacts")
           .select("id, title, subtitle, tags, subject_ref, current_version, "
                   "template_key, archived_at")
           .eq("id", artifact_id).maybe_single().execute()).data or {}
    versoes = (db.table("artifact_versions")
               .select("version, status, data_as_of, confidence_note, data_sources")
               .eq("artifact_id", artifact_id)
               .order("version", desc=False).limit(20).execute()).data or []
    print("   %s" % titulo_do_passo)
    print("      id ................ %s" % str(art.get("id"))[:8])
    print("      title ............. %s" % art.get("title"))
    print("      subtitle .......... %s" % art.get("subtitle"))
    print("      tags .............. %s" % (art.get("tags") or []))
    print("      subject_ref ....... %s" % (art.get("subject_ref") or {}))
    print("      current_version ... %s" % art.get("current_version"))
    print("      archived_at ....... %s" % art.get("archived_at"))
    for v in versoes:
        fontes = v.get("data_sources") or []
        print("      v%s  status=%-10s data_as_of=%s  fontes=%d  nota=%s"
              % (v.get("version"), v.get("status"), v.get("data_as_of"),
                 len(fontes), v.get("confidence_note")))


def passo_ab_simulado(db) -> list:
    """(a)(b) sobre o dublê: `_publicar` duas vezes, a MESMA identidade."""
    from app.agents.tools.relatorios_comerciais import (
        _publicar, fontes_dos_blocos, identidade_do_periodo)
    from datetime import datetime

    def blocos_de(titulo: str, verdito: str) -> list:
        return [
            {"block": "cover", "props": {
                "eyebrow": "Pulso 360", "title": titulo,
                "subtitle": "Pulso 360 · 2026 · dados lidos em 04/09/2026 às 03:00",
                "period": "2026"}},
            {"block": "verdict", "props": {"text": verdito}},
            {"block": "sources", "props": {"items": [
                {"label": "InfoCap · carteira da corretora",
                 "detail": "produção, comissão e produtores",
                 "as_of_label": "consultado em 04/09/2026 às 03:00"}]}},
        ]

    lidos_em = datetime.now().astimezone()
    b1 = blocos_de("Porto concentra 46,8% da comissão de 2026",
                   "Acima de 40%, um reajuste dessa seguradora mexe em quase "
                   "metade da receita.")
    id1 = _publicar(db, RESULTA, titulo=b1[0]["props"]["title"],
                    subtitulo=b1[0]["props"]["subtitle"],
                    resumo=b1[1]["props"]["text"],
                    template="executive.pulse360", payload={"evidence_pack": {}},
                    blocos=b1, identidade=identidade_do_periodo("2026"),
                    data_sources=fontes_dos_blocos(b1), data_as_of=lidos_em,
                    confidence_note="2 métrica(s) indisponível(is); cobertura mínima 80,6%")
    _mostrar_peca(db, id1, "(a) primeiro pedido")

    # 🔴 O achado MUDOU entre as duas leituras — é o caso que importa: a peça
    # é a mesma, e o título tem de acompanhar o dado.
    b2 = blocos_de("61 apólices vencem na janela · 12 já vencidas",
                   "Renovação não trabalhada é comissão que some no mês seguinte.")
    id2 = _publicar(db, RESULTA, titulo=b2[0]["props"]["title"],
                    subtitulo=b2[0]["props"]["subtitle"],
                    resumo=b2[1]["props"]["text"],
                    template="executive.pulse360", payload={"evidence_pack": {}},
                    blocos=b2, identidade=identidade_do_periodo("2026"),
                    data_sources=fontes_dos_blocos(b2), data_as_of=lidos_em)
    _mostrar_peca(db, id2, "(b) o MESMO pedido de novo")

    print()
    print("   📊 mesmo artifact_id ......... %s" % (id1 == id2))
    print("   📊 artifacts inseridos ....... %d"
          % len(db.tabelas.get("artifacts", [])))
    print("   📊 versões inseridas ......... %d"
          % len(db.tabelas.get("artifact_versions", [])))
    eventos = [e.get("event_type") for e in db.tabelas.get("artifact_events", [])]
    print("   📊 eventos ................... %s" % eventos)

    # O PAR: identidade DIFERENTE tem de criar peça nova.
    b3 = blocos_de("Raio-X de 2025", "Outro período.")
    id3 = _publicar(db, RESULTA, titulo=b3[0]["props"]["title"],
                    subtitulo="", resumo="", template="executive.pulse360",
                    payload={}, blocos=b3,
                    identidade=identidade_do_periodo("2025"),
                    data_sources=fontes_dos_blocos(b3), data_as_of=lidos_em)
    print("   📊 PAR · identidade 2025 → peça NOVA: %s (artifacts agora: %d)"
          % (id3 != id1, len(db.tabelas.get("artifacts", []))))
    # 🔴 As DUAS voltam: o passo (f) arquiva tudo o que este script criou, e
    # não só a peça principal. Devolver uma só deixaria a do PAR viva, marcada
    # como canário, na biblioteca do dono — que é o defeito que o (f) existe
    # para não cometer.
    return [id1, id3]


async def passo_ab_ao_vivo(db, periodo: str) -> list:
    """(a)(b) AO VIVO: a tool do Pulso pelo caminho real, com o cliente real."""
    from app.agents.tools.executive_intelligence import ExecutiveIntelligenceTool

    tool = ExecutiveIntelligenceTool(company_id=RESULTA, supabase=db)
    for rotulo in ("(a) primeiro pedido", "(b) o MESMO pedido de novo"):
        resposta = await tool._arun(period=periodo)
        print("   %s → %s" % (rotulo, str(resposta).splitlines()[0][:120]))

    art = (db.table("artifacts")
           .select("id").eq("company_id", RESULTA)
           .eq("template_key", "executive.pulse360")
           .eq("subject_ref->>id", periodo).is_("archived_at", "null")
           .limit(2).execute()).data or []
    if not art:
        raise RuntimeError("o canário não achou a peça que acabou de publicar")
    artifact_id = str(art[0]["id"])
    _mostrar_peca(db, artifact_id, "(e) a peça, depois dos dois pedidos")
    print("   📊 peças vivas com esta identidade: %d  (tem de ser 1)" % len(art))
    return [artifact_id]


def passo_c(db, ao_vivo: bool) -> None:
    """(c) O briefing SEM GRAVAR: os leitores + `compor` + `compor_pecas`."""
    from datetime import datetime, timedelta, timezone

    from app.services.intelligence.briefing_service import compor
    from app.services.intelligence.workflows import compor_pecas

    fim = datetime.now(timezone.utc)
    inicio = fim - timedelta(days=1)

    if ao_vivo:
        from app.services.intelligence.briefing_service import BriefingService
        from app.services.intelligence.finding_engine import FindingEngine
        from app.services.intelligence.recommendation_service import RecommendationService

        servico = BriefingService(db)
        findings = FindingEngine(db).ativos(RESULTA, limite=40)
        recomendacoes = RecommendationService(db).elegiveis(RESULTA, limite=20)
        em_curso = servico._trabalhos(RESULTA, ativos=True)
        concluidos = servico._trabalhos(RESULTA, ativos=False, desde=inicio)
        faltando = servico._o_que_falta(RESULTA, inicio, findings)
    else:
        # 💭 O dublê carrega o retrato do que o banco tinha em 04/09: um achado
        # de observação com sumário de três frases, dois itens IDÊNTICOS, e
        # Work Runs do relógio da plataforma junto com um pedido de verdade.
        findings = [
            {"id": "f1", "finding_type": "observacao", "title": "Ponto de atenção",
             "summary": "Fila acumulada. 61 atendimentos parados há mais de 24 h "
                        "e nenhum deles foi respondido hoje.",
             "priority_score": 92.0, "severity": "high",
             "why_now": "A fila cresceu 40% em 24 h.",
             "next_step": "Distribuir os 61 entre a equipe antes das 10 h.",
             "fact_statement": "61 atendimentos com última resposta há mais de 24 h"},
            {"id": "f2", "finding_type": "fila_acumulada", "title": "Cotações paradas",
             "summary": "12 cotações sem retorno.", "priority_score": 60.0,
             "why_now": "Cotação parada perde para quem responde primeiro.",
             "next_step": "Responder as 12."},
            {"id": "f3", "finding_type": "fila_acumulada", "title": "Cotações paradas",
             "summary": "12 cotações sem retorno.", "priority_score": 59.0},
        ]
        recomendacoes = []
        em_curso = [
            {"id": "w1", "outcome_title": "Procurar o que mudou na operação",
             "status": "running", "progress_percent": 0, "source_type": "system"},
            {"id": "w2", "outcome_title": "Procurar o que mudou na operação",
             "status": "running", "progress_percent": 0, "source_type": "system"},
            {"id": "w3", "outcome_title": "Procurar o que mudou na operação",
             "status": "running", "progress_percent": 0, "source_type": "system"},
            {"id": "w4", "outcome_title": "Cobrar os boletos vencidos",
             "status": "running", "progress_percent": 50, "source_type": "routine"},
            {"id": "w5", "outcome_title": "Cobrar os boletos vencidos",
             "status": "running", "progress_percent": 50, "source_type": "routine"},
        ]
        concluidos = [
            {"id": "w6", "outcome_title": "Medir os resultados", "status": "completed",
             "result_summary": "0 medições.", "source_type": "system"},
        ]
        faltando = []

    spec = compor(company_id=RESULTA, briefing_type="daily_operational",
                  findings=findings, recomendacoes=recomendacoes,
                  trabalhos_em_curso=em_curso, resultados=concluidos,
                  outcomes=[], faltando=faltando,
                  period_start=inicio, period_end=fim)

    print("   manchete .......... %s" % spec.headline)
    print("   resumo ............ %s" % spec.executive_summary)
    print()
    itens = [i.como_dict(n) for n, i in enumerate(spec.itens)]
    for i in itens:
        print("      [%s] %s" % (i["item_type"], i["headline"]))
        if i.get("why_now"):
            print("           why_now   : %s" % i["why_now"])
        if i.get("next_step"):
            print("           next_step : %s" % i["next_step"])

    chaves = [(i["headline"], i["summary"]) for i in itens]
    duplicados = len(chaves) - len(set(chaves))
    com_porque = len([i for i in itens
                      if i["item_type"] == "finding" and i.get("why_now")])
    achados = len([i for i in itens if i["item_type"] == "finding"])
    print()
    print("   📊 itens .................... %d" % len(itens))
    print("   📊 itens duplicados ......... %d   (tem de ser 0)" % duplicados)
    print("   📊 achados com `why_now` .... %d de %d" % (com_porque, achados))
    print("   📊 Work Runs entregues ...... %d de %d pedidos"
          % (len(concluidos), len(em_curso)))
    do_relogio = len([w for w in list(em_curso) + list(concluidos)
                      if str(w.get("source_type") or "") == "system"])
    print("   📊 Work Runs `system` na ENTRADA .. %d" % do_relogio)
    print("   📊 a frase 'trabalho(s) pronto(s)' na manchete: %s"
          % ("trabalho(s) pronto(s)" in spec.headline))

    blocos = compor_pecas(spec.como_payload())
    print("   📊 blocos da peça ........... %s"
          % [b.get("block") for b in blocos])
    acoes = [b for b in blocos if b.get("block") == "actions"]
    for b in acoes:
        for it in (b.get("props") or {}).get("items", [])[:3]:
            print("      ação: %s" % it.get("title"))
            print("            %s" % it.get("detail"))


def passo_f(db, ids: list) -> None:
    """(f) O canário arquiva o que criou. Nada `canario` fica vivo."""
    from app.services.artifacts.service import TAG_DO_CANARIO, ArtifactService

    servico = ArtifactService(db)
    for artifact_id in ids:
        ok = servico.arquivar(RESULTA, artifact_id,
                              "canário vivo da SPEC-095 — arquivado pelo próprio script")
        print("   arquivou %s… → %s" % (str(artifact_id)[:8], ok))
    vivas = (db.table("artifacts").select("id, tags")
             .eq("company_id", RESULTA).is_("archived_at", "null")
             .limit(200).execute()).data or []
    restam = [v for v in vivas if TAG_DO_CANARIO in (v.get("tags") or [])]
    print("   📊 peças `%s` vivas ao fim: %d   (tem de ser 0)"
          % (TAG_DO_CANARIO, len(restam)))


def main() -> int:
    p = argparse.ArgumentParser(description="Canário vivo da SPEC-095.")
    p.add_argument("--simular", action="store_true",
                   help="dublê em memória, sem rede. O modo do builder.")
    p.add_argument("--periodo", default="2026", help="o período do Pulso (ao vivo).")
    a = p.parse_args()

    sem_o_init_pesado()
    print("=" * 74)
    print("CANÁRIO DA SPEC-095 · %s" % ("SIMULADO (dublê, sem rede)" if a.simular
                                        else "AO VIVO"))
    print("AUTOBROKERS_CANARIO = %r" % os.environ.get("AUTOBROKERS_CANARIO"))
    print("=" * 74)
    print()

    if a.simular:
        db = BancoDeMentira()
    else:
        from app.core.database import get_supabase_client

        db = get_supabase_client().client

    print("[a][b] A PEÇA — uma identidade, duas versões")
    print("-" * 74)
    if a.simular:
        criados = passo_ab_simulado(db)
    else:
        import asyncio

        criados = asyncio.run(passo_ab_ao_vivo(db, a.periodo))
    print()

    print("[c] O BRIEFING — sem gravar")
    print("-" * 74)
    passo_c(db, ao_vivo=not a.simular)
    print()

    print("[f] O CANÁRIO ARQUIVA O QUE CRIOU")
    print("-" * 74)
    passo_f(db, criados)
    print()
    if a.simular:
        print("📊 escritas no dublê ......... %d" % db.escritas)
        print("⚠️ MODO SIMULADO. Nada saiu desta máquina, nada foi ao banco.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
