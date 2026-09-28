#!/usr/bin/env python3

import csv
import os
import re
import sys
import unicodedata
from pathlib import Path

import psycopg
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/pokedex")
RAIZ = Path(__file__).resolve().parent
CONCILIACAO_CSV = RAIZ / "conciliacao.csv"


TIPOS_REAIS = ["normal", "fighting", "flying", "poison", "ground", "rock", "bug", "ghost",
               "steel", "fire", "water", "grass", "electric", "psychic", "ice", "dragon",
               "dark", "fairy"]

GERACOES = [(1, "Geração I", "Kanto"), (2, "Geração II", "Johto"), (3, "Geração III", "Hoenn"),
            (4, "Geração IV", "Sinnoh"), (5, "Geração V", "Unova"), (6, "Geração VI", "Kalos")]
ROMANOS = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9}

NOME_AUSENTE = "Nome não informado"


def ler_bronze():
    cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = cliente["pokedex_bronze"]

    pokemon_csv = sorted(db.pokemon_csv.find({}), key=lambda d: int(d["#"]))
    combates = sorted(db.combates.find({}), key=lambda d: d["_linha"])
    especies = {d["id"]: d for d in db.especies.find({}, {
        "id": 1, "name": 1, "generation": 1, "habitat": 1, "color": 1, "shape": 1,
        "capture_rate": 1, "base_happiness": 1, "is_legendary": 1, "is_mythical": 1,
        "is_baby": 1, "varieties": 1})}
    formas = {d["name"]: d for d in db.pokemon.find({}, {
        "id": 1, "name": 1, "is_default": 1, "height": 1, "weight": 1,
        "abilities": 1, "species": 1, "types": 1})}
    tipos = {d["name"]: d for d in db.tipos.find({})}

    for nome, dados, esperado in [("pokemon_csv", pokemon_csv, 800), ("combates", combates, 50000),
                                  ("especies", especies, 721), ("tipos", tipos, 21)]:
        if len(dados) != esperado:
            sys.exit(f"Bronze incompleto: {nome} tem {len(dados)} documentos (esperado {esperado}). "
                     f"Execute extrair.py primeiro.")
    if not formas:
        sys.exit("Bronze incompleto: coleção 'pokemon' vazia. Execute extrair.py primeiro.")
    return pokemon_csv, combates, especies, formas, tipos


def slug(texto):
    """Normaliza um nome ao formato dos identificadores da PokéAPI:
    minúsculas, sem acento/apóstrofo/ponto, espaços -> hífen."""
    texto = texto.replace("♀", " f").replace("♂", " m")
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = texto.lower().replace("'", "").replace(".", "")
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")


EXCECOES = {
    "zygarde half forme": "zygarde-50",   
    "hoopa confined": "hoopa",            
}
SUFIXOS_RUIDO = {"forme", "form", "mode", "cloak", "size"}


def candidatos(nome):
    """Possíveis slugs da PokéAPI para um nome do CSV, do mais ao menos específico."""
    nome = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", nome).strip()      # 'DeoxysAttack Forme' -> 'Deoxys Attack Forme'
    t = nome.split()
    if t[0] in ("Mega", "Primal") and len(t) > 1:                  # 'Mega Charizard X' -> 'charizard-mega-x'
        corpo, xy = t[1:], ""
        if len(corpo) > 1 and corpo[-1] in ("X", "Y"):
            xy, corpo = "-" + corpo[-1].lower(), corpo[:-1]
        return [f"{slug(' '.join(corpo))}-{t[0].lower()}{xy}"]
    saida = []
    if len(t) == 2 and t[1] == "Rotom":                            # 'Heat Rotom' -> 'rotom-heat'
        saida.append(f"rotom-{slug(t[0])}")
    while len(t) > 1 and t[-1].lower() in SUFIXOS_RUIDO:           # 'Wormadam Plant Cloak' -> 'wormadam-plant'
        t = t[:-1]
    if len(t) > 1 and t[-1] == t[0]:                               # 'Kyurem Black Kyurem' -> 'kyurem-black'
        t = t[:-1]
    saida.append(slug(" ".join(t)))
    return saida


def achar_forma(nome, formas, especies_por_nome):
    """Devolve (slug_api, estrategia) ou (None, motivo)."""
    if not nome.strip():
        return None, "nome_ausente"
    ajustado = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", nome).strip().lower()
    if ajustado in EXCECOES and EXCECOES[ajustado] in formas:
        return EXCECOES[ajustado], "excecao_manual"
    direto = slug(nome)
    if direto in formas:
        return direto, "direto"
    for c in candidatos(nome):
        if c in formas:
            return c, "regra"
    especie = especies_por_nome.get(direto)                        # 'Basculin' -> forma padrão da espécie
    if especie:
        padrao = next((v["pokemon"]["name"] for v in especie["varieties"] if v["is_default"]), None)
        if padrao in formas:
            return padrao, "especie_padrao"
    return None, "sem_correspondencia"


def conciliar(pokemon_csv, formas, especies):
    especies_por_nome = {e["name"]: e for e in especies.values()}
    resultados, usados = {}, {}
    for r in pokemon_csv:
        idc, nome = int(r["#"]), r["Name"]
        slug_api, estrategia = achar_forma(nome, formas, especies_por_nome)
        obs = ""
        if slug_api is not None and slug_api in usados:            # duas linhas do CSV para a mesma forma
            obs = f"duplicado: a forma {slug_api} já foi associada ao registro {usados[slug_api]}"
            slug_api, estrategia = None, "duplicado"
        if slug_api is None:
            obs = obs or ("nome ausente na fonte (dado ausente); registro mantido" if not nome.strip()
                          else "sem correspondência na PokéAPI; atributos de espécie = 'Não conciliado'")
            resultados[idc] = dict(slug=None, forma=None, estrategia=estrategia, obs=obs)
            continue
        usados[slug_api] = idc
        forma = formas[slug_api]
        api_tipos = {t["type"]["name"] for t in forma["types"]}
        csv_tipos = {r["Type 1"].lower()} | ({r["Type 2"].lower()} if r["Type 2"] else set())
        resultados[idc] = dict(slug=slug_api, forma=forma, estrategia=estrategia,
                               obs="" if api_tipos == csv_tipos else
                               f"tipos divergem: API={sorted(api_tipos)} CSV={sorted(csv_tipos)}")
    return resultados


def gravar_conciliacao_csv(pokemon_csv, resultados):
    with open(CONCILIACAO_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id_csv", "nome_csv", "slug_api", "id_forma_api", "id_pokedex",
                    "estrategia", "status", "observacao"])
        for r in pokemon_csv:
            idc = int(r["#"])
            res = resultados[idc]
            forma = res["forma"]
            w.writerow([idc, r["Name"], res["slug"] or "",
                        forma["id"] if forma else "",
                        id_especie(forma) if forma else "",
                        res["estrategia"], "conciliado" if forma else "NAO_CONCILIADO", res["obs"]])


def id_especie(forma):
    return int(forma["species"]["url"].rstrip("/").split("/")[-1])


# ==========================================================================
# 3. Construção das linhas das dimensões
# ==========================================================================
def categoria_raridade(is_baby, is_legendary, is_mythical):
    """Precedência: Mítico > Lendário > Bebê > Comum."""
    if is_mythical:
        return "Mítico"
    if is_legendary:
        return "Lendário"
    if is_baby:
        return "Bebê"
    return "Comum"


COLUNAS_POKEMON = [
    "id_csv", "id_pokedex", "id_forma_api", "nome", "nome_api", "membro_especial", "conciliado",
    "tipo_forma", "categoria_raridade", "tipo_primario", "tipo_secundario", "geracao_numero",
    "hp", "ataque", "defesa", "ataque_especial", "defesa_especial", "velocidade",
    "habitat", "cor", "forma_corporal", "taxa_captura", "felicidade_base",
    "altura_m", "peso_kg", "qtd_habilidades"]


def linhas_dim_pokemon(pokemon_csv, resultados, especies, nomes_tipo_validos):
    linhas, div_geracao = [], 0
    for r in pokemon_csv:
        idc = int(r["#"])
        res = resultados[idc]
        forma = res["forma"]
        sem_nome = not r["Name"].strip()
        t1 = r["Type 1"].capitalize()
        t2 = r["Type 2"].capitalize() if r["Type 2"] else "Nenhum"
        for t in (t1, t2):
            if t not in nomes_tipo_validos:
                sys.exit(f"Tipo desconhecido no CSV: {t!r} (registro {idc})")
        ger_csv = int(r["Generation"])
        lendario_csv = r["Legendary"].strip().lower() == "true"
        stats = [int(r[c]) for c in ("HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed")]

        if forma:
            esp = especies[id_especie(forma)]                     # atributos de espécie HERDADOS
            geracao = ROMANOS[esp["generation"]["name"].split("-")[-1]]
            div_geracao += geracao != ger_csv
            if esp["habitat"]:
                habitat = esp["habitat"]["name"]
            else:                                                 # nulo: ausente ou inaplicável?
                habitat = "Não se aplica" if geracao > 3 else "Não informado"
            especie_attr = (
                habitat,
                esp["color"]["name"] if esp["color"] else "Não informado",
                esp["shape"]["name"] if esp["shape"] else "Não informado",
                esp["capture_rate"], esp["base_happiness"])
            raridade = categoria_raridade(esp["is_baby"], esp["is_legendary"], esp["is_mythical"])
            atrib_forma = (forma["height"] / 10, forma["weight"] / 10, len(forma["abilities"]))
            ids = (id_especie(forma), forma["id"], res["slug"], True,
                   "Padrão" if forma["is_default"] else "Alternativa")
        else:
            geracao = ger_csv
            especie_attr = ("Não conciliado", "Não conciliado", "Não conciliado", None, None)
            raridade = "Lendário" if lendario_csv else "Comum"     # sem espécie: recorre ao CSV
            atrib_forma = (None, None, None)
            ids = (None, None, None, False, "Não conciliado")

        linhas.append((idc, ids[0], ids[1], NOME_AUSENTE if sem_nome else r["Name"], ids[2],
                       sem_nome, ids[3], ids[4], raridade, t1, t2, geracao, *stats,
                       *especie_attr, *atrib_forma))
    return linhas, div_geracao


def multiplicadores_de_tipo(tipos):
    """(atacante, defensor) -> fator, para os 18 x 18 tipos reais.
    O JSON só lista as exceções; toda combinação não listada vale 1."""
    reais = set(TIPOS_REAIS)
    m = {(a, d): 1.0 for a in TIPOS_REAIS for d in TIPOS_REAIS}
    for a in TIPOS_REAIS:
        rel = tipos[a]["damage_relations"]
        for chave, fator in (("double_damage_to", 2.0), ("half_damage_to", 0.5), ("no_damage_to", 0.0)):
            for alvo in rel[chave]:
                if alvo["name"] in reais:
                    m[(a, alvo["name"])] = fator
    # conferência cruzada: as listas *_from devem ser o espelho das *_to
    divergencias = 0
    for d in TIPOS_REAIS:
        rel = tipos[d]["damage_relations"]
        for chave, fator in (("double_damage_from", 2.0), ("half_damage_from", 0.5), ("no_damage_from", 0.0)):
            for origem in rel[chave]:
                if origem["name"] in reais and m[(origem["name"], d)] != fator:
                    divergencias += 1
    return m, divergencias


# ==========================================================================
# 4. Carga
# ==========================================================================
SQL_FATO = """
INSERT INTO silver.fato_confronto (
    combate_id, atacou_primeiro, pokemon_sk, oponente_sk,
    tipo_primario_sk, tipo_secundario_sk, oponente_tipo_primario_sk, oponente_tipo_secundario_sk,
    geracao_sk, venceu, velocidade, velocidade_oponente, diferenca_velocidade, multiplicador_efetivo)
SELECT c.combate_id, c.atacou_primeiro, p.pokemon_sk, o.pokemon_sk,
       tp1.tipo_sk, tp2.tipo_sk, ot1.tipo_sk, ot2.tipo_sk,
       g.geracao_sk,
       (c.id_a = c.id_vencedor)::int,
       p.velocidade, o.velocidade, p.velocidade - o.velocidade,
       e1.multiplicador * COALESCE(e2.multiplicador, 1)       -- sem 2º tipo no oponente: fator 1
FROM (
      SELECT combate_id, id_primeiro AS id_a, id_segundo  AS id_b, id_vencedor, 1 AS atacou_primeiro FROM stg_combate
      UNION ALL
      SELECT combate_id, id_segundo,          id_primeiro,         id_vencedor, 0                    FROM stg_combate
     ) c
JOIN silver.dim_pokemon p   ON p.id_csv  = c.id_a
JOIN silver.dim_pokemon o   ON o.id_csv  = c.id_b
JOIN silver.dim_tipo tp1    ON tp1.nome  = p.tipo_primario
JOIN silver.dim_tipo tp2    ON tp2.nome  = p.tipo_secundario
JOIN silver.dim_tipo ot1    ON ot1.nome  = o.tipo_primario
JOIN silver.dim_tipo ot2    ON ot2.nome  = o.tipo_secundario
JOIN silver.dim_geracao g   ON g.numero  = p.geracao_numero
JOIN silver.efetividade_tipo e1 ON e1.atacante_sk = tp1.tipo_sk AND e1.defensor_sk = ot1.tipo_sk
LEFT JOIN silver.efetividade_tipo e2 ON e2.atacante_sk = tp1.tipo_sk AND e2.defensor_sk = ot2.tipo_sk
ORDER BY c.combate_id, c.atacou_primeiro DESC
"""


def main():
    print("== Silver: lendo da camada bronze (MongoDB) ==")
    pokemon_csv, combates, especies, formas, tipos = ler_bronze()

    print("== Conciliando chaves (CSV '#' <-> PokéAPI) por nome ==")
    resultados = conciliar(pokemon_csv, formas, especies)
    gravar_conciliacao_csv(pokemon_csv, resultados)
    n_ok = sum(1 for r in resultados.values() if r["forma"])
    print(f"   conciliados: {n_ok}/{len(pokemon_csv)} | não conciliados: {len(pokemon_csv) - n_ok}"
          f"  (relatório: {CONCILIACAO_CSV.name})")
    for idc, r in resultados.items():
        if not r["forma"]:
            nome = next(x["Name"] for x in pokemon_csv if int(x["#"]) == idc) or "<sem nome>"
            print(f"     - #{idc} {nome}: {r['obs']}")

    matriz, div_efet = multiplicadores_de_tipo(tipos)
    nomes_tipo = {t.capitalize() for t in TIPOS_REAIS} | {"Nenhum"}
    linhas_pokemon, div_geracao = linhas_dim_pokemon(pokemon_csv, resultados, especies, nomes_tipo)

    ids_validos = {int(r["#"]) for r in pokemon_csv}
    linhas_combate = []
    for c in combates:
        a, b, v = int(c["First_pokemon"]), int(c["Second_pokemon"]), int(c["Winner"])
        if a not in ids_validos or b not in ids_validos or v not in (a, b):
            sys.exit(f"Combate inconsistente na linha {c['_linha']}: {a} x {b}, vencedor {v}")
        linhas_combate.append((c["_linha"], a, b, v))

    print("== Gravando no PostgreSQL (uma transação) ==")
    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute((RAIZ / "sql" / "silver.sql").read_text(encoding="utf-8"))

            cur.executemany("INSERT INTO silver.dim_geracao (numero, nome, regiao) VALUES (%s, %s, %s)",
                            GERACOES)

            cur.executemany("INSERT INTO silver.dim_tipo (id_tipo_api, nome) VALUES (%s, %s)",
                            [(tipos[t]["id"], t.capitalize()) for t in TIPOS_REAIS])
            cur.execute("INSERT INTO silver.dim_tipo (id_tipo_api, nome, membro_especial) "
                        "VALUES (NULL, 'Nenhum', true)")

            cur.executemany(
                "INSERT INTO silver.efetividade_tipo (atacante_sk, defensor_sk, multiplicador) "
                "SELECT a.tipo_sk, d.tipo_sk, %s FROM silver.dim_tipo a, silver.dim_tipo d "
                "WHERE a.nome = %s AND d.nome = %s",
                [(f, a.capitalize(), d.capitalize()) for (a, d), f in matriz.items()])

            cur.executemany(
                f"INSERT INTO silver.dim_pokemon ({', '.join(COLUNAS_POKEMON)}) "
                f"VALUES ({', '.join(['%s'] * len(COLUNAS_POKEMON))})", linhas_pokemon)

            cur.execute("CREATE TEMP TABLE stg_combate (combate_id integer, id_primeiro integer, "
                        "id_segundo integer, id_vencedor integer) ON COMMIT DROP")
            with cur.copy("COPY stg_combate (combate_id, id_primeiro, id_segundo, id_vencedor) "
                          "FROM STDIN") as cp:
                for linha in linhas_combate:
                    cp.write_row(linha)
            cur.execute(SQL_FATO)

            # ---- verificações: falha => rollback de toda a carga ----
            cur.execute("SELECT count(*), count(DISTINCT combate_id), sum(venceu) FROM silver.fato_confronto")
            n_fato, n_combates, n_vitorias = cur.fetchone()
            if n_fato != 2 * len(combates) or n_combates != len(combates) or n_vitorias != len(combates):
                raise RuntimeError(f"Fato inconsistente: {n_fato} linhas, {n_combates} combates, "
                                   f"{n_vitorias} vitórias (esperado {2 * len(combates)}, "
                                   f"{len(combates)}, {len(combates)}).")

            print("== Contagem de linhas por tabela ==")
            for tabela in ("dim_geracao", "dim_tipo", "efetividade_tipo", "dim_pokemon", "fato_confronto"):
                cur.execute(f"SELECT count(*) FROM silver.{tabela}")
                print(f"   silver.{tabela:18s} {cur.fetchone()[0]:>8d}")

    print(f"   conferências: divergências de efetividade (_to x _from) = {div_efet}; "
          f"geração CSV x API divergente em {div_geracao} registros")
    print("== Silver concluído ==")


if __name__ == "__main__":
    main()
