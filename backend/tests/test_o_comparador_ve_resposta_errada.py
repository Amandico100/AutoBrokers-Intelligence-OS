# -*- coding: utf-8 -*-
"""🔴 O GUARDA QUE PROVA QUE O GUARDA ENXERGA — P-084-14.

> ## Um guarda que não tem como ficar vermelho não guarda nada.

O `--comparar-com` contava CASAMENTOS. Os sete defeitos do BLOCO 1 casavam a
tela — todos os sete — e por isso nenhum apareceu como perda. O comparador
ficou cego exatamente onde o dano mora.

`conferir_respostas.py` acrescentou três perguntas. **Este arquivo prova que as
três funcionam, reintroduzindo defeitos HISTÓRICOS de verdade** — não defeitos
inventados que casam a regra por construção.

```
A  idade_de_fabricacao perde a origem do slot E o fallback  -> passo CALADO
B  menu_qual_seguro_tres_opcoes volta a responder "1"       -> decide pelo cliente
C  o_que_aconteceu volta a ter ancora seca                  -> tela do outro oficio
```

🔴 **E a restauração NUNCA é `git checkout`.** A memória desta pasta diz por quê:
`git checkout` apaga trabalho não commitado, e `git diff --quiet` mente sobre
arquivo que ele nem rastreia. Aqui é cópia byte a byte, e a volta é conferida
por **hash**.
"""

from __future__ import annotations

import hashlib
import importlib
import io
import os
import shutil
import sys
import tempfile
from typing import Callable, List, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

ALVO_PB = os.path.join(RAIZ, "app", "services", "corridor_playbooks.py")

_verdes: List[str] = []
_vermelhas: List[str] = []


def check(nome: str, ok: bool, detalhe: object = "") -> None:
    if ok:
        _verdes.append(nome)
        print(f"  [ok] {nome}")
    else:
        _vermelhas.append(nome)
        print(f"  [FALHOU] {nome}  {detalhe}")


def _hash(caminho: str) -> str:
    with open(caminho, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _achados_agora() -> list:
    """Roda a conferência com o corredor RECARREGADO do disco."""
    for nome in list(sys.modules):
        if nome.startswith("app.services.corridor_playbooks") or nome in (
                "conferir_respostas", "regua_motor", "replay"):
            del sys.modules[nome]
    import regua_motor  # noqa: F401
    import conferir_respostas as CR
    importlib.reload(CR)
    return CR.conferir_tudo()


# ═════════════════════════════════════════════════════════════════════════════
# AS TRÊS MUTAÇÕES — cada uma um defeito que ESTEVE NO AR
# ═════════════════════════════════════════════════════════════════════════════
def _mut_b(fonte: str) -> str:
    """🔴 O DEFEITO Nº 3: todo condomínio ia para a apólice residencial.

    📊 `menu_qual_seguro` respondia "1" a um menu de TRÊS opções onde 2 é
    Condomínio, e 5 sessões de condomínio existem no acervo. Não travava:
    acertava a tecla e abria o chamado que seria recusado no local.

    ═══════════════════════════════════════════════════════════════════════════
    🔴 A MUTAÇÃO PASSOU A DIZER **ONDE** — 28/09/2026, e por medição
    ═══════════════════════════════════════════════════════════════════════════

    Ela trocava a PRIMEIRA ocorrência de `"reply": "{qual_seguro_opcao}"` no
    arquivo. 📊 O conserto B da SPEC-119 fez `menu_solicitar_para` — a SEGUNDA
    tela de três opções, que respondia `"1"` e abria condomínio na apólice da
    unidade — passar a usar o mesmo slot, e ela mora ANTES no arquivo. A partir
    daí a mutação mutava o passo ERRADO, o achado saía em `menu_solicitar_para`,
    o detector exigia `"qual_seguro" in a.passo` e **o guarda ficava VERDE**.

    ⚠️ É o terceiro verde-por-detalhe-de-mutação desta família (CLAUDE.md §9.5:
    *"ficou verde por engano duas vezes, as duas por detalhe de mutação, não de
    regra"*). A cura é a mesma de `_mut_a`: a mutação diz ONDE.
    """
    # 🔴 Ancorada na ÂNCORA do passo, que é única no arquivo — não na posição.
    velho = ('r"\\*?1\\s*-\\s*resid[êe]ncial",\n'
             '            "reply": "{qual_seguro_opcao}",\n'
             '            "requires": ["qual_seguro_opcao"],')
    novo = ('r"\\*?1\\s*-\\s*resid[êe]ncial",\n'
            '            "reply": "1",\n'
            '            "requires": [],')
    if velho not in fonte:
        raise AssertionError(
            "🔴 a mutação B não achou `menu_qual_seguro_tres_opcoes` pela âncora "
            "dele. Ela NÃO pode cair no `replace` da primeira ocorrência: foi "
            "assim que este guarda ficou verde por engano em 28/09/2026")
    return fonte.replace(velho, novo, 1)


def _mut_c(fonte: str) -> str:
    """🔴 O DEFEITO Nº 1: a mesma pergunta, três ofícios, três listas.

    📊 A âncora era `o que aconteceu\\?`, seca. O passo do ELETRICISTA respondia
    a tecla do problema elétrico na tela do ENCANADOR e na do CHAVEIRO.
    """
    velho = r'"anchor": r"o que aconteceu\?[\s\S]{0,60}casa inteira ou parcial sem energia",'
    novo = r'"anchor": r"o que aconteceu\?",'
    return fonte.replace(velho, novo, 1)


def _mut_a(fonte: str) -> str:
    """🔴 O DEFEITO DO GUARDA ANTERIOR: slot sem origem = passo CALADO.

    📊 2min22 de silêncio medidos em 19/08/2026, até o Founder clicar "1" do
    próprio celular.
    """
    # ⚠️ TODAS as ocorrencias, nao a primeira: `origens_do_slot` usa `any()`
    #    sobre os subservicos, entao basta UM declarar para o slot ter origem.
    #    📊 Em 22/08 o BLOCO 4 declarou `ar_condicionado` com o MESMO slot, a
    #    mutacao passou a remover so metade, e este guarda ficou VERDE por
    #    engano -- provando de novo que mutacao sem controle nao guarda nada.
    # ⚠️ A ORDEM IMPORTA, e ela ja me enganou uma vez: tirar o SLOT primeiro
    #    fazia a terceira troca nao achar mais o texto, o `fallback_adaptive`
    #    ficava, e o achado saia AMARELO em vez de vermelho. O guarda passava
    #    a mentir sobre si mesmo.
    #    Primeiro o fallback (para o passo poder ficar CALADO), depois o slot.
    fonte = fonte.replace('''            "reply": "{idade_aparelho_opcao}",
            "requires": ["idade_aparelho_opcao"],
            "fallback_adaptive": True,''',
                          '''            "reply": "{idade_aparelho_opcao}",
            "requires": ["idade_aparelho_opcao"],''', 1)
    # ⚠️ TODAS as ocorrencias: `origens_do_slot` usa `any()` sobre os
    #    subservicos, entao basta UM declarar para o slot ter origem.
    #    📊 Em 22/08 o BLOCO 4 declarou `ar_condicionado` com o MESMO slot, a
    #    mutacao removia so metade, e este guarda ficou VERDE por engano.
    # 🔴 E A MUTACAO CEGA POR SER LARGA DEMAIS -- terceira licao do mesmo
    #    bloco. 📊 Em 22/08 `_COMO_PERGUNTAR` ganhou a chave
    #    `"idade_aparelho_opcao": "a idade do aparelho..."`, e o replace geral
    #    arrancava a CHAVE, deixando `: "texto"` solto:
    #        SyntaxError: invalid syntax, corridor_playbooks.py:7053
    #    O guarda nao ficava vermelho -- ele DERRUBAVA o import, e o proximo
    #    leitor veria um traceback em vez de um defeito.
    #
    #    ⚠️ Mutacao por string crua ganha ponto cego a cada linha nova do
    #    arquivo. A cura e a mutacao dizer ONDE: aqui, so onde o slot e
    #    DECLARADO numa lista -- nunca onde ele e CHAVE de dicionario, que a
    #    lookahead `(?!\s*:)` exclui.
    import re as _re
    return _re.sub(r'"idade_aparelho_opcao",?(?!\s*:)', '', fonte)


MUTACOES: List[Tuple[str, str, Callable[[str], str], Callable[[list], bool]]] = [
    ("B", "menu de 3 opcoes volta a responder '1' (condominio -> residencial)",
     "B", _mut_b,
     lambda ach: any(a.regra == "B" and a.grave and "ALTERNATIVAS DE CONTEUDO" in a.porque
                     and a.passo == "menu_qual_seguro_tres_opcoes" for a in ach)),
    # 🔴 O NOME DO PASSO POR IGUALDADE, NUNCA POR SUBSTRING — 28/09/2026.
    #    📊 `"o_que_aconteceu" in a.passo` casa TAMBEM `chave_o_que_aconteceu`, um
    #    passo da yelum que a SPEC-119 acusa de verdade (2 achados C graves, no
    #    acervo de hoje). Com a substring, o CONTROLE NEGATIVO desta linha ficava
    #    vermelho sem que o defeito historico estivesse presente — medido tanto
    #    no HEAD de hoje quanto em `e76cb28`, ANTES do conserto B, o que prova
    #    que a colisao nao veio do conserto e sim do nome parecido.
    ("C", "o_que_aconteceu volta a ter ancora seca (tela do outro oficio)",
     "C", _mut_c,
     lambda ach: any(a.regra == "C" and a.grave and a.passo == "o_que_aconteceu"
                     for a in ach)),
    ("A", "idade_de_fabricacao perde origem E fallback (passo CALADO)",
     "A", _mut_a,
     lambda ach: any(a.regra == "A" and a.grave and "idade_aparelho_opcao" in a.porque
                     for a in ach)),
]


def main() -> int:
    print("=" * 74)
    print("[1] A linha de CONTROLE: o guarda ja roda, e o estado de HOJE e conhecido")
    print("=" * 74)
    base = _achados_agora()
    n_base = len(base)
    print(f"  achados no estado atual: {n_base}")
    check("CONTROLE: a conferencia roda e devolve algo mensuravel", n_base >= 0, n_base)

    # 🔴 A LINHA QUE DA DIREITO A CONCLUSAO: nenhum dos tres defeitos historicos
    #    esta presente AGORA. Sem isto, um teste que "passa" pode estar so
    #    reencontrando o que ja estava la.
    for _, _, regra, _, detector in MUTACOES:
        check(f"CONTROLE NEGATIVO [{regra}]: o defeito NAO esta presente hoje",
              not detector(base))

    print()
    print("=" * 74)
    print("[2] Cada regra fica VERMELHA com o defeito historico reintroduzido")
    print("=" * 74)

    hash_antes = _hash(ALVO_PB)
    with tempfile.TemporaryDirectory() as tmp:
        copia = os.path.join(tmp, "corridor_playbooks.py.bak")
        # 🔴 COPIA, nunca `git checkout` -- ver o cabecalho deste arquivo.
        shutil.copy2(ALVO_PB, copia)

        for nome, descricao, regra, mutar, detector in MUTACOES:
            fonte = io.open(ALVO_PB, encoding="utf-8").read()
            mutada = mutar(fonte)
            aplicou = mutada != fonte
            try:
                if aplicou:
                    io.open(ALVO_PB, "w", encoding="utf-8").write(mutada)
                    ach = _achados_agora()
                    ficou_vermelha = detector(ach)
                else:
                    ficou_vermelha = False
            finally:
                shutil.copy2(copia, ALVO_PB)

            check(f"[{regra}] a mutacao APLICOU  ({descricao})", aplicou)
            check(f"[{regra}] o guarda ficou VERMELHO", aplicou and ficou_vermelha,
                  "se ficar verde, a regra continua CEGA")

        restaurado = _hash(ALVO_PB) == hash_antes
        check("o corredor foi RESTAURADO byte a byte (conferido por hash)", restaurado,
              "🔴 NAO commitar se esta linha falhar")

    print()
    print("=" * 74)
    print(f"  {len(_verdes)} assercoes verdes - {len(_vermelhas)} vermelhas")
    print("=" * 74)
    return 1 if _vermelhas else 0


if __name__ == "__main__":
    sys.exit(main())
