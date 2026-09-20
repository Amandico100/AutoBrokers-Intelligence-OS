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

    _conferir_trecho(linha, numero, texto, paginas, campos, motivos)
    _conferir_coberto(linha, texto, campos, motivos)
    _conferir_limite(linha, texto, campos, motivos)
    _conferir_plano(linha, paginas, planos_da_ancora, campos, motivos)
    _conferir_produto(linha, campos, motivos)

    veredito = DIVERGE if DIVERGE_CAMPO in campos.values() else CONFERE
    return Veredito(veredito, campos, motivos, numero)


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


def _conferir_coberto(linha, texto, campos, motivos) -> None:
    """O `coberto` é do SERVIÇO, ou foi colhido da cláusula de outra cobertura?"""
    coberto = str(linha.get("coberto") or "")
    servico = str(linha.get("servico") or "")
    trecho = str(linha.get("trecho") or "").strip()
    base = trecho if len(trecho) >= 12 else texto
    leitura = _para_leitura(base)
    if not coberto:
        return
    campos["coberto"] = OK

    # 1 · o "não" que é exclusão de risco DENTRO de outra cobertura (padrão 1).
    #     Os regexes são os do verificador de escrita: um parecer só por frase.
    if coberto == "nao" and _E_EXCLUSAO_DE_RISCO.search(base) \
            and not _NEGA_O_SERVICO.search(base):
        campos["coberto"] = DIVERGE_CAMPO
        motivos.append("o 'nao' veio de uma cláusula de exclusão de risco, "
                       "não de uma recusa do serviço")

    # 2 · o "sim" numa cobertura que só existe se contratada.
    if coberto == "sim" and _E_OPCIONAL.search(leitura):
        campos["coberto"] = DIVERGE_CAMPO
        motivos.append("a página trata de cobertura adicional/opcional: "
                       "'sim' promete o que só existe se o cliente contratou")

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
    for numero in _numeros_de(limite_texto) or _numeros_de(valor):
        if not _numero_esta_na_pagina(numero, leitura_pagina):
            campos["limite"] = DIVERGE_CAMPO
            motivos.append("o número %s do limite não está na página %s"
                           % (numero, linha.get("pagina")))
            break


def _conferir_plano(linha, paginas, planos_da_ancora, campos, motivos) -> None:
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
        if _para_leitura(plano) in conhecidos:
            campos["plano"] = OK
        else:
            campos["plano"] = DIVERGE_CAMPO
            motivos.append("o plano %r não está entre os que a cláusula de "
                           "planos enumera (%s)"
                           % (plano, ", ".join(sorted(planos_da_ancora))[:120]))
        return

    if _para_leitura(plano) == _para_leitura(_PLANO_PADRAO):
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
