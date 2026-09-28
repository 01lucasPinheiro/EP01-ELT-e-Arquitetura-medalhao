-- analise 1 quantidade de pokemon por tipo primario e geracao
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

-- analise 2 media de status por tipo primario
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

-- maior velocidade media
SELECT tipo_primario AS tipo, ROUND(AVG(velocidade), 1) AS velocidade_media
FROM silver.dim_pokemon
GROUP BY tipo_primario
ORDER BY AVG(velocidade) DESC
LIMIT 1;

-- maior resistencia media
SELECT tipo_primario AS tipo,
       ROUND(AVG(hp), 1) AS hp, ROUND(AVG(defesa), 1) AS defesa, ROUND(AVG(defesa_especial), 1) AS defesa_esp,
       ROUND((AVG(hp) + AVG(defesa) + AVG(defesa_especial)) / 3, 1) AS resistencia_media
FROM silver.dim_pokemon
GROUP BY tipo_primario
ORDER BY AVG(hp) + AVG(defesa) + AVG(defesa_especial) DESC
LIMIT 1;

-- verifica se algum tipo domina todos os atributos
WITH medias AS (
    SELECT tipo_primario AS tipo, AVG(hp) hp, AVG(ataque) atk, AVG(defesa) def,
           AVG(ataque_especial) spa, AVG(defesa_especial) spd, AVG(velocidade) vel
    FROM silver.dim_pokemon
    GROUP BY tipo_primario
),
posicoes AS (
    SELECT tipo,
           RANK() OVER (ORDER BY hp DESC)  AS p_hp,  RANK() OVER (ORDER BY atk DESC) AS p_atk,
           RANK() OVER (ORDER BY def DESC) AS p_def, RANK() OVER (ORDER BY spa DESC) AS p_spa,
           RANK() OVER (ORDER BY spd DESC) AS p_spd, RANK() OVER (ORDER BY vel DESC) AS p_vel
    FROM medias
)
SELECT tipo
FROM posicoes
WHERE p_hp = 1 AND p_atk = 1 AND p_def = 1 AND p_spa = 1 AND p_spd = 1 AND p_vel = 1;

-- analise 3 ranking de pokemon dez maiores taxas de vitoria
SELECT pokemon, tipo_primario, tipo_secundario, categoria_raridade, n_combates, n_vitorias, taxa_vitorias
FROM gold.ranking_pokemon
WHERE n_combates >= 100
ORDER BY taxa_vitorias DESC, n_combates DESC
LIMIT 10;

-- dez menores taxas de vitoria
SELECT pokemon, tipo_primario, tipo_secundario, categoria_raridade, n_combates, n_vitorias, taxa_vitorias
FROM gold.ranking_pokemon
WHERE n_combates >= 100
ORDER BY taxa_vitorias ASC, n_combates DESC
LIMIT 10;

-- analise 4 taxa de vitorias por tipo primario
SELECT tipo_primario, n_pokemon, n_combates, n_vitorias, taxa_vitorias
FROM gold.taxa_vitorias_por_tipo
ORDER BY taxa_vitorias DESC;

-- analise 5 relacao entre diferenca de velocidade e vitoria
SELECT faixa, n_combates, n_vitorias, taxa_vitorias
FROM gold.taxa_vitorias_por_faixa_velocidade
ORDER BY faixa_ordem;

-- analise 6 relacao entre vantagem de tipo e vitoria
SELECT multiplicador, n_combates, n_vitorias, taxa_vitorias
FROM gold.taxa_vitorias_por_multiplicador
ORDER BY multiplicador;

-- analise 7 matriz de confronto entre tipos
SELECT tipo_atacante, tipo_defensor, n_confrontos, taxa_vitorias, multiplicador_tipo
FROM gold.matriz_confronto
ORDER BY tipo_atacante, tipo_defensor;

-- posicoes divergentes entre taxa e multiplicador
SELECT tipo_atacante, tipo_defensor, multiplicador_tipo, n_confrontos, taxa_vitorias
FROM gold.matriz_confronto
WHERE divergente
ORDER BY ABS(taxa_vitorias - 0.5) DESC;

-- analise 8 proposta vitorias por raridade forma e iniciativa
SELECT categoria_raridade, tipo_forma, n_pokemon, n_combates, taxa_vitorias,
       taxa_vitorias_atacando_primeiro, taxa_vitorias_atacando_depois
FROM gold.taxa_vitorias_por_raridade
ORDER BY taxa_vitorias DESC;
