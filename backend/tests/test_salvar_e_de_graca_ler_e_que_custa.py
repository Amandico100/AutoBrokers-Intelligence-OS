"""Salvar o áudio é de graça. Transcrever é que custa — e só isso pede orçamento.

O pedido do Founder, literal
-----------------------------
> *"Eu não quero que os áudios sejam transcritos já. Quero que eles sejam feitos
> download e não custem nada pra serem baixados. E aí na hora de transcrever, aí
> sim teríamos um custo — mas não na hora de salvar, pra garantir que eles estão
> no nosso banco salvos."*
>
> *"Também precisa se precaver no fato de baixar os áudios não vá bloquear o
> número. Garanta que isso seja garantido que não aconteça."*

A promessa que o código fazia e não cumpria
--------------------------------------------
O comentário do `enqueue_observer_media` dizia, palavra por palavra:

> *"sem orçamento aberto devolve -1 e a mídia só é ARQUIVADA. Ela não se perde
> — fica sem leitura, e a leitura pode ser feita depois."*

**Não era verdade.** O portão estava no **enfileiramento**: sem orçamento, nada
era baixado, nada era arquivado, e o áudio existia apenas como uma coordenada
num campo JSON.

📊 Medido em 04/08/2026: **2.849 mídias com coordenada de download, ZERO
arquivadas.** E 3.654 áudios anteriores ao conserto das coordenadas já estão
perdidos — não têm nem a coordenada.

A assimetria que decide
------------------------
```
BAIXAR + ARQUIVAR   custo zero. Bytes do WhatsApp pela sessão já pareada,
                    guardados no MinIO da própria casa.
                    📊 488 MB no total · 80 MB só de áudio.

TRANSCREVER         Whisper cobra por minuto. É aqui que há conta.
```

E a coordenada de mídia do WhatsApp **expira**. Não arquivar hoje é escolher
perder o áudio; transcrever depois é sempre possível, porque o arquivo estará
no disco.

Por isso o portão desceu do enfileiramento para `_derive_text` — o único lugar
onde há dinheiro envolvido.

O guarda contra bloqueio do número
-----------------------------------
Baixar mídia em rajada por uma sessão que cai e volta é o padrão que faz o
WhatsApp desconfiar. O `_load_integration_sync` conferia `is_active` **só no
caminho de fallback** — e o caminho normal (por `integration_id`) não conferia
nada. O caso [3] fecha isso.
"""

from __future__ import annotations

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALVO = os.path.join(RAIZ, "backend", "app", "services", "atlas", "observer_media.py")
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _fonte() -> str:
    with open(ALVO, encoding="utf-8") as fh:
        return fh.read()


def _funcao(nome: str):
    arvore = ast.parse(_fonte())
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return no
    return None


def _chamadas(no) -> list[str]:
    out = []
    for f in ast.walk(no):
        if isinstance(f, ast.Call):
            alvo = f.func
            if isinstance(alvo, ast.Name):
                out.append(alvo.id)
            elif isinstance(alvo, ast.Attribute):
                out.append(alvo.attr)
    return out


# ---------------------------------------------------------------------------

def teste_enfileirar_nao_pede_orcamento():
    print("\n[1] Enfileirar para BAIXAR não consulta orçamento")
    fn = _funcao("enqueue_observer_media")
    checar(fn is not None, "a função de enfileirar existe")
    if fn is None:
        return

    checar("_pode_gastar_midia" not in _chamadas(fn),
           "o enfileiramento NÃO consulta o orçamento",
           "era daqui que 2.849 mídias ficavam sem ser baixadas — e o áudio "
           "cuja coordenada expira não volta")

    # E continua recusando o que não deve entrar na fila.
    fonte_fn = ast.get_source_segment(_fonte(), fn) or ""
    checar("ALLOWED_TABLES" in fonte_fn,
           "CONTROLE — mas segue recusando tabela fora da lista",
           "abrir o portão do custo não pode ter aberto o portão do escopo")


def teste_transcrever_continua_pedindo_orcamento():
    print("\n[2] Transcrever CONTINUA pedindo orçamento — é o que custa")
    fn = _funcao("_process_payload")
    checar(fn is not None, "o processamento existe")
    if fn is None:
        return

    chamadas = _chamadas(fn)
    checar("_pode_gastar_midia" in chamadas,
           "o processamento consulta o orçamento")
    checar("_derive_text" in chamadas, "e é ele que decide a transcrição")

    trecho = ast.get_source_segment(_fonte(), fn) or ""
    i_arquiva = trecho.find("_archive_private_sync")
    i_orcamento = trecho.find("_pode_gastar_midia")
    checar(0 < i_arquiva < i_orcamento,
           "🔴 e ARQUIVAR vem ANTES de consultar o orçamento",
           f"arquiva={i_arquiva} orcamento={i_orcamento} — se o orçamento viesse "
           "primeiro, o arquivo continuaria não sendo salvo")

    # O estado precisa distinguir "salvo sem ler" de "salvo e lido", senão não
    # há como achar depois o que ainda falta transcrever.
    checar('"arquivado"' in trecho,
           "existe o estado `arquivado` (salvo, sem transcrição)",
           "sem ele, 'processed' significaria duas coisas diferentes")
    checar('"processed" if pode_ler else "arquivado"' in trecho,
           "e ele depende do orçamento, não de outra coisa")


def teste_nao_baixa_por_canal_que_caiu():
    print("\n[3] CONTRA BLOQUEIO — não baixa por canal fora do ar")
    fn = _funcao("_load_integration_sync")
    checar(fn is not None, "o carregador de integração existe")
    if fn is None:
        return

    trecho = ast.get_source_segment(_fonte(), fn) or ""
    comandos = "\n".join(l for l in trecho.split("\n") if not l.lstrip().startswith("#"))

    checar('if not linha.get("is_active")' in comandos,
           "linha aposentada NÃO serve download",
           "o caminho por integration_id não conferia nada — e é o caminho normal")
    checar("esta_conectado" in comandos or "normalizar_estado" in comandos,
           "e o estado do canal é consultado pelo tradutor único",
           "comparar string crua não enxerga `retired` nem `unknown`")

    # Levantar (e não devolver None) importa: o item volta para a fila em vez
    # de ser marcado como processado sem arquivo.
    levanta = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
    checar(bool(levanta), "e a recusa LEVANTA, para o item ser retentado",
           "devolver None marcaria como visto sem ter baixado")


def teste_o_ritmo_continua_manso():
    print("\n[4] O ritmo não pode ter virado rajada")
    fn = _funcao("check_observer_media")
    checar(fn is not None, "o laço do worker existe")
    if fn is None:
        return

    # 📊 3 arquivos a cada 10s = 18/min. Para 2.849 arquivos, ~2h40 — mais
    # lento do que uma pessoa rolando o histórico no celular.
    padrao = next((d for d in (fn.args.defaults or []) if isinstance(d, ast.Constant)), None)
    checar(padrao is not None and isinstance(padrao.value, int) and padrao.value <= 5,
           f"o lote padrão é pequeno ({getattr(padrao, 'value', '?')} por rodada)",
           "lote grande + intervalo curto é exatamente o padrão que faz o "
           "WhatsApp desconfiar do número")

    trecho = ast.get_source_segment(_fonte(), fn) or ""
    checar("min(10," in trecho, "e há teto absoluto por rodada",
           "sem teto, um lote configurado errado vira rajada")


def teste_o_detector_consegue_acusar():
    print("\n[5] CONTRAPROVA — os guardas conseguem reprovar")

    # Um enfileiramento de mentira, com o portão de volta no lugar errado.
    culpado = ast.parse(
        "async def enqueue(x):\n"
        "    if not await _pode_gastar_midia():\n"
        "        return False\n"
        "    return True\n")
    fn = next(n for n in ast.walk(culpado)
              if isinstance(n, ast.AsyncFunctionDef))
    checar("_pode_gastar_midia" in _chamadas(fn),
           "o detector reconhece o portão no enfileiramento",
           "prova que o verde do caso [1] vem de o código estar certo")

    # E um carregador sem guarda de canal.
    sem_guarda = ast.parse(
        "def carregar(p):\n"
        "    rows = db.table('integrations').select('*').execute().data\n"
        "    return rows[0]\n")
    fn2 = next(n for n in ast.walk(sem_guarda) if isinstance(n, ast.FunctionDef))
    trecho2 = "def carregar(p):\n    rows = db.table('integrations').select('*').execute().data\n    return rows[0]\n"
    checar('if not linha.get("is_active")' not in trecho2
           and not [n for n in ast.walk(fn2) if isinstance(n, ast.Raise)],
           "e reconhece um carregador SEM guarda de canal")


def teste_so_baixa_o_que_foi_pedido():
    """O Founder pediu ÁUDIO. Baixar o resto é tráfego que não pediram.

    > *"Não precisa baixar as imagens e documentos. A ideia é garantir que temos
    >  os áudios agora salvos para podermos transcrever e destilar depois."*

    📊 Medido em 04/08/2026, o que o corte economiza:

        audio      1.623 arquivos ·  80 MB   ← onde o segurado EXPLICA o caso
        document     292          · 165 MB
        image        792          · 106 MB
        video         29          · 106 MB
        sticker      108          ·  30 MB

    Só áudio corta **84% dos bytes e 43% dos arquivos**. E menos tráfego pela
    sessão do WhatsApp é menos risco de o número ser marcado como anômalo — a
    garantia que ele pediu com todas as letras.

    O filtro fica no ENFILEIRAMENTO, não no worker: o que não entra na fila não
    gasta tráfego nenhum.
    """
    import os

    print("\n[6] Só o tipo pedido entra na fila")
    mod = _carregar_modulo()

    anterior = os.environ.pop("OBSERVER_MEDIA_KINDS", None)
    try:
        checar(mod.tipos_que_baixamos() == frozenset({"audio"}),
               "o padrão é SÓ áudio", str(sorted(mod.tipos_que_baixamos())))

        # CONTROLE — a função consegue devolver outra coisa. Sem isto, um
        # `return {"audio"}` cravado passaria por configuração respeitada.
        os.environ["OBSERVER_MEDIA_KINDS"] = "audio,image"
        checar(mod.tipos_que_baixamos() == frozenset({"audio", "image"}),
               "CONTROLE — e obedece quando alguém alarga",
               str(sorted(mod.tipos_que_baixamos())))

        os.environ["OBSERVER_MEDIA_KINDS"] = ""
        checar(mod.tipos_que_baixamos() == frozenset({"audio"}),
               "env vazia cai no lado seguro (áudio), não em 'tudo'",
               "vazio virando 'tudo' baixaria 488 MB sem ninguém pedir")
    finally:
        os.environ.pop("OBSERVER_MEDIA_KINDS", None)
        if anterior is not None:
            os.environ["OBSERVER_MEDIA_KINDS"] = anterior

    # E o filtro tem de estar no enfileiramento.
    fn = _funcao("enqueue_observer_media")
    checar(fn is not None and "tipos_que_baixamos" in _chamadas(fn),
           "o enfileiramento consulta o filtro",
           "no worker seria tarde: o tráfego já teria acontecido")


def _carregar_modulo():
    import importlib.util

    spec = importlib.util.spec_from_file_location("_observer_media", ALVO)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    print("=" * 70)
    print("SALVAR E DE GRACA; LER E QUE CUSTA")
    print("=" * 70)
    for teste in (teste_enfileirar_nao_pede_orcamento,
                  teste_transcrever_continua_pedindo_orcamento,
                  teste_nao_baixa_por_canal_que_caiu,
                  teste_o_ritmo_continua_manso,
                  teste_o_detector_consegue_acusar,
                  teste_so_baixa_o_que_foi_pedido):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O AUDIO FICA SALVO SEM CUSTAR NADA, E A LEITURA ESPERA A HORA CERTA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
