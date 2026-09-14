# -*- coding: utf-8 -*-
r"""B4 — "DIGITANDO…" SÓ QUANDO O AGENTE VAI MESMO FALAR.
SPEC-EXTRA-001.2 BLOCO AB (§6.4, §20 E02/E03).

🔴 **A regra que impede a promessa vazia.** A Meta é literal: *"only display a
typing indicator if you are going to respond"* e *"the typing indicator will be
dismissed once you respond, or **after 25 seconds**, whichever comes first"*.
Mostrar "digitando…" e depois calar é **pior** que silêncio: o segurado fica
olhando para uma promessa que ninguém fez.

📊 13/09/2026: não existia **nenhuma** chamada de presença no produto. O único
reconhecimento do problema era um comentário — `buffer_processor.py:39`, *"é o
segurado nº 4 olhando para o 'digitando…' que não vem"*.

🔴 **D1 — a rota é OUTRA da que a proposta previa.** O atendimento roda no
**Evolution GO**, e o fork implantado expõe `POST /message/presence` com
`{number, state, delay, isAudio}` — ⛔ **não** `/chat/sendPresence` (essa é do
Evolution Node e devolve 404 aqui). O `delay`, em milissegundos, mantém o
`composing` vivo re-enviando e manda `paused` ao fim.

```
 [B4a] O PORTÃO       a presença sai DEPOIS do portão de silêncio, no fonte
 [B4b] A FLAG         `PRESENCA_DIGITANDO_LIGADA=false` -> ZERO chamadas
 [B4c] O TETO         o `delay` nunca passa de 25 000 ms
 [B4d] SEM CAPACIDADE provider que não anuncia `presence` -> 0 chamadas, 0 erro
 [B4e] `paused`       o fim do turno manda `paused`, inclusive no descarte
```

⛔ Sem rede: o provider é dublê e o `_post` nunca é chamado de verdade.
⛔ Este guarda NÃO conta no teto de 12 (é o gate B4 da §12).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_digitando_so_quando_vai_falar.py
    ... --so B4c   ·   ... --mutar   ·   ... --mutar M-PRE1
"""
from __future__ import annotations

import ast
import asyncio
import io
import os
import shutil
import subprocess
import sys
import tempfile
import types

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

PASS = 0
FAIL = 0

from app.services.whatsapp.models import SendResult  # noqa: E402
from app.services.whatsapp.providers.base import ProviderCapabilities  # noqa: E402
from app.services.whatsapp_service import WhatsappService  # noqa: E402


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
# O PROVIDER DUBLÊ — e o registry dublado, para a FACHADA REAL achá-lo
# ===========================================================================
class _ProviderDuble:
    def __init__(self, tem_presenca=True):
        self.capabilities = ProviderCapabilities(presence=tem_presenca)
        self.chamadas = []

    def send_presence(self, to, presence, delay_ms=0):
        self.chamadas.append({"to": to, "state": presence, "delay": delay_ms})
        return SendResult(ok=True)


def fachada_com(provider):
    """A FACHADA REAL (`WhatsappService.send_presence`) sobre um provider dublê."""
    modulo = types.ModuleType("app.services.whatsapp.registry")
    modulo.resolve_provider = lambda _integration: provider
    sys.modules["app.services.whatsapp.registry"] = modulo
    return WhatsappService()


INTEGRACAO = {"provider": "evolution-go", "company_id": "empresa-A",
              "base_url": "http://x", "token": "t", "instance_id": "i"}


# ===========================================================================
# `_presenca` REAL, recortada do webhook (o módulo custa 📊 ~77 s p/ importar)
# ===========================================================================
def presenca_real(flag_ligada: bool, servico):
    fonte = io.open(WEBHOOK, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    nos = [n for n in arvore.body
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
           and n.name == "_presenca"]
    check("`_presenca` existe em webhook.py", len(nos) == 1,
          "se foi renomeada, este guarda precisa saber")

    class _Settings:
        PRESENCA_DIGITANDO_LIGADA = flag_ligada

    class _LoggerMudo:
        def __getattr__(self, _n):
            return lambda *a, **k: None

    ns = {"__name__": "webhook_recortado", "settings": _Settings(),
          "asyncio": asyncio, "whatsapp_service": servico,
          "logger": _LoggerMudo(), "TETO_DA_RAJADA_SEGUNDOS": 25}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nos, type_ignores=[])),  # noqa: S102
                 WEBHOOK, "exec"), ns)
    return ns["_presenca"]


# ===========================================================================
# B4a — A PRESENÇA SAI DEPOIS DO PORTÃO DE SILÊNCIO
# ===========================================================================
def b4a():
    _p("\n[B4a] A presença só sai DEPOIS do portão de silêncio")
    fonte = io.open(WEBHOOK, encoding="utf-8").read()

    pos_portao = fonte.find("a_ia_deve_calar(")
    pos_composing = fonte.find('_presenca(integration, payload.phone, "composing"')
    pos_modelo = fonte.find("ai_response, metrics = await langchain_service.process_message")
    check("o portão de silêncio existe no caminho", pos_portao > 0)
    check("a presença `composing` existe", pos_composing > 0,
          "sem ela o segurado nº 4 continua olhando para o nada")
    check("🔴 e ela vem DEPOIS do portão", pos_portao < pos_composing,
          f"portão em {pos_portao}, composing em {pos_composing} — "
          "E02: 'only display a typing indicator if you are going to respond'")
    check("e ANTES da geração do modelo", pos_composing < pos_modelo,
          "depois do modelo não é 'digitando…', é 'digitei'")

    # ⛔ Nunca simular "digitando…" com texto.
    check("nenhum texto de produto diz 'digitando'",
          "digitando..." not in fonte.replace("digitando…", ""),
          "⛔ presença é presença; frase é frase")


# ===========================================================================
# B4b — A FLAG DESLIGADA SILENCIA TUDO
# ===========================================================================
def b4b():
    _p("\n[B4b] `PRESENCA_DIGITANDO_LIGADA` nasce desligada, e desligada não chama nada")
    from app.core.config import settings

    check("o padrão do produto é DESLIGADO",
          getattr(settings, "PRESENCA_DIGITANDO_LIGADA", None) is False,
          "falhar para o lado de não prometer")

    provider = _ProviderDuble()
    servico = fachada_com(provider)
    asyncio.run(presenca_real(False, servico)(INTEGRACAO, TEL, "composing", 25000))
    check("com a flag desligada: ZERO chamadas", provider.chamadas == [],
          f"{provider.chamadas!r}")

    asyncio.run(presenca_real(True, servico)(INTEGRACAO, TEL, "composing", 25000))
    check("com a flag ligada: UMA chamada", len(provider.chamadas) == 1,
          f"{provider.chamadas!r}")
    check("e ela é `composing`", provider.chamadas[0]["state"] == "composing")


# ===========================================================================
# B4c — O TETO DE 25 s
# ===========================================================================
def b4c():
    _p("\n[B4c] O `delay` nunca passa de 25 000 ms — o número da Meta")
    provider = _ProviderDuble()
    servico = fachada_com(provider)
    chamar = presenca_real(True, servico)
    asyncio.run(chamar(INTEGRACAO, TEL, "composing", 300_000))
    check("um delay de 300 s é cortado no teto",
          provider.chamadas and provider.chamadas[-1]["delay"] <= 25_000,
          f"{provider.chamadas[-1] if provider.chamadas else None!r}")

    # E o teto também vive no provider — as duas pontas, porque quem chama pode
    # mudar e o wire não pode prometer 5 minutos de "digitando…".
    from app.services.whatsapp.providers.evolution_go import EvolutionGoProvider

    enviados = []

    class _GO(EvolutionGoProvider):
        def __init__(self):
            self._base_url, self._token, self._instance_id = "http://x", "t", "i"
            self._integration_id = self._company_id = None
            self._ja_tentou_curar = False

        def _post(self, path, payload):
            enviados.append((path, payload))
            return SendResult(ok=True)

    go = _GO()
    go.send_presence(TEL, "composing", 999_999)
    check("o EvolutionGoProvider também corta em 25 000",
          enviados and enviados[-1][1]["delay"] == 25_000, f"{enviados!r}")
    check("🔴 e a rota é a MEDIDA no swagger do fork: /message/presence",
          enviados[-1][0] == "/message/presence",
          "⛔ /chat/sendPresence é do Evolution Node e devolve 404 aqui (D1)")
    check("o corpo tem os quatro campos do schema do GO",
          set(enviados[-1][1]) == {"number", "state", "delay", "isAudio"},
          f"{enviados[-1][1]!r}")

    recusado = go.send_presence(TEL, "pensando", 1000)
    check("um `state` fora do enum é RECUSADO, não enviado",
          recusado.ok is False and len(enviados) == 1,
          "o enum é deles; inventar um valor é um 400 silencioso")
    check("o teto do delay e o teto da rajada são a MESMA constante (25)",
          __import__("app.services.message_buffer_service", fromlist=["x"]
                     ).TETO_DA_RAJADA_SEGUNDOS * 1000 == 25_000)


# ===========================================================================
# B4d — PROVIDER SEM A CAPACIDADE
# ===========================================================================
def b4d():
    _p("\n[B4d] Provider que não anuncia `presence`: 0 chamadas, 0 erro")
    provider = _ProviderDuble(tem_presenca=False)
    servico = fachada_com(provider)
    saiu = servico.send_presence(TEL, "composing", INTEGRACAO, 5000)
    check("a fachada devolve False sem chamar o provider",
          saiu is False and provider.chamadas == [], f"{provider.chamadas!r}")

    check("`presence` é uma flag do conjunto FECHADO de capacidades",
          "presence" in ProviderCapabilities.__dataclass_fields__,
          "o próprio base.py manda começar pela flag")
    check("e ela nasce False para quem não a implementa",
          ProviderCapabilities().presence is False)

    from app.services.whatsapp.providers.evolution_go import _GO_CAPABILITIES
    from app.services.whatsapp.providers.uazapi import _UAZAPI_CAPABILITIES
    from app.services.whatsapp.providers.zapi import _ZAPI_CAPABILITIES

    check("o Evolution GO anuncia presence=True (foi medido no swagger)",
          _GO_CAPABILITIES.presence is True)
    check("z-api e uazapi continuam sem presença — e a fachada não os chama",
          _ZAPI_CAPABILITIES.presence is False
          and _UAZAPI_CAPABILITIES.presence is False)

    # A rota legada z-api nem chega ao registry.
    zapi = _ProviderDuble()
    servico_zapi = fachada_com(zapi)
    servico_zapi.send_presence(TEL, "composing", {"provider": "z-api"}, 1000)
    check("integração z-api não chama presença nenhuma", zapi.chamadas == [])


# ===========================================================================
# B4e — `paused` AO FIM, INCLUSIVE NO DESCARTE
# ===========================================================================
def b4e():
    _p("\n[B4e] `paused` ao terminar — e também quando o turno é descartado")
    fonte = io.open(WEBHOOK, encoding="utf-8").read()
    pausas = fonte.count('_presenca(integration, payload.phone, "paused")')
    check("há `paused` em mais de um desfecho", pausas >= 3,
          f"{pausas} — o envio, o takeover no meio do turno e o turno perdido")

    # O descarte por takeover e o descarte por posse perdida pausam ANTES de
    # devolver. Um "digitando…" pendurado é a promessa vazia da E02.
    for marca in ("resposta do agente descartada", "rodada já respondeu"):
        pos = fonte.find(marca)
        check("o descarte '%s' pausa a presença" % marca[:28],
              pos > 0 and '_presenca(integration, payload.phone, "paused")'
              in fonte[pos:pos + 700])

    provider = _ProviderDuble()
    servico = fachada_com(provider)
    chamar = presenca_real(True, servico)
    asyncio.run(chamar(INTEGRACAO, TEL, "paused"))
    check("`paused` sai com delay 0", provider.chamadas[-1] ==
          {"to": TEL, "state": "paused", "delay": 0}, f"{provider.chamadas!r}")

    # ⛔ Presença que estoura NUNCA pode custar a resposta.
    class _ProviderQueExplode:
        capabilities = ProviderCapabilities(presence=True)

        def send_presence(self, *a, **k):
            raise RuntimeError("provedor fora do ar")

    servico_ruim = fachada_com(_ProviderQueExplode())
    try:
        saiu = servico_ruim.send_presence(TEL, "composing", INTEGRACAO, 1000)
        explodiu = False
    except Exception:  # noqa: BLE001
        saiu, explodiu = None, True
    check("provider que estoura não derruba o turno", not explodiu and saiu is False,
          "presença é enfeite; a resposta não é")


GATES = {"B4a": b4a, "B4b": b4b, "B4c": b4c, "B4d": b4d, "B4e": b4e}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
WH = "app/api/webhook.py"
GO = "app/services/whatsapp/providers/evolution_go.py"
SVC = "app/services/whatsapp_service.py"

MUTACOES = [
    # (a) 🔴 A MUTACAO DO CARD: presenca ANTES do portao de silencio -> o
    #     "digitando..." aparece para quem o agente vai CALAR.
    ("M-PRE1", WH,
     '        safe_phone = f"...{str(payload_dict.get(\'phone\', \'\'))[-4:]}"',
     '        safe_phone = f"...{str(payload_dict.get(\'phone\', \'\'))[-4:]}"\n'
     '        await _presenca(integration, payload.phone, "composing", 25000)  # MUTACAO',
     "B4a"),
    # (b) o teto do delay some na fachada -> promessa de 5 minutos
    ("M-PRE2", WH,
     "            min(int(delay_ms or 0), TETO_DA_RAJADA_SEGUNDOS * 1000),",
     "            int(delay_ms or 0),  # MUTACAO",
     "B4c"),
    # (c) o teto some no provider tambem
    ("M-PRE3", GO,
     "        atraso = max(0, min(int(delay_ms or 0), 25_000))",
     "        atraso = int(delay_ms or 0)  # MUTACAO",
     "B4c"),
    # (d) a fachada para de olhar a flag de capacidade -> chama quem nao sabe
    ("M-PRE4", SVC,
     '            if not getattr(provider.capabilities, "presence", False):\n'
     "                return False",
     "            pass  # MUTACAO",
     "B4d"),
    # (e) a flag de produto nasce LIGADA -> promete antes do canario
    ("M-PRE5", "app/core/config.py",
     "    PRESENCA_DIGITANDO_LIGADA: bool = False",
     "    PRESENCA_DIGITANDO_LIGADA: bool = True  # MUTACAO",
     "B4b"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate],
        # 🔴 `encoding` explicito: o cp1252 do Windows estoura no primeiro emoji
        # e uma mutacao VERMELHA vira "verde" sem ninguem ver.
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
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-ab-b4").name
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
        _p("  B4 -- DIGITANDO SO QUANDO VAI FALAR  (SPEC-EXTRA-001.2 §6.4)")
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


def test_digitando_so_quando_vai_falar():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
