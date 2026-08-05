"""O atendimento soa humano — sem nunca mentir que é humano.

A HISTÓRIA
----------
O Founder decidiu, em 05/08/2026, como o agente responde quando perguntam o que
ele é. A decisão tem três fases, e a ordem delas é a decisão inteira:

    1. NÃO ANUNCIA    nenhuma mensagem abre dizendo "sou uma IA"
    2. PERGUNTOU      desvia com leveza, uma frase, e segue resolvendo
    3. INSISTIU       ASSUME que é um agente — e nunca nega

    "Não queremos enganar ninguém. Queremos só omitir a informação de ficar
     escancarada. Não é para dizer humano e nem parecer nunca ser uma IA."

Omitir é legítimo. **Negar é mentira**, e mentira não é omissão. Este arquivo
guarda a diferença entre as duas — que é fina no texto e enorme na consequência.

📊 Os moldes de AVISAR, ACOMPANHAR e PASSAR PARA A EQUIPE não são copy inventada:
são transcrições do acervo real de atendimento da corretora (nomes removidos),
levantadas em 05/08/2026. Guardar o formato é guardar o que já se provou.

⛓️ E o risco que humanizar CRIA: quanto mais o agente soa gente, mais barato
fica contar uma ação que não aconteceu ("já cobrei a seguradora"). O bloco
"SÓ RELATE O QUE VOCÊ REALMENTE FEZ" é o preço de admissão dos outros quatro.

POR QUE O GUARDA NÃO É "A FRASE NÃO APARECE NO PROMPT"
------------------------------------------------------
Seria o teste errado, e passaria pelo motivo errado. O prompt **precisa** dizer
`"sou uma IA"` — é assim que ele PROÍBE a frase. Um guarda de ausência literal
obrigaria a apagar a proibição para ficar verde.

O que se guarda é outra coisa: **toda linha que cita uma frase proibida tem de
ser uma linha de proibição.** É a diferença entre o prompt nomear o defeito e o
prompt ensinar o defeito.

A LINHA DE CONTROLE (CLAUDE.md §9.2)
------------------------------------
Três guardas aqui poderiam passar sem guardar nada, e cada um tem o seu controle:

* `controle_o_detector_de_frase_proibida_reprova` — injeta uma linha com a frase
  proibida SEM marcador de proibição, e exige que o detector a acuse. Sem isto,
  "nenhuma linha suspeita" não distingue "o prompt está certo" de "o detector
  não olha nada".
* `controle_o_comparador_de_variacao_reprova` — passa cinco frases quase iguais e
  exige que o comparador as recuse. Um comparador frouxo aprovaria cinco cópias.
* `controle_case_ids_diferentes_dao_variantes_diferentes` — se todos os casos
  caíssem na mesma variante, "o mesmo caso dá sempre o mesmo texto" seria
  verdade e inútil.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import os
import re
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))          # backend/
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  ok    {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X     {nome}  {detalhe}")


def _carregar(nome: str, rel: str):
    """Carrega o módulo PELO CAMINHO, sem passar pelo pacote `app`.

    Importar `app.core.prompts` puxa `app/core/__init__.py` e com ele a cadeia
    de configuração do backend (pydantic, redis, openai), que não existe numa
    máquina de desenvolvimento. O teste reprovaria por dependência ausente, não
    por defeito — a pior espécie de vermelho, porque ensina a ignorar o teste.
    """
    caminho = os.path.join(RAIZ, rel)
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


# `pytz` é opcional em `build_composite_prompt` (há fallback), mas o stub evita
# depender de qual máquina roda a suíte. timezone→None = datetime naive.
sys.modules.setdefault("pytz", types.SimpleNamespace(timezone=lambda *a, **k: None))

PROMPTS = _carregar("_prompts_sob_teste", "app/core/prompts.py")
FOLLOWUP = _carregar("_followup_sob_teste", "app/tasks/dispatch_followup.py")

# O PROMPT VIVO, não a constante. É o que `graph.py` monta e o modelo lê: se
# alguém quebrar a composição, o teste tem de cair junto.
ATENDENTE: str = PROMPTS.build_composite_prompt("", agent_role="attendance")


# --------------------------------------------------------------------- #
# Ferramentas de leitura do prompt
# --------------------------------------------------------------------- #

def _bloco(titulo: str) -> str:
    """O texto de um bloco `### …`, do título até o próximo `### `."""
    i = ATENDENTE.find(titulo)
    if i < 0:
        return ""
    j = ATENDENTE.find("\n### ", i + 1)
    return ATENDENTE[i:j if j > 0 else len(ATENDENTE)]


# Frases que o agente NUNCA deve dizer por conta própria.
#
# Duas famílias, e elas não são a mesma coisa:
#   AUTO_REVELACAO — anunciar-se sem ninguém perguntar. Não é mentira; é o
#                    contrário do atendimento humano que se quer imitar.
#   NEGACAO        — dizer que é gente. É MENTIRA, e é a linha que o Founder
#                    proibiu com todas as letras. Fase 3 existe por causa dela.
AUTO_REVELACAO = (
    "sou um assistente virtual",
    "sou uma ia",
    "sou um bot",
    "sou automático",
)
NEGACAO = (
    "sou uma pessoa",
    "sou humano",
    "sou de carne e osso",
    "não sou um robô",
    "não sou uma ia",
    "juro que não sou",
)
# O que faz de uma linha uma linha de PROIBIÇÃO. Sem um destes, citar a frase é
# ensiná-la.
MARCADORES = ("nunca", "proibido", "jamais", "não diga", "nao diga")


def _linhas_que_ensinam(texto: str, frases) -> list[str]:
    """Linhas que citam uma frase proibida SEM proibi-la."""
    suspeitas = []
    for linha in texto.split("\n"):
        baixa = linha.lower()
        if not any(f in baixa for f in frases):
            continue
        if any(m in baixa for m in MARCADORES):
            continue
        suspeitas.append(linha.strip()[:110])
    return suspeitas


def _palavras(frase: str) -> set:
    return {p for p in re.split(r"[^0-9a-zà-ÿ]+", frase.lower()) if len(p) > 2}


def _mais_parecidas(frases: list[str]) -> tuple[float, str]:
    """A maior semelhança entre dois itens da lista (Jaccard de palavras)."""
    pior, quem = 0.0, ""
    for i in range(len(frases)):
        for j in range(i + 1, len(frases)):
            a, b = _palavras(frases[i]), _palavras(frases[j])
            if not a or not b:
                continue
            s = len(a & b) / len(a | b)
            if s > pior:
                pior, quem = s, f"#{i + 1} x #{j + 1}"
    return pior, quem


# Acima disto, duas frases são a mesma frase com outra roupa. 0.45 deixa passar
# variação de estrutura ("já recebeu tudo" / "já está com o histórico") e barra
# reescrita cosmética.
TETO_DE_SEMELHANCA = 0.45


# --------------------------------------------------------------------- #
# CONTROLES — antes dos guardas, porque é o que dá direito à conclusão
# --------------------------------------------------------------------- #

def controle_o_detector_de_frase_proibida_reprova() -> None:
    """CONTROLE. Prove que o detector ACUSA antes de acreditar no 'limpo'."""
    print("\n[C1] CONTROLE: o detector de frase proibida consegue reprovar")

    ensina = '- Se perguntarem, responda: "sou humano, pode ficar tranquilo".'
    achadas = _linhas_que_ensinam(ensina, NEGACAO)
    checar(len(achadas) == 1,
           "uma linha que ENSINA a negar é acusada",
           f"achadas={achadas}")

    proibe = '- **NUNCA diga:** "sou humano", "sou uma pessoa".'
    checar(_linhas_que_ensinam(proibe, NEGACAO) == [],
           "e a MESMA frase, numa linha de proibição, passa",
           "senão o prompt teria de apagar a proibição para ficar verde")

    # E o detector não pode ser cego à segunda família.
    checar(len(_linhas_que_ensinam('- Abra com: "sou uma IA da corretora".',
                                   AUTO_REVELACAO)) == 1,
           "auto-revelação sem proibição também é acusada")


def controle_o_comparador_de_variacao_reprova() -> None:
    """CONTROLE. Cinco cópias com uma vírgula trocada NÃO são cinco formas."""
    print("\n[C2] CONTROLE: o comparador de variação consegue reprovar")

    falsas = [
        "Vou passar seu caso para a equipe, eles já receberam tudo.",
        "Vou passar seu caso para a equipe, eles já receberam tudo!",
        "Vou passar o seu caso para a equipe, eles já receberam tudo.",
        "Vou passar seu caso para a equipe — eles já receberam tudo.",
        "Vou passar seu caso para nossa equipe, eles já receberam tudo.",
    ]
    pior, quem = _mais_parecidas(falsas)
    checar(pior > TETO_DE_SEMELHANCA,
           f"cinco quase-cópias são reprovadas (semelhança {pior:.2f} em {quem})",
           "um comparador frouxo aprovaria a mesma frase cinco vezes")

    diferentes = [
        "Vou pedir para a Ana seguir daqui e te retornar.",
        "Essa parte é com o pessoal de sinistro; já mandei tudo pra eles.",
        "Te passo o contato dela, o histórico inteiro já está lá.",
        "Encaminhei ao analista. Quando ele responder eu te aviso.",
        "Quem cuida disso é o Marcos, e ele já recebeu a conversa.",
    ]
    pior2, _ = _mais_parecidas(diferentes)
    checar(pior2 <= TETO_DE_SEMELHANCA,
           f"e cinco formas de verdade passam (semelhança {pior2:.2f})",
           "um comparador rígido demais impediria escrever cinco frases")


def controle_case_ids_diferentes_dao_variantes_diferentes() -> None:
    """CONTROLE. Se tudo caísse na variante 0, o determinismo seria vazio."""
    print("\n[C3] CONTROLE: casos diferentes conseguem dar textos diferentes")

    casos = [f"caso-{n:04d}" for n in range(60)]
    vistos = {FOLLOWUP._variante_de(c) for c in casos}
    checar(len(vistos) == len(FOLLOWUP.FOLLOWUP_VARIANTES),
           f"60 casos cobrem as {len(FOLLOWUP.FOLLOWUP_VARIANTES)} variantes "
           f"(vistas: {sorted(vistos)})",
           "sem isto, 'o mesmo caso dá o mesmo texto' seria verdade e inútil")

    textos = {FOLLOWUP.texto_de_followup({"case_id": c}) for c in casos}
    checar(len(textos) == len(FOLLOWUP.FOLLOWUP_VARIANTES),
           "e os TEXTOS finais também são distintos, não só os índices")


# --------------------------------------------------------------------- #
# 1 — Identidade: não anuncia, desvia, assume. E nunca nega.
# --------------------------------------------------------------------- #

def teste_o_prompt_nao_ensina_a_se_anunciar_nem_a_negar() -> None:
    print("\n[1] Nenhuma linha do prompt ENSINA a se anunciar ou a negar")

    ensinam_negacao = _linhas_que_ensinam(ATENDENTE, NEGACAO)
    checar(not ensinam_negacao,
           "nenhuma linha manda o agente dizer que é gente",
           f"linhas: {ensinam_negacao}")

    ensinam_revelacao = _linhas_que_ensinam(ATENDENTE, AUTO_REVELACAO)
    checar(not ensinam_revelacao,
           "nenhuma linha manda o agente se anunciar como IA",
           f"linhas: {ensinam_revelacao}")

    # E as proibições EXISTEM — ausência de linha suspeita não prova regra.
    baixa = ATENDENTE.lower()
    for frase in ("sou uma pessoa", "sou humano", "sou de carne e osso"):
        checar(frase in baixa, f"a proibição nomeia '{frase}'",
               "regra que não nomeia o erro não é seguida")


def teste_as_tres_fases_existem_e_se_distinguem() -> None:
    print("\n[2] As três fases estão escritas — e são três coisas diferentes")
    bloco = _bloco("### 🪪 QUEM ESTÁ FALANDO")
    checar(bool(bloco), "o bloco de identidade existe no prompt VIVO",
           "sem ele, as três fases são só uma conversa de corredor")

    checar("NÃO ANUNCIA" in bloco, "fase 1 nomeada: não anuncia")
    checar("desvie" in bloco.lower(), "fase 2 nomeada: desvia")
    checar("INSISTIU" in bloco and "ASSUMA" in bloco,
           "fase 3 nomeada: insistiu → assume")

    # A ordem importa tanto quanto a existência: assumir antes de desviar seria
    # outra decisão, não esta.
    checar(bloco.find("NÃO ANUNCIA") < bloco.find("INSISTIU"),
           "e estão na ordem decidida (anunciar < desviar < assumir)")

    # SÓ o trecho da fase 2. Varrer o bloco inteiro capturava também a frase da
    # fase 3 (é uma linha `- "…"` igual) e o teste diria "4 desvios" contando a
    # confissão como desvio — guarda medindo a coisa errada.
    fase2 = bloco[bloco.find("PERGUNTOU UMA VEZ"):bloco.find("INSISTIU")]
    desvios = re.findall(r'^\s+- "(.+?)"\s*$', fase2, re.M)
    checar(len(desvios) >= 3, f"a fase 2 dá {len(desvios)} desvios (mínimo 3)",
           "uma frase só vira bordão, e bordão é assinatura de robô")
    if len(desvios) >= 3:
        pior, quem = _mais_parecidas(desvios)
        checar(pior <= TETO_DE_SEMELHANCA,
               f"e os desvios são de verdade diferentes ({pior:.2f})", quem)
    checar(_linhas_que_ensinam(fase2, NEGACAO + AUTO_REVELACAO) == [],
           "e nenhum desvio nega nem se anuncia — só desconversa",
           "desviar mentindo seria a fase 2 quebrando a decisão inteira")

    # A fase 3 assume ser AGENTE — e não com um "sou uma IA" seco.
    fase3 = bloco[bloco.find("INSISTIU"):]
    checar("agente" in fase3.lower(),
           "a fase 3 assume ser um agente, com essa palavra")
    checar(re.search(r"seguindo|continu|resolv", fase3, re.I) is not None,
           "e continua resolvendo na mesma frase",
           "assumir e parar transformaria a confissão no fim do atendimento")


def teste_pedir_humano_nao_e_pergunta_de_identidade() -> None:
    print("\n[3] Pedir para falar com uma pessoa continua sendo handoff")
    bloco = _bloco("### 🪪 QUEM ESTÁ FALANDO")
    checar("pedido de humano" in bloco.lower(),
           "o prompt separa 'você é um robô?' de 'quero falar com alguém'",
           "confundir os dois faria o agente desconversar com quem pediu ajuda")


def teste_o_titulo_do_bloco_nao_colide_com_a_identidade_configuravel() -> None:
    """Regressão cruzada: `test_spec017_identity` exige que 'SUA IDENTIDADE' só
    apareça quando a corretora configurou um nome de atendente. Um bloco fixo
    com esse título faria aquele teste cair — e o defeito seria aqui."""
    print("\n[4] O bloco novo não sequestra o título da identidade configurável")
    sem_nome = PROMPTS.build_composite_prompt("Regras.", agent_role="attendance")
    checar("SUA IDENTIDADE" not in sem_nome,
           "sem nome configurado, nenhum bloco se chama 'SUA IDENTIDADE'",
           "o atendente não inventa identidade — SPEC-017")
    com_nome = PROMPTS.build_composite_prompt(
        "Regras.", agent_role="attendance", agent_display_name="Saionara",
        company_display_name="Resulta Seguros")
    checar("SUA IDENTIDADE" in com_nome and "Saionara" in com_nome,
           "e com nome configurado ele continua entrando")


# --------------------------------------------------------------------- #
# 2 — Avisar o que ficou decidido
# --------------------------------------------------------------------- #

def teste_o_aviso_segue_a_ordem_do_acervo() -> None:
    print("\n[5] O aviso sai numa mensagem só, na ordem do atendimento real")
    bloco = _bloco("### 📣 AVISAR O QUE FICOU DECIDIDO")
    checar(bool(bloco), "o bloco de aviso existe")
    checar("uma mensagem só" in bloco.lower() or "UMA mensagem" in bloco,
           "e diz explicitamente que é UMA mensagem",
           "📊 no acervo o aviso chega inteiro, não em três pedaços")

    # A ordem é o molde real: conseguiu → quando → o que muda pra ELE →
    # protocolo → porta aberta. Lê-se os RÓTULOS dos itens numerados, não o
    # texto solto: procurar "Quando" no bloco inteiro casava com a frase de
    # abertura e provava a ordem errada — um guarda que acerta por acaso.
    rotulos = re.findall(r"^\d+\.\s+\*\*(.+?)\*\*", bloco, re.M)
    checar(len(rotulos) == 5, f"o aviso tem cinco passos numerados: {rotulos}")
    esperado = ["conseguiu", "quando", "acontecer", "protocolo", "porta aberta"]
    if len(rotulos) == 5:
        casam = [e in r.lower() for e, r in zip(esperado, rotulos)]
        checar(all(casam),
               f"e na ordem do acervo: {esperado}",
               f"veio: {rotulos}")


def teste_o_texto_da_seguradora_e_reescrito_mas_o_numero_e_copiado() -> None:
    print("\n[6] Reescreve o texto da seguradora; copia o número exato")
    bloco = _bloco("### 📣 AVISAR O QUE FICOU DECIDIDO")
    checar(re.search(r"NUNCA cole o texto da seguradora", bloco) is not None,
           "proíbe colar o texto cru da seguradora",
           "menu de URA repassado ao segurado é a marca do robô")
    checar("EXATOS" in bloco,
           "e manda repassar EXATOS os números")
    for dado in ("protocolo", "senha", "link"):
        checar(dado in bloco.lower(), f"'{dado}' está na lista do que se copia")
    checar("não invente" in bloco.lower() or "não preencha" in bloco.lower(),
           "sem previsão real, a linha do prazo não é inventada",
           "prazo inventado é o dano mais caro deste bloco")


# --------------------------------------------------------------------- #
# 3 — Acompanhar: as três respostas
# --------------------------------------------------------------------- #

def teste_as_tres_respostas_tem_caminho() -> None:
    print("\n[7] Chegou / não chegou / silêncio — cada uma com o seu caminho")
    bloco = _bloco("### 🔄 ACOMPANHAR")
    checar(bool(bloco), "o bloco de acompanhamento existe")
    for resposta in ("CHEGOU", "NÃO CHEGOU", "SILÊNCIO"):
        checar(resposta in bloco, f"a resposta '{resposta}' tem caminho escrito")

    ruim = bloco[bloco.find("NÃO CHEGOU"):bloco.find("SILÊNCIO")]
    passos = ["ACOLHA", "vai fazer", "Pergunte", "AJA", "equipe"]
    posicoes = [ruim.find(p) for p in passos]
    checar(all(p >= 0 for p in posicoes),
           "o 'não chegou' tem os cinco passos (acolher, dizer, perguntar, agir, escalar)",
           str(dict(zip(passos, posicoes))))
    checar(posicoes == sorted(posicoes), "e na ordem — agir antes de acolher seria frio",
           str(posicoes))
    checar("MUDA a sua ação" in ruim or "muda a sua ação" in ruim,
           "e só pergunta o que muda a ação",
           "quem está parado na estrada não responde questionário")

    silencio = bloco[bloco.find("SILÊNCIO"):]
    checar("UM toque" in silencio or "um toque" in silencio,
           "no silêncio, um toque só — não dois",
           "📊 do acervo: 'nao lhe retornei ainda porque ainda nao foi resolvido'")


# --------------------------------------------------------------------- #
# 4 — Handoff: cinco formas, e nenhuma delas com voz de URA
# --------------------------------------------------------------------- #

def teste_o_handoff_tem_cinco_formas_de_verdade() -> None:
    print("\n[8] Cinco formas de passar para a equipe — cinco mesmo")
    bloco = _bloco("### 🙋 PASSAR PARA A EQUIPE")
    checar(bool(bloco), "o bloco de handoff existe")

    formas = re.findall(r'^\d+\.\s+"(.+?)"\s*$', bloco, re.M)
    checar(len(formas) == 5, f"são cinco formas numeradas (achei {len(formas)})")
    checar(len(set(formas)) == len(formas), "e nenhuma é cópia literal de outra")

    if len(formas) == 5:
        pior, quem = _mais_parecidas(formas)
        checar(pior <= TETO_DE_SEMELHANCA,
               f"as cinco são diferentes de verdade (pior par: {pior:.2f})",
               f"{quem} — cinco reescritas da mesma frase não são cinco formas")

        # As DUAS promessas, em TODA forma: (a) já recebeu tudo e (b) não repete
        # nada. As listas abaixo são o VOCABULÁRIO das duas promessas, não a
        # transcrição das cinco frases: reescrever uma forma sem carregar a
        # promessa continua reprovando, que é o ponto.
        for i, f in enumerate(formas, 1):
            baixa = f.lower()
            recebeu = any(p in baixa for p in
                          ("já vai com tudo", "caso completo", "histórico",
                           "com tudo o que", "recebeu a nossa conversa",
                           "já recebeu", "já está com"))
            sem_repetir = any(p in baixa for p in
                              ("não precisa repetir", "não vai ter que contar",
                               "sem recomeçar", "não se perdeu", "nada do que",
                               "nada duas vezes", "perguntar nada duas vezes"))
            checar(recebeu, f"forma {i}: diz que a pessoa JÁ recebeu tudo")
            checar(sem_repetir, f"forma {i}: diz que ele NÃO vai repetir nada",
                   "é a única coisa que o cliente realmente teme no handoff")


def teste_o_handoff_proibe_a_voz_de_ura() -> None:
    print("\n[9] O vocabulário de URA está proibido, com nome e sobrenome")
    bloco = _bloco("### 🙋 PASSAR PARA A EQUIPE")
    for frase in ("vou te transferir", "setor responsável",
                  "você será atendido em breve"):
        checar(frase in bloco.lower(), f"'{frase}' está nomeada como proibida")
    checar("PROIBIDO" in bloco, "e a lista é uma proibição, não uma sugestão")
    # E não pode estar sendo ensinada em outro lugar do prompt.
    ura = ("vou te transferir", "encaminhando para o setor responsável",
           "você será atendido em breve")
    checar(_linhas_que_ensinam(ATENDENTE, ura) == [],
           "e nenhuma outra linha do prompt usa essas frases a sério")


# --------------------------------------------------------------------- #
# 5 — A trava contra ação inventada
# --------------------------------------------------------------------- #

def teste_a_trava_contra_acao_inventada() -> None:
    print("\n[10] O agente só relata o que ELE fez, com ferramenta")
    bloco = _bloco("### ⛓️ SÓ RELATE O QUE VOCÊ REALMENTE FEZ")
    checar(bool(bloco), "o bloco existe",
           "é o preço de admissão de humanizar: soar gente barateia inventar")

    for exemplo in ("já cobrei a seguradora", "liguei na central",
                    "falei com o analista"):
        checar(exemplo in bloco.lower(), f"nomeia o exemplo '{exemplo}'",
               "regra abstrata não pega alucinação concreta")

    checar("ferramenta" in bloco.lower() and "MESMA resposta" in bloco,
           "e exige a chamada da ferramenta na MESMA resposta")
    checar("Prometeu, executou" in bloco,
           "a regra 'prometeu, executou' migrou para cá em vez de sumir",
           "CLAUDE.md §9.3 — a lição migra, não morre")
    # E não ficou duplicada onde estava antes.
    memoria = _bloco("### 🧠 MEMÓRIA DA CONVERSA")
    checar("Prometeu, executou" not in memoria,
           "e NÃO ficou repetida no bloco antigo",
           "prompt longo demais dilui — regra em dois lugares é meia regra")


# --------------------------------------------------------------------- #
# 6 — A coleta que não vira interrogatório
# --------------------------------------------------------------------- #

def teste_a_coleta_distingue_entender_de_executar() -> None:
    print("\n[11] Uma pergunta por vez OU bloco de até 4 — e a regra diz qual")
    bloco = _bloco("### 🎯 PERGUNTAR SEM INTERROGAR")
    checar(bool(bloco), "o bloco existe")
    checar("UMA por vez" in bloco, "o modo 'uma por vez' está escrito")
    checar("até 4" in bloco or "até 4 itens" in bloco, "o modo 'bloco' está escrito")
    checar("ENTENDENDO" in bloco and "DECIDIU" in bloco,
           "e o critério é a FASE, não o gosto do momento",
           "📊 no acervo, o bloco de 3-4 itens só aparece com o caso já contado")
    checar("MUDA a próxima" in bloco or "MUDA a pergunta" in bloco,
           "com a segunda condição: resposta que muda a pergunta seguinte")
    checar("Máximo 4" in bloco, "o teto é explícito")
    checar("DELICADA" in bloco,
           "e pergunta delicada nunca entra em bloco",
           "perguntar de vítimas no meio de uma lista numerada é violência")

    # O prompt não pode continuar mandando o contrário em outro lugar.
    checar("Uma pergunta por vez." not in ATENDENTE,
           "a ordem antiga 'UMA pergunta por vez' sumiu do resto do prompt",
           "duas regras opostas no mesmo prompt = o modelo escolhe uma")


# --------------------------------------------------------------------- #
# 7 — O follow-up varia, mas nunca no mesmo caso
# --------------------------------------------------------------------- #

def teste_o_mesmo_caso_da_sempre_a_mesma_pergunta() -> None:
    print("\n[12] Reenvio repete o texto — variação nunca é sorteio")
    checar(len(FOLLOWUP.FOLLOWUP_VARIANTES) == 3, "são três variantes")

    caso = {"case_id": "AB-2026-0817", "slots": {"titular_nome": "JOAO DA SILVA"}}
    primeira = FOLLOWUP.texto_de_followup(caso)
    for _ in range(30):
        checar_igual = FOLLOWUP.texto_de_followup(caso) == primeira
        if not checar_igual:
            break
    checar(checar_igual, "30 chamadas seguidas devolvem o MESMO texto",
           "a varredura roda a cada 60s e retenta — sorteio mandaria duas "
           "perguntas diferentes sobre o mesmo guincho")

    pior, _ = _mais_parecidas(list(FOLLOWUP.FOLLOWUP_VARIANTES))
    checar(pior <= TETO_DE_SEMELHANCA,
           f"e as três variantes são diferentes de verdade ({pior:.2f})")


def teste_o_followup_usa_o_nome_e_nunca_inventa_um() -> None:
    print("\n[13] Chama pelo nome quando há nome — e só quando há")
    com_nome = FOLLOWUP.texto_de_followup(
        {"case_id": "X1", "slots": {"titular_nome": "MARIA APARECIDA SOUZA"}})
    checar(com_nome.startswith("Maria, "), f"usa o primeiro nome: {com_nome[:20]!r}")

    sem_nome = FOLLOWUP.texto_de_followup({"case_id": "X1", "slots": {}})
    checar(sem_nome.startswith("Oi! "), "sem nome, abre com 'Oi!'")
    checar("Maria" not in sem_nome, "e não inventa nome nenhum")

    # A mesma variante nos dois formatos: o nome não pode trocar a pergunta.
    checar(com_nome.split(", ", 1)[1].lower() == sem_nome[4:].lower(),
           "o corpo da pergunta é o mesmo com e sem nome",
           "o nome é saudação, não outra mensagem")

    for sujo in ("", "  ", "N/A", "nao informado", "123456"):
        t = FOLLOWUP.texto_de_followup({"case_id": "X1",
                                        "slots": {"titular_nome": sujo}})
        checar(t.startswith("Oi! "), f"slot sujo ({sujo!r}) não vira saudação",
               "'Olá 123456' é pior que 'Oi!'")


def teste_o_followup_nao_sorteia() -> None:
    print("\n[14] O código não tem sorteio — e o hash é estável entre processos")
    fonte = io.open(os.path.join(RAIZ, "app/tasks/dispatch_followup.py"),
                    encoding="utf-8").read()
    codigo = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))
    checar("import random" not in codigo and "random." not in codigo,
           "nenhum uso de `random`",
           "reenvio com texto diferente parece dois atendimentos")
    checar("hashlib" in codigo, "a escolha vem de hashlib")
    checar(re.search(r"[^.\w]hash\(", codigo) is None,
           "e NÃO do `hash()` embutido",
           "`hash()` de str é salgado por processo — restart trocaria a variante")


# --------------------------------------------------------------------- #
# 8 — O defeito que este trabalho encontrou de raspão
# --------------------------------------------------------------------- #

def _primeira_linha(fn: ast.AST, nome: str, ctx) -> int:
    """Linha da primeira ocorrência de `nome` no contexto pedido (Store/Load)."""
    linhas = [n.lineno for n in ast.walk(fn)
              if isinstance(n, ast.Name) and n.id == nome
              and isinstance(n.ctx, ctx)]
    return min(linhas) if linhas else -1


def _usa_antes_de_atribuir(fonte: str, funcao: str, nome: str) -> bool:
    arvore = ast.parse(fonte)
    fn = next((n for n in ast.walk(arvore)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == funcao), None)
    if fn is None:
        return False
    escrita = _primeira_linha(fn, nome, ast.Store)
    leitura = _primeira_linha(fn, nome, ast.Load)
    return leitura >= 0 and (escrita < 0 or leitura < escrita)


def teste_a_corretora_e_lida_antes_de_ser_usada() -> None:
    """📊 Defeito encontrado em 05/08/2026 ao editar este arquivo.

    `company_id` era atribuído DEPOIS do ramo de encerramento que já o usava.
    Efeito 1: `UnboundLocalError` na primeira sessão em encerramento — engolido
    pelo `except` da varredura, matando TODOS os follow-ups em silêncio.
    Efeito 2, pior: da segunda volta do laço em diante, `company_id` carregava a
    corretora da chave ANTERIOR — leitura cross-tenant (CLAUDE.md §7).
    """
    print("\n[15] A corretora sai da chave ANTES de qualquer uso")
    fonte = io.open(os.path.join(RAIZ, "app/tasks/dispatch_followup.py"),
                    encoding="utf-8").read()
    for nome in ("company_id", "insurer_phone"):
        checar(not _usa_antes_de_atribuir(fonte, "check_dispatch_followups", nome),
               f"`{nome}` é atribuído antes de ser lido",
               "UnboundLocalError + risco cross-tenant no mesmo lugar")


def controle_o_detector_de_uso_antes_da_atribuicao_reprova() -> None:
    """CONTROLE. O detector acima só vale se ele acusar o código defeituoso."""
    print("\n[C4] CONTROLE: o detector de uso-antes-de-atribuir consegue reprovar")
    defeituoso = (
        "async def check_dispatch_followups():\n"
        "    for k in chaves:\n"
        "        if conferir(company_id):\n"
        "            pass\n"
        "        company_id = k.split(':')[2]\n"
    )
    checar(_usa_antes_de_atribuir(defeituoso, "check_dispatch_followups", "company_id"),
           "a ordem antiga (usar e depois atribuir) é ACUSADA")
    correto = (
        "async def check_dispatch_followups():\n"
        "    for k in chaves:\n"
        "        company_id = k.split(':')[2]\n"
        "        if conferir(company_id):\n"
        "            pass\n"
    )
    checar(not _usa_antes_de_atribuir(correto, "check_dispatch_followups", "company_id"),
           "e a ordem certa passa")


def main() -> int:
    print("=" * 72)
    print("O ATENDIMENTO SOA HUMANO — SEM NUNCA MENTIR QUE E HUMANO")
    print("=" * 72)
    for teste in (
        controle_o_detector_de_frase_proibida_reprova,
        controle_o_comparador_de_variacao_reprova,
        controle_case_ids_diferentes_dao_variantes_diferentes,
        teste_o_prompt_nao_ensina_a_se_anunciar_nem_a_negar,
        teste_as_tres_fases_existem_e_se_distinguem,
        teste_pedir_humano_nao_e_pergunta_de_identidade,
        teste_o_titulo_do_bloco_nao_colide_com_a_identidade_configuravel,
        teste_o_aviso_segue_a_ordem_do_acervo,
        teste_o_texto_da_seguradora_e_reescrito_mas_o_numero_e_copiado,
        teste_as_tres_respostas_tem_caminho,
        teste_o_handoff_tem_cinco_formas_de_verdade,
        teste_o_handoff_proibe_a_voz_de_ura,
        teste_a_trava_contra_acao_inventada,
        teste_a_coleta_distingue_entender_de_executar,
        teste_o_mesmo_caso_da_sempre_a_mesma_pergunta,
        teste_o_followup_usa_o_nome_e_nunca_inventa_um,
        teste_o_followup_nao_sorteia,
        teste_a_corretora_e_lida_antes_de_ser_usada,
        controle_o_detector_de_uso_antes_da_atribuicao_reprova,
    ):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            print(f"  X     {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"FALHOU — {len(FALHAS)} verificacoes")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("NAO ANUNCIA, DESVIA, ASSUME — E NUNCA NEGA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
