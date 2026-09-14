# Corpus de telas reais de PORTAL — ÍNDICE

> Transcrito em **13/09/2026** (SPEC-EXTRA-001.6, BLOCO 0) a partir dos prints de
> desfecho guardados no bucket privado `portal-evidence` pelo `portal_worker`
> (`_prova_do_desfecho`). 📊 `select split_part(name,'/',2), count(*) from
> storage.objects where bucket_id='portal-evidence' and name like '%desfecho%'
> group by 1` → 6 `done` · 4 `needs-human` · 2 `failed` (12 prints, 10 e 11/09).
>
> 📊 Os 12 prints são **6 telas distintas**: os pares de 10/09 e 11/09 da Allianz,
> da Mapfre e da Zurich são byte-idênticos (`md5sum`); os `done` de HDI, Tokio e
> Yelum diferem só em conteúdo dinâmico (avisos, datas). Um arquivo por tela.
>
> 🔴 **Por que texto e não só a foto:** em todos os 6 jobs não-`done` de 10–11/09,
> `evidence.body_text` e `evidence.debug_dom` são NULL. A imagem era a única
> fonte da frase da tela — e ninguém a abria (diagnóstico §9.2, "prova que
> ninguém abre"). O guarda G3 roda o MOTOR (`interpret_login`) sobre este texto,
> nunca regex sobre a constante (CLAUDE.md §9.4).

## Redação aplicada (o corpus vai para o repositório)

| marcador | o que substitui |
|---|---|
| `<usuario>` | o login do corretor no portal (Allianz) |
| `<cpf>` | o CPF do corretor, que o print da Mapfre mostra **em claro** (é o P2 do diagnóstico §9.2; B4.3 mascara no DOM antes da foto) |
| `<nome>` · `<iniciais>` · `<codigo>` | nome da atendente logada e código de corretor nos dashboards |

O nome da corretora ("RESULTA CORRETORA DE SEGUROS LTDA") fica: é razão social,
já nomeada em todo o canon, e o Zurich a usa como âncora de identidade
(`zurich_corretora_na_tela`).

## Os arquivos

| arquivo | job de origem (11/09) | status gravado | o que a tela DIZ | uso no guarda G3 |
|---|---|---|---|---|
| `allianz_corretor-needs_human-20260911.txt` | `e3457c53…` (idêntico a `38c6e7cf…` de 10/09) | `needs_human` · "tela pos-login Allianz nao reconhecida" | **"Acesso negado — Por favor, valide os dados introduzidos."** = credencial recusada | alvo: tem de virar `failed` |
| `mapfre_corretor-failed-20260911.txt` | `823c6692…` (idêntico a `ba70afdc…` de 10/09) | `failed` · "a MAPFRE recusou a credencial (autenticacao invalida)" | **"Autenticação inválida!"** | controle positivo: já é `failed` |
| `zurich_corretor-needs_human-20260911.txt` | `9e942aa0…` (idêntico a `fc64f74f…` de 10/09) | `needs_human` · "200 com ZERO parcelas, duas vezes" | dashboard **logado** ("Parcelas vencidas", "Minha Conta") | 🔴 CONTROLE: NÃO é credencial recusada; login = `done` |
| `hdi_corretor-done-20260911.txt` | `9e8a2579…` | `done` | dashboard logado ("Olá, <nome>", "Sair", "Quadro De Avisos") | controle: continua `done` |
| `tokiomarine_corretor-done-20260911.txt` | `5a2c9c84…` | `done` | dashboard logado ("PARCELAS INADIMPLENTES", "Bem-vindo(a)") | controle |
| `yelum_corretor-done-20260911.txt` | `9ce67f68…` | `done` | dashboard logado ("Minhas pendências", "Sair") | controle |

⚠️ **Não existe print real de dashboard da Allianz no acervo**: o último `done`
dela é de 17/08 e a captura de prova de desfecho nasceu depois. O controle
"dashboard da Allianz continua `done`" usa o texto sintético que já estava em
`tests/test_spec023_allianz_login.py` — e está marcado como sintético.
