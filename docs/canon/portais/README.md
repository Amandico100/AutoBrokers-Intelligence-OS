# Portais das seguradoras — o que já sabemos de cada um

> **Índice do conhecimento de portal.** Um arquivo por seguradora. Cada um
> guarda tudo que já foi descoberto lá dentro — a porta, as armadilhas, as
> travas, e o que cada serviço precisa.

---

## Leia primeiro: o método está em outro lugar

Este diretório **não** ensina a automatizar um portal. Ele guarda o que já se
sabe de cada um. O método mora em duas SPECs, e as duas valem juntas:

| Documento | O que responde |
|---|---|
| [**SPEC-033**](../specs/SPEC-033-portal-api-automation-playbook.md) | **COMO** falar com um portal — chamar por dentro em vez de clicar, capturar por F12, encadear pela resposta, parar antes de finalizar. Escrita pelo Fable a partir da Allianz, e **vale inteira** |
| [**SPEC-070**](../specs/SPEC-070-cobranca-multi-seguradora.md) | **EM QUE ORDEM**, com **que prova** e **quantas vezes** se pode bater na porta. As 5 fases com portão. Nasceu porque duas seguradoras nos bloquearam quando se explorou sem plano |

```
SPEC-033 + SPEC-070 ....... a receita. Igual para toda seguradora.
PORTAL-<nome>.md .......... o mapa do território daquele portal. Cresce sempre.
```

**Antes de abrir um portal novo:** leia a SPEC-070 §2 (as 5 fases) e a SPEC-033
inteira. Depois abra o `PORTAL-<nome>.md` — se já existir.

---

## Estado de cada portal

| Seguradora | Arquivo | Cobrança | Renovação | Cotação |
|---|---|:--:|:--:|:--:|
| **HDI** | [PORTAL-hdi.md](PORTAL-hdi.md) | ✅ pronta | 📋 menus mapeados | 📋 menus mapeados |
| **Allianz** | *(a escrever — o conhecimento está na SPEC-023A)* | ✅ pronta | ⬜ | ⬜ |
| **Tokio Marine** | [PORTAL-tokio.md](PORTAL-tokio.md) | ✅ pronta | 📋 URLs mapeadas | 📋 cotadores mapeados |
| **Yelum** | [PORTAL-yelum.md](PORTAL-yelum.md) | ✅ pronta | 📋 URLs mapeadas | 📋 4 marcas mapeadas |
| Porto · Azul · Bradesco · SulAmérica · MAPFRE · demais | — | ⬜ | ⬜ | ⬜ |

```
✅ funciona   🔨 em construção   📋 conhecimento anotado, sem código   ⬜ nada ainda
```

---

## Por que um arquivo por seguradora

Cada portal vai acumular **cobrança + renovação + cotação + relatórios**. Só a
cobrança da HDI rendeu 4 armadilhas, 3 descobertas de estrutura e 2 limites do
portal. Multiplique por 4 serviços e por 15 seguradoras e um arquivo único vira
algo que ninguém abre.

E quem for fazer *renovação da Tokio* daqui a três meses quer abrir
`PORTAL-tokio.md` e ler — não rolar 400 páginas passando por HDI e Allianz.

## A estrutura, igual em todos

```
1. A PORTA          login, captcha, WAF, sessão (quanto dura), 2FA
2. A TOPOLOGIA      shell × app legado, iframes, encoding, pontes
3. AS ARMADILHAS    ← o ouro. Cada uma com sintoma, causa e como se sabe
4. AS TRAVAS        botões proibidos, limites de janela, teto de frequência
5. OS SERVIÇOS      5.1 cobrança · 5.2 renovação · 5.3 cotação · 5.4 outros
6. DADOS DA TELA    todo campo que a tela mostra, mesmo os que ninguém usa hoje
7. HISTÓRICO        o que já quebrou, e como foi consertado
```

**As seções 1 a 4 e 6 servem os TRÊS serviços.** Quando chegar a vez da
renovação, o login, a topologia, as armadilhas e os limites **já estão
escritos** — só a 5.2 é trabalho novo. É esse o ganho.

**E a seção 6 é a que parece desperdício e não é:** anota-se todo campo que a
tela mostra, inclusive os que a cobrança ignora. Foi lá que a HDI já deixou
guardado o menu de Renovação inteiro, sem custo nenhum.

---

## A regra que não se negocia

> **O portal da corretora não é ambiente de teste.**

📊 Dois portais independentes (HDI e Tokio) recusaram acesso depois de ~15 e ~4
visitas em menos de 30 minutos. Eles reagem à **frequência**, não ao método.

**E a página pública não é o app.** 📊 Em 12/08/2026 eu sondei a tela de login
da Yelum e concluí "nenhuma trava" — mas tinha carregado a página de marketing.
O app logado roda **Akamai Bot Manager**. Antes de afirmar sobre um portal,
perguntar: *a página que eu medi é a mesma sobre a qual eu vou afirmar?*

Teto por fase, em SPEC-070 §2. Toda leitura repetida sai de **fixture salva**
(`backend/tests/fixtures/`), com a estrutura real e os dados trocados.

---

*Autoridade: CLAUDE.md · SPEC-020 · SPEC-023/023A/023B · SPEC-033 · SPEC-070.*
