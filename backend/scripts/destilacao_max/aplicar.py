"""Grava o que o subagente destilou. Direto no banco, fora do contexto de todos.

Por que isto substituiu o `aplicar_sql.py` no fluxo normal
----------------------------------------------------------
Medido em 29/07/2026: cada subagente gastou ~250 mil tokens para destilar ~90
conversas. O trabalho em si — ler a conversa e escrever o conhecimento — custa
uns 85 mil. O resto era **transporte**: gerar um arquivo .sql, lê-lo de volta,
fatiá-lo em blocos que coubessem numa chamada, executar bloco a bloco e
conferir. Um terço do esforço do modelo mais caro do sistema empurrando texto.

Agora o subagente destila e para. Quem grava é este script, que fala com o
banco pela mesma conexão do exportador. O modelo pensa; o script carrega.

`aplicar_sql.py` continua existindo para quando não houver credencial de banco
à mão — é o caminho que só depende do MCP.

As regras de gravação são as de `_store_card_sync`, sem inventar nada:
md5 do texto em minúsculas, 15 a 400 caracteres, `rejected_pii` quando o
templatize mudaria o texto, e a seguradora decidida por
`curadoria_cartas.seguradora_do_fato` — a MESMA função do destilador. A carta
entra como `pending_review`; quem publica no RAG é o publicador de
`distill_once`.

Em 05/08/2026 esta era a terceira porta pela qual a seguradora da SESSÃO virava
rótulo do FATO. Reescrever a regra aqui teria feito o acervo divergir de si
mesmo conforme a porta de entrada — o mesmo motivo pelo qual o mascaramento de
PII é importado e não recopiado.

A MARCA DA CAMPANHA, e por que ela deixou de ser uma constante
--------------------------------------------------------------
`MARCA` era `"destilacao_max_29_07_2026"`, escrita à mão e nunca trocada.

📊 Consequência medida: as 1.941 cartas da campanha de 04/08/2026 foram
gravadas com a marca da campanha de 29/07. As duas ficaram indistinguíveis pelo
marcador — só a data as separa. E `CURADORIA-POR-SUBAGENTES.md:236` manda
conferir a campanha por `pii_check->>'por' = '<marca>'`: a conferência devolvia
as duas campanhas somadas, e ninguém tinha como saber que devolvia.

Uma constante que alguém precisa **lembrar** de editar é o defeito, não o valor
dela. Agora ela vem do calendário e pode ser dita na linha de comando —
o mesmo desenho que `aplicar_seguradoras.py` já usa:

    python aplicar.py lote.jsonl                  → destilacao_max_08_08_2026
    python aplicar.py lote.jsonl --marca reforco  → reforco

A ORDEM DE ESCRITA, que era o inverso desta
-------------------------------------------
`summary.distilled` era gravado DENTRO do laço, conversa a conversa, e o
`upsert` das cartas só no fim do arquivo. As duas escritas não são uma
transação. Se a rodada caísse entre elas — rede, chave expirada, Ctrl-C — as
sessões já marcadas ficavam declaradas destiladas **sem uma carta no acervo**,
e a marca é justamente o "não volte mais": `exportar.py` e o destilador as
pulam para sempre. O sintoma é uma sessão que parece pronta; a perda não deixa
rastro nenhum (P-109).

A carta é idempotente (`on_conflict=card_hash, ignore_duplicates`); a marca é
irreversível na prática. Então: **cartas primeiro, marca depois** — a mesma
ordem que `aplicar_seguradoras._gravar` escolheu de propósito e explica no
próprio cabeçalho. Nesta ordem qualquer queda no meio deixa trabalho refazível
e nada duplicado.

Uso
---
    python aplicar.py lotes/lote_011.destilado.jsonl [outro.jsonl ...]
    python aplicar.py lote.jsonl --marca destilacao_max_reforco_agosto
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from exportar import _credenciais  # noqa: E402
from mascarar import _carregar_servico, templatize  # noqa: E402

_CURADORIA = _carregar_servico("curadoria_cartas")
assunto_da_carta = _CURADORIA.assunto_da_carta
seguradora_do_fato = _CURADORIA.seguradora_do_fato

PREFIXO_MARCA = "destilacao_max"
UUID = re.compile(r"[0-9a-fA-F-]{36}")


def marca_de_hoje(quando: "datetime.date | None" = None) -> str:
    """A marca desta campanha, pelo calendário. `destilacao_max_DD_MM_AAAA`.

    O formato é o da marca antiga porque o acervo já tem 5.295 cartas com ele
    e `CURADORIA-POR-SUBAGENTES.md` ensina a conferir por ele. Mudar o formato
    junto com o defeito quebraria a conferência de tudo que já foi gravado.

    Vem do calendário e não de uma constante para que o valor certo seja o
    caminho de MENOR esforço. Uma constante só está certa enquanto alguém
    lembra dela, e 📊 em 04/08/2026 ninguém lembrou.
    """
    dia = quando or datetime.date.today()
    return f"{PREFIXO_MARCA}_{dia:%d_%m_%Y}"


# Compatibilidade de importação: `aplicar_seguradoras` e os testes importam
# `_cartas_de`/`_distilled` daqui e passam a marca DELES. Este valor é só o
# padrão de quem não passa nenhuma — e ele muda todo dia, que é o conserto.
MARCA = marca_de_hoje()


def _distilled(d: dict, marca: str = MARCA) -> dict:
    return {
        "tipo": d.get("tipo"), "ramo": d.get("ramo"),
        "servico": d.get("servico"), "seguradora": d.get("seguradora"),
        "resumo_conduta": d.get("resumo_conduta") or [],
        "perguntas_na_ordem": d.get("perguntas_na_ordem") or [],
        "score": d.get("score"), "flags": d.get("flags") or [],
        "at": None, "por": marca,
    }


def _dono_por_texto(texto: str, candidata: str) -> tuple:
    """DE QUEM É A REGRA no acervo de ATENDIMENTO — a seguradora é candidata.

    📊 05/08/2026: das 3.354 cartas etiquetadas, só 32,3% citavam a própria
    seguradora. Ali a companhia da SESSÃO é palpite, e `seguradora_do_fato`
    só a aceita quando o texto do fato a nomeia.

    Isto está numa função separada por um motivo: existe um segundo acervo em
    que a resposta é OUTRA. Em `observed_sessions` a conversa **é** com a
    seguradora — a mesma pergunta, feita sobre uma evidência diferente, tem
    resposta diferente. `aplicar_seguradoras.py` injeta a dele aqui em vez de
    recopiar as regras de gravação, e as duas ficam lado a lado, visíveis.
    """
    seg, prestadora = seguradora_do_fato(texto, candidata)
    return seg, ({"prestadora": prestadora} if prestadora else {})


def _cartas_de(d: dict, sessao: str = "", marca: str = MARCA, dono=_dono_por_texto) -> list:
    ramo = str(d.get("ramo") or "outro")
    candidata = str(d.get("seguradora") or "")   # da SESSÃO — candidata, não veredito
    saida = []
    for fato in (d.get("fatos_reutilizaveis") or [])[:8]:
        texto = " ".join(str(fato or "").split())
        if len(texto) < 15 or len(texto) > 400:
            # 🔴 O DESCARTE PASSA A CONTAR E A DIZER O QUE PERDEU — 15/08/2026.
            #
            # Este `continue` era mudo. Uma carta longa demais sumia sem log,
            # sem contagem e sem rastro, e o acervo ficava parecendo completo.
            #
            # 📊 E o padrão é perverso: quanto mais COMPLETA a carta, maior a
            # chance de morrer aqui. Uma lista de documentos de sinistro é longa
            # PORQUE é completa — é exatamente o que a torna útil e o que a mata.
            #
            # ⚠️ Não mexi no limite. Primeiro medir, depois decidir (§9.2): um
            # teto que eu mudasse antes de saber o volume seria palpite com
            # consequência no RAG. A linha abaixo é o instrumento que faltava.
            print(f"[aplicar] DESCARTADO por tamanho ({len(texto)} ch, "
                  f"limite 15-400) sessao={sessao[:8]} ramo={ramo}: "
                  f"{texto[:90]}...", file=sys.stderr)
            continue
        limpo = templatize(texto) == texto
        seg, extras = dono(texto, candidata)
        if seg and not re.fullmatch(r"[a-z0-9_-]{2,40}", seg):
            seg = None
        marcas = {"deterministic": limpo, "llm_instructed": True,
                  "por": marca, "sessao": sessao}
        marcas.update(extras or {})
        saida.append({
            "card_hash": hashlib.md5(texto.lower().encode("utf-8")).hexdigest(),
            "card_text": texto, "category": assunto_da_carta(texto), "ramo": ramo,
            "insurer_key": seg,
            "status": "pending_review" if limpo else "rejected_pii",
            "pii_check": marcas,
        })
    return saida


def _planejar(db, caminho: str, marca: str) -> tuple:
    """(sessões a marcar, cartas a gravar, linhas inválidas). Só LÊ.

    Separar o plano da escrita é o que permite gravar as cartas antes das
    marcas: enquanto o plano era feito dentro do laço que já escrevia, a ordem
    era a única possível.
    """
    sessoes: list = []
    cartas: dict = {}              # hash -> linha (dedup dentro do arquivo)
    puladas = 0
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            try:
                d = json.loads(linha)
            except json.JSONDecodeError:
                puladas += 1
                continue
            sid = str(d.get("id") or "").strip()
            if not UUID.fullmatch(sid):
                puladas += 1
                continue

            # Lê o resumo atual para PRESERVAR `marker` e `source`, e para
            # nunca sobrescrever uma destilação que já existe — o mesmo
            # `WHERE summary->'distilled' IS NULL` do caminho por SQL.
            atual = (db.table("attendance_sessions").select("summary")
                     .eq("id", sid).limit(1).execute().data or [])
            resumo = dict((atual[0] if atual else {}).get("summary") or {})
            if resumo.get("distilled"):
                continue
            resumo["distilled"] = _distilled(d, marca=marca)
            sessoes.append((sid, resumo))
            for c in _cartas_de(d, sid, marca=marca):
                cartas.setdefault(c["card_hash"], c)
    return sessoes, cartas, puladas


def _gravar(db, sessoes: list, cartas: dict) -> int:
    """CARTAS PRIMEIRO, marca da sessão depois. Ver o cabeçalho (P-109).

    A ordem inversa — a que estava aqui — deixava sessões declaradas destiladas
    sem carta nenhuma no acervo quando a rodada caía no meio, e a marca é o
    "não volte mais". Devolve quantas sessões foram marcadas.
    """
    linhas = list(cartas.values())
    for i in range(0, len(linhas), 200):
        db.table("knowledge_cards").upsert(
            linhas[i:i + 200], on_conflict="card_hash",
            ignore_duplicates=True).execute()

    marcadas = 0
    for sid, resumo in sessoes:
        # Releitura imediatamente antes de escrever: entre o plano e agora as
        # cartas foram gravadas, e outra rodada pode ter marcado esta sessão.
        # É a mesma leitura que `aplicar_seguradoras._gravar` faz.
        atual = (db.table("attendance_sessions").select("summary")
                 .eq("id", sid).limit(1).execute().data or [])
        agora = dict((atual[0] if atual else {}).get("summary") or {})
        if agora.get("distilled"):
            continue
        agora["distilled"] = resumo["distilled"]
        db.table("attendance_sessions").update({"summary": agora}).eq("id", sid).execute()
        marcadas += 1
    return marcadas


def aplicar_arquivos(db, caminhos: list, marca: str) -> dict:
    """O trabalho inteiro, sem tocar em `sys.argv` nem em credencial."""
    total_s = total_c = puladas = 0
    for caminho in caminhos:
        sessoes, cartas, invalidas = _planejar(db, caminho, marca)
        puladas += invalidas
        marcadas = _gravar(db, sessoes, cartas)
        total_s += marcadas
        total_c += len(cartas)
        print(f"[aplicar] {os.path.basename(caminho)}: {marcadas} sessões · "
              f"{len(cartas)} cartas", file=sys.stderr)
    return {"sessoes": total_s, "cartas": total_c, "invalidas": puladas,
            "marca": marca}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Grava o que o subagente destilou do acervo de atendimento.")
    p.add_argument("arquivos", nargs="+", help="*.destilado.jsonl")
    p.add_argument("--marca", default=None,
                   help=f"marcador da campanha; padrão = {marca_de_hoje()}")
    args = p.parse_args(argv)

    marca = (args.marca or "").strip() or marca_de_hoje()

    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)
    print(f"[aplicar] marca desta campanha: {marca}", file=sys.stderr)
    r = aplicar_arquivos(db, args.arquivos, marca)

    print(f"[aplicar] TOTAL {r['sessoes']} sessões · {r['cartas']} cartas · "
          f"{r['invalidas']} linhas inválidas · marca {r['marca']}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
