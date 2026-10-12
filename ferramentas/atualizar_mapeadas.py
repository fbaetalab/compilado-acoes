"""Atualiza ja-mapeadas/acoes.csv com as ações que já estão no boralula.org, de hoje em diante.

    python ferramentas/atualizar_mapeadas.py

Roda sozinho no GitHub a cada hora (.github/workflows/atualizar-mapeadas.yml). Lê a lista pública do site, a mesma que
o mapa usa, e guarda só o necessário para achar repetidas: nada de contato, de quem cadastrou nem de
parâmetros dos links.
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
           "online", "fonte_url", "link_boralula"]


def baixar() -> dict:
    pedido = urllib.request.Request(FONTE, headers={"User-Agent": "boralula-acoes (github.com)"})
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
            "link_boralula": PAGINA.format(a["id"]),
        })
    saida.sort(key=lambda l: (l["data"], l["uf"], chave(l["municipio"]), l["hora_inicio"], chave(l["titulo"])))
    return saida


def main() -> int:
    publico = baixar()
    resultado = linhas(publico, carregar_municipios())
    if not resultado:
        print("A lista pública veio sem nenhuma ação futura; ja-mapeadas/acoes.csv ficou como estava.")
        return 1
    SAIDA.parent.mkdir(exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, lineterminator="\n")
        w.writeheader()
        w.writerows(resultado)
    print(f"{len(resultado)} ações de hoje em diante em {SAIDA.relative_to(RAIZ).as_posix()}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
