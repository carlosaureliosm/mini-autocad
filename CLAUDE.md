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

- Clique com a ferramenta "Texto" ativa abre uma caixa (`abrir_caixa_texto`)
  para digitar o conteúdo e escolher **tamanho da fonte**, **cor** (botão
  "Cor" com seletor do sistema, ou "Auto" para voltar à cor do tema) e
  **rotação** (0–359°, via opção `angle` dos itens de texto do canvas,
  suportada desde Tk 8.6).
- Clicar em cima de um texto já existente com a ferramenta "Texto" (clique
  único), ou dar **duplo clique** sobre qualquer texto já inserido — com
  qualquer ferramenta ativa —, abre a mesma caixa pré-preenchida com o
  texto, tamanho, cor e rotação atuais para edição
  (`duplo_clique_texto`/`clicar`). Salvar com o campo vazio apaga o texto
  (via ação `delete` do histórico).
- O último tamanho de fonte e a última rotação usados ficam guardados em
  `self.ultimo_tamanho_fonte` / `self.ultima_rotacao_texto` e pré-preenchem
  a próxima caixa de texto criada. A cor não é memorizada entre inserções:
  por padrão cada texto novo usa a cor do tema atual (dia/noite), a menos
  que uma cor customizada seja escolhida para ele.
- Edições de texto existente geram uma ação `edit_texto` no histórico
  (guarda estado "antes" e "depois" de texto/tamanho/ângulo/cor via
  `capturar_estado_texto`) para suportar undo/redo (`aplicar_estado_texto`).
- O tamanho de fonte "base" (sem zoom) fica guardado na tag
  `fontsize_<N>` de cada item de texto; `aplicar_zoom` recalcula o tamanho
  visível multiplicando pelo `zoom_factor` atual. Textos com cor
  customizada levam a tag `custom_color`, que faz `alternar_modo_noturno`
  pular a recoloração automática desses itens ao trocar de tema.

## Salvar / Abrir / Exportar

- **Salvar Projeto / Abrir Projeto** (`salvar_arquivo`/`abrir_arquivo`, atalhos
  Ctrl+S/Ctrl+O): formato próprio `.croqui`, um JSON simples com
  `zoom_factor`, `grid_size`, `block_counter`, `modo_noturno` e a lista de
  itens do canvas serializados via `serializar_item`/`recriar_item`. A
  serialização é genérica: para cada item visível com a tag `desenho`
  (exceto `juncao`, que é recalculada), grava `tipo` (`canvas.type`),
  `coords` e todas as opções retornadas por `canvas.itemconfig(item)`
  (fill, width, dash, font, angle, justify, etc.), então recria o item na
  volta chamando o `create_<tipo>` correspondente com essas mesmas opções.
  Isso preserva fielmente cor, rotação, tamanho de fonte e blocos
  (`bloco_N`), mas **não preserva o histórico de undo/redo** — abrir um
  projeto limpa `self.historico`/`self.futuro`.
- **Exportar DXF / Importar DXF** (`exportar_dxf`/`importar_dxf`):
  formato aberto de troca de desenhos da Autodesk (texto simples), que o
  AutoCAD e outros CADs importam nativamente — ao contrário do `.dwg`
  (binário, proprietário, inviável de implementar sem SDK pago). Gera um
  DXF mínimo (`SECTION ENTITIES` ... `ENDSEC EOF`) mapeando: paredes/linhas
  → `LINE`, arcos de porta → `ARC`, círculos de escada caracol → `CIRCLE`,
  textos → `TEXT` (com rotação no grupo 50). As coordenadas são divididas
  por `zoom_factor` (que cresce/decresce junto com `grid_size`, então
  `coord / zoom_factor` dá a posição "lógica" independente do zoom atual)
  e o eixo Y é invertido (`-y`) porque o canvas do Tk cresce para baixo
  enquanto DXF/CAD usam Y crescendo para cima; os ângulos de arco/texto já
  são gravados na mesma convenção CCW visual usada internamente pelo app,
  então não precisam de ajuste de sinal. A importação é um parser DXF
  simplificado (só entende `LINE`/`ARC`/`CIRCLE`/`TEXT`; ignora
  `POLYLINE`, blocos, splines etc. com aviso) — feito para reabrir DXFs
  exportados pelo próprio app e, de forma best-effort, DXFs simples vindos
  de outros programas.

## Convenções

- Nomes de métodos/variáveis em português, seguindo o padrão já existente
  no arquivo.
- Sem dependências externas além do Tkinter padrão; Pillow é opcional e
  guardado atrás do flag `TEM_PILLOW`.
