"""Mídia tem de ser recuperável — e a chave dela não pode vazar. SPEC-052/054.

O que foi perdido, medido em 30/07/2026
---------------------------------------
    3.653 áudios capturados
        0 com bytes guardados
        0 com chave de download
       26 presos em `pending` · 11 com falha de HTTP

Dentro deles estava o treinamento de emissão de seis seguradoras, que um
destilador encontrou citado em conversa e não existe escrito em lugar nenhum:

> "o passo a passo de emissão por seguradora existe apenas como áudios de
>  WhatsApp não transcritos. Esse conhecimento não entrou no acervo e se perde
>  com o canal."

Não foi descuido de ninguém. A captura guardava a FICHA — duração, tamanho,
formato — e descartava `mediaKey` e `directPath`, que são o que permite buscar
o conteúdo depois. O worker recebia o payload inteiro pela fila do Redis e
funcionava enquanto a fila existisse; ela expira em três dias.

    ficha guardada + coordenadas descartadas = mídia irrecuperável
    ficha guardada + coordenadas guardadas   = mídia recuperável

A tensão que este arquivo protege
---------------------------------
`mediaKey` É uma chave de descriptografia. Ela precisa existir no banco para a
mídia ser recuperável e NÃO pode aparecer em resposta de API — CLAUDE.md §13.3.
As duas exigências puxam para lados opostos, e o erro fácil é resolver uma e
esquecer a outra.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m

# `_extract_content` importa o desembrulhador do inbound da Evolution, e esse
# módulo puxa a configuração inteira do app (pydantic_settings, openai...). Nada
# disso participa da decisão que este arquivo testa — qual campo é guardado e
# qual é escondido. Stub mínimo: desembrulhar é devolver a própria mensagem.
for _n in ("app.services.whatsapp", "app.services.whatsapp.evolution_inbound"):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        if _n.endswith("evolution_inbound"):
            _m._unwrap_message = lambda msg: msg
            _m._interactive_from_message = lambda msg: None
        sys.modules[_n] = _m

_spec = importlib.util.spec_from_file_location(
    "app.services.atlas.observer_intake",
    os.path.join(RAIZ, "app", "services", "atlas", "observer_intake.py"))
OI = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(OI)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _fonte(*p: str) -> str:
    with open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


# Um áudio como o WhatsApp entrega de verdade.
AUDIO = {"audioMessage": {
    "mimetype": "audio/ogg; codecs=opus", "seconds": 44, "fileLength": 100012,
    "ptt": True,
    "directPath": "/v/t62.7117-24/12345_67890_n.enc",
    "mediaKey": "aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789+/=",
    "fileEncSha256": "Zm9vYmFyZW5jc2hhMjU2dmFsdWVoZXJl",
    "fileSha256": "Zm9vYmFyc2hhMjU2dmFsdWVoZXJlMDAw",
    "mediaKeyTimestamp": 1753900000,
}}


def teste_a_captura_guarda_o_que_permite_buscar():
    print("\n[1] O áudio capturado hoje pode ser buscado amanhã")
    kind, _texto, _inter, meta = OI._extract_content(AUDIO)

    checar(kind == "audio", "reconhece como áudio")
    checar(meta.get("segundos") == 44, "guarda a duração")
    for chave in ("directPath", "mediaKey", "fileEncSha256"):
        checar(meta.get(chave) not in (None, ""), f"guarda `{chave}`",
               "sem isto a mídia é irrecuperável depois que a fila expira")
    checar(OI.sem_coordenadas(meta).get("download") == "recuperavel",
           "a ficha diz que é recuperável")


def teste_a_chave_nunca_sai_do_banco():
    print("\n[2] A chave existe no banco e não aparece na resposta")
    _k, _t, _i, meta = OI._extract_content(AUDIO)
    limpo = OI.sem_coordenadas(meta)

    for chave in OI.COORDENADAS_DE_MIDIA:
        checar(chave not in limpo, f"`{chave}` não sai",
               "CLAUDE.md §13.3: presença, nunca o valor")
    # O valor não pode reaparecer disfarçado dentro de outro campo.
    checar(AUDIO["audioMessage"]["mediaKey"] not in str(limpo),
           "o valor da mediaKey não aparece em lugar nenhum da saída")
    checar(limpo.get("segundos") == 44 and limpo.get("kind") == "audio",
           "o que não é segredo continua visível")


def teste_o_endpoint_admin_usa_o_escondedor():
    print("\n[3] Quem lê pelo admin não recebe a chave")
    src = _fonte("app", "api", "admin_atlas.py")
    bloco = src[src.find("def observer_report"):]
    bloco = bloco[:bloco.find("\n@router")] if "\n@router" in bloco else bloco

    checar("sem_coordenadas" in bloco, "o relatório passa media_meta pelo escondedor")
    checar('"media_meta": sem_coordenadas' in bloco,
           "sobrescreve o campo — não adiciona um limpo ao lado do sujo",
           "espalhar `{**e, ...}` sem trocar media_meta deixaria o original")


def teste_a_lista_de_segredos_e_uma_so():
    print("\n[4] Gravador e escondedor leem a mesma lista")
    src = _fonte("app", "services", "atlas", "observer_intake.py")

    checar(src.count("COORDENADAS_DE_MIDIA = (") == 1,
           "a lista é definida uma única vez")
    # Se a captura repetisse os nomes em literais, acrescentar uma chave nova
    # ao gravador e esquecer do escondedor publicaria um segredo — e ninguém
    # perceberia, porque o dado continuaria funcionando.
    gravador = src[src.find("for chave in"):src.find("return kind, str(m.get(\"caption\")")]
    checar("COORDENADAS_DE_MIDIA" in gravador,
           "o gravador usa a constante, não uma cópia dos nomes")
    checar('"mediaKey"' not in gravador,
           "não há segunda lista de nomes escrita à mão")


def teste_o_que_nao_e_midia_passa_intacto():
    print("\n[5] O escondedor não estraga o que não é mídia")
    checar(OI.sem_coordenadas(None) is None, "None continua None")
    checar(OI.sem_coordenadas({"kind": "list", "options": []}).get("options") == [],
           "meta de interativo passa inteiro")
    # Mídia sem coordenadas é o caso dos 3.653 já perdidos: precisa ser
    # distinguível de mídia recuperável, senão a auditoria não vê o rombo.
    checar(OI.sem_coordenadas({"kind": "audio", "segundos": 9}).get("download")
           == "sem coordenadas",
           "áudio sem coordenadas é declarado como tal")


if __name__ == "__main__":
    print("=" * 66)
    print("MÍDIA RECUPERÁVEL, CHAVE ESCONDIDA")
    print("=" * 66)
    teste_a_captura_guarda_o_que_permite_buscar()
    teste_a_chave_nunca_sai_do_banco()
    teste_o_endpoint_admin_usa_o_escondedor()
    teste_a_lista_de_segredos_e_uma_so()
    teste_o_que_nao_e_midia_passa_intacto()
    print("\n" + "=" * 66)
    if FALHAS:
        print(f"FALHOU ({len(FALHAS)})")
        for f in FALHAS:
            print(f"  - {f}")
        sys.exit(1)
    print("TUDO VERDE")
