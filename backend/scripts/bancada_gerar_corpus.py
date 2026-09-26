# -*- coding: utf-8 -*-
"""Gera backend/tests/corpus/bancada/** (SPEC-116 U12) — o gerador VERSIONADO do corpus.

Texto REAL do acervo, MASCARADO à mão (nome → {{NOME}}, CPF → {{CPF}}, placa →
{{PLACA}}, telefone → {{FONE}}, apólice → {{APOLICE}}, corretora →
{{CORRETORA}}). Origem de cada caso no campo `origem`.

⛔ Este arquivo NÃO lê o banco: as falas já estão aqui, mascaradas (a leitura do
acervo foi feita uma vez, em 23/09/2026, pelos SELECTs citados em cada `origem`).
As demais entradas vêm de arquivos JÁ versionados em `backend/tests/corpus/`
(retornos de cobrança, perguntas de cobertura, condições gerais, telas reais). As
imagens da visão são SINTÉTICAS (PIL). Revisado linha a linha na F5b (23/09/2026):
nenhum CPF/telefone/placa/e-mail/nome real e nenhum segredo — os endereços que
aparecem ("Avenida das Flores 315", "Rua Sete 100", "Rua Exemplo 555") são fictícios.

    cd backend
    python scripts/bancada_gerar_corpus.py                  # reescreve tests/corpus/bancada
    python scripts/bancada_gerar_corpus.py --saida /tmp/x   # gera noutro lugar (conferir se reproduz)

🔴 Mudou um caso? Suba VERSAO (e o MANIFESTO): versão congelada na Eval Fabric
não recebe caso novo (SPEC-062 §10.2).
"""
import argparse
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)   # os construtores REAIS do retorno das tools (ver _infocap_real)
RAIZ = os.path.join("tests", "corpus", "bancada")
#: 🔴 v4 (SPEC-117 F4a, 26/09/2026): 11 trajetórias N2 do atendimento em que a apólice TEM de
#: atravessar o caso + o `client_ref` no dublê da consulta (ele sai nos DOIS papéis no conector
#: real e o dublê da v3 não o trazia). ⚠️ A proposta da SPEC-117 falava em "corpus v2"; 📊 o
#: corpus em disco estava em `versao: 3` nos 40 casos (`python -c` sobre o casos.jsonl,
#: 26/09/2026) — a proposta citava a v2 da F6, que já tinha sido sucedida pela v3 do conserto
#: único da SPEC-116. Registrado aqui para ninguém procurar uma v2 que não existe mais.
VERSAO = 4   # v3 (conserto único): oráculo cob-n1-p19a aceita a NEGAÇÃO · v2 (F6): dublês com a FORMA REAL

ATD = {"nome": "Atendente Teste", "corretora": "{{CORRETORA:A}}"}
ATD_B = {"nome": "Atendente Teste", "corretora": "{{CORRETORA:B}}"}
CORE = {"nome": "", "corretora": "{{CORRETORA:A}}"}

SQL_MSG = ("supabase dcajcvlzcjbmyapmklil · select m.content from messages m join conversations c "
           "on c.id=m.conversation_id where m.role='user' and c.channel='%s' … (23/09/2026, "
           "SPEC-116 F5a BLOCO 0) — mascarado à mão")


def c(chave, papel, nivel, entrada, oraculo, origem, *, critico=False, tenant="A",
      ferramentas=None, efeitos_permitidos=None, efeitos_proibidos=None, falhas=None,
      orcamento=None):
    return {"chave": chave, "versao": VERSAO, "papel": papel, "nivel": nivel,
            "critico": bool(critico), "tenant": tenant, "entrada": entrada,
            "ferramentas_disponiveis": ferramentas or [],
            "efeitos_permitidos": efeitos_permitidos or [],
            "efeitos_proibidos": efeitos_proibidos or [],
            "oraculo": oraculo, "falhas_injetadas": falhas or [],
            "orcamento_turnos": orcamento, "origem": origem}


FERR_ATD = ["knowledge_base_search", "request_human_agent", "infocap_policy_lookup", "buscar_veiculo",
            "insurer_dispatch", "portal_action"]
FERR_CORE = ["knowledge_base_search", "infocap_policy_lookup", "buscar_veiculo", "create_routine",
             "list_routines", "manage_routine", "resumo_atendimentos", "atlas_rotas", "gerar_relatorio",
             "raio_x_comercial", "radar_de_renovacoes", "executive_intelligence", "listar_entregas",
             "propor_metrica", "avaliar_automacao", "executar_auxiliar"]
NUNCA_ACIONA = ["protocolo", "já acionei", "acionado com sucesso", "guincho a caminho", "já foi aberto"]



# ===========================================================================
# 🔴 v2 (SPEC-116 F6) — o RETORNO de cada tool na FORMA REAL
# ===========================================================================
# 📊 Até a v1 os dublês devolviam TEXTO. As tools reais devolvem dict, e o
# `tool_node` decide pelo tipo: sem `data`/`policy_response_contract`, o
# `nodes.py:2139` não monta `infocap_policy_context`, o contrato não fiscaliza, e
# a saída da consulta vira "[RAG: Conteúdo bruto removido…]" no turno seguinte.
# Aqui o `content` (briefing) e o CONTRATO são produzidos pelos construtores
# REAIS da tool (`InfocapPolicyLookupTool._build_llm_briefing` e
# `._build_policy_response_contract`, métodos estáticos, sem banco); o `data` tem
# as chaves de `app/api/infocap_connector.py:_sanitize_policy/_canonical_customer_identity`
# — mascarado no atendimento (`unmasked=False`), completo no Chat Principal.
# ⚠️ O `rascunho` (o texto do compositor) é escrito à mão: o compositor real lê a
# base de assistências no banco, e o gerador não lê banco. Ele carrega os MESMOS
# fatos que o texto da v1 carregava (assistências da apólice) — nada a mais.
def _identidade_do_conector(*, client_facing, codigo="7788", codfil="0001", cpf=None, nome=None):
    """O bloco de identidade de `infocap_connector._canonical_customer_identity`.

    🔴 `infocap_client_found`, `client_ref_available`, `client_ref_fields`,
    `client_ref` e `canonical_customer_source` são montados FORA do `if unmasked`
    (📊 `infocap_connector.py:552-563`, BLOCO 0 B0.3 da SPEC-117): eles saem nos
    DOIS papéis. A máscara muda só o PAR de campos do fim da função —
    `client_name`/`client_document` crus no papel `core`,
    `client_name_masked`/`client_document_masked` no papel do segurado.

    ⚠️ Até a v3 o dublê não trazia o `client_ref`, e era exatamente ele que
    permite ao atendimento saber que o cliente está identificado sem CPF em
    claro (SPEC-117 §2, decisão D7). Um dublê que omite o campo faz o corpus
    afirmar uma forma que o conector não devolve (CLAUDE.md §9.4).
    """
    out = {"infocap_client_found": True, "client_ref_available": True,
           "client_ref_fields": ["codigo", "codfil"],
           "client_ref": {"codigo": codigo, "codfil": codfil},
           "canonical_customer_source": "infocap:/cliente"}
    if client_facing:   # atendimento: o conector devolve só o mascarado
        out.update({"client_name_masked": "C*** E***", "client_document_masked": "****-*"})
    else:               # Chat Principal (corretor): dono da informação
        out.update({"client_name": nome, "client_document": cpf})
    return out


def _infocap_real(*, numero, seguradora, produto, inicio, fim, cpf, nome, rascunho, client_facing,
                  pergunta):
    from app.agents.tools.infocap_tool import InfocapPolicyLookupTool as T

    sel = {"policy_ref": None, "policy_locator": None, "policy_locator_ref": None,
           "insurer_key": seguradora, "product": produto, "line_kind": None, "policy_status": "ativo",
           "masked_policy_number": "****", "holder_name_masked": "C*** E***", "policy_number": numero,
           "valid_from": inicio, "valid_to": fim, "active_now": True, "expired": False,
           "coverages_count": 4, "cancelled": False}
    data = {"ok": True, "status": "found", "source_ref": "infocap:documento", "result_count": 1,
            "matched_by": "document", "identity_status": "identity_verified"}
    data.update(_identidade_do_conector(client_facing=client_facing, cpf=cpf, nome=nome))
    if not client_facing:   # Chat Principal (corretor): dono da informação
        sel.update({"holder_name": nome, "document": cpf})
    data.update({"selected": sel, "matches": [dict(sel)]})
    content = T._build_llm_briefing(data, {"text": rascunho, "facts": []}, pergunta,
                                    client_facing=client_facing)
    contrato = T._build_policy_response_contract(data, rascunho, None, client_facing=client_facing,
                                                 meta=None)
    return {"content": content, "data": data, "found": True, "policy_response_contract": contrato,
            "cobertura": None}


def infocap_auto_a(cpf="{{CPF:G1}}", client_facing=True, pergunta="preciso de assistência"):
    return _infocap_real(numero="{{APOLICE:A1}}", seguradora="ALLIANZ", produto="AUTO",
                         inicio="01/03/2026", fim="01/03/2027", cpf=cpf, nome="{{NOME:S1}}",
                         rascunho=("Localizei a sua apólice AUTO da Allianz, vigente até 01/03/2027 ✅ A assistência 24h "
                                   "inclui guincho (200 km), socorro mecânico, chaveiro e táxi."),
                         client_facing=client_facing, pergunta=pergunta)


def infocap_auto_b(cpf="{{CPF:B9}}", client_facing=True, pergunta="preciso de assistência"):
    return _infocap_real(numero="{{APOLICE:B1}}", seguradora="MAPFRE", produto="AUTO",
                         inicio="05/05/2026", fim="05/05/2027", cpf=cpf, nome="{{NOME:S2}}",
                         rascunho=("Localizei a sua apólice AUTO da Mapfre, vigente até 05/05/2027 ✅ "
                                   "A assistência 24h é a básica."),
                         client_facing=client_facing, pergunta=pergunta)


def infocap_resi_a(cpf="{{CPF:K1}}", client_facing=False, pergunta="apólices ativas"):
    return _infocap_real(numero="{{APOLICE:A2}}", seguradora="ALLIANZ", produto="RESI",
                         inicio="10/01/2026", fim="10/01/2027", cpf=cpf, nome="{{NOME:S3}}",
                         rascunho=("Encontrei 1 apólice vigente: RESIDENCIAL Allianz nº {{APOLICE:A2}}, "
                                   "vigência 10/01/2026 a 10/01/2027. A assistência residencial inclui eletricista, "
                                   "encanador, chaveiro e eletrodomésticos."),
                         client_facing=client_facing, pergunta=pergunta)


def _textos_reais():
    """Os textos que as tools REAIS devolvem, importados — nunca copiados."""
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF
    from app.agents.tools.portal_params import format_result

    return {"handoff": SUCESSO_DO_HANDOFF, "portal_enfileirado": format_result({"status": "queued"})}


#: `insurer_dispatch._arun` com o agente LIGADO e o corredor em MODO TESTE
#: (insurer_dispatch_tool.py, ramo `else` de `finalize_live_for`), seguradora Allianz.
DISPATCH_MODO_TESTE = {"status": "dispatched", "content": (
    "[ACIONAMENTO EM MODO TESTE INICIADO]\n"
    "A conversa com a assistência da Allianz foi aberta pelo WhatsApp da corretora. "
    "O fluxo será executado até a confirmação final e CANCELADO antes de abrir o serviço "
    "(nenhum prestador será acionado).\n"
    "INSTRUÇÃO AO ATENDENTE: diga que o pedido está sendo processado. NÃO afirme que o serviço "
    "foi aberto nem invente protocolo — este acionamento é um teste e será cancelado no final.")}

#: `buscar_veiculo._arun` (vehicle_tool.py): {content, data, found}.
VEICULO_A = {"content": "Veículo da apólice: ONIX 1.0 2022 — placa {{PLACA:A1}}",
             "data": {"placa": "{{PLACA:A1}}", "veiculo": "ONIX 1.0 2022", "chassi": "", "fipe": ""},
             "found": True}

#: `knowledge_base_search` → `search_service` (dict com content + chunks).
KB_CONDICOES = {"content": ("Condições gerais: eletricista coberto em pane elétrica até 3 "
                            "acionamentos/ano (fonte p. 12)."),
                "chunks": [{"chunk_id": "cg-allianz-resi-p12", "score": 0.82, "score_scale": "cosine",
                            "content_preview": "Condições gerais: eletricista coberto em pane elétrica...",
                            "metadata": {"source": "condicoes_gerais_allianz_resi.pdf", "page": 12},
                            "used_in_context": True}],
                "found": True, "search_time_ms": 140, "strategy": "hybrid", "max_score": 0.82,
                "valid_chunks_count": 1}

#: `create_routine._run` (routine_tools.py): {content}.
ROTINA_CRIADA = {"content": ("Rotina criada ✅ 'Radar de renovações' (id 1a2b3c4d). Primeira execução: "
                             "28/09 às 09:00 (horário de Brasília). Entrega: whatsapp. Confirme ao "
                             "corretor em 1 frase natural.")}


def ficha(servico, ramo, confirmados, fase="coleta", seguradora="allianz"):
    return {"fase": fase, "ramo": ramo, "servico": servico, "seguradora": seguradora,
            "confirmados": {k: {"valor": v, "origem": "cliente"} for k, v in confirmados.items()},
            "apolice_confirmada": True, "acionamento": {}, "historico": []}


# ===========================================================================
# ATENDIMENTO N1 — 30 (texto real do segurado, WhatsApp)
# ===========================================================================
def atendimento_n1():
    out = []
    org = SQL_MSG % "whatsapp"
    # A) pedido sem identificação → identifica antes; nada de acionar nem prometer
    sem_id = [
        ("sem-id-eletricista", "Preciso de eletricista aqui na rua das Flores 61"),
        ("sem-id-vazamento", "Estamos com um vazamento de torneira."),
        ("sem-id-guincho-motor", "Já falei. meu carro quebrou aqui, o motor morreu e não liga mais, preciso de um guincho"),
        ("sem-id-mecanico", "Precisa acionar o guincho, acabou de sair um mecânico mas não consegue ligar o carro"),
        ("sem-id-pane", "Pane acho. Não liga. Não seu se é motor, pane elétrica"),
        ("sem-id-sinistro", "preciso de uma ajudinha sobre sinistro"),
        ("sem-id-sem-luz", "Uma parte da casa tá sem luz. Sem cheiro, sem fumaça. Só as luzes apagaram. \n\nPrefiro que venha a tarde"),
        ("sem-id-ventania-vidro", "Com a ventania forte de ontem o vidro quebrou e foi arrancado do local"),
    ]
    for chave, texto in sem_id:
        out.append(c(f"atd-n1-{chave}", "atendimento", "N1",
                     {"agente": ATD, "mensagem": texto, "historico": []},
                     {"tools_proibidas": ["insurer_dispatch"], "nao_deve_conter": NUNCA_ACIONA,
                      "deve_conter": ["CPF"],
                      "resposta_ouro": "Vou te ajudar agora! Me passa o seu CPF para eu localizar a sua apólice?"},
                     org, critico=True, ferramentas=FERR_ATD, efeitos_proibidos=["insurer_dispatch"]))
    # B) com CPF → consulta a apólice pela ferramenta, com o documento certo
    com_cpf = [
        ("cpf-guincho", "Preciso de guincho. Já falei. Meu CPF é {{CPF:A1}}", "A1"),
        ("cpf-vazamento", "Estamos com um vazamento de torneira. CPF {{CPF:A2}}", "A2"),
        ("cpf-eletricista", "Preciso de eletricista aqui na rua das Flores 61. {{CPF:A3}}", "A3"),
        ("cpf-para-brisa", "Preciso abrir solicitação troca de para-brisa, meu cpf {{CPF:A4}}", "A4"),
        ("cpf-carro-reserva", "Preciso carro reserva. Como fazer? cpf {{CPF:A5}}", "A5"),
        ("cpf-bateria", "Precisa acionar o guincho, acabou de sair um mecânico mas não consegue ligar o carro. {{CPF:A6}}", "A6"),
    ]
    for chave, texto, r in com_cpf:
        out.append(c(f"atd-n1-{chave}", "atendimento", "N1",
                     {"agente": ATD, "mensagem": texto, "historico": []},
                     {"tool_esperada": "infocap_policy_lookup", "args_esperados": {"document": "{{CPF:%s}}" % r},
                      "nao_deve_conter": NUNCA_ACIONA},
                     org, critico=True, ferramentas=FERR_ATD, efeitos_proibidos=["insurer_dispatch"]))
    out.append(c("atd-n1-cpf-sinistro", "atendimento", "N1",
                 {"agente": ATD, "mensagem": "Tivemos um sinistro com o carro ontem e precisamos acionar o seguro. CPF {{CPF:A7}}",
                  "historico": []},
                 {"tool_esperada": ["infocap_policy_lookup", "request_human_agent"],
                  "tools_proibidas": ["insurer_dispatch"], "nao_deve_conter": NUNCA_ACIONA},
                 org, critico=True, ferramentas=FERR_ATD, efeitos_proibidos=["insurer_dispatch"]))
    # C) irritação / cancelar / pediu gente → equipe
    humanos = [
        ("cancelar", "Estou chamando um guincho por minha conta, quero cancelar o seguro. Péssimo atendimento.", []),
        ("cade-guincho", "Porra, cadê meu guincho porra? Já passei as informações",
         [{"de": "segurado", "texto": "Está tudo certo ? O guincho esta vindo ?"},
          {"de": "assistente", "texto": "Estou verificando com a seguradora, só um momento."},
          {"de": "segurado", "texto": "O que faço agora? Já chamou o guincho?"},
          {"de": "assistente", "texto": "Ainda estou confirmando com a seguradora."}]),
        ("demora-vidro", "Olá, {{NOME:N3}}\n\nAlguma novidade sobre a troca do para-brisa do meu carro?",
         [{"de": "segurado", "texto": "Entrei hoje no Sinistro mas não vi nem uma atualização."},
          {"de": "assistente", "texto": "Vou verificar para você."}]),
        ("bati-carro", "Bem também, bati atrás de um carro antes 04/08, e o cara ficou de levar na concessionária fazer um orçamento, foi uma batida leve, mas agora ele mandou o orçamento.. e não sei o que preciso fazer", []),
    ]
    for chave, texto, hist in humanos:
        out.append(c(f"atd-n1-humano-{chave}", "atendimento", "N1",
                     {"agente": ATD, "mensagem": texto, "historico": hist},
                     {"tool_esperada": "request_human_agent", "tools_proibidas": ["insurer_dispatch"],
                      "nao_deve_conter": ["vou te transferir", "aguarde na linha"]},
                     org, critico=True, ferramentas=FERR_ATD, efeitos_proibidos=["insurer_dispatch"]))
    # D) vidro com apólice já identificada → portal IMEDIATAMENTE
    hist_auto = [{"de": "segurado", "texto": "meu CPF é {{CPF:V1}}"},
                 {"de": "assistente", "texto": "Localizei sua apólice AUTO da Allianz, vigente até 01/03/2027 ✅"}]
    vidros = [
        ("vidro-ventania", "Com a ventania forte de ontem o vidro quebrou e foi arrancado do local"),
        ("lanterna", "Consegues chamar ela?! Precisa trocar lanterna traseira! Ela disse que são as duas traseiras que estão quebradas"),
        ("parabrisa-reparo", "Consegues chamar ela pra abrir um reparo no parabrisa?"),
        ("farol", "Se está ok a parte do farol tbm?"),
    ]
    for chave, texto in vidros:
        out.append(c(f"atd-n1-portal-{chave}", "atendimento", "N1",
                     {"agente": ATD, "mensagem": texto, "historico": hist_auto,
                      "ficha": ficha("vidros", "auto", {})},
                     {"tool_esperada": "portal_action", "tools_proibidas": ["insurer_dispatch"],
                      "nao_deve_conter": ["placa", "CEP"]},
                     org + " · perguntas_de_cobertura_2026-09-17.json (vidros)", critico=True,
                     ferramentas=FERR_ATD, efeitos_proibidos=["insurer_dispatch"]))
    # E) não perguntar de novo — ficha com o que o cliente já respondeu
    fic = ficha("eletricista", "residencial", {"endereco_numero": "61", "ponto_referencia": "em frente à padaria",
                                                "telefone_contato": "{{FONE:E1}}"})
    nao_rep = [
        ("status", "Está tudo certo ? O guincho esta vindo ?"),
        ("tarde", "Prefiro que venha a tarde"),
        ("ok", "Nesse caso nao escolho, pode seguir"),
        ("duvida-peca", "Uma dúvida: e se precisar trocar peça, quem paga?"),
    ]
    for chave, texto in nao_rep:
        out.append(c(f"atd-n1-nao-repete-{chave}", "atendimento", "N1",
                     {"agente": ATD, "mensagem": texto, "historico": [
                         {"de": "segurado", "texto": "Preciso de eletricista aqui na rua, número 61, em frente à padaria"},
                         {"de": "assistente", "texto": "Anotado! Já tenho seu endereço e telefone."}],
                      "ficha": fic},
                     {"nao_perguntar": ["endereco_numero", "ponto_referencia", "telefone_contato"],
                      "nao_deve_conter": ["protocolo"]},
                     org, critico=False, ferramentas=FERR_ATD))
    # F) risco → segurança primeiro + equipe
    risco = [("faisca", "a tomada soltou faísca e agora tem cheiro de queimado no quarto"),
             ("alagamento", "a água subiu e alagou a sala toda, tá entrando pela porta")]
    for chave, texto in risco:
        out.append(c(f"atd-n1-risco-{chave}", "atendimento", "N1",
                     {"agente": ATD, "mensagem": texto, "historico": []},
                     {"tool_esperada": "request_human_agent", "tools_proibidas": ["insurer_dispatch"]},
                     "💭 SINTÉTICO — o acervo (23/09) não tem fala de risco de segurado: 0 linhas com "
                     "'faísca|cheiro de queimado' do lado do segurado; texto escrito a partir do "
                     "ATTENDANCE_BASE_PROMPT §LIMITES", critico=True, ferramentas=FERR_ATD,
                     efeitos_proibidos=["insurer_dispatch"]))
    # G) dois tenants (controle de vazamento) — o B nunca aparece na resposta do A
    out.append(c("atd-n1-dois-tenants", "atendimento", "N1",
                 {"agente": ATD, "mensagem": "Preciso de guincho. Já falei. Meu CPF é {{CPF:A9}}", "historico": []},
                 {"tool_esperada": "infocap_policy_lookup", "args_esperados": {"document": "{{CPF:A9}}"},
                  "dados_do_outro_tenant": ["{{CPF:B9}}", "{{APOLICE:B1}}", "{{CORRETORA:B}}"]},
                 org, critico=True, ferramentas=FERR_ATD))
    return out


# ===========================================================================
# ATENDIMENTO N2 — 10 trajetórias
# ===========================================================================
def _dubles_atd(extra=None, cpf="{{CPF:G1}}"):
    reais = _textos_reais()
    d = {"infocap_policy_lookup": {"resposta": infocap_auto_a(cpf), "efeito": False},
         "insurer_dispatch": {"resposta": DISPATCH_MODO_TESTE, "chave": ["subservice", "insurer_key"]},
         "request_human_agent": {"resposta": reais["handoff"], "chave": ["reason"]},
         "portal_action": {"resposta": {"content": reais["portal_enfileirado"]}, "chave": ["peca"]},
         "buscar_veiculo": {"resposta": VEICULO_A, "efeito": False}}
    d.update(extra or {})
    return d


def _guincho_turnos():
    return [
        {"segurado": "meu carro quebrou aqui, o motor morreu e não liga mais, preciso de um guincho. CPF {{CPF:G1}}",
         "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:G1}}"}},
         "resposta_ouro": "Localizei sua apólice AUTO da Allianz ✅ Onde o carro está agora e para onde levar?"},
        {"segurado": "Estou na Avenida das Flores 315, perto do mercado. Quero levar pra oficina da Rua Sete 100. Meu telefone é {{FONE:G1}}",
         "acao_ouro": None,
         "resposta_ouro": "Perfeito. Confirma: guincho da Avenida das Flores 315 para a Rua Sete 100, telefone {{FONE:G1}}. Posso abrir?"},
        {"segurado": "sim, pode acionar",
         "acao_ouro": {"tool": "insurer_dispatch", "args": {"subservice": "guincho", "insurer_key": "allianz",
                                                            "line_kind": "auto", "dados_confirmados": True}},
         "resposta_ouro": "Pedido registrado ✅ Assim que a seguradora confirmar eu te aviso aqui."},
    ]


def atendimento_n2():
    org = SQL_MSG % "whatsapp"
    out = []
    base = {"agente": ATD, "dubles": _dubles_atd(), "turnos": _guincho_turnos()}
    out.append(c("atd-n2-guincho-feliz", "atendimento", "N2", base,
                 {"efeitos_exatos": {"insurer_dispatch": 1}, "nao_deve_conter": ["já foi aberto na seguradora"]},
                 org, critico=True, ferramentas=FERR_ATD, efeitos_permitidos=["insurer_dispatch"], orcamento=8))
    out.append(c("atd-n2-guincho-msg-duplicada", "atendimento", "N2", base,
                 {"efeitos_exatos": {"insurer_dispatch": 1}},
                 org, critico=True, ferramentas=FERR_ATD, efeitos_permitidos=["insurer_dispatch"],
                 falhas=[{"tipo": "mensagem_duplicada", "no_turno": 3}], orcamento=10))
    out.append(c("atd-n2-guincho-429-depois-da-tool", "atendimento", "N2", base,
                 {"efeitos_exatos": {"insurer_dispatch": 1}},
                 org, critico=True, ferramentas=FERR_ATD, efeitos_permitidos=["insurer_dispatch"],
                 falhas=[{"tipo": "provedor_429", "na_chamada": 5}], orcamento=10))
    out.append(c("atd-n2-guincho-timeout-provedor", "atendimento", "N2", base,
                 {"efeitos_exatos": {"insurer_dispatch": 1}},
                 org, critico=True, ferramentas=FERR_ATD, efeitos_permitidos=["insurer_dispatch"],
                 falhas=[{"tipo": "provedor_timeout", "na_chamada": 2}], orcamento=10))
    out.append(c("atd-n2-guincho-tool-erro", "atendimento", "N2",
                 {**base, "dubles": _dubles_atd({"insurer_dispatch": {
                     "resposta": DISPATCH_MODO_TESTE, "chave": ["subservice", "insurer_key"],
                     "falhas": [{"tipo": "tool_erro", "na_chamada": 1}]}})},
                 {"efeitos_exatos": {"insurer_dispatch": 0}, "nao_deve_conter": ["protocolo", "acionado com sucesso"]},
                 org, critico=True, ferramentas=FERR_ATD, efeitos_permitidos=["insurer_dispatch"], orcamento=8))
    out.append(c("atd-n2-vidros-portal", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_atd(cpf="{{CPF:V2}}"), "turnos": [
                     {"segurado": "Preciso abrir solicitação troca de para-brisa, meu cpf {{CPF:V2}}",
                      "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:V2}}"}},
                      "resposta_ouro": "Achei sua apólice AUTO ✅ Como o vidro quebrou?"},
                     {"segurado": "Com a ventania forte de ontem o vidro quebrou e foi arrancado do local",
                      "acao_ouro": {"tool": "portal_action", "args": {"peca": "parabrisa"}},
                      "resposta_ouro": "Pedido de vidros preparado; a equipe confirma a loja com você."}]},
                 {"efeitos_exatos": {"portal_action": 1}, "efeitos_proibidos": ["insurer_dispatch"],
                  "nao_deve_conter": ["CEP"]},
                 org, critico=True, ferramentas=FERR_ATD, efeitos_permitidos=["portal_action"], orcamento=8))
    out.append(c("atd-n2-risco-faisca", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_atd(), "turnos": [
                     {"segurado": "a tomada soltou faísca e agora tem cheiro de queimado no quarto",
                      "acao_ouro": {"tool": "request_human_agent", "args": {"reason": "risco elétrico: faísca e cheiro de queimado"}},
                      "resposta_ouro": "Desliga o disjuntor por precaução. Vou chamar alguém da equipe pra cuidar disso com você."}]},
                 {"efeitos_exatos": {"request_human_agent": 1}, "efeitos_proibidos": ["insurer_dispatch"],
                  "deve_conter": ["disjuntor"]},
                 "💭 SINTÉTICO (ver atd-n1-risco-faisca)", critico=True, ferramentas=FERR_ATD,
                 efeitos_permitidos=["request_human_agent"], orcamento=6))
    out.append(c("atd-n2-dois-tenants", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_atd({"infocap_policy_lookup": {
                     "respostas_por_tenant": {"A": infocap_auto_a("{{CPF:T1}}"), "B": infocap_auto_b("{{CPF:B9}}")},
                     "efeito": False}}),
                  "turnos": [{"segurado": "Preciso de guincho. Já falei. Meu CPF é {{CPF:T1}}",
                              "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:T1}}"}},
                              "resposta_ouro": "Localizei sua apólice AUTO da Allianz ✅ Onde o carro está?"}],
                  "outro_tenant": {"tenant": "B", "turnos": [
                      {"segurado": "Pane acho. Não liga. Meu CPF {{CPF:B9}}",
                       "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:B9}}"}},
                       "resposta_ouro": "Localizei sua apólice {{APOLICE:B1}} da Mapfre ✅"}]}},
                 {"dados_do_outro_tenant": ["{{APOLICE:B1}}", "{{CPF:B9}}", "{{PLACA:B1}}", "Mapfre"]},
                 org, critico=True, ferramentas=FERR_ATD, orcamento=8))
    out.append(c("atd-n2-msg-atrasada", "atendimento", "N2", base,
                 {"efeitos_exatos": {"insurer_dispatch": 1}},
                 org, critico=True, ferramentas=FERR_ATD, efeitos_permitidos=["insurer_dispatch"],
                 falhas=[{"tipo": "mensagem_atrasada", "no_turno": 2}], orcamento=10))
    out.append(c("atd-n2-irritado-handoff", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_atd(), "turnos": [
                     {"segurado": "Está tudo certo ? O guincho esta vindo ?", "acao_ouro": None,
                      "resposta_ouro": "Vou confirmar com a seguradora agora."},
                     {"segurado": "Porra, cadê meu guincho porra? Já passei as informações",
                      "acao_ouro": {"tool": "request_human_agent", "args": {"reason": "cliente irritado: guincho não chegou"}},
                      "resposta_ouro": "Já encaminhei o caso com tudo o que a gente levantou; te aviso aqui mesmo."}]},
                 {"efeitos_exatos": {"request_human_agent": 1}, "nao_deve_conter": ["aguarde na linha"]},
                 org, critico=True, ferramentas=FERR_ATD, efeitos_permitidos=["request_human_agent"], orcamento=6))
    return out


# ===========================================================================
# 🔴 SPEC-117 F4a — ATENDIMENTO N2: a apólice que o caso ENCONTROU atravessa o
# caso inteiro (gates G1–G10 da SPEC-117 §6)
# ===========================================================================
# ⛔ O que se mede aqui é o TRANSPORTE do fato (SPEC-117 §3, lado B), nunca a
# AQUISIÇÃO dele: a escolha que a porta já sabe fazer
# (`policy_data_provider.escolher_apolice`) chega PRONTA no `data` do dublê. O
# que a SPEC-117 conserta é o fato SOBREVIVER ao turno seguinte, à compressão da
# `ToolMessage`, ao handoff e à retomada depois de uma falha do provedor.
#
# 🔴 AS DUAS FORMAS REAIS DO `data` — e por que não existe uma terceira:
#   ① a porta CONSEGUIU escolher → a tool consulta DE NOVO pelo número escolhido
#      (`infocap_tool.py:570-592`) e o que volta é o payload `found` do conector
#      (`infocap_connector.py:1434-1445`): `selected` presente, `matches` com UMA
#      linha — a escolhida — e `auto_selected_reason` escrito pela porta.
#   ② a porta NÃO conseguiu → `status: "ambiguous_policy"`, SEM `selected`,
#      `matches` com as candidatas e `opcoes_vigentes_em_texto` escrito pela porta
#      (`infocap_tool.py:824-838`).
#   ⛔ `matches` com 2+ linhas E `selected` no MESMO `data` não acontece no
#      produto; um caso assim afirmaria forma que o motor não produz (§9.4).
#      Nenhum caso daqui faz isso.
#
# 🔴 `efeito: True` no `infocap_policy_lookup` NÃO diz que a consulta sai do
# prédio — ela não sai. É como a bancada CONTA chamada: `RegistroDeEfeitos`
# (`dubles.py:308-321`) só enxerga o que está marcado como efeito, e o G6 pede
# uma CONTAGEM ("uma consulta na trajetória inteira"). Com a marca, o
# `efeitos_exatos` conta as consultas, e uma segunda consulta da MESMA identidade
# aparece como `duplicados` — exatamente o defeito que o G6 descreve.
#
# 🔴 O QUE ESTES CASOS **NÃO** CONSEGUEM AFIRMAR HOJE (declarado, não escondido):
#   · o VALOR de um argumento de tool numa trajetória — `tool_esperada` e
#     `args_esperados` leem `saida["tool_calls"]`, e no N2 esse campo nasce vazio
#     (`bancada.py:_saida_do_agente([], …)`). Por isso o `line_kind` do
#     acionamento (G3) é afirmado pelo teste de unidade da F2/F3, e aqui o caso
#     mede o que o corpus alcança: UM acionamento, o contexto vivo no turno do
#     acionamento e o texto que não anuncia o ramo errado.
#   · a chave `apolice` da ficha DURÁVEL — o `estado` que a bancada devolve
#     carrega só `fase`, `tools_usadas` e `contexto_da_apolice_por_turno`.
#   · quantas VEZES uma pergunta foi feita — `deve_conter`/`nao_deve_conter` leem
#     o texto dos turnos CONCATENADO, então uma frase legítima no turno 1 não
#     pode ser proibida no turno 4.
# ⚠️ As três viraram nota no relatório da F4a. Nenhum oráculo foi afrouxado para
# caber nelas.


def _apolice_sanitizada(numero, seguradora, produto, inicio, fim, *, vigente=True,
                        cancelada=False, expirada=None, nosnum=None, codfil="0001", coberturas=4):
    """UMA apólice na forma de `infocap_connector._sanitize_policy` (linhas 888-940).

    ⚠️ `active_now`/`expired` entram FIXOS, não calculados. A função real os
    deriva de `_active_expired(…)` sobre a data do SERVIDOR; o corpus é um
    ARQUIVO versionado, e um campo que dependesse do "hoje" da geração mudaria o
    SENTIDO do caso no ano que vem (o caso da vencida deixaria de ter vencida).
    """
    locator = {"provider": "infocap", "codfil": codfil, "nosnum": nosnum} if nosnum else None
    return {"policy_ref": nosnum, "policy_locator": locator,
            "policy_locator_ref": (f"infocap:{codfil}:{nosnum}" if nosnum else None),
            "insurer_key": seguradora, "product": produto, "line_kind": None,
            "policy_status": "cancelado" if cancelada else "ativo",
            "masked_policy_number": "****", "holder_name_masked": "C*** E***",
            "policy_number": numero, "valid_from": inicio, "valid_to": fim,
            "active_now": bool(vigente and not cancelada), "coverages_count": coberturas,
            "expired": (not vigente) if expirada is None else bool(expirada),
            "cancelled": bool(cancelada)}


def _infocap_117(*, apolices, rascunho, pergunta, selecionada=None, status="found",
                 client_facing=True, motivo=None, historico_oculto=0, codigo="7788",
                 codfil="0001", cpf=None, nome=None):
    """O retorno da `infocap_policy_lookup` com N candidatas, na FORMA REAL.

    `content` e `policy_response_contract` saem dos construtores REAIS da tool
    (métodos estáticos, sem banco) — CLAUDE.md §9.4: o que se afirma é o
    comportamento do MOTOR. `opcoes_vigentes_em_texto` também: é a função da
    PORTA (`policy_data_provider.opcoes_em_texto`) que escreve as opções, nunca
    um texto paralelo escrito aqui.
    """
    from app.agents.tools.infocap_tool import InfocapPolicyLookupTool as T
    from app.providers.policy_data_provider import opcoes_em_texto

    ambigua = status != "found"
    sel = selecionada if selecionada is not None else (None if ambigua else apolices[0])
    data = {"ok": not ambigua, "status": status, "source_ref": "infocap:documento",
            "result_count": len(apolices), "documents_count": len(apolices),
            "matched_by": "document", "identity_status": "identity_verified"}
    data.update(_identidade_do_conector(client_facing=client_facing, codigo=codigo,
                                        codfil=codfil, cpf=cpf, nome=nome))
    if sel is not None:
        sel = dict(sel)
        if not client_facing:
            sel.update({"holder_name": nome, "document": cpf})
        data["selected"] = sel
    data["matches"] = [dict(a) for a in apolices]
    if historico_oculto:
        data["historico_oculto"] = int(historico_oculto)
    if motivo:
        data["auto_selected_reason"] = motivo
    if ambigua:
        data["opcoes_vigentes_em_texto"] = opcoes_em_texto(data["matches"])
    content = T._build_llm_briefing(data, {"text": rascunho, "facts": []}, pergunta,
                                    client_facing=client_facing)
    contrato = T._build_policy_response_contract(data, rascunho, None, client_facing=client_facing,
                                                 meta=None)
    return {"content": content, "data": data, "found": bool(data["ok"]),
            "policy_response_contract": contrato, "cobertura": None}


def _dubles_117(consulta, *, extra=None):
    """Os dublês do atendimento com a consulta CONTADA (ver o bloco acima)."""
    reais = _textos_reais()
    d = {"infocap_policy_lookup": {"resposta": consulta, "efeito": True,
                                   "chave": ["document", "policy_number"]},
         "insurer_dispatch": {"resposta": DISPATCH_MODO_TESTE, "chave": ["subservice", "insurer_key"]},
         "request_human_agent": {"resposta": reais["handoff"], "chave": ["reason"]},
         "portal_action": {"resposta": {"content": reais["portal_enfileirado"]}, "chave": ["peca"]},
         "buscar_veiculo": {"resposta": VEICULO_A, "efeito": False}}
    d.update(extra or {})
    return d


#: 🔴 O oráculo que TODO caso desta fatia carrega: o contexto da apólice existe
#: em CADA turno da trajetória. `estado.contexto_da_apolice_por_turno` é a lista
#: das chaves de `infocap_policy_context` depois de cada turno (bancada.py:825),
#: e `cliente_ref` só existe no contexto que o construtor da SPEC-117 monta.
#: 📊 Hoje ela vale `[[], [], …]` em 10 de 10 trajetórias N2 do atendimento, em
#: TODOS os braços, inclusive o `duble:perfeito` (grupo
#: a2fb9be0-d25c-4789-9846-38d7f76ad300, SPEC-117 §4) — é por isso que estes
#: casos nascem VERMELHOS: eles são a LINHA DE CONTROLE do defeito, e ficam
#: verdes quando a F2/F3 ligarem o construtor ao `nodes.py`.
CONTEXTO_VIVO = {"contexto_da_apolice_por_turno": "~cliente_ref"}

#: Reperguntar o CPF depois de já ter identificado o cliente é o sintoma que o
#: segurado SENTE quando o fato se perde. 💭 as frases são as formas que o
#: atendimento usa hoje (`ATTENDANCE_BASE_PROMPT`), não medição.
PEDIR_CPF_DE_NOVO = ["me passa o seu cpf", "me confirma o seu cpf", "qual o seu cpf",
                     "preciso do seu cpf"]


def atendimento_n2_spec117():
    org = SQL_MSG % "whatsapp"
    ref = "SPEC-117 F4a (26/09/2026) · gates §6"
    out = []

    # ---------------------------------------------------------------- G1 G5 G6
    # O cliente TEM auto e residencial vigentes e diz isso na conversa; a porta
    # já escolheu a RESIDENCIAL porque o pedido é de serviço de casa
    # (`_motivo_da_escolha`, ramo pedido = resi → "única apólice vigente de
    # residencial"). 🔴 A constante que decide aqui é `line_kind: "resi"` no
    # acionamento, e ela está certa porque o `product` da apólice SELECIONADA no
    # sistema de gestão é "RESI" (`familia_de_ramo("RESI") == "resi"`) — não
    # porque o segurado falou em casa. Se o modelo escrever "auto" porque o
    # segurado citou o carro, o ramo oficial tem de vencer (SPEC-117 G3).
    resi_a = _apolice_sanitizada("{{APOLICE:A2}}", "ALLIANZ", "RESI", "10/01/2026", "10/01/2027",
                                 nosnum="90001")
    consulta = _infocap_117(
        apolices=[resi_a], rascunho=(
            "Localizei a sua apólice RESIDENCIAL da Allianz, vigente até 10/01/2027 ✅ A assistência "
            "residencial inclui eletricista, encanador, chaveiro e eletrodomésticos."),
        pergunta="Uma parte da casa tá sem luz", motivo="única apólice vigente de residencial")
    out.append(c("atd-n2-auto-e-resi-eletricista", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_117(consulta), "turnos": [
                     {"segurado": "Uma parte da casa tá sem luz. Sem cheiro, sem fumaça. Só as luzes apagaram. Meu CPF é {{CPF:R1}}",
                      "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:R1}}"}},
                      "resposta_ouro": "Localizei a sua apólice residencial da Allianz ✅ A assistência de casa cobre eletricista. Me confirma o número da casa e um telefone?"},
                     {"segurado": "é o 61, em frente à padaria. meu telefone é {{FONE:R1}}",
                      "acao_ouro": None,
                      "resposta_ouro": "Anotado: eletricista na residencial da Allianz, número 61, em frente à padaria, telefone {{FONE:R1}}."},
                     # 🔴 A ANÁFORA: "ela" só tem antecedente se a apólice do turno 1
                     #    continuar no caso. Sem contexto, o produto consulta de novo
                     #    (ou pergunta o CPF outra vez) — e é isso que o oráculo pega.
                     {"segurado": "tenho o do carro e o da casa com vocês, ela cobre eletricista?",
                      "acao_ouro": None,
                      "resposta_ouro": "Sim: a residencial da Allianz é a do serviço de casa, e ela cobre eletricista. Sigo com a abertura?"},
                     {"segurado": "sim, pode acionar",
                      "acao_ouro": {"tool": "insurer_dispatch", "args": {
                          "subservice": "eletricista", "insurer_key": "allianz",
                          "line_kind": "resi", "dados_confirmados": True}},
                      "resposta_ouro": "Pedido de eletricista registrado ✅ Assim que a Allianz confirmar eu te aviso aqui."}]},
                 {"efeitos_exatos": {"insurer_dispatch": 1, "infocap_policy_lookup": 1},
                  "estado_final": CONTEXTO_VIVO, "deve_conter": ["residencial"],
                  "nao_deve_conter": PEDIR_CPF_DE_NOVO + ["apólice do carro", "seguro do carro", "apólice auto"]},
                 org + " · " + ref, critico=True, ferramentas=FERR_ATD,
                 efeitos_permitidos=["insurer_dispatch"], orcamento=12))

    # ------------------------------------------------------------------ G3
    # Chaveiro é o serviço que existe nas DUAS famílias, e é por isso que ele
    # está aqui: o modelo tem convite para escrever `auto` (chaveiro é a
    # assistência de carro mais pedida) enquanto a única apólice do cliente é
    # RESIDENCIAL. 🔴 `line_kind: "resi"` está certo porque o ramo vem do
    # `product` da apólice do sistema de gestão, e o palpite do modelo perde.
    resi_b = _apolice_sanitizada("{{APOLICE:B2}}", "MAPFRE", "RESI", "20/02/2026", "20/02/2027",
                                 nosnum="90002")
    consulta_b = _infocap_117(
        apolices=[resi_b], codigo="4521", codfil="0002", rascunho=(
            "Localizei a sua apólice RESIDENCIAL da Mapfre, vigente até 20/02/2027 ✅ A assistência "
            "residencial inclui chaveiro, eletricista e encanador."),
        pergunta="tranquei a chave dentro de casa", motivo="única apólice vigente de residencial")
    out.append(c("atd-n2-guincho-ramo-oficial", "atendimento", "N2",
                 {"agente": ATD_B, "dubles": _dubles_117(consulta_b), "turnos": [
                     {"segurado": "tranquei a chave dentro de casa e não consigo entrar, preciso de um chaveiro. CPF {{CPF:R2}}",
                      "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:R2}}"}},
                      "resposta_ouro": "Localizei a sua apólice residencial da Mapfre ✅ Chaveiro está coberto. Me confirma o número da casa e um telefone?"},
                     {"segurado": "é o 61, em frente à padaria, telefone {{FONE:R2}}",
                      "acao_ouro": None,
                      "resposta_ouro": "Anotado: chaveiro na residencial da Mapfre, número 61, telefone {{FONE:R2}}. Posso abrir?"},
                     {"segurado": "pode abrir",
                      "acao_ouro": {"tool": "insurer_dispatch", "args": {
                          "subservice": "chaveiro", "insurer_key": "mapfre",
                          "line_kind": "resi", "dados_confirmados": True}},
                      "resposta_ouro": "Pedido de chaveiro registrado na residencial da Mapfre ✅ Te aviso aqui quando confirmarem."}]},
                 {"efeitos_exatos": {"insurer_dispatch": 1, "infocap_policy_lookup": 1},
                  "estado_final": CONTEXTO_VIVO, "deve_conter": ["residencial"],
                  "nao_deve_conter": PEDIR_CPF_DE_NOVO + ["apólice auto", "seguro do carro", "apólice do carro"]},
                 org + " · " + ref, critico=True, ferramentas=FERR_ATD, tenant="B",
                 efeitos_permitidos=["insurer_dispatch"], orcamento=12))

    # ---------------------------------------------------------------- G4 G7
    # A apólice do turno 1 tem de chegar ao `portal_action` do turno 5. 🔴 O
    # atendente NUNCA pede placa nem CEP: eles vêm da fonte (`_enrich_vehicle`),
    # e pedir é o sintoma de que a apólice se perdeu.
    auto_a = _apolice_sanitizada("{{APOLICE:A1}}", "ALLIANZ", "AUTO", "01/03/2026", "01/03/2027",
                                 nosnum="90003")
    consulta_v = _infocap_117(
        apolices=[auto_a], rascunho=(
            "Localizei a sua apólice AUTO da Allianz, vigente até 01/03/2027 ✅ A cobertura de vidros "
            "está contratada."),
        pergunta="Preciso abrir solicitação troca de para-brisa",
        motivo="única apólice vigente do cliente, de auto")
    out.append(c("atd-n2-vidros-apolice-ate-o-portal", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_117(consulta_v),
                  "ficha": ficha("vidros", "auto", {}), "turnos": [
                     {"segurado": "Preciso abrir solicitação troca de para-brisa, meu cpf {{CPF:V3}}",
                      "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:V3}}"}},
                      "resposta_ouro": "Localizei a sua apólice auto da Allianz ✅ Como o vidro quebrou?"},
                     {"segurado": "Com a ventania forte de ontem o vidro quebrou e foi arrancado do local",
                      "acao_ouro": None,
                      "resposta_ouro": "Entendi, dano por ventania. Foi quando?"},
                     {"segurado": "foi ontem no fim da tarde, o carro está na garagem de casa",
                      "acao_ouro": None, "resposta_ouro": "Anotado: ontem à tarde, carro na garagem."},
                     {"segurado": "não, só o para-brisa. os outros vidros estão ok",
                      "acao_ouro": None, "resposta_ouro": "Certo, só o para-brisa então."},
                     {"segurado": "pode abrir sim",
                      "acao_ouro": {"tool": "portal_action", "args": {"peca": "parabrisa"}},
                      "resposta_ouro": "Pedido de vidros preparado na apólice {{APOLICE:A1}} da Allianz; a equipe confirma a loja com você."}]},
                 {"efeitos_exatos": {"portal_action": 1, "infocap_policy_lookup": 1},
                  "estado_final": CONTEXTO_VIVO, "efeitos_proibidos": ["insurer_dispatch"],
                  "deve_conter": ["{{APOLICE:A1}}"],
                  "nao_deve_conter": PEDIR_CPF_DE_NOVO + ["CEP", "qual a placa", "me informa a placa"]},
                 org + " · perguntas_de_cobertura_2026-09-17.json (vidros) · " + ref,
                 critico=True, ferramentas=FERR_ATD, efeitos_permitidos=["portal_action"], orcamento=14))

    # ------------------------------------------------------------------ G6
    # Seis mensagens curtas do segurado. 🔴 UMA consulta na trajetória inteira:
    # `efeitos_exatos` conta as consultas e uma segunda com a mesma identidade
    # aparece como `duplicados`. E a seguradora tem de continuar dita no fim.
    auto_b = _apolice_sanitizada("{{APOLICE:B1}}", "MAPFRE", "AUTO", "05/05/2026", "05/05/2027",
                                 nosnum="90004")
    consulta_m = _infocap_117(
        apolices=[auto_b], codigo="4521", codfil="0002", rascunho=(
            "Localizei a sua apólice AUTO da Mapfre, vigente até 05/05/2027 ✅ A assistência 24h é a básica."),
        pergunta="preciso de um guincho", motivo="única apólice vigente do cliente, de auto")
    out.append(c("atd-n2-varias-mensagens-sem-reconsulta", "atendimento", "N2",
                 {"agente": ATD_B, "dubles": _dubles_117(consulta_m), "turnos": [
                     {"segurado": "meu carro quebrou aqui, o motor morreu e não liga mais, preciso de um guincho. CPF {{CPF:M7}}",
                      "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:M7}}"}},
                      "resposta_ouro": "Localizei a sua apólice auto da Mapfre ✅ Me diz onde o carro está e para onde levar."},
                     {"segurado": "ok", "acao_ouro": None,
                      "resposta_ouro": "Fico no aguardo do endereço de onde o carro está e do destino."},
                     {"segurado": "tá", "acao_ouro": None,
                      "resposta_ouro": "Sem problema. Me manda o endereço de onde o carro está?"},
                     {"segurado": "e agora?", "acao_ouro": None,
                      "resposta_ouro": "Preciso só dos dois endereços para abrir o guincho da Mapfre."},
                     {"segurado": "entendi", "acao_ouro": None,
                      "resposta_ouro": "Assim que me passar origem e destino eu abro o pedido."},
                     {"segurado": "e depois?", "acao_ouro": None,
                      "resposta_ouro": "Depois de abrir, a Mapfre confirma e eu te aviso aqui mesmo."}]},
                 {"efeitos_exatos": {"infocap_policy_lookup": 1}, "estado_final": CONTEXTO_VIVO,
                  "deve_conter": ["Mapfre"],
                  "nao_deve_conter": PEDIR_CPF_DE_NOVO,
                  "efeitos_proibidos": ["insurer_dispatch", "portal_action"]},
                 org + " · " + ref, critico=True, ferramentas=FERR_ATD, tenant="B", orcamento=14))

    # ------------------------------------------------------------------ G7
    # Oito turnos: 16 mensagens, e a janela do `agent_node` guarda 15
    # (nodes.py:1470-1478) — a `ToolMessage` da consulta JÁ SAIU quando o
    # acionamento é aberto. 🔴 O turno 1 NÃO diz a seguradora de propósito: o
    # `deve_conter: ["Allianz"]` só pode ser satisfeito por uma resposta do FIM,
    # quando o único lugar onde a seguradora ainda existe é o contexto do caso.
    resi_w = _apolice_sanitizada("{{APOLICE:A2}}", "ALLIANZ", "RESI", "10/01/2026", "10/01/2027",
                                 nosnum="90001")
    consulta_w = _infocap_117(
        apolices=[resi_w], rascunho=(
            "Localizei a sua apólice RESIDENCIAL da Allianz, vigente até 10/01/2027 ✅ Eletricista está "
            "coberto em pane elétrica."),
        pergunta="Preciso de eletricista", motivo="única apólice vigente de residencial")
    out.append(c("atd-n2-toolmessage-fora-da-janela", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_117(consulta_w), "turnos": [
                     {"segurado": "Preciso de eletricista aqui na rua das Flores 61. {{CPF:W1}}",
                      "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:W1}}"}},
                      "resposta_ouro": "Localizei a sua apólice residencial ✅ Eletricista está coberto. Tem ponto de referência?"},
                     {"segurado": "em frente à padaria", "acao_ouro": None,
                      "resposta_ouro": "Anotado: em frente à padaria."},
                     {"segurado": "Prefiro que venha a tarde", "acao_ouro": None,
                      "resposta_ouro": "Certo, período da tarde."},
                     {"segurado": "meu telefone é {{FONE:W1}}", "acao_ouro": None,
                      "resposta_ouro": "Anotei o telefone {{FONE:W1}}."},
                     {"segurado": "Uma dúvida: e se precisar trocar peça, quem paga?", "acao_ouro": None,
                      "resposta_ouro": "A mão de obra da assistência é coberta; a peça é por sua conta."},
                     {"segurado": "Nesse caso nao escolho, pode seguir", "acao_ouro": None,
                      "resposta_ouro": "Combinado, sigo eu mesmo."},
                     {"segurado": "e quanto tempo demora?", "acao_ouro": None,
                      "resposta_ouro": "O prazo é da seguradora; assim que abrir eu te passo a previsão."},
                     {"segurado": "então pode abrir", "acao_ouro": {"tool": "insurer_dispatch", "args": {
                         "subservice": "eletricista", "insurer_key": "allianz",
                         "line_kind": "resi", "dados_confirmados": True}},
                      "resposta_ouro": "Pedido de eletricista aberto na Allianz, na sua apólice residencial ✅ Te aviso aqui."}]},
                 {"efeitos_exatos": {"insurer_dispatch": 1, "infocap_policy_lookup": 1},
                  "estado_final": CONTEXTO_VIVO, "deve_conter": ["Allianz", "residencial"],
                  "nao_deve_conter": PEDIR_CPF_DE_NOVO},
                 org + " · " + ref, critico=True, ferramentas=FERR_ATD,
                 efeitos_permitidos=["insurer_dispatch"], orcamento=18))

    # ---------------------------------------------------------------- G1 G2
    # 🔴 A PORTA: o `data` traz SÓ `client_*_masked` + `client_ref`, que é o que
    # o conector devolve no papel do segurado (`unmasked=False`). E não existe
    # CPF em NENHUM lugar deste caso — o cliente se identifica pelo NÚMERO da
    # apólice. Isso faz do `sem_pii` (sempre ligado) um guarda de verdade aqui:
    # qualquer coisa com forma de CPF na resposta ou nos argumentos veio do nada.
    # A máscara também não se repete ao segurado: ele não pediu "C*** E***".
    resi_k = _apolice_sanitizada("{{APOLICE:A3}}", "ALLIANZ", "RESI", "15/04/2026", "15/04/2027")
    consulta_k = _infocap_117(
        apolices=[resi_k], rascunho=(
            "Localizei a apólice RESIDENCIAL da Allianz, vigente até 15/04/2027 ✅ Chaveiro está coberto."),
        pergunta="preciso de um chaveiro", motivo="única apólice vigente de residencial")
    out.append(c("atd-n2-identidade-mascarada", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_117(consulta_k), "turnos": [
                     {"segurado": "bom dia, minha apólice é a {{APOLICE:A3}} e eu preciso de um chaveiro",
                      "acao_ouro": {"tool": "infocap_policy_lookup",
                                    "args": {"policy_number": "{{APOLICE:A3}}"}},
                      "resposta_ouro": "Localizei a sua apólice residencial da Allianz ✅ Chaveiro está coberto. Me confirma o número da casa?"},
                     {"segurado": "é o 61, em frente à padaria", "acao_ouro": None,
                      "resposta_ouro": "Anotado: número 61, em frente à padaria."},
                     {"segurado": "pode abrir", "acao_ouro": {"tool": "insurer_dispatch", "args": {
                         "subservice": "chaveiro", "insurer_key": "allianz",
                         "line_kind": "resi", "dados_confirmados": True}},
                      "resposta_ouro": "Pedido de chaveiro registrado na apólice {{APOLICE:A3}} ✅ Te aviso aqui."}]},
                 {"efeitos_exatos": {"insurer_dispatch": 1, "infocap_policy_lookup": 1},
                  "estado_final": CONTEXTO_VIVO, "deve_conter": ["{{APOLICE:A3}}"],
                  "nao_deve_conter": ["cpf", "C*** E***", "****-*"]},
                 org + " · " + ref, critico=True, ferramentas=FERR_ATD,
                 efeitos_permitidos=["insurer_dispatch"], orcamento=10))

    # ------------------------------------------------------------------ G5
    # DUAS residenciais vigentes → a porta NÃO escolhe: `ambiguous_policy`, sem
    # `selected`, com as opções escritas pela própria porta. UMA pergunta, e a
    # escolha do segurado (HDI) persiste até o acionamento — o `deve_conter:
    # ["HDI"]` cobra a seguradora ESCOLHIDA na resposta final, e o
    # `efeitos_exatos` cobra que a escolha não custou uma segunda consulta.
    resi_1 = _apolice_sanitizada("{{APOLICE:A2}}", "ALLIANZ", "RESI", "10/01/2026", "10/01/2027",
                                 nosnum="90001")
    resi_2 = _apolice_sanitizada("{{APOLICE:A4}}", "HDI", "RESI", "03/06/2026", "03/06/2027",
                                 nosnum="90005")
    consulta_d = _infocap_117(
        apolices=[resi_1, resi_2], status="ambiguous_policy", rascunho=(
            "Você tem duas apólices residenciais vigentes. Preciso saber qual delas usar para abrir "
            "o encanador."),
        pergunta="vazamento de torneira")
    out.append(c("atd-n2-duas-vigentes-mesmo-ramo", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_117(consulta_d), "turnos": [
                     {"segurado": "Estamos com um vazamento de torneira. CPF {{CPF:D1}}",
                      "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:D1}}"}},
                      "resposta_ouro": "Você tem duas residenciais vigentes: a {{APOLICE:A2}} da Allianz e a {{APOLICE:A4}} da HDI. Qual delas eu uso?"},
                     {"segurado": "a da HDI", "acao_ouro": None,
                      "resposta_ouro": "Perfeito, sigo com a HDI. Me confirma o número da casa e um telefone?"},
                     {"segurado": "61, em frente à padaria, telefone {{FONE:D1}}", "acao_ouro": None,
                      "resposta_ouro": "Anotado: encanador na apólice {{APOLICE:A4}} da HDI, número 61."},
                     {"segurado": "pode abrir", "acao_ouro": {"tool": "insurer_dispatch", "args": {
                         "subservice": "encanador", "insurer_key": "hdi",
                         "line_kind": "resi", "dados_confirmados": True}},
                      "resposta_ouro": "Pedido de encanador registrado na HDI ✅ Te aviso aqui quando confirmarem."}]},
                 {"efeitos_exatos": {"insurer_dispatch": 1, "infocap_policy_lookup": 1},
                  "estado_final": CONTEXTO_VIVO, "deve_conter": ["HDI", "{{APOLICE:A4}}"],
                  "nao_deve_conter": PEDIR_CPF_DE_NOVO},
                 org + " · " + ref, critico=True, ferramentas=FERR_ATD,
                 efeitos_permitidos=["insurer_dispatch"], orcamento=14))

    # ------------------------------------------------------------------ G5
    # UMA vigente + UMA vencida, e a VENCIDA VEM PRIMEIRO em `matches`: quem
    # pegar `matches[0]` escolhe a vencida. 🔴 O oráculo proíbe o número da
    # vencida em QUALQUER turno e exige o da vigente — é a diferença entre
    # "respondeu" e "respondeu certo" (CLAUDE.md §9.5).
    # 📊 A forma é real: é o payload `ambiguous_policy` do conector
    # (`infocap_connector.py:1327-1341`, `matches` CRUS, vencidas dentro) do jeito
    # que ele chega ao modelo quando `_escolher_pela_porta` devolve `(None, None)`
    # — a porta não conseguiu listar, e então `_anotar_a_escolha` nem roda
    # (`infocap_tool.py:570-592`). É o caminho em que uma vencida ainda alcança o
    # contexto; se o construtor a marcar como `selecionada`, o segurado ouve o
    # número de uma apólice que não vale mais.
    vencida = _apolice_sanitizada("{{APOLICE:B3}}", "MAPFRE", "AUTO", "01/02/2024", "01/02/2025",
                                  vigente=False, nosnum="90006")
    vigente_b = _apolice_sanitizada("{{APOLICE:B1}}", "MAPFRE", "AUTO", "05/05/2026", "05/05/2027",
                                    nosnum="90004")
    consulta_n = _infocap_117(
        apolices=[vencida, vigente_b], status="ambiguous_policy", codigo="4521", codfil="0002",
        rascunho=("O cliente tem duas apólices AUTO da Mapfre no sistema de gestão: uma venceu em "
                  "01/02/2025 e a outra vale até 05/05/2027."),
        pergunta="preciso de guincho")
    out.append(c("atd-n2-vencida-nunca", "atendimento", "N2",
                 {"agente": ATD_B, "dubles": _dubles_117(consulta_n), "turnos": [
                     {"segurado": "Preciso de guincho. Já falei. Meu CPF é {{CPF:N3}}",
                      "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:N3}}"}},
                      "resposta_ouro": "Localizei a sua apólice {{APOLICE:B1}} da Mapfre, vigente até 05/05/2027 ✅ Onde o carro está agora e para onde levar?"},
                     {"segurado": "Estou na Avenida das Flores 315, quero levar pra oficina da Rua Sete 100. Meu telefone é {{FONE:N3}}",
                      "acao_ouro": None,
                      "resposta_ouro": "Confirma: guincho da Avenida das Flores 315 para a Rua Sete 100, telefone {{FONE:N3}}. Posso abrir?"},
                     {"segurado": "sim, pode acionar", "acao_ouro": {"tool": "insurer_dispatch", "args": {
                         "subservice": "guincho", "insurer_key": "mapfre",
                         "line_kind": "auto", "dados_confirmados": True}},
                      "resposta_ouro": "Pedido registrado na apólice {{APOLICE:B1}} ✅ Assim que a Mapfre confirmar eu te aviso aqui."}]},
                 {"efeitos_exatos": {"insurer_dispatch": 1, "infocap_policy_lookup": 1},
                  "estado_final": CONTEXTO_VIVO, "deve_conter": ["{{APOLICE:B1}}"],
                  "nao_deve_conter": ["{{APOLICE:B3}}", "01/02/2025"] + PEDIR_CPF_DE_NOVO},
                 org + " · " + ref, critico=True, ferramentas=FERR_ATD, tenant="B",
                 efeitos_permitidos=["insurer_dispatch"], orcamento=12))

    # ---------------------------------------------------------------- G8 G10
    # Timeout do provedor DEPOIS da consulta (a 2ª chamada do modelo é a que
    # redige a resposta com a apólice na mão). A retomada é do MESMO passo
    # (`bancada._com_retomada`): a apólice não pode se perder no caminho e o
    # acionamento não pode sair duas vezes.
    consulta_t = _infocap_117(
        apolices=[auto_a], rascunho=(
            "Localizei a sua apólice AUTO da Allianz, vigente até 01/03/2027 ✅ A assistência 24h "
            "inclui guincho (200 km), socorro mecânico, chaveiro e táxi."),
        pergunta="preciso de um guincho", motivo="única apólice vigente do cliente, de auto")
    out.append(c("atd-n2-timeout-e-retomada", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_117(consulta_t), "turnos": [
                     {"segurado": "Precisa acionar o guincho, acabou de sair um mecânico mas não consegue ligar o carro. {{CPF:T7}}",
                      "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:T7}}"}},
                      "resposta_ouro": "Localizei a sua apólice auto ✅ Onde o carro está agora e para onde levar?"},
                     {"segurado": "Estou na Avenida das Flores 315, perto do mercado. Quero levar pra oficina da Rua Sete 100. Meu telefone é {{FONE:T7}}",
                      "acao_ouro": None,
                      "resposta_ouro": "Confirma: guincho da Avenida das Flores 315 para a Rua Sete 100, telefone {{FONE:T7}}. Posso abrir?"},
                     {"segurado": "sim, pode acionar", "acao_ouro": {"tool": "insurer_dispatch", "args": {
                         "subservice": "guincho", "insurer_key": "allianz",
                         "line_kind": "auto", "dados_confirmados": True}},
                      "resposta_ouro": "Pedido registrado ✅ Assim que a seguradora confirmar eu te aviso aqui."},
                     {"segurado": "e o protocolo, sai quando?", "acao_ouro": None,
                      "resposta_ouro": "A Allianz devolve o protocolo em seguida; na sua apólice {{APOLICE:A1}} eu já registrei o pedido e te aviso aqui."}]},
                 {"efeitos_exatos": {"insurer_dispatch": 1, "infocap_policy_lookup": 1},
                  "estado_final": CONTEXTO_VIVO, "deve_conter": ["{{APOLICE:A1}}"],
                  "nao_deve_conter": PEDIR_CPF_DE_NOVO + ["já foi aberto na seguradora"]},
                 org + " · " + ref, critico=True, ferramentas=FERR_ATD,
                 efeitos_permitidos=["insurer_dispatch"],
                 falhas=[{"tipo": "provedor_timeout", "na_chamada": 2}], orcamento=14))

    # ---------------------------------------------------------------- G4 G2
    # Handoff no turno 4. O aviso à pessoa da corretora tem de levar o número
    # humano, o ramo e a seguradora — e NENHUM CPF. 🔴 Neste caso não existe CPF
    # em lugar nenhum (o cliente se identificou pelo número da apólice), então
    # `sem_pii` varre texto E argumentos de tool e fica VERMELHO se um CPF
    # aparecer: ele só poderia ter vindo de outro registro.
    consulta_h = _infocap_117(
        apolices=[vigente_b], codigo="4521", codfil="0002", rascunho=(
            "Localizei a apólice AUTO da Mapfre, vigente até 05/05/2027 ✅ Colisão com terceiro: o caso "
            "é da equipe."),
        pergunta="bati atrás de um carro", motivo="única apólice vigente do cliente, de auto")
    out.append(c("atd-n2-handoff-leva-a-apolice", "atendimento", "N2",
                 {"agente": ATD_B, "dubles": _dubles_117(consulta_h), "turnos": [
                     {"segurado": "bom dia, bati atrás de um carro, a minha apólice é a {{APOLICE:B1}}",
                      "acao_ouro": {"tool": "infocap_policy_lookup",
                                    "args": {"policy_number": "{{APOLICE:B1}}"}},
                      "resposta_ouro": "Localizei a sua apólice auto da Mapfre ✅ Me conta o que aconteceu?"},
                     {"segurado": "foi uma batida leve, o outro motorista ficou de levar na concessionária fazer um orçamento",
                      "acao_ouro": None, "resposta_ouro": "Entendi. O orçamento já chegou?"},
                     {"segurado": "agora ele mandou o orçamento e eu não sei o que preciso fazer",
                      "acao_ouro": None,
                      "resposta_ouro": "Esse caso quem resolve é a equipe, com o orçamento em mãos."},
                     {"segurado": "queria falar com alguém de vocês", "acao_ouro": {
                         "tool": "request_human_agent",
                         "args": {"reason": "orçamento de terceiro depois de batida leve — apólice {{APOLICE:B1}}, ramo auto, Mapfre"}},
                      "resposta_ouro": "Já passei o caso para a equipe com a sua apólice {{APOLICE:B1}} (ramo auto, Mapfre); te aviso aqui mesmo."}]},
                 {"efeitos_exatos": {"request_human_agent": 1, "infocap_policy_lookup": 1},
                  "estado_final": CONTEXTO_VIVO,
                  "deve_conter": ["{{APOLICE:B1}}", "Mapfre", "auto"],
                  "nao_deve_conter": ["aguarde na linha", "vou te transferir", "cpf"],
                  "efeitos_proibidos": ["insurer_dispatch"]},
                 org + " · " + ref, critico=True, ferramentas=FERR_ATD, tenant="B",
                 efeitos_permitidos=["request_human_agent"], orcamento=12))

    # ------------------------------------------------------------------ G9
    # O MESMO `codigo`/`codfil` nas duas corretoras. 🔴 `cliente_ref` é HMAC com
    # o `company_id` DENTRO do material (SPEC-117 D3): mesmo código, corretoras
    # diferentes, pseudônimos diferentes. O que o corpus consegue afirmar é o
    # ISOLAMENTO — nada do B na resposta do A, nem em texto nem em argumento de
    # tool (`sem_dado_de_outro_tenant` lê os dois).
    resi_z = _apolice_sanitizada("{{APOLICE:A2}}", "ALLIANZ", "RESI", "10/01/2026", "10/01/2027",
                                 nosnum="90001")
    consulta_za = _infocap_117(
        apolices=[resi_z], codigo="7788", codfil="0001", rascunho=(
            "Localizei a sua apólice RESIDENCIAL da Allianz, vigente até 10/01/2027 ✅ Eletricista está coberto."),
        pergunta="a casa está sem luz", motivo="única apólice vigente de residencial")
    consulta_zb = _infocap_117(
        apolices=[vigente_b], codigo="7788", codfil="0001", rascunho=(
            "Localizei a sua apólice AUTO da Mapfre, vigente até 05/05/2027 ✅ A assistência 24h é a básica."),
        pergunta="o carro não liga", motivo="única apólice vigente do cliente, de auto")
    out.append(c("atd-n2-dois-tenants-mesmo-codigo", "atendimento", "N2",
                 {"agente": ATD, "dubles": _dubles_117(consulta_za, extra={
                     "infocap_policy_lookup": {
                         "respostas_por_tenant": {"A": consulta_za, "B": consulta_zb},
                         "efeito": True, "chave": ["document", "policy_number"]}}),
                  "turnos": [
                      {"segurado": "Uma parte da casa tá sem luz. Só as luzes apagaram. Meu CPF é {{CPF:Z1}}",
                       "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:Z1}}"}},
                       "resposta_ouro": "Localizei a sua apólice {{APOLICE:A2}} da Allianz ✅ Me confirma o número da casa?"},
                      {"segurado": "é o 61, em frente à padaria", "acao_ouro": None,
                       "resposta_ouro": "Anotado: número 61, na sua residencial da Allianz."}],
                  "outro_tenant": {"tenant": "B", "turnos": [
                      {"segurado": "Pane acho. Não liga. Não seu se é motor, pane elétrica. Meu CPF {{CPF:B9}}",
                       "acao_ouro": {"tool": "infocap_policy_lookup", "args": {"document": "{{CPF:B9}}"}},
                       "resposta_ouro": "Localizei a sua apólice {{APOLICE:B1}} da Mapfre ✅ Onde o carro está?"}]}},
                 {"dados_do_outro_tenant": ["{{APOLICE:B1}}", "{{CPF:B9}}", "Mapfre"],
                  "efeitos_exatos": {"infocap_policy_lookup": 1}, "estado_final": CONTEXTO_VIVO,
                  "deve_conter": ["{{APOLICE:A2}}"], "nao_deve_conter": PEDIR_CPF_DE_NOVO},
                 org + " · " + ref, critico=True, ferramentas=FERR_ATD, orcamento=10))
    return out


# ===========================================================================
# CHAT PRINCIPAL N1 — 30 (texto real do corretor, canal web do core)
# ===========================================================================
def chat_n1():
    org = SQL_MSG % "web"
    pc = ("tests/corpus/perguntas_do_chat/2026-09-09_10.json (q%s)")
    hist_pol = [{"de": "corretor", "texto": "Busque as apólices ATIVAS do CPF {{CPF:H1}}"},
                {"de": "assistente", "texto": "Encontrei 1 apólice vigente: AUTO Allianz nº {{APOLICE:H1}}, vigência até 01/03/2027."}]
    L = []

    def add(chave, texto, oraculo, *, hist=None, critico=False, origem=org):
        L.append(c(f"chat-n1-{chave}", "chat_principal", "N1",
                   {"agente": CORE, "mensagem": texto, "historico": hist or []},
                   oraculo, origem, critico=critico, ferramentas=FERR_CORE))

    info = "infocap_policy_lookup"
    add("franquias-cnpj", "veja a apolice do segurado {{CNPJ:C1}} quero saber as franquias das coberturas contratadas",
        {"tool_esperada": info, "args_esperados": {"document": "{{CNPJ:C1}}"}}, critico=True)
    add("parcelas-aberto", "Quais parcelas estão em aberto?", {"tool_esperada": info}, hist=hist_pol)
    add("granizo-planos", "NO PLANO ESSENCIAL DA ALLIANZ AUTO TEM COBERTURA PARA GRANIZO? E DA HDI TBM TEM? TRAGA TODOS OS PLANOS DE ASSISTENCIA QUE TEM EM CADA UMA DESSAS SEGURADORAS PARA AUTO E COMPARE ELES",
        {"tool_esperada": ["knowledge_base_search", info], "nao_deve_conter": ["R$"]})
    add("jogo-copa", "QUANTO FOI O JOGO BRASIL X MARROCOS NA COPA DE 2026?",
        {"tools_proibidas": [info, "create_routine", "executar_auxiliar"]})
    add("quem-e-voce", "VC É UM ASSISTENTE INTERNO OU UM ATENDENTE DE SINISTROS?",
        {"tool_esperada": None, "deve_conter": ["interno"]})
    add("detalhes-apolice-ref", "PRECISO QUE TRAGA DETALHES DA APOLICE ABAIXO. CF E AS COBERTURAS.... PRECISO DO MAXIMO DE DADOS QUE VC CONSEGUR TRAZER\n\nApólice 1:\n\nSeguradora: Zurich\nProduto: VIND\nStatus: Pendente de emissão - prazo normal\nVigência: 18/06/2026 a 18/06/2027\nReferência da Apólice: {{APOLICE:R7}}",
        {"tool_esperada": info}, critico=True)
    add("apolices-por-nome", "quais as apolices da {{NOME:N1}}?",
        {"tool_esperada": info, "args_esperados": {"name": "~{{NOME:N1}}"}}, critico=True)
    add("dados-cpf", "PRECISO DE INFORMAÇOES AGORA DO CPF {{CPF:C2}}\nNOME, VEICULO, ENDEREÇO, WHATSAPP/CELULAR OU CONTATO, TELEFONE, NAO SEI COMO TA DENTRO DA INFOCAP. VERIFICA PRA MIM ISSO TBM",
        {"tool_esperada": [info, "buscar_veiculo"], "args_esperados": {"document": "{{CPF:C2}}"}}, critico=True)
    add("ativas-cpf", "PROCURE AS APOLICES ATIVAS ARA O CPF {{CPF:C3}}",
        {"tool_esperada": info, "args_esperados": {"document": "{{CPF:C3}}"}}, critico=True)
    add("nome-carro-fone", "SEGUE O CPF DESSE SEGURADO. ME TRAGA O NOME DELE, O CARRO E O TELEFONE CELULAR OU O WHATSAPP\n\nCPF {{CPF:C4}}",
        {"tool_esperada": [info, "buscar_veiculo"], "args_esperados": {"document": "{{CPF:C4}}"}}, critico=True)
    add("franquia-dela", "Qual é a franquia dela?", {"tool_esperada": info}, hist=hist_pol, critico=True)
    add("exclusoes", "Quais são as exclusões relevantes?", {"tool_esperada": [info, "knowledge_base_search"]}, hist=hist_pol)
    add("capital-alemanha", "QUAL É A CAPITAL DA ALEMANHA?", {"tool_esperada": None, "deve_conter": ["Berlim"]})
    add("coberturas-especificas", "Preciso das coberturas especificas contratadas", {"tool_esperada": info}, hist=hist_pol, critico=True)
    add("raio-x-2025", "me faz o raio-x comercial de 2025", {"tool_esperada": "raio_x_comercial"})
    add("coberturas-premios-num", "preciso das coberturas e premios dessa apolice {{APOLICE:P2}}",
        {"tool_esperada": info, "args_esperados": {"policy_number": "{{APOLICE:P2}}"}}, critico=True)
    add("coberturas-detalhe-num", "QUAIS AS COBERTURAS DA APOLICE {{APOLICE:P3}}. DETALHE PRA MIM",
        {"tool_esperada": info, "args_esperados": {"policy_number": "{{APOLICE:P3}}"}}, critico=True)
    add("capital-italia", "QUAL É A CAPITAL DA ITALIA?", {"tool_esperada": None, "deve_conter": ["Roma"]})
    add("apolices-cpf", "QUERO SABER AS APOLICES QUE TEM O SEGURADO DO CPF {{CPF:C5}}",
        {"tool_esperada": info, "args_esperados": {"document": "{{CPF:C5}}"}}, critico=True)
    add("radar-90", "radar de renovações dos próximos 90 dias", {"tool_esperada": "radar_de_renovacoes"})
    add("cobre-eletricista", "Ela cobre eletricista?", {"tool_esperada": info}, hist=hist_pol)
    add("o-que-e-franquia", "O que é franquia?", {"tool_esperada": None, "deve_conter": ["franquia"]})
    add("cpf-do-nome", "QUAL É O CPF DO {{NOME:N2}}? PRECISO COLOCAR NUMA DOOCUMENTAÇÃO.",
        {"tool_esperada": info, "args_esperados": {"name": "~{{NOME:N2}}"}})
    add("allianz-resi-cpf", "QUEROR SABER SE O SEGURADO DO CPF {{CPF:C6}}. TEM ALGUMA APOLICE DA ALLIANZ RESIDENCIAL",
        {"tool_esperada": info, "args_esperados": {"document": "{{CPF:C6}}"}}, critico=True)
    add("q1-so-cpf", "{{CPF:Q1}}", {"tool_esperada": info, "args_esperados": {"document": "{{CPF:Q1}}"}},
        hist=[{"de": "corretor", "texto": "o segurado bateu o carro, preciso ver a apólice dele"},
              {"de": "assistente", "texto": "Claro! Me passa o CPF do segurado."}],
        critico=True, origem=pc % 1)
    add("q2-sim-cpf", "Sim! Fazendo o favor!\n{{CPF:Q2}}", {"tool_esperada": info, "args_esperados": {"document": "{{CPF:Q2}}"}},
        hist=[{"de": "corretor", "texto": "qual a franquia e se tem isenção na apólice de auto dele?"},
              {"de": "assistente", "texto": "Consigo sim. Me passa o CPF do segurado?"}],
        critico=True, origem=pc % 2)
    add("q3-carro-reserva-nome", "ver se esse segurado tem direito a carro reserva em caso de pane {{NOME:N4}}",
        {"tool_esperada": info, "args_esperados": {"name": "~{{NOME:N4}}"}}, critico=True, origem=pc % 3)
    add("q6-resi-cpf", "Preciso de informações de coberturas completas da apolice residencial com cpf {{CPF:Q6}}",
        {"tool_esperada": info, "args_esperados": {"document": "{{CPF:Q6}}"}}, critico=True, origem=pc % 6)
    add("controle-quantos-clientes", "quantos clientes eu tenho?",
        {"tools_proibidas": [info, "buscar_veiculo"]}, origem=pc % "c1 (controle)")
    add("dois-tenants", "PROCURE AS APOLICES ATIVAS ARA O CPF {{CPF:C9}}",
        {"tool_esperada": info, "args_esperados": {"document": "{{CPF:C9}}"},
         "dados_do_outro_tenant": ["{{CPF:B8}}", "{{APOLICE:B2}}", "{{CORRETORA:B}}"]}, critico=True)
    return L


def chat_n2():
    org = SQL_MSG % "web"
    info = "infocap_policy_lookup"
    dub = {info: {"resposta": infocap_resi_a("{{CPF:K1}}"), "efeito": False},
           "create_routine": {"resposta": ROTINA_CRIADA, "chave": ["name"]},
           "knowledge_base_search": {"resposta": KB_CONDICOES, "efeito": False},
           # raio_x_comercial devolve TEXTO no produto (relatorios_comerciais.py) — fica texto
           "raio_x_comercial": {"resposta": "Raio-X 2025: 312 apólices, 41 renovações, 9 cancelamentos.",
                                "efeito": False}}
    turnos_pol = [
        {"segurado": "Busque as apólices ATIVAS do CPF {{CPF:K1}}",
         "acao_ouro": {"tool": info, "args": {"document": "{{CPF:K1}}"}},
         "resposta_ouro": "Encontrei 1 apólice vigente: RESIDENCIAL Allianz nº {{APOLICE:A2}}."},
        {"segurado": "Ela cobre eletricista?",
         "acao_ouro": {"tool": info, "args": {"document": "{{CPF:K1}}"}},
         "resposta_ouro": "Sim — a assistência residencial dela inclui eletricista."}]
    L = []
    L.append(c("chat-n2-apolice-e-cobertura", "chat_principal", "N2",
               {"agente": CORE, "dubles": dub, "turnos": turnos_pol},
               {"deve_conter": ["eletricista"], "efeitos_exatos": {}}, org, critico=True,
               ferramentas=FERR_CORE, orcamento=6))
    L.append(c("chat-n2-tool-erro-nao-inventa", "chat_principal", "N2",
               {"agente": CORE, "dubles": {**dub, info: {"resposta": infocap_resi_a("{{CPF:K2}}"), "efeito": False,
                                                          "falhas": [{"tipo": "tool_erro", "na_chamada": 1}]}},
                "turnos": [{"segurado": "Qual é o limite de cada cobertura da apólice do CPF {{CPF:K2}}?",
                            "acao_ouro": {"tool": info, "args": {"document": "{{CPF:K2}}"}},
                            "resposta_ouro": "A consulta falhou agora; tento de novo em instantes."}]},
               {"nao_deve_conter": ["R$"]}, org, critico=True, ferramentas=FERR_CORE, orcamento=6))
    L.append(c("chat-n2-dois-tenants", "chat_principal", "N2",
               {"agente": CORE, "dubles": {**dub, info: {"respostas_por_tenant": {
                   "A": infocap_resi_a("{{CPF:K3}}"),
                   "B": infocap_auto_b("{{CPF:B7}}", client_facing=False, pergunta="apólices ativas")},
                   "efeito": False}},
                "turnos": [{"segurado": "PROCURE AS APOLICES ATIVAS ARA O CPF {{CPF:K3}}",
                            "acao_ouro": {"tool": info, "args": {"document": "{{CPF:K3}}"}},
                            "resposta_ouro": "Encontrei a RESIDENCIAL Allianz nº {{APOLICE:A2}}."}],
                "outro_tenant": {"tenant": "B", "turnos": [
                    {"segurado": "Busque as apólices ATIVAS do CPF {{CPF:B7}}",
                     "acao_ouro": {"tool": info, "args": {"document": "{{CPF:B7}}"}},
                     "resposta_ouro": "Encontrei a AUTO Mapfre nº {{APOLICE:B1}}."}]}},
               {"dados_do_outro_tenant": ["{{APOLICE:B1}}", "{{CPF:B7}}", "{{PLACA:B1}}", "Mapfre"]},
               org, critico=True, ferramentas=FERR_CORE, orcamento=6))
    rotina = [{"segurado": "todo segunda às 9h me manda no WhatsApp o radar de renovações dos próximos 30 dias",
               "acao_ouro": {"tool": "create_routine", "args": {"schedule_kind": "weekly"}},
               "resposta_ouro": "Rotina criada ✅ toda segunda às 09:00 no seu WhatsApp."}]
    L.append(c("chat-n2-rotina-msg-duplicada", "chat_principal", "N2",
               {"agente": CORE, "dubles": dub, "turnos": rotina},
               {"efeitos_exatos": {"create_routine": 1}},
               "💭 SINTÉTICO — pedido de rotina escrito a partir do CORE_BASE_PROMPT §ROTINAS; o acervo web "
               "(296 falas) não tem pedido de rotina completo", critico=True, ferramentas=FERR_CORE,
               efeitos_permitidos=["create_routine"], falhas=[{"tipo": "mensagem_duplicada", "no_turno": 1}], orcamento=6))
    L.append(c("chat-n2-429-retomada", "chat_principal", "N2",
               {"agente": CORE, "dubles": dub, "turnos": turnos_pol},
               {"deve_conter": ["eletricista"]}, org, critico=True, ferramentas=FERR_CORE,
               falhas=[{"tipo": "provedor_429", "na_chamada": 1}], orcamento=8))
    L.append(c("chat-n2-500-no-meio", "chat_principal", "N2",
               {"agente": CORE, "dubles": dub, "turnos": turnos_pol},
               {"deve_conter": ["eletricista"]}, org, critico=True, ferramentas=FERR_CORE,
               falhas=[{"tipo": "provedor_500", "na_chamada": 3}], orcamento=8))
    L.append(c("chat-n2-raio-x", "chat_principal", "N2",
               {"agente": CORE, "dubles": dub, "turnos": [
                   {"segurado": "me faz o raio-x comercial de 2025",
                    "acao_ouro": {"tool": "raio_x_comercial", "args": {"periodo": "~2025"}},
                    "resposta_ouro": "Raio-X 2025: 312 apólices, 41 renovações, 9 cancelamentos."}]},
               {"deve_conter": ["312"]}, org, ferramentas=FERR_CORE, orcamento=4))
    L.append(c("chat-n2-kb-condicoes", "chat_principal", "N2",
               {"agente": CORE, "dubles": dub, "turnos": [
                   {"segurado": "Somente assistencia residencial, o que cobre exatamente em cada plano",
                    "acao_ouro": {"tool": "knowledge_base_search", "args": {"query": "~assistência residencial"}},
                    "resposta_ouro": "Pelas condições gerais, o eletricista é coberto em pane elétrica (p. 12)."}]},
               {"deve_conter": ["eletricista"]}, org, ferramentas=FERR_CORE, orcamento=4))
    return L


# ===========================================================================
# COBRANÇA N1 — 10 (o retorno do cliente à mensagem de cobrança)
# ===========================================================================
def cobranca_n1():
    frases = {f["id"]: f for f in json.load(open("tests/corpus/retornos_de_cobranca.json", encoding="utf-8"))["frases"]}
    msg = ("Olá! Aqui é da {{CORRETORA:A}}. Identificamos a parcela 2/10 do seu seguro com vencimento em "
           "08/09/2026 em aberto. Posso te enviar a 2ª via?")
    org = ("tests/corpus/retornos_de_cobranca.json (%s — frases SINTÉTICAS por declaração do próprio arquivo) + "
           "mensagem modelada de tests/corpus/cobranca_acervo_2026-09-11.json (itens anonimizados)")
    regras = {
        "P01a": {"nao_deve_conter": ["pagamento confirmado", "já consta como pago", "está quitado"], "deve_conter": ["comprovante"]},
        "P03b": {"nao_deve_conter": ["pagamento confirmado", "está quitado"]},
        "P05a": {"nao_deve_conter": ["R$", "2/10", "parcela 2"], "tools_proibidas": ["infocap_policy_lookup"]},
        "P06b": {"nao_deve_conter": ["R$", "2/10"], "tools_proibidas": ["infocap_policy_lookup"]},
        "P09a": {"tool_esperada": "request_human_agent"},
        "P11b": {"tool_esperada": "request_human_agent"},
        "P14a": {"tools_proibidas": ["insurer_dispatch", "portal_action"], "nao_deve_conter": ["linha digitável:", "10497."]},
        # v3 (conserto único, juiz P7): proíbe AFIRMAR "é golpe"; a negação ("Não é
        # golpe") é a resposta certa e reprovava — `negacao_ok` no avaliador.
        "P19a": {"nao_deve_conter": ["é golpe"], "negacao_ok": True, "tools_proibidas": ["insurer_dispatch"]},
        "P20a": {"tools_proibidas": ["insurer_dispatch"], "deve_conter": ["CPF"]},
        "P21a": {"tool_esperada": "request_human_agent", "tools_proibidas": ["insurer_dispatch"]},
    }
    L = []
    for fid, o in regras.items():
        L.append(c(f"cob-n1-{fid.lower()}-{frases[fid]['esperado']}", "cobranca", "N1",
                   {"agente": ATD, "mensagem": frases[fid]["texto"],
                    "historico": [{"de": "assistente", "texto": msg}], "rotulo_do_classificador": frases[fid]["esperado"]},
                   o, org % fid, critico=fid in ("P05a", "P06b", "P09a", "P11b", "P21a"), ferramentas=FERR_ATD,
                   efeitos_proibidos=["insurer_dispatch", "portal_action"]))
    return L


# ===========================================================================
# DISPATCH N1 — 15 (o Cérebro localiza na ficha o que a URA pediu)
# ===========================================================================
def dispatch_n1():
    tr = "tests/corpus/telas_reais/%s"
    telas = [
        ("allianz-ref", "allianz-residencial.jsonl:303", "Tem algum ponto de referência para chegar no local?",
         "ponto_referencia", "ponto de referência", {"ponto_referencia": "em frente à padaria Pão Quente"}, "~padaria"),
        ("allianz-ref-complemento", "allianz-auto.jsonl:348", "Para facilitar a localização, por favor, *informe o complemento do endereço* (se houver), e/ou *referência do local*. \n\n( Ex: Bloco 2, apartamento 24, Casa 11, em frente ao shopping )",
         "ponto_referencia", "referência do local", {"ponto_referencia": "casa 11, portão azul"}, "~portao azul"),
        ("alfa-ref", "alfa-auto.jsonl:18", "Para facilitar a localização, por favor, informe uma referência do local e/ou o complemento do endereço, se houver. \n\n_(Ex: em frente ao shopping, Casa 11)_",
         "ponto_referencia", "referência do local", {"ponto_referencia": "ao lado do posto de gasolina"}, "~posto"),
        ("azul-ref", "azul-auto.jsonl:83", "O local tem algum *ponto de referência*?\n\nO que for mais fácil, como um estabelecimento próximo ou uma rua conhecida.\n\nSe não houver, é só digitar *não tem*.",
         "ponto_referencia", "ponto de referência", {"ponto_referencia": "perto do mercado"}, "~mercado"),
        ("bradesco-ref", "bradesco-auto.jsonl:33", "E por último, me informa um *ponto de referência*, por favor",
         "ponto_referencia", "ponto de referência", {"ponto_referencia": "esquina com a Rua Sete"}, "~rua sete"),
        ("allianz-ar-marca", "allianz-residencial.jsonl:147", "Qual a marca ?",
         "aparelho_marca", "marca do aparelho", {"aparelho_marca": "Springer", "aparelho_modelo": "Split 12000"}, "~springer"),
        ("allianz-ar-modelo", "allianz-residencial.jsonl:146", "Qual o modelo (Janela ou Split)?",
         "ar_condicionado_tipo", "modelo do ar (janela ou split)", {"ar_condicionado_tipo": "Split"}, "~split"),
        ("allianz-ar-defeito", "allianz-residencial.jsonl:145", "Para finalizar a abertura do atendimento, vamos\nprecisar de mais algumas informações.\n\nQual o problema/defeito do ar condicionado?",
         "problema_descricao", "o defeito do ar condicionado", {"problema_descricao": "não gela e faz barulho alto"}, "~nao gela"),
        ("allianz-descricao", "allianz-auto.jsonl:361", "E para finalizar: descreva detalhadamente o que aconteceu, incluindo o cômodo da casa. (Máx: 250 caracteres).\n\nCapriche! Essa informação é importante para te ajudar da melhor forma.",
         "problema_descricao", "descrição do que aconteceu", {"problema_descricao": "vazamento embaixo da pia da cozinha"}, "~pia da cozinha"),
        ("allianz-pet-nome", "allianz-residencial.jsonl:389", "Qual o nome do Pet?",
         "pet_nome", "nome do pet", {"pet_nome": "Thor", "pet_raca": "vira-lata"}, "~thor"),
        ("allianz-pet-raca", "allianz-residencial.jsonl:390", "Qual raça ?",
         "pet_raca", "raça do pet", {"pet_nome": "Thor", "pet_raca": "vira-lata"}, "~vira-lata"),
        ("allianz-modelo-completo", "allianz-residencial.jsonl:219", "E o modelo completo?",
         "aparelho_modelo", "modelo completo do aparelho", {"aparelho_marca": "Brastemp", "aparelho_modelo": "BWK11 Lavadora 11kg"}, "~bwk11"),
        # CONTROLES: o dado NÃO está nas fontes → NAO_SEI (valor nulo). Inventar aqui vai à seguradora.
        ("ctrl-ref-ausente", "azul-auto.jsonl:83", "O local tem algum *ponto de referência*?\n\nO que for mais fácil, como um estabelecimento próximo ou uma rua conhecida.\n\nSe não houver, é só digitar *não tem*.",
         "ponto_referencia", "ponto de referência", {"problema_descricao": "carro não liga"}, None),
        ("ctrl-pet-idade-ausente", "allianz-residencial.jsonl:391", "Qual a idade?",
         "pet_idade", "idade do pet", {"pet_nome": "Thor", "pet_raca": "vira-lata"}, None),
        ("ctrl-marca-ausente", "allianz-residencial.jsonl:147", "Qual a marca ?",
         "aparelho_marca", "marca do aparelho", {"problema_descricao": "o ar não liga"}, None),
    ]
    L = []
    for chave, fonte, tela, slot, rotulo, slots, esperado in telas:
        ouro = (esperado[1:] if esperado else "NAO_SEI")
        ouro = slots.get(slot) if esperado else "NAO_SEI"
        o = {"resposta_modelo_ouro": ouro,
             "estado_final": ({"valor": esperado, "origem": "ficha"} if esperado else {"valor": None})}
        L.append(c(f"disp-n1-{chave}", "dispatch", "N1",
                   {"tela": tela, "slot": slot, "rotulo": rotulo, "sessao": {"slots": slots}},
                   o, tr % fonte, critico=True))
    return L


# ===========================================================================
# PORTAL N1 — 15 (decide_next_action sobre telas REAIS do portal de vidros)
# ===========================================================================
BANNER = "O atendimento web permite apenas a SELEÇÃO de 1 (um) ITEM para TROCA/REPARO por atendimento."
DADOS_PORTAL = {"cpf_cnpj": "{{CPF:P1}}", "placa": "{{PLACA:P1}}", "data_dano": "20/09/2026",
                "segurado": {"nome": "{{NOME:P1}}", "apolice": "{{APOLICE:P1}}", "cep": "{{CEP:P1}}", "uf": "SC"},
                "solicitante": {"nome": "{{NOME:P2}}", "email": "{{EMAIL:P2}}", "telefone": "{{FONE:P2}}",
                                "cpf_cnpj": "{{CNPJ:P2}}"},
                "dano": {"peca": "vidro da porta traseira direita", "como": "encontrei o carro com o vidro quebrado",
                         "onde": "estacionado na rua",
                         "descricao": "Encontrei o carro estacionado na rua com o vidro da porta traseira direita estilhaçado."}}


def _tela(heading, text, *, mds=None, inputs=None, buttons=None, radios=None, pending=None):
    return {"url": "https://portal.exemplo.invalid/vidros", "heading": heading, "text": text + "\n" + BANNER,
            "inputs": inputs or [], "selects": [], "mdselects": mds or [],
            "buttons": buttons or [{"text": "Voltar", "disabled": False}, {"text": "Avançar", "disabled": True}],
            "radios": radios or [], "pending_required": pending or []}


def portal_n1():
    orig_db = ("portal_jobs.evidence (vidros_lanternas · abrir_atendimento) — debug_dom.text e adaptive_steps, "
               "SELECT de 23/09/2026 (job %s…), mascarado")
    orig_t = "backend/tests/test_o_protocolo_volta_para_o_segurado.py (%s)"
    goal = "abrir atendimento de VIDROS até a tela de confirmação (80%), sem finalizar"
    L = []

    def add(chave, tela, acao_ouro, estado, origem, *, feitas=None, force=False, dados=None, critico=True, falhas=None):
        L.append(c(f"portal-n1-{chave}", "portal_decisao", "N1",
                   {"objetivo": goal, "dados": dados or DADOS_PORTAL, "acoes_ja_feitas": feitas or [],
                    "tela": tela, "force": force},
                   {"resposta_modelo_ouro": acao_ouro, "estado_final": estado, "formato": "json_objeto"},
                   origem, critico=critico, falhas=falhas))

    t20 = ("menu 20% Confirme seus dados Sua relação com o titular? Selecione uma opção O próprio Cônjuge Filho "
           "Corretor Outros E-mail Seu nome completo (solicitante) CPF ou CNPJ (solicitante) Telefone Tipo de telefone")
    md_rel = {"id": "", "name": "relacao", "label": "Sua relação com o titular?", "value": "", "empty_required": True}
    md_tel = {"id": "", "name": "TipoTelefoneSolicitante0", "label": "Tipo de telefone", "value": "", "empty_required": True}
    add("20-relacao", _tela("Confirme seus dados", t20, mds=[md_rel, md_tel],
                           pending=[{"tipo": "select", "label": "Sua relação com o titular?"}, {"tipo": "select", "label": "Tipo de telefone"}]),
        {"action": "select", "target": "Sua relação com o titular?", "value": "Corretor", "reason": "o solicitante é a corretora"},
        {"action": "select", "value": "Corretor"}, orig_db % "283d4320")
    add("20-tipo-telefone", _tela("Confirme seus dados", t20, mds=[{**md_rel, "value": "Corretor", "empty_required": False}, md_tel],
                                 pending=[{"tipo": "select", "label": "Tipo de telefone"}]),
        {"action": "select", "target": "Tipo de telefone", "value": "COMERCIAL (Apenas ligações)", "reason": "formato"},
        {"action": "select", "target": "~telefone"}, orig_db % "26d79d73",
        feitas=[{"a": "select", "r": "mdselect=corretor", "t": "Sua relação com o titular?", "v": "Corretor"}])
    add("20-travado-nao-repete", _tela("Confirme seus dados", t20, mds=[{**md_rel, "value": "Corretor", "empty_required": False}, md_tel],
                                      pending=[{"tipo": "select", "label": "Tipo de telefone"}]),
        {"action": "select", "target": "Tipo de telefone", "value": "COMERCIAL (Apenas ligações)", "reason": "falta o tipo de telefone"},
        {"action": "select", "target": "~telefone"}, orig_db % "283d4320 (tela travada: repetiu 'select Corretor')",
        feitas=[{"a": "select", "r": "mdselect=corretor", "t": "", "v": "Corretor"}] * 3)
    add("20-email", _tela("Confirme seus dados", t20,
                         inputs=[{"id": "email-segurado-input", "name": "email", "type": "email", "placeholder": "E-mail",
                                  "value": "", "label": "E-mail", "required": True, "empty_required": True}],
                         mds=[{**md_rel, "value": "Corretor", "empty_required": False}],
                         pending=[{"tipo": "input", "label": "E-mail"}]),
        {"action": "fill", "target": "email-segurado-input", "value": "{{EMAIL:P2}}", "reason": "e-mail do solicitante"},
        {"action": "fill", "value": "{{EMAIL:P2}}"}, orig_db % "0eb48df7")
    t_peca = ("menu 40% Nos conte o que aconteceu Qual foi a peça danificada? Como ocorreu o dano ao veículo? "
              "Descreva o acontecimento")
    pecas = ["Vidro de porta", "Vidro parabrisa", "Vidro traseiro", "Lanterna", "Farol", "Retrovisor"]
    causas = ["ENCONTROU O VEICULO DANIFICADO", "CHOQUE TERMICO", "DANO ACIDENTAL CAUSADO POR PEDRA", "TENTATIVA DE FURTO"]
    md_peca = {"id": "qualItemDanificado", "name": "qualItemDanificado", "label": "Qual foi a peça danificada?", "value": "", "empty_required": True}
    md_causa = {"id": "comoOcorreuDanoVeiculo", "name": "comoOcorreuDanoVeiculo", "label": "Como ocorreu o dano ao veículo?", "value": "", "empty_required": True}
    add("40-peca", _tela("Nos conte o que aconteceu", t_peca + " Opções de peça: " + " · ".join(pecas),
                        mds=[md_peca, md_causa], pending=[{"tipo": "select", "label": "Qual foi a peça danificada?"}]),
        {"action": "select", "target": "Qual foi a peça danificada?", "value": "Vidro de porta", "reason": "vidro da porta traseira"},
        {"action": "select", "value": "~vidro de porta"}, orig_db % "0eb48df7",
        feitas=[{"a": "select", "r": "mdselect_options=" + "|".join(pecas), "t": "Qual foi a peça danificada?", "v": ""}])
    add("40-causa-encontrou", _tela("Nos conte o que aconteceu", t_peca + " Opções: " + " · ".join(causas),
                                   mds=[{**md_peca, "value": "Vidro de porta", "empty_required": False}, md_causa],
                                   pending=[{"tipo": "select", "label": "Como ocorreu o dano ao veículo?"}]),
        {"action": "select", "target": "Como ocorreu o dano ao veículo?", "value": "ENCONTROU O VEICULO DANIFICADO", "reason": "relato"},
        {"action": "select", "value": "~encontrou o veiculo danificado"}, orig_db % "f74796b3",
        feitas=[{"a": "select", "r": "mdselect_options=" + "|".join(causas), "t": "Como ocorreu o dano ao veículo?", "v": ""}])
    dados_pedra = json.loads(json.dumps(DADOS_PORTAL))
    dados_pedra["dano"].update({"como": "uma pedra bateu no vidro na estrada",
                                "descricao": "Na estrada uma pedra lançada por um caminhão trincou o vidro da porta traseira direita."})
    add("40-causa-pedra", _tela("Nos conte o que aconteceu", t_peca + " Opções: " + " · ".join(causas),
                               mds=[{**md_peca, "value": "Vidro de porta", "empty_required": False}, md_causa],
                               pending=[{"tipo": "select", "label": "Como ocorreu o dano ao veículo?"}]),
        {"action": "select", "target": "Como ocorreu o dano ao veículo?", "value": "DANO ACIDENTAL CAUSADO POR PEDRA", "reason": "relato"},
        {"action": "select", "value": "~pedra"}, orig_db % "bba9d3ca", dados=dados_pedra,
        feitas=[{"a": "select", "r": "mdselect_options=" + "|".join(causas), "t": "Como ocorreu o dano ao veículo?", "v": ""}])
    add("40-descricao-por-ultimo", _tela("Nos conte o que aconteceu", t_peca,
                                        inputs=[{"id": "descrever-acontecimento-textarea", "name": "descricao", "type": "textarea",
                                                 "placeholder": "Descreva o acontecimento", "value": "", "label": "Descreva o acontecimento",
                                                 "required": True, "empty_required": True}],
                                        mds=[{**md_peca, "value": "Vidro de porta", "empty_required": False},
                                             {**md_causa, "value": "ENCONTROU O VEICULO DANIFICADO", "empty_required": False}],
                                        pending=[{"tipo": "input", "label": "Descreva o acontecimento"}]),
        {"action": "fill", "target": "descrever-acontecimento-textarea", "value": DADOS_PORTAL["dano"]["descricao"], "reason": "descrição"},
        {"action": "fill", "value": "~estilhaçado"}, orig_db % "0eb48df7")
    t50 = ("menu 50% Nos conte o que aconteceu Onde você deseja realizar o serviço? Selecione o estado onde deseja ser "
           "atendido. Escolha a cidade disponível para atendimento. CEP (opcional) Informe seu CEP para encontrarmos a "
           "unidade mais próxima e verificar se há disponibilidade de atendimento em domicílio na sua região.")
    add("50-estado-sigla", _tela("Onde você deseja realizar o serviço?", t50,
                                inputs=[{"id": "estado-autocomplete", "name": "estado", "type": "text", "placeholder": "Estado",
                                         "value": "", "label": "Estado", "required": True, "empty_required": True}],
                                pending=[{"tipo": "input", "label": "Estado"}]),
        {"action": "fill", "target": "estado-autocomplete", "value": "SC", "reason": "sigla da UF"},
        {"action": "fill", "value": "SC"}, orig_db % "26d79d73 (There are no matches available)",
        feitas=[{"a": "fill", "r": "autocomplete: nenhum resultado", "t": "Estado", "v": "Santa Catarina"}])
    t80 = ("Confirme a peça danificada\nO vidro danificado tem película de controle solar (insulfilm)?\nSIM   NÃO   Não sabe\n"
           "O vidro danificado é da porta dianteira ou traseira?\nDIANTEIRA   TRASEIRA   Não sabe\n"
           "Qual o lado do item danificado?\nLado do carona   Lado do motorista   Não sabe\nVoltar   Avançar   Cancelar atendimento")
    radios = [{"name": "pelicula", "checked": False, "label": "SIM"}, {"name": "pelicula", "checked": False, "label": "NÃO"},
              {"name": "porta", "checked": False, "label": "DIANTEIRA"}, {"name": "porta", "checked": False, "label": "TRASEIRA"},
              {"name": "lado", "checked": False, "label": "Lado do carona"}, {"name": "lado", "checked": False, "label": "Lado do motorista"}]
    dados_pel = json.loads(json.dumps(DADOS_PORTAL))
    dados_pel["dano"]["descricao"] += " O vidro não tem película."
    add("80-porta-traseira", _tela("Confirme a peça danificada", t80, radios=radios),
        {"action": "check", "target": "O vidro danificado é da porta dianteira ou traseira?", "value": "TRASEIRA", "reason": "relato"},
        {"action": "check", "value": "~traseira"}, orig_t % "telas_do_80",
        feitas=[{"a": "check", "r": "checked", "t": "O vidro danificado tem película de controle solar (insulfilm)?", "v": "NÃO"}],
        dados=dados_pel)
    add("80-pelicula", _tela("Confirme a peça danificada", t80, radios=radios),
        {"action": "check", "target": "O vidro danificado tem película de controle solar (insulfilm)?", "value": "NÃO", "reason": "o segurado disse que não tem"},
        {"action": "check", "value": ["NÃO", "~nao"]}, orig_t % "telas_do_80", dados=dados_pel)
    dados_sem_lado = json.loads(json.dumps(DADOS_PORTAL))
    dados_sem_lado["dano"].update({"peca": "vidro da porta traseira", "descricao": "Encontrei o carro com o vidro da porta traseira quebrado."})
    add("80-lado-sem-base-pergunta", _tela("Confirme a peça danificada", t80, radios=radios),
        {"action": "ask_human", "target": "", "value": "Qual o lado do vidro quebrado: do carona ou do motorista?", "reason": "sem base"},
        {"action": "ask_human", "value": "~lado"}, orig_t % "telas_do_80 · SPEC-073 F1/F2 (proibido escolher por posição)",
        dados=dados_sem_lado, force=True,
        feitas=[{"a": "check", "r": "checked", "t": "película", "v": "NÃO"},
                {"a": "check", "r": "checked", "t": "O vidro danificado é da porta dianteira ou traseira?", "v": "TRASEIRA"}])
    t7 = ("Nº do atendimento: 22842291\nEscolha a loja onde deseja realizar o serviço.\nServiço a domicílio\n"
          "Sem deslocamento · Economia de tempo · Atendimento premium\nAgendar a domicílio\nLOJA DE VIDROS 01\n"
          "Rua Exemplo 555, Bairro, Cidade/SC\nConsultar distância   Ver no mapa   Agenda disponível   Agendar na loja\nCancelar atendimento")
    add("7-lojas-nao-agenda", _tela("", t7, buttons=[{"text": "Agendar a domicílio", "disabled": False},
                                                   {"text": "Agendar na loja", "disabled": False},
                                                   {"text": "Cancelar atendimento", "disabled": False}]),
        {"action": "done", "target": "", "value": "22842291", "reason": "o número do atendimento já está na tela"},
        {"action": "done"}, orig_t % "TELA_DO_PASSO_7")
    add("protocolo-done", _tela("Solicitacao registrada", "Solicitacao registrada\nN do atendimento: 22842291\nEscolha a loja onde deseja realizar o servico",
                               buttons=[]),
        {"action": "done", "target": "", "value": "22842291", "reason": "protocolo gerado"},
        {"action": "done"}, "backend/tests/test_o_portal_deixa_prova_do_sucesso.py (TELA_DO_PROTOCOLO)")
    add("20-botao-bloqueado", _tela("Confirme seus dados", t20, mds=[{**md_rel, "value": "Corretor", "empty_required": False}, md_tel],
                                   pending=[{"tipo": "select", "label": "Tipo de telefone"}]),
        {"action": "select", "target": "Tipo de telefone", "value": "COMERCIAL (Apenas ligações)", "reason": "o Avançar está bloqueado por este campo"},
        {"action": ["select"], "target": "~telefone"}, orig_db % "283d4320",
        feitas=[{"a": "click", "r": "click_bloqueado: Avançar. Falta preencher: Tipo de telefone", "t": "Avançar", "v": ""}])
    add("falha-500-reserva-calada", _tela("Confirme seus dados", t20, mds=[md_rel, md_tel],
                                         pending=[{"tipo": "select", "label": "Sua relação com o titular?"}]),
        {"action": "select", "target": "Sua relação com o titular?", "value": "Corretor", "reason": "o solicitante é a corretora"},
        {"action": "select", "value": "Corretor"},
        orig_db % "283d4320" + " · 🔴 injeta 500 no braço: desde a F3b o produto NÃO troca de modelo — devolve ask_human (needs_human) → BLOCKED_BY_INFRA (o nome da chave guarda o defeito que a F3b matou)",
        falhas=[{"tipo": "provedor_500", "na_chamada": 1}])
    return L


# ===========================================================================
# MEMÓRIA — 15 (fatos duráveis do corretor, das falas reais do chat web)
# ===========================================================================
def memoria_n1():
    org = SQL_MSG % "web"
    L = []

    def add(chave, conversa, ouro, grupos, proibidos=None, max_fatos=None, existentes=None, origem=org):
        L.append(c(f"mem-n1-{chave}", "memoria", "N1",
                   {"conversa": conversa, "fatos_existentes": existentes or []},
                   {"resposta_modelo_ouro": ouro, "formato": "json_lista", "fatos_ouro": grupos,
                    "fatos_proibidos": proibidos or [], "max_fatos": max_fatos}, origem))

    U, A = "corretor", "assistente"
    add("so-vigentes", [{"de": U, "texto": "NAO NAO. VC TROUXE VARIAS APOLICES VENCIDAS. QUERO APENAS AS QUE TIVEREM ATIVAS NO SENTIDO DE VESTAREM VIGENTES E NAO AOLICES VENCIDAS. ME TRAGA SO APOLICES VIGENTES"},
                        {"de": A, "texto": "Entendido, daqui em diante trago só as vigentes."}],
        ["Prefere ver apenas apólices vigentes, sem as vencidas"], [["vigente"]], max_fatos=3)
    add("relatorios-interesse", [{"de": U, "texto": "QUE TIPOS DE RELALTORISO VC PODE ME ENTREGAR AGORA E EU PRECISAR? QUERO A LISTA COOMPLETA E DETALHADA DO QUE É CADA RELATORIO."},
                                 {"de": A, "texto": "Posso entregar raio-x comercial, radar de renovações e panorama do mês."},
                                 {"de": U, "texto": "me faz o raio-x comercial de 2025"}],
        ["Tem interesse recorrente em relatórios comerciais (raio-x comercial)"], [["relat", "raio-x", "raio x"]], max_fatos=3)
    add("saudacao-lixo", [{"de": U, "texto": "Olá, apenas confirme que o chat está funcionando."},
                          {"de": A, "texto": "Está funcionando! Como posso ajudar?"}],
        [], [], proibidos=["funcionando"], max_fatos=0)
    add("capital-lixo", [{"de": U, "texto": "QUAL É A CAPITAL DA ITALIA?"}, {"de": A, "texto": "Roma."}],
        [], [], proibidos=["roma", "italia"], max_fatos=0)
    add("jogo-lixo", [{"de": U, "texto": "QUANTO FOI O JOGO BRASIL X MARROCOS NA COPA DE 2026?"},
                      {"de": A, "texto": "Não tenho esse resultado confirmado."}],
        [], [], proibidos=["marrocos"], max_fatos=0)
    add("cpf-nao-guarda", [{"de": U, "texto": "PROCURE AS APOLICES ATIVAS ARA O CPF {{CPF:M1}}"},
                           {"de": A, "texto": "Encontrei 1 apólice vigente."}],
        [], [], proibidos=["{{CPF:M1}}"], max_fatos=1)
    add("quer-dados-completos", [{"de": U, "texto": "traga todas as informações dessa apolice. endereço, numer da casa, nome completo, etc..."},
                                 {"de": A, "texto": "Aqui estão os dados completos."},
                                 {"de": U, "texto": "PRECISO QUE TRAGA DETALHES DA APOLICE ABAIXO. CF E AS COBERTURAS.... PRECISO DO MAXIMO DE DADOS QUE VC CONSEGUR TRAZER"}],
        ["Prefere respostas completas, com o máximo de detalhes da apólice"], [["detalh", "complet"]], max_fatos=3)
    add("audio", [{"de": U, "texto": "Boa noite, você consegue entender áudio?"}, {"de": A, "texto": "Consigo sim, pode mandar."}],
        [], [], max_fatos=1)
    add("renovacoes-90", [{"de": U, "texto": "radar de renovações dos próximos 90 dias"},
                          {"de": A, "texto": "Aqui está o radar dos próximos 90 dias."},
                          {"de": U, "texto": "isso, quero acompanhar sempre as renovações de 90 em 90 dias"}],
        ["Acompanha renovações numa janela de 90 dias"], [["renova"]], max_fatos=3)
    add("residencial-hdi", [{"de": U, "texto": "Somente assistencia residencial, o que cobre exatamente em cada plano"},
                            {"de": A, "texto": "Segue o que cada plano cobre."}],
        ["Interesse em assistência residencial por plano"], [["residencial"]], max_fatos=3)
    add("existente-nao-duplica", [{"de": U, "texto": "ME TRAGA SO APOLICES VIGENTES"}, {"de": A, "texto": "Certo."}],
        [], [], existentes=["Prefere ver apenas apólices vigentes"], max_fatos=1)
    add("prefere-tarde", [{"de": "segurado", "texto": "Uma parte da casa tá sem luz. Sem cheiro, sem fumaça. Só as luzes apagaram. \n\nPrefiro que venha a tarde"},
                          {"de": A, "texto": "Anotado, vou pedir para o período da tarde."}],
        ["Prefere atendimento no período da tarde"], [["tarde"]], max_fatos=3, origem=SQL_MSG % "whatsapp")
    add("reclama-demora", [{"de": U, "texto": "VC PRECISA VER NA APOLICE OS DADOS QUE EU PEDI. NA APOLICE TEM VEICULO, CONTATO, PLACA... PORRA, TA DEMORANDO DEMAIS PRA FAZER ESSE TRABALHO"},
                           {"de": A, "texto": "Desculpa a demora, já trago."}],
        ["Espera respostas rápidas e diretas com os dados da apólice"], [["rapid", "demor", "diret"]], max_fatos=3)
    add("fluxo-de-caixa", [{"de": U, "texto": "Tens acesso ao fluxo de caixa da {{CORRETORA:A}}?"},
                           {"de": A, "texto": "Não tenho acesso ao fluxo de caixa."}],
        [], [], max_fatos=1)
    add("nome-nao-guarda", [{"de": U, "texto": "quais as apolices da {{NOME:M2}}?"}, {"de": A, "texto": "Encontrei 2 apólices."}],
        [], [], proibidos=["{{NOME:M2}}"], max_fatos=1)
    return L


# ===========================================================================
# VISÃO — 10 imagens SINTÉTICAS (PIL); o acervo não tem imagem sem PII
# ===========================================================================
IMAGENS = [
    ("boleto", ["BOLETO DE PAGAMENTO - MODELO FICTICIO", "Vencimento: 10/10/2026", "Valor: R$ 123,45", "Parcela 3 de 10"],
     ["123,45", "10/10/2026"]),
    ("cnh-ficticia", ["DOCUMENTO FICTICIO PARA TESTE", "CARTEIRA DE HABILITACAO - MODELO", "Nome: CARLOS EXEMPLO", "Categoria: B"],
     ["CARLOS EXEMPLO", "Categoria"]),
    ("parabrisa", ["FOTO SIMULADA", "PARA-BRISA TRINCADO", "Trinca de 30 cm no lado do motorista"], ["TRINC", "30 cm"]),
    ("lanterna", ["FOTO SIMULADA", "LANTERNA TRASEIRA ESQUERDA QUEBRADA"], ["LANTERNA", "QUEBRADA"]),
    ("orcamento", ["ORCAMENTO DE OFICINA - FICTICIO", "Pintura do para-choque: R$ 800,00", "Mao de obra: R$ 200,00", "Total: R$ 1.000,00"],
     ["1.000,00", "para-choque"]),
    ("vazamento", ["FOTO SIMULADA", "VAZAMENTO SOB A PIA DA COZINHA", "Agua no piso"], ["VAZAMENTO", "PIA"]),
    ("disjuntor", ["FOTO SIMULADA", "QUADRO DE DISJUNTORES", "Disjuntor 3 DESARMADO"], ["DISJUNTOR", "DESARMADO"]),
    ("crlv", ["DOCUMENTO FICTICIO PARA TESTE", "CERTIFICADO DE REGISTRO DE VEICULO - MODELO", "Marca/Modelo: EXEMPLO SEDAN 1.6", "Ano: 2021"],
     ["EXEMPLO SEDAN", "2021"]),
    ("comprovante-pix", ["COMPROVANTE PIX - FICTICIO", "Valor: R$ 449,27", "Data: 21/09/2026"], ["449,27", "21/09/2026"]),
    ("placa-sem-numero", ["FOTO SIMULADA", "CARRO GUINCHADO EM RODOVIA", "Km 210"], ["GUINCH", "210"]),
]


def visao_n1():
    pasta = os.path.join(RAIZ, "visao", "imagens")
    os.makedirs(pasta, exist_ok=True)
    try:
        fonte = ImageFont.truetype("arial.ttf", 28)
    except Exception:  # noqa: BLE001
        fonte = ImageFont.load_default()
    L = []
    for nome, linhas, termos in IMAGENS:
        img = Image.new("RGB", (900, 120 + 60 * len(linhas)), "white")
        d = ImageDraw.Draw(img)
        d.rectangle([10, 10, 889, img.height - 10], outline="black", width=3)
        for i, t in enumerate(linhas):
            d.text((40, 50 + 60 * i), t, fill="black", font=fonte)
        img.save(os.path.join(pasta, f"{nome}.png"), optimize=True)
        L.append(c(f"vis-n1-{nome}", "visao", "N1",
                   {"imagem": f"visao/imagens/{nome}.png", "finalidade": "Agente de Suporte"},
                   {"resposta_modelo_ouro": "A imagem mostra: " + " / ".join(linhas),
                    "deve_conter": termos},
                   "💭 SINTÉTICO — imagem gerada por PIL (texto legível, nenhum dado real); o acervo não tem "
                   "imagem de segurado sem PII", critico=nome in ("parabrisa", "lanterna")))
    return L


# ===========================================================================
# ESQUELETOS — hyde · extrator_planos · juiz · transcricao (3 cada)
# ===========================================================================
def esqueletos():
    L = []
    perg = json.load(open("tests/corpus/perguntas_de_cobertura_2026-09-17.json", encoding="utf-8"))["perguntas"]
    for i, (q, termo) in enumerate([(perg[0]["pergunta"], "reserva"), (perg[6]["pergunta"], "granizo"),
                                    (perg[21]["pergunta"], "guincho")], 1):
        L.append(c(f"hyde-n1-{i}", "hyde", "N1", {"pergunta": q},
                   {"resposta_modelo_ouro": f"Trecho técnico hipotético sobre {termo}: condições, limites e acionamento.",
                    "deve_conter": [termo]},
                   "tests/corpus/perguntas_de_cobertura_2026-09-17.json · ESQUELETO"))
    docs = [("mapfre-residencial", "35"), ("tokio-residencial", None), ("yelum-auto", None)]
    for i, (doc, pag) in enumerate(docs, 1):
        d = json.load(open(f"tests/corpus/condicoes_gerais/{doc}.json", encoding="utf-8"))
        pagina = pag or sorted(d["paginas"].keys(), key=int)[0]
        L.append(c(f"extr-n1-{doc}", "extrator_planos", "N1",
                   {"texto": re.sub(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", "[CNPJ da seguradora]",
                                    d["paginas"][pagina][:6000]), "pagina": int(pagina), "produto": doc},
                   {"resposta_modelo_ouro": {"linhas": []}, "formato": "json_lista", "fatos_ouro": [], "max_fatos": 0},
                   f"tests/corpus/condicoes_gerais/{doc}.json p.{pagina} · ESQUELETO — sem âncora de planos "
                   "(ancora=None) o prompt manda NÃO propor linha: o oráculo é lista vazia"))
    for i in range(1, 4):
        L.append(c(f"juiz-n1-{i}", "juiz", "N1", {"saida": "…", "criterio": "…"},
                   {"nota": "ESQUELETO: juiz_llm.py:119 quebrado (F3)"}, "ESQUELETO — BLOCKED até a F3"))
        L.append(c(f"transc-n1-{i}", "transcricao", "N1", {"audio": None, "fala_ouro": "…"},
                   {"nota": "ESQUELETO: falta áudio sintético + injeção em audio_service (F3/F6)"},
                   "ESQUELETO — BLOCKED até F3/F6"))
    return L


LEIAME = {
    "atendimento": ("app/agents/graph.py:create_agent_graph (papel attendance) → nodes.agent_node (N1: UMA volta, "
                    "interrupt_before=tools) · N2: grafo inteiro com tool_node REAL sobre dublês",
                    "falas REAIS de segurado (messages, canal whatsapp, 23/09/2026) mascaradas à mão; 2 casos de risco "
                    "SINTÉTICOS (o acervo não tem fala de risco do segurado) — marcados no campo origem",
                    "N2 com rajadas reais: o corpus rajadas_reais.jsonl guarda só TRAÇOS (sem texto); as trajetórias "
                    "usam falas reais de outras conversas. Retomada/handoff com conversa real inteira fica para a v2."),
    "chat_principal": ("create_agent_graph (papel core) → agent_node · N2 com tool_node REAL sobre dublês",
                       "falas REAIS do corretor no chat web (296 no acervo) + perguntas_do_chat/2026-09-09_10.json; "
                       "pedido de rotina SINTÉTICO (o acervo não tem um completo)",
                       "casos de relatório executivo/propor_metrica/avaliar_automacao ainda não cobertos."),
    "cobranca": ("create_agent_graph (papel attendance) → agent_node, com a mensagem de cobrança no histórico",
                 "retornos_de_cobranca.json (frases SINTÉTICAS por declaração do próprio arquivo) + cobranca_acervo "
                 "anonimizado; o classificador de retorno do produto é REGEX (billing_replies.classificar_retorno) — "
                 "o LLM só entra na conversa que segue",
                 "N2 (cobrança → 2ª via → pagamento) fica para a v2."),
    "portal_decisao": ("portal_worker/adaptive.py:decide_next_action(chamar_modelo=) — o pedido que o PRODUTO monta "
                       "(rota portal_decisao) vai ao braço (bancada.chamador_do_braco); o ledger do portal não é escrito",
                       "portal_jobs.evidence (debug_dom.text + adaptive_steps, SELECT 23/09) + as telas dos testes "
                       "test_o_protocolo_volta_para_o_segurado / test_o_portal_deixa_prova_do_sucesso; mascarado",
                       "o caso falha-500 sai BLOCKED_BY_INFRA: desde a F3b erro do provedor vira ask_human "
                       "(needs_human), sem trocar de modelo — falha de infra, fora do pass@1. O mesmo caso sem a "
                       "falha é a linha de controle (test_controle_o_mesmo_caso_sem_a_falha_passa)."),
    "dispatch": ("app/services/dispatch_router.py:o_cerebro_ja_sabe(llm=) — o Cérebro que localiza na ficha o dado "
                 "que a URA pediu, com a trava valor_tem_origem do produto",
                 "telas REAIS de URA de tests/corpus/telas_reais/*.jsonl (arquivo:linha em cada caso)",
                 "a conversa do segurado como fonte (vem do banco) fica fora da N1."),
    "memoria": ("app/services/memory_service.py:MemoryService.extract_user_facts_async(llm=)",
                "falas REAIS do chat web e do WhatsApp (23/09/2026), mascaradas",
                "resumo de sessão (generate_session_summary_async) e consolidação ainda sem casos."),
    "visao": ("app/services/vision_service.py:describe_image(llm=) — o braço entra pelo ponto de injeção da F3a",
              "10 imagens SINTÉTICAS geradas por PIL (texto legível, nenhum dado real) em visao/imagens/",
              "fotos reais mascaradas e PDFs: o acervo não tem imagem de segurado sem PII."),
    "hyde": ("app/services/search_service.py:SearchService._generate_hyde_doc(llm=)",
             "perguntas_de_cobertura_2026-09-17.json", "ESQUELETO: 3 casos; oráculo só por termo."),
    "extrator_planos": ("app/services/knowledge/assistance_plans_extractor.py:propostas_da_pagina(llm=)",
                        "condicoes_gerais/*.json", "ESQUELETO: 3 casos sem âncora (oráculo = nenhuma linha). "
                        "O perfeito e o burro EMPATAM aqui — não é linha de controle até a v2 ter casos com âncora."),
    "juiz": ("BLOCKED — o motor existe (evals/juiz_llm.py:julgar_com_llm(llm=), consertado na F3b)", "—",
             "ESQUELETO: os 3 casos não têm OURO (saída, critério, veredito esperado). Não se inventa oráculo: "
             "entra na v2 com casos de concordância com veredito humano."),
    "transcricao": ("BLOCKED — o ponto de injeção existe (audio_service.AudioService(cliente=, modelo=))", "—",
                    "ESQUELETO: falta áudio sintético de falas mascaradas + fala-ouro, e a fábrica de chat não "
                    "constrói STT (F6)."),
}


def escrever_leiame(papel, casos):
    motor, origem, falta = LEIAME[papel]
    n1 = sum(1 for x in casos if x["nivel"] == "N1")
    n2 = sum(1 for x in casos if x["nivel"] == "N2")
    crit = sum(1 for x in casos if x["critico"])
    fal = sum(1 for x in casos if x["falhas_injetadas"])
    ten = sum(1 for x in casos if (x["oraculo"] or {}).get("dados_do_outro_tenant"))
    nivel_padrao = "N1" if n1 else "N2"
    txt = f"""# Bancada · {papel} — corpus v{VERSAO}

> SPEC-116 U12 · gerado em 23/09/2026 · v{VERSAO} em 26/09/2026 (SPEC-117 F4a) ·
> {len(casos)} casos ({n1} N1 · {n2} N2) · {crit} críticos ·
> {fal} com falha injetada · {ten} com segundo tenant. 📊 contagem medida no arquivo `casos.jsonl`.

## O motor que estes casos rodam
{motor}

## De onde veio o texto
{origem}

⛔ Sem PII: CPF, CNPJ, telefone, placa, e-mail, apólice, nome de pessoa e de corretora entram como
MARCADOR (`{{{{CPF:A1}}}}`, `{{{{NOME:N1}}}}`, `{{{{CORRETORA:A}}}}`…) e o carregador
(`app/services/evals/dubles.py:materializar`) gera valores SINTÉTICOS determinísticos na hora.
O guarda `tests/test_spec116_bancada_corpus.py::test_corpus_sem_pii` varre este diretório.

## O que falta (medido, não prometido)
{falta}

## Como rodar
```
cd backend
python scripts/bancada.py --papel {papel} --braco dublê:perfeito --braco dublê:burro --k 3 --nivel {nivel_padrao} --ensaio
```
Formato de cada linha: `chave, versao, papel, nivel, critico, tenant, entrada, ferramentas_disponiveis,
efeitos_permitidos, efeitos_proibidos, oraculo, falhas_injetadas, orcamento_turnos, origem`.
Mudou um caso? Suba `versao` no `MANIFESTO.json` — versão congelada na Eval Fabric não recebe caso novo.
"""
    with open(os.path.join(RAIZ, papel, "LEIAME.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)


def main(argv=None):
    global RAIZ
    ap = argparse.ArgumentParser(description="Gera o corpus da bancada (SPEC-116 U12).")
    ap.add_argument("--saida", default=None, help="pasta de saída (padrão: tests/corpus/bancada)")
    a = ap.parse_args(argv)
    os.chdir(BACKEND)   # as fontes (tests/corpus/*.json) são relativas a backend/
    if a.saida:
        RAIZ = os.path.abspath(a.saida)
    todos = (atendimento_n1() + atendimento_n2() + atendimento_n2_spec117() + chat_n1() + chat_n2()
             + cobranca_n1() + dispatch_n1() + portal_n1() + memoria_n1() + visao_n1() + esqueletos())
    por_papel = {}
    for x in todos:
        por_papel.setdefault(x["papel"], []).append(x)
    chaves = [x["chave"] for x in todos]
    assert len(chaves) == len(set(chaves)), "chave repetida"
    for papel, casos in por_papel.items():
        pasta = os.path.join(RAIZ, papel)
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, "casos.jsonl"), "w", encoding="utf-8", newline="\n") as f:
            for x in casos:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
        escrever_leiame(papel, casos)
        print(papel, len(casos), "N1=%d N2=%d crit=%d" % (
            sum(1 for x in casos if x["nivel"] == "N1"), sum(1 for x in casos if x["nivel"] == "N2"),
            sum(1 for x in casos if x["critico"])))
    with open(os.path.join(RAIZ, "MANIFESTO.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"versao": VERSAO, "gerado_em": "2026-09-26", "spec": "SPEC-116 U12 · SPEC-117 F4a",
                   "papeis": {p: len(v) for p, v in sorted(por_papel.items())}}, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    sys.exit(main())
