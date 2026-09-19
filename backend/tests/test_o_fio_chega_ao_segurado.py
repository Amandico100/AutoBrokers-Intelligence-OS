# -*- coding: utf-8 -*-
r"""🔴 O FIO INTEIRO — da tool até o WhatsApp (CONSERTO B1 e B2 da EXTRA-001.5.1).

📊 **O QUE O JUIZ MEDIU EM 19/09/2026, NA CÓPIA SÓ DE `backend/`**, e que nenhum
gate da fatia 3 atravessava:

```
B1  `_build_llm_briefing` dava `return` no ramo `if client_facing:` ANTES de
    `_linhas_do_veredito` e do RASCUNHO SEGURO. Nos SEIS estados, a LLM do
    atendimento NUNCA via o veredito; os `if client_facing` de dentro de
    `_linhas_do_veredito` eram código morto; e a linha de `ATTENDANCE_BASE_PROMPT`
    que cita `veredito_de_cobertura` nunca disparava.
B1b em `nao_sabemos_ainda` e `fonte_indisponivel` o contrato saía com
    `required_facts=[]`: um candidato "Sim! tem esse serviço sim" PASSAVA CRU
    pelo guarda de `nodes.py`. Com 0 linhas publicadas na base, isso é quase
    TODA pergunta de cobertura — e a lacuna ainda mandava um 🆘 dizendo
    "eu não afirmei nada", que passaria a ser mentira.
B2  `_lacuna_vira_tarefa` não passava conversa nem telefone. A porta da 001.3
    aceita conversa vazia mas PULA as perguntas 3 e 4 ("conversa assumida?",
    "humano falou há pouco?"): o grupo era avisado POR CIMA da atendente, com um
    texto que mandava "responda ao cliente" sem dizer qual.
```

🔴 **Os gates da fatia 3 mediam o COMPOSITOR e o SERVIÇO, e os dois estavam
certos.** O que chega ao segurado passa por `_render_content` /
`_build_llm_briefing` / `_build_policy_response_contract` e por `_arun` — e por
lá não passava guarda nenhum. É a cegueira da 001.5 um andar acima, e é isto que
este arquivo fecha.

⛔ NENHUMA mensagem sai: a porta do grupo é dublê. ⛔ NENHUMA escrita em
produção: `capability_gaps` é duplo em memória.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tests"))

#: 🔴 A FLAG QUE LIGA O CAMINHO QUE SE QUER MEDIR.
#:
#: `_render_content` só chama o compositor sob `POLICY_INTELLIGENCE_V2`; sem
#: ela cai no resumo legado e `meta` volta `None`. 📊 Em produção ela está
#: LIGADA (a 001.5 a acendeu); aqui ela é declarada para que o guarda meça o
#: caminho vivo, e não o legado.
os.environ["POLICY_INTELLIGENCE_V2"] = "true"

from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

from app.agents.nodes import _guard_infocap_policy_final_response as GUARDA  # noqa: E402
from app.agents.tools.infocap_tool import InfocapPolicyLookupTool  # noqa: E402
from app.agents.tools import infocap_tool as TOOL  # noqa: E402

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _fechar() -> int:
    print()
    print("=" * 74)
    print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
    print("=" * 74)
    return 1 if FAIL else 0


# ---------------------------------------------------------------------------
# A base sintética: um plano publicado e um serviço SEM linha (`nao_sabemos`)
# ---------------------------------------------------------------------------
db = BaseEmMemoria()
AUTO = db.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                plano="Essencial", nivel=1, documento_id="doc-hdi-auto", pagina=9)
db.servico(AUTO, "carro_reserva", "nao", documento_id="doc-hdi-auto", pagina=23)
db.servico(AUTO, "guincho", "sim", documento_id="doc-hdi-auto", pagina=25,
           limite_valor=200, limite_unidade="km")


def _pack():
    return {
        "source": "infocap", "policy_ref": "999001", "insurer_detected": "hdi",
        "product_detected": "Auto Perfil", "line_kind_detected": "auto",
        "policy_status": "ativa", "active_now": True,
        "valid_from": "2026-01-01", "valid_to": "2027-01-01",
        "coverage_sections": [{"label": "Assistência 24h", "amount": None}],
        "structured_coverage_available": True, "structured_coverage_absent": False,
        "installments": [], "limitations": [],
        "assistance_plan": {"plano": "Essencial", "nivel": 1, "estado": "contratado"},
    }


def _result():
    return {"ok": True, "status": "found",
            "selected": {"insurer_key": "hdi", "product": "Auto Perfil",
                         "policy_number": "1234567890", "numapo": "1234567890",
                         "holder_name": "Cliente Sintetico", "policy_status": "ativa",
                         "active_now": True, "valid_from": "2026-01-01",
                         "valid_to": "2027-01-01"},
            "policy_evidence_pack": _pack()}


#: ⚠️ O compositor é chamado pelo `_render_content` SEM `db` (é o que acontece em
#: produção: a Skill monta o cliente síncrono sozinha). Para exercer a base
#: sintética, o duplo entra pelo módulo, no lugar do resolvedor.
from app.services.knowledge import assistance_plans_base as BASE  # noqa: E402

_db_original = BASE._db
BASE._db = lambda supabase_client=None: db


def _fio(pergunta, *, cliente: bool):
    """`(briefing, contrato, rendered)` — o caminho REAL da tool, sem rede."""
    tool = InfocapPolicyLookupTool(
        company_id="11111111-1111-1111-1111-111111111111",
        agent_role=("attendance" if cliente else "core"))
    conteudo, politica, rendered, meta = tool._render_content(
        _result(), pergunta, detail=False, atendente=None)
    contrato = tool._build_policy_response_contract(
        _result(), rendered, politica, client_facing=cliente, meta=meta)
    return conteudo, contrato, rendered, meta


# ---------------------------------------------------------------------------
print("\n[1] 🔴 B1 — o briefing do CLIENTE carrega o veredito e o rascunho")
for rotulo, pergunta, estado in (("nao_coberto", "tem carro reserva?", "nao_coberto"),
                                 ("coberto", "tem guincho?", "coberto"),
                                 ("nao_sabemos_ainda", "tem taxi?", "nao_sabemos_ainda")):
    briefing, contrato, rendered, meta = _fio(pergunta, cliente=True)
    checar((meta.get("cobertura") or {}).get("estado") == estado,
           f"`{rotulo}`: o motor produziu o estado esperado",
           repr((meta.get("cobertura") or {}).get("estado")))
    checar("veredito_de_cobertura" in briefing,
           f"🔴 `{rotulo}`: o briefing do WhatsApp TRAZ `veredito_de_cobertura` "
           "(era o `return` prematuro do ramo do cliente)", briefing[-300:])
    checar("RASCUNHO SEGURO" in briefing and str(rendered).strip() in briefing,
           f"🔴 `{rotulo}`: e traz o RASCUNHO SEGURO **do canal**",
           briefing[-300:])
    checar("CLIENTE FINAL: NUNCA cite documento" in briefing,
           f"`{rotulo}`: a instrução de canal deixou de ser código morto",
           briefing[-300:])
    checar("- fonte: documento" not in briefing,
           f"🔴 `{rotulo}`: e a linha `fonte: documento … pagina` NÃO viaja ao "
           "cliente", briefing[-300:])

print("\n      🔴 CONTROLE: no canal do CORRETOR a fonte CONTINUA no briefing")
briefing_cor, _c, _r, _m = _fio("tem carro reserva?", cliente=False)
checar("veredito_de_cobertura" in briefing_cor and "- fonte: documento" in briefing_cor,
       "🔴 CONTROLE: o corretor recebe veredito E fonte — a ausência acima é do "
       "canal, não de um briefing vazio", briefing_cor[-200:])

print("\n      🔴 a chave que o PROMPT cita é a que o briefing TRAZ (nos dois canais)")
_prompts = open(os.path.join(RAIZ, "app", "core", "prompts.py"),
                encoding="utf-8").read()
checar("veredito_de_cobertura" in _prompts,
       "`prompts.py` cita `veredito_de_cobertura`")
checar("veredito_de_cobertura" in briefing_cor,
       "e o briefing do corretor a traz")

# ---------------------------------------------------------------------------
print("\n[2] 🔴 B1b — a LLM MENTIROSA não chega ao segurado")
MENTIRA = "Sim, tem esse serviço sim! Seu plano cobre tudo isso, pode ficar tranquilo."
for rotulo, pergunta in (("nao_sabemos_ainda", "tem taxi?"),):
    for cliente in (True, False):
        _b, contrato, rendered, meta = _fio(pergunta, cliente=cliente)
        canal = "segurado" if cliente else "corretor"
        checar("encerrar_com_o_rascunho" in (contrato.get("required_facts") or []),
               f"🔴 `{rotulo}` · {canal}: o contrato marca `encerrar_com_o_rascunho`",
               repr(contrato.get("required_facts")))
        saiu = GUARDA(MENTIRA, contrato)
        checar(saiu.strip() == str(rendered).strip(),
               f"🔴 `{rotulo}` · {canal}: o guarda ANULA a mentira e devolve o "
               "rascunho do canal", saiu[:160])
        checar("Sim, tem esse serviço sim" not in saiu,
               f"🔴 `{rotulo}` · {canal}: o 'sim' inventado NÃO chega a ninguém",
               saiu[:160])

print("\n      e `fonte_indisponivel` fecha do mesmo jeito")


class _BaseQueQuebra(BaseEmMemoria):
    def table(self, nome):  # noqa: D102
        raise RuntimeError("base fora do ar")


BASE._db = lambda supabase_client=None: _BaseQueQuebra()
_b, contrato_falha, rendered_falha, meta_falha = _fio("tem guincho?", cliente=True)
checar((meta_falha.get("cobertura") or {}).get("estado") == "fonte_indisponivel",
       "o motor produziu `fonte_indisponivel`",
       repr((meta_falha.get("cobertura") or {}).get("estado")))
checar("encerrar_com_o_rascunho" in (contrato_falha.get("required_facts") or [])
       and GUARDA(MENTIRA, contrato_falha).strip() == str(rendered_falha).strip(),
       "🔴 `fonte_indisponivel`: a mentira também é anulada",
       repr(contrato_falha.get("required_facts")))
BASE._db = lambda supabase_client=None: db

print("\n      🔴 CONTROLE: em `coberto` o guarda NÃO encerra — a LLM redige")
_b, contrato_ok, rendered_ok, _m = _fio("tem guincho?", cliente=True)
checar("encerrar_com_o_rascunho" not in (contrato_ok.get("required_facts") or []),
       "🔴 CONTROLE: `coberto` não marca o fato — a regra é por ESTADO, não um "
       "silêncio geral", repr(contrato_ok.get("required_facts")))
_boa = "Tem sim! O seu plano inclui guincho até 200 km. Quer que eu solicite?"
checar(GUARDA(_boa, contrato_ok).strip() == _boa,
       "🔴 CONTROLE: e uma resposta BOA da LLM passa inteira", GUARDA(_boa, contrato_ok))

# ---------------------------------------------------------------------------
print("\n[3] 🔴 MUTAÇÃO de B1 — tirar o anexo do ramo do cliente")
_original = TOOL._linhas_do_veredito
try:
    TOOL._linhas_do_veredito = lambda cobertura, client_facing=False: []
    briefing_mutado, _c, _r, _m = _fio("tem carro reserva?", cliente=True)
    checar("veredito_de_cobertura" not in briefing_mutado,
           "🔴 MUTAÇÃO: sem o anexo, o briefing do cliente perde o veredito — "
           "este guarda CONSEGUE ficar vermelho", briefing_mutado[-200:])
finally:
    TOOL._linhas_do_veredito = _original

_original_estados = TOOL._ESTADOS_QUE_ENCERRAM
try:
    TOOL._ESTADOS_QUE_ENCERRAM = ()
    _b, contrato_sem, rendered_sem, _m = _fio("tem taxi?", cliente=True)
    saiu_sem = GUARDA(MENTIRA, contrato_sem)
    checar(saiu_sem.strip() == MENTIRA,
           "🔴 MUTAÇÃO: sem `encerrar_com_o_rascunho`, a mentira CHEGA INTEIRA "
           "ao segurado — era o estado de 19/09", saiu_sem[:160])
finally:
    TOOL._ESTADOS_QUE_ENCERRAM = _original_estados

_de_volta = GUARDA(MENTIRA, _fio("tem taxi?", cliente=True)[1])
checar("Sim, tem esse serviço sim" not in _de_volta,
       "🔴 CONTROLE: restauradas as duas, a porta fecha de novo", _de_volta[:120])

# ---------------------------------------------------------------------------
print("\n[4] 🔴 B2 — o 🆘 da lacuna carrega a CONVERSA, e a guarda da 001.3 roda")
from app.services import lacunas_de_conhecimento as L  # noqa: E402
import app.services.o_grupo_so_o_que_importa as G  # noqa: E402

CONVERSA = "aaaaaaaa-0000-4000-8000-aaaaaaaaaaaa"
EMPRESA = "11111111-1111-1111-1111-111111111111"
TELEFONE = "11987654321"


class _TabelaMinima:
    """`capability_gaps` + `conversations` em memória. ⛔ Nada em produção."""

    def __init__(self, conversa_assumida=False):
        self.gaps = []
        self.conversa_assumida = conversa_assumida
        self.alvo = None

    def table(self, nome):
        self.alvo = nome
        return self

    def select(self, *_a, **_k):
        return self

    def insert(self, carga):
        self._carga, self._acao = carga, "insert"
        return self

    def update(self, carga):
        self._carga, self._acao = carga, "update"
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, _n):
        return self

    def execute(self):
        class R:
            pass
        r = R()
        if self.alvo == "conversations":
            r.data = [{"id": CONVERSA, "user_phone": TELEFONE}]
            return r
        if getattr(self, "_acao", "") == "insert":
            linha = dict(self._carga, id="gap-1", frequency_count=1)
            self.gaps.append(linha)
            r.data = [linha]
            self._acao = ""
            return r
        r.data = list(self.gaps)
        return r


class _PortaFiel:
    """O dublê FIEL: ⛔ não envia, mas RODA a guarda de verdade da 001.3.

    🔴 É o que dá direito a dizer "as perguntas 3 e 4 rodaram": um dublê que só
    anota provaria que a porta foi CHAMADA, nunca que a guarda foi APLICADA.
    """

    def __init__(self, conversa_no_banco):
        self.avisos = []
        self.calados = []
        self._conversa = conversa_no_banco

    async def __call__(self, _db, **kw):
        pode, porque = await G.o_grupo_pode_saber(
            _db, company_id=kw.get("company_id", ""),
            conversation_id=kw.get("conversation_id", ""),
            telefone=kw.get("telefone", ""), tipo=kw.get("tipo", ""),
            conversa=self._conversa)
        if not pode:
            self.calados.append(porque)
            return {"enviado": False, "calado": True, "motivo": porque}
        self.avisos.append(kw)
        return {"enviado": True, "calado": False, "motivo": "", "destino_ok": True}


COBERTURA = {"estado": "nao_sabemos_ainda", "servico": "carro_reserva",
             "insurer_key": "hdi", "ramo": "auto", "produto": "Auto Perfil",
             "motivo": "sem_linha_publicada"}

#: A conversa SEM dono: a guarda deixa passar.
LIVRE = {"id": CONVERSA, "company_id": EMPRESA, "claimed_by": None,
         "claimed_by_name": None, "claimed_at": None}
#: A MESMA conversa, assumida agora por uma pessoa: a guarda CALA.
from datetime import datetime, timezone  # noqa: E402

ASSUMIDA = dict(LIVRE, claimed_by="user-1", claimed_by_name="a atendente",
                claimed_at=datetime.now(timezone.utc).isoformat())


def _rodar_a_tool(conversa_no_banco, *, com_sessao=True):
    """Pelo MÉTODO DA TOOL — `_lacuna_vira_tarefa`, não pelo serviço."""
    tool = InfocapPolicyLookupTool(company_id=EMPRESA, agent_role="attendance")
    banco = _TabelaMinima()
    porta = _PortaFiel(conversa_no_banco)
    marcador = {}

    async def _marcador(company_id, conversation_id, tipo, segundos):
        chave = (company_id, conversation_id, tipo)
        if chave in marcador:
            return True
        marcador[chave] = 1
        return False

    antes_m, antes_e = G.reivindicar_o_envio, G.enviar_ao_grupo
    try:
        G.reivindicar_o_envio = _marcador
        G.enviar_ao_grupo = porta
        asyncio.run(tool._lacuna_vira_tarefa(
            banco, {"cobertura": COBERTURA}, "tem carro reserva?",
            "whatsapp:5511987654321:x" if com_sessao else None))
    finally:
        G.reivindicar_o_envio, G.enviar_ao_grupo = antes_m, antes_e
    return banco, porta


banco1, porta1 = _rodar_a_tool(LIVRE)
checar(len(porta1.avisos) == 1,
       "a tool avisou o grupo uma vez", repr(len(porta1.avisos)))
checar(porta1.avisos and porta1.avisos[0].get("conversation_id") == CONVERSA,
       "🔴 e o aviso CARREGA a conversa — a guarda da 001.3 tem sujeito",
       repr(porta1.avisos[0].get("conversation_id") if porta1.avisos else None))
checar(porta1.avisos and porta1.avisos[0].get("telefone") == TELEFONE,
       "e o telefone, que é o que a pergunta 2 da guarda precisa")
_texto1 = str(porta1.avisos[0].get("texto") if porta1.avisos else "")
checar("wa.me/5511987654321" in _texto1,
       "🔴 e o texto traz o WhatsApp do segurado — 'responda ao cliente' passou "
       "a dizer QUAL cliente", _texto1[-200:])
checar("vez(es)" not in _texto1,
       "🔴 P4: e NÃO diz quantas vezes perguntaram (a contagem é global, e "
       "global some a pergunta de outra corretora)", _texto1[-200:])
checar(TELEFONE not in str(banco1.gaps),
       "⛔ e o telefone NÃO entrou em `capability_gaps`", repr(banco1.gaps)[:200])

banco2, porta2 = _rodar_a_tool(ASSUMIDA)
checar(len(porta2.avisos) == 0 and len(porta2.calados) == 1,
       "🔴 A PERGUNTA 3 RODOU: conversa assumida por uma pessoa → o grupo CALA",
       repr(porta2.calados))
checar(len(banco2.gaps) == 1,
       "⚠️ e a lacuna É gravada mesmo assim — calar o grupo não apaga o roadmap",
       repr(len(banco2.gaps)))

print("\n      🔴 CONTROLE de B2: sem `session_id`, não há conversa (o estado de 19/09)")
banco3, porta3 = _rodar_a_tool(ASSUMIDA, com_sessao=False)
checar(len(porta3.avisos) == 1,
       "🔴 CONTROLE: sem sessão o aviso sai POR CIMA da atendente — era o que "
       "acontecia antes do conserto", repr(len(porta3.avisos)))

# ---------------------------------------------------------------------------
print("\n[5] 🔴 P2/M4 — a tool DEIXAR de chamar a lacuna tem de ficar VERMELHO")
_original_lacuna = InfocapPolicyLookupTool._lacuna_vira_tarefa
try:
    async def _nao_faz_nada(self, *_a, **_k):
        return None

    InfocapPolicyLookupTool._lacuna_vira_tarefa = _nao_faz_nada
    banco4, porta4 = _rodar_a_tool(LIVRE)
    checar(len(porta4.avisos) == 0 and len(banco4.gaps) == 0,
           "🔴 MUTAÇÃO M4: sem a chamada, ZERO lacuna e ZERO aviso — este guarda "
           "pega o que o gate D não pegava", f"{len(banco4.gaps)} · {len(porta4.avisos)}")
finally:
    InfocapPolicyLookupTool._lacuna_vira_tarefa = _original_lacuna

banco5, porta5 = _rodar_a_tool(LIVRE)
checar(len(banco5.gaps) == 1 and len(porta5.avisos) == 1,
       "🔴 CONTROLE: restaurada, a tool volta a registrar e avisar")

# ---------------------------------------------------------------------------
print("\n[6] 🔴 P2/M1 — tirar `client_facing=` da chamada ao compositor")
# 📊 A M1 do juiz ficou VERDE com as 68 asserções do gate C: ele mede o
#    COMPOSITOR, e a M1 acontece no CHAMADOR. Aqui ela fica vermelha.
import app.services.policy_answer_composer as COMP  # noqa: E402

_original_comp = COMP.compose_policy_answer_with_meta
try:
    def _sem_canal(**kw):
        return _original_comp(**{**kw, "client_facing": False})

    COMP.compose_policy_answer_with_meta = _sem_canal
    _b, _c, rendered_m1, _m = _fio("tem carro reserva?", cliente=True)
    checar(re.search(r"p\.\s*\d|Condi[çc][õo]es gerais|(?<![a-z])dele(?![a-z])",
                     str(rendered_m1)) is not None,
           "🔴 MUTAÇÃO M1: sem o canal, o `rendered_safe_answer` do WhatsApp "
           "volta a ter citação e 'dele' — o D10 reintroduzido",
           str(rendered_m1)[:200])
finally:
    COMP.compose_policy_answer_with_meta = _original_comp

_b, _c, rendered_ok2, _m = _fio("tem carro reserva?", cliente=True)
checar(re.search(r"p\.\s*\d|Condi[çc][õo]es gerais|(?<![a-z])dele(?![a-z])",
                 str(rendered_ok2)) is None,
       "🔴 CONTROLE: restaurada, a resposta do WhatsApp volta a ser limpa",
       str(rendered_ok2)[:200])

BASE._db = _db_original
sys.exit(_fechar())
