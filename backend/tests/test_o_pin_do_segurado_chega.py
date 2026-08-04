"""O pin do segurado chega — o sistema não pergunta e depois joga a resposta fora.

📊 03/08/2026, teste adversarial do atendimento. O agente pergunta *"onde você
está?"*. A pessoa no acostamento faz a coisa mais rápida que o WhatsApp oferece
e manda o **pin de localização**. Em `evolution_inbound.py`, o laço de mídia
conhecia imagem, documento e áudio — não conhecia `locationMessage`. Sem texto e
sem mídia, `normalize_evolution_inbound` devolvia `skip: no_text`.

O sistema ficava **mudo para a única resposta que ele mesmo tinha pedido.**

O conserto tem três exigências, e a terceira é a que separa conserto de remendo:

  1. o pin vira texto, com a coordenada que o guincho usa;
  2. `name`/`address` entram — e ANTES da coordenada, porque `parse_address_br`
     lê endereço, não par de floats;
  3. **`(0, 0)` não vira coordenada.** É o default do protobuf para um `double`
     não preenchido, não a Ilha Nula no golfo da Guiné. Errar com confiança
     mandaria o guincho para o meio do Atlântico.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

_falhas: list[str] = []


def checar(condicao: bool, descricao: str, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok    {descricao}")
    else:
        print(f"  FALHA {descricao}" + (f" — {detalhe}" if detalhe else ""))
        _falhas.append(descricao)


def _carregar(rel: str, nome: str):
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    for pkg in ("app", "app.services", "app.services.whatsapp"):
        if pkg not in sys.modules:
            casca = types.ModuleType(pkg)
            casca.__path__ = [str(RAIZ / pkg.replace(".", "/"))]  # type: ignore[attr-defined]
            sys.modules[pkg] = casca
    spec = importlib.util.spec_from_file_location(nome, RAIZ / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


INB = _carregar("app/services/whatsapp/evolution_inbound.py", "evo_inbound_pin")
CP = _carregar("app/services/corridor_playbooks.py", "cp_pin")


def _evento(mensagem: dict) -> dict:
    """Um `messages.upsert` real do Evolution, com o mínimo que o normalizador lê."""
    return {
        "event": "messages.upsert",
        "instance": "corretora-1",
        "data": {
            "key": {"remoteJid": "5548999990000@s.whatsapp.net", "fromMe": False, "id": "PIN1"},
            "pushName": "Segurado",
            "messageTimestamp": 1754200000,
            "message": mensagem,
        },
    }


def o_pin_simples_deixa_de_ser_descartado() -> None:
    """O caso do teste adversarial: pin puro, sem nome nem endereço."""
    out = INB.normalize_evolution_inbound(_evento({
        "locationMessage": {"degreesLatitude": -27.5945, "degreesLongitude": -48.5477}
    }))
    checar(out["skip"] is False, "o pin NAO e mais descartado",
           f"skip_reason={out['skip_reason']}")
    checar(out["skip_reason"] != "no_text",
           "e o motivo `no_text` sumiu deste caminho")
    texto = out["text"] or ""
    checar("-27.5945" in texto and "-48.5477" in texto,
           "as duas coordenadas estao no texto", texto)
    checar("," in texto and "-27.5945,-48.5477" in texto,
           "no formato lat,lon que o guincho usa", texto)
    checar("ocaliza" in texto,
           "e o texto DIZ que e uma localizacao — quem le sabe o que sao os numeros",
           texto)


def o_nome_e_o_endereco_vem_junto_e_primeiro() -> None:
    """A ordem importa: `parse_address_br` le endereco, nao par de floats."""
    out = INB.normalize_evolution_inbound(_evento({
        "locationMessage": {
            "degreesLatitude": -27.5945,
            "degreesLongitude": -48.5477,
            "name": "Posto BR",
            "address": "Rua Bocaiuva, 2468 - Centro, Florianopolis - SC",
        }
    }))
    texto = out["text"] or ""
    checar(out["skip"] is False, "pin com endereco tambem passa")
    checar("Posto BR" in texto, "o NOME do lugar entra no texto", texto)
    checar("Rua Bocaiuva, 2468" in texto, "o ENDERECO do pin entra no texto", texto)
    checar(texto.index("Rua Bocaiuva") < texto.index("-27.5945"),
           "e o endereco vem ANTES da coordenada", texto)
    checar(texto.splitlines()[0].endswith("SC"),
           "e a coordenada esta em OUTRA LINHA — endereco e uma linha",
           repr(texto))

    # A prova de que a ordem serve para alguma coisa: o parser do corredor
    # extrai rua/numero/bairro/cidade/UF deste mesmo texto.
    #
    # 📊 Este era o achado: com a coordenada colada na mesma linha, `cidade`
    # saia `'48.5477'`. Uma cidade chamada 48.5477 nao e deducao ruim, e
    # invencao — e ela vai para a URA da seguradora como se fosse verdade.
    end = CP.parse_address_br(texto)
    checar(end.get("rua") == "Rua Bocaiuva", f"o corredor le a rua: {end.get('rua')!r}", str(end))
    checar(end.get("numero") == "2468", f"e o numero: {end.get('numero')!r}", str(end))
    checar(end.get("bairro") == "Centro", f"e o bairro: {end.get('bairro')!r}", str(end))
    checar(end.get("cidade") == "Florianopolis", f"e a cidade: {end.get('cidade')!r}", str(end))
    checar(end.get("uf") == "SC", f"e a UF: {end.get('uf')!r}", str(end))
    checar("48.5477" not in str(end),
           "e NENHUM campo de endereco recebeu a coordenada", str(end))


def a_live_location_tambem_chega() -> None:
    """`liveLocationMessage` e outro tipo — e quem esta em movimento importa mais."""
    out = INB.normalize_evolution_inbound(_evento({
        "liveLocationMessage": {
            "degreesLatitude": -23.5505,
            "degreesLongitude": -46.6333,
            "caption": "estou andando ate o posto",
        }
    }))
    texto = out["text"] or ""
    checar(out["skip"] is False, "a localizacao AO VIVO nao e descartada",
           f"skip_reason={out['skip_reason']}")
    checar("-23.5505" in texto and "-46.6333" in texto, "com as coordenadas", texto)
    checar("ao vivo" in texto.lower(), "e o texto diz que e AO VIVO", texto)
    checar("movimento" in texto.lower(),
           "avisando que a pessoa pode estar se movendo",
           "o guincho que vai ao ponto errado perde a corrida duas vezes")
    checar("estou andando ate o posto" in texto, "e a legenda do segurado nao se perde", texto)


def o_zero_zero_nao_vira_coordenada() -> None:
    """O guarda que impede errar com confianca.

    `(0, 0)` e o default do protobuf para `double` nao preenchido. Um pin com
    nome e sem coordenada chega assim — e mandar `0,0` ao guincho e pior que
    nao mandar nada, porque parece dado.
    """
    out = INB.normalize_evolution_inbound(_evento({
        "locationMessage": {"degreesLatitude": 0, "degreesLongitude": 0,
                            "name": "Oficina do Ze", "address": "Rua A, 10"}
    }))
    texto = out["text"] or ""
    checar(out["skip"] is False, "o pin com nome e sem coordenada ainda passa", texto)
    checar("0,0" not in texto and "0.0" not in texto,
           "e a coordenada (0,0) NAO e escrita como se fosse posicao", texto)
    checar("Oficina do Ze" in texto and "Rua A, 10" in texto,
           "o que o segurado de fato mandou continua la", texto)

    # E o pin COMPLETAMENTE vazio nao inventa mensagem nenhuma.
    vazio = INB.normalize_evolution_inbound(_evento({"locationMessage": {}}))
    checar(vazio["skip"] is True and vazio["skip_reason"] == "no_text",
           "pin totalmente vazio continua sendo `no_text` — nao se inventa resposta",
           f"skip={vazio['skip']} motivo={vazio['skip_reason']}")


def o_guarda_tem_como_falhar() -> None:
    """Um extrator que devolvesse texto para qualquer coisa passaria acima.

    Aqui ele precisa RECUSAR: mensagem que nao e pin nenhum segue `no_text`, e
    texto de verdade continua vencendo o pin.
    """
    for nome, msg in (
        ("reacao (so emoji, sem corpo)", {"reactionMessage": {"text": "\U0001f44d"}}),
        ("protocolo de sessao", {"senderKeyDistributionMessage": {"groupId": "x"}}),
    ):
        out = INB.normalize_evolution_inbound(_evento(msg))
        checar(out["skip"] is True and out["skip_reason"] == "no_text",
               f"{nome} NAO vira localizacao",
               f"virou texto: {out['text']!r}")

    # Texto de verdade continua tendo precedencia sobre o pin.
    out = INB.normalize_evolution_inbound(_evento({
        "conversation": "estou na BR-101",
        "locationMessage": {"degreesLatitude": -27.1, "degreesLongitude": -48.6},
    }))
    checar(out["text"] == "estou na BR-101",
           "e o texto escrito pelo segurado continua vencendo o pin",
           f"texto={out['text']!r}")


def o_pin_sobrevive_ao_embrulho() -> None:
    """Mensagem efemera embrulha o `locationMessage` — e o desembrulho ja existia."""
    out = INB.normalize_evolution_inbound(_evento({
        "ephemeralMessage": {"message": {
            "locationMessage": {"degreesLatitude": -30.0331, "degreesLongitude": -51.23}
        }}
    }))
    checar(out["skip"] is False and "-30.0331" in (out["text"] or ""),
           "pin dentro de mensagem efemera tambem chega",
           f"skip={out['skip']} texto={out['text']!r}")


def a_grafia_da_chave_nao_e_incidente() -> None:
    """A licao do P-56 (937 de 947 cliques numa grafia que ninguem previu).

    Quem serializa o protobuf escolhe o nome da chave e nao avisa. `latitude`
    e `degreesLatitude` sao o mesmo dado.
    """
    out = INB.normalize_evolution_inbound(_evento({
        "locationMessage": {"latitude": -27.5945, "longitude": -48.5477}
    }))
    checar(out["skip"] is False and "-27.5945" in (out["text"] or ""),
           "a grafia curta (`latitude`/`longitude`) tambem e lida",
           f"skip_reason={out['skip_reason']} texto={out['text']!r}")


def main() -> int:
    print(__doc__)
    print("== o pin simples deixa de ser descartado ==")
    o_pin_simples_deixa_de_ser_descartado()
    print("== o nome e o endereco vem junto, e primeiro ==")
    o_nome_e_o_endereco_vem_junto_e_primeiro()
    print("== a live location tambem chega ==")
    a_live_location_tambem_chega()
    print("== (0,0) nao vira coordenada ==")
    o_zero_zero_nao_vira_coordenada()
    print("== o guarda tem como falhar ==")
    o_guarda_tem_como_falhar()
    print("== o pin sobrevive ao embrulho ==")
    o_pin_sobrevive_ao_embrulho()
    print("== a grafia da chave nao e incidente ==")
    a_grafia_da_chave_nao_e_incidente()

    print()
    if _falhas:
        print(f"VERMELHO — {len(_falhas)} falha(s)")
        for f in _falhas:
            print(f"  - {f}")
        return 1
    print("O PIN DO SEGURADO CHEGA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
