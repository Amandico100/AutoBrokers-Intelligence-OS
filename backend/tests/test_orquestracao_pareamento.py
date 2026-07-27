"""A orquestração do pareamento: quem observa, quem responde, quem fica parado.

As regras do Founder (27/07/2026), em ordem de importância
----------------------------------------------------------
1. **O Observador nunca desliga.** Pareou, observa — com o agente ligado ou
   desligado, hoje e daqui a um ano. Ele completa rotas que faltam e atualiza
   quando encontra diferença.
2. **O agente de atendimento nasce desligado** e só é ligado pelo botão.
3. Ligado, ele responde. Desligado, **nunca** responde: quem atende é a pessoa,
   direto no WhatsApp.
4. Cada corretora é independente. Ligar o agente da Resulta não faz nada na
   AutoFleet.
5. Com o agente desligado, o Cartógrafo fica **parado** — o número é da
   atendente humana.

O defeito que este arquivo existe para impedir de voltar
--------------------------------------------------------
`observer_tap` devolvia "consumido" sempre que a integração fosse
`purpose='observer'`, e o webhook faz `if _observed is not None: return`. Como o
dashboard pareia justamente com `purpose='observer'`, **toda mensagem morria
ali** — inclusive depois de o botão "Ligar agente" ser clicado.

No dia 8 o Founder clicaria no botão, veria "Atendendo os segurados" na tela, e
o agente ficaria mudo para sempre. O pior tipo de defeito: tudo parece certo.

A causa era ter colado duas decisões diferentes numa variável só — CAPTURAR e
CONSUMIR. Capturar nunca para; consumir para quando o agente assume.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# `lib/` e `app/` do Next vivem na raiz do repositorio, um nivel acima de
# `backend/`. Ler o arquivo errado daria FileNotFoundError — que ao menos falha
# alto; o perigoso seria ler um arquivo homonimo e provar a coisa errada.
RAIZ_REPO = os.path.dirname(RAIZ)
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


def _ler_repo(*p: str) -> str:
    with open(os.path.join(RAIZ_REPO, *p), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario_py(fonte: str) -> str:
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))


def _sem_comentario_ts(fonte: str) -> str:
    sem = "\n".join(l for l in fonte.split("\n")
                    if not l.lstrip().startswith(("//", "*", "/*")))
    return re.sub(r"/\*.*?\*/", "", sem, flags=re.S)


# --------------------------------------------------------------------------
def teste_capturar_e_consumir_sao_decisoes_separadas():
    print("\n[1] Capturar e consumir são decisões diferentes")
    fonte = _sem_comentario_py(_ler("app", "services", "atlas", "observer_intake.py"))

    checar("attendance_agent_active" in fonte,
           "o consumo consulta se o agente está LIGADO",
           "sem isso, a mensagem morre no observador mesmo com o agente ligado")
    checar("is_observer and not _agente_ligado" in fonte,
           "só consome enquanto o agente está calado")
    # A forma antiga não pode voltar: ela é o defeito.
    checar(re.search(r"consumed\s*=\s*\{\"status\":\s*\"observed\"\}\s*if\s+is_observer\s+else\s+None",
                     fonte) is None,
           "a forma antiga (consumir sempre) não voltou",
           "era ela que deixaria o agente mudo no dia 8")


def teste_o_observador_captura_com_o_agente_ligado():
    print("\n[2] Com o agente LIGADO, o Observador continua capturando")
    fonte = _sem_comentario_py(_ler("app", "services", "atlas", "observer_intake.py"))
    # `is_observer` governa a captura e NÃO pode depender do estado do agente.
    i = fonte.find("is_observer = purpose ==")
    checar(i != -1, "is_observer vem do propósito da integração")
    linha = fonte[i: fonte.find("\n", i)]
    checar("_agente_ligado" not in linha and "attendance_agent_active" not in linha,
           "e NÃO depende do estado do agente",
           "se dependesse, ligar o agente desligaria o Observador — o oposto "
           "da regra do Founder")
    # A captura de conversa com segurado é guardada por `is_observer`.
    checar("if is_observer:" in fonte,
           "a captura de conversa com segurado é guardada por is_observer")


def teste_agente_nasce_desligado():
    print("\n[3] O agente de atendimento nasce desligado")
    bp = _sem_comentario_ts(_ler_repo("lib", "admin", "agent-blueprints-canonical.ts"))

    def _declaracao(nome: str) -> str:
        """O corpo da constante, da declaração até a próxima `export const`.

        Recortar por número de caracteres não serve: os prompts destes
        blueprints têm milhares de caracteres, e uma janela fixa provaria a
        ausência do campo em vez da presença — falso negativo silencioso.
        """
        i = bp.find(f"export const {nome}")
        if i == -1:
            return ""
        j = bp.find("export const ", i + 10)
        return bp[i: j if j != -1 else len(bp)]

    atendimento = _declaracao("EVEN_ATTENDANCE_BLUEPRINT")
    checar(bool(atendimento), "achei a declaração do blueprint de atendimento")
    checar("default_active: false" in atendimento,
           "o blueprint do atendimento nasce inativo")

    core = _declaracao("AUTOBROKERS_CORE_BLUEPRINT")
    checar("default_active: true" in core,
           "e o chat interno (core) nasce ATIVO",
           "desligar o core entregaria uma corretora sem assistente")

    # E a garantia no banco, para o caminho que não passa pelo blueprint.
    mig = _ler("supabase", "migrations", "20260727_08_atendimento_nasce_desligado.sql")
    checar("before insert on public.agents" in mig,
           "há gatilho no banco cobrindo qualquer caminho de criação")
    checar("before update" not in mig.lower(),
           "e o gatilho NÃO toca em UPDATE",
           "ligar tem de continuar sendo exclusividade do botão")


def teste_parear_nao_mexe_no_agente():
    print("\n[4] Parear NÃO desliga um agente que está trabalhando")
    # Re-parear é comum: telefone desligado, logout, QR vencido, troca de
    # aparelho. Com o desligamento no pareamento, a corretora reconectava e o
    # agente ficava mudo sem ninguém saber.
    fonte = _sem_comentario_py(_ler("app", "services", "whatsapp",
                                    "pairing_orchestrator.py"))
    checar(re.search(r'table\("agents"\)\.update\(\{"is_active"', fonte) is None,
           "o pareamento não escreve em agents.is_active",
           "re-parear silenciaria um agente em produção")


def teste_so_o_botao_liga_e_e_por_corretora():
    print("\n[5] Só o botão liga — e vale para UMA corretora")
    store = _sem_comentario_ts(_ler_repo("lib", "admin", "tenant-agent-store.ts"))
    i = store.find("setTenantAgentActive")
    corpo = store[i: i + 900] if i != -1 else ""
    checar("toggle_only_attendance" in corpo,
           "o toggle recusa qualquer papel que não seja atendimento",
           "o Observador não tem liga-desliga, e o core também não")
    checar(corpo.count("companyId") >= 2,
           "a leitura e a escrita filtram por empresa",
           "sem os dois filtros, ligar uma corretora mexeria na outra")
    checar(".eq('id', agent.id).eq('company_id', companyId)" in corpo,
           "o update casa id E empresa",
           "cinto e suspensório: id sozinho já bastaria, mas o filtro por "
           "empresa torna impossível um id de outra corretora funcionar")


def teste_cartografo_para_com_o_agente_desligado():
    print("\n[6] Com o agente desligado, o Cartógrafo fica parado")
    fonte = _sem_comentario_py(_ler("app", "services", "cartographer_runner.py"))
    i = fonte.find("async def start_exploration")
    corpo = fonte[i: i + 2500] if i != -1 else ""
    checar("attendance_agent_active" in corpo,
           "a exploração confere se o agente está ligado")
    pos_guarda = corpo.find("attendance_agent_active")
    pos_envio = corpo.find('send("Oi")')
    checar(pos_guarda != -1 and pos_envio != -1 and pos_guarda < pos_envio,
           "e confere ANTES de mandar a primeira mensagem",
           "o Cartógrafo escreve no MESMO número da atendente humana")
    checar("dispatch:active" in fonte,
           "o freio do acionamento real continua valendo")


def teste_observador_continua_mudo():
    print("\n[7] Nada disso deu voz ao Observador")
    for arq in ("observer_intake.py", "attendance_capture.py", "weaver.py",
                "history_ingest.py", "templater.py", "atlas_parser.py"):
        fonte = _sem_comentario_py(_ler("app", "services", "atlas", arq))
        envios = re.findall(
            r"\b(send_message|send_text|sendText|enviar_mensagem|start_live_dispatch)\s*\(",
            fonte)
        checar(not envios, f"{arq} continua sem caminho de envio", str(set(envios)))


def teste_confirmar_ligado_falha_para_o_silencio():
    print("\n[8] Não confirmar que o agente está ligado = silêncio")
    fonte = _sem_comentario_py(_ler("app", "services", "atlas",
                                    "attendance_capture.py"))
    i = fonte.find("async def attendance_agent_active")
    fim = fonte.find("async def attendance_observation_mode", i)
    corpo = fonte[i: fim if fim != -1 else i + 2000] if i != -1 else ""
    checar(bool(corpo), "a função existe")
    checar("is True" in corpo,
           "só devolve ligado com prova (is True)",
           "'truthy' aceitaria None e string — e None viraria permissão")
    trecho_except = corpo[corpo.find("except"):] if "except" in corpo else ""
    checar("return False" in trecho_except,
           "falha de leitura devolve DESLIGADO")


def main() -> int:
    print("=" * 70)
    print("ORQUESTRAÇÃO DO PAREAMENTO — QUEM OBSERVA, QUEM RESPONDE, QUEM PARA")
    print("=" * 70)
    for teste in (teste_capturar_e_consumir_sao_decisoes_separadas,
                  teste_o_observador_captura_com_o_agente_ligado,
                  teste_agente_nasce_desligado,
                  teste_parear_nao_mexe_no_agente,
                  teste_so_o_botao_liga_e_e_por_corretora,
                  teste_cartografo_para_com_o_agente_desligado,
                  teste_observador_continua_mudo,
                  teste_confirmar_ligado_falha_para_o_silencio):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O OBSERVADOR NÃO PARA. O AGENTE SÓ FALA SE O BOTÃO MANDAR.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
