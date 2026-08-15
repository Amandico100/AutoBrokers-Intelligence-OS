# -*- coding: utf-8 -*-
"""Backfill de `temas` no acervo inteiro.

⚠️ AGRUPA POR CONJUNTO DE TEMAS antes de escrever.

A primeira versao fazia um UPDATE por carta: 17.438 idas ao banco. Morreu em
`RemoteProtocolError <ConnectionTerminated last_stream_id:19999>` -- o limite de
streams de UMA conexao HTTP/2. E o mesmo defeito que ja tinha derrubado o
espelho, por outro caminho.

Cartas que recebem o MESMO conjunto de temas cabem num unico UPDATE com
`.in_('id', [...])`. Milhares de cartas viram algumas centenas de requisicoes --
e o retry cobre o resto.
"""
import os, re, sys, collections, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from supabase import create_client
import httpx

db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

T = {
 'carro_reserva': r'carro\s+reserva|ve[ií]culo\s+reserva|locadora|loca[çc][ãa]o de ve[ií]culo|movida|localiza|unidas|di[áa]rias de carro',
 'funilaria': r'funilaria|lataria|martelinho|repar[oa] r[áa]pid[oa]|amassad|riscad|pintura|polimento|est[ée]tica',
 'franquia': r'franquia',
 'perda_total': r'perda total|indeniza[çc][ãa]o integral|integral do ve[ií]culo|salvado|sucata|baixa de chassi|100% da (?:fipe|tabela)',
 'vistoria': r'vistoria|vistoriad|inspe[çc][ãa]o pr[ée]via|autovistoria',
 'pecas': r'pe[çc]a[s]?\b|autope[çc]a|reposi[çc][ãa]o de pe|fornecimento de pe',
 'reparo_oficina': r'oficina|concession[áa]ria|refer',
 'vidros': r'vidro|parabrisa|para-brisa|p[áa]ra-brisa|retrovisor|farol|lanterna',
 'guincho': r'guincho|reboque|assist[êe]ncia 24|24h|remo[çc][ãa]o do ve[ií]culo',
 'terceiro': r'terceiro|reclama[çc][ãa]o de terceiro|dano moral|colis[ãa]o com outro',
 'boletim_ocorrencia': r'boletim de ocorr|\bB\.?O\.?\b|registro de ocorr',
 'roubo_furto': r'roubo|furto|subtra[çc]',
 'documentacao': r'documenta[çc][ãa]o|documento|CRLV|CNH|habilita[çc][ãa]o|procura[çc][ãa]o|DUT|ATPV',
 'prazo': r'prazo|\bdias [úu]teis|at[ée] \d+ dias',
 'indenizacao': r'pagamento da indeniza|dep[óo]sito|dados banc[áa]ri|conta para cr[ée]dito|PIX da indeniza',
 'endosso': r'ap[óo]lice|endosso|altera[çc][ãa]o cadastral|inclus[ãa]o de condutor|troca de ve[ií]culo',
 'cobranca_boleto': r'boleto|parcela|inadimpl|cancelamento por falta de pagamento|d[ée]bito autom|carn[êe]|fatura',
 'renovacao': r'renova[çc][ãa]o|renovar|vencimento da ap[óo]lice|cota[çc][ãa]o de renova',
 'residencia': r'residencial|encanador|eletricista|chaveiro residencial|im[óo]vel',
 'pneu': r'pneu|estepe|troca de pneu',
 'bateria': r'bateria|carga na bateria|pane el[ée]trica',
 'chaveiro': r'chaveiro|chave (?:reserva|trancada)|perda de chave',
 'sinistro_abertura': r'abrir sinistro|abertura de sinistro|acionar o seguro|comunicar o sinistro|aviso de sinistro',
 'regulacao': r'regula[çc][ãa]o|regulador|analista de sinistro|an[áa]lise do sinistro|sindic[âa]ncia',
 'reembolso': r'reembols|ressarci',
}
R = {k: re.compile(v, re.I) for k, v in T.items()}


def com_retry(fn, tentativas=4):
    """Uma queda de conexao nao pode matar a rodada inteira. Ver espelho_chat."""
    for i in range(tentativas):
        try:
            return fn()
        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError):
            if i == tentativas - 1:
                raise
            time.sleep(1.5 * (i + 1))


# ---- 1. LER ----------------------------------------------------------------
grupos = collections.defaultdict(list)     # (tema,tema,...) -> [id, ...]
ini = lidas = sem_tema = ja_ok = 0
while True:
    lote = com_retry(lambda: (db.table('knowledge_cards')
                              .select('id, card_text, temas')
                              .order('id').range(ini, ini + 999).execute().data)) or []
    if not lote:
        break
    for c in lote:
        lidas += 1
        achados = tuple(sorted(k for k, r in R.items() if r.search(c.get('card_text') or '')))
        if not achados:
            sem_tema += 1
            continue
        if tuple(c.get('temas') or []) == achados:
            ja_ok += 1
            continue
        grupos[achados].append(c['id'])
    ini += 1000
    if len(lote) < 1000:
        break
    if lidas % 5000 == 0:
        print(f'  ... {lidas} lidas', file=sys.stderr)

print(f'lidas={lidas} sem_tema={sem_tema} ja_ok={ja_ok} grupos={len(grupos)}', file=sys.stderr)

# ---- 2. ESCREVER, um UPDATE por conjunto (fatiado por seguranca) ------------
tocadas = rotulos = 0
hist = collections.Counter()
for temas, ids in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
    lst = list(temas)
    for i in range(0, len(ids), 200):
        pedaco = ids[i:i + 200]
        com_retry(lambda: db.table('knowledge_cards')
                  .update({'temas': lst}).in_('id', pedaco).execute())
        tocadas += len(pedaco)
        rotulos += len(pedaco) * len(lst)
    for t in lst:
        hist[t] += len(ids)

print(f'CARTAS LIDAS ....... {lidas}')
print(f'CARTAS ROTULADAS ... {tocadas}')
print(f'JA ESTAVAM OK ...... {ja_ok}')
print(f'SEM NENHUM TEMA .... {sem_tema}')
print(f'ROTULOS ESCRITOS ... {rotulos}')
print('TEMAS:')
for k, v in hist.most_common(30):
    print(f'  {k:22s} {v}')
