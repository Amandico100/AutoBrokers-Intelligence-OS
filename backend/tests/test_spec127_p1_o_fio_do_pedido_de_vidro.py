# -*- coding: utf-8 -*-
r"""SPEC-127 P1 — 🔴 O TESTE DO FIO: o pedido de vidro só nasce com o "ok" e nunca cai no DOM por falta de dado.

```
segurado "quero trocar o para-brisa" → PortalActionTool._arun REAL → build_portal_params REAL
  → O PORTÃO DO OK (insurer_dispatch_tool.prova_da_confirmacao: a conversa DURÁVEL + regex E classificador)
     sem o resumo + o "sim" → confirm_first com a LINHA PRONTA, NADA criado
  → "pode mandar" → UM job abrir_atendimento
  → a FILA (borda): o job chega ao worker SEM a cidade do serviço (📊 BLOCO 0 §7.1 — a tool não o
     deixa nascer; só um job escrito à mão/legado o alcança: é a 2ª rede)
  → vidros_lanternas.abrir_atendimento (flag ligada) → vidros_apifirst.abrir_atendimento_api (o MOTOR)
     → PARADA PRÉ-FRONTEIRA `faltou_cidade_servico`, etapa "abertura", 0 POST (era `None` → o DOM)
  → _aguardar → format_result: a pergunta em português
  → a resposta (especificos.cidade_para_o_servico) → _continuar_ou_explicar → UM job continuar_atendimento
  → vidros_continuacao (ramo "abertura": RECOMEÇA no MESMO pedido) → 1 POST no total → o desfecho do HAR
```

Dublê SÓ na borda: a página do portal (o HAR real, `_replay_vidros` — o leitor único), o banco
(`portal_jobs` + a conversa), a InfoCap, o classificador do papel `confirmacao`
(`bancada_confirmacao.classificador_duble_na_borda`) e o WhatsApp. ⛔ Nenhum valor pessoal do HAR é
impresso ou afirmado em texto; corretoras fictícias (CLAUDE.md §13.9).
Rodar (de backend/):  python -m pytest -q tests/test_spec127_p1_o_fio_do_pedido_de_vidro.py
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import copy
import dataclasses
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _c in (str(ROOT), str(ROOT / "tests")):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from cryptography.fernet import Fernet  # noqa: E402

os.environ.setdefault("PORTAL_VAULT_KEY", Fernet.generate_key().decode())

import _replay_vidros as RV  # noqa: E402

try:
    HAR = RV.carregar("NOVO")
except RV.HarAusente as _e:  # pragma: no cover — sem o acervo local
    pytest.skip(f"sem os HAR do portal (fora do Git): {_e}", allow_module_level=True)

from app.agents.tools import portal_params as PP  # noqa: E402
from app.agents.tools import portal_tool as PT  # noqa: E402
from app.services.evals import bancada_confirmacao as BC  # noqa: E402
from app.services.evals.dubles import SupabaseDuble  # noqa: E402
from portal_worker import guardrails as G  # noqa: E402
from portal_worker import worker as W  # noqa: E402
from portal_worker.journeys import vidros_api as API  # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF  # noqa: E402
from portal_worker.journeys import vidros_continuacao as VC  # noqa: E402
from portal_worker.journeys import vidros_estado as ST  # noqa: E402
from portal_worker.journeys import vidros_lanternas as VL  # noqa: E402

EMPRESA = "aaaaaaaa-0000-4000-8000-0000000127a1"
SESSAO = f"whatsapp:5500000000127:{EMPRESA}:agente-1"
CONVERSA = "conversa-127"


# ── as BORDAS, derivadas do HAR em memória (o molde de `test_e00110_a_costura_do_agente_ao_desfecho`) ──
def _bordas():
    ab = RV.primeira(HAR, "POST", "/atendimentos", requisicao=True) or {}
    apolice = RV.primeira(HAR, "GET", "/apolices") or {}
    sol = RV.primeira(HAR, "POST", "/solicitantes", requisicao=True) or {}
    corretor = RV.primeira(HAR, "PUT", "/atendimentos/corretores", requisicao=True) or {}
    patch = RV.primeira(HAR, "PATCH", "/atendimentos", requisicao=True) or {}
    cid = next(c for c in (RV.primeira(HAR, "GET", "/cidades") or [])
               if c.get("Codigo") == patch.get("CodigoCidade"))
    motivo = next(m for m in (RV.primeira(HAR, "GET", "/motivos-dano") or [])
                  if m.get("CodigoObjetoCausa") == patch.get("CodigoObjetoCausa"))
    tel = str(((sol.get("Telefones") or [{}])[0]).get("Numero") or "")
    profile = {"nome": str(sol.get("NomeSolicitante") or "CORRETORA"),
               "email": str(sol.get("EmailTitularAplice") or sol.get("EmailSegurado") or ""),
               "telefone": tel, "cpf_cnpj": str(corretor.get("Documento") or "")}
    infocap = {"ok": True, "status": "found",
               "policy": {"numapo": str(apolice.get("NumeroDaApolice") or ""),
                          "seguradora": str(ab.get("Seguradora") or ""), "active": True},
               "vehicle": {"placa": str(ab.get("PlacaInformada") or ""),
                           "chassi": str(apolice.get("Chassi") or ""), "veiculo": "VEICULO"},
               "client": {"nome": "Segurado", "cpf_cnpj": str(ab.get("CpfCnpjSegurado") or ""),
                          "email": str(sol.get("EmailSegurado") or ""), "telefone": tel,
                          "cidade": str(cid.get("Nome") or ""), "estado": str(cid.get("UF") or ""),
                          "cep": str(patch.get("Cep") or "")}}
    iso = str(ab.get("DataSinistro") or "")[:10]
    flat = {"cpf_cnpj": infocap["client"]["cpf_cnpj"], "data_dano": "/".join(reversed(iso.split("-"))),
            "peca": "para-brisa", "como_ocorreu": str(motivo.get("DescricaoObjetoCausa") or ""),
            "onde_ocorreu": "rodoviario" if patch.get("PerimetroDano") == "R" else "urbano",
            # 📊 o que a captura respondeu, nas palavras do segurado (o molde da costura C1)
            "especificos": {"cidade_para_o_servico": f"{cid.get('Nome')}/{cid.get('UF')}",
                            "aceita_reparo": "sim", "posicao_do_trincado": "do lado do passageiro",
                            "tamanho_do_trincado": "pequenininha", "sensor_de_direcao_ou_faixa": "nao sei"}}
    return profile, infocap, flat


PROFILE, INFOCAP, FLAT = _bordas()
PLACA = INFOCAP["vehicle"]["placa"]


class RT:
    """O que o worker injeta em `params["_runtime"]`: o guard REAL + checkpoint em memória."""

    def __init__(self, liberado: bool):
        self.guard = G.PortalActionGuard(material_liberado=liberado, _checkpoint=self.cp)

    async def cp(self, _patch):
        return None


def _params_completos(**extra):
    params, erro = PP.build_portal_params(copy.deepcopy(FLAT), dict(PROFILE), copy.deepcopy(INFOCAP),
                                          enviar_de_verdade=True)
    assert erro is None, "a borda do HAR deixou de montar um pedido completo"
    params["_idempotency_key"] = PP.chave_de_idempotencia(params, EMPRESA)
    params.update(extra)
    return params


def _evidencia_do_worker(r, ev):
    if r.status == "needs_human":
        return W._augment_hitl_evidence(r, ev)
    return {**ev, **(r.captured or {}), "message": r.message}


def _abrir(params, har=None):
    """O worker pela porta de entrada REAL (`vidros_lanternas.abrir_atendimento`, flag ligada)."""
    page = RV.PaginaDeReplay(har or HAR)
    ev: dict = {}
    p = {**copy.deepcopy({k: v for k, v in params.items() if k != "_runtime"}), "_runtime": RT(True)}
    r = asyncio.run(VL.abrir_atendimento(page, p, ev))
    return r, _evidencia_do_worker(r, ev), page


def _har_com(caminho: str, corpo, *, status: int = 200) -> list:
    """O DUBLÊ DA BORDA: o MESMO HAR com a resposta de `caminho` trocada (o portal respondendo outra coisa)."""
    saida = []
    for c in HAR:
        if RV.caminho_de(c).split("?")[0] == caminho:
            c = dataclasses.replace(c, corpo_resp=json.dumps(corpo), status=status)
        saida.append(c)
    return saida


@pytest.fixture(autouse=True)
def _flag_ligada(monkeypatch):
    monkeypatch.setenv("PORTAL_VIDROS_API_FIRST", "1")


# ═════════════════════════════════════════════════════════════════════════════
# 1 · A TOOL recusa cedo o que não é do segurado (item 3) e a data que não é data
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("campo,frase", [("cpf_cnpj", "o documento da corretora"),
                                         ("telefone", "o telefone da corretora")])
def test_o_cadastro_da_corretora_incompleto_e_recusado_na_tool_e_nao_vira_pergunta(campo, frase):
    perfil = {**PROFILE, campo: ""}
    info = copy.deepcopy(INFOCAP)
    if campo == "telefone":
        info["client"]["telefone"] = ""          # sem o celular do segurado também
    params, erro = PP.build_portal_params(copy.deepcopy(FLAT), perfil, info, enviar_de_verdade=True)
    assert params is None and frase in erro and "cadastro de acionamento" in erro
    assert "NAO peca nada a ele" in erro and "Personalizacao -> Corretora" in erro
    # CONTROLE: o telefone da corretora some, mas a apólice tem o do segurado → o pedido nasce
    if campo == "telefone":
        ok, e2 = PP.build_portal_params(copy.deepcopy(FLAT), perfil, copy.deepcopy(INFOCAP),
                                        enviar_de_verdade=True)
        assert e2 is None and ok["contato"]["telefone"]


@pytest.mark.parametrize("data", ["ontem", "31/02/2026", "5/10", "2026-13-01", "05/10/26"])
def test_a_data_que_nao_e_data_e_perguntada_antes_de_qualquer_job(data):
    params, erro = PP.build_portal_params({**FLAT, "data_dano": data}, dict(PROFILE), copy.deepcopy(INFOCAP))
    assert params is None and "Em que dia isso aconteceu?" in erro


def test_a_regra_da_data_da_tool_nunca_aceita_o_que_o_worker_recusa():
    """§9.4 — a regra é repetida nos dois lados (o worker não importa `app/`): o que a tool aceita, o
    worker aceita, e com o MESMO dia."""
    for d in ("05/10/2026", "5/1/2026", "05-10-2026", "05.10.2026", "2026-10-05", "29/02/2028",
              "29/02/2026", "31/04/2026", "ontem", "", "05/10/26"):
        assert PP.data_do_dano_iso(d) in ("", AF.data_iso(d)), d
        if PP.data_do_dano_iso(d):
            assert AF.data_iso(d) == PP.data_do_dano_iso(d)


# ═════════════════════════════════════════════════════════════════════════════
# 2 · A 2ª REDE NO WORKER: cada campo da lista "faltou" para ANTES do POST (era o DOM)
# ═════════════════════════════════════════════════════════════════════════════
def _sem(params, caminhos: str):
    """O job SEM o dado (`a.b|c.d`: todos os lugares de onde o motor o lê — o contrato A↔C cai para
    `solicitante`/`segurado` quando `contato` vem vazio)."""
    p = copy.deepcopy(params)
    for caminho in caminhos.split("|"):
        alvo = p
        partes = caminho.split(".")
        for parte in partes[:-1]:
            alvo = alvo[parte]
        alvo[partes[-1]] = "" if partes[-1] != "cidade_servico" else {"uf": "", "cidade": ""}
    return p


FALTAS = [  # (o que some do job, a parada, o segurado responde?)
    ("cpf_cnpj", ST.PARADA_PEDIDO_INCOMPLETO, False),
    ("placa", ST.PARADA_PEDIDO_INCOMPLETO, False),
    ("data_dano", ST.PARADA_PEDIDO_INCOMPLETO, False),
    ("dano.peca", ST.PARADA_FALTOU_PECA, True),
    ("dano.como", ST.PARADA_FALTOU_COMO, True),
    ("dano.onde", ST.PARADA_FALTOU_ONDE, True),
    ("local.cidade_servico", ST.PARADA_FALTOU_CIDADE, True),
    ("dano.descricao", ST.PARADA_FALTOU_DESCRICAO, True),
    ("contato.documento_corretor|solicitante.cpf_cnpj", ST.PARADA_CADASTRO_DA_CORRETORA, False),
    ("contato.telefone|segurado.telefone|solicitante.telefone", ST.PARADA_CADASTRO_DA_CORRETORA, False),
]


@pytest.mark.parametrize("campo,stage,do_segurado", FALTAS)
def test_cada_falta_para_antes_do_POST_e_nunca_cai_no_DOM(campo, stage, do_segurado):
    r, ev, page = _abrir(_sem(_params_completos(), campo))
    assert r.status == "needs_human" and ev["stage"] == stage
    assert page.quantas("POST", "/atendimentos") == 0 and page.escritas() == []   # NADA escrito
    assert ev["api_first"]["usado"] is True and ev["api_first"]["antes_da_fronteira"] is True
    assert "caiu para o caminho DOM" not in json.dumps(ev.get("api_first"))
    cont = ev["continuacao"]
    assert cont["etapa"] == "abertura" and cont["sessao_guardada"] is False and cont["sessao_cifrada"] == ""
    assert PP.continuacao_possivel(ev) is do_segurado
    assert (PP.acao_esperada(ev)[0] == "responder") is do_segurado
    assert not G.tem_prova_de_efeito(ev) and G.pode_repetir_com_seguranca(ev)
    # a pergunta sai em PORTUGUÊS e nunca diz que algo foi aberto
    texto = PP.format_result({"status": "needs_human", "evidence": ev})
    para_ele = texto.split("[para a equipe")[0]
    assert "Ainda NAO abri nada na seguradora" in para_ele
    assert "pedido esta aberto" not in para_ele and "NUMERO DO ATENDIMENTO" not in texto
    if do_segurado:
        assert PP._EU_CONTINUO in para_ele and "[para voce, agente] Este pedido PODE CONTINUAR" in texto


def test_CONTROLE_o_pedido_completo_segue_ate_o_desfecho_do_HAR():
    r, ev, page = _abrir(_params_completos())
    assert r.status == "done" and (ev.get("desfecho") or {}).get("tipo") == ST.DESFECHO_LOJA_DIRETA
    assert page.quantas("POST", "/atendimentos") == 1
    assert "antes_da_fronteira" not in (ev.get("api_first") or {})


# ── G2 no API-first: o CEP do PATCH é o do lugar do SERVIÇO, nunca o do cadastro de outra cidade ──
def test_o_PATCH_nunca_leva_o_CEP_do_cadastro_de_OUTRA_cidade():
    info = copy.deepcopy(INFOCAP)
    info["client"]["cidade"] = "Cidade Do Cadastro"          # mora noutra cidade; o serviço é na do HAR
    params, erro = PP.build_portal_params(copy.deepcopy(FLAT), dict(PROFILE), info, enviar_de_verdade=True)
    assert erro is None and params["local"]["cep"]            # o cadastro TEM CEP — e ele não pode ir
    params["_idempotency_key"] = PP.chave_de_idempotencia(params, EMPRESA)
    r, ev, page = _abrir(params)
    assert page.corpo_de("PATCH", "/atendimentos")["Cep"] == ""
    assert ev["cep_do_servico"] == {"origem": "ausente"}


def test_CONTROLE_mesma_cidade_o_CEP_do_cadastro_vai_e_e_o_do_HAR():
    r, ev, page = _abrir(_params_completos())
    cep_har = str((RV.primeira(HAR, "PATCH", "/atendimentos", requisicao=True) or {}).get("Cep") or "")
    assert cep_har and page.corpo_de("PATCH", "/atendimentos")["Cep"] == cep_har
    assert ev["cep_do_servico"] == {"origem": "cadastro_na_mesma_cidade"}


def test_cep_do_servico_pura():
    base = {"cidade": "Palhoca", "estado": "SC", "cep": "88130000"}
    assert AF.cep_do_servico({**base, "cidade_servico": {"uf": "SC", "cidade": "Joinville"}}) == ("", "ausente")
    assert AF.cep_do_servico({**base, "cidade_servico": {"uf": "SC", "cidade": "Palhoça"}}) == (
        "88130000", "cadastro_na_mesma_cidade")
    assert AF.cep_do_servico({**base, "cidade_servico": {"uf": "PR", "cidade": "Palhoca"}})[0] == ""
    assert AF.cep_do_servico({**base, "cidade_servico": {"uf": "SC", "cidade": "Joinville",
                                                         "cep": "89201-000"}}) == ("89201000", "servico")


# ── o preflight: resposta do portal → parada; transporte fora → DOM (o legítimo) ──────────
@pytest.mark.parametrize("corpo,status,stage", [
    ({"ApoliceNaoEncontrada": True, "MaisDeUmaApoliceEncontrada": False}, 200, ST.PARADA_APOLICE_NAO_ENCONTRADA),
    ({"ApoliceNaoEncontrada": False, "MaisDeUmaApoliceEncontrada": True}, 200, ST.PARADA_PREFLIGHT_AMBIGUO),
    ({"Tipo": "RegraDeNegocioExcecao", "Message": "regra nova"}, 400, ST.PARADA_REGRA_DESCONHECIDA),
])
def test_o_preflight_que_nao_acha_UMA_apolice_para_antes_e_vai_a_equipe(corpo, status, stage):
    r, ev, page = _abrir(_params_completos(), har=_har_com("/apolices", corpo, status=status))
    assert ev["stage"] == stage and page.escritas() == []
    assert PP.continuacao_possivel(ev) is False and ev["continuacao"]["etapa"] == "abertura"


def test_CONTROLE_api_fora_no_preflight_continua_indo_ao_DOM():
    """O DOM fica para API fora: o MOTOR devolve `None` (a porta de entrada então cai no navegador)."""
    page = RV.PaginaDeReplay(_har_com("/apolices", {}, status=503))
    ev: dict = {}
    p = {**_params_completos(), "_runtime": RT(True)}
    assert asyncio.run(AF.abrir_atendimento_api(page, p, ev)) is None
    assert ev["api_first"]["usado"] is False and page.escritas() == []


# ── D-127-C: a dedup do PRÓPRIO portal, logo depois do POST, com o token ─────────────────
def test_outro_atendimento_aberto_para_o_carro_para_logo_depois_do_POST():
    r, ev, page = _abrir(_params_completos(),
                         har=_har_com("/atendimentos/atendimentos-abertos-existentes", True))
    assert ev["stage"] == ST.PARADA_ATENDIMENTO_ABERTO_EXISTENTE
    assert page.escritas() == [("POST", "/atendimentos")]          # nada DEPOIS do rascunho
    assert PP.continuacao_possivel(ev) is False and ev["aberto_existente"]["existe"] is True
    assert "NUNCA abra um novo" in PP.format_result({"status": "needs_human", "evidence": ev})


def test_CONTROLE_a_dedup_sai_depois_do_POST_com_o_token_e_false_segue():
    r, ev, page = _abrir(_params_completos())
    i_post = page.ordem_de("POST", "/atendimentos")
    i_ded = page.ordem_de("GET", "/atendimentos/atendimentos-abertos-existentes")
    assert 0 <= i_post < i_ded
    assert API.HEADER_TOKEN in page.registro[i_ded]["cabecalhos"]
    assert ev["aberto_existente"] == {"consultado": True, "status": 200, "existe": False}
    assert r.status == "done"


# ═════════════════════════════════════════════════════════════════════════════
# 3 · O FIO INTEIRO: a tool, o portão do ok, o worker, a pergunta, a resposta, a continuação
# ═════════════════════════════════════════════════════════════════════════════
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

    def eq(self, c, v):
        self.f[c] = v
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return self.banco.executar(self)


def _campo(linha, chave):
    if chave.startswith("params->>"):
        return str((linha.get("params") or {}).get(chave.split(">>", 1)[1]) or "")
    return linha.get(chave)


class _Resp:
    def __init__(self, data):
        self.data = data


class Banco:
    """`portal_jobs` (com o worker dublado SÓ na fila) + a conversa durável (`SupabaseDuble`)."""

    def __init__(self, falas, *, sem_no_job=None):
        self.jobs: list = []
        self.paginas: list = []
        self.erros: list = []
        self.sem_no_job = sem_no_job
        self.conversa = SupabaseDuble({"conversations": [{"id": CONVERSA, "company_id": EMPRESA,
                                                          "session_id": SESSAO, "channel": "whatsapp"}],
                                       "messages": []})
        self.client = self
        for quem, texto in falas:
            self.falar(quem, texto)

    def falar(self, quem, texto):
        msgs = self.conversa.tabelas["messages"]
        quando = datetime.now(timezone.utc) - timedelta(seconds=60 - len(msgs))
        msgs.append({"id": f"m{len(msgs)}", "conversation_id": CONVERSA,
                     "role": "user" if quem == "segurado" else "assistant", "content": texto,
                     "payload": {}, "created_at": quando.isoformat()})

    def table(self, nome):
        return _Q(self, nome) if nome == "portal_jobs" else self.conversa.table(nome)

    def executar(self, q):
        if q.op == "insert":
            linha = q.linha
            if linha.get("idempotency_key") and any(
                    j["company_id"] == linha["company_id"] and j.get("idempotency_key") == linha["idempotency_key"]
                    and j.get("status") != "failed" for j in self.jobs):
                raise RuntimeError("duplicate key value violates unique constraint (23505)")
            if linha.get("journey") == "abrir_atendimento" and self.sem_no_job:
                linha["params"] = _sem(linha["params"], self.sem_no_job)     # 🔴 a borda: o job incompleto
            linha.update({"id": f"job-{len(self.jobs) + 1}",
                          "created_at": datetime.now(timezone.utc).isoformat()})
            linha.setdefault("evidence", {})
            self.jobs.append(linha)
            return _Resp([{"id": linha["id"]}])
        achados = [j for j in self.jobs if all(_campo(j, k) == v for k, v in q.f.items())]
        if q.op == "update":
            for j in achados:
                j.update(q.linha)
            return _Resp([])
        if "id" in q.f:
            for j in achados:
                if j.get("status") == "queued":
                    self._worker(j)
        return _Resp(sorted([copy.deepcopy(j) for j in achados],
                            key=lambda j: j.get("created_at", ""), reverse=True))

    def _worker(self, job):
        """O worker, dublado só na fila: a porta de entrada REAL da journey, sobre o HAR."""
        params = {**copy.deepcopy(job["params"]), "_runtime": RT(bool(job["params"].get("confirm")))}
        fn = VL.abrir_atendimento if job["journey"] == "abrir_atendimento" else VC.continuar_atendimento
        page = RV.PaginaDeReplay(HAR)
        ev = dict(job.get("evidence") or {})
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            try:
                r = ex.submit(asyncio.run, fn(page, params, ev)).result()
            except Exception as exc:  # noqa: BLE001 — o DOM numa página de replay explode: é o vermelho
                self.erros.append(type(exc).__name__)
                job.update({"status": "failed", "error": type(exc).__name__})
                return
        self.paginas.append(page)
        job.update({"status": r.status, "evidence": _evidencia_do_worker(r, ev)})

    def posts(self):
        return sum(p.quantas("POST", "/atendimentos") for p in self.paginas)


class Portal(PT.PortalActionTool):
    async def _fetch_infocap(self, cpf, policy_number):  # noqa: D102 — a InfoCap é rede
        return copy.deepcopy(INFOCAP)

    def _load_profile(self):  # noqa: D102 — o perfil da corretora (banco)
        return dict(PROFILE)

    async def _garantir_work_run(self, **_k):  # noqa: D102
        return None

    async def _fechar_work_run(self, run_id, job):  # noqa: D102
        return None

    def _attendance_agent_id(self):  # noqa: D102
        return None


@pytest.fixture
def mundo(monkeypatch):
    import app.services.tela_cega as TC

    estado = {"notificacoes": [], "liberado": True}

    async def _nada(**_k):
        return True

    async def _liberado(self, cpf="", journey="abrir_atendimento"):
        return estado["liberado"]

    monkeypatch.setattr(TC, "registrar_tela_cega", _nada)
    monkeypatch.setattr(PT, "POLL_EVERY_S", 0)
    monkeypatch.setattr(PT, "POLL_TIMEOUT_S", 30)
    monkeypatch.setattr(Portal, "_envio_liberado", _liberado)
    monkeypatch.setattr(Portal, "_notify", lambda self, *a, **k: estado["notificacoes"].append(a))
    return estado


def _chamar(banco, **extra):
    flat = {**copy.deepcopy(FLAT), **extra}
    return asyncio.run(Portal(company_id=EMPRESA, supabase_client=banco)._arun(**flat, session_id=SESSAO))


def test_o_FIO_do_pedido_de_vidro_ok_parada_pergunta_resposta_e_UM_POST(mundo):
    banco = Banco([("segurado", "oi, quebrou o para-brisa do meu carro, quero trocar")],
                  sem_no_job="local.cidade_servico")
    with BC.classificador_duble_na_borda() as classificador:
        # ① 1º turno, sem o resumo nem o "sim": NADA criado; a LINHA PRONTA volta ao agente
        r1 = _chamar(banco)
        assert r1["status"] == "confirm_first" and banco.jobs == [] and classificador == []
        linha = r1["linha_pronta"]
        assert linha == PP.linha_de_confirmacao_do_vidro(_params_completos())
        assert linha.startswith("Confirma: ") and linha.endswith("posso acionar?")
        assert "para-brisa" in linha and f"placa final {PLACA[-4:]}" in linha and PLACA not in linha
        cidade = INFOCAP["client"]["cidade"]
        assert f"com o serviço em {cidade}/" in linha
        assert "NADA foi acionado" in r1["content"] and f"«{linha}»" in r1["content"]

        # ② o agente manda a linha; "pode deixar" NÃO é o ok (com o classificador dizendo ok)
        banco.falar("agente", linha)
        banco.falar("segurado", "pode deixar")
        r2 = _chamar(banco)
        assert r2["status"] == "confirm_first" and banco.jobs == [] and classificador == []

        # ③ "pode mandar" → o portão (regex E classificador, UMA chamada) → UM job
        banco.falar("agente", linha)
        banco.falar("segurado", "pode mandar")
        r3 = _chamar(banco)
        assert len(classificador) == 1 and classificador[0]["papel"] == "confirmacao"
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]
    assert banco.erros == [], banco.erros                       # nunca o DOM
    ab = banco.jobs[0]
    assert ab["status"] == "needs_human" and ab["evidence"]["stage"] == ST.PARADA_FALTOU_CIDADE
    assert banco.posts() == 0                                    # a parada é ANTES da escrita
    assert "Em qual CIDADE e ESTADO" in r3["content"]
    assert "especificos.cidade_para_o_servico" in r3["content"]

    # ④ a resposta do segurado → o MESMO pedido continua (nunca outro abrir_atendimento)
    r4 = _chamar(banco)
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento", "continuar_atendimento"]
    cont = banco.jobs[1]
    assert cont["params"]["_continuacao"]["operacao"] == "responder"
    assert set(cont["params"]["_continuacao"]["respostas"]) == {"cidade_servico"}
    assert cont["params"]["_pedido_key"] == ab["idempotency_key"]
    assert cont["evidence"]["continuacao_pedida"].get("recomecou_a_abertura") is True
    # ⑤ UM POST no total e o desfecho do HAR
    assert banco.posts() == 1, banco.posts()
    assert cont["status"] == "done"
    assert (cont["evidence"].get("desfecho") or {}).get("tipo") == ST.DESFECHO_LOJA_DIRETA
    assert "O atendimento FOI ABERTO" in r4["content"]


def test_a_2a_resposta_igual_nao_cria_2a_continuacao(mundo):
    banco = Banco([], sem_no_job="local.cidade_servico")
    with BC.classificador_duble_na_borda():
        banco.falar("segurado", "quebrou o para-brisa")
        banco.falar("agente", PP.linha_de_confirmacao_do_vidro(_params_completos()))
        banco.falar("segurado", "pode mandar")
        _chamar(banco)
        _chamar(banco)
        _chamar(banco)             # o pedido já concluiu: a mesma chamada não reabre nada
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento", "continuar_atendimento"]
    assert banco.posts() == 1


def test_duas_faltas_em_seguida_a_2a_resposta_nao_apaga_a_1a(mundo):
    """Faltavam a peça E a cidade: a 1ª resposta recomeça e para na 2ª falta; a 2ª continuação leva AS DUAS
    respostas (nada estava no portal) → 1 POST e o desfecho."""
    banco = Banco([], sem_no_job="dano.peca|local.cidade_servico")
    with BC.classificador_duble_na_borda():
        banco.falar("segurado", "quebrou o para-brisa")
        banco.falar("agente", PP.linha_de_confirmacao_do_vidro(_params_completos()))
        banco.falar("segurado", "pode mandar")
        _chamar(banco)
    assert banco.jobs[0]["evidence"]["stage"] == ST.PARADA_FALTOU_PECA
    _chamar(banco, especificos={**FLAT["especificos"], "peca": "para-brisa"})
    assert banco.jobs[1]["evidence"]["stage"] == ST.PARADA_FALTOU_CIDADE and banco.posts() == 0
    r = _chamar(banco, especificos={**FLAT["especificos"], "peca": "para-brisa"})
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"] + ["continuar_atendimento"] * 2
    assert set(banco.jobs[2]["params"]["_continuacao"]["respostas"]) == {"peca", "cidade_servico"}
    assert banco.posts() == 1 and banco.jobs[2]["status"] == "done"
    assert "O atendimento FOI ABERTO" in r["content"]


def test_classificador_fora_do_ar_nada_e_criado(mundo, monkeypatch):
    from app.factories import llm_factory as LF

    async def _fora(papel, mensagens, **_k):
        raise TimeoutError("fora")

    monkeypatch.setattr(LF, "invocar_com_reserva", _fora)
    banco = Banco([("segurado", "quebrou o para-brisa")])
    banco.falar("agente", PP.linha_de_confirmacao_do_vidro(_params_completos()))
    banco.falar("segurado", "pode mandar")
    r = _chamar(banco)
    assert r["status"] == "confirm_first" and banco.jobs == []


def test_o_parente_recebe_a_linha_sem_a_placa(mundo, monkeypatch):
    async def _parente(self, session_id):
        return True

    monkeypatch.setattr(Portal, "_apolice_de_outra_pessoa", _parente)
    banco = Banco([("segurado", "o para-brisa do carro do meu pai quebrou")])
    with BC.classificador_duble_na_borda():
        r = _chamar(banco)
    assert r["status"] == "confirm_first" and "placa" not in r["linha_pronta"]
    assert PLACA[-4:] not in r["linha_pronta"]


def test_o_sim_de_um_pedido_anterior_nao_abre_outro(mundo):
    """O FATO durável gasta a confirmação: o "sim" do para-brisa não abre a lanterna (RT-B3 da 126)."""
    banco = Banco([])
    with BC.classificador_duble_na_borda():
        banco.falar("segurado", "quebrou o para-brisa")
        banco.falar("agente", PP.linha_de_confirmacao_do_vidro(_params_completos()))
        banco.falar("segurado", "pode mandar")
        _chamar(banco)
        assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]
        r = _chamar(banco, peca="lanterna traseira esquerda",
                    especificos={**FLAT["especificos"], "lado_motorista_ou_carona": "motorista"})
    assert r.get("status") == "confirm_first", r.get("content", "")[:120]
    assert len(banco.jobs) == 1


def test_CONTROLE_o_que_ja_protegia_o_portal_continua_agente_desligado_para_no_80(mundo):
    """O ok não LIGA nada: com o agente desligado/freio armado (`envio_liberado` False), o job nasce com
    `confirm=False` e o guard da fronteira A segura o POST, como sempre."""
    mundo["liberado"] = False
    banco = Banco([])
    with BC.classificador_duble_na_borda():
        banco.falar("segurado", "quebrou o para-brisa")
        banco.falar("agente", PP.linha_de_confirmacao_do_vidro(_params_completos()))
        banco.falar("segurado", "pode mandar")
        _chamar(banco)
    assert banco.jobs[0]["params"]["confirm"] is False
    assert banco.jobs[0]["evidence"]["stage"] == "pronto_para_abrir" and banco.posts() == 0


def test_CONTROLE_a_allowlist_malformada_do_canario_continua_barrando(monkeypatch):
    import app.services.atlas.attendance_capture as AC

    async def _ligado(_c):
        return True

    monkeypatch.setattr(AC, "attendance_agent_active", _ligado)
    monkeypatch.setenv("PORTAL_EFEITO_MATERIAL_LIBERADO", "1")
    monkeypatch.setenv("PORTAL_CANARIO_ALLOWLIST", " , ")
    assert asyncio.run(PT.envio_liberado(EMPRESA, FLAT["cpf_cnpj"])) is False
