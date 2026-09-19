# -*- coding: utf-8 -*-
"""Publica EM LOTE as linhas da base de planos que um leitor já conferiu.

SPEC-EXTRA-001.5.1 · unidade B (D6) · emenda E2. Rodar de dentro de `backend/`:

```
# em seco (o padrão): nada é escrito, e o relatório diz o que ACONTECERIA
PYTHONIOENCODING=utf-8 python scripts/publicar_linhas_da_base.py

# para valer: exige o revisor, que é a pessoa que responde pelas linhas
PYTHONIOENCODING=utf-8 python scripts/publicar_linhas_da_base.py \\
    --conferidas ../docs/canon/reports/SPEC-EXTRA-001.5-LINHAS-CONFERIDAS.json \\
    --revisor <uuid do usuário> --aplicar
```

🔴 POR QUE ESTE SCRIPT EXISTE
=============================
📊 19/09/2026 a base tinha **73 serviços e 33 planos em `proposto` e ZERO
publicado**: 73 linhas = 73 cliques na tela, 60 por vez. Enquanto ninguém
clicasse, o assistente respondia *"ainda não sei"* a tudo — com o trabalho
inteiro já feito e guardado.

⛔ **E ele não é um segundo publicador** (CLAUDE.md §5). Quem publica continua
sendo `assistance_plans_base.publicar_servico`, que é quem sabe que só se sobe a
partir de `proposto`, que o plano pai vai junto e que republicar trocaria quem
revisou. Este arquivo lê um JSON, filtra, CHAMA e conta.

🔴 O SECO É O PADRÃO, E O REVISOR É OBRIGATÓRIO
===============================================
```
sem argumento nenhum   ->  ensaio: nada é escrito
--aplicar sem --revisor ->  RECUSA, antes de tocar no banco
--aplicar --revisor X   ->  publica, e X fica gravado em `revisado_por`
```
`revisado_por` é a única resposta à pergunta *"quem respondeu por 'guincho até
200 km'?"*. Um lote que publicasse sem essa resposta tiraria da base a
propriedade que ela existe para ter.

🔴 O QUE ELE FAZ COM CADA VEREDITO DO LEITOR
============================================
```
PUBLICAR       publica (e o plano pai junto), SE a linha ainda estiver `proposto`
RECUSAR        desce para `rascunho` COM o motivo do leitor, SE ainda `proposto`
CORRIGIR       ⛔ NÃO corrige sozinho. Lista para a próxima rodada
NAO_CONSEGUI   ⛔ não toca. É "não consegui olhar", nunca "está errado"
```
⚠️ **`CORRIGIR` não vira correção automática de propósito.** Corrigir é mudar o
que a base AFIRMA (um limite, uma unidade, uma condição); fazê-lo a partir de um
campo de texto de um relatório, sem ninguém olhar, é publicar o palpite do
leitor com a autoridade de uma revisão humana.

## O arquivo de conferência

```json
{"revisor_sugerido": "<uuid>",
 "linhas": [{"servico_id": "...", "plano_id": "...", "veredito": "PUBLICAR",
             "campo_errado": null, "valor_certo": null, "motivo": "..."}]}
```

⚠️ **Em produção (console do EasyPanel) o arquivo não está na imagem** — `docs/`
não entra nela. Dois caminhos, e os dois estão implementados:

```
copiar o JSON para dentro do contêiner e apontar --conferidas para ele
--conferidas -    lê o JSON da ENTRADA PADRÃO (cat arquivo | python scripts/...)
```

🔴 **E `--ids` é FILTRO, nunca fonte de veredito** — decisão com nota
(protocolo §9):
```
--ids filtra a lista conferida .......... 88   escolhido
--ids publica os ids passados ........... 45   publicar sem conferência é
    exatamente o que a coluna `curadoria` existe para impedir; e o id chega
    pela mão de quem digita, que é onde o engano mora
```

⛔ Nada de PII: este script imprime seguradora, ramo, serviço, estado e
contagem. Nunca CPF, telefone, placa, apólice ou nome de pessoa — nem o do
revisor, de quem só o uuid aparece.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

#: Onde o leitor read-only deixa a conferência das linhas (fora da imagem).
CONFERIDAS_PADRAO = os.path.normpath(os.path.join(
    RAIZ, "..", "docs", "canon", "reports",
    "SPEC-EXTRA-001.5-LINHAS-CONFERIDAS.json"))

VEREDITOS = ("PUBLICAR", "CORRIGIR", "RECUSAR", "NAO_CONSEGUI")


class ConferenciaInvalida(Exception):
    """O arquivo do leitor não tem a forma combinada. ⛔ Não se adivinha."""


def carregar_conferidas(caminho: str) -> Dict[str, Any]:
    """Lê o JSON do leitor. `-` lê da entrada padrão.

    🔴 Um arquivo sem `linhas` é RECUSADO, nunca tratado como lista vazia: uma
    lista vazia faz o script imprimir "nada a fazer" e sair com sucesso — e
    quem rodou vai embora achando que conferiu 81 linhas e não havia nenhuma
    para publicar.
    """
    if caminho == "-":
        bruto = json.loads(sys.stdin.read() or "{}")
    else:
        if not os.path.isfile(caminho):
            raise ConferenciaInvalida(
                "o arquivo de conferência não existe: %s\n"
                "   Em produção ele não está na imagem (`docs/` não entra no "
                "`COPY . .`): copie-o para dentro do contêiner, ou use "
                "`--conferidas -` e mande o JSON pela entrada padrão." % caminho)
        with open(caminho, "r", encoding="utf-8") as fh:
            bruto = json.load(fh)
    if not isinstance(bruto, dict) or not isinstance(bruto.get("linhas"), list):
        raise ConferenciaInvalida(
            "o arquivo %r não tem a chave `linhas` com uma lista — é o formato "
            "do leitor read-only? (chaves vistas: %s)"
            % (caminho, sorted(bruto.keys()) if isinstance(bruto, dict) else type(bruto).__name__))
    if not bruto["linhas"]:
        raise ConferenciaInvalida(
            "o arquivo %r tem `linhas: []`. Um lote de zero linhas não é um "
            "lote: ou a conferência não rodou, ou o caminho está errado." % caminho)
    return bruto


def _chave_do_relatorio(plano: Dict[str, Any]) -> Tuple[str, str]:
    return (str(plano.get("insurer_key") or "?"), str(plano.get("ramo") or "?"))


def executar(
    conferidas: Dict[str, Any],
    *,
    revisor: Optional[str] = None,
    aplicar: bool = False,
    seguradora: Optional[str] = None,
    ramo: Optional[str] = None,
    ids: Optional[List[str]] = None,
    db: Any = None,
) -> Dict[str, Any]:
    """O lote inteiro. Devolve o relatório; **não imprime nada**.

    ⚠️ Separado de `main` de propósito: é isto que o guarda roda contra o duplo
    em memória, e um guarda que tivesse de ler `stdout` para saber o que
    aconteceu estaria medindo o texto, não o efeito.
    """
    from app.services.knowledge import assistance_plans_base as BASE

    if aplicar and not str(revisor or "").strip():
        # 🔴 Antes de qualquer consulta: o erro é do COMANDO, e descobri-lo
        # depois de ler o banco convida a "já que estamos aqui".
        raise BASE.RevisorObrigatorio(
            "publicar em lote sem `--revisor` é publicar sem ninguém por trás: "
            "`revisado_por` é a resposta a \"quem respondeu por esta linha?\"")

    cliente = BASE._db(db)
    alvo_ids = {str(i).strip() for i in (ids or []) if str(i).strip()}

    relatorio: Dict[str, Any] = {
        "aplicar": bool(aplicar),
        "revisor": str(revisor or "") or None,
        "por_seguradora_ramo": {},
        "publicadas": 0, "derrubadas": 0, "puladas": 0,
        "para_corrigir": [], "pulos": {}, "erros": [],
        "verify": {},
    }

    def _contar(chave: Tuple[str, str], campo: str) -> None:
        linha = relatorio["por_seguradora_ramo"].setdefault(
            "%s · %s" % chave,
            {"publicadas": 0, "derrubadas": 0, "puladas": 0})
        linha[campo] += 1

    def _pular(motivo: str, chave: Optional[Tuple[str, str]] = None) -> None:
        relatorio["puladas"] += 1
        relatorio["pulos"][motivo] = relatorio["pulos"].get(motivo, 0) + 1
        if chave:
            _contar(chave, "puladas")

    for item in conferidas.get("linhas") or []:
        if not isinstance(item, dict):
            _pular("linha_ilegivel")
            continue
        servico_id = str(item.get("servico_id") or "").strip()
        veredito = str(item.get("veredito") or "").strip().upper()
        if not servico_id:
            _pular("sem_servico_id")
            continue
        if alvo_ids and servico_id not in alvo_ids:
            _pular("fora_do_--ids")
            continue
        if veredito not in VEREDITOS:
            _pular("veredito_desconhecido:%s" % (veredito or "vazio"))
            continue

        atual = (
            cliente.table(BASE.TABELA_SERVICOS)
            .select("id, servico, plano_id, curadoria")
            .eq("id", servico_id).limit(1).execute()
        ).data or []
        if not atual:
            _pular("linha_nao_existe_mais")
            continue
        linha = atual[0]
        plano = ((
            cliente.table(BASE.TABELA_PLANOS)
            .select("id, insurer_key, ramo, produto, plano, curadoria")
            .eq("id", str(linha.get("plano_id"))).limit(1).execute()
        ).data or [{}])[0]
        chave = _chave_do_relatorio(plano)

        if seguradora and str(plano.get("insurer_key") or "") != str(seguradora):
            _pular("fora_do_--seguradora")
            continue
        if ramo and str(plano.get("ramo") or "") != str(ramo):
            _pular("fora_do_--ramo")
            continue

        estado = str(linha.get("curadoria") or "")

        if veredito == "CORRIGIR":
            # ⛔ Listado, nunca aplicado. Ver o cabeçalho.
            relatorio["para_corrigir"].append({
                "servico_id": servico_id,
                "seguradora_ramo": "%s · %s" % chave,
                "servico": str(linha.get("servico") or ""),
                "campo_errado": str(item.get("campo_errado") or "")[:60],
                "valor_certo": str(item.get("valor_certo") or "")[:120],
            })
            _pular("veredito_CORRIGIR", chave)
            continue
        if veredito == "NAO_CONSEGUI":
            _pular("veredito_NAO_CONSEGUI", chave)
            continue

        if estado != "proposto":
            # 🔴 A IDEMPOTÊNCIA MORA AQUI. Segunda rodada: tudo já está no
            # estado final, e o relatório diz "nada a fazer" em vez de tentar
            # de novo e colecionar exceções.
            _pular("ja_em_%s" % (estado or "desconhecido"), chave)
            continue

        if veredito == "PUBLICAR":
            # 🔴 O plano pai precisa estar em `proposto`: `publicar_servico` só
            # o sobe a partir dali, e publicar a linha sem o plano é o pior
            # desfecho — o trabalho é feito e o segurado continua sem resposta.
            if str(plano.get("curadoria") or "") != "proposto":
                _pular("plano_pai_%s" % (plano.get("curadoria") or "ausente"), chave)
                continue
            if not aplicar:
                relatorio["publicadas"] += 1
                _contar(chave, "publicadas")
                continue
            try:
                BASE.publicar_servico(servico_id, revisor, db=cliente)
                relatorio["publicadas"] += 1
                _contar(chave, "publicadas")
            except BASE.BaseDePlanosRecusa as exc:
                relatorio["erros"].append({"servico_id": servico_id,
                                           "erro": str(exc)[:160]})
                _pular("recusado_pelo_modulo", chave)
            continue

        # veredito == "RECUSAR"
        motivo = str(item.get("motivo") or item.get("campo_errado") or "").strip()
        if not motivo:
            # ⚠️ `para_rascunho` recusa motivo vazio, e está certo: uma linha
            # derrubada sem motivo não ensina nada a quem for reextraí-la.
            _pular("recusar_sem_motivo", chave)
            continue
        if not aplicar:
            relatorio["derrubadas"] += 1
            _contar(chave, "derrubadas")
            continue
        try:
            BASE.para_rascunho(servico_id, "conferência do leitor: %s" % motivo[:200],
                               db=cliente)
            relatorio["derrubadas"] += 1
            _contar(chave, "derrubadas")
        except BASE.BaseDePlanosRecusa as exc:
            relatorio["erros"].append({"servico_id": servico_id, "erro": str(exc)[:160]})
            _pular("recusado_pelo_modulo", chave)

    relatorio["verify"] = _verify(cliente, BASE)
    return relatorio


def _verify(cliente: Any, BASE: Any) -> Dict[str, Any]:
    """O estado do banco DEPOIS — e a trava que não pode ter sido furada.

    🔴 `publicado_sem_revisor` tem de ser **0**. Ele é o VERIFY que importa: o
    banco já tem o CHECK `servico_publicado_foi_revisado`, e esta contagem prova
    que o lote não encontrou nenhum caminho por fora dele.
    """
    fora: Dict[str, Any] = {"planos": {}, "servicos": {}, "publicado_sem_revisor": 0}
    for tabela, destino in ((BASE.TABELA_PLANOS, "planos"),
                            (BASE.TABELA_SERVICOS, "servicos")):
        for estado in BASE.CURADORIAS:
            r = (cliente.table(tabela).select("id", count="exact")
                 .eq("curadoria", estado).execute())
            n = getattr(r, "count", None)
            n = int(n) if n is not None else len(getattr(r, "data", None) or [])
            if n:
                fora[destino][estado] = n
    for tabela in (BASE.TABELA_PLANOS, BASE.TABELA_SERVICOS):
        linhas = (cliente.table(tabela).select("id, revisado_por")
                  .eq("curadoria", "publicado").execute()).data or []
        fora["publicado_sem_revisor"] += sum(
            1 for l in linhas if not str(l.get("revisado_por") or "").strip())
    return fora


def imprimir(relatorio: Dict[str, Any]) -> None:
    """O relatório, em texto. ⛔ Sem PII: seguradora, ramo, serviço e contagem."""
    print("=" * 78)
    print("📊 PUBLICAÇÃO EM LOTE DA BASE DE PLANOS — modo: %s"
          % ("APLICAR (grava)" if relatorio["aplicar"] else "ensaio (nada é escrito)"))
    print("=" * 78)
    print("  revisor: %s" % (relatorio["revisor"] or "— (ensaio)"))
    print()
    print("  %-34s %10s %10s %10s" % ("seguradora · ramo", "publica", "derruba", "pula"))
    print("  " + "-" * 66)
    for chave in sorted(relatorio["por_seguradora_ramo"]):
        n = relatorio["por_seguradora_ramo"][chave]
        print("  %-34s %10s %10s %10s"
              % (chave[:34], n["publicadas"], n["derrubadas"], n["puladas"]))
    print("  " + "-" * 66)
    print("  %-34s %10s %10s %10s" % ("TOTAL", relatorio["publicadas"],
                                      relatorio["derrubadas"], relatorio["puladas"]))

    if relatorio["pulos"]:
        print("\n  por que pulou:")
        for motivo in sorted(relatorio["pulos"]):
            print("    %-40s %s" % (motivo, relatorio["pulos"][motivo]))

    if relatorio["para_corrigir"]:
        print("\n  ⚠️ para a PRÓXIMA rodada (o leitor pediu CORRIGIR — este script "
              "não corrige sozinho):")
        for c in relatorio["para_corrigir"][:40]:
            print("    %s · %s · %s -> %s"
                  % (c["seguradora_ramo"], c["servico"], c["campo_errado"] or "?",
                     c["valor_certo"] or "?"))
        if len(relatorio["para_corrigir"]) > 40:
            print("    … e mais %s" % (len(relatorio["para_corrigir"]) - 40))

    if relatorio["erros"]:
        print("\n  ⛔ recusadas pelo módulo (o motivo é dele, não deste script):")
        for e in relatorio["erros"][:20]:
            print("    %s: %s" % (e["servico_id"], e["erro"]))

    v = relatorio["verify"]
    print("\n  VERIFY (estado do banco agora)")
    print("    planos:   %s" % (v.get("planos") or {}))
    print("    servicos: %s" % (v.get("servicos") or {}))
    print("    🔴 publicado sem revisor: %s   (tem de ser 0)"
          % v.get("publicado_sem_revisor"))
    if not relatorio["publicadas"] and not relatorio["derrubadas"]:
        print("\n  ✅ nada a fazer — o lote já está no estado final.")
    print("=" * 78)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="publicar_linhas_da_base.py",
        description="Publica em lote as linhas da base de planos que um leitor "
                    "já conferiu contra a página do documento.",
        epilog="⚠️ PRODUÇÃO (console do EasyPanel): `docs/` não entra na imagem, "
               "então o arquivo de conferência NÃO está lá. Copie-o para dentro "
               "do contêiner e aponte --conferidas para ele, ou mande o JSON "
               "pela entrada padrão com `--conferidas -`. "
               "🔴 --ids é FILTRO sobre a lista conferida, nunca fonte de "
               "veredito: publicar um id que ninguém conferiu é o que a coluna "
               "`curadoria` existe para impedir.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--conferidas", default=CONFERIDAS_PADRAO,
                   help="JSON do leitor (padrão: %(default)s). `-` lê da entrada padrão.")
    p.add_argument("--revisor", default="",
                   help="uuid do usuário que responde pelas linhas. OBRIGATÓRIO com --aplicar.")
    p.add_argument("--seguradora", default="", help="só as linhas desta `insurer_key`.")
    p.add_argument("--ramo", default="", help="só as linhas deste ramo.")
    p.add_argument("--ids", default="",
                   help="filtra por `servico_id` (separados por vírgula).")
    p.add_argument("--dry-run", action="store_true",
                   help="o padrão. Nada é escrito (mantido para quem escreve o comando inteiro).")
    p.add_argument("--aplicar", action="store_true",
                   help="grava de verdade. Sem --revisor, recusa antes de tocar no banco.")
    args = p.parse_args(argv)

    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(RAIZ, ".env"))
    except Exception:  # noqa: BLE001
        pass

    try:
        conferidas = carregar_conferidas(args.conferidas)
    except ConferenciaInvalida as exc:
        print("⛔ %s" % exc)
        return 2
    except Exception as exc:  # noqa: BLE001
        print("⛔ não consegui ler %r: %s" % (args.conferidas, type(exc).__name__))
        return 2

    # 🔴 SPEC-EXTRA-001.5.1 · CONSERTO P1 — O FALLBACK CONTRADIZIA O `--help`.
    #
    # A docstring e o `--help` dizem, nestas palavras: *"--aplicar sem --revisor
    # -> RECUSA, antes de tocar no banco"*. E a linha era
    # `args.revisor or conferidas["revisor_sugerido"]`: um uuid que veio DENTRO
    # DO ARQUIVO de conferência publicava 81 linhas em nome de alguém que não
    # digitou nada. 📊 Quem responde por "guincho até 200 km" tem de ter
    # ESCRITO o próprio id na linha de comando.
    #
    # ⚠️ `revisor_sugerido` continua no JSON e continua útil: ele é a SUGESTÃO
    # que o operador copia. O que ele deixou de ser é o valor PADRÃO.
    revisor = args.revisor.strip()
    if args.aplicar and not revisor:
        sugerido = str(conferidas.get("revisor_sugerido") or "").strip()
        print("⛔ --aplicar exige --revisor <uuid>. Nada foi tocado no banco.")
        if sugerido:
            print("   O arquivo de conferência SUGERE %s — copie-o para o comando "
                  "se for você quem responde por estas linhas." % sugerido)
        return 2
    try:
        relatorio = executar(
            conferidas,
            revisor=revisor,
            aplicar=bool(args.aplicar),
            seguradora=args.seguradora.strip() or None,
            ramo=args.ramo.strip() or None,
            ids=[i for i in args.ids.split(",")] if args.ids.strip() else None,
        )
    except Exception as exc:  # noqa: BLE001 — RevisorObrigatorio inclusive
        print("⛔ %s" % str(exc)[:400])
        return 2

    imprimir(relatorio)
    if relatorio["verify"].get("publicado_sem_revisor"):
        print("⛔ VERIFY REPROVOU: há linha publicada sem revisor.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
