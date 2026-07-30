"""SPEC-038 ATLAS — Templater (Bloco B).

Transforma a tela crua observada em TEMPLATE reutilizável: troca a PII do
cliente por placeholders ({CPF}/{PLACA}/{NOME}/{ENDERECO}/{PROTOCOLO}/{DATA}/
{NUM}), preservando a ESTRUTURA (a inteligência que é nossa e global). É o que
garante a política do conhecimento global: o mapa NUNCA guarda dado de cliente.

Reusa os helpers canônicos: node_hash/normalize_screen_text (ura_map_service),
parse_options/classify_screen (cartographer).
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# Ordem importa: específico → genérico.
_PII_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # `(?<!\d)` e `(?!\d)` no lugar de `\b`. A fronteira de palavra falha ao
    # lado de sublinhado, porque para o regex `_` é letra: num anexo chamado
    # `CTPS_12345678900.pdf` o CPF passava inteiro. Achado por um subagente
    # destilando o lote 002 da AutoFleet em 29/07/2026 — a mesma família do
    # defeito que separava `tokio_marine` de `tokio`.
    #
    # A âncora por dígito ainda é MAIS segura que `\b` para o vizinho de baixo:
    # onze dígitos no meio de um cartão de dezesseis não casam, então o CPF não
    # come um pedaço do cartão e deixa o resto exposto.
    # LINHA DIGITÁVEL DE BOLETO — 44 a 48 dígitos, com pontos e espaços. Vem
    # ANTES de tudo: os padrões de baixo mordem pedaços dela (o de cartão come
    # 16 dígitos, o de CPF come 11) e deixam o resto exposto, que é o pior dos
    # dois mundos. Como o PIX copia-e-cola, não é dado pessoal — é instrumento
    # de pagamento: quem tem a string paga, ou cobra. Lote 012, 29/07/2026.
    (re.compile(r"(?<!\d)(?:\d[\s.]{0,2}){40,}\d(?!\d)"), "{LINHA_DIGITAVEL}"),
    # O separador aceita ESPAÇO. "123 456 789 00" é como o segurado digita o
    # CPF no WhatsApp, e só a forma com ponto era reconhecida.
    (re.compile(r"(?<!\d)\d{3}[\s.]?\d{3}[\s.]?\d{3}[\s-]?\d{2}(?!\d)"), "{CPF}"),
    (re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)"), "{CNPJ}"),
    # NÚMERO DE CARTÃO — 13 a 19 dígitos, em grupos ou corridos.
    #
    # Descoberto em 29/07/2026 por um subagente destilando o lote 003: um
    # parceiro colou no WhatsApp o número completo do cartão, validade e nome
    # do titular de um segurado. O mascarador pegava CPF, CNPJ, placa, CEP,
    # telefone e data — cartão, não. O dado mais sensível que existe numa
    # conversa de corretora atravessava o portão inteiro.
    #
    # Vem depois de CPF e CNPJ para não roubar o rótulo deles (11 e 14 dígitos
    # continuam sendo {CPF} e {CNPJ}), e antes de telefone, que morderia um
    # pedaço do meio do cartão e deixaria o resto exposto.
    (re.compile(r"(?<!\d)\d{4}[\s.\-]?\d{4}[\s.\-]?\d{4}[\s.\-]?\d{1,7}(?!\d)"), "{CARTAO}"),
    # Validade de cartão: "12/28", "12/2028". A regra de data pede dd/mm/aaaa
    # e não pega isto. Sozinha a validade não vale nada; ao lado do número,
    # vale tudo — e é assim que ela aparece.
    (re.compile(r"(?i)\b(?:validade|venc(?:imento)?\.?)\s*:?\s*\d{2}\s*/\s*\d{2,4}\b"),
     "validade {VALIDADE}"),
    # Mercosul e antiga. `IGNORECASE` porque o segurado digita "abc1d23" no
    # WhatsApp tanto quanto "ABC1D23", e a placa em minúsculas passava direto.
    # O formato é específico o bastante para não morder prosa: três letras,
    # dígito, alfanumérico, dois dígitos, sem separador de palavra em volta.
    (re.compile(r"(?<![A-Za-z0-9])[A-Z]{3}[-\s]?\d[A-Z0-9]\d{2}(?![A-Za-z0-9])",
                re.IGNORECASE), "{PLACA}"),
    (re.compile(r"\b\d{5}-?\d{3}\b"), "{CEP}"),
    # O `\s?` depois do 9 — é como muita gente escreve: "(51) 9 9999-8888".
    # O padrão exigia o 9 colado no resto e deixava passar o formato mais comum
    # em teclado de celular. Achado no lote 041 em 30/07/2026.
    (re.compile(r"(?<!\d)(?:\+?55\s?)?\(?\d{2}\)?\s?9?\s?\d{4}[-\s]?\d{4}(?!\d)"), "{TELEFONE}"),
    (re.compile(r"\b\d{2}/\d{2}/\d{2,4}\b"), "{DATA}"),
    # O `(?=[\w-]*\d)` exige um DÍGITO no que vem depois da palavra.
    #
    # Sem ele, "protocolo aberto" virava "protocolo {PROTOCOLO}" — qualquer
    # palavra de 4+ letras era tratada como número de protocolo. E como
    # `_card_pii_clean` reprova todo texto que o templatize mudaria, uma carta
    # legítima como "o protocolo aberto na seguradora deve ser informado ao
    # segurado" era marcada como PII e nunca chegava ao RAG.
    #
    # É a mesma família do defeito do rótulo sem dois-pontos, encontrada no
    # mesmo dia (29/07/2026) por um subagente destilando o lote 002. Número de
    # protocolo e número de chassi SEMPRE têm dígito; prosa, não.
    (re.compile(r"\bprotocolo[:\s]*\#?\s*(?=[\w-]*\d)[\w\-]{4,}", re.IGNORECASE),
     "protocolo {PROTOCOLO}"),
    (re.compile(r"\bchassi[:\s]*(?=\w*\d)\w{6,}", re.IGNORECASE), "chassi {CHASSI}"),
    # SEGREDO DENTRO DE URL. A regra de rótulo exige o rótulo no começo da
    # linha; `...artigo?auth_token=abc123` esconde a credencial no meio de um
    # link que parece inofensivo. Achado no lote 011 da Resulta, 29/07/2026.
    # `chave_acesso` e `chNFe` entraram depois: o lote 031 trouxe URL de download
    # de nota fiscal com a chave na query string. Cada nome novo que eu
    # acrescentasse deixaria o próximo passar, então a lista fecha com um
    # coringa: qualquer parâmetro cujo NOME contenha "chave", "token", "key",
    # "senha" ou "secret".
    (re.compile(r"(?i)([?&][^=&\s]*(?:chave|chnfe|chcte|token|key|senha|password|pwd|secret)"
                r"[^=&\s]*=)[^\s&#]+"), r"\1{SEGREDO}"),
    # CAMINHO E QUERY DE URL — o domínio fica, o resto sai.
    #
    # Seis sessões dos lotes 036/037 trazem link curto com token no CAMINHO,
    # não na query: rastreio de prestador, regularização de parcela,
    # contratação. A regra de parâmetro não alcança, porque não há `?nome=`.
    #
    # Mascarar a URL inteira apagaria conhecimento real — "o acompanhamento da
    # Tokio é no autoatendimento.tokiomarine.com.br" é a carta que o agente
    # precisa. Então o DOMÍNIO fica e o caminho vai embora: sobra o que ensina,
    # sai o que identifica uma pessoa ou autoriza uma ação.
    (re.compile(r"(?i)\b((?:https?://)?[a-z0-9.-]+\.(?:com|com\.br|br|net|org|gov\.br|io)"
                r"(?::\d+)?)(/\S+)"), r"\1/{CAMINHO}"),
    # CARTÃO COM O MEIO JÁ MASCARADO, PONTAS EM CLARO.
    #
    # O lote 037 trouxe "1234 **** **** 5678": alguém mascarou o meio e as
    # pontas ficaram. A regra de cartão exige quatro grupos de dígitos e não
    # casa. Oito dígitos de um cartão mais a bandeira já bastam para muita
    # coisa — e a linha PARECE protegida, que é o pior estado possível.
    (re.compile(r"(?<!\d)\d{4}[\s.\-]*(?:[*xX]{2,}[\s.\-]*){1,4}\d{4}(?!\d)"), "{CARTAO}"),
    # PAYLOAD PIX copia-e-cola. Não é credencial, é instrumento de pagamento:
    # quem tem a string cobra em nome de quem a gerou. Começa sempre por 000201
    # (payload format indicator do BR Code) e vem numa tacada só.
    (re.compile(r"\b000201[0-9A-Za-z.\-*+/:]{25,}"), "{PIX_COPIA_E_COLA}"),
    # E-MAIL. Nenhuma carta de conhecimento precisa de um endereço específico —
    # o que ensina é "o condomínio envia por e-mail", não qual endereço. 43
    # apareceram nos lotes pendentes, incluindo corporativos com nome e
    # sobrenome no próprio endereço.
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"), "{EMAIL}"),
    # CAUDA DE PIX COPIA-E-COLA.
    #
    # A cabeça é mascarada por `{PIX_COPIA_E_COLA}` e a cauda sobrevive na mesma
    # linha: `***9999a999`, o CRC final do BR Code. Eu havia registrado isso como
    # risco baixo — "cauda sem cabeça não paga nada" — e mantenho o julgamento.
    # Mas agora tenho a FORMA exata (22 ocorrências), então o padrão é preciso e
    # não há motivo para deixar.
    (re.compile(r"\*{3}\d{3,4}[0-9A-Za-z]{2,6}"), "{PIX_FIM}"),
    # NÚMERO LONGO NO MEIO DA LINHA, DEPOIS DE UM RÓTULO QUE NÃO ESTÁ NA LISTA.
    #
    # A forma que a varredura mais achou (74 vezes): `palavra: 999999999`.
    # Protocolo, celular de nove dígitos sem DDD, número de aviso, matrícula.
    # Cada rótulo novo que eu acrescentasse à lista deixaria o próximo passar.
    #
    # Sete dígitos ou mais, no meio da linha, é IDENTIFICADOR — em seguro o que
    # ensina é percentual, prazo em dias e quilometragem, e nenhum desses passa
    # de quatro dígitos. Valor em reais já foi mascarado antes desta regra.
    #
    # O `(?<![\d{])` e o `(?![\d}])` impedem que a regra morda o interior de um
    # placeholder já colocado.
    (re.compile(r"(?<![\d{])\d{7,11}(?![\d}])"), "{NUMERO}"),
    # NÚMERO SOZINHO NUMA LINHA, SEM RÓTULO NENHUM.
    #
    # O lote 024 trouxe seis casos assim: login do portal Bradesco em grupos de
    # dígitos, celular de nove dígitos sem DDD (a regra de telefone exige o
    # DDD), código de acesso a plataforma de pagamento. Todos numa linha só,
    # sem palavra que os anuncie — então nenhuma regra de rótulo os alcança.
    #
    # É seguro tratar por posição: **carta de conhecimento nunca é só um
    # número**. Num transcript, linha que é apenas dígitos é dado de alguém.
    #
    # Mínimo de sete dígitos para que "197" (polícia), "200" (km de cobertura)
    # e "2026" (ano) continuem intactos — são conhecimento e aparecem sozinhos.
    (re.compile(r"(?m)^\s*\d[\d\s.\-]{5,15}\d\s*$"), "{NUMERO}"),
    # SEGREDO LONGE DO RÓTULO.
    #
    # A regra de rótulo exige o valor logo depois dele. Estes três formatos, do
    # lote 020, põem palavras no meio:
    #
    #     "A senha para abrir o PDF e os 5 primeiros digitos do seu cpf 91227"
    #     "senha do arquivo: 91227"
    #     "o codigo de seguranca do atendimento e 4471"
    #
    # Aqui a unidade é a LINHA: se ela fala de senha, código de acesso/segurança
    # ou token, toda sequência de QUATRO ou mais dígitos nela é segredo.
    #
    # Quatro e não três de propósito: "os 5 primeiros dígitos" sobrevive, e a
    # instrução continua legível — o que se perde é o número, que é o segredo.
    # E a regra só age na linha que já se declara sobre credencial, então
    # "o boleto vence em 10 dias" nunca é tocado.
    (re.compile(r"(?im)^(?=.*(?:senha|c[óo]digo de (?:seguran[çc]a|acesso)|token))"
                r"(.*?)(?<!\d)(\d{4,})(?!\d)"),
     lambda m: f"{m.group(1)}{{SEGREDO}}"),
    # VALOR EM REAIS. Franquia de um segurado, indenização de um sinistro,
    # prejuízo apurado — número que só vale para aquele caso.
    #
    # Mascarar isto é ganho puro, e a razão é simples: o que ENSINA em seguro é
    # percentual e prazo, não cifra. "A franquia é de 10% da cobertura" e
    # "reembolso de até 30% do prêmio" continuam intactos porque não usam `R$`.
    # Já "a franquia é de R$ 2.480,00" só serve para uma apólice.
    #
    # Achado pelos subagentes nos lotes 007 e 008 da Resulta, em três conversas.
    (re.compile(r"(?i)R\$\s*\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?"), "{VALOR_RS}"),
    # VALOR EM REAIS SEM O "R$".
    #
    # Os lotes 032 e 033 trouxeram franquia e prejuízo escritos só como
    # "2.480,00" e "1.250,50" — a regra anterior exigia o símbolo.
    #
    # Exige separador de milhar OU três dígitos antes da vírgula, para que
    # "1,50 metros" e "0,5%" não sejam tocados. Continua valendo que o que
    # ENSINA é percentual e prazo, não cifra.
    (re.compile(r"(?<![\d,.])(?:\d{1,3}(?:\.\d{3})+|\d{3,}),\d{2}(?![\d])"), "{VALOR_RS}"),
    # RÓTULO NO MEIO DA LINHA. `_LABELED_VALUE` está ancorado em `^`, porque
    # nasceu para ler TELA de comprovante, onde cada campo ocupa uma linha. Mas
    # gente escreve num parágrafo só: "segue os dados banco 341 agencia 1234
    # conta 56789". Um subagente destilando o lote 003 da AutoFleet achou o
    # bloco bancário inteiro de um beneficiário de reembolso escrito assim.
    #
    # Aqui a lista é CURTA e o valor precisa conter DÍGITO. É o que separa
    # "conta 98765-4" de "a conta corrente do segurado deve ser informada" —
    # prosa não tem número no meio. Sem essa exigência, a regra comeria a
    # metade das cartas de cobrança, que é o defeito que já consertamos hoje.
    # As ABREVIAÇÕES entram junto. Um subagente destilando o lote 006 da Resulta
    # achou o bloco bancário de um condomínio escrito "AG 1234 C/C 56789-0" —
    # a lista tinha "agência" e "conta" por extenso, e ninguém escreve por
    # extenso quando está com pressa. A exigência de DÍGITO no valor é o que
    # mantém isso seguro: "a CC do condomínio" não tem número e passa.
    # O valor aceita PONTUAÇÃO DE SENHA, e um conector curto antes dele.
    #
    # A classe era `[\w@.\-]`, que para em `!` e `$`. Resultado medido no lote
    # 010 da Resulta: a senha do banco da corretora saiu como
    # `senha do banco {VALOR}!2026` — metade mascarada. Meia senha é pior que
    # nenhuma: parece protegida e não está.
    #
    # O conector opcional (`é`, `e`, `=`) cobre "a senha é Xy9$Kl", que é como
    # gente escreve. A exigência de DÍGITO segue sendo o que protege o
    # conhecimento: "a senha do atendimento são os quatro últimos dígitos do
    # telefone" não tem número junto ao rótulo e continua passando inteira.
    (re.compile(r"(?i)\b(banco|ag[êe]ncia|ag|conta corrente|conta|c/c|cc|pix|senha|"
                r"login|usu[áa]rio|token|acesso|c[óo]digo)"
                # O SEPARADOR TAMBÉM É HÍFEN E BARRA VERTICAL.
                #
                # Descoberto em 30/07/2026 varrendo os lotes 020-029 pela FORMA
                # das linhas (letras viram `a`, dígitos viram `9`) — sem trazer
                # um único valor para o contexto. A forma que apareceu 18 vezes:
                #
                #     aaaaa - aa999999          "senha - <valor>"
                #     aaaaa - aaaaa9999!@
                #
                # É como se escreve uma lista de acessos de portal, e era o
                # formato que o subagente do lote 023 tinha reportado como
                # "o mascarador não trata senha". Tratava — só não com hífen.
                r"\s*(?:[:.=\-–|]|\b[ée]\b)?\s*(?=[\w@.\-/!#$%&*+=?]*\d)"
                r"[\w@.\-!#$%&*+=?]{3,}"), r"\1 {VALOR}"),
]

# Rótulos de campo que costumam preceder um VALOR de cliente numa linha
# "Rótulo: valor" (Placa: QJQ0A91 / Modelo: Gol / Nome: ...).
#
# A segunda metade da lista veio das telas de COMPROVANTE, medidas em
# 28/07/2026. "Assistência: 8923467" (Yelum) e "Agendamento: 28/01/2026, entre
# 10h00 e 12h00" (Porto) não eram mascarados, e cada protocolo diferente virava
# uma TELA diferente: 18 nós na Yelum e 10 na Porto para o que é uma tela só.
# Mascarado o valor, o mapa volta a ter o tamanho da URA de verdade.
_LABELED_VALUE = re.compile(
    r"(?im)^(\s*[\*\-•]*\s*\*?(?:nome|modelo|placa|ve[íi]culo|cor|endere[çc]o|"
    r"cliente|segurado|cpf|cnpj|telefone|celular|marca|ano|cidade|estado|bairro|rua|"
    r"n[úu]mero|complemento|refer[êe]ncia|logradouro|"
    r"assist[êe]ncia|agendamento|protocolo|boleto|parcelas?|senha|ordem|"
    # CREDENCIAL. Um subagente destilando o lote 009 em 29/07/2026 achou login
    # e senha da corretora no portal da Allianz em texto claro dentro de uma
    # conversa. `senha` já estava na lista; o que vem ao lado dela, não.
    # Credencial não é dado de um cliente — é a chave do cofre de todos eles.
    r"login|usu[áa]rio|e-?mail|acesso|token|c[óo]digo de acesso|"
    # DADO BANCÁRIO. Um subagente destilando o primeiro lote da AutoFleet em
    # 29/07/2026 achou nome, CPF e dados bancários completos do beneficiário de
    # um reembolso, em texto claro. Agência e conta não estavam em lista
    # nenhuma — e são o que basta para o dinheiro sair do lugar errado.
    r"banco|ag[êe]ncia|conta(?: corrente| poupan[çc]a)?|pix|chave pix|"
    r"favorecido|benefici[áa]rio|titular|"
    r"chamado|solicita[çc][ãa]o|atendimento|pedido|ap[óo]lice|sinistro|contrato|"
    r"data do (?:vencimento|pagamento(?: mensal)?)|"
    r"quantidade de parcelas(?: a pagar| restantes)?)\*?\s*:?\*?\s*)(.+)$"
)


def templatize(text: str) -> str:
    """Devolve a tela com a PII trocada por placeholders. Determinístico."""
    s = str(text or "")
    for rx, repl in _PII_PATTERNS:
        s = rx.sub(repl, s)
    # "Placa: QJQ0A91" → "Placa: {VALOR}" (o valor após o rótulo é dado do cliente)
    def _mask_labeled(m: re.Match) -> str:
        val = m.group(2).strip()
        # não mascara se o "valor" já é placeholder ou é curtíssimo/opção
        if val.startswith("{") or len(val) <= 1:
            return m.group(0)
        # SEM DOIS-PONTOS, o rótulo pode ser só a primeira palavra de uma frase.
        #
        # O `:` era opcional, e o `(.+)$` é guloso: "Boleto de seguro não pago
        # até a data limite leva ao cancelamento" virava "Boleto {VALOR}".
        # Como `_card_pii_clean` reprova todo texto que o templatize mudaria,
        # QUALQUER carta começando por boleto / sinistro / apólice / protocolo /
        # atendimento era marcada como PII e nunca chegava ao RAG. Medido em
        # 29/07/2026: 51 das 306 barradas — 17% — eram conhecimento legítimo
        # jogado fora, e nenhuma delas tinha dado de pessoa.
        #
        # Com dois-pontos é rótulo de formulário e o valor é do cliente. Sem
        # dois-pontos, só é valor se PARECER valor: começa com dígito
        # ("Assistência 8923467") ou é um código/nome em caixa alta
        # ("Placa QJQ0A91"). Prosa em minúscula é frase, não campo.
        if ":" not in m.group(1):
            primeira = val.split()[0]
            # Valor começa com letra ou dígito. "Cidade/CEP onde o reparo será
            # feito" é RÓTULO de campo de um playbook de conduta, e a regra
            # tratava "/CEP" como valor em caixa alta — reprovou o playbook de
            # vidros no gate de PII em 30/07/2026, por dado que não existe.
            if not primeira[0].isalnum():
                return m.group(0)
            parece_valor = primeira[0].isdigit() or (
                len(primeira) >= 2 and primeira.upper() == primeira
                and any(c.isalnum() for c in primeira))
            if not parece_valor:
                return m.group(0)
        return f"{m.group(1)}{{VALOR}}"
    s = _LABELED_VALUE.sub(_mask_labeled, s)
    return s


# Linhas que NÃO são escolha de menu (eco de dados do cliente): "Placa: {X}",
# "Modelo: Gol", "Telefone {X}" — viram ruído de opção. Filtradas.
_DATA_ECHO = re.compile(
    r"^(?:placa|modelo|ve[íi]culo|telefone|celular|nome|cor|marca|ano|cidade|"
    r"bairro|rua|endere[çc]o|cpf|cnpj|cliente|segurado|chassi|protocolo)\b[:\s]",
    re.IGNORECASE)


def _real_options(labels: List[str]) -> List[str]:
    """Descarta 'opções' que na verdade são linhas de dados (Placa:/Modelo:/...)
    ou que contêm placeholder de valor — não são cliques de menu."""
    out = []
    for lab in labels:
        if _DATA_ECHO.match(lab.strip()):
            continue
        if "{VALOR}" in lab or "{PLACA}" in lab or "{CPF}" in lab or "{TELEFONE}" in lab:
            continue
        out.append(lab)
    return out


def _options_do_interativo(interactive: Optional[Dict]) -> List[str]:
    """Os títulos exatos de uma lista/botão do WhatsApp.

    Esta é a fonte da verdade e estava sendo ignorada. O evento guarda a
    estrutura que o WhatsApp mandou:

        {"kind": "list", "options": [
            {"title": "Abertura de sinistro",
             "description": "Batida ou acidente com envolvimento de terceiros"},
            {"title": "Carro reserva",
             "description": "Solicitar, prorrogar ou dúvidas com as locações"}]}

    O Tecelão lia o TEXTO RENDERIZADO e adivinhava quais linhas eram opção —
    e no render a lista vira título e descrição em linhas alternadas, sem
    marca. Resultado medido em 28/07/2026: a Porto ficou com 859 "opções" em
    353 telas, quase o dobro do real, porque as descrições viraram opções.

    E opção que não existe nunca é percorrida: cada descrição contada virava
    uma lacuna permanente, afundando a cobertura de todas as seguradoras que
    usam lista.
    """
    if not isinstance(interactive, dict):
        return []
    titulos: List[str] = []
    for op in interactive.get("options") or []:
        if isinstance(op, dict):
            t = str(op.get("title") or "").strip()
        else:
            t = str(op or "").strip()
        if t:
            titulos.append(t)
    return titulos


def screen_node(text: str, interactive: Optional[Dict] = None) -> Dict:
    """Constrói o nó canônico da tela (template + hash + kind + opções).

    Quando a tela veio como lista ou botão do WhatsApp, as opções saem da
    ESTRUTURA (`interactive`), não do texto. Só quando não há estrutura — URA
    de texto puro, como a da Allianz — é que o texto é interpretado.
    """
    from app.services.cartographer import classify_screen, parse_options
    from app.services.ura_map_service import node_hash

    template = templatize(text)

    estruturadas = _options_do_interativo(interactive)
    if estruturadas:
        # Os títulos também passam pelo templatize: uma lista pode trazer o
        # nome do segurado num item ("Confirmar João da Silva"), e PII não
        # entra no Atlas nem como rótulo de opção.
        options = _real_options([templatize(t) for t in estruturadas])
    else:
        options = _real_options(parse_options(template))

    kind = classify_screen(template, options)
    # marca app nativo/humano quando reconhecível (mesma semântica do cartógrafo)
    up = template.upper()
    if "FORMULARIO NATIVO" in up:
        kind = "app_form"
    node = {
        "hash": node_hash(template),
        "text": template[:400],
        "kind": kind,
        "options": [{"label": o, "reply": o, "leads_to": None} for o in options],
    }
    if kind == "pergunta":
        hint = answer_hint(template)
        if hint:
            node["answer_hint"] = hint
    return node


# O que o AGENTE deve responder numa pergunta aberta (founder: "respostas com
# exemplos, o atendente já sabe o que precisa"). Determinístico, sem PII.
_ANSWER_HINTS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"cpf|cnpj", re.IGNORECASE), "{CPF}", "CPF/CNPJ do titular da apólice (só números)"),
    (re.compile(r"placa", re.IGNORECASE), "{PLACA}", "Placa do veículo (ex.: ABC1D23) — vem da InfoCap"),
    (re.compile(r"telefone|celular|n[úu]mero (?:de|para) contato", re.IGNORECASE), "{TELEFONE}", "Telefone do cliente com DDD"),
    (re.compile(r"\bcep\b", re.IGNORECASE), "{CEP}", "CEP do local (8 dígitos)"),
    (re.compile(r"complemento", re.IGNORECASE), "{COMPLEMENTO}", "Apto/bloco/casa — ou 'não tem'"),
    (re.compile(r"refer[êe]ncia", re.IGNORECASE), "{REFERENCIA}", "Ponto de referência próximo (mercado, posto...)"),
    (re.compile(r"endere[çc]o|localiza[çc][ãa]o|onde (?:o ve[íi]culo|o carro|voc[êe]) est[áa]", re.IGNORECASE),
     "{ENDERECO}", "Endereço completo: rua, número, bairro, cidade - UF"),
    (re.compile(r"nome", re.IGNORECASE), "{NOME}", "Nome completo de quem acompanha no local"),
    (re.compile(r"\bdata\b|\bdia\b", re.IGNORECASE), "{DATA}", "Data (dd/mm/aaaa)"),
    (re.compile(r"motivo|conte o que|descreva", re.IGNORECASE), "{DESCRICAO}", "Descrição curta do ocorrido"),
]


def answer_hint(question_text: str) -> Optional[Dict[str, str]]:
    """Para telas-pergunta (sem botões): o placeholder e a instrução do que o
    agente/atendente deve responder. None quando não reconhecido."""
    for rx, ph, instr in _ANSWER_HINTS:
        if rx.search(str(question_text or "")):
            return {"placeholder": ph, "instrucao": instr}
    return None


def infer_ramo_servico(labels: List[str], full_text: str) -> Tuple[str, str]:
    """Infere ramo/serviço PELA ROTA (labels), não pelo número (uma seguradora
    atende vários ramos no mesmo WhatsApp)."""
    blob = (" ".join(labels) + " " + str(full_text or "")).lower()
    servico = ""
    for key, terms in (
        ("guincho", ("guincho", "reboque", "remocao", "remoção")),
        ("chaveiro", ("chaveiro", "chave", "trancad")),
        ("bateria", ("bateria", "carga")),
        ("pane_seca", ("pane seca", "combustivel", "combustível")),
        ("pneu", ("pneu", "troca de pneu", "estepe")),
        ("vidros", ("vidro", "para-brisa", "parabrisa")),
        ("residencial", ("encanador", "eletricista", "chaveiro residencial", "residencia", "residência")),
    ):
        if any(t in blob for t in terms):
            servico = key
            break
    ramo = "residencial" if servico == "residencial" or "residenc" in blob else "auto"
    if any(t in blob for t in ("sinistro", "colisao", "colisão", "acidente")):
        servico = servico or "sinistro"
    return ramo, servico
