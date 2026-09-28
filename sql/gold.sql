CREATE SCHEMA IF NOT EXISTS gold;

-- registro da publicacao
CREATE TABLE IF NOT EXISTS gold.log_publicacao (
    tabela        text PRIMARY KEY,
    linhas        integer     NOT NULL,
    publicado_em  timestamptz NOT NULL
);

-- analise 3 ranking de pokemon
CREATE TABLE IF NOT EXISTS gold.ranking_pokemon (
    pokemon_sk         integer PRIMARY KEY,
    id_csv             integer  NOT NULL,
    pokemon            text     NOT NULL,
    tipo_primario      text     NOT NULL,
    tipo_secundario    text     NOT NULL,
    geracao            smallint NOT NULL,
    categoria_raridade text     NOT NULL,
    n_combates         integer  NOT NULL,
    n_vitorias         integer  NOT NULL,
    taxa_vitorias      numeric(6,4) NOT NULL
);

-- analise 4 taxa de vitorias por tipo
CREATE TABLE IF NOT EXISTS gold.taxa_vitorias_por_tipo (
    tipo_primario  text PRIMARY KEY,
    n_pokemon      integer NOT NULL,
    n_combates     integer NOT NULL,
    n_vitorias     integer NOT NULL,
    taxa_vitorias  numeric(6,4) NOT NULL
);

-- analise 5 taxa de vitorias por faixa de velocidade
CREATE TABLE IF NOT EXISTS gold.taxa_vitorias_por_faixa_velocidade (
    faixa_ordem    smallint PRIMARY KEY,
    faixa          text     NOT NULL,
    diff_min       smallint NOT NULL,
    diff_max       smallint NOT NULL,
    n_combates     integer  NOT NULL,
    n_vitorias     integer  NOT NULL,
    taxa_vitorias  numeric(6,4)
);

-- analise 6 taxa de vitorias por multiplicador
CREATE TABLE IF NOT EXISTS gold.taxa_vitorias_por_multiplicador (
    multiplicador  numeric(4,2) PRIMARY KEY,
    n_combates     integer NOT NULL,
    n_vitorias     integer NOT NULL,
    taxa_vitorias  numeric(6,4) NOT NULL
);

-- analise 7 matriz de confronto
CREATE TABLE IF NOT EXISTS gold.matriz_confronto (
    tipo_atacante        text NOT NULL,
    tipo_defensor        text NOT NULL,
    n_confrontos         integer NOT NULL,
    n_vitorias_atacante  integer NOT NULL,
    taxa_vitorias        numeric(6,4),
    multiplicador_tipo   numeric(3,2) NOT NULL,
    divergente           boolean NOT NULL,
    PRIMARY KEY (tipo_atacante, tipo_defensor)
);

-- analise 8 taxa de vitorias por raridade
CREATE TABLE IF NOT EXISTS gold.taxa_vitorias_por_raridade (
    categoria_raridade               text NOT NULL,
    tipo_forma                       text NOT NULL,
    n_pokemon                        integer NOT NULL,
    n_combates                       integer NOT NULL,
    n_vitorias                       integer NOT NULL,
    taxa_vitorias                    numeric(6,4) NOT NULL,
    taxa_vitorias_atacando_primeiro  numeric(6,4),
    taxa_vitorias_atacando_depois    numeric(6,4),
    PRIMARY KEY (categoria_raridade, tipo_forma)
);

TRUNCATE gold.ranking_pokemon,
         gold.taxa_vitorias_por_tipo,
         gold.taxa_vitorias_por_faixa_velocidade,
         gold.taxa_vitorias_por_multiplicador,
         gold.matriz_confronto,
         gold.taxa_vitorias_por_raridade;

-- carga analise 3
INSERT INTO gold.ranking_pokemon
SELECT p.pokemon_sk, p.id_csv, p.nome, p.tipo_primario, p.tipo_secundario,
       p.geracao_numero, p.categoria_raridade,
       COUNT(*), SUM(f.venceu), ROUND(AVG(f.venceu), 4)
FROM silver.fato_confronto f
JOIN silver.dim_pokemon p ON p.pokemon_sk = f.pokemon_sk
GROUP BY p.pokemon_sk, p.id_csv, p.nome, p.tipo_primario, p.tipo_secundario,
         p.geracao_numero, p.categoria_raridade;

-- carga analise 4
INSERT INTO gold.taxa_vitorias_por_tipo
SELECT t.nome, COUNT(DISTINCT f.pokemon_sk), COUNT(*), SUM(f.venceu), ROUND(AVG(f.venceu), 4)
FROM silver.fato_confronto f
JOIN silver.dim_tipo t ON t.tipo_sk = f.tipo_primario_sk
GROUP BY t.nome;

-- carga analise 5
INSERT INTO gold.taxa_vitorias_por_faixa_velocidade
WITH faixas (ordem, rotulo, minimo, maximo) AS (
    VALUES (1, 'a) muito mais lento (<= -50)',  -999, -50),
           (2, 'b) mais lento (-49 a -20)',      -49, -20),
           (3, 'c) um pouco mais lento (-19 a -6)', -19, -6),
           (4, 'd) equivalente (-5 a +5)',        -5,   5),
           (5, 'e) um pouco mais rápido (+6 a +19)', 6,  19),
           (6, 'f) mais rápido (+20 a +49)',      20,  49),
           (7, 'g) muito mais rápido (>= +50)',   50, 999)
)
SELECT x.ordem, x.rotulo, x.minimo, x.maximo,
       COUNT(f.participacao_sk), COALESCE(SUM(f.venceu), 0), ROUND(AVG(f.venceu), 4)
FROM faixas x
LEFT JOIN silver.fato_confronto f ON f.diferenca_velocidade BETWEEN x.minimo AND x.maximo
GROUP BY x.ordem, x.rotulo, x.minimo, x.maximo;

-- carga analise 6
INSERT INTO gold.taxa_vitorias_por_multiplicador
SELECT f.multiplicador_efetivo, COUNT(*), SUM(f.venceu), ROUND(AVG(f.venceu), 4)
FROM silver.fato_confronto f
GROUP BY f.multiplicador_efetivo;

-- carga analise 7
INSERT INTO gold.matriz_confronto
SELECT a.nome, d.nome,
       COALESCE(x.n, 0), COALESCE(x.v, 0), x.taxa, e.multiplicador,
       COALESCE((e.multiplicador > 1 AND x.taxa < 0.5) OR (e.multiplicador < 1 AND x.taxa > 0.5), false)
FROM silver.efetividade_tipo e
JOIN silver.dim_tipo a ON a.tipo_sk = e.atacante_sk
JOIN silver.dim_tipo d ON d.tipo_sk = e.defensor_sk
LEFT JOIN (
    SELECT tipo_primario_sk AS atk, oponente_tipo_primario_sk AS def,
           COUNT(*) AS n, SUM(venceu) AS v, ROUND(AVG(venceu), 4) AS taxa
    FROM silver.fato_confronto
    GROUP BY tipo_primario_sk, oponente_tipo_primario_sk
) x ON x.atk = e.atacante_sk AND x.def = e.defensor_sk;

-- carga analise 8
INSERT INTO gold.taxa_vitorias_por_raridade
SELECT p.categoria_raridade, p.tipo_forma,
       COUNT(DISTINCT f.pokemon_sk), COUNT(*), SUM(f.venceu), ROUND(AVG(f.venceu), 4),
       ROUND(AVG(f.venceu) FILTER (WHERE f.atacou_primeiro = 1), 4),
       ROUND(AVG(f.venceu) FILTER (WHERE f.atacou_primeiro = 0), 4)
FROM silver.fato_confronto f
JOIN silver.dim_pokemon p ON p.pokemon_sk = f.pokemon_sk
GROUP BY p.categoria_raridade, p.tipo_forma;
