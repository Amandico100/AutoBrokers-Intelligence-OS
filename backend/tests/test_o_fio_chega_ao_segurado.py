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
import app.agents.nodes as NODES  # noqa: E402

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
db.servico(AUTO, "vidros", "condicionado", documento_id="doc-hdi-auto", pagina=26,
           condicao="so com a cobertura de vidros contratada")


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


def _fio(pergunta, *, cliente: bool, mensagem=None):
    """`(briefing, contrato, rendered)` — o caminho REAL da tool, sem rede.

    ⚠️ `mensagem` é a ÚLTIMA humana (RODADA 2). Sem ela, a tool cai na janela —
    que é o que acontecia antes de a porta de intenção existir.
    """
    tool = InfocapPolicyLookupTool(
        company_id="11111111-1111-1111-1111-111111111111",
        agent_role=("attendance" if cliente else "core"))
    conteudo, politica, rendered, meta = tool._render_content(
        _result(), pergunta, detail=False, atendente=None,
        mensagem_atual=(mensagem if mensagem is not None else pergunta))
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
from app.services import lacunas_de_conhecimento as L5  # noqa: E402
import app.services.o_grupo_so_o_que_importa as G  # noqa: E402

CONVERSA = "aaaaaaaa-0000-4000-8000-aaaaaaaaaaaa"
EMPRESA = "11111111-1111-1111-1111-111111111111"
TELEFONE = "11987654321"


class _TabelaMinima:
    """`capability_gaps` + `conversations` em memória. ⛔ Nada em produção.

    🔴 RODADA 2 (carimbo J5 do juiz): este duplo **RESPEITA os filtros**. Antes
    o `eq()` devolvia `self` e ignorava tudo — e por isso a mutação "tirar o
    `.eq(company_id, …)` de `_a_conversa_deste_atendimento`" ficava VERDE. Um
    duplo que ignora o filtro não consegue provar o §7 do CLAUDE.md: ele prova
    que a consulta foi feita, nunca que ela foi feita para a corretora certa.
    """

    #: 📊 Duas corretoras com o MESMO `session_id` — é a colisão que o filtro
    #: por `company_id` existe para impedir.
    CONVERSAS = {
        ("11111111-1111-1111-1111-111111111111", "whatsapp:5511987654321:x"):
            {"id": CONVERSA, "user_phone": TELEFONE},
        ("99999999-9999-9999-9999-999999999999", "whatsapp:5511987654321:x"):
            {"id": "bbbbbbbb-0000-4000-8000-bbbbbbbbbbbb",
             "user_phone": "11900000000"},
    }

    def __init__(self, conversa_assumida=False):
        self.gaps = []
        self.conversa_assumida = conversa_assumida
        self.alvo = None
        self.filtros = {}

    def table(self, nome):
        self.alvo = nome
        self.filtros = {}
        return self

    def select(self, *_a, **_k):
        return self

    def insert(self, carga):
        self._carga, self._acao = carga, "insert"
        return self

    def update(self, carga):
        self._carga, self._acao = carga, "update"
        return self

    def eq(self, campo, valor):
        self.filtros[str(campo)] = str(valor)
        return self

    def limit(self, _n):
        return self

    def execute(self):
        class R:
            pass
        r = R()
        if self.alvo == "conversations":
            # 🔴 O filtro é APLICADO: sem `company_id`, nada casa.
            chave = (self.filtros.get("company_id"),
                     self.filtros.get("session_id"))
            achada = self.CONVERSAS.get(chave)
            r.data = [achada] if achada else []
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


def _rodar_a_tool(conversa_no_banco, *, com_sessao=True, pergunta=True,
                  fonte=None):
    """Pelo MÉTODO DA TOOL — `_lacuna_vira_tarefa`, não pelo serviço.

    ⚠️ RODADA 2: o `meta` do duplo carrega `pergunta_de_cobertura`, como o real
    — é ele que decide se alguém é interrompido.
    """
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
            banco,
            {"cobertura": dict(COBERTURA,
                               intencao=("pergunta" if pergunta else "pedido")),
             "pergunta_de_cobertura": pergunta,
             # 🔴 RODADA 4 (B-N1): a MESMA fonte que decidiu a intenção.
             "fonte_da_intencao": fonte or ""},
            "tem carro reserva?",
            "whatsapp:5511987654321:x" if com_sessao else None,
            "tem carro reserva?" if pergunta else "preciso de carro reserva"))
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

# ---------------------------------------------------------------------------
print("\n[7] 🔴 RODADA 2 · N1 — PERGUNTAR NÃO É PEDIR, e o acionamento não cala")
from app.services.skills.cobertura_e_assistencia import (  # noqa: E402
    e_pergunta_de_cobertura as INTENCAO,
)

#: 📊 As 11 frases de acionamento que o juiz da confirmação usou.
ACIONAMENTO = [
    "preciso de guincho",
    "meu pneu furou, preciso de socorro",
    "a bateria do carro morreu, manda alguem",
    "perdi a chave do carro, preciso de chaveiro",
    "quebrou o vidro do meu carro, quero acionar",
    "meu carro deu pane seca, estou parado na estrada",
    "preciso de um reboque agora",
    "meu carro nao liga",
    "bati o carro, o que faco",
    "minha casa alagou com a enchente",
    "preciso de assistencia",
]
#: O candidato LEGÍTIMO que o atendente escreveria no meio de um acionamento.
PROXIMO_PASSO = ("Achei a sua apólice, está ativa. Me passa o endereço com um "
                 "ponto de referência que eu já abro o chamado?")

_viraram_pergunta = [t for t in ACIONAMENTO if INTENCAO(t)]
checar(not _viraram_pergunta,
       "🔴 as 11 frases de acionamento dão 0/11 como pergunta de cobertura "
       "(a porta é PURA, lida da mensagem ATUAL)", repr(_viraram_pergunta))

# ⚠️ A base deste bloco reproduz PRODUÇÃO: **0 linhas publicadas** para
#    estes serviços — é onde o juiz mediu 6/11. Com linha publicada o estado
#    é DECIDIDO e a regra da 001.5 continua valendo (o texto tem de nomear o
#    serviço); esse outro caso está medido em [7b].
_base_vazia = BaseEmMemoria()
_base_vazia.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                  plano="Essencial", nivel=1, documento_id="doc-hdi-auto",
                  pagina=9)
BASE._db = lambda supabase_client=None: _base_vazia
_substituidas = []
for _frase in ACIONAMENTO:
    _b, _contrato, _r, _m = _fio(_frase, cliente=True, mensagem=_frase)
    if GUARDA(PROXIMO_PASSO, _contrato).strip() != PROXIMO_PASSO:
        _substituidas.append(_frase)
checar(not _substituidas,
       "🔴 e pelo FIO INTEIRO: 0 de 11 respostas do atendente são substituídas "
       "(📊 antes da RODADA 2: 6 de 11 — guincho, pneu, bateria, chaveiro, "
       "vidro, pane seca)", repr(_substituidas))

print("\n      🔴 CONTROLE do [7]: a PERGUNTA continua sendo anulada")
_b, _contrato_p, _rendered_p, _m = _fio("tem guincho?", cliente=True,
                                        mensagem="tem guincho?")
checar(GUARDA(MENTIRA, _contrato_p).strip() == str(_rendered_p).strip(),
       "🔴 CONTROLE: 'tem guincho?' + candidato mentiroso -> ANULADO",
       GUARDA(MENTIRA, _contrato_p)[:120])
checar(GUARDA(PROXIMO_PASSO, _fio("preciso de guincho", cliente=True,
                                  mensagem="preciso de guincho")[1]).strip()
       == PROXIMO_PASSO,
       "🔴 e 'preciso de guincho' + próximo passo legítimo -> INTACTA")

print("\n      🔴 o TURNO N não contamina o TURNO N+1")
# A janela da tool são as 3 últimas humanas; a INTENÇÃO é só da atual.
_b, _contrato_n1, _r, _m = _fio("tem guincho? | então manda um",
                                cliente=True, mensagem="então manda um")
checar(GUARDA(PROXIMO_PASSO, _contrato_n1).strip() == PROXIMO_PASSO,
       "🔴 janela com a pergunta do turno N, mensagem atual = pedido -> o "
       "pedido PASSA", GUARDA(PROXIMO_PASSO, _contrato_n1)[:120])

print("\n      [7b] com o serviço PUBLICADO o estado é DECIDIDO, e a regra "
      "da 001.5 continua valendo")
BASE._db = lambda supabase_client=None: db
_b, _contrato_dec, _rendered_dec, _m = _fio("preciso de guincho", cliente=True,
                                            mensagem="preciso de guincho")
checar("encerrar_com_o_rascunho" not in (_contrato_dec.get("required_facts") or []),
       "🔴 num PEDIDO a flag NÃO liga nem com o serviço publicado",
       repr(_contrato_dec.get("required_facts")))
# 🔴 A LIÇÃO MIGROU (CLAUDE.md §9.3): esta linha afirmava que, num PEDIDO,
# `assistencia_da_base` FISCALIZAVA o texto final. Era verdade até 19/09/2026 —
# e era o defeito. O que ela virou está quatro linhas abaixo.
_passo_que_nomeia = ("O seu guincho está incluído. Me passa o endereço com um "
                     "ponto de referência que eu já abro o chamado?")
checar(GUARDA(_passo_que_nomeia, _contrato_dec).strip() == _passo_que_nomeia,
       "🔴 e um próximo passo que NOMEIA o serviço passa inteiro — o "
       "acionamento segue", GUARDA(_passo_que_nomeia, _contrato_dec)[:120])

# 🔴 FECHO DA RODADA 2 — NO PEDIDO O VEREDITO INFORMA, NÃO FISCALIZA.
#
# 📊 Medido em 19/09/2026, ANTES desta mudança: com `assistencia_da_base`
# em `required_facts` num PEDIDO, o próximo passo legítimo que NÃO nomeia o
# serviço era trocado pelo veredito — um turno perdido no momento mais
# aflito — e, depois do acionamento, "Pronto! Já acionei a assistência"
# virava "Quer que eu já solicite?".
checar("assistencia_da_base" not in (_contrato_dec.get("required_facts") or []),
       "🔴 no PEDIDO, `assistencia_da_base` NÃO entra em `required_facts`",
       repr(_contrato_dec.get("required_facts")))
checar(bool(_contrato_dec.get("assistencia_da_base")),
       "⚠️ mas o veredito CONTINUA no contrato — ele informa, só não fiscaliza",
       repr(_contrato_dec.get("assistencia_da_base")))
PASSO_SEM_O_NOME = ("Achei a sua apólice, está ativa. Me passa o endereço onde "
                    "o carro está?")
checar(GUARDA(PASSO_SEM_O_NOME, _contrato_dec).strip() == PASSO_SEM_O_NOME,
       "🔴 e o próximo passo SEM o nome do serviço passa INTACTO",
       GUARDA(PASSO_SEM_O_NOME, _contrato_dec)[:140])
DEPOIS_DE_ACIONAR = ("Pronto! Já acionei a assistência, o prestador chega em "
                     "40 min.")
checar(GUARDA(DEPOIS_DE_ACIONAR, _contrato_dec).strip() == DEPOIS_DE_ACIONAR,
       "🔴 e 'Pronto! Já acionei a assistência' (sem a palavra guincho) "
       "passa INTACTO", GUARDA(DEPOIS_DE_ACIONAR, _contrato_dec)[:140])

print("\n      🔴 CONTROLE do [7b]: na PERGUNTA a régua da 001.5 continua viva")
_b, _contrato_perg, _rendered_perg, _m = _fio("tem guincho?", cliente=True,
                                              mensagem="tem guincho?")
checar("assistencia_da_base" in (_contrato_perg.get("required_facts") or []),
       "🔴 CONTROLE: na PERGUNTA `assistencia_da_base` FISCALIZA (M-B5)",
       repr(_contrato_perg.get("required_facts")))
checar(GUARDA(PASSO_SEM_O_NOME, _contrato_perg).strip() != PASSO_SEM_O_NOME,
       "🔴 CONTROLE: e um candidato que OMITE o serviço é anulado",
       GUARDA(PASSO_SEM_O_NOME, _contrato_perg)[:120])

print("      🔴 e o espelho olha a FRASE que nomeia o serviço")
COM_OUTRA_NEGACAO = "Tem guincho sim! E você não tem parcelas em atraso."
checar(GUARDA(COM_OUTRA_NEGACAO, _contrato_perg).strip() == COM_OUTRA_NEGACAO,
       "🔴 'E você não tem parcelas em atraso' NÃO anula a resposta certa "
       "(📊 `_NEGATIVA_RE` casava 'não tem' ali e trocava o texto inteiro)",
       GUARDA(COM_OUTRA_NEGACAO, _contrato_perg)[:140])
NEGA_O_SERVICO = "Não, seu plano não tem guincho."
checar(GUARDA(NEGA_O_SERVICO, _contrato_perg).strip() != NEGA_O_SERVICO,
       "🔴 CONTROLE: mas a negação NA FRASE DO SERVIÇO continua anulada",
       GUARDA(NEGA_O_SERVICO, _contrato_perg)[:120])

print("      🔴 AS DUAS MUTAÇÕES do fecho")
_fatos_mut = dict(_contrato_dec,
                  required_facts=list(_contrato_dec.get("required_facts") or [])
                  + ["assistencia_da_base"])
checar(GUARDA(PASSO_SEM_O_NOME, _fatos_mut).strip() != PASSO_SEM_O_NOME,
       "🔴 MUTAÇÃO (a): o pedido voltando a FISCALIZAR troca o próximo "
       "passo do atendente", GUARDA(PASSO_SEM_O_NOME, _fatos_mut)[:120])
checar(GUARDA(DEPOIS_DE_ACIONAR, _fatos_mut).strip() != DEPOIS_DE_ACIONAR,
       "🔴 MUTAÇÃO (a'): e troca também o 'Pronto! Já acionei'",
       GUARDA(DEPOIS_DE_ACIONAR, _fatos_mut)[:120])
_nega_original = NODES._nega_o_servico
try:
    NODES._nega_o_servico = lambda c, r: bool(NODES._NEGATIVA_RE.search(str(c or "")))
    checar(GUARDA(COM_OUTRA_NEGACAO, _contrato_perg).strip() != COM_OUTRA_NEGACAO,
           "🔴 MUTAÇÃO (b): o espelho no candidato INTEIRO anula a resposta "
           "certa por causa das parcelas",
           GUARDA(COM_OUTRA_NEGACAO, _contrato_perg)[:120])
finally:
    NODES._nega_o_servico = _nega_original

# ⚠️ A ação posterior consome `assistencia_da_base` JUNTO com a flag.
_consumido_acao = dict(_contrato_perg, required_facts=[
    f for f in (_contrato_perg.get("required_facts") or [])
    if f not in ("encerrar_com_o_rascunho", "assistencia_da_base")])
checar(GUARDA(DEPOIS_DE_ACIONAR, _consumido_acao).strip() == DEPOIS_DE_ACIONAR,
       "🔴 e depois de uma AÇÃO nem a PERGUNTA fiscaliza — a resposta do "
       "turno é sobre o que foi feito",
       GUARDA(DEPOIS_DE_ACIONAR, _consumido_acao)[:120])
_fonte_no = open(os.path.join(RAIZ, "app", "agents", "nodes.py"),
                 encoding="utf-8").read()
_sem_com = "\n".join(l.split("#")[0] for l in _fonte_no.splitlines())
# 🔴 A LIÇÃO MIGROU (CLAUDE.md §9.3): na RODADA 3 o consumo deixou de ser um
# conjunto local (`_CONSUMIDOS`) e virou `_REGUAS_DE_COBERTURA` +
# `_consumir_regua_apos_acao`, chamado nos DOIS pontos do grafo. O bloco [11]
# mede isso pelo caminho real.
checar('"assistencia_da_base"' in _sem_com.split("_REGUAS_DE_COBERTURA")[1][:220],
       "🔴 e as duas réguas estão no CÓDIGO do nó, não num comentário")

BASE._db = lambda supabase_client=None: _base_vazia

print("\n      🔴 as 30 perguntas REAIS do corpus")
import json as _json  # noqa: E402

with open(os.path.join(RAIZ, "tests", "corpus",
                       "perguntas_de_cobertura_2026-09-17.json"),
          encoding="utf-8") as _fh:
    _CORPUS = _json.load(_fh)["perguntas"]
_como_pergunta = [p["pergunta"] for p in _CORPUS if INTENCAO(p["pergunta"])]
#: ⚠️ NÃO são 30/30, e a diferença é MEDIDA, não tolerância: 📊 6 das 30 são
#: PEDIDOS ou perguntas sobre outro assunto ("que numero chama guincho porto???",
#: "Consegues chamar ela?!", "Preciso carro reserva. Como fazer?"). Para elas o
#: comportamento seguro é exatamente o que a porta dá: NÃO calar o atendente.
#: O veredito continua sendo produzido para as 30 (`test_a_resposta_traz_
#: documento_e_pagina`, 17 verdes) — o que a porta governa é só a flag, o
#: rascunho no briefing e o 🆘.
print("      📊 corpus classificado como PERGUNTA: %d/%d"
      % (len(_como_pergunta), len(_CORPUS)))
checar(len(_como_pergunta) >= 24,
       "🔴 pelo menos 24 das 30 do corpus continuam sendo PERGUNTA",
       repr([p["pergunta"][:50] for p in _CORPUS
             if not INTENCAO(p["pergunta"])]))
checar(len(_como_pergunta) < len(_CORPUS),
       "⚠️ e a porta SEPARA de verdade — se desse 30/30 ela não estaria "
       "olhando a intenção", str(len(_como_pergunta)))

print("\n      🔴 a MISTA não encerra: a flag não liga")
_b, _contrato_mista, _r, _m = _fio(
    "tem taxi? e quantas parcelas faltam?", cliente=False,
    mensagem="tem taxi? e quantas parcelas faltam?")
checar("encerrar_com_o_rascunho" not in (_contrato_mista.get("required_facts") or []),
       "🔴 mista (cobertura + parcelas) NÃO liga a flag — o `rendered` da mista "
       "não carrega as parcelas, e encerrar com ele apagaria a metade verdadeira",
       repr(_contrato_mista.get("required_facts")))
_resposta_mista = "Sobre táxi eu confirmo. E faltam 3 parcelas."
checar(GUARDA(_resposta_mista, _contrato_mista).strip() == _resposta_mista,
       "e a resposta com as DUAS partes sobrevive", GUARDA(_resposta_mista, _contrato_mista)[:120])

print("\n      🔴 MUTAÇÃO do [7]: a porta de intenção sempre-True")
import app.services.skills.cobertura_e_assistencia as SKI  # noqa: E402

# 🔴 A LIÇÃO MIGROU (CLAUDE.md §9.3): quem a tool chama desde a RODADA 3 e
# `intencao_da_mensagem` (tres saidas), nao `e_pergunta_de_cobertura`. Mutar a
# funcao que ninguem chama mais faria este bloco passar por vacuo — foi o que
# aconteceu no primeiro re-run.
_porta_original = SKI.intencao_da_mensagem
try:
    SKI.intencao_da_mensagem = lambda _t: "pergunta"
    _mut = [f for f in ACIONAMENTO
            if GUARDA(PROXIMO_PASSO, _fio(f, cliente=True, mensagem=f)[1]).strip()
            != PROXIMO_PASSO]
    checar(len(_mut) >= 5,
           "🔴 MUTAÇÃO: com a porta sempre-True, %d das 11 respostas do "
           "atendente voltam a ser SUBSTITUÍDAS — era o blocker N1" % len(_mut),
           repr(_mut[:3]))
finally:
    SKI.intencao_da_mensagem = _porta_original

# ---------------------------------------------------------------------------
BASE._db = lambda supabase_client=None: db

print("\n[8] 🔴 RODADA 2 — o PEDIDO grava a lacuna e NÃO interrompe ninguém")
banco_ped, porta_ped = _rodar_a_tool(LIVRE, pergunta=False)
checar(len(banco_ped.gaps) == 1,
       "🔴 o pedido GRAVA a lacuna (a frequência é boa para o painel)",
       repr(len(banco_ped.gaps)))
checar(len(porta_ped.avisos) == 0,
       "🔴 e NÃO manda 🆘 nenhum — o texto diria que o cliente PERGUNTOU sobre "
       "cobertura, o que é falso", repr(porta_ped.avisos))
_descricao = str((banco_ped.gaps or [{}])[0].get("description_redacted"))
checar(_descricao.startswith("Pedido de"),
       "🔴 e a descrição no painel diz PEDIDO, não 'Cobertura de'", _descricao)

# ---------------------------------------------------------------------------
print("\n[9] 🔴 RODADA 2 · J5 — o filtro `company_id` na leitura da conversa")
_original_conversa = InfocapPolicyLookupTool._a_conversa_deste_atendimento
try:
    async def _sem_o_filtro(self, db, session_id):
        """A mutação J5: a leitura sem `.eq("company_id", …)`."""
        from app.services.o_fim_do_atendimento import _cliente, _executar

        achado = await _executar(_cliente(db).table("conversations")
                                 .select("id, user_phone")
                                 .eq("session_id", str(session_id or ""))
                                 .limit(1))
        linha = (list(getattr(achado, "data", None) or [{}]) or [{}])[0] or {}
        return {"conversation_id": str(linha.get("id") or ""),
                "telefone": str(linha.get("user_phone") or "")}

    InfocapPolicyLookupTool._a_conversa_deste_atendimento = _sem_o_filtro
    _banco_j5, _porta_j5 = _rodar_a_tool(LIVRE)
    _conversa_j5 = (_porta_j5.avisos[0].get("conversation_id")
                    if _porta_j5.avisos else "")
    checar(_conversa_j5 != CONVERSA,
           "🔴 MUTAÇÃO J5: sem o `.eq(company_id, …)` a conversa NÃO é achada — "
           "o duplo respeita filtros, e a mutação fica VERMELHA",
           repr(_conversa_j5))
finally:
    InfocapPolicyLookupTool._a_conversa_deste_atendimento = _original_conversa

_banco_ok, _porta_ok = _rodar_a_tool(LIVRE)
checar(_porta_ok.avisos and _porta_ok.avisos[0].get("conversation_id") == CONVERSA,
       "🔴 CONTROLE: restaurado o filtro, a conversa CERTA volta",
       repr(_porta_ok.avisos[0].get("conversation_id") if _porta_ok.avisos else None))

# ---------------------------------------------------------------------------
print("\n[10] 🔴 RODADA 2 · J6 — a injeção do `session_id` em `nodes.py`")
import ast as _ast  # noqa: E402

_fonte_nodes = open(os.path.join(RAIZ, "app", "agents", "nodes.py"),
                    encoding="utf-8").read()
_sem_comentario = "\n".join(l.split("#")[0] for l in _fonte_nodes.splitlines())
for _campo in ('"session_id": str(state.get("session_id")',
               '"mensagem_atual": str(current_user_query'):
    checar(_campo in _sem_comentario,
           "🔴 `nodes.py` INJETA %s a partir do ESTADO (não de um comentário)"
           % _campo.split(":")[0], _campo)
checar('"mensagem_atual"' in _sem_comentario
       and _sem_comentario.index('"mensagem_atual"')
       > _sem_comentario.index("infocap_policy_lookup"),
       "e a injeção está no ramo de `infocap_policy_lookup`")
_mutado_j6 = _sem_comentario.replace('"session_id": str(state.get("session_id") or "")', "")
checar('"session_id": str(state.get("session_id") or "")' not in _mutado_j6,
       "🔴 MUTAÇÃO J6: removida a injeção, esta asserção falharia — o guarda "
       "mede a LINHA, não a intenção")

# ---------------------------------------------------------------------------
print("\n[11] 🔴 RODADA 3 · B3 — o consumo é por ESTADO, pelo CAMINHO REAL do nó")
# 📊 Carimbo M4 do juiz: a mutação "consumo REMOVIDO" ficava VERDE, porque este
# bloco montava o contrato consumido À MÃO. E o defeito real era outro: o grafo
# é `agent ⇄ tools`, a consulta e o acionamento caem em INVOCAÇÕES diferentes, e
# a versão por chamada não via a segunda. Medido: "Pronto! Já acionei a
# assistência, o prestador chega em 40 minutos." → TROCADO.
_b, _contrato_acao, _rendered_acao, _m = _fio("tem taxi?", cliente=True,
                                              mensagem="tem taxi?")
checar("encerrar_com_o_rascunho" in (_contrato_acao.get("required_facts") or []),
       "a flag está no contrato (é o caso em que ela deve estar)",
       repr(_contrato_acao.get("required_facts")))
checar(isinstance(_contrato_acao.get("tools_ja_usadas"), list)
       or _contrato_acao.get("tools_ja_usadas") is None,
       "o contrato nasce sem snapshot (quem o põe é o nó)",
       repr(_contrato_acao.get("tools_ja_usadas")))

DEPOIS_DA_ACAO = "Pronto! Já acionei a assistência, o prestador chega em 40 minutos."

#: 🔴 O SNAPSHOT, como o `tool_node` o escreve: as tools do turno no instante em
#: que o contrato nasceu.
_com_snapshot = dict(_contrato_acao,
                     tools_ja_usadas=["infocap_policy_lookup"])
checar(NODES._consumir_regua_apos_acao(_com_snapshot,
                                       ["infocap_policy_lookup"])
       is _com_snapshot,
       "🔴 sem ação nova, o contrato NÃO é tocado (é o mesmo objeto)")
checar(GUARDA(DEPOIS_DA_ACAO, _com_snapshot).strip() != DEPOIS_DA_ACAO,
       "🔴 CONTROLE: com a régua de pé, a resposta da AÇÃO seria trocada",
       GUARDA(DEPOIS_DA_ACAO, _com_snapshot)[:100])

#: A SEGUNDA invocação do grafo: `tools_used` do ESTADO já tem o acionamento.
_apos = NODES._consumir_regua_apos_acao(
    _com_snapshot, ["infocap_policy_lookup", "insurer_dispatch"])
checar("encerrar_com_o_rascunho" not in (_apos.get("required_facts") or [])
       and "assistencia_da_base" not in (_apos.get("required_facts") or []),
       "🔴 com `insurer_dispatch` no estado, AS DUAS réguas são consumidas",
       repr(_apos.get("required_facts")))
checar(GUARDA(DEPOIS_DA_ACAO, _apos).strip() == DEPOIS_DA_ACAO,
       "🔴 e 'Pronto! Já acionei a assistência' passa INTACTO na 2ª invocação",
       GUARDA(DEPOIS_DA_ACAO, _apos)[:100])

#: ⚠️ A CONTAGEM, não o conjunto: a ação que já tinha rodado ANTES não consome.
_ja_tinha = dict(_contrato_acao,
                 tools_ja_usadas=["insurer_dispatch", "infocap_policy_lookup"])
checar(NODES._consumir_regua_apos_acao(
           _ja_tinha, ["insurer_dispatch", "infocap_policy_lookup"]) is _ja_tinha,
       "🔴 CONTROLE: ação que rodou ANTES da consulta não consome nada")
checar("encerrar_com_o_rascunho" not in (NODES._consumir_regua_apos_acao(
           _ja_tinha, ["insurer_dispatch", "infocap_policy_lookup",
                       "insurer_dispatch"]).get("required_facts") or []),
       "🔴 mas a MESMA ação rodando DE NOVO depois consome — por contagem, "
       "não por conjunto")

print("\n      🔴 MUTAÇÃO M4 (a do juiz): o consumo REMOVIDO")
_consumo_original = NODES._consumir_regua_apos_acao
try:
    NODES._consumir_regua_apos_acao = lambda contrato, tools_usadas: contrato
    _mut = NODES._consumir_regua_apos_acao(
        _com_snapshot, ["infocap_policy_lookup", "insurer_dispatch"])
    checar(GUARDA(DEPOIS_DA_ACAO, _mut).strip() != DEPOIS_DA_ACAO,
           "🔴 MUTAÇÃO M4: sem o consumo, 'Pronto! Já acionei' volta a ser "
           "TROCADO — este guarda CONSEGUE ficar vermelho",
           GUARDA(DEPOIS_DA_ACAO, _mut)[:100])
finally:
    NODES._consumir_regua_apos_acao = _consumo_original

_fonte_do_no = open(os.path.join(RAIZ, "app", "agents", "nodes.py"),
                    encoding="utf-8").read()
_sem_comment = "\n".join(l.split("#")[0] for l in _fonte_do_no.splitlines())
checar(_sem_comment.count("_consumir_regua_apos_acao(") >= 3,
       "🔴 e o nó CHAMA o consumo nos DOIS pontos (tool_node e agent_node)",
       str(_sem_comment.count("_consumir_regua_apos_acao(")))
checar("tools_ja_usadas=[str(t) for t in tools_used]" in _sem_comment,
       "🔴 e o SNAPSHOT é escrito quando o contrato nasce")
checar("_consumir_regua_apos_acao(contract, state.get(" in _sem_comment,
       "🔴 e o guarda pós-LLM consome a partir do ESTADO — é a 2ª invocação")

print("\n[12] 🔴 RODADA 2 — a LLM não pode NEGAR o que a base AFIRMOU")
# 📊 Medido em 19/09/2026: com a base dizendo `sim` para guincho, o candidato
# "Não, seu plano não tem guincho" PASSAVA — o guarda só olhava a direção `nao`.
# Com 23 linhas publicadas hoje, é o segurado ouvindo que não tem o que tem.
BASE._db = lambda supabase_client=None: db
for _rotulo, _pergunta, _mentira in (
        ("coberto", "tem guincho?",
         "Não, o seu plano não tem guincho. Infelizmente não dá pra acionar."),
        ("condicionado", "cobre vidro trincado?",
         "Não, vidros não está coberto no seu plano.")):
    _b, _contrato_m, _rendered_m, _meta_m = _fio(_pergunta, cliente=True,
                                                 mensagem=_pergunta)
    checar((_meta_m.get("cobertura") or {}).get("estado") == _rotulo,
           f"`{_rotulo}`: o motor produziu o estado",
           repr((_meta_m.get("cobertura") or {}).get("estado")))
    _saiu = GUARDA(_mentira, _contrato_m)
    checar(_saiu.strip() == str(_rendered_m).strip(),
           f"🔴 `{_rotulo}`: a NEGAÇÃO da LLM é anulada (antes PASSAVA)",
           _saiu[:120])
    _verdade = ("Tem sim! O seu plano inclui guincho — 200 km. Quer que eu "
                "solicite?" if _rotulo == "coberto"
                else "Tem sim: vidros, com uma condição do seu contrato.")
    checar(GUARDA(_verdade, _contrato_m).strip() == _verdade,
           f"🔴 CONTROLE `{_rotulo}`: a resposta VERDADEIRA passa inteira",
           GUARDA(_verdade, _contrato_m)[:120])

print("\n      🔴 MUTAÇÃO do [12]: a regra invertida removida")
_negativa_original = NODES._NEGATIVA_RE
try:
    import re as _re2
    NODES._NEGATIVA_RE = _re2.compile(r"(?!x)x")  # nunca casa
    _b, _contrato_mut, _r, _m = _fio("tem guincho?", cliente=True,
                                     mensagem="tem guincho?")
    _mentira_g = "Não, o seu plano não tem guincho."
    checar(GUARDA(_mentira_g, _contrato_mut).strip() == _mentira_g,
           "🔴 MUTAÇÃO: sem `_NEGATIVA_RE`, a negação volta a PASSAR",
           GUARDA(_mentira_g, _contrato_mut)[:100])
finally:
    NODES._NEGATIVA_RE = _negativa_original
BASE._db = lambda supabase_client=None: _base_vazia

# ---------------------------------------------------------------------------
print("\n[13] 🔴 RODADA 3 · B1 — O TURNO DO CPF NÃO DESLIGA A FISCALIZAÇÃO")
# 📊 O fluxo real (a janela em `nodes.py:1692-1711`, incidente 12/07): o
# cliente pergunta, o agente pede o CPF, e a tool roda NO TURNO DO CPF. Medido
# pelo juiz da rodada 3, com duas saídas só na porta:
#     "tem guincho? | 12345678900"       -> required_facts=[]
#     "Sim, tem esse serviço sim!"       -> CHEGAVA INTACTO
# 🔴 E este bloco é também o carimbo M9: em TODO caso aqui a janela é DIFERENTE
#    da mensagem atual — sem isso, a tese central da rodada 2 não era medida.
from app.services.skills.cobertura_e_assistencia import (  # noqa: E402
    INDETERMINADA, PEDIDO, PERGUNTA, intencao_da_mensagem,
)

BASE._db = lambda supabase_client=None: db
CPF_FICTICIO = "12345678900"   # 💭 fictício, não pertence a ninguém

print("      ① pergunta no turno N, CPF no turno N+1 -> FISCALIZA como pergunta")
_b, _c_cpf, _r_cpf, _m_cpf = _fio("tem carro reserva? | %s" % CPF_FICTICIO,
                                  cliente=True, mensagem=CPF_FICTICIO)
checar(_m_cpf.get("pergunta_de_cobertura") is True,
       "🔴 a intenção veio da JANELA (a mensagem atual é indeterminada)",
       repr(_m_cpf.get("pergunta_de_cobertura")))
checar("assistencia_da_base" in (_c_cpf.get("required_facts") or []),
       "🔴 e a régua da 001.5 (M-B5) CONTINUA fiscalizando no turno do CPF",
       repr(_c_cpf.get("required_facts")))
MENTIRA_CPF = "Sim! Seu plano tem carro reserva por 7 dias, pode contar com isso."
checar(GUARDA(MENTIRA_CPF, _c_cpf).strip() != MENTIRA_CPF,
       "🔴 e a MENTIRA (a base diz NÃO) é anulada — era o blocker B1",
       GUARDA(MENTIRA_CPF, _c_cpf)[:120])

print("      ② pedido no turno N, CPF no turno N+1 -> segue PEDIDO")
_b, _c_ped, _r_ped, _m_ped = _fio("preciso de guincho | %s" % CPF_FICTICIO,
                                  cliente=True, mensagem=CPF_FICTICIO)
checar(_m_ped.get("pergunta_de_cobertura") is False,
       "🔴 a janela diz PEDIDO, e o turno do CPF herda o pedido",
       repr(_m_ped.get("pergunta_de_cobertura")))
PASSO_DO_ACIONAMENTO = ("Achei a sua apólice, está ativa. Me passa o endereço "
                        "onde o carro está?")
checar(GUARDA(PASSO_DO_ACIONAMENTO, _c_ped).strip() == PASSO_DO_ACIONAMENTO,
       "🔴 e o próximo passo do acionamento passa INTACTO",
       GUARDA(PASSO_DO_ACIONAMENTO, _c_ped)[:120])

print("      ③ mensagem atual ausente -> a JANELA decide (comportamento antigo)")
for _vazia in (None, "", "   "):
    _b, _c_v, _r_v, _m_v = _fio("tem carro reserva?", cliente=True,
                                mensagem=_vazia)
    checar(_m_v.get("pergunta_de_cobertura") is True,
           "🔴 mensagem atual %r -> a janela decide" % _vazia,
           repr(_m_v.get("pergunta_de_cobertura")))

print("      ④ a porta tem TRÊS saídas, e ausência de sinal nunca é pedido")
for _sinal in (CPF_FICTICIO, "ABC1D23", "ok", "pode ser", "apolice 998877"):
    checar(intencao_da_mensagem(_sinal) == INDETERMINADA,
           "🔴 %r -> indeterminada" % _sinal, intencao_da_mensagem(_sinal))

print("\n      🔴 MUTAÇÃO de B1: indeterminada -> pedido")
import app.services.skills.cobertura_e_assistencia as SKI2  # noqa: E402

_intencao_original = SKI2.intencao_da_mensagem
try:
    SKI2.intencao_da_mensagem = lambda t: (
        PEDIDO if _intencao_original(t) == INDETERMINADA else _intencao_original(t))
    _b, _c_mut, _r_mut, _m_mut = _fio("tem carro reserva? | %s" % CPF_FICTICIO,
                                      cliente=True, mensagem=CPF_FICTICIO)
    checar(GUARDA(MENTIRA_CPF, _c_mut).strip() == MENTIRA_CPF,
           "🔴 MUTAÇÃO: com indeterminada→pedido, a mentira volta a CHEGAR "
           "INTACTA ao segurado — era o blocker B1",
           GUARDA(MENTIRA_CPF, _c_mut)[:120])
finally:
    SKI2.intencao_da_mensagem = _intencao_original

print("\n      🔴 MUTAÇÃO M9 (a do juiz): `mensagem_atual` IGNORADA")
# 📊 Ela ficava VERDE porque nos testes a mensagem ERA a janela. Aqui a janela é
#    DIFERENTE, e a mutação muda o veredito.
#: ⚠️ A janela tem de ser classificada como PERGUNTA sozinha — senão a mutação
#: não muda nada e o guarda passaria por vácuo.
JANELA_QUE_PERGUNTA = "tem carro reserva? | %s" % CPF_FICTICIO
checar(intencao_da_mensagem(JANELA_QUE_PERGUNTA) == PERGUNTA,
       "🔴 CONTROLE da M9: a JANELA, sozinha, e PERGUNTA",
       intencao_da_mensagem(JANELA_QUE_PERGUNTA))
_b, _c_m9, _r_m9, _m_m9 = _fio(JANELA_QUE_PERGUNTA, cliente=True,
                               mensagem="preciso de um reboque agora")
checar(_m_m9.get("pergunta_de_cobertura") is False,
       "🔴 mensagem atual = PEDIDO vence a janela que traz a pergunta",
       repr(_m_m9.get("pergunta_de_cobertura")))
_b, _c_m9b, _r_m9b, _m_m9b = _fio(JANELA_QUE_PERGUNTA,
                                  cliente=True, mensagem=None)
checar(_m_m9b.get("pergunta_de_cobertura") is True,
       "🔴 MUTAÇÃO M9: ignorando a mensagem atual (= cair na janela), o mesmo "
       "turno vira PERGUNTA — a tese da rodada 2 passa a ser medida",
       repr(_m_m9b.get("pergunta_de_cobertura")))

# ---------------------------------------------------------------------------
print("\n[14] 🔴 RODADA 3 · B2 — A MATRIZ DE CONFUSÃO DA PORTA")
# 🔴 ORIGEM DO CORPUS, declarada (CLAUDE.md §9.4): as 30 PERGUNTAS vêm do acervo
# real (`tests/corpus/perguntas_de_cobertura_2026-09-17.json`, já usado pelo
# guarda M-B2). Os 22 PEDIDOS são as 11 frases do juiz da rodada 2 + 11 formas
# que o juiz da rodada 3 mediu como perdidas ("consegue", "podem", "tem como",
# "dá pra", "ajudar", "mandem"). ⛔ Ler o acervo de mensagens de entrada custaria
# mais que o teto desta rodada; a origem fica DECLARADA aqui, e a pendência
# P-001.5.1-CORPUS-DE-PEDIDOS-DO-ACERVO pede a medição sobre conversas reais.
PEDIDOS_MEDIDOS = ACIONAMENTO + [
    "consegue mandar um guincho?",
    "voces podem mandar o reboque ate a oficina?",
    "tem como chamar um chaveiro aqui em casa?",
    "da pra mandar alguem hoje ainda?",
    "quero acionar meu seguro, preciso de guincho",
    "me ajudar com o guincho por favor",
    "preciso que mandem um borracheiro",
    "pode chamar o guincho pra mim?",
    "gostaria de solicitar carro reserva",
    "socorro, meu carro parou na rodovia",
    "abrir um chamado de vidro",
]
_erro_caro = [t for t in PEDIDOS_MEDIDOS
              if intencao_da_mensagem(t) == PERGUNTA]
_erro_barato = [p["pergunta"] for p in _CORPUS
                if intencao_da_mensagem(p["pergunta"]) != PERGUNTA]
print("      📊 MATRIZ: erro CARO (pedido→pergunta) %d/%d · erro BARATO "
      "(pergunta→outro) %d/%d"
      % (len(_erro_caro), len(PEDIDOS_MEDIDOS), len(_erro_barato), len(_CORPUS)))
checar(not _erro_caro,
       "🔴 erro CARO = 0/%d — ⚠️ o '10/22' que esta linha dizia era de "
       "OUTRO juiz sobre OUTRAS frases: 📊 sobre ESTAS 22, a porta de "
       "`421b2c7` errava 1" % len(PEDIDOS_MEDIDOS),
       repr(_erro_caro))
checar(len(_erro_barato) <= 6,
       "🔴 erro BARATO <= 6/%d — são perguntas de PROCEDIMENTO ('que numero "
       "chama guincho?'), em que o fiscal de cobertura não é o ponto"
       % len(_CORPUS),
       repr([t[:55] for t in _erro_barato]))
checar(len(_erro_barato) > 0,
       "⚠️ e ele NÃO é zero — uma porta que classificasse tudo como pergunta "
       "não estaria olhando a intenção")

print("\n[15] 🔴 RODADA 3 — o PEDIDO que a base NEGA avisa o modelo")
_base_nega = BaseEmMemoria()
_P = _base_nega.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                      plano="Essencial", nivel=1, documento_id="d", pagina=9)
_base_nega.servico(_P, "carro_reserva", "nao", documento_id="d", pagina=23)
_base_nega.servico(_P, "guincho", "sim", documento_id="d", pagina=25)
BASE._db = lambda supabase_client=None: _base_nega
_brief_nega, _c_n, _r_n, _m_n = _fio("preciso de carro reserva", cliente=True,
                                     mensagem="preciso de carro reserva")
checar((_m_n.get("cobertura") or {}).get("estado") == "nao_coberto",
       "a base NEGA o serviço pedido",
       repr((_m_n.get("cobertura") or {}).get("estado")))
checar("NAO prometa o servico" in _brief_nega,
       "🔴 e o briefing do PEDIDO manda NÃO prometer e deixar a equipe "
       "confirmar — a mitigação do 'pedido sem fiscal'", _brief_nega[-260:])
_brief_ok, _c_o, _r_o, _m_o = _fio("preciso de guincho", cliente=True,
                                   mensagem="preciso de guincho")
checar("NAO prometa o servico" not in _brief_ok,
       "🔴 CONTROLE: quando a base AFIRMA, o aviso NÃO aparece",
       _brief_ok[-200:])
BASE._db = lambda supabase_client=None: db

# ---------------------------------------------------------------------------
print("\n[16] 🔴 RODADA 4 · B-N1 — UMA FONTE SÓ: a intenção, o serviço e o 🆘")
# 📊 Medido pelo juiz final: a rodada 3 moveu a INTENÇÃO para a janela, mas
# deixou `texto` (e portanto `so_de_cobertura`) na mensagem atual. Como a flag
# exige `so_de_cobertura`, a fiscalização ficava desligada no turno do documento:
#     "meu plano cobre taxi? | 12345678900", atual="12345678900"
#        pergunta=True · so_de_cobertura=False · required_facts=[]
#        "Sim! Seu plano tem taxi sim, pode acionar."   -> CHEGAVA INTACTO
# 🔴 E isso é 100 % do tráfego: sem linha publicada, toda pergunta de cobertura
#    cai em `nao_sabemos_ainda` — um dos dois estados que a flag cobre.
BASE._db = lambda supabase_client=None: _base_vazia
MENTIRA_LISA = "Sim! Seu plano tem taxi sim, pode acionar."

for _doc in (CPF_FICTICIO, "ok", "ABC1D23"):
    _janela = "meu plano cobre taxi? | %s" % _doc
    _b, _c_doc, _r_doc, _m_doc = _fio(_janela, cliente=True, mensagem=_doc)
    checar((_m_doc.get("cobertura") or {}).get("estado") == "nao_sabemos_ainda",
           f"turno do documento {_doc!r}: o estado é `nao_sabemos_ainda` "
           "(100 % do tráfego de hoje)",
           repr((_m_doc.get("cobertura") or {}).get("estado")))
    checar(_m_doc.get("so_de_cobertura") is True,
           f"🔴 {_doc!r}: `so_de_cobertura` veio da MESMA mensagem que decidiu "
           "a intenção", repr(_m_doc.get("so_de_cobertura")))
    checar("encerrar_com_o_rascunho" in (_c_doc.get("required_facts") or []),
           f"🔴 {_doc!r}: a flag LIGA no turno do documento",
           repr(_c_doc.get("required_facts")))
    checar(GUARDA(MENTIRA_LISA, _c_doc).strip() == str(_r_doc).strip(),
           f"🔴 {_doc!r}: a mentira é ANULADA e sai o rascunho honesto",
           GUARDA(MENTIRA_LISA, _c_doc)[:120])

print("      e `fonte_indisponivel` no turno do documento fecha igual")


class _BaseQueQuebra2(BaseEmMemoria):
    def table(self, nome):  # noqa: D102
        raise RuntimeError("base fora do ar")


BASE._db = lambda supabase_client=None: _BaseQueQuebra2()
_b, _c_fi, _r_fi, _m_fi = _fio("meu plano cobre taxi? | %s" % CPF_FICTICIO,
                               cliente=True, mensagem=CPF_FICTICIO)
checar((_m_fi.get("cobertura") or {}).get("estado") == "fonte_indisponivel"
       and "encerrar_com_o_rascunho" in (_c_fi.get("required_facts") or [])
       and GUARDA(MENTIRA_LISA, _c_fi).strip() == str(_r_fi).strip(),
       "🔴 `fonte_indisponivel` no turno do documento: a flag liga e a mentira "
       "é anulada", repr(_c_fi.get("required_facts")))
BASE._db = lambda supabase_client=None: _base_vazia

print("\n      🔴 MUTAÇÃO de B-N1: `texto` voltando à mensagem atual")
#: ⚠️ Pelo `__dict__`, para guardar o DESCRITOR (`staticmethod`). Restaurar a
#: funcao crua a transformaria em metodo de instancia, e ela passaria a
#: receber `self` — o `except` do `_render_content` engoliria o TypeError e o
#: bloco seguinte mediria o caminho LEGADO sem saber (CLAUDE.md §9.1).
_intencao_original_r4 = InfocapPolicyLookupTool.__dict__["_a_intencao_da_mensagem"]
try:
    @staticmethod
    def _com_texto_na_atual(mensagem_atual, user_query):
        """A mutação: a intenção vem da janela, o serviço vem da atual."""
        from app.services.knowledge.assistance_plans_base import servico_canonico
        from app.services.skills.cobertura_e_assistencia import (
            INDETERMINADA, PERGUNTA, intencao_da_mensagem,
        )
        atual = str(mensagem_atual or "").strip()
        janela = str(user_query or "")
        intencao = intencao_da_mensagem(atual)
        if intencao == INDETERMINADA:
            intencao = intencao_da_mensagem(janela)
        texto = atual or janela          # <- o defeito medido
        try:
            reconhece = bool(servico_canonico(texto))
        except Exception:  # noqa: BLE001
            reconhece = False
        return {"pergunta": intencao == PERGUNTA,
                "so_de_cobertura": bool(intencao == PERGUNTA and reconhece),
                "fonte": texto}

    InfocapPolicyLookupTool._a_intencao_da_mensagem = _com_texto_na_atual
    _b, _c_mut4, _r_mut4, _m_mut4 = _fio(
        "meu plano cobre taxi? | %s" % CPF_FICTICIO, cliente=True,
        mensagem=CPF_FICTICIO)
    checar(GUARDA(MENTIRA_LISA, _c_mut4).strip() == MENTIRA_LISA,
           "🔴 MUTAÇÃO B-N1: com `texto` na atual, a mentira volta a CHEGAR "
           "INTACTA ao segurado", GUARDA(MENTIRA_LISA, _c_mut4)[:120])
finally:
    InfocapPolicyLookupTool._a_intencao_da_mensagem = _intencao_original_r4

# ---------------------------------------------------------------------------
print("\n[17] 🔴 RODADA 4 · B-N2 — a janela é um BLOCO, e manda a MAIS NOVA")
# 📊 `user_query` são as 3 últimas humanas juntadas por `SEPARADOR_DA_JANELA`
# (`nodes.py:1711`, que IMPORTA a constante da tool),
# e `_COBERTURA_FORTE_RE` é a primeira trava — a pergunta do turno N-2 vencia o
# pedido do turno N-1:
#   "meu plano cobre guincho? | preciso de guincho, estou parado | 12345678900"
#      pergunta=True -> "Achei a sua apólice… Me passa o endereço?" era TROCADO
BASE._db = lambda supabase_client=None: db
PASSO_LEGITIMO = ("Achei a sua apólice, está ativa. Me passa o endereço onde o "
                  "carro está?")
_janela_pedido = ("meu plano cobre guincho? | preciso de guincho, estou parado"
                  " | %s" % CPF_FICTICIO)
_b, _c_bn2, _r_bn2, _m_bn2 = _fio(_janela_pedido, cliente=True,
                                  mensagem=CPF_FICTICIO)
checar(_m_bn2.get("pergunta_de_cobertura") is False,
       "🔴 janela `pergunta | pedido | documento`: o PEDIDO (mais novo) vence",
       repr(_m_bn2.get("pergunta_de_cobertura")))
checar(GUARDA(PASSO_LEGITIMO, _c_bn2).strip() == PASSO_LEGITIMO,
       "🔴 e o próximo passo do acionamento passa INTACTO",
       GUARDA(PASSO_LEGITIMO, _c_bn2)[:120])

_janela_pergunta = ("preciso de guincho, estou parado | meu plano cobre carro "
                    "reserva? | %s" % CPF_FICTICIO)
_b, _c_bn2b, _r_bn2b, _m_bn2b = _fio(_janela_pergunta, cliente=True,
                                     mensagem=CPF_FICTICIO)
checar(_m_bn2b.get("pergunta_de_cobertura") is True,
       "🔴 janela `pedido | pergunta | documento`: a PERGUNTA (mais nova) vence",
       repr(_m_bn2b.get("pergunta_de_cobertura")))
MENTIRA_CR = "Sim! Seu plano tem carro reserva por 7 dias, pode contar com isso."
checar(GUARDA(MENTIRA_CR, _c_bn2b).strip() != MENTIRA_CR,
       "🔴 e a mentira sobre a cobertura é ANULADA",
       GUARDA(MENTIRA_CR, _c_bn2b)[:120])

print("\n      🔴 MUTAÇÃO de B-N2: a janela varrida do mais VELHO")
try:
    @staticmethod
    def _varre_do_velho(mensagem_atual, user_query):
        from app.services.knowledge.assistance_plans_base import servico_canonico
        from app.services.skills.cobertura_e_assistencia import (
            INDETERMINADA, PERGUNTA, intencao_da_mensagem,
        )
        from app.agents.tools.infocap_tool import SEPARADOR_DA_JANELA
        atual = str(mensagem_atual or "").strip()
        janela = str(user_query or "")
        intencao = intencao_da_mensagem(atual)
        fonte = atual
        if intencao == INDETERMINADA:
            for parte in [t.strip() for t in janela.split(SEPARADOR_DA_JANELA)
                          if t.strip()]:            # <- SEM `reversed`
                achada = intencao_da_mensagem(parte)
                if achada != INDETERMINADA:
                    intencao, fonte = achada, parte
                    break
        try:
            reconhece = bool(servico_canonico(fonte))
        except Exception:  # noqa: BLE001
            reconhece = False
        return {"pergunta": intencao == PERGUNTA,
                "so_de_cobertura": bool(intencao == PERGUNTA and reconhece),
                "fonte": fonte}

    InfocapPolicyLookupTool._a_intencao_da_mensagem = _varre_do_velho
    _b, _c_mv, _r_mv, _m_mv = _fio(_janela_pedido, cliente=True,
                                   mensagem=CPF_FICTICIO)
    checar(_m_mv.get("pergunta_de_cobertura") is True
           and GUARDA(PASSO_LEGITIMO, _c_mv).strip() != PASSO_LEGITIMO,
           "🔴 MUTAÇÃO B-N2: varrendo do mais VELHO, a pergunta do turno N-2 "
           "volta a trocar o próximo passo do acionamento",
           GUARDA(PASSO_LEGITIMO, _c_mv)[:120])
finally:
    InfocapPolicyLookupTool._a_intencao_da_mensagem = _intencao_original_r4

print("\n      🔴 o 🆘 carrega a PERGUNTA, não o documento")
_banco_doc, _porta_doc = _rodar_a_tool(LIVRE, fonte="meu plano cobre taxi?")
_texto_doc = str(_porta_doc.avisos[0].get("texto") if _porta_doc.avisos else "")
checar("cobre taxi" in _texto_doc.lower(),
       "🔴 o aviso traz a PERGUNTA do cliente", _texto_doc[:220])
checar(CPF_FICTICIO not in _texto_doc,
       "⛔ e não traz o documento", _texto_doc[:220])

# ---------------------------------------------------------------------------
print("\n[18] 🔴 RODADA 4 · P4 — `condicionado` não vira um 'sim' liso")
# 📊 Medido no banco em 19/09/2026: das 25 linhas marcadas PUBLICAR e ainda em
# `proposto`, **17 são `condicionado`** e 8 são `sim`. A maioria do que o
# produto passa a saber HOJE é condicionada — e o juiz mediu que
# "Sim! Seu plano tem vidros" passava inteiro, com a condição sumindo.
BASE._db = lambda supabase_client=None: db
_b, _c_cond, _r_cond, _m_cond = _fio("cobre vidro trincado?", cliente=True,
                                     mensagem="cobre vidro trincado?")
checar((_m_cond.get("cobertura") or {}).get("estado") == "condicionado",
       "a base diz `condicionado`",
       repr((_m_cond.get("cobertura") or {}).get("estado")))
SIM_LISO = "Sim! Seu plano tem vidros, pode acionar."
checar(GUARDA(SIM_LISO, _c_cond).strip() != SIM_LISO,
       "🔴 o 'sim' LISO é ANULADO — a condição não pode sumir",
       GUARDA(SIM_LISO, _c_cond)[:140])
checar("condi" in GUARDA(SIM_LISO, _c_cond).lower(),
       "🔴 e o que sai é o texto do canal, COM a condição",
       GUARDA(SIM_LISO, _c_cond)[:160])
COM_CONDICAO = ("Tem sim: vidros, desde que a cobertura adicional esteja "
                "contratada.")
checar(GUARDA(COM_CONDICAO, _c_cond).strip() == COM_CONDICAO,
       "🔴 CONTROLE: a resposta que DIZ a condição passa INTACTA",
       GUARDA(COM_CONDICAO, _c_cond)[:140])
for _forma in ("Tem vidros, somente para o para-brisa.",
               "Você tem vidros caso tenha contratado o adicional.",
               "Tem sim: vidros — mediante contratação da cobertura adicional."):
    checar(GUARDA(_forma, _c_cond).strip() == _forma,
           "🔴 CONTROLE: %r passa" % _forma[:44], GUARDA(_forma, _c_cond)[:120])

print("      🔴 CONTROLE do [18]: com a base dizendo `sim`, o 'sim' liso PASSA")
_b, _c_sim, _r_sim, _m_sim = _fio("tem guincho?", cliente=True,
                                  mensagem="tem guincho?")
SIM_LISO_OK = "Sim! Seu plano tem guincho, pode acionar."
checar((_m_sim.get("cobertura") or {}).get("estado") == "coberto"
       and GUARDA(SIM_LISO_OK, _c_sim).strip() == SIM_LISO_OK,
       "🔴 CONTROLE: `coberto` + 'sim' liso -> INTACTO (não é defeito quando a "
       "base afirma liso)", GUARDA(SIM_LISO_OK, _c_sim)[:120])
checar(not NODES._afirma_sem_condicao("Tem vidros. Se precisar, é só chamar.",
                                      "vidros") is False,
       "⚠️ e o 'se' avulso na frase SEGUINTE não salva o 'sim' liso — a marca "
       "tem de estar na frase do serviço")

print("\n      🔴 MUTAÇÃO do [18]: a regra desligada")
_afirma_original = NODES._afirma_sem_condicao
try:
    NODES._afirma_sem_condicao = lambda c, r: False
    checar(GUARDA(SIM_LISO, _c_cond).strip() == SIM_LISO,
           "🔴 MUTAÇÃO: sem a regra, o 'sim' liso volta a PASSAR — e 17 das 25 "
           "linhas que entram hoje são `condicionado`",
           GUARDA(SIM_LISO, _c_cond)[:120])
finally:
    NODES._afirma_sem_condicao = _afirma_original

# ---------------------------------------------------------------------------
print("\n[19] 🔴 RODADA 4 · P1 — o par que SÓ OS STEMS resolvem")
# 🔴 O crédito estava no lugar errado (§12.1): 📊 o juiz final rodou a porta de
# `421b2c7` sobre as 22 frases e mediu **1/22**, não 10/22; revertendo os stems
# a matriz sai IDÊNTICA. O ganho veio da separação FORTE × FRACA e da ORDEM.
# ⚠️ Mas os stems resolvem o que a ordem não alcança — e estes dois pares são
# a prova, medidos pelo juiz como perdidos sem eles.
SO_OS_STEMS = ("mandam um borracheiro?", "solicito o guincho")
for _frase in SO_OS_STEMS:
    checar(intencao_da_mensagem(_frase) == PEDIDO,
           "🔴 %r -> PEDIDO (só o stem resolve)" % _frase,
           intencao_da_mensagem(_frase))

print("      🔴 MUTAÇÃO do [19]: os stems revertidos ao texto da rodada 2")
_pedido_original = SKI2._PEDIDO_DE_SERVICO_RE
try:
    import re as _re4
    SKI2._PEDIDO_DE_SERVICO_RE = _re4.compile(
        r"(?<![a-zà-ú])("
        r"preciso|precisava|quero|queria|gostaria|manda|mandar|envia|enviar|"
        r"solicita|solicitar|chama|chamar|chamo|aciona|acionar|pede|pedir|"
        r"me\s+ajuda|socorro|urgente|estou\s+parad|to\s+parad|tô\s+parad|"
        r"abrir\s+um|abre\s+um"
        r")(?![a-zà-ú])", _re4.IGNORECASE)
    _perdidos = [f for f in SO_OS_STEMS
                 if SKI2.intencao_da_mensagem(f) != PEDIDO]
    checar(len(_perdidos) == len(SO_OS_STEMS),
           "🔴 MUTAÇÃO: com as formas FIXAS, os %d pares voltam a ser perdidos "
           "— os stems passam a ser MEDIDOS" % len(SO_OS_STEMS),
           repr(_perdidos))
finally:
    SKI2._PEDIDO_DE_SERVICO_RE = _pedido_original
BASE._db = lambda supabase_client=None: db

# ---------------------------------------------------------------------------
print("\n[20] 🔴 RODADA 5 · B-N3 — quem escolhe o SERVIÇO é a mesma mensagem")
# 📊 Medido pelo juiz final: `question=str(user_query)` levava a JANELA inteira
# ao compositor, e `servico_canonico` pega o PRIMEIRO que casa — a mensagem
# mais VELHA:
#   janela "cobre vidro trincado? | meu plano cobre guincho? | <doc>"
#      fonte da intenção .. "meu plano cobre guincho?"
#      veredito/lacuna .... servico='vidros'
#      AO CORRETOR ........ "…nem que tem nem que não tem vidros."
BASE._db = lambda supabase_client=None: _base_vazia
JANELA_DOIS_SERVICOS = ("cobre vidro trincado? | meu plano cobre guincho? | %s"
                        % CPF_FICTICIO)
_b, _c_bn3, _r_bn3, _m_bn3 = _fio(JANELA_DOIS_SERVICOS, cliente=False,
                                  mensagem=CPF_FICTICIO)
checar(_m_bn3.get("fonte_da_intencao") == "meu plano cobre guincho?",
       "🔴 a fonte da intenção é a pergunta MAIS NOVA",
       repr(_m_bn3.get("fonte_da_intencao")))
checar((_m_bn3.get("cobertura") or {}).get("servico") == "guincho",
       "🔴 e o SERVIÇO do veredito é o dela — não o `vidros` da mais velha",
       repr((_m_bn3.get("cobertura") or {}).get("servico")))
checar("guincho" in str(_m_bn3.get("text") or "")
       and "vidros" not in str(_m_bn3.get("text") or ""),
       "🔴 e o copiloto do corretor nomeia o serviço CERTO",
       str(_m_bn3.get("text") or "")[:160])
checar(L5.descricao_da_lacuna(_m_bn3.get("cobertura") or {}).lower()
       .find("guincho") >= 0,
       "🔴 e a lacuna grava `guincho` em `capability_gaps` — é essa fila que "
       "decide o que se destila depois",
       L5.descricao_da_lacuna(_m_bn3.get("cobertura") or {}))

print("      🔴 CONTROLE do [20]: fonte SEM serviço reconhecível cai na janela")
_b, _c_fb, _r_fb, _m_fb = _fio("cobre vidro trincado? | preciso de ajuda, estou parado",
                               cliente=False, mensagem="preciso de ajuda, estou parado")
checar((_m_fb.get("cobertura") or {}).get("servico") == "vidros",
       "🔴 CONTROLE: sem serviço na fonte, o compositor volta à JANELA e a "
       "Skill CONTINUA respondendo (sem o fallback ela calaria inteira)",
       repr((_m_fb.get("cobertura") or {}).get("servico")))

print("\n      🔴 AS DUAS MUTAÇÕES do [20]")
import app.services.policy_answer_composer as COMP5  # noqa: E402

_comp_original5 = COMP5.compose_policy_answer_with_meta
try:
    def _kwarg_ignorado(**kw):
        kw.pop("fonte_da_intencao", None)
        return _comp_original5(**kw)

    COMP5.compose_policy_answer_with_meta = _kwarg_ignorado
    _b, _c_mi, _r_mi, _m_mi = _fio(JANELA_DOIS_SERVICOS, cliente=False,
                                   mensagem=CPF_FICTICIO)
    checar((_m_mi.get("cobertura") or {}).get("servico") == "vidros",
           "🔴 MUTAÇÃO: kwarg ignorado -> volta a escolher o serviço da "
           "mensagem mais VELHA", repr((_m_mi.get("cobertura") or {}).get("servico")))
finally:
    COMP5.compose_policy_answer_with_meta = _comp_original5

_canonico_original = None
try:
    from app.services.knowledge import assistance_plans_base as B5

    _canonico_original = B5.servico_canonico

    def _sem_fallback(**kw):
        """A mutação: a fonte manda SEMPRE, sem cair de volta na janela."""
        kw["question"] = str(kw.get("fonte_da_intencao") or kw.get("question") or "")
        kw.pop("fonte_da_intencao", None)
        return _comp_original5(**kw)

    COMP5.compose_policy_answer_with_meta = _sem_fallback
    _b, _c_sf, _r_sf, _m_sf = _fio(
        "cobre vidro trincado? | preciso de ajuda, estou parado", cliente=False,
        mensagem="preciso de ajuda, estou parado")
    checar((_m_sf.get("cobertura") or {}) == {} or not _m_sf.get("cobertura"),
           "🔴 MUTAÇÃO: sem o FALLBACK, um pedido sem nome de serviço cala a "
           "Skill INTEIRA — o produto voltaria ao 'sim' de tabela",
           repr(_m_sf.get("cobertura")))
finally:
    COMP5.compose_policy_answer_with_meta = _comp_original5

# ---------------------------------------------------------------------------
print("\n[21] 🔴 RODADA 5 · O ELO produtor→consumidor de `fonte_da_intencao`")
# 📊 Carimbo do juiz: ele apagou `meta["fonte_da_intencao"] = …` NO PRODUTO e
# este arquivo ficou 154/154 VERDE — o `_rodar_a_tool(fonte=…)` injetava a chave
# à mão. É o §0.3 em miniatura: medir A, medir B, e não medir que B CHEGA em A.
BASE._db = lambda supabase_client=None: _base_vazia
_b, _c_elo, _r_elo, _m_elo = _fio("meu plano cobre taxi? | %s" % CPF_FICTICIO,
                                  cliente=True, mensagem=CPF_FICTICIO)
checar(_m_elo.get("fonte_da_intencao") == "meu plano cobre taxi?",
       "🔴 é `_render_content` QUEM ESCREVE `meta['fonte_da_intencao']` — e ela "
       "é a pergunta, não o documento",
       repr(_m_elo.get("fonte_da_intencao")))

print("      🔴 MUTAÇÃO do [21]: a linha apagada no produto")
_render_original = InfocapPolicyLookupTool.__dict__["_render_content"]
try:
    def _sem_a_fonte(self, data, user_query, detail, atendente=None,
                     mensagem_atual=None):
        conteudo, pol, rendered, meta = _render_original(
            self, data, user_query, detail, atendente, mensagem_atual)
        if isinstance(meta, dict):
            meta.pop("fonte_da_intencao", None)   # <- a linha que o juiz apagou
        return conteudo, pol, rendered, meta

    InfocapPolicyLookupTool._render_content = _sem_a_fonte
    _b, _c_mm, _r_mm, _m_mm = _fio("meu plano cobre taxi? | %s" % CPF_FICTICIO,
                                   cliente=True, mensagem=CPF_FICTICIO)
    checar(not _m_mm.get("fonte_da_intencao"),
           "🔴 MUTAÇÃO: sem a linha, a chave SOME do `meta` — e o 🆘 volta a "
           "cair na `mensagem_atual` (o documento)",
           repr(_m_mm.get("fonte_da_intencao")))
finally:
    InfocapPolicyLookupTool._render_content = _render_original

# ---------------------------------------------------------------------------
print("\n[22] 🔴 RODADA 5 · a régua da CONDIÇÃO, medida nos dois sentidos")
# 🔴 Ela protege as 17 linhas `condicionado` que entram em produção hoje.
SIM_LISOS = [
    "Sim! Seu plano tem vidros, e so SE dirigir a uma oficina",
    "Voce tem vidros, pode SE tranquilizar",
    "Tem vidros sim, APENAS me confirme o endereco",
    "Tem vidros sim, CASO queira eu ja abro o chamado",
    "Sim! Seu plano tem vidros, pode acionar.",
    "Voce tem vidros sim, e so chamar",
    "Tem vidros sim, pode ficar tranquilo",
    "Seu plano cobre vidros, sem problema",
]
CONDICOES_LEGITIMAS = [
    "Tem vidros, somente para o para-brisa.",
    "Tem sim: vidros, desde que a cobertura adicional esteja contratada.",
    "Tem vidros, sujeito a contratacao do adicional.",
    "Voce tem vidros caso tenha contratado o adicional.",
    "Tem sim: vidros, com uma condicao do seu contrato.",
    "Tem vidros, somente se contratada a cobertura adicional.",
    "Tem vidros, dependendo da cobertura adicional contratada.",
    "Tem sim: vidros - mediante contratacao da cobertura adicional.",
    "Tem vidros, apenas no para-brisa dianteiro.",
    "Tem vidros ate R$ 500 por evento.",
]
_escapam = [t for t in SIM_LISOS if not NODES._afirma_sem_condicao(t, "vidros")]
_falsos = [t for t in CONDICOES_LEGITIMAS
           if NODES._afirma_sem_condicao(t, "vidros")]
print("      📊 MATRIZ: 'sim liso' anulados %d/%d · condições legítimas "
      "preservadas %d/%d"
      % (len(SIM_LISOS) - len(_escapam), len(SIM_LISOS),
         len(CONDICOES_LEGITIMAS) - len(_falsos), len(CONDICOES_LEGITIMAS)))
checar(not _escapam,
       "🔴 os %d 'sim liso' são ANULADOS (📊 antes da RODADA 5, 5 de 8 "
       "ESCAPAVAM por `se`/`caso`/`apenas` em sentido não condicional)"
       % len(SIM_LISOS), repr(_escapam))
checar(not _falsos,
       "🔴 e as %d condições legítimas passam INTACTAS (📊 antes, "
       "'sujeito a contratação' era anulada: `contratad` sem stem era "
       "alternativa MORTA)" % len(CONDICOES_LEGITIMAS), repr(_falsos))
checar(NODES._afirma_sem_condicao("Tem vidros. Se precisar, é só chamar.",
                                  "vidros"),
       "🔴 CONTROLE: a marca na frase SEGUINTE não salva o 'sim' liso")
BASE._db = lambda supabase_client=None: db

BASE._db = _db_original
sys.exit(_fechar())
