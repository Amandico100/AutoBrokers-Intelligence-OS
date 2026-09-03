# -*- coding: utf-8 -*-
"""O manifesto de capacidade — SPEC-094 BLOCO C. **Ausente não é zero.**

Peça pura: `dataclasses`, `json`, `os`, `typing`. Lê o **censo medido** do
BLOCO 0 (`docs/canon/providers/infocap/`) e responde a UMA pergunta, antes de
qualquer cálculo:

> **A fonte consegue entregar o dado de que esta métrica precisa?**

## Os cinco estados, e por que `UNKNOWN` é o que mais importa

```
SUPPORTED    rota classe 200 medida + campo presente na amostra
PARTIAL      o dado existe, mas não no grão, na cobertura ou no lote que a
             métrica pede
UNAVAILABLE  🔴 MEDIDO: não há rota nem campo. Nunca inferido
UNKNOWN      🔴 NÃO medido nesta rodada. NUNCA se lê como "indisponível"
DEGRADED     o schema da rota MUDOU desde o censo. Ver o drift, abaixo
```

🔴 A distinção entre `UNAVAILABLE` e `UNKNOWN` é a coluna que sustenta esta
SPEC. 📊 O censo de 03/09/2026 mediu **um** `UNAVAILABLE` por ausência
comprovada (`financial.cashflow`: a rota não existe no Gateway) e **três**
`UNKNOWN` (`commission_reversals`, `commission_tax`, `producer_repasse_paid`),
que ninguém sondou.

As duas coisas produzem o mesmo `value` no envelope — `UNAVAILABLE`, porque não
há número. Produzem **frases diferentes**:

```
UNAVAILABLE  →  "a InfoCap não expõe isto"      é uma afirmação sobre a FONTE
UNKNOWN      →  "isto não foi verificado"       é uma afirmação sobre NÓS
```

Trocar a segunda pela primeira é afirmar sobre o produto do cliente algo que se
sabe apenas sobre a própria diligência. É a mutação **M2** — e é o motivo de
`bloqueio()` devolver o motivo junto com o veredito.

## O drift: a rota mudou, e uma métrica cai — não todas

📊 O censo gravou o `sha256` das chaves ordenadas de cada rota
(`infocap-schema-fingerprints.json`: 20 chaves na rota de produção, 33 na de
vencimentos). O adapter recalcula o mesmo hash **a cada leitura** e passa por
aqui.

🔴 Quando um fingerprint diverge, só as capacidades que **dependem daquela
rota** viram `DEGRADED`. As outras sobrevivem. É a mutação **M14**, e o
contrário — derrubar o relatório inteiro porque um campo novo apareceu numa
rota — seria trocar um aviso por um apagão.

⚠️ A proposta original pedia um *drift monitor* agendado (§94). Ele foi
recusado (§6): um cron que roda de hora em hora descobre o drift **depois** de
o número errado ter chegado ao dono. A comparação a cada leitura custa um
`sha256` sobre as chaves de uma linha.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# Os estados
# --------------------------------------------------------------------------
SUPPORTED = "SUPPORTED"
PARTIAL = "PARTIAL"
INDISPONIVEL = "UNAVAILABLE"
NAO_VERIFICADO = "UNKNOWN"
DEGRADED = "DEGRADED"
ESTADOS = (SUPPORTED, PARTIAL, INDISPONIVEL, NAO_VERIFICADO, DEGRADED)

#: 🔴 O que cada estado quer dizer, em uma frase, no idioma do Artifact. É esta
#: tabela que impede o produto de dizer "indisponível" sobre algo que só não foi
#: verificado.
FRASE_DO_ESTADO = {
    SUPPORTED: "medido e disponível",
    PARTIAL: "disponível em parte — o grão ou a cobertura não bastam",
    INDISPONIVEL: "não exposto pela fonte (medido: a rota não existe)",
    NAO_VERIFICADO: "não verificado nesta rodada — não é o mesmo que indisponível",
    DEGRADED: "o schema da rota mudou desde o censo: bloqueado até remedir",
}

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
DIRETORIO_DO_CENSO = os.path.join(_RAIZ, "docs", "canon", "providers")


# --------------------------------------------------------------------------
# Uma capacidade
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Capacidade:
    """O que o censo mediu sobre UMA capacidade."""

    nome: str
    state: str = NAO_VERIFICADO
    coverage_pct: Optional[float] = None
    source_routes: Tuple[str, ...] = ()
    evidence: str = ""

    @property
    def entrega_dado(self) -> bool:
        """`SUPPORTED` ou `PARTIAL`. Só estes dois deixam a métrica calcular."""
        return self.state in (SUPPORTED, PARTIAL)

    @property
    def foi_medida(self) -> bool:
        """🔴 `UNKNOWN` é a única resposta que significa *"ninguém olhou"*."""
        return self.state != NAO_VERIFICADO

    @property
    def exige_cobertura(self) -> bool:
        """`PARTIAL` e `DEGRADED` **obrigam** a métrica a declarar cobertura.

        📊 A razão está na `Cobertura` da 081: 19,4% das apólices de 2025 não
        têm produtor identificado, e um ranking que soma 80,6% e se apresenta
        como "o ano inteiro" mente por omissão. Cobertura omitida em métrica
        parcial é a mutação **M15**.
        """
        return self.state in (PARTIAL, DEGRADED)

    def frase(self) -> str:
        base = FRASE_DO_ESTADO.get(self.state, self.state)
        if self.coverage_pct is not None:
            return f"{base} (cobertura medida: {self.coverage_pct:.1f}%)"
        return base


# --------------------------------------------------------------------------
# O manifesto
# --------------------------------------------------------------------------
@dataclass
class ProviderCapabilityManifest:
    """O censo de um provider, em memória, com o drift desta leitura por cima.

    ⚠️ Ele é **por leitura**, não global: `conferir_drift` marca `DEGRADED`
    nesta instância. Duas corretoras lendo ao mesmo tempo não contaminam uma à
    outra porque cada leitura carrega o seu (`carregar_manifesto` devolve cópia).
    """

    provider_key: str
    measured_at: str = ""
    capacidades: Dict[str, Capacidade] = field(default_factory=dict)
    fingerprints_do_censo: Dict[str, str] = field(default_factory=dict)
    rotas_medidas: int = 0
    #: `capability → motivo`. Preenchido por `conferir_drift`.
    degradadas: Dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------ consulta
    def capacidade(self, nome: str) -> Capacidade:
        """A capacidade pedida — ou uma `UNKNOWN` explícita.

        🔴 Capacidade que o censo não conhece é `UNKNOWN`, **jamais**
        `UNAVAILABLE`. Perguntar por um nome que o censo não mediu é
        exatamente o caso de "não verificado".
        """
        if nome in self.degradadas:
            base = self.capacidades.get(nome)
            return Capacidade(
                nome=nome, state=DEGRADED,
                coverage_pct=base.coverage_pct if base else None,
                source_routes=base.source_routes if base else (),
                evidence=self.degradadas[nome])
        return self.capacidades.get(
            nome, Capacidade(nome=nome, state=NAO_VERIFICADO,
                             evidence="capacidade fora do censo: não verificada"))

    def estado(self, nome: str) -> str:
        return self.capacidade(nome).state

    def estados(self) -> Dict[str, str]:
        saida = {n: c.state for n, c in self.capacidades.items()}
        saida.update({n: DEGRADED for n in self.degradadas})
        return saida

    # -------------------------------------------------------------- drift
    def conferir_drift(self, fingerprints_medidos: Dict[str, str]) -> List[str]:
        """Compara os fingerprints desta leitura com os do censo.

        Devolve os avisos. 🔴 E marca `DEGRADED` **só** nas capacidades cujas
        `source_routes` incluem a rota que mudou — as outras sobrevivem (M14).

        ⚠️ Rota que o censo não fingerprintou **não** produz drift: não se pode
        afirmar mudança contra uma medição que não existe (seria inferência
        vestida de fato, CLAUDE.md §12.1).
        """
        avisos: List[str] = []
        for rota, medido in (fingerprints_medidos or {}).items():
            if rota.startswith("__") or not medido:
                continue
            esperado = self.fingerprints_do_censo.get(rota)
            if not esperado or esperado == medido:
                continue
            motivo = (f"o schema de {rota} mudou desde o censo "
                      f"({esperado[:8]}… → {medido[:8]}…): a métrica que depende "
                      f"desta rota fica bloqueada até remedir")
            avisos.append(motivo)
            for nome, cap in self.capacidades.items():
                if rota in cap.source_routes:
                    self.degradadas[nome] = motivo
        return avisos

    # ------------------------------------------------------------ bloqueio
    def bloqueio(self, requeridas: Sequence[str],
                 aceitos: Sequence[str] = (SUPPORTED, PARTIAL)) -> Tuple[bool, List[str]]:
        """`(bloqueada?, motivos)` para uma métrica que exige estas capacidades.

        🔴 O motivo é devolvido junto com o veredito de propósito. Sem ele o
        Artifact escreveria "indisponível" para os dois casos — e afirmar que a
        fonte não expõe algo que apenas não foi sondado é afirmar sobre o
        sistema do cliente o que só se sabe sobre a própria diligência (M2).

        ⚠️ `aceitos` existe porque nem toda métrica se contenta com o mesmo
        estado. 📊 A comissão RECEBIDA é `PARTIAL`: o dado existe, mas só no
        detalhe de UMA apólice por chamada — ler a carteira inteira custaria uma
        requisição por apólice. Para um número de carteira isso é indisponível
        na prática, e a métrica declara `aceitos=(SUPPORTED,)`.
        """
        motivos: List[str] = []
        bloqueada = False
        for nome in requeridas or ():
            cap = self.capacidade(nome)
            if cap.state in aceitos:
                if cap.state == PARTIAL:
                    motivos.append(f"{nome}: {cap.frase()}")
                continue
            bloqueada = True
            motivos.append(f"{nome}: {cap.frase()}")
        return bloqueada, motivos

    def exige_cobertura(self, requeridas: Sequence[str]) -> bool:
        """Alguma das capacidades pedidas obriga a declarar cobertura? (M15)"""
        return any(self.capacidade(n).exige_cobertura for n in (requeridas or ()))


# --------------------------------------------------------------------------
# A carga
# --------------------------------------------------------------------------
def _ler_json(caminho: str) -> Dict[str, Any]:
    if not os.path.exists(caminho):
        return {}
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f) or {}


def manifesto_de_dicionarios(provider_key: str, manifesto: Dict[str, Any],
                             fingerprints: Optional[Dict[str, Any]] = None
                             ) -> ProviderCapabilityManifest:
    """Monta o manifesto a partir do JSON já lido. Puro, e o que o teste usa."""
    capacidades: Dict[str, Capacidade] = {}
    for nome, corpo in (manifesto.get("capabilities") or {}).items():
        corpo = corpo if isinstance(corpo, dict) else {}
        estado = str(corpo.get("state") or NAO_VERIFICADO).strip().upper()
        if estado not in ESTADOS:
            # ⚠️ Estado desconhecido lê-se como NÃO VERIFICADO, nunca como
            # disponível: a interpretação otimista de um valor que ninguém
            # entendeu é como um campo novo vira número no relatório.
            estado = NAO_VERIFICADO
        cobertura = corpo.get("coverage_pct")
        capacidades[nome] = Capacidade(
            nome=nome, state=estado,
            coverage_pct=float(cobertura) if isinstance(cobertura, (int, float)) else None,
            source_routes=tuple(corpo.get("source_routes") or ()),
            evidence=str(corpo.get("evidence") or ""))
    rotas = (fingerprints or {}).get("rotas") or {}
    fp = {rota: str((corpo or {}).get("sha256_das_chaves_ordenadas") or "")
          for rota, corpo in rotas.items() if isinstance(corpo, dict)}
    return ProviderCapabilityManifest(
        provider_key=provider_key,
        measured_at=str(manifesto.get("measured_at") or ""),
        capacidades=capacidades,
        fingerprints_do_censo={k: v for k, v in fp.items() if v},
        rotas_medidas=int(manifesto.get("rotas_medidas") or 0),
    )


#: O censo lido do disco UMA vez por processo. O manifesto devolvido é sempre
#: uma cópia — `conferir_drift` escreve, e duas corretoras não podem se
#: contaminar (o mesmo motivo do `company_id` na chave de cache).
_CACHE: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}


def carregar_manifesto(provider_key: str = "infocap",
                       diretorio: Optional[str] = None
                       ) -> ProviderCapabilityManifest:
    """O manifesto do provider, do censo versionado em `docs/canon/providers/`.

    📊 Para a InfoCap, em 03/09/2026: 51 rotas medidas · SUPPORTED 9 · PARTIAL 6
    · UNKNOWN 3 · UNAVAILABLE 1.

    ⚠️ Censo ausente devolve um manifesto **vazio**, e manifesto vazio responde
    `UNKNOWN` a tudo — que é a resposta certa: sem censo, nada foi verificado.
    Devolver "tudo SUPPORTED" faria o motor calcular sobre o que não existe.
    """
    chave = f"{provider_key}|{diretorio or ''}"
    if chave not in _CACHE:
        base = diretorio or os.path.join(DIRETORIO_DO_CENSO, provider_key)
        _CACHE[chave] = (
            _ler_json(os.path.join(base, f"{provider_key}-capability-manifest.json")),
            _ler_json(os.path.join(base, f"{provider_key}-schema-fingerprints.json")),
        )
    manifesto, fingerprints = _CACHE[chave]
    return manifesto_de_dicionarios(provider_key, manifesto, fingerprints)


def esquecer_censo() -> None:
    """Zera o cache de disco. Para testes — e só para testes."""
    _CACHE.clear()
