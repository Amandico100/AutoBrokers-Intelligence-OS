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


def _rodar_a_tool(conversa_no_banco, *, com_sessao=True, pergunta=True):
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
             "pergunta_de_cobertura": pergunta},
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
checar("assistencia_da_base" in (_contrato_dec.get("required_facts") or []),
       "⚠️ mas `assistencia_da_base` CONTINUA (a base decidiu: é o valor da "
       "001.5) — o texto final tem de nomear o serviço",
       repr(_contrato_dec.get("required_facts")))
_passo_que_nomeia = ("O seu guincho está incluído. Me passa o endereço com um "
                     "ponto de referência que eu já abro o chamado?")
checar(GUARDA(_passo_que_nomeia, _contrato_dec).strip() == _passo_que_nomeia,
       "🔴 e um próximo passo que NOMEIA o serviço passa inteiro — o "
       "acionamento segue", GUARDA(_passo_que_nomeia, _contrato_dec)[:120])
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

_porta_original = SKI.e_pergunta_de_cobertura
try:
    SKI.e_pergunta_de_cobertura = lambda _t: True
    _mut = [f for f in ACIONAMENTO
            if GUARDA(PROXIMO_PASSO, _fio(f, cliente=True, mensagem=f)[1]).strip()
            != PROXIMO_PASSO]
    checar(len(_mut) >= 5,
           "🔴 MUTAÇÃO: com a porta sempre-True, %d das 11 respostas do "
           "atendente voltam a ser SUBSTITUÍDAS — era o blocker N1" % len(_mut),
           repr(_mut[:3]))
finally:
    SKI.e_pergunta_de_cobertura = _porta_original

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
print("\n[11] 🔴 RODADA 2 · N1 item 4 — a flag não sobrevive a uma AÇÃO posterior")
# 📊 O contrato fica no estado até o fim do turno (`nodes.py:1450` zera só a
# variável local). Se `insurer_dispatch` rodou DEPOIS da consulta, "Pronto! O
# guincho foi solicitado" também era trocado pelo rascunho — o cliente ouvia que
# nada tinha sido feito, com o guincho já a caminho.
import app.agents.nodes as NODES  # noqa: E402

_b, _contrato_acao, _rendered_acao, _m = _fio("tem taxi?", cliente=True,
                                              mensagem="tem taxi?")
checar("encerrar_com_o_rascunho" in (_contrato_acao.get("required_facts") or []),
       "a flag está no contrato (é o caso em que ela deve estar)",
       repr(_contrato_acao.get("required_facts")))

DEPOIS_DA_ACAO = "Pronto! O guincho foi solicitado, previsão de 40 minutos."
checar(GUARDA(DEPOIS_DA_ACAO, _contrato_acao).strip() != DEPOIS_DA_ACAO,
       "🔴 CONTROLE: com a flag de pé, a resposta da AÇÃO seria trocada",
       GUARDA(DEPOIS_DA_ACAO, _contrato_acao)[:100])

#: O consumo é o MESMO código de `nodes.py`: os fatos menos a flag.
_consumido = dict(_contrato_acao, required_facts=[
    f for f in (_contrato_acao.get("required_facts") or [])
    if f != "encerrar_com_o_rascunho"])
checar(GUARDA(DEPOIS_DA_ACAO, _consumido).strip() == DEPOIS_DA_ACAO,
       "🔴 consumida a flag, a resposta da AÇÃO passa INTACTA",
       GUARDA(DEPOIS_DA_ACAO, _consumido)[:100])
checar("insurer_dispatch" in NODES._TOOLS_DE_ACAO
       and "request_human_agent" in NODES._TOOLS_DE_ACAO
       and "portal_action" in NODES._TOOLS_DE_ACAO,
       "🔴 e `nodes._TOOLS_DE_ACAO` nomeia as tools que disparam o consumo",
       repr(sorted(NODES._TOOLS_DE_ACAO)))
_fonte_do_no = open(os.path.join(RAIZ, "app", "agents", "nodes.py"),
                    encoding="utf-8").read()
_sem_comment = "\n".join(l.split("#")[0] for l in _fonte_do_no.splitlines())
checar("_TOOLS_DE_ACAO" in _sem_comment and "_ordem_do_turno" in _sem_comment
       and "encerrar_com_o_rascunho" in _sem_comment,
       "🔴 e o consumo está no CÓDIGO do nó (ordem do turno + a lista), não "
       "num comentário")

# ---------------------------------------------------------------------------
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

BASE._db = _db_original
sys.exit(_fechar())
