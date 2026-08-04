"""O encaminhamento chega ao segurado — e o caso encerra resolvido, não abandonado.

P-46. As peças existiam, estavam provadas, e ninguém as chamava.
-----------------------------------------------------------------
Até 03/08/2026 todo corredor tinha um fim só: chegar ao protocolo. Vidros provou
que isso é falso.

📊 URA da Porto, observada em 03/08/2026 — TRÊS mensagens seguidas::

    "Certo. Para conserto ou reparo de vidro, retrovisor, farol ou lanterna,
     é necessário *preencher o formulário* de sinistro de vidros abaixo"
    "https://porto.vc/reparovidros"
    "Não se preocupe, esse acionamento *para vidros* não irá afetar a sua
     classe de bônus."

📊 URA da Zurich, mesma data — orientação, e nenhum link::

    "*Assistência a vidros*: encontre informações sobre como pedir o reparo ou
     a troca de vidros, para-brisa, faróis e retrovisores"

`corridor_playbooks` declarava tudo o que era preciso: `outcome: encaminha`,
`referral: True` no passo, `client_message`, `closes_as`. E
``detect_referral_step()`` existia, tinha teste — e **nenhum chamador em
produção**.

O que acontecia na prática: o passo era `noop` (correto — não se responde à URA
aqui), a conversa parava, e o caso ficava aberto até o watchdog. **O segurado
nunca recebia o formulário.** O desfecho era registrado como abandono, e o
trabalho que a corretora fez virava nada.

Por que não se fecha na primeira mensagem
------------------------------------------
O entregável da Porto é o LINK, e ele vem na mensagem SEGUINTE, sozinho. Fechar
na âncora entregaria ao segurado uma frase sobre um formulário sem o formulário.
Então a âncora abre uma janela curta de escuta, o link é capturado pelo mesmo
`extract_capture_anchors` de sempre, e só aí o caso encerra.

E os dois tipos não pedem a mesma coisa:

    formulario (Porto)   o entregável é o ENDEREÇO — sem link, handoff
    orientacao (Zurich)  o entregável é o TEXTO — fecha na hora

Esperar link na Zurich transformaria o desfecho certo em handoff, que é
exatamente o defeito que P-46 existe para desfazer.

O link NUNCA é escrito no código
---------------------------------
Quem escreve o endereço é a seguradora, na hora. Link de seguradora muda; link
decorado no código vira link morto na mão de quem está com o para-brisa
trincado. Por isso, sem link capturado, o caso de formulário vai para uma
pessoa — e não para um endereço de memória.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _so_codigo(fonte: str) -> str:
    """Comentário não é prova — e atrapalha: os comentários deste conserto
    CITAM `clear_active_dispatch` e o endereço observado da Porto. Comparar
    posições ou procurar strings sem tirá-los mede o texto, não o programa."""
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))


for _nome in ("app", "app.services", "app.services.atlas", "app.tasks"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, os.path.join(RAIZ, rel))
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PB = _carregar("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
DS = _carregar("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")

# As frases REAIS (📊 ura_maps status='observed', 03/08/2026).
PORTO_MENU = ("O que você precisa? Guincho (reboque) Bateria Troca de pneu Conserto de vidro "
              "(Inclui retrovisor, farol ou lanterna) Chaveiro para o veículo Táxi")
PORTO_FORM = ("Certo. Para conserto ou reparo de vidro, retrovisor, farol ou lanterna, "
              "é necessário *preencher o formulário* de sinistro de vidros abaixo")
PORTO_LINK = "https://porto.vc/reparovidros"
PORTO_BONUS = ("Não se preocupe, esse acionamento *para vidros* não irá afetar a sua "
               "classe de bônus.")
ZURICH_MENU = ("Você deseja acionar qual serviço? Acionar seguro Assistência 24h "
               "Assistência a vidros Voltar ao menu")
ZURICH_INFO = ("*Assistência a vidros*: encontre informações sobre como pedir o reparo ou a "
               "troca de vidros, para-brisa, faróis e retrovisores")

CASO_VIDROS = {
    "titular_cpf": "11122233344", "veiculo_placa": "ABC1D23",
    "problema_descricao": "para-brisa trincado", "quando": "amanha de manha",
    "telefone_contato": "48991234567",
}


def _sessao(insurer: str):
    return DS.start_dispatch(DS.new_dispatch_session(
        case_id=f"c-{insurer}", company_id="co",
        playbook_ref=f"{insurer}-auto-whatsapp@v1",
        subservice="vidros", slots=CASO_VIDROS))


def _saidas(s) -> list:
    return [t["text"] for t in s["transcript"] if t["direction"] == "out"]


# --------------------------------------------------------------------------- #
# Casos
# --------------------------------------------------------------------------- #

def teste_o_motor_consome_o_encaminhamento():
    print("\n[1] Porto: o formulario e ENTREGUE e o caso ENCERRA")
    s = _sessao("porto")
    s = DS.handle_insurer_message(s, PORTO_MENU)
    checar(_saidas(s)[-1:] == ["Conserto de vidro"], "o menu real e respondido", str(_saidas(s)[-1:]))

    antes = len(_saidas(s))
    s = DS.handle_insurer_message(s, PORTO_FORM)
    checar(len(_saidas(s)) == antes, "a mensagem do formulario NAO recebe resposta",
           "responder aqui empurraria a URA para um passo que nao existe")
    checar(bool(s.get("referral")), "mas o motor RECONHECE o encaminhamento",
           "era isto que faltava: detect_referral_step nao tinha chamador")
    checar(s["state"] == "ura",
           "e ainda nao encerra — o link vem na proxima mensagem", s["state"])

    s = DS.handle_insurer_message(s, PORTO_LINK)
    checar(s["state"] == "encaminhado",
           "com o link em maos, o caso encerra como ENCAMINHADO", s["state"])
    checar(s.get("reason") == "encaminhado:formulario",
           "e o desfecho tem nome proprio", str(s.get("reason")))
    checar(s["referral"].get("link") == PORTO_LINK,
           "o link entregue e o que a SEGURADORA mandou", str(s["referral"].get("link")))
    checar(len(_saidas(s)) == antes,
           "e nada foi respondido a URA no caminho inteiro", str(_saidas(s)))


def teste_nao_e_handoff_nem_protocolo():
    print("\n[2] Encaminhado NAO e handoff, e NAO e protocolo")
    s = _sessao("porto")
    for msg in (PORTO_MENU, PORTO_FORM, PORTO_LINK):
        s = DS.handle_insurer_message(s, msg)

    checar(s["state"] != "needs_human",
           "o caso NAO cai em handoff",
           "antes, a conversa parava e o caso ficava aberto ate o watchdog")
    checar(s["state"] != "captured" and not (s.get("captured") or {}).get("protocol"),
           "e tambem nao finge protocolo — a seguradora nao emitiu nenhum",
           str((s.get("captured") or {}).get("protocol")))
    checar("encaminhado" in DS.DISPATCH_STATES,
           "`encaminhado` e um estado declarado da maquina")
    checar("encaminhado" in DS.FASES_ENCERRADAS,
           "e e uma fase ENCERRADA — o trabalho acabou")
    checar("encaminhado" not in DS.FASES_EM_VOO,
           "nao fica em voo esperando um protocolo que nunca vem")
    checar(DS.status_duravel_da_fase("encaminhado") == "completed",
           "e o Work Run fecha como COMPLETED, nao cancelled",
           DS.status_duravel_da_fase("encaminhado"))


def teste_a_mensagem_seguinte_nao_reabre_a_conversa():
    print("\n[3] Depois de encerrado, a URA pode falar — o motor nao responde")
    s = _sessao("porto")
    for msg in (PORTO_MENU, PORTO_FORM, PORTO_LINK):
        s = DS.handle_insurer_message(s, msg)
    antes = len(_saidas(s))
    estado = s["state"]

    # A terceira mensagem da sequencia observada chega DEPOIS do link.
    s = DS.handle_insurer_message(s, PORTO_BONUS)
    checar(len(_saidas(s)) == antes, "a mensagem seguinte nao vira resposta", str(_saidas(s)))
    checar(s["state"] == estado, "e o estado continua encaminhado", s["state"])
    checar(not (s.get("captured") or {}).get("protocol"),
           "e nada nela vira 'protocolo'",
           "depois do encaminhamento, uma ancora de protocolo que casasse um "
           "numero qualquer diria ao segurado que o servico foi aberto")


def teste_orientacao_nao_espera_link_que_nunca_vem():
    print("\n[4] Zurich: orientacao fecha na hora — o texto E o entregavel")
    s = _sessao("zurich")
    s = DS.handle_insurer_message(s, ZURICH_MENU)
    checar(_saidas(s)[-1:] == ["Assistência a vidros"], "o menu real e respondido",
           str(_saidas(s)[-1:]))

    antes = len(_saidas(s))
    s = DS.handle_insurer_message(s, ZURICH_INFO)
    checar(len(_saidas(s)) == antes, "o texto informativo nao e respondido")
    checar(s["state"] == "encaminhado",
           "e o caso encerra IMEDIATAMENTE como encaminhado", s["state"])
    checar(s.get("reason") == "encaminhado:orientacao", "com o tipo certo", str(s.get("reason")))
    checar(s["referral"].get("link") == "",
           "sem link, porque a seguradora nao mandou nenhum",
           "📊 a mensagem observada em 03/08/2026 nao traz link")
    checar(PB.subservice_referral(_pb("zurich"), "vidros").get("kind") == "orientacao",
           "a Zurich se declara orientacao, e e o que decide nao esperar")


def _pb(insurer: str) -> dict:
    return PB.get_playbook(PB.resolve_playbook_ref(insurer, "auto"))


def teste_formulario_sem_link_vai_para_uma_pessoa():
    print("\n[5] Formulario sem link NAO inventa endereco")
    s = _sessao("porto")
    s = DS.handle_insurer_message(s, PORTO_MENU)
    s = DS.handle_insurer_message(s, PORTO_FORM)
    # A URA fala outras coisas, e o link nunca vem.
    for i in range(DS.ENCAMINHAMENTO_MENSAGENS_DE_ESPERA):
        checar(s["state"] == "ura", f"ainda esperando o link ({i + 1}a mensagem)", s["state"])
        s = DS.handle_insurer_message(s, f"Aguarde um momento, por favor. ({i})")

    checar(s["state"] == "needs_human",
           "esgotada a janela, o caso vai para uma PESSOA", s["state"])
    checar(s.get("reason") == "encaminhamento_sem_link",
           "com o motivo escrito", str(s.get("reason")))
    checar("porto.vc" not in str(s), "e nenhum endereco foi inventado",
           "link de seguradora muda; link decorado vira link morto na mao do segurado")


def teste_o_link_nao_esta_escrito_no_codigo():
    print("\n[6] O endereco nunca mora no repositorio")
    # Só o CÓDIGO. O endereço observado está citado nos comentários de propósito
    # — é a evidência de onde o corredor saiu. O que não pode é ele ser um valor
    # que o programa usa.
    playbooks = _so_codigo(_ler("app", "services", "corridor_playbooks.py"))
    ref = PB.subservice_referral(_pb("porto"), "vidros")
    checar("http" not in ref.get("client_message", ""),
           "o texto ao cliente nao traz URL", ref.get("client_message", "")[:60])
    checar("porto.vc" not in playbooks,
           "e o endereco real da Porto nao e VALOR em corridor_playbooks.py",
           "quem escreve o link e a seguradora, na hora")
    checar("porto.vc" not in _so_codigo(_ler("app", "services", "insurer_dispatch_service.py")),
           "nem no motor")
    checar(ref.get("link_capture") == "tracking_link",
           "o corredor diz apenas ONDE o link cai quando ele chega")


def teste_o_segurado_recebe_e_fica_rastro():
    print("\n[7] O roteador ENTREGA — e deixa rastro (a licao de R4)")
    roteador = _so_codigo(_ler("app", "services", "dispatch_router.py"))
    trecho = roteador.split('if state == "encaminhado":', 1)
    checar(len(trecho) == 2, "o roteador trata o estado `encaminhado`",
           "sem isto, o motor encerraria certo e o segurado continuaria sem o formulario")
    if len(trecho) != 2:
        return
    corpo = trecho[1].split('if state == "captured":', 1)[0]

    checar("send_to_client(client_phone, aviso)" in corpo,
           "a mensagem vai para o SEGURADO")
    checar('referral.get("client_message")' in corpo and 'referral.get("link")' in corpo,
           "e leva o texto do corredor MAIS o link capturado")
    checar('referral.get("insurer_text")' in corpo,
           "e as palavras da propria seguradora, sem parafrase",
           "os dois client_message mandam repassar exatamente o que ela enviou")
    checar("_registrar_fala_ao_cliente" in corpo and '"[AO CLIENTE] ' in corpo,
           "o aviso deixa rastro no dossie e no transcript",
           "falar com o cliente e nao registrar faz o agente prometer de novo "
           "o que ja foi entregue")
    checar("client_notify_failed" in corpo and "_support_alert_seguro" in corpo,
           "e falha de entrega NAO passa em silencio",
           "sem a entrega, o encaminhamento nao aconteceu")

    i_save = corpo.index("save_active_dispatch")
    i_clear = corpo.index("clear_active_dispatch")
    checar(i_save < i_clear,
           "salva ANTES de liberar a sessao",
           "clear_active_dispatch rele do Redis para saber que Work Run fechar; "
           "sem o save ele leria a fase anterior e gravaria `cancelled`")
    checar("_start_next_in_queue" in corpo,
           "e o proximo acionamento da fila entra")


def teste_o_resto_do_sistema_conhece_o_desfecho():
    print("\n[8] Um estado novo que ninguem conhece e um estado perdido")
    esperado = {
        ("app/tasks/dispatch_watchdog.py", "_TERMINAL_STATES"):
            "o Vigia para de cobrar resposta de uma conversa que acabou",
        ("app/services/operational_view.py", "_STATE_PT"):
            "a tela diz o desfecho em portugues, em vez do nome cru",
        ("app/services/activity_log.py", "DISPATCH_STATE_TITLES"):
            "o feed de Atividades registra o trabalho entregue",
        ("app/services/platform_outbound.py", "_ESTADOS_QUE_NAO_OCUPAM"):
            "e o segurado deixa de contar como 'em atendimento'",
    }
    for (caminho, marca), porque in esperado.items():
        fonte = _ler(*caminho.split("/"))
        bloco = fonte.split(marca, 1)[1].split("\n\n", 1)[0] if marca in fonte else ""
        checar("encaminhado" in bloco, f"{caminho}: {marca} conhece `encaminhado`", porque)

    roteador = _ler("app", "services", "dispatch_router.py")
    fecha = roteador.split("final = status or (", 1)[1].split(")", 1)[0]
    checar("encaminhado" in fecha,
           "e o Work Run fecha como COMPLETED, nao cancelled",
           f"{fecha!r} — desfecho de sucesso gravado como abandono e o defeito "
           "de P-46 sobrevivendo no relatorio")


def teste_o_guarda_tem_como_falhar():
    print("\n[9] CONTROLE — quem ABRE nao pode ser encaminhado")
    # A Azul tem vidros como TECLA e vai ate o protocolo. Se o encaminhamento
    # disparasse nela, o conserto teria trocado um defeito por outro pior:
    # um caso que a seguradora ABRIRIA seria encerrado sem protocolo.
    azul = _pb("azul")
    checar(PB.subservice_outcome(azul, "vidros") == PB.OUTCOME_ABRE,
           "Azul ABRE vidros", PB.subservice_outcome(azul, "vidros"))
    checar(PB.subservice_referral(azul, "vidros") == {},
           "e nao declara encaminhamento nenhum")
    checar(PB.detect_referral_step(azul, PORTO_FORM) is None,
           "a frase da Porto NAO dispara encaminhamento na Azul",
           "cada corredor so encaminha onde a evidencia dele diz que encaminha")

    s = _sessao("azul")
    s = DS.handle_insurer_message(s, PORTO_FORM)
    checar(not s.get("referral"), "e a sessao da Azul nao entra em encaminhamento",
           str(s.get("referral")))
    checar(s["state"] != "encaminhado", "nem encerra como encaminhado", s["state"])

    # E o outro lado do controle: um corredor SEM o passo de referral segue o
    # caminho de sempre. Se `detect_referral_step` casasse qualquer coisa, todos
    # os casos acima passariam sem provar nada.
    allianz = _pb("allianz")
    for texto in (PORTO_FORM, ZURICH_INFO, PORTO_MENU, "Qual o CPF do titular?"):
        checar(PB.detect_referral_step(allianz, texto) is None,
               f"Allianz nao encaminha: {texto[:38]}…",
               "ela nao tem vidros observado — cai em handoff, que e o certo")


def teste_todo_desfecho_novo_entra_nos_MAPAS():
    """Estado que nasce fora dos mapas so existe para quem o escreveu.

    📊 03/08/2026: `resolvido` foi criado pelo encerramento do follow-up e NAO
    entrou em mapa nenhum. O preco, medido na auditoria do mesmo dia:

        ordem_da_fase          -> 0
        status_duravel_da_fase -> "running"   o Work Run NUNCA fechava
        _TERMINAL_STATES       -> ausente     o Vigia perseguiria para sempre
                                              uma conversa encerrada com sucesso

    Este caso nao guarda `resolvido`: guarda a REGRA. Todo estado de
    `DISPATCH_STATES` tem de estar nos quatro mapas — inclusive o proximo, que
    ainda nao existe.
    """
    print("\n[E5] todo estado declarado esta nos quatro mapas")
    faltando = []
    for estado in DS.DISPATCH_STATES:
        if estado not in DS._ORDEM_DAS_FASES:
            faltando.append(f"{estado}: fora de _ORDEM_DAS_FASES")
        if estado not in DS.STATUS_WORK_RUN_POR_FASE:
            faltando.append(f"{estado}: fora de STATUS_WORK_RUN_POR_FASE")
        em_voo = estado in DS.FASES_EM_VOO
        encerrada = estado in DS.FASES_ENCERRADAS
        if em_voo == encerrada:
            faltando.append(f"{estado}: precisa estar em EM_VOO **ou** ENCERRADAS, nunca nos dois nem em nenhum")
    checar(not faltando, "todo estado de DISPATCH_STATES esta nos quatro mapas", "; ".join(faltando))

    # E o Vigia precisa parar em toda fase encerrada — senao cutuca uma
    # seguradora sobre um servico que ja foi prestado.
    wd = (RAIZ / "app/tasks/dispatch_watchdog.py").read_text(encoding="utf-8")
    i = wd.index("_TERMINAL_STATES = {")
    bloco = wd[i:wd.index("}", i)]
    fora = [e for e in DS.FASES_ENCERRADAS if f'"{e}"' not in bloco]
    checar(not fora, "o Vigia para em toda fase encerrada", f"nao conhece: {fora}")


def main() -> int:
    print("=" * 74)
    print("O ENCAMINHAMENTO CHEGA AO SEGURADO — P-46")
    print("=" * 74)

    for teste in (teste_o_motor_consome_o_encaminhamento,
                  teste_nao_e_handoff_nem_protocolo,
                  teste_a_mensagem_seguinte_nao_reabre_a_conversa,
                  teste_orientacao_nao_espera_link_que_nunca_vem,
                  teste_formulario_sem_link_vai_para_uma_pessoa,
                  teste_o_link_nao_esta_escrito_no_codigo,
                  teste_o_segurado_recebe_e_fica_rastro,
                  teste_o_resto_do_sistema_conhece_o_desfecho,
                  teste_o_guarda_tem_como_falhar):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("ENCAMINHAR E UM DESFECHO, NAO UM ABANDONO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
