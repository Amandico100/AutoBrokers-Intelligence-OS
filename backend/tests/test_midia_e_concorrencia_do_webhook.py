# -*- coding: utf-8 -*-
"""A mídia do segurado chega, e o produto não congela enquanto ela chega.

Cinco defeitos que o piloto de 09/09 encontraria no primeiro dia:

  1. FOTO GRANDE      acima de 5 MB o produto devolvia `None` em SILÊNCIO. O
                      segurado fotografava o para-choque e não voltava nada.
  2. VÍDEO            `videoMessage` não estava no mapa de mídia; sem legenda
                      virava `skip:no_text` e o cliente falava sozinho.
  3. ÁUDIO QUE FALHA  a frase enviada era "Erro ao processar áudio." — o
                      produto falando de si para quem descreveu uma batida.
  4. EVENT LOOP       `send_message` é síncrono (`requests` + `time.sleep`) e
                      era chamado direto de corrotina: um envio parava TODOS os
                      atendimentos por segundos (por trinta, num timeout).
  5. FILA SERIAL      o varredor do buffer processava uma conversa por vez; a
                      quarta pessoa esperava as três da frente.

COMO ESTES TESTES OLHAM O CÓDIGO
--------------------------------
`app.api.webhook` custa 📊 ~77 s só para importar (medido em 08/09/2026:
`python -c "import app.api.webhook"`). Um teste que o importasse seria um teste
que ninguém roda. Então os casos que precisam EXECUTAR uma função do webhook
carregam a função **do próprio fonte**, pelos nós reais da AST — é o código que
vai para produção, byte a byte, sem o custo dos imports do módulo. Editar
`webhook.py` muda o que estes testes executam; é essa a garantia que importa
(CLAUDE.md §9.4: o alvo é o MOTOR, não uma cópia dele).

Sem rede, sem Redis, sem banco.
"""

import ast
import asyncio
import io
import os
import sys
import time
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(RAIZ, "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

WEBHOOK = os.path.join(BACKEND, "app", "api", "webhook.py")

_falhas = []


def checar(condicao, oque, porque=""):
    if condicao:
        print(f"  [OK] {oque}")
    else:
        print(f"  [FALHOU] {oque} :: {porque}")
        _falhas.append(f"{oque} :: {porque}")
    assert condicao, f"{oque} :: {porque}"


# =============================================================================
# CARREGADOR: as funções REAIS do webhook.py, sem importar o módulo
# =============================================================================
def carregar_do_fonte(caminho, nomes, extras=None):
    """Executa, num namespace isolado, os nós do arquivo pedidos por nome.

    `nomes` aceita funções e constantes de módulo. `extras` injeta os dublês
    (httpx falso, logger mudo) que a função precisa para rodar sem rede.
    """
    fonte = open(caminho, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    escolhidos = []
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name in nomes:
            escolhidos.append(no)
        elif isinstance(no, ast.Assign):
            for alvo in no.targets:
                if isinstance(alvo, ast.Name) and alvo.id in nomes:
                    escolhidos.append(no)
                    break
    faltando = set(nomes) - {
        (n.name if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
         else n.targets[0].id) for n in escolhidos
    }
    checar(not faltando, f"todos os nomes pedidos existem em {os.path.basename(caminho)}",
           f"sumiram: {sorted(faltando)} — se foram renomeados, o teste precisa saber")

    modulo = ast.Module(body=escolhidos, type_ignores=[])
    ns = {"__name__": "webhook_recortado"}
    ns.update(extras or {})
    exec(compile(ast.fix_missing_locations(modulo), caminho, "exec"), ns)  # noqa: S102
    return ns


def carregar_do_webhook(nomes, extras=None):
    return carregar_do_fonte(WEBHOOK, nomes, extras)


class _LoggerMudo:
    def __getattr__(self, _nome):
        return lambda *a, **k: None


def _webhook_visao(image_bytes):
    """Namespace com `process_image_for_vision` real e o mundo todo dublado."""

    class _Resposta:
        content = image_bytes

        def raise_for_status(self):
            return None

    class _Cliente:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, _url):
            return _Resposta()

    httpx_falso = types.SimpleNamespace(AsyncClient=_Cliente)

    subidos = []

    class _Storage:
        def __init__(self, bucket):
            self.bucket = bucket

        def upload(self, path, blob, opts):
            subidos.append((self.bucket, path, len(blob)))
            return {"path": path}

        def create_signed_url(self, path, _ttl):
            return {"signedURL": f"https://exemplo.invalido/{self.bucket}/{path}"}

    supabase_falso = types.SimpleNamespace(
        storage=types.SimpleNamespace(from_=lambda b: _Storage(b)))

    from datetime import date
    from typing import Optional
    from uuid import uuid4

    ns = carregar_do_webhook(
        ["_LIMITE_DO_WHATSAPP_BYTES", "_LIMITE_DA_VISAO_BYTES", "FOTO_GRANDE_DEMAIS",
         "_TTL_MIDIA_S", "_url_de_midia", "_encolher_para_a_visao",
         "process_image_for_vision"],
        extras={"httpx": httpx_falso, "logger": _LoggerMudo(), "asyncio": asyncio,
                "date": date, "uuid4": uuid4, "Optional": Optional,
                "settings": types.SimpleNamespace(SUPABASE_URL="https://x.invalido")},
    )
    return ns, supabase_falso, subidos


def _jpeg_de(alvo_bytes):
    """Um JPEG REAL com pelo menos `alvo_bytes` — ruído não comprime."""
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001
        return None
    lado = 2200
    while lado <= 9000:
        img = Image.frombytes("RGB", (lado, lado), os.urandom(lado * lado * 3))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=97)
        dados = buf.getvalue()
        if len(dados) >= alvo_bytes:
            return dados
        lado = int(lado * 1.5)
    return dados


# =============================================================================
# [1] A FOTO DE 8 MB NÃO É DESCARTADA
# =============================================================================
def teste_a_foto_de_oito_megas_nao_e_descartada():
    print("\n[1] A foto de 8 MB do segurado chega ao produto")

    foto = _jpeg_de(8 * 1024 * 1024)
    if foto is None:
        # Sem Pillow não dá para FABRICAR um JPEG de 8 MB, mas a regra do teto
        # ainda pode ser provada com bytes quaisquer — a redução só é tentada
        # depois, e falhar nela não pode mais descartar a foto.
        foto = b"\xff\xd8\xff" + os.urandom(8 * 1024 * 1024)
    checar(len(foto) > 5 * 1024 * 1024,
           f"a foto de teste passa dos 5 MB antigos ({len(foto)} bytes)",
           "sem isso o teste não exercita nada")
    checar(len(foto) < 16 * 1024 * 1024, "e cabe no limite do WhatsApp")

    ns, supabase_falso, subidos = _webhook_visao(foto)
    url = asyncio.run(ns["process_image_for_vision"](
        "https://exemplo.invalido/foto.jpg", "empresa-1", supabase_falso))

    checar(url is not None,
           "a foto de 8 MB devolve uma URL — não é mais descartada",
           "era exatamente o defeito: `return None` mudo acima de 5 MB")
    checar(url is not ns["FOTO_GRANDE_DEMAIS"],
           "e não é o sentinela de 'grande demais' — 8 MB é foto normal hoje",
           f"veio {url!r}")
    checar(len(subidos) == 1 and subidos[0][0] == "chat-media",
           "os bytes foram para o storage da conversa",
           f"subidos={subidos}")

    # E o teto novo é o do canal, não um número inventado.
    checar(ns["_LIMITE_DO_WHATSAPP_BYTES"] == 16 * 1024 * 1024,
           "o teto é o do WhatsApp: 16 MB")


def teste_acima_de_dezesseis_megas_o_produto_explica():
    print("\n[2] Acima de 16 MB não há silêncio — há uma frase em português")

    ns, supabase_falso, subidos = _webhook_visao(b"\xff\xd8" + os.urandom(17 * 1024 * 1024))
    url = asyncio.run(ns["process_image_for_vision"](
        "https://exemplo.invalido/enorme.jpg", "empresa-1", supabase_falso))

    checar(url is ns["FOTO_GRANDE_DEMAIS"],
           "acima do limite do canal volta o SENTINELA, não `None`",
           "`None` é 'falhei e não sei explicar'; aqui o produto sabe explicar")
    checar(not subidos, "e nada foi enviado ao storage")

    # A frase que o segurado lê existe, é humana e pede a próxima ação.
    fonte = open(WEBHOOK, encoding="utf-8").read()
    frase = carregar_do_webhook(["AVISO_DE_FOTO_GRANDE"])["AVISO_DE_FOTO_GRANDE"]
    for proibido in ("erro", "Erro", "None", "5MB", "byte", "processar"):
        checar(proibido not in frase,
               f"o aviso da foto não fala '{proibido}' com o segurado",
               f"frase: {frase!r}")
    checar("?" in frase, "e ele termina pedindo alguma coisa — não é um beco",
           f"frase: {frase!r}")
    checar("AVISO_DE_FOTO_GRANDE" in fonte.split("AVISO_DE_FOTO_GRANDE =", 1)[1],
           "a constante é USADA, não só declarada",
           "uma frase declarada e nunca enviada é a mesma coisa que silêncio")


def teste_a_reducao_e_opcional_e_nao_derruba_nada():
    print("\n[3] A redução é um bônus, nunca um portão")

    ns = carregar_do_webhook(
        ["_encolher_para_a_visao"], extras={"logger": _LoggerMudo()})
    encolher = ns["_encolher_para_a_visao"]

    # Lixo que não é imagem: devolve None (e NÃO levanta) — e o chamador,
    # provado no teste [1], segue com os bytes originais.
    checar(encolher(b"isto nao e uma imagem", 1024) is None,
           "bytes que não são imagem devolvem None, sem exceção")

    foto = _jpeg_de(6 * 1024 * 1024)
    if foto is None:
        print("  [pulado] Pillow ausente neste ambiente — só o teto vale aqui")
        return
    menor = encolher(foto, 5 * 1024 * 1024)
    checar(menor is not None and len(menor) <= 5 * 1024 * 1024,
           f"com Pillow, {len(foto)} bytes cabem em 5 MB ({len(menor or b'')} bytes)",
           "a foto grande passa a ser ATENDIDA, não recusada")


# =============================================================================
# [4] O VÍDEO CHEGA
# =============================================================================
def _payload_de_video(caption=None):
    video = {"mimetype": "video/mp4", "seconds": 12}
    if caption is not None:
        video["caption"] = caption
    return {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999990000@s.whatsapp.net", "fromMe": False,
                    "id": "VID1"},
            "pushName": "Cliente",
            "message": {"videoMessage": video},
            "messageTimestamp": 1757000000,
        },
    }


def teste_o_video_sem_legenda_nao_e_mais_descartado():
    print("\n[4] O vídeo do segurado chega ao pipeline")
    from app.services.whatsapp.evolution_inbound import (
        MARCA_DO_VIDEO, normalize_evolution_inbound,
    )

    sem = normalize_evolution_inbound(_payload_de_video())
    checar(sem["skip"] is False,
           "vídeo SEM legenda não é mais ignorado",
           f"skip_reason={sem['skip_reason']} — era 'no_text', e o cliente "
           "ficava falando sozinho")
    checar(sem["skip_reason"] != "no_text", "e o motivo antigo sumiu")
    checar(sem["text"] == MARCA_DO_VIDEO,
           "ele chega como texto de contexto",
           f"veio {sem['text']!r}")
    checar(sem["media"] is None,
           "e NENHUM download é agendado — `media` continua vazio",
           "baixar vídeo exigiria storage e transcodificação que não existem")

    com = normalize_evolution_inbound(_payload_de_video("olha o estrago"))
    checar(com["skip"] is False, "vídeo COM legenda também passa")
    checar(com["text"].startswith(MARCA_DO_VIDEO),
           "o rótulo vem primeiro — o agente sabe que não há foto para analisar",
           f"veio {com['text']!r}")
    checar("olha o estrago" in com["text"],
           "e a legenda, que é a fala do cliente, não é engolida",
           f"veio {com['text']!r}")

    # CONTROLE (CLAUDE.md §9.2): o que já funcionava continua igual. Se o texto
    # comum também tivesse virado "[Cliente enviou um vídeo]", o teste acima
    # passaria pelo motivo errado.
    texto = normalize_evolution_inbound({
        "event": "messages.upsert",
        "data": {"key": {"remoteJid": "5511999990000@s.whatsapp.net", "fromMe": False,
                         "id": "T1"},
                 "message": {"conversation": "bati o carro"}},
    })
    checar(texto["text"] == "bati o carro" and not texto["skip"],
           "CONTROLE: mensagem de texto normal segue intacta",
           f"veio {texto['text']!r}")


def teste_a_figurinha_continua_ignorada_e_sem_erro():
    print("\n[5] Figurinha: ignorada em silêncio, e sem explodir")
    from app.services.whatsapp.evolution_inbound import normalize_evolution_inbound

    fig = normalize_evolution_inbound({
        "event": "messages.upsert",
        "data": {"key": {"remoteJid": "5511999990000@s.whatsapp.net", "fromMe": False,
                         "id": "S1"},
                 "message": {"stickerMessage": {"mimetype": "image/webp"}}},
    })
    checar(fig["skip"] is True and fig["skip_reason"] == "no_text",
           "figurinha continua sendo ignorada (decisão de produto)",
           f"veio skip={fig['skip']} reason={fig['skip_reason']}")
    checar(fig["media"] is None, "e não vira mídia para baixar")


# =============================================================================
# [6] A FRASE DO ÁUDIO QUE FALHA
# =============================================================================
def _literais_enviadas(fonte):
    """Todo texto literal que sai como argumento de um `send_message`."""
    arvore = ast.parse(fonte)
    achados = []
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        nome = no.func.attr if isinstance(no.func, ast.Attribute) else None
        if nome != "send_message":
            continue
        for arg in list(no.args) + [k.value for k in no.keywords]:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                achados.append(arg.value)
        # `asyncio.to_thread(send, phone, texto, ...)` — o texto viaja como
        # argumento do to_thread, não do send_message.
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) \
                and no.func.attr == "to_thread":
            for arg in list(no.args) + [k.value for k in no.keywords]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    achados.append(arg.value)
    return achados


def teste_o_audio_que_falha_fala_como_gente():
    print("\n[6] A frase do áudio que falha")
    fonte = open(WEBHOOK, encoding="utf-8").read()

    enviadas = _literais_enviadas(fonte)
    checar("Erro ao processar áudio." not in enviadas,
           "a frase antiga NÃO é mais enviada a ninguém",
           f"ainda sai como texto: {[e for e in enviadas if 'Erro ao' in e]}")

    frase = carregar_do_webhook(["AVISO_DE_AUDIO_ILEGIVEL"])["AVISO_DE_AUDIO_ILEGIVEL"]
    checar("Erro" not in frase and "erro" not in frase,
           "a frase nova não devolve o erro do produto para o segurado",
           f"frase: {frase!r}")
    checar(frase.rstrip().endswith("?"),
           "ela termina numa pergunta — dá o próximo passo a quem está parado",
           f"frase: {frase!r}")

    # E O PORTÃO CONTINUA LÁ. Trocar a frase não pode ter soltado a trava: o
    # produto só fala com o agente LIGADO (`attendance_agent_active`), e erro
    # de leitura é silêncio.
    i = fonte.find("AVISO_DE_AUDIO_ILEGIVEL,")
    checar(i > 0, "o envio da frase nova existe no caminho do áudio")
    janela = fonte[max(0, i - 1800):i]
    checar("attendance_agent_active" in janela,
           "a permissão é consultada ANTES de responder o áudio",
           "era o furo da SPEC-065 — o sistema falava 115 linhas antes do portão")
    checar("_pode_falar = False" in janela,
           "e continua fail-closed: erro de leitura vira silêncio")


# =============================================================================
# [7] NENHUM ENVIO SÍNCRONO NO EVENT LOOP
# =============================================================================
_ENVIOS = ("send_message", "send_image", "send_audio")


def envios_sincronos_em_corrotina(fonte):
    """Chamadas diretas a `whatsapp_service.send_*` no corpo de um `async def`.

    Nested `def`/`lambda` são pulados de propósito: eles são funções SÍNCRONAS
    entregues a outro motor, que as chama como `callable(...)`. Envolvê-las em
    `to_thread` faria o envio virar uma corrotina que ninguém aguarda — o
    corredor da seguradora pararia em silêncio. O defeito real, e o conserto
    local, é a chamada direta no corpo da corrotina.
    """
    arvore = ast.parse(fonte)
    culpadas = []

    def _direto(no, dentro_de_corrotina):
        for filho in ast.iter_child_nodes(no):
            if isinstance(filho, (ast.FunctionDef, ast.Lambda)):
                continue  # sync callback: contrato de outro motor
            if isinstance(filho, ast.AsyncFunctionDef):
                _direto(filho, True)
                continue
            if dentro_de_corrotina and isinstance(filho, ast.Call) \
                    and isinstance(filho.func, ast.Attribute) \
                    and filho.func.attr in _ENVIOS:
                culpadas.append(f"{filho.func.attr}:{filho.lineno}")
            _direto(filho, dentro_de_corrotina)

    for no in arvore.body:
        if isinstance(no, ast.AsyncFunctionDef):
            _direto(no, True)
        else:
            _direto(no, False)
    return culpadas


def teste_nenhum_envio_bloqueia_o_event_loop():
    print("\n[7] Nenhum envio síncrono direto dentro de corrotina")

    # CONTRAPROVA PRIMEIRO: o detector CONSEGUE ficar vermelho. Sem isto ele é
    # carimbo, não guarda (CLAUDE.md §9.3).
    doente = ("import asyncio\n"
              "async def responde(payload, integration):\n"
              "    whatsapp_service.send_message(payload.phone, 'oi', integration)\n")
    checar(len(envios_sincronos_em_corrotina(doente)) == 1,
           "CONTRAPROVA: o detector acusa a chamada direta",
           "um detector que nunca acusa passa sempre")

    curado = ("import asyncio\n"
              "async def responde(payload, integration):\n"
              "    await asyncio.to_thread(whatsapp_service.send_message,\n"
              "                            payload.phone, 'oi', integration)\n")
    checar(envios_sincronos_em_corrotina(curado) == [],
           "e absolve a versão com to_thread",
           "se acusasse as duas, ele não estaria medindo o que diz medir")

    fonte = open(WEBHOOK, encoding="utf-8").read()
    culpadas = envios_sincronos_em_corrotina(fonte)
    checar(not culpadas,
           "webhook.py: todo envio dentro de corrotina passa por to_thread",
           f"congelam o loop: {culpadas}")

    # E o guarda tem de estar olhando alguma coisa: se `to_thread` sumisse dos
    # envios, o teste acima ficaria verde por não haver envio nenhum.
    checar(fonte.count("asyncio.to_thread(\n                    whatsapp_service") +
           fonte.count("asyncio.to_thread(\n                            whatsapp_service") +
           fonte.count("asyncio.to_thread(\n            whatsapp_service") +
           fonte.count("asyncio.to_thread(\n                whatsapp_service") > 0,
           "e existem envios de verdade atrás do to_thread",
           "zero envios encontrados = o guarda não está guardando ninguém")


# =============================================================================
# [8] A FILA DO BUFFER É PARALELA
# =============================================================================
BUFFER_PY = os.path.join(BACKEND, "app", "tasks", "buffer_processor.py")


def carregar_buffer_processor():
    """O motor REAL do varredor, recortado do fonte — sem Redis e sem `app`.

    ⚠️ 📊 Medido em 08/09/2026: rodando a suíte inteira, `import
    app.tasks.buffer_processor` morria com `ModuleNotFoundError: No module named
    'app.core.redis'` — e o módulo existe. `test_o_sinistro_deixa_rastro.py`
    monta um pacote `app` SINTÉTICO em `sys.modules` para não pagar os 77 s de
    import do webhook, e não o desfaz. Quem roda depois dele herda um `app` que
    não é o `app`, e o import de qualquer submódulo real quebra.

    Um teste que fica vermelho por causa do vizinho não mede o produto: mede a
    ordem de coleta. Aqui vale a MESMA técnica do webhook — os nós reais da AST,
    lidos do mesmo disco, sem os imports de topo que o varredor só usa no
    `check_buffers` (Redis, APScheduler), que este teste não exercita.
    """
    return carregar_do_fonte(
        BUFFER_PY,
        ["_PARALELISMO_PADRAO", "_env_int", "processar_buffers_prontos"],
        extras={"asyncio": asyncio, "os": os, "logger": _LoggerMudo()},
    )


class _BufferFalso:
    """Dublê do `message_buffer_service` — nada de Redis."""

    def __init__(self, chaves_que_explodem=()):
        self.explodem = set(chaves_que_explodem)
        self.entregues = []

    async def should_process(self, _chave):
        return True

    async def get_and_clear_buffer(self, chave):
        return {"payload": {"phone": "x", "_chave": chave},
                "messages": [f"msg de {chave}"]}

    def get_combined_message(self, buffer):
        return "\n".join(buffer["messages"])


async def _processador_lento(payload_dict=None, combined_message=None,
                             buffered_messages=None):
    await asyncio.sleep(0.2)
    return True


def teste_o_buffer_processa_em_paralelo():
    print("\n[8] Quatro conversas prontas não fazem fila indiana")
    processar_buffers_prontos = carregar_buffer_processor()["processar_buffers_prontos"]

    chaves = [f"whatsapp_buffer:int-1:5511{n:09d}" for n in range(6)]
    servico = _BufferFalso()

    inicio = time.monotonic()
    resumo = asyncio.run(processar_buffers_prontos(
        chaves, servico, _processador_lento, paralelismo=6))
    gasto = time.monotonic() - inicio

    serial = len(chaves) * 0.2
    checar(resumo["processadas"] == len(chaves),
           f"as {len(chaves)} conversas foram processadas",
           f"resumo={resumo}")
    checar(gasto < serial,
           f"em {gasto:.2f}s — menos que os {serial:.2f}s da fila indiana",
           "se não bateu, o gather não está paralelizando de verdade")

    # CONTROLE: com teto 1 o mesmo motor volta a ser serial. É ele que dá
    # direito à conclusão acima — sem ele, um ambiente rápido "passaria" por
    # acaso e o mérito iria para o lugar errado (CLAUDE.md §9.2).
    inicio = time.monotonic()
    asyncio.run(processar_buffers_prontos(
        chaves, _BufferFalso(), _processador_lento, paralelismo=1))
    gasto_serial = time.monotonic() - inicio
    checar(gasto_serial >= serial * 0.9,
           f"CONTROLE: com paralelismo=1 o mesmo motor leva {gasto_serial:.2f}s",
           "as duas medidas precisam CONSEGUIR ser diferentes")


def teste_uma_conversa_que_explode_nao_derruba_as_outras():
    print("\n[9] O defeito de uma pessoa não vira silêncio para todas")
    processar_buffers_prontos = carregar_buffer_processor()["processar_buffers_prontos"]

    chaves = [f"whatsapp_buffer:int-1:5511{n:09d}" for n in range(5)]
    vistos = []

    async def _as_vezes_explode(payload_dict=None, combined_message=None,
                                buffered_messages=None):
        chave = payload_dict["_chave"]
        if chave == chaves[0]:
            raise RuntimeError("integração fora do ar")
        vistos.append(chave)
        return True

    resumo = asyncio.run(processar_buffers_prontos(
        chaves, _BufferFalso(), _as_vezes_explode, paralelismo=4))

    checar(resumo["falhas"] == 1, f"a conversa que estourou foi contada ({resumo})")
    checar(resumo["processadas"] == len(chaves) - 1,
           "e todas as outras foram atendidas assim mesmo",
           f"resumo={resumo} — com `await` no `for`, a primeira exceção "
           "abortava a varredura inteira")
    checar(sorted(vistos) == sorted(chaves[1:]),
           "nenhuma conversa foi pulada por causa da vizinha")


def teste_o_teto_de_paralelismo_vem_do_ambiente():
    print("\n[10] O teto é regulável sem deploy")
    bp = carregar_buffer_processor()

    checar(bp["_PARALELISMO_PADRAO"] == 6, "o padrão é 6")
    antes = os.environ.get("WHATSAPP_BUFFER_PARALELISMO")
    try:
        os.environ["WHATSAPP_BUFFER_PARALELISMO"] = "2"
        chaves = [f"whatsapp_buffer:int-1:5511{n:09d}" for n in range(4)]
        inicio = time.monotonic()
        asyncio.run(bp["processar_buffers_prontos"](
            chaves, _BufferFalso(), _processador_lento))
        gasto = time.monotonic() - inicio
        checar(gasto >= 0.36,
               f"WHATSAPP_BUFFER_PARALELISMO=2 estreita a passagem ({gasto:.2f}s)",
               "se o env fosse ignorado, 4 conversas sairiam em ~0,2s")
        checar(gasto < 0.75,
               "e ainda assim é mais rápido que serial (~0,80s)",
               f"{gasto:.2f}s")
    finally:
        if antes is None:
            os.environ.pop("WHATSAPP_BUFFER_PARALELISMO", None)
        else:
            os.environ["WHATSAPP_BUFFER_PARALELISMO"] = antes


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("teste_") and callable(fn):
            fn()
    print("\nFALHAS:", _falhas or "nenhuma")
