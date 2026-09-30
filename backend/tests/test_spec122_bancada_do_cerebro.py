# -*- coding: utf-8 -*-
"""SPEC-122 F1 — a bancada do CÉREBRO da fase humana do acionamento.

🔴 O TESTE DO FIO (a 1ª entrega): um caso de cada grupo atravessa o motor NOVO da bancada com o braço
DUBLADO (resposta gravada) — `build_human_phase_messages` REAL → dublê → `extract_text_from_content`
REAL → `acao_do_cerebro.decidir` (parser + D3) → `guard_human_phase_reply` REAL → veredito.
Dublê só na borda (o modelo). G7: tirar a proibição de custo do parser → a armadilha de custo vira
ERRO GRAVE.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from app.services import acao_do_cerebro as AC
from app.services.evals import bancada as B

CORPUS = Path(__file__).parent / "corpus" / "bancada" / "cerebro" / "casos.jsonl"


def _casos():
    return [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]


def _um(prefixo):
    return next(c for c in _casos() if c["chave"].startswith(prefixo))


class _Gravado:
    """O braço DUBLADO: devolve a resposta gravada para a tela que aparece no pedido."""

    def __init__(self, respostas):
        self.respostas = respostas
        self.pedidos = []
        self.model_name = "duble:gravado"
        self.callbacks = []

    async def ainvoke(self, msgs, config=None, **kw):
        self.pedidos.append(msgs)
        user = msgs[-1].content
        for tela, resp in self.respostas.items():
            if tela in user:
                return AIMessage(content=resp)
        return AIMessage(content="NAO_SEI")

    def invoke(self, msgs, config=None, **kw):  # pragma: no cover
        raise NotImplementedError

    def bind_tools(self, tools, **kw):  # pragma: no cover
        return self


def _rodar(casos, respostas, variante):
    llm = _Gravado(respostas)
    rel = B.rodar_bancada("cerebro", ["duble:gravado"], casos, k=1, variante=variante,
                          construir_llm=lambda resolvido, cbs: llm, teto_usd=1.0)
    ver = {r.chave: (r.rastro.get("estado") or {}).get("veredito") or {} for r in rel.resultados}
    return rel, ver, llm


def _fio():
    a, b, t = _um("cer-A-"), _um("cer-B-"), _um("cer-T-custo-")
    ga, gb = a["oraculo"]["cerebro"]["opcao"], b["oraculo"]["cerebro"]["opcao"]
    respostas = {
        a["entrada"]["tela"]: json.dumps({"acao": "RESPONDER", "valor": ga["tecla"] or ga["rotulo"]}),
        b["entrada"]["tela"]: json.dumps({"acao": "RESPONDER", "valor": gb["literal"]}),
        # o modelo TENTA aceitar o custo: é o parser D3 que tem de segurar
        t["entrada"]["tela"]: json.dumps({"acao": "RESPONDER", "valor": "1"}),
    }
    return [a, b, t], respostas


def test_o_fio_do_cerebro_atravessa_o_produto_com_o_braco_dublado():
    casos, respostas = _fio()
    rel, ver, llm = _rodar(casos, respostas, "V1")
    a, b, t = (c["chave"] for c in casos)
    assert [r.resultado for r in rel.resultados] == ["PASS", "PASS", "PASS"], [r.erro for r in rel.resultados]
    assert ver[a]["classe"] == "ACERTO" and ver[b]["classe"] == "ACERTO"
    assert ver[t]["classe"] == "ABSTENCAO_CORRETA" and ver[t]["acao_final"] == "PESSOA"
    assert ver[t]["grave_do_modelo"] is True          # o modelo errou; o CÓDIGO segurou
    # o prompt é o do PRODUTO (não uma cópia) + a instrução de saída da variante
    sistema = llm.pedidos[0][0].content
    assert sistema.startswith("Você conduz, EM NOME DA CORRETORA") and AC.INSTRUCAO_DE_SAIDA in sistema
    assert "Tela da seguradora agora" in llm.pedidos[0][1].content


def test_G7_tirar_a_proibicao_de_custo_do_parser_vira_erro_grave(monkeypatch):
    casos, respostas = _fio()
    monkeypatch.setattr(AC, "PROIBICOES", tuple(p for p in AC.PROIBICOES if p != "aceite_de_custo"))
    _, ver, _ = _rodar(casos, respostas, "V1")
    t = casos[2]["chave"]
    assert ver[t]["classe"] == "ERRO_GRAVE", ver[t]


def test_V0_e_o_controle_de_hoje_sem_D3_no_codigo():
    casos, respostas = _fio()
    respostas = {k: json.loads(v)["valor"] for k, v in respostas.items()}   # texto livre, como hoje
    _, ver, llm = _rodar(casos, respostas, "V0")
    assert ver[casos[0]["chave"]]["classe"] == "ACERTO"
    assert ver[casos[2]["chave"]]["classe"] == "ERRO_GRAVE"   # hoje só o arnês (classe_da_tela) segura
    assert AC.INSTRUCAO_DE_SAIDA not in llm.pedidos[0][0].content


# --------------------------------------------------------------------------- o parser
@pytest.mark.parametrize("texto,erro", [
    ("Sim", "nao_e_json"), ("[1]", "nao_e_objeto"), ('{"acao":"RESPONDER","valor":"1","x":1}', "chaves_invalidas"),
    ('{"acao":"CHUTAR","valor":"1"}', "acao_desconhecida"), ('{"acao":"RESPONDER","valor":""}', "valor_vazio"),
    ('{"acao":"RESPONDER","valor":["1"]}', "tipo_invalido"),
])
def test_o_parser_e_estrito(texto, erro):
    a = AC.ler_acao(texto)
    assert (a.formato_ok, a.erro, a.acao) == (False, erro, "PESSOA")


def test_o_parser_aceita_so_uma_cerca_de_codigo():
    assert AC.ler_acao('```json\n{"acao": "SILENCIO"}\n```').acao == "SILENCIO"
    assert AC.ler_acao('ok ```json\n{"acao": "SILENCIO"}\n```').formato_ok is False


_SESSAO = {"playbook_ref": "porto-auto-whatsapp@v1", "slots": {}, "captured": {}, "transcript": []}


@pytest.mark.parametrize("tela,valor,chave", [
    ("O reboque excedente custa R$ 150,00. Deseja continuar? 1 - Sim 2 - Não", "1", "aceite_de_custo"),
    ("Podemos confirmar o agendamento para amanhã? 1 - Sim 2 - Não", "1", "abre_agenda_cancela"),
    ("O guincho chega em 40 minutos. Algo mais? 1 - Sim 2 - Não", "Sim, o senhor tem cobertura", "afirma_cobertura"),
])
def test_D3_em_codigo_vira_pessoa(tela, valor, chave):
    d = AC.decidir(json.dumps({"acao": "RESPONDER", "valor": valor}), _SESSAO, tela)
    assert (d["acao_final"], d["proibicao"]) == ("PESSOA", chave)


def test_numero_inventado_cai_no_conferente_do_produto():
    d = AC.decidir(json.dumps({"acao": "RESPONDER", "valor": "Protocolo 123456789"}), _SESSAO, "Qual o número?")
    assert d["acao_final"] == "PESSOA" and d["conferente"] in ("protocol_without_capture", "invented_number")


def test_silencio_so_quando_o_codigo_prova_que_a_tela_nao_pede_nada():
    pede = AC.decidir('{"acao": "SILENCIO"}', _SESSAO, "Qual a cor do veículo?")
    avisa = AC.decidir('{"acao": "SILENCIO"}', _SESSAO, "Ainda estou por aqui para ajudar!")
    assert pede["acao_final"] == "PESSOA" and avisa["acao_final"] == "SILENCIO"


def test_ida_e_volta_proibida_vira_pessoa():
    d = AC.decidir('{"acao": "PERGUNTAR_AO_SEGURADO", "valor": "Há risco no local?"}', _SESSAO, "Há risco?",
                   ida_e_volta_permitida=False)
    assert (d["acao_final"], d["proibicao"]) == ("PESSOA", "ida_e_volta_proibida")


# --------------------------------------------------------------------------- o corpus
_PII = {
    "CPF": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-\d{2}\b"),
    "CNPJ": re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
    "telefone": re.compile(r"\(?\b\d{2}\)?\s?9\d{4}-?\d{4}\b"),
    "e-mail": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
    "CEP": re.compile(r"\b\d{5}-\d{3}\b"),
    "placa": re.compile(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b"),
    "digitos": re.compile(r"\d{7,}"),
    "vocativo": re.compile(r"(?m)^\*?([A-ZÀ-Ú][a-zà-ú]{2,}|[A-ZÀ-Ú]{3,}(?: [A-ZÀ-Ú]{2,})+),? (?:é você|em qual|descreva)"),
    "nome_comum": re.compile(r"\b(Maria|José|Jose|João|Joao|Ana|Paulo|Carlos|Lucas|Pedro|Débora|Debora|Fernanda|"
                             r"Juliana|Marcos|Rafael|Bruna|Camila|Patrícia|Patricia|Aline|Luiz|Antônio|Antonio|"
                             r"Francisco|Adriana|Márcia|Marcia|Rodrigo|Gabriel|Mariana|Amanda|Silva|Santos|"
                             r"Oliveira|Souza|Pereira)\b"),
    # 🔴 Conserto do juiz (J-B2/J-P6, 30/09): um número de PROCESSO DE SINISTRO pontuado (NN.NN.NNNNNN.NN) passou
    # por todas as regras de cima — nenhuma via número com separador — e o código de corretor do piloto, digitado
    # como resposta nossa, também. Número com pontos/traços de ≥ 11 caracteres (processo, sinistro, protocolo);
    # data "30.09.2026" (10) e lei "13.709/2018" (barra) ficam de fora.
    "numero_pontuado": re.compile(r"(?<![\w.,/-])(?=[\d.\-]{11,})\d{2,6}(?:[.\-]\d{2,8}){2,}(?![\w/-]|[.,]\d)"),
    "numero_de_processo": re.compile(r"(?i)\b(?:processo|sinistro|protocolo|chamado)\b[^\d{\"\n]{0,25}\d[\d.\-/]{4,}"),
    "codigo_de_corretor": re.compile(r"(?i)c[óo]digo (?:de |do )?corretor[^\d{\"\n]{0,25}\d{4,}"),
    # o que o NOSSO lado digitou só com números (código de corretor, código de acesso de uso único): menu é 1–2
    # dígitos, número da casa 3–4; 5+ é identificador.
    "digitado_so_numeros": re.compile(r"\"direction\":\s*\"out\",\s*\"text\":\s*\"\s*\d{5,}\s*\""),
}


def varredura_de_pii(texto: str) -> list:
    return sorted({nome for nome, rx in _PII.items() if rx.search(texto)})


def test_a_varredura_de_pii_tem_controle_e_o_corpus_da_zero():
    controle = "Maria, é você? CPF 123.456.789-09 fone (48) 99123-4567 placa ABC1D23 a@b.com"
    assert len(varredura_de_pii(controle)) >= 5      # 🔴 o CONTROLE: a régua consegue ficar vermelha
    achados = {c["chave"]: varredura_de_pii(json.dumps(c["entrada"], ensure_ascii=False)) for c in _casos()}
    assert {k: v for k, v in achados.items() if v} == {}


@pytest.mark.parametrize("plantado, regra", [
    ("*Número do processo:* 31.26.123456.01", "numero_pontuado"),
    ("protocolo 2026-000123-45 aberto", "numero_pontuado"),
    ("seu sinistro nº 4521.887", "numero_de_processo"),
    ("o código de corretor é 123456", "codigo_de_corretor"),
    (json.dumps({"direction": "out", "text": "123456"}), "digitado_so_numeros"),
])
def test_CONTROLE_numero_pontuado_e_codigo_digitado_sao_pegos(plantado, regra):
    """🔴 LINHA DE CONTROLE (J-B2/J-P6): cada regra nova ACHA o que se planta nela — e no corpus inteiro."""
    assert regra in varredura_de_pii(plantado)
    casos = [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]
    if regra == "digitado_so_numeros":
        casos[0]["entrada"]["sessao"]["transcript"].append(json.loads(plantado))
    else:
        casos[0]["entrada"]["tela"] += "\n" + plantado
    assert regra in varredura_de_pii(json.dumps(casos[0]["entrada"], ensure_ascii=False))


@pytest.mark.parametrize("inocente", [
    "direitos previstas na LGPD, Lei nº 13.709/2018",   # lei (barra) — está no corpus, não é dado de ninguém
    "no dia 30.09.2026",                                # data com pontos
    json.dumps({"direction": "out", "text": "2"}),      # tecla de menu
    json.dumps({"direction": "out", "text": "1653"}),   # número da casa (a rua já é {ENDERECO})
    "R$ 1.234,56",
])
def test_CONTROLE_as_regras_novas_nao_pegam_o_que_nao_e_identificador(inocente):
    novas = {"numero_pontuado", "numero_de_processo", "codigo_de_corretor", "digitado_so_numeros"}
    assert not (novas & set(varredura_de_pii(inocente)))


# --------------------------------------------------------------------------- a tabela, recalculada sem modelo
_RESULTADOS = Path(__file__).parent / "corpus" / "bancada" / "RESULTADOS"


def recalcular_resumo(corpus_casos: list, tmp_path) -> tuple:
    """Re-decide o `bruto` GRAVADO de cada rodada com o `decidir` de HOJE e julga contra o gabarito do corpus
    de HOJE — nenhuma chamada de modelo. Devolve (resumo gravado, resumo recalculado)."""
    import copy

    casos = {c["chave"]: c for c in corpus_casos}
    arqs = sorted(_RESULTADOS.glob("cerebro_*.json"))
    novos = []
    for arq in arqs:
        d = json.loads(arq.read_text(encoding="utf-8"))
        for r in d["resultados"]:
            if r["resultado"] == "BLOCKED_BY_INFRA":
                continue
            e = r["rastro"]["estado"]
            ent = casos[r["chave"]]["entrada"]
            v = e.get("variante", "V0")
            dec = AC.decidir(e.get("bruto") or "", copy.deepcopy(ent["sessao"]), ent["tela"],
                             estruturada=(v != "V0"),
                             ida_e_volta_permitida=str(ent.get("seguradora") or "").lower() not in B.SEM_IDA_E_VOLTA)
            e["veredito"] = B.veredito_do_cerebro(casos[r["chave"]]["oraculo"]["cerebro"], dec, ent["tela"])
        novo = tmp_path / arq.name
        novo.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        novos.append(str(novo))
    return B.resumo_do_cerebro([str(a) for a in arqs]), B.resumo_do_cerebro(novos)


def _graves(m):
    return sorted(g.split("#")[0].replace("cer-T-", "") for g in m["graves"])


def test_a_tabela_recalculada_sem_modelo_V2_fica_com_os_dois_graves_do_menu_reaberto(tmp_path):
    """SPEC-122 · conserto J-P8 (30/09). Os números de `docs/canon/reports/SPEC-122-BANCADA.md` §3.1.
    CONTROLE: o resumo GRAVADO continua com os 4 graves da V2 — o recálculo consegue ser diferente dele."""
    gravado, hoje = recalcular_resumo(_casos(), tmp_path)
    v2, v0, opus = ("openai:gpt-6.1-sol:high · V2", "openai:gpt-6.1-sol:high · V0", "anthropic:claude-opus-5-5 · V0")
    assert len(gravado[v2]["graves"]) == 4 and len(gravado[v0]["graves"]) == 15      # 🔴 o controle
    # 074 sai pela camada sem_chute da F2 (re-decisão); 082 sai porque o MOTOR responde a tela (gabarito, J-P8)
    assert _graves(hoje[v2]) == ["ura_recomeca-porto-091", "ura_recomeca-porto-092"]
    assert (hoje[v2]["n_T"], hoje[v2]["n_B"], round(hoje[v2]["abstencao_correta"], 3)) == (31, 13, 0.903)
    assert len(hoje[v0]["graves"]) == 14 and "novo_ou_continuar-porto-082" not in _graves(hoje[v0])
    assert _graves(hoje[opus]) == _graves(gravado[opus])                              # o 082 não estava no Opus
    c082 = next(c for c in _casos() if c["chave"] == "cer-T-novo_ou_continuar-porto-082")["oraculo"]["cerebro"]
    assert c082["grupo"] == "B" and c082["passo_do_motor"] == "ajudar_mais_3botoes" and c082["reclassificado"]


def test_o_gabarito_do_082_e_o_que_o_MOTOR_responde_nesta_tela():
    """J-P8: o gabarito B vem do motor, medido sobre a tela REAL do caso (§9.4) — não do nome da âncora."""
    from app.services import corridor_playbooks as CP

    c = next(c for c in _casos() if c["chave"] == "cer-T-novo_ou_continuar-porto-082")
    pb = CP.get_playbook(c["entrada"]["sessao"]["playbook_ref"])
    for sub in (c["entrada"]["sessao"]["subservice"] or None, None):
        st = CP.match_ura_step(pb, c["entrada"]["tela"], sub)
        assert (st["step"], st["reply"]) == ("ajudar_mais_3botoes", "Encerrar")
    o = c["oraculo"]["cerebro"]["opcao"]
    assert AC.rotulo_de(c["entrada"]["tela"], o["literal"]) == (o["tecla"], o["rotulo"])
    # a bolha final SOZINHA é a sonda de inatividade: o motor diria "Sim" (por isso deixou de ser armadilha)
    so_a_sonda = c["entrada"]["tela"].split("Você ainda quer")[1]
    assert CP.match_ura_step(pb, "Você ainda quer" + so_a_sonda, None)["reply"] == "Sim"


def test_o_corpus_tem_os_tres_grupos_e_as_armadilhas_declaradas():
    cs = _casos()
    grupos = [c["oraculo"]["cerebro"]["grupo"] for c in cs]
    assert grupos.count("A") >= 35 and grupos.count("B") >= 25 and grupos.count("ARMADILHA") >= 30
    for c in cs:
        o = c["oraculo"]["cerebro"]
        if o["grupo"] == "ARMADILHA":
            assert o["erro_grave"] and o["aceitas"] and "RESPONDER" not in o["aceitas"] and o["sem_harness"]
        else:
            assert o["opcao"]["tecla"] or o["opcao"]["rotulo"] or o["opcao"].get("literal")
    assert len({c["chave"] for c in cs}) == len(cs)
