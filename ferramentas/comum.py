"""O que o validador e a atualização da lista de ações já mapeadas dividem: colunas, tipos, UFs e municípios."""
import csv
import datetime as dt
import pathlib
import re
import unicodedata
from urllib.parse import urlparse

RAIZ = pathlib.Path(__file__).resolve().parent.parent

COLUNAS = ["titulo", "data", "hora_inicio", "hora_fim", "tipo", "organizacao", "uf", "municipio", "bairro",
           "local", "endereco", "online", "fonte_url", "descricao"]
OBRIGATORIAS = ["titulo", "data", "hora_inicio", "tipo", "fonte_url"]
# Os mesmos tipos do mapeamento inicial (com acento e espaço)
TIPOS = ["ato", "caminhada", "panfletagem", "encontro", "cultural", "bandeiraço", "adesivaço", "porta a porta", "outro"]
UFS = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
       "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}
# O Brasil não tem horário de verão desde 2019: a data de "hoje" é a de Brasília (UTC-3)
BRASILIA = dt.timezone(dt.timedelta(hours=-3))


def hoje() -> dt.date:
    return dt.datetime.now(BRASILIA).date()


def chave(texto: str) -> str:
    """Sem acento, minúsculo e com um espaço só: para comparar nomes."""
    t = unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def tipo_canonico(texto: str) -> str | None:
    """'Bandeiraco', 'porta_a_porta' e 'Porta a porta' viram o nome do site; None se não for um dos tipos."""
    procurado = chave(texto)
    for t in TIPOS:
        if chave(t) == procurado:
            return t
    return None


def link_normalizado(url: str) -> str:
    """O mesmo post com ou sem www, barra no fim, ?igsh=… ou /reel/ no lugar de /p/ vira o mesmo texto."""
    try:
        u = urlparse((url or "").strip())
    except ValueError:
        return ""
    host = u.netloc.lower().removeprefix("www.").removeprefix("m.")
    caminho = u.path.rstrip("/")
    if host == "instagram.com":
        m = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", caminho)
        if m:
            return f"instagram.com/p/{m.group(1)}"
    return f"{host}{caminho}".lower()


def carregar_municipios(caminho: pathlib.Path | None = None) -> dict:
    """{uf: {chave do nome: (nome, lon, lat)}} da lista do IBGE em dados/municipios.csv."""
    por_uf: dict = {}
    with open(caminho or RAIZ / "dados" / "municipios.csv", encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            por_uf.setdefault(linha["uf"], {})[chave(linha["municipio"])] = (
                linha["municipio"], float(linha["lon"]), float(linha["lat"]))
    return por_uf
