# -*- coding: utf-8 -*-
"""A sessão API do portal de vidros — SPEC-074, camada L1 da escada.

O que este módulo é
===================
Um cliente HTTP **estreito e vigiado** que fala com `api.autoglass.com.br`
usando a sessão legítima que o próprio navegador obteve. Segue o padrão que a
Yelum já usa (`_api()` via `page.evaluate` + `fetch`) — não inventa transporte
novo, não instala biblioteca, não abre socket próprio.

O que ele NÃO é
===============
    ✗ não inventa token          o `token_autorizacao` vem de `POST /atendimentos`
    ✗ não burla login            é a mesma sessão, o mesmo cookie, o mesmo app
    ✗ não aceita URL livre       allowlist fechada de host, checada por chamada
    ✗ não guarda segredo         o token vive em memória e nunca vai para evidence

Por que chamar a API, e não clicar
==================================
📊 A mineração de 16/08/2026 mostrou que o portal é API-first: o AngularJS é uma
casca sobre 34 endpoints REST. Cada pergunta que a API responde de forma
estruturada é uma pergunta que o robô **não precisa** resolver lendo pixel:

    catálogo de peças ...... `GET /apolices/itens-cobertos`      vs ler um <md-select>
    causas do dano ......... `GET /motivos-dano`                  vs ler outro
    próxima pergunta ....... `POST /questionarios/perguntas`      vs adivinhar a tela
    franquia ............... `GET /atendimentos`.Franquias        vs raspar o 100%
    cobertura ausente ...... HTTP 400 + Tipo                      vs interpretar um modal

Isso não substitui o DOM: substitui o *chute*. O navegador continua sendo quem
autentica, quem executa o que só existe em tela, e o fallback quando a API muda.

🔴 A regra que fecha a porta
============================
Nenhuma resposta desta camada autoriza efeito material sozinha. As duas
fronteiras (`POST /atendimentos` e `POST /questionarios`) passam pelo
`PortalActionGuard` da SPEC-073 como qualquer clique — o fato de a chamada ser
"limpa" e "estruturada" não a torna menos irreversível.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from portal_worker.journeys import vidros_api as API

logger = logging.getLogger(__name__)

# Teto de chamadas por job. Um laço numa API não é mais barato que um laço numa
# tela — é só mais rápido de fazer. 📊 A sessão medida usou 34 chamadas de
# negócio; 150 dá folga de 4x e ainda denuncia recursão.
MAX_CHAMADAS = 150


class HostNaoPermitido(RuntimeError):
    """Tentativa de sair da allowlist. Nunca vira warning — vira parada."""


@dataclass
class SessaoVidros:
    """Fala com a API do portal usando a página autenticada.

    `token` nasce vazio e só existe depois de `POST /atendimentos`. Antes disso,
    as chamadas de leitura (`/seguradoras`, `/apolices`) funcionam sem ele —
    📊 medido: `GET /apolices` não gera nem preflight CORS, porque não manda
    header custom.
    """

    page: Any = None
    token: str = ""
    chamadas: int = 0
    # Trilha para evidência: método, path normalizado e status. Nunca corpo.
    trilha: list = field(default_factory=list)

    def _registrar(self, metodo: str, caminho: str, status: int) -> None:
        if len(self.trilha) < MAX_CHAMADAS:
            self.trilha.append({
                "m": str(metodo).upper()[:6],
                "p": caminho.split("?")[0][:80],
                "s": int(status or 0),
            })

    async def chamar(self, caminho: str, *, metodo: str = "GET",
                     corpo: Optional[Dict[str, Any]] = None,
                     com_token: bool = True) -> Dict[str, Any]:
        """Uma chamada. Devolve `{ok, status, json, text}` — nunca levanta por HTTP.

        Só levanta em violação de allowlist, que é erro de programação nosso, e
        precisa parar a execução em vez de virar um `status: 0` silencioso.
        """
        url = f"{API.BASE_API}{caminho}"
        if not API.host_permitido(url):
            raise HostNaoPermitido(
                f"host fora da allowlist: {url.split('/')[2] if '//' in url else url}")

        if self.chamadas >= MAX_CHAMADAS:
            return {"ok": False, "status": 0, "json": None, "text": "",
                    "erro": "teto_de_chamadas"}
        self.chamadas += 1

        cabecalhos: Dict[str, str] = {"Accept": "application/json"}
        if com_token and self.token:
            cabecalhos[API.HEADER_TOKEN] = self.token

        try:
            r = await self.page.evaluate(
                """async ({url, metodo, corpo, cabecalhos}) => {
                  const init = {method: metodo, credentials: 'omit', headers: cabecalhos};
                  if (corpo !== null) {
                    init.headers['Content-Type'] = 'application/json';
                    init.body = JSON.stringify(corpo);
                  }
                  const r = await fetch(url, init);
                  let t = ''; try { t = await r.text(); } catch (e) { t = ''; }
                  return {ok: r.ok, status: r.status, text: t};
                }""",
                {"url": url, "metodo": metodo.upper(), "corpo": corpo,
                 "cabecalhos": cabecalhos},
            )
        except Exception as exc:  # noqa: BLE001
            self._registrar(metodo, caminho, 0)
            return {"ok": False, "status": 0, "json": None, "text": "",
                    "erro": type(exc).__name__}

        texto = r.get("text") or ""
        # 📊 A API responde em latin-1/Windows-1252 em algumas rotas; os erros
        # 400 vêm com escapes `\uXXXX`. `page.evaluate` já devolve `str` decodificado
        # pelo browser, então o problema de encoding morre aqui — mas a nota fica,
        # porque um replay offline que leia os bytes crus PRECISA saber disso.
        try:
            r["json"] = json.loads(texto) if texto.lstrip()[:1] in ("{", "[") else None
        except (ValueError, IndexError):
            r["json"] = None
        self._registrar(metodo, caminho, r.get("status") or 0)
        return r

    # ---- leituras: nenhuma delas muda nada no mundo ---------------------
    async def seguradoras(self) -> Dict[str, Any]:
        return await self.chamar(API.EP_SEGURADORAS, com_token=False)

    async def buscar_apolice(self, *, seguradora: str, cpf_cnpj: str,
                             placa: str, data_sinistro: str,
                             tipo_atendimento: Optional[int] = None) -> Dict[str, Any]:
        """O PREFLIGHT. É esta resposta que decide se pode haver escrita.

        🔴 Nunca chamar `POST /atendimentos` sem passar por aqui e obter
        `pode_escrever=True`. 📊 No HAR `RODA SEM COBERTURA` o fluxo inteiro
        morre nesta chamada, com 400 — e nenhum atendimento nasceu. Pular o
        preflight é criar pedido para quem não tem cobertura.
        """
        q = (f"?CpfCnpj={cpf_cnpj}&DataSinistro={data_sinistro}"
             f"&Placa={placa}&Seguradora={seguradora}")
        if tipo_atendimento is not None:
            q += f"&TipoAtendimento={tipo_atendimento}"
        return await self.chamar(API.EP_APOLICES + q, com_token=False)

    async def itens_cobertos(self, seguradora: str) -> Dict[str, Any]:
        """O catálogo de peças DESTA apólice. Nunca uma tabela decorada.

        📊 Yelum devolveu 30 itens e Porto 21, para a mesma família de produto.
        Um catálogo estático estaria errado para uma das duas no primeiro dia.
        """
        return await self.chamar(f"{API.EP_ITENS_COBERTOS}?Seguradora={seguradora}")

    async def motivos_dano(self, codigo_item_coberto: str) -> Dict[str, Any]:
        """As causas mudam POR PEÇA. 📊 Yelum 12, Porto 14, e não são as mesmas:
        `AO TROCAR A LÂMPADA QUEBROU O ITEM` só existe para lanterna/farol."""
        from urllib.parse import quote

        return await self.chamar(
            f"{API.EP_MOTIVOS_DANO}?CodigoItemCoberto={quote(codigo_item_coberto, safe='')}")

    async def ler_atendimento(self, *, imagem: bool = False) -> Dict[str, Any]:
        """O read model único. Depois de cada mutação, é aqui que se confere.

        `imagem=False` de propósito: 📊 `RetornarImagemVeiculo=true` embute um
        base64 de ~90 KB no agregado, e `itens-cobertos/imagens` chega a 2,2 MB.
        Nada disso ajuda um robô a decidir.
        """
        flag = "true" if imagem else "false"
        return await self.chamar(
            f"{API.EP_ATENDIMENTOS}?GerarPdf=false&RetornarImagemVeiculo={flag}")

    async def atendimento_aberto_existente(self, *, chassi: str,
                                           cpf_cnpj: str) -> Dict[str, Any]:
        """A dedup do próprio portal. Vale consultar ANTES de criar.

        📊 Devolve o booleano cru `false`. É a checagem que o app faz no passo 2,
        e usá-la é mais barato e mais correto que descobrir duplicidade depois.
        """
        return await self.chamar(
            f"{API.EP_ATENDIMENTOS_ABERTOS}?Chassi={chassi}&CpfCnpjSegurado={cpf_cnpj}")

    # ---- o motor de perguntas -------------------------------------------
    async def proxima_pergunta(self, respostas: list) -> Dict[str, Any]:
        """Envia o acumulado, recebe UMA pergunta — ou 204, que é o fim.

        📊 O motor é stateless no servidor: o cliente reenvia o array inteiro a
        cada rodada. Isso o torna trivialmente replayável offline, e é por isso
        que o fixture consegue reproduzir o questionário sem rede.
        """
        r = await self.chamar(API.EP_QUESTIONARIO_PERGUNTAS, metodo="POST",
                              corpo={"PerguntasResposta": list(respostas or [])})
        # 204 = acabou. Marcado explicitamente para o chamador não confundir
        # "sem corpo" com "falhou".
        r["fim_do_questionario"] = (int(r.get("status") or 0) == 204)
        return r

    # ---- as duas fronteiras materiais -----------------------------------
    # 🔴 Estas DUAS funções são as únicas do módulo que mudam o mundo. Elas não
    # chamam o guard por dentro de propósito: quem arma o checkpoint e pede
    # autorização é a journey, que é quem tem o contexto de negócio. Um cliente
    # HTTP que se autoriza sozinho é o oposto do que a SPEC-073 construiu.
    async def criar_atendimento(self, corpo: Dict[str, Any]) -> Dict[str, Any]:
        """FRONTEIRA A — `POST /atendimentos`. Emite NumeroProtocolo e Token.

        Depois desta chamada existe registro na seguradora. Retry cego aqui
        produz dois pedidos.
        """
        r = await self.chamar(API.EP_ATENDIMENTOS, metodo="POST", corpo=corpo,
                              com_token=False)
        dados = r.get("json") or {}
        if isinstance(dados, dict) and dados.get("Token"):
            # O token entra em memória e NUNCA em evidence/log.
            self.token = str(dados.get("Token"))
        return r

    async def gravar_questionario(self, respostas: list) -> Dict[str, Any]:
        """FRONTEIRA B — `POST /questionarios`. Materializa o CodigoAtendimento.

        📊 Medido: antes desta chamada `CodigoAtendimento` é `null`; depois dela
        existe, junto de `ScriptFinalizacao` e `LinkAreaSegurado`.
        """
        return await self.chamar(API.EP_QUESTIONARIO, metodo="POST",
                                 corpo={"PerguntasResposta": list(respostas or [])})

    def resumo_para_evidencia(self) -> Dict[str, Any]:
        """Trilha da camada API. Sem corpo, sem token, sem query com PII.

        📊 A API do portal coloca CPF, placa e chassi em QUERY STRING. Isso é
        comportamento dela, e não podemos mudá-lo — mas podemos não repetir a
        exposição do nosso lado. Por isso a trilha guarda o path **sem** a query.
        """
        return {
            "camada": "api",
            "chamadas": self.chamadas,
            "tem_token": bool(self.token),
            "trilha": self.trilha[:60],
        }
