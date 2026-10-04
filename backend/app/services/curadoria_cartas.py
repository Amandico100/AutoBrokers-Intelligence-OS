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
import os
import re
import time
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

LIMIAR = 0.47

# ─────────────────────────────────────────────────────────────────────────────
# 🔴 A RÉGUA DE UMA CARTA MORA AQUI, E É UMA SÓ — 15/08/2026
# ─────────────────────────────────────────────────────────────────────────────
# `knowledge_cards` tinha DUAS réguas de tamanho, e a tabela é a mesma.
#
#     15–400    escrito à mão em QUATRO lugares (attendance_distiller,
#               aplicar.py, aplicar_sql.py, atribuir_seguradora.py)
#     40–1800   acervo de condições gerais (`publicar_cartas.py`)
#
# 📊 O custo medido do 400, na leva de 15/08/2026: das 1.527 cartas destiladas,
# **23 morreram — todas por passar de 400, nenhuma por ficar abaixo de 15.**
# O piso nunca descartou nada, em lugar nenhum: 📊 das 18.598 cartas já
# gravadas, **uma** tem menos de 40 caracteres (39 ch: "Pode ser solicitado RG
# e CPF do síndico"), e ZERO têm menos de 15.
#
# O padrão do que o teto matava é perverso: quanto mais COMPLETA a carta, maior
# a chance de morrer. Lista de documentos de indenização integral, relação de
# documentos de colisão com terceiro, o conjunto fechado do reembolso de
# franquia — são longas PORQUE são completas, que é o que as torna úteis.
# E 3 das 23 eram inéditas (Jaccard < 0,22 contra as 18.400 do acervo).
#
# O teto certo é o FÍSICO, e ele já estava medido e justificado em
# `publicar_cartas.py`: 1.800 é onde o texto deixa de caber numa mensagem.
# Cortar uma lista taxativa faz a carta mentir por omissão.
#
# Quatro literais iguais não são uma regra — são quatro chances de divergir.
# Aqui é o dono das regras de carta (assunto, seguradora, contradição), então é
# aqui que a régua mora. Quem ingere IMPORTA; ninguém mais escreve o número.
MIN_CARACTERES = 40
MAX_CARACTERES = 1800


def fora_do_tamanho(texto: str) -> Optional[str]:
    """O MOTIVO da recusa por tamanho, ou None se a carta cabe.

    Devolve texto e não booleano de propósito: 🔴 um filtro que joga fora sem
    dizer o que perdeu não pode ser auditado, e foi assim que as 23 sumiram
    sem deixar rastro. Todo chamador registra o motivo antes de descartar.
    """
    n = len(texto or "")
    if n < MIN_CARACTERES:
        return f"curta demais ({n} ch, mínimo {MIN_CARACTERES})"
    if n > MAX_CARACTERES:
        return f"longa demais ({n} ch, máximo {MAX_CARACTERES})"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 🔴 O `pii_check` ESTAVA CALIBRADO NO EIXO ERRADO — 15/08/2026
# ─────────────────────────────────────────────────────────────────────────────
# A regra era `rejected_pii` quando `templatize(texto) != texto` — ou seja,
# **qualquer coisa que o mascarador tocaria** derrubava a carta, mesmo quando o
# que ele tocaria era uma palavra comum.
#
# 📊 As 320 cartas em `rejected_pii` passaram por todos os detectores:
# **ZERO têm CPF, CNPJ, telefone, placa, e-mail ou nome de pessoa.** E medido
# hoje contra o `templatize` de hoje, **315 das 320 não são tocadas por regra
# nenhuma**: as regras que as derrubaram já foram consertadas desde então, e a
# rejeição — gravada uma vez, nunca reavaliada — ficou de pé sozinha.
#
# As 5 que ainda são tocadas são o retrato do defeito:
#
#     "celular com DDD confirmado por botão"      → "celular com {NOME}"
#     "ou do WhatsApp que pediu a assistência"    → "ou do {NOME} que pediu"
#     "o telefone de quem está no local ANTES do" → "no local {NOME} do"
#     "atendimento tem de ser feito pelo 0800."   → "feito pelo {SEGREDO}."
#
# `DDD`, `WhatsApp`, `ANTES` e um `0800` — vocabulário de contexto, não dado de
# ninguém. É o eixo errado: o portão perguntava "o mascarador encostaria aqui?"
# quando a pergunta é "sobrou dado pessoal no que vai ser guardado?".
#
# O EIXO CERTO: MASCARAR SEMPRE, REJEITAR SÓ IDENTIFICADOR
# --------------------------------------------------------
# O que é guardado é o texto MASCARADO — sempre, os dois caminhos. Então nenhum
# dado pessoal entra no acervo, aconteça o que acontecer com a classificação.
# Isso é o que permite parar de rejeitar por heurística.
#
# `PII_QUE_REJEITA` são os identificadores de FORMA determinística: CPF, CNPJ,
# telefone, placa, e-mail, cartão, CEP, chassi, endereço, instrumento de
# pagamento — e a marca de CORRETORA, que é vazamento entre tenants (§7) e não
# some no mascaramento, porque a carta passaria a ser sobre aquela corretora.
# Uma carta que contém um desses não é conhecimento: é o caso de uma pessoa, e
# a presença do identificador é sinal de que a destilação falhou.
#
# `PII_QUE_SO_MASCARA` são as regras LEXICAIS — as que leem contexto e adivinham.
# Elas erram, está medido acima e está documentado em meia dúzia de blocos do
# próprio `templater.py`. Rejeitar por elas custa conhecimento real; mascarar
# por elas não custa nada, porque o nome — se houver nome — já saiu do texto.
#
# ⚠️ O que isto NÃO afrouxa: as 38 regras continuam TODAS ligadas e TODAS
# mascarando. O que muda é só o que a carta tocada por uma delas vira —
# `pending_review` mascarada, em vez de `rejected_pii` com o texto cru guardado.
PII_QUE_REJEITA = frozenset({
    "{CPF}", "{CNPJ}", "{TELEFONE}", "{PLACA}", "{EMAIL}", "{CARTAO}",
    "{VALIDADE}", "{CEP}", "{CHASSI}", "{ENDERECO}", "{LINHA_DIGITAVEL}",
    "{PIX_COPIA_E_COLA}", "{PIX_FIM}", "{CORRETORA}",
})
PII_QUE_SO_MASCARA = frozenset({
    "{NOME}", "{NUM}", "{NUMERO}", "{VALOR}", "{VALOR_RS}", "{CAMINHO}",
    "{DATA}", "{PROTOCOLO}", "{SEGREDO}",
})

_PLACEHOLDER = re.compile(r"\{[A-Z_]+\}")


def veredito_de_pii(texto: str, *,
                    documento_publico: bool = False,
                    marcas: Optional[Iterable[str]] = None) -> Tuple[str, List[str]]:
    """(texto a GUARDAR, identificadores encontrados). Determinístico.

    O texto devolvido é sempre o mascarado — guarde ESTE, nunca o cru. Se a
    lista voltar vazia, a carta é `pending_review`; se vier com algo, é
    `rejected_pii` e a lista diz o quê, para o `pii_check` poder ser auditado.

    ⚠️ `rotulo_de_campo=False` é obrigatório aqui e não é afrouxamento.
    `_LABELED_VALUE` nasceu para ler TELA, onde cada campo ocupa uma linha, e
    está ancorado em `^`. Uma carta é PROSA, e o `^` alcança a primeira palavra
    dela sempre. 📊 Foi o que comeu 4 das 320:

        "CORRECAO DE ACERVO: encerramento do canal…"  → "COR{VALOR}"
        "Veículo 100% elétrico na Yelum não muda…"    → "Veículo {VALOR}"
        "Assistencia 24h retirada na renovacao…"      → "Assistencia {VALOR}"

    O próprio `templater.templatize` já documenta essa causa e já expõe o
    parâmetro para desligá-la. As 38 regras de PII de verdade continuam ligadas.
    """
    from app.services.atlas.templater import templatize

    cru = str(texto or "")
    # `marcas=None` é o de sempre (as marcas de `companies` do templater); só o
    # porteiro do global passa a lista dele — ver `templatize(marcas=...)`.
    mascarado = templatize(cru, documento_publico=documento_publico,
                           rotulo_de_campo=False, marcas=marcas)
    antes = _PLACEHOLDER.findall(cru)
    depois = _PLACEHOLDER.findall(mascarado)
    achados = sorted({p for p in depois
                      if depois.count(p) > antes.count(p) and p in PII_QUE_REJEITA})
    return mascarado, achados


# ------------------------------------------------------------------ #
# 🔴 O PORTEIRO DO CONHECIMENTO GLOBAL — P-E0018-14 · D-MC-39 (04/10/2026)
# ------------------------------------------------------------------ #
# `conduct_playbooks` é GLOBAL e continua global ("O Atlas é UM SÓ, e é de
# todas" — D-MC-39: ⛔ nunca `company_id` nela). Mas o que entra nela nasce das
# conversas de UMA corretora: o destilador e o lapidador escrevem por um funil
# só, `attendance_distiller._save_playbook_draft_sync`. Antes deste porteiro o
# `content` que o modelo devolvia ia para o insert como veio.
#
# ⛔ NÃO É UM TERCEIRO MASCARADOR (CLAUDE.md §5). Ele COMPÕE os que existem:
#   1. limpa      `veredito_de_pii` — o `templatize` em modo prosa, a MESMA régua
#                 das cartas —, com DUAS diferenças só daqui (a mensagem não muda):
#                   · a lista de marcas é a do porteiro (`_perfis_de_corretora`),
#                     sem palavra do ofício: "Total Corretora" não vira a marca
#                     "Total" e "perda total" não vira "perda {CORRETORA}" (Q4);
#                   · o conhecimento PÚBLICO é guardado antes e devolvido depois:
#                     0800/3003/4004 e os números das seguradoras do registro;
#                     e "Pode ser" que o mascarador leu como nome volta a ser
#                     "Pode ser" (palavra comum nunca é {NOME});
#   2. confere    o que SOBROU, por caminhos independentes:
#                   a. o mesmo mascarador de novo — se ele ainda acha CPF, placa,
#                      telefone, e-mail, corretora ou {NOME}, a limpeza falhou;
#                   b. a SEGUNDA REDE, `intelligence.redaction_service`, só os
#                      identificadores de forma (CPF, CNPJ, placa, e-mail,
#                      telefone, cartão) — outro motor, outro dialeto de regex —,
#                      mais as formas que nenhum dos dois motores pega
#                      (`_FORMAS_QUE_OS_MOTORES_NAO_PEGAM`);
#                   c. a CORRETORA, pelas VARIANTES do nome que o banco dá: o
#                      nome inteiro, o núcleo distintivo (sem "corretora",
#                      "seguros", "ltda"…), e a forma COMPACTA dentro de
#                      domínio/handle ("vagalumeseguros.com.br", "@vagalume");
#                   d. NOME DE PESSOA em contexto: prenome da lista de dados
#                      `app/data/prenomes_brasileiros.txt` depois de artigo,
#                      tratamento, cargo, "falar com", assinatura (Q3);
#   3. se sobrou QUALQUER coisa, ou se a lista de corretoras não pôde ser
#      RELIDA agora, quem chama NÃO GRAVA. Falha fechada.
#
# ⚠️ A lista de corretoras do porteiro é lida AQUI, de `companies`, e vale 5 min.
# Banco mudo na releitura = lista indisponível = não grava — ⛔ nunca a lista
# velha (uma corretora criada depois da última leitura atravessaria). O
# mascarador de MENSAGEM continua com a cache dele (`templater`): para ele, a
# lista velha é melhor que nenhuma, e é ele quem roda em todo atendimento.
#
# ⚠️ LIMITE DECLARADO (nome de pessoa): a conferência (d) acha prenome
# brasileiro COMUM em contexto de pessoa. Não acha: sobrenome sozinho ("o
# Silveira confirmou"), prenome raro/estrangeiro fora da lista sem tratamento
# ("a Kerolayne"), apelido, nem prenome-palavra (rosa, luz, socorro…) escrito
# em minúscula sem contexto forte. Isso só um modelo de entidades pegaria; a
# rede que sobra é a instrução ao modelo e a ativação manual pelo master admin.
_MARCAS_VALEM_S = 300.0
_marcas_lidas_em: Optional[float] = None
_NOMES_DE_CORRETORA: Tuple[str, ...] = ()

#: As marcas de `redaction_service.PADROES_PII` que são IDENTIFICADOR de forma.
#: ⚠️ Fora de propósito: `apólice …`/`sinistro …` casam prosa ("sinistro deve
#: ser") e `[DOCUMENTO]`/`[CEP]` já são cobertos pelo `templatize`. Uma rede que
#: reprova o próprio vocabulário do serviço comeria todo playbook.
_SEGUNDA_REDE = frozenset({"[CPF]", "[CNPJ]", "[PLACA]", "[EMAIL]",
                           "[TELEFONE]", "[CARTAO]"})

#: O que o mascarador, rodando de NOVO sobre o texto já limpo, não pode achar.
_RESIDUO_DO_MASCARADOR = PII_QUE_REJEITA | {"{NOME}"}

#: 🔴 As formas de identificador que o red team de 04/10 passou pelos DOIS
#: motores (o `templatize` e a segunda rede). Ficam aqui, e não no `templatize`,
#: porque lá elas mudariam o mascaramento de TODA mensagem — e duas delas são
#: trocas documentadas do motor ("abc-1234" minúsculo foi solto de propósito
#: contra o falso positivo "das 8h00", `templater.py`). No global, a conta é
#: outra: um playbook com "placa abc-1234" é o caso de uma pessoa.
_FORMAS_QUE_OS_MOTORES_NAO_PEGAM: Tuple[Tuple[re.Pattern, str], ...] = (
    # placa antiga minúscula com hífen, em qualquer lugar: "abc-1234"
    (re.compile(r"(?i)(?<![\w-])[a-z]{3}-\d{4}(?![\w-])"), "[PLACA]"),
    # placa depois da palavra "placa", em qualquer caixa e com espaço:
    # "placa abc 1234", "placa abc 1d23" (sem o rótulo, "ano 2026" casaria)
    (re.compile(r"(?i)\bplaca\W{0,3}[a-z]{3}[\s.-]?\d[a-z0-9]\d{2}\b"), "[PLACA]"),
    # celular sem DDD com o 9 separado: "9 9876-5432", "9 9876 5432"
    (re.compile(r"(?<![\d-])9\s\d{4}[\s.-]?\d{4}(?![\d-])"), "[TELEFONE]"),
    # celular sem DDD colado: "99876-5432"
    (re.compile(r"(?<![\d-])9\d{4}-\d{4}(?![\d-])"), "[TELEFONE]"),
    # CPF com barra ou separador misto: "123/456/789-09"
    (re.compile(r"(?<![\d/.-])\d{3}[./\s-]\d{3}[./\s-]\d{3}[./\s-]?\d{2}(?![\d/])"),
     "[CPF]"),
)

#: Fixo sem DDD ("3222-1144") — à parte porque tem exceções: os números de
#: capital (3003/400x/4020/4062/4090) são canal PÚBLICO de seguradora, e
#: "2025-2026" é intervalo de ano, não telefone.
_FIXO_SEM_DDD = re.compile(r"(?<![\d-])([2-5]\d{3})-(\d{4})(?![\d-])")
_PREFIXO_DE_CAPITAL = re.compile(r"^(?:300\d|400\d|4020|4062|4090)$")
_ANO = re.compile(r"^(?:19|20)\d{2}$")

#: Número de discagem nacional/capital: canal PÚBLICO, nunca dado de alguém.
_NUMERO_PUBLICO = re.compile(
    r"(?<!\d)(?:0[3589]00[\s.-]?\d{3}[\s.-]?\d{4}"
    r"|(?:300\d|400\d|4020|4062|4090)[\s.-]?\d{4})(?!\d)")
#: Candidato a telefone com DDD, para conferir contra o registro de seguradoras.
_TELEFONE_COM_DDD = re.compile(
    r"(?<!\d)(?:\+?55[\s.-]*)?(?:\(\s*\d{2}\s*\)|\d{2})[\s.-]*9?[\s.-]?\d{4}[\s.-]?\d{4}(?!\d)")
_SENTINELA = ""


# ----------------------------------------------------------------------
# a lista de corretoras do PORTEIRO — lida do banco, nunca velha
# ----------------------------------------------------------------------
def _ler_nomes_de_corretora() -> Tuple[str, ...]:
    """`company_name` e `legal_name` CRUS de `companies`. Levanta se o banco falhar."""
    from app.core.database import get_supabase_client

    linhas = (get_supabase_client().client.table("companies")
              .select("company_name, legal_name").limit(1000)
              .execute().data or [])
    nomes = []
    for linha in linhas:
        for campo in ("company_name", "legal_name"):
            bruto = str((linha or {}).get(campo) or "").strip()
            if bruto and bruto not in nomes:
                nomes.append(bruto)
    return tuple(nomes)


def nomes_de_corretora_frescos() -> Optional[Tuple[str, ...]]:
    """Os nomes das corretoras RELIDOS há no máximo 5 min — ou None.

    🔴 None quando a releitura falhou: o porteiro trata como "lista
    indisponível" e NÃO grava. ⛔ Nunca devolve a lista velha (red team 04/10:
    a lista velha deixava passar a corretora criada depois da última leitura).
    Vazia não marca a hora: a próxima chamada tenta ler de novo.
    """
    global _marcas_lidas_em, _NOMES_DE_CORRETORA
    agora = time.monotonic()
    if (_marcas_lidas_em is not None and _NOMES_DE_CORRETORA
            and (agora - _marcas_lidas_em) < _MARCAS_VALEM_S):
        return _NOMES_DE_CORRETORA
    try:
        nomes = _ler_nomes_de_corretora()
    except Exception:  # noqa: BLE001
        return None
    _NOMES_DE_CORRETORA = nomes
    if nomes:
        _marcas_lidas_em = agora
    # O mascarador de MENSAGEM aproveita a releitura (a cache dele não vence
    # sozinha). Se o banco cair na leitura dele, ele fica com a lista que tinha.
    try:
        from app.services.atlas.templater import marcas_de_corretora

        marcas_de_corretora(recarregar=True)
    except Exception:  # noqa: BLE001
        pass
    return nomes


# ----------------------------------------------------------------------
# as VARIANTES do nome de uma corretora (Q2) e o que NÃO é marca (Q4)
# ----------------------------------------------------------------------
#: O que um nome de corretora carrega e não a distingue de nenhuma outra.
_SUFIXOS_DE_CORRETORA = frozenset({
    "corretora", "corretor", "corretores", "corretagem", "seguros", "seguro",
    "seguradora", "securitaria", "de", "da", "do", "das", "dos", "e", "em",
    "ltda", "limitada", "me", "epp", "eireli", "slu", "sa", "ss", "cia",
    "companhia", "assessoria", "administradora", "administracao", "consultoria",
    "servicos", "negocios", "adm", "broker", "brokers", "insurance", "grupo",
    "agencia", "agenciamento",
})
#: As palavras que fazem de um nome de empresa uma CORRETORA, e não seguradora.
_PALAVRAS_DE_CORRETORA = frozenset({
    "corretora", "corretor", "corretores", "corretagem", "assessoria",
    "consultoria", "broker", "brokers", "agencia", "agenciamento",
})
_CONECTIVOS = frozenset({"de", "da", "do", "das", "dos", "e"})

#: 🔴 Q4 — palavra GENÉRICA nunca vira marca sozinha. constante_justificada:
#: é VOCABULÁRIO, não nome de cliente (§13.9): o português do ofício (ramos,
#: serviços, termos de apólice), as palavras de fantasia que qualquer empresa
#: usa ("center", "express", "total", "plena", "forte"…) e cores. Somam-se a
#: ela, em tempo de execução, os nomes de SEGURADORA (`INSURER_REGISTRY` e a
#: tabela de apelidos de `corridor_playbooks`) e as palavras vazias deste
#: arquivo (`_VAZIAS`). 📊 O red team de 04/10 mediu o estrago sem ela: "Auto
#: Center Corretora" barrava TODO playbook `ramo=auto`, "Guincho Express" todo
#: `auto/guincho`, "Vida Plena" todo `ramo=vida`, e "Total Corretora" gravava
#: "em perda {CORRETORA}".
_VOCABULARIO_GENERICO = frozenset("""
auto automovel automoveis carro carros veiculo veiculos moto motos caminhao
caminhoes frota frotas taxi residencial residencia residencias casa casas lar
vida vidas saude odonto dental empresarial empresa empresas condominio viagem
viagens funeral funeraria guincho reboque chaveiro vidro vidros eletricista
encanador encanamento desentupimento eletrodomesticos sinistro sinistros
assistencia assistencias cobertura coberturas franquia apolice apolices
protecao prevencao previdencia consorcio capitalizacao garantia fianca
responsabilidade civil carga cargas transporte transportes agro rural pet
celular bike bicicleta patrimonial total perda parcial roubo furto colisao
incendio vistoria indenizacao proposta renovacao cotacao endosso premio
center centro express expresso plus prime top master max maxi mais plena
pleno forte fortes nova novo real gold ouro prata brasil brasileira brasileiro
brasileiros nacional central rapido rapida facil confianca uniao alianca
primeira primeiro unica unico global digital online net web invest solucoes
solucao gestao protege protegido protegida segura seguranca certo certa bem
boa bom melhor mega super life home car smart easy fast club clube mundo
mundial vip premium ideal lider elite star estrela sol mar terra sul norte
leste oeste capital metropolitana cidade popular familia amigo amigos amiga
azul verde vermelho vermelha amarelo amarela branco branca preto preta roxo
roxa rosa laranja cinza dourado dourada prateado prateada
""".split())

_VOCABULARIO_CACHE: Optional[frozenset] = None
_SEGURADORAS_CACHE: Optional[Tuple[frozenset, frozenset]] = None


def _palavras_baixas(texto: str) -> List[str]:
    """As palavras de `texto`, sem acento, minúsculas, sem pontuação."""
    return re.findall(r"[a-z0-9]+", _sem_acento(texto).lower())


def _seguradoras() -> Tuple[frozenset, frozenset]:
    """(nomes INTEIROS de seguradora, PALAVRAS de nome de seguradora).

    Do `INSURER_REGISTRY` e de `corridor_playbooks._INSURER_ALIASES` — as
    tabelas que já dizem quem é seguradora (§5: nenhuma lista nova de
    companhias). Se nenhuma carregar, levanta: sem saber quem é seguradora, o
    porteiro não sabe o que é genérico, e falha fechado.
    """
    global _SEGURADORAS_CACHE
    if _SEGURADORAS_CACHE is not None:
        return _SEGURADORAS_CACHE
    inteiros, palavras = set(), set()
    fontes = 0
    try:
        from app.services.insurer_registry import INSURER_REGISTRY

        for chave, info in INSURER_REGISTRY.items():
            for forma in (str(chave), str((info or {}).get("label") or "")):
                if forma.strip():
                    inteiros.add(" ".join(_palavras_baixas(forma)))
                    palavras.update(_palavras_baixas(forma))
        fontes += 1
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.services.corridor_playbooks import _INSURER_ALIASES

        for forma in list(_INSURER_ALIASES) + list(_INSURER_ALIASES.values()):
            inteiros.add(" ".join(_palavras_baixas(forma)))
            palavras.update(_palavras_baixas(forma))
        fontes += 1
    except Exception:  # noqa: BLE001
        pass
    if not fontes:
        raise RuntimeError("nenhuma tabela de seguradoras carregou")
    resultado = (frozenset(inteiros), frozenset(palavras))
    if fontes == 2:                 # só guarda a resposta COMPLETA
        _SEGURADORAS_CACHE = resultado
    return resultado


def _vocabulario_generico() -> frozenset:
    global _VOCABULARIO_CACHE
    if _VOCABULARIO_CACHE is None:
        _VOCABULARIO_CACHE = (_VOCABULARIO_GENERICO | _seguradoras()[1]
                              | _SUFIXOS_DE_CORRETORA
                              | {_sem_acento(v).lower() for v in _VAZIAS})
    return _VOCABULARIO_CACHE


def _e_generica(palavra: str) -> bool:
    return len(palavra) <= 2 or palavra in _vocabulario_generico()


def _regex_de_frase(palavras: List[str], *, conectivos_opcionais: bool) -> re.Pattern:
    """As palavras em sequência, separadas por qualquer pontuação/espaço."""
    sep = (r"[\W_]+(?:(?:de|da|do|das|dos|e)[\W_]+)?" if conectivos_opcionais
           else r"[\W_]+")
    corpo = sep.join(re.escape(p) for p in palavras)
    return re.compile(rf"(?<![a-z0-9]){corpo}(?![a-z0-9])")


class _PerfilDeCorretora:
    """As formas pelas quais UM nome de `companies` pode aparecer num texto."""

    __slots__ = ("frases", "frases_com_maiuscula", "compactos", "marcas")

    def __init__(self, bruto: str):
        self.frases: List[re.Pattern] = []
        self.frases_com_maiuscula: List[re.Pattern] = []
        self.compactos: List[str] = []
        self.marcas: List[str] = []
        palavras = [p for p in _palavras_baixas(bruto) if len(p) > 1]
        nucleo = [p for p in palavras if p not in _SUFIXOS_DE_CORRETORA]
        if not nucleo:
            return                      # "Corretora de Seguros Ltda": nada distingue
        inteiros, palavras_de_seguradora = _seguradoras()
        sem_sufixo_legal = " ".join(p for p in palavras if p not in {
            "ltda", "limitada", "me", "epp", "eireli", "slu", "sa", "ss", "cia",
            "companhia"})
        parece_seguradora = (sem_sufixo_legal in inteiros or (
            all(p in palavras_de_seguradora for p in nucleo)
            and not any(p in _PALAVRAS_DE_CORRETORA for p in palavras)))
        if parece_seguradora:
            # "Porto Seguros" cadastrada como corretora não pode fazer o global
            # perder "Porto Seguro" — o mesmo guarda de `pode_virar_marca`.
            return
        distintivas = [p for p in nucleo if not _e_generica(p)]
        tem_sufixo = len(palavras) > len(nucleo)

        # 1. o NOME INTEIRO: vale se tem palavra distintiva, ou se o sufixo de
        #    corretora está nele ("Total Corretora" sim; "Total" sozinho não).
        if distintivas or (tem_sufixo and len(palavras) >= 2):
            self.frases.append(_regex_de_frase(palavras, conectivos_opcionais=False))
            self.marcas.append(bruto.strip())
            compacto = "".join(palavras)
            if len(compacto) >= 8:
                self.compactos.append(compacto)
        # 2. o NÚCLEO distintivo ("Vagalume", "Céu Azul", "Azul Marinho").
        #    ⛔ Núcleo todo genérico ("Auto Center", "Vida Plena") não vale
        #    sozinho: exige-se a frase inteira de cima (Q4).
        if distintivas and not (len(nucleo) == 1 and len(nucleo[0]) < 4):
            frase = _regex_de_frase(nucleo, conectivos_opcionais=True)
            if len(distintivas) == len(nucleo):
                self.frases.append(frase)
                # o mascarador do porteiro troca o núcleo, na grafia do banco
                exibido = [w for w in re.findall(r"[^\W_]+", bruto)
                           if _sem_acento(w).lower() in nucleo]
                if exibido:
                    self.marcas.append(" ".join(exibido))
            else:
                # Núcleo MISTO ("Céu Azul": "azul" é seguradora e cor). Em
                # minúscula é prosa ("com céu azul"); com maiúscula é a marca.
                self.frases_com_maiuscula.append(frase)
            compacto = "".join(nucleo)
            if len(compacto) >= 5:
                self.compactos.append(compacto)
        # 3. o NÚCLEO todo GENÉRICO de ≥ 2 palavras ("Porto Real", "Auto
        #    Center", "Vida Plena", "Alfa Real"). 📊 A confirmação de 04/10
        #    mediu: só o nome INTEIRO era procurado, e "aqui é da Porto Real",
        #    "site portoreal.com.br", "a Auto Center confirma" iam ao global.
        #    Vale como o núcleo MISTO: com MAIÚSCULA em cada palavra é a marca;
        #    em minúscula é prosa do serviço ("leve a um auto center", "perda
        #    total") e passa. E a forma COLADA (domínio/handle) com ≥ 8 letras.
        #    ⛔ Uma palavra genérica SOZINHA continua nunca sendo marca (Q4), e
        #    núcleo só de palavras de SEGURADORA ("Tokio Marine Corretora") não
        #    vale: "a Tokio Marine abre sinistro" é conhecimento público.
        elif (len(nucleo) >= 2
              and not all(p in palavras_de_seguradora for p in nucleo)):
            self.frases_com_maiuscula.append(
                _regex_de_frase(nucleo, conectivos_opcionais=True))
            compacto = "".join(nucleo)
            if len(compacto) >= 8:
                self.compactos.append(compacto)


def _perfis_de_corretora(nomes: Tuple[str, ...]) -> List[_PerfilDeCorretora]:
    return [p for p in (_PerfilDeCorretora(n) for n in nomes)
            if p.frases or p.frases_com_maiuscula or p.compactos]


def _marcas_do_porteiro(perfis: List[_PerfilDeCorretora]) -> Tuple[str, ...]:
    """O que o mascarador do PORTEIRO troca por {CORRETORA}. Maior primeiro."""
    marcas = {m for p in perfis for m in p.marcas if len(m) >= 4}
    return tuple(sorted(marcas, key=len, reverse=True))


def marcas_de_corretora_frescas() -> Tuple[str, ...]:
    """As marcas que o porteiro mascara, de `companies` relida há ≤ 5 min.

    Vazia quando o banco não respondeu — e o porteiro trata vazia como FALHA
    (nenhuma instalação com conversa para destilar tem zero corretoras).
    """
    nomes = nomes_de_corretora_frescos()
    if not nomes:
        return ()
    return _marcas_do_porteiro(_perfis_de_corretora(nomes))


#: O que pode vir COLADO depois do nome num domínio/handle e ainda ser a marca:
#: "vagalumeseguros", "vagalumecorretora". ⚠️ Lista fechada de propósito — 📊
#: 04/10/2026, nos 18 playbooks reais, a forma compacta solta de uma corretora
#: real casava "resultado" (a marca + "do"): substring não é marca.
_RESTO_DE_HANDLE = frozenset({
    "", "seguros", "seguro", "corretora", "corretoras", "corretor", "corretores",
    "corretoradeseguros", "corretagem", "assessoria", "consultoria", "broker",
    "brokers", "insurance", "seg", "segs", "oficial", "online", "digital", "br",
})


def _segmentos_colados(base: str) -> List[List[str]]:
    """Para cada token (domínio, handle, hashtag, CamelCase, palavra), os pedaços.

    "www.VagalumeCorretora.com" → ["www", "vagalume", "corretora", "com"].
    Quem decide se é marca é `_marca_colada`: o pedaço tem de COMEÇAR pela marca
    e o resto tem de ser `_RESTO_DE_HANDLE` — "resultado" não passa.
    """
    saida = []
    for w in base.split():
        pedacos = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", w)
        pedacos = [p for p in re.split(r"[^A-Za-z0-9]+", pedacos.lower()) if p]
        if pedacos:
            saida.append(pedacos)
    return saida


def _marca_colada(compacto: str, colados: List[List[str]]) -> bool:
    for pedacos in colados:
        for i in range(len(pedacos)):
            junto = ""
            for j in range(i, min(i + 4, len(pedacos))):
                junto += pedacos[j]
                if junto.startswith(compacto) and junto[len(compacto):] in _RESTO_DE_HANDLE:
                    return True
    return False


def _corretora_no_texto(texto: str, perfis: List[_PerfilDeCorretora]) -> bool:
    base = _sem_acento(texto)
    baixo = base.lower()
    mesma_medida = len(base) == len(baixo)
    colados = _segmentos_colados(base)
    for perfil in perfis:
        if any(rx.search(baixo) for rx in perfil.frases):
            return True
        for rx in perfil.frases_com_maiuscula:
            for m in rx.finditer(baixo):
                if not mesma_medida:
                    return True          # não dá para conferir a caixa: fecha
                trecho = re.findall(r"[^\W_]+", base[m.start():m.end()])
                if all(w[:1].isupper() for w in trecho
                       if w.lower() not in _CONECTIVOS):
                    return True
        # domínio, handle, hashtag: "vagalumeseguros.com.br", "@vagalume_seguros"
        if any(_marca_colada(c, colados) for c in perfil.compactos):
            return True
    return False


# ----------------------------------------------------------------------
# NOME DE PESSOA em contexto (Q3)
# ----------------------------------------------------------------------
_PRENOMES_CACHE: Optional[frozenset] = None

#: Prenomes que também são PALAVRA (ou cidade, ou marca de carro). Só contam em
#: contexto FORTE de pessoa, ou com maiúscula depois de artigo ("a Rosa").
#: constante_justificada: é a lista que impede "rosa", "socorro", "dores",
#: "norma", "marcos" e "Mercedes" de virarem gente no meio de um playbook.
_PRENOMES_QUE_SAO_PALAVRA = frozenset("""
rosa luz gloria paz socorro graca celeste neves bento vitoria aurora clara
branca bela perola estrela esperanca conceicao aparecida dores fatima penha
lourdes natal franco prado messias salvador cruz jesus amparo mercedes marina
vera iris jade flor luna serena linda diva mel liz lis constancia clemente
amado augusto fausto feliz valente modesto pastor romano domingos marcos
armando caio tomas roque israel jacinto juvenal norma edite sara perpetua
margarida jurema mariana marilia lorena iracema oscar cesar ester rui leo
""".split())

#: Antes do prenome, diz que é PESSOA (tratamento, cargo, assinatura, vocativo).
_CONTEXTO_FORTE = frozenset("""
sr sra srta srs dr dra dona senhor senhora seu
atendente atendentes corretor corretora consultor consultora analista gerente
supervisor supervisora assistente operador operadora colaborador colaboradora
funcionario funcionaria vendedor vendedora responsavel segurado segurada
cliente titular condutor condutora motorista tecnico tecnica prestador perito
vistoriador vistoriadora regulador reguladora colega chefe diretor diretora
socio socia contato
chamo att atenciosamente abraco abracos abs assinado assinatura ass oi ola
""".split())
#: Duas palavras antes do prenome que dizem que é pessoa ("aqui é a", "falar com").
_CONTEXTO_FORTE_DUPLO = frozenset({
    ("aqui", "e"), ("nome", "e"), ("falar", "com"), ("fale", "com"),
    ("falei", "com"), ("fala", "com"), ("ligar", "para"), ("ligue", "para"),
    ("confirme", "com"), ("confirmar", "com"), ("confirmou", "com"),
    ("procure", "a"), ("procure", "o"), ("pergunte", "a"), ("pergunte", "o"),
})
_CONTEXTO_FORTE_SIMPLES_VERBO = frozenset({"sou", "procure", "pergunte", "chame"})
#: Artigo/preposição colado ao prenome: contexto FRACO.
_ARTIGOS = frozenset({"a", "o", "ao", "da", "do", "na", "no", "pela", "pelo",
                      "para", "pra", "com"})
#: Palavra antes que faz do prenome um LUGAR ou título histórico, não pessoa.
_ANTES_DE_LUGAR = frozenset("""
sao santo santa sta sto dom padre frei irma princesa principe presidente
marechal general almirante duque barao conde visconde governador prefeito
senador deputado coronel capitao tenente major cardeal papa lei rua avenida
av travessa praca alameda rodovia estrada bairro vila jardim parque hospital
colegio escola igreja edificio
""".split())
_LUGARES_COM_PRENOME = frozenset({("joao", "pessoa"), ("vitoria", "da"),
                                  ("maria", "da", "penha")})
_RX_PALAVRA = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")


def _prenomes() -> frozenset:
    """A lista de dados `app/data/prenomes_brasileiros.txt`. Levanta se faltar."""
    global _PRENOMES_CACHE
    if _PRENOMES_CACHE is None:
        caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "data", "prenomes_brasileiros.txt")
        with open(caminho, encoding="utf-8") as f:
            nomes = {_sem_acento(l.strip()).lower() for l in f
                     if l.strip() and not l.lstrip().startswith("#")}
        nomes -= _seguradoras()[1]          # "darwin" é seguradora, não gente
        if len(nomes) < 100:
            raise RuntimeError("lista de prenomes curta demais")
        _PRENOMES_CACHE = frozenset(nomes)
    return _PRENOMES_CACHE


def _nome_de_pessoa_no_texto(texto: str) -> bool:
    """Há prenome em contexto de pessoa? Ver o LIMITE DECLARADO no topo."""
    prenomes = _prenomes()
    achadas = [(m.group(0), m.start(), m.end()) for m in _RX_PALAVRA.finditer(texto)]
    norm = [_sem_acento(p).lower() for p, _, _ in achadas]
    for i, (palavra, inicio, _fim) in enumerate(achadas):
        n = norm[i]
        if n not in prenomes:
            continue
        ant = norm[i - 1] if i > 0 else ""
        if ant in _ANTES_DE_LUGAR or (ant == "senhora" and i > 1 and norm[i - 2] == "nossa"):
            continue
        prox = tuple(norm[i:i + 3])
        if any(prox[:len(l)] == l for l in _LUGARES_COM_PRENOME):
            continue
        maiuscula = palavra[:1].isupper()
        # o contexto: pula UM artigo ("falar com a Joana", "aqui é a Joana")
        k = i - 1
        fraco = k >= 0 and norm[k] in _ARTIGOS
        if fraco and norm[k] in {"a", "o"}:
            k -= 1
        ant1 = norm[k] if k >= 0 else ""
        ant2 = norm[k - 1] if k >= 1 else ""
        forte = (ant1 in _CONTEXTO_FORTE or ant1 in _CONTEXTO_FORTE_SIMPLES_VERBO
                 or (ant2, ant1) in _CONTEXTO_FORTE_DUPLO)
        if n in _PRENOMES_QUE_SAO_PALAVRA:
            if forte or (fraco and maiuscula):
                return True
        elif forte or fraco or maiuscula:
            return True
    return False


# ----------------------------------------------------------------------
# o mascarador do PORTEIRO: a régua da casa + o que só o global precisa
# ----------------------------------------------------------------------
_NUMEROS_DAS_SEGURADORAS: Optional[frozenset] = None


def _numeros_das_seguradoras() -> frozenset:
    """Telefones/WhatsApp PÚBLICOS do `INSURER_REGISTRY`, só os dígitos com DDD."""
    global _NUMEROS_DAS_SEGURADORAS
    if _NUMEROS_DAS_SEGURADORAS is None:
        numeros = set()
        carregou = False
        try:
            from app.services.insurer_registry import INSURER_REGISTRY

            def _todos(v):
                if isinstance(v, dict):
                    for x in v.values():
                        yield from _todos(x)
                elif isinstance(v, (list, tuple)):
                    for x in v:
                        yield from _todos(x)
                elif isinstance(v, str):
                    yield v

            for info in INSURER_REGISTRY.values():
                for texto in _todos(info):
                    for m in re.finditer(r"\d[\d\s().-]{7,}\d", texto):
                        d = re.sub(r"\D", "", m.group(0))
                        if len(d) >= 12 and d.startswith("55"):
                            d = d[2:]
                        if 10 <= len(d) <= 11:
                            numeros.add(d)
            carregou = True
        except Exception:  # noqa: BLE001
            pass
        if not carregou:            # sem o registro, tenta de novo na próxima
            return frozenset(numeros)
        _NUMEROS_DAS_SEGURADORAS = frozenset(numeros)
    return _NUMEROS_DAS_SEGURADORAS


def _trechos_publicos(texto: str) -> List[Tuple[int, int]]:
    """Onde estão os números PÚBLICOS: 0800/3003/400x e os das seguradoras."""
    trechos = [m.span() for m in _NUMERO_PUBLICO.finditer(texto)]
    conhecidos = _numeros_das_seguradoras()
    for m in _TELEFONE_COM_DDD.finditer(texto):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) >= 12 and d.startswith("55"):
            d = d[2:]
        if d in conhecidos:
            trechos.append(m.span())
    trechos.sort()
    unidos: List[Tuple[int, int]] = []
    for a, b in trechos:
        if unidos and a <= unidos[-1][1]:
            unidos[-1] = (unidos[-1][0], max(b, unidos[-1][1]))
        else:
            unidos.append((a, b))
    return unidos


def _guardar_publicos(texto: str) -> Tuple[str, List[str]]:
    guardados: List[str] = []
    partes, fim = [], 0
    for a, b in _trechos_publicos(texto):
        partes.append(texto[fim:a])
        partes.append(f"{_SENTINELA}{chr(0xE100 + len(guardados))}{_SENTINELA}")
        guardados.append(texto[a:b])
        fim = b
    partes.append(texto[fim:])
    return "".join(partes), guardados


def _devolver_publicos(texto: str, guardados: List[str]) -> str:
    for i, g in enumerate(guardados):
        texto = texto.replace(f"{_SENTINELA}{chr(0xE100 + i)}{_SENTINELA}", g)
    return texto


def _sem_publicos(texto: str) -> str:
    """O texto sem os números públicos — é sobre ELE que as redes conferem."""
    partes, fim = [], 0
    for a, b in _trechos_publicos(texto):
        partes.append(texto[fim:a])
        partes.append(" ")
        fim = b
    partes.append(texto[fim:])
    return "".join(partes)


def _palavra_comum(palavra: str) -> bool:
    n = _sem_acento(palavra).lower()
    return bool(n) and n in _vocabulario_generico() and n not in _prenomes()


def _devolver_palavra_comum(antes: str, depois: str) -> str:
    """Desfaz o {NOME} que o mascarador pôs sobre palavra COMUM.

    📊 04/10/2026, o juiz mediu num playbook ATIVO: "de quem estava dirigindo?
    Pode ser foto legível" → "{NOME} ser foto legível". A regra lexical do
    `templatize` lê "quem estava … <Maiúscula>" como nome. Na mensagem isso é
    troca conhecida; no global, é conhecimento degradado para TODAS. Aqui só
    se devolve o trecho quando TODAS as palavras dele são vocabulário comum e
    nenhuma é prenome — nome de verdade continua {NOME}.
    """
    if "{NOME}" not in depois or "{NOME}" in antes:
        return depois
    import difflib

    sm = difflib.SequenceMatcher(None, antes, depois, autojunk=False)
    saida: List[str] = []
    bloco_a, bloco_d = [], []

    def _fecha():
        if not (bloco_a or bloco_d):
            return
        a, d = "".join(bloco_a), "".join(bloco_d)
        palavras = _RX_PALAVRA.findall(a)
        if (d.strip() == "{NOME}" and palavras
                and all(_palavra_comum(p) for p in palavras)):
            saida.append(a)
        else:
            saida.append(d)
        bloco_a.clear()
        bloco_d.clear()

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            _fecha()
            saida.append(depois[j1:j2])
        else:
            bloco_a.append(antes[i1:i2])
            bloco_d.append(depois[j1:j2])
    _fecha()
    return "".join(saida)


def _mascarar_para_o_global(texto: str, marcas: Tuple[str, ...]) -> str:
    """`veredito_de_pii` com as marcas do porteiro e o conhecimento público guardado."""
    guardado, publicos = _guardar_publicos(str(texto or ""))
    mascarado, _ = veredito_de_pii(guardado, marcas=marcas)
    mascarado = _devolver_palavra_comum(guardado, mascarado)
    # "(21) 3906-2985" virava "({TELEFONE}": o parêntese órfão sai com o número.
    mascarado = re.sub(r"\((\{TELEFONE\})(?!\))", r"\1", mascarado)
    return _devolver_publicos(mascarado, publicos)


def _padroes_da_segunda_rede() -> List[Tuple[re.Pattern, str]]:
    """Os padrões de identificador da redação canônica. Levanta se não carregar.

    Mesmo arranjo de `auxiliaries.factory._modulo_de_redacao`: tenta o import
    normal e, sem o pacote montado (teste isolado, script), carrega o arquivo
    pelo caminho. A LISTA é a de lá — aqui só se escolhe quais marcas valem.
    """
    import importlib
    import importlib.util
    import sys

    nome = "app.services.intelligence.redaction_service"
    modulo = sys.modules.get(nome)
    if modulo is None:
        try:
            modulo = importlib.import_module(nome)
        except Exception:  # noqa: BLE001 — carga isolada por caminho
            caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "intelligence", "redaction_service.py")
            spec = importlib.util.spec_from_file_location(nome, caminho)
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            sys.modules[nome] = modulo
    padroes = [(p, m) for p, m in modulo.PADROES_PII if m in _SEGUNDA_REDE]
    if not padroes:
        raise RuntimeError("segunda rede sem padroes")
    return padroes


def _fixo_sem_ddd(texto: str) -> bool:
    for m in _FIXO_SEM_DDD.finditer(texto):
        a, b = m.group(1), m.group(2)
        if _PREFIXO_DE_CAPITAL.match(a) or (_ANO.match(a) and _ANO.match(b)):
            continue
        return True
    return False


def _vazamentos_no_texto(texto: str, perfis: List[_PerfilDeCorretora],
                         marcas: Tuple[str, ...],
                         rede: List[Tuple[re.Pattern, str]]) -> set:
    """Os TIPOS de vazamento que sobraram em `texto`. Nunca o trecho."""
    achou: set = set()
    if not texto:
        return achou
    # a. o mesmo mascarador (o do porteiro), de novo.
    remascarado = _mascarar_para_o_global(texto, marcas)
    antes = _PLACEHOLDER.findall(texto)
    depois = _PLACEHOLDER.findall(remascarado)
    achou.update(p for p in set(depois)
                 if p in _RESIDUO_DO_MASCARADOR and depois.count(p) > antes.count(p))
    visivel = _sem_publicos(texto)
    # b. a segunda rede, e as formas que nenhum dos dois motores pega.
    for padrao, marca in rede:
        if padrao.search(visivel):
            achou.add(marca)
    for padrao, marca in _FORMAS_QUE_OS_MOTORES_NAO_PEGAM:
        if padrao.search(visivel):
            achou.add(marca)
    if _fixo_sem_ddd(visivel):
        achou.add("[TELEFONE]")
    # c. a corretora, pelas variantes do nome que o banco dá.
    if _corretora_no_texto(visivel, perfis):
        achou.add("corretora")
    # d. nome de pessoa em contexto.
    if _nome_de_pessoa_no_texto(visivel):
        achou.add("nome_de_pessoa")
    return achou


def _textos_de(obj: Any) -> Iterable[str]:
    """Todo texto de um JSON: valores, CHAVES e números (telefone vira int)."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from _textos_de(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _textos_de(v)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield str(obj)


def anonimizar_para_o_global(conteudo: Any, *, tambem_conferir: Iterable[str] = ()
                             ) -> Tuple[Any, Dict[str, int], List[str]]:
    """(conteúdo a GRAVAR, o que foi mascarado por marca, o que SOBROU).

    Lista de sobras não vazia = NÃO GRAVE. Ela traz só TIPOS (`{CPF}`,
    `[TELEFONE]`, `corretora`, `nome_de_pessoa`, …), nunca o dado — pode ir
    para o log. `tambem_conferir` são textos que vão para a linha sem serem
    mascarados (as chaves `ramo`/`servico` do playbook): só se conferem, e a
    sobra deles vem com o prefixo `chave:`.
    """
    try:
        nomes = nomes_de_corretora_frescos()
        perfis = _perfis_de_corretora(nomes or ())
        marcas = _marcas_do_porteiro(perfis)
        mascarados: Dict[str, int] = {}

        def _limpar(v: Any) -> Any:
            if isinstance(v, str):
                limpo = _mascarar_para_o_global(v, marcas)
                antes = _PLACEHOLDER.findall(v)
                for p in _PLACEHOLDER.findall(limpo):
                    if p not in antes:
                        mascarados[p] = mascarados.get(p, 0) + 1
                return limpo
            if isinstance(v, dict):
                return {k: _limpar(x) for k, x in v.items()}
            if isinstance(v, (list, tuple)):
                return [_limpar(x) for x in v]
            return v

        limpo = _limpar(conteudo)
        sobras: set = set()
        if not nomes or not perfis:
            sobras.add("lista_de_corretoras_indisponivel")
        try:
            rede = _padroes_da_segunda_rede()
        except Exception:  # noqa: BLE001
            rede = []
            sobras.add("segunda_rede_indisponivel")
        for texto in _textos_de(limpo):
            sobras |= _vazamentos_no_texto(texto, perfis, marcas, rede)
        for texto in tambem_conferir:
            sobras |= {f"chave:{t}" for t in _vazamentos_no_texto(
                str(texto or ""), perfis, marcas, rede)}
        return limpo, mascarados, sorted(sobras)
    except Exception as e:  # noqa: BLE001
        # ⛔ Porteiro que quebra não abre a porta.
        return None, {}, [f"porteiro_falhou:{type(e).__name__}"]

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
# O FILTRO DE VALOR — "isto é sobre seguro?"
# ------------------------------------------------------------------ #
#
# 🔴 O CAMINHO INTEIRO EXISTIA E NINGUÉM PERGUNTAVA ISSO.
# =======================================================
# `conversa → transcrição → carta → RAG` estava aberto de ponta a ponta, e
# `publicar_lote_sync` leva `pending_review → published` **sem humano nenhum**.
# O único portão do caminho é o de PII — e ele responde OUTRA pergunta.
#
# 📊 `knowledge_cards` tem 320 cartas `rejected_pii`: o filtro de dado pessoal
# existe e reprova de verdade. Mas o WhatsApp de uma corretora é um telefone de
# gente: no meio das conversas com segurado vão existir o grupo do prédio, o
# convite de aniversário, o cunhado pedindo dinheiro. **Uma conversa doméstica
# sem um único CPF passa no filtro de PII sem disparar nada** — ela está
# perfeitamente anônima e continua não valendo nada para o cérebro.
#
# 📊 Em 03/08/2026 o Observador capturou 630 contatos pessoais e 2.556
# transcrições. Foi revertido a tempo e zero cartas foram geradas. Por sorte.
#
# POR QUE NÃO É `assunto_da_carta` COM OUTRO NOME
# ==============================================
# `_ASSUNTOS` responde "em que gaveta esta carta mora" e tem um catch-all que
# garante gaveta para QUALQUER texto — inclusive para "vou renovar o contrato
# do aluguel" (`renova` + `contrata`) e "minha vida está corrida" (`vida`).
# É um classificador de roteamento, calibrado para nunca deixar carta sem
# destino. Usá-lo como portão seria usar uma régua de encaixe como fechadura.
# A pergunta é outra, então a lista é outra — no mesmo módulo, à vista.
#
# DOIS NÍVEIS, E A RAZÃO DE EXISTIREM DOIS
# ========================================
# Um nível só não resolve. 📊 Medido em 08/08/2026 contra as 12.063 published:
# com um vocabulário único de seguro, **184 cartas (1,53%) seriam recusadas** —
# e ao ler as 184 uma a uma, a esmagadora maioria era conhecimento REAL de
# corretora que simplesmente não escreve a palavra "seguro":
#
#     "O analista pode solicitar documentos adicionais além dos padrões"
#     "Prazo padrão de retorno de solicitações é de 5 dias úteis"
#     "Assinaturas de herdeiros e testemunhas podem ser exigidas com firma
#      reconhecida"
#
# São a regulação de um sinistro de vida ou residencial descrita pelo trabalho,
# não pelo produto. Recusá-las é o custo que o CLAUDE.md §9.2 manda MEDIR em vez
# de deduzir — e medido, ele é alto demais.
#
# Então:
#   `_SOBRE_SEGURO`      uma menção BASTA. São palavras que só este mundo usa.
#   `_TRABALHO`          precisa de DUAS menções DISTINTAS. Cada uma sozinha
#                        aparece em qualquer conversa; duas juntas, não.
#
# 📊 O RESULTADO MEDIDO, 08/08/2026, contra as 12.063 `published`, refazendo a
# mesma consulta a cada ajuste (o número é a linha de controle da própria
# regra — sem ele, "ampliei o vocabulário" seria só uma afirmação):
#
#     um vocabulário só, sem nomes de companhia          184  (1,53%)
#     dois níveis, sem os nomes das seguradoras          399  (3,31%)  ← pior
#     + nomes de seguradora no nível forte               169  (1,40%)
#     + dinheiro repartido em seis entradas               64  (0,53%)  ← esta
#
# O passo que PIOROU é o que ensina: dois níveis com vocabulário estreito
# recusa mais que um nível largo. O ganho não veio de "ter dois níveis" — veio
# de o que está em cada um.
#
# E o que sobra nas 64 é o que deve sobrar. Elas descrevem trabalho de
# escritório que serviria a uma pizzaria: *"Reentrar no sistema (logout/login)
# pode resolver falhas de exibição"*, *"Problemas de conexão via QR Code podem
# ser resolvidos dando refresh na página"*, *"É comum informar previamente o
# DDD do número que fará o contato"*. Nenhuma delas ensina seguro a ninguém.
#
# ⚠️ O que NÃO entrou em `_TRABALHO`, de propósito: `foto`, `whatsapp`,
# `telefone`, `link`, `pdf`, `e-mail`, `mensagem`. São o vocabulário de
# QUALQUER conversa — "manda a foto do bolo no WhatsApp" bateria duas e passaria.
# Palavra de canal não é palavra de trabalho.
#
# ERRAR PARA QUAL LADO
# ====================
# Recusar carta boa é recuperável: ela fica em `rejected_fora_de_escopo`, com
# texto e hash intactos, e o admin pode aprovar uma a uma pelo /admin/espelho —
# o mesmo desenho de recuperação de `rejected_pii`. Publicar a vida particular
# do corretor no RAG da corretora não se desfaz.

# Uma menção BASTA. Sem acento: o texto é dobrado por `_sem_acento` antes.
_SOBRE_SEGURO = re.compile(
    r"\bsegur(?:o|os|ada|ado|adas|ados|adora|adoras|avel|aveis)\b|seguradora"
    r"|\bcorretor(?:a|as|es)?\b|corretagem|assessoria de seguros"
    r"|apolice|endosso|vigencia|franquia|cobertura|sinistr|susep|dpvat"
    r"|estipulante|beneficiari|indeniza|ressarcim|sub-roga|subroga"
    r"|regulaca|regulado|regulador|pericia|\bperito\b|salvado|perda total"
    r"|avaria|vistoria|\blaudo\b|boletim de ocorrencia|\bb\.?o\.?\b|delegacia"
    r"|guincho|reboque|chaveiro|pane seca|carro reserva|assistencia"
    # `prestador` é FORTE porque neste mundo ele tem dono: é quem a seguradora
    # manda ao local. Nenhuma conversa doméstica chama alguém assim.
    r"|prestador|rede referenciada|credenciad|oficina|autoglass|vidraceiro|borracheiro"
    r"|\bboleto|\bcarne\b|inadimpl|\bpremio\b|\bapolices\b"
    r"|\bcrlv\b|\bcnh\b|detran|renavam|chassi|\batpv|\bdut\b"
    r"|\bura\b|acionament|aviso de sinistro|central de atendimento"
    r"|\bplaca\b|\bveiculo|para-brisa|parabrisa"
    r"|desentup|encanador|eletricista|hidraulic|funeral|leva e traz"
    # O sinistro descrito pelo EVENTO, não pela palavra "sinistro". Um fato de
    # corretora fala de colisão, granizo e furto muito mais do que fala do
    # termo técnico — e nada disso é conversa doméstica.
    r"|colis|capotam|\bbatida\b|\broubo\b|\bfurto\b|\bfurtad|\broubad"
    r"|granizo|alagament|vendaval|enchente|incendio|\bsucata\b|\bsalvado"
    r"|reembols|prejuizo|\bavariad|\bterceiro envolvido|\bcotaca|\bcotacao"
    r"|\bmulta de transito|\bpane\b|\bsegurador"
    # Assistência residencial e automotiva pelo serviço prestado.
    r"|\bchave reserva|carro de aluguel|\btaxi\b|\bloja de vidros?\b"
    r"|caca-vazamento|impermeabiliza|\bmarido de aluguel\b"
    r"|vazament|entupiment|destelham|caixa d.agua|linha branca"
    r"|eletrodomestic|ar-condicionado|ar condicionado|\btelhad"
    # Vidro automotivo pelo defeito, não pela palavra "vidro" (que é de casa
    # também): trinca, estilhaço e película só aparecem num sinistro de vidros.
    r"|\btrinca|estilhac|\bpelicula\b|\bvigia\b|sensor de chuva",
    re.IGNORECASE)


def _nomes_de_seguradora() -> re.Pattern:
    """As companhias conhecidas, como um regex só. Cache de uma construção.

    🔴 O NOME DA COMPANHIA É, SOZINHO, PROVA DE ASSUNTO.
    📊 08/08/2026: sem esta peça o filtro recusava 399 das 12.063 published
    (3,31%), e a maior parte das recusadas era o acervo OBSERVADO — a corretora
    falando com a URA da seguradora. Essas cartas descrevem o robô do outro
    lado ("A Yelum encerra a conversa depois da terceira resposta que ela não
    aceita") e podem não escrever nenhuma outra palavra de seguro. Com os nomes
    dentro, 📊 a recusa caiu para 169 (1,40%).

    A tabela é a MESMA de `_formas_da_seguradora` e de
    `aplicar_seguradoras._companhias_citadas`: `corridor_playbooks`. Uma
    segunda lista de "quem é seguradora" envelheceria separada da primeira, e a
    cópia que ninguém olha é sempre a que envelhece antes (CLAUDE.md §5).

    `_NOME_AMBIGUO` continua valendo: 📊 `caixa` aparece 80 vezes nas published
    e 31 delas são "caixa d'água". Aqui a palavra solta não prova assunto — e a
    caixa d'água já é aceita pelo vocabulário de assistência, com o nome certo.
    """
    global _RX_SEGURADORAS
    if _RX_SEGURADORAS is None:
        from app.services.corridor_playbooks import _INSURER_ALIASES

        formas = sorted({_sem_acento(a).lower() for a in _INSURER_ALIASES
                         if a not in _NOME_AMBIGUO and len(a) >= 3},
                        key=len, reverse=True)
        _RX_SEGURADORAS = re.compile(
            "|".join(rf"\b{re.escape(f)}\b" for f in formas))
    return _RX_SEGURADORAS


_RX_SEGURADORAS: Optional[re.Pattern] = None


# Precisa de DUAS DISTINTAS. Lista, e não um regex só, porque o que importa
# aqui é QUANTAS bateram — um `search` responderia "pelo menos uma", que é
# exatamente a pergunta errada.
_TRABALHO: Tuple[str, ...] = (
    r"\banalista\b|\banalistas\b",
    r"document",                 # documento, documentação, documental
    r"\bprocesso\b|\bprocessos\b",
    r"\bprazo|dias uteis|horas uteis",
    r"formulario|\bformularios\b",
    r"\banexo|\banexar|\banexad",
    r"orcamento|orcamentos",
    r"nota fiscal|notas fiscais",
    r"comprova",                 # comprovante, comprovação, comprovar
    r"pendencia|pendencias|pendente",
    r"cartorio|firma reconhecida|autentica",
    r"herdeir|inventario|obito|falecid|espolio",
    r"reanalise|\banalise\b|reabertura|reaberto",
    r"solicitad|solicitac|solicitar|solicita\b",
    r"exigid|exigenc|\bexige\b|\bexigem\b",
    r"\bsindico\b|assembleia|administradora|condominio",
    r"procuracao|\btermo de\b|declaracao",
    r"\breparo|conserto|\bobra\b|mao de obra|material|telhado|pedreiro",
    r"\btecnico\b|\btecnicos\b|agendament|\bvisita\b",
    r"cadastro|cadastros|cadastrad",
    r"liberaca|autorizac|autorizad|aprovac|aprovad",
    r"\bmatriz\b|\bfilial\b|\bcarteira\b|\bequipe\b|\bcentral\b",
    r"\bcpf\b|\bcnpj\b|\brg\b|identidade|titular",
    r"\bcliente|\bsegurado",     # `segurado` também é forte; aqui só soma
    r"protocolo|atendiment|atendente",
    r"\bimovel|\bresidencia|\bfachada|\bsinistrad",
    r"\bbanco\b|\bagencia\b|\bconta\b|deposito|transferencia",
    r"\bportal\b|\bsistema\b|\bmenu\b|\bcanal\b",
    r"\bprova\b|\bprovas\b|\bevidencia|relatorio|monitoramento",
    r"\bvalor\b|\bvalores\b|\bdesconto\b|\bcredito\b",
    r"\bretirada\b|\bdevolucao\b|\breserva\b|\bremocao\b",
    # DINHEIRO, EM SEIS ENTRADAS E NÃO EM UMA.
    #
    # 📊 Colapsado num balde só, este vocabulário custou a categoria `cobranca`
    # inteira: "Cobranças alternativas costumam ter data de vencimento
    # definida" batia UMA vez e era recusada, embora seja cobrança de prêmio de
    # ponta a ponta. Um balde grande demais vale o mesmo que um termo — e a
    # regra dos dois só funciona se os dois puderem ser coisas diferentes.
    r"pagament|\bpagar\b|\bpago\b|\bpaga\b",
    r"cobranc|\bcobrar\b|\bcobrad",
    r"\bparcela|\bcarne\b|\bcarnes\b|recorrent",
    r"vencimento|\bvence\b|\bvencid|data limite|\batraso\b|em aberto",
    r"\bpix\b|qrcode|qr code|codigo de barras|linha digitavel|copia-e-cola",
    r"\bcartao|\bcredito\b|\bdebito|\bfatura|\bjuros\b|estorno|quitac|quitad",
    # O aviso e o terceiro — as duas palavras que o acervo usa o tempo todo
    # sem escrever "sinistro" ao lado.
    r"\baviso\b|\bavisos\b|\bchamado|\bocorrencia\b|\bevento\b",
    r"\bterceiro|\bsegurada\b|\bfamilia\b|\bempresa\b",
    # O contrato. "renovar" e "contratar" sozinhos servem para plano de
    # celular e aluguel — por isso moram aqui, e não no nível forte.
    r"renova|proposta|emissao|\bemitir\b|\bemitid|cancelament|cancelad"
    r"|\bcancelar\b|rescis|contrata|\bcontrato\b",
    # O estrago e o serviço, sem a palavra do evento.
    r"\bdano|\bdanific|\bpeca\b|\bpecas\b|\bpintura\b|\bfunilaria\b|\bvidro",
    r"\bprestador|\bloja\b|concessionaria|locadora|\bagenda\b|\bfila\b",
    # O ramo do seguro. Cada um é palavra comum do português — "vida",
    # "saúde", "auto", "pet" —, e é justamente por isso que somam em vez de
    # decidir sozinhos.
    r"\bvida\b|\bsaude\b|\bpet\b|\bfrota\b|\bramo\b|empresarial|\bauto\b",
)

# Quantas palavras do trabalho precisam aparecer juntas. Duas, e não uma: uma
# só é o normal de qualquer conversa ("me manda o cadastro do salão de festas").
MENCOES_DE_TRABALHO = 2

# O status de quem foi recusada AQUI. Nome próprio, e não `rejected_pii`: a
# carta não vazou nada de ninguém — ela simplesmente não é sobre seguro. Um
# nome que mente sobre o que guarda reinfecta todo leitor seguinte
# (CLAUDE.md §12.1), e sem nome próprio ninguém consegue medir este filtro
# separado do outro depois.
STATUS_FORA_DE_ESCOPO = "rejected_fora_de_escopo"


def e_sobre_seguro(texto: str) -> bool:
    """Esta CARTA pertence ao mundo de seguros? Determinístico, sem modelo.

    Decide sobre a carta — o fato destilado —, não sobre a conversa inteira.
    A conversa é longa, mistura assuntos e não é o que vai para o RAG; a carta
    é uma frase só, e é ela que o agente vai repetir para um segurado.

    Sem LLM de propósito: isto roda sobre milhares de cartas por rodada, e uma
    chamada de modelo aqui seria cara, lenta e — pior — não reprodutível: a
    mesma carta poderia ser aceita hoje e recusada amanhã sem nada ter mudado.
    """
    alvo = _sem_acento(str(texto or "")).lower()
    if _SOBRE_SEGURO.search(alvo) or _nomes_de_seguradora().search(alvo):
        return True
    batidas = 0
    for padrao in _TRABALHO:
        if re.search(padrao, alvo):
            batidas += 1
            if batidas >= MENCOES_DE_TRABALHO:
                return True
    return False


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


# Quanto duas cartas precisam falar do mesmo assunto para uma poder APOSENTAR a
# outra. É menor que `LIMIAR` (o de quase-cópia) de propósito: a carta que nega
# carrega palavras que a que afirma não tem ("não", "deixou", "mais"), então o
# par contraditório é sempre MENOS parecido que o par duplicado.
#
# 📊 Calibrado contra o caso real da Porto (07/08/2026), que é o motivo deste
# código existir. A medida é CONTENÇÃO — quanto da carta MENOR está na maior —
# e não Jaccard, e isso foi medido, não escolhido:
#
#   par                                  contenção   jaccard
#   ─────────────────────────────────────────────────────────
#   nega × afirma (4 pares reais)        0,33–0,60   0,18–0,33   ← devem casar
#   assunto diferente, mesma companhia   0,14        0,06        ← não podem
#
# O Jaccard punia a carta que nega por ela ser mais longa: ela traz a explicação
# inteira ("...há cerca de 55 dias para pagar") e a que afirma não. Com Jaccard,
# o par real ficava em 0,20 e qualquer limiar que o pegasse pegaria lixo junto.
# Contenção não se importa com o tamanho do texto maior.
#
# ⚠️ O guarda contra o falso positivo não é o limiar: são QUATRO exigências ao
# mesmo tempo — mesma seguradora, mesma categoria, contenção acima do corte e
# polaridade oposta. Quatro coincidências, não uma.
LIMIAR_CONTRADICAO = 0.30


# As formas de dizer "isto nao acontece (mais)". Uma lista so, dois usos: a
# contradicao entre cartas do RAG (aqui) e entre memorias da corretora
# (`memory_fabric.contradiz`, que importa daqui).
#
# 📊 Calibrada contra o caso real da Porto: "nao e mais atualizado" e "deixou
# de atualizar" sao as duas formas que apareceram no acervo.
NEGACOES = ("nao ", "não ", "nunca ", "jamais ", "deixou de ", "deixaram de ",
            "nao e mais", "não é mais", "nao ha mais", "não há mais")


def tem_negacao(texto: str) -> bool:
    """O texto NEGA alguma coisa? Sinal de polaridade, nao de sentido."""
    return any(n in str(texto or "").lower() for n in NEGACOES)


def contencao(a: frozenset, b: frozenset) -> float:
    """Quanto do MENOR conjunto está no maior. 0..1.

    Diferente de `parecidas` (Jaccard), não penaliza um texto por ser mais
    longo que o outro — que é exatamente o que acontece quando a carta nova
    explica a regra nova e a antiga só a afirmava.
    """
    return len(a & b) / max(1, min(len(a), len(b))) if a and b else 0.0


def achar_contradicoes(
    novas: List[Dict[str, Any]], publicadas: List[Dict[str, Any]]
) -> List[Tuple[str, str]]:
    """Pares `(id_publicada_a_aposentar, id_nova_que_substitui)`.

    🔴 A CURADORIA SÓ OLHAVA A FILA. NUNCA O ACERVO.
    ================================================
    `escolher_representantes` compara a carta nova com as outras cartas novas do
    mesmo lote. Conhecimento novo nunca desafiava conhecimento velho — e por
    isso o RAG podia afirmar duas coisas opostas ao mesmo tempo.

    📊 07/08/2026, cartas sobre boleto da Porto, TODAS publicadas:

        28–29/07  "Porto Seguro emite boleto ATUALIZADO quando há parcela
                   em aberto, com novo prazo de vencimento"
        30/07     "Na Porto o boleto NÃO É MAIS atualizado"
                  "A Porto DEIXOU DE atualizar boleto"

    Cinco afirmavam, três negavam, zero foram aposentadas. O agente respondia
    uma ou outra por sorte da busca — e dizer a um segurado *"peça o boleto
    atualizado"* quando a Porto deixou de emitir faz ele perder o prazo e a
    apólice cancelar. O dano não é uma resposta feia: é um cliente sem seguro.

    O código já documentava este caso exato como motivo de existir
    `despublicar_carta_sync`. A função foi escrita e nunca foi chamada, porque
    só rodava por clique numa tela de admin.

    O QUE IMPEDE DE APOSENTAR CARTA BOA
    ===================================
    Três exigências ao mesmo tempo, não uma:

    1. **mesma seguradora** — regra da Porto não aposenta regra da HDI;
    2. **mesma categoria** — cobrança não aposenta sinistro;
    3. **polaridade oposta** — uma nega o que a outra afirma (`contradiz`).

    E a mais nova ganha, sempre: a seguradora mudou a regra, e é o fato recente
    que vale. A antiga não é apagada — vira `superseded` com o ponteiro para
    quem a substituiu, e sai do índice. Histórico auditável, RAG limpo.
    """
    # A régua de "falam da mesma coisa" é desta casa: 📊 o corte de 0,6 de
    # `memory_fabric.contradiz` não serve para carta (o par real da Porto dá
    # 0,30), porque a carta que nega traz a explicação inteira e a que afirma
    # não. `tem_negacao` (a polaridade) é compartilhada; a medida, não.
    pares: List[Tuple[str, str]] = []
    aposentadas: set = set()

    # Índice por (seguradora, categoria): só se compara o que é comparável.
    balde: Dict[Tuple[Any, Any], List[Dict[str, Any]]] = {}
    for antiga in publicadas:
        chave = (antiga.get("insurer_key"), antiga.get("category"))
        balde.setdefault(chave, []).append(antiga)

    for nova in novas:
        texto_novo = str(nova.get("card_text") or "")
        sig_nova = assinatura(texto_novo)
        if len(sig_nova) < 3:
            continue  # curta demais para afirmar contradição de nada
        chave = (nova.get("insurer_key"), nova.get("category"))
        for antiga in balde.get(chave, []):
            if antiga["id"] in aposentadas:
                continue
            texto_antigo = str(antiga.get("card_text") or "")
            if contencao(sig_nova, assinatura(texto_antigo)) < LIMIAR_CONTRADICAO:
                continue
            # Polaridade OPOSTA. Duas que afirmam são quase-cópias (outro
            # tratamento); duas que negam concordam. Só o par afirma × nega é
            # contradição — e é ele que aposenta.
            if tem_negacao(texto_novo) == tem_negacao(texto_antigo):
                continue
            pares.append((antiga["id"], nova["id"]))
            aposentadas.add(antiga["id"])
    return pares


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
    sobreviventes = [c for c in cartas if c["id"] not in proibidos]
    ficam, copias = escolher_representantes(sobreviventes)

    # 🔴 O SEGUNDO OLHO: a carta nova é comparada com o ACERVO, não só com o
    # lote. Ver `achar_contradicoes` para o caso da Porto que motivou isto.
    #
    # Só as que ficaram desafiam o acervo: uma quase-cópia que já perdeu para
    # outra do próprio lote não tem por que aposentar nada.
    ids_que_ficam = set(ficam)
    contradicoes = achar_contradicoes(
        [c for c in sobreviventes if c["id"] in ids_que_ficam],
        _acervo_publicado_sync(db),
    )

    if aplicar:
        for ids, status in ((barradas, "rejected_absoluto"), (copias, "superseded")):
            for i in range(0, len(ids), 100):
                db.client.table("knowledge_cards").update({"status": status}) \
                    .in_("id", ids[i:i + 100]).execute()
        _aposentar_contraditas_sync(db, contradicoes)

    return {"lidas": len(cartas), "barradas": len(barradas),
            "juntadas": len(copias), "ideias_distintas": len(ficam),
            "contraditas_aposentadas": len(contradicoes), "aplicado": aplicar}


def _acervo_publicado_sync(db: Any) -> List[Dict[str, Any]]:
    """Todas as cartas publicadas. Paginado — o PostgREST corta em 1.000.

    📊 12.071 publicadas em 07/08/2026: são 13 páginas. Vale a ida: sem o
    acervo em mãos, a curadoria compara a carta nova só com as outras novas, e
    foi assim que 5 cartas afirmaram e 3 negaram a mesma regra da Porto ao
    mesmo tempo, por oito dias.
    """
    saida: List[Dict[str, Any]] = []
    inicio = 0
    while True:
        lote = (db.client.table("knowledge_cards")
                .select("id, card_text, insurer_key, ramo, category")
                .eq("status", "published")
                # `id` e não `created_at`: a destilação grava até oito cartas no
                # mesmo instante e o Postgres não promete ordem entre iguais.
                # 📊 Paginar por data já perdeu 12 linhas e repetiu 12 em 11.640.
                .order("id", desc=False)
                .range(inicio, inicio + 999).execute().data) or []
        saida.extend(lote)
        if len(lote) < 1000:
            return saida
        inicio += 1000
        if inicio > 200_000:
            return saida


def _aposentar_contraditas_sync(db: Any, pares: List[Tuple[str, str]]) -> None:
    """Aposenta a carta velha e ANOTA quem a substituiu.

    A anotação não é enfeite: sem ela, ninguém consegue responder "por que esta
    carta saiu do ar?" seis meses depois — e uma aposentadoria que não se
    explica é indistinguível de um apagamento por engano.

    Tira do índice também. Mudar o status sem apagar o vetor deixa o pior estado
    possível: uma carta que a auditoria vê como removida e a busca continua
    entregando.
    """
    from app.services.attendance_distiller import despublicar_carta_sync

    for id_antiga, id_nova in pares:
        try:
            atual = (db.client.table("knowledge_cards").select("pii_check")
                     .eq("id", id_antiga).limit(1).execute().data or [{}])
            marca = dict((atual[0] or {}).get("pii_check") or {})
            marca["substituida_por"] = id_nova
            marca["aposentada_em"] = _agora_iso()

            # 🔴 A ORDEM ERA O INVERSO — E A ORDEM É O CONSERTO.
            #
            # O `update` vinha primeiro e `despublicar_carta_sync` depois, com o
            # retorno descartado. Quando o índice recusasse, o banco já diria
            # `superseded` e ninguém saberia: a carta some da auditoria e
            # continua respondendo ao segurado. É o estado que o docstring
            # acima chama de "o pior possível", produzido pela própria função.
            #
            # Agora o índice manda: só depois de o vetor sair é que o banco
            # muda. Se o Qdrant recusar, a carta continua `published` — visível,
            # errada e ACHÁVEL, que é melhor que invisível e errada. A marca
            # `qdrant_pendente` fica para o reconciliador reencontrar.
            if not despublicar_carta_sync(id_antiga, motivo="superseded"):
                marca["qdrant_pendente"] = True
                db.client.table("knowledge_cards").update(
                    {"pii_check": marca}).eq("id", id_antiga).execute()
                logger.error("[CURADORIA] %s NÃO saiu do índice — continua "
                             "publicada e marcada para reconciliação", id_antiga)
                continue

            # `despublicar_carta_sync` já gravou `status`; aqui vai só a
            # anotação de POR QUE ela saiu, que é o que ninguém consegue
            # reconstruir seis meses depois.
            db.client.table("knowledge_cards").update(
                {"pii_check": marca}).eq("id", id_antiga).execute()
        except Exception as erro:  # noqa: BLE001
            # Uma que falha não pode derrubar as outras: cada carta ainda
            # publicada e já contradita é uma resposta errada ao segurado.
            logger.warning("[CURADORIA] não consegui aposentar %s (%s)",
                           id_antiga, type(erro).__name__)


def _agora_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


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

    🔴 E AQUI FICA O FILTRO DE VALOR — porque ESTA é a porta automática.
    ==================================================================
    Esta função é o único ponto em que uma carta vira `published` **sem que
    ninguém tenha olhado para ela**. O portão de PII já mora dentro do
    `publish_card_sync`; o de valor mora aqui, e não lá, por um motivo concreto:
    `publish_card_sync` devolvendo `False` faz esta função marcar
    `rejected_pii`, e uma carta recusada por não ser sobre seguro **não vazou
    nada de ninguém**. Marcá-la assim seria um nome mentindo sobre o que guarda,
    e o próximo a medir "quantas cartas vazaram PII?" contaria errado.

    A aprovação manual do /admin/espelho NÃO passa por aqui de propósito: lá um
    master admin está olhando uma carta específica e dizendo "publique esta".
    Isso É a aprovação humana que o P-67 pede — e é por ela que uma carta
    recusada aqui volta ao acervo, se alguém decidir que ela deve voltar.
    """
    from app.core.database import get_supabase_client
    from app.services.attendance_distiller import publish_card_sync

    db = get_supabase_client()
    reconciliado = reconciliar_indice_sync()
    # 🔴 O SELECT E A LISTA DO QUE SOBREVIVE — 15/08/2026 (SPEC-072).
    # Este caminho roda SOZINHO a cada rodada do Destilador, e pedia quatro
    # colunas. `publish_card_sync` grava no Qdrant o que recebe, e `category`,
    # `source_unit_id` e a `faceta` (que mora em `pii_check`) nao vinham — logo
    # nao chegavam ao indice. Pior, sem `source_unit_id` a rede de PII roda
    # apertada numa carta de documento publico e a recusa vira `rejected_pii`,
    # que e um nome mentindo sobre o que aconteceu. Mesmo defeito de
    # `reindexar_acervo.py:157`, mesma correcao.
    alvo = (db.client.table("knowledge_cards")
            .select("id, card_text, insurer_key, ramo, category, "
                    "source_unit_id, pii_check, temas")
            .eq("status", "pending_review")
            .order("created_at", desc=False)
            .limit(max(1, min(int(limite or 300), 2000))).execute().data) or []

    publicadas = falhas = fora_de_escopo = 0
    for c in alvo:
        try:
            if not e_sobre_seguro(c.get("card_text") or ""):
                # NÃO SOME, e não volta para a fila. Fica com status próprio,
                # texto e hash intactos: dá para contar, listar, revisar e
                # aprovar uma a uma. É o mesmo desenho de `rejected_pii` — o
                # que muda é só o nome, e o nome é a informação.
                db.client.table("knowledge_cards").update(
                    {"status": STATUS_FORA_DE_ESCOPO}).eq("id", c["id"]).execute()
                fora_de_escopo += 1
                continue
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
            "fora_de_escopo": fora_de_escopo,
            "indice_reconciliado": reconciliado.get("limpas", 0),
            "indice_pendente": reconciliado.get("falhas", 0)}
