# -*- coding: utf-8 -*-
"""O ponto de referência do pin não pode virar a rua — e `R.` é uma rua.

SPEC-118, fatia F5. 📊 **O defeito, medido em 26/09/2026** pela fatia F4 e
reconferido aqui em isolamento, antes do conserto:

```
parse_address_br('Posto Shell, R. Rafael Bandeira, 41 - Centro, '
                 'Florianopolis - SC, 88015-530')
   ->  rua    = 'Posto Shell'           ❌  o posto virou a rua
       bairro = 'R. Rafael Bandeira'    ❌  a rua virou o bairro
```

## Por que a abreviação não casava, e por que só `R.`

`_STREET_RE` listava as abreviações dentro de um grupo terminado por `\\b`:

```
\\b(?:rua|r\\.|av\\.?|...|linha)\\b
```

Depois de um ponto, `\\b` exige um **caractere de palavra** logo em seguida — e
`"R. Rafael"` traz um **espaço**. As outras abreviações escapavam por acaso: em
`av\\.?` o ponto é opcional, então o motor retrocede, casa só `av` e encontra a
fronteira entre `v` e `.`. `r\\.` não tem essa saída — o ponto é obrigatório, e a
alternativa **nunca podia casar**. Uma linha de sete alternativas com uma morta.

## Por que isto importa AGORA, e não é dívida cosmética

🔴 A Porto passou a fechar o formulário **com o pin de localização**, e o pin do
WhatsApp entrega `name` **mais** `address` na mesma linha
(`evolution_inbound._texto_de_localizacao`): o nome do lugar — um posto, um
mercado, um shopping — vem **antes** da rua. Sem reconhecer `R.`, o primeiro
segmento ganha por omissão e o guincho sai com o destino errado, **sem travar**.
É a classe do CLAUDE.md §9.5: o passo responde, ninguém vê, e chega ao segurado.

## As linhas de CONTROLE — sem elas este arquivo não prova nada

1. a **mesma via sem a abreviação** (`Rua Rafael Bandeira`) já estava certa antes
   do conserto: se ela passasse a falhar, o mérito não seria do conserto;
2. `Dr.` e `Sr.` **continuam não sendo logradouro** — o conserto não pode ter
   virado "qualquer letra seguida de ponto";
3. um endereço **sem ponto de referência nenhum** sai idêntico ao de antes.

⚠️ Tudo aqui chama o MOTOR (`parse_address_br` e `inject_address_slots`, os
mesmos que a produção usa). Nenhum helper deste arquivo reimplementa a regra
(CLAUDE.md §9.4). Nenhum endereço de pessoa: as vias são públicas e o número é
`0` ou o da própria captura mascarada.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLAYBOOKS_PY = RAIZ / "app" / "services" / "corridor_playbooks.py"


def _carregar(nome: str, caminho: Path):
    """O arquivo REAL de produção, sem subir os `__init__` da stack de IA."""
    nomes = ("app", "app.services")
    anteriores = {n: sys.modules.get(n) for n in nomes}
    injetados = [n for n in nomes if n not in sys.modules]
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location(nome, str(caminho))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[nome] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


PB = _carregar("app.services.corridor_playbooks", PLAYBOOKS_PY)

#: 📊 A primeira linha que `_texto_de_localizacao` monta quando o pin traz
#: `name` e `address` — `", ".join([rotulo, endereco])`. Via pública de
#: Florianópolis, número `41` da própria captura mascarada.
PIN_COM_PONTO_DE_REFERENCIA = (
    "Posto Shell, R. Rafael Bandeira, 41 - Centro, Florianopolis - SC, 88015-530"
)
#: A MESMA via, escrita por extenso. É a linha de controle.
PIN_SEM_ABREVIACAO = (
    "Posto Shell, Rua Rafael Bandeira, 41 - Centro, Florianopolis - SC, 88015-530"
)


def test_a_abreviacao_R_ponto_e_reconhecida_como_logradouro():
    fora = PB.parse_address_br(PIN_COM_PONTO_DE_REFERENCIA)
    assert fora.get("rua") == "R. Rafael Bandeira", (
        "o ponto de referencia do pin virou a rua: %r" % fora)
    assert fora.get("bairro") != "R. Rafael Bandeira", (
        "a rua virou bairro: %r" % fora)
    assert fora.get("numero") == "41", fora


def test_CONTROLE_a_mesma_via_POR_EXTENSO_continua_certa():
    """Se esta cair, o mérito do conserto seria creditado ao lugar errado."""
    fora = PB.parse_address_br(PIN_SEM_ABREVIACAO)
    assert fora.get("rua") == "Rua Rafael Bandeira", fora
    assert fora.get("numero") == "41", fora


def test_CONTROLE_abreviacao_de_TRATAMENTO_nao_e_logradouro():
    """`Dr.`/`Sr.` seguem fora: o conserto nao virou 'letra + ponto'."""
    for tratamento in ("Dr. Fulano de Tal", "Sr. Fulano de Tal"):
        alvo = "Mercado Central, %s, 0 - Centro, Sao Jose - SC" % tratamento
        fora = PB.parse_address_br(alvo)
        assert fora.get("rua") == "Mercado Central", (
            "%r passou a valer como logradouro: %r" % (tratamento, fora))


def test_CONTROLE_endereco_SEM_ponto_de_referencia_sai_igual():
    fora = PB.parse_address_br("R. Exemplo Um, 0, Centro, Florianopolis - SC")
    assert fora.get("rua") == "R. Exemplo Um", fora
    assert fora.get("cidade") == "Florianopolis", fora
    assert fora.get("uf") == "SC", fora


def test_o_MOTOR_que_a_producao_usa_leva_a_rua_certa_ao_corredor():
    """`inject_address_slots` e quem alimenta `local_rua`/`destino_rua`."""
    slots = PB.inject_address_slots({"local_atual": PIN_COM_PONTO_DE_REFERENCIA})
    assert slots.get("local_rua") == "R. Rafael Bandeira", slots
    assert slots.get("local_numero") == "41", slots


def test_a_rodovia_continua_com_caminho_PROPRIO():
    """Controle da lição de 03/08: rodovia nao tem numero de casa."""
    fora = PB.parse_address_br("Rodovia BR-101, km 150, Palhoca - SC")
    assert "numero" not in fora, fora
    assert "bairro" not in fora, fora
