# -*- coding: utf-8 -*-
"""SPEC-074 — o contrato medido do Maxpar, provado offline contra fixture.

Este arquivo é o **replay**: ele roda o motor inteiro contra as respostas reais
do portal, sem rede, sem browser e sem criar um único atendimento.

O que ele prova, em uma frase cada
==================================
    [1] preflight    o gate que separa "consultar" de "criar", nos 5 estados
    [2] questionario o motor dinâmico, nas DUAS ordens medidas
    [3] estado       as duas fronteiras materiais e o que cada uma libera
    [4] idempotencia o lado entra na chave — P-79
    [5] franquia     vem da API, e chega antes da tela mostrar
    [6] vistoria     o campo é conhecido; o valor, não — e não se inventa
    [7] allowlist    descoberta não vira cliente HTTP de URL livre
    [8] catalogos    a autoridade é a resposta de agora, não uma tabela
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fixtures.vidros import maxpar_apolices as FA        # noqa: E402
from fixtures.vidros import maxpar_atendimento as FT     # noqa: E402
from fixtures.vidros import maxpar_catalogos as FC       # noqa: E402
from fixtures.vidros import maxpar_questionario as FQ    # noqa: E402
from portal_worker.journeys import vidros_api as A       # noqa: E402
from portal_worker.journeys import vidros_estado as E    # noqa: E402
from portal_worker.journeys import vidros_questionario as Q  # noqa: E402

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:220] if extra else ""))


# ==========================================================================
print("\n[1] PREFLIGHT — o gate que decide se pode haver escrita")
# ==========================================================================
r_ok = A.classificar_preflight(200, FA.APOLICE_OK)
r_nf = A.classificar_preflight(200, FA.APOLICE_NAO_ENCONTRADA)
r_amb = A.classificar_preflight(200, FA.APOLICE_AMBIGUA)
r_cov = A.classificar_preflight(FA.COVERAGE_ABSENT_PORTO_STATUS, FA.COVERAGE_ABSENT_PORTO)
r_out = A.classificar_preflight(400, FA.OUTRA_REGRA_DE_NEGOCIO)

check("apólice válida -> policy_ok", r_ok["estado"] == A.POLICY_OK)
check("e é o ÚNICO estado que libera escrita", r_ok["pode_escrever"] is True)
check("não encontrada -> policy_not_found", r_nf["estado"] == A.POLICY_NOT_FOUND)
check("ambígua -> policy_ambiguous", r_amb["estado"] == A.POLICY_AMBIGUOUS)
check("400 + RegraDeNegocio + 'não possui cláusula' -> coverage_absent",
      r_cov["estado"] == A.COVERAGE_ABSENT, r_cov)
check("e extrai o escopo da cobertura que falta",
      "roda" in r_cov["escopo"] and "pneu" in r_cov["escopo"], r_cov["escopo"])
check("preserva a mensagem literal do portal, para o dossiê",
      "não possui cláusula" in r_cov["mensagem_portal"])

# 🔴 O controle que impede o classificador de virar otimista: `Tipo` é enum
# ABERTO. Outra regra de negócio com o MESMO Tipo não pode virar
# `coverage_absent` — e muito menos passar.
check("MESMO Tipo, outra regra -> business_rule_rejection_unknown",
      r_out["estado"] == A.BUSINESS_RULE_UNKNOWN, r_out)
check("e ela também NÃO libera escrita", r_out["pode_escrever"] is False)
check("Tipo desconhecido também não libera",
      A.classificar_preflight(400, {"Tipo": "TipoNovo", "Message": "x"})["pode_escrever"] is False)

for nome, st, corpo in [("500", 500, None), ("200 sem os flags", 200, {}),
                        ("corpo nulo", 200, None), ("403", 403, {})]:
    check(f"{nome} -> não libera escrita",
          A.classificar_preflight(st, corpo)["pode_escrever"] is False)

check("CONTROLE: os cinco estados são DISTINTOS",
      len({r_ok["estado"], r_nf["estado"], r_amb["estado"],
           r_cov["estado"], r_out["estado"]}) == 5)

# ==========================================================================
print("\n[2] QUESTION ENGINE — replay das duas sequências medidas")
# ==========================================================================
respostas_do_segurado = {
    "pelicula": "sim, tem insulfilm",
    "porta": "é da porta dianteira",
    "lado": "lado do carona",
}

sess_y = FQ.SessaoDeQuestionarioFalsa(FQ.SEQUENCIA_YELUM)
res_y = asyncio.run(Q.rodar_questionario(sess_y, respostas_do_segurado=respostas_do_segurado))
check("Yelum: o motor chega ao 204", res_y.completo, res_y.motivo)
check("Yelum: respondeu as 3 perguntas", len(res_y.respostas) == 3, res_y.respostas)
check("Yelum: o acumulado CRESCE a cada rodada (0,1,2,3)",
      [len(x) for x in sess_y.enviados] == [0, 1, 2, 3], [len(x) for x in sess_y.enviados])
check("Yelum: escolheu o código certo da película (SIM=1)",
      res_y.respostas[0] == {"CodigoPergunta": 4, "CodigoResposta": 1, "TipoPergunta": "A"})
check("Yelum: dianteira = 123", res_y.respostas[1]["CodigoResposta"] == 123)
check("Yelum: carona = 38", res_y.respostas[2]["CodigoResposta"] == 38)

sess_p = FQ.SessaoDeQuestionarioFalsa(FQ.SEQUENCIA_PORTO)
res_p = asyncio.run(Q.rodar_questionario(sess_p, respostas_do_segurado={"lado": "lado do carona"}))
check("Porto: o motor chega ao 204", res_p.completo, res_p.motivo)
check("Porto: 1 pergunta só — quantidade NÃO é fixa", len(res_p.respostas) == 1)

# 🔴 A ASSERÇÃO MAIS IMPORTANTE DO ARQUIVO.
# A mesma pergunta 35 vem com ordem trocada e TipoPergunta diferente entre as
# duas seguradoras. Se o motor escolhesse por posição, "a segunda opção" daria
# CARONA na Yelum e MOTORISTA na Porto — e o vidraceiro trocaria a porta errada.
p_y = Q.ler_pergunta(FQ.PERGUNTA_LADO)
p_p = Q.ler_pergunta(FQ.PERGUNTA_LADO_PORTO)
check("a MESMA pergunta vem em ordem diferente nas duas seguradoras",
      p_y.textos_das_opcoes != p_p.textos_das_opcoes,
      (p_y.textos_das_opcoes, p_p.textos_das_opcoes))
check("e até com TipoPergunta diferente ('O' × 'P')",
      p_y.tipo != p_p.tipo, (p_y.tipo, p_p.tipo))
esc_y = Q.escolher_resposta(p_y, respostas_do_segurado={"lado": "lado do motorista"})
esc_p = Q.escolher_resposta(p_p, respostas_do_segurado={"lado": "lado do motorista"})
check("MOTORISTA dá o MESMO código (39) nas duas — posição não manda",
      esc_y["codigo"] == esc_p["codigo"] == 39, (esc_y["codigo"], esc_p["codigo"]))
esc_c = Q.escolher_resposta(p_p, respostas_do_segurado={"lado": "lado do carona"})
check("CONTROLE: carona dá OUTRO código (38) — o motor distingue de verdade",
      esc_c["codigo"] == 38 and esc_c["codigo"] != esc_p["codigo"])

# Sem resposta, o motor não chuta: devolve as opções REAIS, que viram a pergunta.
sess_x = FQ.SessaoDeQuestionarioFalsa(FQ.SEQUENCIA_YELUM)
res_x = asyncio.run(Q.rodar_questionario(sess_x, respostas_do_segurado={}))
check("sem resposta do segurado -> falta_resposta, não chute",
      res_x.situacao == Q.FALTA_RESPOSTA, res_x.situacao)
check("e para na PRIMEIRA pergunta, sem gastar rodada à toa", res_x.rodadas == 1)
check("devolvendo a pergunta pendente com as opções reais",
      res_x.pergunta_pendente is not None
      and len(res_x.pergunta_pendente.textos_das_opcoes) == 3)
check("o dossiê diz QUAL dado falta",
      "PELÍCULA" in res_x.motivo.upper() or "pelicula" in res_x.motivo.lower(), res_x.motivo)

# 🔴 O protocolo de coexistência dos dois vocabulários (achado do subagente):
# `explicar_especifico` devolve `dominio == "nenhum"` para dizer "esta lista não
# é minha" — e aí o certo é cair em `explicar_match`, o casador de PEÇA.
p_peca = Q.Pergunta(codigo=99, texto="Qual foi a peça danificada?", tipo="P",
                    opcoes=[{"CodigoResposta": 1, "DescricaoResposta": "VIDRO DE PORTA"},
                            {"CodigoResposta": 2, "DescricaoResposta": "VIDRO PARABRISA"}])
esc_peca = Q.escolher_resposta(p_peca, respostas_do_segurado={"peca": "vidro da porta"})
check("pergunta de PEÇA cai no vocabulário de peça, não no de atributo",
      esc_peca["situacao"] == "ok" and esc_peca["codigo"] == 1, esc_peca)

check("resposta 200 sem pergunta legível -> erro, não silêncio",
      Q.ler_pergunta({"semCodigo": 1}) is None)
check("pergunta sem opções -> erro explícito",
      Q.escolher_resposta(Q.Pergunta(codigo=1, texto="x", tipo="A", opcoes=[]),
                          respostas_do_segurado={"a": "b"})["situacao"] == Q.ERRO_API)

# ==========================================================================
print("\n[3] MÁQUINA DE ESTADOS — as duas fronteiras materiais")
# ==========================================================================
e_pre = E.ler_estado_do_agregado(FT.ATENDIMENTO_PRE_QUESTIONARIO)
e_fra = E.ler_estado_do_agregado(FT.ATENDIMENTO_COM_FRANQUIA)
e_pos = E.ler_estado_do_agregado(FT.ATENDIMENTO_POS_QUESTIONARIO)
e_can = E.ler_estado_do_agregado(FT.ATENDIMENTO_CANCELADO)
e_prot = E.ler_estado_do_agregado(FT.ATENDIMENTO_PRE_QUESTIONARIO, tinha_protocolo=True)

check("sem CodigoAtendimento e sem protocolo -> pre_protocolo",
      e_pre.estado == E.PRE_PROTOCOLO, e_pre.estado)
check("com protocolo emitido mas sem código -> protocolo_criado",
      e_prot.estado == E.PROTOCOLO_CRIADO, e_prot.estado)
check("com CodigoAtendimento -> atendimento_materializado",
      e_pos.estado == E.ATENDIMENTO_MATERIALIZADO, e_pos.estado)
check("Cancelado=true vence tudo", e_can.estado == E.CANCELADO, e_can.estado)
check("📊 a franquia chega ANTES do CodigoAtendimento",
      e_fra.estado == E.PRE_PROTOCOLO
      and A.descricao_da_franquia(FT.ATENDIMENTO_COM_FRANQUIA)["tem"] is True)

check("só pre_protocolo permite reabrir", e_pre.safe_to_retry_open is True)
for nome, est in [("protocolo_criado", e_prot), ("materializado", e_pos),
                  ("cancelado", e_can)]:
    check(f"{nome} NÃO permite reabrir", est.safe_to_retry_open is False)
check("desconhecido também não",
      E.EstadoDoAtendimento(estado=E.DESCONHECIDO).safe_to_retry_open is False)
check("e desconhecido é o único que pede reconciliação",
      E.EstadoDoAtendimento(estado=E.DESCONHECIDO).precisa_reconciliar is True)

# 🔴 O número que a pessoa anota é o de 8 dígitos, não o de 16.
check("a referência para o segurado é o CodigoAtendimento (8 díg.)",
      e_pos.referencia_para_o_segurado == "99999999", e_pos.referencia_para_o_segurado)
check("CONTROLE: o NumeroProtocolo (16 díg.) é INTERNO e não vaza como referência",
      str(FT.RESPOSTA_POST_ATENDIMENTOS["NumeroProtocolo"]) != e_pos.referencia_para_o_segurado)

from portal_worker import guardrails as G  # noqa: E402

check("falha após materializar -> fase CONFIRMED (o recovery não recomeça)",
      E.fase_apos_falha(e_pos) == G.FASE_CONFIRMED)
check("falha com protocolo -> CONFIRMED também",
      E.fase_apos_falha(e_prot) == G.FASE_CONFIRMED)
check("falha em pre_protocolo -> sem fase (pode recomeçar)",
      E.fase_apos_falha(e_pre) == "")
check("estado desconhecido -> UNKNOWN",
      E.fase_apos_falha(E.EstadoDoAtendimento(estado=E.DESCONHECIDO)) == G.FASE_UNKNOWN)

# ==========================================================================
print("\n[4] IDEMPOTÊNCIA — o lado entra na chave (P-79)")
# ==========================================================================
kc1 = E.idempotencia_de_continuacao(company_id="c1", protocolo="99999999",
                                    operacao="consultar")
kc2 = E.idempotencia_de_continuacao(company_id="c1", protocolo="99999999",
                                    operacao="continuar")
kc3 = E.idempotencia_de_continuacao(company_id="c2", protocolo="99999999",
                                    operacao="consultar")
check("continuação: mesma entrada, mesma chave",
      kc1 == E.idempotencia_de_continuacao(company_id="c1", protocolo="99999999",
                                           operacao="consultar"))
check("continuação: operação diferente, chave diferente", kc1 != kc2)
check("continuação: corretora diferente, chave diferente", kc1 != kc3)
check("continuação sem protocolo -> vazia (fail-open)",
      E.idempotencia_de_continuacao(company_id="c1", protocolo="", operacao="x") == "")
check("continuação sem corretora -> vazia",
      E.idempotencia_de_continuacao(company_id="", protocolo="1", operacao="x") == "")

# ==========================================================================
print("\n[5] FRANQUIA — da API, não da tela")
# ==========================================================================
f_sem = A.descricao_da_franquia(FT.ATENDIMENTO_PRE_QUESTIONARIO)
f_com = A.descricao_da_franquia(FT.ATENDIMENTO_COM_FRANQUIA)
check("sem franquia populada -> tem=False", f_sem["tem"] is False)
check("com franquia -> tem=True e traz o item", f_com["tem"] is True and f_com["itens"])
check("o título vem literal do portal",
      f_com["itens"][0]["titulo"] == "Valor para troca", f_com["itens"][0])
check("o valor vem como o portal manda (string)", f_com["itens"][0]["valor"] == "925")
check("RequerFranquia é preservado", f_com["requer"] is True)
check("corpo inválido não explode", A.descricao_da_franquia(None)["tem"] is False)

# ==========================================================================
print("\n[6] VISTORIA — campo conhecido, valor não inventado")
# ==========================================================================
v = A.vistoria_do_atendimento(FT.ATENDIMENTO_POS_QUESTIONARIO)
check("📊 nas capturas o link vem VAZIO", v["tem_link"] is False and v["link"] == "")
check("e as flags dizem por quê: vistoria não habilitada",
      v["permite_mobile"] is False and v["permite_loja"] is False)
check("com link preenchido, ele é devolvido literal",
      A.vistoria_do_atendimento({**FT.ATENDIMENTO_POS_QUESTIONARIO,
                                 "LinkVistoriaMobile": "https://vistoria.mobi/app/#/app/intro/abc"}
                                )["link"].endswith("/abc"))

# ==========================================================================
print("\n[7] ALLOWLIST — descoberta não vira HTTP client de URL livre")
# ==========================================================================
check("host da API é permitido", A.host_permitido(f"{A.BASE_API}/atendimentos"))
check("host da SPA é permitido", A.host_permitido("https://abraseuatendimento.com.br/x"))
check("área do segurado é permitida",
      A.host_permitido("https://areadosegurado.autoglass.com.br/#/detalhe/x"))
for mau in ("https://evil.com/api", "http://169.254.169.254/latest/meta-data",
            "https://api.autoglass.com.br.evil.com/x", ""):
    check(f"host recusado: {mau[:40] or '(vazio)'}", not A.host_permitido(mau))

# ==========================================================================
print("\n[8] CATÁLOGOS — a autoridade é a resposta de agora")
# ==========================================================================
check("as causas MUDAM por peça (vidro × lanterna)",
      {m["CodigoObjetoCausa"] for m in FC.MOTIVOS_DANO_VIDRO_PORTA}
      != {m["CodigoObjetoCausa"] for m in FC.MOTIVOS_DANO_LANTERNA})
check("e há causa que só existe em lanterna/farol",
      any("LÂMPADA" in m["DescricaoObjetoCausa"] for m in FC.MOTIVOS_DANO_LANTERNA)
      and not any("LÂMPADA" in m["DescricaoObjetoCausa"]
                  for m in FC.MOTIVOS_DANO_VIDRO_PORTA))
check("os itens cobertos diferem entre seguradoras",
      {i["CodigoItemCoberto"] for i in FC.ITENS_COBERTOS_YELUM}
      != {i["CodigoItemCoberto"] for i in FC.ITENS_COBERTOS_PORTO})
check("o slug da Yelum no portal é LIBERTY, não YELUM",
      FC.SLUG_DA_YELUM == "LIBERTY"
      and any(s["CodigoSeguradora"] == "LIBERTY" for s in FC.SEGURADORAS))

partes = A.partes_do_item_coberto("3|129|N|10700|1|0|V")
check("a chave composta é quebrada corretamente",
      partes["codigo_script"] == 3 and partes["codigo_tipo_script"] == 129
      and partes["categoria"] == "V", partes)
check("formato inesperado -> {} (fail-closed, não CodigoScript errado)",
      A.partes_do_item_coberto("3|129|V") == {})
check("todos os itens das duas seguradoras têm chave válida",
      all(A.partes_do_item_coberto(i["CodigoItemCoberto"])
          for i in FC.ITENS_COBERTOS_YELUM + FC.ITENS_COBERTOS_PORTO))

# TipoAtendimento — só a Porto
check("Porto + vidro -> 1", A.tipo_atendimento_para("PORTO", "vidro de porta") == 1)
check("Porto + roda -> 2", A.tipo_atendimento_para("PORTO", "roda e pneu") == 2)
for slug in ("LIBERTY", "ALLIANZ", "HDI", "TOKIOMARINE", "MAPFRE", "ZURICH"):
    check(f"{slug} -> None (não generalizar 1/2)",
          A.tipo_atendimento_para(slug, "vidro de porta") is None)

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
