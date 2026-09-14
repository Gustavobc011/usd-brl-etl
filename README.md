# 💱 Automação de Cotação USD-BRL (ETL em Python)

Automação que coleta a cotação do dólar em tempo real, armazena o histórico em banco de dados e gera um relatório comparando a variação entre a última e a penúltima consulta.

Projeto desenvolvido para praticar o fluxo completo de um pipeline de dados (**Extract, Transform, Load**) com Python puro, tratamento de erros e persistência em banco relacional.

## 🎯 Objetivo

Automatizar uma tarefa que, no dia a dia, seria manual e repetitiva: consultar a cotação do dólar e comparar com a consulta anterior para saber se houve alta, queda ou estabilidade — útil para quem acompanha câmbio com frequência (finanças pessoais, compras internacionais, controle de custos, etc.).

## ⚙️ Como funciona

O projeto segue uma arquitetura ETL simples, dividida em 4 etapas dentro de `main.py`:

### 1. Extract — `extrair_cotacao(url)`
Busca a cotação atual do dólar na [AwesomeAPI](https://economia.awesomeapi.com.br/), trata a resposta e converte os dados relevantes.
- Tratamento de `HTTPError`, `ConnectionError` e `KeyError`, para lidar com falhas de rede, API fora do ar ou mudanças na estrutura do JSON retornado.

### 2. Load — `salvar_cotacao(registro)`
Persiste o registro coletado em um banco SQLite (`cotacoes.db`), criando a tabela automaticamente caso não exista.
- Uso de placeholders (`?`) nas queries para evitar SQL Injection.

```sql
CREATE TABLE IF NOT EXISTS cotacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotacao REAL NOT NULL,
    data_hora_consulta TEXT NOT NULL
);
```

### 3. Report — `gerar_relatorio()`
Consulta as duas últimas cotações salvas, calcula a variação entre elas e classifica o resultado como **alta**, **queda** ou **estabilidade**. Também trata os casos de banco vazio ou com apenas um registro.

### 4. Orquestrador — `main()`
Executa o fluxo completo: Extract → Load → Report, na ordem correta, garantindo que só grava e gera relatório se a extração foi bem-sucedida.

## 🖥️ Exemplo de execução

```text
Sucesso: Cotação salva no banco de dados!

=== RELATÓRIO DE VARIAÇÃO ===
Cotação Atual (ID 6): R$ 5.1461 em 2026-09-14T19:00:42.723776
Cotação Anterior (ID 5): R$ 5.1012 em 2026-09-11T01:09:34.765918
Variação: +0.0449 (alta)
```

## 🛠️ Tecnologias utilizadas

- **Python 3**
- **requests** — consumo da API
- **sqlite3** — persistência dos dados (biblioteca nativa do Python)
- **datetime** — registro de data/hora de cada consulta

## 🚀 Como executar o projeto

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/automacao-cotacao.git
cd automacao-cotacao

# Crie e ative um ambiente virtual
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac

# Instale as dependências
pip install -r requirements.txt

# Execute
python main.py
```

> A automação roda sob demanda (execução manual), não em agendamento automático.

## 📁 Estrutura do projeto

```text
automacao_cotacao/
├── main.py             # Extract, Load, Report e orquestrador
├── requirements.txt    # Dependências do projeto
├── .gitignore
└── README.md
```

> O arquivo `cotacoes.db` não é versionado (está no `.gitignore`), pois é gerado automaticamente na primeira execução.

## 🔜 Próximos passos

Este projeto é a base de dados para um projeto seguinte: um **dashboard de visualização** (Python/Streamlit e Power BI) construído sobre o histórico de cotações coletado aqui.

## 👤 Autor

**Gustavo**
Estudante de Análise e Desenvolvimento de Sistemas (Uninove)
