# -*- coding: utf-8 -*-
r"""G3 — A MÍDIA DO SEGURADO ENTRA NO BUFFER, NOS TRÊS PONTOS.
SPEC-EXTRA-001.2 BLOCO AB (§6.2, §12).

🔴 **O defeito, medido.** Três lugares de `webhook.py` desviavam imagem e áudio
para geração IMEDIATA e devolviam `{"status":"received","type":"media"}` **sem
passar pelo buffer**. A foto abria um turno em PARALELO ao texto que ainda
estava no buffer — o segurado mandava *"bateu aqui"* + foto e recebia **duas**
respostas, cada uma cega para a metade da outra.

📊 O tamanho do buraco: **27,06%** das rajadas do acervo têm mídia, e existem
rajadas **100% mídia** (6 de 6, 5 de 5) — nessas, o buffer não via **nada**.
⚠️ E `documento_payload` já caía no buffer: a assimetria era acidental.

```
 [G3a] OS TRÊS PONTOS   `grep '"type": "media"'` em webhook.py = ZERO desvios
 [G3b] FOTO + LEGENDA   legenda e arquivo viajam no MESMO item, e o turno
                        recebe os dois juntos
 [G3c] SÓ FOTOS         5 imagens seguidas = 1 turno com 5 itens, não 5 turnos
 [G3d] ÁUDIO E DOC      o mesmo, pelo mesmo portão
 [G3e] COMPATIBILIDADE  o formato v1 que estiver no Redis ainda é lido
```

⚠️ Como este teste olha o webhook: `app.api.webhook` custa 📊 ~77 s só para
importar. As funções REAIS são recortadas do fonte pelos nós da AST — é o
código que vai para produção, byte a byte (CLAUDE.md §9.4).

⛔ Sem rede, sem banco, sem Redis. Telefones 100% sintéticos.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_a_midia_entra_no_buffer.py
    ... --so G3b   ·   ... --mutar   ·   ... --mutar M-MID1
"""
from __future__ import annotations

import ast
import asyncio
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

WEBHOOK = os.path.join(RAIZ, "app", "api", "webhook.py")
TEL = "5511900000001"
INTEG = "integ-corretora-A"

PASS = 0
FAIL = 0

import app.services.message_buffer_service as M  # noqa: E402


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


# ===========================================================================
# O CARREGADOR — as funções REAIS do webhook.py, sem importar o módulo
# ===========================================================================
def carregar_do_webhook(nomes, extras=None):
    fonte = io.open(WEBHOOK, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    escolhidos = []
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name in nomes:
            escolhidos.append(no)
    achados = {n.name for n in escolhidos}
    faltando = set(nomes) - achados
    check("todos os nomes pedidos existem em webhook.py", not faltando,
          f"sumiram: {sorted(faltando)} — se foram renomeados, o teste precisa saber")
    modulo = ast.Module(body=escolhidos, type_ignores=[])
    ns = {"__name__": "webhook_recortado"}
    ns.update(extras or {})
    exec(compile(ast.fix_missing_locations(modulo), WEBHOOK, "exec"), ns)  # noqa: S102
    return ns


# ===========================================================================
# RELÓGIO E REDIS DUBLADOS (os mesmos do guarda irmão)
# ===========================================================================
RELOGIO = [datetime(2026, 9, 14, 12, 0, 0)]


class _DataHoraDublada:
    @staticmethod
    def now():
        return RELOGIO[0]

    @staticmethod
    def fromisoformat(texto):
        return datetime.fromisoformat(texto)


class _Pipe:
    def __init__(self, redis):
        self.redis, self.acoes = redis, []

    def get(self, k):
        self.acoes.append(("get", k))

    def delete(self, k):
        self.acoes.append(("delete", k))

    async def execute(self):
        return [await getattr(self.redis, a)(k) for a, k in self.acoes]


class _RedisDuble:
    def __init__(self):
        self.dados = {}

    async def get(self, k):
        item = self.dados.get(k)
        if item is None:
            return None
        valor, expira = item
        if expira is not None and RELOGIO[0] >= expira:
            self.dados.pop(k, None)
            return None
        return valor

    async def set(self, k, v, nx=False, ex=None):
        if nx and await self.get(k) is not None:
            return None
        self.dados[k] = (v, RELOGIO[0] + timedelta(seconds=int(ex)) if ex else None)
        return True

    async def setex(self, k, ttl, v):
        self.dados[k] = (v, RELOGIO[0] + timedelta(seconds=int(ttl)))
        return True

    async def delete(self, k):
        return 1 if self.dados.pop(k, None) is not None else 0

    def pipeline(self):
        return _Pipe(self)


def servico_novo():
    M.datetime = _DataHoraDublada
    RELOGIO[0] = datetime(2026, 9, 14, 12, 0, 0)
    return M.MessageBufferService(_RedisDuble())


def portao_do_webhook(servico):
    """`_item_do_inbound` e `_buffer_or_dispatch_text` REAIS, ligados ao dublê."""

    async def _get_service():
        return servico

    class _LoggerMudo:
        def __getattr__(self, _n):
            return lambda *a, **k: None

    return carregar_do_webhook(
        ["_item_do_inbound", "_buffer_or_dispatch_text"],
        extras={"get_message_buffer_service": _get_service, "logger": _LoggerMudo()},
    )


def payload(texto=None, imagem=None, audio=None, documento=None, mid="m1"):
    return {
        "phone": TEL, "connectedPhone": "5511999998888", "_integration_id": INTEG,
        "text": {"message": texto} if texto else None,
        "image": imagem, "audio": audio, "document": documento, "messageId": mid,
    }


# ===========================================================================
# G3a — ZERO DESVIOS
# ===========================================================================
def g3a():
    _p("\n[G3a] Os três desvios de mídia morreram")
    fonte = io.open(WEBHOOK, encoding="utf-8").read()
    desvios = fonte.count('"type": "media"')
    check("`grep '\"type\": \"media\"'` em webhook.py = 0",
          desvios == 0,
          f"{desvios} desvio(s) vivo(s) — cada um é uma foto abrindo turno paralelo")

    # E o portão único existe, e é chamado das três rotas.
    chamadas = fonte.count("_buffer_or_dispatch_text(")
    check("o portão único do buffer é chamado de pelo menos 4 lugares "
          "(a definição + as três rotas)", chamadas >= 4, f"{chamadas}")


# ===========================================================================
# G3b — FOTO + LEGENDA + TEXTO = UM TURNO
# ===========================================================================
def g3b():
    _p("\n[G3b] Foto com legenda e o texto que veio junto: UM turno")
    s = servico_novo()
    ns = portao_do_webhook(s)

    async def cenario():
        await ns["_buffer_or_dispatch_text"](
            payload(texto="bateu aqui na porta", mid="m1"), TEL)
        await ns["_buffer_or_dispatch_text"](
            payload(imagem={"imageUrl": "https://x/f.jpg", "caption": "olha o amassado"},
                    mid="m2"), TEL)
        chave = s.chave(INTEG, TEL)
        buffer = await s.get_and_clear_buffer(chave)
        return buffer, s.get_combined_message(buffer)

    buffer, combinado = asyncio.run(cenario())
    itens = M.itens_do_buffer(buffer)
    check("a foto entrou no buffer — UM turno com 2 itens", len(itens) == 2,
          f"{len(itens)} itens: {[i.get('tipo') for i in itens]}")
    check("o item da foto é tipado como imagem", itens[1].get("tipo") == "image")
    check("🔴 a LEGENDA e o ARQUIVO viajam no MESMO item",
          itens[1].get("legenda") == "olha o amassado"
          and (itens[1].get("midia") or {}).get("imageUrl") == "https://x/f.jpg",
          f"{itens[1]!r}")
    check("e o texto combinado tem as duas falas, na ordem",
          combinado == "bateu aqui na porta\nolha o amassado", repr(combinado))
    check("o wa_message_id de cada item é preservado",
          [i.get("wa_message_id") for i in itens] == ["m1", "m2"])


# ===========================================================================
# G3c — RAJADA 100% IMAGENS
# ===========================================================================
def g3c():
    _p("\n[G3c] Cinco fotos seguidas: 1 turno com 5 itens (hoje eram 5 turnos)")
    s = servico_novo()
    ns = portao_do_webhook(s)

    async def cenario():
        for n in range(5):
            await ns["_buffer_or_dispatch_text"](
                payload(imagem={"imageUrl": f"https://x/{n}.jpg", "caption": None},
                        mid=f"m{n}"), TEL)
            RELOGIO[0] = RELOGIO[0] + timedelta(seconds=2)
        chave = s.chave(INTEG, TEL)
        antes = await s.should_process(chave)
        RELOGIO[0] = RELOGIO[0] + timedelta(seconds=9)
        depois = await s.should_process(chave)
        buffer = await s.get_and_clear_buffer(chave)
        return antes, depois, buffer, s.get_combined_message(buffer)

    antes, depois, buffer, combinado = asyncio.run(cenario())
    itens = M.itens_do_buffer(buffer)
    check("as 5 fotos estão no MESMO buffer", len(itens) == 5, f"{len(itens)}")
    check("2 s depois da última a janela ainda NÃO fechou", antes is False,
          "mídia sem legenda espera 8 s — o segurado costuma explicar logo atrás")
    check("mais 9 s e ela fecha — UM turno", depois is True)
    check("e o prompt vê as 5, nunca uma linha vazia",
          combinado.count("🖼️ [Imagem enviada]") == 5, repr(combinado[:120]))


# ===========================================================================
# G3d — ÁUDIO E DOCUMENTO
# ===========================================================================
def g3d():
    _p("\n[G3d] Áudio pelo mesmo portão; o documento continua entrando")
    s = servico_novo()
    ns = portao_do_webhook(s)

    async def cenario():
        await ns["_buffer_or_dispatch_text"](
            payload(audio={"audioUrl": "https://x/a.ogg"}, mid="m1"), TEL)
        await ns["_buffer_or_dispatch_text"](
            payload(texto="[DOCUMENTO apolice.pdf]\nconteudo extraido",
                    documento={"fileName": "apolice.pdf"}, mid="m2"), TEL)
        chave = s.chave(INTEG, TEL)
        buffer = await s.get_and_clear_buffer(chave)
        return buffer, s.get_combined_message(buffer)

    buffer, combinado = asyncio.run(cenario())
    itens = M.itens_do_buffer(buffer)
    check("áudio e documento no MESMO turno", len(itens) == 2,
          f"{[i.get('tipo') for i in itens]}")
    check("o áudio é tipado, com a URL guardada",
          itens[0].get("tipo") == "audio"
          and (itens[0].get("midia") or {}).get("audioUrl") == "https://x/a.ogg")
    check("o documento é tipado e leva o texto extraído",
          itens[1].get("tipo") == "document"
          and "conteudo extraido" in M.texto_do_item(itens[1]))
    check("o áudio mudo aparece no prompt como fala, não como vazio",
          "[Mensagem de voz]" in combinado, repr(combinado[:120]))

    # A janela do documento é a da frase completa: o ritmo do PDF não é o da
    # pessoa que o mandou.
    check("documento fecha a rajada em 8 s",
          M.janela_de_espera(M.tracos_da_mensagem("texto longo do pdf",
                                                  tipo="document")) == 8)


# ===========================================================================
# G3e — O FORMATO v1 AINDA É LIDO (a migração é in-flight, <= 60 s)
# ===========================================================================
def g3e():
    _p("\n[G3e] O buffer v1 que ficou no Redis no deploy ainda é lido")
    s = servico_novo()
    chave = s.chave(INTEG, TEL)
    agora = RELOGIO[0].isoformat()
    velho = {"messages": ["bati o carro", "na avenida"], "first_at": agora,
             "last_at": agora, "company_id": "pending", "user_id": "pending",
             "integration": {}, "payload": {"_integration_id": INTEG}}

    async def cenario():
        await s.redis.setex(chave, 60, json.dumps(velho))
        RELOGIO[0] = RELOGIO[0] + timedelta(seconds=20)
        pronto = await s.should_process(chave)
        buffer = await s.get_and_clear_buffer(chave)
        return pronto, buffer, s.get_combined_message(buffer)

    pronto, buffer, combinado = asyncio.run(cenario())
    check("o v1 ainda é processado (ninguém fica preso no Redis)", pronto is True)
    check("e o texto sai inteiro", combinado == "bati o carro\nna avenida",
          repr(combinado))
    check("`itens_do_buffer` converte o v1 em itens de texto",
          [i["tipo"] for i in M.itens_do_buffer(buffer)] == ["text", "text"])
    check("e o v2 novo nasce com a marca de versão",
          M.itens_do_buffer({"v": 2, "itens": [{"tipo": "image"}]})[0]["tipo"] == "image")


GATES = {"G3a": g3a, "G3b": g3b, "G3c": g3c, "G3d": g3d, "G3e": g3e}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
WH = "app/api/webhook.py"
MBS = "app/services/message_buffer_service.py"

MUTACOES = [
    # (a) 🔴 A MUTACAO DO CARD: religar o desvio do caminho QUENTE (o antigo
    #     `webhook.py:2228`) -> a rajada com foto volta a virar 2 turnos.
    ("M-MID1", WH,
     '    return await _buffer_or_dispatch_text(payload_dict, normalized["phone"])',
     '    if image_payload or audio_payload:\n'
     '        background_tasks.add_task(process_whatsapp_message_background, payload_dict)\n'
     '        return {"status": "received", "type": "media"}  # MUTACAO\n'
     '    return await _buffer_or_dispatch_text(payload_dict, normalized["phone"])',
     "G3a"),
    # (b) a legenda deixa de viajar com o arquivo
    ("M-MID2", WH,
     '        return "image", str(imagem.get("caption") or texto or ""), dict(imagem)',
     '        return "image", "", dict(imagem)  # MUTACAO',
     "G3b"),
    # (c) a midia volta a ser um item de texto qualquer -> nada de arquivo
    ("M-MID3", WH,
     '    if imagem:\n'
     '        return "image", str(imagem.get("caption") or texto or ""), dict(imagem)',
     '    if imagem:\n        return "text", texto, None  # MUTACAO',
     "G3b"),
    # (d) a marca da midia muda some -> 5 fotos viram 5 linhas vazias
    ("M-MID4", MBS,
     '        marca = MARCA_DE_MIDIA.get(str((item or {}).get("tipo") or "").lower())\n'
     "        if marca:\n            linhas.append(marca)",
     "        continue  # MUTACAO",
     "G3c"),
    # (e) o v1 deixa de ser lido -> quem estava no Redis no deploy fica preso
    ("M-MID5", MBS,
     '    return [{"tipo": "text", "texto": str(m or "")}\n'
     '            for m in (dados.get("messages") or [])]',
     "    return []  # MUTACAO",
     "G3e"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate],
        # 🔴 `encoding` explicito: sem ele o cp1252 do Windows estoura no
        # primeiro emoji e uma mutacao VERMELHA e contada como verde.
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-ab-g3").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    if not so:
        _p("=" * 78)
        _p("  G3 -- A MIDIA ENTRA NO BUFFER  (SPEC-EXTRA-001.2 BLOCO AB §6.2)")
        _p("=" * 78)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-900:]))
    if not so:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_a_midia_entra_no_buffer():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
