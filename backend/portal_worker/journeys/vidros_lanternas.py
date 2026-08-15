"""Journey do portal de vidros/lanternas (SPEC-020 P2) — abraseuatendimento.com.br.

Mapeado AO VIVO (2026-07-06) com apólice de teste. O portal e PUBLICO (sem login).
Fluxo do acionamento (igual/quase-igual entre seguradoras — Yelum, Tokio, Porto):
  0. #/  -> #seguradora-input (digita) -> botao Avancar
  1. #/<insurer>/menu-atendimento -> "Iniciar atendimento"
  2. #/<insurer>/passo1 -> #inserir-cpf-input + #input_1(placa) + #input_3(data,
     datepicker Material) -> "Iniciar atendimento" -> modal "Dados da apolice"
     -> "Confirmar"
  3. #/<insurer>/passo2/<uuid> -> "Sua relacao com o titular?" (=Corretor),
     #email-segurado-input, nome/CPF-CNPJ solicitante, #telefone-input,
     "Tipo de telefone" -> Avancar
  4. #/<insurer>/passo3 -> "Qual foi a peca danificada?", "Como ocorreu o dano?",
     "Onde ocorreu o dano?" (dropdowns que VARIAM por peca/seguradora) + descricao
     (min 30 chars) -> Avancar
  5. local do servico: estado + cidade + CEP(opcional) -> Avancar
  6. 80% "Confirme a peca danificada": perguntas ESPECIFICAS que variam
     (pelicula, dianteira/traseira, lado; ou posicao do trincado, >10cm, versao).
     -> Avancar aqui CONFIRMA o pedido. So com confirm=True.
  7. escolha da loja/servico a domicilio -> confirmar -> PROTOCOLO.

📊 CONFERIDO contra producao em 03/08/2026 (Supabase dcajcvlzcjbmyapmklil, 39
portal_jobs de 06 a 10/07/2026). Os 8 passos continuam valendo; os nomes reais
dos campos, vistos nos jobs, sao:
  passo2  segr (relacao) · email-segurado-input · nome-solicitante-input ·
          cpf-cnpj-solicitante-input · telefone-input · TipoTelefoneSolicitante0
  passo3  qualItemDanificado · comoOcorreuDanoVeiculo · ondeOcorreuDano ·
          descrever-acontecimento-textarea
  local   estado e cidade sao md-autocomplete (o estado exige a SIGLA: 'SC')
  80%     "Confirme a peca danificada" + "O vidro danificado tem pelicula de
          controle solar (insulfilm)?" — SIM / NAO / Nao sabe
O passo 7 (loja/protocolo) NUNCA foi alcancado: em 39 acionamentos, zero
protocolos capturados (has_protocol jamais retornou True).

📊 E quando ele for alcancado, o reconhecimento estava QUEBRADO — medido em
04/08/2026 contra o texto literal do mapa: `has_protocol("Nº do atendimento:
22842291")` devolvia False, e `interpret_atendimento` devolvia "parou em
passo5" para a tela que prova que o pedido foi aberto. A causa e uma letra
('º' vira 'o' no NFKD; '°' some no ascii-ignore) e esta escrita por extenso na
secao DO PROTOCOLO, abaixo. Zero protocolos capturados nao era so falta de
oportunidade: era tambem um olho fechado.

DESIGN "cerebro unico": o AGENTE (Smith) DECIDE as escolhas (peca/como/onde/
especificos) a partir da conversa com o segurado; a journey CASA a escolha com a
opcao real do dropdown. Sem match confiante -> needs_human COM as opcoes
disponiveis (o agente/humano decide; a journey nunca escolhe errado nem trava).

Sao DOIS vocabularios puros, porque o portal faz DUAS perguntas diferentes:
  explicar_match       PECA — 'vidro da porta' x 'VIDRO DE PORTA' (passo 4)
  explicar_especifico  ATRIBUTO da peca — lado, dianteira/traseira, pelicula,
                       tamanho e posicao do trincado (passo 6, os 80%)
Um vocabulario NAO e um segundo placar: cada um sabe dizer quando a lista NAO e
dele (explicar_especifico devolve dominio='nenhum'), entao continua havendo um
so lugar que decide cada pergunta. O que nao pode voltar a existir e o que ja
existiu: um segundo placar escrito em JS dentro do adaptive.py, decidindo a
MESMA pergunta diferente do que os testes provavam.

A TRAVA: o passo 6 e o que ABRE o pedido. run_adaptive para nele com
confirm=False (is_confirm_screen) e tambem recusa o 'done' do cerebro sem
confirm. Nao afrouxar: 📊 o unico job 'done' de producao foi criado
03:51:55Z de 07/07, quatro minutos ANTES de a trava existir (commit 7d31490,
03:56:10Z), com confirm=false e sem protocolo nenhum.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from portal_worker.journeys import JourneyResult

VIDROS_BASE = "https://abraseuatendimento.com.br/#/"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


# ---------------------------------------------------------------------------
# VOCABULARIO DE PECAS — portugues do Brasil (como o segurado FALA) x como o
# portal ESCREVE. Cada chave e uma IDENTIDADE de peca. Duas identidades
# diferentes NUNCA sao a mesma peca: e essa regra que impede 'vidro da porta'
# de virar 'VIDRO PARABRISA - CARGA'.
#
# 📊 medido em 03/08/2026 (Supabase dcajcvlzcjbmyapmklil, portal_jobs):
#     qualItemDanificado   'vidro da porta'   -> VIDRO PARABRISA - CARGA   3x
#     comoOcorreuDanoVeiculo 'deixei o carro estacionado...' -> CHOQUE TERMICO 3x
# Nos dois casos a opcao CERTA nao existia na lista daquela seguradora, e um
# unico token generico ('vidro') bastou para o casamento errado.
# ---------------------------------------------------------------------------
_PECAS = {
    "parabrisa":  ("parabrisa", "windshield"),
    "lateral":    ("porta", "janela", "lateral", "basculante", "ventarola", "quebra-vento"),
    "vigia":      ("vigia",),
    "retrovisor": ("retrovisor", "espelho"),
    "farol":      ("farol", "farolete", "farolim"),
    "lanterna":   ("lanterna",),
    "teto":       ("teto", "panoramico"),
}
# 'luz' nao identifica peca: pode ser farol OU lanterna. Fica AMBIGUO de
# proposito — se o portal oferecer os dois, a funcao para em vez de escolher.
_AMBIGUOS = {"luz": ("farol", "lanterna"), "lampada": ("farol", "lanterna"),
             "farois": ("farol",), "luzes": ("farol", "lanterna")}
# Modificador de POSICAO: so vira identidade quando nao ha substantivo de peca
# ('vidro dianteiro' = parabrisa; mas 'porta dianteira' continua sendo LATERAL).
_POSICAO = {"dianteiro": "parabrisa", "dianteira": "parabrisa", "frontal": "parabrisa",
            "frente": "parabrisa", "traseiro": "vigia", "traseira": "vigia"}
# Expressoes de varias palavras, resolvidas ANTES de separar em tokens.
_EXPRESSOES = (
    ("para brisa", "parabrisa"), ("para-brisa", "parabrisa"), ("parabrisas", "parabrisa"),
    ("vidro dianteiro", "parabrisa"), ("vidro da frente", "parabrisa"),
    ("vidro frontal", "parabrisa"), ("vidro traseiro", "vidro vigia"),
    ("vidro de tras", "vidro vigia"), ("oculo traseiro", "vidro vigia"),
    ("oculos traseiro", "vidro vigia"), ("espelho retrovisor", "retrovisor"),
)
_STOP = {"de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "um", "uma",
         "no", "na", "em", "para", "por", "com", "meu", "minha", "the"}
# Substantivo de CATEGORIA: nomeia o balcao, nao a peca. Num portal de vidros
# 'vidro' esta em quase toda opcao — nao distingue nem desqualifica nada.
_CATEGORIA = {"vidro", "peca", "item", "veiculo", "carro", "auto", "automovel"}

# Confianca minima e distancia minima para o 2o colocado. Abaixo disso a
# funcao devolve None: parar e o comportamento correto (o agente/humano ve as
# opcoes e decide). NUNCA "chutar o mais proximo".
_CONFIANCA_MINIMA = 1.0
_MARGEM_MINIMA = 0.5


def _singular(t: str) -> str:
    """Plural do portugues -> singular (lanternas->lanterna, retrovisores->
    retrovisor, farois->farol, laterais->lateral)."""
    for fim, troca in (("oes", "ao"), ("ais", "al"), ("eis", "el"), ("ois", "ol"),
                       ("res", "r"), ("ns", "m")):
        if t.endswith(fim) and len(t) > len(fim) + 1:
            return t[: -len(fim)] + troca
    return t[:-1] if t.endswith("s") and len(t) > 3 else t


def _tokens(s: str) -> List[str]:
    """Texto -> tokens comparaveis: sem acento, sem pontuacao, sem plural, sem
    palavra vazia. A ORDEM nao importa (conjunto), entao 'porta do vidro' e
    'vidro da porta' dao o mesmo resultado."""
    t = _norm(s)
    for de, para in _EXPRESSOES:
        t = t.replace(de, para)
    limpo = "".join(c if c.isalnum() else " " for c in t)
    return [_singular(x) for x in limpo.split() if x and x not in _STOP]


def identidade_peca(texto: str) -> set:
    """PURO: quais IDENTIDADES de peca o texto nomeia. Vazio = o texto nao fala
    de peca (ex.: uma causa de dano) — ai o casamento cai so nas palavras."""
    toks = set(_tokens(texto))
    achados = {nome for nome, sin in _PECAS.items()
               if any(_singular(_norm(s)) in toks for s in sin)}
    for t in toks:                      # 'luz' pode ser farol OU lanterna
        if t in _AMBIGUOS:
            achados.update(_AMBIGUOS[t])
    if not achados:                     # so entao a posicao vira identidade
        for t in toks:
            if t in _POSICAO:
                achados.add(_POSICAO[t])
    return achados


def explicar_match(wanted: str, options: List[str]) -> Dict[str, Any]:
    """PURO: decide E explica. {'escolha', 'motivo', 'placar', 'opcoes'}.
    'escolha' None = ninguem casou com confianca -> quem chamou PARA e mostra
    'opcoes' para o agente/humano decidir. Testavel offline."""
    reais = [o for o in (options or []) if str(o).strip() and "selecione" not in _norm(o)]
    vazio = {"escolha": None, "motivo": "sem_opcoes", "placar": [], "opcoes": reais}
    if not str(wanted or "").strip() or not reais:
        return vazio

    alvo = _norm(wanted)
    for o in reais:                                     # 1) igualdade literal
        if _norm(o) == alvo:
            return {"escolha": o, "motivo": "exato", "placar": [(o, 999.0)], "opcoes": reais}

    tw, cw = set(_tokens(wanted)), identidade_peca(wanted)
    if not tw:
        return {**vazio, "motivo": "pedido_vazio"}

    # 2) Peso por raridade: um token que aparece em TODA opcao ('vidro' num
    # portal de vidros) nao distingue nada — foi ele que casou 'vidro da porta'
    # com 'VIDRO PARABRISA - CARGA'. Palavra rara vale; palavra comum, quase nada.
    tokens_por_opcao = {o: set(_tokens(o)) for o in reais}
    def peso(t: str) -> float:
        if len(reais) < 3:
            return 1.0
        freq = sum(1 for s in tokens_por_opcao.values() if t in s) / len(reais)
        return 0.0 if freq >= 1.0 else (0.25 if freq > 0.6 else 1.0)

    placar = []
    for o in reais:
        to, co = tokens_por_opcao[o], identidade_peca(o)
        # 3) VETO: pedido e opcao nomeiam PECAS DIFERENTES -> nunca casa.
        if cw and co and not (cw & co):
            continue
        nota = sum(peso(t) for t in tw if t in to)
        if cw & co:
            nota += 1.0
        if tw <= to:            # a opcao e o pedido, mais especifico
            nota += 1.0
        # Qualificador extra na opcao ('- CARGA', 'BLINDADO') pede cautela. Nao
        # conta como extra: o substantivo da CATEGORIA ('vidro' num portal de
        # vidros) nem a palavra que nomeia a MESMA peca que o pedido — sao
        # sinonimos, nao ressalvas ('janela' x 'VIDRO DE PORTA').
        extras = [t for t in to if t not in tw and peso(t) > 0.5
                  and t not in _CATEGORIA and t not in _POSICAO and t not in _AMBIGUOS
                  and not (identidade_peca(t) & cw)]
        nota -= min(0.5, 0.25 * len(extras))
        placar.append((o, round(nota, 3)))

    placar.sort(key=lambda x: -x[1])
    if not placar:
        return {**vazio, "motivo": "peca_diferente"}
    melhor, nota = placar[0]
    segunda = placar[1][1] if len(placar) > 1 else 0.0
    # Sobrou UMA opcao da peca pedida e nenhuma concorrente: nao ha o que
    # confundir. E o caso de 'espelho' quando o portal so oferece um retrovisor.
    if len(placar) == 1 and cw and (cw & identidade_peca(melhor)) and nota >= 0.5:
        return {"escolha": melhor, "motivo": "unica_da_peca", "placar": placar, "opcoes": reais}
    if nota < _CONFIANCA_MINIMA:
        return {"escolha": None, "motivo": "confianca_baixa", "placar": placar, "opcoes": reais}
    if nota - segunda < _MARGEM_MINIMA:
        return {"escolha": None, "motivo": "ambiguo", "placar": placar, "opcoes": reais}
    return {"escolha": melhor, "motivo": "confiante", "placar": placar, "opcoes": reais}


def match_option(wanted: str, options: List[str]) -> Optional[str]:
    """PURO: a opcao do dropdown que casa com 'wanted' COM CONFIANCA. None
    quando nenhuma casa, quando o pedido nomeia outra peca, ou quando duas
    opcoes empatam — nesses casos quem chama PARA e mostra as opcoes. Casar
    errado abre um pedido errado na seguradora; parar so custa 10 segundos de
    um humano. Testavel offline."""
    return explicar_match(wanted, options)["escolha"]


# ===========================================================================
# VOCABULARIO DO 80% — o passo 6 nao pergunta PECA, pergunta ATRIBUTO.
#
# 📊 As perguntas reais, do mapa MEDIDO (docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-
# TELA.md §4 — captura tela a tela do Founder, 06/07/2026):
#   VIDRO DE PORTA (Yelum)  1) tem pelicula de controle solar (insulfilm)?
#                           2) e da porta DIANTEIRA ou TRASEIRA?
#                           3) qual o LADO? -> Lado do carona / Lado do motorista
#   PARABRISA (Tokio)       1) posicao do trincado? -> em frente ao motorista /
#                              em frente ao carona / nas bordas / no centro
#                           2) maior ou menor que 10 CM? -> troca x REPARO
#                           3) a versao do veiculo e comfortline?
#
# Por que NAO da para reaproveitar o casamento de PECAS:
#
# 📊 medido em 04/08/2026 (backend/tests/test_o_80_por_cento_sabe_o_que_pergunta.py,
#    secao [M1], que roda a funcao antiga contra as opcoes reais):
#      explicar_match("porta dianteira", ["DIANTEIRA","TRASEIRA","Nao sabe"]) -> None
#    porque identidade_peca('porta dianteira') = {lateral} e
#           identidade_peca('DIANTEIRA')      = {parabrisa}  (via _POSICAO)
#    -> o VETO de peca elimina as DUAS opcoes reais e sobra so 'Nao sabe'.
#    O MAPA CERTO NUM LUGAR E O MAPA ERRADO NO OUTRO: na tela da peca
#    'dianteira' significa parabrisa; na tela do atributo significa a porta da
#    frente — e a peca ja foi escolhida duas telas antes.
#
# 📊 e o placar por tokens nao tem como resolver o resto: 'lado do passageiro'
#    e 'Lado do carona' so compartilham 'lado', que aparece em TODA opcao e por
#    isso pesa 0.0. Nenhum ajuste de peso descobre que passageiro = carona.
#    Isso nao e semelhanca de texto, e TABELA DE FATO.
#
# 🔴 E o fato que mais custa errar: NO BRASIL O MOTORISTA SENTA A ESQUERDA.
#    lado do motorista = ESQUERDO · lado do carona = DIREITO.
#    Errar o lado manda trocar o vidro errado — e o portal PROIBE corrigir:
#    seria preciso abrir OUTRO acionamento (mapa §3). Nao ha desfazer.
# ===========================================================================

def _espacado(s: str) -> str:
    """Texto normalizado com a pontuacao virando espaco e com folga nas pontas —
    para casar FRASES ('quem dirige', 'de tras') sem tropecar em virgula,
    parentese ou fim de linha."""
    t = "".join(c if c.isalnum() else " " for c in _norm(s))
    return " " + " ".join(t.split()) + " "


def _palavras(s: str) -> set:
    """Palavras cruas: sem acento e sem pontuacao, mas SEM tirar plural e SEM
    tirar palavra vazia. Diferente de _tokens de proposito: aqui 'nao' e 'sem'
    PRECISAM sobreviver — sao eles que invertem a resposta ('nao tem pelicula')."""
    return set(_espacado(s).split())


def _menciona(texto: str, termos) -> bool:
    """Termo de UMA palavra casa como TOKEN INTEIRO; termo de VARIAS casa como
    trecho. E o que impede 'lado' de casar dentro de 'isolado' e ainda deixa
    'quem dirige' casar dentro de 'lado de quem dirige'."""
    palavras, frase = _palavras(texto), _espacado(texto)
    for t in termos:
        t = _norm(t)
        if " " in t:
            if f" {t} " in frase:
                return True
        elif t and t in palavras:
            return True
    return False


# 🔴 A tabela de fato do lado. Motorista a ESQUERDA (Brasil). Note quem NAO
# esta aqui: 'do meu lado' — quem fala pode ser o segurado, o corretor ou quem
# estava no banco do carona. Fica de fora para a funcao PARAR em vez de chutar.
_LADO = {
    "motorista": ("motorista", "condutor", "volante", "esquerdo", "esquerda",
                  "quem dirige", "quem esta dirigindo", "quem conduz",
                  "lado do volante", "lado do condutor"),
    "carona": ("carona", "passageiro", "acompanhante", "direito", "direita",
               "porta luvas", "porta-luvas"),
}
_PORTA = {
    "dianteira": ("dianteira", "dianteiro", "frontal", "frente", "da frente",
                  "de frente", "na frente", "primeira porta", "porta da frente"),
    "traseira": ("traseira", "traseiro", "tras", "atras", "de tras", "la atras",
                 "fundo", "banco de tras", "segunda porta", "porta de tras"),
}
_POSICAO_TRINCA = {
    "motorista": ("motorista", "condutor", "volante", "esquerdo", "esquerda", "quem dirige"),
    "carona": ("carona", "passageiro", "acompanhante", "direito", "direita"),
    "bordas": ("borda", "bordas", "canto", "cantos", "quina", "quinas", "beirada",
               "beira", "beiradas", "extremidade", "extremidades", "moldura", "orla"),
    "centro": ("centro", "central", "meio", "no meio", "bem no meio"),
}
_SIM_NAO = {"sim": ("sim",), "nao": ("nao",)}
# Tamanho do trincado. 📊 O limite 10 esta escrito na propria pergunta do
# portal: "O trincado esta maior ou menor que 10 cm?" — e ele decide TROCA x
# REPARO, ou seja, qual servico o vidraceiro vai prestar.
_LIMITE_CM = 10.0
_TAMANHO = {
    "maior": ("maior", "maiores", "grande", "grandona", "comprido", "comprida",
              "longa", "longo", "atravessa", "atravessando", "de ponta a ponta",
              "rachadura", "rachado", "rachada", "rachou", "enorme", "mais de", "acima de"),
    "menor": ("menor", "menores", "pequeno", "pequena", "pequenininha", "moeda",
              "pontinho", "unha", "dedo", "estrelinha", "olho de boi", "minusculo",
              "minuscula", "menos de", "abaixo de", "do tamanho de uma moeda"),
}
# Como a OPCAO se escreve quando o portal descreve o SERVICO em vez do tamanho
# ("Maior (troca do vidro)" / "Menor (possibilidade de reparo)"). So vale para
# classificar OPCAO: 'quero trocar' dito pelo segurado nao mede trincado nenhum.
_TAMANHO_SERVICO = {"maior": ("troca", "trocar", "substituicao", "substituir"),
                    "menor": ("reparo", "reparar", "conserto", "consertar")}
# Pelicula: os dois lados do sim/nao, e os marcadores que INVERTEM a resposta.
_PELICULA_SIM = ("pelicula", "peliculas", "insulfilm", "insufilm", "fume",
                 "escurecido", "escurecida", "escuro", "escura", "papel fume",
                 "controle solar", "filme", "film")
_PELICULA_NAO = ("original", "originais", "incolor", "transparente", "de fabrica")
_NEGACAO = ("nao", "sem", "nenhum", "nenhuma", "negativo", "nunca", "jamais")
_AFIRMACAO = ("sim", "tem", "possui", "positivo", "isso", "correto", "afirmativo",
              "exato", "claro", "com certeza", "isso mesmo")
# 🔴 'Nao sabe' esta em TODAS as perguntas do 80% e e uma armadilha: destrava a
# tela e o portal deixa de saber qual vidro pedir (mapa §4a e §8.2). So e
# honesto quando o SEGURADO realmente nao sabe — nunca por preguica do robo.
_IGNORANCIA = ("nao sei", "nao sabe", "nao sabemos", "nao sei dizer", "nao soube dizer",
               "nao sabe dizer", "nao sei informar", "nao sabe informar", "nao faco ideia",
               "nao lembro", "nao me lembro", "nao tenho certeza", "nao reparei",
               "nao consigo dizer", "nao da pra saber", "sem informacao", "nao informado")
# Palavras que a pergunta do portal usa para se enunciar e que por isso NAO
# identificam do que ela trata ("A versao do veiculo e comfortline?" trata de
# comfortline, nao de 'versao').
_GENERICOS_PERGUNTA = {
    "qual", "quais", "quando", "onde", "como", "poderia", "informar", "favor", "por",
    "veiculo", "carro", "vidro", "vidros", "item", "peca", "danificado", "danificada",
    "esta", "estao", "tem", "foi", "ser", "sobre", "versao", "modelo", "seu", "sua",
    "atendimento", "portal", "selecione", "opcao", "escolha", "lado", "posicao",
    "tamanho", "trincado", "trinca", "solicitante", "titular", "segurado",
}
# Uma opcao de ATRIBUTO e curta ("Menor (possibilidade de reparo)" = 3 palavras).
# A lista de LOJAS carrega endereco inteiro — e um bairro chamado 'Centro' nao
# pode virar 'posicao do trincado'. Este teto e o que separa as duas coisas.
_MAX_PALAVRAS_ATRIBUTO = 6
_RE_MEDIDA = re.compile(r"(\d+(?:[.,]\d+)?)\s*(centimetros?|cm|milimetros?|mm|metros?|m)\b")
_FATOR_CM = {"cm": 1.0, "centimetro": 1.0, "centimetros": 1.0,
             "mm": 0.1, "milimetro": 0.1, "milimetros": 0.1,
             "m": 100.0, "metro": 100.0, "metros": 100.0}


def _nomeia_peca(texto: str) -> bool:
    """PURO: ha um SUBSTANTIVO de peca no texto? Diferente de identidade_peca:
    aqui a POSICAO sozinha ('DIANTEIRA') NAO conta como peca — e justamente por
    isso que ela pode ser resposta de atributo no 80%. E o que mantem
    ['FAROL DIANTEIRO','LANTERNA TRASEIRA'] sendo escolha de PECA."""
    toks = set(_tokens(texto))
    if any(t in _AMBIGUOS for t in toks):
        return True
    return any(_singular(_norm(s)) in toks for sinonimos in _PECAS.values() for s in sinonimos)


def _e_opcao_de_ignorancia(opcao: str) -> bool:
    """A opcao 'Nao sabe' / 'Nao informado' que toda pergunta do 80% oferece."""
    o = _norm(opcao)
    return (o.startswith("nao sabe") or o.startswith("nao sei")
            or o.startswith("nao informad") or o in ("desconheco", "sem informacao"))


def _classe(texto: str, *tabelas) -> set:
    """PURO: em que classe(s) do dominio o texto cai. Mais de uma classe = o
    texto e ambiguo DE VERDADE ('na borda do lado do motorista')."""
    achadas = set()
    for tabela in tabelas:
        for classe, termos in tabela.items():
            if _menciona(texto, termos):
                achadas.add(classe)
    return achadas


def _e_dominio(uteis: List[str], *tabelas) -> bool:
    """A lista de opcoes PERTENCE a este dominio? Exige que TODA opcao caia em
    EXATAMENTE uma classe e que haja pelo menos DUAS classes distintas —
    'quase encaixa' nao encaixa."""
    classes = []
    for o in uteis:
        c = _classe(o, *tabelas)
        if len(c) != 1:
            return False
        classes.append(next(iter(c)))
    return len(set(classes)) >= 2


def _pode_ser_atributo(uteis: List[str]) -> bool:
    """Dois portoes antes de qualquer dominio de atributo abrir:
    (a) nenhuma opcao nomeia uma PECA — ['FAROL DIANTEIRO','LANTERNA TRASEIRA']
        e escolha de peca, e quem decide isso continua sendo explicar_match;
    (b) as opcoes sao CURTAS — a lista de lojas tem endereco dentro."""
    return bool(uteis) and not any(_nomeia_peca(o) for o in uteis) \
        and all(len(_palavras(o)) <= _MAX_PALAVRAS_ATRIBUTO for o in uteis)


def _qual_dominio(uteis: List[str]):
    """PURO: (nome_do_dominio, tabelas) ou ('', ()). A ordem importa so para
    NOMEAR: lado e posicao_do_trincado compartilham motorista/carona e dariam a
    mesma resposta; 'lado' vem antes por ser a pergunta mais curta."""
    for nome, tabelas in (("lado", (_LADO,)),
                          ("porta_dianteira_traseira", (_PORTA,)),
                          ("tamanho_trincado", (_TAMANHO, _TAMANHO_SERVICO)),
                          ("posicao_trincado", (_POSICAO_TRINCA,)),
                          ("sim_nao", (_SIM_NAO,))):
        if _e_dominio(uteis, *tabelas):
            return nome, tabelas
    return "", ()


def _centimetros(texto: str) -> Optional[float]:
    """PURO: '20 cm' -> 20.0 · '3 mm' -> 0.3 · 'meio metro' -> None (sem digito).
    Le a medida que o segurado deu, em centimetros, para comparar com os 10 cm
    que o portal usa para decidir troca x reparo."""
    m = _RE_MEDIDA.search(_norm(texto))
    if not m:
        return None
    try:
        valor = float(m.group(1).replace(",", "."))
    except ValueError:  # noqa: PERF203
        return None
    return valor * _FATOR_CM.get(m.group(2), 1.0)


def _termo_da_pergunta(pergunta: str) -> str:
    """PURO: a palavra de que a pergunta TRATA, quando ha uma so.
    'A versao do veiculo e comfortline?' -> 'comfortline'. Duas candidatas ou
    nenhuma -> '' (a pergunta nao se deixa resumir; nao inventamos)."""
    candidatas = [t for t in _palavras(pergunta)
                  if len(t) >= 5 and t not in _GENERICOS_PERGUNTA and not t.isdigit()]
    return candidatas[0] if len(candidatas) == 1 else ""


def _classe_sim_nao(resposta: str, pergunta: str):
    """PURO: (classe, motivo) para um sim/nao. Trata a NEGACAO explicitamente —
    'nao tem pelicula' cita 'pelicula' e mesmo assim a resposta e NAO. Um placar
    por tokens inverteria isso, e vidro com insulfilm custa outro preco."""
    # 🔴 'Nao sei' NAO e 'Nao'. Sem esta linha o token 'nao' de 'nao sei' cai na
    # negacao la embaixo e o robo AFIRMA que o vidro nao tem pelicula — quando o
    # segurado so disse que nao sabe. Inventar fato e pior que parar. (Este e o
    # unico dominio em que da para confundir os dois: nos outros 'nao' nao e
    # resposta valida.)
    if _menciona(resposta, _IGNORANCIA):
        return "", "nao_sabe"
    neg = _menciona(resposta, _NEGACAO)
    termo = _termo_da_pergunta(pergunta)
    # Vocabulario de pelicula quando e disso que a pergunta trata — ou quando
    # nao da para saber do que ela trata (o cerebro as vezes mira pelo name
    # tecnico e a pergunta chega vazia). Se a pergunta nomeia OUTRO termo
    # ('comfortline'), 'escurecido' nao pode significar sim.
    if _menciona(pergunta, ("pelicula", "peliculas", "insulfilm", "controle solar")) or not termo:
        marca = _menciona(resposta, _PELICULA_SIM)
        inverso = _menciona(resposta, _PELICULA_NAO)
    else:
        marca = termo in _palavras(resposta)
        inverso = False
    if marca and inverso:
        return "", "resposta_contraditoria"
    if marca:
        return ("nao" if neg else "sim"), ""
    if inverso:                       # 'nao e original' = tem pelicula
        return ("sim" if neg else "nao"), ""
    if _menciona(resposta, _AFIRMACAO) and not neg:
        return "sim", ""
    if neg:
        return "nao", ""
    return "", "nao_reconhecido"
    # NAO inferimos 'Nao' pela AUSENCIA do termo na descricao do veiculo: a
    # descricao da InfoCap pode vir truncada, e um 'Nao' errado em
    # 'e comfortline?' pede o parabrisa sem o suporte do sensor — vidro errado.


def _classe_tamanho(resposta: str):
    """PURO: (classe, motivo) para 'maior ou menor que 10 cm'. A MEDIDA e a
    PALAVRA precisam concordar; se discordarem ('menor que 20 cm' — que pode
    ser dos dois lados dos 10), nao ha resposta honesta e a funcao para."""
    cm = _centimetros(resposta)
    pelo_numero = ""
    if cm is not None and cm != _LIMITE_CM:
        pelo_numero = "maior" if cm > _LIMITE_CM else "menor"
    achadas = _classe(resposta, _TAMANHO)
    if len(achadas) > 1:
        return "", "ambiguo"
    pela_palavra = next(iter(achadas)) if achadas else ""
    if pelo_numero and pela_palavra and pelo_numero != pela_palavra:
        return "", "medida_contradiz_a_palavra"
    classe = pelo_numero or pela_palavra
    return (classe, "") if classe else ("", "nao_reconhecido")


def explicar_especifico(resposta: str, opcoes: List[str], pergunta: str = "") -> Dict[str, Any]:
    """PURO: casa a resposta do segurado com a opcao real de uma pergunta
    ESPECIFICA do 80% (lado · dianteira/traseira · pelicula · tamanho e posicao
    do trincado · sim/nao). Devolve o mesmo formato de explicar_match mais
    'dominio' e 'classe'.

    'dominio' == 'nenhum' significa 'esta lista nao e minha' — quem chamou deve
    usar o casamento de PECAS. E o unico jeito honesto de ter dois vocabularios
    sem ter dois placares: cada um diz quando NAO e o dono da pergunta.

    escolha None = para e devolve as opcoes, igual ao casamento de pecas. Errar
    o lado aqui manda trocar o vidro errado, e o portal nao deixa corrigir."""
    reais = [o for o in (opcoes or []) if str(o).strip() and "selecione" not in _norm(o)]
    uteis = [o for o in reais if not _e_opcao_de_ignorancia(o)]
    base: Dict[str, Any] = {"escolha": None, "motivo": "fora_do_dominio",
                            "dominio": "nenhum", "classe": "", "opcoes": reais}
    if not _pode_ser_atributo(uteis):
        return base
    dominio, tabelas = _qual_dominio(uteis)
    if not dominio:
        return base
    base["dominio"] = dominio
    if not str(resposta or "").strip():
        return {**base, "motivo": "resposta_vazia"}

    if dominio == "sim_nao":
        classe, motivo = _classe_sim_nao(resposta, pergunta)
    elif dominio == "tamanho_trincado":
        classe, motivo = _classe_tamanho(resposta)
    else:
        achadas = _classe(resposta, *tabelas)
        classe = next(iter(achadas)) if len(achadas) == 1 else ""
        motivo = "" if classe else ("ambiguo" if achadas else "nao_reconhecido")

    if not classe:
        # So DEPOIS de nao achar resposta de verdade e que 'Nao sabe' entra —
        # e so se o segurado tiver dito que nao sabe. 'nao sei o que houve, mas
        # quebrou o do lado do motorista' responde LADO DO MOTORISTA.
        ignorancia = [o for o in reais if _e_opcao_de_ignorancia(o)]
        if _menciona(resposta, _IGNORANCIA) and len(ignorancia) == 1:
            return {**base, "escolha": ignorancia[0], "motivo": "nao_sabe_honesto",
                    "classe": "nao_sabe"}
        return {**base, "motivo": motivo}

    candidatos = [o for o in uteis if classe in _classe(o, *tabelas)]
    if len(candidatos) != 1:
        return {**base, "classe": classe,
                "motivo": "opcao_ambigua" if candidatos else "sem_opcao_para_a_resposta"}
    return {**base, "escolha": candidatos[0], "motivo": "atributo", "classe": classe}


def responder_especifico(resposta: str, opcoes: List[str], pergunta: str = "") -> Optional[str]:
    """PURO: a opcao do 80% que responde ao segurado COM CONFIANCA, ou None."""
    return explicar_especifico(resposta, opcoes, pergunta)["escolha"]


# ---- login (portais de CORRETOR — os que pedem login/senha; vidros nao usa) ----
_LOGIN_OK = ("sair", "logout", "meus pedidos", "bem-vindo", "bem vindo", "painel", "minha conta")
_LOGIN_FAIL = ("senha invalida", "usuario invalido", "credenciais invalidas", "login invalido",
               "dados incorretos", "senha incorreta")
_HITL = ("captcha", "verificacao", "codigo de seguranca", "autenticacao em duas etapas", "two-factor", "2fa")


def interpret_login(page_text: str, url: str = "") -> JourneyResult:
    """PURO: resultado do login (portais de corretor)."""
    text = _norm(page_text)
    if any(s in text for s in (_norm(x) for x in _LOGIN_FAIL)):
        return JourneyResult(status="failed", message="credenciais rejeitadas pelo portal")
    if any(s in text for s in _HITL):
        return JourneyResult(status="needs_human", message="portal pediu CAPTCHA/2FA")
    if any(s in text for s in _LOGIN_OK):
        return JourneyResult(status="done", captured={"logged_in": True})
    return JourneyResult(status="needs_human", message="tela pos-login nao reconhecida")


_VIDROS_ERR = ("nao encontrad", "invalid", "nao localizamos", "apolice nao", "sem cobertura")


# ===========================================================================
# O PROTOCOLO — o numero que prova que o pedido existe
#
# 📊 Ele nasce no passo 7, NO TOPO da tela, ANTES da escolha da loja
# (docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md §7): `Nº do atendimento:
# 22842291`. Quando este numero aparece, o pedido JA EXISTE na seguradora —
# desistir daqui em diante nao desfaz nada, e repetir o fluxo cria um SEGUNDO
# atendimento (mapa §9.5).
#
# 🔴 O DEFEITO QUE ESTA SECAO DESFAZ — medido, nao lido.
#
# 📊 04/08/2026, contra o texto literal do mapa, com o codigo de entao
#    (`_PROTO` = protocolo | numero do atendimento | n do atendimento |
#     solicitacao registrada | atendimento n):
#
#      has_protocol({"text": "Nº do atendimento: 22842291"})   -> False
#      has_protocol({"text": "N° do atendimento: 22842291"})   -> True
#      interpret_atendimento(".../passo5/<uuid>", <tela 7>)
#          -> needs_human, captured={'stage': 'passo5'}, "parou em passo5"
#
# A causa e de uma letra. `_norm` faz NFKD + ascii-ignore, e os dois sinais que
# um humano le como "numero" nao se comportam igual:
#
#      'º' MASCULINE ORDINAL INDICATOR  -> NFKD 'o'  -> "No do atendimento"
#      '°' DEGREE SIGN                  -> NFKD '°'  -> some  -> "N do atendimento"
#
# O portal usa 'º' (o ordinal). A lista tinha "n do atendimento" e nao tinha
# "no do atendimento" — entao reconhecia o sinal ERRADO e nao reconhecia o
# certo. A tela do protocolo teria sido registrada como "parou em passo5": o
# atendimento aberto, e nos declarando que o robo tinha parado no meio.
#
# 📊 Isso nunca custou um atendimento so porque o passo 7 nunca foi alcancado
# (39 acionamentos, zero protocolos). Ele esta prestes a ser.
#
# Por que a extracao mora AQUI e nao no adaptive.py: a mesma regra ja valia
# para `explicar_match`. Duas listas de rotulo em dois arquivos sao duas
# verdades que divergem no dia em que so uma for corrigida — e era exatamente
# esse o estado anterior (`_PROTO` e `_VIDROS_PROTO`, identicas por copia).
# ===========================================================================

# Rotulos do MAIS especifico ao MAIS generico: o primeiro que casar responde.
# Todos sao comparados com FRONTEIRA DE PALAVRA dos dois lados (ver `_espacado`)
# — sem isso "no de atendimento" casaria dentro de "plaNO DE ATENDIMENTO".
_ROTULOS_DE_PROTOCOLO = (
    "numero do atendimento", "numero de atendimento",
    "no do atendimento", "no de atendimento",      # 'Nº ...' (ordinal) depois do NFKD
    "n do atendimento",                            # 'N° ...' (grau) depois do ascii-ignore
    "numero do protocolo", "numero da solicitacao",
    "atendimento numero", "atendimento no", "atendimento n",
    "protocolo",
)
# Marcas de que a tela E a do protocolo, mesmo quando o numero nao se deixa ler
# (portal que escreve so "Solicitacao registrada"). Servem para RECONHECER a
# tela; nunca para inventar um numero.
_MARCAS_DE_PROTOCOLO = _ROTULOS_DE_PROTOCOLO + ("solicitacao registrada", "atendimento registrado")
# Do rotulo ate o numero cabem ": ", " nº ", " numero " — nao um paragrafo.
# `[^0-9]{0,16}` e essa folga; o `[0-9]` final e o que impede o ponto/hifen de
# grudar no fim ("Protocolo: 123456." -> "123456").
_RE_NUMERO_DO_PROTOCOLO = re.compile(r"[^0-9]{0,16}([0-9][0-9./\-]{2,24}[0-9])")
# Menos de 5 digitos nao e protocolo: e o "1 (um) ITEM" do aviso que aparece em
# todas as telas, ou uma data. 📊 O numero real medido tem 8.
_MINIMO_DE_DIGITOS_DO_PROTOCOLO = 5
_SEPARADORES_DE_NUMERO = ".-/"


def _frase_do_protocolo(texto: str) -> str:
    """Normalizado com fronteira de palavra, PRESERVANDO o separador que estiver
    ENTRE DIGITOS.

    `_espacado` troca toda pontuacao por espaco. Isso e certo para casar frases
    e fatal para um protocolo escrito `2026-0001234`: ele sairia partido em dois
    e o primeiro pedaco viraria o "numero" — 🔴 um protocolo truncado nao e meio
    protocolo, e um numero ERRADO, e o segurado vai usa-lo para cobrar a
    seguradora.

    A regra e exata de proposito: o separador so sobrevive com digito dos DOIS
    lados. Assim `2026-0001234` fica inteiro e o ponto final de um rotulo
    ("atendimento.") continua virando espaco, sem o qual a fronteira de palavra
    deixaria de casar.
    """
    bruto = _norm(texto)
    saida = []
    for i, c in enumerate(bruto):
        if c.isalnum():
            saida.append(c)
        elif (c in _SEPARADORES_DE_NUMERO and i and bruto[i - 1].isdigit()
                and i + 1 < len(bruto) and bruto[i + 1].isdigit()):
            saida.append(c)
        else:
            saida.append(" ")
    return " " + " ".join("".join(saida).split()) + " "


def extrair_protocolo(page_text: str) -> str:
    """PURO: o NUMERO do atendimento que a tela mostra. "" quando nao ha.

    Le so o que esta colado ao rotulo. Um numero solto na tela (o CEP da loja,
    um telefone, o '1 (um) ITEM' do aviso) nao vira protocolo — dizer ao
    segurado um numero errado e pior que nao dizer numero nenhum.
    """
    frase = _frase_do_protocolo(page_text)
    for rotulo in _ROTULOS_DE_PROTOCOLO:
        alvo = f" {rotulo} "
        pos = frase.find(alvo)
        while pos != -1:
            m = _RE_NUMERO_DO_PROTOCOLO.match(frase, pos + len(alvo) - 1)
            if m:
                numero = m.group(1).strip(_SEPARADORES_DE_NUMERO)
                if sum(c.isdigit() for c in numero) >= _MINIMO_DE_DIGITOS_DO_PROTOCOLO:
                    return numero
            pos = frase.find(alvo, pos + 1)
    return ""


def tem_protocolo(page_text: str) -> bool:
    """PURO: esta tela e a do protocolo? Mais larga que `extrair_protocolo` de
    proposito — a tela pode anunciar o pedido sem um numero legivel, e ainda
    assim o pedido EXISTE. Reconhecer a tela e o que impede o robo de seguir
    clicando como se nao tivesse aberto nada."""
    if extrair_protocolo(page_text):
        return True
    frase = _frase_do_protocolo(page_text)
    return any(f" {m} " in frase for m in _MARCAS_DE_PROTOCOLO)


# ===========================================================================
# FRANQUIA e LINK DA VISTORIA — os outros dois numeros da tela do protocolo
#
# 📊 SPEC-071 BLOCO 6, telas que a Regina entregou em 14/08/2026:
#
#     Atendimento nº 23085997     ✅ ja era lido
#     Franquia R$ 925,00          ❌ ZERO mencoes no portal_worker inteiro
#     https://vistoria.mobi/...   ❌ ZERO mencoes
#
# Os tres saem da MESMA tela e valem coisas diferentes para o segurado: o
# protocolo e para cobrar, a franquia e quanto ele vai PAGAR, e o link e por
# onde ele manda as fotos. Levar so o protocolo e entregar um terco do
# atendimento e obrigar a atendente a abrir o portal para ver o resto.
#
# ⚠️ POR QUE NAO DA PARA REUSAR `_frase_do_protocolo` NOS DOIS:
#
#   franquia  R$ 925,00 -> a virgula so sobrevive ENTRE DIGITOS, e e o que
#             `_frase_do_protocolo` ja faz. Mas ele NAO preserva o "R$", e sem
#             ele "925,00" e indistinguivel de qualquer outro numero da tela.
#             Por isso a leitura e sobre o texto normalizado COM o cifrao.
#
#   link      `_norm` destroi URL — tira acento, baixa caixa e a pontuacao
#             vira espaco. Uma URL normalizada nao e mais uma URL. A leitura
#             tem de ser sobre o texto CRU, e e a unica deste arquivo que e.
# ===========================================================================

_ROTULOS_DE_FRANQUIA = (
    "valor da franquia", "franquia a pagar", "franquia do servico",
    "participacao obrigatoria",   # como algumas seguradoras chamam
    "franquia",
)
# `R$` seguido do valor. Aceita `R$ 925,00`, `R$925,00`, `R$ 1.250,00`.
# O grupo pega SO os digitos e os separadores — o cifrao fica fora.
_RE_VALOR_EM_REAIS = re.compile(r"r\$\s*([0-9][0-9.,]{0,12}[0-9])")
# 🔴 O PISO E EM REAIS, NAO EM DIGITOS — e a diferenca importa.
#
# A primeira versao contava digitos: `R$ 1,00` tem tres ("100") e PASSAVA. O
# robo diria ao segurado que a franquia dele e de um real. Contar digito e
# medir a grafia; o que decide se aquilo e uma franquia e o VALOR.
#
# 📊 A tela da Regina traz R$ 925,00. Franquia de vidro abaixo de dez reais nao
# existe — o que aparece nessa faixa e "1 (um) ITEM", numero de parcela ou
# percentual.
_PISO_DA_FRANQUIA_EM_REAIS = 10.0


def _valor_em_reais(bruto: str) -> float:
    """`"1.250,00"` -> `1250.0`. Devolve 0.0 quando nao da para ler."""
    try:
        return float(str(bruto).replace(".", "").replace(",", "."))
    except (TypeError, ValueError):
        return 0.0

# 📊 O dominio que a Regina mostrou. Deliberadamente ESTREITO: um regex de URL
# generico pegaria o link do proprio portal, o da politica de privacidade e o
# do rodape — e o robo diria ao segurado "sua vistoria e em
# abraseuatendimento.com.br/politica", que e pior que nao dizer nada.
_DOMINIOS_DE_VISTORIA = ("vistoria.mobi", "vistoriamobi.com.br")
_RE_LINK = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)


def extrair_franquia(page_text: str) -> str:
    """PURO: o valor da franquia como a tela escreve. "" quando nao ha.

    Devolve `"925,00"` — sem o `R$`, com a virgula. É o que se diz ao segurado.
    """
    frase = _frase_do_protocolo(page_text or "")
    bruto = _norm(page_text or "")
    # O `_norm` come o cifrao; a busca do valor acontece no texto com cifrao.
    com_cifrao = " " + " ".join(str(page_text or "").lower().split()) + " "

    for rotulo in _ROTULOS_DE_FRANQUIA:
        if f" {rotulo} " not in frase and rotulo not in bruto:
            continue
        # A janela: do rotulo em diante. Um `R$` que aparece ANTES do rotulo e
        # de outra coisa (o valor do servico, o do vidro) — e pegar o numero
        # errado aqui e dizer ao segurado que ele vai pagar o que nao vai.
        pos = com_cifrao.find(rotulo.split()[0])
        janela = com_cifrao[pos:] if pos >= 0 else com_cifrao
        m = _RE_VALOR_EM_REAIS.search(janela)
        if not m:
            continue
        valor = m.group(1).strip(".,")
        if _valor_em_reais(valor) >= _PISO_DA_FRANQUIA_EM_REAIS:
            return valor
    return ""


def extrair_link_de_vistoria(page_text: str) -> str:
    """PURO: o link da vistoria que a tela mostra. "" quando nao ha.

    ⚠️ Le o texto CRU, sem `_norm`: normalizar destroi a URL. É a unica leitura
    deste arquivo que nao passa pelo normalizador, e e de proposito.
    """
    for url in _RE_LINK.findall(str(page_text or "")):
        limpo = url.rstrip(".,;:)")
        if any(d in limpo.lower() for d in _DOMINIOS_DE_VISTORIA):
            return limpo
    return ""


def tem_vistoria(page_text: str) -> bool:
    """PURO: esta tela oferece vistoria por link?"""
    return bool(extrair_link_de_vistoria(page_text))


# ===========================================================================
# DOMICILIO x LOJA — a escolha do passo 7, que e do SEGURADO
#
# 📊 A tela oferece duas saidas (mapa §7): "Agendar a domicilio" (com os selos
# "Sem deslocamento · Economia de tempo · Atendimento premium") e a lista de
# lojas, cada uma com endereco, "Consultar distancia", "Ver no mapa" e
# "Agendar na loja".
#
# O que se pergunta ao segurado e a PREFERENCIA, nunca a loja: ele nao conhece
# a lista, e a lista so existe nesta tela. E a preferencia nem sempre e
# atendivel — 📊 o rotulo do CEP diz que ele serve para "verificar se ha
# disponibilidade de atendimento em domicilio na sua regiao", ou seja, o
# domicilio pode simplesmente nao existir no CEP dele.
#
# 🔴 A assimetria proposital desta funcao: na duvida ela NAO diz 'domicilio'.
# Marcar loja por engano custa uma parada com a lista na mao (barato, e o
# humano ve as palavras do segurado no dossie). Marcar domicilio por engano
# marcaria um tecnico para ir a casa de quem pediu para levar o carro.
# ===========================================================================
_ATENDIMENTO_A_DOMICILIO = (
    "domicilio", "domiciliar", "casa", "residencia", "em casa", "na minha casa",
    "ate mim", "ate min", "ate aqui", "onde eu estou", "onde estou", "onde eu estiver",
    "no trabalho", "no meu trabalho", "no escritorio", "venha ate", "venham ate",
    "tecnico venha", "vem aqui", "venha aqui", "sem sair", "sem deslocamento",
)
_ATENDIMENTO_NA_LOJA = (
    "loja", "lojas", "oficina", "oficinas", "unidade", "unidades", "concessionaria",
    "vidracaria", "levar", "levo", "levando", "vou levar", "prefiro levar",
    "vou ate", "vou la", "presencial", "deixar o carro", "deixo o carro",
)
# So estas negacoes bloqueiam o 'domicilio'. 'sem' fica de fora de proposito:
# 📊 e palavra do proprio selo do portal ("Sem deslocamento") — inclui-la faria
# a resposta mais clara de todas ser recusada.
_NEGA_A_PREFERENCIA = ("nao", "nem", "nunca", "jamais")


def preferencia_de_atendimento(resposta: str) -> str:
    """PURO: 'domicilio' | 'loja' | '' (nao da para saber).

    '' NAO e falha: e a resposta honesta quando o texto diz as duas coisas
    ("nao tenho como levar" fala de levar e de impedimento) ou nenhuma. Quem
    chama para e mostra a lista real — o que ja seria feito de qualquer forma.
    """
    achadas = _classe(resposta, {"domicilio": _ATENDIMENTO_A_DOMICILIO,
                                 "loja": _ATENDIMENTO_NA_LOJA})
    if len(achadas) != 1:
        return ""
    classe = next(iter(achadas))
    if classe == "domicilio" and _menciona(resposta, _NEGA_A_PREFERENCIA):
        return ""
    return classe


def botao_de_domicilio(botoes) -> str:
    """PURO: o texto do botao "Agendar a domicilio", ou "". 📊 So existe quando
    o CEP do segurado tem cobertura de domicilio."""
    return _primeiro_botao(botoes, ("agendar", "domicili"))


def botao_de_loja(botoes) -> str:
    """PURO: o texto de um botao "Agendar na loja", ou "". A presenca dele diz
    que HA lojas na tela; QUAL delas continua sendo escolha do segurado."""
    return _primeiro_botao(botoes, ("agendar", "loja"))


def _primeiro_botao(botoes, exigidos) -> str:
    """PURO: o texto do 1o botao VISIVEL e habilitado que contem todos os termos.
    Aceita a lista de `capture_state` ({'text','disabled'}) ou strings cruas."""
    for b in botoes or []:
        texto = str((b.get("text") if isinstance(b, dict) else b) or "")
        if isinstance(b, dict) and b.get("disabled"):
            continue
        alvo = _norm(texto)
        if alvo and all(termo in alvo for termo in exigidos):
            return " ".join(texto.split())
    return ""


def interpret_atendimento(url: str, page_text: str) -> JourneyResult:
    """PURO: em que ponto do acionamento de vidros parou.

    A ordem importa e nao e cosmetica: o protocolo e conferido ANTES da URL
    porque a tela do protocolo MORA em `#/<slug>/passo5/<uuid>` (mapa §2). Ler
    a URL primeiro devolveria "parou em passo5" para a tela que prova que o
    atendimento foi aberto.
    """
    u = _norm(url)
    if tem_protocolo(page_text):
        numero = extrair_protocolo(page_text)
        return JourneyResult(
            status="done",
            captured={"stage": "protocolo", "protocolo": numero},
            message=(f"protocolo capturado: {numero}" if numero else "protocolo capturado"),
        )
    text = _norm(page_text)
    if any(s in text for s in _VIDROS_ERR):
        return JourneyResult(status="failed", message="portal nao localizou CPF/placa ou dado invalido")
    for stage in ("passo5", "passo4", "passo3", "passo2", "passo1", "menu-atendimento"):
        if stage in u:
            return JourneyResult(status="needs_human", captured={"stage": stage}, message=f"parou em {stage}")
    return JourneyResult(status="needs_human", message="tela do acionamento nao reconhecida")


# ---------------- shell Playwright (imperativo) ----------------
async def _dismiss(page) -> None:
    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(250)
        await page.mouse.click(5, 5)
        await page.wait_for_timeout(250)
    except Exception:  # noqa: BLE001
        pass


async def _click_button(page, text: str) -> bool:
    for x in await page.query_selector_all("button"):
        try:
            if await x.is_visible() and _norm(text) in _norm(await x.inner_text()):
                await x.click()
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _visible_options(page) -> List[str]:
    for sel in ("[role=option]", ".ng-option", "mat-option", ".dropdown-item", "li"):
        out = []
        for o in await page.query_selector_all(sel):
            try:
                if await o.is_visible():
                    t = (await o.inner_text() or "").strip()
                    if t:
                        out.append(t)
            except Exception:  # noqa: BLE001
                continue
        if out:
            return out
    return []


async def _choose(page, trigger, wanted: str) -> tuple:
    """Abre um dropdown e escolhe a opcao que casa com 'wanted'.
    Retorna (ok, options). Sem match -> (False, options) p/ o agente decidir."""
    try:
        await trigger.click()
        await page.wait_for_timeout(900)
        options = await _visible_options(page)
        chosen = match_option(wanted, options)
        if not chosen:
            await _dismiss(page)
            return False, options
        for o in await page.query_selector_all("[role=option], .ng-option, mat-option, .dropdown-item, li"):
            try:
                if await o.is_visible() and (await o.inner_text() or "").strip() == chosen:
                    await o.click()
                    await page.wait_for_timeout(500)
                    return True, options
            except Exception:  # noqa: BLE001
                continue
        await _dismiss(page)
        return False, options
    except Exception:  # noqa: BLE001
        return False, []


async def _choose_any_select(page, wanted: str) -> tuple:
    """Acha o <select> nativo (mesmo visually-hidden do Material) que tem a opcao
    desejada e a seleciona (dispara change/input p/ o Angular ligar). Robusto para
    dropdowns escondidos. Retorna (ok, options)."""
    if not wanted:
        return True, []
    for s in await page.query_selector_all("select"):
        try:
            opts = await s.evaluate(
                "el => Array.from(el.options).map(o => (o.textContent||'').trim()).filter(Boolean)")
        except Exception:  # noqa: BLE001
            continue
        chosen = match_option(wanted, opts)
        if chosen:
            try:
                await s.select_option(label=chosen)
                await s.evaluate(
                    "el => { el.dispatchEvent(new Event('change',{bubbles:true}));"
                    " el.dispatchEvent(new Event('input',{bubbles:true})); }")
                await page.wait_for_timeout(500)
                return True, opts
            except Exception:  # noqa: BLE001
                return False, opts
    return False, []


async def _select_first_real(page, sel_el) -> bool:
    """Seleciona a 1a opcao real (nao 'Selecione...') de um <select> — para campos
    obrigatorios onde qualquer valor serve para avancar (ex.: tipo de telefone)."""
    try:
        opts = await sel_el.evaluate(
            "el => Array.from(el.options).map(o => ({v:o.value, t:(o.textContent||'').trim()}))")
        for o in opts:
            if o["v"] and "selecione" not in o["t"].lower():
                await sel_el.select_option(value=o["v"])
                await sel_el.evaluate("el => el.dispatchEvent(new Event('change',{bubbles:true}))")
                await page.wait_for_timeout(400)
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


async def _achar_campo(page, ids: tuple, pistas: tuple):
    """Acha um input pelo SENTIDO antes da POSICAO. 'pistas' casa contra
    name/id/placeholder/aria-label/label; 'ids' sao os seletores numerados pelo
    Angular (#input_1, #input_3), aceitos so quando o sentido nao resolve —
    id numerado depende da ordem dos campos e muda sem aviso."""
    try:
        metas = await page.evaluate(
            """() => [...document.querySelectorAll('input,textarea')].map((e, i) => {
                 let lab = (e.labels && e.labels[0] && e.labels[0].textContent) || '';
                 if (!lab) { const c = e.closest('md-input-container,md-autocomplete');
                             if (c) { const l = c.querySelector('label'); if (l) lab = l.textContent; } }
                 return {i, txt: [e.name, e.id, e.placeholder, e.getAttribute('aria-label'), lab]
                            .filter(Boolean).join(' '),
                         vis: !!(e.offsetParent || e.getClientRects().length)};
               })"""
        )
    except Exception:  # noqa: BLE001
        metas = []
    els = await page.query_selector_all("input,textarea")
    for m in metas or []:
        if m.get("vis") and any(p in _norm(m.get("txt")) for p in pistas):
            i = m.get("i")
            if isinstance(i, int) and i < len(els):
                return els[i]
    for sel in ids:                      # ultimo recurso: o id numerado de sempre
        el = await page.query_selector(sel)
        if el:
            return el
    return None


async def _campos_visiveis(page) -> List[Dict[str, Any]]:
    """Raio-X do passo1 quando ele nao e reconhecido — para o proximo ajuste ser
    feito com o DOM real na mao, e nao por chute."""
    try:
        return await page.evaluate(
            """() => [...document.querySelectorAll('input,textarea')]
                 .filter(e => !!(e.offsetParent || e.getClientRects().length))
                 .map(e => ({id:e.id, name:e.name, ph:e.placeholder||'', type:e.type}))"""
        ) or []
    except Exception:  # noqa: BLE001
        return []


async def _select_insurer_start(page, insurer: str) -> bool:
    await page.goto(VIDROS_BASE, wait_until="domcontentloaded")
    await page.wait_for_timeout(3500)
    inp = await page.query_selector("#seguradora-input")
    if not inp:
        return False
    await inp.click()
    await inp.fill(insurer)
    await page.wait_for_timeout(1500)
    for o in await page.query_selector_all("[role=option]"):
        if await o.is_visible():
            await o.click()
            break
    await page.wait_for_timeout(500)
    await _click_button(page, "Avan")            # Avancar
    await page.wait_for_timeout(3500)
    await _click_button(page, "Iniciar atendimento")
    await page.wait_for_timeout(3500)
    return "passo1" in page.url


async def abrir_atendimento(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """Vidros PUBLICO. O agente monta os params a partir da conversa. A journey
    navega ate a tela de confirmacao (80%) e SO submete o pedido com confirm=True.
    params: insurer_name, cpf_cnpj, placa, data_dano, solicitante{relacao,email,
    nome,cpf_cnpj,telefone}, dano{peca,como,onde,descricao}, local{estado,cidade,
    cep}, especificos{pergunta->resposta}, confirm."""
    insurer = str(params.get("insurer_name") or "").strip()
    cpf = str(params.get("cpf_cnpj") or "").strip()
    placa = str(params.get("placa") or "").strip()
    data_dano = str(params.get("data_dano") or "").strip()
    if not (insurer and cpf and placa and data_dano):
        return JourneyResult(status="failed", message="faltam dados: insurer_name, cpf_cnpj, placa, data_dano")

    if not await _select_insurer_start(page, insurer):
        return JourneyResult(status="needs_human", message="tela inicial do portal de vidros mudou")

    # passo1: CPF + placa + data (datepicker Material -> digita e fecha overlay).
    # Os ids #input_1/#input_3 sao NUMERADOS pelo Angular: dependem da ORDEM em
    # que os campos nascem. Um campo a mais na tela e a placa vai para o campo
    # errado, calada. Por isso procuramos primeiro pelo SENTIDO (label/placeholder/
    # name) e so caimos no id numerado como ultimo recurso.
    campo_cpf = await _achar_campo(page, ("#inserir-cpf-input",), ("cpf", "cnpj", "documento"))
    campo_placa = await _achar_campo(page, ("#input_1",), ("placa",))
    if not campo_cpf or not campo_placa:
        evidence["passo1"] = await _campos_visiveis(page)
        return JourneyResult(status="needs_human",
                             message="passo1 do portal mudou: nao achei o campo de CPF ou de placa")
    await campo_cpf.fill(cpf)
    await campo_placa.fill(placa)
    d = await _achar_campo(page, ("#input_3",), ("data", "sinistro", "ocorrencia", "ocorreu"))
    if d:
        await d.click()
        await page.wait_for_timeout(300)
        await page.keyboard.type(data_dano)
        await page.keyboard.press("Tab")
        await _dismiss(page)
    await _click_button(page, "Iniciar atendimento")
    await page.wait_for_timeout(4500)
    body = await page.inner_text("body")
    if any(s in _norm(body) for s in _VIDROS_ERR):
        return JourneyResult(status="failed", message="portal nao localizou CPF/placa (verifique a apolice)")

    # modal "Dados da apolice" -> Confirmar
    await _click_button(page, "Confirmar")
    await page.wait_for_timeout(4000)

    # Camada 2 (SPEC-020) — daqui pra frente o CEREBRO dirige a tela (passo2 -> 80%).
    # Variacoes por seguradora/peca sao tratadas com inteligencia; nunca trava. Para
    # na confirmacao (80%) sem enviar (a menos de confirm=True). Dados REAIS, sem mascara.
    from portal_worker.adaptive import run_adaptive

    goal = f"Abrir atendimento de vidros na seguradora {insurer} para o segurado, ate a tela de confirmacao."
    collected = {
        "cpf_cnpj": cpf, "placa": placa, "data_dano": data_dano,
        "segurado": params.get("segurado") or {},   # apolice/chassi/veiculo (InfoCap)
        "solicitante": params.get("solicitante") or {},
        "dano": params.get("dano") or {},
        "local": params.get("local") or {},
        "especificos": params.get("especificos") or {},
    }
    return await run_adaptive(page, goal, collected, evidence, confirm=bool(params.get("confirm")))


async def login_check(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """Portais de CORRETOR (com login/senha). Vidros NAO usa isto."""
    login_url = str(params.get("login_url") or "")
    username = str(params.get("username") or "")
    password = str(params.get("password") or "")
    if not login_url:
        return JourneyResult(status="failed", message="login_url ausente nos params")
    await page.goto(login_url, wait_until="domcontentloaded")
    for sel in ("input[type=email]", "input[name=usuario]", "input[name=login]",
                "input[name=email]", "input[name=user]", "#usuario", "#login", "#email"):
        el = await page.query_selector(sel)
        if el:
            await el.fill(username)
            break
    for sel in ("input[type=password]", "input[name=senha]", "input[name=password]", "#senha", "#password"):
        el = await page.query_selector(sel)
        if el:
            await el.fill(password)
            break
    for sel in ("button[type=submit]", "input[type=submit]",
                "button:has-text('Entrar')", "button:has-text('Acessar')", "button:has-text('Login')"):
        el = await page.query_selector(sel)
        if el:
            await el.click()
            break
    await page.wait_for_timeout(2500)
    try:
        body = await page.inner_text("body")
    except Exception:  # noqa: BLE001
        body = ""
    evidence["url"] = getattr(page, "url", login_url)
    return interpret_login(body, evidence["url"])
