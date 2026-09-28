# -*- coding: utf-8 -*-
"""DECIDE × CONDUZ — SPEC-119 F3, e a linha de controle são as OITO de 22/08.

> ## 🔴 Casar a tela não é responder certo. E travar por bobagem também não é.

O Founder, 27/09/2026: *"será que o GPT não está sendo podado? Muito melhor dar
liberdade para um agente inteligentíssimo do que deixar ele determinístico o
tempo todo e travar numa situação que seria fácil de responder."*

**Ele está metade certo, e este arquivo guarda as duas metades.**

## A metade em que ele está ERRADO — as OITO, e elas continuam vermelhas

📊 `CLAUDE.md` §9.5 e `backend/scripts/conferir_respostas.py` registram oito
passos que **casaram a tela e responderam errado**, todos com gate verde, nenhum
travando:

```
1  allianz resid  o_que_aconteceu         a tecla do ELETRICISTA na tela do ENCANADOR
2  allianz resid  aviso_fora_da_garantia  "1" onde 1 = "Até 10 anos" (AFIRMAVA a idade)
3  allianz resid  menu_qual_seguro        "1" num menu onde 2 = Condomínio
4  zurich  auto   vidros_orientacao       casava o CARDÁPIO e ENCERRAVA o caso
5  azul    auto   menu_inicial            casava ZERO — nem aparecia
6  azul    auto   cor_menu                "Outra cor", rótulo que não é do caso
7  tokio   (4 rotas)                      prometiam PROTOCOLO onde só há LINK
8  bradesco auto  captura de protocolo    o CEP do destino virava o nº do chamado
```

🔴 **Um modelo livre faria MAIS desses, não menos.** Cada um dos oito tem aqui
um teste que roda **O MOTOR** sobre a **TELA REAL** do acervo versionado, com o
`session_id` ao lado. Se um deles voltar, este arquivo fica vermelho.

## A metade em que ele está CERTO — e o controle que a torna segura

Onde a resposta só **CONDUZ** (navegar, confirmar sem consequência, ecoar um dado
que o caso já tem), exigir tela mapeada é desperdiçar a inteligência do agente.
Então a tela desconhecida que só conduz passa a ser respondida pelo agente — com
a tela REAL na frente, o contexto do caso, teto de tentativas e handoff.

🔴 **E o controle é o que dá direito à conclusão** (CLAUDE.md §9.2): as telas de
**aposta alta** — escolher o serviço/o seguro, aceitar custo — **viram handoff**,
e o cérebro não é convidado a opinar. Sem esse par, `conduz` seria afrouxamento
geral com nome novo.

## 📊 O que a separação mede, no acervo inteiro (27/09/2026)

```
passos de URA dos 14 corredores ....... 803   decide 337 · conduz 466
   dos `conduz`: 230 `noop` · 227 eco de dado do caso · 9 constante de navegação

telas DESCONHECIDAS distintas .......... 624   (corpus REGERADO pela F2, 27/09)
   seguem o caminho de ANTES ........... 594   (214 alternativa de conteúdo + 380 indefinidas)
   viram HANDOFF novo ..................  26   (14 escolha de serviço · 12 custo)
   o agente CONDUZ .....................   4
```

⚠️ **Quatro.** A cirurgia é estreita porque o acervo é assim: as telas "Sim/Não"
que nenhum passo casa **perguntam FATOS** — *"Houve vítimas no local?"*,
*"O veículo está impedido de rodar?"*, *"Os equipamentos estão em boas
condições?"*. `Sim` não tem significado próprio: herda o da pergunta. Por isso
`sim`/`nao` **não** estão no vocabulário da navegação do produto, e por isso a
liberdade que dá para dar hoje é pequena — e honesta.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"
PLAYBOOKS_PY = RAIZ / "app" / "services" / "corridor_playbooks.py"


def _carregar(nome: str, caminho: Path):
    """Carrega o módulo sem passar por `app.services.__init__` (fastembed).

    🔴 E DESFAZ o que injetou: `pytest tests/` roda outros arquivos na mesma
    sessão, e deixar um `app` falso em `sys.modules` os quebraria — em OUTRO
    arquivo, que é a pior forma de defeito de teste (foi o conserto `4ad9092`).
    """
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


M = _carregar("_spec119_motor", MOTOR_PY)
PB = _carregar("_spec119_playbooks", PLAYBOOKS_PY)


# ═════════════════════════════════════════════════════════════════════════════
# AS TELAS REAIS — cada uma com o arquivo e a sessão de onde saiu
#
# ⛔ Nenhuma foi escrita de cabeça (CLAUDE.md §9.4: *"o texto da tela vem do
#    acervo, não da imaginação"*). Onde o corpus versionado está MASCARADO
#    (`{ENDERECO}`, `{CEP}`), o valor foi restituído para um plausível — a FORMA
#    da tela é a real, e é ela que o motor lê.
# ═════════════════════════════════════════════════════════════════════════════

#: 📊 `allianz-residencial.jsonl`, sessão `9694992d`, servico=**encanador**.
TELA_DO_ENCANADOR = (
    "O que aconteceu?\n\n"
    "*1 -* Vazamento em dispositivo como torneira, sifão, cuba, registro, descarga, etc.\n"
    "*2 -* Vazamento em tubulação")

#: 📊 `allianz-residencial.jsonl`, sessão `448c6aae`, servico=ar_condicionado.
#:    A tela que PERGUNTA a idade — e onde "1" NÃO é "Continuar".
TELA_DA_IDADE_DO_APARELHO = (
    "Qual a idade de fabricação do aparelho/equipamento?\n\n"
    "*1 -* Até 10 anos\n*2 -* Mais de 10 anos de fabricação")

#: 📊 `allianz-residencial.jsonl`, sessão `c6b63f95`. O menu do RAMO da apólice.
TELA_DO_RAMO_DA_APOLICE = (
    "Qual seguro deseja utilizar?\n\n"
    "*1 - Residencial:* Para sua casa ou apartamento individual\n"
    "*2 - Condomínio:* Para áreas comuns e estrutura do condomínio\n"
    "*3 - Empresarial:* Para proteger seu negócio")

#: 📊 `zurich-auto.jsonl`, sessão `9f7dbd91`. O CARDÁPIO — a legenda de um item
#:    dele era entregue ao segurado como se fosse a orientação de vidros.
TELA_DO_CARDAPIO_DA_ZURICH = (
    "Aqui você pode de forma rápida e fácil:\n\n"
    "• *Assistência 24h*\n"
    "• *Assistência a vidros*: encontre informações sobre como pedir o reparo ou a "
    "troca de vidros, para-brisa, faróis e retrovisores de forma rápida.\n"
    "• *Carro reserva*: você receberá todas as orientações sobre como solicitar o "
    "seu carro reserva após o acionamento do seguro.\n"
    "• *Outros serviços*: como pequenos reparos ou manual do segurado.")

#: 📊 `azul-auto.jsonl`, sessão `6c5280df`, servico=guincho. O menu inicial que
#:    o corredor casava ZERO vezes.
TELA_DO_MENU_INICIAL_DA_AZUL = (
    "Selecione uma opção, por favor.\n"
    "Assistência emergencial\nGuincho, técnico e chaveiro\n"
    "Sinistro\nSinistro para roubo, furto ou acidente\n"
    "Vidros e faróis\nAtendimento para vidros, faróis e retrovisores\n"
    "Carro reserva\nSolicitar ou prorrogar locações")

#: 📊 `azul-auto.jsonl`, sessão `d70ced75`, servico=tecnico.
TELA_DA_COR_DA_AZUL = (
    "Por favor, agora informe a cor do veículo.\n"
    "Branco\nPrata\nCinza\nPreto\nAzul\nVermelho\nMarrom\nVerde\nAmarelo\nOutra cor")

#: 📊 `tokio-auto.jsonl`, sessão `d8a81c33`. A Tokio entrega LINK, não protocolo.
TELA_DO_LINK_DA_TOKIO = (
    "Clique no link para *AVISAR SINISTRO AUTOMÓVEL*\n"
    "https://autoatendimento.tokiomarine.com.br/aviso\n\n"
    "Clique no link para *ACOMPANHAR / AGENDAR VISTORIA DE SINISTRO AUTOMÓVEL:*\n"
    "https://autoatendimento.tokiomarine.com.br/vistoria")

#: 📊 `bradesco-auto.jsonl`, sessão `a10d095d`, servico=guincho — com o CEP
#:    restituído no formato que `corridor_playbooks.py:136` documenta como a
#:    origem do defeito: *"…areias, sao jose - sc, 88113-600"*.
TELA_DO_CEP_DO_BRADESCO = (
    "Só vamos confirmar as informações\n\n"
    "Origem: *Estrada Velha - Centro, Florianópolis - SC, 88010-100, Brazil*\n\n"
    "Destino do veículo: *Rua das Areias - Areias, São José - SC, 88113-600, Brazil*\n"
    "Referência: perto do mercado\n\n"
    "Posso confirmar a abertura da assistência?")

#: 📊 `mapfre-auto.jsonl`, sessão `b979f244`. Uma das QUATRO telas desconhecidas
#:    do acervo em que **todas** as opções só movem o fluxo — as outras três são
#:    `allianz-auto 5d34bab2`, `yelum-auto 01bf91c2` e `zurich-auto 25d956a3`.
TELA_QUE_SO_NAVEGA = "O que gostaria de fazer agora?\nBotão 1: Voltar\nBotão 2: Encerrar"

#: 📊 `allianz-auto.jsonl`, sessão `d2edf0dd`. A escolha do SERVIÇO.
TELA_QUE_ESCOLHE_O_SERVICO = (
    "Vamos lá! Informe o tipo de serviço:\n\n"
    "*1 -* Serviços Emergenciais (encanador, eletricista e chaveiro)\n"
    "*2 -* Para meus eletrodomésticos\n*3 -* Outros serviços")

#: 📊 `allianz-auto.jsonl`, sessão `4971b50b`, com o valor restituído. Ela decide
#:    PARA ONDE O CARRO VAI e mexe na franquia que o segurado paga.
TELA_QUE_PEDE_ACEITE_DE_CUSTO = (
    "Podemos levar o veículo para um oficina referenciada Allianz?\n\n"
    "Confira alguns dos benefícios que você pode ter:\n"
    "- Desconto de até R$ 1.500,00 na franquia\n"
    "- Franquia parcelada em até 3 vezes")

#: 📊 `hdi-auto.jsonl`, sessão `68f511d9` — com a grafia real da seguradora
#:    ("confimar", sem o `r`, a única ocorrência em 16 corpora).
TELA_QUE_ECOA_O_ENDERECO = (
    "Certo! Poderia confimar o endereço?\n"
    "*Rua:* Servidao das Palmeiras\n*Numero:* 314\n*Bairro:* Ingleses\n"
    "*Cidade:* Florianopolis")

ENDERECO_DO_CASO = "Servidao das Palmeiras, 314, Ingleses, Florianopolis"

#: 📊 `hdi-auto.jsonl`, sessão `bb5b0f11`. A tela que tem a FORMA de navegação e
#:    o preço de uma decisão: "Sim" aqui AFIRMA que houve vítima.
TELA_DE_FATO_COM_SIM_E_NAO = (
    "Houve vítimas no local?\nBotão 1: Sim\nBotão 2: Não\nBotão 3: Voltar")

CORREDORES = tuple(sorted(PB.list_playbooks()))


def _sessao(ref: str, slots=None, subservice: str = "guincho"):
    return {"state": "ura", "slots": dict(slots or {}), "subservice": subservice,
            "case_id": "c-119", "transcript": [], "playbook_ref": ref}


# ═════════════════════════════════════════════════════════════════════════════
# 1 · AS OITO RESPOSTAS ERRADAS HISTÓRICAS — a linha de controle desta fatia
# ═════════════════════════════════════════════════════════════════════════════

def test_01_a_tecla_do_eletricista_nao_responde_a_tela_do_encanador():
    """Defeito nº 1. 🔴 É a pergunta `C` do conferidor: passo de um ofício
    respondendo a tela de outro. A tela do encanador ESTAVA ÓRFÃ, então nem `A`
    nem `B` a pegariam — só o ofício."""
    pb = PB.get_playbook("allianz-residencial-whatsapp@v1")
    for oficio in ("eletricista", "chaveiro", "maquina_de_lavar", "eletrodomesticos"):
        passo = PB.match_ura_step(pb, TELA_DO_ENCANADOR, subservice=oficio)
        assert passo is None, (
            f"o passo {passo.get('step')!r} responde a tela do ENCANADOR quando o "
            f"caso é de {oficio} — é o defeito nº 1 do §9.5 de volta")
    # E o ofício certo continua respondendo: sem isto o teste passaria por vácuo.
    passo = PB.match_ura_step(pb, TELA_DO_ENCANADOR, subservice="encanador")
    assert passo and passo.get("only_subservices") == ["encanador"], passo


def test_02_a_idade_do_aparelho_nao_e_afirmada_pelo_corredor():
    """Defeito nº 2. A tela PERGUNTA a idade: "1" ali é *"Até 10 anos"*, e
    responder "1" AFIRMA um fato sobre o aparelho do segurado."""
    pb = PB.get_playbook("allianz-residencial-whatsapp@v1")
    passo = PB.match_ura_step(pb, TELA_DA_IDADE_DO_APARELHO,
                              subservice="maquina_de_lavar")
    assert passo, "nenhum passo casa a tela da idade — o defeito nº 5 no lugar do nº 2"
    reply = str(passo.get("reply") or "")
    assert "{" in reply, (
        f"o passo {passo['step']!r} responde a CONSTANTE {reply!r} a uma tela que "
        "PERGUNTA a idade do aparelho — defeito nº 2 do §9.5")
    assert PB.classe_do_passo(passo) == PB.CLASSE_DECIDE, passo.get("step")


def test_03_o_condominio_nao_vira_apolice_residencial():
    """Defeito nº 3. 📊 5 sessões de condomínio no acervo: "1" fixo abre um
    chamado que é recusado no local, porque o serviço não cobre unidade."""
    pb = PB.get_playbook("allianz-residencial-whatsapp@v1")
    passo = PB.match_ura_step(pb, TELA_DO_RAMO_DA_APOLICE)
    assert passo, "nenhum passo casa o menu do ramo da apólice"
    reply = str(passo.get("reply") or "")
    assert "{" in reply and reply.strip() != "1", (
        f"o passo {passo['step']!r} responde {reply!r} ao menu do RAMO — defeito nº 3")
    assert PB.classe_do_passo(passo) == PB.CLASSE_DECIDE, (
        f"{passo['step']!r} escolhe entre Residencial, Condomínio e Empresarial e "
        "não está classificado como `decide`")


def test_04_o_cardapio_da_zurich_nao_encerra_o_caso_de_vidros():
    """Defeito nº 4. O CARDÁPIO lista serviços com uma legenda cada; a legenda
    de vidros era entregue ao segurado como se fosse a orientação, e o caso
    encerrava. 🔴 Encerrar é `encaminha` — e nenhum encaminhamento pode nascer
    desta tela."""
    pb = PB.get_playbook("zurich-auto-whatsapp@v1")
    assert PB.detect_referral_step(pb, TELA_DO_CARDAPIO_DA_ZURICH) is None, (
        "o cardápio da Zurich dispara um ENCAMINHAMENTO — o caso de vidros "
        "encerraria com a legenda de um item de menu (defeito nº 4)")
    passo = PB.match_ura_step(pb, TELA_DO_CARDAPIO_DA_ZURICH, subservice="vidros")
    if passo is not None:
        assert passo.get("noop"), (
            f"o passo {passo['step']!r} RESPONDE ao cardápio da Zurich em vez de "
            "apenas reconhecê-lo")
        assert PB.classe_do_passo(passo) == PB.CLASSE_CONDUZ, passo.get("step")


def test_05_o_menu_inicial_da_azul_nao_casa_zero():
    """Defeito nº 5, e ele é o oposto dos outros: o passo não existia e a tela
    ficava muda. ⚠️ Silêncio é pior que resposta errada — nem o log registra."""
    pb = PB.get_playbook("azul-auto-whatsapp@v1")
    passo = PB.match_ura_step(pb, TELA_DO_MENU_INICIAL_DA_AZUL, subservice="guincho")
    assert passo is not None, (
        "o menu inicial da Azul voltou a casar ZERO passos — defeito nº 5")


def test_06_a_cor_do_veiculo_nao_e_um_rotulo_chutado():
    """Defeito nº 6. O corredor respondia a constante *"Outra cor"* — um rótulo
    que não é o do caso. Hoje a resposta vem do caso.

    ⚠️ **O RESIDUAL ESTÁ MEDIDO E REGISTRADO:** o valor do caso **não** é
    conferido contra a lista da tela. 📊 Com `veiculo_cor_rotulo="Bordô"` (cor
    que não está entre as dez da Azul), o motor responde "Bordô" e a URA rejeita.
    A trava `resolver_tecla` só cobre `{*_opcao}`, não `{*_rotulo}` — está no
    relatório da F3 como achado, e é de outra fatia."""
    pb = PB.get_playbook("azul-auto-whatsapp@v1")
    passo = PB.match_ura_step(pb, TELA_DA_COR_DA_AZUL, subservice="guincho")
    assert passo, "nenhum passo casa a tela da cor"
    reply = str(passo.get("reply") or "")
    assert "{" in reply, (
        f"o passo {passo['step']!r} responde a CONSTANTE {reply!r} à tela da cor — "
        "defeito nº 6 do §9.5")
    assert PB.classe_do_passo(passo) == PB.CLASSE_DECIDE, (
        "a tecla que escolhe a cor entre dez opções é `decide`")


def test_07_a_tokio_nao_promete_protocolo_porque_ela_entrega_link():
    """Defeito nº 7, em quatro rotas. 📊 A Tokio manda link; prometer protocolo é
    dizer ao segurado que existe um chamado que não existe."""
    pb = PB.get_playbook("tokio-auto-whatsapp@v1")
    capturado = PB.extract_capture_anchors(pb, TELA_DO_LINK_DA_TOKIO)
    assert "protocol" not in capturado, (
        f"a tela de LINK da Tokio produziu protocolo {capturado.get('protocol')!r} "
        "— defeito nº 7")
    assert capturado.get("tracking_link"), (
        "e o link tem de ser capturado — é ele o desfecho desta seguradora")
    assert PB.subservice_outcome(pb, "guincho") == PB.OUTCOME_ENCAMINHA, (
        "a Tokio deixou de ser `encaminha`: ela voltaria a prometer abertura")


def test_08_o_cep_do_destino_nao_vira_numero_do_chamado():
    """Defeito nº 8. 📊 `corridor_playbooks.py:136`: o "protocolo" entregue ao
    segurado era o **CEP do destino do guincho** — e o Bradesco não emite
    protocolo neste canal."""
    pb = PB.get_playbook("bradesco-auto-whatsapp@v1")
    capturado = PB.extract_capture_anchors(pb, TELA_DO_CEP_DO_BRADESCO)
    assert "protocol" not in capturado, (
        f"o CEP virou protocolo ({capturado.get('protocol')!r}) — defeito nº 8")


def test_09_CONTROLE_a_ancora_de_protocolo_CONSEGUE_capturar():
    """🔴 CLAUDE.md §9.3: *"quando o teste comparar duas coisas, prove que elas
    CONSEGUEM ser diferentes"*. Sem esta linha, os testes 7 e 8 passariam com uma
    âncora quebrada que não captura nada em nenhuma tela."""
    pb = PB.get_playbook("bradesco-auto-whatsapp@v1")
    # 📊 A forma real do resumo da família: `*Assistência:* 9666474`.
    capturado = PB.extract_capture_anchors(
        pb, "*Resumo da solicitação*\n*Placa:* AAA0926\n*Assistência:* 9662631")
    assert capturado.get("protocol") == "9662631", (
        f"a âncora de protocolo não captura nem o protocolo real: {capturado!r}")


# ═════════════════════════════════════════════════════════════════════════════
# 2 · TODO PASSO DE URA TEM UMA CLASSE, E A DECLARAÇÃO É CONFERIDA
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ref", CORREDORES)
def test_10_todo_passo_tem_classe(ref):
    """Nenhum passo fica sem classe, e a classe é uma das duas."""
    pb = PB.get_playbook(ref)
    passos = pb.get("ura_steps") or []
    assert passos, f"{ref} sem passos de URA"
    for passo in passos:
        classe = PB.classe_do_passo(passo)
        assert classe in (PB.CLASSE_DECIDE, PB.CLASSE_CONDUZ), (
            f"{ref}/{passo.get('step')}: classe {classe!r}")


@pytest.mark.parametrize("ref", CORREDORES)
def test_11_nenhuma_declaracao_de_conduz_contradiz_a_evidencia(ref):
    """🔴 O GUARDA DA MUTAÇÃO. Declarar `conduz` num passo que DECIDE é pior que
    não declarar nada: é a declaração que autoriza o agente a responder sozinho.

    📊 Provado por mutação em 27/09/2026: marcar `"classe": "conduz"` em
    `menu_qual_seguro_tres_opcoes` (o menu do RAMO da apólice) deixa este teste
    VERMELHO com *"responde a TECLA DE MENU `{qual_seguro_opcao}`"*."""
    contraditorios = PB.passos_com_classe_contraditoria(PB.get_playbook(ref))
    assert not contraditorios, (
        f"{ref}: passo(s) declarados `conduz` cuja evidência diz `decide`: "
        + "; ".join(f"{p} — {porque}" for p, porque in contraditorios))


def test_12_CONTROLE_o_guarda_da_classe_CONSEGUE_ficar_vermelho():
    """Sem isto, o teste acima é um carimbo: uma função que devolvesse sempre
    `[]` passaria nos 14 corredores. 🔴 Aqui a mutação é aplicada de verdade, em
    memória, sobre os quatro caminhos que tornam uma declaração falsa."""
    casos = [
        ({"step": "ramo", "classe": "conduz", "reply": "{qual_seguro_opcao}"},
         "TECLA DE MENU"),
        ({"step": "risco", "classe": "conduz", "reply": "{x}", "sem_chute": True},
         "sem_chute"),
        ({"step": "menu", "classe": "conduz", "reply": "Assistência emergencial"},
         "vocabulário da navegação"),
        ({"step": "enc", "classe": "conduz", "reply": "", "referral": True},
         "encaminhamento"),
    ]
    for passo, esperado in casos:
        achados = PB.passos_com_classe_contraditoria({"ura_steps": [passo]})
        assert achados, f"a mutação {passo!r} passou batida pelo guarda"
        assert esperado in achados[0][1], (achados, esperado)
    # E o CONTRASTE: um `conduz` honesto passa. Se nem ele passasse, o guarda
    # estaria reprovando a classe inteira em vez da declaração falsa.
    honestos = {"ura_steps": [
        {"step": "aviso", "classe": "conduz", "reply": "", "noop": True},
        {"step": "cpf", "classe": "conduz", "reply": "{titular_cpf}"},
        {"step": "segue", "classe": "conduz", "reply": "Continuar"},
    ]}
    assert PB.passos_com_classe_contraditoria(honestos) == []


def test_13_sim_e_nao_nao_sao_navegacao():
    """🔴 A decisão mais importante da fatia, e ela é medida.

    `Sim` não tem significado próprio: herda o da pergunta. 📊 As telas reais em
    que ele AFIRMA UM FATO: *"Os equipamentos para troca estão no veículo e em
    boas condições?"* (allianz-auto c6fff008) · *"O veículo está impedido de
    rodar?"* (bradesco 72af1ae1) · *"Houve vítimas no local?"* (hdi bb5b0f11).

    ⚠️ `scripts/conferir_respostas.py::_NAVEGACAO` (a régua offline) inclui
    "sim", "nao" e "confirmar". Para medir a FORMA de uma declaração isso passa;
    para AUTORIZAR o produto a responder, não."""
    for rotulo in ("Sim", "SIM", "Não", "nao", "Sim, pode", "Confirmar", "Confirmo"):
        assert not PB.rotulo_e_de_navegacao(rotulo), (
            f"{rotulo!r} entrou no vocabulário da navegação — a tela "
            "'Houve vítimas no local? 1-Sim 2-Não' viraria `conduz`")
    for rotulo in ("Continuar", "Voltar", "Sair", "Voltar ao menu", "Encerrar",
                   "Mais opções"):
        assert PB.rotulo_e_de_navegacao(rotulo), f"{rotulo!r} deixou de navegar"
    # =====================================================================
    # 🔴 `Abrir novo atendimento` SAIU DAQUI — e a lição MIGROU (CLAUDE.md §9.3)
    # =====================================================================
    #
    # Esta linha afirmava que *"Abrir novo atendimento"* NAVEGA. Era verdade
    # até deixar de ser: 📊 medido em 28/09/2026 na tela real
    # `yelum-auto.jsonl`, sessão `01bf91c2` — *"Você gostaria de abrir um novo
    # atendimento ou continuar de onde parou?"* —, `classe_da_tela` respondia
    # `conduz/navegacao` **por causa deste rótulo**, e o prompt do modelo
    # recebia *"⛔ NÃO responda NAO_SEI aqui"*. Abrir um segundo atendimento
    # perde o protocolo do primeiro.
    #
    # ⛔ A afirmação não foi apagada: ela foi INVERTIDA e ganhou o porquê. Manter
    #    a versão vencida ensinaria a ignorar teste.
    for rotulo in ("Abrir novo atendimento", "Novo atendimento", "Outro serviço",
                   "Outros serviços"):
        assert not PB.rotulo_e_de_navegacao(rotulo), (
            f"🔴 {rotulo!r} voltou a NAVEGAR — a tela 'abrir um novo atendimento "
            f"ou continuar de onde parou?' volta a ser `conduz`, e com ela a rede "
            f"de segurança do NAO_SEI é desligada por instrução")
    # 🔴 CONTROLE: rótulo vazio NÃO navega. A régua offline trata vazio como
    #    navegação; aqui, um rótulo que ninguém leu não autoriza nada.
    assert not PB.rotulo_e_de_navegacao("")


# ═════════════════════════════════════════════════════════════════════════════
# 3 · A TELA DESCONHECIDA QUE CONDUZ — e o controle que a torna segura
# ═════════════════════════════════════════════════════════════════════════════

def test_20_a_tela_de_navegacao_desconhecida_e_conduzida_pelo_agente():
    """A tela que só navega deixa de gastar uma rodada de recusa do modelo.

    🔴 Antes, ela ia para a fase humana com a orientação do corredor dizendo
    *"se for CONFIRMAR/ABRIR, não confirme"* e a regra *"se não der para deduzir,
    NAO_SEI"* — e `NAO_SEI` é `model_declined`, que em duas telas seguidas chama
    uma pessoa. Agora o prompt diz que ela CONDUZ."""
    saida = M.handle_insurer_message(_sessao("mapfre-auto-whatsapp@v1"),
                                     TELA_QUE_SO_NAVEGA)
    assert saida.get("state") != "needs_human", (
        f"a tela que só navega travou: {saida.get('reason')}")
    conduzindo = saida.get("conduzindo") or {}
    assert conduzindo.get("porque"), "o motor não marcou a tela como conduzida"
    assert conduzindo.get("opcoes") == ["Voltar", "Encerrar"], conduzindo
    prompt = M.build_human_phase_messages(saida, TELA_QUE_SO_NAVEGA)["user"]
    assert "APENAS CONDUZ" in prompt and "NÃO responda NAO_SEI aqui" in prompt, (
        "a instrução de conduzir não chegou ao prompt do agente")


def test_21_CONTROLE_a_tela_que_escolhe_servico_NAO_e_respondida_pelo_agente():
    """🔴 A LINHA DE CONTROLE DA FATIA. Sem ela, `conduz` é afrouxamento geral.

    A tela desconhecida que escolhe o serviço vira handoff, e o cérebro **não** é
    convidado a opinar: `falta_para_a_ura` (que alimenta o modelo) fica vazio, e
    o motivo vai em `motivo_legivel` (que a PESSOA lê)."""
    saida = M.handle_insurer_message(_sessao("allianz-auto-whatsapp@v1"),
                                     TELA_QUE_ESCOLHE_O_SERVICO)
    assert saida.get("state") == "needs_human", saida.get("state")
    assert saida.get("reason") == "tela_que_decide:escolhe_o_servico", saida.get("reason")
    assert not saida.get("conduzindo")
    assert not saida.get("falta_para_a_ura"), (
        "o caminho da tela que DECIDE alimentou o cérebro — seria o mesmo chute "
        "com um parágrafo de justificativa")
    assert "serviço" in (saida.get("motivo_legivel") or {}).get("rotulo", "")


def test_22_a_tela_de_aceite_de_custo_e_sempre_handoff():
    """📊 A tela real da allianz-auto (4971b50b) decide PARA ONDE O CARRO VAI e
    mexe na franquia que o segurado paga — e nenhum passo a casa."""
    saida = M.handle_insurer_message(_sessao("allianz-auto-whatsapp@v1"),
                                     TELA_QUE_PEDE_ACEITE_DE_CUSTO)
    assert saida.get("state") == "needs_human", saida.get("state")
    assert saida.get("reason") == "tela_que_decide:aceite_de_custo", saida.get("reason")
    assert not saida.get("conduzindo")


def test_23_CONTROLE_a_tela_que_so_confirma_o_endereco_ja_coletado_e_conduzida():
    """🔴 O PAR DO TESTE 22, e ele prova que o veto do custo não é uma peneira
    que pega tudo: a mesma forma de tela — pergunta, "Sim/Não" implícito,
    confirmação — CONDUZ quando o que ela repete é um dado que o caso já tem."""
    pb = PB.get_playbook("hdi-auto-whatsapp@v1")
    classe = M.classe_da_tela(pb, TELA_QUE_ECOA_O_ENDERECO,
                              slots={"local_atual": ENDERECO_DO_CASO})
    assert classe["classe"] == PB.CLASSE_CONDUZ, classe
    assert classe["chave"] == "eco_de_dado", classe
    assert not classe["handoff"]


def test_24_CONTROLE_o_eco_depende_do_ECO_e_nao_das_palavras():
    """A MESMA tela, com o caso tendo OUTRO endereço, deixa de ser eco.

    🔴 Sem esta linha, o teste 23 estaria provando que a palavra "confirmar"
    autoriza o agente — e não que o produto reconheceu o próprio dado de volta."""
    pb = PB.get_playbook("hdi-auto-whatsapp@v1")
    outro = M.classe_da_tela(pb, TELA_QUE_ECOA_O_ENDERECO,
                             slots={"local_atual": "Rua Vinte e Cinco, 90, Centro"})
    assert outro["classe"] != PB.CLASSE_CONDUZ, outro
    vazio = M.classe_da_tela(pb, TELA_QUE_ECOA_O_ENDERECO, slots={})
    assert vazio["classe"] != PB.CLASSE_CONDUZ, vazio


def test_25_CONTROLE_a_tela_que_abre_o_chamado_nao_conduz_mesmo_ecoando():
    """📊 `bradesco 72af1ae1` ecoa origem e destino E pergunta *"posso confirmar
    a ABERTURA da sua assistência?"*. Ela não está conduzindo: está abrindo."""
    pb = PB.get_playbook("bradesco-auto-whatsapp@v1")
    classe = M.classe_da_tela(pb, TELA_DO_CEP_DO_BRADESCO,
                              slots={"local_atual": "Estrada Velha - Centro, Florianópolis"})
    assert classe["classe"] != PB.CLASSE_CONDUZ, classe


def test_26_CONTROLE_a_tela_que_pergunta_um_FATO_nao_conduz():
    """*"Houve vítimas no local? 1-Sim 2-Não"* tem a forma de navegação e o preço
    de uma decisão. Ela segue o caminho de antes — nunca `conduz`."""
    pb = PB.get_playbook("hdi-auto-whatsapp@v1")
    classe = M.classe_da_tela(pb, TELA_DE_FATO_COM_SIM_E_NAO)
    assert classe["classe"] != PB.CLASSE_CONDUZ, classe


def test_27_CONTROLE_a_classificacao_CONSEGUE_dar_as_tres_respostas():
    """🔴 CLAUDE.md §9.3: uma função que devolvesse sempre `indefinida` passaria
    em quase tudo acima — inclusive nos controles."""
    pb = PB.get_playbook("hdi-auto-whatsapp@v1")
    respostas = {
        M.classe_da_tela(pb, TELA_QUE_SO_NAVEGA)["classe"],
        M.classe_da_tela(pb, TELA_QUE_ESCOLHE_O_SERVICO)["classe"],
        M.classe_da_tela(pb, "Estamos verificando as informações, um momento.")["classe"],
    }
    assert respostas == {PB.CLASSE_CONDUZ, PB.CLASSE_DECIDE, PB.CLASSE_INDEFINIDA}, (
        f"a classificação não consegue produzir as três respostas: {respostas}")


def test_28_a_maioria_das_telas_desconhecidas_segue_o_caminho_de_antes():
    """⚠️ A cirurgia é ESTREITA, e este teste é o que impede alguém de alargá-la
    sem medir. 📊 Das 542 telas desconhecidas do acervo, 517 não mudam de
    comportamento. Um padrão novo que mande metade do produto para uma pessoa
    desfaria a decisão do Founder de 05/08/2026 (*"o cérebro dá conta de uma URA
    que MUDOU"*) — e a Regina receberia handoff porque a seguradora trocou uma
    palavra do menu.

    📊 27/09/2026, sobre o corpus REGERADO pela F2: 624 telas desconhecidas
    distintas, 594 sem mudança de comportamento."""
    avisos = [
        "Estamos verificando as informações, um momento.",              # zurich
        "O telefone digitado não é válido.",                            # allianz-auto
        "Obrigado por entrar em contato!\nQualquer coisa estou sempre aqui!",  # alfa
        "Essas são as informações do seu pagamento:",                   # zurich 4118ba36
    ]
    pb = PB.get_playbook("zurich-auto-whatsapp@v1")
    for tela in avisos:
        classe = M.classe_da_tela(pb, tela)
        assert not classe["handoff"], (
            f"um aviso informativo virou handoff: {tela!r} → {classe!r}")
        assert classe["classe"] == PB.CLASSE_INDEFINIDA, (tela, classe)


# ═════════════════════════════════════════════════════════════════════════════
# 4 · O TETO, E O MOTIVO EM PORTUGUÊS
# ═════════════════════════════════════════════════════════════════════════════

def test_30_o_teto_de_telas_conduzidas_vira_handoff_com_motivo_em_portugues():
    """Conduzir é levar o fluxo adiante esperando que o corredor volte a
    reconhecer a tela. Se ele não volta, não é condução: é passeio."""
    sessao = _sessao("mapfre-auto-whatsapp@v1")
    for _ in range(PB and M.TETO_DE_TELAS_CONDUZIDAS or 3):
        sessao = M.handle_insurer_message(sessao, TELA_QUE_SO_NAVEGA)
        assert sessao.get("state") != "needs_human", sessao.get("reason")
        sessao["pending_insurer_messages"] = []
    sessao = M.handle_insurer_message(sessao, TELA_QUE_SO_NAVEGA)
    assert sessao.get("state") == "needs_human", sessao.get("state")
    assert sessao.get("reason") == "conducao_esgotada", sessao.get("reason")
    assert not sessao.get("conduzindo"), (
        "o handoff manteve a licença de conduzir gravada na sessão")
    # 🔴 O guarda do produto exige que TODA família de motivo tenha frase.
    frase = M.motivo_em_portugues(sessao["reason"])
    assert "conducao_esgotada" not in frase and "_" not in frase, frase
    assert "telas de navegação" in frase, frase
    assert "telas de navegação seguidas" in (sessao.get("motivo_legivel") or {})["rotulo"]


def test_31_o_passo_reconhecido_zera_o_contador():
    """⚠️ O teto é de telas SEGUIDAS. Sem zerar, um acionamento longo e saudável
    esgotaria o teto por acumulação — e handoff por acumulação é handoff que
    ninguém entende."""
    sessao = M.handle_insurer_message(_sessao("mapfre-auto-whatsapp@v1"),
                                      TELA_QUE_SO_NAVEGA)
    assert sessao.get("telas_conduzidas") == 1
    sessao["pending_insurer_messages"] = []
    # 📊 A tela REAL que o corredor da mapfre conhece — `mapfre-auto.jsonl`,
    #    sessão `b03a6b30`, passo `avisos_informativos_mapfre`.
    conhecida = ("Lembrando que você pode digitar *SAIR* a qualquer momento para "
                 "encerrar este atendimento. 😉")
    pb = PB.get_playbook("mapfre-auto-whatsapp@v1")
    assert PB.match_ura_step(pb, conhecida, subservice="guincho"), (
        "a tela de aviso da mapfre deixou de casar passo — o CONTROLE deste "
        "teste evaporou e ele passaria por vácuo")
    sessao = M.handle_insurer_message(sessao, conhecida)
    assert sessao.get("telas_conduzidas") == 0, (
        "o corredor voltou a reconhecer a tela e o contador de telas conduzidas "
        f"seguidas NÃO zerou: {sessao.get('telas_conduzidas')}")


def test_32_as_duas_familias_novas_nao_vazam_nome_de_chave_no_cartao():
    """📊 R11 do Founder: o que é lido por gente sai em frase. `loop_guard` não
    diz o que houve; `tela_que_decide` também não."""
    for motivo in ("tela_que_decide", "tela_que_decide:aceite_de_custo",
                   "tela_que_decide:escolhe_o_servico", "conducao_esgotada"):
        frase = M.motivo_em_portugues(motivo)
        assert frase and "_" not in frase, (motivo, frase)
        assert frase != M._MOTIVOS_EM_PORTUGUES["handoff"], (
            f"{motivo!r} caiu na frase genérica — ele não tem tradução própria")
