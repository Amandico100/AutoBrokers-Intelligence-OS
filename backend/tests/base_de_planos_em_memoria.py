# -*- coding: utf-8 -*-
"""Um `db` duplo EM MEMÓRIA para os guardas do BLOCO B da SPEC-EXTRA-001.5.

🔴 POR QUE UM DUPLO, E NÃO UMA TRANSAÇÃO COM ROLLBACK
=====================================================
A fatia 1 (M-A2/M-A3) escreve em produção dentro de `psycopg` com ROLLBACK
porque o que ela prova é **o BANCO recusando** — CHECK `servico_tem_fonte`,
`servico_publicado_foi_revisado`. O alvo é o servidor.

O BLOCO B prova outra coisa: **a Skill**. O motor que tem de rodar é
`cobertura_e_assistencia` + `assistance_plans_base` (o contrato da fatia 1 roda
INTEIRO aqui: `chave_de_conhecimento`, `servico_canonico`, `planos_publicados`,
`buscar_servico`, `existe_plano_superior` — nada é reimplementado). Só o
TRANSPORTE é duplo. 📊 E há um motivo medido: `insurer_assistance_plans` tem
**0 linhas** em produção (17/09/2026), então uma transação com ROLLBACK teria de
INSERIR as linhas de teste de qualquer jeito — o mesmo dado sintético, com o
custo de uma conexão e o risco de uma escrita que escapa do rollback.

⚠️ O que este duplo NÃO prova: os CHECKs do banco. Isso é M-A2/M-A3, e continua
sendo delas.

🔴 O duplo é BURRO de propósito: ele não conhece `curadoria`, `nivel` nem
`servico` — só compara igualdade de coluna e ordena. Quem sabe que só
`curadoria='publicado'` chega ao segurado é `assistance_plans_base`, e é isso
que os guardas medem. Um duplo esperto responderia certo mesmo com a regra
apagada do módulo.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional


class _Resposta:
    def __init__(self, data: Any) -> None:
        self.data = data


class _Consulta:
    """A cadeia `select().eq().order().limit().execute()` do cliente Supabase."""

    def __init__(self, linhas: List[Dict[str, Any]]) -> None:
        self._linhas = list(linhas)

    def select(self, *_args, **_kw) -> "_Consulta":
        return self

    def eq(self, coluna: str, valor: Any) -> "_Consulta":
        self._linhas = [l for l in self._linhas if str(l.get(coluna)) == str(valor)]
        return self

    def in_(self, coluna: str, valores) -> "_Consulta":
        alvo = {str(v) for v in (valores or [])}
        self._linhas = [l for l in self._linhas if str(l.get(coluna)) in alvo]
        return self

    def order(self, coluna: str, desc: bool = False) -> "_Consulta":
        self._linhas.sort(key=lambda l: (l.get(coluna) is None, l.get(coluna)), reverse=desc)
        return self

    def limit(self, n: int) -> "_Consulta":
        self._linhas = self._linhas[: int(n)]
        return self

    def execute(self) -> _Resposta:
        return _Resposta(list(self._linhas))


class _Tabela(_Consulta):
    def __init__(self, banco: "BaseEmMemoria", nome: str) -> None:
        super().__init__(banco.tabelas.setdefault(nome, []))
        self._banco = banco
        self._nome = nome

    def insert(self, linha: Dict[str, Any]) -> _Consulta:
        nova = dict(linha)
        nova.setdefault("id", str(uuid.uuid4()))
        self._banco.tabelas.setdefault(self._nome, []).append(nova)
        return _Consulta([nova])


class BaseEmMemoria:
    """Cliente `db` mínimo: `.table(nome)`. Contador de chamadas incluído.

    `chamadas_de_tabela` é o que dá à linha de CONTROLE do M-B2 o direito de
    concluir: *"a pergunta que não é de cobertura NÃO consultou a base"* se
    mede contando as consultas, não lendo o texto da resposta.
    """

    def __init__(self) -> None:
        self.tabelas: Dict[str, List[Dict[str, Any]]] = {}
        self.chamadas_de_tabela: List[str] = []

    # o atributo que `_db()` de `assistance_plans_base` procura
    @property
    def client(self) -> "BaseEmMemoria":
        return self

    def table(self, nome: str) -> _Tabela:
        self.chamadas_de_tabela.append(nome)
        return _Tabela(self, nome)

    # ------------------------------------------------------------------
    # Atalhos de montagem — a linha nasce PUBLICADA porque o que este duplo
    # prova é a LEITURA. Publicar sem revisor é o que M-A2/M-A3 guardam.
    # ------------------------------------------------------------------
    def plano(
        self,
        *,
        insurer_key: str,
        ramo: str,
        produto: str,
        plano: str,
        nivel: int,
        documento_id: str = "doc-cg-0001",
        pagina: int = 23,
        curadoria: str = "publicado",
    ) -> str:
        linha = {
            "id": str(uuid.uuid4()),
            "insurer_key": insurer_key,
            "ramo": ramo,
            "produto": produto,
            "plano": plano,
            "nivel": int(nivel),
            "documento_id": documento_id,
            "pagina": int(pagina),
            "curadoria": curadoria,
            "confianca": "alta",
        }
        self.tabelas.setdefault("insurer_assistance_plans", []).append(linha)
        return linha["id"]

    def servico(
        self,
        plano_id: str,
        servico: str,
        coberto: str,
        *,
        documento_id: str = "doc-cg-0001",
        pagina: int = 24,
        limite_valor: Optional[float] = None,
        limite_unidade: Optional[str] = None,
        limite_texto: Optional[str] = None,
        carencia_dias: Optional[int] = None,
        condicao: Optional[str] = None,
        curadoria: str = "publicado",
    ) -> str:
        linha = {
            "id": str(uuid.uuid4()),
            "plano_id": plano_id,
            "servico": servico,
            "coberto": coberto,
            "limite_valor": limite_valor,
            "limite_unidade": limite_unidade,
            "limite_texto": limite_texto,
            "carencia_dias": carencia_dias,
            "condicao": condicao,
            "documento_id": documento_id,
            "pagina": int(pagina),
            "trecho_hash": "0" * 64,
            "confianca": "alta",
            "curadoria": curadoria,
        }
        self.tabelas.setdefault("insurer_assistance_services", []).append(linha)
        return linha["id"]


class BaseQueCai(BaseEmMemoria):
    """A base que NÃO responde — o par 2 do M-B1.

    🔴 `fonte_indisponivel` não é `nao_sabemos_ainda`: um é *"não sei o que o
    contrato dele diz"*, o outro é *"não consegui olhar"*. O segurado precisa
    ouvir coisas diferentes, e a única forma de provar isso é derrubar a busca
    de verdade.
    """

    def table(self, nome: str):  # noqa: D102
        raise ConnectionError("base de planos indisponível (duplo do M-B1 par 2)")
