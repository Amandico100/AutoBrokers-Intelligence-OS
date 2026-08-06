"""Da carta crua ao RAG: junta o repetido, barra o absoluto, publica o resto.

Por que isto roda sozinho
-------------------------
O Founder não é especialista em seguros e não tem como ler 1.441 fatos um a
um — e em 29/07/2026 chegam as centenas da AutoFleet. A revisão que importa
aqui é a de PII, e ela é **determinística**: `templatize` mascara na extração,
a LLM é instruída a não citar pessoa, e `_card_pii_clean` reconfere no momento
exato da publicação. Três camadas, nenhuma dependendo de alguém lembrar.

O que sobra para o humano é o que só o humano decide: rejeitar um fato que ele
sabe estar errado. Isso continua em /admin/espelho, e rejeitar tira do RAG.

As três coisas que este módulo faz
----------------------------------
**1. Junta o que diz a mesma coisa.** O `card_hash` só pega texto idêntico.
Ninguém escreve a mesma frase duas vezes — escreve a mesma ideia de vinte
jeitos:

    "Quando o pagamento EM cartão não é autorizado, a seguradora gera boleto…"
    "Quando o pagamento NO cartão não é autorizado, a seguradora gera boleto…"

No RAG isso é veneno: o agente busca "cartão recusado", recebe quinze
quase-cópias e gasta todo o orçamento de contexto com uma ideia só.

O limiar de 0,47 foi MEDIDO amostrando a faixa par a par: em 0,45 apareceu um
falso positivo real ("boletos são enviados ao segurado" × "alterações de forma
de pagamento"). E só junta dentro da MESMA seguradora — "a HDI gera boleto"
não é a mesma informação que a genérica, é ela que dá confiança ao agente
quando o segurado é da HDI.

**2. Barra promessa absoluta.** Em seguro quase tudo tem exceção. Um agente
repetindo "sem possibilidade de recuperação" faz a corretora prometer o que
não pode cumprir — ainda mais quando existe outra carta dizendo que
comprovante permite pedir reanálise.

**3. Publica com CONTEXTO no próprio texto.** O chunk vai para o Qdrant como

    (hdi / auto / cobrança) Quando a parcela do cartão não é autorizada…

O assunto entra no texto de propósito: a busca é híbrida, e o BM25 casa por
palavra exata. Sem "cobrança" ali, uma pergunta sobre boleto disputa espaço em
igualdade com uma carta de vistoria que por acaso menciona pagamento.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

LIMIAR = 0.47

_VAZIAS = {
    "as", "os", "das", "dos", "ele", "ela", "com", "sem", "que", "ser", "sao",
    "tem", "uma", "uns", "umas", "para", "por", "nao", "sim", "seu", "sua",
    "seus", "suas", "este", "esta", "isso", "pode", "podem", "deve", "devem",
    "ate", "apos", "quando", "caso", "mesmo", "sobre", "entre", "mais", "menos",
    "muito", "pouco", "comum", "possivel", "necessario", "the", "and", "esse",
    "essa", "como", "onde", "qual", "quais", "todo", "toda", "todos", "todas",
    "apenas", "tambem",
}

_ABSOLUTO = re.compile(
    r"sem possibilidade de|nunca (?:e|é|sera|será) (?:coberto|pago|aceito|possivel|possível)"
    r"|sempre (?:e|é) (?:coberto|pago|aceito|garantido)|em hip[óo]tese alguma|jamais"
    r"|imposs[íi]vel recuperar|garantidamente|sem exce[çc][ãa]o",
    re.IGNORECASE)

# O ASSUNTO DA CARTA — CINCO MOMENTOS DO TRABALHO, e nada além disso.
#
# A lista anterior tinha sete valores e misturava duas perguntas diferentes:
# MOMENTO (sinistro, cobrança) com ARTEFATO (documentos, vistoria). Um artefato
# atravessa todos os momentos — CNH aparece em sinistro, comprovante aparece em
# cobrança, laudo aparece em vistoria prévia e em regulação — então a carta caía
# na gaveta que o regex alcançasse primeiro, não na que descreve o trabalho.
#
# 📊 05/08/2026, medido sobre as 10.818 published (`medir7.py`/`medir8.py`, com
# linha de CONTROLE repetindo a rodada anterior em cada passo):
#
#     lista antiga (7 valores)   3.891 cartas (36,0%) casavam DOIS ou mais
#     lista nova   (5 momentos)  3.188 cartas (29,5%)
#
# O ganho não está no número — está em QUEM empata. No empate antigo, "carta de
# vistoria" disputava com "carta de sinistro": artefato contra momento, e não
# existe ordem defensável entre os dois. No empate novo disputam dois momentos
# reais (o guincho veio depois da colisão), e aí a ordem se explica em uma
# frase. Empate resolvido por regra escrita é decisão; resolvido por ordem de
# digitação é sorte.
#
# A ORDEM, e por que ela é esta:
#   sinistro     primeiro porque é o momento que engole os outros — o boleto da
#                franquia e o guincho do acidente são do sinistro, não da
#                cobrança nem da assistência.
#   cobranca     antes de apólice porque cancelamento por falta de pagamento é
#                assunto de dinheiro; quem procura isso digita "boleto".
#   assistencia  o serviço na rua quando não houve sinistro (chaveiro, pane).
#   apolice      o contrato: emissão, endosso, vigência, cobertura, renovação.
#   atendimento  CATCH-ALL, e SEMPRE o último. É o nome honesto do que sobra:
#                prática de corretora, canal, prazo de resposta, conduta.
#                📊 fica com 1.266 cartas (11,7%) — o conselheiro previu 11,4%.
#
# O catch-all é nomeado de propósito. `processo` — o valor que ficou em 100%
# das 11.640 cartas — não diz nada a ninguém: nem ao corretor que busca, nem ao
# BM25 que indexa o prefixo, nem a quem lê a tabela.
_ASSUNTOS: List[Tuple[str, re.Pattern]] = [
    # `vistoria` mora aqui, e não em apólice, porque NESTE acervo ela é
    # esmagadoramente do sinistro: vidro, funilaria, dano elétrico, regulação.
    # 📊 Testado com vistoria em apólice: das 4 cartas conferidas na amostra, 3
    # eram claramente de sinistro ("depois que o segurado passa na loja para a
    # vistoria"). A vistoria PRÉVIA — a do contrato — sai pelo lookahead e cai
    # em apólice, que é o único lugar onde ela faz sentido.
    ("sinistro", re.compile(
        r"sinistro|regulad|perito|per[íi]cia|colis|batida|roubo|furto|avaria"
        r"|indeniza|salvado|perda total|sucata|vendaval|alagament|granizo"
        r"|boletim de ocorr[êe]ncia|terceiro envolvido|oficina|dpvat|guincho de acidente"
        r"|dano|reembolso|pe[çc]a|conserto|preju[íi]zo|laudo|inspe[çc]"
        r"|vistoria(?! pr[ée]via)", re.I)),
    ("cobranca", re.compile(
        r"boleto|parcela|cobran|pagament|cart[ãa]o|pix|d[ée]bito autom|inadimpl"
        r"|vencimento|juros|fatura|qrcode|carn[êe]|quita|estorno|reprograma"
        r"|pr[êe]mio|baixa do pag|linha digit[áa]vel", re.I)),
    ("assistencia", re.compile(
        r"guincho|reboque|chaveiro|encanador|eletricista|desentup|pane seca"
        r"|assist[êe]ncia|prestador|carro reserva|t[áa]xi|vidraceiro|borracheiro"
        r"|hidr[áa]ulic|funeral|residencial 24|leva e traz", re.I)),
    ("apolice", re.compile(
        r"ap[óo]lice|endosso|vig[êe]ncia|cobertura|franquia|renova|proposta"
        r"|emiss[ãa]o|emitir|importância segurada|import[âa]ncia segurada|susep"
        r"|cancelament|cancelad|cancelar|rescis|vistoria pr[ée]via|contrata", re.I)),
]

# O nome do catch-all vive aqui porque quem lê a lista precisa vê-lo: ele não
# é "nenhum dos anteriores", é um assunto com significado próprio.
ASSUNTO_PADRAO = "atendimento"

ASSUNTOS_VALIDOS = tuple([nome for nome, _ in _ASSUNTOS] + [ASSUNTO_PADRAO])


def assunto_da_carta(texto: str) -> str:
    """Em que gaveta esta carta mora. Determinístico, sem modelo."""
    for nome, rx in _ASSUNTOS:
        if rx.search(str(texto or "")):
            return nome
    return ASSUNTO_PADRAO


def _sem_acento(t: str) -> str:
    n = unicodedata.normalize("NFKD", str(t or ""))
    return "".join(c for c in n if not unicodedata.combining(c))


# ------------------------------------------------------------------ #
# DE QUEM É A REGRA — a única resposta, usada por todos os caminhos
# ------------------------------------------------------------------ #
#
# O defeito que esta seção conserta
# ---------------------------------
# `attendance_distiller` carimbava em ATÉ OITO fatos a seguradora da SESSÃO
# INTEIRA. O campo guardava "este fato apareceu numa conversa sobre a Allianz"
# e o nome prometia "este fato é regra da Allianz". São coisas diferentes, e a
# diferença só fica barata enquanto ninguém filtra por seguradora.
#
# 📊 05/08/2026, medido nas 3.354 published etiquetadas: só 1.083 (32,3%)
# citam a própria seguradora no texto. As outras 2.271 são fato genérico de
# mercado usando a companhia da conversa como rótulo — inclusive uma carta de
# seguro PET gravada como `allianz` / `auto`.
#
# As TRÊS perguntas, nesta ordem
# ------------------------------
# 1. **É seguradora?**  A resposta mora em `_INSURER_ALIASES`, no
#    `corridor_playbooks` — uma tabela só. `autoglass`, `mondial`, `hantei` e
#    `crawford` aparecem NO TEXTO da carta e mesmo assim não podem ficar aqui:
#    a Autoglass atende várias seguradoras, e arquivar a regra dela sob uma
#    companhia faz o filtro devolver a errada. Prestadora vai para `prestadora`.
# 2. **O texto a nomeia?**  Sem o nome escrito, a carta é do mercado.
# 3. **Nomeia como DONA, ou como exemplo?**  "Na Allianz o boleto…" é regra da
#    Allianz. "…nesta conversa foi num endosso da Porto" é exemplo. E "o BANCO
#    Bradesco passou a exigir autorização" é o banco, não a seguradora.

# Nome de seguradora que também é palavra comum do português.
#
# 📊 `caixa` aparece 80 vezes nas published e 31 delas são "caixa d'água" (a
# assistência residencial limpa caixa d'água). Aceitar a palavra solta como
# menção à Caixa Seguradora etiquetaria 48 cartas de assistência residencial
# com uma companhia que não tem nada a ver com elas. Só conta com qualificador.
_NOME_AMBIGUO = {"caixa"}

# QUEM ATENDE PELA SEGURADORA — e por isso NÃO é a seguradora.
#
# Uma prestadora atende várias companhias ao mesmo tempo. `resulta` e
# `autofleet` são as próprias corretoras, que também não são seguradoras.
# Estas chaves saem de `insurer_key` e vão para `pii_check.prestadora`, onde
# a informação continua existindo sem mentir sobre o que é.
_PRESTADORAS = {
    "autoglass": "autoglass", "maxpar": "autoglass",
    "mondial": "mondial", "mondial assistance": "mondial",
    "crawford": "crawford", "crawford brasil": "crawford",
    "hantei": "hantei",
    "ativa": "ativa", "ativa assistencia": "ativa", "ativa assistência": "ativa",
    "resulta": "resulta", "autofleet": "autofleet",
}

# Marcadores de EXEMPLIFICAÇÃO — a carta cita a companhia como ilustração.
#
# 📊 A lista é curta de propósito. "nesse caso" (113 cartas) e "por exemplo"
# (61) parecem marcadores e não são: em "Nesse caso a AXA gera boleto novo", a
# AXA é quem age — o "nesse caso" retoma a situação da frase anterior, não
# transforma a AXA em exemplo. Um marcador largo rebaixaria ~130 rótulos
# CORRETOS. O que marca exemplo é a referência à própria conversa.
_EXEMPLIFICA = re.compile(
    r"\b(nest[ae] conversa|ness[ae] conversa|num[ae]? conversa|nest[ae] atendimento"
    r"|nest[ae] sess[ãa]o|num caso|num atendimento|numa apolice|num endosso"
    r"|por exemplo|ex\.:|exemplo:|como (?:na|no)\b|foi num|foi numa)\b")

# "o banco Bradesco" é o BANCO. Bradesco Seguros é outra empresa, e a regra de
# um não é a regra do outro.
_BANCO_ANTES = re.compile(r"\bbanco\s*$")


def _formas_da_seguradora(chave: str) -> List[str]:
    """Como esta companhia pode estar ESCRITA numa carta.

    Sai da mesma `_INSURER_ALIASES` que normaliza a chave — reescrever os
    apelidos aqui criaria a tabela paralela que o CLAUDE.md §5 proíbe, e a
    cópia que ninguém olha é sempre a que envelhece primeiro.
    """
    from app.services.corridor_playbooks import _INSURER_ALIASES

    formas = [a for a, k in _INSURER_ALIASES.items()
              if k == chave and a not in _NOME_AMBIGUO]
    if not formas:
        formas = [chave] if chave not in _NOME_AMBIGUO else []
    return sorted(set(formas), key=len, reverse=True)


def texto_nomeia_seguradora(texto: str, chave: str) -> bool:
    """A carta nomeia esta companhia como DONA da regra?

    Não basta o nome aparecer: ele tem de aparecer fora de um trecho de
    exemplificação e fora de "o banco X". A oração é a unidade — o que separa
    "Na Porto o boleto…" de "…; nesta conversa foi num endosso da Porto" é o
    pedaço de frase em que o nome está, não a carta inteira.
    """
    alvo = _sem_acento(str(texto or "")).lower()
    for forma in _formas_da_seguradora(str(chave or "")):
        for m in re.finditer(rf"\b{re.escape(_sem_acento(forma).lower())}\b", alvo):
            # A oração: do último separador forte até a menção.
            ini = max((alvo.rfind(s, 0, m.start()) for s in (";", ":", " - ", " — ")),
                      default=-1)
            oracao = alvo[ini + 1:m.start()]
            if _BANCO_ANTES.search(oracao) or _EXEMPLIFICA.search(oracao):
                continue
            return True
    return False


def seguradora_do_fato(texto: str, seguradora_bruta: Any) -> Tuple[Optional[str], Optional[str]]:
    """(insurer_key, prestadora) para uma carta. Ambos podem ser None.

    Esta é a ÚNICA resposta do sistema para "de quem é esta regra". O
    destilador, o script de atribuição por consenso e a limpeza do acervo
    passam por aqui — se a regra melhorar, melhora nos três no mesmo commit.

    `seguradora_bruta` é o que a conversa disse (o campo da sessão, ou o
    rótulo que já está gravado). Ela só vira `insurer_key` se for seguradora
    conhecida E o texto do FATO a nomear.
    """
    from app.services.corridor_playbooks import _INSURER_ALIASES, normalize_insurer_key

    bruto = str(seguradora_bruta or "").strip().lower()
    if not bruto:
        return None, None

    # Chave composta é fato de VÁRIAS companhias — logo, de nenhuma. O
    # normalizador devolveria a primeira que casasse ("mapfre/yelum/ezze" vira
    # `yelum` pela ordem do dicionário, que não é decisão de ninguém).
    if re.search(r"[/;+]| e | ou ", bruto):
        return None, None

    chave = normalize_insurer_key(bruto, para="conhecimento")
    if chave in _PRESTADORAS or bruto in _PRESTADORAS:
        return None, _PRESTADORAS.get(chave) or _PRESTADORAS[bruto]
    if chave not in set(_INSURER_ALIASES.values()):
        return None, None
    return (chave, None) if texto_nomeia_seguradora(texto, chave) else (None, None)


def assinatura(texto: str) -> frozenset:
    limpo = re.sub(r"[^a-z0-9\s]", " ", _sem_acento(texto).lower())
    return frozenset(p[:6] for p in limpo.split() if len(p) > 2 and p not in _VAZIAS)


def parecidas(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _riqueza(c: Dict[str, Any]) -> Tuple[int, int]:
    return (len(assinatura(c.get("card_text") or "")), len(c.get("card_text") or ""))


def escolher_representantes(cartas: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """(ficam, sao_copias). Só junta cartas da MESMA seguradora."""
    por_seg: Dict[Optional[str], List[Dict[str, Any]]] = {}
    for c in cartas:
        por_seg.setdefault(c.get("insurer_key"), []).append(c)

    ficam: List[str] = []
    copias: List[str] = []
    for grupo in por_seg.values():
        grupo = sorted(grupo, key=_riqueza, reverse=True)
        guardadas: List[frozenset] = []
        for c in grupo:
            sig = assinatura(c.get("card_text") or "")
            if len(sig) < 3:
                ficam.append(c["id"])       # curta demais para comparar: fica
                continue
            if any(parecidas(sig, g) >= LIMIAR for g in guardadas):
                copias.append(c["id"])
            else:
                guardadas.append(sig)
                ficam.append(c["id"])
    return ficam, copias


def curar_sync(aplicar: bool = True) -> Dict[str, Any]:
    """Junta as quase-cópias e barra os absolutos. Sem LLM, sem custo."""
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    cartas: List[Dict[str, Any]] = []
    inicio = 0
    while True:
        lote = (db.client.table("knowledge_cards")
                .select("id, card_text, insurer_key, ramo")
                .eq("status", "pending_review")
                # PAGINAR POR CHAVE QUE EMPATA PERDE LINHA.
                #
                # `created_at` empata: a destilação grava as até oito cartas de
                # uma sessão no mesmo instante, e o Postgres não promete ordem
                # entre iguais. Duas páginas seguidas podem repetir uma linha e
                # nunca mostrar outra.
                #
                # 📊 Medido em 05/08/2026 baixando o acervo com esta mesma
                # paginação: 11.640 linhas lidas, 11.628 hashes distintos — 12
                # repetidas e 12 que nunca apareceram. Numa curadoria, a carta
                # que não aparece é a quase-cópia que fica no RAG para sempre.
                # `id` é único, então não há empate para o banco desfazer.
                .order("id", desc=False)
                .range(inicio, inicio + 999).execute().data) or []
        cartas.extend(lote)
        if len(lote) < 1000:
            break
        inicio += 1000

    barradas = [c["id"] for c in cartas if _ABSOLUTO.search(c.get("card_text") or "")]
    proibidos = set(barradas)
    ficam, copias = escolher_representantes([c for c in cartas if c["id"] not in proibidos])

    if aplicar:
        for ids, status in ((barradas, "rejected_absoluto"), (copias, "superseded")):
            for i in range(0, len(ids), 100):
                db.client.table("knowledge_cards").update({"status": status}) \
                    .in_("id", ids[i:i + 100]).execute()

    return {"lidas": len(cartas), "barradas": len(barradas),
            "juntadas": len(copias), "ideias_distintas": len(ficam), "aplicado": aplicar}


def reconciliar_indice_sync(limite: int = 500) -> Dict[str, int]:
    """Tira do Qdrant os pontos de cartas que já não estão publicadas.

    Por que o banco sozinho não resolve
    -----------------------------------
    Despublicar são dois movimentos: mudar o status e apagar o vetor. Quem muda
    o status é o banco; quem apaga o vetor é o Qdrant. Quando o segundo falha —
    rede, credencial ausente, script rodando fora do servidor — o primeiro já
    aconteceu, e sobra o pior estado possível: uma carta que a auditoria vê como
    removida e a busca continua entregando.

    Marcar `qdrant_pendente` no lugar de fingir sucesso transforma essa falha em
    trabalho pendente. Aqui ela é feita, com a credencial de quem roda no
    servidor, e a marca sai.
    """
    from app.core.database import get_supabase_client
    from app.services.attendance_distiller import despublicar_carta_sync

    db = get_supabase_client()
    pendentes = (db.client.table("knowledge_cards").select("id, status")
                 .eq("pii_check->>qdrant_pendente", "true")
                 .limit(max(1, min(int(limite or 500), 2000))).execute().data) or []

    limpas = falhas = 0
    for c in pendentes:
        try:
            # `despublicar_carta_sync` já apaga o ponto e, se conseguir, grava o
            # status. Aqui o status certo já está no banco, então só interessa
            # que o ponto saia; passar o status atual evita reescrevê-lo.
            if despublicar_carta_sync(str(c["id"]), motivo=str(c.get("status") or "superseded")):
                atual = (db.client.table("knowledge_cards").select("pii_check")
                         .eq("id", c["id"]).limit(1).execute().data or [{}])
                marca = dict((atual[0] or {}).get("pii_check") or {})
                marca.pop("qdrant_pendente", None)
                db.client.table("knowledge_cards").update(
                    {"pii_check": marca}).eq("id", c["id"]).execute()
                limpas += 1
            else:
                falhas += 1
        except Exception as exc:  # noqa: BLE001 — um ponto ruim não trava o resto
            falhas += 1
            logger.warning("[CARTAS] reconciliação falhou em %s: %s",
                           c["id"], type(exc).__name__)

    if limpas or falhas:
        logger.info("[CARTAS] reconciliação: %d pontos removidos · %d pendentes",
                    limpas, falhas)
    return {"limpas": limpas, "falhas": falhas, "pendentes": len(pendentes)}


def publicar_lote_sync(limite: int = 300) -> Dict[str, Any]:
    """Publica no RAG global as cartas que sobraram da curadoria.

    Uma de cada vez, marcando logo depois: se a rodada cair no meio, o que já
    foi publicado está marcado e a próxima continua de onde parou — nunca
    republica nem deixa metade sem ninguém saber qual metade.

    Antes de publicar, reconcilia: carta errada que ficou no índice responde
    junto com a certa que a substitui, e a busca não sabe qual das duas é a boa.
    Tirar a velha primeiro é mais importante que colocar a nova.
    """
    from app.core.database import get_supabase_client
    from app.services.attendance_distiller import publish_card_sync

    db = get_supabase_client()
    reconciliado = reconciliar_indice_sync()
    alvo = (db.client.table("knowledge_cards")
            .select("id, card_text, insurer_key, ramo")
            .eq("status", "pending_review")
            .order("created_at", desc=False)
            .limit(max(1, min(int(limite or 300), 2000))).execute().data) or []

    publicadas = falhas = 0
    for c in alvo:
        try:
            if publish_card_sync(c):
                from datetime import datetime, timezone

                db.client.table("knowledge_cards").update(
                    {"status": "published",
                     "published_at": datetime.now(timezone.utc).isoformat()}
                ).eq("id", c["id"]).execute()
                publicadas += 1
            else:
                # NAO VOLTA PARA A FILA. `publish_card_sync` so devolve False
                # quando o texto reprova no filtro de PII do momento da
                # publicacao — a terceira e ultima camada. Deixar em
                # `pending_review` faria a mesma carta ser tentada em toda
                # rodada, para sempre, ocupando lugar de quem ainda nao
                # publicou. Na rodada de 29/07/2026 foram 22 assim.
                db.client.table("knowledge_cards").update(
                    {"status": "rejected_pii"}).eq("id", c["id"]).execute()
                falhas += 1
        except Exception as exc:  # noqa: BLE001 — uma carta ruim não trava o lote
            falhas += 1
            logger.warning("[CARTAS] publicação falhou: %s", type(exc).__name__)

    return {"publicadas": publicadas, "falhas": falhas, "tentadas": len(alvo),
            "indice_reconciliado": reconciliado.get("limpas", 0),
            "indice_pendente": reconciliado.get("falhas", 0)}
