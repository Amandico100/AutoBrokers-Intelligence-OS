# -*- coding: utf-8 -*-
"""O humano é chamado de verdade — SPEC-085, BLOCO B.

📊 **São TRÊS cadeias de handoff, e a terceira é a única com prova em produção.**
Dos dois `needs_human` duráveis da história do produto, um tem
`error_code = 'needs_human:sentinela_stall'` — o caminho **C**, o Vigia.

🔴 E era o único que **nunca falava com o segurado**. Contagem no arquivo, antes
deste bloco:

    client_phone 0 · send_to_client 0 · HUMAN_REQUESTED 0
    reivindicar_o_aviso 0 · contar_lembrete 0

O caminho B (`dispatch_router`) ao menos manda *"um colega vai assumir"*.
**No caminho C o segurado não ouvia nem isso. Ouvia nada.**

## O que este arquivo guarda, e por que cada um

| guarda | o defeito que ele impede |
|---|---|
| o Vigia avisa o segurado | o silêncio total do caminho C |
| e o texto depende do desfecho | prometer "um colega vai assumir" quando o dossiê não saiu |
| UMA implementação do marcador | o "segundo marcador de aviso" que a §8 proíbe |
| sem id → sem marcador, nunca `None` | `handoff_realerta:None` é chave GLOBAL: calaria TODAS as corretoras |
| ausente ≠ recusado ≠ envio_falhou | três instruções diferentes para a corretora |
| o dossiê para de mentir | quem lê "já foi avisado" não fala com o segurado |
| 🔴 CONTROLE: os 4 alertas não-handoff | mexer no `_support_alert` calaria "a URA está calada há 20min" e mais três |
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VIGIA = RAIZ / "app" / "tasks" / "dispatch_watchdog.py"
ROUTER = RAIZ / "app" / "services" / "dispatch_router.py"
MOTOR = RAIZ / "app" / "services" / "insurer_dispatch_service.py"


def _sem_comentario(texto: str) -> str:
    """Só o CÓDIGO — sem `#` E SEM DOCSTRING.

    🔴 A primeira versão tirava só o `#`, e ficou vermelha por defeito próprio:
    a docstring de `entregar_dossie_uma_vez` **explica** que nunca se deve
    chamar `reivindicar_o_aviso(None, ...)`, e o guarda leu a explicação como
    se fosse a chamada. Ele reprovou o conserto por causa do texto que descreve
    o conserto.

    ⚠️ Guarda estático que lê comentário guarda o comentário. E aqui é pior que
    inútil: ele manda consertar o que já está certo.
    """
    fora, dentro, delim = [], False, ""
    for linha in texto.splitlines():
        crua = linha
        if not dentro:
            crua = crua.split("#", 1)[0]
        i = 0
        while i < len(crua):
            if not dentro:
                if crua.startswith('"""', i) or crua.startswith("'''", i):
                    delim, dentro = crua[i:i + 3], True
                    i += 3
                    continue
            else:
                if crua.startswith(delim, i):
                    dentro = False
                    i += 3
                    continue
            i += 1
        if dentro or '"""' in crua or "'''" in crua:
            continue
        if crua.strip():
            fora.append(crua)
    return "\n".join(fora)


def _carregar_modulo(nome: str, caminho: Path):
    """Carrega um módulo de `app/` sem passar por `app.services.__init__`.
    📊 O `gate.yml` não roda `pip install`; guarda que precise de dependência
    não roda em CI, e guarda que não roda não guarda."""
    import importlib.util
    import sys
    import types

    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services", "app.agents")}
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


MOTOR_MOD = _carregar_modulo("_spec085_motor_B", MOTOR)


def _funcao(caminho: Path, nome: str) -> str:
    """O corpo de uma função, com âncora ÚNICA exigida."""
    fonte = caminho.read_text(encoding="utf-8")
    marca = f"def {nome}("
    assert fonte.count(marca) == 1, (
        f"âncora ambígua: `{marca}` aparece {fonte.count(marca)} vezes em "
        f"{caminho.name}")
    corpo = fonte.split(marca, 1)[-1]
    corpo = re.split(r"\n(?:async )?def ", corpo, maxsplit=1)[0]
    return _sem_comentario(corpo)


# ---------------------------------------------------------------------------
# 1. B.0 — O CAMINHO C PASSA A FALAR COM O SEGURADO
# ---------------------------------------------------------------------------

def test_o_vigia_avisa_o_segurado():
    corpo = _funcao(VIGIA, "_sentinela_recover")
    assert "_avisar_o_segurado(" in corpo, (
        "o Vigia voltou a não falar com o segurado. É a cadeia com prova em "
        "produção, e o segurado dela não ouve NADA quando o acionamento morre")


def test_o_texto_depende_do_desfecho_do_dossie():
    """🔴 Prometer 'um colega vai assumir' quando o dossiê NÃO saiu é dizer que
    existe alguém esperando quando não existe — a mesma família do
    `dossier_sent = True` incondicional, um degrau acima.

    ⚠️ ESTE GUARDA MUDOU DE FORMA, e a mudança é melhoria: ele lia o TEXTO das
    constantes no fonte do Vigia. Elas mudaram de casa (foram para o motor, que
    é puro e que as três cadeias importam) e o guarda ficou vermelho sem que
    nada tivesse regredido. Agora ele **chama a função** — que é o que importa,
    e não onde a string mora.
    """
    corpo = _funcao(VIGIA, "_avisar_o_segurado")
    assert "aviso_de_handoff(" in corpo, (
        "o aviso ao segurado deixou de perguntar ao motor qual frase usar")
    assert 'session.get("dossier_sent")' in corpo, (
        "o texto não olha mais se o dossiê saiu")


def test_as_duas_frases_dizem_coisas_DIFERENTES():
    """§9.3: prove que elas CONSEGUEM ser diferentes. Duas frases iguais
    passariam no teste acima e mentiriam do mesmo jeito.

    🔴 E a checagem é sobre o COMPORTAMENTO — a função pura, chamada com os
    dois valores — em vez de um `grep` no fonte.
    """
    com = MOTOR_MOD.aviso_de_handoff(True)
    sem = MOTOR_MOD.aviso_de_handoff(False)
    assert com and sem and com != sem, "as duas frases são a mesma coisa"
    assert "colega" in com.lower(), "a frase do sucesso não menciona o colega"
    assert "colega" not in sem.lower(), (
        "a frase de FALHA promete um colega — é a mentira que o bloco mata")
    assert "24h" in sem or "assistência" in sem.lower(), (
        "a frase de falha não dá saída nenhuma ao segurado, que pode estar na "
        "estrada, à noite")


def test_a_frase_de_FALHA_passa_pelo_fiscal_do_caminho_A():
    """🔴 BLOCO C.3 — a regra do fiscal vale para o caminho B, e o lugar certo
    de aplicá-la a uma CONSTANTE é aqui, não em tempo de execução.

    `honestidade_do_handoff.afirma_transferencia` é o mesmo regex que reescreve
    a resposta do agente quando ela afirma, no passado, que a transferência
    aconteceu. Rodá-lo sobre um literal a cada mensagem é desperdício; rodá-lo
    sobre o literal UMA vez, no gate, é o guarda.
    """
    fiscal = _carregar_modulo("_spec085_fiscal",
                              RAIZ / "app" / "agents" / "honestidade_do_handoff.py")
    sem = MOTOR_MOD.aviso_de_handoff(False)
    assert not fiscal.afirma_transferencia(sem), (
        "a frase de FALHA afirma, no passado, que a transferência aconteceu — "
        f"é exatamente o que o fiscal do caminho A reescreve: {sem[:90]!r}")


def test_CONTROLE_o_fiscal_CONSEGUE_reprovar_uma_frase():
    """E o controle do controle: um fiscal que aprovasse tudo faria o teste
    acima passar sem guardar nada."""
    fiscal = _carregar_modulo("_spec085_fiscal2",
                              RAIZ / "app" / "agents" / "honestidade_do_handoff.py")
    assert fiscal.afirma_transferencia(
        "Já encaminhei seu caso para um colega da equipe."), (
        "o fiscal não reconhece nem uma afirmação óbvia de transferência")


def test_a_flag_de_aviso_so_e_marcada_DEPOIS_do_envio():
    corpo = _funcao(VIGIA, "_avisar_o_segurado")
    pos_envio = corpo.find("wa.send_message")
    pos_flag = corpo.find('session["client_notified_handoff"] = True')
    assert pos_envio != -1 and pos_flag > pos_envio, (
        "a flag é marcada antes do envio — flag que mente encerra a investigação")


# ---------------------------------------------------------------------------
# 2. B.1 — UMA implementação do marcador, para as DUAS cadeias
# ---------------------------------------------------------------------------

def test_o_marcador_tem_UMA_implementacao():
    """🔴 A §8 da SPEC proíbe 'um segundo marcador de aviso'. Duas cópias da
    mesma regra em arquivos diferentes é isso com outro nome."""
    assert "async def entregar_dossie_uma_vez(" in ROUTER.read_text(encoding="utf-8"), (
        "a regra do marcador sumiu do `dispatch_router`")
    vigia = VIGIA.read_text(encoding="utf-8")
    assert "entregar_dossie_uma_vez" in vigia, (
        "o Vigia deixou de usar a regra compartilhada — ou ele parou de usar "
        "marcador, ou ele escreveu o SEGUNDO")
    corpo = _funcao(VIGIA, "_entregar_dossie_com_marcador")
    for proibido in ("reivindicar_o_aviso", "contar_lembrete", "devolver_a_vez"):
        assert proibido not in corpo, (
            f"o Vigia voltou a chamar `{proibido}` direto — é a segunda cópia "
            "da regra, e ela vai divergir")


def test_as_duas_cadeias_REUSAM_o_marcador_da_SPEC_086():
    """§3.2: o marcador e o teto são da SPEC-086, estão prontos, e são REUSADOS
    — nunca reescritos."""
    corpo = _funcao(ROUTER, "entregar_dossie_uma_vez")
    for peca in ("reivindicar_o_aviso", "contar_lembrete", "devolver_a_vez",
                 "MAX_LEMBRETES_POR_CONVERSA", "HORAS_ENTRE_AVISOS_PADRAO"):
        assert peca in corpo, f"a regra deixou de reusar `{peca}`"
    assert "human_handoff" in corpo, "o import da SPEC-086 sumiu"


def test_CONTROLE_sem_id_de_conversa_NUNCA_reserva_com_None():
    """🔴 `reivindicar_o_aviso(None, ...)` gravaria `handoff_realerta:None` —
    uma chave GLOBAL que calaria o handoff de TODAS as corretoras por seis
    horas. É isolamento entre corretoras (`CLAUDE.md` §7)."""
    corpo = _funcao(ROUTER, "entregar_dossie_uma_vez")
    antes_do_import = corpo.split("from app.agents.tools.human_handoff", 1)[0]
    assert "if not conversa_id:" in antes_do_import, (
        "o caminho sem id de conversa não retorna ANTES de tocar o marcador")
    assert "reivindicar_o_aviso" not in antes_do_import, (
        "o marcador é chamado antes de conferir o id — `handoff_realerta:None` "
        "é uma chave global")


def test_a_reserva_e_devolvida_quando_o_aviso_nao_sai():
    corpo = _funcao(ROUTER, "entregar_dossie_uma_vez")
    assert "devolver_a_vez(conversa_id)" in corpo, (
        "reserva que não virou aviso não é devolvida — uma falha de envio "
        "silencia o grupo pelas seis horas inteiras do marcador")


# ---------------------------------------------------------------------------
# 3. B.2 / B.3 — AUSENTE, RECUSADO e ENVIO_FALHOU são três coisas
# ---------------------------------------------------------------------------

def test_o_roteador_distingue_ausente_de_recusado():
    """🔴 São caminhos de código diferentes e dão instruções OPOSTAS:

        ausente   → CADASTRE um destino
        recusado  → PARE DE COMPARTILHAR o que você já tem

    Fundir os dois num `sem_destino_de_suporte` apaga a diferença que decide o
    que a pessoa faz.
    """
    fonte = _sem_comentario(ROUTER.read_text(encoding="utf-8"))
    assert "resolver_destino_de_suporte(company_id)" in fonte, (
        "o roteador voltou a usar só o destino, perdendo o motivo da recusa")
    for estado in ('"recusado"', '"ausente"', '"envio_falhou"'):
        assert estado in fonte, f"o estado {estado} sumiu"


def test_a_falta_de_destino_deixou_de_ser_so_um_log():
    """Um estado que só existe no log é um estado que ninguém vê — é a SPEC
    inteira em miniatura."""
    fonte = _sem_comentario(ROUTER.read_text(encoding="utf-8"))
    assert 'session["suporte_indisponivel"]' in fonte, (
        "a falta de destino voltou a ser só um `warning`")


def test_o_estado_de_suporte_SOBREVIVE_ao_mascarador():
    """Ele viaja no retrato durável. Se o mascarador o engolir, a Fila do
    BLOCO E não tem o que ler."""
    pii = (RAIZ / "app" / "services" / "pii_da_sessao.py").read_text(encoding="utf-8")
    assert '"suporte_indisponivel"' in pii, (
        "`suporte_indisponivel` não está entre as chaves seguras — vira "
        "`{TEXTO:n}` e a corretora deixa de saber que está surda")


# ---------------------------------------------------------------------------
# 4. B.4 — o dossiê para de mentir
# ---------------------------------------------------------------------------

def test_o_dossie_so_diz_avisado_se_avisou():
    """📊 A linha era INCONDICIONAL, mesmo quando o envio ao cliente estourava.
    ⚠️ E a diferença muda o que a pessoa FAZ: quem lê 'já foi avisado' continua
    de onde parou; quem lê 'NÃO foi avisado' fala com o segurado primeiro."""
    fonte = _sem_comentario(MOTOR.read_text(encoding="utf-8"))
    assert 'avisado = bool(session.get("client_notified_handoff"))' in fonte, (
        "o dossiê voltou a afirmar o aviso sem olhar se ele saiu")
    assert "AINDA NÃO foi avisado" in MOTOR.read_text(encoding="utf-8"), (
        "sumiu o ramo que diz a verdade quando o aviso não saiu")


# ---------------------------------------------------------------------------
# 5. 🔴 O CONTROLE DO CONTROLE — os quatro alertas que NÃO são handoff
# ---------------------------------------------------------------------------

def test_CONTROLE_os_alertas_nao_handoff_continuam_saindo():
    """🔴 `_support_alert` tem CINCO chamadores. Só UM é handoff. Mexer na
    definição calaria *"a URA está calada há 20min"*, *"o humano sumiu"*,
    *"nunca começou"* e *"passou do prazo"* — quatro avisos que a corretora
    recebe hoje e que não têm nada a ver com esta SPEC."""
    fonte = _sem_comentario(VIGIA.read_text(encoding="utf-8"))
    chamadas = fonte.count("_support_alert(")
    assert chamadas >= 5, (
        f"só {chamadas} referências a `_support_alert` — os quatro alertas "
        "não-handoff do Vigia podem ter sido calados junto com o conserto")
    for achado in ("ura_silent", "human_silent_alert", "never_started", "deadline"):
        assert achado in fonte, f"o alerta `{achado}` sumiu do Vigia"


def test_CONTROLE_o_handoff_do_vigia_passa_pela_regra_e_os_outros_NAO():
    """A cirurgia é no ramo de handoff, e só nele."""
    corpo = _funcao(VIGIA, "_sentinela_recover")
    assert "_entregar_dossie_com_marcador(" in corpo, (
        "o handoff do Vigia deixou de passar pela regra compartilhada")
    fonte = _sem_comentario(VIGIA.read_text(encoding="utf-8"))
    # os quatro alertas continuam chamando `_support_alert` DIRETO — sem o
    # marcador, que é de handoff e não de "a URA está calada"
    assert fonte.count("_entregar_dossie_com_marcador(") == 2, (
        "a regra do marcador vazou para outros alertas — eles não são handoff, "
        "e um teto de 4 por conversa calaria avisos operacionais legítimos")


# ---------------------------------------------------------------------------
# 6. BLOCO C.1 — A ORDEM, e ela é uma decisão da §4 da SPEC
# ---------------------------------------------------------------------------

def test_o_segurado_e_avisado_DEPOIS_do_dossie():
    """🔴 *"Primeiro exista o colega, depois se promete o colega."*

    📊 A frase saía ANTES de qualquer tentativa de avisar alguém, e saía IGUAL
    nos dois casos. Numa corretora sem destino de suporte, *"um colega da
    equipe vai assumir daqui a pouquinho"* é uma promessa sobre uma pessoa que
    não existe — e o segurado desliga o telefone achando que resolveu.

    ⚠️ A ordem NÃO é estilo: é o que torna possível o texto depender do
    desfecho. Avisar primeiro obriga a escolher a frase antes de saber o que
    aconteceu, e a única frase possível aí é a otimista.
    """
    fonte = _sem_comentario(ROUTER.read_text(encoding="utf-8"))
    ramo = fonte.split('if state == "needs_human":', 1)[-1]
    pos_dossie = ramo.find("entregar_dossie_uma_vez(")
    pos_aviso = ramo.find("aviso_de_handoff(")
    assert pos_dossie != -1, "o ramo de needs_human não entrega mais o dossiê"
    assert pos_aviso != -1, "o ramo de needs_human não avisa mais o segurado"
    assert pos_aviso > pos_dossie, (
        "o segurado volta a ser avisado ANTES do dossiê — a promessa sai antes "
        "de existir alguém para cumpri-la")


def test_a_promessa_antiga_nao_sobrou_em_lugar_nenhum():
    """🔴 O gate do BLOCO C pede a busca, e ela é o guarda: `grep -rn "vai
    assumir" backend/app/` — toda ocorrência com o caso que a autoriza.

    A frase só pode existir onde o dossiê comprovadamente saiu.
    """
    # ⚠️ Sobre o CÓDIGO, nunca sobre o arquivo: os três comentam o conserto
    # CITANDO a frase antiga, e é assim que ela deve aparecer — como registro
    # do que foi tirado. Um guarda que reprova a citação reprova a memória.
    proibida = "colega da equipe vai assumir daqui a pouquinho"
    for arquivo in (ROUTER, VIGIA, MOTOR):
        codigo = _sem_comentario(arquivo.read_text(encoding="utf-8"))
        assert proibida not in codigo, (
            f"a promessa incondicional voltou ao CÓDIGO de {arquivo.name}")
