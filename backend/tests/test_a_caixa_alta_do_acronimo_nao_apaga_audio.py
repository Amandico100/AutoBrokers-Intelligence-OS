"""A caixa alta do acrônimo não apaga áudio — nem outra vez.

A HISTÓRIA
----------
📊 Medido em 05/08/2026, sobre 2.655 áudios do acervo:

    grafia IGUAL à que pedíamos    directPath 2.654 · mediaKey 2.654
                                   mediaKeyTimestamp 2.655
    grafia DIFERENTE               fileSha256 0 · url 0

Um fator — a caixa das letras — e seis resultados. O Evolution GO serializa o
evento com `json.Marshal` do struct do whatsmeow, não com protojson, então as
chaves do webhook são as tags json = os nomes do **proto**: `fileSHA256`,
`fileEncSHA256`, `URL`. Nós pedíamos a grafia do Baileys e recebíamos nada —
sem erro, sem log, sem nada.

E o serializador está provado, não suposto: `mediaKeyTimestamp` chega como
**número** JSON, e protojson emitiria `int64` como string.

**É a segunda vez.** `selectedButtonId` × `selectedButtonID` já apagou 98,9%
dos cliques na leitura, pelo mesmo serializador, pela mesma causa. Este teste
existe para não haver uma terceira.

O QUE ELE GUARDA
----------------
Não guarda "a lista tem seis itens" — isso não é verdade nenhuma. Guarda que o
extrator **lê as duas grafias e grava sob um nome só**, e que o escondedor de
PII **cobre as duas eras** do banco.

A LINHA DE CONTROLE (CLAUDE.md §9.2)
------------------------------------
`teste_a_grafia_antiga_realmente_perdia` reconstrói o extrator ingênuo — o que
pede o nome exato — e prova que ele PERDE o payload do Go. Sem essa linha, um
teste que passa não distingue "o conserto funciona" de "o defeito nunca
existiu", e o mérito se credita ao lugar errado.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
ATLAS = os.path.join(RAIZ, "app", "services", "atlas")


def _carregar(nome: str, caminho: str):
    """Carrega o módulo PELO CAMINHO, sem passar pelo pacote `app`.

    Importar `app.services.atlas.observer_intake` puxa a cadeia inteira de
    configuração do backend — `pydantic_settings`, `redis`, `openai` — que não
    existe numa máquina de desenvolvimento. O teste reprovaria por ausência de
    dependência, não por defeito, e essa é a pior espécie de vermelho: ela
    ensina a ignorar o teste.

    Os dois módulos aqui só importam biblioteca padrão e `httpx` no topo. O que
    é pesado eles importam DENTRO das funções — e as funções que este teste
    exercita não chegam lá.
    """
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


# O ÚNICO DUBLÊ, e ele fica FORA do caminho do defeito.
#
# `_extract_content` importa quatro auxiliares de `evolution_inbound` para
# desembrulhar a mensagem e reconhecer resposta interativa. Para um
# `audioMessage`, os dois primeiros passos são identidade e "não é
# interativo" — e aí o código entra no laço de mídia, que é exatamente o que
# está sob teste.
#
# Dublar aqui não enfraquece nada: se o dublê estivesse errado, o teste
# explodiria em vez de passar. O laço de mídia é real, linha por linha.
_falso = types.ModuleType("app.services.whatsapp.evolution_inbound")
_falso._CHAVES_DE_ID = ()
_falso._CHAVES_DE_ROTULO = ()
_falso._INVOLUCROS_DE_RESPOSTA = ()
_falso._interactive_from_message = lambda _m: None
_falso._niveis_de = lambda _m: []
_falso._primeiro_valor = lambda *_a, **_k: None
_falso._unwrap_message = lambda m: m if isinstance(m, dict) else {}
for _p in ("app", "app.services", "app.services.whatsapp"):
    sys.modules.setdefault(_p, types.ModuleType(_p))
sys.modules["app.services.whatsapp.evolution_inbound"] = _falso

intake = _carregar("_intake_sob_teste", os.path.join(ATLAS, "observer_intake.py"))
midia = _carregar("_midia_sob_teste", os.path.join(ATLAS, "observer_media.py"))

FALHAS: list = []


def checar(condicao: bool, descricao: str) -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  X     {descricao}")
        FALHAS.append(descricao)


# O payload REAL do Evolution GO: acrônimos em maiúscula, mediaKeyTimestamp
# como número (a assinatura do `encoding/json`).
AUDIO_DO_GO = {
    "audioMessage": {
        "URL": "https://mmg.whatsapp.net/v/t62.7117-24/exemplo.enc",
        "directPath": "/v/t62.7117-24/exemplo.enc",
        "mediaKey": "bWVkaWFLZXlGYWxzYQ==",
        "fileEncSHA256": "ZmlsZUVuY1NoYUZhbHNv",
        "fileSHA256": "ZmlsZVNoYUZhbHNv",
        "mediaKeyTimestamp": 1754400000,
        "mimetype": "audio/ogg; codecs=opus",
        "seconds": 22,
        "fileLength": 41234,
    }
}

# O payload do Baileys: a grafia que a lista antiga pedia.
AUDIO_DO_BAILEYS = {
    "audioMessage": {
        "url": "https://mmg.whatsapp.net/v/t62.7117-24/exemplo.enc",
        "directPath": "/v/t62.7117-24/exemplo.enc",
        "mediaKey": "bWVkaWFLZXlGYWxzYQ==",
        "fileEncSha256": "ZmlsZUVuY1NoYUZhbHNv",
        "fileSha256": "ZmlsZVNoYUZhbHNv",
        "mediaKeyTimestamp": "1754400000",
        "mimetype": "audio/ogg; codecs=opus",
        "seconds": 22,
    }
}


def teste_a_grafia_antiga_realmente_perdia() -> None:
    """CONTROLE. O extrator ingênuo perde o payload do Go — prove antes de crer."""
    print("\n[1] CONTROLE: os dois lados conseguem ser diferentes")
    antigas = ("directPath", "mediaKey", "fileEncSha256", "fileSha256",
               "mediaKeyTimestamp", "url")
    m = AUDIO_DO_GO["audioMessage"]
    achadas = [c for c in antigas if m.get(c) not in (None, "")]
    checar(sorted(achadas) == ["directPath", "mediaKey", "mediaKeyTimestamp"],
           f"a lista antiga acha só 3 de 6 no payload do Go: {sorted(achadas)}")
    checar("fileSHA256" not in antigas and "URL" not in antigas,
           "e ela nem conhece as grafias que o Go usa")


def teste_o_extrator_le_as_duas_grafias() -> None:
    """O conserto: as duas eras entram, sob o mesmo nome de destino."""
    print("\n[2] O extrator lê Go E Baileys")
    _extract_content = intake._extract_content

    for rotulo, payload in (("Go", AUDIO_DO_GO), ("Baileys", AUDIO_DO_BAILEYS)):
        kind, _texto, _inter, meta = _extract_content(payload)
        meta = meta or {}
        checar(kind == "audio", f"{rotulo}: reconhecido como áudio")
        for coord in ("directPath", "mediaKey", "fileEncSHA256",
                      "fileSHA256", "mediaKeyTimestamp"):
            checar(meta.get(coord) not in (None, ""),
                   f"{rotulo}: {coord} foi guardado")
        checar(meta.get("segundos") == 22, f"{rotulo}: a duração veio junto")


def teste_o_destino_e_um_nome_so() -> None:
    """Uma coordenada, uma chave. Não uma por fornecedor."""
    print("\n[3] O banco não ganha duas chaves para a mesma coisa")
    _extract_content = intake._extract_content

    _k, _t, _i, meta = _extract_content(AUDIO_DO_BAILEYS)
    meta = meta or {}
    checar("fileSha256" not in meta,
           "a grafia do Baileys NÃO vira chave própria no banco")
    checar(meta.get("fileSHA256") == "ZmlsZVNoYUZhbHNv",
           "ela é gravada sob o nome canônico do proto")


def teste_o_escondedor_cobre_as_duas_eras() -> None:
    """PII: a lista de esconder não pode encolher quando a de gravar muda."""
    print("\n[4] Nenhuma coordenada vaza — em nenhuma das duas grafias")
    sem_coordenadas = intake.sem_coordenadas

    for rotulo, meta in (
        ("grafia nova (Go)", {"kind": "audio", "directPath": "/v/x", "mediaKey": "K",
                              "fileEncSHA256": "H", "fileSHA256": "H2", "URL": "https://x"}),
        ("grafia antiga (já no banco)", {"kind": "audio", "directPath": "/v/x",
                                         "mediaKey": "K", "fileEncSha256": "H",
                                         "fileSha256": "H2", "url": "https://x"}),
    ):
        limpo = sem_coordenadas(meta) or {}
        vazou = [k for k in limpo
                 if k.lower() in {"directpath", "mediakey", "fileencsha256",
                                  "filesha256", "url"}]
        checar(not vazou, f"{rotulo}: nada vazou ({vazou or 'limpo'})")
        checar(limpo.get("download") == "recuperavel",
               f"{rotulo}: e a presença continua sendo informada")


def teste_o_atalho_do_base64() -> None:
    """Os bytes que já vieram no webhook não pedem segunda passada."""
    print("\n[5] O atalho sem rede")
    import base64 as b64

    _bytes_embutidos = midia._bytes_embutidos

    conteudo = b"OggS\x00fake audio bytes"
    blob, mimetype = _bytes_embutidos(
        {"base64": b64.b64encode(conteudo).decode(), "mimetype": "audio/ogg"})
    checar(blob == conteudo, "os bytes embutidos são lidos")
    checar(mimetype == "audio/ogg", "e o mimetype vem junto")

    vazio, _ = _bytes_embutidos({"audioMessage": {"directPath": "/v/x"}})
    checar(vazio == b"", "sem base64, devolve vazio e o caminho HTTP segue")

    grande, _ = _bytes_embutidos({"base64": b64.b64encode(b"x" * (60 * 1024 * 1024)).decode()})
    checar(grande == b"", "acima do teto de tamanho, recusa em vez de estourar")


def teste_a_frase_do_erro_chega_sem_url() -> None:
    """O 500 sozinho não distingue cinco consertos. A frase sim."""
    print("\n[6] O erro do provedor passa a ter nome")
    _frase_do_provedor = midia._frase_do_provedor

    class _Resp:
        def __init__(self, corpo):
            self._corpo = corpo

        def json(self):
            if self._corpo is None:
                raise ValueError("nao e json")
            return self._corpo

    checar(_frase_do_provedor(_Resp({"error": "no active session found"}))
           == "no active session found", "a frase do Go é preservada")

    com_url = _frase_do_provedor(
        _Resp({"error": "Failed to download audio: https://mmg.whatsapp.net/v/segredo.enc"}))
    checar("mmg.whatsapp.net" not in com_url and "<url>" in com_url,
           f"e a URL é apagada — coordenada não vai para log ({com_url!r})")

    checar(_frase_do_provedor(_Resp(None)) == "", "corpo não-JSON não derruba nada")
    checar(_frase_do_provedor(_Resp({"data": {"base64": "SEGREDO"}})) == "",
           "e nada além de `error` é lido — `data` pode ter conteúdo de cliente")


def teste_o_filtro_de_miniatura_filtra_mesmo() -> None:
    """Um filtro que não filtra é um comentário mentindo."""
    print("\n[7] A miniatura sai, na grafia do fio")
    _message_for_download = midia._message_for_download

    limpo = _message_for_download(
        {"imageMessage": {"JPEGThumbnail": "AAAA", "directPath": "/v/x"}})
    dentro = limpo["imageMessage"]
    checar("JPEGThumbnail" not in dentro, "JPEGThumbnail (grafia do Go) foi removida")
    checar(dentro.get("directPath") == "/v/x", "e a coordenada continua lá")


def main() -> int:
    print("=" * 72)
    print("A CAIXA ALTA DO ACRONIMO NAO APAGA AUDIO")
    print("=" * 72)
    for teste in (teste_a_grafia_antiga_realmente_perdia,
                  teste_o_extrator_le_as_duas_grafias,
                  teste_o_destino_e_um_nome_so,
                  teste_o_escondedor_cobre_as_duas_eras,
                  teste_o_atalho_do_base64,
                  teste_a_frase_do_erro_chega_sem_url,
                  teste_o_filtro_de_miniatura_filtra_mesmo):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            print(f"  X     {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}")

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"FALHOU — {len(FALHAS)} verificacoes")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O EXTRATOR LE AS DUAS GRAFIAS, E NENHUMA COORDENADA VAZA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
