# -*- coding: utf-8 -*-
"""SPEC-124 F2 — gera o corpus `visao_campos`: 10 documentos SINTÉTICOS em imagem + o gabarito por campo.

⛔ Nenhum dado real. O texto do corpus (`casos.jsonl`) guarda só MARCADORES (`{{CPF:V1}}`, `{{PLACA:V1}}`,
`{{NOME:V1}}`, `{{APOLICE:V1}}`); `app/services/evals/dubles.py:materializar` os troca por valores
FICTÍCIOS DETERMINÍSTICOS — CPF com dígito verificador válido, placa no formato Mercosul, apólice de 15
dígitos — e é com ESSES MESMOS valores que este script desenha as imagens. O gabarito e a imagem nunca
divergem: os dois saem do mesmo marcador.

Rodar (de backend/):  python tests/corpus/bancada/visao_campos/gerar_imagens.py
Mudou um documento? Rode de novo e suba `versao` no MANIFESTO.json e aqui.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(AQUI, "..", "..", "..", ".."))
sys.path.insert(0, BACKEND)

from app.services.evals.dubles import materializar  # noqa: E402

VERSAO = 4   # = MANIFESTO.json (papel novo: dataset novo na Eval Fabric, sem subir a versão dos outros)
ORIGEM = ("💭 SINTÉTICO — documento gerado por PIL (gerar_imagens.py); marcadores materializados por "
          "dubles.materializar; nenhum dado real")


def _fonte(tam: int, negrito: bool = False, mono: bool = False):
    nomes = (["consola.ttf", "DejaVuSansMono.ttf"] if mono else
             (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if negrito else ["arial.ttf", "DejaVuSans.ttf"]))
    for n in nomes:
        try:
            return ImageFont.truetype(n, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def _br(valor: float) -> str:
    """1234.5 → 'R$ 1.234,50'."""
    s = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def _dmy(iso: str) -> str:
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def _digitos(semente: str, n: int) -> str:
    h = hashlib.sha256(semente.encode()).hexdigest()
    return "".join(str(int(c, 16) % 10) for c in h)[:n]


# ---------------------------------------------------------------------------
# Os 10 documentos — o GABARITO (campos do esquema; null = o documento não tem)
# ---------------------------------------------------------------------------
NULO = {"tipo_documento": None, "nome": None, "cpf": None, "placa": None, "numero_apolice": None,
        "vigencia_inicio": None, "vigencia_fim": None, "coberturas": None, "valor_total": None,
        "franquia": None, "vencimento": None, "validade": None}


#: A linha "Assistência 24h" fica DENTRO do quadro de coberturas do layout A, sem LMI. 📊 01/10/2026, 1ª
#: rodada (gpt-6-luna k=3): o modelo a listou com valor null em 4/30 — leitura defensável do documento.
#: O gabarito a declara OPCIONAL (pode vir sem valor, ou não vir); com valor inventado continua erro.
ASSISTENCIA_OPCIONAL = {"nome": "Assistência 24h", "valor": None, "opcional": True}


def _g(**kw) -> dict:
    return {**NULO, **kw}


DOCS = [
    ("apolice-auto-a", "apolice_auto", True, _g(
        tipo_documento="apolice_auto", nome="{{NOME:VA}} Duarte Moreira", cpf="{{CPF:VA}}",
        placa="{{PLACA:VA}}", numero_apolice="{{APOLICE:VA}}", vigencia_inicio="2026-08-15",
        vigencia_fim="2027-08-15",
        coberturas=[{"nome": "Casco (Colisão, Incêndio e Roubo)", "valor": 92350.00},
                    {"nome": "Danos Materiais a Terceiros", "valor": 150000.00},
                    {"nome": "Danos Corporais a Terceiros", "valor": 150000.00},
                    {"nome": "Acidentes Pessoais por Passageiro - Morte", "valor": 20000.00},
                    ASSISTENCIA_OPCIONAL],
        valor_total=3487.62, franquia=4120.00)),
    ("apolice-auto-b", "apolice_auto", True, _g(
        tipo_documento="apolice_auto", nome="{{NOME:VB}} Siqueira Lopes", cpf="{{CPF:VB}}",
        placa="{{PLACA:VB}}", numero_apolice="{{APOLICE:VB}}", vigencia_inicio="2026-02-03",
        vigencia_fim="2027-02-03",
        coberturas=[{"nome": "Casco Compreensivo", "valor": 61800.00},
                    {"nome": "RCF-V Danos Materiais", "valor": 100000.00},
                    {"nome": "RCF-V Danos Corporais", "valor": 200000.00}],
        valor_total=3125.19, franquia=2980.00)),
    ("apolice-residencial", "apolice_residencial", True, _g(
        tipo_documento="apolice_residencial", nome="{{NOME:VC}} Paiva Nogueira", cpf="{{CPF:VC}}",
        numero_apolice="{{APOLICE:VC}}", vigencia_inicio="2026-05-10", vigencia_fim="2027-05-10",
        coberturas=[{"nome": "Incêndio, Raio e Explosão", "valor": 450000.00},
                    {"nome": "Danos Elétricos", "valor": 25000.00},
                    {"nome": "Roubo ou Furto Qualificado", "valor": 30000.00},
                    {"nome": "Responsabilidade Civil Familiar", "valor": 50000.00},
                    {"nome": "Vendaval", "valor": 40000.00}],
        valor_total=689.90)),
    ("cnh", "cnh", False, _g(
        tipo_documento="cnh", nome="{{NOME:VD}} Teixeira Campos", cpf="{{CPF:VD}}", validade="2031-04-22")),
    ("crlv", "crlv", True, _g(
        tipo_documento="crlv", nome="{{NOME:VE}} Rocha Albuquerque", cpf="{{CPF:VE}}", placa="{{PLACA:VE}}")),
    ("orcamento", "orcamento", False, _g(
        tipo_documento="orcamento", nome="{{NOME:VF}} Barros Vieira", placa="{{PLACA:VF}}", valor_total=2920.00)),
    ("boleto", "boleto", True, _g(
        tipo_documento="boleto", nome="{{NOME:VG}} Fonseca Lima", cpf="{{CPF:VG}}",
        numero_apolice="{{APOLICE:VG}}", valor_total=412.37, vencimento="2026-10-20")),
    ("foto-parabrisa", "foto_dano", True, _g(tipo_documento="foto_dano", placa="{{PLACA:VH}}")),
    ("apolice-auto-degradada", "apolice_auto", True, _g(
        tipo_documento="apolice_auto", nome="{{NOME:VI}} Antunes Ribeiro", cpf="{{CPF:VI}}",
        placa="{{PLACA:VI}}", numero_apolice="{{APOLICE:VI}}", vigencia_inicio="2026-11-01",
        vigencia_fim="2027-11-01",
        coberturas=[{"nome": "Casco (Colisão, Incêndio e Roubo)", "valor": 74900.00},
                    {"nome": "Danos Materiais a Terceiros", "valor": 100000.00},
                    {"nome": "Danos Corporais a Terceiros", "valor": 100000.00},
                    ASSISTENCIA_OPCIONAL],
        valor_total=2764.08, franquia=3870.00)),
    ("cnh-fotografada", "cnh", False, _g(
        tipo_documento="cnh", nome="{{NOME:VJ}} Correia Matos", cpf="{{CPF:VJ}}", validade="2029-12-03")),
]


# ---------------------------------------------------------------------------
# Desenho
# ---------------------------------------------------------------------------
class Folha:
    def __init__(self, w: int, h: int, fundo="white"):
        self.img = Image.new("RGB", (w, h), fundo)
        self.d = ImageDraw.Draw(self.img)
        self.y = 40

    def texto(self, x, t, tam=24, negrito=False, cor="black", mono=False, avancar=True, y=None):
        yy = self.y if y is None else y
        self.d.text((x, yy), t, fill=cor, font=_fonte(tam, negrito, mono))
        if avancar and y is None:
            self.y += int(tam * 1.55)

    def faixa(self, t, cor="#1f3b63"):
        self.d.rectangle([30, self.y, self.img.width - 30, self.y + 40], fill=cor)
        self.texto(45, t, 22, True, "white", avancar=False, y=self.y + 8)
        self.y += 56

    def linha(self):
        self.d.line([30, self.y, self.img.width - 30, self.y], fill="#999999", width=2)
        self.y += 14


def apolice_auto_a(g: dict, ex: dict) -> Image.Image:
    f = Folha(1100, 1240)
    f.texto(40, "SEGURADORA EXEMPLO S.A.", 34, True, "#1f3b63")
    f.texto(40, "APÓLICE DE SEGURO AUTOMÓVEL — DOCUMENTO FICTÍCIO PARA TESTE", 20, cor="#444444")
    f.texto(40, f"Apólice nº {g['numero_apolice']}      Proposta nº {ex['proposta']}      Endosso 0", 22, True)
    f.texto(40, f"Vigência: das 24h de {_dmy(g['vigencia_inicio'])} às 24h de {_dmy(g['vigencia_fim'])}", 22)
    f.faixa("DADOS DO SEGURADO")
    f.texto(45, f"Segurado: {g['nome'].upper()}", 24)
    f.texto(45, f"CPF: {g['cpf']}        Data de nascimento: 14/03/1984", 24)
    f.texto(45, "Endereço: Rua das Acácias, 120 — Bairro Modelo — Cidade Exemplo/UF", 22)
    f.faixa("DADOS DO VEÍCULO")
    f.texto(45, "Marca/Modelo: EXEMPLO MOTORS HATCH 1.0 TURBO    Ano/Modelo: 2023/2024", 22)
    f.texto(45, f"Placa: {g['placa']}        Chassi: {ex['chassi']}        Uso: Particular", 22)
    f.faixa("COBERTURAS CONTRATADAS (LMI)")
    for c in [c for c in g["coberturas"] if not c.get("opcional")]:
        f.texto(45, c["nome"], 22, avancar=False)
        f.texto(760, _br(c["valor"]), 22, True)
    f.texto(45, "Assistência 24h: Plano Completo (guincho 400 km)", 20, cor="#444444")
    f.faixa("FRANQUIA E PRÊMIO")
    f.texto(45, f"Franquia do casco (básica): {_br(g['franquia'])}", 24, True)
    f.texto(45, f"Prêmio líquido: {_br(ex['premio_liquido'])}     IOF: {_br(ex['iof'])}", 22)
    f.texto(45, f"PRÊMIO TOTAL: {_br(g['valor_total'])}   em 10x sem juros", 26, True)
    f.linha()
    f.texto(40, "Documento sintético gerado para avaliação de leitura. Sem valor contratual.", 18, cor="#777777")
    return f.img


def apolice_auto_b(g: dict, ex: dict) -> Image.Image:
    f = Folha(1150, 1260, "#fbfaf5")
    f.d.rectangle([20, 20, 1130, 1240], outline="#8a1c1c", width=4)
    f.texto(50, "COMPANHIA MODELO DE SEGUROS", 30, True, "#8a1c1c")
    f.texto(50, "Seguro Auto Individual — Frente da Apólice (FICTÍCIA)", 22, cor="#555555")
    f.linha()
    x2 = 600
    pares = [("Nº da Apólice", g["numero_apolice"]), ("Ramo", "0531 — Automóvel"),
             ("Segurado(a)", g["nome"].upper()), ("CPF/CNPJ", g["cpf"]),
             ("Início de Vigência", f"00h00 de {_dmy(g['vigencia_inicio'])}"),
             ("Término de Vigência", f"24h00 de {_dmy(g['vigencia_fim'])}"),
             ("Veículo", "EXEMPLO SEDAN 2.0 FLEX AUT."), ("Placa / Ano", f"{g['placa']} / 2022")]
    for i in range(0, len(pares), 2):
        for j, (rot, val) in enumerate(pares[i:i + 2]):
            x = 50 if j == 0 else x2
            f.texto(x, rot, 18, cor="#8a1c1c", avancar=False)
            f.texto(x, val, 24, True, avancar=False, y=f.y + 24)
        f.y += 70
    f.linha()
    f.texto(50, "QUADRO DE COBERTURAS", 24, True, "#8a1c1c")
    f.texto(50, "Cobertura", 20, True, avancar=False)
    f.texto(560, "LMI", 20, True, avancar=False)
    f.texto(850, "Prêmio", 20, True)
    for c, premio in zip(g["coberturas"], ex["premios"]):
        f.texto(50, c["nome"], 22, avancar=False)
        f.texto(560, _br(c["valor"]), 22, avancar=False)
        f.texto(850, _br(premio), 22)
    f.y += 10
    f.texto(50, f"Franquia Básica (Casco): {_br(g['franquia'])}", 24, True)
    f.texto(50, f"Franquia Vidros: {_br(ex['franquia_vidros'])}  (Para-brisa)", 22)
    f.linha()
    f.texto(50, f"Prêmio Líquido: {_br(ex['premio_liquido'])}", 22)
    f.texto(50, f"IOF (7,38%): {_br(ex['iof'])}", 22)
    f.texto(50, f"Prêmio Total: {_br(g['valor_total'])}", 28, True)
    f.texto(50, "Forma de pagamento: 4 parcelas no cartão", 20, cor="#555555")
    return f.img


def apolice_residencial(g: dict, ex: dict) -> Image.Image:
    f = Folha(1100, 1150)
    f.texto(40, "SEGURADORA EXEMPLO S.A. — SEGURO RESIDENCIAL", 30, True, "#1d5c3a")
    f.texto(40, "Apólice (documento fictício para teste)", 20, cor="#555555")
    f.faixa("IDENTIFICAÇÃO", "#1d5c3a")
    f.texto(45, f"Apólice: {g['numero_apolice']}", 24, True)
    f.texto(45, f"Segurado: {g['nome']}", 24)
    f.texto(45, f"CPF: {g['cpf']}", 24)
    f.texto(45, f"Vigência: {_dmy(g['vigencia_inicio'])} a {_dmy(g['vigencia_fim'])}", 24)
    f.texto(45, "Local de risco: Av. Exemplo, 900, apto 31 — Cidade Modelo/UF", 22)
    f.texto(45, "Tipo de imóvel: Apartamento — Habitual", 22)
    f.faixa("COBERTURAS E LIMITES MÁXIMOS DE INDENIZAÇÃO", "#1d5c3a")
    for c in g["coberturas"]:
        f.texto(45, c["nome"], 22, avancar=False)
        f.texto(760, _br(c["valor"]), 22, True)
    f.faixa("PRÊMIO", "#1d5c3a")
    f.texto(45, f"Prêmio líquido: {_br(ex['premio_liquido'])}    IOF: {_br(ex['iof'])}", 22)
    f.texto(45, f"Prêmio total anual: {_br(g['valor_total'])}", 26, True)
    f.texto(45, "Serviços: chaveiro, eletricista e encanador (3 acionamentos/ano)", 20, cor="#555555")
    return f.img


def cnh(g: dict, ex: dict) -> Image.Image:
    f = Folha(1000, 640, "#e8efe3")
    f.d.rectangle([12, 12, 988, 628], outline="#3d6b35", width=5)
    f.texto(40, "REPÚBLICA FEDERATIVA DO BRASIL — MODELO FICTÍCIO", 20, True, "#3d6b35")
    f.texto(40, "CARTEIRA NACIONAL DE HABILITAÇÃO (DOCUMENTO DE TESTE)", 22, True, "#3d6b35")
    f.d.rectangle([40, 120, 250, 380], fill="#c9d3c4", outline="#3d6b35", width=2)
    f.texto(95, "FOTO", 28, True, "#6d7d68", avancar=False, y=230)
    x = 290
    linhas = [("NOME", g["nome"].upper()), ("DOC. IDENTIDADE / ÓRG. EMISSOR / UF", f"{ex['rg']} SSP UF"),
              ("CPF", g["cpf"]), ("DATA NASCIMENTO", "02/07/1990"),
              ("Nº REGISTRO", ex["registro"]), ("VALIDADE", _dmy(g["validade"])),
              ("1ª HABILITAÇÃO", "11/09/2009"), ("CAT. HAB.", "AB")]
    yy = 120
    for rot, val in linhas:
        f.texto(x, rot, 15, cor="#3d6b35", avancar=False, y=yy)
        f.texto(x, val, 23, True, avancar=False, y=yy + 18)
        yy += 58 if rot not in ("Nº REGISTRO", "VALIDADE") else 0
        if rot == "Nº REGISTRO":
            x_reg = x
            x = 640
        elif rot == "VALIDADE":
            x = x_reg
            yy += 58
    return f.img


def crlv(g: dict, ex: dict) -> Image.Image:
    f = Folha(1100, 900, "#f3f0e6")
    f.texto(40, "CERTIFICADO DE REGISTRO E LICENCIAMENTO DE VEÍCULO — CRLV (MODELO FICTÍCIO)", 22, True, "#5a4a1f")
    f.texto(40, "Documento sintético para teste — sem validade", 18, cor="#777777")
    f.linha()
    campos = [("CÓDIGO RENAVAM", ex["renavam"]), ("PLACA", g["placa"]), ("EXERCÍCIO", "2026"),
              ("ANO FABRICAÇÃO", "2021"), ("ANO MODELO", "2022"), ("CATEGORIA", "PARTICULAR"),
              ("MARCA / MODELO / VERSÃO", "EXEMPLO/SUV 1.5 TURBO"), ("COR PREDOMINANTE", "PRATA"),
              ("CHASSI", ex["chassi"]), ("COMBUSTÍVEL", "ALCOOL/GASOLINA"),
              ("NOME", g["nome"].upper()), ("CPF / CNPJ", g["cpf"]),
              ("LOCAL", "CIDADE EXEMPLO UF"), ("DATA", "14/01/2026")]
    for i, (rot, val) in enumerate(campos):
        x = 45 if i % 2 == 0 else 600
        if rot in ("MARCA / MODELO / VERSÃO", "NOME"):
            x = 45
        f.texto(x, rot, 15, cor="#5a4a1f", avancar=False)
        f.texto(x, val, 24, True, avancar=False, y=f.y + 19)
        if x == 600 or rot in ("MARCA / MODELO / VERSÃO", "NOME") or i == len(campos) - 1:
            f.y += 66
    return f.img


def orcamento(g: dict, ex: dict) -> Image.Image:
    f = Folha(1000, 980)
    f.texto(40, "AUTO CENTER EXEMPLO — FUNILARIA E PINTURA", 28, True)
    f.texto(40, "Orçamento nº 4471 — emitido em 22/09/2026 (fictício)", 20, cor="#555555")
    f.linha()
    f.texto(40, f"Cliente: {g['nome']}", 24)
    f.texto(40, f"Veículo: EXEMPLO HATCH 1.6      Placa: {g['placa']}", 24)
    f.texto(40, "Telefone: (00) 0000-0000", 20, cor="#555555")
    f.linha()
    f.texto(40, "Descrição", 22, True, avancar=False)
    f.texto(720, "Valor", 22, True)
    for desc, val in ex["itens"]:
        f.texto(40, desc, 22, avancar=False)
        f.texto(720, _br(val), 22)
    f.linha()
    f.texto(40, "Subtotal", 22, avancar=False)
    f.texto(720, _br(ex["subtotal"]), 22)
    f.texto(40, "Desconto à vista", 22, avancar=False)
    f.texto(720, "- " + _br(ex["desconto"]), 22)
    f.texto(40, "TOTAL", 28, True, avancar=False)
    f.texto(720, _br(g["valor_total"]), 28, True)
    f.texto(40, "Validade do orçamento: 15 dias. Prazo de execução: 5 dias úteis.", 18, cor="#555555")
    return f.img


def boleto(g: dict, ex: dict) -> Image.Image:
    f = Folha(1200, 700)
    f.texto(40, "BANCO EXEMPLO  | 000-0 |  " + ex["linha_digitavel"], 24, True, mono=True)
    f.linha()
    cel = [("Beneficiário", "SEGURADORA EXEMPLO S.A."), ("Vencimento", _dmy(g["vencimento"])),
           ("Data do documento", "25/09/2026"), ("Valor do documento", _br(g["valor_total"])),
           ("Nosso número", ex["nosso_numero"]), ("Parcela", "2/10")]
    for i in range(0, len(cel), 2):
        for j, (rot, val) in enumerate(cel[i:i + 2]):
            x = 40 if j == 0 else 700
            f.texto(x, rot, 16, cor="#555555", avancar=False)
            f.texto(x, val, 24, True, avancar=False, y=f.y + 20)
        f.y += 68
    f.texto(40, f"Instruções: referente à apólice {g['numero_apolice']} — seguro auto. "
                "Não receber após 30 dias do vencimento.", 18)
    f.linha()
    f.texto(40, "Pagador", 16, cor="#555555")
    f.texto(40, f"{g['nome'].upper()} — CPF {g['cpf']}", 24, True)
    f.texto(40, "Rua das Palmeiras, 45 — Cidade Exemplo/UF", 20)
    rnd = random.Random("barras")
    x = 40
    while x < 1100:
        w = rnd.choice((2, 3, 4, 6))
        f.d.rectangle([x, 600, x + w, 680], fill="black")
        x += w + rnd.choice((2, 3, 5))
    return f.img


def foto_parabrisa(g: dict, ex: dict) -> Image.Image:
    img = Image.new("RGB", (1000, 750), "#7d8a99")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 520, 1000, 750], fill="#4a4a4a")                       # chão
    d.rounded_rectangle([120, 220, 880, 600], 60, fill="#b03030")          # carroceria
    d.polygon([(220, 230), (780, 230), (700, 90), (300, 90)], fill="#9fc6d9")   # para-brisa
    rnd = random.Random("trinca")
    cx, cy = 430, 170
    for _ in range(9):                                                      # a trinca
        x, y = cx, cy
        for _ in range(6):
            nx, ny = x + rnd.randint(-45, 45), y + rnd.randint(-25, 25)
            d.line([x, y, nx, ny], fill="white", width=2)
            x, y = nx, ny
    d.ellipse([160, 300, 280, 380], fill="#f3e9b0")                         # faróis
    d.ellipse([720, 300, 840, 380], fill="#f3e9b0")
    d.rectangle([370, 430, 630, 500], fill="white", outline="black", width=3)    # placa Mercosul
    d.rectangle([370, 430, 630, 448], fill="#1d4f9c")
    d.text((470, 431), "BRASIL", fill="white", font=_fonte(14, True))
    d.text((392, 449), g["placa"], fill="black", font=_fonte(40, True))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def _degradar(img: Image.Image, escala: float, angulo: float, fundo: str, ruido: int, semente: str,
              jpeg: int) -> Image.Image:
    w, h = img.size
    img = img.resize((int(w * escala), int(h * escala)), Image.BILINEAR)
    img = img.rotate(angulo, expand=True, fillcolor=fundo, resample=Image.BICUBIC)
    rnd = random.Random(semente)
    px = img.load()
    for _ in range(int(img.width * img.height * 0.02)):
        x, y = rnd.randrange(img.width), rnd.randrange(img.height)
        r, g_, b = px[x, y]
        dv = rnd.randint(-ruido, ruido)
        px[x, y] = (max(0, min(255, r + dv)), max(0, min(255, g_ + dv)), max(0, min(255, b + dv)))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=jpeg)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def _extras(chave: str, g: dict) -> dict:
    ex = {"proposta": _digitos(chave + "p", 9), "chassi": "9BW" + _digitos(chave + "c", 6) + "EXMPL" + _digitos(chave + "k", 3),
          "rg": _digitos(chave + "r", 7), "registro": _digitos(chave + "g", 10), "renavam": _digitos(chave + "v", 11),
          "nosso_numero": _digitos(chave + "n", 12),
          "linha_digitavel": " ".join(_digitos(chave + "l" + str(i), n) for i, n in enumerate((10, 11, 11, 1, 14)))}
    if g.get("coberturas") and g["tipo_documento"] == "apolice_auto":
        ex["premio_liquido"] = round(g["valor_total"] / 1.0738, 2)
        ex["iof"] = round(g["valor_total"] - ex["premio_liquido"], 2)
        ex["premios"] = [1840.22, 512.40, 557.78]
        ex["franquia_vidros"] = 450.00
    if g["tipo_documento"] == "apolice_residencial":
        ex["premio_liquido"] = round(g["valor_total"] / 1.0738, 2)
        ex["iof"] = round(g["valor_total"] - ex["premio_liquido"], 2)
    if g["tipo_documento"] == "orcamento":
        ex["itens"] = [("Para-choque dianteiro (peça)", 1450.00), ("Pintura do para-choque", 980.00),
                       ("Mão de obra (funilaria)", 640.00)]
        ex["subtotal"] = 3070.00
        ex["desconto"] = 150.00
    return ex


DESENHOS = {"apolice-auto-a": apolice_auto_a, "apolice-auto-b": apolice_auto_b,
            "apolice-residencial": apolice_residencial, "cnh": cnh, "crlv": crlv, "orcamento": orcamento,
            "boleto": boleto, "foto-parabrisa": foto_parabrisa, "apolice-auto-degradada": apolice_auto_a,
            "cnh-fotografada": cnh}


def main() -> int:
    pasta = os.path.join(AQUI, "imagens")
    os.makedirs(pasta, exist_ok=True)
    linhas = []
    for nome, tipo, critico, gab in DOCS:
        real = materializar(gab)                      # os MESMOS valores que o carregador produzirá
        img = DESENHOS[nome](real, _extras(nome, real))
        if nome == "apolice-auto-degradada":
            img = _degradar(img, 0.62, 3.5, "#d9d6cf", 40, nome, 38)
        elif nome == "cnh-fotografada":
            img = _degradar(img, 0.80, -7.0, "#5b4b3a", 30, nome, 45)
            img = img.filter(ImageFilter.GaussianBlur(0.7))
        caminho = os.path.join(pasta, f"{nome}.png")
        img.convert("P", palette=Image.ADAPTIVE, colors=128).save(caminho, optimize=True)
        linhas.append({
            "chave": f"vcampos-{nome}", "versao": VERSAO, "papel": "visao_campos", "nivel": "N1",
            "critico": critico, "tenant": "A" if len(linhas) % 2 == 0 else "B",
            # `dados_da_imagem` = o que está DESENHADO (os campos do gabarito): é a "entrada" do caso —
            # o juiz `sem_pii` não acusa o CPF que o modelo leu da própria imagem.
            "entrada": {"imagem": f"visao_campos/imagens/{nome}.png", "tipo": tipo, "dados_da_imagem": gab},
            "ferramentas_disponiveis": [], "efeitos_permitidos": [], "efeitos_proibidos": [],
            "oraculo": {"campos": gab, "resposta_modelo_ouro": gab},
            "falhas_injetadas": [], "orcamento_turnos": None, "origem": ORIGEM})
    with open(os.path.join(AQUI, "casos.jsonl"), "w", encoding="utf-8") as fh:
        for linha in linhas:
            fh.write(json.dumps(linha, ensure_ascii=False) + "\n")
    for nome, *_ in DOCS:
        p = os.path.join(pasta, f"{nome}.png")
        print(f"{nome:<26} {os.path.getsize(p):>7} bytes")
    print(f"{len(linhas)} casos -> casos.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
