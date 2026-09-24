# -*- coding: utf-8 -*-
"""C4 — o vigia RELÊ uma parada técnica: uma vez, só com a sessão jovem, nunca
sobre `maybe_committed`.

SPEC-EXTRA-001.10.1 C4. Roda `vigia_do_portal.varrer_portal` DE VERDADE sobre um
dublê do Supabase; o escritor da continuação é o MESMO da tool
(`portal_tool.enfileirar_continuacao` + `portal_params.montar_job_de_continuacao`).

## 🔴 O que está em jogo

📊 O token do portal EXPIRA (21/09 22:09 UTC → 401 em 23/09 23:40 UTC). Uma
parada técnica depois do protocolo (`patch_recusado`, `roteador_ilegivel`…) não
tem nada a perguntar ao segurado — a releitura pelo estado real resolve, SE sair
cedo. Três jeitos de errar, um por bloco:

```
jovem   => UMA continuação "reler" (e o job de origem marcado)
velho   => nenhuma (a sessão provavelmente morreu; quem conclui é a equipe)
2a volta=> nenhuma nova (uma vez por job, nunca releitura de releitura)
maybe_committed => nenhuma (reconciliação, não nova tentativa)
```
"""
from __future__ import annotations

import asyncio
import copy
import os
import sys
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

for _var in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY",
             "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"):
    os.environ.pop(_var, None)
ALCANCOU_O_REAL: list = []
try:
    import supabase as _supabase_pkg  # noqa: E402

    def _armadilha(*_a, **_k):
        ALCANCOU_O_REAL.append("supabase.create_client")
        raise RuntimeError("TESTE: cliente Supabase REAL alcancado — proibido")

    _supabase_pkg.create_client = _armadilha
except Exception:  # noqa: BLE001
    pass

from app.tasks import vigia_do_portal as VIGIA  # noqa: E402

PASS = FAIL = 0


def checar(cond, nome, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok]     " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  << " + str(extra)[:400] if extra else ""))


EMPRESA_A = "aaaaaaaa-0000-4000-8000-000000000001"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-000000000002"
TOKEN_FALSO = "TOKEN-CIFRADO-DE-TESTE-9f8e7d"
AGORA = datetime.now(timezone.utc)


def _job(jid: str, company: str, *, idade_min: int, stage: str = "patch_recusado",
         reconciliar: bool = False, possivel: bool = True) -> dict:
    return {
        "id": jid, "company_id": company, "portal_key": "vidros_lanternas",
        "journey": "abrir_atendimento", "status": "needs_human",
        "session_id": "whatsapp:5548900000000:co:ag", "agent_id": "agente-x",
        "work_run_id": f"run-{jid}", "idempotency_key": f"v2:{company}:AAA0A91:05072026:porta vidro",
        "created_at": (AGORA - timedelta(minutes=idade_min)).isoformat(),
        "params": {"cpf_cnpj": "52998224725", "placa": "AAA0A91",
                   "dano": {"peca": "vidro de porta"}, "confirm": True},
        "evidence": {
            "stage": stage, "protocolo": "1234567890123456",
            "entregue_ao_agente": True,
            "vidros_estado": {"precisa_reconciliar": reconciliar},
            "continuacao": {"possivel": possivel, "acao_esperada": "reler",
                            "emitida_em": (AGORA - timedelta(minutes=idade_min)).isoformat(),
                            "sessao_guardada": True, "sessao_cifrada": TOKEN_FALSO},
        },
    }


class _R:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.f, self.op, self.linha = banco, tabela, {}, "select", {}

    def select(self, *_a, **_k):
        return self

    def insert(self, linha):
        self.op, self.linha = "insert", copy.deepcopy(dict(linha))
        return self

    def update(self, patch):
        self.op, self.linha = "update", copy.deepcopy(dict(patch))
        return self

    def eq(self, k, v):
        self.f[k] = v
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        return self.banco.executar(self)


class Banco:
    def __init__(self, jobs):
        self.jobs = [copy.deepcopy(j) for j in jobs]
        self.updates: list = []

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Q(self, nome)

    def executar(self, q):
        if q.tabela != "portal_jobs":
            return _R([])
        f = q.f
        if q.op == "insert":
            chave = q.linha.get("idempotency_key")
            if chave and any(j.get("company_id") == q.linha.get("company_id")
                             and j.get("idempotency_key") == chave
                             and j.get("status") != "failed" for j in self.jobs):
                raise RuntimeError("duplicate key 23505")
            linha = {**q.linha, "id": f"cont-{len(self.jobs)}",
                     "created_at": AGORA.isoformat()}
            self.jobs.append(linha)
            return _R([{"id": linha["id"]}])
        if q.op == "update":
            self.updates.append({"f": dict(f), "patch": q.linha})
            for j in self.jobs:
                if all(j.get(k) == v for k, v in f.items()):
                    j.update(q.linha)
            return _R([])
        achados = [j for j in self.jobs if all(j.get(k) == v for k, v in f.items())]
        return _R([copy.deepcopy(j) for j in achados])


ENVIADAS: list = []
ALERTAS: list = []


def _preparar(banco):
    import app.core.database as DB
    import app.services.atlas.attendance_capture as AC
    import app.services.integration_service as IS
    import app.services.whatsapp_service as WS
    import app.tasks.dispatch_watchdog as DW

    class _WA:
        def send_message(self, tel, texto, integ):
            ENVIADAS.append(texto)

    class _IS:
        def get_platform_whatsapp_integration(self, _c):
            return {"id": "integ"}

    async def _agente(_c):
        return True

    async def _alerta(company_id, texto, wa, integ):
        ALERTAS.append((company_id, texto))

    DB.get_supabase_client = lambda: banco
    WS.get_whatsapp_service = lambda: _WA()
    IS.get_integration_service = lambda: _IS()
    AC.attendance_agent_active = _agente
    DW._support_alert = _alerta


def _releituras(banco):
    return [j for j in banco.jobs if j.get("journey") == "continuar_atendimento"]


def pedir_releitura_puro() -> None:
    print("\n[C4-puro] quem decide e uma funcao pura")
    checar(VIGIA.pedir_releitura(_job("j", EMPRESA_A, idade_min=5), AGORA),
           "tecnico + possivel + sessao de 5 min => RELE")
    checar(not VIGIA.pedir_releitura(_job("j", EMPRESA_A, idade_min=40), AGORA),
           "sessao de 40 min (> 30) => NAO rele")
    checar(not VIGIA.pedir_releitura(_job("j", EMPRESA_A, idade_min=5, reconciliar=True), AGORA),
           "🔴 maybe_committed (precisa_reconciliar) => NAO rele")
    checar(not VIGIA.pedir_releitura(_job("j", EMPRESA_A, idade_min=5, stage="cidade_sem_rede"), AGORA),
           "parada do SEGURADO (cidade_sem_rede) => NAO rele (ela espera a resposta dele)")
    checar(not VIGIA.pedir_releitura(_job("j", EMPRESA_A, idade_min=5, possivel=False), AGORA),
           "sem a prova da journey (possivel False) => NAO rele")
    reler_de_reler = _job("j", EMPRESA_A, idade_min=5)
    reler_de_reler["params"]["_continuacao"] = {"operacao": "reler"}
    checar(not VIGIA.pedir_releitura(reler_de_reler, AGORA),
           "releitura de releitura => NAO (sem laco de jobs)")


def varredura() -> None:
    print("\n[C4-varredura] jovem => 1 releitura; velho => 0; 2a volta => 0")
    jovem = _job("jovem", EMPRESA_A, idade_min=5)
    velho = _job("velho", EMPRESA_B, idade_min=40)
    incerto = _job("incerto", EMPRESA_A, idade_min=5, reconciliar=True)
    banco = Banco([jovem, velho, incerto])
    _preparar(banco)
    ENVIADAS.clear()
    ALERTAS.clear()
    asyncio.run(VIGIA.varrer_portal())

    rel = _releituras(banco)
    checar(len(rel) == 1, "UMA continuacao 'reler' nasceu", len(rel))
    if rel:
        r = rel[0]
        c = r["params"].get("_continuacao") or {}
        checar(c.get("operacao") == "reler" and c.get("job_origem") == "jovem",
               "operacao 'reler', do job jovem", c)
        checar(r["company_id"] == EMPRESA_A and r["journey"] == "continuar_atendimento",
               "na corretora do job de origem", r["company_id"])
        checar(str(r.get("idempotency_key") or "").startswith("cont:"),
               "com chave de continuacao", r.get("idempotency_key"))
        checar(c.get("sessao", {}).get("sessao_cifrada") == TOKEN_FALSO,
               "a sessao vai inteira (cifrada), sem ser lida")
        checar(r.get("work_run_id") == "run-jovem", "e atualiza o MESMO run do pedido")
    origem = [j for j in banco.jobs if j["id"] == "jovem"][0]
    checar(origem["evidence"].get("releitura_pedida_em"),
           "o job de origem ficou MARCADO (uma vez por job)")
    checar(origem["evidence"].get("entregue_ao_agente") is True
           and origem["evidence"].get("continuacao", {}).get("possivel") is True,
           "e a marca foi FUNDIDA na evidence (nada do que havia se perdeu)")
    checar(all(u["f"].get("company_id") for u in banco.updates),
           "todo UPDATE do vigia filtra company_id", banco.updates[-1:])
    checar(not [j for j in _releituras(banco) if (j["params"]["_continuacao"] or {})
                .get("job_origem") == "velho"],
           "o VELHO (40 min) nao ganhou releitura")
    checar(not [j for j in _releituras(banco) if (j["params"]["_continuacao"] or {})
                .get("job_origem") == "incerto"],
           "🔴 o maybe_committed nao ganhou releitura")
    checar(any(c == EMPRESA_B and "nao pode ser relida" in t for c, t in ALERTAS),
           "e a EQUIPE da corretora B e avisada de que a releitura nao sai "
           "(o segurado ouviu 'tentando de novo')", [c[:8] for c, _t in ALERTAS])
    checar(all(str(t).strip() for t in ENVIADAS),
           "nenhuma mensagem VAZIA saiu ao segurado", ENVIADAS)
    checar(TOKEN_FALSO not in " ".join(ENVIADAS) + " ".join(t for _c, t in ALERTAS),
           "🔴 G6: o token nao aparece em mensagem nem alerta")

    asyncio.run(VIGIA.varrer_portal())
    checar(len(_releituras(banco)) == 1,
           "2a varredura: NENHUMA releitura nova", len(_releituras(banco)))
    checar(not ALCANCOU_O_REAL, "P-E00110-A17: o cliente real nunca foi alcancado", ALCANCOU_O_REAL)


def a_equipe_sabe_do_401() -> None:
    print("\n[C4-401] sessao_expirada entregue ao segurado => a EQUIPE e avisada")
    job = _job("expirou", EMPRESA_A, idade_min=5, stage="sessao_expirada", possivel=False)
    job["journey"] = "continuar_atendimento"
    achado = VIGIA.diagnosticar(job, AGORA)
    checar(achado and achado["para_o_segurado"] == "" and "EQUIPE" in achado["para_o_suporte"],
           "so a equipe recebe, com o dossie", achado)
    agenda_cont = _job("ag", EMPRESA_A, idade_min=5)
    agenda_cont.update({"status": "done"})
    agenda_cont["evidence"].update({"stage": "", "desfecho": {"tipo": "agenda"},
                                    "continuacao": {"possivel": True, "acao_esperada": "agendar"}})
    checar(VIGIA.diagnosticar(agenda_cont, AGORA) is None,
           "agenda COM continuacao, ja entregue => o robo fecha; a equipe NAO e chamada")
    agenda_cont["evidence"]["continuacao"] = {"possivel": False}
    ctl = VIGIA.diagnosticar(agenda_cont, AGORA)
    checar(ctl and "EQUIPE PRECISA CONCLUIR" in ctl["para_o_suporte"],
           "CONTROLE: SEM continuacao, a equipe continua sendo chamada", ctl)


if __name__ == "__main__":
    print("=" * 72)
    print("C4 — o vigia rele a parada tecnica, uma vez e cedo")
    print("=" * 72)
    pedir_releitura_puro()
    varredura()
    a_equipe_sabe_do_401()
    print("\n" + "=" * 72)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
    print("=" * 72)
    sys.exit(1 if FAIL else 0)
