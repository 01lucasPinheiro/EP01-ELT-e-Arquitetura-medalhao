DROP SCHEMA IF EXISTS silver CASCADE;
CREATE SCHEMA silver;

-- dimensao geracao
CREATE TABLE silver.dim_geracao (
    geracao_sk  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    numero      smallint NOT NULL UNIQUE,
    nome        text     NOT NULL,
    regiao      text     NOT NULL
);

-- dimensao tipo
CREATE TABLE silver.dim_tipo (
    tipo_sk          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tipo_api      smallint UNIQUE,
    nome             text    NOT NULL UNIQUE,
    membro_especial  boolean NOT NULL DEFAULT false
);

-- efetividade de tipos
CREATE TABLE silver.efetividade_tipo (
    atacante_sk    integer      NOT NULL REFERENCES silver.dim_tipo (tipo_sk),
    defensor_sk    integer      NOT NULL REFERENCES silver.dim_tipo (tipo_sk),
    multiplicador  numeric(3,2) NOT NULL CHECK (multiplicador IN (0, 0.5, 1, 2)),
    PRIMARY KEY (atacante_sk, defensor_sk)
);

-- dimensao pokemon
CREATE TABLE silver.dim_pokemon (
    pokemon_sk          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_csv              integer NOT NULL UNIQUE,
    id_pokedex          integer,
    id_forma_api        integer,
    nome                text    NOT NULL,
    nome_api            text,
    membro_especial     boolean NOT NULL DEFAULT false,
    conciliado          boolean NOT NULL,
    tipo_forma          text    NOT NULL CHECK (tipo_forma IN ('Padrão', 'Alternativa', 'Não conciliado')),
    categoria_raridade  text    NOT NULL CHECK (categoria_raridade IN ('Comum', 'Bebê', 'Lendário', 'Mítico')),
    tipo_primario       text    NOT NULL,
    tipo_secundario     text    NOT NULL,
    geracao_numero      smallint NOT NULL,
    hp                  smallint NOT NULL,
    ataque              smallint NOT NULL,
    defesa              smallint NOT NULL,
    ataque_especial     smallint NOT NULL,
    defesa_especial     smallint NOT NULL,
    velocidade          smallint NOT NULL,
    habitat             text    NOT NULL,
    cor                 text    NOT NULL,
    forma_corporal      text    NOT NULL,
    taxa_captura        smallint,
    felicidade_base     smallint,
    altura_m            numeric(5,1),
    peso_kg             numeric(6,1),
    qtd_habilidades     smallint
);

-- fato participacao em combate
CREATE TABLE silver.fato_confronto (
    participacao_sk             bigint   GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    combate_id                  integer  NOT NULL,
    atacou_primeiro             smallint NOT NULL CHECK (atacou_primeiro IN (0, 1)),
    pokemon_sk                  integer  NOT NULL REFERENCES silver.dim_pokemon (pokemon_sk),
    oponente_sk                 integer  NOT NULL REFERENCES silver.dim_pokemon (pokemon_sk),
    tipo_primario_sk            integer  NOT NULL REFERENCES silver.dim_tipo (tipo_sk),
    tipo_secundario_sk          integer  NOT NULL REFERENCES silver.dim_tipo (tipo_sk),
    oponente_tipo_primario_sk   integer  NOT NULL REFERENCES silver.dim_tipo (tipo_sk),
    oponente_tipo_secundario_sk integer  NOT NULL REFERENCES silver.dim_tipo (tipo_sk),
    geracao_sk                  integer  NOT NULL REFERENCES silver.dim_geracao (geracao_sk),
    venceu                      smallint NOT NULL CHECK (venceu IN (0, 1)),
    velocidade                  smallint NOT NULL,
    velocidade_oponente         smallint NOT NULL,
    diferenca_velocidade        smallint NOT NULL,
    multiplicador_efetivo       numeric(4,2) NOT NULL CHECK (multiplicador_efetivo IN (0, 0.25, 0.5, 1, 2, 4)),
    UNIQUE (combate_id, atacou_primeiro)
);

CREATE INDEX ix_fato_pokemon        ON silver.fato_confronto (pokemon_sk);
CREATE INDEX ix_fato_tipo_oponente  ON silver.fato_confronto (tipo_primario_sk, oponente_tipo_primario_sk);
