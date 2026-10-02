# -*- coding: utf-8 -*-
"""SPEC-125 S3 · D2/M3/M5 — o segurado reconhecido pelo telefone, NA MESMA corretora.

Motor REAL (`quem_e_o_segurado`, `attendance_ficha`, `MemoryService`,
`InfocapPolicyLookupTool._risco_na_ficha`); dublê só na BORDA — um banco em
memória que aplica `eq`/`in_`/`or_`/`order`/`limit` de verdade, para o
isolamento entre corretoras ser medido e não presumido (CLAUDE.md §7, §9.4).
Dados 100% fictícios: CPF gerado (dígito verificador válido), telefones de teste.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.agents import quem_e_o_segurado as Q
from app.services import attendance_ficha as F

# ---- dados fictícios ---------------------------------------------------------
EMPRESA_A = str(uuid.uuid4())
EMPRESA_B = str(uuid.uuid4())
AGENTE_A = str(uuid.uuid4())
OUTRO_AGENTE = str(uuid.uuid4())
FONE = "5547900001111"            # o MESMO telefone nas duas corretoras
CPF = "52998224725"               # fictício, dígito verificador válido
CPF_FMT = "529.982.247-25"
AGORA = datetime.now(timezone.utc)


def _iso(dias: float = 0, minutos: float = 0) -> str:
    return (AGORA - timedelta(days=dias, minutes=minutos)).isoformat()


# ---- o dublê da borda: um PostgREST em memória que FILTRA de verdade ---------
class _R:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.f, self.n, self.ordem = banco, tabela, [], None, None
        self.op, self.payload = "select", None

    def select(self, *_a, **_k):
        return self

    def update(self, dados):
        self.op, self.payload = "update", dados
        return self

    def eq(self, c, v):
        if not (self.banco.ignora_empresa and c == "company_id"):
            self.f.append(lambda l, c=c, v=v: str(l.get(c)) == str(v))
        return self

    def in_(self, c, vs):
        vs = {str(x) for x in vs}
        self.f.append(lambda l: str(l.get(c)) in vs)
        return self

    def or_(self, expr):
        # só o dialeto que o produto usa: "col.eq.X,col.is.null"
        regras = []
        for parte in expr.split(","):
            col, op, val = parte.split(".", 2)
            regras.append((col, op, val))
        self.f.append(lambda l: any((op == "eq" and str(l.get(col)) == val)
                                    or (op == "is" and val == "null" and l.get(col) is None)
                                    for col, op, val in regras))
        return self

    def order(self, col, desc=False, **_k):
        self.ordem = (col, desc)
        return self

    def limit(self, n):
        self.n = n
        return self

    def execute(self):
        linhas = [l for l in self.banco.t.get(self.tabela, []) if all(f(l) for f in self.f)]
        if self.op == "update":
            for l in linhas:
                l.update(self.payload)
            return _R(linhas)
        if self.ordem:
            linhas.sort(key=lambda l: str(l.get(self.ordem[0]) or ""), reverse=self.ordem[1])
        return _R([dict(l) for l in linhas[: self.n or None]])


class Banco:
    def __init__(self, ignora_empresa: bool = False):
        self.t = {}
        self.ignora_empresa = ignora_empresa   # MUTAÇÃO: o código sem o `.eq(company_id)`
        self.client = self

    def table(self, nome):
        return _Q(self, nome)


def _apolice_do_caso(empresa: str) -> dict:
    return {"versao": 1, "company_id": empresa, "selecionada": "k1",
            "apolices": [{"chave": "k1", "numapo": "7001234", "ramo": "auto", "seguradora": "porto",
                          "vigencia_fim": "2027-03-10", "vigente": True}]}


def _semear(banco: Banco, empresa: str, *, mensagens, user_name="", ficha=None, resumos=(),
            grafia: str = FONE):
    conv, user = str(uuid.uuid4()), str(uuid.uuid4())
    banco.t.setdefault("conversations", []).append({
        "id": conv, "company_id": empresa, "user_id": user, "user_name": user_name,
        "session_id": f"whatsapp:{FONE}:{empresa}:default", "channel": "whatsapp",
        "user_phone": grafia, "ficha_atendimento": ficha, "updated_at": _iso(0)})
    for role, texto, quando in mensagens:
        banco.t.setdefault("messages", []).append({
            "conversation_id": conv, "role": role, "content": texto, "created_at": quando, "payload": {}})
    for texto, quando in resumos:
        banco.t.setdefault("session_summaries", []).append({
            "company_id": empresa, "user_id": user, "agent_id": None, "summary": texto, "created_at": quando})
    return conv


def _o_fio(banco: Banco) -> None:
    """Corretora A: o CPF foi dito na msg 3 de um assunto de 40 dias atrás; hoje, assunto novo."""
    ficha = F.fundir(F.ficha_vazia(), {
        F.CHAVE_DO_CONTEXTO_DA_APOLICE: _apolice_do_caso(EMPRESA_A),
        "confirmados": {"veiculo_descricao": F.confirmacao("Onix 1.0", F.ORIGEM_SISTEMA_DE_GESTAO)}})
    _semear(banco, EMPRESA_A, user_name="5547900001111", ficha=ficha, mensagens=[
        ("user", "oi, preciso de um guincho", _iso(40, 30)),
        ("assistant", "Claro! Pode me passar o CPF do titular?", _iso(40, 29)),
        ("user", f"meu nome é joão, cpf {CPF_FMT}", _iso(40, 28)),
        ("assistant", "Obrigada, João. Acionei o guincho.", _iso(40, 20)),
        ("user", "bati o carro hoje cedo, o que eu faço?", _iso(0, 1)),
    ], resumos=[("Guincho acionado para o Onix; segurado satisfeito.", _iso(39))])


def _quem(banco, empresa, historico=None):
    return asyncio.run(Q.quem_e_o_segurado(empresa, FONE, historico, db=banco, n_dias=7))


# ---- 1. O FIO ------------------------------------------------------------------
def test_o_fio_o_cpf_de_um_assunto_anterior_vira_confirmacao_e_nao_pergunta():
    banco = Banco()
    _o_fio(banco)
    quem = _quem(banco, EMPRESA_A)

    # 🔴 Conserto X2 (§9.3 — a verdade mudou): o CPF de um assunto ANTERIOR não volta
    #    inteiro (o telefone pode ser de outra pessoa agora, D2). Vai o FINAL, para
    #    confirmar; o número só entra depois do "sim" dele no assunto atual
    #    (`test_spec125_conserto_x.py::test_x2_depois_do_sim…`). A lição — não perguntar
    #    do zero — continua: `perguntar_cpf` é False e o bloco manda confirmar.
    assert quem["cpf"] == "" and quem["cpf_final"] == "4725" and quem["perguntar_cpf"] is False
    assert quem["cpf_de_assunto_anterior"] is True       # veio de antes do reencontro
    assert quem["cpf_mascarado"].endswith("4725") and CPF not in quem["cpf_mascarado"]
    assert (quem["nome"], quem["nome_origem"]) == ("João", "dito pelo segurado")
    assert "7001234" in quem["apolice"] and "Onix 1.0" in quem["apolice"]
    assert "Guincho acionado" in quem["caso_anterior"]

    bloco = Q.bloco_para_o_prompt(quem)
    assert len(bloco) <= Q.TETO_DO_BLOCO
    for trecho in ("João", "final 4725", "7001234", "num assunto anterior", "não pergunte", "confirme"):
        assert trecho in bloco, trecho
    assert CPF not in bloco


def test_o_historico_entregue_pela_s2_e_a_fonte_quando_vem():
    """Com `historico` na mão, o motor usa ELE (a fonte única da S2), não relê `messages`."""
    banco = Banco()
    _o_fio(banco)
    so_hoje = [{"role": "user", "content": "bati o carro", "created_at": _iso(0, 1)}]
    quem = _quem(banco, EMPRESA_A, historico=so_hoje)
    assert quem["cpf"] == "" and quem["perguntar_cpf"] is True


@pytest.mark.parametrize("grafia", [FONE, FONE[2:], "554700001111", "4700001111"])
def test_a_conversa_e_achada_em_toda_grafia_do_numero(grafia):
    """📊 905 de 1.081 conversas guardam o número COM o 55 — a grafia majoritária
    tem de ser achada (a 1ª versão, só com `_variantes_do_telefone`, não achava)."""
    banco = Banco()
    _semear(banco, EMPRESA_A, user_name="Ana Lima", grafia=grafia,
            mensagens=[("user", "oi", _iso(0, 2))])
    assert _quem(banco, EMPRESA_A)["nome"] == "Ana"


# ---- 2. DUAS CORRETORAS, O MESMO TELEFONE ---------------------------------------
def _dois_tenants(banco: Banco):
    _o_fio(banco)                                       # A: tem CPF, nome, apólice, caso anterior
    _semear(banco, EMPRESA_B, user_name="Maria Souza", mensagens=[
        ("user", "boa tarde, o vidro do carro quebrou", _iso(0, 2))])
    return _quem(banco, EMPRESA_A), _quem(banco, EMPRESA_B)


def _vazou(de_a: dict, de_b: dict) -> bool:
    texto_b = repr(de_b) + Q.bloco_para_o_prompt(de_b)
    texto_a = repr(de_a) + Q.bloco_para_o_prompt(de_a)
    return any(x in texto_b for x in (CPF, "4725", "João", "7001234", "Guincho")) or "Maria" in texto_a


def test_o_mesmo_telefone_em_duas_corretoras_nada_atravessa():
    de_a, de_b = _dois_tenants(Banco())
    assert de_a["cpf_final"] == "4725" and de_a["nome"] == "João"     # X2: assunto anterior = só o final
    assert de_b["cpf"] == "" and de_b["perguntar_cpf"] is True
    assert (de_b["nome"], de_b["nome_origem"]) == ("Maria", "contato do WhatsApp")
    assert de_b["apolice"] == "" and de_b["caso_anterior"] == ""
    assert not _vazou(de_a, de_b)


def test_sem_o_eq_do_banco_o_cinto_no_codigo_ainda_segura():
    """Metade da mutação: o `.eq(company_id)` some — o cinto (`_da_corretora`) segura."""
    assert not _vazou(*_dois_tenants(Banco(ignora_empresa=True)))


def test_MUTACAO_sem_o_filtro_de_corretora_o_guarda_fica_vermelho(monkeypatch):
    """§9.3: o guarda acima CONSEGUE falhar. Sem o `.eq` E sem o cinto, A vaza para B."""
    monkeypatch.setattr(Q, "_da_corretora", lambda linhas, empresa: [x for x in (linhas or [])
                                                                     if isinstance(x, dict)])
    assert _vazou(*_dois_tenants(Banco(ignora_empresa=True)))


# ---- 3. SEM CPF, NADA INVENTADO -----------------------------------------------------
def test_sem_cpf_na_conversa_nada_e_inventado_e_a_pergunta_e_normal():
    banco = Banco()
    _semear(banco, EMPRESA_A, user_name="47 99999-0000", mensagens=[
        ("user", "meu celular é 47999990000 e o protocolo 12345678901", _iso(0, 3)),
        ("user", "sou a segurada, o carro não liga", _iso(0, 2))])
    quem = _quem(banco, EMPRESA_A)
    # celular não é CPF; 11 dígitos sem dígito verificador válido não é CPF; "segurada" não é nome
    assert quem == {**Q.identidade_vazia()}
    assert Q.bloco_para_o_prompt(quem) == ""


def test_telefone_desconhecido_ou_sem_corretora_devolve_vazio():
    assert _quem(Banco(), EMPRESA_A) == Q.identidade_vazia()
    assert asyncio.run(Q.quem_e_o_segurado("", FONE, db=Banco())) == Q.identidade_vazia()


def test_dois_cpfs_ditos_o_ultimo_vale_e_o_bloco_manda_confirmar_qual():
    # 🔴 Conserto X2 (§9.3): antes o 2º CPF era "o titular é meu pai, CPF …" — e o bloco o
    #    oferecia como dele. Agora o CPF atribuído a outra pessoa nunca é oferecido
    #    (`test_spec125_conserto_x.py::test_x2_nem_no_mesmo_assunto…`); a lição do "disse
    #    dois, confirme qual" migra para dois CPFs que ele disse como seus.
    outro = "11144477735"
    hist = [{"role": "user", "content": f"cpf {CPF_FMT}", "created_at": _iso(0, 9)},
            {"role": "user", "content": f"opa, digitei errado, o cpf certo é {outro}", "created_at": _iso(0, 5)}]
    quem = Q.montar(historico=hist, n_dias=7)
    assert quem["cpf"] == outro and quem["cpfs_distintos"] == 2
    assert "confirme qual" in Q.bloco_para_o_prompt(quem)


def test_cpf_dito_pela_corretora_nao_conta():
    hist = [{"role": "assistant", "content": f"O CPF {CPF_FMT} está certo?", "created_at": _iso(0, 2)}]
    assert Q.montar(historico=hist)["cpf"] == ""


def test_o_bloco_respeita_o_teto_cortando_so_o_caso_anterior():
    quem = {**Q.identidade_vazia(), "nome": "João", "nome_origem": "dito pelo segurado", "cpf": CPF,
            "apolice": "7001234 · automóvel · Porto · vigente até 2027-03-10 · Onix 1.0",
            "caso_anterior": "em 01/08/2026: " + "x" * 900}
    bloco = Q.bloco_para_o_prompt(quem)
    assert len(bloco) <= Q.TETO_DO_BLOCO and CPF in bloco and "ignore este bloco" in bloco


# ---- 4. M3 — o risco da apólice vai para a ficha ------------------------------------
def test_m3_auto_placa_e_veiculo_entram_como_sistema_de_gestao():
    data = {"vehicle_info": {"placa": "ABC1D23", "veiculo": "Onix 1.0"}}
    nov = F.novidades_do_risco(data, "auto")
    ficha = F.fundir(F.ficha_vazia(), nov)
    assert {k: F.origem_de(v) for k, v in ficha["confirmados"].items()} == {
        "veiculo_placa": F.ORIGEM_SISTEMA_DE_GESTAO, "veiculo_descricao": F.ORIGEM_SISTEMA_DE_GESTAO}
    bloco = F.bloco_para_o_prompt(ficha)
    assert "Veio do sistema de gestão" in bloco and "ABC1D23" in bloco and "Onix 1.0" in bloco
    # e o banco de respostas da URA recebe a placa CRUA (mascarada ela não serviria)
    assert F.dados_conhecidos(ficha)["veiculo_placa"] == "ABC1D23"


def test_m3_residencial_a_cidade_do_risco_e_a_do_atendimento_mas_frota_nao():
    um = {"policy_evidence_pack": {"risk_objects": [{"city": "Joinville", "state": "SC"}]}}
    assert set(F.novidades_do_risco(um, "resi")["confirmados"]) == {"local_cidade", "local_uf"}
    frota = {"policy_evidence_pack": {"risk_objects": [{"city": "A"}, {"city": "B"}]}}
    assert F.novidades_do_risco(frota, "resi") == {}
    # auto NÃO grava cidade (o carro quebra fora da cidade da apólice)
    assert F.novidades_do_risco(um, "auto") == {}
    assert F.novidades_do_risco({"vehicle_info": {"placa": "X"}}, "vida") == {}


def test_m3_o_que_o_segurado_disse_nao_e_sobrescrito_pelo_cadastro():
    ficha = F.fundir(F.ficha_vazia(), {"confirmados": {"veiculo_placa": F.confirmacao("NOV0A00")}})
    nov = F.novidades_do_risco({"vehicle_info": {"placa": "ABC1D23", "veiculo": "Onix"}}, "auto", ficha=ficha)
    assert set(nov["confirmados"]) == {"veiculo_descricao"}
    assert F.valor_de(F.fundir(ficha, nov)["confirmados"]["veiculo_placa"]) == "NOV0A00"


def test_m3_nenhum_documento_nem_nome_vai_para_a_ficha_duravel():
    data = {"vehicle_info": {"placa": "ABC1D23", "veiculo": "Onix", "telefone_cliente": "47999990000"},
            "client_document": CPF, "client_name": "João da Silva"}
    texto = repr(F.novidades_do_risco(data, "auto"))
    assert CPF not in texto and "João" not in texto and "47999990000" not in texto


def test_m3_a_tool_grava_o_risco_na_ficha_desta_corretora_e_so_nela(monkeypatch):
    """Motor real da tool (`_risco_na_ficha`) → `attendance_ficha.gravar` → banco dublê."""
    import app.core.database as _db
    from app.agents.tools.infocap_tool import InfocapPolicyLookupTool

    banco = Banco()
    sessao = f"whatsapp:{FONE}:x:default"
    for emp in (EMPRESA_A, EMPRESA_B):
        banco.t.setdefault("conversations", []).append(
            {"company_id": emp, "session_id": sessao, "ficha_atendimento": None})
    monkeypatch.setattr(_db, "get_supabase_client", lambda *a, **k: banco)
    tool = InfocapPolicyLookupTool(company_id=EMPRESA_A, agent_role="attendance")
    result = {"status": "found", "selected": {"product": "AUTOMOVEL", "numapo": "7001234"},
              "vehicle_info": {"placa": "ABC1D23", "veiculo": "Onix 1.0"}}
    asyncio.run(tool._risco_na_ficha(result, sessao))

    fichas = {c["company_id"]: c["ficha_atendimento"] for c in banco.t["conversations"]}
    assert F.valor_de(fichas[EMPRESA_A]["confirmados"]["veiculo_placa"]) == "ABC1D23"
    assert fichas[EMPRESA_B] is None                              # a outra corretora intacta

    # o Chat Principal (core) não escreve ficha de atendimento
    banco.t["conversations"][0]["ficha_atendimento"] = None
    asyncio.run(InfocapPolicyLookupTool(company_id=EMPRESA_A, agent_role="core")
                ._risco_na_ficha(result, sessao))
    assert banco.t["conversations"][0]["ficha_atendimento"] is None


# ---- 5. M5 — os resumos do espelho chegam ao agente, da MESMA corretora -------------
def _banco_de_resumos() -> tuple:
    banco, user = Banco(), str(uuid.uuid4())
    for emp, agente, texto in ((EMPRESA_A, None, "espelho A"), (EMPRESA_A, AGENTE_A, "agente A"),
                               (EMPRESA_A, OUTRO_AGENTE, "outro agente A"), (EMPRESA_B, None, "espelho B")):
        banco.t.setdefault("session_summaries", []).append(
            {"company_id": emp, "user_id": user, "agent_id": agente, "summary": texto, "created_at": _iso(1)})
    return banco, user


def test_m5_o_agente_le_os_resumos_do_espelho_da_mesma_corretora():
    from app.services.memory_service import MemoryService

    banco, user = _banco_de_resumos()
    lidos = asyncio.run(MemoryService(banco).get_recent_summaries_async(user, EMPRESA_A, limit=10,
                                                                        agent_id=AGENTE_A))
    assert sorted(r["summary"] for r in lidos) == ["agente A", "espelho A"]


def test_m5_controle_o_filtro_antigo_escondia_o_espelho():
    """Linha de CONTROLE (§9.2): o `.eq(agent_id)` de antes, no MESMO banco, perde o espelho."""
    banco, user = _banco_de_resumos()
    antigo = banco.table("session_summaries").select("*").eq("user_id", user) \
        .eq("company_id", EMPRESA_A).eq("agent_id", AGENTE_A).execute().data
    assert [r["summary"] for r in antigo] == ["agente A"]


def test_m5_o_fato_do_proprio_agente_vence_o_do_espelho():
    from app.services.memory_service import MemoryService

    banco, user = Banco(), str(uuid.uuid4())
    for agente, fatos in ((None, ["do espelho"]), (AGENTE_A, ["do agente"])):
        banco.t.setdefault("user_memories", []).append(
            {"company_id": EMPRESA_A, "user_id": user, "agent_id": agente, "facts": fatos})
    mem = asyncio.run(MemoryService(banco).get_user_memory_async(user, EMPRESA_A, agent_id=AGENTE_A))
    assert mem["facts"] == ["do agente"]
    banco.t["user_memories"] = banco.t["user_memories"][:1]
    mem = asyncio.run(MemoryService(banco).get_user_memory_async(user, EMPRESA_A, agent_id=AGENTE_A))
    assert mem["facts"] == ["do espelho"]


@pytest.mark.parametrize("bruto,esperado", [
    ("", ""), (None, ""), ("nao-e-uuid", ""), ("x,agent_id.is.null", ""),
    ("11111111-2222-3333-4444-555555555555",
     "agent_id.eq.11111111-2222-3333-4444-555555555555,agent_id.is.null"),
])
def test_m5_o_filtro_nunca_interpola_o_que_nao_e_uuid(bruto, esperado):
    from app.services.memory_service import filtro_do_agente_com_espelho

    assert filtro_do_agente_com_espelho(bruto) == esperado
