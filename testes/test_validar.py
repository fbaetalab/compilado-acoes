"""Testes do validador: python -m unittest discover testes"""
import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "ferramentas"))

import validar  # noqa: E402
from comum import COLUNAS, carregar_municipios, link_normalizado, tipo_canonico  # noqa: E402

HOJE = dt.date(2026, 10, 12)
CABECALHO = ",".join(COLUNAS)
MUNICIPIOS = carregar_municipios()
MAPEADA = {"data": "2026-10-18", "hora_inicio": "10:00", "hora_fim": "", "tipo": "ato",
           "titulo": "Caminhada da Virada", "uf": "SP", "municipio": "São Paulo", "bairro": "", "local": "Praça da Sé",
           "online": "", "fonte_url": "https://www.instagram.com/p/ABC123/",
           "link_boralula": "https://boralula.org/agenda/#/acao/1"}


def linha(**campos) -> str:
    base = {"titulo": "Panfletaço na feira", "data": "2026-10-18", "hora_inicio": "09:00", "tipo": "panfletagem",
            "uf": "SP", "municipio": "São Paulo", "local": "Feira da Rua X", "fonte_url": "https://exemplo.org/a/1"}
    base.update(campos)
    return ",".join(f'"{base.get(c, "")}"' for c in COLUNAS)


class Validar(unittest.TestCase):
    def conferir(self, *linhas, nome="acoes/SP/teste.csv", texto=None, mapeadas=(), vistas=None):
        with tempfile.TemporaryDirectory() as pasta:
            raiz = pathlib.Path(pasta)
            arq = raiz / nome
            arq.parent.mkdir(parents=True)
            arq.write_text(texto if texto is not None else "\n".join([CABECALHO, *linhas]) + "\n", encoding="utf-8")
            r = validar.Relatorio()
            total = validar.validar_arquivo(arq, raiz, MUNICIPIOS, list(mapeadas), vistas or {}, HOJE, r)
            return total, r

    def test_arquivo_certo_passa(self):
        total, r = self.conferir(linha(), linha(titulo="Ato online", uf="", municipio="", local="", online="sim",
                                                fonte_url="https://exemplo.org/sala/2"))
        self.assertEqual((total, r.erros, r.avisos), (2, [], []))

    def test_formatos_errados(self):
        _, r = self.conferir(linha(data="18/10/2026", hora_inicio="9h", tipo="passeata", fonte_url="exemplo.org"))
        texto = "\n".join(r.erros)
        for trecho in ("AAAA-MM-DD", "HH:MM", "passeata", "https://"):
            self.assertIn(trecho, texto)

    def test_municipio_com_sugestao(self):
        _, r = self.conferir(linha(municipio="Sao Paolo"))
        self.assertIn('Você quis dizer "São Paulo"', r.erros[0])

    def test_municipio_sem_acento_e_tipo_sem_cedilha_valem(self):
        _, r = self.conferir(linha(municipio="sao paulo", tipo="Bandeiraco"))
        self.assertEqual(r.erros, [])

    def test_uf_diferente_da_pasta(self):
        _, r = self.conferir(linha(uf="RJ", municipio="Niterói"))
        self.assertIn("pasta SP", r.erros[0])

    def test_pasta_br_aceita_qualquer_uf(self):
        _, r = self.conferir(linha(uf="RJ", municipio="Niterói"), nome="acoes/BR/nacional.csv")
        self.assertEqual(r.erros, [])

    def test_presencial_sem_local(self):
        _, r = self.conferir(linha(local=""))
        self.assertIn("local", r.erros[0])

    def test_dado_pessoal(self):
        for texto in ("Fale com a Ana (11) 91234-5678", "contato: ana@exemplo.org", "zap 11912345678"):
            _, r = self.conferir(linha(descricao=texto))
            self.assertEqual(len(r.erros), 1, texto)
        _, r = self.conferir(linha(descricao="Na rua 25 de Março, 1000, às 10h. https://instagram.com/p/12345678901/"))
        self.assertEqual(r.erros, [])

    def test_data_passada_so_avisa(self):
        _, r = self.conferir(linha(data="2026-10-01"))
        self.assertEqual(r.erros, [])
        self.assertIn("já passou", r.avisos[0])

    def test_repetida_no_mesmo_arquivo(self):
        _, r = self.conferir(linha(), linha(titulo="Panfletaço na Feira!"))
        self.assertIn("ação repetida", r.erros[0])

    def test_repetida_em_outro_arquivo(self):
        vistas = {k: "acoes/SP/outro.csv, linha 2" for k in validar.chaves_da_acao(
            {"titulo": "Panfletaço na feira", "data": "2026-10-18", "hora_inicio": "09:00", "municipio": "São Paulo",
             "fonte_url": "https://exemplo.org/a/1"})}
        _, r = self.conferir(linha(), vistas=vistas)
        self.assertIn("acoes/SP/outro.csv", r.erros[0])

    def test_ja_no_mapa_e_erro(self):
        _, r = self.conferir(linha(titulo="Caminhada da virada!", hora_inicio="10:00"), mapeadas=[MAPEADA])
        self.assertIn("já está no mapa", r.erros[0])
        _, r = self.conferir(linha(titulo="Outra coisa", hora_inicio="10:00", fonte_url="https://instagram.com/reel/ABC123"),
                             mapeadas=[MAPEADA])
        self.assertIn("já está no mapa", r.erros[0])

    def test_parecida_no_mapa_e_aviso(self):
        _, r = self.conferir(linha(titulo="Caminhada da Virada SP", hora_inicio="10:30"), mapeadas=[MAPEADA])
        self.assertEqual(r.erros, [])
        self.assertIn("pode ser a mesma", r.avisos[0])

    def test_pagina_geral_de_agenda_nao_identifica_a_acao(self):
        geral = dict(MAPEADA, titulo="Ato no centro", fonte_url="https://comitepopular.org.br/agenda/")
        _, r = self.conferir(linha(titulo="Feira cultural", hora_inicio="10:00",
                                   fonte_url="https://comitepopular.org.br/agenda/"), mapeadas=[geral])
        self.assertEqual((r.erros, r.avisos), ([], []))

    def test_pagina_geral_de_agenda_nao_repete_entre_arquivos(self):
        geral = "https://comitepopular.org.br/agenda/"
        vistas = {k: "acoes/RJ/outro.csv, linha 2" for k in validar.chaves_da_acao(
            {"titulo": "Ato no Rio", "data": "2026-10-18", "hora_inicio": "09:00", "municipio": "Rio de Janeiro",
             "fonte_url": geral})}
        _, r = self.conferir(linha(fonte_url=geral), vistas=vistas)
        self.assertEqual(r.erros, [])

    def test_quebra_de_linha_dentro_de_aspas(self):
        _, r = self.conferir(linha(descricao="primeira linha\nsegunda linha"), linha(data="18-10-2026"))
        self.assertEqual(len(r.erros), 1)
        self.assertIn("linha 4", r.erros[0])

    def test_primeira_linha_vazia(self):
        _, r = self.conferir(texto="\n" + CABECALHO + "\n")
        self.assertIn("sem cabeçalho", r.erros[0])

    def test_json_certo_passa(self):
        texto = json.dumps([
            {"titulo": "Panfletaço na feira", "data": "2026-10-18", "hora_inicio": "09:00", "tipo": "panfletagem",
             "uf": "SP", "municipio": "São Paulo", "local": "Feira da Rua X", "fonte_url": "https://exemplo.org/a/1"},
            {"titulo": "Conversa online", "data": "2026-10-19", "hora_inicio": "20:00", "tipo": "encontro",
             "online": True, "fonte_url": "https://exemplo.org/sala/2", "hora_fim": None},
        ], ensure_ascii=False)
        total, r = self.conferir(texto=texto, nome="acoes/SP/coletor.json")
        self.assertEqual((total, r.erros, r.avisos), (2, [], []))

    def test_json_com_problemas(self):
        _, r = self.conferir(texto='[{"titulo": "A",}]', nome="acoes/SP/x.json")
        self.assertIn("JSON inválido na linha 1", r.erros[0])
        _, r = self.conferir(texto='{"titulo": "A"}', nome="acoes/SP/x.json")
        self.assertIn("lista de ações", r.erros[0])
        _, r = self.conferir(texto='[{"titulo": "A", "cidade": "Recife"}, {"titulo": "B", "data": 20261018}, "C"]',
                             nome="acoes/SP/x.json")
        self.assertEqual(len(r.erros), 3)
        self.assertIn("ação 1", r.erros[0])
        self.assertIn("cidade", r.erros[0])
        self.assertIn("texto entre aspas", r.erros[1])
        self.assertIn("ação 3", r.erros[2])

    def test_json_e_csv_se_enxergam_como_repetidos(self):
        acao = {"titulo": "Panfletaço na feira", "data": "2026-10-18", "hora_inicio": "09:00", "tipo": "panfletagem",
                "uf": "SP", "municipio": "São Paulo", "local": "Feira", "fonte_url": "https://exemplo.org/a/1"}
        with tempfile.TemporaryDirectory() as pasta:
            raiz = pathlib.Path(pasta)
            (raiz / "acoes" / "SP").mkdir(parents=True)
            (raiz / "acoes" / "SP" / "antigo.json").write_text(json.dumps([acao]), encoding="utf-8")
            novo = raiz / "acoes" / "SP" / "novo.csv"
            novo.write_text(CABECALHO + "\n" + linha() + "\n", encoding="utf-8")
            vistas = validar.acoes_do_repositorio(raiz, {novo.resolve()})
            r = validar.Relatorio()
            validar.validar_arquivo(novo, raiz, MUNICIPIOS, [], vistas, HOJE, r)
            self.assertIn("acoes/SP/antigo.json, ação 1", r.erros[0])

    def test_cabecalho_e_separador(self):
        _, r = self.conferir(texto="titulo;data;hora_inicio\nA;B;C\n")
        self.assertIn("vírgula", r.erros[0])
        _, r = self.conferir(texto=CABECALHO.replace("municipio", "cidade") + "\n")
        self.assertIn("cidade", r.erros[0])

    def test_nome_e_pasta_do_arquivo(self):
        _, r = self.conferir(linha(), nome="acoes/SP/Meu Arquivo.csv")
        self.assertIn("letras minúsculas", r.erros[0])
        _, r = self.conferir(linha(), nome="acoes/XX/teste.csv")
        self.assertTrue(any("não é uma UF" in e for e in r.erros))

    def test_alteracoes_fora_de_acoes(self):
        with tempfile.TemporaryDirectory() as pasta:
            status = pathlib.Path(pasta) / "status.txt"
            status.write_text("A\tacoes/SP/novo.csv\nA\tacoes/SP/coletor.json\nM\tferramentas/validar.py\n"
                              "D\tacoes/RJ/velho.csv\nM\tacoes/BA/de-outra-pessoa.csv\n"
                              "R100\tacoes/PE/a.csv\tacoes/PE/b.csv\n", encoding="utf-8")
            r = validar.Relatorio()
            self.assertEqual(validar.conferir_alteracoes(status, r), ["acoes/SP/novo.csv", "acoes/SP/coletor.json"])
            self.assertEqual(len(r.erros), 4)
            r = validar.Relatorio()
            self.assertEqual(validar.conferir_alteracoes(status, r, equipe=True),
                             ["acoes/SP/novo.csv", "acoes/SP/coletor.json", "acoes/BA/de-outra-pessoa.csv",
                              "acoes/PE/b.csv"])
            self.assertEqual(r.erros, [])


class Comum(unittest.TestCase):
    def test_link_normalizado(self):
        self.assertEqual(link_normalizado("https://www.instagram.com/reel/ABC/?igsh=x"), "instagram.com/p/ABC")
        self.assertEqual(link_normalizado("https://instagram.com/comite/p/ABC/"), "instagram.com/p/ABC")

    def test_tipos(self):
        self.assertEqual(tipo_canonico("porta_a_porta"), "porta a porta")
        self.assertIsNone(tipo_canonico("passeata"))


if __name__ == "__main__":
    unittest.main()
