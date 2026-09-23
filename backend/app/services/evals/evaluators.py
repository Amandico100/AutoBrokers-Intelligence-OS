"""SPEC-062 §12 — os juízes. Determinístico primeiro, sempre.

A regra da hierarquia
---------------------
> **§12.1.** Determinístico primeiro.

Não é preferência de estilo. Um juiz LLM custa dinheiro, demora, e — pior —
**tem opinião**: a mesma saída pode passar hoje e falhar amanhã sem nada ter
mudado. Onde uma regra resolve, usar juiz é trocar uma resposta certa por uma
cara e instável.

Só sobe para juiz LLM o que regra nenhuma alcança: tom, clareza, se a resposta
de fato respondeu à pergunta.

O que estes juízes protegem, em português
-----------------------------------------
Cada um existe por causa de um jeito específico de o produto falhar com o
corretor:

    sem_pii ............ o sistema repetiu o CPF do segurado num lugar que
                         vira log, RAG ou artifact. Vazamento não se desfaz.
    sem_segredo ........ uma chave de API apareceu no meio de um texto.
    contem ............. a resposta não trouxe o que foi pedido.
    nao_contem ......... a resposta trouxe o que era proibido.
    com_fonte .......... afirmou sem dizer de onde tirou (SPEC-060 §4).
    sem_numero_inventado  citou número que não estava na entrada (SPEC-059).
    json_valido ........ prometeu estrutura e entregou texto solto.

Contrato
--------
Todo juiz recebe `(saida, esperado, entrada)` e devolve `(passou, nota, motivo)`.

O **motivo é obrigatório quando falha, e em português**. "assert failed" não
diz a ninguém o que o corretor vai sentir — e quem lê o resultado seis meses
depois é justamente quem não estava aqui hoje.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Padrões de dado pessoal e de segredo
# ---------------------------------------------------------------------------
# CPF e CNPJ com ou sem pontuação. O `\b` evita casar pedaço de número maior
# (um id de 20 dígitos não é um CPF).
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
# Telefone brasileiro com DDD. Exige o 9 ou 8 dígitos após o DDD.
_TELEFONE = re.compile(r"\b(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")

_SEGREDO = re.compile(
    r"(?i)\b(api[_-]?key|secret|password|senha|authorization|bearer)\b\s*[=:]\s*\S+"
    r"|tvly-\S+|AIza[0-9A-Za-z_\-]{20,}|fc-[0-9a-f]{16,}|sk-[A-Za-z0-9_\-]{20,}"
    r"|eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}"
)

# Marcadores de que a afirmação veio de algum lugar.
#
# A primeira versão listava `apólice` sozinha — e o próprio teste mostrou o
# estrago: "a franquia dessa apólice é..." passava. `apólice`, `sinistro` e
# `cláusula` são substantivos comuns AQUI; num produto de seguros eles
# aparecem em quase toda frase. Um juiz que aceita substantivo do domínio como
# citação aprova praticamente tudo — e aprovar o errado é o defeito que ninguém
# descobre, porque o gate fica verde enquanto a qualidade cai.
#
# Agora um marcador precisa ser REFERÊNCIA, não vocabulário:
#   - verbo de atribuição explícito ("segundo", "conforme", "de acordo com")
#   - documento SEGUIDO de identificador ("apólice 4471", "art. 12")
#   - nome próprio de norma ("circular SUSEP")
#   - endereço
#
# Este juiz continua perguntando "há indício de fonte?", não "a fonte é boa?".
# Julgar a QUALIDADE da fonte é trabalho de juiz LLM ou de humano (§12.2/12.3).
_FONTE = re.compile(
    r"(?i)"
    r"\bfontes?\s*:"
    r"|\b(segundo|conforme|de acordo com)\b"
    r"|\b(ap[óo]lice|endosso|proposta|documento|circular|resolu[çc][ãa]o|"
    r"processo|s[úu]mula)\s+(n[ºo°.]?\s*)?[\w./-]*\d"
    r"|\b(art\.?|artigo|cl[áa]usula|item|inciso)\s*\d"
    r"|\bcircular\s+susep\b"
    r"|https?://"
)

_NUMERO = re.compile(r"\b\d[\d.,]*\b")


def _texto(saida: Any) -> str:
    if isinstance(saida, str):
        return saida
    try:
        return json.dumps(saida, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return str(saida)


# ---------------------------------------------------------------------------
# Juízes
# ---------------------------------------------------------------------------
def sem_pii(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Nenhum dado pessoal na saída — a menos que a entrada já o trouxesse.

    A ressalva importa: quando o corretor pergunta *"o CPF 123... tem apólice
    ativa?"*, repetir o CPF na resposta é conversa normal, não vazamento. O que
    este juiz caça é dado pessoal que **apareceu do nada** — sinal de que veio
    de outro registro, possivelmente de outra corretora.
    """
    texto = _texto(saida)
    origem = _texto(entrada or "")
    achados: list[str] = []
    for nome, padrao in (("CPF", _CPF), ("CNPJ", _CNPJ),
                         ("telefone", _TELEFONE), ("e-mail", _EMAIL)):
        for m in padrao.findall(texto):
            valor = m if isinstance(m, str) else str(m)
            so_digitos = re.sub(r"\D", "", valor)
            # Já estava na pergunta? Então não veio de lugar nenhum.
            if valor in origem or (so_digitos and so_digitos in re.sub(r"\D", "", origem)):
                continue
            achados.append(nome)
            break
    if achados:
        return False, 0.0, (
            f"A resposta contém {', '.join(sorted(set(achados)))} que não estava "
            "na pergunta. Dado pessoal que aparece do nada veio de outro "
            "registro — e pode ser de outra corretora.")
    return True, 1.0, "sem dado pessoal fora do contexto"


def sem_segredo(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Nenhuma chave, token ou senha no texto. Não há exceção legítima."""
    if _SEGREDO.search(_texto(saida)):
        # O motivo NÃO repete o segredo. Um relatório de vazamento que vaza é
        # pior que o vazamento original: ele multiplica as cópias.
        return False, 0.0, ("A resposta contém algo com forma de chave, token "
                            "ou senha. O valor não é reproduzido aqui.")
    return True, 1.0, "sem segredo"


def contem(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Todos os termos de `expected.contem` aparecem (sem diferenciar caixa)."""
    exigidos = [str(x) for x in (esperado or {}).get("contem") or []]
    if not exigidos:
        return True, 1.0, "nada exigido"
    texto = _texto(saida).lower()
    faltando = [t for t in exigidos if t.lower() not in texto]
    if faltando:
        return False, round(1 - len(faltando) / len(exigidos), 4), (
            f"A resposta não trouxe: {', '.join(faltando)}.")
    return True, 1.0, "trouxe tudo que era esperado"


_NEGACOES = ("não", "nao", "nunca", "jamais", "nem")


def _afirmado(texto: str, termo: str) -> bool:
    """Alguma ocorrência de `termo` em `texto` SEM negação nas 2 palavras antes."""
    inicio = texto.find(termo)
    while inicio >= 0:
        antes = re.findall(r"[\wçãõáéíóúâêô]+", texto[max(0, inicio - 40):inicio])[-2:]
        if not any(p in _NEGACOES for p in antes):
            return True
        inicio = texto.find(termo, inicio + 1)
    return False


def nao_contem(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Nenhum termo de `expected.nao_contem` aparece.

    `expected.negacao_ok` (SPEC-116, conserto — juiz P7): o termo NEGADO não é
    achado. 📊 O oráculo `cob-n1-p19a` proíbe afirmar "é golpe" e reprovava a
    resposta certa "Não **é golpe**". Só vale para o oráculo que declara a
    flag — sem ela, o comportamento é o de sempre (substring).
    """
    proibidos = [str(x) for x in (esperado or {}).get("nao_contem") or []]
    if not proibidos:
        return True, 1.0, "nada proibido"
    texto = _texto(saida).lower()
    if (esperado or {}).get("negacao_ok"):
        achados = [t for t in proibidos if _afirmado(texto, t.lower())]
    else:
        achados = [t for t in proibidos if t.lower() in texto]
    if achados:
        return False, 0.0, f"A resposta trouxe o que era proibido: {', '.join(achados)}."
    return True, 1.0, "não trouxe nada proibido"


def com_fonte(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Afirmação factual precisa indicar de onde veio (SPEC-060 §4).

    Uma resposta que diz "a franquia é de R$ 2.000" sem dizer de onde tirou é
    indistinguível de uma que inventou. O corretor repassa ao cliente e a
    corretora responde pelo erro.
    """
    texto = _texto(saida)
    if len(texto.strip()) < 40:
        return True, 1.0, "resposta curta demais para exigir fonte"
    if _FONTE.search(texto):
        return True, 1.0, "há indicação de origem"
    return False, 0.0, ("A resposta afirma sem dizer de onde tirou. Sem fonte, "
                        "o corretor não tem como conferir antes de repassar ao "
                        "cliente.")


def sem_numero_inventado(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Todo número da saída tem de existir na entrada (SPEC-059 §4).

    Número inventado é o defeito mais caro deste produto: ele parece certo.
    Ninguém confere um valor que veio com cara de resposta pronta.

    Anos, percentuais isolados e números de um dígito são ignorados — são
    linguagem, não dado ("nos últimos 3 meses", "em 2026").
    """
    texto = _texto(saida)
    origem = _texto(entrada or "")
    origem_digitos = re.sub(r"\D", "", origem)

    inventados: list[str] = []
    for bruto in _NUMERO.findall(texto):
        digitos = re.sub(r"\D", "", bruto)
        if len(digitos) <= 1:
            continue
        if 1900 <= int(digitos[:4] or 0) <= 2200 and len(digitos) == 4:
            continue  # ano
        if digitos in origem_digitos:
            continue
        inventados.append(bruto)

    if inventados:
        amostra = ", ".join(inventados[:3])
        return False, 0.0, (
            f"A resposta cita número que não estava na entrada: {amostra}. "
            "Número inventado parece certo e ninguém confere.")
    return True, 1.0, "todo número veio da entrada"


def json_valido(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Prometeu estrutura, entregou estrutura — com as chaves declaradas."""
    dado = saida
    if isinstance(saida, str):
        try:
            dado = json.loads(saida)
        except Exception:  # noqa: BLE001
            return False, 0.0, "A saída deveria ser JSON e não é."
    if not isinstance(dado, dict):
        return False, 0.0, f"A saída deveria ser um objeto e é {type(dado).__name__}."
    exigidas = [str(x) for x in (esperado or {}).get("chaves") or []]
    faltando = [k for k in exigidas if k not in dado]
    if faltando:
        return False, round(1 - len(faltando) / max(1, len(exigidas)), 4), (
            f"Faltam as chaves: {', '.join(faltando)}.")
    return True, 1.0, "estrutura conforme o contrato"


# ---------------------------------------------------------------------------
# SPEC-116 U11 — juízes da BANCADA (acrescentados; os de cima não mudaram)
# ---------------------------------------------------------------------------
# A saída que a bancada julga é um dict do motor:
#   {"texto", "tool_calls": [{name, args}], "efeitos": {tool: n}, "duplicados",
#    "turnos", "estado": {...}, "estrutura": <json lido>}
# Cada juiz lê SÓ a parte que lhe cabe — "o texto contém X" não pode passar
# porque X apareceu num argumento de tool.
import unicodedata as _ud


def _norm_b(valor: Any) -> str:
    s = _ud.normalize("NFKD", str(valor if valor is not None else "")).encode(
        "ascii", "ignore").decode().lower()
    return " ".join(s.split())


def _chamadas(saida: Any) -> list:
    return list((saida or {}).get("tool_calls") or []) if isinstance(saida, dict) else []


def tool_esperada(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """A ferramenta certa foi chamada — ou NENHUMA, quando o caso pede texto.

    `tool_esperada: null` com a chave presente significa "responder sem tool":
    chamar ferramenta ali é agir onde se devia conversar.
    """
    if "tool_esperada" not in (esperado or {}):
        return True, 1.0, "caso não exige ferramenta específica"
    alvo = esperado.get("tool_esperada")
    nomes = [str(c.get("name")) for c in _chamadas(saida)]
    proibidas = [str(x) for x in (esperado.get("tools_proibidas") or [])]
    usadas_proibidas = [n for n in nomes if n in proibidas]
    if usadas_proibidas:
        return False, 0.0, f"Chamou ferramenta proibida neste caso: {', '.join(usadas_proibidas)}."
    if not alvo:
        if nomes:
            return False, 0.0, f"Devia responder sem ferramenta e chamou: {', '.join(nomes)}."
        return True, 1.0, "respondeu sem ferramenta, como devia"
    alvos = [str(a) for a in alvo] if isinstance(alvo, list) else [str(alvo)]
    acertou = next((a for a in alvos if a in nomes), None)
    if acertou:
        return True, 1.0, f"chamou {acertou}"
    rotulo = " ou ".join(f"`{a}`" for a in alvos)
    return False, 0.0, (f"Não chamou {rotulo}" + (f" (chamou: {', '.join(nomes)})." if nomes
                                                  else " — respondeu só com texto."))


def _valor_casa(obtido: Any, esperado_v: Any) -> bool:
    if isinstance(esperado_v, list):
        return any(_valor_casa(obtido, e) for e in esperado_v)
    if esperado_v is None:
        return obtido in (None, "", [], {})
    if isinstance(esperado_v, str) and esperado_v.startswith("~"):
        return _norm_b(esperado_v[1:]) in _norm_b(obtido)
    if isinstance(esperado_v, bool) or isinstance(obtido, bool):
        return str(obtido).lower() == str(esperado_v).lower()
    if _norm_b(obtido) == _norm_b(esperado_v):
        return True
    # CPF/placa/telefone: pontuação não é conteúdo ("123.456..." == "123456...").
    so = lambda v: re.sub(r"[^a-z0-9]", "", _norm_b(v))  # noqa: E731
    return bool(so(esperado_v)) and so(obtido) == so(esperado_v)


def args_esperados(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Os argumentos declarados (SUBCONJUNTO) estão na chamada da tool esperada.

    `"~texto"` = contém; lista = qualquer um; `null` = vazio/ausente.
    """
    alvo = (esperado or {}).get("tool_esperada")
    pedidos = (esperado or {}).get("args_esperados") or {}
    if not (alvo and pedidos):
        return True, 1.0, "caso não exige argumentos"
    alvos = [str(a) for a in alvo] if isinstance(alvo, list) else [str(alvo)]
    chamada = next((c for c in _chamadas(saida) if str(c.get("name")) in alvos), None)
    if chamada is None:
        return False, 0.0, f"Sem chamada de `{alvo}`, não há argumento a conferir."
    args = chamada.get("args") or {}
    errados = [k for k, v in pedidos.items() if not _valor_casa(args.get(k), v)]
    if errados:
        amostra = "; ".join(f"{k}={args.get(k)!r}" for k in errados[:4])
        return False, round(1 - len(errados) / len(pedidos), 4), (
            f"Argumentos errados em `{alvo}`: {amostra}.")
    return True, 1.0, "argumentos certos"


def nao_perguntar(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Não volta a perguntar o que o cliente JÁ respondeu.

    ⚠️ A régua é a DO PRODUTO (`attendance_ficha.slots_reperguntados`, o mesmo
    fiscal que o `agent_node` usa) — CLAUDE.md §9.4: o motor sobre o texto
    real, nunca um regex paralelo.
    """
    slots = [str(s) for s in (esperado or {}).get("nao_perguntar") or []]
    if not slots:
        return True, 1.0, "nada a não perguntar"
    texto = str((saida or {}).get("texto") or "") if isinstance(saida, dict) else _texto(saida)
    ficha = (esperado or {}).get("ficha") or {}
    try:
        from app.services.attendance_ficha import slots_reperguntados

        repetidos = slots_reperguntados(texto, ficha, corredor=str(ficha.get("servico") or ""))
    except Exception as exc:  # noqa: BLE001
        return False, 0.0, f"O fiscal da pergunta repetida não rodou ({type(exc).__name__})."
    achados = [s for s in repetidos if s in slots]
    if achados:
        return False, 0.0, f"Perguntou de novo o que o cliente já respondeu: {', '.join(achados)}."
    return True, 1.0, "não repetiu pergunta respondida"


def efeitos_exatos(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Cada efeito aconteceu EXATAMENTE o número de vezes pedido — e nenhum
    efeito duplicado. Acionamento em dobro é um segundo guincho na porta."""
    pedidos = (esperado or {}).get("efeitos_exatos")
    dup = int((saida or {}).get("duplicados") or 0) if isinstance(saida, dict) else 0
    if dup:
        return False, 0.0, f"Efeito DUPLICADO: {dup} execução(ões) a mais com a mesma chave."
    if not pedidos:
        return True, 1.0, "sem efeito exigido e sem duplicado"
    obtidos = (saida or {}).get("efeitos") or {}
    errados = [f"{t}: {obtidos.get(t, 0)} (esperado {n})" for t, n in pedidos.items()
               if int(obtidos.get(t, 0)) != int(n)]
    if errados:
        return False, 0.0, f"Efeitos fora do esperado — {'; '.join(errados)}."
    return True, 1.0, "efeitos exatos"


def sem_efeito_proibido(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    proibidos = [str(x) for x in (esperado or {}).get("efeitos_proibidos") or []]
    obtidos = (saida or {}).get("efeitos") or {} if isinstance(saida, dict) else {}
    achados = [t for t in proibidos if int(obtidos.get(t, 0)) > 0]
    if achados:
        return False, 0.0, f"Produziu efeito proibido neste caso: {', '.join(achados)}."
    return True, 1.0, "nenhum efeito proibido"


def sem_dado_de_outro_tenant(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """A resposta de uma corretora não carrega dado da OUTRA (CLAUDE.md §7)."""
    marcas = [str(x) for x in (esperado or {}).get("dados_do_outro_tenant") or [] if str(x).strip()]
    if not marcas:
        return True, 1.0, "caso sem segundo tenant"
    if isinstance(saida, dict):
        # texto E argumentos de tool: o CPF do B indo para a consulta do A também é vazamento
        texto = _norm_b(str(saida.get("texto") or "") + " " + json.dumps(
            saida.get("tool_calls_todas") or saida.get("tool_calls") or [], ensure_ascii=False))
    else:
        texto = _norm_b(saida)
    achados = [m for m in marcas if _norm_b(m) in texto]
    if achados:
        return False, 0.0, ("A resposta traz dado de OUTRA corretora. Vazamento entre "
                            "tenants não se desfaz.")
    return True, 1.0, "nenhum dado de outro tenant"


def turnos_no_orcamento(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    teto = (esperado or {}).get("orcamento_turnos")
    if not teto:
        return True, 1.0, "sem orçamento de turnos"
    n = int((saida or {}).get("turnos") or 0) if isinstance(saida, dict) else 0
    if n > int(teto):
        return False, 0.0, f"Gastou {n} voltas do modelo; o orçamento era {teto}."
    return True, 1.0, f"{n} de {teto} voltas"


def estado_final(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """O estado que o motor devolveu contém o esperado (subconjunto)."""
    pedidos = (esperado or {}).get("estado_final") or {}
    if not pedidos:
        return True, 1.0, "sem estado exigido"
    estado = (saida or {}).get("estado") or {} if isinstance(saida, dict) else {}
    errados = [k for k, v in pedidos.items() if not _valor_casa(estado.get(k), v)]
    if errados:
        amostra = "; ".join(f"{k}={estado.get(k)!r}" for k in errados[:4])
        return False, round(1 - len(errados) / len(pedidos), 4), f"Estado final fora do esperado: {amostra}."
    return True, 1.0, "estado final certo"


def estrutura_valida(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """O modelo prometeu JSON (lista/objeto) e o motor conseguiu LER."""
    formato = (esperado or {}).get("formato")
    if formato not in ("json_lista", "json_objeto"):
        return True, 1.0, "caso sem formato estruturado"
    dado = (saida or {}).get("estrutura") if isinstance(saida, dict) else None
    ok = isinstance(dado, list) if formato == "json_lista" else isinstance(dado, dict)
    if not ok:
        return False, 0.0, f"Esperava {formato} legível e veio {type(dado).__name__}."
    return True, 1.0, "estrutura legível"


def fatos_ouro(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Memória: cada fato-ouro presente, nenhum fato proibido (inventado/lixo)."""
    grupos = (esperado or {}).get("fatos_ouro")
    proibidos = [str(x) for x in (esperado or {}).get("fatos_proibidos") or []]
    teto = (esperado or {}).get("max_fatos")
    if grupos is None and not proibidos and teto is None:
        return True, 1.0, "caso sem fatos exigidos"
    fatos = (saida or {}).get("estrutura") if isinstance(saida, dict) else None
    if not isinstance(fatos, list):
        return False, 0.0, "A extração não devolveu uma lista de fatos."
    alvo = [_norm_b(f) for f in fatos]
    faltando = []
    for g in grupos or []:
        alternativas = g if isinstance(g, list) else [g]
        if not any(_norm_b(a) in f for f in alvo for a in alternativas):
            faltando.append(str(alternativas[0]))
    lixo = [p for p in proibidos if any(_norm_b(p) in f for f in alvo)]
    if lixo:
        return False, 0.0, f"Guardou o que não devia: {', '.join(lixo[:3])}."
    if teto is not None and len(fatos) > int(teto):
        return False, 0.0, f"Guardou {len(fatos)} fatos; o teto do caso é {teto}."
    if faltando:
        total = max(1, len(grupos or []))
        return False, round(1 - len(faltando) / total, 4), f"Faltou o fato: {', '.join(faltando[:3])}."
    return True, 1.0, "fatos certos"


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------
JUIZES: dict[str, Callable[..., tuple]] = {
    "sem_pii": sem_pii,
    "sem_segredo": sem_segredo,
    "contem": contem,
    "nao_contem": nao_contem,
    "com_fonte": com_fonte,
    "sem_numero_inventado": sem_numero_inventado,
    "json_valido": json_valido,
    # SPEC-116 U11 — bancada
    "tool_esperada": tool_esperada,
    "args_esperados": args_esperados,
    "nao_perguntar": nao_perguntar,
    "efeitos_exatos": efeitos_exatos,
    "sem_efeito_proibido": sem_efeito_proibido,
    "sem_dado_de_outro_tenant": sem_dado_de_outro_tenant,
    "turnos_no_orcamento": turnos_no_orcamento,
    "estado_final": estado_final,
    "estrutura_valida": estrutura_valida,
    "fatos_ouro": fatos_ouro,
}

# Os que valem para QUALQUER caso, sem ninguém precisar pedir. Vazamento de
# dado pessoal e de segredo não é assunto de um dataset específico — é assunto
# de todos, e depender de alguém lembrar de listar é como não ter.
SEMPRE = ("sem_pii", "sem_segredo")


def julgar(saida: Any, esperado: Optional[dict] = None,
           entrada: Any = None,
           juizes: Optional[list[str]] = None) -> list[dict]:
    """Roda os juízes pedidos + os obrigatórios. Um por linha de resultado."""
    esperado = esperado or {}
    pedidos = list(juizes or esperado.get("juizes") or [])
    # Deduplica preservando ordem: obrigatórios primeiro, para o motivo mais
    # grave aparecer no topo de quem lê.
    ordem: list[str] = []
    for slug in list(SEMPRE) + pedidos:
        if slug not in ordem and slug in JUIZES:
            ordem.append(slug)

    resultados: list[dict] = []
    for slug in ordem:
        try:
            passou, nota, motivo = JUIZES[slug](saida, esperado, entrada)
        except Exception as exc:  # noqa: BLE001
            # Juiz que explode não pode virar "passou". Um erro no avaliador é
            # ausência de veredito, e ausência de veredito é reprovação — senão
            # basta quebrar o juiz para o gate ficar verde.
            passou, nota, motivo = False, 0.0, (
                f"O avaliador '{slug}' falhou ({type(exc).__name__}); sem "
                "veredito, o caso não passa.")
        resultados.append({"evaluator_slug": slug, "passou": bool(passou),
                           "nota": float(nota), "motivo": motivo})
    return resultados
