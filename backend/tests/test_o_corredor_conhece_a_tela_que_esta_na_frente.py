"""O corredor conhece a tela que está na frente dele.

📊 04/08/2026. Quatro corredores foram medidos contra `observed_events` — o que
a seguradora REALMENTE escreveu, não o que o playbook supunha. Os quatro
perdiam entradas reais, e cada um perdia de um jeito diferente:

    azul       a tela que ABRE o serviço não freava, e o cancelamento
               declarado ("4") seria rejeitado pela lista que está na frente
    allianz    o formato de protocolo MAIS COMUM (`*Protocolo N.°:*`) não
               era capturado pelo corredor residencial — o de auto capturava
    allianz    o menu que escolhe o PROFISSIONAL não existia no playbook, e
               `desentupimento`, que é a opção 3 dele, não era serviço declarado
    hdi        metade das aparições do menu de serviço não casava, porque a
               URA tem duas redações da mesma pergunta

O que os quatro têm em comum não é o defeito, é a CAUSA: a âncora foi escrita
uma vez, contra uma captura, e nunca foi conferida contra o acervo. Uma URA que
muda de redação — ou uma seguradora que troca de bot — não quebra nada com
erro: ela faz o corredor emudecer, com o cronômetro da URA correndo.

E cada guarda aqui é DIFERENCIAL, com linha de controle (CLAUDE.md §9.2): a
âncora ANTIGA roda contra a mesma sonda que a nova. A conclusão só vale quando
a antiga REPROVA e a nova aprova — e onde a antiga acertava, ela precisa
continuar acertando, senão o conserto trocou um buraco por outro.

    python backend/tests/test_o_corredor_conhece_a_tela_que_esta_na_frente.py
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

_falhas: list[str] = []


def checar(condicao: bool, descricao: str, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  FALHA {descricao}" + (f" — {detalhe}" if detalhe else ""))
        _falhas.append(descricao)


def _carregar(rel: str, nome: str):
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    for pkg in ("app", "app.services"):
        if pkg not in sys.modules:
            casca = types.ModuleType(pkg)
            casca.__path__ = [str(RAIZ / pkg.replace(".", "/"))]  # type: ignore[attr-defined]
            sys.modules[pkg] = casca
    spec = importlib.util.spec_from_file_location(nome, RAIZ / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


PB = _carregar("app/services/corridor_playbooks.py", "cp_telas")
DISPATCH = _carregar("app/services/insurer_dispatch_service.py", "ids_telas")

# ATUALIZADO em 04/08/2026 (P-90), CLAUDE.md §9.3 — `DISPATCH_FINALIZE_MODE`
# nasce em `live`. O freio de finalização era o padrão porque o Founder testava
# no próprio celular; a decisão dele foi que a única trava passa a ser o agente
# desligado.
#
# `o_modo_teste_da_azul_cancela_de_verdade` continua sendo exatamente o que o
# nome diz — o MODO TESTE. Ele só passa a armá-lo em vez de herdá-lo.
os.environ["DISPATCH_FINALIZE_MODE"] = "test"


# ---------------------------------------------------------------------------
# As TELAS REAIS. Copiadas de `observed_events` (projeto dcajcvlzcjbmyapmklil),
# com a contagem que cada uma tinha em 04/08/2026. Nada aqui é redigido por
# nós: mudar uma vírgula é inventar a seguradora.
# ---------------------------------------------------------------------------

# 📊 azul · 8 ocorrências · 07/04/2026 → 28/07/2026 · interactive.kind = list
AZUL_TELA_FINAL = (
    "Como você quer prosseguir?\n"
    "Confirmar solicitação\n"
    "Mudar localização atual\n"
    "Alterar local de destino\n"
    "Alterar dados de contato\n"
    "De quem está no local para acompanhar o serviço\n"
    "Sair e não agendar"
)
# 📊 azul · 8 ocorrências · o RESUMO que vem NA MENSAGEM ANTERIOR à tela final
AZUL_RESUMO = (
    "Antes de confirmar a solicitação, confira as informações 👇\n\n"
    "*Serviço*: Auto - Guincho para remoção de veículo\n"
    "*Localização*: R. Frida Melzer Silv#, ###, Palhoça, SC\n"
    "*Complemento*: N tem\n"
    "*Ponto de referência*: Não tem\n"
    "*Quem está no local*: Joel\n"
    "*Telefone principal*: (31) 97166-1484\n"
    "*Endereço de destino*: R. 70#, ###, Itapema, SC\n"
    "*Agendamento*: 19/06/2026"
)
# 📊 azul · 13 ocorrências · a tela de MAIOR frequência do corredor
AZUL_GEOCODE = "Está correto?\nBotão 1: Sim\nBotão 2: Não"
# 📊 azul · 2 ocorrências · o menu NUMERADO de telefone (não é a tela final)
AZUL_TELEFONE = "O número está correto?\n(47) 99999-8440\n\n*1* - Sim\n*2* - Não"
# 📊 azul · 2 ocorrências · 17/09/2025 → 26/12/2025 · a URA numerada de 2025
AZUL_TELA_FINAL_2025 = (
    "Tudo está correto?\n\n"
    "*1* - Sim\n*2* - Alterar localização\n*3* - Alterar quem está no local?\n"
    "*4* - Sair e não agendar"
)

# 📊 allianz · 15 com `N.°:` + 4 com `Nrº:` = 19 mensagens com `*Protocolo N`
ALLIANZ_RESUMO_PONTO = (
    "*RESUMO*\n\n"
    "*Protocolo N.°:* 52652744\n"
    "*Serviço:* *ENCANADOR*;\n"
    "*Endereço:* RUA ### GAIVO###, 61 - ####IANOP#### - SC\n"
    "*Tipo solicitação:* Agendado\n"
    "*Agendamento para:* Segunda-feira, 13/07/2026"
)
ALLIANZ_RESUMO_NR = (
    "*RESUMO*\n\n"
    "*Protocolo Nrº:* 52189904\n"
    "*Serviço:* REBOQUE;\n"
    "*Origem:* RUA BERNADINA BITTENCOURT MULLER, 201 - JARAGUA DO SUL - SC"
)
# O formato que a âncora ANTIGA JÁ pegava — a linha de controle da captura.
ALLIANZ_PROTOCOLO_ANTIGO = (
    "Sua assistência foi solicitada com sucesso! \n"
    "O número de protocolo é *51014008*\n\n"
    "É necessário um responsável maior de 18 anos para receber o técnico."
)

# 📊 allianz · 13 ocorrências · o menu que escolhe o OFÍCIO
ALLIANZ_MENU_PROFISSIONAL = (
    "De qual profissional?\n\n"
    "*1 -* Eletricista\n*2 -* Encanador\n*3 -* Desentupimento\n*4 -* Chaveiro\n*5 -* Voltar"
)
# 📊 allianz · 64 ocorrências · o menu ANTERIOR, que escolhe a FAMÍLIA
ALLIANZ_MENU_TIPO = (
    "Vamos lá! Informe o tipo de serviço:\n\n"
    "*1 -* Serviços Emergenciais (encanador, eletricista e chaveiro)\n"
    "*2 -* Para meus eletrodomésticos\n*3 -* Outros serviços"
)

# 📊 hdi 7 · yelum 3 — a redação que a âncora antiga NÃO pegava
HDI_MENU_CURTO = (
    "Qual o serviço que você precisa?\n"
    "Encanador\nSelecione esta opção se está com um vazamento aparente\n"
    "Desentupimento\nSelecione esta opção se precisa de um desentupimento residencial\n"
    "Eletricista\nSelecione esta opção se precisa de um reparo elétrico\n"
    "Chaveiro\nSelecione esta opção se está com problemas na entrada principal\nVoltar"
)
# 📊 hdi 7 · yelum 3 — a redação que ela pegava (linha de CONTROLE)
HDI_MENU_LONGO = (
    "SAIONARA DA SILVA, estamos prontos para seguir com o seu atendimento.\n\n"
    "Qual é o serviço que você precisa solicitar?\n"
    "Encanador\nSelecione para conserto de vazamentos como torneiras, sifões, etc\n"
    "Desentupimento\nSelecione se precisa de um desentupimento\n"
    "Eletricista\nSelecione se precisa de um reparo elétrico\nVoltar"
)

# As âncoras de ONTEM. Elas existem aqui por um motivo só: dar à conclusão o
# direito de existir. Um teste que só afirma que o código NOVO funciona não
# prova que o defeito existia — nem que o conserto foi o que o fechou.
ANCORA_ANTIGA_PROTOCOLO_RESIDENCIAL = (
    r"(?:n[úu]mero (?:da assist[êe]ncia|de protocolo) [ée]|protocolo)\s*:?\s*\*?(\d{5,12})"
)
ANCORA_ANTIGA_MENU_HDI = r"qual [ée] o servi[çc]o que voc[êe] precisa solicitar"
FREIO_ANTIGO_AZUL = [r"tudo est[áa] correto", r"posso confirmar", r"confirmar o agendamento"]


def _casa(padrao: str, texto: str) -> bool:
    return bool(re.search(padrao, PB._norm(texto), re.IGNORECASE | re.DOTALL))


def _passo(ref: str, texto: str, subservico: str = "") -> str:
    step = PB.match_ura_step(PB.get_playbook(ref) or {}, texto, subservice=subservico or None)
    return str((step or {}).get("step") or "")


# ===========================================================================
# 3.1 — A AZUL não tinha freio na tela que ABRE o serviço
# ===========================================================================

def a_azul_nao_freava_em_nada() -> None:
    """A linha de CONTROLE: o freio de ontem contra a tela de hoje.

    Se algum dos padrões antigos casasse esta tela, o defeito não seria "a Azul
    não freia" — e o conserto estaria creditado ao lugar errado.
    """
    casou = [p for p in FREIO_ANTIGO_AZUL if _casa(p, AZUL_TELA_FINAL)]
    checar(not casou,
           "CONTROLE: NENHUM freio antigo da Azul casava a tela real de 2026",
           f"casaram: {casou}")
    checar(_casa(FREIO_ANTIGO_AZUL[0], AZUL_TELA_FINAL_2025),
           "CONTROLE: e o freio antigo casava a tela de 2025 — ele não era inválido, ficou VENCIDO",
           "se nem isso casasse, a sonda estaria errada e o teste não provaria nada")


def a_azul_freia_na_tela_que_abre_o_servico() -> None:
    az = PB.get_playbook("azul-auto-whatsapp@v1") or {}
    checar(PB.detect_finalize_anchor(az, AZUL_TELA_FINAL) is not None,
           "a tela real de 2026 ('Como você quer prosseguir?') AGORA freia")
    checar(PB.detect_finalize_anchor(az, AZUL_TELA_FINAL_2025) is not None,
           "e a tela numerada de 2025 continua freando — o corredor não perdeu o que sabia")


def o_cancelamento_da_azul_e_aceitavel_pela_tela() -> None:
    """Freio que dispara e manda resposta rejeitada não cancela nada.

    A tela é `interactive.kind = list`: o que se responde é o RÓTULO. "4" não é
    rótulo de nada nela — e a prova está no próprio texto da tela.
    """
    az = PB.get_playbook("azul-auto-whatsapp@v1") or {}
    abort = str(az.get("finalize_abort_reply") or "")
    rotulos = [linha.strip() for linha in AZUL_TELA_FINAL.split("\n")[1:]]
    checar(abort in rotulos,
           f"o cancelamento da Azul ({abort!r}) É uma opção da tela real",
           f"opções: {rotulos}")
    checar("4" not in rotulos,
           "CONTROLE: e '4' (o valor de ontem) NÃO é opção nenhuma nesta tela",
           "se '4' estivesse na lista, a troca não teria motivo")


def a_azul_conhece_as_duas_telas_que_faltavam() -> None:
    """📊 21 mensagens reais (13 + 8) em que `match_ura_step` devolvia NENHUM."""
    checar(_passo("azul-auto-whatsapp@v1", AZUL_GEOCODE) == "endereco_correto",
           "a confirmação do geocode (13x) casa `endereco_correto`",
           f"casou: {_passo('azul-auto-whatsapp@v1', AZUL_GEOCODE)!r}")
    checar(_passo("azul-auto-whatsapp@v1", AZUL_RESUMO) == "resumo_solicitacao",
           "o RESUMO (8x) casa `resumo_solicitacao`",
           f"casou: {_passo('azul-auto-whatsapp@v1', AZUL_RESUMO)!r}")

    az = PB.get_playbook("azul-auto-whatsapp@v1") or {}
    resumo = PB.match_ura_step(az, AZUL_RESUMO)
    checar(bool(resumo and resumo.get("noop")),
           "e o RESUMO é NOOP — reconhecer não é responder",
           "responder ao resumo é confirmar a abertura um passo antes dela")


def a_ordem_dos_passos_da_azul_e_a_regra() -> None:
    """O passo GENÉRICO (`está correto?`) não pode comer os ESPECÍFICOS.

    `match_ura_step` devolve o PRIMEIRO que casa. As três telas contêm "está
    correto?", e as respostas certas são diferentes: "Sim" na lista de botões,
    "1" nos dois menus numerados. Responder "Sim" a um menu numerado é resposta
    inválida — e a URA encerra por inatividade sem erro nenhum no log.
    """
    checar(_passo("azul-auto-whatsapp@v1", AZUL_TELEFONE) == "telefone_correto",
           "'O número está correto?' continua caindo em `telefone_correto`",
           f"caiu em: {_passo('azul-auto-whatsapp@v1', AZUL_TELEFONE)!r}")
    checar(_passo("azul-auto-whatsapp@v1", AZUL_TELA_FINAL_2025) == "confirmar_tudo",
           "'Tudo está correto?' continua caindo em `confirmar_tudo`",
           f"caiu em: {_passo('azul-auto-whatsapp@v1', AZUL_TELA_FINAL_2025)!r}")

    # E a prova de que a ordem é o que sustenta isso: o passo genérico casa as
    # TRÊS telas quando testado sozinho. É ele que precisa vir por último.
    az = PB.get_playbook("azul-auto-whatsapp@v1") or {}
    generico = next((s for s in az["ura_steps"] if s.get("step") == "endereco_correto"), None)
    checar(generico is not None, "o passo genérico existe")
    if generico:
        pega_tudo = [t for t in (AZUL_GEOCODE, AZUL_TELEFONE, AZUL_TELA_FINAL_2025)
                     if _casa(generico["anchor"], t)]
        checar(len(pega_tudo) == 3,
               "CONTROLE: sozinha, a âncora genérica casaria as TRÊS telas",
               f"casou {len(pega_tudo)} de 3 — se casasse só uma, a ordem não importaria")
        nomes = [s.get("step") for s in az["ura_steps"]]
        checar(nomes.index("endereco_correto") > nomes.index("telefone_correto")
               and nomes.index("endereco_correto") > nomes.index("confirmar_tudo"),
               "por isso ela é consultada DEPOIS das específicas",
               f"ordem: {nomes[-5:]}")


def o_modo_teste_da_azul_cancela_de_verdade() -> None:
    """Pelo motor, ponta a ponta: freio → cancelamento → `test_aborted`."""
    slots = {
        "titular_cpf": "11122233344", "veiculo_placa": "ABC1D23", "titular_nome": "Cliente",
        "local_atual": "Rua X, 100, Florianópolis, SC", "local_destino": "Oficina Y, São José, SC",
        "problema_descricao": "pneu furado", "quando": "agora",
        "telefone_contato": "48999998888", "pessoa_no_local": "Cliente",
    }
    s = DISPATCH.new_dispatch_session(case_id="tela1", company_id="co",
                                      playbook_ref="azul-auto-whatsapp@v1",
                                      subservice="pneu", slots=slots)
    s = DISPATCH.start_dispatch(s)
    s = DISPATCH.handle_insurer_message(s, AZUL_RESUMO)
    saidas = [t.get("text") for t in s["transcript"] if t.get("direction") == "out"]
    checar(saidas == ["Olá"],
           "o motor NÃO responde ao RESUMO (noop de verdade, não só no dicionário)",
           f"respondeu: {saidas}")
    s = DISPATCH.handle_insurer_message(s, AZUL_TELA_FINAL)
    saidas = [t.get("text") for t in s["transcript"] if t.get("direction") == "out"]
    checar(s.get("state") == "test_aborted" and saidas[-1] == "Sair e não agendar",
           "e na tela final ele CANCELA com o rótulo que a lista aceita",
           f"estado={s.get('state')!r} última saída={saidas[-1]!r}")


# ===========================================================================
# 3.2 — O protocolo mais comum da Allianz não era capturado no residencial
# ===========================================================================

def a_ancora_antiga_perdia_o_protocolo_do_resumo() -> None:
    """CONTROLE: a âncora residencial de ontem contra os dois formatos reais."""
    for nome, texto in (("N.°:", ALLIANZ_RESUMO_PONTO), ("Nrº:", ALLIANZ_RESUMO_NR)):
        checar(not _casa(ANCORA_ANTIGA_PROTOCOLO_RESIDENCIAL, texto),
               f"CONTROLE: a âncora antiga NÃO capturava `*Protocolo {nome}*`",
               "se capturasse, o defeito medido não existiria")
    checar(_casa(ANCORA_ANTIGA_PROTOCOLO_RESIDENCIAL, ALLIANZ_PROTOCOLO_ANTIGO),
           "CONTROLE: e capturava o formato que ela conhecia ('O número de protocolo é *X*')",
           "sem isto, a sonda estaria errada e não haveria o que comparar")


def o_residencial_captura_os_dois_formatos_do_resumo() -> None:
    ar = PB.get_playbook("allianz-residencial-whatsapp@v1") or {}
    casos = [
        (ALLIANZ_RESUMO_PONTO, "52652744", "*Protocolo N.°:*"),
        (ALLIANZ_RESUMO_NR, "52189904", "*Protocolo Nrº:*"),
        (ALLIANZ_PROTOCOLO_ANTIGO, "51014008", "'O número de protocolo é *X*'"),
        ("O protocolo desse atendimento é: 51426858", "51426858", "'O protocolo desse atendimento é:'"),
    ]
    for texto, esperado, rotulo in casos:
        got = PB.extract_capture_anchors(ar, texto)
        checar(got.get("protocol") == esperado,
               f"o residencial captura o protocolo em {rotulo}",
               f"capturou: {got.get('protocol')!r} (esperado {esperado!r})")


def a_definicao_do_protocolo_e_uma_so() -> None:
    """Duas âncoras para o MESMO fato é a causa, não o sintoma.

    Enquanto o residencial tinha regex próprio, o corredor de auto capturava o
    protocolo e o residencial encerrava sem número — na mesma seguradora, no
    mesmo dia, no mesmo formato de mensagem.
    """
    ar = PB.get_playbook("allianz-residencial-whatsapp@v1") or {}
    aa = PB.get_playbook("allianz-auto-whatsapp@v1") or {}
    checar(ar["capture_anchors"]["protocol"] == aa["capture_anchors"]["protocol"]
           == PB._ANCORA_DE_PROTOCOLO,
           "residencial e auto leem a MESMA `_ANCORA_DE_PROTOCOLO`")

    # E ela não pode ter virado um coringa que casa qualquer número.
    for ruido in ("Conforme sistema, o segurado já utilizou os 2 protocolos de chaveiro",
                  "Bom dia! Tudo bem com você?",
                  "O prazo é de 30 dias corridos."):
        checar("protocol" not in PB.extract_capture_anchors(ar, ruido),
               f"e NÃO inventa protocolo em: {ruido[:38]}…",
               f"capturou: {PB.extract_capture_anchors(ar, ruido)}")

    # A SENHA não pode ter sido perdida na troca. 📊 O texto é o real, 11
    # ocorrências: só o corredor residencial captura senha de acesso, e trocar o
    # dicionário inteiro por `_AUTO_CAPTURE_ANCHORS` a apagaria em silêncio.
    senha = PB.extract_capture_anchors(
        ar, "O telefone registrado nesse atendimento para contato é o que estamos falando agora:\n"
            "*+55 (48) 99107-2089*.\n\nSua senha será os 4 últimos dígitos desse telefone *2089*")
    checar(senha.get("password") == "2089",
           "e a captura de SENHA (que só o residencial tem) sobreviveu à troca",
           f"capturou: {senha}")
    checar("password" not in (PB.get_playbook("allianz-auto-whatsapp@v1") or {})["capture_anchors"],
           "CONTROLE: o corredor de AUTO não tem senha — a troca foi de UM campo, não do dicionário",
           "se auto também tivesse, a checagem de cima não provaria nada")


# ===========================================================================
# 3.3 — A Allianz residencial não conhecia o menu que escolhe o ofício
# ===========================================================================

def o_menu_do_profissional_nao_existia() -> None:
    """CONTROLE: sem o passo novo, NADA no playbook casa esta tela.

    A prova roda contra o playbook REAL com o passo removido — não contra uma
    lembrança de como ele era.
    """
    ar = PB.get_playbook("allianz-residencial-whatsapp@v1") or {}
    sem_o_passo = dict(ar)
    sem_o_passo["ura_steps"] = [s for s in ar["ura_steps"] if s.get("step") != "menu_profissional"]
    checar(PB.match_ura_step(sem_o_passo, ALLIANZ_MENU_PROFISSIONAL) is None,
           "CONTROLE: sem `menu_profissional`, nenhum passo casa 'De qual profissional?'",
           f"casou: {(PB.match_ura_step(sem_o_passo, ALLIANZ_MENU_PROFISSIONAL) or {}).get('step')}")
    checar(PB.match_ura_step(sem_o_passo, ALLIANZ_MENU_TIPO) is not None,
           "CONTROLE: e o menu ANTERIOR sempre casou — o buraco era só o segundo",
           "se este também não casasse, o diagnóstico seria outro")


def cada_oficio_tem_a_tecla_do_menu_real() -> None:
    """A tecla vem do menu OBSERVADO, e a ordem dele é a verdade."""
    ar = PB.get_playbook("allianz-residencial-whatsapp@v1") or {}
    checar(_passo("allianz-residencial-whatsapp@v1", ALLIANZ_MENU_PROFISSIONAL) == "menu_profissional",
           "'De qual profissional?' casa `menu_profissional`")

    # A tecla declarada tem de bater com a POSIÇÃO no texto real da tela.
    esperado = {"eletricista": "1", "encanador": "2", "desentupimento": "3", "chaveiro": "4"}
    for oficio, tecla in esperado.items():
        sub = (ar.get("subservices") or {}).get(oficio) or {}
        checar(sub.get("profissional_opcao") == tecla,
               f"{oficio} → tecla {tecla} (a que está escrita no menu real)",
               f"declarado: {sub.get('profissional_opcao')!r}")
        rotulo = oficio if oficio != "eletrodomesticos" else "eletrodom"
        linha = f"*{tecla} -* {rotulo}"
        checar(PB._norm(linha) in PB._norm(ALLIANZ_MENU_PROFISSIONAL),
               f"e a tela real confirma essa posição: '{linha}'",
               "tecla que não está na tela é tecla inventada")

    # Eletrodoméstico sai pelo PRIMEIRO menu (opção 2) — a tela do profissional
    # não aparece nesse ramo, e declarar tecla ali seria adivinhar.
    ed = (ar.get("subservices") or {}).get("eletrodomesticos") or {}
    checar("profissional_opcao" not in ed,
           "eletrodomésticos NÃO declara tecla de profissional (a tela não aparece nesse ramo)",
           f"declarou: {ed.get('profissional_opcao')!r}")


def o_desentupimento_deixou_de_virar_handoff() -> None:
    """📊 Opção 3 do menu real, e não era serviço declarado."""
    ar = PB.get_playbook("allianz-residencial-whatsapp@v1") or {}
    hdi = PB.get_playbook("hdi-residencial-whatsapp@v1") or {}
    checar(PB.subservice_supported(ar, "desentupimento"),
           "desentupimento é serviço declarado na Allianz residencial")
    checar(PB.subservice_supported(hdi, "desentupimento"),
           "…como já era na HDI residencial — o mesmo trabalho nos dois corredores")
    faltando = PB.missing_slots_for_subservice(ar, "desentupimento", {})
    checar(PB.SUBSERVICO_INVALIDO not in faltando,
           "e ele não devolve mais o sentinela de handoff",
           f"devolveu: {faltando}")
    checar("desentupimento" in (ar.get("subservice_labels") or {}),
           "com rótulo próprio para o resumo ao especialista humano")


def a_tecla_do_menu_chega_aos_slots_sozinha() -> None:
    """Declarar a tecla no playbook não basta: ela tem de chegar ao passo.

    Antes, `new_dispatch_session` injetava `tipo_servico_opcao` pelo NOME. Uma
    segunda tecla declarada ficaria no playbook e nunca nos slots — o corredor
    pararia no menu que ele sabia responder, com `missing_slots`.
    """
    base = {
        "titular_cpf": "11122233344", "endereco_numero": "61", "telefone_contato": "48999998888",
        "problema_descricao": "ralo do banheiro entupido", "periodo_preferido": "tarde",
    }
    s = DISPATCH.new_dispatch_session(case_id="prof1", company_id="co",
                                      playbook_ref="allianz-residencial-whatsapp@v1",
                                      subservice="desentupimento", slots=dict(base))
    checar(s.get("state") == "ready_to_send",
           "com os dados do caso, o acionamento de desentupimento nasce PRONTO",
           f"estado={s.get('state')!r} faltando={s.get('missing_slots')}")
    checar(s["slots"].get("tipo_servico_opcao") == "1"
           and s["slots"].get("profissional_opcao") == "3",
           "as DUAS teclas chegaram aos slots sozinhas (regra do sufixo `_opcao`)",
           f"slots: {s['slots'].get('tipo_servico_opcao')!r} / {s['slots'].get('profissional_opcao')!r}")

    # E pelo motor: os dois menus, um depois do outro, respondidos.
    s = DISPATCH.start_dispatch(s)
    s = DISPATCH.handle_insurer_message(s, ALLIANZ_MENU_TIPO)
    s = DISPATCH.handle_insurer_message(s, ALLIANZ_MENU_PROFISSIONAL)
    saidas = [t.get("text") for t in s["transcript"] if t.get("direction") == "out"]
    checar(saidas[-2:] == ["1", "3"],
           "e o motor responde '1' à família e '3' ao ofício, na sequência real",
           f"saídas: {saidas}")

    # A tecla é do MOTOR: ela não pode virar pergunta ao segurado.
    ar = PB.get_playbook("allianz-residencial-whatsapp@v1") or {}
    faltando = PB.missing_slots_for_subservice(ar, "desentupimento", base)
    checar("profissional_opcao" not in faltando,
           "e ela NUNCA é cobrada do segurado (o `_opcao` é do motor, não do cliente)",
           f"faltando: {faltando}")


# ===========================================================================
# 3.4 — A HDI residencial perdia metade das aparições do menu
# ===========================================================================

def a_ancora_antiga_da_hdi_perdia_metade() -> None:
    """CONTROLE: uma redação casava, a outra não. É o defeito inteiro."""
    checar(_casa(ANCORA_ANTIGA_MENU_HDI, HDI_MENU_LONGO),
           "CONTROLE: a âncora antiga casava 'Qual é o serviço que você precisa solicitar?'",
           "se nem essa casasse, a sonda estaria errada")
    checar(not _casa(ANCORA_ANTIGA_MENU_HDI, HDI_MENU_CURTO),
           "CONTROLE: e NÃO casava 'Qual o serviço que você precisa?' — as duas são a MESMA tela",
           "se casasse, não haveria metade perdida")


def as_duas_redacoes_caem_no_mesmo_passo() -> None:
    for nome, texto in (("longa", HDI_MENU_LONGO), ("curta", HDI_MENU_CURTO)):
        casou = _passo("hdi-residencial-whatsapp@v1", texto)
        checar(casou == "menu_servico_residencial",
               f"a redação {nome} do menu cai em `menu_servico_residencial`",
               f"caiu em: {casou!r}")


def a_ancora_nova_da_hdi_nao_virou_coringa() -> None:
    """Afrouxar âncora é o conserto que costuma criar o próximo defeito."""
    hdi = PB.get_playbook("hdi-residencial-whatsapp@v1") or {}
    for ruido in (
        "Qual o serviço que você contratou na apólice?",
        "Você precisa de qual serviço? Digite abaixo.",
        "Bom dia! Em que posso ajudar?",
        "O serviço já foi concluído. Obrigado pelo contato!",
    ):
        casou = PB.match_ura_step(hdi, ruido)
        checar(casou is None or casou.get("step") != "menu_servico_residencial",
               f"texto que NÃO é o menu continua sem casar: {ruido[:40]}…",
               f"casou: {casou and casou.get('step')}")


def main() -> int:
    print(__doc__)
    print("== 3.1 · AZUL — o freio na tela que ABRE o servico ==")
    a_azul_nao_freava_em_nada()
    a_azul_freia_na_tela_que_abre_o_servico()
    o_cancelamento_da_azul_e_aceitavel_pela_tela()
    a_azul_conhece_as_duas_telas_que_faltavam()
    a_ordem_dos_passos_da_azul_e_a_regra()
    o_modo_teste_da_azul_cancela_de_verdade()

    print("\n== 3.2 · ALLIANZ residencial — o protocolo do RESUMO ==")
    a_ancora_antiga_perdia_o_protocolo_do_resumo()
    o_residencial_captura_os_dois_formatos_do_resumo()
    a_definicao_do_protocolo_e_uma_so()

    print("\n== 3.3 · ALLIANZ residencial — o menu que escolhe o oficio ==")
    o_menu_do_profissional_nao_existia()
    cada_oficio_tem_a_tecla_do_menu_real()
    o_desentupimento_deixou_de_virar_handoff()
    a_tecla_do_menu_chega_aos_slots_sozinha()

    print("\n== 3.4 · HDI residencial — as duas redacoes do mesmo menu ==")
    a_ancora_antiga_da_hdi_perdia_metade()
    as_duas_redacoes_caem_no_mesmo_passo()
    a_ancora_nova_da_hdi_nao_virou_coringa()

    print()
    if _falhas:
        print(f"VERMELHO — {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("O CORREDOR CONHECE A TELA QUE ESTA NA FRENTE DELE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
