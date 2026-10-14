"""Atualiza o mapeamento inicial (ja-mapeadas/acoes.csv e acoes.json): as ações já compiladas, de hoje em diante.

    python ferramentas/atualizar_mapeadas.py

Roda sozinho no GitHub a cada hora (.github/workflows/atualizar-mapeadas.yml). Lê a lista pública e guarda só o
necessário para achar repetidas: nada de contato, de quem cadastrou nem de parâmetros dos links.
"""
import csv
import json
import math
import sys
import urllib.request

from comum import RAIZ, carregar_municipios, chave, hoje

FONTE = "https://boralula.org/agenda/publico.json"
PAGINA = "https://boralula.org/agenda/#/acao/{}"
SAIDA = RAIZ / "ja-mapeadas" / "acoes.csv"
COLUNAS = ["data", "hora_inicio", "hora_fim", "tipo", "titulo", "uf", "municipio", "bairro", "local",
           "online", "fonte_url", "link"]
# Planilha lê como fórmula a célula que começa com =, +, - ou @ (e tab ou CR antes deles); aspas de CSV não impedem
INICIO_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def baixar() -> dict:
    pedido = urllib.request.Request(FONTE, headers={"User-Agent": "compilado-acoes (github.com)"})
    with urllib.request.urlopen(pedido, timeout=60) as resposta:
        return json.load(resposta)


def uf_da_cidade(cidade: str, lon, lat, municipios: dict) -> str:
    """A lista pública traz a cidade sem a UF: o nome resolve quase sempre; homônimas, pelo ponto no mapa."""
    candidatas = [(uf, dados) for uf, nomes in municipios.items() if (dados := nomes.get(chave(cidade)))]
    if len(candidatas) == 1:
        return candidatas[0][0]
    if candidatas and lon is not None and lat is not None:
        return min(candidatas, key=lambda c: math.hypot(c[1][1] - lon, c[1][2] - lat))[0]
    return ""


def linhas(publico: dict, municipios: dict) -> list[dict]:
    acoes = {a["id"]: a for a in publico["acoes"] if a.get("status") == "publicada"}
    desde = hoje().isoformat()
    saida = []
    for t in publico["turnos"]:
        a = acoes.get(t["acao"])
        if not a or not t.get("inicio") or t["inicio"][:10] < desde:
            continue
        link = a.get("link_divulgacao") or ""
        # Sem ?… nem #…: o link do post basta para achar repetidas, e senha de sala (pwd=) não vai para cá
        link = link.split("?")[0].split("#")[0]
        saida.append({
            "data": t["inicio"][:10],
            "hora_inicio": t["inicio"][11:16],
            "hora_fim": (t.get("fim") or "")[11:16],
            "tipo": a.get("tipo") or "",
            "titulo": " ".join((a.get("titulo") or "").split()),
            "uf": uf_da_cidade(a["cidade"], a.get("lon"), a.get("lat"), municipios) if a.get("cidade") else "",
            "municipio": a.get("cidade") or "",
            "bairro": a.get("bairro") or "",
            "local": a.get("lugar_nome") or "",
            "online": "sim" if a.get("online") else "",
            "fonte_url": link if link.startswith(("http://", "https://")) and " " not in link and "%20" not in link else "",
            "link": PAGINA.format(a["id"]),
        })
    saida.sort(key=lambda l: (l["data"], l["uf"], chave(l["municipio"]), l["hora_inicio"], chave(l["titulo"])))
    return saida


def para_planilha(valor):
    """O texto que uma planilha leria como fórmula ganha um apóstrofo na frente e fica texto.

    Todas as colunas deste CSV são texto (data e hora vêm como "2026-10-18" e "09:00", nunca como número), então a
    regra vale para qualquer texto, inclusive "-2" num título. Valor que já é número (int ou float) passa como está:
    número negativo de verdade não vira texto. Só o CSV passa por aqui; o JSON guarda o texto como veio.
    """
    if isinstance(valor, str) and valor.startswith(INICIO_DE_FORMULA):
        return "'" + valor
    return valor


def gravar_csv(resultado: list[dict], caminho):
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, lineterminator="\n")
        w.writeheader()
        w.writerows({k: para_planilha(v) for k, v in l.items()} for l in resultado)


def gravar_json(resultado: list[dict], caminho):
    # A mesma lista em JSON, para quem compara no próprio coletor ("online" vira true/false, como no envio)
    em_json = [{**l, "online": l["online"] == "sim"} for l in resultado]
    caminho.write_text(json.dumps(em_json, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    publico = baixar()
    resultado = linhas(publico, carregar_municipios())
    if not resultado:
        print("A lista pública veio sem nenhuma ação futura; ja-mapeadas/acoes.csv ficou como estava.")
        return 1
    SAIDA.parent.mkdir(exist_ok=True)
    gravar_csv(resultado, SAIDA)
    gravar_json(resultado, SAIDA.with_suffix(".json"))
    print(f"{len(resultado)} ações de hoje em diante em ja-mapeadas/acoes.csv e ja-mapeadas/acoes.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
