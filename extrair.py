#!/usr/bin/env python3
"""
extrair.py  --  FONTES -> BRONZE (MongoDB)

Lê a PokéAPI e os dois CSVs e grava, SEM TRANSFORMAR, cinco coleções no banco
`pokedex_bronze`:  pokemon, especies, tipos, pokemon_csv, combates.

Garantias (R1, R2, R3):
  * o documento reproduz a resposta da fonte; só se ACRESCENTAM campos de
    linhagem prefixados por "_" (_fonte, _url, _ingerido_em, e _linha nos CSVs);
  * _id derivado da chave natural  ->  a carga é um upsert (idempotente);
  * cache em disco (dados_brutos/) antes de qualquer requisição: a segunda
    execução faz ZERO requisições e produz exatamente o mesmo estado no Mongo,
    porque _ingerido_em vem da data do arquivo em cache, não do relógio.

Uso:
    python extrair.py

Variáveis de ambiente (opcionais):
    MONGO_URI   (padrão: mongodb://localhost:27017)
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from pymongo import MongoClient, ReplaceOne

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = "pokedex_bronze"

API = "https://pokeapi.co/api/v2"
CSV_URLS = {
    "pokemon.csv": "https://raw.githubusercontent.com/cdiener/pokemon_app/master/pokemon.csv",
    "combats.csv": "https://raw.githubusercontent.com/cdiener/pokemon_app/master/combats.csv",
}
N_ESPECIES = 721          # gerações I a VI
PAUSA = 0.1               # segundos entre requisições à API
LOTE = 5000               # tamanho do lote de escrita no Mongo

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ / "dados_brutos"

sessao = requests.Session()
sessao.headers["User-Agent"] = "ep01-etl-medalhao (trabalho academico)"
requisicoes = 0


# --------------------------------------------------------------------------
# Rede + cache
# --------------------------------------------------------------------------
def baixar(url):
    """GET com novas tentativas. Única função do script que toca a rede."""
    global requisicoes
    for tentativa in range(1, 6):
        try:
            requisicoes += 1
            resp = sessao.get(url, timeout=30)
            time.sleep(PAUSA)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 * tentativa)
                continue
            resp.raise_for_status()
        except requests.RequestException as erro:
            if tentativa == 5:
                raise
            print(f"   ! falha em {url} ({erro}); tentativa {tentativa}/5", file=sys.stderr)
            time.sleep(2 * tentativa)
    raise RuntimeError(f"não foi possível obter {url}")


def gravar_atomico(caminho, conteudo_bytes):
    """Grava via arquivo temporário: um cache truncado nunca é aceito como válido."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.name + ".tmp")
    tmp.write_bytes(conteudo_bytes)
    tmp.replace(caminho)


def obter_json(url, caminho):
    """Cache primeiro; a API só é consultada se o arquivo não existir."""
    if not caminho.exists():
        gravar_atomico(caminho, baixar(url).content)
    return json.loads(caminho.read_text(encoding="utf-8"))


def obter_arquivo(url, caminho):
    if not caminho.exists():
        gravar_atomico(caminho, baixar(url).content)
    return caminho


def carimbo(caminho):
    """Momento de obtenção = data do arquivo em cache (estável entre execuções)."""
    ts = datetime.fromtimestamp(caminho.stat().st_mtime, tz=timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def id_da_url(url):
    return int(url.rstrip("/").split("/")[-1])


def documento(_id, fonte, url, caminho, conteudo, **extras):
    """Resposta da fonte + campos de linhagem. Nada da fonte é alterado."""
    doc = {"_id": _id, "_fonte": fonte, "_url": url, "_ingerido_em": carimbo(caminho)}
    doc.update(extras)
    doc.update(conteudo)
    return doc


def gravar_colecao(db, nome, docs):
    """Upsert por _id. ReplaceOne (e não $set) para que campos como 'Sp. Atk'
    sejam preservados literalmente, sem que o ponto vire caminho aninhado."""
    ops = [ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs]
    for i in range(0, len(ops), LOTE):
        db[nome].bulk_write(ops[i:i + LOTE], ordered=False)


# --------------------------------------------------------------------------
# PokéAPI
# --------------------------------------------------------------------------
def extrair_tipos():
    url_indice = f"{API}/type?limit=100"
    indice = obter_json(url_indice, CACHE / "tipos" / "_indice.json")
    docs = []
    for item in indice["results"]:
        tid = id_da_url(item["url"])
        caminho = CACHE / "tipos" / f"{tid}.json"
        dados = obter_json(item["url"], caminho)
        docs.append(documento(f"tipo/{tid}", "pokeapi", item["url"], caminho, dados))
    print(f"   tipos: {len(docs)} (esperado 21)")
    return docs


def extrair_especies_e_formas():
    """Percorre as 721 espécies e, a partir de varieties[], TODAS as formas."""
    docs_especies, docs_pokemon, vistos = [], [], set()
    for sid in range(1, N_ESPECIES + 1):
        url_esp = f"{API}/pokemon-species/{sid}"
        caminho_esp = CACHE / "especies" / f"{sid}.json"
        esp = obter_json(url_esp, caminho_esp)
        docs_especies.append(documento(f"especie/{sid}", "pokeapi", url_esp, caminho_esp, esp))

        for variedade in esp["varieties"]:
            url_pok = variedade["pokemon"]["url"]
            pid = id_da_url(url_pok)
            if pid in vistos:
                continue
            vistos.add(pid)
            caminho_pok = CACHE / "pokemon" / f"{pid}.json"
            pok = obter_json(url_pok, caminho_pok)
            docs_pokemon.append(documento(f"pokemon/{pid}", "pokeapi", url_pok, caminho_pok, pok))

        if sid % 50 == 0 or sid == N_ESPECIES:
            print(f"   espécies {sid}/{N_ESPECIES}  |  formas acumuladas: {len(docs_pokemon)}")
    return docs_especies, docs_pokemon


# --------------------------------------------------------------------------
# CSVs
# --------------------------------------------------------------------------
def ler_csv(nome_arquivo):
    """Uma linha = um dict; todos os valores permanecem TEXTO (sem conversão)."""
    url = CSV_URLS[nome_arquivo]
    caminho = obter_arquivo(url, CACHE / "csv" / nome_arquivo)
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    return url, caminho, linhas


def extrair_csvs():
    url, caminho, linhas = ler_csv("pokemon.csv")
    docs_pokemon_csv = [
        documento(f"pokemon_csv/{r['#']}", "csv", url, caminho, r, _linha=n)
        for n, r in enumerate(linhas, start=1)
    ]
    url, caminho, linhas = ler_csv("combats.csv")
    docs_combates = [
        documento(f"combate/{n}", "csv", url, caminho, r, _linha=n)
        for n, r in enumerate(linhas, start=1)
    ]
    print(f"   pokemon_csv: {len(docs_pokemon_csv)} (esperado 800) | combates: {len(docs_combates)} (esperado 50000)")
    return docs_pokemon_csv, docs_combates


# --------------------------------------------------------------------------
def main():
    inicio = time.time()
    print("== Bronze: extraindo das fontes (cache em dados_brutos/) ==")
    tipos = extrair_tipos()
    especies, formas = extrair_especies_e_formas()
    pokemon_csv, combates = extrair_csvs()

    print(f"== Gravando no MongoDB ({MONGO_URI}, banco {MONGO_DB}) ==")
    cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = cliente[MONGO_DB]
    for nome, docs in [("tipos", tipos), ("especies", especies), ("pokemon", formas),
                       ("pokemon_csv", pokemon_csv), ("combates", combates)]:
        gravar_colecao(db, nome, docs)
        print(f"   {nome:12s} enviados: {len(docs):6d} | na coleção: {db[nome].count_documents({}):6d}")

    print(f"== Concluído em {time.time() - inicio:.1f}s | requisições HTTP nesta execução: {requisicoes} ==")


if __name__ == "__main__":
    main()
