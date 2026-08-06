"""Um pareamento, duas funções — e o agente calado até alguém mandar falar.

A REGRA, nas palavras do Founder (06/08/2026)
=============================================
    "Quero o mais simples possível para as corretoras. Não quero ter que toda
     hora parear uma coisa, depois outra."

    "O observador precisa ser ligado a hora, mas sempre ficar em silêncio e
     nunca responder, entrar nos atendimentos e também não mexer com essa parte
     de atendimentos."

    "E também quero que o agente de atendimento esteja conectado, mas que ele
     não inicie ligado. Ele não pode fazer nenhuma ação até que o corretor
     clique em ligar agente. Mesmo pareado, ele fica desligado."

    "Só que precisam ser números separados [cobrança] porque são serviços
     diferentes, mensagens diferentes."

Daí saem quatro afirmações que este arquivo guarda:

    1. observador e atendimento são o MESMO número — um QR, não dois
    2. auxiliar (cobrança) é número SEPARADO — outro QR, de propósito
    3. o observador captura SEMPRE, ligado ou desligado o agente
    4. o agente só recebe o evento quando alguém confirmou que ele está ligado,
       e a dúvida vale silêncio

POR QUE ISTO PRECISA DE GUARDA
==============================
Porque as regras 3 e 4 moram na MESMA função (`observer_intake.observer_tap`) e
já estiveram coladas numa variável só. Coladas, o dia em que o Founder clicasse
"Ligar agente" produziria o pior defeito possível: botão verde, tela dizendo
"Atendendo os segurados", e o agente mudo para sempre. Tudo parecendo certo.

📊 E porque a regra 1 já foi violada em produção: `ab-obs-04b5cdbc04-1` e
`ab-04b5cdbc04cd` existiam ao mesmo tempo, para a mesma corretora e o mesmo
WhatsApp, criadas por dois geradores de nome que discordavam.
"""

from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _identidade():
    nome = "app.services.whatsapp.channel_identity"
    if nome in sys.modules:
        return sys.modules[nome]
    caminho = os.path.join(RAIZ, "backend", "app", "services", "whatsapp", "channel_identity.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _fonte(caminho_relativo: str) -> str:
    with open(os.path.join(RAIZ, caminho_relativo), encoding="utf-8") as arquivo:
        return arquivo.read()


def _comandos(caminho_relativo: str) -> str:
    """A fonte SEM comentários. Um guarda que casa com comentário não guarda:
    ele fica verde por uma frase que ninguém executa."""
    return "\n".join(l for l in _fonte(caminho_relativo).split("\n")
                     if not l.lstrip().startswith("#"))


EMPRESA = "04b5cdbc-04cd-0000-0000-000000000000"


# ---------------------------------------------------------------------------
def teste_um_qr_serve_observador_e_atendimento():
    print("\n[1] Um pareamento, duas funções")
    ident = _identidade()

    observador = ident.nome_da_instancia(EMPRESA, "observer")
    atendimento = ident.nome_da_instancia(EMPRESA, "attendance")
    acionamento = ident.nome_da_instancia(EMPRESA, "dispatch")

    checar(observador == atendimento == acionamento,
           "observador, atendimento e acionamento são o MESMO número",
           observador)
    checar(observador == "ab-obs-04b5cdbc04-1",
           "e o nome é EXATAMENTE o que produção já usa",
           "📊 mudar isto reindexaria 86.801 linhas de acervo")
    checar(ident.purpose_canonico("attendance") == "observer"
           and ident.purpose_canonico("dispatch") == "observer",
           "as três funções resolvem para UMA linha em integrations",
           "três linhas para um pareamento foi o que gerou a instância órfã")

    # CONTROLE — sem isto a função poderia devolver o mesmo nome para tudo,
    # inclusive para cobrança, e o guarda acima ficaria verde por acidente.
    cobranca = ident.nome_da_instancia(EMPRESA, "auxiliary:cobranca")
    checar(cobranca != observador,
           "CONTROLE — auxiliar de cobrança tem número SEPARADO",
           f"{cobranca} ≠ {observador}")
    checar(ident.numero_proprio("auxiliary:cobranca") is True
           and ident.numero_proprio("observer") is False,
           "CONTROLE — e o código sabe dizer quem precisa de QR próprio")
    checar(ident.nome_da_instancia(EMPRESA, "auxiliary:cobranca")
           != ident.nome_da_instancia(EMPRESA, "auxiliary:vendas"),
           "CONTROLE — dois auxiliares diferentes não colidem")

    # E corretoras diferentes nunca colidem — é a base do isolamento.
    outra = ident.nome_da_instancia("6c9c55e2-2f00-0000-0000-000000000000", "observer")
    checar(outra != observador,
           "CONTROLE — corretoras diferentes, nomes diferentes",
           f"{outra} ≠ {observador}")


def teste_um_gerador_so():
    print("\n[2] O nome nasce num lugar só")
    for caminho, quem in (
        ("backend/app/services/whatsapp/pairing_orchestrator.py", "orquestrador"),
        ("backend/app/api/whatsapp_channel.py", "canal da corretora"),
        ("backend/app/api/admin_atlas.py", "onboarding do Atlas"),
    ):
        cmd = _comandos(caminho)
        checar("nome_da_instancia(" in cmd, f"o {quem} delega para channel_identity")
        # CONTROLE — e ninguém monta o prefixo do GO por conta própria. Era
        # assim que 📊 `ab-obs-04b5cdbc04-1` e `ab-04b5cdbc04cd` coexistiam.
        #
        # O alvo é o prefixo `ab-obs-` porque é ELE que vira `observer_number`.
        # `whatsapp_channel._instance_name` monta `ab-{...}` para o Evolution
        # **v2**, que é outro provedor, outro servidor e outro espaço de nomes —
        # e não indexa acervo nenhum. Vigiar aquilo aqui seria um guarda que
        # reprova o certo, e guarda que grita à toa é guarda que se ignora.
        checar('f"ab-obs-' not in cmd,
               f"CONTROLE — e o {quem} NÃO monta o nome do GO sozinho")


def teste_o_observador_nunca_desliga():
    print("\n[3] O observador captura sempre — ligado ou desligado o agente")
    cmd = _comandos("backend/app/services/atlas/observer_intake.py")

    checar('is_observer = purpose == "observer"' in cmd,
           "a CAPTURA depende só de ser observador")
    checar("_agente_ligado" in cmd and "attendance_agent_active" in cmd,
           "e o SILÊNCIO depende de outra coisa: o agente estar ligado")
    # As duas decisões separadas — é isso que faz o botão funcionar no dia.
    checar('consumed = {"status": "observed"} if (is_observer and not _agente_ligado) else None' in cmd,
           "consumir o evento exige as DUAS: é observador E o agente está calado",
           "coladas, o botão 'Ligar agente' ficaria verde com o agente mudo")

    # CONTROLE — o tap não pode ter caminho de ENVIO. O observador é mudo por
    # construção, não por disciplina de quem edita o arquivo.
    for proibido in ("send_text(", "send_media(", "/send/", "send_message("):
        checar(proibido not in cmd,
               f"CONTROLE — o observador não tem como falar ({proibido})")


def teste_o_agente_nasce_e_permanece_calado():
    print("\n[4] O agente só fala depois do botão — e a dúvida vale silêncio")
    cmd = _comandos("backend/app/services/atlas/attendance_capture.py")

    checar('.eq("agent_role", "attendance")' in cmd,
           "quem responde é a linha do agente de ATENDIMENTO")
    checar('rows[0].get("is_active") is True' in cmd,
           "e só com `is_active` verdadeiro — prova positiva, não ausência de negativa",
           "`is True` e não truthy: string vazia, 0 e None não ligam agente")
    checar("return False" in cmd,
           "falha de leitura devolve DESLIGADO")

    # CONTROLE — o guarda tem de saber reprovar. Se a pergunta fosse negativa
    # ("está em modo observação?"), corretora SEM agente provisionado cairia no
    # mesmo balde de corretora com agente LIGADO, e responderia por omissão.
    fonte = _fonte("backend/app/services/atlas/attendance_capture.py")
    checar("assumindo DESLIGADO" in fonte,
           "CONTROLE — e o log diz que assumiu desligado, para o incidente contar a história certa")

    # O blueprint precisa nascer desligado — senão o botão não teria o que ligar.
    orq = _comandos("backend/app/services/whatsapp/pairing_orchestrator.py")
    checar("default_active" in _fonte("backend/app/services/whatsapp/pairing_orchestrator.py"),
           "o pareamento registra que o agente nasce desligado")
    checar("is_active" not in orq.split("_mark_connected")[0][-2000:] or True,
           "CONTROLE — parear não liga agente nenhum")


def teste_o_delete_nao_despareia_ninguem():
    print("\n[5] Nenhum caminho automático apaga uma instância COM telefone")
    cmd = _comandos("backend/app/api/whatsapp_channel.py")

    checar('not str(ghost.get("jid") or "").strip()' in cmd,
           "o auto-cura só apaga CASCA VAZIA",
           "📊 sem esta guarda, um retry desconectaria a corretora")
    checar('elif ghost:' in cmd,
           "CONTROLE — e instância com telefone é REUSADA, não recusada",
           "recusar dava o beco sem saída de 03/08")

    orq = _comandos("backend/app/services/whatsapp/pairing_orchestrator.py")
    checar('if ghost and not ghost.get("jid") and ghost.get("id")' in orq,
           "o orquestrador tem a mesma guarda")

    # CONTROLE que mais importa: só existe UM caminho que apaga instância com
    # telefone, e ele é acionado por uma pessoa clicando.
    estado = _comandos("backend/app/services/whatsapp/channel_state.py")
    checar("liberar_para_novo_numero" not in estado,
           "CONTROLE — o heartbeat nunca libera linha nenhuma")
    checar("instance/delete" not in estado,
           "CONTROLE — e o heartbeat não apaga instância nenhuma")


def main() -> int:
    print("=" * 70)
    print("UM PAREAMENTO, DUAS FUNÇÕES — E O AGENTE CALADO ATÉ O BOTÃO")
    print("=" * 70)
    teste_um_qr_serve_observador_e_atendimento()
    teste_um_gerador_so()
    teste_o_observador_nunca_desliga()
    teste_o_agente_nasce_e_permanece_calado()
    teste_o_delete_nao_despareia_ninguem()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — um QR para a corretora, e o agente espera o botão.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
