"""O agente responde a TELA, nao a ultima bolha dela.

Rodar: python backend/tests/test_o_agente_responde_a_tela_inteira.py

A HISTORIA
----------
A URA nao manda uma mensagem: manda uma RAJADA. O aviso vem numa bolha, o menu
na seguinte, a pergunta na terceira. Quem le no celular ve UMA tela, e e sobre a
tela inteira que decide o que responder.

O buffer do webhook ja juntava a rajada. E o laco logo abaixo dele a DESJUNTAVA,
chamando o motor uma vez por bolha.

  medido em 05/08/2026, sobre o trafego real das seguradoras
  34,1% dos turnos chegam com 2+ mensagens
  nesses turnos, a pergunta esta na ULTIMA em 68,1% das vezes

Ou seja: em 2 de cada 3 turnos com rajada o modelo respondia a PRIMEIRA bolha —
quase sempre um "aguarde" — e ja tinha falado quando o menu de verdade chegou.
Duas respostas para uma pergunta so, e a primeira sobre a tela errada.

O CONSERTO QUE **NAO** SERVIA
-----------------------------
Juntar tudo num texto so e mandar para o motor. O caminho deterministico
precisa ver cada mensagem em ordem: o menu pode estar na PRIMEIRA e o "aguarde"
na ultima. Colar as duas faria as ancoras casarem com o texto errado.

O conserto e separar os dois TEMPOS: cada mensagem passa pelo deterministico em
ordem (`ainda_vem_mais=True` apenas acumula), e a ULTIMA do turno abre a
deliberacao — uma chamada ao modelo, sobre a tela completa.

A LINHA DE CONTROLE (CLAUDE.md 9.2)
-----------------------------------
"Responder a tela inteira" e "responder a ultima mensagem" acertam o mesmo caso
em 68,1% das vezes. Sao coisas diferentes, e um teste que so olhasse o caso
comum aprovaria as duas.

Por isso o bloco 2 inverte a rajada: a pergunta vai para a PRIMEIRA bolha. Se a
implementacao fosse "usa a ultima", esse bloco falharia. E o bloco 3 prova que o
silencio e o nao-silencio CONSEGUEM ser diferentes na mesma estrutura de rajada
— muda so se a tela pede alguma coisa.
"""

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FAILURES = []


def checar(nome, condicao, detalhe=None):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print(f"  [ok] {nome}")
    else:
        FAIL += 1
        FAILURES.append((nome, detalhe))
        print(f"  [X] {nome}{': ' + str(detalhe) if detalhe else ''}")


def _load(dotted, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


for _nome in ("app", "app.services"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []

pb = _load("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
dispatch = _load("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")
router = _load("app.services.dispatch_router", "app/services/dispatch_router.py")

SLOTS = {
    "titular_cpf": "11122233344", "titular_nome": "Fulano de Tal",
    "veiculo_placa": "ABC1D23", "local_atual": "Rua A, 1, Centro, Cidade SC",
    "local_destino": "Rua B, 2, Bairro, Cidade SC", "problema_descricao": "pane",
    "telefone_contato": "48999990000", "pessoa_no_local": "Fulano",
}

# Telas que NAO caem no caminho deterministico de proposito: se caissem, a
# resposta sairia antes de o modelo ser chamado e o teste mediria outra coisa.
AVISO = "Um momento, estou localizando seu cadastro."
AGUARDE = "Aguarde um instante, por favor."
VERIFICANDO = "Estamos verificando as informacoes."
PERGUNTA = "Qual o melhor horario para o nosso retorno?"


def _sessao_em_fase_humana(company_id, telefone, caso):
    s = dispatch.new_dispatch_session(
        case_id=caso, company_id=company_id, playbook_ref="yelum-auto-whatsapp@v3",
        subservice="guincho", slots=dict(SLOTS),
    )
    s["state"] = "human_phase"
    s["client_phone"] = "5547988087463"
    asyncio.run(router.save_active_dispatch(company_id, telefone, s))
    return s


def _rajada(company_id, telefone, mensagens, resposta_do_modelo):
    """Roda a rajada EXATAMENTE como o webhook roda: uma chamada por mensagem,
    `ainda_vem_mais` verdadeiro em todas menos na ultima.

    Devolve (o que o modelo VIU, o que foi enviado a seguradora, a sessao)."""
    vistas, enviadas = [], []

    async def provider(_sessao, texto):
        vistas.append(texto)
        return resposta_do_modelo

    async def rodar():
        for i, msg in enumerate(mensagens):
            await router.try_route_insurer_inbound(
                company_id=company_id, from_phone=telefone, text=msg,
                send_to_insurer=enviadas.append, send_to_client=lambda p, t: None,
                human_reply_provider=provider,
                ainda_vem_mais=(i < len(mensagens) - 1),
            )
        return await router.load_active_dispatch(company_id, telefone)

    sessao = asyncio.run(rodar())
    return vistas, enviadas, sessao


def rodar():
    print("== O agente responde a TELA inteira, nao a ultima bolha ==\n")

    # ---------------------------------------------------------------- bloco 1
    print("-- 1. uma rajada, UMA deliberacao, sobre a tela completa --")
    _sessao_em_fase_humana("coT1", "551130001111", "t1")
    vistas, _env, _s = _rajada("coT1", "551130001111", [AVISO, PERGUNTA], "Pode ser as 15h.")
    checar("o modelo foi chamado UMA vez (antes: uma por bolha)", len(vistas) == 1, len(vistas))
    tela = vistas[0] if vistas else ""
    checar("a tela levou a PRIMEIRA bolha (o aviso)", "localizando seu cadastro" in tela, tela[:120])
    checar("a tela levou a ULTIMA bolha (a pergunta)", "melhor horario" in tela, tela[:120])
    # `and` curto-circuita de proposito: sem isso, um `.index()` de algo ausente
    # levanta ValueError e o teste MORRE em vez de REPROVAR — e uma bateria que
    # morre no meio esconde as checagens seguintes.
    checar("a tela e UM texto so, na ordem em que chegou",
           "localizando" in tela and "melhor horario" in tela
           and tela.index("localizando") < tela.index("melhor horario"), tela[:160])

    # ---------------------------------------------------------------- bloco 2
    #
    # A LINHA DE CONTROLE. Mesma rajada, ordem invertida: a pergunta vem
    # PRIMEIRO. "Responder a tela" e "responder a ultima mensagem" acertam o
    # bloco 1 do mesmo jeito — e so aqui se separam. Sem este bloco, uma
    # implementacao que pegasse so a ultima bolha passaria no teste inteiro.
    print("\n-- 2. CONTROLE: a pergunta na PRIMEIRA bolha --")
    _sessao_em_fase_humana("coT2", "551130002222", "t2")
    vistas2, _env2, _s2 = _rajada("coT2", "551130002222", [PERGUNTA, AGUARDE], "Pode ser as 15h.")
    checar("continua UMA deliberacao", len(vistas2) == 1, len(vistas2))
    tela2 = vistas2[0] if vistas2 else ""
    checar("a pergunta chegou ao modelo mesmo estando no COMECO",
           "melhor horario" in tela2, tela2[:120])
    checar("e o filler do fim veio junto", "Aguarde um instante" in tela2, tela2[:120])

    # ---------------------------------------------------------------- bloco 3
    #
    # O guarda tem de julgar a MESMA tela que o modelo leu. Se ele recebesse so
    # a ultima bolha, um "aguarde" solto passaria por tela-que-nao-pede-nada e o
    # silencio seria aprovado com a pergunta duas linhas acima.
    #
    # Os dois casos abaixo tem a MESMA forma: duas bolhas, a ultima sem pergunta,
    # e o modelo propondo SEM_RESPOSTA. Muda so se a tela pede alguma coisa —
    # e e por isso que este par tem direito a concluir.
    print("\n-- 3. o guarda le a mesma tela (silencio nao escapa pela ultima bolha) --")
    _sessao_em_fase_humana("coT3", "551130003333", "t3")
    _v3, env3, s3 = _rajada("coT3", "551130003333", [PERGUNTA, AGUARDE], "SEM_RESPOSTA")
    checar("tela que PEDE algo: o silencio foi RECUSADO",
           not (s3 or {}).get("silencio_deliberado_ate"), (s3 or {}).get("silencio_deliberado_ate"))
    checar("tela que PEDE algo: contou como recusa do modelo",
           int((s3 or {}).get("human_phase_guard_fails") or 0) == 1,
           (s3 or {}).get("human_phase_guard_fails"))
    checar("tela que PEDE algo: nada foi enviado as cegas", not env3, env3)

    _sessao_em_fase_humana("coT4", "551130004444", "t4")
    _v4, env4, s4 = _rajada("coT4", "551130004444", [VERIFICANDO, AGUARDE], "SEM_RESPOSTA")
    checar("CONTROLE — tela que NAO pede nada: o silencio foi ACEITO",
           bool((s4 or {}).get("silencio_deliberado_ate")), (s4 or {}).get("silencio_deliberado_ate"))
    checar("CONTROLE — o silencio nao gastou chance",
           int((s4 or {}).get("human_phase_guard_fails") or 0) == 0,
           (s4 or {}).get("human_phase_guard_fails"))
    checar("CONTROLE — a rajada inteira contou como UM silencio, nao dois",
           int((s4 or {}).get("silencios_seguidos") or 0) == 1,
           (s4 or {}).get("silencios_seguidos"))

    # ---------------------------------------------------------------- bloco 4
    #
    # O QUE NAO PODE TER QUEBRADO. O deterministico continua vendo cada mensagem
    # em ordem — e a prova e que as DUAS bolhas foram acumuladas por ele.
    print("\n-- 4. o deterministico continua vendo cada bolha, em ordem --")
    entradas = [t.get("text") for t in (s4 or {}).get("transcript") or []
                if t.get("direction") == "in"]
    checar("as duas bolhas passaram pelo motor", len(entradas) == 2, entradas)
    checar("na ordem em que chegaram",
           entradas[:2] == [VERIFICANDO, AGUARDE], entradas[:2])
    pendentes = (s4 or {}).get("pending_insurer_messages") or []
    checar("e as duas ficaram pendentes (o silencio nao apaga a tela)",
           len(pendentes) == 2, pendentes)

    # ---------------------------------------------------------------- bloco 5
    print("\n-- 5. mensagem unica: o caminho de sempre nao mudou --")
    _sessao_em_fase_humana("coT5", "551130005555", "t5")
    vistas5, _e5, _s5 = _rajada("coT5", "551130005555", [PERGUNTA], "Pode ser as 15h.")
    checar("uma mensagem -> uma deliberacao", len(vistas5) == 1, len(vistas5))
    checar("e o modelo viu exatamente ela", (vistas5[0] if vistas5 else "") == PERGUNTA,
           vistas5[:1])

    # ---------------------------------------------------------------- bloco 6
    #
    # O corte por teto. Corta pela CABECA, porque a pergunta mora no fim — e
    # corta por mensagens INTEIRAS, para nao entregar meia frase ao modelo.
    print("\n-- 6. tela gigante: corta pela cabeca, nunca pelo fim --")
    grandes = [f"{i}-" + ("x" * 1200) for i in range(6)]
    tela6 = router._tela_do_turno({"pending_insurer_messages": grandes}, "")
    checar("respeitou o teto", len(tela6) <= router._TETO_DA_TELA, len(tela6))
    checar("a ULTIMA mensagem sobreviveu inteira", grandes[-1] in tela6, tela6[:40])
    checar("a PRIMEIRA foi a que saiu", not tela6.startswith("0-"), tela6[:40])
    checar("sem pendencia, cai no texto que chegou",
           router._tela_do_turno({}, "so isso") == "so isso")

    # ESTES TRES NASCERAM DE UM FURO. A checagem acima nao distinguia cortar
    # pela cabeca de cortar pelo fim: descartando mensagens INTEIRAS o texto ja
    # cabia, e o fatiamento final virava no-op. Trocar `[-N:]` por `[:N]` passava
    # verde — o guarda existia e nao guardava nada.
    #
    # So uma mensagem que sozinha estoura o teto exercita o corte, e ai a
    # direcao importa: a pergunta mora no FIM.
    unica = "COMECO DESCARTAVEL " + ("y" * 5000) + " PERGUNTA NO FIM"
    tela6b = router._tela_do_turno({"pending_insurer_messages": [unica]}, "")
    checar("bolha unica gigante: respeitou o teto",
           len(tela6b) <= router._TETO_DA_TELA, len(tela6b))
    checar("bolha unica gigante: guardou o FIM (onde mora a pergunta)",
           tela6b.endswith("PERGUNTA NO FIM"), tela6b[-30:])
    checar("bolha unica gigante: a cabeca foi a que saiu",
           not tela6b.startswith("COMECO"), tela6b[:25])

    # ---------------------------------------------------------------- bloco 7
    #
    # UMA RESPOSTA POR TURNO. O passo mapeado responde sozinho o que sabe
    # responder. Quando ele respondia, o modelo era chamado logo em seguida
    # sobre o que tivesse sobrado de pendente — e saiam DUAS mensagens nossas
    # para uma pergunta da URA.
    #
    # O par abaixo tem a MESMA rajada; muda so a ultima bolha: uma o
    # deterministico sabe responder, a outra nao. E so isso que decide.
    print("\n-- 7. uma resposta por turno (o deterministico ja falou) --")
    _sessao_em_fase_humana("coT7", "551130007777", "t7")
    v7, env7, s7 = _rajada("coT7", "551130007777",
                           [AGUARDE, "Qual o CPF do titular?"], "nunca deveria sair")
    checar("o deterministico respondeu o CPF", any("11122233344" in e for e in env7), env7)
    checar("o modelo NAO foi chamado por cima", len(v7) == 0, v7)
    checar("uma mensagem so foi as seguradora", len(env7) == 1, env7)
    checar("e o pendente nao se perdeu (vai para a tela do proximo turno)",
           AGUARDE in ((s7 or {}).get("pending_insurer_messages") or []),
           (s7 or {}).get("pending_insurer_messages"))

    _sessao_em_fase_humana("coT8", "551130008888", "t8")
    v8, env8, _s8 = _rajada("coT8", "551130008888", [AGUARDE, PERGUNTA], "Pode ser as 15h.")
    checar("CONTROLE — ultima bolha que o deterministico NAO sabe: o modelo entra",
           len(v8) == 1, v8)
    checar("CONTROLE — e a resposta dele saiu", any("15h" in e for e in env8), env8)

    # ---------------------------------------------------------------- bloco 8
    #
    # A FIACAO. O conserto so existe se o webhook de fato marcar as bolhas do
    # meio. Sem esta checagem, alguem removeria o argumento e todos os blocos
    # acima continuariam verdes — eles chamam o roteador direto.
    print("\n-- 8. o webhook realmente marca as bolhas do meio --")
    fonte = (ROOT / "app" / "api" / "webhook.py").read_text(encoding="utf-8")
    checar("webhook.py passa ainda_vem_mais para o roteador",
           "ainda_vem_mais=(_i < len(_rajada) - 1)" in fonte)
    checar("e continua chamando o roteador uma vez por mensagem",
           "for _i, _msg in enumerate(_rajada)" in fonte)

    # ---------------------------------------------------------------- bloco 9
    #
    # A COSTURA COM O GUARDA DA CONFIRMACAO — a emenda que nenhum dos dois
    # testes cobria sozinho.
    #
    # O guarda le o resumo numa JANELA das ultimas 3 mensagens da seguradora,
    # justamente porque a URA parte o resumo em bolhas. Aqui a ancora de
    # finalizacao ("Podemos confirmar?") casa so na SEGUNDA bolha, e o endereco
    # veio na PRIMEIRA. Se a janela nao atravessasse a rajada, o guarda leria
    # uma tela sem dado nenhum, aprovaria por `resumo_nao_lido` — e o "1" sairia
    # com o endereco errado dentro. Que e exatamente o acidente que ele existe
    # para impedir.
    print("\n-- 9. resumo PARTIDO na rajada: a conferencia atravessa as bolhas --")
    CERTO = "Rua Doutor Fulvio Aducci, 1235 - Estreito - Florianopolis - SC"
    ERRADO = "Rua Doutor Fulvio Aducci, 1253 - Estreito - Florianopolis - SC"
    DESTINO = "Rua Sao Jose, 90 - Centro - Sao Jose - SC"
    SLOTS_ALLIANZ = {
        "titular_cpf": "11122233344", "titular_nome": "Joao da Silva",
        "veiculo_placa": "JCL9A59", "veiculo_descricao": "Toyota Hilux SW4 2019",
        "local_atual": CERTO, "local_destino": DESTINO,
        "problema_descricao": "nao liga", "quando": "agora",
        "telefone_contato": "48991072089", "servico_opcao": "3",
    }
    FECHO = ("Podemos confirmar o atendimento?\n*1 -* Sim\n"
             "*2 -* Nao, desejo reiniciar\n*0 -* Sair")

    def _rajada_da_ura(origem):
        """O resumo em DUAS bolhas: os dados numa, a pergunta final na outra."""
        corpo = ("*RESUMO DA SOLICITACAO*\n*Placa:* JC#-###9\n*Veiculo:* HILUX SW4\n"
                 "*Servico:* reboque para pane mecanica\n"
                 f"*Origem:* {origem}\n*Destino:* {DESTINO}")
        s = dispatch.new_dispatch_session(
            case_id="costura", company_id="coC", playbook_ref="allianz-auto-whatsapp@v1",
            subservice="guincho", slots=dict(SLOTS_ALLIANZ))
        s = dispatch.start_dispatch(s)
        for bolha in (corpo, FECHO):
            s = dispatch.handle_insurer_message(s, bolha)
        saidas = [t.get("text") for t in (s.get("transcript") or [])
                  if t.get("direction") == "out" and t.get("step") is not None]
        return saidas, s

    saidas_err, s_err = _rajada_da_ura(ERRADO)
    checar("endereco errado na 1a bolha: o motor NAO responde '1'",
           "1" not in saidas_err, saidas_err)
    checar("endereco errado na 1a bolha: ele corrige com o dado DO CASO",
           any("1235" in str(x) for x in saidas_err), saidas_err)
    checar("e a conferencia registrou a divergencia de ORIGEM",
           any("origem" in str(d).lower()
               for d in ((s_err or {}).get("conferencia") or {}).get("divergencias") or []),
           ((s_err or {}).get("conferencia") or {}).get("divergencias"))

    # CONTROLE: a MESMA rajada partida, com o endereco certo. Sem esta linha, um
    # guarda que reprovasse todo resumo partido passaria nas tres acima.
    saidas_ok, s_ok = _rajada_da_ura(CERTO)
    checar("CONTROLE — endereco certo na 1a bolha: o motor confirma ('1')",
           "1" in saidas_ok, saidas_ok)
    checar("CONTROLE — e a conferencia APROVOU",
           bool(((s_ok or {}).get("conferencia") or {}).get("ok")),
           (s_ok or {}).get("conferencia"))
    checar("CONTROLE — conferiu a origem de fato (nao aprovou no vazio)",
           any("origem" in str(c).lower()
               for c in ((s_ok or {}).get("conferencia") or {}).get("conferidos") or []),
           ((s_ok or {}).get("conferencia") or {}).get("conferidos"))

    # --------------------------------------------------------------- bloco 10
    #
    # O ROTULO NAO PODE MENTIR. O prompt lista as pendencias sob o titulo
    # "Mensagens ANTERIORES da seguradora ainda sem resposta". Agora que a tela
    # atual E montada a partir dessa mesma lista, repeti-la ali fazia o modelo
    # ler a pergunta de AGORA como pergunta velha — e ja repetida, que e o jeito
    # mais rapido de ele achar que ja respondeu.
    print("\n-- 10. o prompt nao chama a tela de agora de 'mensagem anterior' --")
    base = dispatch.new_dispatch_session(case_id="p1", company_id="coP",
                                         playbook_ref="yelum-auto-whatsapp@v3",
                                         subservice="guincho", slots=dict(SLOTS))
    base["pending_insurer_messages"] = [AVISO, PERGUNTA]

    montado = dispatch.build_human_phase_messages(base, AVISO + "\n" + PERGUNTA)
    checar("tela montada: nada aparece como 'anterior'",
           "Mensagens anteriores" not in montado["user"],
           montado["user"][-400:])
    checar("tela montada: a pergunta esta la, uma vez so",
           montado["user"].count(PERGUNTA) == 1, montado["user"].count(PERGUNTA))
    checar("e o rotulo diz TELA, avisando que pode ter vindo em partes",
           "Tela da seguradora agora" in montado["user"])

    # CONTROLE: quem NAO deliberou sobre o pendente ainda precisa ve-lo. Sem
    # esta linha, apagar o bloco inteiro passaria nas tres checagens acima.
    sobrou = dispatch.build_human_phase_messages(base, PERGUNTA)
    checar("CONTROLE — o que ficou de FORA da tela continua listado",
           "Mensagens anteriores" in sobrou["user"] and AVISO in sobrou["user"],
           sobrou["user"][-400:])

    print(f"\n{'=' * 60}")
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAILURES:
        print("\nFALHAS:")
        for nome, detalhe in FAILURES:
            print(f"  - {nome}: {detalhe}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(rodar())
