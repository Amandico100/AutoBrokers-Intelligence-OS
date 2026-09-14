# -*- coding: utf-8 -*-
r"""G8 — O AGENTE SE APRESENTA UMA VEZ, NO TAMANHO CERTO, COM A IDENTIDADE DESTE ASSUNTO.

SPEC-EXTRA-001.2 BLOCO DF (§8.1 apresentacao · §8.2 tamanho · §8.3 identidade).

```
deve_se_apresentar      (o MOTOR, puro)      -> 1 apresentacao por ASSUNTO
bloco_de_quem_fala      (o MOTOR, puro)      -> a UNICA linha que vai ao prompt
build_composite_prompt  (o MOTOR do prompt)  -> o `sempre-se-apresente` MORREU
classe_do_tamanho       (o MOTOR, puro)      -> conversa 3 · bloco 4 · lista SEM TETO
agent_node              (o MOTOR de producao)-> UMA regeneracao, depois ENVIA e registra
fundir                  (o MOTOR da ficha)   -> assunto novo REESCREVE a identidade
```

🔴 OS DEFEITOS QUE ESTE GUARDA MEDE — todos de producao:

📊 09/09/2026, 11:40: o robo cumprimentou *"bom dia, e bom comecar o dia com
   voce"* na **30a mensagem** de um sinistro com vitima. A causa era um
   conflito de blocos: o ESTATICO (cacheado, e primeiro no prompt) mandava se
   apresentar "na primeira mensagem" e o DINAMICO mandava continuar de onde
   parou. O modelo leu "primeira mensagem" como "a primeira MINHA".

📊 10/09/2026: mensagens de **760 caracteres** numa conversa comum — com as
   regras de tamanho JA escritas no prompt. Prosa no prompt nao conserta prosa
   do modelo (AAA §3).

📊 10/09/2026: o agente abriu um caso chamando o cliente pelo nome de OUTRA
   pessoa, de **22 dias atras**. A thread e por TELEFONE e nunca reinicia.

⚠️ A regua humana medida (14/09, 6.213 rajadas >=3 respondidas): mediana **92
caracteres**, 1 a 2 mensagens. ⛔ Balao NAO e a regua (`balloons.py` 300/500/4
e humanizacao): o que se mede aqui e UM TURNO.

⛔ SEGURANCA: sem rede, sem banco, sem modelo, sem PII. Ficha sintetica, modelo
duble, e o "replay do encanador" e ESTRUTURAL (numero de turnos e papeis), nao
o texto de gente real.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_o_agente_se_apresenta_uma_vez.py
    ... --so GD8b   ·   ... --medir   ·   ... --mutar [M-D8a]
"""
from __future__ import annotations

import asyncio
import io
import os
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

PASS = 0
FAIL = 0
MEDIDAS: dict = {}

#: ⛔ SINTETICO.
EMPRESA = "empresa-sintetica"
SESSAO = "sessao-sintetica"
CORRETORA = "Corretora Sintetica"
AGENTE = "Aurora"


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


def medir(chave, valor):
    MEDIDAS[chave] = valor
    return valor


# --------------------------------------------------------------------- #
# GD8a — 30 turnos, UMA apresentacao. E o assunto novo traz outra.
# --------------------------------------------------------------------- #

def _entregar(ident, *, resposta=None):
    """Simula o passo 9 do webhook: o `send_message` devolveu True.

    🔴 **É o que J5 acrescentou ao caminho** (14/09/2026). A montagem do
    prompt só anota `apresentacao_pendente_*`; quem promove a
    `apresentado_em` é `confirmar_apresentacao_enviada`, DEPOIS do envio — e
    só se a resposta que saiu realmente carregar a apresentação.

    ⚠️ O guarda chama o MOTOR (`a_resposta_se_apresenta`), nunca uma cópia da
    regra (CLAUDE.md §9.4).
    """
    from app.services import o_fim_do_atendimento as F

    pendente = str((ident or {}).get("apresentacao_pendente_em") or "")
    if not pendente:
        return dict(ident or {})
    nome = str((ident or {}).get("apresentacao_pendente_nome") or "")
    texto = resposta if resposta is not None else (
        "Oi! Aqui é a %s, assistente virtual da %s. Como posso ajudar?"
        % (nome, CORRETORA))
    if not F.a_resposta_se_apresenta(texto, agent_name=nome):
        return dict(ident or {})
    novo = dict(ident)
    novo["apresentado_em"] = pendente
    novo["nome_da_apresentacao"] = nome
    return novo


def _replay(n_turnos, *, agent_name=AGENTE, assunto_novo_no_turno=(),
            turnos_descartados=()):
    """Roda o MOTOR turno a turno, carregando a identidade como o produto faz.

    `turnos_descartados` — os turnos em que a mensagem NÃO saiu (posse
    perdida, atendente assumiu, envio falhou). ⛔ Neles a ficha NÃO pode
    registrar que a apresentação aconteceu.

    Devolve a lista de blocos que o prompt receberia, um por turno.
    """
    from app.services import o_fim_do_atendimento as F

    ident = {"assunto_id": "", "titular_nome": "", "apresentado_em": "",
             "nome_da_apresentacao": ""}
    blocos = []
    for i in range(n_turnos):
        novo = (i == 0) or (i in assunto_novo_no_turno)
        if novo:
            # É o que o `graph` faz: identidade REESCRITA, nunca herdada.
            ident = {"assunto_id": "assunto-%d" % i, "titular_nome": "",
                     "apresentado_em": "", "nome_da_apresentacao": ""}
        bloco, ident = F.bloco_de_quem_fala(
            assunto_novo=novo, identidade=ident,
            agent_name=agent_name if not callable(agent_name) else agent_name(i),
            corretora=CORRETORA, quem_vai_atender=None)
        blocos.append(bloco)
        if i not in turnos_descartados:
            ident = _entregar(ident)
    return blocos


def gd8a_uma_apresentacao_por_assunto():
    _p("\n[GD8a] 30 turnos do encanador -> UMA apresentacao, e ZERO cumprimentos no meio")

    blocos = _replay(30)
    apresenta = [i for i, b in enumerate(blocos) if "apresente-se agora" in b.lower()]
    calados = [i for i, b in enumerate(blocos) if "NÃO se apresente" in b]
    medir("apresentacao.turnos", len(blocos))
    medir("apresentacao.vezes", len(apresenta))
    _p("       📊 %d turnos · apresentou em %s · calado em %d"
       % (len(blocos), apresenta, len(calados)))

    check("apresentou UMA vez, e foi na abertura",
          apresenta == [0],
          "o cumprimento na 30a mensagem de um sinistro com vitima e este "
          "numero diferente de [0]: %s" % apresenta)
    check("os outros 29 turnos mandam NAO se apresentar",
          len(calados) == 29, "calados=%d" % len(calados))

    # PAR — assunto NOVO no turno 17 traz exatamente mais UMA apresentacao.
    blocos2 = _replay(30, assunto_novo_no_turno={17})
    apresenta2 = [i for i, b in enumerate(blocos2) if "apresente-se agora" in b.lower()]
    check("assunto novo no meio -> exatamente UMA apresentacao a mais",
          apresenta2 == [0, 17],
          "o segurado que volta 3 meses depois merece um comeco: %s" % apresenta2)

    # LINHA DE CONTROLE — o motor CONSEGUE mandar se apresentar. Sem isto,
    # um motor que sempre cala passaria em tudo acima.
    from app.services import o_fim_do_atendimento as F

    apresenta_sempre, modo = F.deve_se_apresentar(
        assunto_novo=True, apresentado_neste_assunto=True,
        nome_atual=AGENTE, nome_da_apresentacao="")
    check("CONTROLE: o motor consegue dizer SIM (assunto novo vence tudo)",
          apresenta_sempre and modo == "primeira", "(%s, %r)" % (apresenta_sempre, modo))
    cala, modo_c = F.deve_se_apresentar(
        assunto_novo=False, apresentado_neste_assunto=True,
        nome_atual=AGENTE, nome_da_apresentacao=AGENTE)
    check("e consegue dizer NAO no meio da conversa",
          (not cala) and modo_c == "", "(%s, %r)" % (cala, modo_c))


# --------------------------------------------------------------------- #
# GD8b — o `sempre-se-apresente` morreu no bloco ESTATICO
# --------------------------------------------------------------------- #

def gd8b_o_bloco_estatico_nao_manda_mais_se_apresentar():
    _p("\n[GD8b] O bloco ESTATICO (cacheado) nao manda mais se apresentar")
    from app.core import prompts as P

    fonte = io.open(os.path.join(RAIZ, "app/core/prompts.py"), encoding="utf-8").read()
    ocorrencias = fonte.count("SEMPRE se apresente")
    medir("prompts.sempre_se_apresente", ocorrencias)
    check("`SEMPRE se apresente` tem ZERO ocorrencias no fonte",
          ocorrencias == 0,
          "o bloco estatico vem PRIMEIRO no prompt e vence o dinamico: %d" % ocorrencias)

    # E o MOTOR do prompt: o que sai montado tambem nao manda.
    montado = P.build_composite_prompt(
        "instrucoes da corretora", agent_role="attendance",
        agent_display_name=AGENTE, company_display_name=CORRETORA)
    check("nem o prompt MONTADO manda se apresentar sempre",
          "SEMPRE se apresente" not in montado,
          montado[-600:])
    check("mas o prompt montado continua dizendo QUEM ele e",
          AGENTE in montado and CORRETORA in montado, montado[-600:])
    # ⚠️ A expressão CONTINUA no prompt — como PROIBIÇÃO. O que não pode é a
    #    corretora se chamar assim.
    check("e so cita 'sua corretora' para PROIBIR",
          montado.count("sua corretora") == montado.count('NUNCA diga "da sua corretora"'),
          "ocorrencias=%d proibicoes=%d"
          % (montado.count("sua corretora"),
             montado.count('NUNCA diga "da sua corretora"')))

    # ⛔ Os nomes INVENTADOS de atendente sairam do prompt estatico (§10.3).
    for inventado in ("a Ana", "o Marcos"):
        check("o prompt nao ensina mais o nome inventado %r" % inventado,
              inventado not in montado,
              "um nome que nao existe na corretora e pior que nenhum")


# --------------------------------------------------------------------- #
# GD8c — trocar o nome no meio nao muda o assunto em andamento
# --------------------------------------------------------------------- #

def gd8c_trocar_o_nome_nao_muda_o_assunto_atual():
    _p("\n[GD8c] Trocar o nome do agente no meio -> nada agora, UMA linha no assunto seguinte")
    from app.services import o_fim_do_atendimento as F

    ident = {"assunto_id": "a1", "titular_nome": "", "apresentado_em": "",
             "nome_da_apresentacao": ""}
    _, ident = F.bloco_de_quem_fala(assunto_novo=True, identidade=ident,
                                    agent_name="Aurora", corretora=CORRETORA)
    check("a MONTAGEM so anota a intencao (J5), nunca o fato",
          ident.get("apresentacao_pendente_nome") == "Aurora"
          and not ident.get("apresentado_em"), ident)
    ident = _entregar(ident)          # o `send_message` devolveu True
    check("a apresentacao gravou o nome usado",
          ident["nome_da_apresentacao"] == "Aurora" and ident["apresentado_em"],
          ident)

    # A corretora troca o nome AGORA, no meio do acionamento.
    bloco_meio, ident_meio = F.bloco_de_quem_fala(
        assunto_novo=False, identidade=ident, agent_name="Helena",
        corretora=CORRETORA)
    check("no assunto ATUAL nao acontece nada",
          "NÃO se apresente" in bloco_meio and "Helena" not in bloco_meio,
          "trocar de pessoa no meio de um acionamento e pior que manter o nome "
          "antigo ate o assunto fechar: %s" % bloco_meio)
    check("e a identidade do assunto atual nao e reescrita",
          ident_meio["nome_da_apresentacao"] == "Aurora", ident_meio)

    # No PROXIMO assunto, uma linha — e uma so.
    ident_novo = {"assunto_id": "a2", "titular_nome": "", "apresentado_em": "",
                  "nome_da_apresentacao": ident["nome_da_apresentacao"]}
    bloco_novo, ident2 = F.bloco_de_quem_fala(
        assunto_novo=True, identidade=ident_novo, agent_name="Helena",
        corretora=CORRETORA)
    ident2 = _entregar(ident2, resposta=(
        "Oi! Aqui é a Helena, assistente virtual da %s — antes eu me "
        "apresentava como Aurora." % CORRETORA))
    check("no assunto seguinte ele diz que mudou de nome, UMA vez",
          "mudou de nome" in bloco_novo and "Helena" in bloco_novo
          and "Aurora" in bloco_novo, bloco_novo)
    seguinte, _ = F.bloco_de_quem_fala(assunto_novo=False, identidade=ident2,
                                       agent_name="Helena", corretora=CORRETORA)
    check("e no turno seguinte ja nao diz mais nada",
          "NÃO se apresente" in seguinte, seguinte)


# --------------------------------------------------------------------- #
# GD8d — a classe do tamanho, e a excecao documental
# --------------------------------------------------------------------- #

_CONVERSA_DE_760 = (
    "Entendi perfeitamente a sua situacao e quero te tranquilizar desde ja, "
    "porque esse tipo de ocorrencia e bastante comum e costuma se resolver com "
    "rapidez quando a gente segue o procedimento correto desde o primeiro "
    "momento. O que acontece e que a seguradora precisa registrar o evento "
    "dentro do sistema dela antes de acionar qualquer prestador, e esse "
    "registro depende de algumas informacoes basicas que eu ja estou "
    "levantando aqui do seu cadastro. Assim que isso estiver concluido eu "
    "aciono a assistencia e te informo o protocolo por aqui mesmo, sem que "
    "voce precise ligar para ninguem nem repetir nada do que ja me contou ate "
    "agora, combinado."
)

_LISTA_DOCUMENTAL = "\n".join(
    ["Para abrir o aviso, preciso destes documentos:"]
    + ["%d) documento numero %d" % (i, i) for i in range(1, 21)]
)


def gd8d_a_classe_do_tamanho():
    _p("\n[GD8d] conversa 3 frases · bloco 4 itens · lista documental SEM TETO · delicada sozinha")
    from app.services import o_fim_do_atendimento as F

    classe, unidades, chars = F.classe_do_tamanho(_CONVERSA_DE_760)
    medir("tamanho.conversa_chars", chars)
    _p("       📊 conversa de %d chars, %d frases -> classe %s" % (chars, unidades, classe))
    estourou, _, _, teto = F.fora_da_classe(_CONVERSA_DE_760)
    check("a conversa de ~760 chars e classificada como conversa e ESTOURA",
          classe == F.CLASSE_CONVERSA and estourou and teto == 3,
          "classe=%s estourou=%s teto=%s" % (classe, estourou, teto))

    # 🔴 AS DUAS PERGUNTAS, e cada uma pega o que a outra nao pega.
    #
    # 📊 O textao de 10/09 tinha 3 FRASES: um teto so de frases o deixaria
    # passar inteiro. E um teto so de caracteres deixaria passar cinco frases
    # curtas em sequencia, que e interrogatorio.
    check("o textao de POUCAS frases longas estoura pelo teto de CARACTERES",
          unidades <= 3 and estourou,
          "contar so frase mede pontuacao, nao textao: frases=%s" % unidades)
    cinco_curtas = ("Oi! Recebi aqui. Vou olhar. Um minuto. Ja te falo.")
    fora_5, classe_5, unid_5, _ = F.fora_da_classe(cinco_curtas)
    check("e cinco frases curtas estouram pelo teto de FRASES",
          fora_5 and classe_5 == F.CLASSE_CONVERSA and unid_5 == 5,
          "chars=%d frases=%s estourou=%s" % (len(cinco_curtas), unid_5, fora_5))

    # PAR — a resposta humana mediana (92 chars) passa.
    curta = "Perfeito! Ja estou acionando a assistencia. Te mando o protocolo em instantes."
    fora_curta, classe_curta, _, _ = F.fora_da_classe(curta)
    check("PAR: a resposta curta de verdade passa",
          (not fora_curta) and classe_curta == F.CLASSE_CONVERSA,
          "uma regua que reprova a resposta boa e mordaca: %s" % classe_curta)

    # A EXCECAO DOCUMENTAL — 20 itens, SEM TETO.
    fora_doc, classe_doc, itens_doc, teto_doc = F.fora_da_classe(_LISTA_DOCUMENTAL)
    medir("tamanho.lista_itens", itens_doc)
    check("a lista de 20 documentos NAO estoura (teto 0 = sem teto)",
          (not fora_doc) and classe_doc == F.CLASSE_LISTA_DOCUMENTAL and teto_doc == 0,
          "meia lista e pior que lista nenhuma: classe=%s itens=%s teto=%s"
          % (classe_doc, itens_doc, teto_doc))

    # O BLOCO DE ATE 4 — o formato que o produto ENSINA, em uma linha corrida.
    bloco_ok = ("Pra eu abrir o guincho, me confirma: 1) o endereco com uma "
                "referencia 2) pra onde levar 3) quem estara com o carro 4) um "
                "telefone. Com isso eu abro agora.")
    fora_b, classe_b, itens_b, _ = F.fora_da_classe(bloco_ok)
    check("o bloco de 4 itens em linha corrida e visto como bloco e passa",
          (not fora_b) and classe_b == F.CLASSE_BLOCO and itens_b == 4,
          "classe=%s itens=%s" % (classe_b, itens_b))
    bloco_6 = bloco_ok.replace("Com isso eu abro agora.",
                               "5) a cor do carro 6) o ano.")
    fora_6, _, itens_6, _ = F.fora_da_classe(bloco_6)
    check("com 6 itens ele estoura (acima de 4 vira formulario)",
          fora_6 and itens_6 == 6, "itens=%s estourou=%s" % (itens_6, fora_6))

    # A PERGUNTA DELICADA vai SOZINHA.
    delicada_sozinha = "Alguem se feriu?"
    delicada_em_bloco = ("Que susto! Me diz o endereco, por favor. Alguem se "
                         "feriu? E ja me manda uma foto do carro.")
    fora_d1, classe_d1, _, teto_d1 = F.fora_da_classe(delicada_sozinha)
    fora_d2, classe_d2, unid_d2, _ = F.fora_da_classe(delicada_em_bloco)
    check("a pergunta delicada sozinha passa",
          (not fora_d1) and classe_d1 == F.CLASSE_AVISAR and teto_d1 == 1,
          "classe=%s teto=%s" % (classe_d1, teto_d1))
    check("a mesma pergunta enfiada no meio de outras coisas ESTOURA",
          fora_d2 and classe_d2 == F.CLASSE_AVISAR,
          "vitima nunca entra em bloco: classe=%s unidades=%s" % (classe_d2, unid_d2))


# --------------------------------------------------------------------- #
# GD8e — em producao: UMA regeneracao, e depois ENVIA e REGISTRA
# --------------------------------------------------------------------- #

class _ModeloQueInsiste:
    """Duble do LLM. Responde `textos[i]` na i-esima chamada, repetindo o ultimo."""

    def __init__(self, textos):
        self.textos = list(textos)
        self.chamadas = []

    async def ainvoke(self, mensagens, config=None):
        from langchain_core.messages import AIMessage

        self.chamadas.append(mensagens)
        i = min(len(self.chamadas) - 1, len(self.textos) - 1)
        return AIMessage(content=self.textos[i])


def _rodar_turno(textos):
    """O `agent_node` REAL, com ficha vazia (nada a repergunta) e modelo duble."""
    import app.services.activity_log as AL
    from langchain_core.messages import HumanMessage

    from app.agents import nodes as N
    from app.services.attendance_ficha import ficha_vazia

    feed: list = []

    async def _log(company_id, category, title, detail=""):
        feed.append({"company_id": company_id, "category": category,
                     "title": title, "detail": detail})

    modelo = _ModeloQueInsiste(textos)
    estado = {
        "messages": [HumanMessage(content="bom dia")],
        "company_id": EMPRESA, "session_id": SESSAO, "user_id": "u",
        "company_config": {}, "agent_data": {"agent_role": "attendance"},
        "system_prompt": "prompt sintetico", "static_prompt": "prompt sintetico",
        "dynamic_context": "", "ficha_atendimento": ficha_vazia(),
    }
    _log_real = AL.log_activity
    AL.log_activity = _log
    try:
        saida = asyncio.run(N.agent_node(estado, None, modelo))
    finally:
        AL.log_activity = _log_real
    texto = ""
    for m in saida.get("messages") or []:
        texto = getattr(m, "content", "") or texto
    return modelo, texto, feed


def gd8e_uma_regeneracao_e_depois_envia():
    _p("\n[GD8e] A resposta fora da classe provoca UMA regeneracao — e depois SAI")
    boa = "Perfeito! Ja estou acionando a assistencia. Te aviso o protocolo."

    # (1) o modelo insiste no textao -> uma regeneracao, e a resposta SAI.
    modelo, texto, feed = _rodar_turno([_CONVERSA_DE_760, _CONVERSA_DE_760])
    check("o textao provocou UMA regeneracao",
          len(modelo.chamadas) == 2,
          "chamadas ao modelo: %d (o fiscal do tamanho nao existe)"
          % len(modelo.chamadas))
    ultima = " ".join(str(getattr(m, "content", ""))
                      for m in (modelo.chamadas[-1] if len(modelo.chamadas) > 1 else []))
    check("a segunda chamada levou a REGUA explicita",
          "3 frases" in ultima or "MÁXIMO 3" in ultima,
          "regenerar sem dizer o que estourou e torcer para adivinhar: %r"
          % ultima[-400:])
    check("insistiu, mas a resposta SAI assim mesmo",
          texto.strip() == _CONVERSA_DE_760.strip(),
          "travar a mensagem do segurado para proteger estilo troca um defeito "
          "silencioso por um barulhento (CLAUDE.md §9.5): saiu %r" % texto[:120])
    linhas = [f for f in feed if "tamanho_fora_da_classe" in str(f)]
    check("e o feed registra `tamanho_fora_da_classe`", bool(linhas), "feed: %s" % feed)
    check("o registro fica na corretora certa",
          bool(linhas) and linhas[0].get("company_id") == EMPRESA, "feed: %s" % feed)

    # (2) PAR — o modelo se corrige: a boa sai, e nada e registrado.
    modelo2, texto2, feed2 = _rodar_turno([_CONVERSA_DE_760, boa])
    check("quando a regeneracao conserta, a resposta boa e que sai",
          texto2.strip() == boa.strip(), "saiu %r" % texto2[:120])
    check("e nada vira defeito no feed", not feed2, "feed: %s" % feed2)

    # (3) PAR — a lista documental NAO paga regeneracao nenhuma.
    modelo3, texto3, feed3 = _rodar_turno([_LISTA_DOCUMENTAL])
    check("a lista de 20 documentos passa direto, sem regeneracao e sem feed",
          len(modelo3.chamadas) == 1 and not feed3
          and texto3.strip() == _LISTA_DOCUMENTAL.strip(),
          "chamadas=%d feed=%s" % (len(modelo3.chamadas), feed3))


# --------------------------------------------------------------------- #
# GD8f — a identidade da thread e REESCRITA no assunto novo
# --------------------------------------------------------------------- #

def gd8f_a_identidade_e_reescrita():
    _p("\n[GD8f] Assunto novo -> identidade REESCRITA, e o nome de 22 dias atras NAO volta")
    import app.services.attendance_ficha as A

    velha = A.fundir(A.ficha_vazia(), {
        "ramo": "auto", "servico": "guincho",
        "identidade": {"assunto_id": "assunto-de-22-dias-atras"},
        "confirmados": {
            "titular_nome": {"valor": "Fulano Sintetico De Antes",
                             "origem": A.ORIGEM_CLIENTE,
                             "em": "2026-08-23T12:00:00+00:00"},
            "placa": {"valor": "ABC1D23", "origem": A.ORIGEM_SISTEMA_DE_GESTAO,
                      "em": "2026-08-23T12:00:00+00:00"},
        },
    }, [])
    check("CONTROLE: antes do assunto novo o nome ESTA na ficha e na identidade",
          A.titular_do_prompt(velha) == "Fulano Sintetico De Antes"
          and "titular_nome" in velha["confirmados"],
          "sem este controle, 'o nome sumiu' passaria por conserto: %s"
          % velha.get("identidade"))
    bloco_antes = A.bloco_para_o_prompt(velha, [])
    check("e ele aparece no bloco do prompt",
          "Fulano Sintetico De Antes" in bloco_antes, bloco_antes[:300])

    # O assunto novo chega (o motor do reencontro e quem sabe).
    nova = A.fundir(velha, {"identidade": {"assunto_id": "assunto-de-hoje"}}, [])
    check("a identidade foi REESCRITA, nunca herdada",
          A.identidade_de(nova)["assunto_id"] == "assunto-de-hoje"
          and A.titular_do_prompt(nova) == "", A.identidade_de(nova))
    check("o nome de 22 dias atras saiu da ficha",
          "titular_nome" not in (nova.get("confirmados") or {}),
          "confirmados: %s" % list((nova.get("confirmados") or {}).keys()))
    bloco_depois = A.bloco_para_o_prompt(nova, [])
    check("e NAO volta pelo bloco do prompt",
          "Fulano Sintetico De Antes" not in bloco_depois, bloco_depois[:400])

    # ⚠️ O QUE NAO E DO ASSUNTO FICA. A placa e do contrato, nao do caso.
    check("a placa continua — ela e do contrato, nao do assunto",
          "placa" in (nova.get("confirmados") or {}),
          "apagar tudo seria trocar um defeito por outro")

    # PAR — o MESMO assunto nao apaga nada.
    mesmo = A.fundir(velha, {"identidade": {"assunto_id": "assunto-de-22-dias-atras",
                                            "apresentado_em": "2026-08-23T12:00:00+00:00"}},
                     [])
    check("PAR: no MESMO assunto a identidade so se completa, e o nome fica",
          A.titular_do_prompt(mesmo) == "Fulano Sintetico De Antes"
          and A.identidade_de(mesmo)["apresentado_em"], A.identidade_de(mesmo))

    # O nome do segurado entra no prompt SO da identidade deste assunto.
    from app.services import o_fim_do_atendimento as F

    bloco_com, _ = F.bloco_de_quem_fala(
        assunto_novo=False, identidade=A.identidade_de(mesmo),
        agent_name=AGENTE, corretora=CORRETORA)
    bloco_sem, _ = F.bloco_de_quem_fala(
        assunto_novo=True, identidade=A.identidade_de(nova),
        agent_name=AGENTE, corretora=CORRETORA)
    check("com identidade, o prompt diz como chamar o segurado",
          "Fulano Sintetico De Antes" in bloco_com, bloco_com)
    check("sem identidade, o prompt PROIBE usar nome de memoria/historico",
          "não sabe o nome" in bloco_sem.lower()
          and "Fulano" not in bloco_sem, bloco_sem)


def gd8g_turno_descartado_ainda_se_apresenta():
    _p("\n[GD8g] Turno DESCARTADO -> o proximo AINDA se apresenta (J5)")
    from app.services import o_fim_do_atendimento as F

    # 📊 O defeito medido em 14/09/2026: `graph.py` gravava
    #    `identidade.apresentado_em` na MONTAGEM do prompt. Bastava montar. Se
    #    o turno fosse descartado depois (posse perdida, atendente assumiu,
    #    envio falhou), o segurado NUNCA ouvia a apresentacao e a ficha ja
    #    dizia que ela tinha acontecido: "uma vez" virava "nunca".
    blocos = _replay(3, turnos_descartados={0})
    apresenta = [i for i, b in enumerate(blocos) if "apresente-se agora" in b.lower()]
    check("\U0001F534 o turno 0 foi descartado -> o turno 1 AINDA se apresenta",
          apresenta[:2] == [0, 1],
          "a apresentacao que nao saiu nao pode contar como feita: %s" % apresenta)
    check("e depois que ela SAI, o turno 2 ja cala",
          len(apresenta) == 2, apresenta)

    # PAR / CONTROLE: com o turno 0 entregue, so ha UMA apresentacao.
    entregues = _replay(3)
    apresenta2 = [i for i, b in enumerate(entregues) if "apresente-se agora" in b.lower()]
    check("CONTROLE: entregue, apresenta UMA vez so", apresenta2 == [0], apresenta2)
    check("e as duas medidas CONSEGUEM ser diferentes (CLAUDE.md §9.2)",
          apresenta != apresenta2, (apresenta, apresenta2))

    # ⛔ E a promocao exige que o TEXTO ENVIADO carregue a apresentacao: se o
    #    modelo ignorou a instrucao, marcar seria mentir para o turno seguinte.
    ident = {"assunto_id": "a1", "titular_nome": "", "apresentado_em": "",
             "nome_da_apresentacao": ""}
    _, ident = F.bloco_de_quem_fala(assunto_novo=True, identidade=ident,
                                    agent_name=AGENTE, corretora=CORRETORA)
    mudo = _entregar(ident, resposta="Certo, me manda o endereco por favor.")
    check("resposta que NAO se apresenta nao marca a ficha",
          not mudo.get("apresentado_em"), mudo)
    certo = _entregar(ident)
    check("PAR: a que se apresenta marca", bool(certo.get("apresentado_em")), certo)


def gd8h_a_apresentacao_nao_repete_a_corretora():
    _p("\n[GD8h] Nome que JA diz a corretora -> a corretora aparece UMA vez")
    from app.services import o_fim_do_atendimento as F

    # 📊 O `display_name` do blueprint e "AutoBrokers da {corretora}" — e a
    #    linha saia "Aqui e a AutoBrokers da Resulta, assistente virtual da
    #    Resulta" (achado do juiz, 14/09/2026).
    linha = F.linha_da_apresentacao(F.MODO_PRIMEIRA,
                                    agent_name="AutoBrokers da Corretora Sintetica",
                                    corretora="Corretora Sintetica")
    check("o nome da corretora aparece UMA vez", linha.count("Corretora Sintetica") == 1,
          linha)
    check("e a frase continua dizendo o que ele e",
          "assistente virtual" in linha, linha)

    # PAR: nome que NAO carrega a corretora continua ganhando o "da {corretora}".
    outra = F.linha_da_apresentacao(F.MODO_PRIMEIRA, agent_name="Aurora",
                                    corretora="Corretora Sintetica")
    check("PAR: nome comum mantem 'assistente virtual da {corretora}'",
          "assistente virtual da Corretora Sintetica" in outra, outra)
    check("e as duas CONSEGUEM ser diferentes", linha != outra)


def gd8i_uma_regeneracao_por_TURNO_e_os_metadados_ficam():
    _p("\n[GD8i] UMA regeneracao por TURNO entre os fiscais, e os metadados sobrevivem")
    from langchain_core.messages import AIMessage

    from app.agents import nodes as N
    import app.services.activity_log as AL

    # ------------------------------------------------------------------ #
    # (1) o teto: se o fiscal de cima JA regenerou, o do tamanho NAO regenera
    # ------------------------------------------------------------------ #
    # \U0001F4CA O defeito medido em 14/09/2026 (J8): os dois fiscais regeneravam em
    #    sequencia — DUAS chamadas extras ao modelo num turno so, dobrando a
    #    espera do segurado, e a segunda reescrita nao sabe nada sobre a
    #    pergunta repetida que a primeira acabou de consertar.
    feed = []

    async def _log(company_id, category, title, detail=""):
        feed.append({"company_id": company_id, "title": title})

    estado = {"company_id": EMPRESA, "agent_data": {"agent_role": "attendance"}}
    chamadas = []

    async def _regenerar(_regua):
        chamadas.append(_regua)
        return "curtinha."

    _log_real = AL.log_activity
    AL.log_activity = _log
    try:
        # com `ja_regenerou=True` o motor NAO pode chamar `regenerar`
        texto, classe = asyncio.run(N._resposta_no_tamanho_da_classe(
            _CONVERSA_DE_760, estado, regenerar=_regenerar, ja_regenerou=True))
        check("\U0001F534 o turno ja gastou a sua regeneracao: o 2o fiscal NAO chama o modelo",
              chamadas == [], "chamou %d vez(es)" % len(chamadas))
        check("a mensagem SAI assim mesmo (nunca travar o segurado)",
              texto.strip() == _CONVERSA_DE_760.strip(), texto[:80])
        check("e o defeito vai para o feed", any(
            "tamanho_fora_da_classe" in str(f.get("title")) for f in feed), feed)
        check("a classe que estourou e devolvida", bool(classe), classe)

        # CONTROLE: sem regeneracao anterior, o mesmo motor REGENERA
        feed2 = []

        async def _log2(company_id, category, title, detail=""):
            feed2.append(title)

        AL.log_activity = _log2
        chamadas2 = []

        async def _regenerar2(_regua):
            chamadas2.append(_regua)
            return "curtinha."

        texto2, classe2 = asyncio.run(N._resposta_no_tamanho_da_classe(
            _CONVERSA_DE_760, estado, regenerar=_regenerar2, ja_regenerou=False))
        check("CONTROLE: sem regeneracao anterior, ele REGENERA",
              len(chamadas2) == 1, "chamou %d" % len(chamadas2))
        check("e as duas medidas CONSEGUEM ser diferentes (CLAUDE.md \u00a79.2)",
              len(chamadas) != len(chamadas2))
        check("a resposta curta e que sai", texto2.strip() == "curtinha.", texto2)
    finally:
        AL.log_activity = _log_real

    # ------------------------------------------------------------------ #
    # (2) os METADADOS nao se perdem na substituicao
    # ------------------------------------------------------------------ #
    # \U0001F4CA Cada fiscal fazia `AIMessage(content=...)` cru: `response_metadata`,
    #    `usage_metadata` e o `id` sumiam, e o turno regenerado ficava sem
    #    custo e sem modelo na telemetria.
    original = AIMessage(content="texto original",
                         response_metadata={"model_name": "modelo-sintetico"},
                         usage_metadata={"input_tokens": 11, "output_tokens": 22,
                                         "total_tokens": 33},
                         id="run-sintetico-1")
    nova = N.mesma_mensagem_com_texto(original, "texto novo")
    check("o texto e o novo", nova.content == "texto novo", nova.content)
    check("\U0001F534 `response_metadata` sobrevive",
          nova.response_metadata == original.response_metadata, nova.response_metadata)
    check("`usage_metadata` sobrevive (e dele que sai o custo)",
          nova.usage_metadata == original.usage_metadata, nova.usage_metadata)
    check("e o `id` do rastro tambem", nova.id == original.id, nova.id)

    # \u26d4 E nenhum fiscal do `agent_node` pode voltar a construir a mensagem crua.
    fonte = io.open(os.path.join(RAIZ, "app", "agents", "nodes.py"),
                    encoding="utf-8").read()
    cruas = fonte.count("response = AIMessage(content=")
    check("nenhum fiscal substitui a resposta por uma AIMessage CRUA",
          cruas == 0, "%d sobrevivente(s) — sobrevivente = metadados perdidos" % cruas)


def gd8j_desculpa_nao_e_culpa():
    _p("\n[GD8j] A pergunta DELICADA casa por PALAVRA e na MESMA frase (J3)")
    from app.services import o_fim_do_atendimento as F

    # \U0001F4CA Os dois defeitos medidos em 14/09/2026: `"desculpa"` contem
    #    `"culpa"`, e o acolhimento de uma frase virava `avisar` por causa da
    #    pergunta de OUTRA frase. `avisar` tem o teto mais apertado do produto
    #    (1 frase, 300 chars): casar por engano REGENERA uma resposta correta.
    for texto in ("Desculpa a demora! Pode me dizer o endereco?",
                  "Que bom que ninguem se feriu. Pode me dizer onde voce esta?",
                  "Que bom que ningu\u00e9m se feriu. Pode me dizer onde voc\u00ea est\u00e1?"):
        classe, _u, _c = F.classe_do_tamanho(texto)
        check("%-46s -> conversa" % (texto[:44] + ".."),
              classe == F.CLASSE_CONVERSA, "deu %s" % classe)

    # PAR — a pergunta delicada de verdade CONTINUA sendo `avisar`.
    for texto in ("Alguem se feriu?", "Algu\u00e9m se feriu?",
                  "Houve alguma vitima no acidente?",
                  "A culpa foi atribuida a quem?"):
        classe, _u, _c = F.classe_do_tamanho(texto)
        check("PAR: %-40s -> avisar" % (texto[:38] + ".."),
              classe == F.CLASSE_AVISAR, "deu %s" % classe)

    check("e as duas medidas CONSEGUEM ser diferentes (CLAUDE.md \u00a79.2)",
          F.classe_do_tamanho("Desculpa a demora! Pode me dizer o endereco?")[0]
          != F.classe_do_tamanho("Alguem se feriu?")[0])
    check("sem `?` nenhuma palavra delicada muda a classe",
          F.classe_do_tamanho("Nao houve vitima nenhuma.")[0] == F.CLASSE_CONVERSA)


GATES = {
    "GD8a": gd8a_uma_apresentacao_por_assunto,
    "GD8i": gd8i_uma_regeneracao_por_TURNO_e_os_metadados_ficam,
    "GD8j": gd8j_desculpa_nao_e_culpa,
    "GD8g": gd8g_turno_descartado_ainda_se_apresenta,
    "GD8h": gd8h_a_apresentacao_nao_repete_a_corretora,
    "GD8b": gd8b_o_bloco_estatico_nao_manda_mais_se_apresentar,
    "GD8c": gd8c_trocar_o_nome_nao_muda_o_assunto_atual,
    "GD8d": gd8d_a_classe_do_tamanho,
    "GD8e": gd8e_uma_regeneracao_e_depois_envia,
    "GD8f": gd8f_a_identidade_e_reescrita,
}

MUTACOES = [
    # (a) o `sempre-se-apresente` volta ao bloco ESTATICO — o defeito de 09/09.
    ("M-D8a", "app/core/prompts.py",
     '- NUNCA diga "da sua corretora" — diga o NOME da corretora.',
     '- SEMPRE se apresente com nome E corretora na primeira mensagem.\n'
     '- NUNCA diga "da sua corretora" — diga o NOME da corretora.',
     "GD8b"),
    # (b) `deve_se_apresentar` sempre True — o cumprimento na 30a mensagem.
    ("M-D8b", "app/services/o_fim_do_atendimento.py",
     "    ja = bool(apresentado_neste_assunto) and not novo",
     "    ja = False",
     "GD8a"),
    # (c) a identidade e HERDADA no assunto novo — o nome de 22 dias atras volta.
    ("M-D8c", "app/services/attendance_ficha.py",
     '        if depois.get("assunto_id") and depois["assunto_id"] != antes.get("assunto_id"):',
     '        if False:',
     "GD8f"),
    # (d) o teto de FRASES da conversa vira 99 — as cinco curtas passam.
    ("M-D8d", "app/services/o_fim_do_atendimento.py",
     "    CLASSE_CONVERSA: 3,\n    CLASSE_BLOCO: 4,",
     "    CLASSE_CONVERSA: 99,\n    CLASSE_BLOCO: 4,",
     "GD8d"),
    # (d2) o teto de CARACTERES some — o textao de 3 frases volta a passar.
    ("M-D8d2", "app/services/o_fim_do_atendimento.py",
     "    CLASSE_CONVERSA: 450,",
     "    CLASSE_CONVERSA: 0,",
     "GD8d"),
    # (h) 🔴 J8 de volta: o 2o fiscal regenera mesmo depois do 1o
    ("M-D8h", "app/agents/nodes.py",
     "    if ja_regenerou:",
     "    if False:",
     "GD8i"),
    # (i) 🔴 J3 de volta: a palavra delicada volta a casar por SUBSTRING
    ("M-D8i", "app/services/o_fim_do_atendimento.py",
     "    delicada = pergunta_delicada(texto)",
     '    delicada = "?" in texto and any(p in baixo for p in _PALAVRAS_DELICADAS)',
     "GD8j"),
    # (f) 🔴 J5 de volta: a MONTAGEM marca a apresentacao como feita
    ("M-D8f", "app/services/o_fim_do_atendimento.py",
     '                       marcar_apresentacao: bool = False)',
     '                       marcar_apresentacao: bool = True)',
     "GD8g"),
    # (g) 🔴 a linha volta a repetir o nome da corretora
    ("M-D8g", "app/services/o_fim_do_atendimento.py",
     "    if nome and _nome_ja_diz_a_corretora(nome, corretora):",
     "    if False:",
     "GD8h"),
    # (e) o fiscal do tamanho nao regenera — o textao sai na primeira.
    ("M-D8e", "app/agents/nodes.py",
     "    estourou, classe, unidades, teto = fora_da_classe(texto or \"\")\n    if not estourou:",
     "    estourou, classe, unidades, teto = fora_da_classe(texto or \"\")\n    if estourou or not estourou:",
     "GD8e"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate, "--medir"],
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0012d8").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    calado = "--medir" in args
    if not calado:
        _p("=" * 78)
        _p("  G8 -- O AGENTE SE APRESENTA UMA VEZ  (SPEC-EXTRA-001.2 BLOCO DF)")
        _p("=" * 78)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-700:]))

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_o_agente_se_apresenta_uma_vez():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
