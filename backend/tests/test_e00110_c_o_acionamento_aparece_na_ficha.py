# -*- coding: utf-8 -*-
"""P-PILOTO-02 + P-PILOTO-08 + `_idempotency_key`, pelo caminho REAL da tool.

O arquivo irmão (`test_e00110_c_o_desfecho_chega_ao_segurado.py`) prova as
funções puras. Este aqui roda `PortalActionTool._arun` de verdade, com um dublê
do cliente Supabase — o mesmo molde de
`test_o_que_acontece_quando_o_agente_liga.py`. Só a InfoCap, a rede do WhatsApp
e o `registrar_tela_cega` são substituídos: **quem escreve o `work_run` é o
helper de produção** (`work.runs.criar_registro_sem_fila`).

## 🔴 O defeito, medido

📊 08/09/2026, reconfirmado em 20/09 (P-PILOTO-02): `portal_jobs` tem as colunas
`work_run_id`, `agent_id` e `operation_key`, e as três ficavam vazias.
`lib/atendimento/casos.ts` lê cinco tabelas e nenhuma é `portal_jobs`. Efeito: um
acionamento de vidros acontecia, custava dinheiro ao segurado, e **não existia**
para quem olha o produto.

📊 P-PILOTO-08: `tela_cega` só era escrita pelo corredor de URA; o worker do
navegador gravava `debug_dom` num jsonb que ninguém varria.

## ⛔ E a lei que atravessa tudo: DUAS CORRETORAS

O backend roda com service role — a RLS não protege contra um filtro esquecido
no código (CLAUDE.md §7). Por isso cada bloco aqui tem a corretora B do lado,
com a MESMA sessão e o MESMO pedido, e a pergunta é sempre a mesma: *o que é de
uma apareceu na outra?*
"""
from __future__ import annotations

import asyncio
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.agents.tools import portal_tool as PT  # noqa: E402

PASS = FAIL = 0


def checar(cond, nome, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok]     " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  << " + str(extra)[:400] if extra else ""))


# 💭 Duas corretoras fictícias, com uuids óbvios. ⛔ Nenhum nome de corretora
# real entra em teste (CLAUDE.md §13.9).
EMPRESA_A = "aaaaaaaa-0000-4000-8000-000000000001"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-000000000002"
CONVERSA_A = "cccccccc-0000-4000-8000-00000000000a"
CONVERSA_B = "cccccccc-0000-4000-8000-00000000000b"
AGENTE_A = "dddddddd-0000-4000-8000-00000000000a"
AGENTE_B = "dddddddd-0000-4000-8000-00000000000b"
SESSAO = "whatsapp:5548900000000:co:ag"

PERFIL_ROW = {
    "company_name": "Corretora Exemplo", "legal_name": "Corretora Exemplo LTDA",
    "primary_contact_name": "Atendimento Exemplo",
    "primary_contact_email": "operacao@exemplo.test",
    "primary_contact_phone": "4830000000", "cnpj": "00000000000191",
    "acionamento_profile": None,
}

INFOCAP = {
    "ok": True,
    "policy": {"numapo": "000000", "seguradora": "LIBERTY SEGUROS S/A"},
    "vehicle": {"placa": "AAA0A91", "veiculo": "MODELO EXEMPLO 1.0",
                "chassi": "9XX0000000000000"},
    "client": {"nome": "Segurado Exemplo", "cep": "88000-000",
               "logradouro": "Rua Exemplo", "numero": "1", "bairro": "Centro",
               "cidade": "Florianopolis", "estado": "SC",
               "telefone": "48900000000", "email": "segurado@exemplo.test"},
}

PEDIDO = {
    "cpf_cnpj": "52998224725", "data_dano": "05/07/2026",
    "peca": "vidro de porta", "como_ocorreu": "encontrou o veiculo danificado",
    "onde_ocorreu": "urbano",
    "descricao": "o carro estava estacionado e o vidro da porta foi quebrado",
    # ⚠️ ATUALIZADO em 20/09/2026 (CLAUDE.md §9.3): "completo" mudou de novo. As
    # perguntas que o portal REALMENTE FAZ no questionario passaram a ser cobradas
    # antes da fronteira A — 📊 na captura do vidro de porta ele perguntou pelicula
    # (P4), dianteira/traseira (P39) e lado (P35). **Nao existe journey de
    # continuacao**: o token vive so em memoria e `safe_to_retry_open` e False
    # depois do POST, entao faltar uma resposta vira atendimento terminado a mao.
    "especificos": {"onde_realizar_o_servico": "loja",
                    "cidade_para_o_servico": "Joinville/SC",
                    "pelicula": "tem insulfilm sim",
                    "porta_dianteira_ou_traseira": "dianteira",
                    "lado_motorista_ou_carona": "do lado do carona"},
}

DESFECHO_CONHECIDO = {"tipo": "loja_direta", "codigo_atendimento": "99999999",
                      "franquias": [{"titulo": "Franquia", "valor": "630"}],
                      "loja": {"nome": "Vidracaria Exemplo",
                               "endereco": "Rua de Exemplo, 100"}}
EVIDENCIA_DESCONHECIDA = {"tela_desconhecida": {
    "onde": "opcoes-disponiveis", "resumo_mascarado": "Tela nova do portal ***"}}


class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.operacao, self.linha = {}, "select", {}

    def select(self, *_a, **_k):
        return self

    def insert(self, linha):
        self.operacao, self.linha = "insert", dict(linha)
        return self

    def update(self, patch):
        self.operacao, self.linha = "update", dict(patch)
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def neq(self, *_a):
        return self

    def is_(self, *_a):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return self.banco.executar(self)


class BancoDeMentira:
    """Guarda o que foi escrito e por quem — é isso que o teste lê depois."""

    def __init__(self, resultado_do_job: dict):
        self.jobs: list = []
        self.work_runs: list = []
        self.work_events: list = []
        self.updates_de_job: list = []
        self.updates_de_run: list = []
        self.resultado_do_job = resultado_do_job
        # As duas corretoras têm conversa com a MESMA `session_id` de propósito:
        # é assim que um filtro esquecido vira dado cruzado.
        self.conversas = [
            {"id": CONVERSA_A, "company_id": EMPRESA_A, "session_id": SESSAO},
            {"id": CONVERSA_B, "company_id": EMPRESA_B, "session_id": SESSAO},
        ]
        self.agentes = [
            {"id": AGENTE_A, "company_id": EMPRESA_A},
            {"id": AGENTE_B, "company_id": EMPRESA_B},
        ]

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Consulta(self, nome)

    def _filtrar(self, linhas, filtros):
        return [l for l in linhas
                if all(l.get(k) == v for k, v in filtros.items() if k in l or True)]

    def executar(self, q: _Consulta) -> _Resposta:
        f = q.filtros
        if q.tabela == "agents":
            achados = [a for a in self.agentes if a["company_id"] == f.get("company_id")]
            return _Resposta([{"id": achados[0]["id"]}] if achados else [])
        if q.tabela == "companies":
            return _Resposta([dict(PERFIL_ROW)])
        if q.tabela == "conversations":
            achados = [c for c in self.conversas
                       if all(c.get(k) == v for k, v in f.items())]
            return _Resposta([{"id": c["id"]} for c in achados])
        if q.tabela == "work_runs":
            if q.operacao == "insert":
                self.work_runs.append(dict(q.linha))
                return _Resposta([dict(q.linha)])
            if q.operacao == "update":
                self.updates_de_run.append({"filtros": dict(f), "patch": dict(q.linha)})
                return _Resposta([])
            return _Resposta([])          # nunca reaproveita: sempre nasce
        if q.tabela == "work_events":
            self.work_events.append(dict(q.linha))
            return _Resposta([])
        if q.tabela == "portal_jobs":
            if q.operacao == "insert":
                linha = {**q.linha, "id": f"job-{len(self.jobs) + 1}"}
                self.jobs.append(linha)
                return _Resposta([{"id": linha["id"]}])
            if q.operacao == "update":
                self.updates_de_job.append({"filtros": dict(f), "patch": dict(q.linha)})
                return _Resposta([])
            if "id" in f:                 # o poll do `_arun`
                return _Resposta([dict(self.resultado_do_job)])
            return _Resposta([])          # nenhum pedido vivo
        return _Resposta([])


class PortalDeMentira(PT.PortalActionTool):
    """A ferramenta REAL. Só a InfoCap sai — ela é rede, não decisão."""

    async def _fetch_infocap(self, cpf, policy_number):  # noqa: D102
        return INFOCAP


TELAS_CEGAS: list = []


def _preparar_ambiente():
    """Troca só o que é rede. O resto é código de produção."""
    import app.core.database as DB
    import app.services.tela_cega as TC
    import app.services.atlas.attendance_capture as AC

    async def _cliente_async():
        return _ATUAL["banco"]

    async def _registrar(**kwargs):
        TELAS_CEGAS.append(dict(kwargs))
        return True

    async def _agente_ligado(_company_id):
        return False      # o pedido para no 80%; o espelho nasce do mesmo jeito

    DB.create_async_supabase_client = _cliente_async
    DB.get_supabase_client = lambda: _ATUAL["banco"]
    TC.registrar_tela_cega = _registrar
    AC.attendance_agent_active = _agente_ligado
    PT.POLL_EVERY_S = 0


_ATUAL = {"banco": None}


def _acionar(company_id: str, resultado_do_job: dict) -> tuple:
    banco = BancoDeMentira(resultado_do_job)
    _ATUAL["banco"] = banco
    TELAS_CEGAS.clear()
    ferramenta = PortalDeMentira(company_id=company_id, supabase_client=banco)
    saida = asyncio.run(ferramenta._arun(**dict(PEDIDO), session_id=SESSAO))
    return banco, saida


# ==========================================================================
def a_chave_de_idempotencia_chega_ao_params() -> None:
    print("\n[_idempotency_key] lida desde sempre, escrita a partir de agora")

    banco, _ = _acionar(EMPRESA_A, {"status": "needs_human", "error": None,
                                    "evidence": {"message": "parou no 80%"}})
    checar(len(banco.jobs) == 1, "o job nasceu", len(banco.jobs))
    job = banco.jobs[0]
    checar("_idempotency_key" in (job.get("params") or {}),
           "📊 `params['_idempotency_key']` existe — antes era lida e nunca escrita "
           "(vidros_apifirst.py:231)", str(sorted((job.get('params') or {}))))
    checar(job["params"]["_idempotency_key"] == job["idempotency_key"],
           "e e a MESMA chave do dedup do job — um conceito so de 'mesmo pedido'",
           f"{job['params'].get('_idempotency_key')} != {job.get('idempotency_key')}")
    checar(job["params"]["_idempotency_key"].startswith("v2:" + EMPRESA_A),
           "e ela comeca pela corretora, como manda `chave_de_idempotencia`",
           job["params"]["_idempotency_key"])


def o_acionamento_vira_work_run() -> None:
    print("\n[P-PILOTO-02] o acionamento aparece na Fila e na Ficha")

    banco, _ = _acionar(EMPRESA_A, {"status": "done", "error": None,
                                    "evidence": {"desfecho": DESFECHO_CONHECIDO}})
    checar(len(banco.work_runs) == 1, "um work_run nasceu", len(banco.work_runs))
    if not banco.work_runs:
        return
    run = banco.work_runs[0]
    job = banco.jobs[0]

    checar(job.get("work_run_id") == run["id"],
           "e o `portal_jobs.work_run_id` aponta para ele — a coluna que nunca teve "
           "escritor", f"{job.get('work_run_id')} != {run['id']}")
    checar(job.get("agent_id") == AGENTE_A,
           "e o `agent_id` da corretora tambem foi gravado", job.get("agent_id"))
    checar(run["source_type"] == "portal",
           "o run diz que veio do PORTAL (source_type)", run.get("source_type"))
    checar(run["outcome_type"] == PT.OUTCOME_ACIONAMENTO,
           "com o MESMO outcome do acionamento por WhatsApp — um resultado de negocio",
           run.get("outcome_type"))
    checar(run["risk_level"] == "high",
           "e risco ALTO: do outro lado esta a seguradora de verdade")
    checar(run["conversation_id"] == CONVERSA_A,
           "e a conversa foi PROVADA a partir da sessao", run.get("conversation_id"))
    checar(run["thread_id"] == f"work:{EMPRESA_A}:{run['id']}",
           "e o thread_id segue o CHECK do banco", run.get("thread_id"))

    # 🔴 PII: o payload do run e lido por tela de operacao e por relatorio.
    payload = run.get("input_payload") or {}
    for proibido in ("52998224725", "48900000000", "segurado@exemplo.test",
                     "Segurado Exemplo", "Rua Exemplo"):
        checar(proibido not in str(payload),
               f"e o payload NAO carrega '{proibido[:14]}…' (PII fora do relatorio)",
               str(payload))
    checar(payload.get("placa") == "AAA0A91" and payload.get("peca") == "vidro de porta",
           "CONTROLE: mas ele identifica o pedido (placa + peca)", str(payload))

    # O desfecho fecha o run, e o numero do atendimento fica DURAVEL nele.
    concluidos = [u for u in banco.updates_de_run
                  if u["patch"].get("status") == "completed"]
    checar(len(concluidos) == 1, "o run foi CONCLUIDO quando o desfecho chegou",
           str(banco.updates_de_run)[:300])
    if concluidos:
        resultado = concluidos[0]["patch"].get("result_payload") or {}
        checar(resultado.get("numero_do_atendimento") == "99999999",
               "e o numero do atendimento ficou guardado NO RUN (nao so no evidence)",
               str(resultado))
        checar(resultado.get("desfecho") == "loja_direta",
               "junto com o tipo de desfecho, para a Ficha saber a fase", str(resultado))


def dois_tenants_nao_se_cruzam() -> None:
    print("\n[§7] a corretora B, com a MESMA sessao e o MESMO pedido")

    banco_a, _ = _acionar(EMPRESA_A, {"status": "done", "error": None,
                                      "evidence": {"desfecho": DESFECHO_CONHECIDO}})
    banco_b, _ = _acionar(EMPRESA_B, {"status": "done", "error": None,
                                      "evidence": {"desfecho": DESFECHO_CONHECIDO}})

    run_a, run_b = banco_a.work_runs[0], banco_b.work_runs[0]
    checar(run_a["company_id"] == EMPRESA_A and run_b["company_id"] == EMPRESA_B,
           "cada run nasce na SUA corretora",
           f"{run_a['company_id']} / {run_b['company_id']}")
    checar(run_a["conversation_id"] == CONVERSA_A,
           "o run de A aponta para a conversa de A", run_a.get("conversation_id"))
    checar(run_b["conversation_id"] == CONVERSA_B,
           "🔴 e o de B para a de B — a MESMA `session_id` existe nas duas casas",
           run_b.get("conversation_id"))
    checar(run_a["conversation_id"] != run_b["conversation_id"],
           "CONTROLE: as duas conversas sao DIFERENTES",
           "com a mesma conversa nos dois runs, o bloco acima nao provaria nada")
    checar(banco_a.jobs[0]["agent_id"] == AGENTE_A
           and banco_b.jobs[0]["agent_id"] == AGENTE_B,
           "e o agente atendente tambem e o da propria corretora")

    # Toda atualizacao de job feita pela tool filtra por corretora.
    for banco, empresa in ((banco_a, EMPRESA_A), (banco_b, EMPRESA_B)):
        com_filtro = [u for u in banco.updates_de_job
                      if u["filtros"].get("company_id") in (empresa, None)]
        checar(len(com_filtro) == len(banco.updates_de_job),
               f"nenhum UPDATE de job escapou para outra corretora ({empresa[:8]}…)",
               str(banco.updates_de_job)[:200])


def g9_a_parada_desconhecida_vira_fila() -> None:
    print("\n[G9] parada desconhecida: dossie + mensagem honesta + 1 linha na fila")

    banco, saida = _acionar(EMPRESA_A, {
        "status": "needs_human", "error": None,
        "evidence": {"stage": "tela_desconhecida", **EVIDENCIA_DESCONHECIDA}})

    checar(len(TELAS_CEGAS) == 1,
           "UMA chamada a registrar_tela_cega — nem zero, nem duas", len(TELAS_CEGAS))
    if TELAS_CEGAS:
        linha = TELAS_CEGAS[0]
        checar(linha["company_id"] == EMPRESA_A,
               "com o company_id CERTO — a fila de aprendizado e por corretora",
               linha.get("company_id"))
        checar(linha["ramo"] == "vidros", "ramo 'vidros'", linha.get("ramo"))
        checar(linha["insurer_key"] == "yelum",
               "e a seguradora sai do DADO do job, nao de uma lista fixa",
               linha.get("insurer_key"))
        checar(linha["playbook_ref"] == "portal:vidros_lanternas:opcoes-disponiveis",
               "e o playbook_ref diz ONDE o robo parou", linha.get("playbook_ref"))
        checar("Tela nova do portal" in linha["texto"],
               "com o texto ja mascarado pela origem", linha.get("texto"))
        for proibido in ("52998224725", "48900000000", "AAA0A91"):
            checar(proibido not in str(linha),
                   f"e sem PII na linha da fila ('{proibido[:8]}…')", str(linha)[:200])

    # A mensagem ao agente: pergunta honesta + dossie, nunca silencio.
    conteudo = str(saida.get("content") or "")
    checar("não conheço" in conteudo, "o segurado ouve a verdade, sem jargao", conteudo[:250])
    checar("para a equipe" in conteudo, "e a equipe recebe o dossie", conteudo[:400])

    # A marca fica no job, para a proxima varredura nao repetir.
    marcas = [u for u in banco.updates_de_job
              if (u["patch"].get("evidence") or {}).get("tela_cega_registrada")]
    checar(len(marcas) == 1, "e o job fica MARCADO (uma linha por job)", len(marcas))

    # ------------------------------------------------------------------
    # 🔴 O PAR DE CONTROLE. Sem ele, um `registrar_tela_cega` chamado sempre
    # passaria em tudo acima — e a fila de trabalho viraria log de sucesso.
    # ------------------------------------------------------------------
    _acionar(EMPRESA_B, {"status": "done", "error": None,
                         "evidence": {"desfecho": DESFECHO_CONHECIDO}})
    checar(TELAS_CEGAS == [],
           "CONTROLE: parada CONHECIDA (loja_direta) ⇒ ZERO chamadas",
           str(TELAS_CEGAS)[:200])


def o_espelho_nunca_derruba_o_acionamento() -> None:
    print("\n[fail-safe] perder o espelho nao pode custar o atendimento")

    import app.core.database as DB

    antes = DB.create_async_supabase_client

    async def _explode():
        raise RuntimeError("banco de work_runs fora do ar")

    try:
        DB.create_async_supabase_client = _explode
        banco, saida = _acionar(EMPRESA_A, {"status": "done", "error": None,
                                            "evidence": {"desfecho": DESFECHO_CONHECIDO}})
    finally:
        DB.create_async_supabase_client = antes

    checar(len(banco.jobs) == 1,
           "o acionamento acontece mesmo sem o espelho durável", len(banco.jobs))
    checar(banco.jobs[0].get("work_run_id") is None,
           "o job nasce com work_run_id NULO, e isso e a verdade",
           banco.jobs[0].get("work_run_id"))
    checar("99999999" in str(saida.get("content") or ""),
           "e o segurado recebe o numero do atendimento assim mesmo",
           str(saida.get("content"))[:200])

    # 🔴 CONTROLE: com o banco de pe, o espelho VOLTA. Sem esta linha, um
    # `_garantir_work_run` que sempre devolvesse None passaria acima.
    banco2, _ = _acionar(EMPRESA_A, {"status": "done", "error": None,
                                     "evidence": {"desfecho": DESFECHO_CONHECIDO}})
    checar(banco2.jobs[0].get("work_run_id"),
           "CONTROLE: com o banco de pe, o work_run volta a nascer",
           banco2.jobs[0].get("work_run_id"))


if __name__ == "__main__":
    print("=" * 72)
    print("P-PILOTO-02 · P-PILOTO-08 — o acionamento existe para quem olha")
    print("=" * 72)
    _preparar_ambiente()
    a_chave_de_idempotencia_chega_ao_params()
    o_acionamento_vira_work_run()
    dois_tenants_nao_se_cruzam()
    g9_a_parada_desconhecida_vira_fila()
    o_espelho_nunca_derruba_o_acionamento()
    print("\n" + "=" * 72)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
    print("=" * 72)
    sys.exit(1 if FAIL else 0)
