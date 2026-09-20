# SPEC-EXTRA-001.5.2 · O documento vira base sem virar erro

> **Proposta** · 20/09/2026 · escrita depois da EXTRA-001.5.1 (main `333d506`)
> **Nível sugerido:** PADRÃO · **💭 3–4 h** sob o rito proposto · **depende de:** nada (a 001.5.1 já está no ar)
> **Por que existe:** 📊 das 81 linhas que o extrator propôs, **25 estavam certas**. 40 pedem correção e 16 foram
> recusadas. Publicar a fila do jeito que ela está é publicar erro com carimbo de gente.

---

## 1. O problema, medido

📊 19/09/2026 — um leitor read-only abriu os **27 documentos** no MinIO, extraiu **3.052 páginas** e conferiu
**135** contra a linha proposta (`docs/canon/reports/SPEC-EXTRA-001.5-LINHAS-CONFERIDAS.{md,json}`):

```
25  PUBLICAR      a linha diz o que a página diz
40  CORRIGIR      a linha existe, mas o campo está errado
16  RECUSAR       a linha não deveria existir
 0  NAO_CONSEGUI
```

**E os erros não são aleatórios: são cinco padrões, e cada um tem a mesma causa.**

| # | o padrão | exemplo medido | a causa |
|---|---|---|---|
| 1 | **risco excluído dentro de OUTRA cobertura vira cobertura do plano** | *"riscos excluídos: inundação por transbordamento"*, dentro de Vendaval/Granizo, virou `alagamento = nao` do plano inteiro | o extrator casa a palavra, não o escopo da cláusula |
| 2 | **os planos reais do documento são apagados num "Plano único"** | 📊 o manual **Bradesco Auto tem 9 planos** (118, 108, 113, 112, 106, 21, 41, 15, 16) e virou um só. HDI Auto tem a Cláusula 2 com Essencial/Especial 1/Especial 2/VIP. Tokio tem Básico/Completo/VIP no item 9.5.9 | **o extrator atribui o serviço antes de ler a cláusula de planos** |
| 3 | **número de tabela lido sem a coluna** | *"R$ 300,00"* colhido sem saber se é por evento, por vigência, ou de qual plano | a tabela é lida como texto corrido |
| 4 | **o nome do arquivo vira o nome do produto** | `Seguro Residencial Conteudo_V1.2` gravado como produto; um nome terminando em travessão solto | o produto não é lido da CAPA |
| 5 | **a versão declarada não é a do documento** | Mapfre Auto declarada v34.0 sendo v41; Mapfre Residencial v2.9 sendo 3.2 | a versão vem do cadastro, não da capa |

🔴 **A causa raiz é uma só:** o extrator trata a condição geral como **um texto** e procura serviços nele. Uma
condição geral é **uma tabela de planos com serviços dentro**, e o serviço só tem sentido dentro de uma coluna.

---

## 2. O resultado desejado

```
Um documento de condições gerais entra.
Sai uma proposta de base que um humano publica SEM ter de abrir o PDF —
porque cada linha já nasce com o veredito de quem conferiu contra a página.
```

E, como consequência: **as 40 linhas corrigidas, as 16 recusadas refeitas do jeito certo, e as 4 seguradoras que
faltam entrando pelo mesmo cano** — sem repetir os cinco padrões.

---

## 3. As unidades

### A · A cláusula de planos é a ÂNCORA, e vem primeiro
O extrator passa a ter **duas passadas**. A primeira só procura a **cláusula que enumera os planos** (o texto que
diz "Plano Básico / Plano Completo / Plano VIP", a tabela de níveis, a Cláusula 2 da HDI, o item 9.5.9 da Tokio, a
lista de códigos do Bradesco). A segunda atribui cada serviço a **uma coluna** dessa tabela.
🔴 **Sem a âncora, o extrator NÃO propõe.** Ele registra o documento como "cláusula de planos não localizada" e
entra numa fila própria — porque *"Plano único"* é a mentira que produziu 📊 25 dos 38 planos da onda 1.
**GATE A:** nos 27 documentos do acervo, quantos têm cláusula de planos localizada? Para os que têm, o número de
planos bate com a contagem feita à mão em 5 documentos de controle (Bradesco Auto = 9, HDI Auto = 6, Tokio
Residencial = 3, Yelum Residencial = 4, Azul Auto = ?). **Mutação:** âncora desligada → o extrator tem de recusar,
não inventar.

### B · O escopo da cláusula manda no veredito
Todo serviço proposto carrega **o caminho da cláusula de onde saiu** (ex.: `9.5.9.2 › Plano Vip › Carro Reserva`).
Se a frase que decidiu `coberto` está **dentro de uma cláusula de outro serviço ou de exclusões**, a linha nasce
`condicionado` com a ressalva, ou não nasce.
**GATE B:** as 6 linhas do padrão 1 (alagamento/granizo da amostra) reentram e **nenhuma** volta como `nao` do
plano. **Controle:** uma exclusão que é MESMO do plano continua virando `nao`.

### C · Número de tabela vem com a coluna, ou não vem
Limite só é gravado com **unidade e escopo lidos do cabeçalho da coluna/linha** (por evento · por vigência ·
utilizações). Sem cabeçalho legível, o campo fica **vazio** e a linha diz por quê.
**GATE C:** as 4 linhas de limite marcadas CORRIGIR (HDI eletricista R$ 300/evento + R$ 600/vigência; HDI
hospedagem; Tokio guincho 200 km; Tokio condomínio) saem certas. **Controle:** tabela sem cabeçalho → campo vazio,
não um número solto.

### D · O produto e a versão vêm da CAPA
Nome do produto e versão lidos da primeira página do documento (ou do rodapé de versão), nunca do nome do arquivo,
nunca do cadastro. Divergência entre a versão da capa e a do cadastro vira **alerta**, não silêncio.
**GATE D:** os 2 casos medidos (Mapfre Auto v34 × v41, Mapfre Residencial v2.9 × 3.2) acendem o alerta. **Controle:**
documento onde as duas batem não acende.

### E · Cobertura não é assistência
📊 15 linhas usam a chave `vidros`: 7 residencial, 6 auto, 2 condomínio. Quebra de vidros **residencial** é
**cobertura contratada**, não serviço de assistência 24 h — e hoje as duas moram na mesma chave (P-E00151-06).
O vocabulário ganha a distinção, e o extrator a respeita.
**GATE E:** as 7 linhas residenciais saem como cobertura; as 6 de auto continuam assistência.

### F · O conferente entra no cano, e a fila nasce conferida
O que o leitor fez à mão em 19/09 vira **passo do pipeline**: toda linha proposta recebe, antes de chegar à fila,
um veredito automático contra a **página** (o trecho existe? o número existe? o plano existe na âncora?). A fila
mostra o veredito ao lado da linha.
🔴 **Isso é o que faz a curadoria caber num dia** em vez de exigir que o Founder abra 27 PDFs.
**GATE F:** rodado sobre as 81 linhas antigas, o conferente automático tem de concordar com o leitor humano em
**≥ 80 %** dos 135 campos conferidos (📊 é a única linha de base que existe). Divergência é listada, não escondida.

### G · A fila é limpa: as 40 corrigidas, as 16 refeitas
As 40 `CORRIGIR` reentram pela v2 e são comparadas com o valor que o leitor escreveu (`valor_certo` está no JSON).
As 16 `RECUSAR` ficam em `rascunho` com o motivo — e, se a v2 as produzir diferentes, entram como linhas novas.
**GATE G:** no fim, **0 linhas em `proposto` sem veredito do conferente**, e o relatório diz quantas das 40 saíram
iguais ao que o leitor pediu.

---

## 4. O que NÃO entra

- A destilação das 4 seguradoras que faltam (bradesco 18 documentos vigentes · mapfre 23 · tokio 14 · azul 3):
  é trabalho do Founder, pelo `PROTOCOLO-DE-DESTILACAO-DAS-SEGURADORAS.md` (decisão de 19/09). **Mas esta SPEC é o
  pré-requisito dela** — destilar com o extrator v1 é fabricar mais 40 linhas erradas.
- Mexer na Skill de resposta: ela está pronta e guardada (001.5.1).
- Publicar: continua sendo ato humano, e o lote já existe (`scripts/publicar_linhas_da_base.py`).

---

## 5. Onde entra na fila

Depois da **001.7** (piloto medido) e antes de qualquer destilação em volume. Não bloqueia 001.8, 001.9 nem 001.10.
🔴 **Bloqueia sim o valor da 001.5/001.5.1:** hoje o produto responde por 23 linhas; as outras 58 estão paradas
porque não dá para confiar nelas.

---

## 6. O que prova que funcionou

```
📊 as 40 CORRIGIR reentram e ≥ 32 saem iguais ao que o leitor escreveu
📊 as 5 âncoras de controle batem (Bradesco Auto = 9 planos, não 1)
📊 nenhum documento novo gera "Plano único"
📊 o conferente automático concorda com o leitor humano em ≥ 80 % dos 135 campos
📊 a fila fica com 0 linhas sem veredito
```

**E o teste do produto:** o Founder abre a fila, lê o veredito ao lado de cada linha e publica **sem abrir um PDF**.
