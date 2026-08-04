"""O acionamento chega ao número — e o número chega ao segurado.

Por que este arquivo existe
---------------------------
📊 O `Nº do atendimento` nasce no **passo 7**, no TOPO da tela, ANTES da escolha
da loja (`docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` §7). Quando ele
aparece, **o pedido já existe na seguradora**. Três consequências, todas do mapa:

    capturar o protocolo NÃO PODE ESPERAR o fim do fluxo
    desistir depois daqui NÃO DESFAZ nada
    repetir o fluxo cria um SEGUNDO atendimento, não corrige o primeiro

E até 04/08/2026 o passo 7 nunca tinha sido alcançado: 📊 39 acionamentos, zero
protocolos. Com a trava `confirm=False` saindo, ele vai ser — e tudo o que vem
depois dele nunca foi exercitado uma única vez.

M0 · O que estava quebrado, MEDIDO antes de mexer
--------------------------------------------------
📊 04/08/2026, contra o texto literal do mapa, com a lista de rótulos de então
(`_PROTO` = protocolo | numero do atendimento | n do atendimento | solicitacao
registrada | atendimento n):

    has_protocol({"text": "Nº do atendimento: 22842291"})  ->  False
    has_protocol({"text": "N° do atendimento: 22842291"})  ->  True
    interpret_atendimento(".../passo5/<uuid>", <tela 7>)
        -> needs_human, {'stage': 'passo5'}, "parou em passo5"

**A causa é de uma letra**, e ela não se descobre lendo — só medindo:

    'º'  MASCULINE ORDINAL INDICATOR  -> NFKD 'o'  -> "No do atendimento"
    '°'  DEGREE SIGN                  -> NFKD '°'  -> some no ascii-ignore
                                                   -> "N do atendimento"

A lista tinha `"n do atendimento"` e **não** tinha `"no do atendimento"`. Ou
seja: reconhecia o sinal que o portal **não** usa e ignorava o que ele usa. A
tela que prova que o atendimento foi aberto seria registrada como *"parou em
passo5"* — o pior desfecho possível deste sistema, porque o segurado fica com
um pedido aberto que ninguém sabe rastrear, e a leitura do job manda **tentar
de novo**, que é justamente o que cria o segundo atendimento.

A seção [M0] deste arquivo **roda a lista antiga de novo**, aqui, para que o
número não vire folclore — e a [M1] roda a nova ao lado. É a linha de CONTROLE
do CLAUDE.md §9.2: sem ela, o acerto se credita ao lugar errado.

E a escolha da loja
-------------------
📊 A mesma tela pergunta *"Escolha a loja onde deseja realizar o serviço"*:
"Agendar a domicílio" de um lado, a lista de lojas com endereço do outro.

**A lista só existe naquela tela.** O segurado nunca a viu — perguntar "qual
loja?" antes de abrir o portal é pedir que ele responda o que não sabe. Mas a
**preferência** ele sabe sempre: *"o técnico vai até você, ou você prefere
levar?"*. Então a preferência é perguntada na conversa, e a escolha concreta
acontece com a lista na mão.

O robô não escolhe loja. Não por dropdown (`_is_critical_select` já para) e não
por botão — e este arquivo prova as duas portas, porque a segunda não tinha
guarda nenhuma: o passo 7 é feito de BOTÕES, não de selects.

Cada guarda abaixo tem CONTROLE — a linha que prova que ela consegue falhar.
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# `app/agents/__init__.py` puxa o grafo inteiro (langgraph, langchain, qdrant) e
# esta suíte roda sem eles. Mesma solução do `test_spec020_portal_action.py`: os
# pacotes `app.*` viram stubs e os dois módulos de que precisamos entram POR
# CAMINHO. `portal_worker` é importado normalmente — ele não depende de nada
# disso, e é de lá que vem o vocabulário de peça desde a SPEC-020.
for _nome in ("app", "app.agents", "app.agents.tools", "app.services"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, os.path.join(RAIZ, rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod

# O console do Windows nasce em cp1252 e engasga com 📊 e com os acentos do
# português — sem isto o teste morre de UnicodeEncodeError antes de checar nada.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with io.open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


_carregar("app.services.attendance_ficha", "app/services/attendance_ficha.py")
_perguntas = _carregar("app.services.perguntas_do_portal_de_vidros",
                       "app/services/perguntas_do_portal_de_vidros.py")
_pp = _carregar("app.agents.tools.portal_params", "app/agents/tools/portal_params.py")

ONDE_REALIZAR_O_SERVICO = _perguntas.ONDE_REALIZAR_O_SERVICO
mensagem_para_o_agente = _perguntas.mensagem_para_o_agente
o_que_falta = _perguntas.o_que_falta
format_result = _pp.format_result

from portal_worker.adaptive import (                                          # noqa: E402
    _is_critical_select,
    aviso_de_pedido_aberto,
    decidir_no_passo_7,
    has_protocol,
    preferencia_do_segurado,
    registrar_protocolo,
)
from portal_worker.journeys.vidros_lanternas import (                         # noqa: E402
    _norm,
    botao_de_domicilio,
    botao_de_loja,
    extrair_protocolo,
    interpret_atendimento,
    preferencia_de_atendimento,
    tem_protocolo,
)

# ---------------------------------------------------------------------------
# A TELA REAL do passo 7, copiada do mapa MEDIDO (§4 e §7, captura de
# 06/07/2026 em Yelum). O 'º' aqui é o MASCULINE ORDINAL INDICATOR (U+00BA) —
# o mesmo do mapa. Trocá-lo por 'N°' faria este arquivo testar outra coisa.
# ---------------------------------------------------------------------------
TELA_DO_PASSO_7 = (
    "Nº do atendimento: 22842291\n"
    "Escolha a loja onde deseja realizar o serviço.\n"
    "Serviço a domicílio\n"
    "Sem deslocamento · Economia de tempo · Atendimento premium\n"
    "Agendar a domicílio\n"
    "AUTOGLASS MG19\n"
    "Rua Camilo Veríssimo da Silva 555, Rocado, São José/SC 88108-250\n"
    "Consultar distância   Ver no mapa   Agenda disponível   Agendar na loja\n"
    "Cancelar atendimento\n"
    "O atendimento web permite apenas a SELEÇÃO de 1 (um) ITEM para "
    "TROCA/REPARO por atendimento."
)
URL_DO_PASSO_7 = "https://abraseuatendimento.com.br/#/yelum/passo5/8f2a1c34-aaaa-bbbb-cccc-0000111122"

BOTOES_DO_PASSO_7 = [
    {"text": "Agendar a domicílio", "disabled": False},
    {"text": "Consultar distância", "disabled": False},
    {"text": "Ver no mapa", "disabled": False},
    {"text": "Agendar na loja", "disabled": False},
    {"text": "Cancelar atendimento", "disabled": False},
]
ESTADO_DO_PASSO_7 = {"url": URL_DO_PASSO_7, "heading": "", "text": TELA_DO_PASSO_7,
                     "buttons": BOTOES_DO_PASSO_7}

# CONTROLE global: a tela do 80%. Nada aqui pode virar protocolo — se virar, o
# robô declara pedido aberto uma tela ANTES de o pedido existir.
TELA_DO_80 = (
    "Confirme a peça danificada\n"
    "O vidro danificado tem película de controle solar (insulfilm)?\n"
    "SIM   NÃO   Não sabe\n"
    "Avançar\n"
    "O atendimento web permite apenas a SELEÇÃO de 1 (um) ITEM para "
    "TROCA/REPARO por atendimento."
)

# A lista de rótulos EXATA que rodava em produção antes desta mudança.
# 📊 Copiada de `portal_worker/adaptive.py::_PROTO` no commit e244d5c.
_PROTO_ANTIGO = ("protocolo", "numero do atendimento", "n do atendimento",
                 "solicitacao registrada", "atendimento n")


def _reconhecia_antes(texto: str) -> bool:
    """A regra de então, reproduzida literalmente: `any(s in _norm(text))`."""
    return any(s in _norm(texto) for s in _PROTO_ANTIGO)


# ===========================================================================
# [M0] A MEDIÇÃO — a lista antiga, rodada de novo, aqui
# ===========================================================================
def teste_m0_a_lista_antiga_nao_reconhecia_o_formato_real() -> None:
    print("\n[M0] o que a medição mostrou ANTES de mexer")

    checar(_reconhecia_antes("Nº do atendimento: 22842291") is False,
           "M0 · 'Nº do atendimento' (ordinal, o que o portal usa) NÃO era reconhecido",
           "se isto virar True, a premissa desta correção deixou de valer")

    # CONTROLE da medição: a mesma lista antiga reconhecia o sinal de GRAU.
    # Sem esta linha, "não reconhecia" poderia ser "a lista não funcionava para
    # nada" — e o mérito da correção iria para o lugar errado.
    checar(_reconhecia_antes("N° do atendimento: 22842291") is True,
           "M0 CONTROLE · a MESMA lista antiga reconhecia 'N°' (grau)",
           "prova que o defeito era o CARACTERE, não a lista inteira")

    checar(_norm("Nº do atendimento") == "no do atendimento"
           and _norm("N° do atendimento") == "n do atendimento",
           "M0 · a causa é o NFKD: 'º' vira 'o'; '°' some",
           f"medido: {_norm('Nº do atendimento')!r} vs {_norm('N° do atendimento')!r}")

    checar(_reconhecia_antes(TELA_DO_PASSO_7) is False,
           "M0 · a TELA INTEIRA do passo 7 não era reconhecida")


# ===========================================================================
# [M1] O protocolo é reconhecido — e o número é lido
# ===========================================================================
def teste_o_protocolo_real_e_reconhecido() -> None:
    print("\n[M1] o formato real, agora")

    checar(tem_protocolo("Nº do atendimento: 22842291") is True,
           "'Nº do atendimento: 22842291' É reconhecido")
    checar(extrair_protocolo("Nº do atendimento: 22842291") == "22842291",
           "o NÚMERO é lido: 22842291",
           f"leu {extrair_protocolo('Nº do atendimento: 22842291')!r}")
    checar(has_protocol(ESTADO_DO_PASSO_7) is True,
           "has_protocol reconhece a tela inteira do passo 7")
    checar(extrair_protocolo(TELA_DO_PASSO_7) == "22842291",
           "e lê o número no meio da tela inteira",
           f"leu {extrair_protocolo(TELA_DO_PASSO_7)!r}")

    # As outras redações que o mesmo portal (ou outra seguradora) pode usar.
    for texto, esperado in (("N° do atendimento: 22842291", "22842291"),
                            ("Número do atendimento: 22842291", "22842291"),
                            ("Protocolo: 2026-0001234", "2026-0001234"),
                            ("Atendimento nº 22842291", "22842291")):
        checar(extrair_protocolo(texto) == esperado,
               f"variação lida: {texto!r} -> {esperado}",
               f"leu {extrair_protocolo(texto)!r}")

    # ---- CONTROLE: um texto SEM protocolo não é reconhecido ----
    checar(tem_protocolo(TELA_DO_80) is False,
           "CONTROLE · a tela do 80% NÃO é protocolo",
           "seria declarar pedido aberto uma tela antes de ele existir")
    checar(extrair_protocolo(TELA_DO_80) == "",
           "CONTROLE · e nenhum número é inventado nela",
           f"inventou {extrair_protocolo(TELA_DO_80)!r}")
    checar(tem_protocolo("") is False and extrair_protocolo("") == "",
           "CONTROLE · tela vazia não vira protocolo")

    # CONTROLE do 'grude': o número tem de estar COLADO ao rótulo. O CEP da
    # loja (88108-250) e o "1 (um) ITEM" estão na mesma tela e não podem virar
    # protocolo — dizer ao segurado um número errado é pior que não dizer
    # nenhum, porque é com ele que o segurado vai cobrar a seguradora.
    checar(extrair_protocolo("Rua X 555, São José/SC 88108-250") == "",
           "CONTROLE · um CEP solto não vira protocolo")
    checar(extrair_protocolo("permite apenas a SELEÇÃO de 1 (um) ITEM") == "",
           "CONTROLE · o aviso de 1 item não vira protocolo")

    # CONTROLE da FRONTEIRA de palavra. Sem ela, "plaNO DE ATENDIMENTO" casaria
    # com o rótulo "no de atendimento". A linha de baixo prova que a armadilha
    # existe de verdade: a busca ingênua CASA, a nossa não.
    armadilha = "plano de atendimento 55501234"
    ingenua = "no de atendimento" in _norm(armadilha)
    checar(ingenua is True,
           "CONTROLE · a busca ingênua CASARIA em 'plano de atendimento'",
           "se isto for False, o controle abaixo não prova nada")
    checar(extrair_protocolo(armadilha) == "",
           "'plano de atendimento 55501234' NÃO é protocolo (fronteira de palavra)",
           f"leu {extrair_protocolo(armadilha)!r}")


def teste_a_tela_do_protocolo_nao_e_mais_parou_em_passo5() -> None:
    print("\n[M1] a URL do protocolo é a mesma do passo 5 — e a ordem importa")

    r = interpret_atendimento(URL_DO_PASSO_7, TELA_DO_PASSO_7)
    checar(r.status == "done", "interpret_atendimento: done (não 'parou em passo5')",
           f"veio {r.status!r} / {r.message!r}")
    checar((r.captured or {}).get("protocolo") == "22842291",
           "e devolve o número em captured",
           f"veio {r.captured!r}")

    # ---- CONTROLE: a MESMA URL, sem protocolo na tela, ainda diz passo5 ----
    # Sem esta linha, "done" poderia vir de a função ter deixado de olhar a URL.
    sem = interpret_atendimento(URL_DO_PASSO_7, "Onde deseja realizar o serviço? Estado Cidade CEP")
    checar(sem.status == "needs_human" and (sem.captured or {}).get("stage") == "passo5",
           "CONTROLE · a mesma URL SEM protocolo continua 'parou em passo5'",
           f"veio {sem.status!r} / {sem.captured!r}")


# ===========================================================================
# [M2] O número é gravado CEDO — e sobrevive ao que der errado depois
# ===========================================================================
def teste_o_protocolo_e_gravado_mesmo_que_o_resto_falhe() -> None:
    print("\n[M2] gravado assim que aparece")

    evidencia: dict = {}
    numero = registrar_protocolo(evidencia, TELA_DO_PASSO_7)
    checar(numero == "22842291" and evidencia.get("protocolo") == "22842291",
           "registrar_protocolo grava em `evidence` (o dicionário que o worker "
           "escreve no job em TODOS os desfechos, inclusive `failed`)",
           f"evidence={evidencia!r}")

    # IDEMPOTENTE: o primeiro número visto manda. Uma tela seguinte com outro
    # número (ou um "Solicitar novo atendimento") não pode reescrever o que já
    # foi entregue ao segurado.
    registrar_protocolo(evidencia, "Nº do atendimento: 99999999")
    checar(evidencia["protocolo"] == "22842291",
           "o PRIMEIRO número manda — uma tela posterior não o reescreve",
           f"virou {evidencia['protocolo']!r}")

    # A frase que toda parada DEPOIS do passo 7 carrega.
    aviso = aviso_de_pedido_aberto(evidencia)
    checar("22842291" in aviso and "reexecute" in _norm(aviso),
           "uma parada posterior avisa que o pedido JÁ existe e manda NÃO repetir",
           f"aviso={aviso!r}")

    # ---- CONTROLE: sem protocolo, nada é afirmado ----
    checar(aviso_de_pedido_aberto({}) == "",
           "CONTROLE · sem protocolo, nenhum aviso é inventado")
    vazio: dict = {}
    checar(registrar_protocolo(vazio, TELA_DO_80) == "" and "protocolo" not in vazio,
           "CONTROLE · a tela do 80% não grava protocolo nenhum",
           f"gravou {vazio!r}")


# ===========================================================================
# [M3] A preferência domicílio × loja é PERGUNTADA — e só quando falta
# ===========================================================================
# Uma ficha completa de 'vidro de porta' (identidade `lateral`): tudo o que o
# portal pergunta, MENOS a preferência de onde fazer o serviço.
FICHA_SEM_A_PREFERENCIA = {
    "cpf_cnpj": "123.456.789-00",
    "peca": "vidro de porta",
    "como_ocorreu": "quebraram para furtar o som",
    "data_dano": "05/07/2026",
    "onde_ocorreu": "urbano",
    "cep": "88108-250",
    "pelicula": "SIM",
    "porta_dianteira_ou_traseira": "DIANTEIRA",
    "lado_motorista_ou_carona": "Lado do motorista",
}


def teste_a_preferencia_e_perguntada_quando_falta() -> None:
    print("\n[M3] a preferência de domicílio × loja")

    faltam = o_que_falta("vidro de porta", FICHA_SEM_A_PREFERENCIA)
    campos = [p.campo for p in faltam]
    checar(campos == [ONDE_REALIZAR_O_SERVICO],
           "com a ficha inteira menos a preferência, falta EXATAMENTE ela",
           f"faltam={campos!r}")

    pergunta = faltam[0]
    texto = _norm(pergunta.texto)
    checar("prefere" in texto and ("levar" in texto or "loja" in texto),
           "e a pergunta é de PREFERÊNCIA (o técnico vai até você × você leva)",
           pergunta.texto)
    checar("cep" in texto,
           "e ela avisa que domicílio depende do CEP — 📊 o portal só oferece "
           "domicílio onde há cobertura na região",
           pergunta.texto)

    # 🔴 A pergunta que NÃO se faz: qual loja. A lista só existe na tela do
    # passo 7, e o segurado nunca a viu.
    checar("qual loja" not in texto and "autoglass" not in texto,
           "e ela NÃO pergunta QUAL loja — ele não conhece a lista")

    # O caminho de VOLTA existe. Uma pergunta cuja resposta o schema descarta é
    # o laço infinito que este repositório já pagou uma vez.
    checar("especificos" in _norm(pergunta.como_devolver)
           and ONDE_REALIZAR_O_SERVICO in pergunta.como_devolver,
           "e diz ao agente COMO devolver a resposta (especificos)",
           pergunta.como_devolver)
    mensagem = mensagem_para_o_agente(faltam, "vidro de porta")
    checar(ONDE_REALIZAR_O_SERVICO in mensagem,
           "e isso chega à mensagem que o agente lê",
           mensagem[:200])

    # ---- CONTROLE: sabida, ela NÃO é perguntada de novo ----
    # Este é o controle que prova que a guarda acima consegue falhar: a única
    # diferença entre as duas chamadas é a chave da preferência.
    sabida = {**FICHA_SEM_A_PREFERENCIA, ONDE_REALIZAR_O_SERVICO: "domicilio"}
    checar(o_que_falta("vidro de porta", sabida) == [],
           "CONTROLE · com a preferência respondida, NADA mais falta",
           f"ainda faltam {[p.campo for p in o_que_falta('vidro de porta', sabida)]!r}")
    checar(mensagem_para_o_agente(o_que_falta("vidro de porta", sabida), "vidro de porta") == "",
           "CONTROLE · e a mensagem ao agente fica vazia")

    # CONTROLE de escopo: a preferência não pode virar bloqueio de outra coisa.
    # Sem peça, quem falta é a PEÇA — e as específicas nem nascem.
    sem_peca = [p.campo for p in o_que_falta("", {"cpf_cnpj": "1", "como_ocorreu": "x",
                                                  "data_dano": "05/07/2026",
                                                  "onde_ocorreu": "urbano", "cep": "1"})]
    checar("peca" in sem_peca and "pelicula" not in sem_peca,
           "CONTROLE · sem peça, a peça é que falta (as específicas nem nascem)",
           f"faltam={sem_peca!r}")


def teste_o_vocabulario_da_preferencia_prefere_parar_a_chutar() -> None:
    print("\n[M3] o vocabulário — e a assimetria proposital")

    for texto, esperado in (("domicilio", "domicilio"),
                            ("em casa", "domicilio"),
                            ("prefiro que venham até mim", "domicilio"),
                            ("no meu trabalho", "domicilio"),
                            ("prefiro levar", "loja"),
                            ("vou levar numa loja", "loja"),
                            ("levo na oficina", "loja")):
        checar(preferencia_de_atendimento(texto) == esperado,
               f"'{texto}' -> {esperado}",
               f"deu {preferencia_de_atendimento(texto)!r}")

    # ---- CONTROLE: o que NÃO se deixa classificar para, e não chuta ----
    for texto in ("tanto faz", "", "sei lá", "o que for mais rápido"):
        checar(preferencia_de_atendimento(texto) == "",
               f"CONTROLE · '{texto}' não vira preferência nenhuma",
               f"virou {preferencia_de_atendimento(texto)!r}")

    # 🔴 A ASSIMETRIA. Errar para 'loja' custa uma parada com a lista na mão;
    # errar para 'domicilio' marcaria um técnico na casa de quem pediu para
    # levar o carro. Por isso a negação bloqueia SÓ o lado do domicílio.
    checar(preferencia_de_atendimento("não quero em casa") == "",
           "negado, 'em casa' NÃO vira domicílio")
    checar(preferencia_de_atendimento("em casa") == "domicilio",
           "CONTROLE · sem a negação, a MESMA frase vira domicílio",
           "prova que o bloqueio é da negação, e não da frase")
    # E 'sem' fica de fora da negação de propósito: 📊 "Sem deslocamento" é selo
    # do próprio portal para o serviço a domicílio.
    checar(preferencia_de_atendimento("quero o sem deslocamento") == "domicilio",
           "'sem deslocamento' (selo do portal) continua sendo domicílio")


# ===========================================================================
# [M4] O robô NÃO escolhe a loja — nem por dropdown, nem por botão
# ===========================================================================
def teste_o_robo_nao_escolhe_a_loja() -> None:
    print("\n[M4] a escolha da loja é do segurado")

    # A porta que já tinha guarda: o dropdown.
    checar(_is_critical_select("Escolha a loja onde deseja realizar o serviço") is True,
           "o campo da loja é CRÍTICO (o robô não cai na 1ª opção)")
    # CONTROLE: um campo de FORMATO continua tolerante — se tudo virasse
    # crítico, o robô travaria em campo onde parar não protege ninguém.
    checar(_is_critical_select("Tipo de telefone") is False,
           "CONTROLE · 'tipo de telefone' continua tolerante")

    # A porta que NÃO tinha guarda nenhuma: 📊 o passo 7 é feito de BOTÕES
    # ("Agendar a domicílio" / "Agendar na loja"), e `_is_critical_select` só
    # protege select/mdselect. Um `click` passava direto.
    dossie = decidir_no_passo_7(ESTADO_DO_PASSO_7, {"especificos": {ONDE_REALIZAR_O_SERVICO: "loja"},
                                                    "dano": {"peca": "vidro de porta"}})
    checar(dossie["protocolo"] == "22842291",
           "o dossiê do passo 7 traz o protocolo")
    checar(dossie["tem_domicilio"] is True and dossie["tem_loja"] is True,
           "e enxerga que a tela oferece domicílio E lojas",
           f"{dossie!r}")
    checar("AUTOGLASS MG19" not in str(dossie),
           "e NENHUMA loja é escolhida — o nome da loja não aparece como decisão",
           f"apareceu em {dossie!r}")
    # CONTROLE: prova que a loja ESTAVA lá para ser copiada. Sem esta linha, o
    # "não aparece" poderia ser só porque a tela não tinha loja nenhuma.
    checar("AUTOGLASS MG19" in TELA_DO_PASSO_7,
           "CONTROLE · a loja ESTAVA na tela, disponível para ser copiada")

    checar("ELE escolha" in dossie["recomendacao"] or "ele escolha" in dossie["recomendacao"],
           "e a recomendação manda o segurado escolher",
           dossie["recomendacao"])

    # O caso que só a preferência coletada antes resolve: ele quer domicílio e
    # o CEP dele não tem. 📊 O rótulo do CEP no portal diz exatamente isso.
    sem_domicilio = decidir_no_passo_7(
        {**ESTADO_DO_PASSO_7, "buttons": [{"text": "Agendar na loja"}]},
        {"especificos": {ONDE_REALIZAR_O_SERVICO: "domicilio"}})
    checar(sem_domicilio["tem_domicilio"] is False
           and "NAO oferece domicilio" in sem_domicilio["recomendacao"],
           "pediu domicílio e o portal não oferece: o dossiê DIZ isso",
           sem_domicilio["recomendacao"])
    # CONTROLE: com o botão de volta, a recomendação muda.
    com_domicilio = decidir_no_passo_7(ESTADO_DO_PASSO_7,
                                       {"especificos": {ONDE_REALIZAR_O_SERVICO: "domicilio"}})
    checar(com_domicilio["tem_domicilio"] is True
           and "NAO oferece domicilio" not in com_domicilio["recomendacao"],
           "CONTROLE · com o botão na tela, a recomendação é outra",
           com_domicilio["recomendacao"])

    # Sem preferência nenhuma, o dossiê admite que não sabe — não inventa.
    sem_pref = decidir_no_passo_7(ESTADO_DO_PASSO_7, {})
    checar(sem_pref["preferencia"] == "" and "Ainda nao sei" in sem_pref["recomendacao"],
           "sem preferência coletada, o dossiê admite que não sabe",
           sem_pref["recomendacao"])

    # Os leitores de botão, isolados.
    checar(botao_de_domicilio(BOTOES_DO_PASSO_7) == "Agendar a domicílio",
           "botao_de_domicilio lê o botão real")
    checar(botao_de_loja(BOTOES_DO_PASSO_7) == "Agendar na loja",
           "botao_de_loja lê o botão real")
    checar(botao_de_domicilio([{"text": "Agendar a domicílio", "disabled": True}]) == "",
           "CONTROLE · botão DESABILITADO não conta como oferta")
    checar(botao_de_domicilio([{"text": "Avançar"}]) == "" and botao_de_loja([]) == "",
           "CONTROLE · tela sem esses botões devolve vazio")

    checar(preferencia_do_segurado({"especificos": {ONDE_REALIZAR_O_SERVICO: "prefiro levar"}}) == "loja",
           "a preferência viaja em `especificos` — o mesmo transporte do 80%")
    checar(preferencia_do_segurado({}) == "",
           "CONTROLE · sem `especificos`, nenhuma preferência é presumida")


# ===========================================================================
# [M5] O número chega ao texto que o AGENTE fala
# ===========================================================================
def teste_o_numero_chega_ao_segurado() -> None:
    print("\n[M5] o que o agente diz ao segurado")

    job_ok = {"status": "done",
              "evidence": {"protocolo": "22842291",
                           "passo7": decidir_no_passo_7(
                               ESTADO_DO_PASSO_7,
                               {"especificos": {ONDE_REALIZAR_O_SERVICO: "domicilio"}}),
                           "message": "atendimento aberto"}}
    frase = format_result(job_ok)
    checar("22842291" in frase,
           "o NÚMERO aparece na frase que o agente lê", frase)
    checar("SEGURADO" in frase.upper(),
           "e a frase manda dizê-lo AO SEGURADO", frase)
    checar("segundo" in _norm(frase) and "de novo" in _norm(frase),
           "e avisa para NÃO reabrir (repetir cria um segundo atendimento)", frase)

    # 🔴 O caso que amarrar o número ao status `done` deixaria de fora: o pedido
    # existe e o fluxo QUEBROU depois. É o mais perigoso de todos.
    for status in ("needs_human", "failed", "queued"):
        job = {"status": status, "error": "TimeoutError",
               "evidence": {"protocolo": "22842291",
                            "message": "tela travada: repetiu 'click Agendar'"}}
        checar("22842291" in format_result(job),
               f"status={status}: o pedido existe e o número é dito assim mesmo",
               format_result(job))

    # ---- CONTROLE: sem protocolo, nenhum número é prometido ----
    # As frases antigas continuam valendo — é o que prova que a guarda acima
    # depende do campo `protocolo`, e não de a função ter virado otimista.
    sem = format_result({"status": "done", "evidence": {"message": "protocolo gerado"}})
    checar("concluido" in _norm(sem) and "22842291" not in sem,
           "CONTROLE · done SEM protocolo mantém a frase antiga", sem)
    r80 = format_result({"status": "needs_human",
                         "evidence": {"stage_80": "Confirme a peca",
                                      "message": "cheguei na confirmacao (80%)"}})
    checar("confirmacao" in _norm(r80) and "22842291" not in r80,
           "CONTROLE · a parada do 80% continua sendo a parada do 80%", r80)
    falhou = format_result({"status": "failed", "error": "x", "evidence": {}})
    checar("nao consegui" in _norm(falhou),
           "CONTROLE · failed sem protocolo continua dizendo que não conseguiu", falhou)


# ===========================================================================
# [M6] Continua havendo UM lugar que sabe o que é protocolo
# ===========================================================================
def teste_o_vocabulario_do_protocolo_e_um_so() -> None:
    print("\n[M6] uma lista, não duas")

    adaptive = _ler("portal_worker", "adaptive.py")
    journey = _ler("portal_worker", "journeys", "vidros_lanternas.py")

    checar("_PROTO = (" not in adaptive,
           "a segunda lista de rótulos saiu do adaptive.py",
           "duas listas idênticas por cópia divergem no dia em que só uma é corrigida")
    checar("extrair_protocolo" in adaptive and "from portal_worker.journeys.vidros_lanternas import" in adaptive,
           "o adaptive IMPORTA o vocabulário em vez de manter o seu")
    checar(journey.count("_ROTULOS_DE_PROTOCOLO = (") == 1,
           "e a lista é declarada UMA vez, na journey")

    # CONTROLE: a trava do 80% não foi tocada. Este arquivo não é dono dela.
    checar("if is_confirm_screen(state) and not confirm:" in adaptive,
           "CONTROLE · a trava do 80% (is_confirm_screen + confirm) segue de pé")
    checar("confirme a peca danificada" in adaptive,
           "CONTROLE · e os gatilhos do 80% continuam onde estavam")


def teste_alargar_o_protocolo_nao_pode_pular_a_trava_do_80() -> None:
    """🔴 A guarda que esta mudança OBRIGA a existir.

    `has_protocol` roda ANTES de `is_confirm_screen` no laço do `run_adaptive`
    (era assim antes desta mudança e continua sendo). A lista de rótulos ficou
    MAIS LARGA — ganhou "no do atendimento", "atendimento no", "atendimento
    registrado" e outros. Se algum deles casasse por acaso numa tela do 80%, o
    robô declararia pedido aberto e **passaria por cima da trava**, que é a
    única coisa entre um teste e um pedido de verdade na seguradora.

    Alargar reconhecimento é barato até o dia em que ele reconhece a tela
    errada. Esta é a fatura.
    """
    print("\n[M7] o reconhecimento mais largo não atravessa a trava")

    from portal_worker.adaptive import is_confirm_screen  # noqa: PLC0415

    # 📊 As duas telas do 80% medidas (mapa §4, captura de 06/07/2026), com o
    # banner permanente que aparece em TODAS as telas do portal.
    BANNER = ("O atendimento web permite apenas a SELEÇÃO de 1 (um) ITEM para "
              "TROCA/REPARO por atendimento. Se o item escolhido possuir "
              "lateralidade, será necessário abrir uma nova solicitação.")
    telas_do_80 = {
        "vidro de porta (Yelum)": (
            "Confirme a peça danificada\n"
            "O vidro danificado tem película de controle solar (insulfilm)?\n"
            "SIM   NÃO   Não sabe\n"
            "O vidro danificado é da porta dianteira ou traseira?\n"
            "DIANTEIRA   TRASEIRA   Não sabe\n"
            "Qual o lado do item danificado?\n"
            "Lado do carona   Lado do motorista   Não sabe\n"
            "Voltar   Avançar   Cancelar atendimento\n" + BANNER),
        "parabrisa (Tokio)": (
            "Confirme a peça danificada\n"
            "Poderia informar a posição do trincado?\n"
            "Em frente ao motorista   Em frente ao carona   Nas bordas   No centro\n"
            "O trincado está maior ou menor que 10 cm?\n"
            "Maior (troca do vidro)   Menor (possibilidade de reparo)   Não sabe\n"
            "A versão do veículo é comfortline?\n"
            "Sim   Não   Não sabe\n"
            "Voltar   Avançar   Cancelar atendimento\n" + BANNER),
    }
    for nome, texto in telas_do_80.items():
        estado = {"heading": "Confirme a peça danificada", "text": texto}
        checar(has_protocol(estado) is False,
               f"80% '{nome}': NÃO é confundida com protocolo",
               "confundir aqui pularia a trava e abriria o pedido")
        checar(is_confirm_screen(estado) is True,
               f"CONTROLE · 80% '{nome}': a trava RECONHECE a tela",
               "sem isto, o 'False' acima não prova nada — provaria só que a "
               "tela não é reconhecida por ninguém")

    # E o outro lado: a tela do passo 7 é protocolo e NÃO é a do 80%.
    checar(has_protocol(ESTADO_DO_PASSO_7) is True
           and is_confirm_screen(ESTADO_DO_PASSO_7) is False,
           "CONTROLE · e a tela do passo 7 é protocolo, não confirmação",
           f"has={has_protocol(ESTADO_DO_PASSO_7)} confirm={is_confirm_screen(ESTADO_DO_PASSO_7)}")

    # As telas ANTERIORES também não podem virar protocolo — todas carregam o
    # banner com a palavra "atendimento", e ela sozinha não é um número.
    for nome, texto in (("passo 1", "Iniciar atendimento   Consultar atendimento\n" + BANNER),
                        ("passo 3", "Confirme seus dados\nSua relação com o titular\n"
                                    "E-mail   Telefone   Tipo de telefone\nAvançar\n" + BANNER),
                        ("passo 5", "Onde deseja realizar o serviço?\n"
                                    "Estado   Cidade   CEP\nAvançar\n" + BANNER)):
        checar(has_protocol({"text": texto}) is False,
               f"CONTROLE · '{nome}' (com o banner) não vira protocolo",
               f"leu {extrair_protocolo(texto)!r}")


# ===========================================================================
# [M8] O LAÇO DE VERDADE — `run_adaptive`, não só as funções puras
# ===========================================================================
# As guardas acima provam o vocabulário. Esta prova o CAMINHO: que o número
# realmente sai da tela e entra no `evidence` que o worker grava no job — e que
# ele continua lá quando o navegador morre no passo seguinte.
#
# 📊 É o cenário exato do risco: o `Nº do atendimento` nasce no clique, e o
# `capture_state` da volta seguinte é a primeira coisa que pode explodir. Se a
# captura só acontecesse ali, o pedido existiria na seguradora e o job sairia
# `failed` sem número nenhum.
_ESTADO_VAZIO = {"url": "", "heading": "", "inputs": [], "selects": [], "mdselects": [],
                 "radios": [], "pending_required": []}


class _PaginaFalsa:
    """O mínimo de `page` que o `run_adaptive` usa neste caminho.

    `morre_na_leitura` = em qual leitura de tela o navegador cai. É assim que o
    teste reproduz "o Playwright explodiu depois do clique" sem Playwright.
    """

    def __init__(self, texto: str, texto_depois_do_clique: str = "",
                 botoes=None, morre_na_leitura: int = 0):
        self.texto = texto
        self.texto_depois = texto_depois_do_clique
        self.botoes = botoes if botoes is not None else [{"text": "Avançar", "disabled": False}]
        self.morre_na_leitura = morre_na_leitura
        self.leituras = 0
        self.cliques = 0

    async def evaluate(self, js, *a):
        if "querySelectorAll" in js:                      # capture_state
            self.leituras += 1
            if self.morre_na_leitura and self.leituras >= self.morre_na_leitura:
                raise RuntimeError("Target page, context or browser has been closed")
            return {**_ESTADO_VAZIO, "text": self.texto, "buttons": self.botoes}
        if "innerText" in js:                             # a leitura curta pós-clique
            return self.texto
        return None

    async def query_selector_all(self, sel):
        if "button" not in sel:
            return []
        pagina = self

        class _Botao:
            def __init__(self, rotulo):
                self.rotulo = rotulo

            async def is_visible(self):
                return True

            async def is_disabled(self):
                return False

            async def inner_text(self):
                return self.rotulo

            async def get_attribute(self, _k):
                return ""

            async def click(self):
                pagina.cliques += 1
                if pagina.texto_depois:
                    pagina.texto = pagina.texto_depois

        return [_Botao(str(b.get("text") or "")) for b in self.botoes]

    async def wait_for_timeout(self, _ms):
        return None


def teste_o_laco_real_grava_o_numero_e_ele_sobrevive_a_queda() -> None:
    print("\n[M8] o `run_adaptive` de verdade")

    import asyncio                                          # noqa: PLC0415

    import portal_worker.adaptive as AD                      # noqa: PLC0415

    COLETADO = {"especificos": {ONDE_REALIZAR_O_SERVICO: "domicilio"},
                "dano": {"peca": "vidro de porta", "como": "quebraram para furtar"}}

    # ---- (a) a tela do passo 7 chega ao laço: done, com número e dossiê ----
    evidencia: dict = {}
    pagina = _PaginaFalsa(TELA_DO_PASSO_7, botoes=BOTOES_DO_PASSO_7)
    r = asyncio.run(AD.run_adaptive(pagina, "abrir vidros", COLETADO, evidencia, confirm=True))
    checar(r.status == "done" and (r.captured or {}).get("protocolo") == "22842291",
           "o laço devolve done COM o número", f"{r.status} / {r.captured}")
    checar(evidencia.get("protocolo") == "22842291",
           "e o número está no `evidence` que o worker grava no job",
           f"{ {k: v for k, v in evidencia.items() if k != 'final'} }")
    checar(isinstance(evidencia.get("passo7"), dict)
           and evidencia["passo7"]["preferencia"] == "domicilio",
           "e o dossiê do passo 7 vai junto, com a preferência do segurado",
           str(evidencia.get("passo7")))
    checar(pagina.cliques == 0,
           "🔴 e o laço NÃO clicou em nada na tela do protocolo",
           f"clicou {pagina.cliques}x — seria escolher loja ou agendar por ele")

    # ---- (b) o navegador morre logo DEPOIS do clique que abriu o pedido ----
    original = AD.decide_next_action

    async def _cerebro_manda_avancar(state, goal, collected, history, force=False):
        return {"action": "click", "target": "Avançar", "value": "", "reason": "teste"}

    AD.decide_next_action = _cerebro_manda_avancar
    try:
        evid_queda: dict = {}
        # A tela ANTES do clique é a do 80%; o clique a transforma na do passo 7
        # (é literalmente o que o Avançar do 80% faz), e a leitura seguinte cai.
        pag = _PaginaFalsa("Confirme a peça danificada. Avançar",
                           texto_depois_do_clique=TELA_DO_PASSO_7,
                           morre_na_leitura=2)
        caiu = ""
        try:
            asyncio.run(AD.run_adaptive(pag, "abrir vidros", COLETADO, evid_queda, confirm=True))
        except Exception as exc:  # noqa: BLE001
            caiu = f"{type(exc).__name__}"
        checar(caiu == "RuntimeError" and pag.cliques == 1,
               "o navegador caiu na leitura seguinte ao clique (cenário reproduzido)",
               f"caiu={caiu!r} cliques={pag.cliques}")
        checar(evid_queda.get("protocolo") == "22842291",
               "🔴 e o número JÁ ESTAVA GRAVADO — o pedido existe e é rastreável",
               f"evidence={evid_queda!r}")
        checar("22842291" in format_result({"status": "failed", "error": "RuntimeError",
                                            "evidence": evid_queda}),
               "e o agente diz o número mesmo com o job em `failed`",
               format_result({"status": "failed", "evidence": evid_queda}))

        # ---- CONTROLE: mesma queda, mas o clique NÃO abriu pedido nenhum ----
        # Sem esta linha, o "22842291" acima poderia vir de qualquer lugar — de
        # um valor cravado, de uma leitura antiga. Aqui a ÚNICA diferença é o
        # que a tela passou a mostrar depois do clique.
        evid_controle: dict = {}
        pag2 = _PaginaFalsa("Confirme a peça danificada. Avançar",
                            texto_depois_do_clique="Onde deseja realizar o serviço? Estado Cidade CEP",
                            morre_na_leitura=2)
        try:
            asyncio.run(AD.run_adaptive(pag2, "abrir vidros", COLETADO, evid_controle, confirm=True))
        except Exception:  # noqa: BLE001
            pass
        checar("protocolo" not in evid_controle and pag2.cliques == 1,
               "CONTROLE · clique que NÃO abriu pedido não grava protocolo nenhum",
               f"evidence={evid_controle!r}")
        checar("nao consegui" in _norm(format_result({"status": "failed", "error": "x",
                                                      "evidence": evid_controle})),
               "CONTROLE · e aí o agente diz que não conseguiu, sem inventar número")
    finally:
        AD.decide_next_action = original


def main() -> int:
    print("=" * 72)
    print("O PROTOCOLO NASCE NO PASSO 7 — E TEM DE CHEGAR AO SEGURADO")
    print("=" * 72)
    for t in (teste_m0_a_lista_antiga_nao_reconhecia_o_formato_real,
              teste_o_protocolo_real_e_reconhecido,
              teste_a_tela_do_protocolo_nao_e_mais_parou_em_passo5,
              teste_o_protocolo_e_gravado_mesmo_que_o_resto_falhe,
              teste_a_preferencia_e_perguntada_quando_falta,
              teste_o_vocabulario_da_preferencia_prefere_parar_a_chutar,
              teste_o_robo_nao_escolhe_a_loja,
              teste_o_numero_chega_ao_segurado,
              teste_o_vocabulario_do_protocolo_e_um_so,
              teste_alargar_o_protocolo_nao_pode_pular_a_trava_do_80,
              teste_o_laco_real_grava_o_numero_e_ele_sobrevive_a_queda):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O PEDIDO TEM NÚMERO, O NÚMERO CHEGA AO SEGURADO, E A LOJA CONTINUA SENDO ESCOLHA DELE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
