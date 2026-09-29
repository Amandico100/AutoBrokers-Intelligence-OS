# -*- coding: utf-8 -*-
"""SPEC-120 F1 · F2 · F3 — as telas que ninguém respondia, o residencial que tenta,
e a tela dos amperes que NUNCA trava.

> *"Quanto mais atendimentos conseguirmos fazer sem travar, sem errar e sem humano,
> mais valiosos seremos."* — o Founder
> ⛔ E o CLAUDE.md §9.5: **responder a tela ≠ responder CERTO.**

🔴 **Tudo aqui roda O MOTOR** (`handle_insurer_message`, `match_ura_step`,
`render_reply`, `classe_da_tela`, `new_dispatch_session`) sobre a **TELA REAL** do
acervo versionado (`tests/corpus/telas_reais/*.jsonl`), lida pelo `session_id`.
Nenhum `re.search` de âncora aqui dentro (CLAUDE.md §9.4).

⚠️ As ÚNICAS telas escritas à mão são as formas de múltipla escolha dos amperes
(§ F3): 📊 o acervo inteiro tem UMA pergunta de amperes, e ela é texto livre. A
pergunta é a real; as opções seguem as TRÊS formas reais de opção do acervo
(`*1 -*` da allianz, `Botão 1:` da família hdi/yelum, a lista nua da porto) — e o
Founder pediu, com todas as letras, que funcione *"escrito ou múltipla escolha ou
pra digitar um número"*.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CORPUS = RAIZ / "tests" / "corpus" / "telas_reais"
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"


def _carregar(nome: str, caminho: Path):
    """O motor sem `app.services.__init__` (fastembed) — o mesmo carregador de
    `test_o_passo_que_decide_e_o_passo_que_conduz.py`, e ele DESFAZ o que injetou."""
    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services")}
    injetados = [n for n in anteriores if n not in sys.modules]
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location(nome, str(caminho))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


M = _carregar("_spec120_motor", MOTOR_PY)
#: 🔴 O MESMO módulo de playbooks que o motor usa — não uma segunda cópia. Mutar
#:    uma cópia que o motor não lê seria a "mutação que parece guarda mudo".
PB = sys.modules[M.get_playbook.__module__]


def tela(arquivo: str, sessao: str, padrao: str) -> str:
    """A tela REAL: a primeira linha do corpus daquela sessão que casa `padrao`."""
    for linha in (CORPUS / f"{arquivo}.jsonl").read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        x = json.loads(linha)
        if x["session_id"] == sessao and re.search(padrao, x["text"], re.IGNORECASE):
            return x["text"]
    raise AssertionError(f"a tela /{padrao}/ saiu de {arquivo}.jsonl sessão {sessao}")


def _sessao(ref, slots=None, subservice="guincho", state="ura"):
    return {"state": state, "slots": dict(slots or {}), "subservice": subservice,
            "case_id": "c-120", "transcript": [], "playbook_ref": ref}


def responde(ref, texto, slots=None, subservice="guincho", state="ura"):
    """`(texto que SAIU ou None, sessão)` — pelo motor inteiro."""
    s = M.handle_insurer_message(_sessao(ref, slots, subservice, state), texto)
    saidas = [t for t in (s.get("transcript") or []) if t.get("direction") == "out"]
    return (saidas[-1]["text"] if saidas else None), s


HDI, YELUM = "hdi-auto-whatsapp@v1", "yelum-auto-whatsapp@v3"
PORTO, AZUL, BRADESCO = "porto-auto-whatsapp@v1", "azul-auto-whatsapp@v1", "bradesco-auto-whatsapp@v1"
ALLIANZ_R, HDI_R, YELUM_R = ("allianz-residencial-whatsapp@v1", "hdi-residencial-whatsapp@v1",
                             "yelum-residencial-whatsapp@v1")

CASO_AUTO = {"titular_cpf": "00000000191", "titular_nome": "Maria Souza",
             "veiculo_placa": "ABC1D23", "local_atual": "Rua das Flores, 100, Centro, Joinville, SC",
             "local_destino": "Avenida Brasil, 2000, Centro, Joinville, SC",
             "problema_descricao": "o carro morreu e não liga mais", "quando": "agora",
             "telefone_contato": "47999990000", "pessoa_no_local": "Maria Souza"}
CASO_AUTO = {**CASO_AUTO, **PB.inject_address_slots(dict(CASO_AUTO)),
             # o que `new_dispatch_session` injeta do SUBSERVIÇO guincho (hdi/yelum)
             "servico_pos_aviso_opcao": "Guincho"}


# ═════════════════════════════════════════════════════════════════════════════
# F1 · AS CONSTANTES — cada uma com a decisão do Founder, sobre a tela real
# ═════════════════════════════════════════════════════════════════════════════

CONSTANTES = [
    # (decisão, corredor, arquivo, sessão, padrão da tela, esperado)
    ("D1 blindado", HDI, "hdi-auto", "2548c9c7", r"blindado", "Não"),
    ("D1 blindado", YELUM, "yelum-auto", "b187d77a", r"blindado", "Não"),
    ("D3 câmbio", HDI, "hdi-auto", "78b2de6f", r"c[âa]mbio est[áa] travado", "Não"),
    ("D3 câmbio", YELUM, "yelum-auto", "19d73270", r"c[âa]mbio est[áa] travado", "Não"),
    ("D4 desatrelado", HDI, "hdi-auto", "fa2ceb6f", r"desatrelado", "Sim"),
    ("D4 desatrelado", YELUM, "yelum-auto", "6b4c37e4", r"desatrelado", "Sim"),
    ("D5 rodas livres", HDI, "hdi-auto", "2548c9c7", r"rodas livres", "Sim"),
    ("D6 animal", HDI, "hdi-auto", "ea61eb64", r"animal de estima", "Não"),
    ("D10 posso ligar", AZUL, "azul-auto", "2f0cd86a", r"qualquer um deles", "1"),
    ("D11 impedido", BRADESCO, "bradesco-auto", "706df513", r"impedido de rodar", "Sim"),
    ("continuar", YELUM, "yelum-auto", "01bf91c2", r"continuar de onde parou", "Continuar"),
    ("destino por método", YELUM, "yelum-auto", "705f915b", r"definiremos", "Digitar endereço"),
    ("destino por método (lista)", YELUM, "yelum-auto", "19d73270", r"definiremos", "Digitar endereço"),
    ("não abrir 2º serviço", HDI, "hdi-auto", "fa2ceb6f", r"algum outro servi", "Não"),
    ("serviço da rota", HDI, "hdi-auto", "4b2d0c2a", r"melhor atender[áa] o problema", "Guincho"),
    ("retomar agendamento", PORTO, "porto-auto", "12203ed9", r"estava agendando", "Sim"),
    ("manter horário", PORTO, "porto-auto", "12203ed9", r"hor[áa]rio escolhido mesmo", "Sim"),
    ("ramo da rota", PORTO, "porto-auto", "ba772444", r"qual tipo de atendimento", "Serviços para veículo"),
]


@pytest.mark.parametrize("decisao,ref,arquivo,sessao,padrao,esperado", CONSTANTES,
                         ids=[f"{c[0]}-{c[3]}" for c in CONSTANTES])
def test_a_tela_orfa_agora_e_respondida_com_a_decisao(decisao, ref, arquivo, sessao, padrao, esperado):
    texto = tela(arquivo, sessao, padrao)
    saiu, s = responde(ref, texto, CASO_AUTO)
    assert saiu == esperado, (f"{decisao} · {arquivo} {sessao}: saiu {saiu!r} "
                              f"(estado {s.get('state')}, motivo {s.get('reason')})")
    assert s.get("state") != "needs_human"


@pytest.mark.parametrize("decisao,ref,arquivo,sessao,padrao,esperado", CONSTANTES,
                         ids=[f"{c[0]}-{c[3]}" for c in CONSTANTES])
def test_a_constante_que_escolhe_nomeia_o_rotulo_da_tela(decisao, ref, arquivo, sessao, padrao, esperado):
    """🔴 CLAUDE.md §9.5: a constante que escolhe entre alternativas diz POR QUÊ, e
    o porquê NOMEIA o rótulo que ela aperta — `1` na azul é `Sim`."""
    texto = tela(arquivo, sessao, padrao)
    passo = PB.match_ura_step(PB.get_playbook(ref), texto, subservice="guincho")
    if "{" in str(passo.get("reply") or ""):
        return  # resposta do CASO (servico_pos_aviso_opcao), não constante
    just = PB._norm(passo.get("constante_justificada") or "")
    rotulo = esperado
    if esperado.isdigit():
        rotulo = dict(PB.opcoes_da_tela(texto))[esperado]
    assert just, f"`{passo['step']}` escolhe {esperado!r} sem `constante_justificada`"
    assert PB._norm(rotulo) in just, (
        f"`{passo['step']}` aperta {rotulo!r} e a justificativa não nomeia esse rótulo")


# ═════════════════════════════════════════════════════════════════════════════
# F1 · AS TRÊS QUE SÃO DO CASO (D2, D8, D9) — perguntadas ANTES da URA
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ref,sub,slot", [
    (HDI, "guincho", "veiculo_nivel_rua"),        # D2
    (YELUM, "guincho", "veiculo_nivel_rua"),      # D2
    (ALLIANZ_R, "encanador", "periodo_preferido"),  # D8
    (PORTO, "guincho", "taxi_apos_guincho"),      # D9
])
def test_o_dado_do_caso_e_cobrado_antes_de_acionar(ref, sub, slot):
    """🔴 Pelo portão do motor: a sessão NÃO nasce `ready_to_send` sem ele."""
    slots = {k: v for k, v in CASO_AUTO.items()}
    s = M.new_dispatch_session(case_id="c-120", company_id="x", playbook_ref=ref,
                               subservice=sub, slots=slots)
    assert slot in (s.get("missing_slots") or []), (ref, sub, s.get("missing_slots"))
    assert PB._COMO_PERGUNTAR.get(slot), f"`{slot}` sem redação para o segurado"


def test_D9_e_so_da_porto():
    """CONTROLE do D9: *"isso precisa ser para a Porto Seguro"*."""
    for ref in (AZUL, BRADESCO, HDI, YELUM):
        faltam = PB.missing_slots_for_subservice(PB.get_playbook(ref), "guincho", {})
        assert "taxi_apos_guincho" not in faltam, ref


@pytest.mark.parametrize("valor,esperado", [
    ("não precisa", "Não"), ("Nao, obrigado", "Não"), ("sim, vamos em 3", "Sim"),
    ("vou precisar sim", "Sim")])
def test_D9_a_tela_do_taxi_recebe_o_que_o_segurado_disse(valor, esperado):
    texto = tela("porto-auto", "77983f63", r"al[ée]m do guincho")
    saiu, s = responde(PORTO, texto, {**CASO_AUTO, "taxi_apos_guincho": valor})
    assert saiu == esperado, (valor, saiu, s.get("reason"))


def test_D9_resposta_ilegivel_vai_a_uma_pessoa_e_nao_vira_palpite():
    texto = tela("porto-auto", "77983f63", r"al[ée]m do guincho")
    saiu, s = responde(PORTO, texto, {**CASO_AUTO, "taxi_apos_guincho": "talvez"})
    assert saiu is None and s["state"] == "needs_human", (saiu, s.get("state"))
    assert str(s.get("reason")).startswith("sem_chute"), s.get("reason")


def test_D9_a_oferta_antiga_do_taxi_tambem_pergunta():
    """📊 `taxi_oferta` respondia "Não" fixo e dizia *"está em PENDENCIAS"*."""
    texto = tela("porto-auto", "ba772444", r"tamb[ée]m precisa solicitar um t[áa]xi")
    assert responde(PORTO, texto, {**CASO_AUTO, "taxi_apos_guincho": "sim"})[0] == "Sim"
    assert responde(PORTO, texto, {**CASO_AUTO, "taxi_apos_guincho": "não"})[0] == "Não"


@pytest.mark.parametrize("nivel,garagem,esperado", [
    ("subsolo", "sim", "Sim"), ("Acima do nível da rua", "sim", "Sim"),
    ("nível da rua com acesso livre", "sim", "Não"), ("não sei", "na rua", "Não"),
    ("no nível da rua", "", "Não")])
def test_D2_o_subsolo_vem_do_que_o_segurado_contou(nivel, garagem, esperado):
    texto = tela("hdi-auto", "78b2de6f", r"garagem subsolo ou acima")
    saiu, _s = responde(HDI, texto, {**CASO_AUTO, "veiculo_nivel_rua": nivel,
                                     "veiculo_em_garagem": garagem})
    assert saiu == esperado, (nivel, garagem, saiu)


def test_D2_sem_leitura_segura_o_cerebro_assume_e_nao_se_chuta():
    texto = tela("yelum-auto", "705f915b", r"garagem subsolo ou acima")
    saiu, s = responde(YELUM, texto, {**CASO_AUTO, "veiculo_nivel_rua": "não sei dizer"})
    assert saiu is None and s["state"] != "needs_human", (saiu, s.get("state"))
    assert (s.get("falta_para_a_ura") or {}).get("campo") == "garagem_subsolo_ou_acima"


def test_D2_a_garagem_respeita_o_que_o_segurado_disse_e_o_resto_segue_igual():
    """🔴 §9.5: `garagem` respondia "Não" FIXO por cima do `veiculo_em_garagem`
    cobrado do segurado. CONTROLE: fora do guincho a tela segue o passo antigo."""
    texto = tela("hdi-auto", "78b2de6f", r"est[áa] em uma garagem\?")
    assert responde(HDI, texto, {**CASO_AUTO, "veiculo_em_garagem": "sim, no estacionamento"})[0] == "Sim"
    assert responde(HDI, texto, {**CASO_AUTO, "veiculo_em_garagem": "na rua"})[0] == "Não"
    assert responde(HDI, texto, CASO_AUTO, subservice="bateria")[0] == "Não"


def test_D8_o_encanador_agendado_recebe_a_primeira_data_e_o_periodo_do_segurado():
    data = tela("allianz-residencial", "5e72e523", r"escolha qual data")
    periodo = tela("allianz-residencial", "5e72e523", r"hor[áa]rios de agendamento")
    base = {"titular_cpf": "00000000191", "endereco_numero": "100",
            "telefone_contato": "47999990000", "problema_descricao": "vazamento",
            "periodo_preferido": "manhã"}
    M._derivar_teclas_do_caso(base)
    assert responde(ALLIANZ_R, data, base, subservice="encanador")[0] == "1"   # D7
    assert responde(ALLIANZ_R, periodo, base, subservice="encanador")[0] == "1"  # manhã
    tarde = {**base, "periodo_preferido": "tarde", "periodo_agendamento_opcao": ""}
    M._derivar_teclas_do_caso(tarde)
    assert responde(ALLIANZ_R, periodo, tarde, subservice="encanador")[0] == "2"


def test_D8_CONTROLE_o_chaveiro_continua_fora_do_agendamento():
    """O escopo alargou para `encanador`, não para todo mundo: o chaveiro tem outro
    fluxo (*"escolha um horário daqui a pelo menos 2 horas"*)."""
    data = tela("allianz-residencial", "5e72e523", r"escolha qual data")
    passo = PB.match_ura_step(PB.get_playbook(ALLIANZ_R), data, subservice="chaveiro")
    assert (passo or {}).get("step") != "escolher_data_agendamento"


# ═════════════════════════════════════════════════════════════════════════════
# F1 · 🔴 A ORIGEM IA COMO DESTINO — o defeito silencioso que a medição achou
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ref,arquivo,sessao", [
    (HDI, "hdi-auto", "2548c9c7"), (HDI, "hdi-auto", "83d2b9e3"),
    (YELUM, "yelum-auto", "705f915b"), (YELUM, "yelum-auto", "9d2655e2")])
def test_o_destino_digitado_e_o_destino_e_nao_a_origem(ref, arquivo, sessao):
    """📊 8 de 8 telas vêm logo depois de "para onde devemos levar o veículo"."""
    texto = tela(arquivo, sessao, r"digite o endere[çc]o seguindo o exemplo")
    saiu, _s = responde(ref, texto, CASO_AUTO)
    assert saiu == CASO_AUTO["local_destino"], saiu
    assert saiu != CASO_AUTO["local_atual"]


def test_CONTROLE_a_redacao_da_origem_continua_mandando_a_origem():
    texto = tela("yelum-auto", "6b4c37e4", r"me informe o \*?endere[çc]o completo")
    assert responde(YELUM, texto, CASO_AUTO)[0] == CASO_AUTO["local_atual"]


def test_o_destino_da_porto_e_o_destino():
    texto = tela("porto-auto", "51b2ed32", r"digite o endere[çc]o completo\. coloque")
    assert responde(PORTO, texto, CASO_AUTO)[0] == CASO_AUTO["local_destino"]


# ═════════════════════════════════════════════════════════════════════════════
# F1 · os repiques, os avisos, os desfechos e o sinistro
# ═════════════════════════════════════════════════════════════════════════════

def test_a_placa_nao_achada_vai_de_novo_no_formato_da_ura_e_depois_o_cpf():
    texto = tela("hdi-auto", "4b2d0c2a", r"n[ãa]o encontrei a placa")
    s = _sessao(HDI, {**CASO_AUTO, "veiculo_placa": "abc-1d23"})
    s = M.handle_insurer_message(s, texto)
    s = M.handle_insurer_message(s, texto)
    saidas = [t["text"] for t in s["transcript"] if t.get("direction") == "out"]
    assert saidas == ["ABC1D23", "00000000191"], saidas


def test_a_placa_nao_achada_com_convite_ao_cpf_manda_o_cpf():
    texto = tela("yelum-auto", "29ae4344", r"vamos tentar com o \*?cpf")
    assert responde(YELUM, texto, CASO_AUTO)[0] == "00000000191"


def test_informe_somente_numeros_reenvia_so_os_digitos_do_numero():
    texto = tela("allianz-residencial", "590b5940", r"^informe somente n")
    saiu, _s = responde(ALLIANZ_R, texto, {"endereco_numero": "100 fundos"},
                        subservice="maquina_de_lavar")
    assert saiu == "100", saiu


@pytest.mark.parametrize("ref,arquivo,sessao,padrao", [
    (YELUM, "yelum-auto", "56bd78f7", r"zona rural"),
    (HDI, "hdi-auto", "2548c9c7", r"^nesse caso, vou precisar que me informe novamente"),
    (YELUM, "yelum-auto", "01bf91c2", r"j[áa] tentou abrir um atendimento"),
    (PORTO, "porto-auto", "77983f63", r"tamb[ée]m pode solicitar um t[áa]xi"),
    (PORTO, "porto-auto", "4830574a", r"o quanto voc[êe] recomendaria"),
    (HDI_R, "hdi-residencial", "61b96027", r"por aqui, voc[êe] pode solicitar"),
])
def test_a_tela_que_so_avisa_nao_recebe_resposta_e_nao_trava(ref, arquivo, sessao, padrao):
    """🔴 zona rural: o "Sim" do banco era da tela SEGUINTE (mesmo segundo)."""
    saiu, s = responde(ref, tela(arquivo, sessao, padrao), CASO_AUTO,
                       subservice="encanador" if ref == HDI_R else "guincho")
    assert saiu is None and s["state"] != "needs_human", (saiu, s.get("state"))


@pytest.mark.parametrize("ref,arquivo,sessao,padrao", [
    (YELUM, "yelum-auto", "7c841763", r"pol[íi]cia liberou"),       # sinistro
    (HDI, "hdi-auto", "4b2d0c2a", r"solicita[çc][ãa]o est[áa] pendente"),  # desfecho sem protocolo
    (HDI, "hdi-auto", "4b2d0c2a", r"est[áa] conclu[íi]da"),         # já existe assistência
])
def test_sinistro_e_desfecho_vao_a_uma_pessoa(ref, arquivo, sessao, padrao):
    saiu, s = responde(ref, tela(arquivo, sessao, padrao), CASO_AUTO)
    assert saiu is None and s["state"] == "needs_human", (saiu, s.get("state"))
    assert str(s.get("reason")).startswith("handoff_trigger"), s.get("reason")


def test_a_policia_na_pane_da_bradesco_e_nao_e_se_o_relato_falar_de_policia_vai_a_uma_pessoa():
    texto = tela("bradesco-auto", "706df513", r"precisou chamar a pol")
    assert responde(BRADESCO, texto, CASO_AUTO)[0] == "Não"
    saiu, s = responde(BRADESCO, texto, {**CASO_AUTO,
                                         "problema_descricao": "bati o carro e a polícia veio"})
    assert saiu is None and s["state"] == "needs_human", (saiu, s.get("state"))


def test_a_confirmacao_da_bradesco_casa_o_passo_que_ja_existia():
    texto = tela("bradesco-auto", "72af1ae1", r"posso confirmar a abertura da sua")
    passo = PB.match_ura_step(PB.get_playbook(BRADESCO), texto, subservice="guincho")
    assert passo and passo["step"] == "confirmar_abertura_bradesco"


def test_D12_a_hdi_residencial_entra_como_segurado_e_a_yelum_nao_mudou():
    texto = tela("hdi-residencial", "61b96027", r"melhor te representa")
    assert responde(HDI_R, texto, {}, subservice="encanador")[0] == "Sou segurado(a)"
    # CONTROLE: D12 é só da HDI residencial.
    passo = PB.match_ura_step(PB.get_playbook(YELUM_R), texto, subservice="encanador")
    assert passo["reply"] == "Sou corretor(a)"


def test_depois_do_protocolo_a_hdi_residencial_nao_abre_um_segundo():
    """🔴 A resposta humana estava ERRADA: 📊 61b96027, "Sim" → protocolo 19905675,
    dois minutos depois do 19905659, mesmo serviço e endereço."""
    texto = tela("hdi-residencial", "61b96027", r"nova solicita[çc][ãa]o de servi")
    assert responde(HDI_R, texto, {}, subservice="encanador")[0] == "Não"


def test_o_eletricista_da_hdi_escolhe_o_ramo_certo_na_primeira_vez():
    """As 3 órfãs de `hdi/residencial/eletricista` (13379965) são de VAZAMENTO e
    GELADEIRA: a atendente se perdeu no menu. O conserto é o menu de serviço sair
    `Eletricista` — e ele sai, pelo motor, sobre a tela real da mesma sessão."""
    texto = tela("hdi-residencial", "13379965", r"qual [ée] o servi[çc]o que voc[êe] precisa")
    pb = PB.get_playbook(HDI_R)
    slots = {"tipo_servico_opcao": pb["subservices"]["eletricista"]["tipo_servico_opcao"]}
    saiu, _s = responde(HDI_R, texto, slots, subservice="eletricista")
    assert saiu == "Eletricista", saiu


def test_a_porto_com_o_segurado_na_conversa():
    """porto/bateria 4830574a: as QUATRO telas que o corredor responde."""
    placa = tela("porto-auto", "4830574a", r"placa e o modelo")
    assert responde(PORTO, placa, {**CASO_AUTO, "veiculo_descricao": "ONIX LT 1.0"},
                    subservice="bateria")[0] == "ABC1D23 ONIX LT 1.0"
    proprio = tela("porto-auto", "4830574a", r"o pr[óo]prio segurado")
    assert responde(PORTO, proprio, CASO_AUTO, subservice="bateria")[0] == "Sim"
    outro = {**CASO_AUTO, "pessoa_no_local": "João Lima"}
    assert responde(PORTO, proprio, outro, subservice="bateria")[0] == (
        "Não. Quem está no local é João Lima.")
    quando = tela("porto-auto", "4830574a", r"imediato ou agendado")
    assert responde(PORTO, quando, CASO_AUTO, subservice="bateria")[0] == "Imediato"


def test_D7_a_primeira_data_da_lista_ou_a_que_o_segurado_pediu():
    real = tela("porto-auto", "910b6295", r"datas dispon")
    assert responde(PORTO, real, CASO_AUTO)[0] == "{DATA}"  # o acervo mascara a data
    # A MESMA tela, com as datas restituídas na forma do humano ("14/09/2026").
    datas = [f"{d:02d}/10/2026" for d in (1, 2, 5, 6, 7, 8, 9)]
    restituida = real.replace("{DATA}", "{}").format(*datas)
    assert responde(PORTO, restituida, CASO_AUTO)[0] == "01/10/2026"
    pediu = {**CASO_AUTO, "data_agendamento": "05/10/2026"}
    assert responde(PORTO, restituida, pediu)[0] == "05/10/2026"


# ═════════════════════════════════════════════════════════════════════════════
# F2 · O RESIDENCIAL TENTA — e a tela que DECIDE continua indo a uma pessoa
# ═════════════════════════════════════════════════════════════════════════════

RESIDENCIAIS = (ALLIANZ_R, HDI_R, "porto-residencial-whatsapp@v1", YELUM_R)


@pytest.mark.parametrize("ref", RESIDENCIAIS)
def test_os_quatro_residenciais_declaram_que_tentam(ref):
    assert PB.get_playbook(ref)["unknown_step_policy"] == "adaptive_then_handoff"


def test_a_tela_desconhecida_do_residencial_vai_ao_cerebro_e_nao_a_uma_pessoa():
    """📊 allianz c58a171a: *"O Pet é: 1-Macho 2-Fêmea"* — nenhum passo a casa.
    O residencial TENTA: fase adaptativa, não `needs_human`."""
    texto = tela("allianz-residencial", "c58a171a", r"o pet [ée]")
    saiu, s = responde(ALLIANZ_R, texto, {}, subservice="consulta_veterinaria")
    assert s["state"] == "human_phase", (s.get("state"), s.get("reason"))
    assert M.classe_da_tela(PB.get_playbook(ALLIANZ_R), texto)["handoff"] is False


def test_CONTROLE_a_escolha_do_servico_desconhecida_continua_indo_a_uma_pessoa():
    """🔴 A rede não se afrouxa. 📊 allianz 44ff2017: *"Qual serviço deseja acionar?"*."""
    texto = tela("allianz-residencial", "44ff2017", r"qual servi[çc]o deseja acionar")
    _saiu, s = responde(ALLIANZ_R, texto, {}, subservice="encanador")
    assert s["state"] == "needs_human"
    assert s["reason"] == "tela_que_decide:escolhe_o_servico", s.get("reason")


def test_CONTROLE_a_tela_dos_tres_ramos_continua_indo_a_uma_pessoa():
    """🔴 *"1-Residencial 2-Condomínio 3-Empresarial"* (allianz c6b63f95) sem o ramo
    da apólice: uma pessoa. Com a apólice de condomínio: uma pessoa também."""
    texto = tela("allianz-residencial", "c6b63f95", r"qual seguro deseja utilizar")
    _saiu, s = responde(ALLIANZ_R, texto, {}, subservice="encanador")
    assert s["state"] == "needs_human" and s["reason"] == "ramo_indeterminado", s.get("reason")
    _saiu, s = responde(ALLIANZ_R, texto, {"qual_seguro_opcao": "Condomínio"},
                        subservice="encanador")
    assert s["state"] == "needs_human", s.get("reason")


# ═════════════════════════════════════════════════════════════════════════════
# F3 · 🔴 OS AMPERES — NUNCA trava, NUNCA chama humano, em NENHUMA seguradora
# ═════════════════════════════════════════════════════════════════════════════

AMPERES_REAL = ("porto-auto", "4830574a", r"quantos amperes")
PERGUNTA = "Você sabe me informar quantos amperes tem a bateria?"
FORMAS = {
    # forma → (tela, resposta esperada para o PADRÃO de 60 Ah)
    "numerada (allianz)": (PERGUNTA + "\n\n*1 -* Até 50Ah\n*2 -* 60Ah\n*3 -* 70Ah ou mais", "2"),
    "botão (hdi/yelum)": (PERGUNTA + "\nBotão 1: 45 a 50 Ah\nBotão 2: 60 Ah\nBotão 3: 70 Ah ou mais",
                          "60 Ah"),
    "lista (porto)": (PERGUNTA + "\nAté 50Ah\n60Ah\nAcima de 70Ah\nNão sei", "60Ah"),
    "sim/não": (PERGUNTA + "\nBotão 1: Sim\nBotão 2: Não", "Sim"),
    "digite o número": ("Digite a amperagem da bateria, somente números.", "60"),
    "sem número": (PERGUNTA + "\nNão sei\nVoltar", "Não sei"),
}


@pytest.mark.parametrize("veiculo,ah", [
    ("", "60"), ("ONIX LT 1.0 TURBO", "60"), ("FIAT MOBI LIKE 1.0", "50"),
    ("COROLLA XEI 2.0 FLEX", "70"), ("JEEP COMPASS LONGITUDE", "70"),
    ("HILUX CD SRV 2.8 DIESEL", "80"), ("VOLKSWAGEN GOL 1.0", "50"),
    ("VOLKSWAGEN GOL 1.6", "60"), ("MODELO QUE NINGUEM CONHECE", "60")])
def test_os_amperes_pelo_porte_e_60_em_qualquer_duvida(veiculo, ah):
    texto = tela(*AMPERES_REAL)
    saiu, s = responde(PORTO, texto, {**CASO_AUTO, "veiculo_descricao": veiculo},
                       subservice="bateria")
    assert saiu == ah and s["state"] != "needs_human", (veiculo, saiu, s.get("state"))


def test_o_segurado_que_disse_a_amperagem_manda():
    texto = tela(*AMPERES_REAL)
    caso = {**CASO_AUTO, "problema_descricao": "bateria de 45Ah arriou"}
    assert responde(PORTO, texto, caso, subservice="bateria")[0] == "45"


@pytest.mark.parametrize("estado", ["ura", "human_phase"])
@pytest.mark.parametrize("ref", sorted(r for r in PB.list_playbooks()
                                        if PB.get_playbook(r).get("line_kind") == "auto"))
def test_os_amperes_nunca_travam_em_nenhuma_seguradora(ref, estado):
    """🔴 G3 — a tela REAL, em TODO corredor de auto, na URA e com uma pessoa."""
    saiu, s = responde(ref, tela(*AMPERES_REAL), {}, subservice="bateria", state=estado)
    assert saiu == "60", (ref, estado, saiu, s.get("state"), s.get("reason"))
    assert s["state"] != "needs_human"


@pytest.mark.parametrize("forma", sorted(FORMAS))
def test_os_amperes_em_toda_forma_de_tela(forma):
    texto, esperado = FORMAS[forma]
    saiu, s = responde(PORTO, texto, {}, subservice="bateria")
    assert saiu == esperado, (forma, saiu, s.get("state"), s.get("reason"))
    assert s["state"] != "needs_human"


def test_os_amperes_com_o_caso_quebrado_nao_derrubam_nada():
    """Slot que não é texto, formatador que levantaria: continua saindo 60."""
    assert PB.responder_amperes(tela(*AMPERES_REAL), {"veiculo_descricao": object()}) == "60"
    assert PB.responder_amperes(None, None) == "60"
    # ⛔ linhas de CONVERSA não são opções: nunca sai "Boa tarde" como resposta.
    conversa = "Boa tarde" + chr(10) + "Sou a consultora" + chr(10) + "Você sabe quantos amperes tem a bateria?"
    assert PB.responder_amperes(conversa, {}) == "60"


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 §9.3 — os guardas CONSEGUEM ficar vermelhos
# ═════════════════════════════════════════════════════════════════════════════

def _sem_passo(ref, nome, monkeypatch):
    pb = copy.deepcopy(PB._PLAYBOOKS[ref])
    pb["ura_steps"] = [p for p in pb["ura_steps"] if p.get("step") != nome]
    monkeypatch.setitem(PB._PLAYBOOKS, ref, pb)


def test_CONTROLE_sem_o_passo_dos_amperes_a_tela_trava(monkeypatch):
    _sem_passo(PORTO, "amperes_da_bateria", monkeypatch)
    saiu, _s = responde(PORTO, tela(*AMPERES_REAL), {}, subservice="bateria")
    assert saiu != "60", "o guarda dos amperes não enxerga a falta do passo"


def test_CONTROLE_sem_o_passo_do_destino_a_origem_volta_a_ir_como_destino(monkeypatch):
    _sem_passo(HDI, "destino_digitado", monkeypatch)
    texto = tela("hdi-auto", "2548c9c7", r"digite o endere[çc]o seguindo o exemplo")
    assert responde(HDI, texto, CASO_AUTO)[0] == CASO_AUTO["local_atual"]


def test_CONTROLE_a_constante_e_o_rotulo_conseguem_divergir():
    """O guarda da justificativa compara duas coisas que CONSEGUEM ser diferentes:
    o rótulo `Sim` da azul não está na justificativa do blindado."""
    blindado = PB.match_ura_step(PB.get_playbook(HDI), tela("hdi-auto", "2548c9c7", r"blindado"))
    assert "nenhum dos dois" not in PB._norm(blindado["constante_justificada"])



# ═════════════════════════════════════════════════════════════════════════════
# 🔴 O CONSERTO ÚNICO — juiz (66) e red team (55), cegos um ao outro, convergentes
# ═════════════════════════════════════════════════════════════════════════════

def _com_passos(ref, texto, slots, passos, subservice="guincho"):
    """O motor com passos JÁ respondidos na sessão (`step_counts`), que é o que
    `reply_if_step_done` lê — a sessão de verdade chega aqui depois deles."""
    s = _sessao(ref, slots, subservice)
    s["step_counts"] = {p: 1 for p in passos}
    s = M.handle_insurer_message(s, texto)
    saidas = [t for t in (s.get("transcript") or []) if t.get("direction") == "out"]
    return (saidas[-1]["text"] if saidas else None), s


# ---- B1 · a recusa não vira "Sim", e a dúvida não vira recusa -------------------
TAXI_77983F63 = ("porto-auto", "77983f63", r"al[ée]m do guincho")


@pytest.mark.parametrize("frase", [
    "claro que não", "pode deixar", "preciso não", "quero não",
    "precisa não, meu filho vem me buscar", "não precisa", "Nao, obrigado"])
def test_B1_a_recusa_em_qualquer_posicao_e_nao(frase):
    """📊 As cinco primeiras saíam "Sim" na tela real (red team)."""
    saiu, s = responde(PORTO, tela(*TAXI_77983F63), {**CASO_AUTO, "taxi_apos_guincho": frase})
    assert saiu == "Não", (frase, saiu, s.get("reason"))


@pytest.mark.parametrize("frase", ["não sei ainda", "talvez", "sim, mas não agora",
                                   "pode ser", "acho que sim"])
def test_B1_a_duvida_vai_a_uma_pessoa(frase):
    """📊 "não sei ainda" saía "Não" — a dúvida virava recusa de um benefício coberto."""
    saiu, s = responde(PORTO, tela(*TAXI_77983F63), {**CASO_AUTO, "taxi_apos_guincho": frase})
    assert saiu is None and s["state"] == "needs_human", (frase, saiu, s.get("state"))


@pytest.mark.parametrize("frase,esperado", [
    ("claro que não", "Não"), ("não tá na rua, tá no estacionamento do prédio", "Sim"),
    ("não está em garagem nenhuma", "Não"), ("sim, no estacionamento", "Sim"),
    ("na rua, em frente ao estacionamento", None)])
def test_B1_a_garagem_le_o_lugar_e_a_negacao(frase, esperado):
    texto = tela("hdi-auto", "78b2de6f", r"est[áa] em uma garagem\?")
    saiu, s = responde(HDI, texto, {**CASO_AUTO, "veiculo_em_garagem": frase})
    assert saiu == esperado, (frase, saiu)
    assert s["state"] != "needs_human"


def test_B1_nao_esta_no_subsolo_nao_vira_sim():
    texto = tela("hdi-auto", "78b2de6f", r"garagem subsolo ou acima")
    saiu, _s = responde(HDI, texto, {**CASO_AUTO, "veiculo_nivel_rua": "não está no subsolo"})
    assert saiu != "Sim", saiu


# ---- B2 · a tela que SÓ AVISA não recebe resposta ------------------------------
@pytest.mark.parametrize("ref,arquivo,sessao,padrao,sub", [
    (PORTO, "porto-auto", "f4838bb3", r"valor da bateria", "bateria"),
    (YELUM, "yelum-auto", "e97943bd", r"GUINCHO GARAGEM", "guincho"),
])
def test_B2_o_aviso_de_preco_e_o_aviso_de_garagem_nao_sao_respondidos(ref, arquivo, sessao, padrao, sub):
    """📊 Na HEAD de antes: "60" no aviso de preço da bateria e "Sim" no aviso do
    GUINCHO GARAGEM. Na base `0c0e070`, nada — era regressão desta SPEC."""
    saiu, s = responde(ref, tela(arquivo, sessao, padrao),
                       {**CASO_AUTO, "veiculo_nivel_rua": "subsolo"}, subservice=sub)
    assert saiu is None and s["state"] != "needs_human", (saiu, s.get("state"))


def test_B2_a_rajada_do_preco_nao_passa_pelos_amperes():
    """Aviso de preço + "Posso continuar o agendamento? Sim/Não" na mesma rajada:
    quem responde NÃO é o passo dos amperes (ele via Sim/Não e mandava "Sim")."""
    rajada = (tela("porto-auto", "f4838bb3", r"valor da bateria") + "\n"
              + tela("porto-auto", "f4838bb3", r"posso continuar o agendamento"))
    passo = PB.match_ura_step(PB.get_playbook(PORTO), rajada, subservice="bateria")
    assert (passo or {}).get("step") != "amperes_da_bateria", passo


#: 🔴 O ALCANCE DE CADA PASSO NOVO NO ACERVO INTEIRO — medido em 29/09/2026,
#: HEAD do conserto, casando cada tela dos 16 corpora com CADA serviço do
#: corredor (não só o da etiqueta). ⚠️ É o guarda que o juiz pediu: a mutação
#: dele (âncora dos amperes alargada até "bateria") deu 2 falhas em 177. Aqui
#: um passo que passa a casar UMA sessão a mais fica vermelho.
ALCANCE = {'amperes_da_bateria': ('porto-auto:4830574a',),
 'animal_de_estimacao': ('hdi-auto:ea61eb64', 'hdi-auto:fa2ceb6f'),
 'cambio_travado': ('hdi-auto:2548c9c7', 'hdi-auto:78b2de6f', 'yelum-auto:19d73270'),
 'confirme_veiculo_do_seguro': ('allianz-residencial:0591c1d1',),
 'continuar_de_onde_parou': ('yelum-auto:01bf91c2',),
 'datas_disponiveis_porto': ('porto-auto:910b6295',),
 'destino_digitado': ('hdi-auto:2548c9c7',
                      'hdi-auto:4b2d0c2a',
                      'hdi-auto:83d2b9e3',
                      'yelum-auto:29ae4344',
                      'yelum-auto:705f915b',
                      'yelum-auto:9d2655e2',
                      'yelum-auto:a1c18e1c',
                      'yelum-auto:ba9f1970'),
 'destino_endereco_completo_porto': ('porto-auto:12203ed9',
                                     'porto-auto:51b2ed32',
                                     'porto-auto:77983f63',
                                     'porto-auto:a9560e3a'),
 'destino_so_a_rua': ('hdi-auto:2548c9c7',),
 'garagem_do_caso': ('hdi-auto:21a53457',
                     'hdi-auto:2548c9c7',
                     'hdi-auto:2e6df205',
                     'hdi-auto:4b2d0c2a',
                     'hdi-auto:78b2de6f',
                     'hdi-auto:83d2b9e3',
                     'yelum-auto:01bf91c2',
                     'yelum-auto:0a1a616e',
                     'yelum-auto:29ae4344',
                     'yelum-auto:56bd78f7',
                     'yelum-auto:705f915b',
                     'yelum-auto:7c841763',
                     'yelum-auto:b187d77a',
                     'yelum-auto:ba9f1970'),
 'garagem_subsolo_ou_acima': ('hdi-auto:4b2d0c2a',
                              'hdi-auto:78b2de6f',
                              'yelum-auto:56bd78f7',
                              'yelum-auto:705f915b',
                              'yelum-auto:ba9f1970'),
 'imediato_ou_agendado': ('porto-auto:4830574a',),
 'impedido_de_rodar': ('bradesco-auto:706df513', 'bradesco-auto:72af1ae1'),
 'informe_novamente_aviso': ('hdi-auto:2548c9c7',),
 'ja_tentou_abrir_aviso': ('yelum-auto:01bf91c2',),
 'manter_horario_oficina_fechada': ('porto-auto:12203ed9',),
 'nova_solicitacao_apos_protocolo': ('hdi-residencial:61b96027',),
 'o_proprio_segurado': ('porto-auto:4830574a',),
 'outro_servico_apos_protocolo': ('hdi-auto:fa2ceb6f',),
 'perfil_hdi_residencial': ('hdi-residencial:0a7c24ef',
                            'hdi-residencial:13379965',
                            'hdi-residencial:1c8d0849',
                            'hdi-residencial:26c0546f',
                            'hdi-residencial:61b96027',
                            'hdi-residencial:834cc238',
                            'hdi-residencial:b638adcd',
                            'hdi-residencial:ed46a953'),
 'pesquisa_de_satisfacao_porto': ('porto-auto:4830574a',),
 'placa_do_beneficio_residencial': ('allianz-residencial:0591c1d1',),
 'placa_e_modelo': ('porto-auto:4830574a',),
 'placa_nao_encontrada_familia': ('hdi-auto:4b2d0c2a', 'yelum-auto:7c841763'),
 'placa_nao_encontrada_tenta_cpf': ('yelum-auto:29ae4344',),
 'pode_ligar_qualquer_azul': ('azul-auto:2f0cd86a',),
 'policia_no_local_pane': ('bradesco-auto:706df513', 'bradesco-auto:72af1ae1'),
 'repique_somente_numeros': ('allianz-residencial:590b5940',),
 'retomar_agendamento_porto': ('porto-auto:12203ed9',),
 'rodas_livres': ('hdi-auto:2548c9c7', 'hdi-auto:78b2de6f'),
 'servicos_disponiveis_aviso': ('hdi-residencial:61b96027',),
 'taxi_alem_do_guincho': ('porto-auto:12203ed9',
                          'porto-auto:51b2ed32',
                          'porto-auto:77983f63',
                          'porto-auto:a9560e3a'),
 'taxi_pode_depois_aviso': ('porto-auto:12203ed9',
                            'porto-auto:51b2ed32',
                            'porto-auto:77983f63',
                            'porto-auto:a9560e3a'),
 'tipo_de_atendimento_veiculo': ('porto-auto:ba772444',),
 'veiculo_blindado_familia': ('hdi-auto:2548c9c7',
                              'hdi-auto:83d2b9e3',
                              'yelum-auto:705f915b',
                              'yelum-auto:7c841763',
                              'yelum-auto:b187d77a',
                              'yelum-auto:ba9f1970'),
 'veiculo_desatrelado': ('hdi-auto:4b2d0c2a', 'hdi-auto:fa2ceb6f', 'yelum-auto:6b4c37e4'),
 'veiculo_do_atendimento_porto': ('porto-auto:12203ed9',),
 'zona_rural_coordenada': ('hdi-auto:fa2ceb6f', 'yelum-auto:21243a23', 'yelum-auto:56bd78f7')}


def _alcance_de_hoje():
    import glob as _glob
    fora = {}
    for f in sorted(_glob.glob(str(CORPUS / "*.jsonl"))):
        seg, ramo = Path(f).stem.split("-", 1)
        ref = PB.resolve_playbook_ref(seg, ramo)
        pb = PB.get_playbook(ref) if ref else None
        if not pb:
            continue
        for linha in Path(f).read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            x = json.loads(linha)
            for sv in sorted(set(pb.get("subservices") or {}) | {x.get("servico") or ""}):
                passo = PB.match_ura_step(pb, x["text"], subservice=sv)
                if passo and passo.get("step") in ALCANCE:
                    fora.setdefault(passo["step"], set()).add(f"{seg}-{ramo}:{x['session_id']}")
    return fora


def test_B2_cada_passo_novo_casa_so_as_sessoes_medidas():
    hoje = _alcance_de_hoje()
    diferentes = {k: sorted(set(hoje.get(k, ())) ^ set(v)) for k, v in ALCANCE.items()
                  if set(hoje.get(k, ())) != set(v)}
    assert not diferentes, f"o alcance mudou (sessões a mais ou a menos): {diferentes}"
    assert ALCANCE["amperes_da_bateria"] == ("porto-auto:4830574a",)


# ---- B3 · a rua do destino da bradesco, e a conferência do destino -------------
def test_B3_a_rua_depois_da_pergunta_do_destino_e_a_do_destino():
    rua = tela("bradesco-auto", "a10d095d", r"nome da \*?rua")
    assert _com_passos(BRADESCO, rua, CASO_AUTO, ())[0] == CASO_AUTO["local_rua"]
    saiu, _s = _com_passos(BRADESCO, rua, CASO_AUTO, ("destino_rodovia",))
    assert saiu == CASO_AUTO["destino_rua"] != CASO_AUTO["local_rua"], saiu


def test_B3_a_conferencia_le_o_destino_do_veiculo_e_reprova_a_rua_errada():
    """📊 Antes: `ok: True, conferidos: ['origem']` — "Destino do veículo:" era
    lido como o campo `veiculo`, e o destino nunca era conferido."""
    resumo = tela("bradesco-auto", "a10d095d", r"s[óo] vamos confirmar").replace(
        "Origem: *Estrada {ENDERECO}", "Origem: *Rua das Flores, 100 - Centro, Joinville/SC")
    errado = resumo.replace("Destino do veículo: *Rua {ENDERECO}",
                            "Destino do veículo: *Rua das Flores, 200 - Joinville/SC")
    assert errado != resumo, "a tela real mudou de forma — o teste não mediria nada"
    v = PB.conferir_confirmacao(PB.get_playbook(BRADESCO), [errado], CASO_AUTO, "guincho",
                                parse_address=PB.parse_address_br)
    assert "destino" in v["conferidos"] and not v["ok"], v
    assert "veiculo" not in v["resumo"], v["resumo"]
    # CONTROLE: com o destino CERTO, a mesma conferência aprova.
    certo = resumo.replace("Destino do veículo: *Rua {ENDERECO}",
                           "Destino do veículo: *Avenida Brasil, 2000 - Joinville/SC")
    v2 = PB.conferir_confirmacao(PB.get_playbook(BRADESCO), [certo], CASO_AUTO, "guincho",
                                 parse_address=PB.parse_address_br)
    assert v2["ok"] and "destino" in v2["conferidos"], v2


# ---- B4 · o número do destino ---------------------------------------------------
@pytest.mark.parametrize("ref,arquivo,sessao", [
    (HDI, "hdi-auto", "fa2ceb6f"), (YELUM, "yelum-auto", "19d73270")])
def test_B4_o_numero_depois_da_pergunta_do_destino_e_o_do_destino(ref, arquivo, sessao):
    """📊 A ÚNICA pergunta de número destas sessões vem depois de "Para qual CEP
    devemos levar o veículo?" — e saía o número da ORIGEM (`reply_repeat`)."""
    texto = tela(arquivo, sessao, r"qual (?:[ée] )?o \*?n[úu]mero")
    saiu, _s = _com_passos(ref, texto, CASO_AUTO, ("destino_como",))
    assert saiu == CASO_AUTO["destino_numero"] != CASO_AUTO["local_numero"], saiu


def test_B4_CONTROLE_a_origem_continua_origem_mesmo_na_segunda_vez():
    """hdi 2548c9c7 (origem) e o caso de yelum 29ae4344: a tela vem DUAS vezes, as
    duas da origem — a contagem mandava o destino na segunda."""
    texto = tela("hdi-auto", "2548c9c7", r"qual (?:[ée] )?o \*?n[úu]mero")
    assert _com_passos(HDI, texto, CASO_AUTO, ())[0] == CASO_AUTO["local_numero"]
    assert _com_passos(HDI, texto, CASO_AUTO, ("endereco_numero",))[0] == CASO_AUTO["local_numero"]


# ---- B5 · polícia: só a PANE clara diz "Não" ------------------------------------
POLICIA = ("bradesco-auto", "72af1ae1", r"chamar a pol")


@pytest.mark.parametrize("relato", [
    "o motorista do outro carro fugiu", "fui atingido por outro veiculo", "o carro pegou fogo",
    "entraram no carro e levaram tudo", "me fecharam na estrada e saí da pista",
    "o carro está parado aqui",
    # a PANE e a OCORRÊNCIA na mesma frase: a ocorrência manda
    "bati o carro e o motor parou", "o carro pegou fogo no motor"])
def test_B5_relato_que_nao_e_pane_clara_vai_a_uma_pessoa(relato):
    """📊 As cinco primeiras saíam "Não" (lista negra). A sexta não diz o que
    houve — e lista BRANCA não afirma fato sobre o que não sabe."""
    saiu, s = responde(BRADESCO, tela(*POLICIA), {**CASO_AUTO, "problema_descricao": relato})
    assert saiu is None and s["state"] == "needs_human", (relato, saiu)


@pytest.mark.parametrize("relato", ["o carro morreu e não liga mais", "a bateria arriou",
                                    "o motor esquentou e parou"])
def test_B5_CONTROLE_a_pane_clara_continua_respondida(relato):
    saiu, _s = responde(BRADESCO, tela(*POLICIA), {**CASO_AUTO, "problema_descricao": relato})
    assert saiu == "Não", (relato, saiu)


# ---- G2 · G3 · M-b ----------------------------------------------------------------
def test_G2_opcoes_com_preco_nao_sao_escolhidas_pelo_robo():
    """Bateria com PREÇO na opção é aceite de custo: uma pessoa (SPEC-119)."""
    precos = ("Você sabe quantos amperes tem a bateria?\n*1 -* Bateria 45Ah - R$ 399,00\n"
              "*2 -* 60Ah - R$ 459,00\n*3 -* 90Ah - R$ 689,00")
    saiu, s = responde(PORTO, precos, {**CASO_AUTO, "veiculo_descricao": "HILUX 2.8 DIESEL"},
                       subservice="bateria")
    assert saiu is None and s["reason"] == "tela_que_decide:aceite_de_custo", (saiu, s.get("reason"))
    # e a faixa do rótulo não lê mais o preço como amperagem
    assert PB._faixa_do_rotulo("Bateria 45Ah - R$ 399,00") == (45, 45)


@pytest.mark.parametrize("veiculo,esperado", [("HILUX 2.8 DIESEL", "Não"), ("ONIX 1.0", "Sim"),
                                              ("", "Sim")])
def test_G2_a_tela_que_afirma_60_so_ouve_nao_de_quem_sabe(veiculo, esperado):
    eco = "A bateria do seu veículo é de 60 amperes. Está correto?\nBotão 1: Sim\nBotão 2: Não"
    saiu, _s = responde(PORTO, eco, {**CASO_AUTO, "veiculo_descricao": veiculo}, subservice="bateria")
    assert saiu == esperado, (veiculo, saiu)


@pytest.mark.parametrize("relato,ah", [
    ("estou no km 120 a caminho", 80), ("tentei dar partida umas 40 a 50 vezes", 80),
    ("a bateria é de 70", 70), ("bateria de 45Ah arriou", 45)])
def test_G3_so_amperagem_com_unidade_ou_da_bateria(relato, ah):
    assert PB.amperes_do_caso({"problema_descricao": relato, "veiculo_descricao": "HILUX DIESEL"}) == ah


@pytest.mark.parametrize("quando,esperado", [
    ("agora de manhã não dá, pode ser hoje à noite", None), ("agora", "Imediato"),
    ("o quanto antes", "Imediato"), ("amanhã às 9h", "Agendado")])
def test_Mb_imediato_ou_agendado(quando, esperado):
    assert PB._imediato_ou_agendado("", {"quando": quando}, "") == esperado
