"""As perguntas que o portal de vidros VAI fazer — sabidas ANTES de entrar nele.

O defeito que esta peça desfaz
------------------------------
📊 39 acionamentos de `vidros_lanternas` (06 a 15/07/2026, Supabase
`dcajcvlzcjbmyapmklil`): **33 pararam em `needs_human`, 5 falharam, 1 terminou
"done" sem protocolo. Zero protocolos.** 📊 Das 33 paradas, 7 foram por um dado
que **já estava disponível** — na InfoCap, ou perguntável em uma frase.

O erro não é falta de inteligência. É **ordem**:

    ANTES   abre o portal → descobre o que falta → para → chama um humano
    AGORA   descobre o que falta → pergunta → abre o portal → preenche

Quando o sistema descobre a lacuna *dentro* do portal, o segurado já saiu do
WhatsApp, o robô está parado numa tela com um dropdown aberto, e alguém precisa
reabrir tudo. E reabrir é caro de um jeito que não se desfaz: 📊 o `Nº do
atendimento` nasce no passo 7, **no topo da tela, antes da escolha da loja**
(`docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` §7) — repetir o fluxo cria um
SEGUNDO atendimento na seguradora, não corrige o primeiro.

O que este módulo é, e o que não é
----------------------------------
É o **catálogo medido** do que o portal pergunta, mais uma função pura que
responde, antes de qualquer navegador abrir: *quais perguntas ainda faltam para
este acionamento não travar?*

Não é um motor de coleta. O motor de "o que ainda falta" do **corredor de
WhatsApp** já existe e continua sendo dele:
`corridor_playbooks.missing_slots_for_subservice`. Aquele lê slots de playbook
de URA; este lê o mapa de um PORTAL web. São duas telas diferentes, com dois
conjuntos de campos medidos em fontes diferentes — e nenhum dos dois responde
pelo outro. O que **não** se duplica aqui é o vocabulário de peça: ele é
importado (ver `identidade_peca` abaixo).

As quatro decisões de desenho
-----------------------------
**1. A pergunta nasce da PEÇA.** As específicas do passo 6 (80%) dependem do que
quebrou: película/dianteira-traseira/lado são de vidro lateral; posição e
tamanho do trincado são de para-brisa. Perguntar de película a quem quebrou o
retrovisor é ruído. E se a peça ainda não é conhecida, **ela é a primeira
pergunta** — as outras nem existem ainda, porque não há como saber quais são.

**2. "Não perguntar" é diferente de "não sei".** A versão do veículo e o CEP
saem da InfoCap e **nunca** viram pergunta ao segurado (§8.3 do mapa: *"Perguntar
ao segurado o que está na apólice"* é proibido). Se a InfoCap não trouxe, isso é
uma **lacuna do PROVEDOR** — de quem opera a integração, não de quem quebrou o
vidro. Por isso `Pergunta.de_quem`.

**3. Peça não mapeada não pode virar bloqueio.** 📊 As específicas de retrovisor,
farol, lanterna, vigia e teto **não foram medidas** (§7 do mapa). O honesto é
declarar isso — `especificas_mapeadas()` devolve False e a mensagem ao agente diz
com todas as letras que não estão mapeadas — e deixar o caminho adaptativo, que
lê a tela real, resolver. Inventar pergunta seria pior que não perguntar:
mandaria o segurado responder algo que o portal não vai usar.

**4. "Não sabe" é veneno, mas existe.** 📊 Toda pergunta do 80% oferece "Não
sabe", e ela destrava a tela degradando o serviço (§8.2 do mapa). A diferença
que este módulo modela: responder "não sabe" **por preguiça do robô** é proibido;
responder "não sabe" **porque o segurado realmente não sabe** é legítimo — mas só
*depois de perguntada*. Por isso "não sabe" nunca aparece em `opcoes` (não é uma
opção que se ofereça) e só encerra a pergunta em `respondida()` quando
`aceita_nao_sabe` é True. Numa pergunta que o portal não deixa pular — a peça —
"não sabe" **não** encerra nada, e o caso continua faltando.

E a descrição não é pergunta
----------------------------
📊 O passo 4 exige **mínimo de 30 caracteres** em `descrever-acontecimento-textarea`.
Isso é burocracia do portal, não informação nova: pedir a um segurado assustado
que "escreva mais" é exatamente o tipo de pergunta que o produto existe para não
fazer. Então a descrição é **composta** do que já se sabe (peça + relato + data +
local), nunca perguntada — ver `compor_descricao`, que prova aritmeticamente o
mínimo de 30.

💭 Os textos das perguntas são copy ilustrativa (linguagem humana para WhatsApp),
não citáveis como medição. 📊 O que é medido é a *existência* de cada pergunta e
as *opções* que o portal oferece — fonte: captura tela a tela do Founder em
06/07/2026 (Yelum e Tokio), consolidada em
`docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md`, que é a autoridade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# O VOCABULÁRIO DE PEÇA É UM SÓ — e ele já existe.
#
# `identidade_peca` é quem decide se "vidro da porta" e "VIDRO PARABRISA - CARGA"
# são a mesma coisa (não são). Escrever aqui uma segunda tabela de peças seria o
# motor paralelo do CLAUDE.md §5, e o preço dele está medido: 📊 três
# acionamentos de produção casaram 'vidro da porta' com 'VIDRO PARABRISA - CARGA'
# quando um token genérico bastava para decidir.
#
# O precedente é do próprio `portal_worker/adaptive.py`, que importa
# `explicar_match` de lá "em vez de manter um segundo, escrito em JS, que decidia
# diferente do que os testes provavam".
#
# 📊 O import atravessa pacotes e isso foi conferido, não suposto:
# `backend/Dockerfile` faz `COPY . .` com `WORKDIR /app`, então `portal_worker`
# viaja na imagem do backend e é importável de `/app`. E o único ponto que puxa
# esta cadeia (`graph.py` → `portal_tool` → `portal_params`) está dentro de um
# `try/except` que só registra warning: uma falha aqui tira a tool do ar, nunca
# o produto (CLAUDE.md §9.1).
from portal_worker.journeys.vidros_lanternas import identidade_peca

# UMA definição de "vazio disfarçado de resposta". `_tem_valor` já recusa
# `"não informado"` — o preenchimento que o modelo inventa para não deixar campo
# em branco. Duplicar a regra aqui faria o mesmo texto ser resposta de um lado e
# ausência do outro.
from app.services.attendance_ficha import _tem_valor

# --------------------------------------------------------------------------
# De quem é a resposta
# --------------------------------------------------------------------------
DO_SEGURADO = "segurado"    # pergunta-se, em linguagem humana, no WhatsApp
DO_PROVEDOR = "provedor"    # está (ou deveria estar) na InfoCap — NUNCA se pergunta

# O que o segurado responde quando genuinamente não sabe. Só vale depois de a
# pergunta ter sido feita, e só nas perguntas que o portal deixa pular.
NAO_SABE = "nao_sabe"
_SINONIMOS_DE_NAO_SABE = ("nao_sabe", "nao sabe", "não sabe", "nao sei", "não sei",
                          "sei la", "sei lá", "nao lembro", "não lembro")

# 📊 `descrever-acontecimento-textarea`: mín. 30 / máx. 2000 (mapa §4, passo 4).
MINIMO_DA_DESCRICAO = 30
MAXIMO_DA_DESCRICAO = 2000

# --------------------------------------------------------------------------
# Os campos. O nome diz o que ele guarda — um nome que mente reinfecta todo
# leitor seguinte (CLAUDE.md §12.1).
# --------------------------------------------------------------------------
CPF_DO_TITULAR = "cpf_cnpj"
DATA_DO_DANO = "data_dano"
PECA = "peca"
COMO_OCORREU = "como_ocorreu"
ONDE_OCORREU = "onde_ocorreu"
DESCRICAO = "descricao"

PELICULA = "pelicula"
PORTA_DIANTEIRA_OU_TRASEIRA = "porta_dianteira_ou_traseira"
LADO_MOTORISTA_OU_CARONA = "lado_motorista_ou_carona"
POSICAO_DO_TRINCADO = "posicao_do_trincado"
# Guarda "maior"/"menor"/"não sabe" — não um booleano. `trincado_maior_que_10cm`
# mentiria sobre o terceiro valor, que existe e é o mais perigoso dos três.
TAMANHO_DO_TRINCADO = "tamanho_do_trincado"
VERSAO_DO_VEICULO = "versao_do_veiculo"
CEP_DO_SEGURADO = "cep_do_segurado"

# Onde a resposta MORA em `ja_sei`, quando não é na própria chave do campo.
# 📊 A versão sai do campo `Veículo` da InfoCap ("NIVUS COMFORTLINE 1.0 200 TSI
# FLEX AUT") e o CEP do cadastro do cliente — os dois já chegam prontos.
_ONDE_MORA = {
    VERSAO_DO_VEICULO: "veiculo",
    CEP_DO_SEGURADO: "cep",
}


@dataclass(frozen=True)
class Pergunta:
    """Uma pergunta que o portal vai fazer e que ainda não tem resposta.

    `texto` é o que o agente FALA — em português de gente, não em nome de campo.
    `opcoes` são as respostas que o portal aceita (📊 medidas); vazio = texto
    livre. "Não sabe" nunca está em `opcoes`: ela não se oferece, se aceita.
    """

    campo: str
    texto: str
    de_quem: str = DO_SEGURADO
    opcoes: Tuple[str, ...] = ()
    aceita_nao_sabe: bool = False
    porque: str = ""

    @property
    def onde_mora(self) -> str:
        """A chave de `ja_sei` que guarda a resposta desta pergunta."""
        return _ONDE_MORA.get(self.campo, self.campo)


# --------------------------------------------------------------------------
# O catálogo — passo 1, passo 4 e passo 5 do mapa (não dependem da peça)
# --------------------------------------------------------------------------
# Ordem = ordem de conversa, não ordem de tela. O CPF vem primeiro porque é ele
# que destrava a InfoCap, e a InfoCap é que dispensa metade das perguntas. A
# peça vem em seguida porque é dela que nascem as específicas — perguntar
# qualquer específica antes de saber a peça é chutar.
_UNIVERSAIS: Tuple[Pergunta, ...] = (
    Pergunta(
        CPF_DO_TITULAR,
        "Pra eu localizar a apólice, me confirma o CPF do titular do seguro?",
        porque="⚠️ o portal rotula o campo como 'CPF/CNPJ (solicitante)', mas o valor "
               "esperado é o do TITULAR — é assim que a apólice é localizada (mapa §4).",
    ),
    Pergunta(
        PECA,
        "Qual vidro foi? O para-brisa (o da frente), o de uma porta, o de trás — "
        "ou foi outra peça, tipo retrovisor, farol ou lanterna?",
        porque="é a peça que decide TODAS as perguntas do passo 6 (80%).",
    ),
    Pergunta(
        COMO_OCORREU,
        "Me conta como aconteceu? (uma pedra na estrada, alguém quebrou pra furtar, "
        "você chegou e já estava assim...)",
        # 📊 Sem `opcoes` DE PROPÓSITO. A lista de "como ocorreu" MUDA conforme a
        # peça e conforme a seguradora — palavras do Founder: "quando escolho
        # parabrisas vem algumas situações... São diferentes da situação dos
        # vidros laterais". §8.1 do mapa proíbe decorar essa lista: quem casa o
        # relato com a opção real é `match_option`, lendo a tela.
        porque="o relato livre é o que `match_option` casa com a opção real da tela.",
    ),
    Pergunta(
        DATA_DO_DANO,
        "Em que dia isso aconteceu?",
    ),
    Pergunta(
        ONDE_OCORREU,
        "Foi na cidade ou na estrada/rodovia?",
        opcoes=("urbano", "rodoviario"),
        porque="📊 campo `ondeOcorreuDano` do passo 4.",
    ),
    Pergunta(
        CEP_DO_SEGURADO,
        "O CEP do segurado não veio no cadastro da InfoCap. Ele é OPCIONAL no portal, "
        "mas é o que habilita atendimento a domicílio — e domicílio é o que transforma "
        "o serviço em conveniência. NÃO pergunte ao segurado: resolva no cadastro.",
        de_quem=DO_PROVEDOR,
        porque="📊 rótulo do portal: 'Informe seu CEP para encontrarmos a unidade mais "
               "próxima e verificar se há disponibilidade de atendimento em domicílio'.",
    ),
)

# --------------------------------------------------------------------------
# O catálogo — passo 6 (80%), POR PEÇA
# --------------------------------------------------------------------------
# 📊 São condicionais e progressivas no portal: a pergunta 2 só nasce depois da
# 1. Aqui elas vêm todas de uma vez de propósito — perguntar as três na mesma
# conversa custa três mensagens; descobri-las uma a uma dentro do portal custa
# o atendimento inteiro.
#
# A chave é a IDENTIDADE devolvida por `identidade_peca`, não o texto da peça.
# 'vidro de porta', 'vidro da porta' e 'janela' caem todos em `lateral`.
_ESPECIFICAS_POR_IDENTIDADE: Dict[str, Tuple[Pergunta, ...]] = {
    # 📊 Medido em Tokio Marine, para-brisa (captura de 06/07/2026).
    "parabrisa": (
        Pergunta(
            POSICAO_DO_TRINCADO,
            "Onde fica a trinca no para-brisa: bem na frente do motorista, na frente "
            "do carona, no meio, ou perto das bordas?",
            opcoes=("Em frente ao motorista", "Em frente ao carona", "Nas bordas", "No centro"),
            aceita_nao_sabe=True,
        ),
        Pergunta(
            TAMANHO_DO_TRINCADO,
            "A trinca é maior ou menor que 10 cm? (mais ou menos o tamanho de um cartão "
            "de crédito) — é isso que decide se dá pra reparar ou se troca o vidro.",
            opcoes=("Maior que 10 cm", "Menor que 10 cm"),
            aceita_nao_sabe=True,
            porque="📊 maior = troca, menor = possibilidade de reparo. Errar aqui manda "
                   "o vidraceiro com a peça errada (mapa §4c).",
        ),
        Pergunta(
            VERSAO_DO_VEICULO,
            "A versão do veículo (ex.: 'Comfortline') sai do campo `Veículo` da InfoCap "
            "— 'NIVUS COMFORTLINE 1.0 200 TSI FLEX AUT'. A InfoCap não trouxe o veículo: "
            "isso é lacuna do provedor. NUNCA pergunte a versão ao segurado.",
            de_quem=DO_PROVEDOR,
            aceita_nao_sabe=True,
            porque="📊 'A versão do veículo é comfortline?' é pergunta de APÓLICE "
                   "disfarçada de pergunta de dano (mapa §4b).",
        ),
    ),
    # 📊 Medido em Yelum, vidro de porta (captura de 06/07/2026).
    #
    # INFERÊNCIA declarada: o portal mediu "VIDRO DE PORTA"; `identidade_peca`
    # junta porta, janela, basculante e ventarola sob `lateral`. Aplicamos as
    # três perguntas a toda a família. O erro possível é perguntar uma a mais
    # (custa uma mensagem, e a resposta é ignorada se a tela não pedir); o erro
    # oposto — não perguntar — é o que produziu 📊 33 paradas.
    "lateral": (
        Pergunta(
            PELICULA,
            "Esse vidro tem película? (aquele filme escuro, o insulfilm)",
            opcoes=("SIM", "NÃO"),
            aceita_nao_sabe=True,
        ),
        Pergunta(
            PORTA_DIANTEIRA_OU_TRASEIRA,
            "É o vidro da porta da frente ou o da porta de trás?",
            opcoes=("DIANTEIRA", "TRASEIRA"),
            aceita_nao_sabe=True,
        ),
        Pergunta(
            LADO_MOTORISTA_OU_CARONA,
            "É do lado do motorista ou do lado do carona? (se quebraram os dois lados, "
            "me avisa — cada lado é um pedido separado)",
            opcoes=("Lado do motorista", "Lado do carona"),
            aceita_nao_sabe=True,
            porque="📊 o portal aceita UM item por atendimento e manda abrir nova "
                   "solicitação para o outro lado (mapa §3). O aviso vai junto da "
                   "pergunta porque é o único momento em que ele chega a tempo.",
        ),
    ),
}

# 📊 O que NÃO foi medido (mapa §7): as específicas de retrovisor, farol,
# lanterna, vigia e teto. Elas não estão aqui, e a ausência é a informação —
# `especificas_mapeadas()` devolve False e a mensagem ao agente diz isso em voz
# alta. Preencher esta tabela por dedução seria inventar pergunta.
PECAS_SEM_ESPECIFICAS_MAPEADAS = ("vigia", "retrovisor", "farol", "lanterna", "teto")


# --------------------------------------------------------------------------
# Respondida, não respondida, e o "não sabe" no meio
# --------------------------------------------------------------------------
def e_nao_sabe(valor: Any) -> bool:
    """O segurado disse que não sabe (em qualquer das formas que ele usa)."""
    return str(valor or "").strip().lower() in _SINONIMOS_DE_NAO_SABE


def respondida(valor: Any, aceita_nao_sabe: bool = False) -> bool:
    """A pergunta já tem resposta?

    Três estados, e o do meio é o que costuma sumir:

      ausente      → não foi perguntada. Falta.
      "não sabe"   → FOI perguntada, e o segurado não sabe. Só encerra a pergunta
                     se o portal oferecer essa saída (`aceita_nao_sabe`).
      um valor     → respondida.

    A peça é o caso em que a distinção decide o atendimento: "não sei qual vidro
    quebrou" não é uma resposta que o portal aceite — é um caso para gente.
    """
    if not _tem_valor(valor):
        return False
    if e_nao_sabe(valor):
        return bool(aceita_nao_sabe)
    return True


# --------------------------------------------------------------------------
# A peça e suas específicas
# --------------------------------------------------------------------------
def _identidades(peca: str) -> List[str]:
    return sorted(identidade_peca(str(peca or "")))


def especificas_mapeadas(peca: str) -> bool:
    """As perguntas do 80% desta peça foram MEDIDAS?

    False para peça vazia, para peça ambígua ("luz" pode ser farol ou lanterna) e
    para toda peça de `PECAS_SEM_ESPECIFICAS_MAPEADAS`. False **não** é erro nem
    bloqueio: é a declaração honesta de que o caminho adaptativo vai ler a tela
    real e descobrir ali.
    """
    ids = _identidades(peca)
    return len(ids) == 1 and ids[0] in _ESPECIFICAS_POR_IDENTIDADE


def especificas_da_peca(peca: str) -> Tuple[Pergunta, ...]:
    """As perguntas do 80% que ESTA peça faz nascer. Vazio quando não mapeadas."""
    ids = _identidades(peca)
    if len(ids) != 1:
        return ()
    return _ESPECIFICAS_POR_IDENTIDADE.get(ids[0], ())


def peca_ambigua(peca: str) -> bool:
    """O texto nomeia mais de uma peça ("a luz quebrou" = farol ou lanterna)."""
    return len(_identidades(peca)) > 1


def peca_conhecida(peca: str) -> bool:
    """O vocabulário único consegue dizer QUAL peça é?

    Exatamente uma identidade. Duas outras respostas, e as duas continuam sendo
    pergunta:

      **zero** — o texto não nomeia peça nenhuma. `"quebrou o vidro"` é o relato
      mais comum que existe e cai aqui: num portal de vidros, "vidro" é o nome
      do balcão, não o da peça.

      **mais de uma** — ambígua. `"a luz quebrou"` é farol ou lanterna.

    Um texto que não identifica peça não é uma peça respondida: é o problema
    adiado até o dropdown do passo 4, onde `match_option` para. 📊 E quando ele
    NÃO parou, o estrago foi pior: três acionamentos de produção casaram
    'vidro da porta' com 'VIDRO PARABRISA - CARGA' porque um token genérico
    bastava. Uma frase agora custa dez segundos; o dropdown custa o atendimento.
    """
    return len(_identidades(peca)) == 1


# --------------------------------------------------------------------------
# O coração
# --------------------------------------------------------------------------
def o_que_falta(peca: str, ja_sei: Optional[Dict[str, Any]] = None) -> List[Pergunta]:
    """O que ainda precisa ser perguntado para este acionamento NÃO travar.

    `peca` é o que o segurado disse que quebrou (texto livre; vazio se ainda não
    se sabe). `ja_sei` é tudo que já se apurou — o que o segurado respondeu MAIS
    os fatos que a InfoCap trouxe (`veiculo`, `cep`).

    Devolve as perguntas na ordem de conversa. Lista vazia = pode entrar no
    portal: nada do que ele vai perguntar está em aberto.

    Três regras que a assinatura não mostra:

    **A peça manda.** Sem peça (ou com peça ambígua), as específicas não entram —
    não porque sejam opcionais, mas porque não há como saber quais são.

    **Peça não mapeada não bloqueia.** Retrovisor, farol, lanterna, vigia e teto
    voltam só com as universais. Ver `especificas_mapeadas`.

    **A descrição não é pergunta.** Ela é composta (`compor_descricao`), e o
    mínimo de 30 caracteres do portal fica garantido por construção assim que
    peça e relato existem — que são duas perguntas desta lista.
    """
    ja_sei = dict(ja_sei or {})
    peca = str(peca or ja_sei.get(PECA) or "").strip()
    ja_sei.setdefault(PECA, peca)

    faltam: List[Pergunta] = []
    for pergunta in _UNIVERSAIS:
        if pergunta.campo == PECA:
            # A peça não se dá por respondida porque o campo tem texto: ela se
            # dá por respondida quando o vocabulário ÚNICO consegue identificá-la
            # (ver `peca_conhecida`). Um texto que não nomeia peça é o problema
            # adiado até o dropdown.
            if not peca_conhecida(peca):
                faltam.append(pergunta)
            continue
        if not respondida(ja_sei.get(pergunta.onde_mora), pergunta.aceita_nao_sabe):
            faltam.append(pergunta)

    # Sem peça identificada as específicas não entram — não por serem opcionais,
    # mas porque não há como saber quais são.
    if not peca_conhecida(peca):
        return faltam

    for pergunta in especificas_da_peca(peca):
        if not respondida(ja_sei.get(pergunta.onde_mora), pergunta.aceita_nao_sabe):
            faltam.append(pergunta)
    return faltam


def para_o_segurado(faltam: List[Pergunta]) -> List[Pergunta]:
    """Só o que se pergunta a uma pessoa. Lacuna de provedor NUNCA vira mensagem
    de WhatsApp — é o que impede o produto de pedir ao segurado a versão do carro
    dele, que já está na apólice."""
    return [p for p in (faltam or []) if p.de_quem == DO_SEGURADO]


def lacunas_do_provedor(faltam: List[Pergunta]) -> List[Pergunta]:
    """O que a InfoCap deveria ter trazido e não trouxe. É trabalho da corretora
    ou da integração, não do segurado."""
    return [p for p in (faltam or []) if p.de_quem == DO_PROVEDOR]


# --------------------------------------------------------------------------
# A descrição — composta, nunca perguntada
# --------------------------------------------------------------------------
def compor_descricao(ja_sei: Optional[Dict[str, Any]] = None) -> str:
    """O texto do passo 4, montado só com o que já se sabe.

    📊 O portal exige mínimo de 30 e máximo de 2000 caracteres. Pedir ao segurado
    que "escreva mais" para satisfazer um contador de caracteres é a pergunta que
    este produto existe para não fazer — então a descrição é DERIVADA.

    Nada é inventado: entram a peça (como ele a nomeou), o relato dele, a data e
    o local. Se o relato já passa de 30 caracteres, ele vai inteiro, com as
    palavras do segurado.

    O mínimo é garantido por aritmética, não por sorte: com peça e relato
    presentes o texto começa em `"Dano em " + peça + ". O segurado relatou: " +
    relato + "."` = 8+1+1 + 1 + 20+1+1 = **33 caracteres no pior caso**. E peça e
    relato (`como_ocorreu`) são duas perguntas de `o_que_falta` — quando elas
    estão respondidas, o mínimo está pago.
    """
    ja_sei = ja_sei or {}
    relato = str(ja_sei.get(DESCRICAO) or "").strip()
    if len(relato) >= MINIMO_DA_DESCRICAO:
        return relato[:MAXIMO_DA_DESCRICAO]

    if not relato:
        relato = str(ja_sei.get(COMO_OCORREU) or "").strip()

    partes: List[str] = []
    peca = str(ja_sei.get(PECA) or "").strip()
    if peca:
        partes.append(f"Dano em {peca}.")
    if relato:
        partes.append(f"O segurado relatou: {relato}.")
    data = str(ja_sei.get(DATA_DO_DANO) or "").strip()
    if data:
        partes.append(f"Ocorrido em {data}.")
    onde = str(ja_sei.get(ONDE_OCORREU) or "").strip()
    if onde:
        partes.append(f"Local: {onde}.")
    return " ".join(partes)[:MAXIMO_DA_DESCRICAO]


# --------------------------------------------------------------------------
# A mensagem que o agente lê
# --------------------------------------------------------------------------
def _marca_nao_sabe(pergunta: Pergunta) -> str:
    """A saída de "não sabe" só se anuncia na pergunta que a tem."""
    return "   [se ele nao souber, registre 'nao sabe']" if pergunta.aceita_nao_sabe else ""


def mensagem_para_o_agente(faltam: List[Pergunta], peca: str = "") -> str:
    """Traduz a lista em ordem de trabalho para o LLM. "" quando não há nada a dizer.

    Uma pergunta em destaque (a próxima), o resto listado para ele coletar na
    mesma conversa, e as duas proibições que o mapa impõe: não perguntar o que
    está na apólice, e não inventar pergunta para peça não mapeada.

    Uma de cada vez é instrução literal: 📊 o passo 6 do portal revela as
    perguntas uma a uma, e um segurado que recebe três perguntas numa mensagem
    responde uma.
    """
    faltam = list(faltam or [])
    perguntas = para_o_segurado(faltam)
    lacunas = lacunas_do_provedor(faltam)
    if not perguntas and not lacunas and especificas_mapeadas(peca):
        return ""

    linhas: List[str] = []
    if perguntas:
        linhas.append(
            f"Faltam dados do acionamento: ainda nao da para abrir o portal "
            f"({len(perguntas)} pergunta(s) em aberto). Colete TUDO nesta conversa, "
            "uma pergunta por mensagem, antes de me chamar de novo — depois que o "
            "portal abre, cada dado que falta custa o atendimento inteiro."
        )
        linhas.append("")
        linhas.append("PERGUNTE AGORA (use estas palavras, ou palavras tao simples quanto):")
        linhas.append(f'  "{perguntas[0].texto}"{_marca_nao_sabe(perguntas[0])}')
        if perguntas[0].opcoes:
            linhas.append(f"  respostas que o portal aceita: {' / '.join(perguntas[0].opcoes)}")
        if len(perguntas) > 1:
            linhas.append("")
            linhas.append("E na sequencia, uma de cada vez, ainda vou precisar destas:")
            for p in perguntas[1:]:
                linhas.append(f'  · "{p.texto}"{_marca_nao_sabe(p)}')
        linhas.append("")
        # A marca vai POR PERGUNTA, e nao numa frase geral, porque a frase geral
        # criava um laco: mandada em bloco, ela autoriza registrar "nao sabe" em
        # `como_ocorreu` — que o portal NAO deixa pular. O agente registraria,
        # este mesmo gate recusaria, e a pergunta voltaria para sempre.
        linhas.append(
            "Onde estiver escrito [se ele nao souber...], essa e a saida legitima — e SO "
            "depois de perguntar: responder 'nao sabe' por conta propria degrada o servico "
            "(o portal deixa de saber qual vidro pedir). Nas perguntas SEM essa marca a "
            "saida nao existe: reformule com exemplos concretos, porque registrar 'nao "
            "sabe' nelas traz o acionamento de volta para a mesma pergunta."
        )

    if lacunas:
        linhas.append("")
        linhas.append("NAO pergunte ao segurado (isto e lacuna do cadastro, nao dele):")
        for p in lacunas:
            linhas.append(f"  · {p.texto}")

    if peca and not especificas_mapeadas(peca):
        linhas.append("")
        if peca_ambigua(peca):
            linhas.append(
                f"A peca '{peca}' esta AMBIGUA (pode ser mais de uma coisa) — confirme "
                "com o segurado exatamente qual peca quebrou antes de me chamar."
            )
        elif peca_conhecida(peca):
            linhas.append(
                f"As perguntas especificas de '{peca}' AINDA NAO FORAM MAPEADAS neste "
                "portal. NAO invente nenhuma: o robo vai ler a tela real e, se ela "
                "perguntar algo que eu nao tenho, eu volto e te digo exatamente o que "
                "perguntar."
            )
        else:
            # DIZER POR QUE a peca voltou. Sem esta frase o agente ve que mandou
            # `peca` e que estou pedindo `peca` de novo, conclui que e ruido, e
            # reenvia o MESMO texto — o laco que nenhuma recusa pode criar.
            #
            # E nao chamar isto de "peca nao mapeada" tambem importa: 'quebrou o
            # vidro' nao e uma peca sem mapa, e um texto que nao nomeia peca
            # nenhuma. Confundir os dois faria o agente esperar que eu lesse a
            # tela para descobrir algo que so o segurado sabe.
            linhas.append(
                f"Voce me mandou peca='{peca}', e isso NAO nomeia uma peca: num portal de "
                "vidros, 'vidro' e o nome do balcao, nao da peca. Nao reenvie o mesmo "
                "texto — pergunte QUAL vidro (para-brisa, de porta, vigia) ou qual peca "
                "(retrovisor, farol, lanterna, teto)."
            )

    linhas.append("")
    linhas.append(
        "Nunca pergunte ao segurado o que esta na apolice: placa, chassi, versao do "
        "veiculo, CEP e endereco eu ja busco sozinho na InfoCap."
    )
    return "\n".join(linhas).strip()
