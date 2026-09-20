# -*- coding: utf-8 -*-
"""O CONFERENTE — o que o leitor humano fez à mão em 19/09, virado passo do cano.

SPEC-EXTRA-001.5.2 · unidade **F**. Toda linha proposta recebe, ANTES de chegar à
fila, um veredito contra a **página** do documento: o trecho está ali? o número do
limite está ali, com unidade? o plano existe na âncora? o `coberto=nao` veio de
uma exclusão de OUTRA cobertura? o produto é nome de arquivo?

🔴 O QUE ESTE MÓDULO NÃO É (CLAUDE.md §5)
=========================================
Não é um segundo verificador. `assistance_plans_extractor.verificar` continua
sendo o verificador de ESCRITA (recusa a linha antes de ela nascer); este aqui
**anota** uma linha que já existe. Os dois nunca publicam, nunca promovem nada a
`publicado`, e o segundo reusa os regexes do primeiro (`_E_EXCLUSAO_DE_RISCO`,
`_NEGA_O_SERVICO`) em vez de reescrevê-los — reescrever produziria dois pareceres
sobre a mesma frase, e o pior dos dois chegaria ao Founder como se fosse o único.

Não é um segundo leitor de PDF: ele recebe `paginas: {numero: texto}` já lidas
por `assistance_plans_base.texto_das_paginas` (o `fitz` de sempre). Quem chama
lê; este módulo compara.

Não é um extrator de âncora (unidade A). Quando a âncora existir, ela chega em
`planos_da_ancora`. Enquanto não existir, o campo `plano` é conferido pelo que dá
para conferir contra a página — e o que não dá é declarado `nao_avaliado`, nunca
`ok` por omissão.

🔴 O DIALETO (CLAUDE.md §9.4)
=============================
📊 20/09/2026: o gabarito de 19/09 guardou o trecho **sem acento**
(*"Riscos Excluidos: danos por inundacao"*), e a mesma página lida pelo `fitz`
tem **com** acento (*"Riscos Excluídos: danos por inundação"*). `BASE.normalizar_trecho`
— que é a normalização do HASH — só colapsa espaço, de propósito: o hash é prova
de identidade e não pode ser tolerante. A comparação de LEITURA é outra pergunta
("um humano diria que esta frase está nesta página?") e precisa de outra régua:
`_para_leitura` baixa a caixa, tira acento e colapsa espaço e hífen de quebra.

⚠️ Aplicar a régua do hash aqui faria o conferente devolver `DIVERGE` para as 81
linhas — inclusive as 25 certas. A régua foi medida no MESMO motor que a aplica:
o texto vem de `fitz`, e o casamento é testado contra `fitz` em
`tests/test_o_conferente_concorda_com_o_leitor.py`.

⚠️ CALIBRAGEM DECLARADA: as regras abaixo foram afinadas contra as 81 linhas de
`SPEC-EXTRA-001.5-LINHAS-CONFERIDAS.json` — que é, hoje, a única linha de base
que existe (📊 a própria SPEC diz isso, §3.F). O número do GATE F é, portanto,
concordância **em amostra de calibragem**; documento novo é medição nova.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import assistance_plans_base as BASE
from .assistance_plans_extractor import (
    _E_EXCLUSAO_DE_RISCO,
    _NEGA_O_SERVICO,
    _PLANO_PADRAO,
    produto_canonico,
)

#: Os três vereditos. `NAO_CONSEGUI` **não** é `DIVERGE`: "o PDF não abriu" e "a
#: página não confirma" mandam a pessoa fazer coisas opostas.
CONFERE, DIVERGE, NAO_CONSEGUI = "CONFERE", "DIVERGE", "NAO_CONSEGUI"

#: Os estados de um campo. `nao_avaliado` é o terceiro valor obrigatório: sem ele,
#: "não tinha como conferir" viraria `ok`, e o silêncio vira carimbo.
OK, DIVERGE_CAMPO, NAO_AVALIADO = "ok", "diverge", "nao_avaliado"

#: Os campos que o conferente olha. A ordem é a da leitura humana de 19/09.
CAMPOS = ("pagina", "trecho", "coberto", "limite", "plano", "produto")

#: 🔴 O INTERRUPTOR QUE TORNA O NÚMERO DO GATE HONESTO (juiz B3, 20/09/2026).
#:
#: 📊 O conferente marcava `plano: diverge` sempre que a linha dizia
#: `Plano único` — e 60 das 81 linhas do gabarito dizem isso. O juiz mediu o
#: contrafactual:
#:
#: ```
#: COM a regra do placeholder ....  65/81 = 80,2 %   (o número que eu reportei)
#: SEM a regra do placeholder ....  44/81 = 54,3 %   ABAIXO do sempre-DIVERGE (69,1 %)
#: ```
#:
#: 🔴 E o extrator v2 **nunca emite "Plano único"**. Ou seja: o gate media uma
#: regra que não vai existir no cano novo, e em linha nova o conferente valeria
#: ~54 %. Um gate que passa por causa de um defeito do extrator antigo mede o
#: defeito, não o conferente.
#:
#: Este interruptor existe para o `--gabarito` reportar os DOIS números lado a
#: lado — e o GATE do script é o SEM a regra.
REGRA_DO_PLACEHOLDER = True


@dataclass(frozen=True)
class Veredito:
    """O parecer de UMA linha. `motivos` é a lista, não um texto só.

    🔴 Uma linha pode divergir por dois motivos ao mesmo tempo (o plano é
    placeholder E o limite é uma referência cruzada). Guardar um texto só
    esconderia o segundo, e o segundo é o que faz o curador abrir o PDF.
    """

    veredito: str
    campos: Dict[str, str] = field(default_factory=dict)
    motivos: List[str] = field(default_factory=list)
    pagina: Optional[int] = None

    def __bool__(self) -> bool:  # pragma: no cover - conveniência
        return self.veredito == CONFERE


# ---------------------------------------------------------------------------
# A régua da LEITURA — e por que ela não é a régua do hash
# ---------------------------------------------------------------------------
#: Hífen no fim de linha que o `fitz` devolve quando a palavra foi quebrada.
_QUEBRA = re.compile(r"-\s*\n\s*")


def _para_leitura(texto: Any) -> str:
    """Caixa baixa, sem acento, sem quebra de palavra, espaço colapsado.

    ⚠️ Medida no motor que a aplica: o texto entra vindo do `fitz`
    (`BASE.texto_das_paginas`), nunca de um `.txt` digitado à mão.
    """
    bruto = _QUEBRA.sub("", str(texto or "").replace("\xa0", " "))
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", bruto)
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


#: 📊 Um trecho gravado tem até 120 caracteres e pode ter sido cortado no meio
#: de uma palavra; comparar o fim truncado produziria `DIVERGE` falso. O
#: casamento tenta primeiro o prefixo estável.
TAMANHO_DO_PREFIXO = 60

#: 🔴 A TERCEIRA TENTATIVA, E POR QUE ELA PRECISOU EXISTIR.
#:
#: 📊 20/09/2026, medido nas 81 linhas contra as páginas REAIS: **14 das 25
#: linhas que o leitor aprovou** falhavam no casamento por substring. A causa
#: não era a linha — era a TABELA. O trecho vem de uma tabela, e o `fitz`
#: lineariza a tabela numa ordem que não é a da leitura:
#:
#: ```
#: gravado  "Hospedagem | Ate R$ 100,00 por evento e R$ 200,00 por Vigencia
#:           (produto Auto Basico, plano Essencial)"
#: fitz     "auto basico passeio, pick-up e utilitarios coberturas essencial
#:           hospedagem ate r$ 100,00 por evento e r$ 200,00 por vigencia"
#: ```
#:
#: Toda palavra está lá; a ORDEM e os separadores não. Exigir a substring seria
#: reprovar a linha certa por causa do extrator de PDF — e um conferente que
#: reprova o que está certo é descartado pelo curador na terceira linha.
#:
#: ⚠️ É a régua MAIS FRACA das três, e por isso é a última: só entra quando as
#: duas exatas falham. O limiar é alto de propósito.
COBERTURA_DE_PALAVRAS = 0.85

#: Palavras curtas não contam: "de", "a", "e", "no" estão em qualquer página, e
#: incluí-las faria qualquer trecho "existir" em qualquer lugar.
TAMANHO_MINIMO_DA_PALAVRA = 3

_PALAVRA = re.compile(r"[a-z0-9$%,./]+")


def _palavras(texto: str) -> List[str]:
    """As palavras comparáveis, SEM a pontuação colada.

    📊 20/09/2026: com a vírgula dentro do token, `basico,` (do trecho) não
    casava com `basico` (da página), e a cobertura da linha certa da HDI caía de
    92 % para 85 % — exatamente em cima do limiar. Pontuação colada é do
    extrator de PDF, não do documento.
    """
    fora = []
    for bruto in _PALAVRA.findall(texto):
        palavra = bruto.strip(",./$%")
        if len(palavra) >= TAMANHO_MINIMO_DA_PALAVRA:
            fora.append(palavra)
    return fora


def _trecho_esta(trecho: str, texto_da_pagina: str) -> bool:
    """O trecho está nesta página? Inteiro, pelo prefixo, ou palavra a palavra."""
    alvo, pagina = _para_leitura(trecho), _para_leitura(texto_da_pagina)
    if not alvo or not pagina:
        return False
    if alvo in pagina:
        return True
    if len(alvo) > TAMANHO_DO_PREFIXO and alvo[:TAMANHO_DO_PREFIXO] in pagina:
        return True
    do_alvo = _palavras(alvo)
    if len(do_alvo) < 4:
        # Com três palavras, 85 % é "duas de três": qualquer página passaria.
        return False
    da_pagina = set(_palavras(pagina))
    presentes = sum(1 for p in do_alvo if p in da_pagina)
    return (presentes / len(do_alvo)) >= COBERTURA_DE_PALAVRAS


# ---------------------------------------------------------------------------
# As formas que decidem cada campo
# ---------------------------------------------------------------------------
#: A cobertura que **só existe se o cliente contratou**. 📊 6 das 40 linhas
#: CORRIGIR são um `sim` seco numa cobertura opcional — e um `sim` desses faz o
#: segurado acionar um direito que ele não comprou.
_E_OPCIONAL = re.compile(
    r"cobertura[s]?\s+adicion|adicionais\s+e\s+opcion|opcional|"
    r"desde\s+que\s+contratad|se\s+contratad|quando\s+contratad|"
    r"mediante\s+contrata|contratacao\s+(?:adicional|facultativa)",
)

#: O limite que é uma REFERÊNCIA, não um limite. 📊 4 linhas da HDI gravaram
#: *"CONFORME DESCRITOS NA CLAUSULA 2 - PLANOS, PRODUTOS E LIMITES"* no campo do
#: limite: quem lê a fila vê um limite preenchido e publica uma promessa vazia.
_E_REFERENCIA_CRUZADA = re.compile(
    r"conforme\s+(?:descrit|previst|disposto|o\s+plano|tabela|clausula)|"
    r"(?:vide|ver|conforme)\s+(?:a\s+)?clausula|"
    r"de\s+acordo\s+com\s+(?:a\s+)?(?:clausula|tabela)",
)

#: O cabeçalho de cobertura numerada — *"COBERTURA 07 - VIDROS"*. 📊 é a forma
#: que denuncia o padrão 1 da SPEC: a frase que decidiu a linha estava dentro da
#: cláusula de OUTRA cobertura.
_CABECALHO_DE_COBERTURA = re.compile(
    r"cobertura\s+(?:n[.º\s]*)?(\d{1,2})\s*[-–:]\s*([a-z0-9 ,/´'’-]{3,60})",
)

#: O nome de produto que é nome de ARQUIVO ou de VERSÃO. 📊 4 das 40: um nome
#: terminando em travessão solto, um `Seguro Residencial Conteudo_V1.2`, um
#: `... CC`, um `— Condições Contratuais V2.9`.
_PRODUTO_E_ARQUIVO = re.compile(
    r"_v\s*\d|\bv\s*\d+\.\d|condicoes\s+(?:contratuais|gerais)|"
    r"\b(?:cc|cg|cp)\b\s*$|[-–—]\s*$|\.(?:pdf|docx?|txt|html?)\b",
)

#: Os números do limite, para conferir se eles existem NA PÁGINA.
_NUMEROS = re.compile(r"\d[\d.,]*")

#: A página que DECLARA um limite. Usada só para a linha que não gravou nenhum.
_PAGINA_DECLARA_LIMITE = re.compile(r"limite\s+de\s+utilizacao|limitado\s+a\s+\d")


def _numeros_de(texto: Any) -> List[str]:
    """Os números de um texto, já sem separador de milhar nem decimal zero."""
    fora = []
    for n in _NUMEROS.findall(str(texto or "")):
        limpo = n.strip(".,").replace(".", "").replace(",", ".")
        if not limpo:
            continue
        try:
            valor = float(limpo)
        except ValueError:
            continue
        fora.append(("%g" % valor))
    return fora


def _numero_esta_na_pagina(numero: str, pagina: str) -> bool:
    """O número aparece na página, com ou sem separador de milhar?

    ⚠️ `1200` na linha pode estar escrito `1.200,00` na página: comparar texto
    cru daria `DIVERGE` numa linha certa. A comparação é sobre o VALOR.
    """
    return numero in _numeros_de(pagina)


# ---------------------------------------------------------------------------
# 🔴 A RELAÇÃO — o que faltava, e o que custou o selo verde em erro
# ---------------------------------------------------------------------------
# 📊 20/09/2026, red team B2, em páginas REAIS (HDI Auto p.90, Tokio Auto p.24),
# COM a âncora certa em mãos. Três linhas ERRADAS receberam `CONFERE` com os
# seis campos `ok`:
#
#   ERRO 1  o limite da coluna VIP (R$ 150/450) atribuído ao plano Essencial
#   ERRO 2  o trecho "Plano Completo: 3 (três) vezes…" atribuído ao plano VIP
#   ERRO 3  `coberto=sim` numa página cujo CABEÇALHO diz "cobertura adicional"
#
# 🔴 A causa é uma só, e não é regex: o conferente perguntava de cada campo
# SOZINHO — *"o plano existe na âncora?"*, *"o número existe na página?"* — e
# nunca a pergunta que decide: **este trecho é DESTE plano?** Numa condição
# geral, todo número de tabela e todo `sim` pertencem a uma COLUNA, e um campo
# certo na coluna errada é uma promessa que a seguradora não honra.
#
# ⚠️ E o pior é que ele SELAVA: `CONFERE` é o carimbo que manda o Founder
# publicar sem abrir o PDF. Errar calado é ruim; errar com carimbo é pior.

#: Quantos caracteres ao redor do trecho contam como "a vizinhança imediata".
#: 💭 Ordem de grandeza de um parágrafo e do cabeçalho logo acima dele.
JANELA_DA_VIZINHANCA = 600

#: E quanto ACIMA do trecho conta como "o cabeçalho da cláusula".
JANELA_DO_CABECALHO = 900


def _onde_esta(trecho: str, texto_da_pagina: str) -> Optional[int]:
    """A posição do trecho no texto NORMALIZADO da página, ou `None`."""
    alvo, pagina = _para_leitura(trecho), _para_leitura(texto_da_pagina)
    if not alvo or not pagina:
        return None
    pos = pagina.find(alvo)
    if pos >= 0:
        return pos
    if len(alvo) > TAMANHO_DO_PREFIXO:
        pos = pagina.find(alvo[:TAMANHO_DO_PREFIXO])
        if pos >= 0:
            return pos
    return None


def _planos_citados(texto: str, ancora: List[str]) -> List[str]:
    """Quais planos da âncora este texto NOMEIA.

    ⚠️ Só nomes da âncora. Procurar "plano" seguido de palavra inventaria
    planos que o documento não tem — e inventar âncora é a unidade A, que não é
    deste módulo (CLAUDE.md §5).
    """
    leitura = _para_leitura(texto)
    fora = []
    for plano in ancora:
        nome = _para_leitura(plano)
        if len(nome) >= 3 and re.search(r"(?<![a-z0-9])%s(?![a-z0-9])"
                                        % re.escape(nome), leitura):
            fora.append(plano)
    return fora


# ---------------------------------------------------------------------------
# O conferente
# ---------------------------------------------------------------------------
def conferir_linha(
    linha: Dict[str, Any],
    paginas: Dict[int, str],
    planos_da_ancora: Optional[List[str]] = None,
) -> Veredito:
    """O parecer automático de UMA linha contra a PÁGINA. 🔴 Nunca publica.

    `linha` é o dicionário da linha (o da fila, ou a proposta do extrator antes
    de virar linha): `servico`, `coberto`, `limite_valor`, `limite_unidade`,
    `limite_texto`, `pagina`, `produto`, `plano` e — quando existir — `trecho`.

    `paginas` é `{numero: texto}` já lido por `BASE.texto_das_paginas`. Passar o
    documento inteiro permite dizer *"o trecho existe, mas na página 31"*, que é
    um defeito diferente de *"o trecho não existe"*.

    `planos_da_ancora`, quando vier (unidade A), é a lista de planos que a
    cláusula de planos do documento enumera.
    """
    campos: Dict[str, str] = {c: NAO_AVALIADO for c in CAMPOS}
    motivos: List[str] = []

    try:
        numero = int(linha.get("pagina"))
    except (TypeError, ValueError):
        numero = None

    paginas = {int(k): str(v or "") for k, v in (paginas or {}).items()}
    if not paginas:
        return Veredito(NAO_CONSEGUI, campos, ["paginas_nao_lidas"], numero)
    if numero is None:
        campos["pagina"] = DIVERGE_CAMPO
        motivos.append("a linha não registrou a página")
        return Veredito(DIVERGE, campos, motivos, None)

    texto = paginas.get(numero)
    if texto is None:
        campos["pagina"] = DIVERGE_CAMPO
        motivos.append("a página %d não está no documento arquivado" % numero)
        return Veredito(DIVERGE, campos, motivos, numero)
    campos["pagina"] = OK

    posicao = _onde_esta(str(linha.get("trecho") or ""), texto)

    _conferir_trecho(linha, numero, texto, paginas, campos, motivos)
    _conferir_coberto(linha, texto, posicao, campos, motivos)
    # ⚠️ A ORDEM IMPORTA: o limite é conferido ANTES do plano, porque é a
    # conferência da RELAÇÃO (dentro de `_conferir_plano`) que pode REBAIXAR um
    # limite `ok` para `nao_avaliado` — "o número existe, mas não sei de qual
    # coluna". Invertê-la faria `_conferir_limite` reescrever o rebaixamento, e
    # o ERRO 1 do red team voltaria em silêncio.
    _conferir_limite(linha, texto, campos, motivos)
    _conferir_plano(linha, paginas, texto, posicao, planos_da_ancora, campos, motivos)
    _conferir_produto(linha, campos, motivos)
    pendentes = _selar(linha, campos, motivos)

    return Veredito(_veredito_de(campos, pendentes), campos, motivos, numero)


#: 🔴 OS CAMPOS CRÍTICOS — os que decidem se a linha pode ser publicada sem que
#: ninguém abra o PDF. `produto` fica de fora de propósito: um produto com nome
#: feio não faz a seguradora negar o atendimento; um limite da coluna errada faz.
CAMPOS_CRITICOS = ("trecho", "plano", "coberto", "limite")


def _selar(linha, campos, motivos) -> None:
    """🔴 A REGRA DO SELO: não se carimba o que não se conferiu.

    📊 O red team B2 produziu `CONFERE` com `limite: nao_avaliado` — e `CONFERE`
    é o carimbo que manda o Founder publicar sem abrir o PDF. Um campo que o
    conferente não conseguiu avaliar **não é um campo aprovado**, e tratá-lo
    como tal é a definição de erro com carimbo.

    ⚠️ Isto REBAIXA linhas antigas: 📊 as 39 da fila não têm `trecho` gravado, e
    todas passam a `NAO_CONSEGUI`. É o honesto — elas nunca foram conferidas.
    """
    tem_limite = linha.get("limite_valor") is not None or bool(
        str(linha.get("limite_texto") or "").strip())
    pendentes = [c for c in CAMPOS_CRITICOS
                 if campos.get(c) == NAO_AVALIADO and (c != "limite" or tem_limite)]
    if pendentes:
        motivos.append("não consegui conferir: %s" % ", ".join(pendentes))
    return pendentes


def _veredito_de(campos, pendentes) -> str:
    """`DIVERGE` vence; depois o selo; só então `CONFERE`."""
    if DIVERGE_CAMPO in campos.values():
        return DIVERGE
    return NAO_CONSEGUI if pendentes else CONFERE


def _conferir_trecho(linha, numero, texto, paginas, campos, motivos) -> None:
    """O trecho está NAQUELA página? E, se não, está em alguma outra?

    🔴 As duas respostas são defeitos diferentes: *"a página está errada"* se
    conserta mudando um número; *"o trecho não existe"* obriga a reextrair.
    """
    trecho = str(linha.get("trecho") or "").strip()
    if len(trecho) < 12:
        # A base não guarda o trecho (só o `trecho_hash`): quando a linha vem da
        # fila sem ele, isto fica declarado, não vira `ok` por omissão.
        motivos.append("a linha não trouxe o trecho para conferir")
        return
    if _trecho_esta(trecho, texto):
        campos["trecho"] = OK
        return
    outras = [p for p, t in sorted(paginas.items()) if p != numero and _trecho_esta(trecho, t)]
    if outras:
        campos["pagina"] = DIVERGE_CAMPO
        campos["trecho"] = OK
        motivos.append("o trecho existe, mas na página %s — a linha aponta a %d"
                       % (", ".join(str(p) for p in outras[:3]), numero))
    else:
        campos["trecho"] = DIVERGE_CAMPO
        motivos.append("o trecho não está em nenhuma página do documento arquivado")


def _conferir_coberto(linha, texto, posicao, campos, motivos) -> None:
    """O `coberto` é do SERVIÇO, ou foi colhido da cláusula de outra cobertura?

    🔴 O DIALETO, MEDIDO (CLAUDE.md §9.4) — red team B2, 20/09/2026
    ==============================================================
    Os regexes vêm do verificador de escrita, que os aplica ao trecho **como o
    modelo o escreveu**. Aqui eles são aplicados ao texto **como o `fitz` o
    devolve** — e isso é outro dialeto:

    ```
    📊 "Riscos Excluídos: danos por inundação…"  (COM acento, o que o PDF tem)
       `risco[s]?\\s+excluid`  ->  ZERO   o 'í' não é 'i'
    📊 "Riscos Excluidos: danos por inundacao…"  (o gabarito, sem acento)
       `risco[s]?\\s+excluid`  ->  casa
    ```

    O resultado era o pior possível: a MESMA frase, com o acento que o documento
    de verdade tem, recebia `CONFERE`; sem acento, `DIVERGE`. **O padrão foi
    medido num motor e aplicado em outro.** A régua é `_para_leitura` — a mesma
    que casa o trecho —, e há guarda exigindo ZERO para o padrão cru sobre a
    fixture acentuada.

    🔴 E O CABEÇALHO DA CLÁUSULA MANDA (ERRO 3)
    ===========================================
    📊 Um `sim` numa página cujo TRECHO não diz nada de opcional, mas cujo
    CABEÇALHO, logo acima, diz *"COBERTURA ADICIONAL"*, recebia `CONFERE`. O
    escopo da cláusula é o que decide (§3.B da SPEC), e ele está **acima** do
    trecho, não dentro dele.
    """
    coberto = str(linha.get("coberto") or "")
    servico = str(linha.get("servico") or "")
    trecho = str(linha.get("trecho") or "").strip()
    base = trecho if len(trecho) >= 12 else texto
    # ⚠️ NORMALIZADO, sempre: é o conserto do dialeto acima.
    leitura = _para_leitura(base)
    if not coberto:
        return
    campos["coberto"] = OK

    # 1 · o "não" que é exclusão de risco DENTRO de outra cobertura (padrão 1).
    #     Os regexes são os do verificador de escrita: um parecer só por frase.
    if coberto == "nao" and _E_EXCLUSAO_DE_RISCO.search(leitura) \
            and not _NEGA_O_SERVICO.search(leitura):
        campos["coberto"] = DIVERGE_CAMPO
        motivos.append("o 'nao' veio de uma cláusula de exclusão de risco, "
                       "não de uma recusa do serviço")

    # 2 · o "sim" numa cobertura que só existe se contratada — no trecho…
    if coberto == "sim" and _E_OPCIONAL.search(leitura):
        campos["coberto"] = DIVERGE_CAMPO
        motivos.append("a página trata de cobertura adicional/opcional: "
                       "'sim' promete o que só existe se o cliente contratou")
    # 2b · …e no CABEÇALHO logo acima dele.
    elif coberto == "sim" and posicao is not None:
        acima = _para_leitura(texto)[max(0, posicao - JANELA_DO_CABECALHO):posicao]
        if _E_OPCIONAL.search(acima):
            campos["coberto"] = DIVERGE_CAMPO
            motivos.append("o cabeçalho da cláusula logo acima do trecho diz "
                           "que a cobertura é adicional/opcional — 'sim' aqui "
                           "promete o que só existe se o cliente contratou")

    # 3 · a frase saiu do cabeçalho de OUTRA cobertura numerada.
    for _numero, nome in _CABECALHO_DE_COBERTURA.findall(leitura):
        canonico = BASE.servico_canonico(nome)
        if canonico and servico and canonico != servico:
            campos["coberto"] = DIVERGE_CAMPO
            motivos.append("a frase está dentro da cláusula '%s', que é de '%s', "
                           "não de '%s'" % (nome.strip(), canonico, servico))
            break


def _conferir_limite(linha, texto, campos, motivos) -> None:
    """O número do limite existe na página, com unidade — ou não existe limite."""
    valor = linha.get("limite_valor")
    unidade = str(linha.get("limite_unidade") or "")
    limite_texto = str(linha.get("limite_texto") or "").strip()
    leitura_pagina = _para_leitura(texto)

    if valor is None and not limite_texto:
        # 🔴 A página que DECLARA um limite e a linha que não gravou nenhum:
        # 📊 o guincho da Tokio (200 km, p. 26) entrou "sem limite gravado".
        if _PAGINA_DECLARA_LIMITE.search(leitura_pagina):
            campos["limite"] = DIVERGE_CAMPO
            motivos.append("a página declara um limite de utilização e a linha "
                           "não gravou nenhum")
        return

    campos["limite"] = OK
    if valor is not None and not unidade:
        campos["limite"] = DIVERGE_CAMPO
        motivos.append("limite com valor e sem unidade")
    if limite_texto and _E_REFERENCIA_CRUZADA.search(_para_leitura(limite_texto)):
        campos["limite"] = DIVERGE_CAMPO
        motivos.append("o limite gravado é uma referência a outra cláusula, "
                       "não um limite: %r" % limite_texto[:60])
        return
    trecho = str(linha.get("trecho") or "").strip()
    do_trecho = set(_numeros_de(trecho)) if len(trecho) >= 12 else None
    for numero in _numeros_de(limite_texto) or _numeros_de(valor):
        if not _numero_esta_na_pagina(numero, leitura_pagina):
            campos["limite"] = DIVERGE_CAMPO
            motivos.append("o número %s do limite não está na página %s"
                           % (numero, linha.get("pagina")))
            break
        # 🔴 ESTAR NA PÁGINA NÃO BASTA (red team B2, ERRO 1).
        # 📊 A tabela da HDI (p.90) tem R$ 100, R$ 150 e R$ 200 na mesma página,
        # em COLUNAS diferentes. Um número que existe na página mas NÃO no
        # trecho que sustenta a linha pode ser da coluna de outro plano — e
        # `ok` aqui é o selo verde em cima de um limite que não é do segurado.
        if do_trecho is not None and numero not in do_trecho:
            campos["limite"] = NAO_AVALIADO
            motivos.append("o número %s está na página, mas não no trecho que "
                           "sustenta a linha — pode ser da coluna de outro plano"
                           % numero)
            break


def _conferir_a_relacao(linha, texto, posicao, ancora, campos, motivos) -> None:
    """🔴 ESTE TRECHO É DESTE PLANO? — a pergunta que faltava (red team B2).

    O plano estar na âncora só diz que ele **existe**. A pergunta que decide se
    a linha pode ser publicada é se o TRECHO pertence à coluna daquele plano.

    ```
    📊 ERRO 2, Tokio Auto p.24, medido: o trecho "Plano Completo: 3 (três)
       vezes…" gravado sob o plano VIP. A página tem as duas frases, uma embaixo
       da outra. O trecho NOMEIA o plano — e não é o da linha.
    📊 ERRO 1, HDI Auto p.90: o limite da coluna VIP (R$ 150/450) gravado sob o
       Essencial. O `fitz` devolve a tabela CÉLULA POR CÉLULA — 'Pane Seca ' numa
       linha, 'Até R$ 150,00 por evento e ' noutra — e a associação de LINHA da
       tabela não sobrevive à extração.
    ```

    🔴 E é aí que o conferente tem de dizer **"não consegui"**, não "ok". Com
    três planos na página e nada ligando o trecho a um deles, qualquer resposta
    é chute — e um chute com selo verde é o defeito que esta rodada consertou.
    """
    plano = str(linha.get("plano") or "").strip()
    trecho = str(linha.get("trecho") or "").strip()

    # 1 · o TRECHO nomeia um plano? Então é ele que manda.
    if len(trecho) >= 12:
        no_trecho = _planos_citados(trecho, ancora)
        if no_trecho:
            if any(_para_leitura(p) == _para_leitura(plano) for p in no_trecho):
                campos["plano"] = OK
            else:
                campos["plano"] = DIVERGE_CAMPO
                motivos.append("o trecho é do plano %s, e a linha o gravou sob %r"
                               % (" / ".join(no_trecho), plano))
            return

    # 2 · a vizinhança imediata do trecho na página.
    leitura = _para_leitura(texto)
    if posicao is not None:
        janela = leitura[max(0, posicao - JANELA_DA_VIZINHANCA):
                         posicao + JANELA_DA_VIZINHANCA]
        perto = _planos_citados(janela, ancora)
        if len(perto) == 1:
            if _para_leitura(perto[0]) == _para_leitura(plano):
                campos["plano"] = OK
            else:
                campos["plano"] = DIVERGE_CAMPO
                motivos.append("ao redor do trecho a página só fala do plano %r,"
                               " e a linha o gravou sob %r" % (perto[0], plano))
            return

    # 3 · a página inteira.
    na_pagina = _planos_citados(texto, ancora)
    if len(na_pagina) == 1 and _para_leitura(na_pagina[0]) == _para_leitura(plano):
        campos["plano"] = OK
        return
    if len(na_pagina) >= 2:
        motivos.append("a página fala de %d planos (%s) e nada liga o trecho ao "
                       "plano %r desta linha — a coluna é um chute"
                       % (len(na_pagina), ", ".join(na_pagina)[:80], plano))
    else:
        motivos.append("a página não nomeia o plano %r em lugar nenhum" % plano)
    campos["plano"] = NAO_AVALIADO
    # 🔴 E o limite cai junto: um número de tabela sem coluna conhecida não é um
    # limite conferido. 📊 é exatamente o ERRO 1 (R$ 150 da coluna VIP).
    if campos.get("limite") == OK:
        campos["limite"] = NAO_AVALIADO


def _conferir_plano(linha, paginas, texto, posicao, planos_da_ancora,
                    campos, motivos) -> None:
    """O plano da linha existe na âncora — ou, sem âncora, foi lido do documento?

    🔴 `Plano único` é o PLACEHOLDER do extrator (`_PLANO_PADRAO`), não um nome
    lido da condição geral. 📊 19/09: 35 das 56 linhas reprovadas o carregam, e
    o manual do Bradesco Auto, que tem 9 planos, virou um só. O conferente não
    tem como dizer que o documento tem um plano só — então ele diz que **não
    conferiu o plano**, e isso é uma divergência, não um `ok`.
    """
    plano = str(linha.get("plano") or "").strip()
    if not plano:
        campos["plano"] = DIVERGE_CAMPO
        motivos.append("a linha não tem plano")
        return

    if planos_da_ancora:
        conhecidos = {_para_leitura(p) for p in planos_da_ancora if p}
        if _para_leitura(plano) not in conhecidos:
            campos["plano"] = DIVERGE_CAMPO
            motivos.append("o plano %r não está entre os que a cláusula de "
                           "planos enumera (%s)"
                           % (plano, ", ".join(sorted(planos_da_ancora))[:120]))
            return
        _conferir_a_relacao(linha, texto, posicao, planos_da_ancora, campos, motivos)
        return

    if REGRA_DO_PLACEHOLDER and _para_leitura(plano) == _para_leitura(_PLANO_PADRAO):
        campos["plano"] = DIVERGE_CAMPO
        motivos.append("o nome do plano não foi lido do documento: %r é o "
                       "preenchimento padrão do extrator" % _PLANO_PADRAO)
        return

    if any(_trecho_esta(plano, t) for t in paginas.values()):
        campos["plano"] = OK
    else:
        motivos.append("o nome do plano %r não aparece no texto do documento — "
                       "sem a cláusula de planos não dá para confirmá-lo" % plano[:60])


def _conferir_produto(linha, campos, motivos) -> None:
    """O produto veio da CAPA, ou é o nome do arquivo com outra roupa?"""
    produto = str(linha.get("produto") or "").strip()
    if not produto:
        return
    campos["produto"] = OK
    if _PRODUTO_E_ARQUIVO.search(_para_leitura(produto)):
        campos["produto"] = DIVERGE_CAMPO
        motivos.append("o produto %r tem cara de nome de arquivo ou de versão, "
                       "não de nome de produto" % produto[:60])
        return
    # `produto_canonico` é o mesmo do extrator: se ele MUDA o texto, o que está
    # gravado não passou por ele — e o resto do nome de arquivo ficou.
    #
    # ⚠️ A COMPARAÇÃO IGNORA A CAIXA, e é uma escolha com custo declarado.
    # 📊 `Mapfre condominio` × `Mapfre Condominio` são, de fato, DUAS chaves na
    # base para o mesmo produto — um defeito real (o gancho *"existe um plano
    # acima do seu"* nunca acha o superior). Mas ele é do produto INTEIRO, não
    # daquela linha: o leitor humano de 19/09 aprovou a linha e registrou a
    # caixa como problema à parte. Acusar a linha por isso mandaria o curador
    # recusar o que está certo. 🔴 Fica como PENDÊNCIA da unidade D, não como
    # divergência da linha.
    if _para_leitura(produto_canonico(produto)) != _para_leitura(produto):
        campos["produto"] = DIVERGE_CAMPO
        motivos.append("o produto gravado (%r) não é o canônico (%r)"
                       % (produto[:40], produto_canonico(produto)[:40]))


# ---------------------------------------------------------------------------
# A medição — a concordância com o leitor humano de 19/09
# ---------------------------------------------------------------------------
#: 🔴 A DEFINIÇÃO, ESCRITA ANTES DE MEDIR (CLAUDE.md §9.2 e o card da unidade F).
#: `PUBLICAR` do leitor ≙ `CONFERE` do conferente; `CORRIGIR` e `RECUSAR` ≙
#: `DIVERGE`. `NAO_CONSEGUI` do conferente nunca conta como concordância com um
#: veredito do leitor que não seja `NAO_CONSEGUI`.
EQUIVALENCIA = {"PUBLICAR": CONFERE, "CORRIGIR": DIVERGE,
                "RECUSAR": DIVERGE, "NAO_CONSEGUI": NAO_CONSEGUI}


def concorda_com_o_leitor(veredito_do_leitor: str, parecer: Veredito) -> bool:
    """Concordância de LINHA — a régua do GATE F."""
    return EQUIVALENCIA.get(str(veredito_do_leitor)) == parecer.veredito


def concorda_no_campo(campo_errado: Optional[str], parecer: Veredito) -> Optional[bool]:
    """Concordância de CAMPO: o conferente apontou o MESMO campo que o leitor?

    `None` quando o leitor não nomeou campo — aí só a linha é comparável.

    ⚠️ `None` TAMBÉM quando o campo que o leitor nomeou não é um dos que o
    conferente olha. 📊 4 das 42 linhas dizem `condicao`, e o conferente não tem
    checagem de `condicao`: contá-las como erro inflaria o denominador com
    perguntas que nunca foram feitas. O que falta vira pendência declarada, não
    um número pior fingindo rigor.
    """
    if not campo_errado:
        return None
    if str(campo_errado) not in CAMPOS:
        return None
    return parecer.campos.get(str(campo_errado)) == DIVERGE_CAMPO


def medir(
    pares: List[Tuple[Dict[str, Any], Veredito]],
) -> Dict[str, Any]:
    """A medição completa: linha, campo e a lista das divergências.

    `pares` = [(linha_do_gabarito, parecer), ...]. O gabarito traz `veredito` e
    `campo_errado`. ⚠️ Devolve a LISTA das discordâncias: o gate manda listá-las,
    não escondê-las (§3.F da SPEC).
    """
    linhas_ok = campos_ok = campos_total = 0
    discordancias: List[Dict[str, Any]] = []
    for gab, parecer in pares:
        bate = concorda_com_o_leitor(gab.get("veredito"), parecer)
        linhas_ok += 1 if bate else 0
        no_campo = concorda_no_campo(gab.get("campo_errado"), parecer)
        if no_campo is not None:
            campos_total += 1
            campos_ok += 1 if no_campo else 0
        if not bate or no_campo is False:
            discordancias.append({
                "servico_id": gab.get("servico_id"),
                "insurer_key": gab.get("insurer_key"),
                "servico": gab.get("servico"),
                "pagina": gab.get("pagina_conferida"),
                "leitor": gab.get("veredito"),
                "campo_do_leitor": gab.get("campo_errado"),
                "conferente": parecer.veredito,
                "campos": parecer.campos,
                "motivos": parecer.motivos,
            })
    total = len(pares)
    return {
        "linhas": total,
        "linhas_concordantes": linhas_ok,
        "concordancia_de_linha": (linhas_ok / total) if total else 0.0,
        "campos_comparaveis": campos_total,
        "campos_concordantes": campos_ok,
        "concordancia_de_campo": (campos_ok / campos_total) if campos_total else 0.0,
        "discordancias": discordancias,
    }
