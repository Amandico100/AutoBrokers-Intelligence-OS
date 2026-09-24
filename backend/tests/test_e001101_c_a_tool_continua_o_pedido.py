# -*- coding: utf-8 -*-
"""G7 + G11 — a tool CONTINUA o pedido já aberto, e nunca abre um segundo.

SPEC-EXTRA-001.10.1 C1/C4. Roda `PortalActionTool._arun` DE VERDADE, com um
dublê do cliente Supabase que imita o índice único parcial
`idx_portal_jobs_pedido_vivo (company_id, idempotency_key) WHERE status <>
'failed'`. Só a InfoCap, o WhatsApp e o interruptor do agente são trocados.

## 🔴 O defeito que este guarda impede de voltar

📊 Até 23/09/2026 a tool criava UM job `abrir_atendimento` e, quando o pedido
parava depois do protocolo (agenda para escolher, cidade sem rede…), a segunda
chamada devolvia `frase_de_pedido_ja_existente` — "a equipe assume". Não havia
continuação. Agora há, e ela tem três jeitos de dar errado, um por bloco:

```
G7a  a escolha vira UM job continuar_atendimento com o contrato §5 inteiro
G7b  a MESMA resposta duas vezes vira UM job (chave de continuação própria)
G7c  sem continuação possível: NENHUM job, e a frase honesta
G7d  resposta (responder:<slot>) só conta se for NOVA
G11  a busca da corretora B nunca devolve o job da A
```

## ⛔ P-E00110-A17 — o teste FALHA ALTO se o cliente REAL for alcançado

As variáveis do Supabase são apagadas do processo e `supabase.create_client`
vira uma armadilha. Se alguém chegar no banco de verdade, o placar fica
vermelho com o nome do culpado — nunca um "passou porque não achou nada".
"""
from __future__ import annotations

import asyncio
import copy
import os
import sys
from datetime import datetime, timezone

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

from app.agents.tools import portal_params as PP  # noqa: E402
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


# 💭 Tudo fictício (CLAUDE.md §12.1 e §13.9): corretoras, lojas, números, token.
EMPRESA_A = "aaaaaaaa-0000-4000-8000-000000000001"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-000000000002"
SESSAO = "whatsapp:5548900000000:co:ag"
TOKEN_FALSO = "TOKEN-CIFRADO-DE-TESTE-9f8e7d"

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
    "especificos": {"cidade_para_o_servico": "Joinville/SC",
                    "pelicula": "tem insulfilm sim",
                    "porta_dianteira_ou_traseira": "dianteira",
                    "lado_motorista_ou_carona": "do lado do carona"},
}

DESFECHO_AGENDA = {
    "tipo": "agenda", "codigo_atendimento": "88888888",
    "lojas": [
        {"codigo_cliente": 40001, "codigo_produto": 7, "nome": "Loja Exemplo Centro",
         "endereco": "Av. de Exemplo, 1", "cidade": "Joinville", "uf": "SC",
         "tem_agenda": True, "dias": ["25/09", "26/09"],
         "horarios": {"25/09": ["08:00", "16:00"]}},
        {"codigo_cliente": 40002, "codigo_produto": 7, "nome": "Loja Exemplo Norte",
         "endereco": "Rua de Exemplo, 2", "cidade": "Joinville", "uf": "SC",
         "tem_agenda": True, "dias": ["25/09"], "horarios": {"25/09": ["09:00"]}},
    ],
}


def _continuacao(acao: str, possivel: bool = True) -> dict:
    return {"possivel": possivel, "etapa": "pos_protocolo", "acao_esperada": acao,
            "emitida_em": datetime.now(timezone.utc).isoformat(),
            "sessao_guardada": True, "motivo": "",
            "sessao_cifrada": TOKEN_FALSO}


RESULTADO_AGENDADO = {
    "status": "done",
    "evidence": {"desfecho": {
        "tipo": "agendado", "codigo_atendimento": "88888888",
        "agendamento": {"loja": "Loja Exemplo Centro", "endereco": "Av. de Exemplo, 1",
                        "referencia": "em frente a praca de exemplo",
                        "data": "25/09/2026", "horario": "16:00", "permanencia": "90",
                        "confirmado_pelo_portal": True}}},
}


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
        self.operacao, self.linha = "insert", copy.deepcopy(dict(linha))
        return self

    def update(self, patch):
        self.operacao, self.linha = "update", copy.deepcopy(dict(patch))
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return self.banco.executar(self)


def _campo(linha: dict, chave: str):
    if chave.startswith("params->>"):
        # o `->>` do PostgREST: texto da chave de topo do jsonb (RED B4 usa placa)
        return str((linha.get("params") or {}).get(chave.split(">>", 1)[1]) or "")
    return linha.get(chave)


class BancoDeMentira:
    """`portal_jobs` com o índice único parcial de verdade (23505)."""

    def __init__(self, resultado_da_continuacao: dict):
        self.jobs: list = []
        self.updates_de_run: list = []
        self.resultado = resultado_da_continuacao
        self.selects_de_jobs: list = []
        # CONSERTO da 001.10.1: o "worker" pode ficar parado (continuacao EM
        # CURSO) e a leitura da ultima continuacao pode cair (fail-closed).
        self.worker_ligado = True
        self.select_falha = False

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Consulta(self, nome)

    def executar(self, q: _Consulta) -> _Resposta:
        f = q.filtros
        if q.tabela == "agents":
            return _Resposta([{"id": "agente-" + str(f.get("company_id"))[:8]}])
        if q.tabela == "companies":
            return _Resposta([dict(PERFIL_ROW)])
        if q.tabela == "work_runs":
            if q.operacao == "update":
                self.updates_de_run.append({"filtros": dict(f), "patch": dict(q.linha)})
            return _Resposta([])
        if q.tabela != "portal_jobs":
            return _Resposta([])
        if q.operacao == "insert":
            linha = q.linha
            chave = linha.get("idempotency_key")
            if chave and any(j.get("company_id") == linha.get("company_id")
                             and j.get("idempotency_key") == chave
                             and j.get("status") != "failed" for j in self.jobs):
                raise RuntimeError("duplicate key value violates unique constraint "
                                   "idx_portal_jobs_pedido_vivo (23505)")
            linha = {**linha, "id": f"job-{len(self.jobs) + 1}",
                     "created_at": f"2026-09-23T10:00:{len(self.jobs):02d}Z"}
            self.jobs.append(linha)
            return _Resposta([{"id": linha["id"]}])
        if q.operacao == "update":
            for j in self.jobs:
                if all(_campo(j, k) == v for k, v in f.items()):
                    j.update(q.linha)
            return _Resposta([])
        self.selects_de_jobs.append(dict(f))
        achados = [j for j in self.jobs if all(_campo(j, k) == v for k, v in f.items())]
        if self.select_falha and "params->>_pedido_key" in f:
            # CONSERTO (JUIZ B1): a leitura da ultima continuacao CAI.
            raise RuntimeError("TESTE: leitura de portal_jobs indisponivel")
        if "id" in f and achados:
            job = achados[0]
            if (job.get("journey") == "continuar_atendimento"
                    and job.get("status") in ("queued", "running")
                    and self.worker_ligado):
                # O "worker": a continuação termina com o resultado roteirizado.
                job.update(copy.deepcopy(self.resultado))
            return _Resposta([copy.deepcopy(job)])
        achados = sorted(achados, key=lambda j: j.get("created_at", ""), reverse=True)
        return _Resposta([copy.deepcopy(j) for j in achados])


NOTIFICACOES: list = []


class PortalDeMentira(PT.PortalActionTool):
    async def _fetch_infocap(self, cpf, policy_number):  # noqa: D102
        return INFOCAP

    def _notify(self, session_id, text, agent_id=None):  # noqa: D102
        NOTIFICACOES.append(text)          # ⛔ nenhuma mensagem sai


_ATUAL = {"banco": None}


def _preparar_ambiente():
    import app.core.database as DB
    import app.services.atlas.attendance_capture as AC
    import app.services.tela_cega as TC

    async def _cliente_async():
        return _ATUAL["banco"]

    async def _registrar(**_k):
        return True

    async def _agente(_c):
        return False

    DB.create_async_supabase_client = _cliente_async
    DB.get_supabase_client = lambda: _ATUAL["banco"]
    TC.registrar_tela_cega = _registrar
    AC.attendance_agent_active = _agente
    PT.POLL_EVERY_S = 0


def _params_do_pedido(company_id: str) -> dict:
    params, erro = PP.build_portal_params(dict(PEDIDO), {
        "nome": "Atendimento Exemplo", "email": "operacao@exemplo.test",
        "telefone": "4830000000", "cpf_cnpj": "00000000000191"}, INFOCAP)
    assert params, erro
    params["_idempotency_key"] = PP.chave_de_idempotencia(params, company_id)
    return params


def _abertura(company_id: str, status: str, evidence: dict) -> dict:
    params = _params_do_pedido(company_id)
    return {"company_id": company_id, "portal_key": "vidros_lanternas",
            "journey": "abrir_atendimento", "params": params, "status": status,
            "idempotency_key": params["_idempotency_key"], "session_id": SESSAO,
            "agent_id": "agente-x", "work_run_id": "run-1",
            "evidence": {"protocolo": "1234567890123456", **evidence}}


def _banco_com(abertura: dict, resultado: dict) -> BancoDeMentira:
    banco = BancoDeMentira(resultado)
    banco.jobs.append({**abertura, "id": "job-abertura",
                       "created_at": "2026-09-23T09:00:00Z"})
    _ATUAL["banco"] = banco
    return banco


def _chamar(banco, company_id: str, especificos_extra: dict) -> str:
    NOTIFICACOES.clear()
    ferramenta = PortalDeMentira(company_id=company_id, supabase_client=banco)
    pedido = copy.deepcopy(PEDIDO)
    pedido["especificos"].update(especificos_extra)
    saida = asyncio.run(ferramenta._arun(**pedido, session_id=SESSAO))
    return str(saida.get("content") or "")


def _continuacoes(banco) -> list:
    return [j for j in banco.jobs if j.get("journey") == "continuar_atendimento"]


def _aberturas(banco) -> list:
    return [j for j in banco.jobs if j.get("journey") == "abrir_atendimento"]


ESCOLHA = {"escolha_agenda": {"loja": "1", "dia": "25/09", "horario": "16h"}}


# ==========================================================================
def g7a_a_escolha_vira_uma_continuacao() -> None:
    print("\n[G7a] pedido parado na agenda + escolha => UM job continuar_atendimento")
    ab = _abertura(EMPRESA_A, "done", {"desfecho": DESFECHO_AGENDA,
                                       "continuacao": _continuacao("agendar")})
    banco = _banco_com(ab, RESULTADO_AGENDADO)
    conteudo = _chamar(banco, EMPRESA_A, ESCOLHA)

    conts = _continuacoes(banco)
    checar(len(conts) == 1, "UM job de continuacao nasceu", len(conts))
    checar(len(_aberturas(banco)) == 1,
           "🔴 e NENHUM segundo abrir_atendimento (so o original)", len(_aberturas(banco)))
    if not conts:
        return
    job = conts[0]
    c = job["params"].get("_continuacao") or {}
    checar(job["company_id"] == EMPRESA_A and job["portal_key"] == "vidros_lanternas",
           "na corretora certa e no portal certo", (job["company_id"], job["portal_key"]))
    checar(job["status"] == "queued" or job["status"] == "done",
           "nasceu queued (e o dublê do worker a terminou)", job["status"])
    checar(c.get("operacao") == "agendar", "operacao 'agendar'", c.get("operacao"))
    checar(c.get("escolha") == {"loja": "40001", "dia": "25/09", "horario": "16:00"},
           "a escolha '1' virou o CodigoCliente PUBLICADO da 1a loja (igualdade), e "
           "'16h' virou '16:00'", c.get("escolha"))
    checar(c.get("sessao") == ab["evidence"]["continuacao"],
           "a SESSAO foi copiada INTEIRA (com sessao_cifrada), sem ser lida",
           sorted((c.get("sessao") or {}).keys()))
    checar(c.get("job_origem") == "job-abertura", "job_origem = o job que tinha a sessao",
           c.get("job_origem"))
    checar(c.get("desfecho_anterior") == DESFECHO_AGENDA,
           "e o desfecho anterior vai junto (a lista que o segurado viu)")
    checar(str(job.get("idempotency_key") or "").startswith("cont:"),
           "chave PROPRIA de continuacao ('cont:'), nunca a de criacao",
           job.get("idempotency_key"))
    checar(job["params"].get("_pedido_key") == ab["idempotency_key"],
           "e a liga do pedido (_pedido_key) aponta para a abertura")
    checar(job.get("work_run_id") == "run-1" and job.get("session_id") == SESSAO,
           "mesmo work_run e mesma conversa da abertura",
           (job.get("work_run_id"), job.get("session_id")))
    checar(job["params"].get("confirm") is False,
           "confirm lido AGORA (agente desligado no dublê => False)",
           job["params"].get("confirm"))
    checar("Agendei o serviço" in conteudo and "16:00" in conteudo,
           "o agente recebe o agendamento CONFIRMADO", conteudo[:300])
    checar(TOKEN_FALSO not in conteudo and all(TOKEN_FALSO not in n for n in NOTIFICACOES),
           "🔴 G6: o token NUNCA aparece no que volta ao agente nem na notificacao")
    concl = [u for u in banco.updates_de_run if u["patch"].get("status") == "completed"]
    checar(len(concl) == 1 and (concl[0]["patch"].get("result_payload") or {})
           .get("agendamento", {}).get("horario") == "16:00",
           "o MESMO work_run do pedido foi CONCLUIDO com o agendamento",
           str(banco.updates_de_run)[:300])


def g7b_a_mesma_resposta_duas_vezes_e_um_job() -> None:
    print("\n[G7b] a MESMA escolha 2x com a continuacao EM CURSO => UM job (Stripe)")
    # 🔴 CONSERTO da 001.10.1 (RED B3) — verdade que MUDOU (CLAUDE.md §9.3):
    # antes este guarda afirmava "a mesma escolha depois de uma continuacao
    # TERMINADA = o mesmo job", e era exatamente isso que prendia para sempre a
    # escolha do segurado depois de um 500 da agenda. A licao migra: a MESMA
    # resposta com a continuacao EM CURSO continua sendo UM job (G7); depois de
    # uma parada SEM efeito, a mesma escolha ganha uma tentativa nova.
    parada_tecnica = {"status": "needs_human", "evidence": {
        "stage": "agenda_nao_respondeu", "desfecho": DESFECHO_AGENDA,
        "continuacao": _continuacao("agendar")}}
    ab = _abertura(EMPRESA_A, "done", {"desfecho": DESFECHO_AGENDA,
                                       "continuacao": _continuacao("agendar")})
    banco = _banco_com(ab, parada_tecnica)
    teto = PT.POLL_TIMEOUT_S
    PT.POLL_TIMEOUT_S = 0.05
    banco.worker_ligado = False           # a 1a continuacao fica EM CURSO
    try:
        _chamar(banco, EMPRESA_A, ESCOLHA)
        segundo = _chamar(banco, EMPRESA_A, ESCOLHA)
    finally:
        PT.POLL_TIMEOUT_S = teto
    checar(len(_continuacoes(banco)) == 1,
           "G7: duas chamadas identicas com a 1a EM CURSO => UM job de continuacao",
           len(_continuacoes(banco)))
    checar("ja existe" in segundo.lower(),
           "e a segunda NAO cria nada: acompanha o job que ja roda", segundo[:200])
    # A corrida (as duas chamadas antes de qualquer insert) cai no indice unico:
    # a MESMA origem + a MESMA escolha = a MESMA chave.
    _esc = {"loja": "40001", "dia": "25/09", "horario": "16:00"}
    k1 = PP.montar_job_de_continuacao(company_id=EMPRESA_A, job_origem=ab, operacao="agendar",
                                      pedido_key="p", protocolo="88888888", confirm=True,
                                      escolha=_esc, extra="job-abertura")["idempotency_key"]
    k2 = PP.montar_job_de_continuacao(company_id=EMPRESA_A, job_origem=ab, operacao="agendar",
                                      pedido_key="p", protocolo="88888888", confirm=True,
                                      escolha=dict(_esc), extra="job-abertura")["idempotency_key"]
    checar(bool(k1) and k1 == k2,
           "G7: corrida de duas chamadas iguais => a MESMA chave (o indice decide)")

    # 🔴 RED B3: a 1a termina numa parada TECNICA sem efeito (a agenda nao
    # respondeu). A MESMA escolha agora ganha uma tentativa nova.
    banco.worker_ligado = True
    for j in _continuacoes(banco):        # o "worker" termina a 1a (parada tecnica)
        j.update(copy.deepcopy(parada_tecnica))
    antes = len(_continuacoes(banco))
    _chamar(banco, EMPRESA_A, ESCOLHA)
    checar(len(_continuacoes(banco)) == antes + 1,
           "RED B3: depois de uma parada SEM efeito, a MESMA escolha => tentativa NOVA",
           (antes, len(_continuacoes(banco))))

    # CONTROLE: uma escolha DIFERENTE e outra continuacao — senao a chave
    # poderia ser constante e o bloco acima nao provaria nada.
    _chamar(banco, EMPRESA_A, {"escolha_agenda": {"loja": "2", "dia": "25/09",
                                                  "horario": "09:00"}})
    checar(len(_continuacoes(banco)) == antes + 2,
           "CONTROLE: escolha diferente => um job NOVO", len(_continuacoes(banco)))
    chaves = {j.get("idempotency_key") for j in _continuacoes(banco)}
    checar(len(chaves) == len(_continuacoes(banco)),
           "CONTROLE: e as chaves sao todas diferentes", chaves)


def b1_leitura_que_cai_nao_manda_nada() -> None:
    print("\n[JUIZ B1] a leitura da ultima continuacao CAI => nada vai a seguradora")
    ab = _abertura(EMPRESA_A, "done", {"desfecho": DESFECHO_AGENDA,
                                       "continuacao": _continuacao("agendar")})
    banco = _banco_com(ab, RESULTADO_AGENDADO)
    banco.select_falha = True
    conteudo = _chamar(banco, EMPRESA_A, ESCOLHA)
    checar(len(_continuacoes(banco)) == 0,
           "JUIZ B1: SELECT caiu => NENHUM job de continuacao (fail-closed)",
           len(_continuacoes(banco)))
    checar("Nao consegui conferir" in conteudo,
           "JUIZ B1: e o agente ouve que a tool nao conseguiu conferir", conteudo[:200])
    # CONTROLE: a MESMA chamada com a leitura de pe cria a continuacao.
    banco.select_falha = False
    _chamar(banco, EMPRESA_A, ESCOLHA)
    checar(len(_continuacoes(banco)) == 1,
           "CONTROLE: com a leitura de pe, a mesma chamada continua", len(_continuacoes(banco)))


def _chamar_com_peca(banco, company_id: str, peca: str) -> str:
    NOTIFICACOES.clear()
    pedido = copy.deepcopy(PEDIDO)
    pedido["peca"] = peca
    saida = asyncio.run(PortalDeMentira(company_id=company_id, supabase_client=banco)
                        ._arun(**pedido, session_id=SESSAO))
    return str(saida.get("content") or "")


def b4_a_peca_reescrita_nao_abre_outro_pedido() -> None:
    print("\n[RED B4] a peca REESCRITA para responder uma parada => continuacao, nunca 2o pedido")
    nova = "vidro da porta dianteira direita"
    ev_parado = {"stage": "peca_ambigua", "continuacao": _continuacao("responder:peca")}
    ab = _abertura(EMPRESA_A, "needs_human", ev_parado)
    banco = _banco_com(ab, RESULTADO_AGENDADO)
    conteudo = _chamar_com_peca(banco, EMPRESA_A, nova)
    checar(len(_aberturas(banco)) == 1,
           "RED B4: NENHUM abrir_atendimento novo (a peca reescrita nao e pedido novo)",
           len(_aberturas(banco)))
    conts = _continuacoes(banco)
    resp = ((conts[0].get("params") or {}).get("_continuacao") or {}).get("respostas") if conts else None
    checar(len(conts) == 1 and resp == {"peca": nova},
           "RED B4: UMA continuacao 'responder' com a peca nova como RESPOSTA", resp)
    checar(bool(conts) and ((conts[0].get("params") or {}).get("dano") or {}).get("peca")
           == ab["params"]["dano"]["peca"],
           "RED B4: e o campo de cima da continuacao e o do pedido (a chave nao muda)")
    checar("NAO abri outro atendimento" in conteudo,
           "RED B4: o agente e avisado de que a chamada virou RESPOSTA", conteudo[:200])

    # ⚠️ Os dois cenarios abaixo ABREM um pedido novo que o dublê nao processa:
    # sem teto curto, a tool espera os 150 s inteiros de POLL_TIMEOUT_S em cada
    # um. 📊 24/09: o arquivo levava 339 s e estourava o teto de 120 s do
    # `test_todos_os_guardas_script_rodam` na bateria. O que se afirma aqui e o
    # que foi INSERIDO, nao a espera.
    teto = PT.POLL_TIMEOUT_S
    PT.POLL_TIMEOUT_S = 0.05
    try:
        _b4_dois_tenants_e_controle(ev_parado, nova)
    finally:
        PT.POLL_TIMEOUT_S = teto


def _b4_dois_tenants_e_controle(ev_parado: dict, nova: str) -> None:
    # DOIS TENANTS: o pedido parado e de B; a chamada de A abre o de A.
    ab_b = _abertura(EMPRESA_B, "needs_human", ev_parado)
    banco_b = _banco_com(ab_b, RESULTADO_AGENDADO)
    _chamar_com_peca(banco_b, EMPRESA_A, nova)
    checar(len(_continuacoes(banco_b)) == 0
           and len([j for j in _aberturas(banco_b) if j.get("company_id") == EMPRESA_A]) == 1,
           "G11: o pedido parado de B NUNCA vira continuacao de uma chamada de A",
           [(str(j.get("company_id"))[:4], j.get("journey")) for j in banco_b.jobs])

    # CONTROLE: a MESMA peca reescrita com o pedido NAO esperando resposta
    # (agenda) abre outro pedido — o guarda CONSEGUE deixar passar (outra peca
    # de verdade = outro pedido, frase_de_pedido_ja_existente).
    ab_c = _abertura(EMPRESA_A, "done", {"desfecho": DESFECHO_AGENDA,
                                         "continuacao": _continuacao("agendar")})
    banco_c = _banco_com(ab_c, RESULTADO_AGENDADO)
    _chamar_com_peca(banco_c, EMPRESA_A, nova)
    checar(len(_aberturas(banco_c)) == 2 and len(_continuacoes(banco_c)) == 0,
           "CONTROLE: sem parada esperando resposta, a regra de antes vale",
           (len(_aberturas(banco_c)), len(_continuacoes(banco_c))))


def g7c_sem_continuacao_possivel() -> None:
    print("\n[G7c] sem continuacao possivel => NENHUM job e a frase honesta")
    ab = _abertura(EMPRESA_A, "done", {"desfecho": DESFECHO_AGENDA,
                                       "continuacao": _continuacao("agendar", possivel=False)})
    banco = _banco_com(ab, RESULTADO_AGENDADO)
    conteudo = _chamar(banco, EMPRESA_A, ESCOLHA)
    checar(len(banco.jobs) == 1, "nenhum job novo (nem continuacao, nem abertura)",
           len(banco.jobs))
    checar("NAO pode ser continuado" in conteudo and "nossa equipe" in conteudo,
           "a frase diz a verdade: este pedido segue com a equipe", conteudo[-500:])
    checar("Me diga o número da loja, o dia e o horário que eu agendo" not in conteudo,
           "🔴 e NAO promete que o robo agenda", conteudo[:400])

    # "possivel" em TEXTO não é prova.
    ab2 = _abertura(EMPRESA_A, "done", {"desfecho": DESFECHO_AGENDA,
                                        "continuacao": {**_continuacao("agendar"),
                                                        "possivel": "true"}})
    banco2 = _banco_com(ab2, RESULTADO_AGENDADO)
    _chamar(banco2, EMPRESA_A, ESCOLHA)
    checar(len(banco2.jobs) == 1, "'possivel': 'true' (texto) NAO abre continuacao",
           len(banco2.jobs))

    # Pedido continuável, mas a chamada NÃO trouxe a escolha: nada sai.
    ab3 = _abertura(EMPRESA_A, "done", {"desfecho": DESFECHO_AGENDA,
                                        "continuacao": _continuacao("agendar")})
    banco3 = _banco_com(ab3, RESULTADO_AGENDADO)
    sem = _chamar(banco3, EMPRESA_A, {})
    checar(len(banco3.jobs) == 1 and "NAO mandei nada" in sem,
           "continuavel mas SEM a escolha => nada sai, e o agente e avisado",
           sem[:200])
    # Escolha fora da lista: nada sai.
    banco4 = _banco_com(ab3, RESULTADO_AGENDADO)
    fora = _chamar(banco4, EMPRESA_A, {"escolha_agenda": {"loja": "1", "dia": "25/09",
                                                          "horario": "11:00"}})
    checar(len(banco4.jobs) == 1 and "horario_fora_da_lista" in fora,
           "horario que a lista CONHECIDA desmente => nada sai", fora[:200])


def g7d_responder_so_com_resposta_nova() -> None:
    print("\n[G7d] responder:<slot> — so a resposta NOVA vira continuacao")
    ev = {"stage": "cidade_sem_rede", "continuacao": _continuacao("responder:cidade_servico")}
    ab = _abertura(EMPRESA_A, "needs_human", ev)
    banco = _banco_com(ab, {"status": "done", "evidence": {"desfecho": {
        "tipo": "analista", "codigo_atendimento": "88888888"}}})
    _chamar(banco, EMPRESA_A, {"cidade_para_o_servico": "Joinville/SC"})
    checar(len(_continuacoes(banco)) == 0,
           "a MESMA cidade com que o portal parou NAO vira continuacao",
           len(_continuacoes(banco)))
    _chamar(banco, EMPRESA_A, {"cidade_para_o_servico": "Curitiba/PR"})
    conts = _continuacoes(banco)
    checar(len(conts) == 1, "outra cidade => UMA continuacao", len(conts))
    if conts:
        c = conts[0]["params"]["_continuacao"]
        checar(c.get("operacao") == "responder"
               and c.get("respostas") == {"cidade_servico": {"uf": "PR", "cidade": "CURITIBA"}},
               "respostas no contrato: {cidade_servico: {uf, cidade}} ja normalizada",
               c.get("respostas"))
    checar(len(_aberturas(banco)) == 1, "e nenhum segundo abrir_atendimento")


def g11_dois_tenants() -> None:
    print("\n[G11] a busca da corretora B nunca devolve o job da A")
    ab_a = _abertura(EMPRESA_A, "done", {"desfecho": DESFECHO_AGENDA,
                                         "continuacao": _continuacao("agendar")})
    banco = _banco_com(ab_a, RESULTADO_AGENDADO)
    _chamar(banco, EMPRESA_A, ESCOLHA)
    cont_a = _continuacoes(banco)
    checar(len(cont_a) == 1, "(preparo) a corretora A tem uma continuacao", len(cont_a))

    # O pior caso: a MESMA chave de pedido nas duas casas.
    chave = ab_a["idempotency_key"]
    ab_b = {**_abertura(EMPRESA_B, "done", {}), "id": "job-abertura-b"}
    achado = PT.buscar_ultimo_estado_do_pedido(banco, EMPRESA_B, ab_b, chave)
    checar(achado is ab_b,
           "🔴 com a MESMA chave, B recebe a PROPRIA abertura — nunca a continuacao de A",
           achado.get("id"))
    filtros = [f for f in banco.selects_de_jobs if f.get("journey") == "continuar_atendimento"]
    checar(filtros and all("company_id" in f for f in filtros),
           "e toda busca de continuacao filtra company_id no CODIGO", filtros[-1:] or filtros)
    # CONTROLE: a MESMA busca feita por A acha a continuação — senão o bloco
    # acima passaria com uma busca que nunca acha nada.
    achado_a = PT.buscar_ultimo_estado_do_pedido(banco, EMPRESA_A, ab_a, chave)
    checar(achado_a.get("journey") == "continuar_atendimento"
           and achado_a.get("company_id") == EMPRESA_A,
           "CONTROLE: a corretora A acha a SUA ultima continuacao", achado_a.get("id"))

    # E a ferramenta de B, com o mesmo pedido, nunca toca no job de A.
    banco.jobs.append({**ab_b, "idempotency_key": PP.chave_de_idempotencia(
        ab_b["params"], EMPRESA_B), "evidence": {"protocolo": "1",
                                                 "continuacao": _continuacao("agendar", False)}})
    antes = len(_continuacoes(banco))
    _chamar(banco, EMPRESA_B, ESCOLHA)
    checar(len(_continuacoes(banco)) == antes,
           "a tool de B (sem continuacao possivel NA CASA DELA) nao cria nada",
           len(_continuacoes(banco)))


def c4_o_run_espera_sem_falhar() -> None:
    print("\n[C4-run] agenda COM continuacao: o run fica ABERTO, nunca 'falhou'")
    banco = BancoDeMentira({})
    _ATUAL["banco"] = banco
    PT.fechar_work_run(EMPRESA_A, "run-9", {"status": "done", "evidence": {
        "desfecho": DESFECHO_AGENDA, "continuacao": _continuacao("agendar")}})
    status = [u["patch"].get("status") for u in banco.updates_de_run]
    passos = [u["patch"].get("current_step_key") for u in banco.updates_de_run]
    checar("failed" not in status and "completed" not in status,
           "nem falhou nem concluiu: espera a escolha do segurado", status)
    checar("aguardando_escolha_do_segurado" in passos, "passo 'aguardando_escolha_do_segurado'",
           passos)
    # CONTROLE: a mesma agenda SEM continuação continua indo para a equipe.
    banco2 = BancoDeMentira({})
    _ATUAL["banco"] = banco2
    PT.fechar_work_run(EMPRESA_A, "run-9", {"status": "done", "evidence": {
        "desfecho": DESFECHO_AGENDA}})
    checar("failed" in [u["patch"].get("status") for u in banco2.updates_de_run],
           "CONTROLE: SEM continuacao, o run vai para a equipe (portal_aguarda_a_equipe)")


def a17_o_cliente_real_nunca_foi_alcancado() -> None:
    print("\n[P-E00110-A17] o cliente Supabase REAL nunca foi alcancado")
    checar(not ALCANCOU_O_REAL, "zero chamadas ao cliente real", ALCANCOU_O_REAL)


if __name__ == "__main__":
    print("=" * 72)
    print("G7 + G11 — a tool continua o MESMO pedido, e so na casa certa")
    print("=" * 72)
    _preparar_ambiente()
    g7a_a_escolha_vira_uma_continuacao()
    g7b_a_mesma_resposta_duas_vezes_e_um_job()
    b1_leitura_que_cai_nao_manda_nada()
    b4_a_peca_reescrita_nao_abre_outro_pedido()
    g7c_sem_continuacao_possivel()
    g7d_responder_so_com_resposta_nova()
    g11_dois_tenants()
    c4_o_run_espera_sem_falhar()
    a17_o_cliente_real_nunca_foi_alcancado()
    print("\n" + "=" * 72)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
    print("=" * 72)
    sys.exit(1 if FAIL else 0)
