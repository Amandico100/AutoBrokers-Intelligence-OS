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

# ─────────────────────────────────────────────────────────────────────────────
# O QUE UMA REGRA DE NOME NUNCA PODE ATRAVESSAR: A QUEBRA DE LINHA
# ─────────────────────────────────────────────────────────────────────────────
# 06/08/2026. `\s` casa `\n`, e toda regra de nome deste arquivo separava o
# rótulo do nome com `\s+`. Resultado: o rótulo de UMA linha capturava a
# primeira palavra da linha SEGUINTE — que num menu de URA é sempre um rótulo
# de opção com inicial maiúscula.
#
# 📊 Medido nos 27 lotes de seguradora (319 sessões), com o templatize de então:
#
#     "Botão 2: Falar com atendente\nBotão 3: Encerrar"  →  "…\n{NOME} 3: Encerrar"
#     "Olá!\nBotão 1: Guincho"                           →  "Olá!\n{NOME} 1: Guincho"
#     "Bem-vindo\nVoltar ao menu"                        →  "Bem-vindo\n{NOME} ao menu"
#     "Prezado\nConfirmar agendamento"                   →  "Prezado\n{NOME} agendamento"
#
# 5 ocorrências reais no acervo (lote_018 nas conversas 6,7,8,9 e lote_011 l.7)
# contra 3.082 `Botão N` intactos — raro, e por isso perigoso: some sem rastro,
# porque `{NOME}` parece mascaramento legítimo. E o que some é justamente o
# rótulo do item de menu, que é a instrução de navegação que o corredor precisa.
#
# É a mesma família de `"Ola, quero abrir um sinistro" → "Ola, {NOME} um
# sinistro"`: uma regra de nome comendo palavra comum capitalizada. Lá o
# defeito era o `(?i)` valer para o padrão inteiro; aqui é o `\s` valer para o
# `\n`. A cura é a mesma — **estreitar o que a regra tem direito de ver**.
#
# `_H` é espaço HORIZONTAL: espaço, tab, NBSP. Nunca quebra de linha. Toda
# regra que ligue um rótulo ao nome que vem depois dele usa `_H`, não `\s`.
_H = r"[^\S\n]"

# O CONECTIVO DE SOBRENOME, NAS DUAS CAIXAS — `Maria de Fátima` e
# `SONIA DE LOURDES PRASS`. Escrever só `d[aeo]s?` dentro de um `(?-i:…)` fazia
# a repetição parar no primeiro conectivo em caixa alta, e o mascaramento saía
# pela metade: `{NOME} DE LOURDES PRASS`. Meio nome mascarado é pior que nenhum
# — a linha parece tratada e o sobrenome, que é o que individualiza a pessoa
# dentro da família, segue em claro.
_CONECTIVO = r"(?:d[aeo]s?|D[AEO]S?)" + _H + r"+"

# O QUE NUNCA É NOME DE PESSOA, ainda que tenha a forma de um.
#
# Vale como lookahead negativo antes de CADA palavra de um nome composto, não
# só antes da primeira: 📊 "Souza Aguiar CPF {CPF}" devolvia `{NOME} {CPF}` com
# a sigla do documento comida junto — o rótulo do campo desaparecia e a linha
# deixava de dizer o que aquele número era.
#
# A lista é curta de propósito. Ela cobre três famílias que o acervo mostrou:
# sigla de documento, rótulo de campo e opção de menu. Marca e modelo de
# veículo NÃO estão aqui porque não precisam estar — a regra que os pegava foi
# a que olhava para `{PLACA}`, e ela deixou de existir.
_NAO_E_NOME = (
    r"(?!(?:CPF|CNPJ|RG|CNH|CRLV|Placa|PLACA|Exemplo|EXEMPLO|Voltar|VOLTAR|"
    r"Sair|SAIR|Menu|MENU|Digite|DIGITE|Informe|INFORME|Segurado|SEGURADO|"
    r"Segurada|SEGURADA|Cliente|CLIENTE|Titular|TITULAR|Modelo|MODELO|"
    r"Marca|MARCA|Ano|ANO|Cor|COR|Endereco|Endereço|Telefone|TELEFONE)\b)")

# NOME NA SAUDAÇÃO — a regra mora aqui fora, com nome, porque ela tem DOIS
# leitores. O segundo é `mascarar.transcript_seguradora`, que precisa saber
# QUEM esta regra reconheceu como nome numa sessão para mascarar as outras
# aparições do mesmo token na mesma conversa (ver a docstring de lá).
#
# Ela ficava embutida na lista, sem nome, e o único jeito de alcançá-la de fora
# era `_PII_PATTERNS[0][0]` — um índice que a próxima regra inserida no topo
# quebraria em silêncio, e o silêncio aqui é PII passando.
#
# 📊 Medido no Atlas de produção: **28 nós** guardam um primeiro nome de pessoa
# assim — Tokio 15, Bradesco 5, Allianz 4, Porto 4. E na Tokio é a RAIZ do mapa,
# a tela por onde toda sessão começa.
#
# `_LABELED_VALUE` mascara nome DEPOIS de um rótulo (`Nome: Fulano`). A saudação
# de uma URA não tem rótulo nenhum: ela diz "Olá, Fulano!" e pronto. O Atlas é
# estrutura global: ele descreve o menu da seguradora, não o cliente. Um nome
# ali não ajuda ninguém e atravessa corretoras.
#
# A regra é ESTREITA de propósito: só depois de uma saudação, só uma ou duas
# palavras capitalizadas, e só até a pontuação. A lista de exclusão é a metade
# que faz a regra funcionar: depois de uma saudação vem, quase sempre, um VERBO
# capitalizado ("Olá! Digite o CPF"). Sem ela, `Digite` virava `{NOME}` e a tela
# perdia a instrução — que é justamente o conhecimento que este mascarador
# existe para preservar.
#
# O `(?-i:...)` no grupo do nome — 06/08/2026, e ele conserta perda de
# conhecimento que já estava acontecendo
# ---------------------------------------------------------------------------
# O `(?i)` do começo vale para o padrão INTEIRO, então `[A-ZÀ-Ú][a-zà-ú]{2,}`
# casava minúscula também: qualquer par de palavras depois de uma saudação
# virava nome, capitalizado ou não. 📊 Medido em 06/08/2026 contra o
# `templatize` de então:
#
#     templatize("Ola, quero abrir um sinistro")
#     → "Ola, {NOME} um sinistro"
#
# Duas palavras de conhecimento apagadas por uma regra de PII, na abertura da
# conversa, que é onde o segurado diz o que quer. `(?-i:...)` devolve a
# sensibilidade a maiúscula SÓ no grupo do nome: a saudação continua casando
# "olá"/"OLÁ"/"Olá", e o nome volta a precisar de inicial maiúscula — que é a
# única coisa que separa "Maria" de "quero".
#
# O separador é `_H` — 06/08/2026. Ver o bloco no topo do arquivo: com `\s+`,
# `"Olá!\nBotão 1: Guincho"` devolvia `"Olá!\n{NOME} 1: Guincho"`. A saudação
# de uma URA e o primeiro item do menu dela vivem em linhas diferentes, e a
# regra não tem o direito de ligar uma na outra.
#
# O separador NÃO aceita aspas. Eu acrescentei `"` numa primeira escrita, por
# causa de `Olá" Meu nome é ANDREZA` (a URA da Allianz erra a pontuação). 📊 A
# medição contra os 27 lotes reprovou na hora: 13 ocorrências viraram
# `Olá" {NOME} nome é {NOME}` — a palavra "Meu" comida, e a frase que ANUNCIA
# o nome destruída junto. O nome ali já é pego pela regra de apresentação, que
# lê "meu nome é". Uma regra a mais não protegia nada e apagava conhecimento.
NOME_NA_SAUDACAO = re.compile(
    r"(?i)\b(ol[áa]|oi|bem[- ]vindo[ao]?|prezad[oa])([,!]?" + _H + r"+)"
    r"(?!(?:digite|informe|escolha|selecione|envie|clique|aguarde|responda|"
    r"para|qual|como|quando|onde|quem|seja|bem|vamos|antes|agora|ainda|caso|"
    r"este|esta|esse|essa|isso|nossa|nosso|obrigad|tudo|aqui|sou|somos|"
    r"estamos|precisa|poderia|favor|por|deseja|voc[êe]|segue|falta|basta|"
    r"de|da|do|ao|à|a|o|senhor|senhora|novamente|cliente|segurad|"
    # 07/08/2026 — "Oi! Assistente virtual" virava "Oi! {NOME} virtual".
    # A URA se apresentando é a coisa MAIS comum depois de uma saudação, e
    # mascarar a apresentação apaga a identidade da tela, que é justamente o
    # conhecimento que o Atlas existe para guardar. Achado ao calibrar o
    # vocativo: o caso reprovou e o padrão culpado era este, não o novo.
    r"assistente|atendente|consultor|especialista|virtual|rob[oô]|bot)\b)"
    r"(?-i:([A-ZÀ-Ú][a-zà-ú]{2,}(?:" + _H + r"+[A-ZÀ-Ú][a-zà-ú]{2,})?))")

# NOME NO VOCATIVO, FORA DA SAUDAÇÃO — 07/08/2026.
#
# 📊 O que `NOME_NA_SAUDACAO` não alcança, medido nos 10 mapas de produção:
# **115 nós** com nome próprio solto, 95 deles só na Porto. O formato é este:
#
#     Oi, sou assistente virtual da Porto Seguro 👋
#
#     Fulano, estou aqui para ajudar você
#
# A saudação está na PRIMEIRA linha e o nome na TERCEIRA. `NOME_NA_SAUDACAO`
# exige que o nome venha colado na saudação, então ele passa direto.
#
# 📊 O que vem depois do nome, medido no acervo da Porto: "estou aqui" (44),
# "a vistoria" (20), "os reparos" (11), "você optou" (4). **Não há pronome
# consistente** — a tentativa de exigir "você/sua/seu" pegava só 7 dos 95.
#
# TRÊS TRAVAS, e cada uma existe por um falso positivo que eu produzi
# -------------------------------------------------------------------
# 1. **Não é palavra comum.** Sem a lista, `Digite, por favor`, `Guincho,
#    reboque`, `Pronto, sua solicitação` e `Florianópolis, SC` viravam `{NOME}`.
#    Apagar a instrução do menu é perder exatamente o conhecimento que este
#    mascarador existe para preservar.
# 2. **Não é a personagem da URA.** `Marina, assistente virtual da Tokio
#    Marine` e `Maitê, assistente virtual da MAPFRE` são o PERSONAGEM da
#    seguradora, não uma pessoa. Mascará-los quebraria a identidade da tela.
# 3. **É uma frase, não item de lista.** Exigir letra minúscula e ao menos três
#    palavras depois da vírgula separa `Fulano, estou aqui para ajudar` de
#    `Auto, Residencial ou Vida`.
_NAO_E_NOME_PROPRIO = (
    r"pronto|prontinho|certo|otimo|ótimo|perfeito|obrigad\w*|desculp\w*|"
    r"digite|informe|escolha|selecione|envie|clique|aguarde|responda|confirmad\w*|"
    r"atencao|atenção|ola|olá|oi|entao|então|bom|boa|sim|nao|não|ok|claro|"
    r"guincho|reboque|bateria|pneu|chaveiro|vidros|sinistro|assistencia|assistência|"
    r"auto|residencial|vida|empresarial|veiculo|veículo|apolice|apólice|taxi|táxi|"
    r"florian\w*|s[ãa]o|rio|belo|santa|santo|nova|novo|brasil|centro|"
    r"segur\w*|client\w*|corretor\w*|titular|condutor|prezad\w*|senhor\w*"
)
# Depois da vírgula: se vier isto, quem falou foi a URA se apresentando.
_APRESENTACAO_DA_URA = (
    r"assistente|sou|atendente|consultor|especialista|virtual|bot|"
    r"aqui esta|aqui está|tudo bem|como vai|obrigad"
)
# A QUARTA TRAVA, e é a que sustenta as outras três: **a URA tem de ter se
# apresentado antes**.
#
# 🔴 Sem ela, este mascarador come português. Um teste que já existia
# (`test_a_conversa_com_a_seguradora_nao_vaza_gente`) reprovou o conserto e
# mostrou três frases reais que eu estava destruindo:
#
#     "Roubo, furto e incêndio têm franquia própria"   → "Roubo" virava {NOME}
#     "Agora, me informe o CEP do local"               → "Agora" virava {NOME}
#     "Elogios, reclamações e informações de como…"    → "Elogios" virava {NOME}
#
# Nenhuma lista de palavras cobre o português inteiro. A trava certa não é
# lexical, é ESTRUTURAL: o nome do segurado só aparece depois que a URA se
# apresentou, porque é a apresentação que estabelece a quem ela fala.
#
# 📊 Medido nos 10 mapas: das 95 telas da Porto com nome solto, **84 (88%)**
# começam com saudação ou apresentação. E as três frases acima não têm nenhuma
# das duas — a trava separa exatamente onde precisa.
_URA_SE_APRESENTOU = (
    r"[^\n]*(?:\bol[áa]\b|\boi\b|bom dia|boa tarde|boa noite|prezad|"
    r"assistente|sou a |sou o |atendimento virtual|atendimento digital)"
    r"[^\n]*\n[\s]*"
)
NOME_NO_VOCATIVO = re.compile(
    r"(?im)\A((?:" + _URA_SE_APRESENTOU + r")+)"
    r"(?!(?:" + _NAO_E_NOME_PROPRIO + r")\b)"
    r"(?-i:[A-ZÀ-Ú][a-zà-ú]{2,15})"
    r"(,[ \t]+)"
    r"(?!(?:" + _APRESENTACAO_DA_URA + r")\b)"
    r"(?=[a-zà-ú]\S*[ ]\S+[ ]\S+)"
)

# ASSINATURA DE ATENDENTE — `Fulana - Autofleet Seguros`.
#
# 📊 24 nós em 3 mapas (hdi 10, yelum 8, tokio 6). A URA da Tokio Marine é
# white-label por corretora e ECOA a marca de volta — a raiz do mapa `tokio`
# literalmente estampa o nome de uma corretora.
#
# Promover esse mapa a "ativo" publicaria a marca de um cliente dentro do
# conhecimento que os outros consomem (CLAUDE.md §7). A estrutura da URA se
# preserva; a identidade some.
#
# O `\{NOME\}` na alternativa é necessário: em vários nós a saudação JÁ
# mascarou o nome, e sobrou `{NOME} - Autofleet Seguros`.
ASSINATURA_DE_CORRETORA = re.compile(
    r"(?:\{NOME\}|(?-i:[A-ZÀ-Ú][a-zà-ú]{2,15}))"
    r"[ \t]*-[ \t]*"
    r"(?-i:[A-ZÀ-Ú][A-Za-zà-ú]{2,15})[ \t]+Seguros\b"
)

# LOGRADOURO EM PROSA — 06/08/2026, achado no acervo das seguradoras.
#
# `_LABELED_VALUE` já mascara `Endereço: ...`, `Rua: ...`, `Bairro: ...`. O que
# ele não alcança é o endereço escrito no meio de uma frase, sem rótulo, que é
# como a URA da seguradora ECOA de volta o local do atendimento e como o humano
# o digita:
#
#     "R. Manoel Loureiro, 1653 - Barreiros, São José - SC, {CEP}"
#
# 📊 Medido em 06/08/2026 sobre as 319 sessões substanciais de
# `observed_sessions`: 266 ocorrências, 195 logradouros distintos, todos com
# número — endereço de residência ou de sinistro de segurado real.
#
# O DÍGITO é a regra inteira. Sem ele, "a rua é conhecida na região",
# "apartamento individual" e "o condomínio está vazando" viram endereço, e o
# mascarador passa a comer prosa — 📊 foi o que a medição mostrou: das 345
# ocorrências que a busca por vocabulário achava, 79 não tinham número e
# nenhuma delas era endereço. É o mesmo critério que já separa
# "protocolo aberto" de "protocolo 8923467" duas dezenas de linhas abaixo.
#
# O TIPO do logradouro fica. "A Porto pede rua e número do local" é
# conhecimento; qual rua é dado de uma pessoa.
#
# O `(?:d[aeo]s?\s+)?` é a metade que faltava na primeira escrita: "Rua das
# Flores, 123" começa com conectivo minúsculo, e exigir maiúscula logo depois
# do tipo deixava passar todo logradouro com "da/de/do/das/dos" no nome — que
# em português é metade deles.
#
# OS TIPOS QUE FALTAVAM — 06/08/2026, medidos nos 27 lotes de seguradora.
#
# A lista nasceu do acervo de atendimento, onde quem escreve o endereço é o
# humano da corretora. No acervo das SEGURADORAS quem escreve é a URA, que ecoa
# o que o Google Maps devolveu — e o Maps escreve `Estr.`, `Br-101`, `SC-281`,
# `Unnamed Road`. Nenhum deles estava aqui, e o endereço saía inteiro:
#
#     "O endereço é: *Estr. Geral Coqueiros, 1963 - Angelina - SC*"   lote_001
#     "SC-281, sertao do maruim, São José"                            lote_024
#     "Endereço de destino: OFICINA DVA - BR-101, 205"                lote_004
#
# A RODOVIA por sigla (`BR-101`, `SC-281`, `RS-118`) exige o número do KM ou do
# imóvel DEPOIS da sigla — senão "a cobertura vale na BR-101" viraria endereço,
# e a rodovia sozinha é conhecimento (diz por onde a assistência atende).
_LOGRADOURO = re.compile(
    r"(?i)\b(rua|r\.|av\.|avenida|alameda|al\.|travessa|rodovia|rod\.|estrada|"
    r"estr\.|pra[çc]a|servid[ãa]o|condom[íi]nio|edif[íi]cio|ed\.|residencial|"
    r"marginal|beco|largo|linha|loteamento|via|road|unnamed road)" + _H + r"+"
    r"(?:(?-i:d[aeo]s?)" + _H + r"+)?(?-i:[A-ZÀ-Ú0-9][^\n,;]{2,45}?)\s*,?\s*"
    r"(?:n?[ºo°]?\s*)?\d{1,6}(?:\s*[-/]\s*\d{1,6})?\b")

# RODOVIA COM NÚMERO DE IMÓVEL — `BR-101, 205` · `SC-281, 1500`.
# Separada do `_LOGRADOURO` porque a sigla não é uma PALAVRA de tipo: é a
# própria identidade da via, e o que a torna endereço é o número que vem depois
# da vírgula. Sem a vírgula-e-número, `BR-101` fica — é conhecimento de
# cobertura, não morada de ninguém.
_RODOVIA_COM_NUMERO = re.compile(
    r"(?i)\b((?:BR|SC|RS|PR|SP|MG|RJ|BA|GO|MT|MS|PE|CE|PA|ES|PB|RN|AL|SE|PI|"
    r"MA|TO|RO|AC|AP|RR|DF)\s?-\s?\d{2,3})\s*,\s*(?:n?[ºo°]?\s*)?\d{1,6}\b")

# PLUS CODE DO GOOGLE — `88V9+6XW`, `W9JJ+R3G`. É coordenada: resolve para um
# ponto de ~14 m. 📊 3 ocorrências no acervo (lote_013 l.5 e l.6, lote_022 l.8),
# todas de zona rural, onde é a ÚNICA forma de endereço que existe — e por isso
# a mais reveladora das três.
#
# O alfabeto é fechado (o Open Location Code descarta vogais e caracteres
# ambíguos: só `23456789CFGHJMPQRVWX`), o que faz o padrão não morder sigla nem
# fórmula: "C++", "A+B" e "2+2" não têm os quatro caracteres exigidos antes do
# `+`.
_PLUS_CODE = re.compile(
    r"\b[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}\b")

# ENDEREÇO ANUNCIADO EM FRASE — 06/08/2026, e é o buraco mais sistemático dos
# endereços: 📊 22 ocorrências nos 27 lotes.
#
# `_LABELED_VALUE` está ancorado em `^` e a lista dele é de RÓTULOS de campo. A
# URA não escreve um campo — escreve uma frase, e o valor às vezes cai na linha
# seguinte, entre asteriscos:
#
#     "O endereço é: \n\n*Estr. Geral Coqueiros, 1963 - Angelina - SC*."
#     "*1 - Endereço da apólice:* R #### ## JUNHO;233"
#     "Endereço de destino: OFICINA DVA - BR-101, 205"
#
# O "O " antes de "endereço" é o que tira a linha do alcance do `^`, e a quebra
# de linha é o que tira o valor do alcance de qualquer regra de uma linha só.
#
# O DÍGITO continua sendo a regra inteira, pelo mesmo motivo de sempre:
# "Endereço de Origem e destino (rua/av., número, bairro, cidade e estado;" é a
# INSTRUÇÃO do formulário da seguradora — conhecimento puro — e não tem número.
# Já "…: Rua X, 1963" tem, e só serve para uma pessoa.
_ENDERECO_ANUNCIADO = re.compile(
    r"(?im)^(.{0,30}?\bendere[çc]o|.{0,30}?\blocaliza[çc][ãa]o|"
    r".{0,20}?\bponto de refer[êe]ncia)"
    r"([^\n:]{0,25}:" + _H + r"*\*?)"
    r"(\n{0,2}" + _H + r"*\*?)"
    r"(?![\s*]*(?:\{|$))"
    r"((?=[^\n]*\d)[^\n]{4,90})")

# COMPLEMENTO DE ENDEREÇO — bloco, apartamento, torre, quadra, lote, sala.
#
# 📊 217 ocorrências nos 27 lotes (`apto 1104`, `Bloco 2`, `APTO 302`,
# `bloco 15 ap 203`, `ap 1301`). O logradouro já era mascarado e o complemento
# ficava na mesma linha, em claro — que é o pior dos dois estados: metade do
# endereço protegida, metade não, e a linha PARECE tratada.
#
# A palavra FICA e o número sai, pelo mesmo motivo pelo qual o tipo do
# logradouro fica: "a Porto pede bloco e apartamento" é conhecimento sobre o
# formulário da seguradora; QUAL apartamento é a casa de uma pessoa.
#
# O DÍGITO é a regra inteira, de novo: "o apartamento estava vazio" e "o bloco
# de coberturas" não têm número e passam inteiros. `\b` antes de `ap` impede
# que a regra veja "cap 3" ou "recap 2".
#
# E A LINHA DE EXEMPLO DA URA FICA INTEIRA — 06/08/2026, achado pelo controle.
# A primeira escrita desta regra comia 109 ocorrências de instrução:
#
#     "( Ex: Bloco 2, apartamento 24, Casa 11, em frente ao shopping )"   81x
#     "_(Ex: em frente ao shopping, Casa 11)_"                            28x
#
# É a Porto ensinando o formato do complemento. O número ali não é a casa de
# ninguém — é o exemplo. Mascarar não vaza nada e não protege nada; só apaga a
# instrução que o corredor precisa para preencher o campo.
#
# Quem decide é a LINHA, não o casamento: se a linha se declara exemplo, o
# complemento dela é ilustração. `_e_exemplo` é o mesmo julgamento que
# `_mask_labeled` já faz com "sem dois-pontos é frase, não campo" — olhar um
# palmo além do que casou antes de apagar.
_COMPLEMENTO = re.compile(
    r"(?i)\b(bloco|bl\.?|apto\.?|apartamento|ap\.?|torre|quadra|lote|"
    r"sala|conj\.?|conjunto|casa)(" + _H + r"*:?" + _H + r"*)"
    r"(?:n?[ºo°]" + _H + r"*)?\d{1,5}\b")

_LINHA_DE_EXEMPLO = re.compile(r"(?i)\b(?:ex|exemplo|modelo de|formato)\b\s*:?")


def _e_exemplo(m: re.Match) -> bool:
    """A linha em que este casamento caiu se declara exemplo?"""
    texto = m.string
    ini = texto.rfind("\n", 0, m.start()) + 1
    fim = texto.find("\n", m.end())
    return bool(_LINHA_DE_EXEMPLO.search(texto[ini:fim if fim >= 0 else len(texto)]))


def _mascara_complemento(m: re.Match) -> str:
    if _e_exemplo(m):
        return m.group(0)
    return f"{m.group(1)}{m.group(2)}{{NUM}}"

# Ordem importa: específico → genérico.
_PII_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # NOME NA SAUDAÇÃO — SPEC-065, 04/08/2026. A regra está definida acima,
    # com nome, porque `mascarar.transcript_seguradora` também a lê. O porquê
    # de cada pedaço dela está lá em cima, junto do padrão.
    (NOME_NA_SAUDACAO, r"\1\2{NOME}"),
    # ASSINATURA antes do VOCATIVO: `Fulana - Autofleet Seguros` tem de virar
    # `{NOME} - {CORRETORA}` inteira. Se o vocativo passasse primeiro, sobraria
    # a marca da corretora solta, que é justamente o que não pode ficar.
    (ASSINATURA_DE_CORRETORA, "{NOME} - {CORRETORA}"),
    # NOME NO VOCATIVO, fora da saudação — a regra está definida acima, com as
    # três travas e o porquê de cada uma.
    (NOME_NO_VOCATIVO, r"\1{NOME}\2"),
    # NOME DEPOIS DE TRATAMENTO — 06/08/2026. "Sr. Gustavo", "Sra. Magda",
    # "Dr. Mário". É a forma que sobra depois que a saudação e o vocativo são
    # tratados: 📊 4 ocorrências nas 319 sessões de seguradora, e é a mais
    # inequívoca de todas — ninguém escreve "Sr." antes de uma opção de menu.
    #
    # A exclusão é curta porque o tratamento também precede PAPEL, não só
    # nome: "Sr. Corretor", "Sra. Segurada". Errar aqui custa um papel virando
    # `{NOME}`, o que não apaga conhecimento nenhum — o papel já está dito na
    # frase inteira.
    (re.compile(r"(?i)\b(sr|sra|srta|dr|dra|dona|senhor|senhora)(\.?" + _H + r"+)"
                r"(?!(?:corretor|corretora|segurad|cliente|gerente|perito|"
                r"doutor|doutora|advogad|analista|atendente|titular)\b)"
                r"(?-i:[A-ZÀ-Ú][a-zà-ú]{2,}(?:" + _H + r"+[A-ZÀ-Ú][a-zà-ú]{2,})?)"),
     r"\1\2{NOME}"),
    # NOME DEPOIS DE APRESENTAÇÃO OU DE PERGUNTA POR NOME — 06/08/2026.
    #
    # Três formas achadas no acervo das seguradoras, e as três põem um nome
    # próprio a uma palavra de distância de um rótulo que o anuncia:
    #
    #     "Meu nome é THAIS, darei continuidade em seu atendimento"   (a URA)
    #     "me chamo Saionara"                                          (nós)
    #     "*Quem estará no local:* Julia"                              (resumo)
    #
    # `_LABELED_VALUE` não alcança nenhuma: a primeira e a segunda não têm
    # dois-pontos, e "quem estará no local" não é um rótulo da lista dele — nem
    # deveria ser, porque a lista é de campos de formulário e este é uma frase.
    #
    # Aceita CAIXA ALTA no nome ("THAIS"), que as outras regras de nome não
    # aceitam de propósito: aqui o rótulo já garantiu que o que vem é nome, e
    # atendente de central escreve o próprio nome em maiúscula o tempo todo.
    #
    # O NOME INTEIRO, e não só duas palavras — 06/08/2026, e é o buraco que
    # mais enganava porque a linha PARECIA resolvida:
    #
    #     "Olá, meu nome é {NOME} SALES e irei realizar seu atendimento."
    #     "meu nome é {NOME} MOURA TERRA"   ·   "{NOME} DIAS DOS SANTOS"
    #
    # 📊 6 ocorrências nos 27 lotes (lote_015 l.6, lote_025 l.2/8/10,
    # lote_026 l.1). O quantificador era `(?:…)?` — uma repetição, no máximo —
    # e nome brasileiro tem três a cinco palavras. O `{NOME}` colocado no lugar
    # do primeiro nome dava a impressão de proteção, e o sobrenome — que é o
    # que individualiza uma pessoa dentro de uma família — seguia em claro.
    #
    # O conectivo minúsculo (`de`, `da`, `dos`) entra na repetição pelo mesmo
    # motivo que entrou no logradouro: sem ele, "DIAS DOS SANTOS" parava em
    # "DIAS" e deixava "DOS SANTOS" para trás.
    #
    # O limite de 5 e o `_H` são o freio. Um nome não atravessa a quebra de
    # linha, e a frase que segue o nome quase sempre começa por minúscula
    # ("e irei realizar") — que é o que faz a repetição parar sozinha.
    #
    # A PERGUNTA DE IDENTIDADE DA PORTO entrou na mesma lista: `falando com`.
    # 📊 33 ocorrências, 8 sessões, sempre a primeira fala da URA:
    #
    #     "Eu estou falando com Nair?"          →  nome do segurado
    #     "Eu estou falando com Segurado(a)?"   →  a MESMA tela, sem nome
    #
    # O segundo é o controle que a própria Porto escreve: quando ela não sabe
    # o nome, imprime o papel. `segurad` já está na exclusão, e é ele que faz a
    # tela genérica sobreviver enquanto a personalizada é mascarada.
    (re.compile(r"(?i)\b(meu nome (?:é|e)|me chamo|nome de quem|"
                r"quem (?:estar[áa]|est[áa]|vai estar|ir[áa] estar)[^:\n]{0,30}|"
                r"nome do respons[áa]vel|falo com|falando com|atendente)"
                r"(" + _H + r"*:?\*?" + _H + r"+)"
                # `segurad` e `corretor` SEM `\b` no fim — 06/08/2026, e é o
                # controle que a própria Porto escreve. Quando ela não sabe o
                # nome, imprime `"Eu estou falando com Segurado(a)?"`. Com
                # `segurad\b` a exclusão falhava (depois de "segurad" vem "o",
                # não uma fronteira) e a tela genérica virava
                # `"falando com {NOME}(a)?"` — 📊 6 ocorrências. Mascarar um
                # papel apaga a tela que a URA usa para TODO mundo, que é
                # justamente a que mais ensina.
                r"(?!(?:segurad|corretor|cliente|titular|respons[áa]vel|"
                r"analista|atendente|condutor|motorista)\w*\b)"
                r"(?!(?:o|a|um|uma|voc[êe]|senhor|senhora|meu|minha|nome)\b)"
                r"(?-i:[A-ZÀ-Ú][A-Za-zà-ú]{2,}"
                r"(?:" + _H + r"+(?:" + _CONECTIVO + r")?"
                + _NAO_E_NOME + r"[A-ZÀ-Ú][A-Za-zà-ú]{2,}){0,4})"),
     r"\1\2{NOME}"),
    # PAPEL DE PESSOA + NOME PRÓPRIO — 06/08/2026.
    #
    # A URA e a corretora nomeiam quem está no local, e o rótulo não é campo de
    # formulário nenhum — é o papel dito no meio da frase:
    #
    #     "Motorista Allan Souza Silveira"                       lote_019 l.6
    #     "Condutor : ANDREZZA HAUTSCH OIKAWA ROCHA"             lote_015 l.12
    #     "conduzido por Rafaela Lídia Santo Iwamoto"            lote_027 l.4
    #     "recebido pelo Fábio porteiro"                          lote_025 l.8
    #
    # DUAS palavras no mínimo. Um papel seguido de UMA palavra capitalizada é
    # quase sempre operação, não gente — e é o que separa a regra de comer a
    # nota de andamento que a seguradora escreve em caixa alta:
    #
    #     "SEGURADO VAI COMPRAR MATERIAL"   lote_007 l.3   ← precisa sobreviver
    #     "SEGURADA, FICOU DE RETORNAR"     lote_005 l.10  ← precisa sobreviver
    #
    # A vírgula depois do papel também exclui: "SEGURADA, ..." é o sujeito de
    # uma frase, não a etiqueta de um nome. `seg`/`segurado` sem dois-pontos
    # ficam DE FORA por isso — o custo está registrado no relatório.
    (re.compile(r"(?i)\b(motorista|condutor|conduzid[oa] por|porteir[oa]|"
                r"propriet[áa]ri[oa]|preposto|s[óo]cio|"
                r"segurad[oa]|titular|respons[áa]vel|benefici[áa]ri[oa])"
                r"(" + _H + r"*:" + _H + r"*|" + _H + r"+)"
                r"(?!(?:d[aeo]s?|que|n[ãa]o|vai|foi|est[áa]|ir[áa]|ficou|"
                r"informou|precisa|pediu|solicitou|confirmou|autoriz|aguarda|"
                r"ser[áa]|tem|deve|pode|principal|do|da)\b)"
                r"(?-i:[A-ZÀ-Ú][A-Za-zà-ú]{2,}"
                r"(?:" + _H + r"+(?:" + _CONECTIVO + r")?"
                + _NAO_E_NOME + r"[A-ZÀ-Ú][A-Za-zà-ú]{2,}){1,4})"),
     r"\1\2{NOME}"),
    # LOGRADOURO EM PROSA — 06/08/2026. Definida acima, junto da medição.
    # Vem cedo: os padrões numéricos abaixo mordem o número da casa e deixam o
    # nome da rua exposto, que é o pior dos dois estados.
    #
    # As três de endereço vêm juntas e ANTES de tudo que é numérico, pelo mesmo
    # motivo: qualquer regra de dígito morde o número da casa e deixa o nome da
    # rua exposto.
    (_ENDERECO_ANUNCIADO, r"\1\2\3{ENDERECO}"),
    (_LOGRADOURO, r"\1 {ENDERECO}"),
    (_RODOVIA_COM_NUMERO, r"\1, {ENDERECO}"),
    (_PLUS_CODE, "{ENDERECO}"),
    (_COMPLEMENTO, _mascara_complemento),
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
    # TELEFONE ANUNCIADO PELA PRÓPRIA TELA — vem ANTES do CPF, e a ordem é o
    # conserto inteiro. SPEC-065, 04/08/2026.
    #
    # 📊 Medido no Atlas de produção: **46 nós em 6 seguradoras** escrevem
    # `"O número de telefone {CPF} está correto?"`. Um celular brasileiro com
    # DDD tem 11 dígitos — os mesmos 11 do CPF — e o padrão de CPF vem primeiro,
    # então mordia o telefone e o de telefone nunca era testado.
    #
    # CLAUDE.md §12.1: quando o nome do campo mente sobre o que ele guarda,
    # **conserte o campo**. O texto errado é o sintoma; o rótulo errado é a
    # causa, e ela reinfecta todo leitor seguinte — inclusive a carta que
    # alguém vai escrever a partir dessa tela.
    #
    # A desambiguação NÃO é por forma do número (CPF e celular têm 11 dígitos e
    # nenhuma regra de dígito separa os dois sem erro). É pelo CONTEXTO: se a
    # própria frase diz "telefone", "celular", "WhatsApp" ou "contato", o número
    # ao lado é telefone. A tela já disse o que é; basta escutá-la.
    #
    # Proteção não muda: os dois caminhos mascaram. O que muda é o rótulo dizer
    # a verdade.
    (re.compile(r"(?i)(telefone|celular|whats\s?app|whatsapp|n[úu]mero de contato|fone)"
                r"([^\d\n]{0,20})"
                r"(?<!\d)(?:\+?55\s?)?\(?\d{2}\)?\s?9?[\s.-]?\d{4}[\s.-]?\d{3,4}(?!\d)"),
     r"\1\2{TELEFONE}"),
    # CNPJ COM O AGRUPAMENTO ERRADO — 06/08/2026, lote_026 l.11.
    #
    #     "056.087.72/0001-77"      ← foi isto que o humano digitou
    #      05.608.772/0001-77       ← é isto que a máscara sabia reconhecer
    #
    # Os catorze dígitos são os mesmos; os pontos é que estão no lugar errado.
    # A regra de baixo valida a FORMA do agrupamento, e a URA da Yelum respondeu
    # "Sua resposta não corresponde a nenhuma opção" — ou seja, o documento nem
    # sequer funcionou, e mesmo assim atravessou o portão inteiro em claro.
    #
    # A assinatura que NÃO depende do agrupamento é o rabo: barra, quatro
    # dígitos de filial, hífen e dois de verificador. Isso não existe em
    # protocolo, em data nem em valor — `01/2026` tem quatro dígitos mas não tem
    # o `-99` no fim, e `R$ 1.000,00` não tem barra.
    #
    # 📊 1 ocorrência no acervo. Uma só, e mesmo assim vale a regra: é o número
    # de inscrição de um condomínio segurado, e a próxima exportação traz
    # outros — a digitação errada não é rara, o que era raro é alguém medir.
    (re.compile(r"(?<![\d./\-])\d[\d.\s\-]{8,14}/" + _H + r"?\d{4}" + _H +
                r"?-?" + _H + r"?\d{2}(?![\d\-])"), "{CNPJ}"),
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
    #
    # O DDD COM ZERO NA FRENTE — 06/08/2026, lote_019 l.11:
    #
    #     "*Nome e telefone do motorista que está no local:* *Charles*
    #      *048-99147-8922*"
    #
    # Duas coisas ao mesmo tempo. O `(?<!\d)` existe para impedir que a regra
    # morda o meio de um número maior — e ele funcionava contra o próprio
    # telefone: o motor tentava casar a partir do `48`, via o `0` à esquerda e
    # desistia. O DDD com zero é como se disca de telefone fixo e como muita
    # gente ainda escreve.
    #
    # E o rótulo estava longe demais para a regra de cima: "telefone" e o número
    # estão separados por 44 caracteres ("do motorista que está no local:*
    # *Charles* *"), e ela só olha 20. Aqui a forma resolve sozinha.
    #
    # O `0?` fica DENTRO do lookbehind negativo, não fora: `(?<!\d)0?\(?\d{2}` —
    # o zero é parte do DDD, e é ele que precisa estar na fronteira.
    #
    # E o separador depois do DDD passou a aceitar HÍFEN. Era `\s?`, e a forma
    # do lote é `048-99147-8922`: com o hífen entre DDD e número, o motor parava
    # ali. Quem escreve o DDD com zero costuma escrever com hífen — as duas
    # metades do mesmo defeito, e consertar só uma não muda o resultado.
    #
    # O primeiro bloco aceita 4 OU 5 dígitos (`99147-8922`): celular tem nove
    # dígitos e a divisão `5-4` é a que o teclado do celular sugere.
    (re.compile(r"(?<!\d)(?:\+?55[-\s.]?)?0?\(?\d{2}\)?[-\s.]?9?[-\s.]?"
                r"\d{4,5}[-\s.]?\d{4}(?!\d)"),
     "{TELEFONE}"),
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
    #
    # O TETO SUBIU DE 11 PARA 12 — 06/08/2026, achado ao testar o disparo ativo
    # da Porto: `"a vistoria do seu veículo para o sinistro 531202690931"`.
    # Doze dígitos corridos não casavam em regra nenhuma: `{NUMERO}` parava em
    # 11 e `{CARTAO}` só começa em 13. Um vão de exatamente uma casa decimal,
    # e o número de sinistro da Porto mora dentro dele.
    #
    # Treze continua sendo cartão: o menor cartão emitido tem 13 dígitos, e
    # roubar essa faixa faria o número de cartão sair rotulado como número
    # qualquer — proteção igual, rótulo mentiroso.
    (re.compile(r"(?<![\d{])\d{7,12}(?![\d}])"), "{NUMERO}"),
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
    # NOME COLADO A UM DOCUMENTO — 06/08/2026, e é a última regra da lista de
    # propósito: ela lê os PLACEHOLDERS que as regras de cima acabaram de pôr.
    #
    # A corretora despacha a ficha do caso numa linha só, e o nome vai junto do
    # documento porque é assim que a seguradora pede:
    #
    #     "{CPF} - ALTAMIRO OSMAR KOERICH {PLACA}"           lote_024 l.3
    #     "JESSICA LUANA GRIGGIO - {CPF}"                     lote_009 l.8
    #     "Paula walter Tavares Ferreira {CPF}"               lote_026 l.1
    #     "{CPF}  SEG SONIA DE LOURDES PRASS"                 lote_020 l.4
    #
    # Aqui não é preciso decidir se aquilo é gente ou razão social: **o que está
    # colado a um CPF é o titular daquele CPF**, e a razão social do condomínio
    # segurado merece a mesma máscara que o nome do segurado. Quem NÃO merece é
    # a seguradora — e ela nunca aparece encostada num documento de cliente.
    #
    # SÓ `{CPF}` E `{CNPJ}` — a placa ficou de fora, e essa foi a medição mais
    # útil desta regra. 📊 Nos 27 lotes, o que encosta em cada documento é
    # sistematicamente diferente:
    #
    #     junto de {CPF}/{CNPJ}   ALTAMIRO OSMAR KOERICH · JESSICA LUANA
    #                             GRIGGIO · SONIA DE LOURDES PRASS   → gente
    #     junto de {PLACA}        BYD SONG PLUS · MITSUBISHI OUTLANDER ·
    #                             DOLPHIN · Voltar RAM               → carro
    #
    # Incluir a placa custava quatro falsos positivos e não ganhava um nome
    # sequer que o CPF já não pegasse. O documento identifica a PESSOA; a placa
    # identifica o VEÍCULO, e ao lado dela vem marca e modelo.
    #
    # A exclusão cobre o que a URA escreve com a mesma forma e precisa
    # sobreviver — "Exemplo de CPF: {CPF}" (ensinando o formato) — e as siglas
    # de documento, que senão entram no meio do nome: "Souza Aguiar CPF {CPF}"
    # devolvia `{NOME} {CPF}` com o "CPF" comido junto.
    #
    # O `:` como separador está fora: rótulo com dois-pontos é campo, e campo é
    # assunto do `_LABELED_VALUE`. Duas palavras no mínimo, pelo mesmo motivo da
    # regra de papel.
    (re.compile(r"(?-i:(\{(?:CPF|CNPJ)\}" + _H + r"*[\-–,]?" + _H + r"*)"
                r"((?:" + _NAO_E_NOME + r"[A-ZÀ-Ú][A-Za-zà-ú]{2,})"
                r"(?:" + _H + r"+(?:" + _CONECTIVO + r")?"
                + _NAO_E_NOME + r"[A-ZÀ-Ú][A-Za-zà-ú]{2,}){1,5})"
                r"(?![A-Za-zÀ-ÿ]))"),
     r"\1{NOME}"),
    (re.compile(r"(?-i:((?<![A-Za-zÀ-ÿ])(?:" + _NAO_E_NOME + r"[A-ZÀ-Ú][A-Za-zà-ú]{2,})"
                r"(?:" + _H + r"+(?:" + _CONECTIVO + r")?"
                + _NAO_E_NOME + r"[A-ZÀ-Ú][A-Za-zà-ú]{2,}){1,5})"
                r"(" + _H + r"*[\-–,]?" + _H + r"*\{(?:CPF|CNPJ)\}))"),
     r"{NOME}\2"),
]

# Rótulos de campo que costumam preceder um VALOR de cliente numa linha
# "Rótulo: valor" (Placa: QJQ0A91 / Modelo: Gol / Nome: ...).
#
# A segunda metade da lista veio das telas de COMPROVANTE, medidas em
# 28/07/2026. "Assistência: 8923467" (Yelum) e "Agendamento: 28/01/2026, entre
# 10h00 e 12h00" (Porto) não eram mascarados, e cada protocolo diferente virava
# uma TELA diferente: 18 nós na Yelum e 10 na Porto para o que é uma tela só.
# Mascarado o valor, o mapa volta a ter o tamanho da URA de verdade.
#
# O QUALIFICADOR ENTRE O RÓTULO E OS DOIS-PONTOS — 06/08/2026, e é o buraco
# mais sistemático que este acervo tinha: 📊 71 ocorrências em 27 lotes, o
# bloco de confirmação cadastral que a Allianz manda em toda apólice.
#
#     "Nome do titular da apólice: MARIELLA VALERIO MEIRA"
#     "Nome do titular da apólice: CONDOMINIO EDIFICIO EUGENIO MULLER"
#
# `nome` SEMPRE esteve nesta lista. O que não estava previsto é que a
# seguradora escreve mais quatro palavras antes dos dois-pontos — e aí o grupo
# do rótulo terminava em "Nome ", o valor virava "do titular da apólice:
# MARIELLA…", e a heurística do "sem dois-pontos" (que existe para não comer
# frase) via um "do" minúsculo, concluía que aquilo era prosa e devolvia a
# linha inteira intacta. Duas defesas certas somando um vazamento.
#
# 📊 A prova de que a linha vizinha funcionava: no MESMO bloco,
# "Endereço: {VALOR}" e "Titular: {VALOR}" saíam mascarados. Só o campo com
# qualificador escapava — o que torna a linha ainda mais enganosa, porque o
# bloco PARECE tratado.
#
# O qualificador é uma lista FECHADA de palavras de ficha, não `\w+`: com
# `\w+` qualquer frase que comece por uma das palavras-rótulo viraria campo, e
# é exatamente o defeito de 29/07/2026 que jogou 17% das cartas fora.
#
# `localiza[çc][ãa]o` entrou junto (lote_011 l.7: "Localização: R. João Antônio
# da Silveir#, ###" — o endereço do atendimento, num rótulo que ninguém tinha
# escrito ainda).
_QUALIFICADOR = (
    r"(?:" + _H + r"+(?:d[aeo]s?|d[oa]\(a\)|\([oa]\)|completo|principal|"
    r"ap[óo]lice|seguro|ve[íi]culo|carro|im[óo]vel|sinistro|contrato|"
    r"titular|respons[áa]vel|condutor|motorista|segurad[oa]|passageiros?|"
    r"origem|destino|local|seguradora|banc[áa]ri[oa]s?|contato)){0,4}")

_LABELED_VALUE = re.compile(
    r"(?im)^(\s*[\*\-•]*\s*\*?(?:nome|modelo|placa|ve[íi]culo|cor|endere[çc]o|"
    r"localiza[çc][ãa]o|condutor|motorista|passageiro|"
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
    r"quantidade de parcelas(?: a pagar| restantes)?)"
    + _QUALIFICADOR + r"\*?\s*:?\*?\s*)(.+)$"
)


# ─────────────────────────────────────────────────────────────────────────────
# O QUE É CONHECIMENTO E NENHUMA REGRA DE PII TEM O DIREITO DE TOCAR
# ─────────────────────────────────────────────────────────────────────────────
# 06/08/2026. Este é o erro OPOSTO ao vazamento, e é o mais caro dos dois
# porque não deixa rastro: ninguém audita o que não existe.
#
# A URA da Tokio imprime o telefone da própria central numa linha só, e a linha
# saía assim do mascarador:
#
#     "Para solicitar assistência para demais serviços de reparos:
#      {NUMERO}"                                   lote_021 l.8/9/10/12, l.5
#     "*Fale conosco / SAC:*
#      {NUMERO}"                                   lote_021 l.8
#     "Para solicitar assistência para demais serviços de reparos:
#      {CPF}"                                      lote_021 l.5, lote_022 l.1
#
# 📊 Reproduzido no laboratório com o templatize de então: `"0800 727 2007"`
# devolvia `{NUMERO}` e `"08007272007"` devolvia `{CPF}`. Não é vazamento — é
# a informação de que aquele caminho da URA é TELEFÔNICO sendo apagada, e o
# corredor deixando de descobrir que existe um canal ali.
#
# A separação é segura e não depende de contexto: **0300, 0500, 0800, 3003,
# 4003, 4004 e 4090 são prefixos de serviço comercial.** A Anatel não os
# atribui a pessoa física; não existe segurado cujo telefone comece assim. É a
# única classe de número neste arquivo que dá para declarar conhecimento sem
# olhar a frase em volta.
#
# 📊 Medido: 23 desses números já sobreviviam no acervo — os que estão no MEIO
# de uma frase ("ligue 0800 701 2757 - demais regiões"). Só os que ocupavam a
# linha inteira eram comidos, porque a regra "linha só com dígitos é dado de
# alguém" não tinha como saber. Agora tem.
#
# COMO, e por que não por ordem de regra: nenhuma ordenação resolve, porque o
# que morde não é uma regra só (é `{CPF}`, é `{NUMERO}`, seria `{CARTAO}`). O
# trecho é RETIRADO do texto antes de qualquer regra rodar e devolvido idêntico
# no fim. O marcador `\x00n\x00` não pode aparecer em texto de WhatsApp, e o
# resultado final é byte a byte igual ao original nesses trechos — o
# `node_hash` da tela não muda por causa disto.
# O SEPARADOR É OBRIGATÓRIO no 0800/0300/0500, e é aqui que a regra escolhe o
# lado seguro. Um 0800 escrito corrido (`08007272007`) tem os mesmos onze
# dígitos de um CPF que comece por 080 — e um CPF assim existe. Sem separador
# não há como saber qual dos dois é, então o número continua sendo tratado como
# documento e mascarado.
#
# 💭 O custo: um 0800 digitado sem espaço nenhum vira `{CPF}` e o canal
# telefônico se perde naquela linha. 📊 No acervo isso não acontece — as 23
# ocorrências reais têm separador ("0800 701 2757", "0800-888-2532",
# "4004 2757"), porque quem publica telefone de central publica legível.
#
# Os prefixos de quatro dígitos (3003/4003/4004/4090) têm oito dígitos no
# total, longe dos onze do CPF, e por isso dispensam o separador.
_CONHECIMENTO_INTOCAVEL = re.compile(
    r"(?<![\d\-])(?:(?:0300|0500|0800)[\s.\-]\d{2,4}(?:[\s.\-]?\d{3,4})?"
    r"|(?:3003|4003|4004|4090)[\s.\-]?\d{4})(?!\d)")

_MARCA = "\x00%d\x00"


def _reservar(s: str):
    """Tira do texto o que é conhecimento e não pode ser mascarado."""
    guardados: List[str] = []

    def _troca(m: re.Match) -> str:
        guardados.append(m.group(0))
        return _MARCA % (len(guardados) - 1)

    return _CONHECIMENTO_INTOCAVEL.sub(_troca, s), guardados


def _devolver(s: str, guardados: List[str]) -> str:
    for i, original in enumerate(guardados):
        s = s.replace(_MARCA % i, original)
    return s


def templatize(text: str) -> str:
    """Devolve a tela com a PII trocada por placeholders. Determinístico."""
    s = str(text or "")
    s, guardados = _reservar(s)
    for rx, repl in _PII_PATTERNS:
        s = rx.sub(repl, s)
    # "Placa: QJQ0A91" → "Placa: {VALOR}" (o valor após o rótulo é dado do cliente)
    def _mask_labeled(m: re.Match) -> str:
        val = m.group(2).strip()
        # não mascara se o "valor" já é placeholder ou é curtíssimo/opção
        if val.startswith("{") or len(val) <= 1:
            return m.group(0)
        # O PARÊNTESE ANTES DO PLACEHOLDER — 06/08/2026, achado pelo controle.
        #
        # `Telefone do responsável: ({TELEFONE}` (📊 77 ocorrências) só passou a
        # cair aqui quando o qualificador entrou na lista de rótulos. O valor
        # JÁ estava mascarado, e com o rótulo certo; a regra o trocava por
        # `{VALOR}` e o campo passava a mentir por omissão — quem lê a carta
        # deixa de saber que ali havia um telefone.
        #
        # CLAUDE.md §12.1: rótulo específico vence rótulo genérico. Se o que
        # sobrou do valor é só pontuação e placeholders, não há o que mascarar.
        if not re.sub(r"\{[A-Z_]+\}|[\s()\[\]*.,;:\-–|/]+", "", val):
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
    return _devolver(s, guardados)


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


# Subserviços que SÓ existem no residencial. Quem cai num deles já disse o ramo:
# não existe encanador de automóvel. `chaveiro` fica de fora de propósito — ele
# existe nos dois ramos, e quem decide ali é a palavra "residenc" no texto.
_SERVICOS_SO_RESIDENCIAIS = ("eletricista", "encanador", "desentupimento", "eletrodomesticos")


def infer_ramo_servico(labels: List[str], full_text: str) -> Tuple[str, str]:
    """Infere ramo/serviço PELA ROTA (labels), não pelo número (uma seguradora
    atende vários ramos no mesmo WhatsApp).

    P-47 — O SERVIÇO É O SUBSERVIÇO, NUNCA O RAMO.
    ----------------------------------------------
    Havia um balde chamado `"residencial"` que engolia *encanador*, *eletricista*
    e a própria palavra *residência*, e devolvia `("residencial", "residencial")`.
    Como nome de serviço isso não existe em lugar nenhum: `"residencial"` não é
    subserviço de nenhum corredor — os declarados são `eletricista`, `encanador`,
    `chaveiro`, `eletrodomesticos` e `desentupimento`. O acionamento caía em
    `subservico_invalido` e o caso virava handoff, para um trabalho que os três
    corredores residenciais sabem fazer.

    E o dano não era só no acionamento: `graph.py` usa este par para achar o
    playbook de conduta (`ramo` + `servico`), e nenhum playbook se chama
    "residencial/residencial". A busca voltava vazia sempre.

    Os termos abaixo são os MESMOS de `corridor_playbooks._SUBSERVICE_ALIASES` —
    de propósito. A Porto chama de "elétrica" e "hidráulica" o que a Allianz e a
    HDI chamam de eletricista e encanador; inventar um vocabulário próprio aqui
    seria um segundo classificador para divergir do primeiro com o tempo.
    """
    blob = (" ".join(labels) + " " + str(full_text or "")).lower()
    servico = ""
    for key, terms in (
        ("guincho", ("guincho", "reboque", "remocao", "remoção")),
        ("chaveiro", ("chaveiro", "chave", "trancad")),
        ("bateria", ("bateria", "carga")),
        ("pane_seca", ("pane seca", "combustivel", "combustível")),
        ("pneu", ("pneu", "troca de pneu", "estepe")),
        ("vidros", ("vidro", "para-brisa", "parabrisa")),
        # Residenciais, cada um com o próprio nome canônico. `eletrodomesticos`
        # vem antes de `eletricista` porque é o mais específico dos dois.
        ("eletrodomesticos", ("eletrodomestico", "eletrodoméstico", "linha branca")),
        ("eletricista", ("eletricista", "eletrica", "elétrica")),
        ("encanador", ("encanador", "encanamento", "hidraulica", "hidráulica")),
        ("desentupimento", ("desentupi",)),
    ):
        if any(t in blob for t in terms):
            servico = key
            break
    # A palavra "residência" continua decidindo o RAMO — ela nunca foi um serviço.
    ramo = "residencial" if servico in _SERVICOS_SO_RESIDENCIAIS or "residenc" in blob else "auto"
    if any(t in blob for t in ("sinistro", "colisao", "colisão", "acidente")):
        servico = servico or "sinistro"
    # 🔴 07/08/2026 — O TRABALHO QUE NÃO É ASSISTÊNCIA NEM SINISTRO.
    #
    # Até aqui a função sabia nomear guincho, encanador e sinistro, e mais nada.
    # Quem escreve o playbook (o destilador) sabe nomear mais: `cobranca`,
    # `apolice`, `renovacao`. Escrever com um vocabulário e procurar com outro
    # é a mesma doença do Lapidador — 📊 6 dos 12 playbooks ATIVOS eram mudos
    # porque esta função nunca produzia a chave com que foram gravados.
    #
    # Os nomes abaixo são os do campo `tipo` do Estágio 1, de propósito. Vêm
    # DEPOIS da assistência e do sinistro porque são menos específicos: quem
    # liga sobre o guincho que não chegou está falando de guincho, mesmo que
    # cite o boleto no meio.
    if not servico:
        for key, terms in (
            ("cobranca", ("boleto", "parcela", "fatura", "pagamento", "pagar",
                          "debito em conta", "débito em conta", "cobran")),
            ("apolice", ("apolice", "apólice", "segunda via", "2a via")),
            ("renovacao", ("renova",)),
        ):
            if any(t in blob for t in terms):
                servico = key
                break
    # E o ramo VIDA, que o destilador produz e esta função transformava em
    # "auto" pelo `else` do ternário acima — sem erro e sem log.
    if any(t in blob for t in ("seguro de vida", "beneficiario", "beneficiário",
                               "falecim", "seguro vida")):
        ramo = "vida"
    return ramo, servico
