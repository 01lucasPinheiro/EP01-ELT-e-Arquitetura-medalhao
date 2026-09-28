# Ciência de Dados — EP01: Relatório de Análises

Este relatório documenta os resultados e as interpretações das oito análises analíticas produzidas a partir do pipeline de dados, cobrindo o cadastro das entidades e a simulação de 50.000 combates (100.000 participações) nas camadas **Silver** e **Gold**.

---

## Análises sobre o Cadastro (Camada Silver)

As análises 1 e 2 são obtidas exclusivamente a partir da dimensão `silver.dim_pokemon`. Realizá-las sobre a tabela fato incorreria em distorção estatística e dupla contagem, uma vez que cada Pokémon participa de cerca de 125 combates, o que ponderaria as médias pelo volume de batalhas disputadas em vez de refletir a distribuição real do cadastro.

---

### Análise 1: Quantidade de Pokémon por Tipo Primário e por Geração

**Consulta SQL:**
```sql
SELECT tipo_primario AS tipo,
       COUNT(*) FILTER (WHERE geracao_numero = 1) AS "Ger. I",
       COUNT(*) FILTER (WHERE geracao_numero = 2) AS "Ger. II",
       COUNT(*) FILTER (WHERE geracao_numero = 3) AS "Ger. III",
       COUNT(*) FILTER (WHERE geracao_numero = 4) AS "Ger. IV",
       COUNT(*) FILTER (WHERE geracao_numero = 5) AS "Ger. V",
       COUNT(*) FILTER (WHERE geracao_numero = 6) AS "Ger. VI",
       COUNT(*)                                   AS total
FROM silver.dim_pokemon
GROUP BY tipo_primario
ORDER BY total DESC, tipo;
```

**Resultado:**

| Tipo Primário | Ger. I | Ger. II | Ger. III | Ger. IV | Ger. V | Ger. VI | Total |
|---|---|---|---|---|---|---|---|
| **Water** | 31 | 18 | 27 | 14 | 18 | 9 | **117** |
| **Normal** | 24 | 15 | 18 | 18 | 19 | 11 | **105** |
| **Grass** | 13 | 9 | 13 | 15 | 15 | 5 | **70** |
| **Bug** | 14 | 12 | 12 | 10 | 18 | 3 | **69** |
| **Psychic** | 11 | 7 | 12 | 8 | 15 | 4 | **57** |
| **Fire** | 14 | 8 | 8 | 5 | 9 | 8 | **52** |
| **Electric** | 9 | 8 | 5 | 7 | 8 | 7 | **44** |
| **Rock** | 10 | 5 | 8 | 6 | 6 | 9 | **44** |
| **Ghost** | 4 | 1 | 5 | 7 | 9 | 6 | **32** |
| **Ground** | 8 | 3 | 7 | 4 | 10 | 0 | **32** |
| **Dragon** | 3 | 1 | 14 | 4 | 7 | 3 | **32** |
| **Dark** | 0 | 6 | 6 | 4 | 13 | 2 | **31** |
| **Poison** | 14 | 1 | 3 | 6 | 2 | 2 | **28** |
| **Fighting** | 8 | 3 | 5 | 4 | 7 | 1 | **28** |
| **Steel** | 0 | 3 | 12 | 3 | 4 | 5 | **27** |
| **Ice** | 2 | 4 | 7 | 3 | 3 | 4 | **23** |
| **Fairy** | 2 | 5 | 0 | 1 | 2 | 7 | **17** |
| **Flying** | 0 | 0 | 0 | 0 | 2 | 2 | **4** |
| **Total Geral**| **166** | **106** | **160** | **121** | **165** | **82** | **800** |

#### Interpretação dos Resultados
1. **Predominância Ecológica de Water e Normal:** O tipo `Water` é o mais volumoso de todo o cadastro (117 Pokémon, ~14,6%), seguido de perto por `Normal` (105 Pokémon). Essa abundância reflete a mecânica de exploração dos jogos (rotas aquáticas extensas e fauna comum de início de jogo).
2. **Evolução Temporal e Mudanças de Regras:**
   - Os tipos `Steel` e `Dark` contam com 0 representantes primários na Geração I, pois foram introduzidos apenas na Geração II (Johto) para balancear a hegemonia do tipo Psychic.
   - O tipo `Fairy` apresenta contagens retroativas nas Gerações I e II devido à reclassificação de espécies clássicas (como Clefairy e Togepi), com introdução formal massiva apenas na Geração VI.
3. **Escassez de Flying Puro:** Apenas 4 Pokémon possuem `Flying` como tipo primário (Noibat, Noivern e as formas de Tornadus). Na quase totalidade das espécies voadoras, `Flying` é posicionado como tipo secundário, tendo `Normal`, `Bug` ou `Fire` como primário.

---

### Análise 2: Médias dos Atributos de Status por Tipo Primário

**Consulta SQL:**
```sql
SELECT tipo_primario AS tipo,
       COUNT(*)                          AS n_pokemon,
       ROUND(AVG(hp), 1)                 AS hp,
       ROUND(AVG(ataque), 1)             AS ataque,
       ROUND(AVG(defesa), 1)             AS defesa,
       ROUND(AVG(ataque_especial), 1)    AS ataque_esp,
       ROUND(AVG(defesa_especial), 1)    AS defesa_esp,
       ROUND(AVG(velocidade), 1)         AS velocidade
FROM silver.dim_pokemon
GROUP BY tipo_primario
ORDER BY velocidade DESC;
```

**Resultado:**

| Tipo | N | HP | Ataque | Defesa | Atq. Esp. | Def. Esp. | Velocidade |
|---|---|---|---|---|---|---|---|
| **Flying** | 4 | 70.8 | 78.8 | 61.5 | 94.2 | 72.5 | **102.5** |
| **Electric** | 44 | 59.8 | 69.8 | 66.3 | 90.0 | 73.7 | **84.5** |
| **Dragon** | 32 | 83.3 | 105.8 | 86.4 | 95.0 | 88.2 | **83.0** |
| **Fire** | 52 | 69.9 | 84.7 | 67.8 | 88.9 | 72.2 | **74.4** |
| **Psychic** | 57 | 70.6 | 71.5 | 67.7 | 98.4 | 86.3 | **81.5** |
| **Dark** | 31 | 66.8 | 88.4 | 70.2 | 74.6 | 69.5 | **76.2** |
| **Normal** | 105 | 77.3 | 73.5 | 59.8 | 55.8 | 63.7 | **71.6** |
| **Ghost** | 32 | 64.4 | 73.8 | 81.2 | 79.3 | 77.9 | **64.3** |
| **Fighting** | 28 | 69.9 | 96.8 | 65.9 | 53.1 | 64.7 | **66.1** |
| **Water** | 117 | 72.1 | 74.2 | 72.9 | 74.8 | 70.5 | **65.0** |
| **Poison** | 28 | 67.2 | 74.7 | 68.8 | 60.4 | 64.3 | **63.6** |
| **Ground** | 32 | 73.8 | 95.8 | 84.8 | 56.5 | 62.8 | **63.6** |
| **Ice** | 23 | 72.0 | 72.8 | 71.4 | 77.5 | 76.2 | **63.5** |
| **Grass** | 70 | 67.3 | 73.2 | 70.8 | 77.9 | 70.4 | **61.9** |
| **Bug** | 69 | 56.9 | 71.0 | 70.7 | 53.9 | 64.7 | **61.7** |
| **Rock** | 44 | 65.4 | 92.8 | 100.8 | 63.3 | 75.8 | **55.9** |
| **Steel** | 27 | 65.2 | 92.7 | 126.4 | 67.5 | 80.6 | **55.3** |
| **Fairy** | 17 | 74.1 | 61.5 | 65.5 | 78.5 | 84.8 | **48.6** |

#### 2a. Tipo de Maior Velocidade Média
- **Vencedor:** `Flying` com **102.5** de velocidade média (seguido de perto por `Electric` com 84.5 e `Dragon` com 83.0). Os representantes de voo e elétricos são historicamente concebidos sob arquétipos de mobilidade e iniciativa ágil.

#### 2b. Tipo de Maior Resistência Média (Média de HP, Defesa e Defesa Especial)
- **Vencedor:** `Steel` com resistência média de **90.7** (HP: 65.2, Defesa: 126.4, Def. Esp.: 80.6), seguido por `Rock` (**80.7**). O tipo Aço é estruturalmente focado em defesas físicas extremas e retenção de dano.

#### 2c. Verificação de Tipo Dominante em Todos os Atributos
- **Resultado:** **Vazio (Nenhum tipo)**.
- **Interpretação:** Não existe nenhum tipo primário que ocupe simultaneamente o 1º lugar nos seis atributos de status. Isso demonstra a intenção de balanceamento estatístico dos desenvolvedores: tipos rápidos (como Flying e Electric) sacrificam defesas e HP; tanques resistentes (como Steel e Rock) pagam o preço com as piores velocidades médias do jogo.

---

## Análises sobre as Batalhas (Camada Gold)

As análises 3 a 8 consultam diretamente as tabelas materializadas do schema `gold`, sem necessidade de junções complexas ou reprocessamento de agrupamentos em tempo de consulta.

---

### Análise 3: Taxa de Vitórias por Pokémon (10 Maiores e 10 Menores)

**Corte Adotado:** Mínimo de **100 combates**.
*Justificativa do Corte:* A distribuição de combates é assimétrica. Cada Pokémon disputou em média ~125 combates (mínimo observado: 92; máximo: 168). Adotar $N \ge 100$ assegura significância estatística, garantindo um erro-padrão amostral inferior a 5 pontos percentuais para taxas em torno de 50%. Sem esse filtro, entidades com pouquíssimas lutas e taxa espúria de 100% figurariam no topo como ruído amostral.

**Top 10 Maiores Taxas de Vitória ($N \ge 100$):**

| Pokémon | Tipo Primário | Tipo Secundário | Raridade | N Combates | Vitórias | Winrate |
|---|---|---|---|---|---|---|
| **Mega Aerodactyl** | Rock | Flying | Comum | 129 | 127 | **0.9845** |
| **Mega Mewtwo X** | Psychic | Fighting | Lendário | 120 | 118 | **0.9833** |
| **Deoxys Speed Forme** | Psychic | Nenhum | Mítico | 114 | 111 | **0.9737** |
| **Mega Rayquaza** | Dragon | Flying | Lendário | 131 | 127 | **0.9695** |
| **Mega Lopunny** | Normal | Fighting | Comum | 124 | 120 | **0.9677** |
| **Mewtwo** | Psychic | Nenhum | Lendário | 106 | 102 | **0.9623** |
| **Greninja** | Water | Dark | Comum | 127 | 122 | **0.9606** |
| **Weavile** | Dark | Ice | Comum | 133 | 127 | **0.9549** |
| **Aerodactyl** | Rock | Flying | Comum | 139 | 132 | **0.9496** |
| **Mega Alakazam** | Psychic | Nenhum | Comum | 112 | 106 | **0.9464** |

**Top 10 Menores Taxas de Vitória ($N \ge 100$):**

| Pokémon | Tipo Primário | Tipo Secundário | Raridade | N Combates | Vitórias | Winrate |
|---|---|---|---|---|---|---|
| **Shuckle** | Bug | Rock | Comum | 135 | 9 | **0.0667** |
| **Silcoon** | Bug | Nenhum | Comum | 125 | 11 | **0.0880** |
| **Togepi** | Fairy | Nenhum | Bebê | 122 | 12 | **0.0984** |
| **Cascoon** | Bug | Nenhum | Comum | 133 | 14 | **0.1053** |
| **Magikarp** | Water | Nenhum | Comum | 102 | 11 | **0.1078** |
| **Solosis** | Psychic | Nenhum | Comum | 117 | 13 | **0.1111** |
| **Wooper** | Water | Ground | Comum | 125 | 14 | **0.1120** |
| **Feebas** | Water | Nenhum | Comum | 129 | 15 | **0.1163** |
| **Swinub** | Ice | Ground | Comum | 119 | 14 | **0.1176** |
| **Slugma** | Fire | Nenhum | Comum | 123 | 15 | **0.1220** |

#### Interpretação dos Resultados
- **O Domínio da Ofensiva Ágil:** O topo é quase inteiramente composto por formas Mega e Pokémon com atributos extremos de **Velocidade** ($\ge 130$) e **Ataque/Sp. Atk** (Mega Aerodactyl, Deoxys Speed, Mega Rayquaza).
- **A Penalidade do Tanque Lento:** O caso emblemático de **Shuckle** ilustra com precisão a dinâmica do simulador: apesar de ostentar 230 de Defesa e 230 de Defesa Especial (as mais altas do jogo), sua Velocidade ínfima (5) e Ataque irrisório (10) tornam-no uma presa indefesa no simulador, amargando a pior taxa de vitórias de todo o ecossistema (6,67%).
- **Estágios Iniciais e Casulos:** Pokémon nos estágios larvais/bebês (Magikarp, Feebas, Silcoon, Togepi) concentram-se no rodapé, confirmando que Pokémon sem status evoluídos não têm viabilidade competitiva.

---

### Análise 4: Taxa de Vitórias por Tipo Primário

**Consulta SQL:**
```sql
SELECT tipo_primario, n_pokemon, n_combates, n_vitorias, taxa_vitorias
FROM gold.taxa_vitorias_por_tipo
ORDER BY taxa_vitorias DESC;
```

**Resultado:**

| Tipo Primário | N Pokémon | N Combates | N Vitórias | Winrate |
|---|---|---|---|---|
| **Flying** | 4 | 506 | 385 | **0.7609** |
| **Dragon** | 32 | 4038 | 2552 | **0.6320** |
| **Electric** | 44 | 5576 | 3236 | **0.5803** |
| **Dark** | 31 | 3908 | 2154 | **0.5512** |
| **Fire** | 52 | 6542 | 3442 | **0.5261** |
| **Psychic** | 57 | 7114 | 3719 | **0.5228** |
| **Normal** | 105 | 13170 | 6649 | **0.5049** |
| **Ground** | 32 | 4004 | 2004 | **0.5005** |
| **Fighting** | 28 | 3514 | 1756 | **0.4997** |
| **Ghost** | 32 | 3972 | 1968 | **0.4955** |
| **Water** | 117 | 14614 | 6940 | **0.4749** |
| **Steel** | 27 | 3410 | 1587 | **0.4654** |
| **Ice** | 23 | 2886 | 1332 | **0.4615** |
| **Grass** | 70 | 8774 | 3896 | **0.4440** |
| **Poison** | 28 | 3516 | 1526 | **0.4340** |
| **Bug** | 69 | 8642 | 3740 | **0.4328** |
| **Rock** | 44 | 5542 | 2378 | **0.4291** |
| **Fairy** | 17 | 2270 | 736 | **0.3242** |

#### Interpretação dos Resultados
- **Existência de Tipos Dominantes:** Existe forte assimetria competitiva entre os tipos primários. `Flying` lidera com folga (76,1%), seguido por `Dragon` (63,2%) e `Electric` (58,0%). A correlação com a velocidade média apurada na Análise 2 é direta: os tipos mais velozes do cadastro são precisamente os tipos com as maiores taxas de vitória globais.
- **Tipos Prejudicados:** `Fairy` (32,4%), `Rock` (42,9%) e `Bug` (43,3%) figuram nas últimas posições. No caso do tipo Fairy, a amostra é composta primordialmente por Pokémon de estágios não evoluídos ou bebês (Togepi, Cleffa, Igglybuff) e Pokémon lentos, rebaixando a taxa média do grupo.

---

### Análise 5: Relação entre Diferença de Velocidade e Vitória

**Consulta SQL:**
```sql
SELECT faixa, n_combates, n_vitorias, taxa_vitorias
FROM gold.taxa_vitorias_por_faixa_velocidade
ORDER BY faixa_ordem;
```

**Resultado:**

| Faixa de Diferença de Velocidade | N Combates | N Vitórias | Winrate |
|---|---|---|---|
| **a) muito mais lento (<= -50)** | 14.162 | 878 | **0.0620** |
| **b) mais lento (-49 a -20)** | 20.354 | 4.312 | **0.2119** |
| **c) um pouco mais lento (-19 a -6)** | 11.238 | 4.148 | **0.3691** |
| **d) equivalente (-5 a +5)** | 8.492 | 4.246 | **0.5000** |
| **e) um pouco mais rápido (+6 a +19)** | 11.238 | 7.090 | **0.6309** |
| **f) mais rápido (+20 a +49)** | 20.354 | 16.042 | **0.7881** |
| **g) muito mais rápido (>= +50)** | 14.162 | 13.284 | **0.9380** |

#### Interpretação dos Resultados
- **Simetria Perfeita em Torno de Zero:** A faixa de velocidade equivalente ($-5$ a $+5$) exibe rigorosamente **50,00%** de vitória, confirmando o equilíbrio quando os atributos de velocidade se anulam. As faixas simétricas espelham-se perfeitamente (ex.: $21,19\% + 78,81\% = 100\%$).
- **A Velocidade como Variável Explicativa Primária:** A relação entre diferença de velocidade e chance de vitória é estritamente monotônica e de magnitude esmagadora. Ter uma vantagem de $+50$ de velocidade contra o oponente confere uma probabilidade empírica de vitória de **93,80%**; inversamente, estar $50$ pontos abaixo reduz as chances a irrisórios **6,20%**. Esse achado demonstra conclusivamente que o simulador de batalhas do dataset dá peso determinante para quem age com rapidez superior.

---

### Análise 6: Vantagem de Tipo e Vitória por Multiplicador Efetivo

**Critério Adotado:** O multiplicador efetivo é o produto das relações de dano do tipo primário do atacante contra os **dois tipos** do defensor ($E_1 \times E_2$), assumindo os valores `0, 0.25, 0.5, 1, 2 ou 4`.

**Consulta SQL:**
```sql
SELECT multiplicador, n_combates, n_vitorias, taxa_vitorias
FROM gold.taxa_vitorias_por_multiplicador
ORDER BY multiplicador;
```

**Resultado:**

| Multiplicador Efetivo | N Combates | N Vitórias | Winrate |
|---|---|---|---|
| **0.00** | 1.834 | 916 | **0.4995** |
| **0.25** | 3.120 | 1.566 | **0.5019** |
| **0.50** | 22.456 | 11.218 | **0.4996** |
| **1.00** | 46.182 | 23.102 | **0.5002** |
| **2.00** | 23.364 | 11.698 | **0.5007** |
| **4.00** | 3.044 | 1.500 | **0.4928** |

#### Interpretação dos Resultados (Achado Fundamental)
- **Ausência de Efeito da Tabela de Tipos no Simulador:** Ao contrário do que ocorreria na mecânica oficial da franquia Pokémon, onde um multiplicador $2\times$ ou $4\times$ garantiria vantagem substancial e um multiplicador $0\times$ significaria dano nulo, **no dataset analisado a taxa de vitória permanece fixa em ~50% para todos os multiplicadores**.
- **Validação da Premissa do Enunciado:** Como o [enunciado.md](file:///home/lucas/Downloads/ep01/enunciado.md#L313) expressamente antecipou, este resultado é plenamente válido e reflete a realidade das batalhas simuladas: o algoritmo sintético que originou o dataset de combates utilizou primordialmente os atributos brutos de status (notadamente Velocidade e Ataque vs. Defesa), **sem incorporar a matriz de efetividade de tipos da PokéAPI**. A modelagem dimensional cumpriu seu papel de permitir a auditoria empírica da fonte.

---

### Análise 7: Matriz de Confronto entre Tipos e Divergências

A matriz de confronto cruza os 18 tipos primários atacantes com os 18 tipos defensores ($18 \times 18 = 324$ células), com a orientação baseada no combatente vitorioso. As células $(A, B)$ e $(B, A)$ somam 1.

**Consulta de Posições Divergentes:**
```sql
SELECT tipo_atacante, tipo_defensor, multiplicador_tipo, n_confrontos, taxa_vitorias
FROM gold.matriz_confronto
WHERE divergente
ORDER BY ABS(taxa_vitorias - 0.5) DESC
LIMIT 10;
```

**Amostra das Maiores Divergências Identificadas:**

| Tipo Atacante | Tipo Defensor | Mult. Teórico | N Confrontos | Taxa Vitórias | Diagnóstico |
|---|---|---|---|---|---|
| **Flying** | **Rock** | 0.50 | 28 | **0.7857** | Desvantagem teórica, mas vence amplamente |
| **Flying** | **Electric** | 0.50 | 28 | **0.7143** | Desvantagem teórica, mas vence amplamente |
| **Flying** | **Steel** | 0.50 | 18 | **0.7222** | Desvantagem teórica, mas vence amplamente |
| **Fairy** | **Dragon** | 2.00 | 92 | **0.2935** | Vantagem teórica, mas perde sistematicamente |
| **Fairy** | **Fighting** | 2.00 | 80 | **0.3125** | Vantagem teórica, mas perde sistematicamente |
| **Fairy** | **Dark** | 2.00 | 88 | **0.3295** | Vantagem teórica, mas perde sistematicamente |
| **Rock** | **Bug** | 2.00 | 378 | **0.4471** | Vantagem teórica com winrate abaixo de 50% |
| **Ghost** | **Normal** | 0.00 | 422 | **0.4929** | Imunidade teórica com winrate próximo de 50% |

#### Interpretação dos Resultados
- **Desconexão Mecânica:** A análise da matriz de 324 posições confirma e aprofunda o diagnóstico da Análise 6. Confrontos onde o tipo atacante possui vantagem de tipo (como `Fairy` atacando `Dragon`, com multiplicador $2.0$) apresentam taxas de vitória de apenas **29,35%**, pois a média dos Pokémon do tipo Dragon possui status base e velocidade vastamente superiores aos do tipo Fairy.
- De forma análoga, `Flying` derrota `Rock`, `Electric` e `Steel` em mais de 70% das ocasiões mesmo tendo desvantagem de dano ($0.5$), devido à velocidade superior de seus espécimes.

---

### Análise 8: Análise Proposta pelo Grupo

**Pergunta de Negócio Formulada:**
> *"Pokémon lendários, míticos e formas alternativas possuem taxa de vitórias estatisticamente superior aos comuns? E a iniciativa do combate (atacar primeiro) é capaz de mitigar a desvantagem de um Pokémon comum?"*

**Capacidade do Modelo Exigida:**
Esta análise cruza as dimensões taxonômicas de cadastro geradas na conciliação da PokéAPI com a fato (`categoria_raridade` e `tipo_forma`), avaliando seu impacto conjunto com a métrica da fato `atacou_primeiro` (proveniente do campo `First_pokemon` do CSV de combates), atributo ausente em todas as análises anteriores.

**Consulta SQL:**
```sql
SELECT categoria_raridade, tipo_forma, n_pokemon, n_combates, taxa_vitorias,
       taxa_vitorias_atacando_primeiro, taxa_vitorias_atacando_depois
FROM gold.taxa_vitorias_por_raridade
ORDER BY taxa_vitorias DESC;
```

**Resultado:**

| Categoria Raridade | Tipo Forma | N Pokémon | N Combates | Winrate Geral | Atacando Primeiro | Atacando Depois | Bônus Iniciativa |
|---|---|---|---|---|---|---|---|
| **Lendário** | **Alternativa** | 6 | 822 | **0.9063** | 0.9416 | 0.8710 | $+7.06\%$ |
| **Lendário** | **Padrão** | 40 | 5.044 | **0.8095** | 0.8521 | 0.7668 | $+8.53\%$ |
| **Mítico** | **Alternativa** | 5 | 608 | **0.7813** | 0.8289 | 0.7336 | $+9.53\%$ |
| **Mítico** | **Padrão** | 20 | 2.532 | **0.7334** | 0.7820 | 0.6848 | $+9.72\%$ |
| **Comum** | **Alternativa** | 68 | 8.520 | **0.6592** | 0.7108 | 0.6075 | $+10.33\%$ |
| **Comum** | **Padrão** | 636 | 79.462 | **0.4619** | 0.5126 | 0.4112 | $+10.14\%$ |
| **Bebê** | **Padrão** | 24 | 3.012 | **0.1786** | 0.2258 | 0.1315 | $+9.43\%$ |

#### Interpretação dos Resultados
1. **Hierarquia Clara de Poder (Raridade e Forma):**
   - **Lendários com Formas Alternativas** (como Mega Rayquaza, Primal Groudon/Kyogre) ocupam o topo absoluto do metagame, vencendo mais de **90%** das batalhas.
   - Formas alternativas de Pokémon comuns (especialmente Mega Evoluções) aumentam expressivamente o winrate médio de **46,19%** para **65,92%** (+19,7 pontos percentuais), evidenciando o incremento maciço de status conferido pelas formas Mega.
   - **Bebês** amargam um desempenho de apenas **17,86%**, evidenciando sua inadequação para confrontos diretos sem evolução.
2. **O Efeito Sistemático da Iniciativa:**
   - Em todas as categorias, **atacar primeiro confere uma vantagem de aproximadamente 7 a 10 pontos percentuais de probabilidade de vitória**.
   - Notavelmente, para Pokémon comuns em sua forma padrão, atacar primeiro é a diferença entre ser competitivo ou não: a taxa sobe de **41,12%** (atacando depois) para **51,26%** (atacando primeiro). Ter a iniciativa permite ao combatente comum superar a marca dos 50% de vitória.
