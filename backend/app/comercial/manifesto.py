# -*- coding: utf-8 -*-
"""O manifesto de capacidade — SPEC-094 BLOCO C. **Ausente não é zero.**

Peça pura: `dataclasses`, `json`, `os`, `typing`. Lê o **censo medido** do
BLOCO 0 (`backend/app/data/providers/infocap/`) e responde a UMA pergunta, antes de
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
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Os estados
# --------------------------------------------------------------------------
SUPPORTED = "SUPPORTED"
PARTIAL = "PARTIAL"
INDISPONIVEL = "UNAVAILABLE"
NAO_VERIFICADO = "UNKNOWN"
DEGRADED = "DEGRADED"
ESTADOS = (SUPPORTED, PARTIAL, INDISPONIVEL, NAO_VERIFICADO, DEGRADED)

#: 🔴 Os ÚNICOS dois estados em que existe número. UMA lista, num lugar só:
#: `entrega_dado` e o default de `bloqueio()` leem a MESMA tupla, e por isso a
#: mutação M2 — "UNAVAILABLE passa a entregar dado" — tem exatamente um alvo. Duas
#: listas divergiriam, e a que ficasse para trás deixaria passar o zero de
#: consolação por um caminho que ninguém estaria olhando.
ESTADOS_QUE_ENTREGAM = (SUPPORTED, PARTIAL)

#: 🔴 O que o adapter grava no lugar do `sha256` quando a rota devolveu ZERO
#: linhas. Um `sha256` de nada seria mentira; OMITIR a rota seria pior, porque
#: "não veio no mapa" é indistinguível de "a rota não foi lida". A rota aparece,
#: marcada, e as duas peças que a leem sabem o que fazer: aqui, não é drift; no
#: registry, a métrica dependente sai UNAVAILABLE.
SEM_AMOSTRA = "SEM_AMOSTRA"

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

#: 🔴 As duas frases do FAIL-CLOSED. Elas viajam como `evidence` da capacidade,
#: e é por isso que chegam ao pack e ao Artifact: quem lê precisa saber que o
#: número não saiu porque a MEDIÇÃO está ilegível, e não porque a fonte não
#: expõe o dado. São afirmações diferentes sobre coisas diferentes.
CENSO_ILEGIVEL = ("censo da fonte ilegível: a medição de capacidade não pôde ser "
                  "lida, e sem ela nenhuma métrica pode afirmar que a fonte "
                  "entrega o dado")
SEM_FINGERPRINT = ("o censo não registrou o fingerprint de %s: não há como "
                   "afirmar que o schema desta rota continua o medido, e uma "
                   "métrica que depende dela fica bloqueada até remedir")

#: 🔴 ONDE O CENSO MORA — DENTRO DO PACOTE (SPEC-EXTRA-001.5.1, unidade A-ter).
#:
#: `backend/app/data/providers/<provider>/`. É `app/`, logo é **código**, logo
#: entra no `COPY . .` do `backend/Dockerfile`.
#:
#: 📊 19/09/2026, medido na cópia que reproduz o contêiner (só `backend/`):
#: `os.path.isdir(DIRETORIO_DO_CENSO)` → **False**, e
#: `carregar_manifesto("infocap")` devolvia **0 capacidades** — na árvore de
#: desenvolvimento, **19**. E `ilegivel` vinha **vazio**: `_ler_json` devolvia
#: `{}` para arquivo ausente, o manifesto nascia vazio e TODA capacidade
#: respondia `UNKNOWN` com a evidência *"capacidade fora do censo: não
#: verificada"*. Sem 500, sem exceção, sem linha vermelha.
#:
#: 🔴 É a TERCEIRA reincidência do mesmo defeito na mesma SPEC (vocabulário de
#: serviços · catálogos SUSEP · censo do provider): **dado de runtime morando em
#: `docs/`**. O bloco [10] do guarda do contêiner existe para que não haja uma
#: quarta.
#:
#: ⚠️ O de `docs/canon/providers/infocap/` continua existindo como PONTEIRO, e o
#: censo NARRADO (o `.md`), o dicionário de campos e os controles-ouro **ficam**
#: lá: nenhum código os abre em runtime.
_NO_PACOTE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "providers")

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

#: O caminho histórico, a partir da raiz do REPOSITÓRIO. Continua sendo
#: procurado (uma árvore antiga ainda pode ter o dado ali), mas só DEPOIS do
#: pacote: deixar o `docs/` na frente faria a árvore de desenvolvimento ler um
#: arquivo e produção outro — a cegueira do CLAUDE.md §9.1, uma casa adiante.
_NO_DOCS = os.path.join(_RAIZ, "docs", "canon", "providers")

#: ⚠️ Mantido para quem compõe o caminho por fora (`executive_intelligence`
#: monta o nome do mapa de produtor). Aponta para o PACOTE.
DIRETORIO_DO_CENSO = _NO_PACOTE


def caminho_do_censo(provider_key: str, nome: str) -> str:
    """O primeiro caminho que EXISTE, o do pacote primeiro. Nenhum → o do pacote.

    ⚠️ Devolver o do pacote quando nenhum existe é de propósito: é ele que tem
    de existir, e é o nome dele que a mensagem de erro precisa citar.
    """
    for pasta in (_NO_PACOTE, _NO_DOCS):
        caminho = os.path.join(pasta, str(provider_key or ""), str(nome or ""))
        if os.path.isfile(caminho):
            return caminho
    return os.path.join(_NO_PACOTE, str(provider_key or ""), str(nome or ""))


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
    #: 🔴 A rota que dá a POPULAÇÃO desta capacidade. As outras COMPLEMENTAM.
    primary_route: str = ""

    @property
    def rota_primaria(self) -> str:
        """A rota sem a qual esta capacidade não tem população — declarada.

        🔴 📊 Achado pelo juiz em 03/09/2026, na peça viva: com `/renovacoes`
        devolvendo `[]` e `/documentos_bi` cheia, `renewal.exposure` saía
        **0,0 · cobertura 1,0 · HIGH**, e o relatório dizia com todas as letras
        *"este 0 é um fato sobre a carteira"*. Não era: era uma rota que não
        respondeu.

        A causa é que `portfolio.renewals` lista DUAS rotas
        (`/renovacoes`, `/documentos_bi`) e o detector de rota vazia perguntava
        *"TODAS as rotas lidas vieram vazias?"*. Uma rota secundária cheia
        bastava para a resposta ser "não", e a métrica passava.

        ⚠️ As duas rotas não são intercambiáveis: `/renovacoes` filtra `fimvig`
        e é a ÚNICA que lista o que vence; `/documentos_bi` filtra `inivig` e
        entra como complemento (produtor, comissão). Chamar as duas de "fonte"
        e tratá-las como equivalentes é o que produziu o zero.

        Sem declaração, a primeira rota do censo vale como primária — e o censo
        as declara explicitamente, para que a ORDEM de um JSON nunca seja o que
        decide se um zero é fato.
        """
        if self.primary_route:
            return self.primary_route
        return self.source_routes[0] if self.source_routes else ""

    @property
    def entrega_dado(self) -> bool:
        """`SUPPORTED` ou `PARTIAL`. Só estes dois deixam a métrica calcular."""
        return self.state in ESTADOS_QUE_ENTREGAM

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
        """A frase que vai ao pack e ao Artifact. 🔴 A `evidence` VENCE a tabela.

        📊 Achado em 03/09/2026, ao provar o fail-closed: com o censo ilegível
        todas as capacidades viravam `DEGRADED`, e esta função lia a tabela e
        respondia *"o schema da rota mudou desde o censo"* — que é uma
        afirmação sobre a FONTE DO CLIENTE, feita quando o problema é a NOSSA
        medição. É a mutação **M2** entrando por outra porta: trocar um fato
        sobre nós por um fato sobre eles.

        Os dois `DEGRADED` têm motivos diferentes (drift de schema × censo
        ilegível × fingerprint ausente), e o motivo mora na `evidence`.
        """
        base = FRASE_DO_ESTADO.get(self.state, self.state)
        if self.state == DEGRADED and self.evidence:
            base = self.evidence
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
    #: 🔴 O motivo pelo qual este manifesto **não pode ser usado**. Vazio é o
    #: caso normal. Preenchido, TUDO fica `DEGRADED` — e `DEGRADED` não está em
    #: `ESTADOS_QUE_ENTREGAM`, então nenhuma métrica calcula.
    #:
    #: 📊 Achado pelo red team em 03/09/2026: o censo corrompido (um byte a mais
    #: no JSON) fazia `carregar_manifesto` devolver `{}` e o chamador devolver
    #: `None`, e `None` **não bloqueia nada** — as 16 métricas saíam com número,
    #: com `HIGH`, sem uma linha de aviso. Um manifesto que não consegue afirmar
    #: nada tem de bloquear tudo; a alternativa é liberar tudo, que é o que
    #: acontecia.
    ilegivel: str = ""

    # ------------------------------------------------------------- carga
    @classmethod
    def de_arquivo(cls, caminho: str,
                   fingerprints: Optional[str] = None) -> "ProviderCapabilityManifest":
        """O manifesto a partir do JSON do censo, pelo CAMINHO do arquivo.

        ⚠️ O arquivo de fingerprints é procurado ao lado, pelo mesmo prefixo de
        provider. Quem tem o manifesto tem o censo inteiro: pedir os dois
        caminhos convidaria alguém a passar só um, e um manifesto sem
        fingerprint não consegue detectar drift — ficaria silenciosamente
        cego (M14).
        """
        base = os.path.dirname(caminho)
        nome = os.path.basename(caminho)
        provider = nome.split("-capability-manifest")[0] or "infocap"
        fp = fingerprints or os.path.join(
            base, "%s-schema-fingerprints.json" % provider)
        return manifesto_de_dicionarios(provider, _ler_json(caminho), _ler_json(fp))

    # ------------------------------------------------------------ consulta
    def capacidade(self, nome: str) -> Capacidade:
        """A capacidade pedida — ou uma `UNKNOWN` explícita.

        🔴 Capacidade que o censo não conhece é `UNKNOWN`, **jamais**
        `UNAVAILABLE`. Perguntar por um nome que o censo não mediu é
        exatamente o caso de "não verificado".
        """
        if self.ilegivel:
            return Capacidade(nome=nome, state=DEGRADED, evidence=self.ilegivel)
        if nome in self.degradadas:
            base = self.capacidades.get(nome)
            return Capacidade(
                nome=nome, state=DEGRADED,
                coverage_pct=base.coverage_pct if base else None,
                source_routes=base.source_routes if base else (),
                primary_route=base.primary_route if base else "",
                evidence=self.degradadas[nome])
        return self.capacidades.get(
            nome, Capacidade(nome=nome, state=NAO_VERIFICADO,
                             evidence="capacidade fora do censo: não verificada"))

    def estado(self, nome: str) -> str:
        return self.capacidade(nome).state

    def estados(self) -> Dict[str, str]:
        if self.ilegivel:
            return {n: DEGRADED for n in self.capacidades}
        saida = {n: c.state for n, c in self.capacidades.items()}
        saida.update({n: DEGRADED for n in self.degradadas})
        return saida

    @property
    def avisos_de_integridade(self) -> List[str]:
        """O que o pack e o Artifact precisam ESCREVER sobre este manifesto.

        🔴 Fail-closed silencioso é meio conserto. Bloquear a métrica e não
        dizer por quê produz um relatório inteiro de INDISPONÍVEL que parece
        defeito da fonte, quando o defeito é do nosso censo.
        """
        avisos: List[str] = []
        if self.ilegivel:
            avisos.append(self.ilegivel)
        for motivo in sorted(set(self.degradadas.values())):
            avisos.append(motivo)
        return avisos

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
            if medido == SEM_AMOSTRA:
                # ⚠️ Rota que veio VAZIA não tem schema a comparar. Ela não é
                # drift — é ausência de linhas, e quem trata isso é o registry
                # (a métrica dependente sai UNAVAILABLE com "fonte sem linhas
                # no período"). Chamar isto de drift seria acusar a fonte de ter
                # mudado quando ela só não tinha o que devolver.
                continue
            esperado = self.fingerprints_do_censo.get(rota)
            if esperado and esperado == medido:
                continue
            if not esperado:
                # 🔴 FAIL-CLOSED. Isto era um `continue`, com a justificativa de
                # que "não se pode afirmar mudança contra uma medição que não
                # existe". A frase continua verdadeira — e a conclusão estava
                # invertida. 📊 Red team, 03/09/2026: apagar o arquivo de
                # fingerprints deixava o drift CEGO e as métricas passavam com
                # `HIGH`. Não se pode afirmar que mudou; também não se pode
                # afirmar que NÃO mudou, e é a segunda afirmação que o número
                # publicado faz. Sem medição, a rota fica bloqueada e diz por quê.
                motivo = SEM_FINGERPRINT % rota
            else:
                motivo = (f"o schema de {rota} mudou desde o censo "
                          f"({esperado[:8]}… → {medido[:8]}…): a métrica que depende "
                          f"desta rota fica bloqueada até remedir")
            avisos.append(motivo)
            for nome, cap in self.capacidades.items():
                if rota in cap.source_routes:
                    self.degradadas[nome] = motivo
        return avisos

    #: ⚠️ O mesmo método, com o nome que o guarda procura. Um alias, e não uma
    #: segunda implementação: duas funções de drift divergiriam no primeiro
    #: `startswith("__")` que uma ganhasse e a outra não.
    def avaliar_drift(self, fingerprints_medidos: Dict[str, str]) -> List[str]:
        return self.conferir_drift(fingerprints_medidos)

    # ------------------------------------------------------------ bloqueio
    def bloqueio(self, requeridas: Sequence[str],
                 aceitos: Sequence[str] = ESTADOS_QUE_ENTREGAM
                 ) -> Tuple[bool, List[str]]:
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
class CensoIlegivel(RuntimeError):
    """O arquivo do censo existe e **não** pôde ser lido.

    🔴 Diferente de ausente. Censo ausente é "ninguém mediu" e responde
    `UNKNOWN` a tudo, que já bloqueia. Censo ILEGÍVEL é "a medição existe e
    está corrompida" — e o caminho antigo engolia a exceção e devolvia `{}`,
    que o motor lia como manifesto vazio e o chamador transformava em `None`.
    `None` libera tudo.
    """


def _ler_json(caminho: str, *, secao: str = "") -> Dict[str, Any]:
    """O JSON do censo — e a AUSÊNCIA dele **grita** (SPEC-EXTRA-001.5.1, A-ter).

    🔴 POR QUE `ERROR`, E POR QUE NÃO UMA EXCEÇÃO
    =============================================
    Era um `return {}` mudo. Um censo vazio **não quebra nada**: o manifesto
    nasce sem capacidade nenhuma e tudo passa a responder `UNKNOWN` com a
    evidência *"capacidade fora do censo"* — que é indistinguível, para quem lê
    o relatório, de "medimos e não sabemos". 📊 Em produção isso valia para as
    **19** capacidades desde que a imagem existe.

    ⛔ E NÃO se levanta exceção: `carregar_manifesto` é chamado no caminho do
    Pulso 360, e derrubar um relatório porque um arquivo de censo sumiu trocaria
    um defeito silencioso por um pior. A resposta continua sendo o manifesto
    vazio — o que muda é que ela **grita**.

    ⚠️ Um PONTEIRO (o arquivo de `docs/`, que hoje só diz onde o dado mora) cai
    aqui como "seção ausente" e recebe o mesmo tratamento: nunca é carregado
    como se fosse censo.
    """
    if not os.path.exists(caminho):
        logger.error(
            "[CENSO] arquivo AUSENTE: %s. Sem ele, TODA capacidade responde "
            "UNKNOWN e nenhuma métrica pode afirmar que a fonte entrega o dado.",
            caminho)
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            bruto = json.load(f) or {}
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        raise CensoIlegivel("%s: %s" % (os.path.basename(caminho),
                                        type(exc).__name__)) from exc
    if secao and not (bruto.get(secao) or {}):
        logger.error(
            "[CENSO] arquivo SEM DADO: seção %r ausente em %s (é um ponteiro?). "
            "Sem ela, TODA capacidade responde UNKNOWN.", secao, caminho)
    return bruto


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
            primary_route=str(corpo.get("primary_route") or ""),
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
    """O manifesto do provider, do censo versionado em `app/data/providers/`.

    📊 Para a InfoCap, em 03/09/2026: 51 rotas medidas · SUPPORTED 9 · PARTIAL 6
    · UNKNOWN 3 · UNAVAILABLE 1.

    ⚠️ Censo ausente devolve um manifesto **vazio**, e manifesto vazio responde
    `UNKNOWN` a tudo — que é a resposta certa: sem censo, nada foi verificado.
    Devolver "tudo SUPPORTED" faria o motor calcular sobre o que não existe.
    """
    chave = f"{provider_key}|{diretorio or ''}"
    if chave not in _CACHE:
        def _arquivo(nome: str) -> str:
            # ⚠️ `diretorio` explícito manda (é como os testes apontam para um
            # censo sintético); sem ele, o resolvedor procura o PACOTE primeiro.
            return os.path.join(diretorio, nome) if diretorio else caminho_do_censo(
                provider_key, nome)

        try:
            _CACHE[chave] = (
                _ler_json(_arquivo(f"{provider_key}-capability-manifest.json"),
                          secao="capabilities"),
                _ler_json(_arquivo(f"{provider_key}-schema-fingerprints.json"),
                          secao="rotas"),
            )
        except CensoIlegivel as exc:
            # 🔴 FAIL-CLOSED, e NÃO em cache: o arquivo pode ser consertado, e
            # guardar a falha faria o processo continuar bloqueado depois do
            # conserto, sem ninguém entender por quê.
            return ProviderCapabilityManifest(
                provider_key=provider_key,
                ilegivel="%s (%s)" % (CENSO_ILEGIVEL, exc))
    manifesto, fingerprints = _CACHE[chave]
    return manifesto_de_dicionarios(provider_key, manifesto, fingerprints)


def esquecer_censo() -> None:
    """Zera o cache de disco. Para testes — e só para testes."""
    _CACHE.clear()
