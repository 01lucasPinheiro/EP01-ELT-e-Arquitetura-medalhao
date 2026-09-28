#!/usr/bin/env python3
"""
publicar.py  --  SILVER -> GOLD (PostgreSQL)

Este script NÃO move dados para o Python. A agregação é feita pelo próprio banco,
em `INSERT INTO gold.<tabela> SELECT ... FROM silver.<tabela>` (sql/gold.sql).
Cabe ao script a orquestração:

  1. executar sql/gold.sql (cria o que faltar, esvazia e repovoa as tabelas);
  2. verificar o resultado (nenhuma tabela vazia; tamanhos conhecidos);
  3. registrar a execução em gold.log_publicacao (linhas por tabela + momento).

Idempotente: rodar de novo produz o mesmo estado (TRUNCATE + INSERT), sem duplicar linhas.
Não acessa o MongoDB, a API nem os CSVs.

Variável de ambiente (opcional):
    POSTGRES_DSN  (padrão: postgresql://postgres:postgres@localhost:5432/pokedex)
"""
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/pokedex")
RAIZ = Path(__file__).resolve().parent

# Tamanhos que o modelo impõe (verificação de consistência).
ESPERADO = {
    "taxa_vitorias_por_tipo": 18,
    "taxa_vitorias_por_faixa_velocidade": 7,
    "matriz_confronto": 324,
}


def main():
    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('silver.fato_confronto')")
            if cur.fetchone()[0] is None:
                sys.exit("silver.fato_confronto não existe. Execute carregar.py primeiro.")

            print("== Gold: executando sql/gold.sql (agregação dentro do PostgreSQL) ==")
            cur.execute((RAIZ / "sql" / "gold.sql").read_text(encoding="utf-8"))

            cur.execute("""SELECT table_name FROM information_schema.tables
                           WHERE table_schema = 'gold' AND table_name <> 'log_publicacao'
                           ORDER BY table_name""")
            tabelas = [r[0] for r in cur.fetchall()]

            contagens = {}
            for t in tabelas:
                cur.execute(sql.SQL("SELECT count(*) FROM gold.{}").format(sql.Identifier(t)))
                contagens[t] = cur.fetchone()[0]

            vazias = [t for t, n in contagens.items() if n == 0]
            if vazias:
                raise RuntimeError(f"Tabelas do gold vazias após a publicação: {vazias}")
            for t, esperado in ESPERADO.items():
                if contagens.get(t) != esperado:
                    raise RuntimeError(f"gold.{t}: {contagens.get(t)} linhas (esperado {esperado})")

            cur.execute("DELETE FROM gold.log_publicacao")
            cur.executemany(
                "INSERT INTO gold.log_publicacao (tabela, linhas, publicado_em) VALUES (%s, %s, now())",
                list(contagens.items()))

            print("== Linhas por tabela do gold ==")
            for t, n in contagens.items():
                print(f"   gold.{t:38s} {n:>6d}")
            cur.execute("SELECT max(publicado_em) FROM gold.log_publicacao")
            print(f"== Publicado em {cur.fetchone()[0]:%Y-%m-%d %H:%M:%S %Z} ==")


if __name__ == "__main__":
    main()
