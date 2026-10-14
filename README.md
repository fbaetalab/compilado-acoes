# Compilado de ações

Este repositório recebe **ações em lote**, em CSV ou JSON, para compilar num mapa só as atividades que fortalecem
a campanha em todo o país.

O objetivo é **unificar** essas ações, **dar visibilidade** a elas e **garantir** que cada uma seja verdadeira e
segura para quem vai.

## O que é uma ação

Qualquer atividade aberta que fortaleça a campanha. Precisa ter:

- **dia, hora e lugar** (ou um link, se for online);
- **portas abertas** a quem quiser participar;
- um **link público** que a anuncie: post, site, página de inscrição.

Não entram reuniões fechadas nem compromissos internos.

## Como enviar

1. **Confira o mapeamento inicial** em [`ja-mapeadas/`](ja-mapeadas/): as ações já compiladas, de hoje em diante,
   em [CSV](ja-mapeadas/acoes.csv) e em [JSON](ja-mapeadas/acoes.json). A lista é atualizada a cada hora, e o
   validador compara o seu arquivo com ela. No CSV, o texto que começa com `=`, `+`, `-` ou `@` vem com um
   apóstrofo na frente (`'=1+1`), para a planilha não ler como fórmula; o JSON traz o texto como veio.
2. **Monte o arquivo** no formato que for mais fácil para você:
   - **CSV**, para quem trabalha em planilha: copie [`modelo/acoes.csv`](modelo/acoes.csv) e preencha **uma linha por
     ação**. No Google Sheets: Arquivo → Fazer download → CSV. No Excel: Salvar como → **CSV UTF-8**.
     Veja o [exemplo](exemplos/acoes-exemplo.csv).
   - **JSON**, para quem gera por script: uma lista de objetos com os mesmos campos
     ([modelo](modelo/acoes.json), [exemplo](exemplos/acoes-exemplo.json)).
3. **Rode o validador** (recomendado):

   ```sh
   python ferramentas/validar.py acoes/SP/comites-zona-leste.csv
   ```

4. **Abra um pull request** com o arquivo em `acoes/<UF>/`, por exemplo `acoes/SP/comites-zona-leste.csv` ou
   `acoes/SP/coletor-sindicato.json`. Ações de várias UFs vão em `acoes/BR/`. Nome do arquivo: letras minúsculas,
   números e hífen.

Para mandar mais ações depois, **crie um arquivo novo** (por exemplo `comites-zona-leste-2.csv`): um pull
request não pode mudar arquivos que já estão no repositório.

## Os campos

Os mesmos no CSV (colunas, todas presentes no cabeçalho) e no JSON (chaves; as opcionais podem faltar).

| campo | obrigatório | como preencher | exemplo |
|---|---|---|---|
| `titulo` | sim | curto, dizendo o que é a ação (até 120 caracteres) | Panfletaço na Praça da Sé |
| `data` | sim | AAAA-MM-DD | 2026-10-18 |
| `hora_inicio` | sim | HH:MM, no horário da cidade | 10:00 |
| `hora_fim` | não | HH:MM | 13:00 |
| `tipo` | sim | um dos tipos abaixo | panfletagem |
| `organizacao` | não | quem chama a ação | Comitê Popular Centro |
| `uf` | sim, se presencial | sigla | SP |
| `municipio` | sim, se presencial | nome do município, como no IBGE | São Paulo |
| `bairro` | não | | Sé |
| `local` | sim, se presencial | onde as pessoas se encontram | Praça da Sé, em frente à catedral |
| `endereco` | não | rua e número | Praça da Sé, s/n |
| `online` | não | `sim` (no JSON, `true`) para ação online; aí uf, município e local podem ficar vazios | não |
| `fonte_url` | **sim** | **link público que anuncia a ação**: post, site, página de inscrição | https://www.instagram.com/p/… |
| `descricao` | não | uma ou duas frases | Distribuição de material na feira. |

**Tipos:** `ato`, `caminhada`, `panfletagem`, `encontro`, `cultural`, `bandeiraço`, `adesivaço`, `porta a porta`,
`outro`. Sem acento também vale (`bandeiraco`, `porta_a_porta`).

No CSV, texto com vírgula vai entre aspas: `"Praça da Sé, em frente à catedral"`. No JSON, todo valor é texto
entre aspas, menos `online` (`true` ou `false`).

```json
[
  {
    "titulo": "Panfletaço na Praça da Sé",
    "data": "2026-10-18",
    "hora_inicio": "10:00",
    "tipo": "panfletagem",
    "uf": "SP",
    "municipio": "São Paulo",
    "local": "Praça da Sé, em frente à catedral",
    "fonte_url": "https://www.instagram.com/p/…"
  }
]
```

## Regras

- **Toda ação precisa de uma fonte pública.** É o que permite conferir que ela existe. Sem `fonte_url`, não entra.
- **Sem repetição.** Se a ação já está em `ja-mapeadas/` ou em outro arquivo de `acoes/`, não mande de novo.
- **Ações a partir de hoje.** As que já passaram são ignoradas.
- **Cada envio tem responsável.** Os primeiros envios de cada pessoa são revisados pela equipe. Envio falso é
  removido, e a conta é bloqueada.

## O validador

O `ferramentas/validar.py` confere o arquivo antes do envio. Roda com Python 3.10 ou mais novo e não precisa instalar
nada.

```sh
python ferramentas/validar.py acoes/SP/meu-arquivo.csv   # um arquivo CSV
python ferramentas/validar.py acoes/SP/coletor.json      # ou JSON
python ferramentas/validar.py acoes/SP/                  # todos os arquivos de uma pasta
```

Ele aponta a linha (no CSV) ou o número da ação (no JSON) e o problema:

```
ERRO   acoes/SP/meu-arquivo.csv, linha 4: data "18/10/2026" fora do formato AAAA-MM-DD (por exemplo, 2026-10-18)
ERRO   acoes/SP/meu-arquivo.csv, linha 7: município "Sao Paolo" não existe em SP. Você quis dizer "São Paulo"?
AVISO  acoes/SP/meu-arquivo.csv, linha 9: pode ser a mesma ação que já está no mapa: "Caminhada da Virada" (…)
```

- **Erro** impede o pull request de entrar: formato, tipo, município, link ou ação que já está no mapa.
- **Aviso** só pede atenção: ação parecida no mesmo dia e cidade, data que já passou.

**Rodar é opcional, mas poupa tempo.** O mesmo validador roda sozinho no GitHub em cada pull request e marca o envio
como aprovado ou com erro. Rodando antes, você corrige tudo de uma vez, sem esperar o GitHub. Sem Python na máquina,
abra o pull request direto e veja o resultado na aba **Checks**.

## O que acontece depois

1. O GitHub confere o pull request com o validador.
2. Sem erro, a equipe faz o merge.
3. As ações entram no mapa, com a fonte de cada uma.
4. Na próxima atualização, elas passam a constar em `ja-mapeadas/`.

## Para quem programa

Um coletor que lê um site de agenda (de sindicato, DCE, coletivo cultural…) e gera o JSON vale muito: rode de
tempos em tempos, compare com [`ja-mapeadas/acoes.json`](ja-mapeadas/acoes.json) e mande as ações novas num pull
request.

Não use contas pessoais para raspar redes sociais.

## Prefere não abrir pull request?

Para poucas ações, dá para cadastrar uma por uma pelo site [boralula.org](https://boralula.org): abra "Divulgar um
evento público", cole o link do post e toque em "Preencher pelo post". O formulário se preenche sozinho; você
confere e envia.

## O que tem aqui

| pasta | o quê |
|---|---|
| `acoes/` | os arquivos enviados (CSV ou JSON), um subdiretório por UF |
| `ja-mapeadas/` | o mapeamento inicial: as ações já compiladas, de hoje em diante, em CSV e JSON (atualizado a cada hora) |
| `modelo/` | os modelos vazios, em CSV e JSON |
| `exemplos/` | o mesmo exemplo em CSV e em JSON (ações fictícias) |
| `ferramentas/` | o validador e a atualização do mapeamento inicial |
| `dados/` | os municípios do IBGE, que o validador usa |
| `testes/` | testes do validador e da atualização do mapeamento: `python -m unittest discover testes` |

---

Comitê Popular do Lula de Tecnologia
