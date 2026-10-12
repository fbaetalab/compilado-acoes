"""Confere arquivos de ações (CSV ou JSON) antes do envio. Roda com Python 3.10 ou mais novo, sem instalar nada.

    python ferramentas/validar.py acoes/SP/comite-centro.csv     # um arquivo
    python ferramentas/validar.py acoes/SP/coletor-sindicato.json
    python ferramentas/validar.py acoes/                         # todos os arquivos de uma pasta

Erro impede o pull request de entrar; aviso só pede atenção. O mesmo script roda no GitHub em cada pull request.
"""
import argparse
import csv
import datetime as dt
import difflib
import io
import json
import pathlib
import re
import sys

from comum import (COLUNAS, OBRIGATORIAS, RAIZ, TIPOS, UFS, carregar_municipios, chave, hoje, link_normalizado,
                   tipo_canonico)

MAX_LINHAS = 2000
FIM_CAMPANHA = dt.date(2026, 10, 25)
NOME_ARQUIVO = re.compile(r"^[a-z0-9][a-z0-9-]*\.(csv|json)$")
FORMATOS = (".csv", ".json")
URL = re.compile(r"https?://\S+")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# Celular ou fixo com DDD: (11) 91234-5678, 11 91234 5678, +55 11 912345678, 1132345678
TELEFONE = re.compile(r"(?<![\d/])(?:\+?55[\s.-]?)?\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}(?![\d/])")
SEM_DADO_PESSOAL = ["titulo", "organizacao", "bairro", "local", "endereco", "descricao"]


class Relatorio:
    def __init__(self):
        self.erros: list[str] = []
        self.avisos: list[str] = []

    def erro(self, onde: str, msg: str):
        self.erros.append(f"{onde}: {msg}")

    def aviso(self, onde: str, msg: str):
        self.avisos.append(f"{onde}: {msg}")


def ler_data(texto: str):
    try:
        return dt.date.fromisoformat(texto) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto) else None
    except ValueError:
        return None


def ler_hora(texto: str):
    """Minutos desde 0h. Aceita também 9:30 e 09:30:00, como as planilhas costumam exportar."""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::00)?", texto)
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def hora_canonica(minutos: int) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def carregar_mapeadas(caminho: pathlib.Path) -> list[dict]:
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def chaves_da_acao(a: dict) -> list[tuple]:
    """As formas de reconhecer a mesma ação: mesmo link + dia + hora, ou mesmo título + dia + hora + cidade."""
    ks = [("titulo", a["data"], a["hora_inicio"], chave(a.get("municipio", "")), chave(a["titulo"]))]
    link = link_normalizado(a.get("fonte_url", ""))
    if link_especifico(link):
        ks.append(("link", a["data"], a["hora_inicio"], link))
    return ks


def link_especifico(link: str) -> bool:
    """Um post ou uma página de uma ação só; a página geral de uma agenda (exemplo.org/agenda) não identifica a ação."""
    return bool(link) and (link.startswith("instagram.com/p/") or link.count("/") >= 2)


def comparar_com_mapeadas(a: dict, mapeadas: list[dict], onde: str, r: Relatorio):
    """Mesma ação no mapa: erro. Ação parecida no mesmo dia e cidade, perto do horário: aviso."""
    minutos = ler_hora(a["hora_inicio"])
    link = link_normalizado(a["fonte_url"])
    link = link if link_especifico(link) else ""
    cidade = chave(a.get("municipio", ""))
    parecidas = []
    for m in mapeadas:
        if m["data"] != a["data"]:
            continue
        mesma_cidade = cidade and chave(m["municipio"]) == cidade
        if not mesma_cidade and not (a.get("online") == "sim" and m.get("online") == "sim"):
            continue
        outra = ler_hora(m["hora_inicio"])
        diferenca = abs(outra - minutos) if outra is not None and minutos is not None else 999
        parecido = difflib.SequenceMatcher(None, chave(m["titulo"]), chave(a["titulo"])).ratio()
        mesmo_link = bool(link) and link_normalizado(m.get("fonte_url", "")) == link
        ref = f"\"{m['titulo']}\" ({m['data']} {m['hora_inicio']}, {m['municipio'] or 'online'}) {m['link']}"
        if diferenca == 0 and (mesmo_link or parecido >= 0.6):
            r.erro(onde, f"essa ação já está no mapa: {ref}")
            return
        if diferenca <= 60 and (mesmo_link or parecido >= 0.4):
            parecidas.append(ref)
    if parecidas:
        r.aviso(onde, f"pode ser a mesma ação que já está no mapa: {parecidas[0]}")


def validar_linha(a: dict, onde: str, uf_pasta: str | None, municipios: dict, dia: dt.date, r: Relatorio):
    for col in OBRIGATORIAS:
        if not a[col]:
            r.erro(onde, f"o campo {col} é obrigatório")
    if a["titulo"] and len(a["titulo"]) > 120:
        r.erro(onde, "o título passa de 120 caracteres")

    data = ler_data(a["data"])
    if a["data"] and not data:
        r.erro(onde, f"data \"{a['data']}\" fora do formato AAAA-MM-DD (por exemplo, 2026-10-18)")
    elif data and data < dia:
        r.aviso(onde, f"a data {a['data']} já passou; essa ação vai ser ignorada")
    elif data and data > FIM_CAMPANHA:
        r.aviso(onde, f"a data {a['data']} é depois do 2º turno (25/10)")

    inicio = ler_hora(a["hora_inicio"])
    if a["hora_inicio"] and inicio is None:
        r.erro(onde, f"hora_inicio \"{a['hora_inicio']}\" fora do formato HH:MM (por exemplo, 09:30)")
    elif inicio is not None:
        a["hora_inicio"] = hora_canonica(inicio)
    if a["hora_fim"]:
        fim = ler_hora(a["hora_fim"])
        if fim is None:
            r.erro(onde, f"hora_fim \"{a['hora_fim']}\" fora do formato HH:MM")
        elif inicio is not None and fim <= inicio:
            r.erro(onde, "hora_fim é antes da hora_inicio")
        else:
            a["hora_fim"] = hora_canonica(fim)

    if a["tipo"]:
        canonico = tipo_canonico(a["tipo"])
        if canonico:
            a["tipo"] = canonico
        else:
            r.erro(onde, f"tipo \"{a['tipo']}\" não existe; use um destes: {', '.join(TIPOS)}")

    online = chave(a["online"])
    if online not in ("", "sim", "nao"):
        r.erro(onde, "o campo online aceita só sim, não ou vazio (no JSON, true ou false)")
    a["online"] = "sim" if online == "sim" else ""
    if not a["online"]:
        for col in ("uf", "municipio", "local"):
            if not a[col]:
                r.erro(onde, f"o campo {col} é obrigatório para ação presencial (ou marque online = sim)")
    if a["uf"]:
        uf = a["uf"].strip().upper()
        if uf not in UFS:
            r.erro(onde, f"UF \"{a['uf']}\" não existe")
        else:
            a["uf"] = uf
            if uf_pasta and uf_pasta != "BR" and uf != uf_pasta:
                r.erro(onde, f"a UF da ação é {uf}, mas o arquivo está na pasta {uf_pasta}")
            if a["municipio"]:
                achado = municipios.get(uf, {}).get(chave(a["municipio"]))
                if achado:
                    a["municipio"] = achado[0]
                else:
                    nomes = [n for n, _, _ in municipios.get(uf, {}).values()]
                    perto = difflib.get_close_matches(a["municipio"], nomes, n=1, cutoff=0.75)
                    dica = f" Você quis dizer \"{perto[0]}\"?" if perto else ""
                    r.erro(onde, f"município \"{a['municipio']}\" não existe em {uf}.{dica}")

    if a["fonte_url"]:
        if not re.fullmatch(r"https?://[^\s/]+\.[^\s/]+\S*", a["fonte_url"]):
            r.erro(onde, "fonte_url precisa ser um link completo, começando com https://")

    for col in SEM_DADO_PESSOAL:
        texto = URL.sub(" ", a[col])
        if EMAIL.search(texto) or TELEFONE.search(texto):
            r.erro(onde, f"o campo {col} tem e-mail ou telefone; tire os dados pessoais")


def ler_csv(texto: str, nome: str, r: Relatorio) -> list[tuple[str, dict]] | None:
    """As ações de um CSV, cada uma com onde ela está ("linha 4"). None se o arquivo não dá para ler."""
    try:
        leitor = csv.reader(io.StringIO(texto, newline=""))
        linhas = [(leitor.line_num, valores) for valores in leitor]
    except csv.Error as e:
        r.erro(nome, f"o CSV está quebrado ({e}); confira as aspas")
        return None
    if not linhas or not linhas[0][1]:
        r.erro(nome, "arquivo vazio ou sem cabeçalho na primeira linha")
        return None
    cabecalho = [c.strip().lower() for c in linhas[0][1]]
    if ";" in linhas[0][1][0] and len(cabecalho) == 1:
        r.erro(nome, "o separador precisa ser vírgula, não ponto e vírgula")
        return None
    desconhecidas = [c for c in cabecalho if c not in COLUNAS]
    faltando = [c for c in COLUNAS if c not in cabecalho]
    if desconhecidas:
        r.erro(nome, f"colunas que não existem no modelo: {', '.join(desconhecidas)}")
    if faltando:
        r.erro(nome, f"faltam colunas do modelo: {', '.join(faltando)} (podem ficar vazias, mas precisam existir)")
    if desconhecidas or faltando:
        return None
    acoes = []
    for n, valores in linhas[1:]:
        if not any(v.strip() for v in valores):
            continue
        if len(valores) != len(cabecalho):
            r.erro(f"{nome}, linha {n}", f"a linha tem {len(valores)} colunas e o cabeçalho tem {len(cabecalho)} "
                                         "(texto com vírgula precisa estar entre aspas)")
            continue
        acoes.append((f"linha {n}", {c: v.strip() for c, v in zip(cabecalho, valores)}))
    return acoes


def ler_json(texto: str, nome: str, r: Relatorio) -> list[tuple[str, dict]] | None:
    """As ações de um JSON: uma lista de objetos com os mesmos campos do CSV. Campo opcional pode faltar."""
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as e:
        r.erro(nome, f"JSON inválido na linha {e.lineno}, coluna {e.colno}: {e.msg}")
        return None
    if not isinstance(dados, list):
        r.erro(nome, "o JSON precisa ser uma lista de ações: [ {\"titulo\": ...}, {\"titulo\": ...} ]")
        return None
    acoes = []
    for i, item in enumerate(dados, start=1):
        onde = f"{nome}, ação {i}"
        if not isinstance(item, dict):
            r.erro(onde, "cada ação precisa ser um objeto { ... }")
            continue
        desconhecidos = [k for k in item if k not in COLUNAS]
        if desconhecidos:
            r.erro(onde, f"campos que não existem no modelo: {', '.join(desconhecidos)}")
            continue
        a = {}
        for c in COLUNAS:
            v = item.get(c)
            if v is None:
                a[c] = ""
            elif c == "online" and isinstance(v, bool):
                a[c] = "sim" if v else ""
            elif isinstance(v, str):
                a[c] = v.strip()
            else:
                r.erro(onde, f"o campo {c} precisa ser texto entre aspas (online também aceita true ou false)")
                break
        else:
            acoes.append((f"ação {i}", a))
    return acoes


def ler_acoes(caminho: pathlib.Path, nome: str, r: Relatorio) -> list[tuple[str, dict]] | None:
    if caminho.is_symlink():
        r.erro(nome, "o arquivo é um link simbólico; envie o arquivo de verdade")
        return None
    try:
        texto = caminho.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        r.erro(nome, "o arquivo não está em UTF-8 (no Excel: Salvar como → CSV UTF-8)")
        return None
    return ler_json(texto, nome, r) if caminho.suffix.lower() == ".json" else ler_csv(texto, nome, r)


def validar_arquivo(caminho: pathlib.Path, raiz: pathlib.Path, municipios: dict, mapeadas: list[dict],
                    vistas: dict, dia: dt.date, r: Relatorio) -> int:
    """Confere um arquivo e devolve quantas ações ele tem. `vistas` junta as ações de todos os arquivos já lidos."""
    try:
        nome = caminho.resolve().relative_to(raiz.resolve()).as_posix()
    except ValueError:
        nome = caminho.as_posix()
    partes = nome.split("/")
    uf_pasta = None
    if partes[0] == "acoes":
        if len(partes) != 3:
            r.erro(nome, "o arquivo precisa ficar em acoes/<UF>/, por exemplo acoes/SP/comite-centro.csv")
        else:
            uf_pasta = partes[1]
            if uf_pasta not in UFS | {"BR"}:
                r.erro(nome, f"a pasta {uf_pasta} não é uma UF (use a sigla, como SP, ou BR para várias UFs)")
            if not NOME_ARQUIVO.match(partes[2]):
                r.erro(nome, "use só letras minúsculas, números e hífen no nome do arquivo, terminando em .csv ou .json")

    erros_antes = len(r.erros)
    acoes = ler_acoes(caminho, nome, r)
    if acoes is None:
        return 0
    if len(acoes) > MAX_LINHAS:
        r.erro(nome, f"mais de {MAX_LINHAS} ações num arquivo só; divida em arquivos menores")
        return 0
    if not acoes and len(r.erros) == erros_antes:
        r.erro(nome, "o arquivo não tem nenhuma ação")

    for ref, a in acoes:
        onde = f"{nome}, {ref}"
        erros_antes = len(r.erros)
        validar_linha(a, onde, uf_pasta, municipios, dia, r)
        if len(r.erros) > erros_antes:
            continue
        repetida = next((vistas[k] for k in chaves_da_acao(a) if k in vistas), None)
        if repetida:
            r.erro(onde, f"ação repetida: é a mesma de {repetida}")
            continue
        for k in chaves_da_acao(a):
            vistas[k] = onde
        comparar_com_mapeadas(a, mapeadas, onde, r)
    return len(acoes)


def acoes_do_repositorio(raiz: pathlib.Path, conferidos: set) -> dict:
    """As ações dos arquivos que já estão em acoes/ (menos os que estão sendo conferidos), para achar repetidas."""
    vistas: dict = {}
    for arq in sorted(a for a in (raiz / "acoes").glob("*/*") if a.suffix.lower() in FORMATOS):
        if arq.resolve() in conferidos:
            continue
        nome = arq.relative_to(raiz).as_posix()
        for ref, a in ler_acoes(arq, nome, Relatorio()) or []:
            minutos = ler_hora(a["hora_inicio"])
            if a["titulo"] and a["data"] and minutos is not None:
                a["hora_inicio"] = hora_canonica(minutos)
                for k in chaves_da_acao(a):
                    vistas.setdefault(k, f"{nome}, {ref}")
    return vistas


def conferir_alteracoes(caminho: pathlib.Path, r: Relatorio, equipe: bool = False) -> list[str]:
    """No GitHub: a saída de `git diff --name-status`. Pull request de fora da equipe só pode criar arquivos em acoes/
    (mudar, renomear ou apagar um arquivo que já existe mexeria nas ações de outra pessoa); o da equipe mexe em tudo, e
    só os arquivos de acoes/ são conferidos."""
    arquivos = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        status, *nomes = linha.split("\t")
        alvo = nomes[-1]
        de_acoes = alvo.startswith("acoes/") and alvo.lower().endswith(FORMATOS)
        if status.startswith("D"):
            if not equipe:
                r.erro(alvo, "o pull request apaga um arquivo; só a equipe pode apagar")
        elif not equipe and de_acoes and not status.startswith(("A", "C")):
            r.erro(alvo, "o pull request muda um arquivo que já existe; para mandar mais ações, crie um arquivo novo")
        elif de_acoes:
            arquivos.append(alvo)
        elif not equipe:
            r.erro(alvo, "o pull request mexe num arquivo que não é de ações (.csv ou .json em acoes/<UF>/); "
                         "envie só os seus arquivos de ações")
    return arquivos


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Confere arquivos de ações (CSV ou JSON) no modelo do compilado.")
    p.add_argument("caminhos", nargs="*", help="arquivos .csv ou .json, ou pastas")
    p.add_argument("--raiz", type=pathlib.Path, default=RAIZ, help="onde fica a pasta acoes/ (padrão: este repositório)")
    p.add_argument("--alteracoes", type=pathlib.Path, help="saída de git diff --name-status (usado no GitHub)")
    p.add_argument("--equipe", action="store_true", help="pull request da equipe (pode mexer fora de acoes/)")
    p.add_argument("--hoje", type=dt.date.fromisoformat, default=None, help="data de hoje, AAAA-MM-DD (para testes)")
    args = p.parse_args(argv)

    r = Relatorio()
    caminhos = [pathlib.Path(c) for c in args.caminhos]
    if args.alteracoes:
        caminhos += [args.raiz / c for c in conferir_alteracoes(args.alteracoes, r, args.equipe)]
    arquivos = []
    for c in caminhos:
        if c.is_dir():
            arquivos += sorted(a for a in c.rglob("*") if a.suffix.lower() in FORMATOS)
        elif c.suffix.lower() in FORMATOS and c.exists():
            arquivos.append(c)
        else:
            r.erro(str(c), "não é um arquivo .csv ou .json")
    if not arquivos and not r.erros:
        print("Nenhum arquivo de ações para conferir.")
        return 0

    municipios = carregar_municipios()
    mapeadas = carregar_mapeadas(RAIZ / "ja-mapeadas" / "acoes.csv")
    if not mapeadas:
        r.aviso("ja-mapeadas/acoes.csv", "lista de ações já mapeadas não encontrada; não deu para conferir repetidas")
    vistas = acoes_do_repositorio(args.raiz, {a.resolve() for a in arquivos})
    dia = args.hoje or hoje()
    total = sum(validar_arquivo(a, args.raiz, municipios, mapeadas, vistas, dia, r) for a in arquivos)

    for e in r.erros:
        print(f"ERRO   {e}")
    for a in r.avisos:
        print(f"AVISO  {a}")
    resumo = f"{total} {'ação conferida' if total == 1 else 'ações conferidas'} em {len(arquivos)} " \
             f"{'arquivo' if len(arquivos) == 1 else 'arquivos'}: {len(r.erros)} erro(s), {len(r.avisos)} aviso(s)."
    print(("\nTudo certo! " if not r.erros else "\nCorrija os erros acima e rode de novo. ") + resumo)
    return 1 if r.erros else 0


if __name__ == "__main__":
    sys.exit(main())
