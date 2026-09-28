# Ciência de Dados — EP01: ETL e Arquitetura Medalhão

## Integrantes do Grupo

- **Lucas Pinheiro da Costa**


---

## 1. Visão Geral do Projeto

Este projeto implementa um pipeline de dados analítico de ponta a ponta fundamentado na **Arquitetura Medalhão** (*Medallion Architecture*), processando e reconciliando dados de duas fontes públicas com características distintas:
1. **PokéAPI (REST/JSON):** Detalha a classificação e atributos físicos/mecânicos de Pokémon, espécies e mecânicas de tipo.
2. **Dataset de Batalhas (CSVs):** Arquivos `pokemon.csv` (800 registros de cadastro) e `combats.csv` (50.000 confrontos simulados).

- **🥉 Bronze (MongoDB):** Dados brutos ingeridos sem transformação a partir da PokéAPI (`extrair.py`).
- **🥈 Silver (PostgreSQL):** Modelo dimensional em esquema estrela, com conciliação de chaves e tratamento de ausências (`carregar.py`).
- **🥇 Gold (PostgreSQL):** Tabelas agregadas no grão das perguntas de negócio para consumo analítico direto (`publicar.py`).

---

## 2. Justificativa Tecnológica da Camada Bronze (MongoDB)

A camada **Bronze** tem como premissa a imutabilidade e a preservação fidedigna do dado bruto entregue pela fonte original, sem conversões de tipo, renomeações de colunas, descartes de campos ou achatamento de estruturas hierárquicas.

A escolha de um **banco orientado a documentos (MongoDB)** para a camada Bronze, em detrimento de um banco relacional, decorre diretamente da natureza estrutural dos dados retornados pela PokéAPI:
- **Hierarquias Profundamente Aninhadas:** A resposta de `/pokemon/{id}` contém subdocumentos aninhados (`types`, `stats`, `abilities`, `species`, etc.). Em um modelo relacional, armazenar o dado bruto sem transformação exigiria a normalização forçada em dezenas de tabelas associativas ou o uso de colunas textuais opacas (`JSONB`), o que viola a proposta de manter a representação natural da entidade.
- **Estruturas de Coleção Variáveis:** No endpoint `/pokemon-species/{id}`, o campo `varieties[]` possui tamanho heterogêneo por espécie (espécies sem formas alternativas possuem 1 item; Charizard possui 3; outras dezenas). Bancos de documentos acomodam listas de subdocumentos nativamente.
- **Campos de Dicionário Dinâmico:** O endpoint `/type/{id}` estrutura as relações de combate em um objeto `damage_relations` com seis listas dinâmicas (`double_damage_to`, `half_damage_to`, `no_damage_to`, etc.). O MongoDB preserva a integridade original dessa árvore JSON.
- **Rastreabilidade e Linhagem sem Efeito Colateral:** O MongoDB permite anexar metadados de governança (`_id`, `_fonte`, `_url`, `_ingerido_em`) no nível raiz do documento sem interferir no conteúdo entregue pela fonte.
- **Preservação de Colunas Não Convencionais no CSV:** O arquivo `pokemon.csv` contém colunas com pontos e espaços (ex.: `Sp. Atk`, `Sp. Def`, `#`). No MongoDB (versão 5.0+), essas chaves são preservadas como strings literais via operações `ReplaceOne`, evitando colisões de tipagem do PostgreSQL nesta fase.

---

## 3. Instruções de Execução

### Pré-requisitos
- Python 3.10 ou superior.
- Docker e Docker Compose (ou MongoDB e PostgreSQL instalados localmente / VM).
- Dependências instaladas:
  ```bash
  pip install -r requirements.txt
  ```

### 3.1 Inicialização dos Bancos de Dados (Docker Compose)
O enunciado permite o uso de contêineres, máquina virtual da disciplina ou instalação local, desde que o procedimento esteja documentado. 

Para maior comodidade, reprodutibilidade e isolamento, disponibilizamos o arquivo `docker-compose.yml`. Para subir os dois bancos configurados e prontos para uso:

```bash
docker compose up -d
```

- **MongoDB 7:** Disponível em `127.0.0.1:27017` (banco `pokedex_bronze`).
- **PostgreSQL 16:** Disponível em `127.0.0.1:5432` (usuário: `postgres`, senha: `postgres`, banco: `pokedex`).
- **Segurança da Rede:** As portas foram vinculadas estritamente ao endereço de loopback local (`127.0.0.1`), garantindo que nenhuma porta fique exposta à rede externa ou ao Wi-Fi.

*(Para desligar os contêineres após a execução do trabalho: `docker compose down`)*.

Caso utilize a **máquina virtual da disciplina** ou instalação local, basta certificar-se de que os serviços do `mongod` e `postgresql` estão ativos nas portas padrão.

### 3.2 Variáveis de Ambiente (Opcionais)
Caso os serviços estejam em portas ou credenciais diferentes das padrões:
```bash
export MONGO_URI="mongodb://localhost:27017"
export POSTGRES_DSN="postgresql://postgres:postgres@localhost:5432/pokedex"
```

### Ordem de Execução do Pipeline

```bash
# 1. Extração: Baixa os dados brutos (com cache em dados_brutos/) e grava no MongoDB (pokedex_bronze)
python extrair.py

# 2. Carga: Lê do MongoDB, executa silver.sql, concilia entidades, popula PostgreSQL e gera conciliacao.csv
python carregar.py

# 3. Publicação: Executa gold.sql e agrega os dados inteiramente dentro do PostgreSQL
python publicar.py
```

### Consultas Analíticas
As consultas das 8 análises estão consolidadas no arquivo `sql/consultas.sql`. Podem ser executadas via terminal ou interface SQL:
```bash
psql -d pokedex -f sql/consultas.sql
```

---

## 4. Idempotência do Pipeline

O pipeline foi projetado para admitir execução repetida em qualquer camada sem duplicação de dados e sem alteração do estado final obtido na primeira execução:

1. **Camada Bronze (`extrair.py`):**
   - **Cache Local:** Antes de tocar a rede, verifica a existência do arquivo em `dados_brutos/`. A segunda execução realiza **zero requisições HTTP**.
   - **Linhagem e Upsert:** O campo `_ingerido_em` é indexado pela data de modificação estável do arquivo de cache. A gravação no MongoDB utiliza `ReplaceOne` com `upsert=True` e `_id` determinístico derivado da chave natural (`pokemon/25`, `especie/25`, `tipo/1`, `pokemon_csv/1`, `combate/1`). Execuções sucessivas substituem os documentos sem alterar a contagem total.

2. **Camada Silver (`carregar.py`):**
   - O script executa `sql/silver.sql`, que inicia com `DROP SCHEMA IF EXISTS silver CASCADE; CREATE SCHEMA silver;`.
   - Toda a carga dimensional e a geração da tabela fato ocorrem em **uma única transação ACID**. Se houver falha, ocorre rollback completo; se bem-sucedido, o estado do schema é reconstruído de forma determinística e limpa.
   - Não acessa a internet nem lê arquivos originais: opera 100% desconectado a partir do MongoDB.

3. **Camada Gold (`publicar.py`):**
   - O script executa `sql/gold.sql`, que aplica `TRUNCATE` em todas as tabelas agregadas e as repopula via comandos `INSERT INTO gold.<tabela> SELECT ... FROM silver.<tabela>`.
   - Registra a contagem de linhas e o carimbo de publicação na tabela `gold.log_publicacao`.

---

## 5. Camada Silver: Modelo Dimensional

### Frase do Grão (RS1)
> **"Uma linha da tabela fato `silver.fato_confronto` representa a participação individual de um Pokémon em um combate específico: o combatente em foco, o oponente enfrentado, seus papéis contextuais de combate e o desfecho binário de vitória (1) ou derrota (0)."**

Cada combate registrado no CSV gera **duas linhas** na tabela fato (uma para cada combatente participante). Assim, os 50.000 combates resultam rigorosamente em **100.000 linhas**.

### Diagrama do Esquema Estrela (RS2)

```
                    ┌──────────────────┐
                    │   dim_geracao    │
                    └────────┬─────────┘
                             │
   ┌──────────────┐   ┌───────┴────────┐   ┌──────────────┐
   │ dim_pokemon  ├───┤ fato_confronto ├───┤   dim_tipo   │
   └──────────────┘   └───────┬────────┘   └──────────────┘
                             │
                   ┌──────────┴──────────┐
                   │  efetividade_tipo   │
                   └─────────────────────┘
```

A tabela central `silver.fato_confronto` conecta-se diretamente às suas dimensões conformadas e papéis:
- **`dim_pokemon`**: Referenciada duas vezes via chaves substitutas para o combatente em foco (`pokemon_sk`) e para o adversário (`oponente_sk`).
- **`dim_tipo`**: Referenciada para o tipo primário e secundário de ambos os lados.
- **`dim_geracao`**: Referenciada para a geração do Pokémon em foco.
- **`efetividade_tipo`**: Matriz de domínio 18×18 materializada para relacionar as vantagens de tipo em SQL.

---

## 6. As Seis Decisões de Modelagem (Seção 4.2)

### Decisão 1: Grão da Tabela Fato
- **Decisão:** Adotou-se o grão de **participação individual no combate** (2 linhas por combate, totalizando 100.000 linhas na tabela fato).
- **Justificativa:** No grão de combate (1 linha por confronto, 50.000 linhas), cada Pokémon pode figurar ora na coluna de primeiro combatente, ora na coluna de segundo. Calcular a taxa de vitórias (*winrate*) exigiria unir via `UNION ALL` ambas as colunas ou redigir expressões condicionais complexas com alto risco de dupla contagem. Com o grão de participação, o cálculo da taxa de vitórias reduz-se a uma média aritmética direta: `AVG(venceu)`.
- **Custos:** O custo é a duplicação do volume de registros da tabela fato (100.000 linhas vs. 50.000), amplamente compensado pela simplicidade e velocidade das consultas analíticas e pela eliminação de junções cruzadas.

### Decisão 2: Representação da Comparação Entre os Lados
- **Decisão:** Gravou-se a métrica `diferenca_velocidade` diretamente na tabela fato durante a carga do Silver (`velocidade - velocidade_oponente`), além de manter as métricas pontuais `velocidade` e `velocidade_oponente`.
- **Justificativa:** A Análise 5 exige agrupar confrontos por faixas de diferença de velocidade. Calcular essa diferença em tempo de execução para 100.000 linhas a cada consulta penaliza o tempo de resposta do PostgreSQL. O pré-cálculo garante que as agregações da camada Gold sejam executadas de maneira direta e vetorial.
- **Custos:** Consumo adicional de bytes por linha no disco, justificável pela economia computacional em leitura analítica.

### Decisão 3: Representação da Efetividade de Tipos
- **Decisão:** Criação da tabela de domínio `silver.efetividade_tipo` (matriz 18x18 = 324 pares) e cálculo antecipado do `multiplicador_efetivo` composto na linha da fato.
- **Justificativa:** O dano de combate depende do tipo atacante contra o tipo defensor. Quando o oponente possui dois tipos, os multiplicadores se multiplicam (ex.: Ground contra Fire/Flying = 2.0 × 0.0 = 0.0). A coluna `multiplicador_efetivo` armazena o produto exato ($E_1 \times E_2$, assumindo 1 quando não há segundo tipo), assumindo os valores `0, 0.25, 0.5, 1, 2 ou 4`. A tabela `efetividade_tipo` é mantida para possibilitar a Análise 7 em puro SQL via junção.
- **Custos:** O custo é o join prévio com a tabela de tipos na fase de ingestão do Silver, economizando múltiplas operações de produto cartesiano na Gold.

### Decisão 4: Representação do Oponente (Dimensão Papel)
- **Decisão:** O oponente é modelado como uma **dimensão papel** (*role-playing dimension*). A mesma dimensão física `silver.dim_pokemon` é referenciada duas vezes na tabela fato: através da FK `pokemon_sk` (combatente em foco) e da FK `oponente_sk` (combatente adversário).
- **Justificativa:** Ambas as entidades compartilham rigorosamente os mesmos atributos de cadastro. Criar uma dimensão separada "dim_oponente" violaria o princípio de conformidade dimensional e duplicaria tabelas desnecessariamente.
- **Custos:** Exige o uso de aliases claros (`p` e `o`) em consultas que inspecionam ambos os combatentes simultaneamente.

### Decisão 5: Localização dos Atributos de Status
- **Decisão:** Os status base (`hp`, `ataque`, `defesa`, `ataque_especial`, `defesa_especial`, `velocidade`) foram centralizados na dimensão `silver.dim_pokemon`. Apenas os status ativamente comparados no combate (`velocidade` e `velocidade_oponente`) foram redundados na tabela fato como métricas numéricas.
- **Justificativa:** Os status descrevem a entidade estática (Pokémon), cabendo naturalmente na dimensão. As Análises 1 e 2 operam exclusivamente sobre a dimensão. A redundância seletiva da velocidade na fato atende à necessidade operacional da Análise 5 sem inchar a fato com todos os outros status.
- **Custos:** Pequena redundância de armazenamento para as colunas de velocidade.

### Decisão 6: Derivação da Categoria de Raridade
- **Decisão:** A categoria de raridade foi derivada na carga do Silver como coluna persistida `categoria_raridade` em `silver.dim_pokemon`, sob a seguinte precedência estrita:
  $$\text{Mítico} > \text{Lendário} > \text{Bebê} > \text{Comum}$$
- **Justificativa:** A PokéAPI discrimina `is_mythical`, `is_legendary` e `is_baby`, enquanto o CSV classifica tudo como `Legendary: True/False`. Derivar e categorizar durante a carga garante consistência taxonômica global e evita expressões condicionais repetidas (`CASE WHEN`) nas camadas Gold e analítica.
- **Custos:** Custo único de processamento condicional na execução do `carregar.py`.

---

## 7. Decisões de Projeto Adicionais

### Tratamento dos Três Problemas Conhecidos da Fonte
1. **Problema 1 (Chave `#` sequencial no CSV não corresponde à Pokédex):**
   - Conciliação realizada por nome através da função `slug()`, tratando sufixos de ruído (`Forme`, `Cloak`, `Mode`), inversão de padrões (`Mega Charizard X` $\rightarrow$ `charizard-mega-x`), e dicionário de exceções explícitas (`zygarde half forme` $\rightarrow$ `zygarde-50`; `hoopa confined` $\rightarrow$ `hoopa`). As chaves naturais de ambas as origens (`id_csv`, `id_pokedex`, `id_forma_api`) são preservadas na dimensão para auditoria.
2. **Problema 2 (Linha 63 sem nome no CSV — Dado Ausente):**
   - Configura um **dado ausente**: a entidade existe e batalha, mas o nome foi omitido. O registro foi cadastrado como **membro especial** na dimensão: `membro_especial = true`, `nome = 'Nome não informado'`, `tipo_forma = 'Não conciliado'`, `conciliado = false`. Todos os seus combates foram integralmente mantidos na fato, respeitando o princípio de que nenhum combate pode ser descartado (50.000 combates = 100.000 participações).
3. **Problema 3 (Campo `habitat` nulo na PokéAPI — Conceito Inaplicável vs. Ausente):**
   - O conceito de habitat só foi mantido nos jogos até a Geração III. Portanto, para espécies com geração $> 3$, o valor nulo foi imputado como `'Não se aplica'` (**conceito inaplicável**). Para espécies de gerações I a III sem habitat registrado, foi imputado como `'Não informado'` (**dado ausente**). Essa distinção semântica atende ao requisito conceitual da modelagem.

### Filtragem dos Tipos Não Reais da PokéAPI
- O endpoint `/type/` entrega 21 tipos. Os identificadores `stellar` (19), `unknown` (10001) e `shadow` (10002) foram mantidos intactos na camada Bronze (atendendo à regra de não transformação), mas **filtrados na camada Silver**, que contém exatamente os **18 tipos canônicos** das Gerações I a VI mais o membro especial `'Nenhum'`. Essa filtragem é justificada porque esses tipos não existem nos jogos que geraram o arquivo de combates, viabilizando a matriz simétrica canônica de 18×18 (324 posições).

### Herança de Atributos de Espécie para Formas Alternativas
- Formas alternativas (ex.: Megas, Primal, Therian) possuem IDs $> 10000$ em `/pokemon/`, mas não possuem registro próprio em `/pokemon-species/`. Na carga do Silver, o script identifica a URL da espécie pai no campo `species.url` da forma e herda seus atributos canônicos: `geracao`, `habitat`, `cor`, `forma_corporal`, `taxa_captura` e `felicidade_base`.

### Ausência de Chave Estrangeira Nula (RS4)
- Na tabela `silver.dim_tipo`, foi inserido um registro dedicado com `tipo_sk` de chave substituta, `id_tipo_api = NULL`, `nome = 'Nenhum'` e `membro_especial = true`. Pokémon monotype apontam seu `tipo_secundario_sk` para este registro, garantindo total integridade referencial com zero FKs nulas na tabela fato.

---

## 8. Análise 8 (Proposta pelo Grupo)

- **Pergunta de Negócio:** *"Pokémon lendários, míticos e formas alternativas possuem taxa de vitórias estatisticamente superior aos comuns? E a iniciativa do combate (atacar primeiro) é capaz de mitigar a desvantagem biológica de um Pokémon comum?"*
- **Relevância:** Avaliar o balanceamento competitivo entre o poder inerente de raridade/formas especiais e a mecânica situacional de iniciativa no turno.
- **Capacidade Exigida do Modelo:** Esta análise exige o cruzamento dimensional de atributos de classificação consolidados na `silver.dim_pokemon` (`categoria_raridade` derivada e `tipo_forma` — Padrão vs. Alternativa) com a métrica da fato `atacou_primeiro`, originada na coluna `First_pokemon` do CSV de combates, elemento que as análises obrigatórias 3 a 7 não exploram.
- **Materialização na Camada Gold:** A pergunta é atendida diretamente pela tabela `gold.taxa_vitorias_por_raridade`.
