"""Testes da atualização de ja-mapeadas: o CSV não leva fórmula para a planilha e o JSON fica como veio."""
import csv
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "ferramentas"))

import atualizar_mapeadas as am  # noqa: E402
import validar  # noqa: E402

HOJE = "2026-10-12"
PERIGOSOS = ["=1+1", "+SOMA(A1:A9)", "-2+3", "@cmd", "\t=1+1", "\r=1+1"]


def acao(titulo: str, **campos) -> dict:
    base = {"data": "2026-10-18", "hora_inicio": "10:00", "hora_fim": "", "tipo": "ato", "titulo": titulo,
            "uf": "SP", "municipio": "São Paulo", "bairro": "", "local": "Praça da Sé", "online": "",
            "fonte_url": "https://www.instagram.com/p/ABC123/", "link": "https://boralula.org/agenda/#/acao/1"}
    base.update(campos)
    return base


class ParaPlanilha(unittest.TestCase):
    def test_texto_que_vira_formula_ganha_apostrofo(self):
        for valor in PERIGOSOS:
            with self.subTest(valor=valor):
                self.assertEqual(am.para_planilha(valor), "'" + valor)

    def test_texto_normal_e_vazio_ficam_como_estao(self):
        for valor in ["Caminhada da Virada", "2026-10-18", "09:00", "https://boralula.org/agenda/#/acao/1", "",
                      "Ato 13 de outubro", "a=b", "'=1+1"]:
            with self.subTest(valor=valor):
                self.assertEqual(am.para_planilha(valor), valor)

    def test_numero_de_verdade_nao_vira_texto(self):
        self.assertEqual(am.para_planilha(-2), -2)
        self.assertEqual(am.para_planilha(-2.5), -2.5)
        self.assertIsNone(am.para_planilha(None))


class Gravar(unittest.TestCase):
    def gravar(self, resultado):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = pathlib.Path(pasta) / "acoes.csv"
            am.gravar_csv(resultado, caminho)
            am.gravar_json(resultado, caminho.with_suffix(".json"))
            texto_csv = caminho.read_text(encoding="utf-8")
            with open(caminho, encoding="utf-8", newline="") as f:
                lidas = list(csv.DictReader(f))
            return texto_csv, lidas, caminho.with_suffix(".json").read_text(encoding="utf-8")

    def test_csv_neutraliza_campos_externos(self):
        resultado = [acao(v, local=v, bairro=v) for v in PERIGOSOS] + [acao("Caminhada da Virada")]
        _, lidas, _ = self.gravar(resultado)
        for valor, lida in zip(PERIGOSOS, lidas):
            with self.subTest(valor=valor):
                self.assertEqual(lida["titulo"], "'" + valor)
                self.assertEqual(lida["local"], "'" + valor)
                self.assertEqual(lida["bairro"], "'" + valor)
                self.assertFalse(lida["titulo"].startswith(am.INICIO_DE_FORMULA))
        normal = lidas[-1]
        self.assertEqual(normal, acao("Caminhada da Virada"))

    def test_json_fica_como_veio(self):
        resultado = [acao(v, local=v) for v in PERIGOSOS] + [acao("Caminhada da Virada", online="sim")]
        _, _, texto_json = self.gravar(resultado)
        esperado = [{**l, "online": l["online"] == "sim"} for l in resultado]
        # O mesmo texto que a versão anterior gravava, byte a byte
        self.assertEqual(texto_json, json.dumps(esperado, ensure_ascii=False, indent=1) + "\n")
        self.assertEqual(json.loads(texto_json)[0]["titulo"], "=1+1")

    def test_validador_ainda_acha_repetida_com_titulo_neutralizado(self):
        # O validador lê o CSV para achar repetidas e compara o título por chave(), que ignora o apóstrofo
        with tempfile.TemporaryDirectory() as pasta:
            caminho = pathlib.Path(pasta) / "acoes.csv"
            am.gravar_csv([acao("-Caminhada da Virada")], caminho)
            mapeadas = validar.carregar_mapeadas(caminho)
        self.assertEqual(mapeadas[0]["titulo"], "'-Caminhada da Virada")
        r = validar.Relatorio()
        validar.comparar_com_mapeadas({**acao("-Caminhada da Virada"), "fonte_url": "https://exemplo.org/a/1"},
                                      mapeadas, "acoes/SP/teste.csv", r)
        self.assertTrue(r.erros, "a ação repetida passou sem erro")


if __name__ == "__main__":
    unittest.main()
