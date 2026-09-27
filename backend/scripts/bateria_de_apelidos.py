# -*- coding: utf-8 -*-
"""SPEC-119 F4 · BATERIA 1 — os apelidos do cliente contra o AGENTE REAL.

🔴 O QUE ESTA BATERIA DECIDE
============================
A régua tem um item que vale 4 pontos — *"apelidos do jeito que o cliente
fala"* (`scripts/rubrica.py:924`) — e ele é **circular por construção**: só
pontua com ≥ 3 apelidos CONFERIDOS no Espelho (`regua_motor.apelidos_conferidos`),
e o Espelho só cresce com o agente ligado.

Esta bateria troca a pergunta. Em vez de *"a tabela `_SUBSERVICE_ALIASES` tem
três strings vivas?"*, ela pergunta o que importa ao segurado:

    🔴 o AGENTE REAL, com a apólice já identificada, escolhe o SUBSERVIÇO CERTO
       quando o cliente descreve o problema com as palavras DELE?

⛔ O QUE ESTA BATERIA **NÃO** FAZ
   · não envia nada a seguradora nenhuma: o nível N1 da bancada roda com
     `interrupt_before=["tools"]` — a chamada de ferramenta é MEDIDA e **nunca
     executada** (`evals/bancada.py:motor_agente`);
   · não liga nem desliga agente, não escreve no banco (modo ensaio);
   · não cria motor paralelo: o motor é `create_agent_graph` do produto, pelo
     runner que já existe (`app/services/evals/bancada.py:rodar_bancada`).
     Os casos entram em MEMÓRIA, pelo parâmetro `casos=` — o corpus versionado
     em `tests/corpus/bancada/**` não é tocado.

O MOTOR, elo a elo (CLAUDE.md §9.4 — chamar o motor, nunca o regex)
-------------------------------------------------------------------
```
a fala do cliente
  → app/agents/graph.py:create_agent_graph(agent_role="attendance")   grafo REAL
  → app/agents/nodes.py:agent_node                                    prompt REAL
  → app/agents/tools/insurer_dispatch_tool.py:InsurerDispatchInput    contrato REAL
       (a descrição é GERADA por `_catalogo_de_subservicos()`)
  → o `subservice` que o modelo escreveu                              o que se mede
  → app/services/corridor_playbooks.py:canonical_subservice           a tabela de apelidos
```

A ORIGEM DE CADA FRASE — 📊 medida, nunca imaginada (CLAUDE.md §12.1)
---------------------------------------------------------------------
Cada caso declara `espelho=<termo>`: o script CONTA, na hora, quantas mensagens
de cliente do Espelho contêm aquele termo (`regua_motor.apelidos_conferidos`) e
imprime o número ao lado da frase. Frase sem lastro no acervo sai marcada
`💭 ILUSTRATIVA` na tabela — e o relatório não pode citá-la como fato.

⚠️ A FICHA NÃO CONTÉM O SERVIÇO. `attendance_ficha.bloco_para_o_prompt` escreve
`Caso: <ramo> · <servico> · <seguradora>` no prompt: um caso com `servico`
preenchido entregaria a resposta ao modelo e a bateria não provaria nada.

A LINHA DE CONTROLE (CLAUDE.md §9.2)
------------------------------------
Dois casos que **têm** de falhar o acionamento, e por motivos diferentes:
  · `ctrl-fora-do-catalogo-*`: trabalho que NENHUM playbook faz (portão
    eletrônico, dedetização). O agente tem de recusar/encaminhar — inventar
    `subservice` aqui é o defeito que a bateria caça;
  · `ctrl-sinistro-colisao`: colisão é SINISTRO, não assistência — vai a humano.
Sem eles, um acerto se credita ao lugar errado.

⚠️ NÃO-DETERMINISMO: braço real varia. O critério é **pass^k** (k tentativas,
todas certas) e o script imprime tentativa a tentativa. Este arquivo é um
SCRIPT, e de propósito: ele NÃO entra na bateria de `pytest`, porque teste que
chama API quebra sozinho e queima crédito (pacote F4b §4).

    cd backend
    # de graça, para conferir a mecânica dos casos (nenhuma API):
    python scripts/bateria_de_apelidos.py --braco dublê:perfeito --k 1
    # o braço REAL de produção do papel `atendimento` (openai:gpt-6-sol:high):
    python scripts/bateria_de_apelidos.py --producao --k 1 --teto-usd 1.50
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ⚠️ armadilha nº 2 do pacote: sem isto, um print com emoji morre de
# UnicodeEncodeError em cp1252 **e o processo sai 0** (falso verde).
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


#: O braço REAL do papel `atendimento` em produção — lido do snapshot de
#: modelos, nunca fixado aqui (`app/factories/modelos_snapshot.json:papeis`).
def braco_de_producao() -> str:
    from pathlib import Path

    arq = Path(RAIZ) / "app" / "factories" / "modelos_snapshot.json"
    papel = json.loads(arq.read_text(encoding="utf-8"))["papeis"]["atendimento"]
    return f"{papel['provider']}:{papel['modelo_primario']}:{papel['esforco']}"


# ═════════════════════════════════════════════════════════════════════════════
# OS CASOS — (chave, seguradora, ramo, fala do cliente, subserviço esperado,
#             termo a CONFERIR no Espelho)
# ═════════════════════════════════════════════════════════════════════════════
#
# 🔴 `esperado=None` significa "NENHUM acionamento": é linha de CONTROLE.
# A seguradora de cada caso é escolhida para que o subserviço esperado EXISTA
# no playbook dela (`subservices`) — senão a ferramenta devolveria handoff por
# cobertura, e a bateria mediria outra coisa.
CASOS = [
    # ── AUTO ────────────────────────────────────────────────────────────────
    ("apelido-auto-guincho-motor-morreu", "allianz", "auto",
     "meu carro quebrou aqui, o motor morreu e não liga mais, preciso de um guincho",
     "guincho", "guincho"),
    ("apelido-auto-guincho-reboque", "porto", "auto",
     "Preciso de um reboque, o carro tem que sair daqui",
     "guincho", "reboque"),
    ("apelido-auto-mecanico-nao-pega", "hdi", "auto",
     "Meu carro não pega. Não sei o que aconteceu. Não liga",
     "socorro_mecanico", "nao pega"),
    ("apelido-auto-mecanico-pane", "zurich", "auto",
     "Pane acho. Não liga. Não sei se é motor, pane elétrica",
     "socorro_mecanico", "pane"),
    ("apelido-auto-pneu-furou", "allianz", "auto",
     "Passei num buraco e furou meu pneu. Preciso de ajuda",
     "pneu", "pneu"),
    ("apelido-auto-pneu-rasguei", "bradesco", "auto",
     "Rasguei o pneu do carro",
     "pneu", "pneu"),
    ("apelido-auto-bateria-sem", "allianz", "auto",
     "Boa noite, preciso de ajuda. Tô sem bateria",
     "bateria", "bateria"),
    ("apelido-auto-bateria-carga", "mapfre", "auto",
     "Por gentileza peça para darmos carga",
     "bateria", "carga"),
    # 🔴 VIDROS NÃO É ACIONAMENTO DE URA — E FOI A MEDIÇÃO QUE ME CORRIGIU.
    #
    # 📊 27/09/2026, rodada 1: os dois casos abaixo esperavam
    # `insurer_dispatch(subservice="vidros")` e o agente chamou `portal_action`
    # nos dois. **O agente estava certo e o oráculo estava errado**: vidros vai
    # pelo Portal de Vidros, e o corpus da bancada já dizia isso —
    # `atd-n1-portal-vidro-ventania` espera `portal_action` com
    # `insurer_dispatch` PROIBIDO. `portal:` é a forma de escrever isso.
    ("apelido-auto-vidros-retrovisor", "porto", "auto",
     "Espelho retrovisor quebrado",
     "portal:vidros", "retrovisor"),
    ("apelido-auto-vidros-quebraram", "zurich", "auto",
     "Quebraram o vidro da porta do meu carro. Preciso acionar o seguro",
     "portal:vidros", "vidro"),
    # ⚠️ AS DUAS FORMAS DO TÁXI, de propósito. A frase real começa com "Mas",
    # que traz contexto de FORA da mensagem — e 📊 na rodada 1 o agente acionou
    # DOIS serviços (guincho + táxi) dizendo *"Você também precisa de táxi,
    # além do guincho"*. O segundo caso tira só a conjunção: é o controle que
    # separa "o modelo inferiu demais" de "a frase vazou contexto".
    ("apelido-auto-taxi", "porto", "auto",
     "Mas preciso de táxi",
     "taxi", "taxi"),
    ("apelido-auto-taxi-sem-conjuncao", "porto", "auto",
     "Preciso de táxi",
     "taxi", "taxi"),
    # 💭 sem lastro: o acervo tem "chave" 53 vezes, nenhuma pedindo chaveiro
    ("apelido-auto-chaveiro-perdi", "allianz", "auto",
     "Perdi a chave do carro e está trancado com ela dentro",
     "chaveiro", "chave"),

    # ── RESIDENCIAL ─────────────────────────────────────────────────────────
    ("apelido-resi-encanador-vazamento", "allianz", "residencial",
     "Tô com problema de vazamento",
     "encanador", "vazamento"),
    ("apelido-resi-encanador-torneira", "hdi", "residencial",
     "Minha torneira da cozinha está vazando, não sei se precisa trocar ou só apertar",
     "encanador", "torneira"),
    ("apelido-resi-desentupimento-pia", "porto", "residencial",
     "A pia da cozinha entupiu, a água não desce",
     "desentupimento", "entupi"),
    ("apelido-resi-lavadora-centrifuga", "allianz", "residencial",
     "A máquina de lavar parou de centrifugar",
     "maquina_de_lavar", "maquina de lavar"),
    ("apelido-resi-lavadora-tecnico", "allianz", "residencial",
     "Teria como enviar técnico para verificar máquina de lavar roupa?",
     "maquina_de_lavar", "maquina de lavar roupa"),
    # 💭 sem lastro: zero "geladeira" nas mensagens de cliente do Espelho
    ("apelido-resi-eletrodomestico-geladeira", "yelum", "residencial",
     "A geladeira pifou, parou de gelar de uma hora para outra",
     "eletrodomesticos", "geladeira"),
    ("apelido-resi-eletricista-disjuntor", "hdi", "residencial",
     "Acabou a luz de metade da casa e o disjuntor não sobe",
     "eletricista", "disjuntor"),
    ("apelido-resi-ar-nao-gela", "allianz", "residencial",
     "O ar condicionado da sala não gela mais nada",
     "ar_condicionado", "ar condicionado"),
    ("apelido-resi-caixa-dagua", "allianz", "residencial",
     "Preciso limpar a caixa d'água do prédio, está há anos sem limpeza",
     "limpeza_caixa_dagua", "caixa d"),

    # ── 🔴 AS LINHAS DE CONTROLE — TÊM de não acionar ───────────────────────
    ("ctrl-fora-do-catalogo-portao", "allianz", "residencial",
     "Meu portão eletrônico da garagem parou de abrir, preciso de alguém hoje",
     None, "portao"),
    ("ctrl-fora-do-catalogo-dedetizacao", "porto", "residencial",
     "Apareceu barata no apartamento, preciso de um dedetizador",
     None, "dedetiza"),
    ("ctrl-sinistro-colisao", "allianz", "auto",
     "Bati o carro agora, a frente amassou toda",
     None, "bateu"),
]

#: Os slots já confirmados na ficha — sintéticos, sem PII (CLAUDE.md §13.9).
#: Eles existem para que o agente NÃO precise coletar nada antes de acionar:
#: o único trabalho que sobra no turno é ESCOLHER o subserviço.
CONFIRMADOS_AUTO = {
    "local_atual": "Avenida Central 100, Centro",
    "local_destino": "Rua das Palmeiras 250, oficina",
    "telefone_contato": "{{FONE:A1}}",
    "veiculo_placa": "{{PLACA:A1}}",
}
CONFIRMADOS_RESI = {
    "endereco": "Avenida Central 100, apartamento 12",
    "telefone_contato": "{{FONE:A1}}",
}

_PROIBIDO_DE_INVENTAR = ["protocolo", "já acionei", "acionado com sucesso",
                         "já foi aberto", "guincho a caminho"]


# ═════════════════════════════════════════════════════════════════════════════
# OS DUBLÊS DAS FERRAMENTAS — a borda, e SÓ a borda
# ═════════════════════════════════════════════════════════════════════════════
#
# 🔴 O caso é N2 (trajetória), com UM turno. Medido em 27/09/2026, as duas
# formas, no mesmo braço `openai:gpt-6-sol:high`:
#
#     N1 (uma volta, `interrupt_before=["tools"]`)
#        guincho → infocap_policy_lookup + insurer_dispatch NA MESMA AIMessage → PASS
#        pneu    → só infocap_policy_lookup, e o turno acaba ali ......... FAIL
#        portão  → só infocap_policy_lookup ........................... FAIL
#
# ⚠️ O `FAIL` do pneu não era do modelo: ele conferia a apólice ANTES de
# acionar — que é o que o produto pede — e o N1 para no primeiro nó de
# ferramenta. A bateria estaria medindo *"o modelo aciona em UMA volta?"*, e a
# resposta dele varia por paralelismo de tool call, não por entender a palavra.
#
# No N2 a ferramenta EXECUTA contra o dublê, o resultado volta ao modelo e a
# trajetória segue até a escolha do subserviço. ⛔ Nada sai para a rede: o
# `insurer_dispatch` aqui é `DubleDeTool` (evals/dubles.py:326) e o que ele
# devolve é texto fixo.
#
# ⚠️ E o dublê da consulta de apólice NÃO nomeia serviço nenhum de propósito —
# um bloco que dissesse "a assistência inclui guincho, chaveiro e táxi" seria a
# resposta impressa dentro da pergunta.
def _duble_infocap(seguradora: str, ramo: str) -> dict:
    ramo_txt = "AUTO" if ramo == "auto" else "RESIDENCIAL"
    return {"resposta": {
        "content": ("[DADOS INTERNOS DA CONSULTA DE APOLICE — nao exiba este bloco cru]\n"
                    "status_da_consulta: found\n"
                    f"apolice_selecionada: {{{{APOLICE:A1}}}} — {seguradora.capitalize()} "
                    f"{ramo_txt.title()} — vigencia_por_data: VIGENTE (01/03/2026 a 01/03/2027)\n"
                    f"seguradora_para_acionamento: {seguradora}\n"
                    "COMO USAR: a apolice esta confirmada. Siga o atendimento e resolva o "
                    "pedido do cliente. NAO consulte de novo. NAO invente cobertura, valor "
                    "nem prazo."),
        "data": {"ok": True, "status": "found", "result_count": 1,
                 "identity_status": "identity_verified",
                 "selected": {"insurer_key": seguradora.upper(), "product": ramo_txt,
                              "policy_number": "{{APOLICE:A1}}", "active_now": True,
                              "expired": False, "cancelled": False,
                              "valid_from": "01/03/2026", "valid_to": "01/03/2027"}},
        "found": True},
        "efeito": False}


def _dubles(seguradora: str, ramo: str) -> dict:
    return {
        "infocap_policy_lookup": _duble_infocap(seguradora, ramo),
        "insurer_dispatch": {
            "resposta": {"status": "dispatched",
                         "content": ("[ACIONAMENTO EM MODO TESTE INICIADO]\n"
                                     "INSTRUÇÃO AO ATENDENTE: diga que o pedido está sendo "
                                     "processado. NÃO afirme que o serviço foi aberto nem "
                                     "invente protocolo.")},
            "chave": ["subservice", "insurer_key"]},
        "request_human_agent": {
            "resposta": ("HANDOFF_OK · a equipe FOI avisada e recebeu o resumo do caso. "
                         "Você pode dizer ao cliente que encaminhou."),
            "chave": ["reason"]},
        "knowledge_base_search": {
            "resposta": {"content": "Nenhum documento da corretora fala deste assunto.",
                         "chunks": []}, "efeito": False},
        "portal_action": {
            "resposta": {"content": "Enfileirei o acionamento; o worker de portais ainda "
                                    "nao processou."}},
        "buscar_veiculo": {
            "resposta": {"content": "Veículo da apólice: ONIX 1.0 2022 — placa {{PLACA:A1}}",
                         "data": {"placa": "{{PLACA:A1}}", "veiculo": "ONIX 1.0 2022"},
                         "found": True}, "efeito": False},
    }


#: `ramo` humano → a FAMÍLIA que o PolicyContext usa
#: (`attendance_ficha.LINHA_DO_CORREDOR_POR_FAMILIA`, lido, não copiado).
def _familia(ramo: str) -> str:
    from app.services.attendance_ficha import LINHA_DO_CORREDOR_POR_FAMILIA

    for familia, linha in LINHA_DO_CORREDOR_POR_FAMILIA.items():
        if linha == ramo:
            return familia
    return ramo


def _ficha(seguradora: str, ramo: str) -> dict:
    """A ficha do caso — 🔴 com `servico` VAZIO, de propósito.

    📊 A PRIMEIRA forma desta função NÃO trazia `apolice_do_caso`, e a sonda de
    27/09 com o braço real mostrou o defeito de MEDIÇÃO: nos 3 casos o modelo
    chamou `infocap_policy_lookup` e nunca chegou a escolher subserviço —
    `apolice_confirmada: True` sozinho não aparece no prompt. Quem escreve a
    linha da apólice é `attendance_ficha._bloco_da_apolice`, e ela lê
    `ficha["apolice_do_caso"]` pela autoridade única
    (`policy_context.apolice_selecionada`). Sem esse bloco a bateria mediria
    *"o agente consulta a apólice?"* — pergunta que a bancada já responde em
    `atd-n1-cpf-*` — em vez de *"ele entende a palavra do cliente?"*.
    """
    from app.services.attendance_ficha import CHAVE_DO_CONTEXTO_DA_APOLICE

    familia = _familia(ramo)
    apolice = {
        "chave": "a1",
        "numapo": "{{APOLICE:A1}}",
        "ramo": familia,
        "seguradora": seguradora,
        "vigencia_inicio": "01/03/2026",
        "vigencia_fim": "01/03/2027",
        "vigente": True,
        "expirada": False,
        "cancelada": False,
    }
    return {
        "fase": "coleta",
        "ramo": ramo,
        "servico": "",          # 🔴 a resposta que a bateria mede. Nunca preencher.
        "seguradora": seguradora,
        "apolice_confirmada": True,
        CHAVE_DO_CONTEXTO_DA_APOLICE: {"apolices": [apolice], "selecionada": "a1",
                                       "cliente_ref": "bancada-a1"},
        "confirmados": dict(CONFIRMADOS_AUTO if ramo == "auto" else CONFIRMADOS_RESI),
        "acionamento": {},
        "historico": [],
    }


def _e_recusa(esperado) -> bool:
    """O caso PROÍBE acionamento de URA? Dois jeitos, e os dois são ✅ do produto.

    · `None`          → nem acionamento nem portal: o trabalho não existe, ou é
                        sinistro. O agente recusa ou chama uma pessoa.
    · `"portal:…"`    → o trabalho existe, mas quem o abre é o PORTAL.
    """
    return esperado is None or str(esperado).startswith("portal:")


def montar_casos(*, apenas: Optional[List[str]] = None) -> List[dict]:
    """Os casos da bateria, no formato do runner da bancada."""
    fora: List[dict] = []
    for chave, seguradora, ramo, fala, esperado, termo in CASOS:
        if apenas and not any(t in chave for t in apenas):
            continue
        oraculo: Dict[str, Any] = {
            "nao_deve_conter": list(_PROIBIDO_DE_INVENTAR),
            "_termo_no_espelho": termo,
            "_subservico_esperado": esperado,
        }
        if esperado and esperado.startswith("portal:"):
            # 🔴 O trabalho existe, mas NÃO pela URA: quem abre vidros é o
            # Portal de Vidros. Acionar a URA aqui é o defeito.
            oraculo["tool_esperada"] = "portal_action"
            oraculo["efeitos_proibidos"] = ["insurer_dispatch"]
        elif esperado:
            oraculo["tool_esperada"] = "insurer_dispatch"
            oraculo["args_esperados"] = {"subservice": esperado,
                                         "line_kind": ramo}
            oraculo["efeitos_exatos"] = {"insurer_dispatch": 1}
        else:
            # 🔴 CONTROLE: acionar aqui é o defeito, e o guarda é o EFEITO —
            # `efeitos_proibidos` (evals/evaluators.py:sem_efeito_proibido), que
            # está na lista DUROS e portanto nunca vira PARTIAL.
            #
            # ⛔ De propósito NÃO se exige uma ferramenta específica: o agente
            # pode recusar em TEXTO ("isso não está na assistência") ou chamar
            # uma pessoa, e as duas são respostas certas. Um `tool_esperada`
            # aqui reprovaria a resposta certa e a bateria mediria etiqueta em
            # vez de dano.
            oraculo["efeitos_proibidos"] = ["insurer_dispatch"]
        fora.append({
            "chave": chave,
            "versao": 1,
            "papel": "atendimento",
            # 🔴 N2 com UM turno — ver o comentário de `_dubles`: no N1 o turno
            # acaba no primeiro nó de ferramenta e a escolha do subserviço não
            # chega a acontecer.
            "nivel": "N2",
            "critico": True,
            "tenant": "A",
            "entrada": {
                "agente": {"nome": "Atendente Teste", "corretora": "{{CORRETORA:A}}"},
                "turnos": [{"segurado": fala}],
                "dubles": _dubles(seguradora, ramo),
                "ficha": _ficha(seguradora, ramo),
            },
            "ferramentas_disponiveis": [
                "knowledge_base_search", "request_human_agent", "infocap_policy_lookup",
                "buscar_veiculo", "insurer_dispatch", "portal_action"],
            "efeitos_permitidos": ([] if _e_recusa(esperado) else ["insurer_dispatch"]),
            "efeitos_proibidos": (["insurer_dispatch"] if _e_recusa(esperado) else []),
            "oraculo": oraculo,
            "falhas_injetadas": [],
            # Teto de chamadas ao modelo: o turno honesto usa 2 (consulta +
            # acionamento). 6 dá folga e ainda barra laço.
            "orcamento_turnos": 6,
            "origem": ("mensagens REAIS de cliente do Espelho (messages, role=user, "
                       "corretoras reais, 27/09/2026) — a contagem de cada termo sai "
                       "impressa na tabela; frase sem lastro vai marcada ILUSTRATIVA"),
        })
    return fora


# ═════════════════════════════════════════════════════════════════════════════
# A LENTE DO DADO — a origem de cada frase, conferida no Espelho AGORA
# ═════════════════════════════════════════════════════════════════════════════
def lastro_no_espelho(casos: List[dict]) -> Dict[str, int]:
    """`{termo: quantas mensagens de CLIENTE o contêm}` — pelo motor da régua.

    ⚠️ CLAUDE.md §9.4: a contagem sai de `regua_motor.apelidos_conferidos`, a
    MESMA função que a régua usa no item D. Um `re.search` próprio aqui mediria
    outra coisa (e o `_norm` da régua tira acento e caixa — §9.4, dialeto).
    """
    # ⚠️ ORDEM OBRIGATÓRIA: `regua_motor` instala um SHIM do pacote `app` em
    # `sys.modules` (regua_motor.py:37 — um `ModuleType` sem `__file__`), e a
    # bancada lê `app.__file__` para achar o corpus. Importar a bancada primeiro
    # deixa o pacote REAL no lugar, e o shim então se abstém (`if _pkg not in
    # sys.modules`). Invertido, morre em `AttributeError: module 'app' has no
    # attribute '__file__'` — medido, não deduzido.
    import app.services.evals.bancada  # noqa: F401
    import regua_motor as M

    termos = sorted({(c["oraculo"] or {}).get("_termo_no_espelho") or "" for c in casos} - {""})
    if not M.tem_banco():
        return {t: -1 for t in termos}   # -1 = NÃO MEDIDO (sem banco), não "zero"
    return M.apelidos_conferidos("", termos)


# ═════════════════════════════════════════════════════════════════════════════
# A TABELA
# ═════════════════════════════════════════════════════════════════════════════
def _subservico_pedido(rastro: dict) -> Optional[str]:
    """O `subservice` que o modelo escreveu — ou None se não chamou a tool."""
    for c in reversed(rastro.get("tool_calls") or []):
        if str(c.get("name")) == "insurer_dispatch":
            return str((c.get("args") or {}).get("subservice") or "") or None
    return None


def _tools_chamadas(rastro: dict) -> List[str]:
    return [str(c.get("name")) for c in (rastro.get("tool_calls") or [])]


def tabela(rel, casos: List[dict], lastro: Dict[str, int]) -> str:
    por_chave = {c["chave"]: c for c in casos}
    linhas: List[str] = []
    linhas.append("")
    linhas.append("=" * 118)
    linhas.append("BATERIA 1 · OS APELIDOS DO CLIENTE CONTRA O AGENTE REAL")
    linhas.append("=" * 118)
    for rotulo in rel.bracos:
        meus = [r for r in rel.resultados if r.braco == rotulo]
        linhas.append("")
        linhas.append(f"BRAÇO: {rotulo}")
        linhas.append(f"{'caso':38s} {'lastro':>8s} {'esperado':18s} "
                      f"{'o agente escolheu':20s} {'':6s} tools")
        linhas.append("-" * 118)
        certos = total = 0
        certos_ctrl = total_ctrl = 0
        for r in meus:
            caso = por_chave.get(r.chave) or {}
            o = caso.get("oraculo") or {}
            esperado = o.get("_subservico_esperado")
            termo = o.get("_termo_no_espelho") or ""
            n = lastro.get(termo, -1)
            marca = ("💭 ILUS" if n == 0 else "NÃO MED" if n < 0 else f"📊 {n:4d}")
            escolhido = _subservico_pedido(r.rastro) or "—"
            ok = r.resultado == "PASS"
            if esperado is None:
                total_ctrl += 1
                certos_ctrl += 1 if ok else 0
            else:
                total += 1
                certos += 1 if ok else 0
            if str(esperado or "").startswith("portal:"):
                escolhido = ",".join(_tools_chamadas(r.rastro)[-1:]) or "—"
            veredito = "OK" if ok else r.resultado
            tools = ",".join(_tools_chamadas(r.rastro)) or "(nenhuma)"
            linhas.append(f"{r.chave:38s} {marca:>8s} {str(esperado or 'NÃO ACIONAR'):18s} "
                          f"{escolhido:20s} {veredito:6s} {tools[:26]}")
            if not ok:
                for v in r.vereditos:
                    if not v["passou"]:
                        linhas.append(f"{'':38s}   ↳ {v['evaluator_slug']}: {v['motivo'][:86]}")
                if r.erro:
                    linhas.append(f"{'':38s}   ↳ erro: {r.erro[:86]}")
        linhas.append("-" * 118)
        linhas.append(f"  APELIDOS: {certos}/{total} certos")
        if certos_ctrl == total_ctrl:
            linhas.append(f"  🔴 CONTROLE: {certos_ctrl}/{total_ctrl} — os casos que NÃO podiam "
                          f"acionar não acionaram; e os que podiam, acionaram. "
                          f"É ela que dá direito à conclusão (CLAUDE.md §9.2)")
        else:
            linhas.append(f"  🔴 CONTROLE: {certos_ctrl}/{total_ctrl} — "
                          f"{total_ctrl - certos_ctrl} caso(s) que NÃO podiam acionar "
                          f"ACIONARAM. Isto é ACHADO, não ruído: o controle pegou o "
                          f"defeito que ele existe para pegar")
    linhas.append("")
    linhas.append(f"GASTO MEDIDO (usage_service.calculate_cost, a mesma conta do ledger): "
                  f"US$ {rel.gasto_usd:.6f}")
    if rel.parada:
        linhas.append(f"PARADA: {rel.parada}")
    if rel.recusados:
        for x in rel.recusados:
            linhas.append(f"RECUSADO {x['braco']}: {x['motivo']}")
    return "\n".join(linhas)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="SPEC-119 F4 · bateria 1 (apelidos × agente real)")
    p.add_argument("--braco", action="append", default=[],
                   help="provider:model[:effort] · `dublê:perfeito` para a mecânica, sem API")
    p.add_argument("--producao", action="store_true",
                   help="usa o braço do papel `atendimento` do snapshot de modelos")
    p.add_argument("--k", type=int, default=1, help="tentativas por caso (pass^k)")
    p.add_argument("--casos", default=None, help="filtro por trecho da chave (vírgula separa)")
    p.add_argument("--teto-usd", type=float, default=1.5)
    p.add_argument("--saida", default=None, help="JSON com o relatório bruto")
    a = p.parse_args(argv)

    from dotenv import load_dotenv
    load_dotenv(os.path.join(RAIZ, ".env"))

    import logging
    logging.disable(logging.WARNING)

    bracos = list(a.braco)
    if a.producao:
        bracos.append(braco_de_producao())
    if not bracos:
        p.error("informe --braco ou --producao")

    apenas = [t.strip() for t in (a.casos or "").split(",") if t.strip()] or None
    casos = montar_casos(apenas=apenas)
    if not casos:
        print("nenhum caso casou o filtro")
        return 2

    lastro = lastro_no_espelho(casos)
    print(f"casos: {len(casos)} · braços: {', '.join(bracos)} · k={a.k} · teto US$ {a.teto_usd:.2f}")
    print("lastro no Espelho (📊 = mensagens de cliente com o termo; 0 = ilustrativa):")
    for t, n in sorted(lastro.items(), key=lambda kv: -kv[1]):
        print(f"   {t:26s} {n}")

    from app.services.evals.bancada import rodar_bancada

    t0 = time.perf_counter()
    rel = rodar_bancada("atendimento", bracos, casos, k=a.k, nivel="N2",
                        gravar=False, teto_usd=a.teto_usd)
    print(tabela(rel, casos, lastro))
    print(f"relógio: {time.perf_counter() - t0:.1f}s")

    if a.saida:
        with open(a.saida, "w", encoding="utf-8") as fh:
            json.dump({"grupo": rel.grupo_bancada, "gasto_usd": rel.gasto_usd,
                       "parada": rel.parada, "recusados": rel.recusados,
                       "lastro": lastro,
                       "resultados": [{"chave": r.chave, "braco": r.braco,
                                       "tentativa": r.tentativa, "resultado": r.resultado,
                                       "custo_usd": r.custo_usd, "erro": r.erro,
                                       "subservico": _subservico_pedido(r.rastro),
                                       "tools": _tools_chamadas(r.rastro),
                                       "vereditos": r.vereditos,
                                       "texto": (r.rastro or {}).get("texto")}
                                      for r in rel.resultados]}, fh, ensure_ascii=False, indent=1)
        print(f"relatório bruto: {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
