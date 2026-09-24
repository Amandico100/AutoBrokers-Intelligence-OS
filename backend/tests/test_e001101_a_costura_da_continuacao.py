# -*- coding: utf-8 -*-
"""🔴 A COSTURA da EXTRA-001.10.1 — a saída REAL de uma fatia é a entrada da outra.

Protocolo AAA v13 §5.2: fatias paralelas (A = journeys do portal · C = tool,
coleta, mensagens) → UMA fatia de costura. Os testes de cada fatia provam o seu
lado com um dublê do OUTRO lado; aqui não há dublê no meio.

O fio que este arquivo atravessa, sem nenhuma peça trocada entre as pontas
=========================================================================
    payload do agente (flat, como a tool recebe)
      → `PortalActionTool._arun` REAL → `build_portal_params` REAL
      → linha em `portal_jobs` (dublê em memória, jsonb serializado de verdade)
      → "worker de costura": `motivo_para_barrar` + `get_journey` (registro REAL)
        + `montar_runtime` (guard REAL, checkpoint no dublê) → a journey REAL
        (`vidros_lanternas.abrir_atendimento` → `abrir_atendimento_api`, ou
        `vidros_continuacao.continuar_atendimento`) → o fechamento do worker
        (`_augment_hitl_evidence`, `_redigir`) → a linha volta ao dublê
      → o poll REAL da tool → `format_result` / `mensagem_do_desfecho` REAIS
    a resposta do segurado
      → `_arun` de novo → `_continuar_ou_explicar` → `mapear_escolha_de_agenda` /
        `respostas_da_chamada` → `montar_job_de_continuacao` →
        `enfileirar_continuacao` → o mesmo worker → a mensagem final.

Dublês, e só eles (a BORDA):
  · a página do portal: `_replay_vidros.PaginaDeReplay` sobre os HAR reais
    LATERAL / LATARIA2 (o que o portal respondeu de verdade);
  · o cliente Supabase: `BancoDeMentira` em memória, com o índice único parcial
    `idx_portal_jobs_pedido_vivo`. ⛔ P-E00110-A17: `supabase.create_client`
    vira armadilha — alcançar o banco REAL deixa o placar VERMELHO;
  · a InfoCap (DERIVADA do HAR em memória: nenhum valor pessoal digitado nem
    impresso), o WhatsApp (`_notify` só anota), o interruptor do agente (True),
    a fila de aprendizado e o relógio do motor (`AF.hoje` = dia da captura).

⛔ PII: CPF, placa, telefone, e-mail, nome, apólice e token dos HAR só vivem em
memória. Toda saída passa por `_limpo`, que troca esses valores (e qualquer
número de 4+ dígitos) por marcadores. Sem os HAR (intake fora do Git): SKIP.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import re
import sys
import threading
from datetime import date
from pathlib import Path

# 🔴 RED P5 (conserto da 001.10.1): o teste não pode depender de quem o chama
# ter posto PYTHONIOENCODING — no Windows (cp1252) o 1º emoji do `print`
# derrubava o teste no meio (📊 UnicodeEncodeError na linha 668).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

# ---- o ambiente DESTE processo (nada de .env, nada de painel) -------------
for _var in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY",
             "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY",
             "PORTAL_CANARIO_ALLOWLIST", "ACIONAMENTO_FREIO_DE_EMERGENCIA"):
    os.environ.pop(_var, None)
from cryptography.fernet import Fernet  # noqa: E402

os.environ["PORTAL_VAULT_KEY"] = Fernet.generate_key().decode()
os.environ["PORTAL_VIDROS_API_FIRST"] = "1"
os.environ["PORTAL_EFEITO_MATERIAL_LIBERADO"] = "1"

ALCANCOU_O_REAL: list = []
try:
    import supabase as _supabase_pkg  # noqa: E402

    def _armadilha(*_a, **_k):
        ALCANCOU_O_REAL.append("supabase.create_client")
        raise RuntimeError("TESTE: cliente Supabase REAL alcancado — proibido")

    _supabase_pkg.create_client = _armadilha
except Exception:  # noqa: BLE001
    pass

import _replay_vidros as RV                                   # noqa: E402
from portal_worker import worker as W                         # noqa: E402
from portal_worker import vault                               # noqa: E402
from portal_worker.journeys import cpf_hash_de, get_journey, motivo_para_barrar  # noqa: E402
from portal_worker.journeys import vidros_api as API          # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF      # noqa: E402
from portal_worker.journeys import vidros_estado as ST        # noqa: E402
from portal_worker.runtime import montar_runtime              # noqa: E402

from app.agents.tools import portal_params as PP              # noqa: E402
from app.agents.tools import portal_tool as PT                # noqa: E402

PASS = FAIL = 0
PII: set = set()


def _limpo(x) -> str:
    """⛔ Nenhum dado pessoal na saída: os valores do HAR viram {pii}."""
    txt = str(x)
    for v in sorted(PII, key=len, reverse=True):
        if v and len(v) >= 4:
            txt = txt.replace(v, "{pii}")
    txt = re.sub(r"\S+@\S+", "{email}", txt)
    return re.sub(r"[0-9a-fA-F-]{16,}|\d{4,}", "{n}", txt)


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  << " + _limpo(extra)[:400] if extra != "" else ""))


# 📊 O relógio da captura: LATERAL e LATARIA são de 21/09/2026.
AF.hoje = lambda: date(2026, 9, 21)

# ==========================================================================
# O banco de mentira — `portal_jobs` com o índice único parcial de verdade
# ==========================================================================
EMPRESA_A = "aaaaaaaa-0000-4000-8000-00000000000a"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-00000000000b"
SESSAO_A = "whatsapp:5548900000001:co:ag"
SESSAO_B = "whatsapp:5548900000002:co:ag"
# 💭 perfis fictícios (CLAUDE.md §13.9): nenhum nome de corretora real.
PERFIS = {
    EMPRESA_A: {"company_name": "Corretora Alfa Exemplo", "legal_name": "Alfa Exemplo LTDA",
                "primary_contact_name": "Operacao Alfa", "primary_contact_email": "alfa@exemplo.test",
                "primary_contact_phone": "4830000001", "cnpj": "00000000000191",
                "acionamento_profile": None},
    EMPRESA_B: {"company_name": "Corretora Beta Exemplo", "legal_name": "Beta Exemplo LTDA",
                "primary_contact_name": "Operacao Beta", "primary_contact_email": "beta@exemplo.test",
                "primary_contact_phone": "4830000002", "cnpj": "11111111000191",
                "acionamento_profile": None},
}


class _Resp:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.dif, self.op, self.linha = {}, {}, "select", {}

    def select(self, *_a, **_k):
        return self

    def insert(self, linha):
        self.op, self.linha = "insert", linha
        return self

    def update(self, patch):
        self.op, self.linha = "update", patch
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def neq(self, campo, valor):
        self.dif[campo] = valor
        return self

    def __getattr__(self, nome):          # order/limit/in_/is_… não filtram aqui
        if nome.startswith("_"):
            raise AttributeError(nome)
        return lambda *a, **k: self

    def execute(self):
        return self.banco.executar(self)


def _jsonb(x):
    """O que o PostgREST faria: serializar. Não serializável = defeito de costura."""
    return json.loads(json.dumps(x))


def _campo(linha, chave):
    if chave.startswith("params->>"):
        return str((linha.get("params") or {}).get(chave.split(">>", 1)[1]) or "")
    return linha.get(chave)


class BancoDeMentira:
    def __init__(self):
        self.tabelas: dict = {"portal_jobs": [], "work_runs": []}
        self.paginas: list = []          # a página do portal de cada job, na ordem
        self.erros_do_worker: list = []
        self.jobs_executados: list = []

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Q(self, nome)

    def jobs(self, **f):
        return [j for j in self.tabelas["portal_jobs"]
                if all(_campo(j, k) == v for k, v in f.items())]

    def executar(self, q: _Q):
        if q.tabela == "companies":
            return _Resp([dict(PERFIS[q.filtros["id"]])] if q.filtros.get("id") in PERFIS else [])
        if q.tabela == "agents":
            return _Resp([{"id": "agente-" + str(q.filtros.get("company_id"))[:8]}])
        linhas = self.tabelas.setdefault(q.tabela, [])
        if q.op == "insert":
            linha = _jsonb(q.linha)
            if q.tabela == "portal_jobs":
                chave = linha.get("idempotency_key")
                if chave and any(j["company_id"] == linha["company_id"]
                                 and j.get("idempotency_key") == chave
                                 and j.get("status") != "failed" for j in linhas):
                    raise RuntimeError("duplicate key value violates unique constraint "
                                       "idx_portal_jobs_pedido_vivo (23505)")
                linha.setdefault("id", f"job-{len(linhas) + 1}")
                linha["created_at"] = f"2026-09-21T10:{len(linhas):02d}:00Z"
                linha.setdefault("evidence", {})
            linha.setdefault("id", f"{q.tabela}-{len(linhas) + 1}")
            linhas.append(linha)
            return _Resp([copy.deepcopy(linha)])
        achados = [j for j in linhas if all(_campo(j, k) == v for k, v in q.filtros.items())
                   and all(_campo(j, k) != v for k, v in q.dif.items())]
        if q.op == "update":
            for j in achados:
                j.update(_jsonb(q.linha))
            return _Resp([])
        if q.tabela == "portal_jobs" and "id" in q.filtros:
            for j in achados:
                if j.get("status") == "queued":
                    self._worker(j)
        achados = sorted(achados, key=lambda j: j.get("created_at", ""), reverse=True)
        return _Resp([copy.deepcopy(j) for j in achados])

    # ---- o worker de costura: o `_run_job` sem Playwright ------------------
    def _worker(self, job: dict) -> None:
        """A mesma ordem do `worker._run_job`: freio por job → journey do
        registro → runtime (guard REAL) → journey → fechamento → `_redigir`."""
        self.jobs_executados.append(job["id"])
        pk, jn = str(job.get("portal_key")), str(job.get("journey"))
        barrado = motivo_para_barrar(pk, jn, job_id=str(job["id"]), cpf_hash=cpf_hash_de(
            str((job.get("params") or {}).get("cpf_cnpj") or "")))
        if barrado:
            job.update({"status": "failed", "error": "barrado: " + barrado})
            return
        fn = get_journey(pk, jn)
        if fn is None or not self.paginas:
            self.erros_do_worker.append(("sem journey ou sem pagina", pk, jn))
            job.update({"status": "failed", "error": "costura: sem journey/pagina"})
            return
        page = self.paginas.pop(0)
        params = copy.deepcopy(job.get("params") or {})
        evidence = dict(job.get("evidence") or {})

        async def _checkpoint(patch):
            job["evidence"] = _jsonb(W._redigir({**evidence, **(patch or {})}))

        runtime = montar_runtime(job, evidence=evidence, checkpoint=_checkpoint,
                                 host_portal=RV.HOST_PORTAL)
        params.update({"_runtime": runtime, "_job_id": str(job["id"]),
                       "_company_id": str(job.get("company_id") or ""), "_portal_key": pk})
        saida: dict = {}

        def _corre():
            try:
                saida["r"] = asyncio.run(fn(page, params, evidence))
            except Exception as exc:  # noqa: BLE001
                saida["e"] = exc

        t = threading.Thread(target=_corre)
        t.start()
        t.join()
        if "e" in saida:
            self.erros_do_worker.append((pk, jn, type(saida["e"]).__name__, str(saida["e"])[:200]))
            job.update({"status": "failed", "error": type(saida["e"]).__name__})
            return
        r = saida["r"]
        evidence.update(runtime.selar_evidencia())
        final = (W._augment_hitl_evidence(r, evidence) if r.status == "needs_human"
                 else {**evidence, **(r.captured or {}), "message": r.message})
        W.decidir_session_reused(final, r.status)
        final["resumo"] = W.resumo_do_desfecho(r.status, final)
        job.update({"status": r.status, "evidence": _jsonb(W._redigir(final))})
        job["_pagina"] = id(page)          # só o teste lê: qual portal este job viu
        PAGINAS[id(page)] = page


PAGINAS: dict = {}
NOTIFICACOES: list = []


class Ferramenta(PT.PortalActionTool):
    """Só as BORDAS trocadas: InfoCap (derivada do HAR) e WhatsApp."""

    infocap: object = None

    async def _fetch_infocap(self, cpf, policy_number):  # noqa: D102
        return copy.deepcopy(self.infocap)

    def _notify(self, session_id, text, agent_id=None):  # noqa: D102
        NOTIFICACOES.append(text)


def _preparar_ambiente(banco_ref: dict) -> None:
    import app.core.database as DB
    import app.services.atlas.attendance_capture as AC
    import app.services.tela_cega as TC

    async def _cliente_async():
        return banco_ref["banco"]

    async def _registrar(**_k):
        return True

    async def _agente_ligado(_c):
        return True

    DB.create_async_supabase_client = _cliente_async
    DB.get_supabase_client = lambda: banco_ref["banco"]
    TC.registrar_tela_cega = _registrar
    AC.attendance_agent_active = _agente_ligado
    PT.POLL_EVERY_S = 0


BANCO = {"banco": None}
_preparar_ambiente(BANCO)


# ==========================================================================
# O agente: o payload que ELE mandaria, e a InfoCap que o provedor devolveria
# ==========================================================================
def agente_e_infocap(chamadas, *, peca, como, onde, especificos, cidade=None):
    """(flat, infocap) — DERIVADOS do HAR em memória. O flat é o que o LLM
    manda na tool (palavras de gente); a InfoCap é o que o provedor devolve."""
    ab = RV.primeira(chamadas, "POST", "/atendimentos", requisicao=True) or {}
    patch = RV.primeira(chamadas, "PATCH", "/atendimentos", requisicao=True) or {}
    sol = RV.primeira(chamadas, "POST", "/solicitantes", requisicao=True) or {}
    segs = RV.primeira(chamadas, "GET", "/seguradoras/") or []
    cidades = RV.primeira(chamadas, "GET", "/cidades") or []
    nome_seg = [s.get("Nome") for s in API._itens_de_seguradora(segs)
                if API._slug_do_item(s) == ab.get("Seguradora")][0]
    cid = [c for c in cidades if c.get("Codigo") == patch.get("CodigoCidade")][0]
    tel = str(((sol.get("Telefones") or [{}])[0]).get("Numero") or "")
    iso = str(ab.get("DataSinistro") or "")[:10]
    for v in (ab.get("CpfCnpjSegurado"), ab.get("PlacaInformada"), tel,
              sol.get("EmailSegurado"), sol.get("NomeSolicitante"), sol.get("EmailTitularAplice")):
        if v:
            PII.add(str(v))
    info = {"ok": True,
            "policy": {"numapo": "000000", "seguradora": nome_seg},
            "vehicle": {"placa": str(ab.get("PlacaInformada") or ""), "veiculo": "VEICULO EXEMPLO",
                        "chassi": ""},
            "client": {"nome": "Segurado Exemplo", "cep": str(patch.get("Cep") or ""),
                       "cidade": cid["Nome"], "estado": cid["UF"], "telefone": tel,
                       "email": str(sol.get("EmailSegurado") or "")}}
    flat = {"cpf_cnpj": str(ab.get("CpfCnpjSegurado") or ""),
            "data_dano": "/".join(reversed(iso.split("-"))),
            "peca": peca, "como_ocorreu": como, "onde_ocorreu": onde,
            "descricao": "o carro estava estacionado na rua e amanheceu com o dano",
            "especificos": {"cidade_para_o_servico": cidade or f"{cid['Nome']}/{cid['UF']}",
                            **especificos}}
    return flat, info, {"uf": cid["UF"], "cidade": cid["Nome"]}


def chamar(banco, empresa, sessao, flat, info, pagina=None):
    """UMA chamada do agente à tool. `pagina` = o portal que o worker vai ver."""
    BANCO["banco"] = banco
    if pagina is not None:
        banco.paginas.append(pagina)
    NOTIFICACOES.clear()
    f = Ferramenta(company_id=empresa, supabase_client=banco)
    f.infocap = info
    saida = asyncio.run(f._arun(**copy.deepcopy(flat), session_id=sessao))
    return str(saida.get("content") or "")


def cursor_antes(chamadas, metodo, caminho):
    """A página "já viveu" o HAR até o último `GET /atendimentos` antes de
    (metodo, caminho): é onde o pedido está quando a continuação o retoma."""
    i_alvo = RV.indice(chamadas, metodo, caminho)
    return max(i for i in range(i_alvo)
               if RV._chave(chamadas[i].metodo, RV.caminho_de(chamadas[i]))
               == ("GET", "/atendimentos"))


def mensagem_ao_segurado(job):
    ev = job.get("evidence") or {}
    return PP.mensagem_do_desfecho(ev.get("desfecho"), ev.get("continuacao"))


def _body(pag, caminho, metodo="POST"):
    """O corpo que o MOTOR mandou (a sessão serializa em texto JSON)."""
    b = pag.corpo_de(metodo, caminho)
    if isinstance(b, str):
        try:
            return json.loads(b)
        except ValueError:
            return None
    return b


def sem_lixo(txt):
    return all(s not in txt for s in ("{", "}", "[", "]", "None"))


try:
    HAR_LAT = RV.carregar("LATERAL")
    HAR_LAT2 = RV.carregar("LATARIA2")
except RV.HarAusente as e:
    print("\n[SKIP] " + str(e))
    sys.exit(0)

TOKEN_LAT = str((RV.primeira(HAR_LAT, "POST", "/atendimentos") or {}).get("Token") or "")
TOKEN_LAT2 = str((RV.primeira(HAR_LAT2, "POST", "/atendimentos") or {}).get("Token") or "")
PII.update({TOKEN_LAT, TOKEN_LAT2})
AGENDA_HAR = RV.primeira(HAR_LAT, "POST", "/agendamentos", requisicao=True) or {}
FALA_LATERAL = {"pelicula": "nao tem pelicula", "porta_dianteira_ou_traseira": "a de tras",
                "lado_motorista_ou_carona": "do lado do motorista"}
TODOS_OS_BANCOS: list = []

# ==========================================================================
print("\n[a] o payload do agente -> build_portal_params -> a abertura REAL -> agenda")
# ==========================================================================
flat_a, info_a, cid_a = agente_e_infocap(HAR_LAT, peca="vidro de porta",
                                         como="encontrou o veiculo danificado",
                                         onde="foi na cidade", especificos=FALA_LATERAL)
banco = BancoDeMentira()
TODOS_OS_BANCOS.append(banco)
resp_a = chamar(banco, EMPRESA_A, SESSAO_A, flat_a, info_a, RV.PaginaDeReplay(HAR_LAT))
ab_a = (banco.jobs(journey="abrir_atendimento") or [{}])[0]
ev_a = ab_a.get("evidence") or {}
check("a: a tool enfileirou UM abrir_atendimento e o worker o executou",
      len(banco.jobs(journey="abrir_atendimento")) == 1 and banco.jobs_executados == [ab_a.get("id")],
      (banco.jobs_executados, banco.erros_do_worker))
check("a: nenhum erro no worker de costura", not banco.erros_do_worker, banco.erros_do_worker)
check("a: o params gravado tem confirm=True (agente ligado, freio solto)",
      (ab_a.get("params") or {}).get("confirm") is True)
check("a: a abertura terminou em `agenda` (done)",
      ab_a.get("status") == "done" and (ev_a.get("desfecho") or {}).get("tipo") == ST.DESFECHO_AGENDA,
      (ab_a.get("status"), ev_a.get("stage"), (ev_a.get("desfecho") or {}).get("tipo")))
cont_a = ev_a.get("continuacao") or {}
check("a: continuacao.possivel is True, acao_esperada agendar (bool, nao texto)",
      cont_a.get("possivel") is True and cont_a.get("acao_esperada") == "agendar",
      {k: cont_a.get(k) for k in ("possivel", "etapa", "acao_esperada")})
check("a: a sessao guardada na linha do banco (depois do _redigir) ainda abre o token",
      bool(TOKEN_LAT) and vault.decrypt(cont_a.get("sessao_cifrada") or "") == TOKEN_LAT)
check("a: o agente recebeu a agenda com horarios e o convite de escolher",
      "22/09:" in resp_a and "Me diga o número da loja, o dia e o horário que eu agendo" in resp_a,
      resp_a[:600])
check("a: e a instrucao ao agente de como a escolha volta (escolha_agenda)",
      "escolha_agenda" in resp_a and "\"dia\": \"DD/MM\"" in resp_a, resp_a[-500:])
_pag_a = PAGINAS.get(ab_a.get("_pagina"))
check("a: o /solicitantes levou o celular do segurado com WhatsApp (Tipo resolvido pelo portal)",
      _pag_a is not None and ((_pag_a.corpo_de("POST", "/solicitantes") or {}).get("Telefones")
                             or [{}])[0].get("StatusEnvioWhatsapp") is True)

# ==========================================================================
print("\n[b] \"quero a loja 1, dia 22/09 as 16:00\" -> continuacao -> agendado")
# ==========================================================================
flat_b = copy.deepcopy(flat_a)
flat_b["especificos"]["escolha_agenda"] = {"loja": "1", "dia": "22/09", "horario": "16:00"}
pag_b = RV.PaginaDeReplay(HAR_LAT, cursor=cursor_antes(HAR_LAT, "GET", "/agendamentos/opcoes-disponiveis"))
resp_b = chamar(banco, EMPRESA_A, SESSAO_A, flat_b, info_a, pag_b)
conts = banco.jobs(journey="continuar_atendimento")
check("b: UM job continuar_atendimento, e NENHUM segundo abrir_atendimento",
      len(conts) == 1 and len(banco.jobs(journey="abrir_atendimento")) == 1,
      (len(conts), len(banco.jobs(journey="abrir_atendimento")), resp_b[:300]))
check("b: nenhum erro no worker de costura", not banco.erros_do_worker, banco.erros_do_worker)
jc = conts[0] if conts else {}
cp = (jc.get("params") or {}).get("_continuacao") or {}
_loja1 = ((ev_a.get("desfecho") or {}).get("lojas") or [{}])[0]
check("b: a escolha '1' virou o CodigoCliente PUBLICADO da 1a loja, em texto",
      cp.get("escolha") == {"loja": str(_loja1.get("codigo_cliente")), "dia": "22/09",
                            "horario": "16:00"}, cp.get("escolha"))
check("b: a sessao foi como a journey a gravou (a cifra do job de origem)",
      (cp.get("sessao") or {}).get("sessao_cifrada") == cont_a.get("sessao_cifrada")
      and cp.get("job_origem") == ab_a.get("id"))
check("b: POST /agendamentos saiu UMA vez, IGUAL ao medido no HAR [048] (chave, valor e ordem)",
      pag_b.quantas("POST", "/agendamentos") == 1
      and list((pag_b.corpo_de("POST", "/agendamentos") or {}).items()) == list(AGENDA_HAR.items()),
      [k for k in (pag_b.corpo_de("POST", "/agendamentos") or {})])
check("b: a continuacao NUNCA emitiu POST /atendimentos", pag_b.quantas("POST", "/atendimentos") == 0)
evc = jc.get("evidence") or {}
ag = (evc.get("desfecho") or {}).get("agendamento") or {}
check("b: desfecho `agendado`, confirmado LENDO o portal",
      jc.get("status") == "done" and (evc.get("desfecho") or {}).get("tipo") == ST.DESFECHO_AGENDADO
      and ag.get("confirmado_pelo_portal") is True,
      (jc.get("status"), evc.get("stage"), (evc.get("desfecho") or {}).get("tipo")))
msg_b = mensagem_ao_segurado(jc)
numero = str((evc.get("desfecho") or {}).get("codigo_atendimento") or "")
check("b: a mensagem ao segurado tem loja, endereco, 22/09/2026, 16:00 e o numero",
      all(bool(v) and str(v) in msg_b for v in (ag.get("loja"), ag.get("endereco"), numero))
      and "22/09/2026" in msg_b and "16:00" in msg_b and "Agendei o serviço" in msg_b, msg_b)
check("b: e nada de '{', '[' ou 'None' no que o segurado le", sem_lixo(msg_b), msg_b)
check("b: o agente recebeu EXATAMENTE essa mensagem pela tool", msg_b in resp_b, resp_b[:300])
check("b: e a permanencia sai em gente (nao o numero cru do portal)",
      "Tempo que o carro fica na loja:" in msg_b, msg_b)

# ==========================================================================
print("\n[c] LATARIA2: preferencia de vistoria dita em linguagem natural")
# ==========================================================================
FALA_LATARIA = {"pecas_lataria": ["porta dianteira esquerda"], "lataria_mesmo_evento": "sim"}
flat_c, info_c, _ = agente_e_infocap(HAR_LAT2, peca="lataria", como="outros", onde="na cidade",
                                     especificos={**FALA_LATARIA,
                                                  "preferencia_vistoria": "prefiro levar numa loja"})
banco_c = BancoDeMentira()
TODOS_OS_BANCOS.append(banco_c)
resp_c = chamar(banco_c, EMPRESA_A, SESSAO_A, flat_c, info_c, RV.PaginaDeReplay(HAR_LAT2))
ab_c = (banco_c.jobs(journey="abrir_atendimento") or [{}])[0]
ev_c = ab_c.get("evidence") or {}
pag_c = PAGINAS.get(ab_c.get("_pagina"))
check("c: nenhum erro no worker de costura", not banco_c.erros_do_worker, banco_c.erros_do_worker)
check("c: build_portal_params normalizou a frase para 'loja'",
      ((ab_c.get("params") or {}).get("especificos") or {}).get("preferencia_vistoria") == "loja",
      ((ab_c.get("params") or {}).get("especificos") or {}).get("preferencia_vistoria"))
check("c: prioridade + ocorrencia '...EM LOJA' (texto do bundle) sairam",
      pag_c is not None and pag_c.quantas("POST", "/atendimentos-prioridades") == 1
      and (pag_c.corpo_de("POST", "/ocorrencias") or {}).get("Ocorrencia")
      == "SEGURADO TEM PREFERÊNCIA POR REALIZAR VISTORIA EM LOJA",
      (ev_c.get("stage"), pag_c and pag_c.escritas()))
check("c: desfecho `analista`",
      (ev_c.get("desfecho") or {}).get("tipo") == ST.DESFECHO_ANALISTA,
      (ab_c.get("status"), ev_c.get("stage"), (ev_c.get("desfecho") or {}).get("tipo")))
msg_c = mensagem_ao_segurado(ab_c)
check("c: a mensagem diz analista, traz o numero e esta limpa",
      "analista" in msg_c.lower() and str((ev_c.get("desfecho") or {}).get("codigo_atendimento") or "x") in msg_c
      and sem_lixo(msg_c) and msg_c in resp_c, msg_c)

print("\n[c'] LATARIA2 SEM preferencia -> pergunta -> 'loja' -> continuacao vistoria")
flat_c2, info_c2, _ = agente_e_infocap(HAR_LAT2, peca="lataria", como="outros", onde="na cidade",
                                       especificos=dict(FALA_LATARIA))
banco_c2 = BancoDeMentira()
TODOS_OS_BANCOS.append(banco_c2)
resp_c2 = chamar(banco_c2, EMPRESA_A, SESSAO_A, flat_c2, info_c2, RV.PaginaDeReplay(HAR_LAT2))
ab_c2 = (banco_c2.jobs(journey="abrir_atendimento") or [{}])[0]
ev_c2 = ab_c2.get("evidence") or {}
pag_c2 = PAGINAS.get(ab_c2.get("_pagina"))
check("c': parou em decidir_vistoria, SEM prioridade nem ocorrencia",
      ev_c2.get("stage") == "decidir_vistoria" and pag_c2 is not None
      and pag_c2.quantas("POST", "/ocorrencias") == 0
      and pag_c2.quantas("POST", "/atendimentos-prioridades") == 0,
      (ab_c2.get("status"), ev_c2.get("stage")))
check("c': continuacao possivel, acao vistoria",
      (ev_c2.get("continuacao") or {}).get("possivel") is True
      and (ev_c2.get("continuacao") or {}).get("acao_esperada") == "vistoria",
      {k: (ev_c2.get("continuacao") or {}).get(k) for k in ("possivel", "etapa", "acao_esperada")})
check("c': o segurado le a pergunta link x loja E o convite de responder",
      "link no celular" in resp_c2 and "Me responde por aqui que eu continuo" in resp_c2,
      resp_c2[:700])
check("c': e o agente aprende a devolver preferencia_vistoria",
      "preferencia_vistoria" in resp_c2, resp_c2[-400:])
flat_c3 = copy.deepcopy(flat_c2)
flat_c3["especificos"]["preferencia_vistoria"] = "loja"
pag_c3 = RV.PaginaDeReplay(HAR_LAT2, cursor=cursor_antes(HAR_LAT2, "GET", "/agendamentos/opcoes-disponiveis"))
resp_c3 = chamar(banco_c2, EMPRESA_A, SESSAO_A, flat_c3, info_c2, pag_c3)
jc3 = (banco_c2.jobs(journey="continuar_atendimento") or [{}])[0]
ev_c3 = jc3.get("evidence") or {}
check("c': UM continuar_atendimento operacao 'vistoria', nenhum 2o abrir",
      len(banco_c2.jobs(journey="continuar_atendimento")) == 1
      and ((jc3.get("params") or {}).get("_continuacao") or {}).get("operacao") == "vistoria"
      and len(banco_c2.jobs(journey="abrir_atendimento")) == 1, resp_c3[:300])
check("c': nenhum erro no worker de costura", not banco_c2.erros_do_worker, banco_c2.erros_do_worker)
check("c': a ocorrencia EM LOJA saiu e a continuacao nao criou pedido",
      (pag_c3.corpo_de("POST", "/ocorrencias") or {}).get("Ocorrencia")
      == "SEGURADO TEM PREFERÊNCIA POR REALIZAR VISTORIA EM LOJA"
      and pag_c3.quantas("POST", "/atendimentos") == 0, pag_c3.escritas())
check("c': desfecho `analista` e a mensagem chega limpa",
      (ev_c3.get("desfecho") or {}).get("tipo") == ST.DESFECHO_ANALISTA
      and sem_lixo(mensagem_ao_segurado(jc3)) and mensagem_ao_segurado(jc3) in resp_c3,
      (jc3.get("status"), ev_c3.get("stage"), resp_c3[:300]))

# ==========================================================================
print("\n[d] responder: a cidade nao casa -> parada -> a cidade certa -> segue")
# ==========================================================================
flat_d, info_d, cid_d = agente_e_infocap(HAR_LAT, peca="vidro de porta",
                                         como="encontrou o veiculo danificado", onde="foi na cidade",
                                         especificos=FALA_LATERAL, cidade="Cidade Inexistente Exemplo/SC")
PII.add(cid_d["cidade"])
banco_d = BancoDeMentira()
TODOS_OS_BANCOS.append(banco_d)
resp_d = chamar(banco_d, EMPRESA_A, SESSAO_A, flat_d, info_d, RV.PaginaDeReplay(HAR_LAT))
ab_d = (banco_d.jobs(journey="abrir_atendimento") or [{}])[0]
ev_d = ab_d.get("evidence") or {}
pag_d = PAGINAS.get(ab_d.get("_pagina"))
check("d: a abertura parou numa parada de cidade, com o pedido ja aberto",
      str(ev_d.get("stage") or "").startswith("cidade_") and pag_d is not None
      and pag_d.quantas("POST", "/atendimentos") == 1, (ab_d.get("status"), ev_d.get("stage")))
check("d: continuacao possivel (responder:<slot da cidade>)",
      (ev_d.get("continuacao") or {}).get("possivel") is True
      and str((ev_d.get("continuacao") or {}).get("acao_esperada") or "").startswith("responder"),
      {k: (ev_d.get("continuacao") or {}).get(k) for k in ("possivel", "etapa", "acao_esperada")})
check("d: o segurado le a pergunta da cidade E o convite de responder",
      "Me responde por aqui que eu continuo" in resp_d and PP._A_EQUIPE_ASSUME not in resp_d,
      resp_d[:600])
flat_d2 = copy.deepcopy(flat_d)
flat_d2["especificos"]["cidade_para_o_servico"] = f"{cid_d['cidade']}/{cid_d['uf']}"
pag_d2 = RV.PaginaDeReplay(HAR_LAT, cursor=cursor_antes(HAR_LAT, "PATCH", "/atendimentos"))
resp_d2 = chamar(banco_d, EMPRESA_A, SESSAO_A, flat_d2, info_d, pag_d2)
jd = (banco_d.jobs(journey="continuar_atendimento") or [{}])[0]
ev_d2 = jd.get("evidence") or {}
check("d: UM continuar_atendimento 'responder' com a cidade no contrato",
      len(banco_d.jobs(journey="continuar_atendimento")) == 1
      and ((jd.get("params") or {}).get("_continuacao") or {}).get("operacao") == "responder",
      (resp_d2[:300], ((jd.get("params") or {}).get("_continuacao") or {}).get("respostas")))
check("d: nenhum erro no worker de costura", not banco_d.erros_do_worker, banco_d.erros_do_worker)
check("d: a continuacao seguiu ate o desfecho (agenda) SEM novo POST /atendimentos",
      pag_d2.quantas("POST", "/atendimentos") == 0
      and (ev_d2.get("desfecho") or {}).get("tipo") == ST.DESFECHO_AGENDA,
      (jd.get("status"), ev_d2.get("stage"), pag_d2.escritas()))
check("d: o PATCH saiu com a cidade do servico resolvida pelo portal",
      (pag_d2.corpo_de("PATCH", "/atendimentos") or {}).get("CodigoCidade")
      == (RV.primeira(HAR_LAT, "PATCH", "/atendimentos", requisicao=True) or {}).get("CodigoCidade"))

# ==========================================================================
print("\n[e] sem sessao guardada, o texto NAO promete continuar")
# ==========================================================================
_chave = os.environ.pop("PORTAL_VAULT_KEY")
try:
    banco_e = BancoDeMentira()
    TODOS_OS_BANCOS.append(banco_e)
    resp_e = chamar(banco_e, EMPRESA_A, SESSAO_A, flat_a, info_a, RV.PaginaDeReplay(HAR_LAT))
    banco_e2 = BancoDeMentira()
    TODOS_OS_BANCOS.append(banco_e2)
    resp_e2 = chamar(banco_e2, EMPRESA_A, SESSAO_A, flat_d, info_d, RV.PaginaDeReplay(HAR_LAT))
finally:
    os.environ["PORTAL_VAULT_KEY"] = _chave
ev_e = ((banco_e.jobs(journey="abrir_atendimento") or [{}])[0]).get("evidence") or {}
check("e: sem cofre, a agenda chega com continuacao.possivel False",
      (ev_e.get("desfecho") or {}).get("tipo") == ST.DESFECHO_AGENDA
      and (ev_e.get("continuacao") or {}).get("possivel") is False)
check("e: agenda sem sessao: NAO diz 'eu agendo', diz que a equipe confirma",
      "eu agendo" not in resp_e and "Quem confirma o horário com a loja é a nossa equipe" in resp_e,
      resp_e[:600])
check("e: e NAO ensina o agente a mandar escolha_agenda", "escolha_agenda" not in resp_e)
check("e: parada de cidade sem sessao: NAO diz 'eu continuo'",
      "eu continuo" not in resp_e2 and "Me responde por aqui" not in resp_e2, resp_e2[:600])
_ev_e2 = ((banco_e2.jobs(journey="abrir_atendimento") or [{}])[0]).get("evidence") or {}
check("e: CONTROLE: a MESMA parada com sessao prometia (o texto CONSEGUE diferir)",
      str(_ev_e2.get("stage")) == str(ev_d.get("stage")) and "Me responde por aqui" in resp_d)

# ==========================================================================
print("\n[f] G11 — dois tenants: a continuacao de A nunca carrega nada de B")
# ==========================================================================
banco_f = BancoDeMentira()
TODOS_OS_BANCOS.append(banco_f)
chamar(banco_f, EMPRESA_B, SESSAO_B, flat_a, info_a, RV.PaginaDeReplay(HAR_LAT))
chamar(banco_f, EMPRESA_A, SESSAO_A, flat_a, info_a, RV.PaginaDeReplay(HAR_LAT))
ab_fa = banco_f.jobs(journey="abrir_atendimento", company_id=EMPRESA_A)[0]
ab_fb = banco_f.jobs(journey="abrir_atendimento", company_id=EMPRESA_B)[0]
check("f: (preparo) as duas corretoras tem o mesmo pedido, cada uma a sua abertura",
      ab_fa["id"] != ab_fb["id"] and ab_fa.get("status") == ab_fb.get("status") == "done")
# 🔴 O pior caso: uma continuação de B que aponta para a chave do pedido de A.
_isca = copy.deepcopy(ab_fb)
_isca.update({"id": "job-isca-b", "journey": "continuar_atendimento", "status": "done",
              "idempotency_key": "cont:isca-b", "created_at": "2026-09-21T23:59:00Z"})
_isca["params"]["_pedido_key"] = ab_fa["idempotency_key"]
_isca["evidence"]["continuacao"] = {**(_isca["evidence"].get("continuacao") or {}),
                                   "sessao_cifrada": "ISCA-DA-CORRETORA-B"}
banco_f.tabelas["portal_jobs"].append(_isca)
pag_f = RV.PaginaDeReplay(HAR_LAT, cursor=cursor_antes(HAR_LAT, "GET", "/agendamentos/opcoes-disponiveis"))
chamar(banco_f, EMPRESA_A, SESSAO_A, flat_b, info_a, pag_f)
jf = [j for j in banco_f.jobs(journey="continuar_atendimento", company_id=EMPRESA_A)]
_txt = json.dumps(jf, ensure_ascii=False, default=str)
check("f: A criou UMA continuacao, na casa dela",
      len(jf) == 1 and jf[0]["company_id"] == EMPRESA_A, len(jf))
check("f: 🔴 nada de B no job de A (nem a isca, nem o job, nem o perfil)",
      "ISCA-DA-CORRETORA-B" not in _txt and "job-isca-b" not in _txt
      and ab_fb["id"] not in _txt and "beta@exemplo.test" not in _txt, _limpo(_txt)[:300])
check("f: a continuacao de A partiu da abertura de A",
      jf and ((jf[0]["params"] or {}).get("_continuacao") or {}).get("job_origem") == ab_fa["id"])
check("f: CONTROLE: o banco TINHA a isca com a mesma chave de pedido (ela podia vazar)",
      bool(banco_f.jobs(id="job-isca-b")) and _isca["params"]["_pedido_key"]
      == (jf[0]["params"] if jf else {}).get("_pedido_key"))

# ==========================================================================
print("\n[g] responder:pergunta — o questionario parou; a resposta volta pela tool")
# ==========================================================================
# 📊 Catálogo do HAR (não é dado pessoal): a pergunta do lado e as opções dela.
_Q_LADO = [RV.corpo_json(c) for c in HAR_LAT if RV.caminho_de(c) == "/questionarios/perguntas"
           and (RV.corpo_json(c) or {}).get("Codigo") == 35][0]
_COD_MOTORISTA = [o["CodigoResposta"] for o in _Q_LADO["Respostas"]
                  if o["DescricaoResposta"] == "LADO DO MOTORISTA"][0]
# A resposta que NÃO casa com opção nenhuma: o portal para e pergunta.
flat_g, info_g, _ = agente_e_infocap(HAR_LAT, peca="vidro de porta",
                                     como="encontrou o veiculo danificado", onde="foi na cidade",
                                     especificos={**FALA_LATERAL, "lado_motorista_ou_carona": "o de cima"})
banco_g = BancoDeMentira()
TODOS_OS_BANCOS.append(banco_g)
resp_g = chamar(banco_g, EMPRESA_A, SESSAO_A, flat_g, info_g, RV.PaginaDeReplay(HAR_LAT))
ab_g = (banco_g.jobs(journey="abrir_atendimento") or [{}])[0]
ev_g = ab_g.get("evidence") or {}
check("g: parou em questionario_incompleto, ja com o pedido aberto",
      ev_g.get("stage") == "questionario_incompleto", (ab_g.get("status"), ev_g.get("stage")))
check("g: a continuacao espera a resposta ETIQUETADA: responder:pergunta_35",
      (ev_g.get("continuacao") or {}).get("possivel") is True
      and (ev_g.get("continuacao") or {}).get("acao_esperada") == "responder:pergunta_35",
      (ev_g.get("continuacao") or {}).get("acao_esperada"))
_para_ele = resp_g.split("[para a equipe", 1)[0]
check("g: o segurado LE a pergunta e as opcoes (antes do bloco da equipe)",
      "Qual o lado do item danificado?" in _para_ele and "Lado do motorista" in _para_ele
      and "Me responde por aqui que eu continuo" in _para_ele, _para_ele[-400:])
check("g: e o agente aprende a devolver em especificos.pergunta_35",
      "especificos.pergunta_35" in resp_g, resp_g[-300:])
flat_g2 = copy.deepcopy(flat_g)
flat_g2["especificos"]["pergunta_35"] = "lado do motorista"
pag_g2 = RV.PaginaDeReplay(HAR_LAT, cursor=cursor_antes(HAR_LAT, "POST", "/questionarios"))
resp_g2 = chamar(banco_g, EMPRESA_A, SESSAO_A, flat_g2, info_g, pag_g2)
jg = (banco_g.jobs(journey="continuar_atendimento") or [{}])[0]
ev_g2 = jg.get("evidence") or {}
check("g: UM continuar_atendimento 'responder' com {pergunta_35: ...}",
      len(banco_g.jobs(journey="continuar_atendimento")) == 1
      and ((jg.get("params") or {}).get("_continuacao") or {}).get("respostas")
      == {"pergunta_35": "lado do motorista"},
      ((jg.get("params") or {}).get("_continuacao") or {}).get("respostas"))
check("g: nenhum erro no worker de costura", not banco_g.erros_do_worker, banco_g.erros_do_worker)
_resp_35 = [r.get("CodigoResposta") for r in ((_body(pag_g2, "/questionarios") or {})
                                               .get("PerguntasResposta") or [])
            if r.get("CodigoPergunta") == 35]
check("g: o questionario gravou o LADO DO MOTORISTA (codigo do catalogo) na pergunta 35",
      _resp_35 == [_COD_MOTORISTA], (_resp_35, ev_g2.get("stage")))
check("g: e seguiu ate o desfecho (agenda) SEM novo POST /atendimentos",
      pag_g2.quantas("POST", "/atendimentos") == 0
      and (ev_g2.get("desfecho") or {}).get("tipo") == ST.DESFECHO_AGENDA,
      (jg.get("status"), ev_g2.get("stage"), pag_g2.escritas()))
# ==========================================================================
print("\n[G6] o token do portal nunca aparece em claro, em NENHUMA linha nem resposta")
# ==========================================================================
_vaz = []
for i, b in enumerate(TODOS_OS_BANCOS):
    txt = json.dumps(b.tabelas, ensure_ascii=False, default=str)
    for tk in (TOKEN_LAT, TOKEN_LAT2):
        if tk and tk in txt:
            _vaz.append(i)
for r in (resp_a, resp_b, resp_c, resp_c2, resp_c3, resp_d, resp_d2, resp_e, resp_e2):
    if TOKEN_LAT in r or TOKEN_LAT2 in r:
        _vaz.append("resp")
check(f"G6: token ausente de {len(TODOS_OS_BANCOS)} bancos e de todas as respostas", not _vaz, _vaz)

print("\n[A17] o cliente Supabase REAL nunca foi alcancado")
check("A17: zero chamadas ao cliente real", not ALCANCOU_O_REAL, ALCANCOU_O_REAL)

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
