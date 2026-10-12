# Ações para o boralula.org

Este repositório recebe **ações da campanha em lote**, em CSV, para entrarem no mapa do [boralula.org](https://boralula.org).

O objetivo é **unificar** as ações das organizações de todo o país num lugar só, **dar visibilidade** a elas e
**garantir** que cada uma seja verdadeira e segura para quem vai.

> **Tem só algumas ações?** Não precisa deste repositório. Em [boralula.org](https://boralula.org), abra
> "Divulgar um evento público", cole o link do post e toque em "Preencher pelo post". O formulário se preenche
> sozinho; você confere e envia.

## O que é uma ação

Uma atividade pública da campanha que:

- tem **dia, hora e lugar** (ou um link, se for online);
- é **aberta** a quem quiser participar;
- é chamada por uma **organização**: comitê, sindicato, coletivo, DCE, movimento, partido, agenda cultural…

Não entram reuniões fechadas, compromissos internos nem perfis de pessoas.

## Como enviar

1. **Confira o que já está no mapa** em [`ja-mapeadas/acoes.csv`](ja-mapeadas/acoes.csv). A lista é atualizada a
   cada hora com as ações de hoje em diante.
2. **Copie o modelo** [`modelo/acoes.csv`](modelo/acoes.csv) e preencha **uma linha por ação**. Pode ser no Google
   Sheets ou no Excel (salve como **CSV UTF-8**, separado por vírgula) ou gerado por um script. Veja o
   [exemplo](exemplos/acoes-exemplo.csv).
3. **Rode o validador** (recomendado):

   ```sh
   python ferramentas/validar.py acoes/SP/comites-zona-leste.csv
   ```

4. **Abra um pull request** com o arquivo em `acoes/<UF>/`, por exemplo `acoes/SP/comites-zona-leste.csv`.
   Ações de várias UFs vão em `acoes/BR/`. Nome do arquivo: letras minúsculas, números e hífen.

Para mandar mais ações depois, crie um arquivo novo ou acrescente linhas ao seu.

## As colunas

| coluna | obrigatória | como preencher | exemplo |
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
| `online` | não | `sim` para ação online (aí uf, município e local podem ficar vazios) | não |
| `fonte_url` | **sim** | **link público que anuncia a ação**: post, site, página de inscrição | https://www.instagram.com/p/… |
| `descricao` | não | uma ou duas frases | Distribuição de material na feira. |

**Tipos:** `ato`, `caminhada`, `panfletagem`, `encontro`, `cultural`, `bandeiraço`, `adesivaço`, `porta a porta`,
`outro`. Sem acento também vale (`bandeiraco`, `porta_a_porta`).

Texto com vírgula vai entre aspas: `"Praça da Sé, em frente à catedral"`.

## Regras

- **Toda ação precisa de uma fonte pública.** É o que permite conferir que ela existe. Sem `fonte_url`, não entra.
- **Só organizações, nunca pessoas.** Nada de telefone, e-mail ou perfil pessoal em nenhuma coluna. Opinião política
  é dado sensível (LGPD), e quem vai a uma ação precisa estar protegido.
- **Sem repetição.** Se a ação já está em `ja-mapeadas/acoes.csv` ou em outro arquivo de `acoes/`, não mande de novo.
- **Ações a partir de hoje.** As que já passaram são ignoradas.
- **Cada envio tem responsável.** Os primeiros envios de cada pessoa são revisados pela equipe. Envio falso ou com
  dados pessoais é removido, e a conta é bloqueada.

## O validador

O `ferramentas/validar.py` confere o arquivo antes do envio. Roda com Python 3.10 ou mais novo e não precisa instalar
nada.

```sh
python ferramentas/validar.py acoes/SP/meu-arquivo.csv   # um arquivo
python ferramentas/validar.py acoes/SP/                  # todos os CSVs de uma pasta
```

Ele aponta a linha e o problema:

```
ERRO   acoes/SP/meu-arquivo.csv, linha 4: data "18/10/2026" fora do formato AAAA-MM-DD (por exemplo, 2026-10-18)
ERRO   acoes/SP/meu-arquivo.csv, linha 7: município "Sao Paolo" não existe em SP. Você quis dizer "São Paulo"?
AVISO  acoes/SP/meu-arquivo.csv, linha 9: pode ser a mesma ação que já está no mapa: "Caminhada da Virada" (…)
```

- **Erro** impede o pull request de entrar: formato, tipo, município, link, dado pessoal ou ação que já está no mapa.
- **Aviso** só pede atenção: ação parecida no mesmo dia e cidade, data que já passou.

**Rodar é opcional, mas poupa tempo.** O mesmo validador roda sozinho no GitHub em cada pull request e marca o envio
como aprovado ou com erro. Rodando antes, você corrige tudo de uma vez, sem esperar o GitHub. Sem Python na máquina,
abra o pull request direto e veja o resultado na aba **Checks**.

## O que acontece depois

1. O GitHub confere o pull request com o validador.
2. Sem erro, a equipe faz o merge.
3. As ações entram no boralula.org e aparecem no mapa, com a fonte de cada uma.
4. Na próxima atualização, elas passam a constar em `ja-mapeadas/acoes.csv`.

## Para quem programa

Um coletor que lê o site de uma organização (sindicato, DCE, agenda cultural) e gera este CSV vale muito: rode de
tempos em tempos e mande as ações novas num pull request.

Prefira sites e páginas de organizações. Não use contas pessoais para raspar redes sociais.

## O que tem aqui

| pasta | o quê |
|---|---|
| `acoes/` | os CSVs enviados, um subdiretório por UF |
| `ja-mapeadas/` | as ações que já estão no boralula.org, de hoje em diante (atualizada a cada hora) |
| `modelo/` | o CSV vazio, só com o cabeçalho |
| `exemplos/` | um CSV preenchido de exemplo (ações fictícias) |
| `ferramentas/` | o validador e a atualização da lista de já mapeadas |
| `dados/` | os municípios do IBGE, que o validador usa |
| `testes/` | testes do validador: `python -m unittest discover testes` |

---

Comitê Popular do Lula de Tecnologia · [boralula.org](https://boralula.org)
