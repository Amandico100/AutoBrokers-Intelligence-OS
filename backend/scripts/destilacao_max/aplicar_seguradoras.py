"""Grava o que o destilador tirou das conversas com a URA da SEGURADORA.

Por que este script existe, e não o `aplicar.py`
-----------------------------------------------
`aplicar.py` escreve `summary.distilled` em **`attendance_sessions`** — a
corretora falando com o segurado. Este acervo mora em **`observed_sessions`**:
a corretora falando com o robô da Porto, da Allianz, da Yelum. Aplicar com o
outro marcaria a sessão errada, ou nenhuma, e as 319 conversas voltariam à fila
para sempre.

O que ele NÃO reescreve
-----------------------
As regras de gravação são as do `aplicar.py`, importadas: md5 do texto em
minúsculas, 15 a 400 caracteres, `rejected_pii` quando o `templatize` mudaria o
texto, o assunto por `curadoria_cartas.assunto_da_carta`, o teto de 8 fatos e o
formato de `summary.distilled`. A credencial vem de `exportar._credenciais`; o
formato do uuid vem de `validar.UUID`. Um segundo motor de gravação divergiria
do primeiro no dia em que um dos dois fosse corrigido (CLAUDE.md §5).

A ÚNICA coisa que muda é de quem é a regra — e a razão está medida
-----------------------------------------------------------------
`aplicar.py` trata a seguradora da sessão como **candidata** e re-decide fato a
fato: 📊 05/08/2026, das 3.354 cartas etiquetadas do acervo de atendimento, só
1.083 (32,3%) citavam a própria seguradora. Lá o campo guardava "este fato
apareceu numa conversa sobre a Allianz" e o nome prometia "este fato é regra da
Allianz". 2.582 rótulos foram rebaixados por isso.

Aqui a evidência é outra: **a conversa É com a seguradora.**
`observed_sessions.insurer_key` não é palpite sobre o assunto — é de quem é a
URA do outro lado da linha. Exigir que o texto a nomeie jogaria fora a única
coisa que este acervo tem de melhor que o outro.

📊 Medido em 06/08/2026 sobre os 918 fatos dos 18 lotes destilados até então,
passando `curadoria_cartas.texto_nomeia_seguradora` sobre as chaves de
`_INSURER_ALIASES` (script em `scratchpad/medir_rotulo.py`):

    915 de 918 (99,7%)  nomeiam a própria seguradora da sessão
      0 de 918          nomeiam SÓ outra companhia
     12 de 918          nomeiam a própria E outra
      3 de 918          não nomeiam companhia nenhuma

    contra 32,3% no acervo de atendimento — a mesma medida, a outra evidência

E os 3 que não nomeiam ninguém são a diferença inteira, em texto:

    "A cor do veículo é exigida também em serviços que não são guincho, como
     bateria nova, e vem antes da data e do endereço."           (sessão porto)

Isso é conhecimento real sobre a Porto. `seguradora_do_fato` devolve `None`
para ele — e devolveria certo, se a evidência fosse a do outro acervo. Aqui a
conversa É com a Porto, e jogar o dono fora seria perder o que só este acervo
tem.

A EXCEÇÃO, e por que ela é resolvida assim
------------------------------------------
Existe uma conversa real com a **Porto** em que a URA responde *"não localizei
suas informações na Porto, mas identifiquei que você é cliente Azul Seguros"* e
redireciona. Um fato tirado dali pode ser sobre a **Azul**, não sobre a Porto.
Aceitar o rótulo da sessão às cegas recriaria, num acervo novo, exatamente o
defeito que acabou de ser consertado no antigo.

A regra é a mais estreita que resolve o caso, e ela tem TRÊS ramos:

| o fato...                          | fica com | por quê |
|---|---|---|
| não nomeia companhia nenhuma       | a da sessão | é a vantagem do acervo: a conversa é com ela |
| nomeia a da sessão (com ou sem outra) | a da sessão | ela é a que AGE na frase; a outra é o objeto |
| nomeia só OUTRA companhia          | **ninguém** | o sujeito da frase não é quem estava na linha |

Os 7 fatos que nomeiam duas foram lidos um a um: nos 7 o sujeito é a URA da
sessão (*"a URA da Porto reconhece um CPF que não é de cliente Porto e responde
que identificou o titular como cliente Azul"*). A regra 5 do
`PROMPT-DESTILADOR-SEGURADORA.md` exige justamente isso — escrever o nome da
seguradora dentro da frase. Então o terceiro ramo é, na prática, um detector de
fato que **saiu da regra 5**: se o destilador escreveu sobre a Azul dentro de
uma conversa com a Porto e esqueceu de dizer Porto, o rótulo cai.

**O rebaixamento não apaga nada.** A carta entra como conhecimento genérico e
`pii_check` guarda `seguradora_da_sessao` e `seguradora_citada` — é o mesmo
caminho de recuperação que o P-103 abriu para os 45 rebaixados do outro acervo.
Errar para baixo é recuperável; errar para cima sai errado na frente do cliente.

O `ramo`, e por que ele NÃO vem do banco
----------------------------------------
📊 06/08/2026: `select count(ramo) from observed_sessions` devolve **0 em 551**.
As colunas `ramo` e `servico` da sessão observada existem e **nunca foram
escritas**. Confiar nelas gravaria "outro" em todas as cartas do acervo.

Então: o `ramo` do BANCO vence quando existir (é observado), o do destilado
entra quando o banco estiver vazio (é o que está lá hoje, em 100% dos casos), e
`outro` só quando os dois faltarem. A ordem está escrita para o dia em que
alguém preencher a coluna — não para hoje.

A ordem de escrita, que é o oposto da do `aplicar.py`
----------------------------------------------------
Primeiro as CARTAS, depois a marca da sessão. As cartas são idempotentes
(`upsert on_conflict=card_hash, ignore_duplicates`); a marca é o "não volte
mais". Marcando primeiro, uma falha na gravação das cartas deixa a sessão
declarada destilada e sem conhecimento nenhum — perda silenciosa e permanente.
Nesta ordem, qualquer queda no meio deixa trabalho refazível e nada duplicado.

Uso
---
    python aplicar_seguradoras.py                    # SIMULAÇÃO (só SELECT)
    python aplicar_seguradoras.py --aplicar          # grava de verdade
    python aplicar_seguradoras.py lotes_seguradoras/lote_016.destilado.jsonl

Sem `--aplicar` ele não escreve uma linha. Sem credencial ele não roda —
`exportar._credenciais` sai com código 2 antes de qualquer coisa acontecer.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from exportar import _credenciais            # noqa: E402 — a MESMA porta de credencial
from mascarar import _carregar_servico       # noqa: E402
from validar import UUID                     # noqa: E402 — o MESMO formato de id
# As MESMAS regras de gravação do acervo de atendimento. `_cartas_de` recebe de
# quem é a regra por injeção justamente para que este arquivo não precise
# recopiar hash, teto, faixa de tamanho, portão de PII e assunto.
from aplicar import _cartas_de, _distilled   # noqa: E402

_CURADORIA = _carregar_servico("curadoria_cartas")
# A MESMA pergunta "o texto nomeia esta companhia como dona da regra?" que o
# acervo de atendimento faz. O que muda entre os dois acervos é o que se faz
# com a resposta, não como ela é obtida.
texto_nomeia_seguradora = _CURADORIA.texto_nomeia_seguradora

MARCA = "destilacao_max_seguradoras_06_08_2026"

PADRAO = os.path.join(AQUI, "lotes_seguradoras", "*.destilado.jsonl")


# ------------------------------------------------------------------ #
# DE QUEM É A REGRA — a versão deste acervo, ao lado da do outro
# ------------------------------------------------------------------ #

def _companhias_citadas(texto: str) -> set:
    """Quais seguradoras conhecidas este texto nomeia como donas de algo.

    Varre a tabela única de `corridor_playbooks` — a mesma de onde
    `curadoria_cartas._formas_da_seguradora` tira as grafias. Uma segunda lista
    de "quem é seguradora" aqui envelheceria separada da primeira.
    """
    from app.services.corridor_playbooks import _INSURER_ALIASES

    return {k for k in set(_INSURER_ALIASES.values())
            if texto_nomeia_seguradora(texto, k)}


def _dono_da_sessao_observada(texto: str, observada: str) -> tuple:
    """(insurer_key, marcas) para um fato tirado de conversa COM a seguradora.

    `observada` é `observed_sessions.insurer_key` — de quem é a URA. Não é
    palpite sobre o assunto da conversa; é o outro lado da linha.
    """
    from app.services.corridor_playbooks import _INSURER_ALIASES, normalize_insurer_key

    bruto = str(observada or "").strip().lower()
    if not bruto:
        # 📊 hoje 0 das 551 sessões caem aqui; o dia em que uma cair, ela vira
        # conhecimento genérico em vez de conhecimento de dono desconhecido.
        return None, {"rotulo": "sessao observada sem insurer_key"}

    chave = normalize_insurer_key(bruto, para="conhecimento")
    if chave not in set(_INSURER_ALIASES.values()):
        return None, {"rotulo": "chave fora da tabela de seguradoras",
                      "seguradora_da_sessao": bruto}

    citadas = _companhias_citadas(texto)
    outras = sorted(citadas - {chave})
    if outras and chave not in citadas:
        # O único ramo que rebaixa. Ver a tabela do cabeçalho: o sujeito da
        # frase não é quem estava na linha, então o rótulo da sessão mentiria.
        return None, {"rotulo": "rebaixado: o fato nomeia outra companhia "
                                "e não nomeia a da sessão",
                      "seguradora_da_sessao": chave,
                      "seguradora_citada": outras}

    marcas = {"rotulo": "observado: a conversa e com esta seguradora",
              "acervo": "observed_sessions"}
    if outras:
        # O fato da relação entre duas companhias. Fica com a da sessão, e a
        # outra é registrada — é ela que permite achar estes fatos depois.
        marcas["tambem_cita"] = outras
    return chave, marcas


# ------------------------------------------------------------------ #
# LEITURA — tudo o que este script faz sem `--aplicar`
# ------------------------------------------------------------------ #

def _sessoes_do_banco(db, ids: list) -> dict:
    """{id: linha} de `observed_sessions`. Uma ida ao banco por fatia de 100."""
    achadas: dict = {}
    for i in range(0, len(ids), 100):
        linhas = (db.table("observed_sessions")
                  .select("id, insurer_key, ramo, summary")
                  .in_("id", ids[i:i + 100]).execute().data) or []
        for r in linhas:
            achadas[str(r.get("id"))] = r
    return achadas


def _hashes_ja_no_acervo(db, hashes: list) -> set:
    """Quais destes `card_hash` o acervo já tem. Só para a contagem prevista."""
    ja: set = set()
    for i in range(0, len(hashes), 100):
        linhas = (db.table("knowledge_cards").select("card_hash")
                  .in_("card_hash", hashes[i:i + 100]).execute().data) or []
        ja.update(str(r.get("card_hash")) for r in linhas)
    return ja


def _planejar(db, caminho: str, contas: collections.Counter) -> tuple:
    """(sessões a marcar, cartas a gravar) para um arquivo. Só lê.

    Devolve `[(id, resumo_novo)]` e `{card_hash: linha}` — nada é escrito aqui,
    nem no modo `--aplicar`. Separar o plano da escrita é o que permite simular
    exatamente o que seria feito, em vez de simular uma aproximação dele.
    """
    registros: list = []
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            try:
                d = json.loads(linha)
            except json.JSONDecodeError:
                contas["linhas invalidas"] += 1
                continue
            sid = str(d.get("id") or "").strip()
            if not UUID.match(sid):
                contas["linhas invalidas"] += 1
                continue
            registros.append((sid, d))

    no_banco = _sessoes_do_banco(db, [sid for sid, _ in registros])

    sessoes: list = []
    cartas: dict = {}
    for sid, d in registros:
        sessao = no_banco.get(sid)
        if sessao is None:
            # Sem sessão não há de quem seja a regra — e o id não existe para
            # ser marcado. Gravar as cartas assim mesmo daria conhecimento
            # rotulado por um campo do arquivo, que é cópia feita pelo modelo.
            contas["sessao inexistente em observed_sessions"] += 1
            continue

        resumo = dict(sessao.get("summary") or {})
        if resumo.get("distilled"):
            contas["ja destilada"] += 1
            continue

        # A SEGURADORA VEM DO BANCO. O campo `seguradora` do destilado é uma
        # cópia que o modelo fez da linha do lote — e modelo copia errado.
        do_banco = str(sessao.get("insurer_key") or "")
        do_arquivo = str(d.get("seguradora") or "")
        if do_arquivo and do_arquivo != do_banco:
            contas["seguradora do arquivo diverge do banco"] += 1

        # O ramo observado venceria; 📊 hoje ele é NULL em 551 de 551.
        ramo = str(sessao.get("ramo") or d.get("ramo") or "outro")

        d = dict(d, seguradora=do_banco, ramo=ramo)
        resumo["distilled"] = _distilled(d, marca=MARCA)
        sessoes.append((sid, resumo))

        for c in _cartas_de(d, sid, marca=MARCA, dono=_dono_da_sessao_observada):
            contas["fatos aproveitados"] += 1
            if c["status"] != "pending_review":
                contas["cartas barradas por PII"] += 1
            if c["insurer_key"]:
                contas["cartas com seguradora"] += 1
            else:
                contas["cartas sem seguradora"] += 1
                if (c["pii_check"] or {}).get("seguradora_citada"):
                    contas["rebaixadas por citar outra companhia"] += 1
            if c["card_hash"] in cartas:
                contas["repetidas dentro do arquivo"] += 1
            cartas.setdefault(c["card_hash"], c)

    return sessoes, cartas


# ------------------------------------------------------------------ #
# ESCRITA — só com `--aplicar`
# ------------------------------------------------------------------ #

def _gravar(db, sessoes: list, cartas: dict) -> int:
    """Cartas primeiro, marca da sessão depois. Ver o cabeçalho.

    Devolve quantas sessões foram marcadas.
    """
    linhas = list(cartas.values())
    for i in range(0, len(linhas), 200):
        db.table("knowledge_cards").upsert(
            linhas[i:i + 200], on_conflict="card_hash",
            ignore_duplicates=True).execute()

    marcadas = 0
    for sid, resumo in sessoes:
        # Releitura imediatamente antes de escrever: o plano pode ter sido
        # feito minutos atrás, e a marca `distilled` é o que impede a mesma
        # conversa de ser destilada de novo. Mesma leitura do `aplicar.py`.
        atual = (db.table("observed_sessions").select("summary")
                 .eq("id", sid).limit(1).execute().data or [])
        agora = dict((atual[0] if atual else {}).get("summary") or {})
        if agora.get("distilled"):
            continue
        agora["distilled"] = resumo["distilled"]
        db.table("observed_sessions").update({"summary": agora}).eq("id", sid).execute()
        marcadas += 1
    return marcadas


def aplicar_arquivos(db, caminhos: list, gravar: bool = False) -> dict:
    """O trabalho inteiro. `gravar=False` não toca no banco a não ser por SELECT."""
    contas: collections.Counter = collections.Counter()
    total_s = total_c = novas = 0
    por_seguradora: collections.Counter = collections.Counter()

    for caminho in caminhos:
        sessoes, cartas = _planejar(db, caminho, contas)
        for c in cartas.values():
            por_seguradora[c["insurer_key"] or "(sem seguradora)"] += 1

        ja = _hashes_ja_no_acervo(db, list(cartas))
        inedita = len(cartas) - len(ja)
        contas["ja existiam no acervo"] += len(ja)

        if gravar:
            marcadas = _gravar(db, sessoes, cartas)
        else:
            marcadas = len(sessoes)

        total_s += marcadas
        total_c += len(cartas)
        novas += inedita
        print(f"[aplicar-seg] {os.path.basename(caminho)}: {marcadas} sessões · "
              f"{len(cartas)} cartas ({inedita} inéditas)", file=sys.stderr)

    return {"sessoes": total_s, "cartas": total_c, "cartas_ineditas": novas,
            "por_seguradora": dict(por_seguradora), "contas": dict(contas),
            "gravado": gravar}


def _conectar(url: str, key: str):
    from supabase import create_client

    return create_client(url, key)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Grava as cartas destiladas das conversas com a seguradora.")
    p.add_argument("arquivos", nargs="*",
                   help=f"*.destilado.jsonl; vazio = {PADRAO}")
    p.add_argument("--aplicar", action="store_true",
                   help="GRAVA no banco. Sem esta bandeira, só simula.")
    args = p.parse_args(argv)

    caminhos = args.arquivos or sorted(glob.glob(PADRAO))
    if not caminhos:
        print(f"[aplicar-seg] nenhum destilado em {PADRAO}", file=sys.stderr)
        return 2

    # A PORTA FECHA AQUI. `_credenciais` sai com código 2 quando falta chave —
    # antes de abrir arquivo, antes de conectar, antes de qualquer escrita.
    # Descobrir a falta de credencial no meio da gravação deixaria metade das
    # sessões marcadas e metade das cartas fora.
    url, key = _credenciais()
    db = _conectar(url, key)

    if not args.aplicar:
        print("[aplicar-seg] SIMULAÇÃO — nada será gravado. Use --aplicar para "
              "valer.", file=sys.stderr)

    r = aplicar_arquivos(db, caminhos, gravar=args.aplicar)

    verbo = "GRAVADO" if r["gravado"] else "PREVISTO"
    print(f"\n[aplicar-seg] {verbo}: {r['sessoes']} sessões · {r['cartas']} cartas "
          f"· {r['cartas_ineditas']} inéditas no acervo", file=sys.stderr)
    for chave, n in sorted(r["por_seguradora"].items(), key=lambda t: -t[1]):
        print(f"[aplicar-seg]   {chave:24} {n}", file=sys.stderr)
    for motivo, n in sorted(r["contas"].items()):
        print(f"[aplicar-seg]   · {motivo}: {n}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
