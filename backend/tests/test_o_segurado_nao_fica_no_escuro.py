"""O segurado não fica no escuro — nem calado, nem esquecido, nem mal localizado.

📊 03/08/2026, teste adversarial do atendimento. Três defeitos diferentes com o
mesmo desfecho: uma pessoa esperando por algo que nunca vem.

**A exceção muda.** `webhook.py` — o `except` de fora do caminho da IA só
logava. Log não é atendimento: quem mandou a mensagem não vê o Sentry, vê um
WhatsApp que não respondeu. O ramo de áudio, dez passos acima, sempre avisou.
O caminho principal — o que atende todo mundo — não.

**O estado sem saída.** 📊 UMA conversa presa em `HUMAN_REQUESTED` há ~730
horas em produção. Trinta dias. Não foi a marcação que falhou: **nenhum job no
produto olhava `conversations.status`.** O aviso ao suporte saía uma vez, no
instante do pedido; se ninguém viu aquela mensagem, ninguém veria nunca mais.

**A BR-101 destroçada.** 📊 `"Rodovia BR-101, km 150, Palhoça - SC"` virava
rua `"Rodovia BR"`, **número `101`**, bairro `"km 150"`. O número da rodovia
virava número de casa; o quilômetro virava bairro. Não é "quase certo" — é o
endereço de uma casa que existe em outra rua, entregue com confiança.

Errar com confiança é pior que não saber.
"""
from __future__ import annotations

import importlib.util
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


def _carregar(dotted: str, rel: str):
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    for pkg in ("app", "app.services"):
        if pkg not in sys.modules:
            casca = types.ModuleType(pkg)
            casca.__path__ = [str(RAIZ / pkg.replace(".", "/"))]  # type: ignore[attr-defined]
            sys.modules[pkg] = casca
    spec = importlib.util.spec_from_file_location(dotted, RAIZ / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


PB = _carregar("cp_escuro", "app/services/corridor_playbooks.py")


# ==================================================================== #
# 2.3 — a exceção no caminho da IA deixava o segurado mudo
# ==================================================================== #

def _corpo_do_except() -> str:
    """O `except` de fora de `process_whatsapp_message_background`."""
    fonte = (RAIZ / "app/api/webhook.py").read_text(encoding="utf-8")
    i = fonte.index("[WEBHOOK BACKGROUND] Critical Error")
    j = fonte.index("\n# =====", i)
    return fonte[i:j]


def a_excecao_nao_emudece_mais() -> None:
    corpo = _corpo_do_except()
    checar("send_message" in corpo,
           "o `except` critico agora FALA com o cliente",
           "antes ele so logava — e log nao e atendimento")
    checar("_pode_falar_ao_cliente" in corpo and "_resposta_ja_enviada" in corpo,
           "e so fala sob as DUAS condicoes")


def o_fallback_respeita_o_portao_de_silencio() -> None:
    """A trava que impede o conserto de virar um defeito pior.

    Falar por uma corretora em MODO OBSERVACAO nao e recuperavel — e a
    excecao pode acontecer ANTES de o portao ser consultado.
    """
    fonte = (RAIZ / "app/api/webhook.py").read_text(encoding="utf-8")
    checar("_pode_falar_ao_cliente = False" in fonte,
           "a autorizacao de fala comeca FALSA — o padrao e calar")
    # E so vira True DEPOIS do portao de silencio.
    i_portao = fonte.index("if _em_silencio:")
    i_libera = fonte.index("_pode_falar_ao_cliente = True")
    checar(i_libera > i_portao,
           "e so vira True DEPOIS do portao de observacao",
           "senao o fallback falaria por quem mandou calar")
    i_gate_def = fonte.index("_em_silencio = not await attendance_agent_active")
    checar(i_libera > i_gate_def,
           "e depois da propria consulta ao portao, nao antes")


def o_fallback_nao_promete_o_que_nao_vai_acontecer() -> None:
    """Honestidade: o texto so pode afirmar o que e verdade."""
    corpo = _corpo_do_except()
    texto = re.search(r'text=\((.*?)\),\s*\n\s*integration=', corpo, re.DOTALL)
    checar(texto is not None, "o texto do fallback esta legivel no fonte")
    msg = (texto.group(1) if texto else "").lower()

    checar("falha t" in msg, "diz o que e VERDADE: deu erro aqui", msg[:90])
    for promessa, porque in (
        ("atendente", "ninguem foi acionado — nenhum humano sabe desta conversa"),
        ("registr", "a gravacao pode ter sido justamente o que falhou"),
        ("minuto", "prazo inventado e a mentira mais facil de contar"),
        ("em breve", "prazo vago tambem e prazo"),
        ("assim que poss", "promessa sem dono"),
    ):
        checar(promessa not in msg, f"e NAO promete: {promessa!r} ({porque})", msg[:90])
    checar("envi" in msg or "manda" in msg,
           "mas diz o que a pessoa pode fazer AGORA", msg[:90])


def o_fallback_nao_duplica_resposta_boa() -> None:
    """Excecao DEPOIS do envio (metrica, preview) nao vira segundo balao."""
    fonte = (RAIZ / "app/api/webhook.py").read_text(encoding="utf-8")
    i_envio = fonte.index("_resposta_ja_enviada = True")
    i_success = fonte.index("if success:")
    checar(i_envio > i_success,
           "a marca de 'ja respondeu' vem do SUCESSO do envio, nao da tentativa",
           "marcar antes esconderia justamente a falha de envio")
    checar("not _resposta_ja_enviada" in _corpo_do_except(),
           "e o fallback so dispara se a resposta NAO saiu")


# ==================================================================== #
# 2.4 — HUMAN_REQUESTED deixa de ser estado sem saída
# ==================================================================== #

def a_varredura_de_handoff_existe_e_esta_agendada() -> None:
    vig = (RAIZ / "app/tasks/handoff_watchdog.py").read_text(encoding="utf-8")
    bp = (RAIZ / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")

    checar("async def varrer_handoffs_parados" in vig, "a varredura existe")
    checar('.eq("status", "HUMAN_REQUESTED")' in vig,
           "e ela OLHA `conversations.status` — o que nenhum job fazia",
           "era essa a causa das ~730 horas")
    checar('.lt("last_message_at"' in vig,
           "so pega conversa PARADA, nao a que acabou de pedir humano")
    checar("varrer_handoffs_parados" in bp and "handoff_watchdog_check" in bp,
           "e ela esta registrada no agendador que ja existe",
           "funcao que ninguem chama e o mesmo silencio com outro nome")
    registro = bp[bp.index("handoff_watchdog_check"):bp.index("scheduler.start()")]
    checar("next_run_time" in registro,
           "com primeira passada logo apos o boot — quem ja esperava continua esperando")


def o_agendador_nao_cai_por_causa_deste_job() -> None:
    """CLAUDE.md §9.1 — build verde nao prova que a aplicacao sobe.

    `main.py` chama `start_buffer_scheduler()` SEM `try`. A ferramenta de
    handoff mora em `app/agents/tools/` e arrasta `app.agents.__init__` →
    `graph.py` → `langgraph`. Importa-la no registro do job faria um
    ImportError derrubar a aplicacao inteira — buffer de mensagens, vigias,
    tudo — e nao so este vigia.
    """
    main = (RAIZ / "app/main.py").read_text(encoding="utf-8")
    bp = (RAIZ / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    vig = (RAIZ / "app/tasks/handoff_watchdog.py").read_text(encoding="utf-8")

    checar("start_buffer_scheduler()" in main,
           "o agendador e iniciado no startup da aplicacao")
    checar("from app.tasks.handoff_watchdog import" in bp
           and "from app.agents" not in bp,
           "o agendador importa o modulo LEVE, nunca `app.agents`",
           "e por isso que a varredura nao mora em human_handoff.py")

    # E o import pesado esta DENTRO de uma funcao, nunca em nivel de MODULO.
    #
    # 🔴 ATUALIZADO EM 19/08/2026. Antes recortava tudo ANTES de
    # `varrer_handoffs_parados` e exigia que `from app.agents` nao aparecesse
    # ali. O recorte mudou de sentido quando o vigia ganhou tres funcoes
    # auxiliares (`_env_int`, `_ja_avisado_recentemente`, `_devolver_a_vez`)
    # que ficam ANTES da varredura e importam de `app.agents` — cada uma
    # DENTRO do proprio corpo, que e exatamente o que a licao pede.
    #
    # A licao nao mudou: nada de `app.agents` em nivel de modulo, porque
    # `start_buffer_scheduler()` e chamado sem `try` no startup e um
    # ImportError ali derruba a aplicacao inteira (CLAUDE.md §9.1). O que
    # mudou foi COMO se verifica — agora por indentacao, que e o que
    # "nivel de modulo" quer dizer de verdade.
    linhas_de_modulo = [ln for ln in vig.splitlines()
                        if ln.startswith("from ") or ln.startswith("import ")]
    checar(not any("app.agents" in ln for ln in linhas_de_modulo),
           "e o modulo do vigia nao importa `app.agents` em nivel de MODULO",
           f"importes de topo: {[ln for ln in linhas_de_modulo if 'app.' in ln]}")
    checar(any("app.agents" in ln for ln in vig.splitlines()
               if ln.startswith("    ") and ln.strip().startswith("from ")),
           "CONTROLE: e ele IMPORTA de app.agents, so que dentro das funcoes",
           "sem isto, um vigia que nao importasse nada passaria na linha acima")
    corpo = vig[vig.index("async def varrer_handoffs_parados"):]
    checar("from app.agents.tools.human_handoff import HumanHandoffTool" in corpo,
           "o import pesado acontece POR EXECUCAO, dentro da funcao")
    i_imp = corpo.index("from app.agents.tools.human_handoff")
    checar("try:" in corpo[max(0, i_imp - 120):i_imp],
           "e sob `try` — indisponivel vira log, nao excecao no agendador")


def a_varredura_reusa_o_que_existe() -> None:
    """'Nao invente escalonamento novo.' O destino e o dossie ja existiam."""
    vig = (RAIZ / "app/tasks/handoff_watchdog.py").read_text(encoding="utf-8")
    hh = (RAIZ / "app/agents/tools/human_handoff.py").read_text(encoding="utf-8")
    checar("_avisar_suporte" in vig,
           "reusa `_avisar_suporte` — que resolve destino e monta o dossie")
    checar("resolver_destino_de_suporte" in hh,
           "e o destino sai do resolvedor canonico, que recusa destino compartilhado",
           "o dossie leva CPF do segurado (CLAUDE.md §7)")
    # Nenhum caminho de envio proprio: se a varredura montasse o WhatsApp na
    # mao, o conserto teria criado um segundo escalonamento em paralelo.
    checar("get_whatsapp_service" not in vig,
           "e NAO monta envio proprio em paralelo ao que ja existe")
    checar("_montar_dossie" not in vig,
           "nem monta dossie proprio — o texto e o que a ferramenta ja escreve")


def a_varredura_nao_vira_metralhadora() -> None:
    """Alerta que chega demais e alerta que se aprende a ignorar — que e
    exatamente como este estado ficou 730 horas sem ninguem olhar."""
    vig = (RAIZ / "app/tasks/handoff_watchdog.py").read_text(encoding="utf-8")
    checar("_ja_avisado_recentemente" in vig, "ha marcador de re-alerta")

    # 🔴 O MARCADOR MUDOU DE CASA EM 19/08/2026 — e a licao veio junto.
    #
    # Ele morava aqui. 📊 Naquele dia descobriu-se que a `HumanHandoffTool`,
    # consertada em 18/08, passou a avisar o grupo em TODA chamada — entao os
    # avisadores da mesma conversa viraram DOIS. Duas copias do marcador
    # seriam duas chaves diferentes no Redis, cada uma silenciando so a si
    # mesma, e o grupo receberia o dobro: o defeito que o marcador existe para
    # resolver, agora em dose dupla.
    #
    # Uma definicao, dois donos. Ela vive em `human_handoff.py` e o vigia
    # delega. As tres exigencias abaixo continuam iguais; mudou o arquivo onde
    # se confere — e conferir no arquivo errado seria dar verde a um marcador
    # que nao existe mais.
    marc = (RAIZ / "app/agents/tools/human_handoff.py").read_text(encoding="utf-8")
    checar("reivindicar_o_aviso" in vig,
           "e o vigia usa o marcador COMPARTILHADO, nao uma copia dele",
           "copia e onde o conserto de um lado deixa o outro quebrado")
    checar("nx=True" in marc,
           "gravado com `nx` — teste-e-marca atomico, sem aviso em dobro",
           "dois workers na mesma passada avisariam duas vezes")
    checar("* 3600" in marc, "e com TTL: o lembrete VOLTA, nao morre")
    checar("nx=True" not in vig,
           "CONTROLE: e o marcador NAO existe mais em duas casas",
           "se as duas tivessem `nx=True`, seriam duas chaves e dois avisos")

    # E o fail-open: Redis fora do ar tem de AVISAR, nao calar.
    # 🔴 O RECORTE VAI ATE A PROXIMA FUNCAO, QUALQUER QUE ELA SEJA.
    #
    # Antes ia ate `devolver_a_vez` pelo nome. Em 21/08 nasceu
    # `contar_lembrete` ENTRE as duas, e a fatia passou a conter duas funcoes:
    # o `except` que o teste inspecionava virou o da funcao errada (que
    # devolve 0, nao False) e o guarda ficou vermelho sem nenhum defeito real.
    #
    # Ancorar num vizinho e ancorar em algo que nao e o alvo. Agora o corte e
    # estrutural: acaba onde a funcao acaba.
    import re as _re
    i = marc.index("async def reivindicar_o_aviso")
    _prox = _re.search(r"\n(?:async )?def ", marc[i + 10:])
    corpo = marc[i:i + 10 + _prox.start()] if _prox else marc[i:]
    checar("return False" in corpo.split("except")[-1],
           "Redis indisponivel => avisa de novo (o defeito e o silencio)",
           "fail-closed aqui reproduziria exatamente o bug que se esta consertando")


def a_telemetria_mede_quem_espera() -> None:
    sli = (RAIZ / "app/services/observability/sli.py").read_text(encoding="utf-8")
    vig = (RAIZ / "app/tasks/handoff_watchdog.py").read_text(encoding="utf-8")
    checar("HANDOFF_ESPERA" in sli, "o SLI da espera humana tem nome canonico")
    trecho = vig[vig.index("async def varrer_handoffs_parados"):]
    checar("HANDOFF_ESPERA" in trecho, "e a varredura o registra")
    # A telemetria vem ANTES do marcador: senao o numero sumiria justamente
    # quando a fila estivesse pior.
    checar(trecho.index("HANDOFF_ESPERA") < trecho.index("_ja_avisado_recentemente("),
           "e mede TODA conversa parada, nao so as que geram aviso",
           "medir so o que alerta faz o grafico melhorar quanto mais gente esperar")


# ==================================================================== #
# 2.5 — a BR-101 chega inteira
# ==================================================================== #

def a_br101_chega_inteira() -> None:
    """O caso medido, exatamente como foi medido."""
    r = PB.parse_address_br("Rodovia BR-101, km 150, Palhoça - SC")
    checar(r.get("numero") is None,
           f"o numero da RODOVIA nao vira numero de casa (numero={r.get('numero')!r})",
           "era 101 — o endereco de uma casa que existe em outra rua")
    checar(r.get("bairro") is None,
           f"e o quilometro nao vira bairro (bairro={r.get('bairro')!r})",
           "era 'km 150'")
    checar("BR-101" in (r.get("rua") or ""),
           f"a rodovia chega INTEIRA em `rua`: {r.get('rua')!r}",
           "era 'Rodovia BR' — partida no hifen de BR-101")
    checar("km 150" in (r.get("rua") or ""),
           "e o quilometro nao se perde — e a unica coisa que diz ONDE na BR-101",
           f"rua={r.get('rua')!r}")
    checar(r.get("cidade") == "Palhoça" and r.get("uf") == "SC",
           f"cidade e UF continuam sendo deduzidas: {r.get('cidade')!r}/{r.get('uf')!r}")


def a_classe_da_rodovia_fecha() -> None:
    """Nao era so a BR: `SC-401` quebrava igual, e `km` virava bairro ate em
    rodovia de nome proprio."""
    casos = [
        ("BR-101, km 210, sentido norte, Biguaçu - SC", "BR-101", "Biguaçu"),
        ("Rodovia SC-401, km 5, Florianopolis - SC", "SC-401", "Florianopolis"),
        ("br 101 km 88, Tijucas SC", "101", "Tijucas"),
        ("Rod. Anhanguera, km 90, Campinas - SP", "Anhanguera", "Campinas"),
        ("Estrada RS-118, km 12, Gravatai - RS", "RS-118", "Gravatai"),
    ]
    for texto, na_rua, cidade in casos:
        r = PB.parse_address_br(texto)
        checar("numero" not in r and "bairro" not in r,
               f"sem numero/bairro inventado: {texto[:38]}…", str(r))
        checar(na_rua in (r.get("rua") or ""),
               f"e a via chega inteira ({na_rua})", str(r))
        checar(r.get("cidade") == cidade,
               f"e a cidade e {cidade!r}", str(r))


def o_endereco_urbano_nao_regride() -> None:
    """O controle. Um parser que devolvesse `{}` para tudo passaria acima."""
    p1 = PB.parse_address_br("R. Abelardo Luz, 342 - Balneario, Florianopolis - SC, 88075-542")
    checar(p1.get("rua") == "R. Abelardo Luz" and p1.get("numero") == "342",
           "rua e numero urbanos intactos", str(p1))
    checar(p1.get("bairro") == "Balneario" and p1.get("cidade") == "Florianopolis",
           "bairro e cidade urbanos intactos", str(p1))
    checar(p1.get("cep") == "88075-542", "e o CEP", str(p1))

    p2 = PB.parse_address_br("Av Santa Tecla 2400, Bage, RS")
    checar(p2.get("numero") == "2400" and p2.get("rua") == "Av Santa Tecla",
           "numero grudado na rua continua sendo lido", str(p2))

    p3 = PB.parse_address_br("Oficina Central, Rua B, 50, Sao Jose SC")
    checar(p3.get("rua") == "Rua B" and p3.get("numero") == "50",
           "rua no meio do texto continua sendo achada", str(p3))

    checar(PB.parse_address_br("") == {}, "e vazio continua vazio")


def o_apartamento_302_nao_e_o_amapa() -> None:
    """O falso positivo que a regra ingenua criaria.

    `AP` e o codigo do Amapa E a abreviacao de apartamento. Uma regra unica
    `<UF>[-\\s]?\\d{2,3}` leria "AP 302" como rodovia e devolveria um endereco
    SEM numero — trocando um erro por outro.
    """
    for texto in ("Rua das Flores, 100, AP 302, Centro, Sao Paulo - SP",
                  "Rua das Flores, 100, AP-302, Centro, Sao Paulo - SP"):
        r = PB.parse_address_br(texto)
        checar(r.get("numero") == "100",
               f"apartamento nao vira rodovia: numero={r.get('numero')!r}", str(r))
        checar(r.get("rua") == "Rua das Flores",
               f"e a rua continua sendo a rua: {r.get('rua')!r}", str(r))

    # E o codigo estadual COM apoio de rodovia continua sendo rodovia.
    r = PB.parse_address_br("Rodovia SC-401, km 5, Florianopolis - SC")
    checar("numero" not in r, "mas SC-401 com 'Rodovia'/'km' continua sendo rodovia", str(r))


def o_guarda_tem_como_falhar() -> None:
    """Um `_e_rodovia` que devolvesse True para tudo mandaria todo endereco
    urbano para o caminho sem numero — e passaria nos checks de rodovia."""
    urbanos = ["Rua B, 50, Sao Jose SC", "Av Santa Tecla 2400, Bage, RS",
               "Rua das Flores, 100, AP 302, Centro"]
    casou = [t for t in urbanos if PB._e_rodovia(t)]
    checar(not casou, "`_e_rodovia` RECUSA endereco urbano", f"casou: {casou}")

    rodovias = ["Rodovia BR-101, km 150", "BR 116", "Rod. Anhanguera, km 90",
                "Estrada SC-401, km 5"]
    recusou = [t for t in rodovias if not PB._e_rodovia(t)]
    checar(not recusou, "e ACEITA rodovia de verdade", f"recusou: {recusou}")


def main() -> int:
    print(__doc__)
    print("== 2.3 a excecao nao emudece mais ==")
    a_excecao_nao_emudece_mais()
    print("== e o fallback respeita o portao de silencio ==")
    o_fallback_respeita_o_portao_de_silencio()
    print("== e nao promete o que nao vai acontecer ==")
    o_fallback_nao_promete_o_que_nao_vai_acontecer()
    print("== e nao duplica resposta boa ==")
    o_fallback_nao_duplica_resposta_boa()
    print("== 2.4 a varredura de handoff existe e esta agendada ==")
    a_varredura_de_handoff_existe_e_esta_agendada()
    print("== e o agendador NAO cai por causa dela ==")
    o_agendador_nao_cai_por_causa_deste_job()
    print("== e reusa o que existe ==")
    a_varredura_reusa_o_que_existe()
    print("== e nao vira metralhadora ==")
    a_varredura_nao_vira_metralhadora()
    print("== e a telemetria mede quem espera ==")
    a_telemetria_mede_quem_espera()
    print("== 2.5 a BR-101 chega inteira ==")
    a_br101_chega_inteira()
    print("== e a classe da rodovia fecha ==")
    a_classe_da_rodovia_fecha()
    print("== o endereco urbano nao regride ==")
    o_endereco_urbano_nao_regride()
    print("== o apartamento 302 nao e o Amapa ==")
    o_apartamento_302_nao_e_o_amapa()
    print("== o guarda tem como falhar ==")
    o_guarda_tem_como_falhar()

    print()
    if _falhas:
        print(f"VERMELHO — {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("O SEGURADO NAO FICA NO ESCURO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
