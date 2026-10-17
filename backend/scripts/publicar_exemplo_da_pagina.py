# -*- coding: utf-8 -*-
"""Os EXEMPLOS da página do cliente com a marca REAL de uma corretora — SPEC-132-B (fatia E · D-132B-08).

    cd backend
    python -m scripts.publicar_exemplo_da_pagina --company-id <uuid> --pagina venda [--com-apolice]
    python -m scripts.publicar_exemplo_da_pagina --company-id <uuid> --pagina renovacao
    ... --confirmar                      publica de verdade (grava o artefato e devolve o link /r/)
    ... --saida <arquivo.html>           sem --confirmar: onde gravar o HTML (padrão: ./exemplo-<pagina>.html)

O que faz:
  · monta um modelo FICTÍCIO da página — a cliente "Mariana", um carro popular, as 3 opções do modelo do contrato
    (`tests/fixtures/proposta/modelo_contrato.json`, cujos preços são os das ofertas saneadas do canário:
    `ofertas_canario_saneadas.json`), a validade e o vencimento contados a partir de HOJE; na renovação, o "seu seguro
    hoje" e uma dona fictícia SEM telefone — com a MARCA REAL da corretora, lida do banco pelo `company_id`
    (`proposta.montar_anfitria`, a mesma leitura do produto) e a faixa "Exemplo — dados fictícios" no topo;
  · em volta das opções, tudo sai das MESMAS funções do produto: a marca, a FAQ, os passos do sinistro, o bloco da
    venda (`bloco_da_venda`/`marca_da_venda`/`pagina_da_cotacao`), o bloco da renovação (`bloco_da_renovacao`,
    `faq_da_renovacao`), o "Quero fechar" (`cta_da_pagina`) e a guarda da comissão (`_sem_comissao`);
  · com `--confirmar`, publica pelo MESMO caminho do produto (`proposta._gravar_e_compartilhar`: artefato
    `proposal.quote` no Hub → render → publicar → compartilhar), com o link valendo 💭 30 dias, e imprime SÓ o link
    `/r/…` e o tamanho do HTML. Sem `--confirmar`: só renderiza (o MESMO renderizador do template) e grava o HTML num
    arquivo local — o banco é aberto SÓ PARA LER (qualquer escrita levanta `EscritaProibida`).

🔴 O caminho mínimo e honesto (nada de linha falsa em `multicalculo_pedidos` nem em `renovacoes`): os publicadores do
produto (`publicar_cotacao`/`publicar_renovacao`) leem um pedido REAL do motor — o exemplo não tem. Então o modelo é
montado aqui e entregue a `_gravar_e_compartilhar` com um `pedido_id` SINTÉTICO (uuid5 de corretora + página: rodar de
novo = VERSÃO nova da mesma peça, nunca uma pilha de peças) e o assunto do artefato marcado
`{"kind": "exemplo_da_pagina", "exemplo": true}`. Nenhuma tabela do motor, da renovação ou da fila é escrita; o único
leitor de `subject_ref.pedido_id` é o próprio publicador (📊 14/10 `grep -rn "subject_ref->>pedido_id"` fora dos testes:
1 linha, `proposta.py`).

SPEC-130-C (F3) — os RAMOS e as FOTOS:
  · `--ramo 31|16|2|18|91` (padrão 31: o auto de sempre). Condomínio (16), residencial (2) e empresarial (18): as opções
    saem da gravação REAL saneada do ramo (`tests/fixtures/agger_ramos/gravacao_*.json`, as do fio da 129-C) pelo
    LEITOR do robô (`leitor_agger.ler_rodada`), pela LINHA do motor (`Motor._linha_da_oferta`) e pela COMPARAÇÃO e pelas
    OPÇÕES do produto (`comparacao.comparar/opcoes` → `proposta.opcoes_da_pagina`) — nunca opções escritas à mão. Vida
    (91): o resultado gravado de vida (`vida_resultado.json`, 7 seguradoras sem preço) + a oferta da Porto do canário
    ao vivo de 16/10 (📊 CANARIO-AO-VIVO §3/§4 da 129-D: R$ 227,16/ano, 12x de R$ 18,93 — a forma reconstruída em
    `test_spec129d_portal_vida._item_da_porto_do_canario`), pelo MESMO leitor. O bem, as dúvidas e o "se acontecer"
    são os do ramo (as funções do produto).
  · FOTOS ILUSTRATIVAS: sem foto cadastrada na marca (📊 16/10: nenhuma corretora tem), o exemplo desenha 4 ilustrações
    em código (PIL: gradiente nas cores da marca, formas simples, a marca "EXEMPLO"), WEBP ≤ 90 KB, `data:` — SÓ no
    modelo do exemplo, nunca gravadas em tabela; `--sem-fotos` mostra a página sem o carrossel. Um prêmio fictício
    ("Prêmio de exemplo", 2025) só no exemplo; `--sem-premio` o tira.

⛔ Nenhuma pessoa real: cliente, corretor e dona são fictícios. ⛔ Nenhum telefone: o WhatsApp da marca é TIRADO do
modelo e a página sai sem o botão "Quero fechar" (diz "responda a mensagem em que recebeu este link"). Só com
`--com-whatsapp-da-corretora` (decisão de quem roda) o botão leva ao WhatsApp de ATENDIMENTO da corretora — o número
dela, nunca de pessoa. `--whatsapp-do-dono +55…` (E.164 BR, um número FICTÍCIO de quem roda) põe esse número como
o WhatsApp de trabalho CONFIRMADO da dona/do corretor fictício — SÓ no modelo do exemplo, nunca em tabela — e a barra
"Quero fechar"/"Quero renovar" e o "Quem cuida de você" passam a apontar para ele. ⛔ Nenhum nome de corretora neste arquivo (CLAUDE.md §13.9): tudo vem do banco.

Ambiente (nomes, nunca valores): SUPABASE_URL, SUPABASE_KEY (service role) e as obrigatórias de `app.core.config`
(OPENAI_API_KEY, ENCRYPTION_KEY, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD) — no contêiner do backend já estão; com
`--confirmar`, também o endereço público do painel: PUBLIC_APP_URL (ou NEXT_PUBLIC_APP_URL, SMITH_WEB_URL, FRONTEND_URL).
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import io
import json
import math
import re
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

#: o modelo do CONTRATO §5 (os preços REAIS do canário saneado) — a fonte das 3 opções do exemplo
MODELO_DO_CONTRATO = BACKEND / "tests" / "fixtures" / "proposta" / "modelo_contrato.json"
PAGINAS = ("venda", "renovacao")
#: 💭 quanto tempo o link do exemplo vale (a página diz "preços válidos até" = isto menos a folga do link da config)
DIAS_DO_LINK = 30
#: 💭 o vencimento fictício da renovação, contado a partir de hoje (DEPOIS da validade dos preços, como na vida)
DIAS_ATE_VENCER = 30
#: 💭 o reajuste fictício entre o "seu seguro hoje" e a "Sua renovação" (a página mostra o R$ e o %)
REAJUSTE_FICTICIO = 0.09
#: 💭 o prêmio da apólice fictícia que a cliente "tem hoje" (`--com-apolice`: a economia é contra ele)
PREMIO_DA_APOLICE_FICTICIA = 6390.0
#: o espaço dos `pedido_id` sintéticos (uuid5): o mesmo exemplo da mesma corretora = a MESMA peça, versão nova
ESPACO_DOS_EXEMPLOS = uuid.UUID("e4e3a132-0b0e-4e0e-8e0e-000000000132")

#: ⛔ só gente FICTÍCIA (CLAUDE.md §13.9) — nenhuma tem telefone, documento ou sobrenome
CLIENTE_FICTICIA = "Mariana"
CORRETOR_FICTICIO = "Caio"
DONA_FICTICIA = "Bruna"
CARRO_POPULAR = {"rotulo": "carro", "descricao": "Chevrolet Onix 1.0 flex", "ano": "2022/2023", "apelido": "Onix"}

# ---------------------------------------------------------------------------------------------------------------------
# SPEC-130-C — os RAMOS do exemplo (as gravações REAIS saneadas) e as FOTOS ilustrativas
# ---------------------------------------------------------------------------------------------------------------------
from portal_worker.multicalculo.contrato import (RAMO_AUTO, RAMO_CONDOMINIO, RAMO_EMPRESARIAL,  # noqa: E402
                                                 RAMO_RESIDENCIAL, RAMO_VIDA)

RAMOS =(RAMO_AUTO, RAMO_CONDOMINIO, RAMO_RESIDENCIAL, RAMO_EMPRESARIAL, RAMO_VIDA)
FIX_DOS_RAMOS = BACKEND / "tests" / "fixtures" / "agger_ramos"
#: a gravação de cada ramo de RE — as do FIO da 129-C (o ranking delas foi contado à mão:
#: `test_spec129c_o_app_por_ramo.ESPERADO`)
GRAVACAO_DO_RAMO = {RAMO_CONDOMINIO: "gravacao_condominio_1", RAMO_RESIDENCIAL: "gravacao_residencial_2",
                    RAMO_EMPRESARIAL: "gravacao_empresarial_2"}
#: 📊 a oferta da Porto do canário AO VIVO de vida (16/10, 129-D CANARIO-AO-VIVO §3/§4): o que o robô gravou —
#: R$ 227,16/ano, 12x de R$ 18,93; as coberturas só com o texto de caixa vazia, que o LEITOR descarta. A forma do item
#: é a reconstruída em `test_spec129d_portal_vida._item_da_porto_do_canario` (a resposta crua não foi guardada).
ITEM_DA_PORTO_DO_CANARIO_DE_VIDA = {
    "seguradora": 8, "seguradoraTxt": "Porto Seguro", "nomeSeguradora": "Porto Seguro", "retorno": True,
    "retornoErro": False,
    "resultados": [{"premio": 227.16, "premioMensal": 18.93, "identificacao": "Porto Vida", "packageType": 0,
                    "coberturas": {"DIT": {"valor": "Não Contratada"}, "isDoencasGravesGrupo": {"valor": "Selecione"}},
                    "parcelamentos": [{"parcelas": 12, "tipoPag": 2, "premioPrimeiraParc": 18.93,
                                       "premioDemaisParc": 18.93}]}]}

#: as 4 fotos ilustrativas (D-130C-06): a legenda diz que é EXEMPLO — nunca uma foto que pareça da corretora
LEGENDAS_ILUSTRATIVAS = ("Exemplo · a equipe", "Exemplo · o escritório", "Exemplo · um evento",
                         "Exemplo · uma premiação")
#: 💭 o teto de cada ilustração (o mesmo alvo das fotos reais da marca, §4 da SPEC)
TETO_DA_ILUSTRACAO = 90 * 1024
#: 💭 o prêmio fictício do exemplo (só no modelo do exemplo; `--sem-premio` o tira)
PREMIO_DE_EXEMPLO = {"nome": "Prêmio de exemplo", "ano": 2025}
#: 💭 a distância mínima da etiqueta "EXEMPLO" até a borda, em fração do MAIOR lado da ilustração (conserto KB: o canto
#: arredondado do cartão da página cortava a etiqueta colada a 28 px do canto — laudo de design 130-C)
MARGEM_DA_ETIQUETA = 0.08


def margem_da_etiqueta(largura: int, altura: int) -> int:
    """A margem (px) da etiqueta "EXEMPLO" até a borda: ≥ MARGEM_DA_ETIQUETA do maior lado (arredondada para cima)."""
    return int(math.ceil(MARGEM_DA_ETIQUETA * max(largura, altura)))


#: o "Meu WhatsApp de trabalho" que `--whatsapp-do-dono` aceita: E.164 do Brasil (+55, DDD, 8 ou 9 dígitos)
_RE_E164_BR = re.compile(r"^\+55[1-9][1-9]9?\d{8}$")


def whatsapp_do_dono(valor: str) -> str:
    """O número de `--whatsapp-do-dono` validado (E.164 BR, ex.: +5511900000000) → os dígitos que a página usa."""
    v = str(valor or "").strip()
    if not _RE_E164_BR.fullmatch(v):
        raise ValueError(f"--whatsapp-do-dono precisa ser E.164 do Brasil, como +5511900000000 (veio {v!r})")
    return v[1:]


class EscritaProibida(RuntimeError):
    """Sem `--confirmar` o exemplo não escreve no banco: uma tentativa de escrita é um defeito, e para tudo."""


class _TabelaSoLeitura:
    def __init__(self, tabela: Any, nome: str):
        self._tabela, self._nome = tabela, nome

    def _recusar(self, *_a: Any, **_k: Any) -> Any:
        raise EscritaProibida(f"sem --confirmar nada é gravado (tentativa de escrever em {self._nome!r})")

    insert = upsert = update = delete = _recusar

    def __getattr__(self, nome: str) -> Any:
        return getattr(self._tabela, nome)


class SoLeitura:
    """O cliente do banco que só LÊ: `table(...).select(...)` passa; `insert/upsert/update/delete` e `rpc` levantam."""

    def __init__(self, db: Any):
        self._db = db

    def table(self, nome: str) -> _TabelaSoLeitura:
        return _TabelaSoLeitura(self._db.table(nome), nome)

    from_ = table

    def rpc(self, nome: str, *_a: Any, **_k: Any) -> Any:
        raise EscritaProibida(f"sem --confirmar nenhuma função do banco é chamada ({nome!r})")

    def __getattr__(self, nome: str) -> Any:
        # 🔴 fechado por padrão: nada além de `table`/`from_` chega ao cliente de verdade (nem `.client`, que o
        # `ArtifactService` desembrulha com `getattr(db, "client", db)` — por ele uma escrita passaria por fora)
        raise AttributeError(f"o banco do ensaio só lê tabelas (sem {nome!r})")


def pedido_do_exemplo(company_id: str, pagina: str, *, com_apolice: bool = False, ramo: int = RAMO_AUTO) -> str:
    """O `pedido_id` SINTÉTICO do exemplo (nunca existe em `multicalculo_pedidos`): estável por corretora + página (+ o
    ramo, fora do auto — o do auto é o de sempre, a mesma peça)."""
    chave = f"{company_id}:{pagina}:{'com_apolice' if com_apolice else 'base'}"
    return str(uuid.uuid5(ESPACO_DOS_EXEMPLOS, chave if int(ramo) == RAMO_AUTO else f"{chave}:{int(ramo)}"))


def _json(caminho: Path) -> Any:
    return json.loads(caminho.read_text(encoding="utf-8"))


def andamento_do_ramo(company_id: str, ramo: int, pedido_id: str, agora: datetime
                      ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """(ofertas, eventos, estados) de UM cálculo `padrao` do exemplo de RE/vida — da gravação REAL pelo LEITOR do robô e
    pela LINHA do motor, como a porta os devolveria à própria corretora. Nada é gravado."""
    from portal_worker.multicalculo import contrato as K
    from portal_worker.multicalculo import presets as PRE
    from portal_worker.multicalculo.leitor_agger import capital_pedido_do_corpo, eventos_do_calculo, ler_rodada
    from portal_worker.multicalculo.motor import Motor

    from app.services.multicalculo.pedido import CHAVE_DA_BASICA

    ramo = int(ramo)
    calc_id = str(uuid.uuid5(ESPACO_DOS_EXEMPLOS, f"{pedido_id}:padrao"))
    pedidas: Optional[Dict[str, Any]] = None
    if ramo == RAMO_VIDA:
        itens = list(_json(FIX_DOS_RAMOS / "vida_resultado.json")["calculos"]) + [ITEM_DA_PORTO_DO_CANARIO_DE_VIDA]
        # conserto KB: o fixture embrulha o corpo (`{"formato", …, "corpo": {...}}`) — passar o arquivo inteiro dava
        # capital None (📊 17/10: `capital_pedido_do_corpo(arquivo)` → None; `(arquivo["corpo"])` → 100000)
        capital = capital_pedido_do_corpo(_json(FIX_DOS_RAMOS / "vida_calcularV2_corpo.json")["corpo"])
        rodada = ler_rodada({"calculos": itens, "ramo": ramo}, capital_pedido=capital)
    elif ramo in GRAVACAO_DO_RAMO:
        g = _json(FIX_DOS_RAMOS / f"{GRAVACAO_DO_RAMO[ramo]}.json")
        rodada = ler_rodada({"calculos": g["calculos"], "ramo": ramo})
        conf = g["versao"]["configuracoes"]
        chaves = (set(PRE.CHAVES_DE_COBERTURA_RE[ramo]) | {CHAVE_DA_BASICA}) - {"assist24hs"}
        # o que o corretor PEDIU naquele negócio real (a régua de RE compara a oferta com o pedido — 129-C)
        pedidas = {k: v for k, v in conf.items()
                   if k in chaves and isinstance(v, (int, float)) and not isinstance(v, bool) and v}
    else:
        raise ValueError(f"ramo sem exemplo de RE/vida: {ramo}")
    calculo = {"id": calc_id, "company_id": company_id, "solicitante_company_id": company_id}
    grupo = SimpleNamespace(pedido_id=pedido_id, company_id=company_id, solicitante_company_id=company_id)
    relogio = SimpleNamespace(agora=lambda: agora)
    ofertas: List[Dict[str, Any]] = []
    for resp in rodada.respostas:
        for o in resp.ofertas:
            linha = Motor._linha_da_oferta(relogio, grupo, calculo, o, nova=True)
            linha.pop("comissao_percentual", None)          # a página nunca vê comissão (G3)
            linha["id"] = str(uuid.uuid5(ESPACO_DOS_EXEMPLOS, f"{calc_id}:{len(ofertas)}"))
            ofertas.append(linha)
    eventos = [{"calculo_id": calc_id, "pedido_id": pedido_id, "company_id": company_id,
                "solicitante_company_id": company_id, "tipo": e.tipo, "seguradora": e.seguradora,
                "seguradora_codigo": e.seguradora_codigo, "familia": e.familia}
               for e in eventos_do_calculo([rodada]) if e.tipo == K.SEGURADORA_RECUSOU]
    estado: Dict[str, Any] = {"calculo_id": calc_id, "opcao": "padrao", "corretora_company_id": company_id,
                              "status": "fechado"}
    if pedidas:
        estado["coberturas_pedidas"] = pedidas
    return ofertas, eventos, [estado]


def _cor(valor: Any, padrao: Tuple[int, int, int]) -> Tuple[int, int, int]:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(valor or "").strip())
    if not m:
        return padrao
    h = m.group(1)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _mistura(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))  # type: ignore[return-value]


def ilustracoes_da_marca(cores: Optional[Mapping[str, Any]] = None) -> List[Dict[str, str]]:
    """As 4 fotos ILUSTRATIVAS do exemplo (D-130C-06): gradiente nas cores da marca, formas simples (a equipe, o
    escritório, um evento, uma premiação), a etiqueta "EXEMPLO" desenhada e a legenda "Exemplo · …". WEBP ≤ 90 KB,
    `data:`. ⛔ Só no modelo do exemplo — nunca gravadas na marca de uma corretora."""
    from PIL import Image, ImageDraw, ImageFont

    cores = cores or {}
    primaria = _cor(cores.get("primaria"), (29, 85, 121))
    acento = _cor(cores.get("acento"), (238, 117, 1))
    escura = _mistura(primaria, (8, 13, 17), 0.55)
    W, H = 960, 640
    branco = (255, 255, 255)

    def fundo(i: int) -> "Image.Image":
        topo = _mistura(primaria, branco, 0.10 + 0.06 * i)
        base = _mistura(escura, acento, 0.12 + 0.05 * i)
        img = Image.new("RGB", (W, H), topo)
        d = ImageDraw.Draw(img)
        for y in range(H):
            d.line([(0, y), (W, y)], fill=_mistura(topo, base, y / (H - 1)))
        return img

    def equipe(d: "ImageDraw.ImageDraw") -> None:
        for k, (cx, r) in enumerate(((210, 62), (365, 70), (520, 78), (675, 70), (820, 60))):
            cy = 300 - (r - 60) * 2
            tom = (*_mistura(branco, acento, 0.25 * (k % 2)), 230)
            d.ellipse([cx - r * 0.55, cy - r * 1.6, cx + r * 0.55, cy - r * 0.5], fill=tom)
            d.rounded_rectangle([cx - r, cy - r * 0.35, cx + r, cy + r * 2.4], radius=int(r * 0.9), fill=tom)
        d.rectangle([0, 520, W, H], fill=(*escura, 150))

    def escritorio(d: "ImageDraw.ImageDraw") -> None:
        d.rectangle([0, 560, W, H], fill=(*escura, 170))
        for x0, x1, topo in ((120, 330, 210), (360, 620, 120), (650, 860, 260)):
            d.rectangle([x0, topo, x1, 560], fill=(*branco, 215))
            for y in range(topo + 30, 540, 52):
                for x in range(x0 + 24, x1 - 30, 46):
                    aceso = (x + y) % 3 == 0
                    d.rectangle([x, y, x + 26, y + 30], fill=(*(acento if aceso else primaria), 235))

    def evento(d: "ImageDraw.ImageDraw") -> None:
        for k in range(9):                                          # as bandeirinhas
            x = 60 + k * 105
            d.polygon([(x, 90 + (k % 2) * 14), (x + 90, 90 + ((k + 1) % 2) * 14), (x + 45, 175)],
                      fill=(*(acento if k % 2 else branco), 230))
        d.line([(40, 92), (W - 40, 92)], fill=(*branco, 200), width=4)
        for k, (cx, cy, r) in enumerate(((240, 380, 70), (420, 330, 82), (600, 390, 66), (760, 340, 76))):
            cor = (*(acento if k % 2 == 0 else _mistura(branco, primaria, 0.2)), 235)
            d.ellipse([cx - r, cy - r * 1.2, cx + r, cy + r * 1.2], fill=cor)
            d.line([(cx, cy + r * 1.2), (cx - 10, cy + r * 1.2 + 120)], fill=(*branco, 200), width=3)
        for k in range(46):                                          # o confete
            x, y = (k * 197) % W, 200 + (k * 131) % 380
            d.rectangle([x, y, x + 10, y + 6], fill=(*(acento if k % 3 else branco), 210))

    def premiacao(d: "ImageDraw.ImageDraw") -> None:
        ouro = _mistura(acento, (255, 214, 102), 0.55)
        cx = W // 2
        d.ellipse([cx - 230, 110, cx + 230, 570], fill=(*branco, 40))
        d.chord([cx - 140, 120, cx + 140, 400], 0, 180, fill=(*ouro, 255))
        d.rectangle([cx - 140, 150, cx + 140, 262], fill=(*ouro, 255))
        for lado in (-1, 1):                                         # as alças
            x = cx + lado * 165
            d.arc([x - 55, 170, x + 55, 290], 90 if lado > 0 else 270, 270 if lado > 0 else 90,
                  fill=(*ouro, 255), width=18)
        d.rectangle([cx - 24, 395, cx + 24, 470], fill=(*ouro, 255))
        d.rounded_rectangle([cx - 120, 470, cx + 120, 530], radius=12, fill=(*escura, 235))
        estrela = [(cx + (38 if k % 2 == 0 else 16) * math.cos(math.pi / 2 + k * math.pi / 5),
                    250 - (38 if k % 2 == 0 else 16) * math.sin(math.pi / 2 + k * math.pi / 5)) for k in range(10)]
        d.polygon(estrela, fill=(*branco, 255))

    try:
        fonte = ImageFont.load_default(size=30)
    except TypeError:                                               # Pillow antigo: sem tamanho
        fonte = ImageFont.load_default()
    saida: List[Dict[str, str]] = []
    for i, (desenho, legenda) in enumerate(zip((equipe, escritorio, evento, premiacao), LEGENDAS_ILUSTRATIVAS)):
        img = fundo(i).convert("RGBA")
        camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        desenho(ImageDraw.Draw(camada))
        img = Image.alpha_composite(img, camada)
        d = ImageDraw.Draw(img)
        # conserto KB (laudo de design 130-C): a etiqueta longe do canto — o cartão da página arredonda a foto e o
        # canto cortava o "EXEMPLO"; a margem é MARGEM_DA_ETIQUETA do MAIOR lado, nos dois eixos
        x0 = y0 = margem_da_etiqueta(W, H)
        d.rounded_rectangle([x0, y0, x0 + 186, y0 + 54], radius=27, fill=(*branco, 235))
        d.text((x0 + 93, y0 + 27), "EXEMPLO", fill=escura, font=fonte, anchor="mm")
        rgb = img.convert("RGB")
        dados = b""
        for qualidade in (80, 70, 60, 50, 40):
            buf = io.BytesIO()
            rgb.save(buf, "WEBP", quality=qualidade, method=6)
            dados = buf.getvalue()
            if len(dados) <= TETO_DA_ILUSTRACAO:
                break
        if len(dados) > TETO_DA_ILUSTRACAO:
            continue                                                # nunca uma ilustração acima do teto
        saida.append({"src": "data:image/webp;base64," + base64.b64encode(dados).decode("ascii"),
                      "legenda": legenda})
    return saida


def _contrato() -> Dict[str, Any]:
    m = json.loads(MODELO_DO_CONTRATO.read_text(encoding="utf-8"))
    m.pop("_contrato", None)
    return m


def _derivada(base: Mapping[str, Any], *, id_: str, rotulo: str, fator: float) -> Dict[str, Any]:
    """Uma opção da renovação a partir da "Sua renovação" (o robô a calcula assim: a mesma seguradora, outro pedido)."""
    o = copy.deepcopy(dict(base))
    o.update(id=id_, rotulo=rotulo, premio_anual=round(float(base["premio_anual"]) * fator, 2), o_que_muda=[])
    if isinstance(o.get("parcelas"), dict) and o["parcelas"].get("valor"):
        o["parcelas"] = dict(o["parcelas"], valor=round(float(o["parcelas"]["valor"]) * fator, 2))
        o["parcelas"].pop("total", None)
    o.pop("parcelas_sem_juros", None)
    o.pop("por_que_mais_barata", None)
    return o


def _opcoes_da_venda(contrato: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """As 3 opções da venda (§4.3: Recomendada · Mais em conta · Mais completa) — as do contrato, como o motor as
    devolveu; a "outra completa" do contrato faz o papel da "Mais completa" (a seguradora com mais cobertura)."""
    ops = [copy.deepcopy(o) for o in contrato["opcoes"]]
    for o in ops[1:]:
        if o["id"] == "outra_completa":
            o["id"], o["rotulo"] = "mais_completa", "Mais completa"
    return ops


#: as ofertas saneadas do canário — de onde vêm as coberturas BRUTAS que os textos do produto leem
OFERTAS_SANEADAS = BACKEND / "tests" / "fixtures" / "proposta" / "ofertas_canario_saneadas.json"


def _coberturas_brutas(seguradora: str, premio: float) -> Dict[str, Any]:
    """As coberturas da oferta saneada que deu esta opção do contrato (a mesma seguradora e o mesmo prêmio)."""
    dados = json.loads(OFERTAS_SANEADAS.read_text(encoding="utf-8"))
    o = next((x for x in dados.get("ofertas") or [] if str(x.get("seguradora")) == seguradora
              and abs(float(x.get("premio_total") or 0) - float(premio)) < 0.005), None)
    return dict((o or {}).get("coberturas") or {})


def _opcoes_da_renovacao(contrato: Mapping[str, Any], *, premio_de_hoje: float) -> List[Dict[str, Any]]:
    """A "Sua renovação" (a seguradora de hoje) em 1º · Franquia reduzida · Mais completa. Os motivos, o "o que muda"
    e o "por que" de cada cartão são os textos do PRODUTO (`comparacao._motivos`/`_o_que_muda`/
    `_por_que_da_renovacao`, os mesmos de `_opcoes_da_renovacao` da 131-B) sobre as coberturas da oferta saneada."""
    from app.services.multicalculo import comparacao as CMP

    rec = copy.deepcopy(contrato["opcoes"][0])
    ramo = int(contrato.get("ramo") or CMP.RAMO_AUTO)
    sua = dict(rec, id="sua_renovacao", rotulo="Sua renovação", o_que_muda=[])
    reduzida = _derivada(sua, id_="franquia_reduzida", rotulo="Franquia reduzida", fator=1.05)
    if isinstance(reduzida.get("franquia"), dict) and reduzida["franquia"].get("valor"):
        reduzida["franquia"] = dict(reduzida["franquia"], valor=round(float(reduzida["franquia"]["valor"]) / 2, 2),
                                    tipo="Reduzida")
    completa = _derivada(sua, id_="mais_completa", rotulo="Mais completa", fator=1.08)
    ops = [sua, reduzida, completa]
    cob = _coberturas_brutas(str(rec["seguradora"]), float(rec["premio_anual"]))
    entradas = [{"oferta_id": o["id"], "seguradora": o["seguradora"], "premio_anual": o["premio_anual"],
                 "franquia": dict(o.get("franquia") or {"valor": None}), "parcelas": o.get("parcelas"),
                 "opcao": "anterior", "ramo": ramo,
                 "coberturas_brutas": dict(cob, reparoRapido=True) if o["id"] == "mais_completa" else dict(cob)}
                for o in ops]
    base = entradas[0]
    hoje = {"seguradora": sua["seguradora"], "premio_anual": premio_de_hoje}
    for o, e in zip(ops, entradas):
        o["motivos"] = CMP._motivos(e, "renovacao", ranking_completa=[], referencia=base, rotulo_ref=sua["rotulo"],
                                    pool=entradas, apolice_atual=hoje, ramo=ramo, renovacao=True)
        o["o_que_muda"] = CMP._o_que_muda(e, base, sua["rotulo"], o["id"], renovacao=True)
        o["por_que"] = CMP._por_que_da_renovacao(e, o["id"], base, ramo)
        # R6/(e): os adicionais da oferta (os pequenos reparos da "Mais completa"), como `comparacao._opcao` os grava
        a_mais = CMP.coberturas_a_mais({"coberturas": e["coberturas_brutas"]}, ramo=ramo)
        if a_mais:
            o["coberturas_a_mais"] = a_mais
    return ops


def _economia_contra_a_apolice(modelo: Mapping[str, Any], atual: float) -> Optional[Dict[str, Any]]:
    """A MESMA conta de `proposta.economia` (contra o preço atual: o menor preço do quadro), sobre o quadro do exemplo."""
    precos = [float(x["premio_anual"]) for x in list(modelo.get("opcoes") or []) + list(modelo.get("ranking") or [])
              if x.get("premio_anual")]
    if not precos or atual - min(precos) < 0.01:
        return None
    para = min(precos)
    return {"ate": round(atual - para, 2), "de": round(atual, 2), "para": round(para, 2), "contra": "atual"}


async def montar_modelo_de_exemplo(db: Any, company_id: str, pagina: str, *, com_apolice: bool = False,
                                   com_whatsapp_da_corretora: bool = False, agora: Optional[datetime] = None,
                                   baixar_logo: Any = None, whatsapp_do_dono_ficticio: Optional[str] = None,
                                   ramo: int = RAMO_AUTO, sem_fotos: bool = False, sem_premio: bool = False
                                   ) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """(modelo, ctx, pedido_id) do exemplo. Lê do banco SÓ a marca e a config da corretora (filtro `company_id`).
    `whatsapp_do_dono_ficticio` (E.164 BR): o WhatsApp de trabalho CONFIRMADO da dona/do corretor fictício — SÓ no
    modelo (nunca em tabela); o "Quem cuida de você" e o "Quero fechar"/"Quero renovar" passam a apontar para ele.
    SPEC-130-C: `ramo` (31 o auto de sempre; 16/2/18/91 pelas gravações reais) · `sem_fotos` (sem o carrossel) ·
    `sem_premio` (sem o prêmio fictício)."""
    from app.services.multicalculo import comparacao as CMP
    from app.services.multicalculo import config as CFG
    from app.services.multicalculo.pedido import CHAVE_DA_BASICA
    from app.services.multicalculo import manual_de_negociacao as MANUAL
    from app.services.multicalculo import proposta as P

    if pagina not in PAGINAS:
        raise ValueError(f"página desconhecida: {pagina!r} (aceitas: {', '.join(PAGINAS)})")
    ramo = int(ramo)
    if ramo not in RAMOS:
        raise ValueError(f"ramo desconhecido: {ramo} (aceitos: {', '.join(str(r) for r in RAMOS)})")
    if com_apolice and ramo != RAMO_AUTO:
        raise ValueError("--com-apolice só no auto: o exemplo de RE/vida não tem apólice fictícia com prêmio")
    company_id = P._uuid(company_id, "company_id")
    renovacao = pagina == "renovacao"
    pedido_id = pedido_do_exemplo(company_id, pagina, com_apolice=com_apolice and not renovacao, ramo=ramo)
    cfg = CFG.carregar(company_id, db=db, servico="renovacao" if renovacao else "cotacao")
    anfitria = await P.montar_anfitria(db, company_id, cfg, baixar_logo=baixar_logo)
    # SPEC-130-C (D-130C-06): sem foto cadastrada, as 4 ILUSTRAÇÕES marcadas "Exemplo" (só neste modelo); o prêmio
    # fictício idem. `--sem-fotos` / `--sem-premio` mostram a página sem eles.
    if sem_fotos:
        anfitria["fotos"] = []
    elif not anfitria.get("fotos"):
        anfitria["fotos"] = ilustracoes_da_marca(anfitria.get("cores"))
    if sem_premio:
        anfitria["premios"] = []
    elif not anfitria.get("premios"):
        anfitria["premios"] = [dict(PREMIO_DE_EXEMPLO)]
    numero = anfitria.pop("whatsapp", None)                     # ⛔ nenhum telefone, salvo a escolha explícita
    if com_whatsapp_da_corretora and numero:
        anfitria["whatsapp"] = numero
    do_dono = whatsapp_do_dono(whatsapp_do_dono_ficticio) if whatsapp_do_dono_ficticio else None
    # a regra do produto (D-131-42 / D-132B-05): o dono confirmado → a corretora → ninguém
    destino = do_dono or (numero if com_whatsapp_da_corretora else None)
    pessoa = {"whatsapp": do_dono} if do_dono else {}

    hoje = P._agora(agora)
    folga = int(cfg["link"]["folga_dias"])
    dias = max(1, DIAS_DO_LINK - folga)                        # o link vale `dias + folga` = DIAS_DO_LINK
    contrato = _contrato()
    modelo: Dict[str, Any] = {
        **contrato,
        "origem": "corretora",
        "cliente": {"primeiro_nome": CLIENTE_FICTICIA},
        "bem": dict(CARRO_POPULAR),
        "anfitria": anfitria,
        "entre_corretoras": None,
        "validade_ate": (hoje.date() + timedelta(days=dias)).isoformat(),
        "gerado_em": hoje.replace(microsecond=0).isoformat(),
        "aviso_legal": P.AVISO_LEGAL_CORRETORA,
        "exemplo": True,
    }
    resumo = dict(modelo.get("resumo") or {})
    resumo.pop("economia", None)
    modelo["resumo"] = resumo
    ref_curta = pedido_id[:8]
    basica = None
    opcoes_re: List[Dict[str, Any]] = []
    if ramo != RAMO_AUTO:
        # SPEC-130-C: as opções de RE/vida saem da gravação REAL pelo leitor, pela comparação e pelas opções do produto
        ofertas, eventos, estados = andamento_do_ramo(company_id, ramo, pedido_id, hoje)
        cfg_c = CMP.config_da_renovacao(cfg, estados) if renovacao else cfg
        quadro = CMP.comparar(ofertas, eventos, estados=estados, config=cfg_c, ramo=ramo)
        ranking = quadro.ranking(quadro.opcao_completa, company_id)
        if not ranking:
            raise RuntimeError(f"a gravação do ramo {ramo} não deu nenhuma oferta completa")
        apolice = ({"seguradora": str(ranking[0].get("seguradora_original") or ranking[0]["seguradora"])}
                   if renovacao else None)
        ops = CMP.opcoes(quadro, situacao="renovacao" if renovacao else "novo_sem_apolice", apolice_atual=apolice,
                         config=cfg_c, corretora=company_id)
        # conserto KB: o `ramo` leva o capital segurado da VIDA a cada opção (o `capital_pedido` que o leitor gravou
        # do corpo REAL `vida_calcularV2_corpo.json` — a Porto do canário não ecoa o capital)
        opcoes_re, _brutas = P.opcoes_da_pagina(ops, ofertas, cfg_c, ramo=ramo)
        resumo = {k: quadro.resumo[k] for k in ("seguradoras_cotadas", "com_preco_comparavel",
                                                 "com_produto_diferente", "nao_responderam")}
        resumo.update(P.resumo_do_volume(ofertas, {}, cfg_c, estados, eventos))
        modelo.update({"ramo": ramo, "bem": P._bem(ofertas, ramo), "resumo": resumo,
                       **P.partes_do_quadro(quadro, ranking)})
        basica = (estados[0].get("coberturas_pedidas") or {}).get(CHAVE_DA_BASICA) if renovacao else None

    if renovacao:
        modelo["situacao"] = "renovacao"
        if ramo == RAMO_AUTO:
            premio_de_hoje = round(float(contrato["opcoes"][0]["premio_anual"]) / (1 + REAJUSTE_FICTICIO), 2)
            modelo["opcoes"] = _opcoes_da_renovacao(contrato, premio_de_hoje=premio_de_hoje)
        else:
            modelo["opcoes"] = opcoes_re
            premio_de_hoje = round(float(opcoes_re[0]["premio_anual"]) / (1 + REAJUSTE_FICTICIO), 2)
        item = {"fimvig": (hoje.date() + timedelta(days=DIAS_ATE_VENCER)).isoformat(),
                "seguradora_atual": modelo["opcoes"][0]["seguradora"], "premio_atual": premio_de_hoje}
        reajuste = CFG.reajuste_basica_pct(cfg, modelo["ramo"])
        modelo["renovacao"] = P.bloco_da_renovacao(item, dono={"primeiro_nome": DONA_FICTICIA, **pessoa}, anos=None,
                                                   basica=basica, reajuste_pct=reajuste)
        modelo["cta"] = P.cta_da_pagina(destino, modelo["opcoes"], nome=CLIENTE_FICTICIA, ref_curta=ref_curta,
                                        renovacao=True)
        modelo["renovacao"]["fechar_com"] = "dono" if do_dono else ("corretora" if destino else "nenhum")
        modelo["faq"] = P.faq_da_renovacao(ramo=modelo["ramo"], opcoes=modelo["opcoes"],
                                           vence_em=modelo["renovacao"].get("vence_em"), reajuste_pct=reajuste,
                                           com_whatsapp=bool(destino),
                                           reajuste_capital_pct=P._reajuste_do_capital(cfg, modelo["ramo"]))
    else:
        modelo["situacao"] = "novo_com_apolice" if com_apolice else "novo_sem_apolice"
        modelo["opcoes"] = _opcoes_da_venda(contrato) if ramo == RAMO_AUTO else opcoes_re
        if com_apolice:
            eco = _economia_contra_a_apolice(modelo, PREMIO_DA_APOLICE_FICTICIA)
            if eco:
                modelo["resumo"]["economia"] = eco
        modelo["cta"] = P.cta_da_pagina(destino, modelo["opcoes"], nome=CLIENTE_FICTICIA, ref_curta=ref_curta)
        modelo["venda"] = P.bloco_da_venda(corretor={"primeiro_nome": CORRETOR_FICTICIO, **pessoa},
                                           marca=P.marca_da_venda(db, company_id),
                                           pagina=CFG.pagina_da_cotacao(cfg, ramo=modelo["ramo"]), destino=destino)
        modelo["faq"] = [{"p": f["pergunta"], "r": f["resposta"]} for f in modelo["venda"]["faq"]]
        modelo["pagina"] = "venda"
    modelo["sinistro"] = MANUAL.sinistro_padrao(cfg, com_whatsapp=bool(destino), ramo=modelo["ramo"])
    P._sem_comissao(modelo)
    ctx = {"anfitria_id": company_id, "cfg_sol": cfg, "dias": dias, "hoje": hoje, "refs": {}}
    return modelo, ctx, pedido_id


def renderizar(modelo: Mapping[str, Any]) -> str:
    """O HTML pelo MESMO gancho que o Hub usa ao renderizar a peça (`templates.PROPOSTA.renderizador`)."""
    from app.services.artifacts.templates import POR_CHAVE
    from app.services.multicalculo.proposta import TEMPLATE_DA_PROPOSTA

    return POR_CHAVE[TEMPLATE_DA_PROPOSTA].renderizador(dict(modelo))


async def gerar_exemplo(db: Any, company_id: str, pagina: str, *, com_apolice: bool = False,
                        com_whatsapp_da_corretora: bool = False, confirmar: bool = False,
                        whatsapp_do_dono_ficticio: Optional[str] = None,
                        saida: Optional[Path] = None, base_url: Optional[str] = None,
                        agora: Optional[datetime] = None, baixar_logo: Any = None, ramo: int = RAMO_AUTO,
                        sem_fotos: bool = False, sem_premio: bool = False) -> Dict[str, Any]:
    """Monta e (com `confirmar`) publica o exemplo. Devolve {url?, token?, artifact_id?, arquivo?, bytes}."""
    from app.services.multicalculo import proposta as P

    extra = {"ramo": ramo, "sem_fotos": sem_fotos, "sem_premio": sem_premio}
    if not confirmar:
        modelo, _ctx, _pid = await montar_modelo_de_exemplo(
            SoLeitura(db), company_id, pagina, com_apolice=com_apolice,
            com_whatsapp_da_corretora=com_whatsapp_da_corretora, agora=agora, baixar_logo=baixar_logo,
            whatsapp_do_dono_ficticio=whatsapp_do_dono_ficticio, **extra)
        html = renderizar(modelo)
        sufixo = ("-com-apolice" if com_apolice else "") + ("" if int(ramo) == RAMO_AUTO else f"-{int(ramo)}")
        destino = Path(saida) if saida else Path.cwd() / f"exemplo-{pagina}{sufixo}.html"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(html.encode("utf-8"))              # os MESMOS bytes do render (sem trocar \n no Windows)
        return {"arquivo": str(destino), "bytes": len(html.encode("utf-8"))}

    base = P._base_do_link(base_url)                           # sem endereço público → recusa ANTES de gravar
    modelo, ctx, pedido_id = await montar_modelo_de_exemplo(
        db, company_id, pagina, com_apolice=com_apolice, com_whatsapp_da_corretora=com_whatsapp_da_corretora,
        agora=agora, baixar_logo=baixar_logo, whatsapp_do_dono_ficticio=whatsapp_do_dono_ficticio, **extra)
    titulo ="Exemplo · Renovação do seguro" if pagina == "renovacao" else "Exemplo · Cotação de seguro"
    publicado = P._gravar_e_compartilhar(db, ctx["anfitria_id"], pedido_id, modelo, ctx, base, titulo_base=titulo,
                                         subject_extra={"kind": "exemplo_da_pagina", "exemplo": True,
                                                        "pagina": pagina})
    return {**publicado, "bytes": len(renderizar(modelo).encode("utf-8"))}


def _argumentos(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Publica (ou só renderiza) um EXEMPLO da página do cliente com a marca "
                                             "real da corretora e dados fictícios.")
    ap.add_argument("--company-id", required=True, help="o uuid da corretora (a marca vem do banco)")
    ap.add_argument("--pagina", required=True, choices=PAGINAS)
    ap.add_argument("--com-apolice", action="store_true", help="venda: a cliente tem apólice (mostra a economia)")
    ap.add_argument("--com-whatsapp-da-corretora", action="store_true",
                    help="o botão 'Quero fechar' leva ao WhatsApp de atendimento da corretora (padrão: sem botão)")
    ap.add_argument("--whatsapp-do-dono", default=None, metavar="+55DDDNUMERO",
                    help="o WhatsApp de trabalho CONFIRMADO do dono/corretor fictício (E.164 BR, ex.: +5511900000000):"
                         " só no modelo do exemplo, nunca em tabela; a barra 'Quero fechar' aponta para ele")
    ap.add_argument("--confirmar", action="store_true", help="publica de verdade; sem isto, só grava o HTML local")
    ap.add_argument("--saida", type=Path, default=None, help="sem --confirmar: o arquivo .html de saída")
    ap.add_argument("--ramo", type=int, default=RAMO_AUTO, choices=RAMOS,
                    help="31 auto (padrão) · 16 condomínio · 2 residencial · 18 empresarial · 91 vida")
    ap.add_argument("--sem-fotos", action="store_true", help="a página sem o carrossel de fotos (nem as ilustrativas)")
    ap.add_argument("--sem-premio", action="store_true", help="a página sem o prêmio fictício do exemplo")
    return ap.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None, *, db: Any = None) -> int:
    a = _argumentos(argv)
    if a.whatsapp_do_dono:
        try:
            whatsapp_do_dono(a.whatsapp_do_dono)
        except ValueError as exc:
            raise SystemExit(str(exc))
    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client().client
    r = asyncio.run(gerar_exemplo(db, a.company_id, a.pagina, com_apolice=a.com_apolice,
                                  com_whatsapp_da_corretora=a.com_whatsapp_da_corretora, confirmar=a.confirmar,
                                  whatsapp_do_dono_ficticio=a.whatsapp_do_dono,
                                  saida=a.saida, ramo=a.ramo, sem_fotos=a.sem_fotos, sem_premio=a.sem_premio))
    print(r["url"] if a.confirmar else r["arquivo"])
    print(f"{r['bytes']} bytes de HTML")
    return 0


if __name__ == "__main__":
    sys.exit(main())
