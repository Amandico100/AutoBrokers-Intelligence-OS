#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Junta base.html + os fragmentos aba-<id>.html num painel.html publicavel.

Uso:  python montar.py      (roda de qualquer lugar; escreve painel.html aqui do lado)

A ORDEM das abas e a ordem do menu em base.html tem de ser a mesma.
Nada de dependencia externa: so a biblioteca padrao.
"""
import io
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ABAS = ["inicio", "tarefas", "specs", "piloto", "vidros",
        "corredores", "conhecimento", "pendencias", "historico"]
MARCA = "<!--ABAS-->"


def ler(nome):
    caminho = os.path.join(AQUI, nome)
    if not os.path.exists(caminho):
        sys.exit("FALTA o arquivo %s" % nome)
    return io.open(caminho, encoding="utf-8").read()


def main():
    base = ler("base.html")
    if MARCA not in base:
        sys.exit("base.html nao tem a marca %s" % MARCA)
    partes = []
    for aba in ABAS:
        html = ler("aba-%s.html" % aba).strip()
        esperado = 'id="tab-%s"' % aba
        if esperado not in html:
            sys.exit("aba-%s.html nao abre com %s" % (aba, esperado))
        if html.count("<div") != html.count("</div>"):
            sys.exit("aba-%s.html tem <div> e </div> em numero diferente" % aba)
        partes.append(html)
        # o menu de base.html precisa ter um botao para cada aba
        if 'data-tab="%s"' % aba not in base:
            sys.exit("base.html nao tem botao para a aba %s" % aba)
    saida = base.replace(MARCA, "\n\n".join(partes))
    destino = os.path.join(AQUI, "painel.html")
    io.open(destino, "w", encoding="utf-8", newline="\n").write(saida)
    print("painel.html escrito: %d abas, %d KB" % (len(ABAS), len(saida.encode("utf-8")) // 1024))


if __name__ == "__main__":
    main()
