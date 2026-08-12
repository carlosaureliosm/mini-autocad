# mini-autocad — Gerador de Croqui / Planta Baixa

Aplicação desktop em Python (Tkinter) para desenhar croquis de plantas baixas
em um plano cartesiano (paredes, portas, escada caracol, texto, etc.) com
zoom, pan, undo/redo e exportação para PNG.

## Como rodar

```bash
python GeradorPlantaBaixa.py
```

Requer Python 3 com Tkinter (padrão na instalação do Windows). Pillow é
opcional — só é necessário para o botão "Exportar PNG" (`TEM_PILLOW`).

Existe também um build standalone (PyInstaller) em `dist/GeradorPlantaBaixa/`
e artefatos intermediários em `build/`. Esses diretórios não fazem parte do
código-fonte e não devem ser versionados manualmente a cada alteração do
`.py` — regenerar com PyInstaller quando necessário.

## Arquitetura

Tudo está em um único arquivo: `GeradorPlantaBaixa.py`, classe `CroquiApp`.

- Canvas do Tkinter (`self.canvas`) representa um plano cartesiano de
  8000x8000 unidades, centrado em (0,0). Zoom e pan são feitos via
  `canvas.scale`/`canvas.scan_mark`/`canvas.scan_dragto`.
- Ferramentas (`self.ferramenta_atual`) são "sticky": ao clicar em uma
  ferramenta na barra lateral (ou usar o atalho de teclado), ela permanece
  ativa até o usuário escolher outra. Ver `set_ferramenta`.
- Histórico de undo/redo (`self.historico` / `self.futuro`) guarda ações
  como dicionários com `tipo` (`add`, `delete`, `move`, `trim`,
  `edit_texto`) e é limitado por `MAX_HISTORICO`.
- Itens do canvas usam tags para agrupamento: `desenho` (tudo que pode ser
  desfeito/apagado), tipo do item (`parede`, `porta`, `texto`,
  `escada_caracol`...), tipo de traço (`tipo_parede`, `tipo_fina`,
  `tipo_arco`, `tipo_tracejada`) para reescalar espessuras em lote no zoom,
  e `bloco_N` para agrupar itens compostos (porta = linha + arco; escada =
  vários itens) que devem mover/apagar juntos.

## Ferramentas disponíveis

| Ferramenta | Atalho | Descrição |
|---|---|---|
| Ponteiro | `s` | Ferramenta padrão ao abrir o app. Não desenha nada ao clicar — usada para navegar/selecionar sem risco de criar elementos sem querer. |
| Parede (`linha`) | `w` depois `a` | Linha grossa (`espessura_parede`). |
| Linha Fina | `l` | Linha fina (`espessura_fina`). |
| Tracejada | `d` | Linha fina tracejada. |
| Porta | `p` | Linha + arco (bloco). Espaço inverte o lado de abertura (`inverter_porta`). |
| Escada Caracol | `e` | Desenho paramétrico (bloco de vários itens). |
| Trim (Cortar) | `c` | Corta um segmento de parede no ponto clicado, calculando interseções com outras paredes/portas próximas. |
| Texto | `t` | Ver seção "Texto" abaixo. |
| Mover | `m` | Move o item (ou bloco) sob o cursor. |
| Borracha | `b` | Apaga (oculta) itens sob o cursor. |

## Texto

- Clique com a ferramenta "Texto" ativa (e fora de um texto já existente)
  abre uma caixa (`abrir_caixa_texto`) para digitar o conteúdo, escolher o
  **tamanho da fonte** e a **rotação** (0–359°, usando a opção `angle` dos
  itens de texto do canvas, suportada desde Tk 8.6).
- **Duplo clique** sobre qualquer texto já inserido — com qualquer
  ferramenta ativa — abre a mesma caixa pré-preenchida com o texto, tamanho
  e rotação atuais para edição (`duplo_clique_texto`). Salvar com o campo
  vazio apaga o texto (via ação `delete` do histórico).
- O último tamanho de fonte e a última rotação usados ficam guardados em
  `self.ultimo_tamanho_fonte` / `self.ultima_rotacao_texto` e pré-preenchem
  a próxima caixa de texto criada.
- Edições de texto existente geram uma ação `edit_texto` no histórico
  (guarda estado "antes" e "depois" de texto/tamanho/ângulo) para suportar
  undo/redo (`aplicar_estado_texto`).
- O tamanho de fonte "base" (sem zoom) fica guardado na tag
  `fontsize_<N>` de cada item de texto; `aplicar_zoom` recalcula o tamanho
  visível multiplicando pelo `zoom_factor` atual.

## Convenções

- Nomes de métodos/variáveis em português, seguindo o padrão já existente
  no arquivo.
- Sem dependências externas além do Tkinter padrão; Pillow é opcional e
  guardado atrás do flag `TEM_PILLOW`.
