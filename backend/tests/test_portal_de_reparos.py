"""O portal de reparos escolhe com confiança, ou não escolhe — mas não erra.

`abraseuatendimento.com.br` é o MESMO portal para 8 seguradoras, é público (sem
login) e cobre vidros, lanternas, retrovisores e pequenos reparos. Um conserto
aqui vale para todas as seguradoras de uma vez.

📊 Medido em 03/08/2026 no Supabase `dcajcvlzcjbmyapmklil`, tabela
`portal_jobs`, 39 acionamentos reais de 06 a 10/07/2026:

    SELECT status, count(*) FROM portal_jobs
    WHERE portal_key='vidros_lanternas' GROUP BY status;
    -->  needs_human 33 · failed 5 · done 1

O diagnóstico honesto dos 33, por mensagem de parada:

    9  "cheguei na confirmacao (80%)"   <- NÃO é falha: é a trava funcionando
    9  "muitos passos sem concluir"     <- teto de 22 passos
    9  "preciso de: ..."                <- o cérebro desistiu e perguntou
    7  "tela travada: repetiu ..."      <- reclicou a mesma coisa 3x
    (os 5 `failed` são infraestrutura: 3 = binário do Playwright ausente,
     2 = worker reiniciado. Nenhum é falha de casamento de opção.)

R.1 · O erro não era acento, nem sinônimo, nem ordem das palavras
-----------------------------------------------------------------
    SELECT s->>'t', s->>'v', s->>'r' FROM portal_jobs,
      jsonb_array_elements(evidence->'adaptive_steps') s
    WHERE s->>'t' IN ('qualItemDanificado','comoOcorreuDanoVeiculo');

    'vidro de porta'  -> VIDRO DE PORTA               14x   certo
    'vidro da porta'  -> VIDRO PARABRISA - CARGA       3x   ERRADO
    'encontrou o veiculo danificado' -> idem          14x   certo
    'deixei o carro estacionado...'  -> CHOQUE TERMICO 3x   ERRADO

`de` e `da` são ambos palavra vazia: os dois pedidos viram o MESMO conjunto de
tokens. O que mudou foi a LISTA — rodaram em seguradoras diferentes. Onde
`VIDRO DE PORTA` existia, o casamento acertou; onde **não existia**, o placar
ainda assim elegeu o melhor dos errados, porque um único token em comum
(`vidro`) já batia o piso `bestScore <= 0`.

**`vidro` é a palavra mais comum de um portal de vidros: ela não distingue
nada.** A causa medida é essa — opção certa AUSENTE + token genérico.

R.2 · A trava de segurança nunca disparou
------------------------------------------
    34 jobs com passos gravados · 31 bateram em `click_notfound` no Avançar
    17 escolheram campo crítico ·  0 pararam devolvendo as opções

Zero. Em 34 acionamentos, o caminho "campo crítico sem match → devolve as
opções" **nunca executou**. E `evidence.opcoes` estava NULO nos 33
`needs_human`: ninguém conseguia resolver sem reabrir o portal, e a próxima
versão do casamento não tinha com o que aprender.

R.3 · Havia dois placares, e o que rodava não era o testado
------------------------------------------------------------
`match_option` (puro, em `vidros_lanternas.py`) só era chamado por `_choose` e
`_choose_any_select` — funções que a jornada de vidros nunca invoca, porque
delega para `run_adaptive` logo após o passo 1. Quem decidia de verdade era um
segundo placar escrito em JavaScript dentro de `_apply_mdselect`. Os testes
provavam um; produção rodava o outro.

R.4 · `click_notfound` respondia duas perguntas diferentes
-----------------------------------------------------------
📊 31 dos 34 jobs bateram nele. O botão Avançar DESABILITADO (falta preencher
um campo) e o botão AUSENTE devolviam a mesma palavra. Sem saber a diferença,
o cérebro reclicava até a tela ser declarada travada.
"""

from __future__ import annotations

import asyncio
import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# O console do Windows nasce em cp1252 e engasga com 📊, ≠ e até com os acentos
# do português — o teste morria de UnicodeEncodeError ANTES de checar qualquer
# coisa, e o relatório saía ilegível. Aqui ele fala UTF-8.
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


# ---------------------------------------------------------------------------
# As listas REAIS do portal. Reconstruídas das opções que o portal marcou nos
# jobs de produção (`mdselect=<texto>` em evidence.adaptive_steps).
# ---------------------------------------------------------------------------
PECA_COM_PORTA = ["Selecione uma opção", "VIDRO PARABRISA", "VIDRO DE PORTA",
                  "VIDRO VIGIA (TRASEIRO)"]
# A lista da seguradora onde o acionamento deu errado: NÃO tem vidro de porta.
PECA_SEM_PORTA = ["Selecione uma opção", "VIDRO PARABRISA", "VIDRO PARABRISA - CARGA",
                  "VIDRO VIGIA (TRASEIRO)"]
CAUSA = ["Selecione uma opção", "ENCONTROU O VEICULO DANIFICADO", "CHOQUE TERMICO",
         "DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO"]
TELEFONE = ["Selecione uma opção", "COMERCIAL (Apenas ligações)", "CELULAR CORRETOR"]
RELACAO = ["Selecione uma opção", "O próprio", "Cônjuge", "Filho", "Corretor", "Outros"]


def teste_a_peca_errada_nao_passa_mais():
    print("\n[R1] O caso que abriu pedido errado na seguradora")
    from portal_worker.journeys.vidros_lanternas import explicar_match, match_option

    d = explicar_match("vidro da porta", PECA_SEM_PORTA)
    checar(d["escolha"] is None,
           "'vidro da porta' sem opção de porta na lista -> NÃO escolhe",
           f"📊 3 acionamentos reais marcaram 'VIDRO PARABRISA - CARGA'; agora dá {d['escolha']}")
    checar(d["motivo"] == "peca_diferente",
           "e o motivo é nomeado: para-brisa não é vidro de porta")
    checar(d["opcoes"] == [o for o in PECA_SEM_PORTA if "Selecione" not in o],
           "a parada carrega TODAS as opções que o portal ofereceu",
           "é com isso que um humano resolve em 10 segundos")

    checar(match_option("vidro da porta", PECA_COM_PORTA) == "VIDRO DE PORTA",
           "e quando a opção certa EXISTE, ela é escolhida",
           "parar sempre seria inútil; o ponto é parar só quando falta a peça certa")
    checar(match_option("vidro de porta", PECA_COM_PORTA) == "VIDRO DE PORTA",
           "'de' e 'da' dão o mesmo resultado (📊 os 14 acertos de produção)")


def teste_a_causa_errada_nao_passa_mais():
    print("\n[R2] O relato de furto que virou 'CHOQUE TERMICO'")
    from portal_worker.journeys.vidros_lanternas import match_option

    relato = "deixei o carro estacionado e quando voltei tava com o vidro da porta quebrado"
    checar(match_option(relato, CAUSA) is None,
           "relato livre que não casa com nenhuma causa -> NÃO escolhe",
           "📊 3 acionamentos reais marcaram CHOQUE TERMICO (variação de temperatura) "
           "para um veículo arrombado")
    checar(match_option("encontrou o veiculo danificado", CAUSA) == "ENCONTROU O VEICULO DANIFICADO",
           "a causa que casa literalmente continua casando (📊 14 acertos)")
    checar(match_option("DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO", CAUSA)
           == "DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO",
           "e a que veio copiada do próprio portal também")


def teste_o_portugues_do_segurado():
    print("\n[R3] O segurado não fala como o portal escreve")
    from portal_worker.journeys.vidros_lanternas import match_option

    v = ["VIDRO PARABRISA", "VIDRO DE PORTA", "VIDRO VIGIA (TRASEIRO)",
         "RETROVISOR ELETRICO", "LANTERNA TRASEIRA", "FAROL DIANTEIRO"]
    for pedido, esperado, porque in (
        ("para-brisa", "VIDRO PARABRISA", "hífen"),
        ("pára-brisa", "VIDRO PARABRISA", "acento"),
        ("vidro dianteiro", "VIDRO PARABRISA", "sinônimo de posição"),
        ("vidro da frente", "VIDRO PARABRISA", "como se fala"),
        ("vidro lateral", "VIDRO DE PORTA", "lateral = porta"),
        ("janela", "VIDRO DE PORTA", "janela = porta"),
        ("porta do vidro", "VIDRO DE PORTA", "ordem trocada"),
        ("vidro traseiro", "VIDRO VIGIA (TRASEIRO)", "traseiro = vigia"),
        ("vigia", "VIDRO VIGIA (TRASEIRO)", "termo técnico"),
        ("espelho", "RETROVISOR ELETRICO", "espelho = retrovisor"),
        ("retrovisores", "RETROVISOR ELETRICO", "plural"),
        ("lanternas", "LANTERNA TRASEIRA", "plural"),
        ("faróis", "FAROL DIANTEIRO", "plural irregular + acento"),
    ):
        checar(match_option(pedido, v) == esperado, f"'{pedido}' -> {esperado}  ({porque})",
               f"deu {match_option(pedido, v)}")


def teste_em_duvida_ele_para():
    print("\n[R4] Em dúvida, parar é o comportamento CERTO")
    from portal_worker.journeys.vidros_lanternas import match_option

    checar(match_option("retrovisor", ["RETROVISOR ELETRICO", "RETROVISOR MANUAL"]) is None,
           "duas variantes da peça certa -> para (elétrico ou manual é decisão de gente)")
    checar(match_option("luz", ["FAROL DIANTEIRO", "LANTERNA TRASEIRA"]) is None,
           "'luz' pode ser farol OU lanterna -> para",
           "fundir os dois num sinônimo só produziria acionamento errado")
    checar(match_option("vidro da porta", ["VIDRO PORTA DIREITA", "VIDRO PORTA ESQUERDA"]) is None,
           "o lado não foi dito -> para")
    checar(match_option("vidro da porta traseira",
                        ["VIDRO DE PORTA DIANTEIRA", "VIDRO DE PORTA TRASEIRA"])
           == "VIDRO DE PORTA TRASEIRA",
           "mas quando o segurado DIZ a posição, ela decide")
    checar(match_option("teto solar", PECA_COM_PORTA) is None,
           "peça que o portal não oferece -> para (nunca o 'mais próximo')")
    checar(match_option("x", []) is None, "lista vazia -> None")
    checar(match_option("", PECA_COM_PORTA) is None, "pedido vazio -> None")
    checar(match_option("qualquer coisa", ["Selecione uma opção"]) is None,
           "só o placeholder na lista -> None")


def teste_campo_de_formato_continua_tolerante():
    print("\n[R5] Campo de formato não pode travar o acionamento")
    from portal_worker.journeys.vidros_lanternas import match_option

    checar(match_option("Comercial", TELEFONE) == "COMERCIAL (Apenas ligações)",
           "'Comercial' casa com 'COMERCIAL (Apenas ligações)'",
           "qualificativo entre parênteses não pode impedir o casamento")
    checar(match_option("Corretor", RELACAO) == "Corretor",
           "relação com o titular casa literalmente")


def teste_o_placar_e_unico():
    print("\n[R6] Um só placar no sistema — o que os testes exercitam")
    ad = _ler("portal_worker", "adaptive.py")
    checar("from portal_worker.journeys.vidros_lanternas import explicar_match" in ad,
           "o adaptive IMPORTA a função pura em vez de reimplementar")
    checar("explicar_match(value, [t for t, _ in reais])" in ad,
           "e é ela que decide dentro do _apply_mdselect")
    checar("let best = null, bestScore = -1;" not in ad,
           "o segundo placar, escrito em JS, não existe mais",
           "era ELE que rodava em produção enquanto os testes provavam o outro")
    checar("if (bestScore <= 0) {" not in ad,
           "e o piso que deixava um único token genérico decidir também não")


def teste_a_trava_de_confirmacao_continua():
    print("\n[R7] O passo 6 é o que ABRE o pedido — a trava não afrouxou")
    from portal_worker.adaptive import is_confirm_screen

    tela80 = {"heading": "", "text": (
        "menu 80% Confirme a peça danificada\n"
        "O atendimento web permite apenas a SELEÇÃO de 1 (um) ITEM para TROCA/REPARO.\n"
        "1) O vidro danificado tem película de controle solar (insulfilm)? SIM NÃO Não sabe")}
    checar(is_confirm_screen(tela80), "a tela real dos 80% é reconhecida",
           "📊 texto copiado de evidence.stage_80 de 9 jobs")

    banner = "O atendimento web permite apenas a SELEÇÃO de 1 (um) ITEM para TROCA/REPARO."
    checar(not is_confirm_screen({"heading": "", "text": "20% Confirme seus dados " + banner}),
           "o banner permanente NÃO é confundido com a confirmação",
           "ele aparece em todas as telas; confundir pararia o robô cedo demais")

    ad = _ler("portal_worker", "adaptive.py")
    checar("if is_confirm_screen(state) and not confirm:" in ad,
           "sem confirm=True, run_adaptive para na confirmação")
    checar('return JourneyResult(status="needs_human", captured={"stage": "confirme_80"}' in ad,
           "e o que sai de lá é needs_human, não done")
    checar("if not confirm:" in ad and
           'message="preenchimento completo — pare para revisao/aprovacao antes de enviar"' in ad,
           "e o 'done' do cérebro também é recusado sem confirm",
           "📊 o único job 'done' de produção nasceu 03:51:55Z de 07/07, quatro minutos "
           "ANTES desta trava (commit 7d31490, 03:56:10Z): confirm=false e SEM protocolo")
    checar("NAO clique em botao que FINALIZE o pedido" in ad,
           "e o cérebro é instruído a não finalizar por conta própria")

    jr = _ler("portal_worker", "journeys", "vidros_lanternas.py")
    checar('confirm=bool(params.get("confirm"))' in jr,
           "a jornada passa o confirm adiante sem inventar valor")


def teste_quando_para_para_bem():
    print("\n[R8] Uma parada só vale se um humano resolver em 10 segundos")
    from portal_worker.adaptive import _pedido_do_segurado, _registrar_parada, _rotulo_do_campo

    tela = {"url": "https://abraseuatendimento.com.br/#/porto/passo3",
            "heading": "Qual foi a peça danificada?",
            "pending_required": [{"tipo": "select", "label": "Tipo de telefone"}],
            "mdselects": [{"name": "qualItemDanificado", "label": "Qual foi a peça danificada?"}],
            "selects": [{"name": "qualItemDanificado", "label": "Qual foi a peça danificada?",
                         "options": PECA_SEM_PORTA}]}
    dito = {"dano": {"peca": "vidro da porta", "como": "estava estacionado",
                     "onde": "urbano", "descricao": "voltei e o vidro estava quebrado"}}

    ev: dict = {}
    _registrar_parada(ev, tela, dito, campo="qualItemDanificado",
                      pergunta="Qual foi a peça danificada?",
                      opcoes=[o for o in PECA_SEM_PORTA if "Selecione" not in o])
    checar(ev["passo"]["url"].endswith("passo3") and ev["passo"]["titulo"] == "Qual foi a peça danificada?",
           "a parada diz em QUE PASSO o robô estava")
    checar(ev["pergunta"] == "Qual foi a peça danificada?",
           "e a pergunta LITERAL que o portal fez")
    checar("VIDRO PARABRISA - CARGA" in ev["opcoes"] and len(ev["opcoes"]) == 3,
           "e TODAS as opções oferecidas",
           "📊 evidence.opcoes estava NULO nos 33 needs_human de produção")
    checar(ev["pedido_do_segurado"]["peca"] == "vidro da porta",
           "e o que o segurado disse, do jeito que ele disse")
    checar(ev["passo"]["obrigatorios_vazios"] == [{"tipo": "select", "label": "Tipo de telefone"}],
           "e o que ainda falta preencher na tela")

    # Sem o cérebro nomear o campo, a tela inteira vira material de aprendizado.
    ev2: dict = {}
    _registrar_parada(ev2, tela, dito)
    checar(ev2["dropdowns_da_tela"][0]["opcoes"] == PECA_SEM_PORTA,
           "sem campo nomeado, guarda os dropdowns da tela com as opções reais",
           "é a matéria-prima da próxima versão do casamento")

    checar(_rotulo_do_campo(tela, "qualItemDanificado") == "Qual foi a peça danificada?",
           "o name técnico vira a frase que o humano lê")
    checar(_rotulo_do_campo(tela, "campo_que_nao_existe") == "campo_que_nao_existe",
           "e um campo desconhecido não some da parada")
    checar(_pedido_do_segurado({"dano": {"peca": "", "como": "x"}}) == {"como": "x"},
           "campo vazio não polui o resumo")


def teste_botao_desabilitado_nao_e_botao_ausente():
    print("\n[R9] Avançar bloqueado ≠ Avançar inexistente (📊 31 de 34 jobs)")
    from portal_worker.adaptive import _click_button, apply_action

    class _B:
        def __init__(self, txt, vis=True, dis=False):
            self.t, self.v, self.d, self.clicado = txt, vis, dis, False

        async def is_visible(self):
            return self.v

        async def is_disabled(self):
            return self.d

        async def inner_text(self):
            return self.t

        async def get_attribute(self, k):
            return ""

        async def click(self, **kw):
            self.clicado = True

    class _P:
        def __init__(self, botoes, faltando=None):
            self.botoes, self.faltando = botoes, faltando or []

        async def query_selector_all(self, sel):
            return self.botoes if "button" in sel else []

        async def evaluate(self, js, *a):
            return self.faltando

        async def wait_for_timeout(self, ms):
            pass

    ok = _B("Avançar")
    checar(asyncio.run(_click_button(_P([ok]), "Avançar")) == "clicked" and ok.clicado,
           "botão livre é clicado")

    travado = _B("Avançar", dis=True)
    checar(asyncio.run(_click_button(_P([travado]), "Avançar")) == "disabled" and not travado.clicado,
           "botão desabilitado devolve 'disabled' — e NÃO é clicado")
    checar(asyncio.run(_click_button(_P([_B("Voltar")]), "Avançar")) == "notfound",
           "botão ausente devolve 'notfound'")

    r = asyncio.run(apply_action(_P([_B("Avançar", dis=True)], ["Tipo de telefone", "CEP"]),
                                 {"action": "click", "target": "Avançar", "value": ""}))
    checar(r.startswith("click_bloqueado:") and "Tipo de telefone" in r and "CEP" in r,
           "e o cérebro recebe QUAIS campos faltam, em vez de reclicar", r)

    ad = _ler("portal_worker", "adaptive.py")
    checar("'click_bloqueado: ... Falta preencher: X, Y' em acoes_ja_feitas" in ad,
           "o prompt do cérebro explica a diferença entre bloqueado e ausente")


def teste_seletor_nao_depende_de_posicao():
    print("\n[R10] Id numerado pelo Angular não decide sozinho onde vai a placa")
    jr = _ler("portal_worker", "journeys", "vidros_lanternas.py")
    codigo = "\n".join(l for l in jr.split("\n") if not l.lstrip().startswith("#"))

    checar('await (await page.query_selector("#input_1")).fill(placa)' not in codigo,
           "o preenchimento cego por #input_1 acabou",
           "id numerado depende da ORDEM dos campos: um campo a mais e a placa "
           "ia para o lugar errado, calada")
    checar('await (await page.query_selector("#inserir-cpf-input")).fill(cpf)' not in codigo,
           "e o CPF também não estoura mais em AttributeError se o campo sumir")
    checar("_achar_campo(page, (\"#input_1\",), (\"placa\",))" in codigo,
           "agora procura pelo SENTIDO (placa) e usa o id numerado como último recurso")
    checar('return JourneyResult(status="needs_human",' in codigo
           and "nao achei o campo de CPF ou de placa" in codigo,
           "e se o passo 1 mudar, para com o raio-X da tela em vez de explodir")


def teste_os_39_casamentos_reais():
    print("\n[R11] Os 39 casamentos críticos gravados em produção, refeitos")
    from portal_worker.journeys.vidros_lanternas import explicar_match

    # (pedido, lista, esperado (None = deve parar), quantas vezes ocorreu 📊)
    reais = [
        ("vidro de porta", PECA_COM_PORTA, "VIDRO DE PORTA", 14),
        ("vidro da porta", PECA_SEM_PORTA, None, 3),
        ("vidro de porta", PECA_COM_PORTA, "VIDRO DE PORTA", 2),
        ("vidro da porta traseira do carona", PECA_COM_PORTA, "VIDRO DE PORTA", 1),
        ("encontrou o veiculo danificado", CAUSA, "ENCONTROU O VEICULO DANIFICADO", 14),
        ("deixei o carro estacionado e quando voltei tava com o vidro da porta quebrado",
         CAUSA, None, 3),
        ("ENCONTROU O VEICULO DANIFICADO", CAUSA, "ENCONTROU O VEICULO DANIFICADO", 2),
        ("DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO", CAUSA,
         "DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO", 1),
    ]
    certos = parados = errados = 0
    for pedido, lista, esperado, n in reais:
        got = explicar_match(pedido, lista)["escolha"]
        if got == esperado and got is not None:
            certos += n
        elif got is None and esperado is None:
            parados += n
        else:
            errados += n
            checar(False, f"'{pedido[:40]}' -> {got}", f"esperado {esperado}")
    print(f"      {certos} casam certo · {parados} param e devolvem as opções · {errados} erram")
    checar(errados == 0, "nenhuma das 39 decisões críticas reais fica ERRADA",
           "📊 antes: 6 erradas (3 peça + 3 causa), 0 paradas")
    checar(certos == 34, "34 continuam casando sozinhas", f"deu {certos}")
    checar(parados == 6, "e as 6 que erravam agora param com a lista na mão", f"deu {parados}")


def main() -> int:
    print("=" * 72)
    print("PORTAL DE REPAROS — CASA COM CONFIANCA, OU NAO CASA; MAS NAO ERRA")
    print("=" * 72)
    for t in (teste_a_peca_errada_nao_passa_mais,
              teste_a_causa_errada_nao_passa_mais,
              teste_o_portugues_do_segurado,
              teste_em_duvida_ele_para,
              teste_campo_de_formato_continua_tolerante,
              teste_o_placar_e_unico,
              teste_a_trava_de_confirmacao_continua,
              teste_quando_para_para_bem,
              teste_botao_desabilitado_nao_e_botao_ausente,
              teste_seletor_nao_depende_de_posicao,
              teste_os_39_casamentos_reais):
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
    print("O PORTAL ESCOLHE COM CONFIANCA, PARA COM AS OPCOES NA MAO, E NAO ENVIA SOZINHO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
