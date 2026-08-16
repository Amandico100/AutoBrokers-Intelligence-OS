# -*- coding: utf-8 -*-
"""SPEC-073 Bloco J — as 22 mutacoes que a implementacao PRECISA detectar.

O que uma matriz de mutacao prova, e o que ela nao prova
=======================================================
Ela nao prova que o worker funciona. Prova que os GUARDAS conseguem reprovar --
que existe um caminho pelo qual cada um deles fica vermelho. Um guarda que nao
tem como falhar nao guarda nada (CLAUDE.md §9.3).

Cada bloco abaixo faz a mesma coisa em tres tempos:

    1. o caso BOM passa      (senao o guarda esta travando trabalho legitimo)
    2. o caso RUIM e negado  (senao o guarda nao existe de fato)
    3. os dois SAO DIFERENTES (senao uma funcao que devolve sempre a mesma
       resposta passaria nos dois -- e e assim que um teste vira decoracao)

A LINHA DE CONTROLE, no fim do arquivo, e obrigatoria: ela prova que a SPEC-073
nao virou "nega tudo". Login continua permitido, consulta continua permitida,
download de PDF continua permitido, worker sem visao continua de pe.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from portal_worker import guardrails as G          # noqa: E402
from portal_worker import identidade as ID         # noqa: E402
from portal_worker import perception as P          # noqa: E402
from portal_worker import redaction as R           # noqa: E402
from portal_worker import runtime as RT            # noqa: E402
from portal_worker.journeys import (               # noqa: E402
    JOURNEYS, JourneyResult, get_journey, portais_com_cobranca)
from portal_worker.profiler import PortalProfiler  # noqa: E402

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:220] if extra else ""))


TELA = {
    "url": "https://portal/passo6",
    "heading": "Confirme a peca danificada",
    "inputs": [{"label": "Qual peca danificada", "id": "peca"},
               {"label": "Nome do solicitante", "id": "nome"}],
    "selects": [{"label": "Lado", "options": ["Motorista", "Carona"]}],
    "buttons": [{"text": "Voltar"}, {"text": "Confirmar"},
                {"text": "Agendar a domicilio"}, {"text": "Cancelar atendimento"}],
    "checkboxes": [{"label": "Desejo receber atualizacoes no WhatsApp"}],
}
DADOS = {"dano": {"peca": "vidro da porta", "lado": "motorista"},
         "segurado": {"nome": "FULANO DE TAL"}}


def guard(**kw):
    base = {"material_liberado": True, "acao_material_esperada": "confirmar"}
    base.update(kw)
    return G.PortalActionGuard(**base)


# ==========================================================================
print("\n[M01] discovery NAO pode permitir efeito material")
# ==========================================================================
ok_normal, _ = guard(discovery_mode=False).avaliar(G.MATERIAL_SIDE_EFFECT)
ok_disc, motivo_disc = guard(discovery_mode=True).avaliar(G.MATERIAL_SIDE_EFFECT)
check("fora do discovery, journey liberada PODE agir", ok_normal)
check("M01: em discovery, efeito material e negado", not ok_disc, motivo_disc)
check("M01 CONTROLE: os dois casos diferem", ok_normal != ok_disc)
check("discovery ainda permite LER", guard(discovery_mode=True).avaliar(G.READ_ONLY)[0])

# ==========================================================================
print("\n[M02] acao material sem checkpoint `armed` nao acontece")
# ==========================================================================
g = guard()
asyncio.run(g.before(action="create_attendance", action_class=G.MATERIAL_SIDE_EFFECT))
check("M02: `before` de acao material grava phase=armed ANTES do efeito",
      G.fase_do_efeito(g.evidence) == G.FASE_ARMED, g.evidence)
check("M02: o checkpoint tem fingerprint sem PII",
      bool((G.efeito_critico(g.evidence) or {}).get("fingerprint")))
g_ro = guard()
asyncio.run(g_ro.before(action="listar", action_class=G.READ_ONLY))
check("M02 CONTROLE: acao read-only NAO arma efeito alto",
      G.efeito_critico(g_ro.evidence) is None)

# ==========================================================================
print("\n[M03] stale com efeito INCERTO nao volta para `queued`")
# ==========================================================================
for fase in (G.FASE_ARMED, G.FASE_SUBMITTED, G.FASE_UNKNOWN):
    job = {"attempts": 0, "evidence": {"critical_effect": {"phase": fase}}}
    p = G.decidir_recuperacao(job, idade_segundos=9999, limite_segundos=1800)
    check(f"M03: fase={fase} nao volta para a fila",
          p and p["status"] == "needs_human", p)

# ==========================================================================
print("\n[M04] stale READ-ONLY continua sendo recuperado — o CONTROLE")
# ==========================================================================
ro = {"attempts": 0, "evidence": {"inadimplentes": [1, 2, 3]}}
p_ro = G.decidir_recuperacao(ro, idade_segundos=9999, limite_segundos=1800)
check("M04: job read-only orfao volta para `queued`, como antes",
      p_ro and p_ro["status"] == "queued", p_ro)
p_novo = G.decidir_recuperacao(ro, idade_segundos=10, limite_segundos=1800)
check("M04: job novo e deixado em paz", p_novo is None)
ro2 = {"attempts": 5, "evidence": {}}
p_ro2 = G.decidir_recuperacao(ro2, idade_segundos=9999, limite_segundos=1800)
check("M04: reincidente vira failed, como antes", p_ro2 and p_ro2["status"] == "failed")

# ==========================================================================
print("\n[M05/M06] company_id e portal_key da conta TEM de conferir")
# ==========================================================================
import inspect  # noqa: E402

from portal_worker import worker as W  # noqa: E402

fonte = inspect.getsource(W._run_job)
i_sel = fonte.find('table("portal_accounts")')
i_dec = fonte.find("vault.decrypt")
i_cid = fonte.find('.eq("company_id"', i_sel)
i_pk = fonte.find("tenant_or_portal_mismatch")
check("M05: o SELECT de portal_accounts filtra por company_id",
      i_sel != -1 and i_cid != -1 and i_cid > i_sel, (i_sel, i_cid))
check("M05 CONTROLE: o filtro vem ANTES de decifrar a credencial",
      i_cid < i_dec, (i_cid, i_dec))
check("M06: existe parada por portal_key divergente", i_pk != -1)
check("M06 CONTROLE: a parada tambem vem antes do decrypt", i_pk < i_dec, (i_pk, i_dec))

# ==========================================================================
print("\n[M07/M08/M09] Authorization, Cookie e PII nao entram em evidence")
# ==========================================================================
ARMADILHA = {
    "headers": {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.aaaaa.bbbbb",
                "Cookie": "session=abc123", "Accept": "application/json"},
    "body": {"cpf": "123.456.789-01", "placa": "QAB1A91",
             "email": "segurado@teste.com.br", "telefone": "(47) 98808-7463",
             "cnpj": "12.345.678/0001-99"},
    "texto": "o segurado 123.456.789-01 tem a placa ABC-1234 e mora no cep 89010-000",
}
limpo = R.redigir(ARMADILHA)
vaz_antes = R.tem_vazamento(ARMADILHA)
vaz_depois = R.tem_vazamento(limpo)
check("M07: Authorization nao sobrevive a redacao",
      "authorization" not in vaz_depois and "eyJ" not in str(limpo))
check("M08: Cookie nao sobrevive a redacao", "cookie" not in vaz_depois)
check("M09: CPF/placa/CNPJ/telefone/email/CEP nao sobrevivem", not vaz_depois, vaz_depois)
check("M07-09 CONTROLE: a armadilha REALMENTE continha os segredos",
      len(vaz_antes) >= 6, vaz_antes)
check("M07-09 CONTROLE: o campo continua existindo, so o valor sai",
      "Authorization" in limpo["headers"])
check("shape_of descreve a forma sem um dado real",
      R.shape_of({"cpf": "12345678901"}) == {"cpf": "<string:11>"})

# ==========================================================================
print("\n[M26] o redator NAO pode comer o payload de trabalho da cobranca")
# ==========================================================================
# 🔴 Esta secao existe por causa de uma REGRESSAO REAL, achada pelo canario
# P-186 rodando contra a Yelum em producao, em 16/08/2026.
#
# A primeira versao envolvia a evidencia INTEIRA em `redigir()`. Medido no job
# real: `inadimplentes[0].recibo` virou `<redacted:...>`.
#
# `recibo` e a chave estavel do item na fila, o nome do PDF no bucket
# (`boleto-{recibo}.pdf`) e a chave anti-duplicacao em `billing_sent_log`.
# Mascarado, TODA execucao concluiria que nada foi enviado -- e o segurado
# receberia a mesma cobranca de novo. A protecao teria produzido o pior
# desfecho do sistema.
#
# Nenhum dano ocorreu porque a rotina estava inativa. O canario pegou antes.
TRABALHO = {
    "inadimplentes": [{
        "recibo": "12345678-202608-3",          # formato Yelum: digitos com hifen
        "cpf_cnpj": "12345678901",
        "apolice_susep": "0553012345678",
        "numero_apolice": "0553012345678",
        "cliente_nome": "CLIENTE DE TESTE",
        "valor": 1825.34,
    }],
    "boletos": [{"recibo": "12345678-202608-3", "ok": True,
                 "storage_path": "c/p/j/boleto-12345678-202608-3.pdf"}],
    "login_fields_found": {"password": True, "username": True},
    # superficies de diagnostico — estas SIM tem de ser redigidas
    "profiler": {"trace": [{"v": "segurado 123.456.789-01 placa ABC1D23"}]},
    "discovery": {"recommendation": "o campo pediu 123.456.789-01"},
    "runtime": {"account_label": "principal"},
}
env = R.redigir_envelope(TRABALHO)
item = env["inadimplentes"][0]
for campo in ("recibo", "cpf_cnpj", "apolice_susep", "numero_apolice", "cliente_nome"):
    check(f"M26: `inadimplentes[].{campo}` passa INTACTO",
          item[campo] == TRABALHO["inadimplentes"][0][campo], item[campo])
check("M26: o recibo do BOLETO tambem passa intacto",
      env["boletos"][0]["recibo"] == "12345678-202608-3")
check("M26: e o storage_path, que aponta para o PDF no bucket",
      "<redacted" not in env["boletos"][0]["storage_path"])
check("M26: booleano sob chave sensivel nao e mascarado (nao carrega segredo)",
      env["login_fields_found"]["password"] is True)

# CONTROLE — o redator continua fazendo o trabalho dele nas superficies certas.
# Sem estas quatro, "nao quebrou a cobranca" e "nao redige mais nada" ficariam
# indistinguiveis, e a correcao teria desligado a protecao inteira.
check("M26 CONTROLE: o profiler CONTINUA sendo redigido",
      not R.tem_vazamento(env["profiler"]), env["profiler"])
check("M26 CONTROLE: o discovery CONTINUA sendo redigido",
      not R.tem_vazamento(env["discovery"]), env["discovery"])
check("M26 CONTROLE: e o PII de dentro deles some de verdade",
      "123.456.789-01" not in str(env["profiler"]) + str(env["discovery"]))
check("M26 CONTROLE: chave sensivel com valor STRING continua mascarada",
      R.redigir_envelope({"runtime": {"authorization": "Bearer abc"}})
      ["runtime"]["authorization"].startswith("<redacted"))

# E a prova de que o worker usa o envelope, nao o redator largo.
src_red = inspect.getsource(W._redigir)
check("M26: o worker chama `redigir_envelope`, nao `redigir` cru",
      "redigir_envelope" in src_red, src_red)

# ==========================================================================
print("\n[M10] visao propondo opcao INEXISTENTE nao e executada")
# ==========================================================================
v_falsa = P.validar_acao({"action": "select", "target": "Lado", "value": "Traseiro"},
                         TELA, collected=DADOS, guard=guard(), origem=P.L4_VISAO)
v_real = P.validar_acao({"action": "select", "target": "Lado", "value": "Motorista"},
                        TELA, collected=DADOS, guard=guard(), origem=P.L4_VISAO)
check("M10: opcao fora da lista real e recusada", not v_falsa.ok, v_falsa.motivo)
check("M10 CONTROLE: opcao que existe na lista passa", v_real.ok, v_real.motivo)
check("M10 CONTROLE: os dois vereditos diferem", v_falsa.ok != v_real.ok)

# ==========================================================================
print("\n[M11] visao NAO bypassa o guard num botao material")
# ==========================================================================
v_vis = P.validar_acao({"action": "click", "target": "Confirmar"}, TELA,
                       guard=guard(), origem=P.L4_VISAO)
v_jrn = P.validar_acao({"action": "click", "target": "Confirmar"}, TELA,
                       guard=guard(), origem="journey")
check("M11: visao nao executa 'Confirmar'", not v_vis.ok, v_vis.motivo)
check("M11 CONTROLE: a journey liberada executa 'Confirmar'", v_jrn.ok, v_jrn.motivo)
v_outro = P.validar_acao({"action": "click", "target": "Agendar a domicilio"}, TELA,
                         guard=guard(), origem="journey")
check("M11+: botao material DIFERENTE do declarado e recusado", not v_outro.ok, v_outro.motivo)
v_cancel = P.validar_acao({"action": "click", "target": "Cancelar atendimento"}, TELA,
                          guard=guard(), origem="journey")
check("M11+: 'Cancelar atendimento' e recusado", not v_cancel.ok)
v_sem = P.validar_acao({"action": "click", "target": "Confirmar"}, TELA,
                       guard=guard(acao_material_esperada=""), origem="journey")
check("M11+: sem a journey NOMEAR a acao, nenhum material passa", not v_sem.ok)

# ==========================================================================
print("\n[M12/M13] nenhuma regra generica manda escolher a PRIMEIRA opcao")
# ==========================================================================
import portal_worker.adaptive as A  # noqa: E402

txt_force = A._FORCE_CHOOSE.lower()
check("M12: `_FORCE_CHOOSE` nao contem mais 'primeira opcao valida'",
      "1a opcao valida" not in txt_force and "primeira opcao valida" not in txt_force,
      txt_force[:120])
check("M12 CONTROLE: ele ainda proibe a pergunta desnecessaria",
      "ask_human" in txt_force)
check("M13: ele proibe explicitamente escolher por POSICAO",
      "posicao" in txt_force and "proibido" in txt_force)
check("M13 CONTROLE: nomeia os campos criticos que nao se chuta",
      all(c in txt_force for c in ("peca", "lado", "cobertura", "horario")))

# 🔴 Estas quatro asserções nasceram de uma mutação que NÃO foi detectada.
# Ao quebrar de propósito o `_valor_conhecido` do validador, a matriz continuou
# 103/103 verde: eu testava o TEXTO do prompt e o campo não-crítico, e nunca
# tinha afirmado que um campo crítico com valor inventado é recusado. O prompt
# proibia, o código impedia, e o teste não olhava — que é como uma proteção
# real morre num refactor sem ninguém perceber.
v_inv = P.validar_acao({"action": "fill", "target": "peca", "value": "para-brisa"},
                       TELA, collected=DADOS, guard=guard())
v_lastro = P.validar_acao({"action": "fill", "target": "peca", "value": "vidro da porta"},
                          TELA, collected=DADOS, guard=guard())
check("M13: campo CRITICO com valor sem lastro no relato e recusado",
      not v_inv.ok, v_inv.motivo)
check("M13 CONTROLE: o mesmo campo com valor que o segurado disse passa",
      v_lastro.ok, v_lastro.motivo)
check("M13 CONTROLE: os dois vereditos diferem", v_inv.ok != v_lastro.ok)
v_chk = P.validar_acao({"action": "check", "target": "Desejo receber atualizacoes no WhatsApp"},
                       TELA, collected=DADOS, guard=guard())
check("M13: checkbox de consentimento/canal nunca e marcada por modelo",
      not v_chk.ok, v_chk.motivo)

# ==========================================================================
print("\n[M14] tres acoes sem progresso ESCALAM em vez de ir ate o teto")
# ==========================================================================
src = inspect.getsource(A.run_adaptive)
check("M14: existe contador de acoes recusadas", "_rejeitadas" in src)
check("M14: ele escala em 3, nao em MAX_STEPS", "_rejeitadas >= 3" in src)
check("M14 CONTROLE: a escalada devolve needs_human com motivo",
      "acao_recusada" in src)
hist = ["fill peca ok filled"]
v_rep = P.validar_acao({"action": "fill", "target": "peca", "value": "vidro da porta"},
                       TELA, collected=DADOS, historico=hist, guard=guard())
check("M14: repetir acao que ja deu certo e recusado", not v_rep.ok, v_rep.motivo)
v_new = P.validar_acao({"action": "fill", "target": "nome", "value": "FULANO DE TAL"},
                       TELA, collected=DADOS, historico=hist, guard=guard())
check("M14 CONTROLE: acao nova continua permitida", v_new.ok, v_new.motivo)

# ==========================================================================
print("\n[M15] provider de visao fora do ar NAO derruba o worker")
# ==========================================================================
class _ProviderQuebrado:
    async def decide(self, **kw):
        raise RuntimeError("provider fora do ar")


r_quebrado = asyncio.run(P.decidir_com_visao(_ProviderQuebrado(), imagem=b"x",
                                             state=TELA, goal="g", collected={}, history=[]))
check("M15: provider quebrado vira ask_human, nao excecao",
      r_quebrado.get("action") == "ask_human", r_quebrado)
r_sem = asyncio.run(P.decidir_com_visao(None, imagem=None, state=TELA, goal="g",
                                        collected={}, history=[]))
check("M15 CONTROLE: sem provider tambem degrada limpo",
      r_sem.get("action") == "ask_human")


class _ProviderOk:
    async def decide(self, **kw):
        return {"action": "click", "target": "Voltar"}


r_ok = asyncio.run(P.decidir_com_visao(_ProviderOk(), imagem=b"x", state=TELA,
                                       goal="g", collected={}, history=[]))
check("M15 CONTROLE: provider bom devolve a acao dele", r_ok.get("action") == "click")

# ==========================================================================
print("\n[M16/M17] o registry nao perde journey nem ganha lista paralela")
# ==========================================================================
ESPERADAS = ("allianz_corretor.cobranca_sweep", "hdi_corretor.cobranca_sweep",
             "tokiomarine_corretor.cobranca_sweep", "yelum_corretor.cobranca_sweep",
             "mapfre_corretor.cobranca_sweep", "zurich_corretor.cobranca_sweep",
             "vidros_lanternas.abrir_atendimento")
for chave in ESPERADAS:
    check(f"M16: `{chave}` continua registrada", chave in JOURNEYS)
    portal, jn = chave.split(".", 1)
    check(f"M16: `{chave}` resolve para uma funcao", callable(get_journey(portal, jn)))
cob = portais_com_cobranca()
check("M17: portais_com_cobranca continua com os 6 da baseline", len(cob) == 6, cob)
fonte_reg = inspect.getsource(sys.modules["portal_worker.journeys"])
i_def = fonte_reg.find("def portais_com_cobranca")
corpo = fonte_reg[i_def:i_def + 700]
check("M17: ele DERIVA do registry (usa o sufixo), nao uma lista literal",
      "JOURNEYS" in corpo and "allianz_corretor\"" not in corpo, corpo[:200])

# ==========================================================================
print("\n[M18] o JourneyResult antigo continua valendo")
# ==========================================================================
r_velho = JourneyResult(status="done")
check("M18: JourneyResult(status=...) sozinho continua construindo",
      r_velho.status == "done" and r_velho.captured == {} and r_velho.screenshots == [])
r_full = JourneyResult(status="needs_human", captured={"a": 1},
                       screenshots=["s"], message="m")
check("M18 CONTROLE: os 4 campos continuam aceitos",
      (r_full.status, r_full.captured, r_full.screenshots, r_full.message)
      == ("needs_human", {"a": 1}, ["s"], "m"))

# ==========================================================================
print("\n[M19] o profiler e PASSIVO — nao intercepta nem altera request")
# ==========================================================================
fonte_prof = inspect.getsource(PortalProfiler)
for proibido in ("page.route", "abort()", "fulfill(", "continue_("):
    check(f"M19: profiler nao usa `{proibido}`", proibido not in fonte_prof)
check("M19 CONTROLE: ele de fato ESCUTA eventos", 'page.on("response"' in fonte_prof)

# ==========================================================================
print("\n[M20] fixture/trace nao guardam HAR bruto")
# ==========================================================================
prof = PortalProfiler(portal_key="x", host_portal="portal.com.br")
prof.registrar_response(url="https://portal.com.br/api/x?cpf=12345678901",
                        method="POST", status=200,
                        content_type="application/json", resource_type="xhr")
prof.evento(layer="dom", action="fill", target="cpf", value="123.456.789-01")
resumo = prof.resumo()
check("M20: o resumo do profiler nao vaza PII",
      not R.tem_vazamento(resumo), R.tem_vazamento(resumo))
check("M20: nao existe corpo de request no artefato",
      "body" not in str(resumo) and "12345678901" not in str(resumo))
check("M20 CONTROLE: o profiler ainda registrou a chamada",
      resumo["requests_relevant"] == 1, resumo)
check("M20: o trace tem teto", len(prof.eventos) <= 80)
check("M20: RAW_TRACE nasce desligado", RT.raw_trace_enabled() is False)

# ==========================================================================
print("\n[M21] checkpoint nao pode ser escrito so no fim do job")
# ==========================================================================
gravacoes = []


async def _cap(patch):
    gravacoes.append(dict(patch))


g_cp = G.PortalActionGuard(material_liberado=True, _checkpoint=_cap)
asyncio.run(g_cp.before(action="create", action_class=G.MATERIAL_SIDE_EFFECT))
n_apos_armar = len(gravacoes)
asyncio.run(g_cp.submetido())
asyncio.run(g_cp.confirmado(receipt="22842291"))
check("M21: o `armed` foi gravado ANTES de qualquer submissao", n_apos_armar == 1,
      gravacoes)
check("M21: cada transicao grava (armed, submitted, confirmed)", len(gravacoes) == 3,
      [g.get("critical_effect", {}).get("phase") for g in gravacoes])
check("M21 CONTROLE: a ordem das fases e a da vida real",
      [g["critical_effect"]["phase"] for g in gravacoes]
      == [G.FASE_ARMED, G.FASE_SUBMITTED, G.FASE_CONFIRMED])

# ==========================================================================
print("\n[M22] efeito CONFIRMADO nunca permite recriar a operacao")
# ==========================================================================
conf = {"attempts": 0, "evidence": {"critical_effect": {"phase": "confirmed",
                                                        "receipt": "22842291"}}}
p_conf = G.decidir_recuperacao(conf, idade_segundos=9999, limite_segundos=1800)
check("M22: confirmado nao volta para a fila", p_conf["status"] == "needs_human")
check("M22: com protocolo em evidence tambem nao volta",
      G.decidir_recuperacao({"attempts": 0, "evidence": {"protocolo": "22842291"}},
                            idade_segundos=9999,
                            limite_segundos=1800)["status"] == "needs_human")
pode, motivo = G.pode_retentar_pelo_dashboard(
    {"company_id": "c1", "status": "needs_human", "evidence": {"protocolo": "1"}}, "c1")
check("M22: o botao do dashboard tambem recusa", not pode, motivo)
check("M22: e explica o porque", "protocolo" in motivo.lower() or "material" in motivo.lower())
pode2, _ = G.pode_retentar_pelo_dashboard(
    {"company_id": "c1", "status": "needs_human", "evidence": {}}, "c1")
check("M22 CONTROLE: sem efeito, o dashboard PODE retentar", pode2)
pode3, m3 = G.pode_retentar_pelo_dashboard(
    {"company_id": "OUTRA", "status": "needs_human", "evidence": {}}, "c1")
check("M22 CONTROLE: job de outra corretora nunca e retentavel", not pode3, m3)

# ==========================================================================
print("\n[M23-extra] identidade de corretora — o P1 que o Founder mandou fechar")
# ==========================================================================
duas = [{"corretora": "RESULTA CORRETORA DE SEGUROS LTDA"},
        {"corretora": "AUTO FLEET R CORRETORA"}]
uma = [{"corretora": "RESULTA CORRETORA DE SEGUROS LTDA"}] * 3
check("M23: duas corretoras na mesma leitura BLOQUEIA, mesmo com rotulo generico",
      bool(ID.conferir_itens_da_corretora(duas, campo="corretora", esperado="principal")))
check("M23 CONTROLE: uma corretora so, com rotulo generico, passa",
      not ID.conferir_itens_da_corretora(uma, campo="corretora", esperado="principal"))
check("M23: rotulo nomeado que nao bate BLOQUEIA",
      bool(ID.conferir_itens_da_corretora(uma, campo="corretora",
                                          esperado="AUTO FLEET R CORRETORA DE SEGU")))
check("M23 CONTROLE: rotulo nomeado truncado que bate passa",
      not ID.conferir_itens_da_corretora(uma, campo="corretora",
                                         esperado="RESULTA CORRETORA DE SEGUROS L"))
check("M23: sessao ilegivel com rotulo nomeado BLOQUEIA (fail-closed)",
      bool(ID.conferir_corretora_da_sessao("", "RESULTA CORRETORA")))
check("M23 CONTROLE: silencio (campo ausente) NAO bloqueia",
      not ID.conferir_itens_da_corretora([{"x": 1}], campo="corretora", esperado="p"))

# 🔴 UNICIDADE NAO E IDENTIDADE — correcao do Founder em 16/08/2026.
# A primeira versao gravava `verificado: True` sempre que a leitura passava.
# Com `account_label='principal'` (14 das 16 contas medidas) isso marcava como
# verificada uma identidade que ninguem conferiu, so porque apareceu UMA
# corretora. "Nao misturei duas empresas" e "estou na empresa certa" sao
# perguntas diferentes, e chamar a primeira de segunda so aparece no incidente.
m_gen = ID.marca_de_identidade(campo="corretora", itens=uma,
                               esperado="principal", bloqueado=False)
m_nom = ID.marca_de_identidade(campo="corretora", itens=uma,
                               esperado="RESULTA CORRETORA DE SEGUROS L", bloqueado=False)
m_blq = ID.marca_de_identidade(campo="corretora", itens=duas,
                               esperado="principal", bloqueado=True)
m_ilg = ID.marca_de_identidade(campo="corretora", itens=[{"x": 1}],
                               esperado="principal", bloqueado=False)
check("M25: uma corretora + rotulo generico NAO e `verified`",
      m_gen["estado"] == ID.UNICO_NAO_VERIFICADO, m_gen)
check("M25: e o campo `verificado` acompanha a verdade", m_gen["verificado"] is False)
check("M25 CONTROLE: rotulo NOMEADO que casa E `verified`",
      m_nom["estado"] == ID.VERIFICADO and m_nom["verificado"] is True, m_nom)
check("M25: bloqueio vira estado `blocked`", m_blq["estado"] == ID.BLOQUEADO)
check("M25: identidade ilegivel vira `unreadable`", m_ilg["estado"] == ID.ILEGIVEL)
check("M25 CONTROLE: os quatro estados sao DISTINTOS",
      len({m_gen["estado"], m_nom["estado"], m_blq["estado"], m_ilg["estado"]}) == 4)
check("M25: o contexto observado fica registrado para comparacao futura",
      m_gen["contexto_observado"] == "RESULTA CORRETORA DE SEGUROS LTDA")
check("M25: com dois contextos o valor NAO e duplicado na marca",
      m_blq["contexto_observado"] == "")

s_gen = ID.marca_de_identidade_da_sessao(lida="AUTO FLEET R CORRETORA",
                                         esperado="principal", bloqueado=False)
s_nom = ID.marca_de_identidade_da_sessao(lida="AUTO FLEET R CORRETORA",
                                         esperado="AUTO FLEET R CORRETORA DE SEGU",
                                         bloqueado=False)
check("M25: o gate de SESSAO segue a mesma regra",
      s_gen["estado"] == ID.UNICO_NAO_VERIFICADO and s_nom["estado"] == ID.VERIFICADO)

# ==========================================================================
print("\n[M24-extra] o kill switch alcanca o worker Python")
# ==========================================================================
salvo = os.environ.pop("GLOBAL_KILL_SWITCH", None)
check("M24 CONTROLE: variavel ausente = comportamento historico", not RT.kill_switch_ativo())
os.environ["GLOBAL_KILL_SWITCH"] = "true"
check("M24: 'true' ativa o freio", RT.kill_switch_ativo())
os.environ["GLOBAL_KILL_SWITCH"] = "false"
check("M24: 'false' desliga", not RT.kill_switch_ativo())
os.environ["GLOBAL_KILL_SWITCH"] = ""
check("M24: valor vazio falha FECHADO", RT.kill_switch_ativo())
if salvo is None:
    os.environ.pop("GLOBAL_KILL_SWITCH", None)
else:
    os.environ["GLOBAL_KILL_SWITCH"] = salvo
src_loop = inspect.getsource(W.poll_loop)
check("M24: o freio e checado DENTRO do laco, nao so no boot",
      src_loop.find("while True") < src_loop.find("kill_switch_ativo"))

# ==========================================================================
print("\n[LINHA DE CONTROLE] a SPEC-073 nao virou 'nega tudo'")
# ==========================================================================
g_ctl = guard()
check("login continua permitido", g_ctl.avaliar(G.READ_ONLY)[0])
check("consulta continua permitida", g_ctl.avaliar(G.READ_ONLY)[0])
check("download de PDF continua permitido", g_ctl.avaliar(G.READ_ONLY)[0])
check("preencher campo antes de enviar continua permitido",
      g_ctl.avaliar(G.REVERSIBLE_UI)[0])
check("clicar botao inofensivo continua permitido",
      P.validar_acao({"action": "click", "target": "Voltar"}, TELA, guard=g_ctl).ok)
check("preencher campo NAO critico com valor livre continua permitido",
      P.validar_acao({"action": "fill", "target": "nome", "value": "FULANO DE TAL"},
                     TELA, collected=DADOS, guard=g_ctl).ok)
check("select com opcao real continua permitido",
      P.validar_acao({"action": "select", "target": "Lado", "value": "Carona"},
                     TELA, collected=DADOS, guard=g_ctl).ok)
check("ask_human nunca e bloqueado", P.validar_acao({"action": "ask_human"}, TELA).ok)
check("worker sem visao continua funcionando (visao nasce desligada)",
      P.visao_habilitada() is False)
check("worker sem discovery continua funcionando (discovery nasce desligado)",
      RT.discovery_mode() is False)
check("profiler nasce LIGADO — e passivo, e e o que ensina",
      RT.profiler_enabled() is True)
check("runtime e ADITIVO: journey que ignora `_runtime` nao quebra",
      "runtime: Any = None" in inspect.signature(A.run_adaptive).__str__()
      or "runtime" in inspect.signature(A.run_adaptive).parameters)

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
