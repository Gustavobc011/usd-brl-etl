import sqlite3
from datetime import datetime

import pytest
import requests

import main


URL_TESTE = "https://api.exemplo.com/USD-BRL"


# ==========================================
# Fixtures e utilitários
# ==========================================
@pytest.fixture(autouse=True)
def pasta_temporaria(tmp_path, monkeypatch):
    """Roda cada teste numa pasta vazia, para o cotacoes.db real nunca ser tocado."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class RespostaFalsa:
    """Imita o objeto Response do requests com o mínimo que o main.py usa."""

    def __init__(self, dados=None, status_code=200):
        self._dados = dados
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Server Error")

    def json(self):
        return self._dados


def simular_api(monkeypatch, resposta=None, erro=None):
    """Troca requests.get por uma função falsa. Guarda as URLs chamadas."""
    chamadas = []

    def get_falso(url, *args, **kwargs):
        chamadas.append(url)
        if erro is not None:
            raise erro
        return resposta

    monkeypatch.setattr(main.requests, "get", get_falso)
    return chamadas


def ler_cotacoes():
    conexao = sqlite3.connect("cotacoes.db")
    linhas = conexao.execute(
        "SELECT id, cotacao, data_hora_consulta FROM cotacoes ORDER BY id"
    ).fetchall()
    conexao.close()
    return linhas


def criar_tabela_vazia():
    conexao = sqlite3.connect("cotacoes.db")
    conexao.execute("""
        CREATE TABLE cotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cotacao REAL NOT NULL,
            data_hora_consulta TEXT NOT NULL
        );
    """)
    conexao.commit()
    conexao.close()


# ==========================================
# 1. extrair_cotacao
# ==========================================
def test_extrair_cotacao_resposta_valida(monkeypatch):
    simular_api(monkeypatch, RespostaFalsa({"USDBRL": {"bid": "5.1461"}}))

    registro = main.extrair_cotacao(URL_TESTE)

    assert registro["cotacao"] == 5.1461
    assert isinstance(registro["cotacao"], float)
    # Não lança erro se a data estiver em formato ISO válido
    datetime.fromisoformat(registro["data_hora_consulta"])


def test_extrair_cotacao_usa_url_recebida(monkeypatch):
    chamadas = simular_api(monkeypatch, RespostaFalsa({"USDBRL": {"bid": "5.0"}}))

    main.extrair_cotacao(URL_TESTE)

    assert chamadas == [URL_TESTE]


def test_extrair_cotacao_erro_http(monkeypatch, capsys):
    simular_api(monkeypatch, RespostaFalsa(status_code=500))

    assert main.extrair_cotacao(URL_TESTE) is None
    assert "Erro HTTP" in capsys.readouterr().out


def test_extrair_cotacao_sem_conexao(monkeypatch, capsys):
    simular_api(monkeypatch, erro=requests.exceptions.ConnectionError())

    assert main.extrair_cotacao(URL_TESTE) is None
    assert "Erro de Conexão" in capsys.readouterr().out


@pytest.mark.parametrize(
    "json_invalido",
    [
        {},                            # sem a chave USDBRL
        {"USDBRL": {}},                # sem a chave bid
        {"EURBRL": {"bid": "6.0"}},    # moeda diferente
    ],
)
def test_extrair_cotacao_json_sem_chave(monkeypatch, capsys, json_invalido):
    simular_api(monkeypatch, RespostaFalsa(json_invalido))

    assert main.extrair_cotacao(URL_TESTE) is None
    assert "KeyError" in capsys.readouterr().out


# ==========================================
# 2. salvar_cotacao
# ==========================================
def test_salvar_cotacao_cria_tabela_e_grava(capsys):
    main.salvar_cotacao({"cotacao": 5.1461, "data_hora_consulta": "2026-09-14T19:00:00"})

    assert ler_cotacoes() == [(1, 5.1461, "2026-09-14T19:00:00")]
    assert "Sucesso" in capsys.readouterr().out


def test_salvar_cotacao_acumula_registros():
    main.salvar_cotacao({"cotacao": 5.10, "data_hora_consulta": "2026-09-14T10:00:00"})
    main.salvar_cotacao({"cotacao": 5.20, "data_hora_consulta": "2026-09-14T11:00:00"})

    linhas = ler_cotacoes()
    assert [linha[0] for linha in linhas] == [1, 2]
    assert [linha[1] for linha in linhas] == [5.10, 5.20]


# ==========================================
# 3. gerar_relatorio
# ==========================================
def test_gerar_relatorio_banco_vazio(capsys):
    criar_tabela_vazia()

    main.gerar_relatorio()

    assert "Nenhum registro encontrado" in capsys.readouterr().out


def test_gerar_relatorio_um_registro(capsys):
    main.salvar_cotacao({"cotacao": 5.1461, "data_hora_consulta": "2026-09-14T19:00:00"})
    capsys.readouterr()  # descarta a mensagem do salvar

    main.gerar_relatorio()

    saida = capsys.readouterr().out
    assert "R$ 5.1461" in saida
    assert "Histórico insuficiente" in saida


@pytest.mark.parametrize(
    "anterior, atual, variacao_esperada, status",
    [
        (5.1012, 5.1461, "+0.0449", "alta"),
        (5.2000, 5.1500, "-0.0500", "queda"),
        (5.1000, 5.1000, "+0.0000", "estabilidade"),
    ],
)
def test_gerar_relatorio_variacao(capsys, anterior, atual, variacao_esperada, status):
    main.salvar_cotacao({"cotacao": anterior, "data_hora_consulta": "2026-09-14T10:00:00"})
    main.salvar_cotacao({"cotacao": atual, "data_hora_consulta": "2026-09-14T11:00:00"})
    capsys.readouterr()

    main.gerar_relatorio()

    saida = capsys.readouterr().out
    assert f"Cotação Atual (ID 2): R$ {atual:.4f}" in saida
    assert f"Cotação Anterior (ID 1): R$ {anterior:.4f}" in saida
    assert f"Variação: {variacao_esperada} ({status})" in saida


# ==========================================
# 4. main (orquestrador)
# ==========================================
def test_main_sucesso_salva_e_gera_relatorio(monkeypatch):
    registro = {"cotacao": 5.0, "data_hora_consulta": "2026-09-14T10:00:00"}
    ordem = []
    monkeypatch.setattr(main, "extrair_cotacao", lambda url: registro)
    monkeypatch.setattr(main, "salvar_cotacao", lambda r: ordem.append(("salvar", r)))
    monkeypatch.setattr(main, "gerar_relatorio", lambda: ordem.append(("relatorio",)))

    main.main()

    assert ordem == [("salvar", registro), ("relatorio",)]


def test_main_falha_na_extracao_nao_salva(monkeypatch):
    ordem = []
    monkeypatch.setattr(main, "extrair_cotacao", lambda url: None)
    monkeypatch.setattr(main, "salvar_cotacao", lambda r: ordem.append("salvar"))
    monkeypatch.setattr(main, "gerar_relatorio", lambda: ordem.append("relatorio"))

    main.main()

    assert ordem == []
