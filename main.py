from datetime import datetime
import requests
import sqlite3


# ==========================================
# 1. EXTRACT (Extração dos dados)
# ==========================================
def extrair_cotacao(url):
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        
        dados = resposta.json()
        cotacao_bid = float(dados["USDBRL"]["bid"])
        data_hora_atual = datetime.now().isoformat()

        # Retorna o dicionário empacotado
        return {
            "cotacao": cotacao_bid,
            "data_hora_consulta": data_hora_atual
        }

    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP: A API retornou um erro ({e})")
    except requests.exceptions.ConnectionError:
        print("Erro de Conexão: Não foi possível conectar à API. Verifique sua conexão com a internet ou a URL utilizada.")
    except KeyError as e:
        print(f"Erro de Estrutura (KeyError): A chave {e} não foi encontrada no JSON retornado pela API.")
    
    # Retorna None caso ocorra qualquer erro acima
    return None


# ==========================================
# 2. LOAD (Persistência no banco)
# ==========================================
def salvar_cotacao(registro):
    conexao = sqlite3.connect("cotacoes.db")
    cursor = conexao.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cotacao REAL NOT NULL,
            data_hora_consulta TEXT NOT NULL
        );
    """)
    
    sql = "INSERT INTO cotacoes (cotacao, data_hora_consulta) VALUES (?, ?)"
    valores = (registro["cotacao"], registro["data_hora_consulta"])
    cursor.execute(sql, valores)
    
    conexao.commit()
    conexao.close()
    print("Sucesso: Cotação salva no banco de dados!")


# ==========================================
# 3. REPORT / TRANSFORM (Análise dos dados)
# ==========================================
def gerar_relatorio():
    conexao = sqlite3.connect("cotacoes.db")
    cursor = conexao.cursor()
    
    cursor.execute("""
        SELECT id, cotacao, data_hora_consulta 
        FROM cotacoes 
        ORDER BY id DESC 
        LIMIT 2;
    """)
    
    resultados = cursor.fetchall()
    conexao.close()
    
    if len(resultados) == 0:
        print("Nenhum registro encontrado no banco de dados.")
        return

    if len(resultados) == 1:
        registro_atual = resultados[0]
        print(f"Cotação atual: R$ {registro_atual[1]:.4f} ({registro_atual[2]})")
        print("Histórico insuficiente para calcular a variação.")
        return

    atual = resultados[0]
    anterior = resultados[1]
    variacao = atual[1] - anterior[1]

    if variacao > 0:
        status = "alta"
    elif variacao < 0:
        status = "queda"
    else:
        status = "estabilidade"
    
    print("\n=== RELATÓRIO DE VARIAÇÃO ===")
    print(f"Cotação Atual (ID {atual[0]}): R$ {atual[1]:.4f} em {atual[2]}")
    print(f"Cotação Anterior (ID {anterior[0]}): R$ {anterior[1]:.4f} em {anterior[2]}")
    print(f"Variação: {variacao:+.4f} ({status})")


# ==========================================
# 4. ORQUESTRADOR (Execução Principal)
# ==========================================
def main():
    url = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
    
    # 1. Extração
    registro = extrair_cotacao(url)
    
    # 2. Salva apenas se a requisição funcionou
    if registro is not None:
        salvar_cotacao(registro)
        # 3. Exibe o relatório
        gerar_relatorio()


# Ponto de entrada do script
if __name__ == "__main__":
    main()