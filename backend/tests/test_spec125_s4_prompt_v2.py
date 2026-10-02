# -*- coding: utf-8 -*-
"""SPEC-125 S4 — o prompt novo (v2), a volta sem deploy (v1) e o que não pode sumir.

O MOTOR é o de produção: `prompts.build_composite_prompt` (a montagem que o
`graph` usa), `graph._versao_do_prompt` (a chave `agents.prompt_versao`, lida
do banco por `id` E `company_id`) e `nodes.agent_node` (os fiscais e o diário)
com um modelo DUBLÊ — sem rede, sem banco, sem LLM, sem PII (CPF sintético
válido pelo dígito verificador).

```
G-V1   o v1 é o prompt de 01/10/2026 BYTE A BYTE (hash + montagem do commit base)
G-12   as travas MANTER do laudo (D6) estão no v2 — e o guarda FICA VERMELHO se
       qualquer âncora for tirada (mutação por regra, §9.3 corolário)
G-T11  nenhuma regra contraditória de como perguntar sobra nos 4 lugares
G-CHAVE  a chave escolhe a base; outra corretora não decide; banco fora → padrão
G-T13  o fiscal da pergunta repetida vê o CPF dito na CONVERSA e no bloco da S3
G-D10  no v2 o fiscal de tamanho MEDE até 2× e só regenera acima (controle: v1)
G-D7   o diário: 1 linha no momento de julgamento, 0 no turno comum
```
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import os
import re
import subprocess
import sys
import tempfile

import pytest

from app.core import prompts as P

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(BACKEND)

#: o commit base da SPEC-125 antes da S4 — onde o `ATTENDANCE_BASE_PROMPT` de
#: 01/10/2026 vive intacto.
COMMIT_BASE = "3d335b3"
SHA_DO_V1 = "2713eee75b689c7b9b7889caa6e61043eb5aaff4a4db645d79d5e469df734a77"

#: CPF sintético, válido pelo dígito verificador (não é de ninguém).
CPF = "52998224725"


def _ler(rel: str) -> str:
    with open(os.path.join(RAIZ, rel), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentarios(fonte: str) -> str:
    """O texto que o MODELO lê numa fonte Python/TS: sem as linhas de comentário."""
    return "\n".join(l for l in fonte.split("\n")
                     if not l.strip().startswith("#") and not l.strip().startswith("//"))


# =========================================================================
# G-V1 — o v1 é o de hoje, byte a byte
# =========================================================================
def test_v1_e_o_texto_de_01_10_byte_a_byte():
    v1 = P.ATTENDANCE_BASE_PROMPT_V1
    assert len(v1) == 22333
    assert hashlib.sha256(v1.encode("utf-8")).hexdigest() == SHA_DO_V1


def _prompts_do_commit_base():
    try:
        fonte = subprocess.run(["git", "show", f"{COMMIT_BASE}:backend/app/core/prompts.py"],
                               cwd=RAIZ, capture_output=True, timeout=60).stdout
    except Exception:  # noqa: BLE001
        return None
    if not fonte:
        return None
    caminho = os.path.join(tempfile.mkdtemp(), "prompts_base.py")
    with open(caminho, "wb") as fh:
        fh.write(fonte)
    spec = importlib.util.spec_from_file_location("_prompts_do_commit_base", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CASOS_DE_MONTAGEM = [
    dict(agent_role="attendance"),
    dict(agent_role="attendance", agent_display_name="Atendente X",
         company_display_name="{{CORRETORA:A}}", company_facts_block="### A CORRETORA\n- fato",
         jeito_block="### O JEITO\n- jeito"),
    dict(agent_role="insured_external"),
    dict(agent_role="core"),
]


@pytest.mark.parametrize("kw", CASOS_DE_MONTAGEM)
def test_com_a_chave_em_v1_a_montagem_e_a_do_commit_base(kw):
    base = _prompts_do_commit_base()
    if base is None:
        pytest.skip("git indisponível — o hash do texto (teste acima) segue valendo")
    hoje = P.build_composite_prompt("instrucoes do cliente", prompt_versao="v1", **kw)
    antes = base.build_composite_prompt("instrucoes do cliente", **kw)
    assert hoje == antes
    # CONTROLE (§9.3 corolário): as duas versões CONSEGUEM ser diferentes.
    if kw["agent_role"] != "core":
        assert P.build_composite_prompt("instrucoes do cliente", prompt_versao="v2", **kw) != antes


# =========================================================================
# G-12 — as travas MANTER (laudo INV, D6) estão no v2
# =========================================================================
#: Regra → frases-âncora (todas têm de estar). T21/T25 moram no CÓDIGO.
MANTER = {
    "T5 só relatar o que fez": ["SÓ RELATE O QUE VOCÊ REALMENTE FEZ", "Prometeu, executou",
                                "Já cobrei a seguradora", "MESMA resposta"],
    "T6 nunca inventar protocolo/prazo/agendamento": [
        "NUNCA invente protocolo, prazo ou agendamento", "MODO TESTE INICIADO",
        "Só diga \"agendado\" com o agendamento CONFIRMADO"],
    "T7 cobertura só com evidência": ["NUNCA confirme cobertura sem evidência da apólice",
                                      "A CARTA DE CONHECIMENTO NÃO É A APÓLICE DELE",
                                      "APÓLICE vence", "nunca copie o texto da carta"],
    "T8 confirmar antes de acionar": ["Antes de ACIONAR, confirme", "dados_confirmados=true",
                                      "espere o \"sim\""],
    "T15 pessoa no grave": ["acione um atendente humano", "SINISTRO", "risco à vida",
                            "condomínio", "empresarial", "serviço sem corredor de acionamento",
                            "pediu uma pessoa", "irritado E pedindo saída", "disjuntor",
                            # 🔴 conserto X5 (RT P6): o "não há saída" e a escalada da falha
                            #    voltaram — o D6 só autorizava afrouxar o "irritado".
                            "ou não há saída", "corrija o dado ou chame a equipe",
                            "a equipe com o dossiê"],
    "T16 guincho por colisão = sinistro": ["Guincho por acidente/colisão é SINISTRO"],
    "T17 identidade": ["NÃO ANUNCIA", "INSISTIU", "ASSUMA", "NEGAR é mentira", "sou humano"],
    "T18 vocabulário de URA": ["PROIBIDO o vocabulário de URA", "vou te transferir",
                               "você será atendido em breve"],
    "T19 mascarar na saída": ["só mascarados", "Nunca exponha dados de outros clientes ou da corretora"],
    "T23 apresentação fora do modelo": [
        "Quando (e se) você deve se apresentar é dito a cada turno na linha APRESENTAÇÃO"],
    # 📊 os 4 defeitos da LINHA DE BASE (docs/canon/reports/SPEC-125-LINHA-DE-BASE.md):
    "BASE C16 dado de terceiro (2/2 FAIL)": [
        "A apólice é do TITULAR", "NÃO consulte e não revele nada, nem se a apólice existe",
        "só o titular pode pedir"],
    "BASE 1ª resposta atende (24/36 'Como posso ajudar?')": [
        "A primeira resposta já atende o pedido",
        "Nunca pergunte \"como posso ajudar?\" a quem já disse como"],
    "BASE T8 acionou antes de confirmar (C2/C3/C13)": [
        "`dados_confirmados=true` só depois desse \"sim\"",
        "nunca no mesmo turno em que os dados chegaram"],
    "BASE C13 resultado na mesma resposta, sem repedir a placa": [
        "Acionou neste turno? A MESMA resposta conta o resultado real",
        "placa e veículo vêm da apólice (confirme, não pergunte)"],
}


def faltando(texto: str) -> list:
    """As regras MANTER cuja âncora sumiu do texto. **PURA.**"""
    return [regra for regra, ancoras in MANTER.items() if any(a not in texto for a in ancoras)]


def _v2_montado() -> str:
    return P.build_composite_prompt("instrucoes", agent_role="attendance", prompt_versao="v2",
                                    agent_display_name="Atendente X")


def test_as_travas_manter_estao_todas_no_v2():
    assert faltando(_v2_montado()) == []


@pytest.mark.parametrize("regra", list(MANTER))
def test_o_guarda_fica_VERMELHO_se_uma_trava_sumir(regra):
    """§9.3 corolário: um guarda que não tem como falhar não guarda nada."""
    texto = _v2_montado()
    for ancora in MANTER[regra]:
        texto = texto.replace(ancora, "")
    assert regra in faltando(texto)


def test_t21_e_t25_continuam_no_codigo():
    """Não moram no prompt — e a S4 não os tocou."""
    fim = _ler("backend/app/services/o_fim_do_atendimento.py")
    assert "async def a_ia_deve_calar(" in fim and "def janela_de_silencio_dias(" in fim
    assert re.search(r"^MAX_BALLOONS = 4$", _ler("backend/app/services/whatsapp/balloons.py"), re.M)


def test_o_v2_tirou_o_que_o_laudo_mandou_tirar():
    v2 = P.ATTENDANCE_BASE_PROMPT_V2
    assert "Confirme entendimento antes de agir" not in v2          # T9
    assert "1 minutinho" not in v2                                   # T10
    assert "após 2 tentativas" not in v2                             # T15: só "irritado E pedindo saída"
    # e o v1 continua com elas (a volta é o de antes, inteiro)
    assert "Confirme entendimento antes de agir" in P.ATTENDANCE_BASE_PROMPT_V1


def test_o_v2_abre_pelo_objetivo_e_pelo_julgamento():
    v2 = P.ATTENDANCE_BASE_PROMPT_V2
    primeira_secao = v2.find("### ")
    assert v2[primeira_secao:].startswith("### 🎯 O OBJETIVO E O JULGAMENTO")
    for frase in ("Deduza o óbvio", "Derrapei na chuva", "Não pergunte o que você já sabe",
                  "O QUE JÁ SABEMOS", "UMA fala"):
        assert frase in v2, frase
    assert v2.find("O OBJETIVO E O JULGAMENTO") < v2.find("LINHAS QUE NÃO SE CRUZAM") < v2.find("### 🛠️ FERRAMENTAS")


def test_tamanho_medido():
    v1, v2 = len(P.ATTENDANCE_BASE_PROMPT_V1), len(P.ATTENDANCE_BASE_PROMPT_V2)
    print("\n[TAMANHO] v1 %d chars · v2 %d chars (%.0f%%) · 💭 ~%d tokens a menos por turno (chars/4)"
          % (v1, v2, 100.0 * v2 / v1, (v1 - v2) // 4))
    # 💭 o alvo da SPEC era "~metade"; os 4 defeitos da LINHA DE BASE (C16, 1ª resposta,
    # T8, C13) entraram depois e custaram ~900 chars. O teto guarda contra o prompt
    # voltar a inchar: acima de 62% do v1, alguém está devolvendo microgerência.
    assert v2 <= 0.62 * v1


# =========================================================================
# G-T11 — UMA regra de como perguntar; as contraditórias sumiram dos 4 lugares
# =========================================================================
CONTRADITORIAS = re.compile(r"uma por vez|informa[cç][aã]o por vez|um de cada vez|"
                            r"colete de uma vez s[oó]|bloco de at[eé] 4", re.IGNORECASE)


def test_nenhuma_regra_contraditoria_no_prompt_v2():
    assert not CONTRADITORIAS.findall(P.ATTENDANCE_BASE_PROMPT_V2)
    assert "### 🎯 COMO PERGUNTAR (a regra é uma só)" in P.ATTENDANCE_BASE_PROMPT_V2


def test_nenhuma_regra_contraditoria_no_molde():
    molde = _sem_comentarios(_ler("lib/admin/agent-blueprints-canonical.ts"))
    assert not CONTRADITORIAS.findall(molde)
    assert "pergunte so o que falta e muda a proxima acao" in molde


def test_nenhuma_regra_contraditoria_na_ferramenta_de_acionamento():
    fonte = _sem_comentarios(_ler("backend/app/agents/tools/insurer_dispatch_tool.py"))
    assert not CONTRADITORIAS.findall(fonte)
    # a LIÇÃO do GOLD-ELEC-005 (não interrogar) migrou e continua escrita
    assert "SOMENTE o que nunca foi informado" in fonte and "nunca um interrogatório" in fonte


def test_a_conduta_no_v2_nao_manda_colher_de_uma_vez():
    fonte = _ler("backend/app/agents/graph.py")
    corpo = fonte[fonte.find("async def _conduta_do_caso("):fonte.find("def montar_bloco_recuperado(")]
    v1 = corpo.find('if prompt_versao == "v1":')
    assert v1 > 0
    # a volta (v1) mantém o título de 01/10/2026; o v2 não manda colher de uma vez
    assert corpo.find('_lista("ficha_coleta", "Colete de uma vez só (não peça em conta-gotas):", 12)') > v1
    assert '_lista("ficha_coleta", "O que este caso costuma precisar (peça só o que ainda falta):", 12)' in corpo


def test_o_prompt_do_banco_troca_so_a_frase_do_molde():
    """🔴 Conserto X6 (§9.3 — a verdade mudou): a troca saiu da migration (parte B
    DESCARTADA, nunca aplicada) e foi para a MONTAGEM, só no v2 — assim a volta ao v1
    continua byte a byte sem `replace` inverso no banco. A lição migra: a frase do molde
    antigo vira EXATAMENTE a do molde novo, e só ela."""
    sql = _ler("backend/supabase/migrations/20261001_07_spec125_prompt_v2.sql")
    assert "DESCARTADA" in sql and "ROLLBACK" in sql and "md5" in sql
    antes = "x; colete uma informacao por vez; y"
    assert P.trocar_a_frase_do_banco_no_v2(antes) == "x; " + P.FRASE_NOVA_DO_MOLDE + "; y"
    assert P.FRASE_NOVA_DO_MOLDE in _sem_comentarios(_ler("lib/admin/agent-blueprints-canonical.ts"))


def test_o_portal_deduz_antes_de_perguntar():
    fonte = _sem_comentarios(_ler("backend/app/agents/tools/portal_params.py"))
    assert "PERGUNTE AGORA" not in fonte
    assert "Escolha pelo que ele ja contou" in fonte


# =========================================================================
# G-CHAVE — `agents.prompt_versao`, por agente, nesta corretora
# =========================================================================
A = "aaaaaaaa-0000-4000-8000-00000000000a"
B = "bbbbbbbb-0000-4000-8000-00000000000b"
AGENTE = "cccccccc-0000-4000-8000-00000000000c"


class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, linhas, filtros_ignorados=False):
        self.linhas, self.ignorar = linhas, filtros_ignorados

    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        if not self.ignorar:
            self.linhas = [x for x in self.linhas if str(x.get(campo)) == str(valor)]
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        return _Resp(list(self.linhas))


class _Banco:
    def __init__(self, linhas, filtros_ignorados=False, quebra=False):
        self.linhas, self.ignorar, self.quebra = linhas, filtros_ignorados, quebra

    def table(self, nome):
        if self.quebra:
            raise RuntimeError("banco fora")
        assert nome == "agents"
        return _Consulta(list(self.linhas), self.ignorar)


def test_a_chave_escolhe_a_base():
    from app.agents.graph import _versao_do_prompt

    banco = _Banco([{"id": AGENTE, "company_id": A, "prompt_versao": "v1"}])
    assert _versao_do_prompt(banco, A, AGENTE) == "v1"
    banco.linhas[0]["prompt_versao"] = "v2"
    assert _versao_do_prompt(banco, A, AGENTE) == "v2"   # o update vale no PRÓXIMO turno, sem cache


def test_outra_corretora_nao_decide_mesmo_se_o_filtro_do_banco_falhar():
    from app.agents.graph import _versao_do_prompt

    # o banco "esquece" o filtro e devolve a linha de B: o cinto no código a recusa
    banco = _Banco([{"id": AGENTE, "company_id": B, "prompt_versao": "v1"}], filtros_ignorados=True)
    assert _versao_do_prompt(banco, A, AGENTE) == P.PROMPT_VERSAO_PADRAO
    # CONTROLE: a mesma linha, na corretora certa, decide
    assert _versao_do_prompt(banco, B, AGENTE) == "v1"


def test_sem_banco_ou_valor_invalido_vale_o_padrao():
    from app.agents.graph import _versao_do_prompt

    assert _versao_do_prompt(_Banco([], quebra=True), A, AGENTE) == "v2"
    assert _versao_do_prompt(None, A, AGENTE) == "v2"
    assert P.normalizar_prompt_versao("v9") == "v2" and P.normalizar_prompt_versao(" V1 ") == "v1"
    assert P._select_base_prompt("attendance", "v1") is P.ATTENDANCE_BASE_PROMPT_V1
    assert P._select_base_prompt("core", "v1") is P.CORE_BASE_PROMPT       # o Core não tem versão


def test_o_graph_passa_a_chave_para_a_montagem_e_para_os_fiscais():
    """O fio no `_build_initial_state` (o turno inteiro roda na bancada N3): a chave lida
    vai à montagem E ao `agent_data` que os fiscais do `agent_node` leem."""
    fonte = _ler("backend/app/agents/graph.py")
    corpo = fonte[fonte.find("async def _build_initial_state("):]
    assert "_prompt_versao = _versao_do_prompt(supabase_client, company_id, agent_id, real_agent_data)" in corpo
    assert '"prompt_versao": _prompt_versao' in corpo
    assert "prompt_versao=_prompt_versao," in corpo
    assert "quem_e_o_segurado(str(company_id), _fone, db=supabase_client)" in corpo


def test_o_bloco_de_cartas_do_v2_e_enxuto():
    from app.agents import graph as G

    cartas = G.SEPARADOR_DE_TRECHOS.join("carta %d " % i + "x" * 500 for i in range(30))
    _t, antes = G.montar_bloco_recuperado(cartas, "pergunta")
    _t2, depois = G.montar_bloco_recuperado(cartas, "pergunta", teto=G.TETO_DAS_CARTAS_NO_ATENDIMENTO_V2_CHARS,
                                            max_trechos=G.CARTAS_NO_ATENDIMENTO_V2)
    print("\n[CARTAS] 30 cartas de ~510 chars: antes %d trechos / %d chars · v2 %d trechos / %d chars"
          % (antes["trechos_no_bloco"], antes["chars_depois"], depois["trechos_no_bloco"], depois["chars_depois"]))
    assert antes["trechos_no_bloco"] == 30
    assert depois["trechos_no_bloco"] == 8 and depois["chars_depois"] <= 8000
    assert "ficaram de fora" in _t2                                   # o corte é DITO, nunca calado


def test_telefone_da_sessao():
    from app.agents.graph import _telefone_da_sessao

    assert _telefone_da_sessao("whatsapp:5547999990000:%s:%s" % (A, AGENTE)) == "5547999990000"
    assert _telefone_da_sessao("web:abc") == ""


# =========================================================================
# agent_node com modelo dublê (o motor real dos fiscais e do diário)
# =========================================================================
class _Modelo:
    def __init__(self, textos):
        self.textos, self.chamadas = list(textos), []

    async def ainvoke(self, mensagens, config=None):
        from langchain_core.messages import AIMessage

        self.chamadas.append(mensagens)
        return AIMessage(content=self.textos[min(len(self.chamadas) - 1, len(self.textos) - 1)])


def _turno(mensagens, textos, *, versao="v2", dynamic="", tools_used=None, monkeypatch=None):
    import app.services.activity_log as AL
    from app.agents import nodes as N

    feed, diario, erros_leves = [], [], []

    async def _log(company_id, category, title, detail=""):
        feed.append(title)

    def _julgamento(state, achado):
        diario.append(achado)

    def _erro_leve(state, sinal):
        erros_leves.append(sinal)

    monkeypatch.setattr(AL, "log_activity", _log)
    monkeypatch.setattr(N, "_registrar_julgamento_no_diario", _julgamento)
    monkeypatch.setattr(N, "_marcar_erro_leve_no_diario", _erro_leve)
    modelo = _Modelo(textos)
    estado = {"messages": list(mensagens), "company_id": A, "session_id": "whatsapp:5500000000000:%s:%s" % (A, AGENTE),
              "user_id": "u", "company_config": {},
              "agent_data": {"agent_role": "attendance", "prompt_versao": versao},
              "system_prompt": "prompt", "static_prompt": "prompt", "dynamic_context": dynamic,
              "ficha_atendimento": {"confirmados": {"problema_descricao": {"valor": "x", "origem": "cliente"}}},
              "tools_used": list(tools_used or [])}
    saida = asyncio.run(N.agent_node(estado, None, modelo))
    texto = ""
    for m in saida.get("messages") or []:
        texto = getattr(m, "content", "") or texto
    return modelo, texto, feed, diario, erros_leves


REPERGUNTA = "Me passa seu CPF pra eu localizar certinho?"
CONFIRMA = "Certo! É o CPF final 4725, né? Já vou consultar sua apólice."


def test_t13_o_cpf_dito_na_conversa_nao_se_pede_de_novo(monkeypatch):
    from langchain_core.messages import AIMessage, HumanMessage

    conversa = [HumanMessage(content="meu cpf é 529.982.247-25"), AIMessage(content="Obrigada!"),
                HumanMessage(content="o carro não pega")]
    modelo, texto, _f, _d, leves = _turno(conversa, [REPERGUNTA, CONFIRMA], monkeypatch=monkeypatch)
    assert len(modelo.chamadas) == 2 and texto == CONFIRMA
    assert leves == ["agente_repetiu_pergunta"]                       # o sinal de erro leve do D7
    # e a regeneração recebe só o FINAL do documento, nunca o número inteiro
    aviso = str(modelo.chamadas[1][-1].content)
    assert "final 4725" in aviso and CPF not in aviso


def test_t13_o_cpf_do_bloco_da_s3_tambem_conta(monkeypatch):
    from langchain_core.messages import HumanMessage

    from app.agents.quem_e_o_segurado import bloco_para_o_prompt

    bloco = bloco_para_o_prompt({"nome": "Fulano", "nome_origem": "contato do WhatsApp", "cpf": CPF,
                                 "cpfs_distintos": 1, "cpf_de_assunto_anterior": True})
    modelo, texto, *_ = _turno([HumanMessage(content="oi, preciso de chaveiro")], [REPERGUNTA, CONFIRMA],
                               dynamic="\n\n" + bloco, monkeypatch=monkeypatch)
    assert len(modelo.chamadas) == 2 and texto == CONFIRMA


def test_t13_CONTROLE_sem_cpf_conhecido_pedir_e_o_certo(monkeypatch):
    from langchain_core.messages import HumanMessage

    modelo, texto, _f, _d, leves = _turno([HumanMessage(content="oi, preciso de chaveiro")],
                                          [REPERGUNTA, CONFIRMA], monkeypatch=monkeypatch)
    assert len(modelo.chamadas) == 1 and texto == REPERGUNTA and leves == []


MEDIA = ("Entendi o que aconteceu com o seu carro. O seu plano cobre o guincho até 200 km. "
         "A franquia não se aplica à assistência. O prestador leva o carro para a oficina que você escolher. "
         "Se precisar de táxi depois, a apólice também cobre.")          # 5 frases, ~250 chars: entre 1× e 2×
LONGA = " ".join("Frase número %d explicando um detalhe do seguro." % i for i in range(1, 9))  # 8 frases > 2×
CURTA = "Certo, o guincho está coberto e eu já sigo com o pedido."


def test_d10_no_v2_entre_1x_e_2x_mede_e_nao_regenera(monkeypatch):
    from langchain_core.messages import HumanMessage

    modelo, texto, feed, *_ = _turno([HumanMessage(content="o guincho é coberto?")], [MEDIA, CURTA],
                                     monkeypatch=monkeypatch)
    assert len(modelo.chamadas) == 1 and texto == MEDIA
    assert any("tamanho_fora_da_classe" in t for t in feed)          # a MEDIÇÃO ficou


def test_d10_no_v2_acima_de_2x_regenera_uma_vez(monkeypatch):
    from langchain_core.messages import HumanMessage

    modelo, texto, *_ = _turno([HumanMessage(content="o guincho é coberto?")], [LONGA, CURTA],
                               monkeypatch=monkeypatch)
    assert len(modelo.chamadas) == 2 and texto == CURTA
    assert "DOBRO" in str(modelo.chamadas[1][-1].content)


def test_d10_CONTROLE_no_v1_a_regua_de_antes_regenera(monkeypatch):
    from langchain_core.messages import HumanMessage

    modelo, texto, *_ = _turno([HumanMessage(content="o guincho é coberto?")], [MEDIA, CURTA],
                               versao="v1", monkeypatch=monkeypatch)
    assert len(modelo.chamadas) == 2 and texto == CURTA


def test_d7_uma_linha_no_momento_de_julgamento(monkeypatch):
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    turno = [HumanMessage(content="a franquia é paga na oficina?"),
             AIMessage(content="", tool_calls=[{"name": "knowledge_base_search", "args": {}, "id": "t1"}]),
             ToolMessage(content="{\"found\": true}", tool_call_id="t1", name="knowledge_base_search")]
    _m, _t, _f, diario, _l = _turno(turno, [CURTA], tools_used=["knowledge_base_search"],
                                    monkeypatch=monkeypatch)
    assert [d["momento"] for d in diario] == ["respondeu_regra"]
    assert diario[0]["fonte"] == "a base de conhecimento da corretora"


def test_d7_zero_linhas_no_turno_comum(monkeypatch):
    from langchain_core.messages import HumanMessage

    _m, _t, _f, diario, _l = _turno([HumanMessage(content="bom dia")], ["Bom dia! Como posso ajudar?"],
                                    monkeypatch=monkeypatch)
    assert diario == []


def test_d7_zero_linhas_quando_chamou_pessoa_quem_escreve_e_o_handoff(monkeypatch):
    """`chamou_pessoa` já é escrito por `human_handoff` (SPEC-123 F7): aqui não dobra."""
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    turno = [HumanMessage(content="isso é coberto?"),
             AIMessage(content="", tool_calls=[{"name": "knowledge_base_search", "args": {}, "id": "t1"}]),
             ToolMessage(content="{}", tool_call_id="t1", name="knowledge_base_search")]
    _m, _t, _f, diario, _l = _turno(turno, [CURTA], tools_used=["knowledge_base_search", "request_human_agent"],
                                    monkeypatch=monkeypatch)
    assert diario == []
