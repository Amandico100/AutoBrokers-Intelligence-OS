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

        # 🔴 A ESCADA DA SPEC-077 aplicada no ÚNICO lugar por onde tudo passa.
        #
        # Um endpoint `CANDIDATE` existe no bundle e nunca foi visto acontecer.
        # A recusa é aqui, e não na journey, de propósito: quem escrever um
        # método novo amanhã não precisa lembrar da regra, e nenhum caminho de
        # exceção a contorna. **Freio liberado e aprovação humana dada não
        # bastam** — os três precisam estar verdes, e este é o terceiro.
        if not API.pode_sair(caminho):
            ep = API.endpoint_do_caminho(caminho)
            self._registrar(metodo, caminho, 0)
            logger.warning("vidros: endpoint CANDIDATE recusado: %s", ep)
            return {"ok": False, "status": 0, "json": None, "text": "",
                    "erro": "endpoint_candidate", "endpoint": ep}

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

    # ---- catálogos e cadastros acrescentados pela EXTRA-001.10 ----------
    async def tipos_de_telefone(self) -> Dict[str, Any]:
        """📊 5 tipos: 2 COMERCIAL · 5 RECADO · 20 CELULAR SEGURADO ·
        21 CELULAR CORRETOR · 22 RESIDENCIA SEGURADO. Lê-se a lista porque
        decorar o número 20 é decorar a posição de outra pessoa."""
        return await self.chamar(API.EP_TIPOS_TELEFONE)

    async def ufs(self) -> Dict[str, Any]:
        """📊 `[{"UF": "AC"}, …]`. Sem query."""
        return await self.chamar(API.EP_UFS)

    async def cidades(self, uf: str) -> Dict[str, Any]:
        """📊 `[{Codigo, UF, Cidade, Nome}, …]` — o `Codigo` é o que o PATCH pede."""
        return await self.chamar(
            f"{API.EP_CIDADES}?ExibeMunicipios=true&UF={str(uf or '').strip().upper()}")

    async def cidade_atendida(self, *, chassi: str, codigo_cidade: Any,
                              codigo_script: Any, codigo_tipo_script: Any,
                              reembolso: str = "N") -> Dict[str, Any]:
        """A cidade tem REDE para esta peça? 📊 `GET /clientes/cidades` →
        `{Codigo, Nome, UF, Zonas: []}`. Cidade sem rede é o que faz o pedido
        nascer e parar — e só dá para perguntar depois do token."""
        return await self.chamar(
            f"{API.EP_CLIENTES_CIDADES}?Chassi={chassi}&CodigoCidade={codigo_cidade}"
            f"&CodigoScript={codigo_script}&CodigoTipoScript={codigo_tipo_script}"
            f"&Reembolso={reembolso}")

    async def servicos_itens(self, *, codigo_script: Any,
                             codigo_tipo_script: Any) -> Dict[str, Any]:
        """As peças da LATARIA. 📊 `[{Codigo, Descricao}, …]` — 21 na captura de
        lataria; `[]` quando a peça é de vidraçaria."""
        return await self.chamar(
            f"{API.EP_SERVICOS_ITENS}?CodigoScript={codigo_script}"
            f"&CodigoTipoScript={codigo_tipo_script}")

    async def servicos_detalhes(self) -> Dict[str, Any]:
        """📊 `[{Codigo:1,Tamanho:"MENOR QUE 05cm"}, …]` — o tamanho do AMASSADO
        de lataria. ⚠️ Não é a régua do trincado de para-brisa (P2-1)."""
        return await self.chamar(API.EP_SERVICOS_DETALHES)

    async def objetos_causa(self, *, codigo_script: Any,
                            codigo_tipo_script: Any) -> Dict[str, Any]:
        """As causas da LATARIA. 📊 1 exercício, na captura de lataria."""
        return await self.chamar(
            f"{API.EP_OBJETOS_CAUSA}?CodigoScript={codigo_script}"
            f"&CodigoTipoScript={codigo_tipo_script}")

    async def registrar_corretor(self, documento: str) -> Dict[str, Any]:
        """`PUT /atendimentos/corretores {"Documento": …}`.

        📊 Presente em 4 de 4 capturas, sempre logo depois do
        `POST /atendimentos` — e 🔴 **é daqui em diante que o header
        `token_autorizacao` viaja**. Pular este passo deixa todo o resto sem
        token, incluindo o catálogo da apólice.

        Não é fronteira material: não cria pedido, vincula o corretor ao que
        acabou de nascer. O pedido já existia quando esta chamada saiu.
        """
        return await self.chamar(API.EP_CORRETORES, metodo="PUT",
                                 corpo={"Documento": str(documento or "").strip()})

    async def registrar_solicitante(self, corpo: Dict[str, Any]) -> Dict[str, Any]:
        """`POST /solicitantes`. Quem é o contato do atendimento.

        📊 O corpo tem 8 ou 9 chaves: `EmailTitularAplice` (sic, sem o `o`)
        só aparece quando `EmailCorretor` é `true` — 2 de 4 capturas.
        🔴 `TermoAceito` é `false` em 4 de 4. Não se inventa `true`.
        """
        return await self.chamar(API.EP_SOLICITANTES, metodo="POST", corpo=corpo)

    async def atualizar_atendimento(self, corpo: Dict[str, Any]) -> Dict[str, Any]:
        """`PATCH /atendimentos` — peça, causa, local.

        🔴 Para categoria `L` esta chamada **é a fronteira material**: 📊 o
        `CodigoAtendimento` nasce logo depois dela e não há questionário nenhum.
        Para `V` ela não materializa. Quem decide qual é o caso é
        `vidros_estado.fronteira_materializar_de`, e quem arma o guard é a
        journey — nunca esta função.

        O corpo vem pronto de `API.corpo_de_atualizacao`, que é onde mora a
        regra por campo. Montá-lo aqui espalharia a regra por dois lugares.
        """
        return await self.chamar(API.EP_ATENDIMENTOS, metodo="PATCH", corpo=corpo)

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

    # ---- o REPARO: uma decisão do segurado que o código não conhecia -----
    async def regras_reparo(self, respostas: list) -> Dict[str, Any]:
        """`POST /questionarios/regras-reparo` → `{"ExibirDialogDeReparo": bool}`.

        🔴 É POST e é **LEITURA**: manda o mesmo acumulado do questionário e
        devolve se o portal vai oferecer o reparo. 📊 `true` no para-brisa,
        `false` no vidro de porta — e roda ANTES da fronteira B, o que permite
        descobrir que falta a decisão do segurado **sem ter materializado nada**.
        """
        return await self.chamar(API.EP_REGRAS_REPARO, metodo="POST",
                                 corpo={"PerguntasResposta": list(respostas or [])})

    async def alterar_reparo(self, aceita: bool) -> Dict[str, Any]:
        """`PUT /atendimentos/alterar-reparo {"Reparo": bool}`.

        📊 1 exercício, com `true`, no para-brisa. Grava a escolha do segurado
        entre tentar o reparo (grátis, 30 min) e trocar o vidro — e é ele quem
        escolhe: 💭 o desconto e o valor de troca são diferentes, e o dinheiro
        é dele.
        """
        return await self.chamar(API.EP_ALTERAR_REPARO, metodo="PUT",
                                 corpo={"Reparo": bool(aceita)})

    # ---- o desfecho e a agenda: LEITURA, com teto ------------------------
    async def opcoes_de_agendamento(self) -> Dict[str, Any]:
        """🔴 O ROTEADOR. 📊 20 chaves; é esta resposta que decide loja direta,
        agenda, vistoria ou analista. Ler isto é o oposto de decidir por peça."""
        return await self.chamar(API.EP_OPCOES_DISPONIVEIS)

    async def consultar_distancia(self, corpo: Dict[str, Any]) -> Dict[str, Any]:
        """`POST /lojas/consultar-distancias` → `{"Distancia", "TempoDuracao"}`.

        ⚠️ **POST de LEITURA.** Ele calcula rota e não muda nada no pedido —
        por isso NÃO passa pelo `PortalActionGuard` como fronteira material.
        🔴 A razão de escrever isto aqui em vez de "ser cauteloso e armar
        mesmo assim": armar o guard num cálculo de rota ensina a equipe a
        ignorar o guard. Semântica vence verbo (SPEC-073), e nos dois sentidos.
        """
        return await self.chamar(API.EP_CONSULTAR_DISTANCIAS, metodo="POST",
                                 corpo=corpo)

    async def datas_disponiveis(self, *, codigo_cliente: Any, codigo_produto: Any,
                                ano: Any) -> Dict[str, Any]:
        """📊 `[{"Mes": 8, "Dias": [15,17,…], "AvancarParaConclusao": false}, …]`."""
        return await self.chamar(
            f"{API.EP_DATAS_DISPONIVEIS}?Ano={ano}&CodigoCliente={codigo_cliente}"
            f"&CodigoProduto={codigo_produto}")

    async def horarios_disponiveis(self, *, codigo_cliente: Any, codigo_produto: Any,
                                   data_agendamento: str) -> Dict[str, Any]:
        """📊 `{IdParametroLoja, TempoPermanencia, TempoServico,
        SolicitacaoEncaixe, CodigoReparo, Blocos: []}` — e `Blocos` veio
        **vazio** na única captura. Lista vazia não é erro: é o que a loja
        publicou naquele dia."""
        return await self.chamar(
            f"{API.EP_HORARIOS_DISPONIVEIS}?CodigoCliente={codigo_cliente}"
            f"&DataAgendamento={data_agendamento}&CodigoProduto={codigo_produto}")

    async def emitir_formalizado(self, codigo_atendimento: str) -> Dict[str, Any]:
        """`POST /atendimentos/emitir-atendimento-formalizado/{cod}`, sem corpo.

        📊 2 exercícios (para-brisa e lataria), os dois no fim, depois da
        conclusão. É o COMPROVANTE.
        """
        cod = str(codigo_atendimento or "").strip()
        return await self.chamar(f"{API.EP_EMITIR_FORMALIZADO}/{cod}",
                                 metodo="POST", corpo={})

    async def livre_escolha(self, *, codigo_externo: Any, codigo_item: Any,
                            codigo_script: Any, codigo_tipo_script: Any,
                            codigo_seguradora: Any, numero_apolice: Any) -> Dict[str, Any]:
        """📊 `{DireitoLivreEscolha: false, ValorFranquiaCredenciado: …}`. É a
        resposta a *"posso indicar minha oficina?"* — e ela vem do contrato,
        não da simpatia do atendente. ⚠️ Os nomes de query aqui são em
        minúscula (`codigoItem`), ao contrário dos outros endpoints."""
        return await self.chamar(
            f"{API.EP_LIVRES_ESCOLHAS_VALIDAR}?codigoExterno={codigo_externo}"
            f"&codigoItem={codigo_item}&codigoScript={codigo_script}"
            f"&codigoTipoScript={codigo_tipo_script}"
            f"&codigoSeguradora={codigo_seguradora}&numeroApolice={numero_apolice}")

    async def status_da_seguradora(self, slug: str) -> Dict[str, Any]:
        """📊 `GET /atendimentos/status-seguradoras/?Seguradora=liberty` → `true`.
        A seguradora está no ar agora. Note o slug em MINÚSCULA na query."""
        return await self.chamar(
            f"{API.EP_STATUS_SEGURADORAS}?Seguradora={str(slug or '').strip().lower()}")

    # ---- escritas ESCRITAS e DESLIGADAS: CANDIDATE na escada da SPEC-077 --
    # 🔴 As cinco funções abaixo existem, estão completas e **não saem**:
    # `chamar` as recusa com `erro="endpoint_candidate"` antes de tocar a rede,
    # porque 📊 nenhuma delas tem um exercício em captura. Escrever o código
    # contra o contrato do bundle é barato e deixa a promoção pronta; deixá-lo
    # sair sem captura é mandar efeito não medido para dentro da seguradora.
    async def agendar(self, corpo: Dict[str, Any]) -> Dict[str, Any]:
        """`POST /agendamentos` — CANDIDATE. 📊 zero exercícios em 4 HAR."""
        return await self.chamar(API.EP_AGENDAMENTOS_NAO_MEDIDO, metodo="POST",
                                 corpo=corpo)

    async def direcionar(self, corpo: Dict[str, Any]) -> Dict[str, Any]:
        """`POST /direcionamentos` — CANDIDATE. 📊 zero exercícios em 4 HAR."""
        return await self.chamar(API.EP_DIRECIONAMENTOS_NAO_MEDIDO, metodo="POST",
                                 corpo=corpo)

    async def abandonar(self, motivo: str) -> Dict[str, Any]:
        """`PATCH /atendimentos/abandonar {"MotivoAbandono": …}` — CANDIDATE.

        📊 **1 exercício** (HAR da Porto, status 200) — a proposta dizia zero, e
        o número medido aqui vence. Continua CANDIDATE mesmo assim: o que falta
        não é captura, é decisão de produto. Desistir do pedido no lugar do
        segurado não é efeito que esta SPEC autoriza.
        """
        return await self.chamar(API.EP_ABANDONAR, metodo="PATCH",
                                 corpo={"MotivoAbandono": str(motivo or "")})

    async def gerar_link_vistoria(self, telefone: str) -> Dict[str, Any]:
        """`GET /atendimentos/vistoriamobile?telefone=…` — CANDIDATE.

        📊 `PermiteVistoriaMobile: false` e `LinkVistoriaMobile: ""` em **todas**
        as capturas: a seguradora nunca habilitou vistoria, então o link nunca
        foi gerado. O caminho fica escrito; a captura o liga.
        """
        return await self.chamar(
            f"{API.EP_VISTORIA_MOBILE_NAO_MEDIDO}?telefone={str(telefone or '').strip()}")

    async def enviar_fotografias(self, *, codigo_atendimento: str,
                                 imagens: list) -> Dict[str, Any]:
        """`POST /atendimentos-fotografias/web` — MULTIPART, CANDIDATE.

        🔴 O único caminho multipart da sessão, e o segundo `page.evaluate` do
        módulo. 📊 Do bundle: `FormData` com `CodigoAtendimento` + N× `Imagens`,
        `transformRequest: angular.identity` e
        `headers: {"Content-Type": undefined}` — 🔴 o Content-Type fica **em
        branco de propósito**, para o browser escrever o `boundary` sozinho.
        Escrevê-lo à mão produz um corpo que o servidor não separa.

        ⛔ Mesma sessão, mesmo cookie, mesma allowlist, mesmo teto: nenhuma
        biblioteca nova, nenhum socket, nenhum transporte alternativo.
        Cada imagem é `{"nome": str, "tipo": str, "base64": str}`.
        """
        caminho = API.EP_FOTOGRAFIAS_WEB_NAO_MEDIDO
        url = f"{API.BASE_API}{caminho}"
        if not API.host_permitido(url):
            raise HostNaoPermitido("host fora da allowlist")
        if not API.pode_sair(caminho):
            self._registrar("POST", caminho, 0)
            return {"ok": False, "status": 0, "json": None, "text": "",
                    "erro": "endpoint_candidate",
                    "endpoint": API.endpoint_do_caminho(caminho)}
        if self.chamadas >= MAX_CHAMADAS:
            return {"ok": False, "status": 0, "json": None, "text": "",
                    "erro": "teto_de_chamadas"}
        self.chamadas += 1
        cabecalhos: Dict[str, str] = {"Accept": "application/json"}
        if self.token:
            cabecalhos[API.HEADER_TOKEN] = self.token
        try:
            r = await self.page.evaluate(
                """async ({url, cabecalhos, codigo, imagens}) => {
                  const fd = new FormData();
                  fd.append('CodigoAtendimento', codigo);
                  for (const img of imagens) {
                    const bin = atob(img.base64);
                    const buf = new Uint8Array(bin.length);
                    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
                    fd.append('Imagens', new Blob([buf], {type: img.tipo}), img.nome);
                  }
                  // 🔴 nenhum Content-Type: o browser escreve o boundary.
                  const r = await fetch(url, {method: 'POST', credentials: 'omit',
                                              headers: cabecalhos, body: fd});
                  let t = ''; try { t = await r.text(); } catch (e) { t = ''; }
                  return {ok: r.ok, status: r.status, text: t};
                }""",
                {"url": url, "cabecalhos": cabecalhos,
                 "codigo": str(codigo_atendimento or ""),
                 "imagens": list(imagens or [])},
            )
        except Exception as exc:  # noqa: BLE001
            self._registrar("POST", caminho, 0)
            return {"ok": False, "status": 0, "json": None, "text": "",
                    "erro": type(exc).__name__}
        self._registrar("POST", caminho, r.get("status") or 0)
        r["json"] = None
        return r

    # ---- cancelar: fronteira material, medida 2× -------------------------
    async def motivos_cancelamento(self) -> Dict[str, Any]:
        """A lista de motivos. 📊 **zero exercícios** nas 4 capturas — está no
        bundle e nunca a vimos responder, então é CANDIDATE e `chamar` a recusa.

        🔴 É por isso que `cancelar` não tem como rodar hoje, e isso é o certo:
        📊 as duas capturas que cancelaram mandaram `codigoMotivoCancelamento:
        39` — um número que o SPA já tinha na mão. Decorar o 39 seria gravar na
        seguradora um motivo que ninguém conferiu. O motivo vem do catálogo, ou
        não vem.
        """
        return await self.chamar(API.EP_MOTIVOS_CANCELAMENTO_NAO_MEDIDO)

    async def cancelar(self, *, codigo_atendimento: str, codigo_motivo: Any,
                       observacao: str = "") -> Dict[str, Any]:
        """`PUT /atendimentos/cancelar` — FRONTEIRA MATERIAL.

        📊 2 exercícios (para-brisa e vidro de porta), corpo de 3 chaves:
        `codigoMotivoCancelamento` · `codigoAtendimento` ·
        `observacaoMotivoCancelamento` (minúsculas, ao contrário dos outros).

        🔴 `codigo_motivo` é obrigatório e quem chama tem de tê-lo lido de
        `motivos_cancelamento()`. Esta função não tem número nenhum decorado, e
        a journey NÃO a chama: cancelar é decisão de gente.
        """
        if codigo_motivo in (None, ""):
            return {"ok": False, "status": 0, "json": None, "text": "",
                    "erro": "motivo_de_cancelamento_ausente"}
        return await self.chamar(API.EP_CANCELAR, metodo="PUT", corpo={
            "codigoMotivoCancelamento": codigo_motivo,
            "codigoAtendimento": str(codigo_atendimento or ""),
            "observacaoMotivoCancelamento": str(observacao or ""),
        })

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
