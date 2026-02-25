import tkinter as tk
import tkinter.simpledialog as sd
import tkinter.filedialog as fd
import math

# Tenta importar Pillow
TEM_PILLOW = False
try:
    from PIL import ImageGrab
    TEM_PILLOW = True
except ImportError:
    pass

CORES = {
    'dia': {'fundo': 'white', 'linha': '#444444', 'grid': '#dddddd', 'texto': 'black', 'porta': 'red', 'escada': 'red'},
    'noite': {'fundo': '#222222', 'linha': '#eeeeee', 'grid': '#333333', 'texto': '#eeeeee', 'porta': '#ff5555', 'escada': '#ff5555'}
}

class CroquiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gerador de Croqui - V19.1 (Corrigido)")
        self.root.state('zoomed') 

        self.cw, self.ch = 2500, 2000           
        self.grid_size = 20.0     
        self.ferramenta_atual = 'linha'
        self.espessura_parede = 8 
        self.espessura_fina = 3 
        
        self.modo_noturno = True           
        self.tema_atual = CORES['noite']   
        self.ortogonal_ativo = True        
        self.flip_porta = 1 

        self.historico = []
        self.futuro = []
        
        self.aguardando_a = False 

        # --- LAYOUT ---
        self.frame_ferramentas = tk.Frame(root, bg="#e0e0e0", width=160)
        self.frame_ferramentas.pack(side=tk.LEFT, fill=tk.Y)
        
        self.frame_canvas = tk.Frame(root)
        self.frame_canvas.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5, pady=5)

        self.canvas = tk.Canvas(self.frame_canvas, bg=self.tema_atual['fundo'], 
                                width=self.cw, height=self.ch, cursor="crosshair", highlightthickness=0)
        self.canvas.pack(expand=True, fill=tk.BOTH)
        self.canvas.config(scrollregion=(0, 0, self.cw, self.ch))

        self.criar_botoes_ferramentas()
        self.desenhar_malha()

        self.inicio_x = self.inicio_y = self.inicio_x_real = self.inicio_y_real = None
        self.linha_atual = self.arco_atual = self.item_movendo = None
        self.itens_escada_atual = [] 
        self.dx_total = self.dy_total = 0
        self.apagados_na_sessao = []

        # --- EVENTOS ---
        self.canvas.bind("<Button-1>", self.clicar)
        self.canvas.bind("<B1-Motion>", self.arrastar)
        self.canvas.bind("<ButtonRelease-1>", self.soltar)
        self.canvas.bind("<MouseWheel>", self.usar_zoom_mouse)
        self.canvas.bind("<ButtonPress-2>", self.iniciar_pan)
        self.canvas.bind("<B2-Motion>", self.arrastar_pan)
        self.canvas.bind("<ButtonRelease-2>", self.soltar_pan)
        self.root.bind("<space>", self.inverter_porta)
        self.root.bind("<Key>", self.gerenciar_atalhos)

    def criar_botoes_ferramentas(self):
        bg_btn = "#e0e0e0"
        
        tk.Label(self.frame_ferramentas, text="AÇÕES", bg=bg_btn, font=("Arial", 9, "bold")).pack(pady=(15,5))
        frame_undo_redo = tk.Frame(self.frame_ferramentas, bg=bg_btn)
        frame_undo_redo.pack(pady=2, padx=5)
        tk.Button(frame_undo_redo, text="⬅️", command=self.desfazer_acao, width=5).pack(side=tk.LEFT, padx=2)
        tk.Button(frame_undo_redo, text="➡️", command=self.refazer_acao, width=5).pack(side=tk.LEFT, padx=2)

        tk.Label(self.frame_ferramentas, text="FERRAMENTAS", bg=bg_btn, font=("Arial", 9, "bold")).pack(pady=(15,5))
        
        tk.Button(self.frame_ferramentas, text="✏️ Parede (WA)", command=lambda: self.set_ferramenta('linha'), width=22, anchor="w").pack(pady=2)
        tk.Button(self.frame_ferramentas, text="📏 Linha Fina (L)", command=lambda: self.set_ferramenta('linha_fina'), width=22, anchor="w").pack(pady=2)
        tk.Button(self.frame_ferramentas, text="🚪 Porta (P)", command=lambda: self.set_ferramenta('porta'), width=22, anchor="w", bg="#e2e3e5").pack(pady=2)
        tk.Button(self.frame_ferramentas, text="🌀 Escada Caracol (E)", command=lambda: self.set_ferramenta('escada_caracol'), width=22, anchor="w", bg="#e2e3e5").pack(pady=2)
        tk.Button(self.frame_ferramentas, text="✂️ Trim (C)", command=lambda: self.set_ferramenta('trim'), width=22, anchor="w", bg="#f8d7da").pack(pady=2)
        tk.Button(self.frame_ferramentas, text="🔤 Texto (T)", command=lambda: self.set_ferramenta('texto'), width=22, anchor="w").pack(pady=2)
        tk.Button(self.frame_ferramentas, text="✋ Mover Texto (M)", command=lambda: self.set_ferramenta('mover_texto'), width=22, anchor="w").pack(pady=2)
        tk.Button(self.frame_ferramentas, text="🧼 Borracha (B)", command=lambda: self.set_ferramenta('borracha'), width=22, anchor="w").pack(pady=2)
        
        tk.Label(self.frame_ferramentas, text="PRANCHETA", bg=bg_btn, font=("Arial", 9, "bold")).pack(pady=(15, 5))
        self.btn_ortogonal = tk.Button(self.frame_ferramentas, text="📐 Trava 90° (F7): ON", command=self.alternar_ortogonal, width=22, anchor="w", bg="#d1e7dd")
        self.btn_ortogonal.pack(pady=2)
        tk.Button(self.frame_ferramentas, text="➕ Expandir (Shift +)", command=lambda: self.redimensionar_tela(500), width=22, anchor="w").pack(pady=2)
        tk.Button(self.frame_ferramentas, text="🌗 Modo Noturno", command=self.alternar_modo_noturno, width=22, anchor="w").pack(pady=2)
        
        tk.Button(self.frame_ferramentas, text="💾 Exportar PNG", command=self.exportar_png, width=22, anchor="w", bg="#fff3cd").pack(pady=(20, 2))
        tk.Button(self.frame_ferramentas, text="🗑️ Limpar Tudo", command=self.limpar_tudo, width=22, anchor="w", fg="red").pack(pady=2)
        
        dicas = "Trim: Arraste p/ cortar.\nPorta: Mouse guia a folha.\nEspaço inverte."
        tk.Label(self.frame_ferramentas, text=dicas, bg=bg_btn, font=("Arial", 8), fg="#555555", justify=tk.LEFT).pack(side=tk.BOTTOM, pady=10)

    # --- GERENCIADOR DE ATALHOS ---
    def gerenciar_atalhos(self, event):
        if isinstance(event.widget, tk.Text): return
        if event.keysym == 'F7': self.alternar_ortogonal(); return
        if event.keysym == 'plus' or (event.keysym == 'equal' and event.state & 0x0001): self.redimensionar_tela(500); return

        char = event.char.lower()
        if not char: return

        if char == 'w': self.aguardando_a = True; return 
        if self.aguardando_a:
            if char == 'a': self.set_ferramenta('linha')
            self.aguardando_a = False; return

        if char == 'l': self.set_ferramenta('linha_fina')
        elif char == 'p': self.set_ferramenta('porta')
        elif char == 'e': self.set_ferramenta('escada_caracol')
        elif char == 'c': self.set_ferramenta('trim')
        elif char == 't': self.set_ferramenta('texto')
        elif char == 'm': self.set_ferramenta('mover_texto')
        elif char == 'b': self.set_ferramenta('borracha')

    # --- TEXTO AUTOMÁTICO ---
    def abrir_caixa_texto(self, x_tela, y_tela, x_canvas, y_canvas):
        top = tk.Toplevel(self.root)
        top.wm_overrideredirect(True)
        top.geometry(f"+{x_tela}+{y_tela}")
        txt = tk.Text(top, width=15, height=2, font=("Arial", 11), wrap=tk.WORD)
        txt.pack()
        txt.focus_set()

        salvo = False
        def salvar(event=None):
            nonlocal salvo
            if salvo: return
            salvo = True
            conteudo = txt.get("1.0", tk.END).strip()
            top.destroy()
            if conteudo:
                id_texto = self.canvas.create_text(x_canvas, y_canvas, text=conteudo.upper(), font=("Arial", 12, "bold"), fill=self.tema_atual['texto'], tags=("desenho", "texto"), justify=tk.CENTER)
                self.registrar_acao({'tipo': 'add', 'itens': [id_texto]})
        
        def on_enter(e):
            if not e.state & 0x0001: salvar(); return "break"

        txt.bind("<FocusOut>", lambda e: salvar())
        txt.bind("<Return>", on_enter)
        txt.bind("<Escape>", lambda e: top.destroy())

    # --- TRIM ENGINE ---
    def ponto_no_segmento(self, P, A, B):
        dAP = math.hypot(P[0]-A[0], P[1]-A[1])
        dPB = math.hypot(B[0]-P[0], B[1]-P[1])
        dAB = math.hypot(B[0]-A[0], B[1]-A[1])
        return abs((dAP + dPB) - dAB) < 1.0

    def calcular_intersecao(self, p1, p2, p3, p4):
        x1, y1, x2, y2 = p1[0], p1[1], p2[0], p2[1]
        x3, y3, x4, y4 = p3[0], p3[1], p4[0], p4[1]
        den = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
        pontos_corte = []
        if abs(den) < 1e-5: return pontos_corte
        t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / den
        u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / den
        if 0.001 < t < 0.999 and -0.001 <= u <= 1.001:
            pontos_corte.append((x1 + t*(x2-x1), y1 + t*(y2-y1)))
        return pontos_corte

    def executar_trim(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        itens_proximos = self.canvas.find_overlapping(cx-15, cy-15, cx+15, cy+15)
        item_id = None
        menor_dist = float('inf')
        for i in itens_proximos:
            if str(self.canvas.itemcget(i, 'state')) == 'hidden': continue
            tags = self.canvas.gettags(i)
            if "parede" in tags:
                coords = self.canvas.coords(i)
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    l2 = (x2 - x1)**2 + (y2 - y1)**2
                    if l2 == 0: dist = math.hypot(cx - x1, cy - y1)
                    else:
                        t = max(0, min(1, ((cx - x1) * (x2 - x1) + (cy - y1) * (y2 - y1)) / l2))
                        dist = math.hypot(cx - (x1 + t * (x2 - x1)), cy - (y1 + t * (y2 - y1)))
                    if dist < menor_dist: menor_dist = dist; item_id = i
        
        if not item_id: return
        tags = self.canvas.gettags(item_id)
        coords = self.canvas.coords(item_id)
        A, B = (coords[0], coords[1]), (coords[2], coords[3])
        todas_linhas = self.canvas.find_withtag("desenho")
        intersecoes = [A, B]
        for outro_id in todas_linhas:
            if outro_id == item_id or str(self.canvas.itemcget(outro_id, 'state')) == 'hidden': continue
            outras_tags = self.canvas.gettags(outro_id)
            if "porta" in outras_tags:
                if self.canvas.type(outro_id) == "arc":
                    c_arc = self.canvas.coords(outro_id)
                    if len(c_arc) == 4:
                        cx_arc, cy_arc = (c_arc[0]+c_arc[2])/2, (c_arc[1]+c_arc[3])/2
                        R_arc = (c_arc[2]-c_arc[0])/2
                        start_arc = float(self.canvas.itemcget(outro_id, "start"))
                        ext_arc = float(self.canvas.itemcget(outro_id, "extent"))
                        H = (cx_arc, cy_arc) 
                        P1 = (cx_arc + R_arc * math.cos(math.radians(start_arc)), cy_arc - R_arc * math.sin(math.radians(start_arc)))
                        P2 = (cx_arc + R_arc * math.cos(math.radians(start_arc + ext_arc)), cy_arc - R_arc * math.sin(math.radians(start_arc + ext_arc)))
                        if self.ponto_no_segmento(H, A, B): intersecoes.append(H)
                        if self.ponto_no_segmento(P1, A, B): intersecoes.append(P1)
                        if self.ponto_no_segmento(P2, A, B): intersecoes.append(P2)
                continue 
            if "parede" in outras_tags:
                ocoords = self.canvas.coords(outro_id)
                if len(ocoords) == 4:
                    pts = self.calcular_intersecao(A, B, (ocoords[0], ocoords[1]), (ocoords[2], ocoords[3]))
                    intersecoes.extend(pts)
        intersecoes = sorted(intersecoes, key=lambda p: math.hypot(p[0]-A[0], p[1]-A[1]))
        pontos_unicos = []
        for p in intersecoes:
            if not pontos_unicos or math.hypot(pontos_unicos[-1][0]-p[0], pontos_unicos[-1][1]-p[1]) > 1: pontos_unicos.append(p)
        segmento_removido_idx = -1
        menor_distancia_seg = float('inf')
        for i in range(len(pontos_unicos) - 1):
            mx, my = (pontos_unicos[i][0] + pontos_unicos[i+1][0]) / 2, (pontos_unicos[i][1] + pontos_unicos[i+1][1]) / 2
            dist = math.hypot(mx - cx, my - cy)
            if dist < menor_distancia_seg: menor_distancia_seg = dist; segmento_removido_idx = i
        if segmento_removido_idx != -1:
            self.canvas.itemconfig(item_id, state='hidden')
            novas_linhas = []
            w, cor = self.canvas.itemcget(item_id, "width"), self.canvas.itemcget(item_id, "fill")
            for i in range(len(pontos_unicos) - 1):
                if i == segmento_removido_idx: continue
                p1, p2 = pontos_unicos[i], pontos_unicos[i+1]
                if math.hypot(p2[0]-p1[0], p2[1]-p1[1]) > 1:
                    nl = self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], width=w, fill=cor, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tags)
                    novas_linhas.append(nl)
                    if "linha_fina" not in tags: self.gerenciar_juncao(p1[0], p1[1]); self.gerenciar_juncao(p2[0], p2[1])
            if "linha_fina" not in tags: self.gerenciar_juncao(A[0], A[1]); self.gerenciar_juncao(B[0], B[1])
            self.registrar_acao({'tipo': 'trim', 'original': item_id, 'novos': novas_linhas, 'pontos': pontos_unicos})

    # --- HISTÓRICO ---
    def inverter_porta(self, event=None):
        if self.ferramenta_atual == 'porta' and self.arco_atual: self.flip_porta *= -1

    def registrar_acao(self, acao):
        self.historico.append(acao); self.futuro.clear()

    def desfazer_acao(self, event=None):
        if not self.historico: return
        acao = self.historico.pop(); self.futuro.append(acao)
        if acao['tipo'] == 'add':
            for i in acao['itens']: self.canvas.itemconfig(i, state='hidden')
            self.atualizar_juncoes_dos_itens(acao['itens'])
        elif acao['tipo'] == 'delete':
            for i in acao['itens']: self.canvas.itemconfig(i, state='normal')
            self.atualizar_juncoes_dos_itens(acao['itens'])
        elif acao['tipo'] == 'move': self.canvas.move(acao['item'], -acao['dx'], -acao['dy'])
        elif acao['tipo'] == 'trim':
            self.canvas.itemconfig(acao['original'], state='normal')
            for nl in acao['novos']: self.canvas.itemconfig(nl, state='hidden')
            for px, py in acao['pontos']: self.gerenciar_juncao(px, py)

    def refazer_acao(self, event=None):
        if not self.futuro: return
        acao = self.futuro.pop(); self.historico.append(acao)
        if acao['tipo'] == 'add':
            for i in acao['itens']: self.canvas.itemconfig(i, state='normal')
            self.atualizar_juncoes_dos_itens(acao['itens'])
        elif acao['tipo'] == 'delete':
            for i in acao['itens']: self.canvas.itemconfig(i, state='hidden')
            self.atualizar_juncoes_dos_itens(acao['itens'])
        elif acao['tipo'] == 'move': self.canvas.move(acao['item'], acao['dx'], acao['dy'])
        elif acao['tipo'] == 'trim':
            self.canvas.itemconfig(acao['original'], state='hidden')
            for nl in acao['novos']: self.canvas.itemconfig(nl, state='normal')
            for px, py in acao['pontos']: self.gerenciar_juncao(px, py)

    # --- CONFIGURAÇÕES E ESTILOS ---
    def alternar_ortogonal(self):
        self.ortogonal_ativo = not self.ortogonal_ativo
        self.btn_ortogonal.config(text=f"📐 Trava 90° (F7): {'LIGADA' if self.ortogonal_ativo else 'DESLIGADA'}", bg="#d1e7dd" if self.ortogonal_ativo else "#f8d7da")

    def alternar_modo_noturno(self):
        self.modo_noturno = not self.modo_noturno
        self.tema_atual = CORES['noite'] if self.modo_noturno else CORES['dia']
        self.canvas.config(bg=self.tema_atual['fundo'])
        self.desenhar_malha()
        for i in self.canvas.find_withtag("parede"): self.canvas.itemconfig(i, fill=self.tema_atual['linha'])
        for i in self.canvas.find_withtag("juncao"): self.canvas.itemconfig(i, fill=self.tema_atual['linha'], outline="")
        for i in self.canvas.find_withtag("texto"): self.canvas.itemconfig(i, fill=self.tema_atual['texto'])
        for i in self.canvas.find_withtag("porta"):
            if self.canvas.type(i) == "line": self.canvas.itemconfig(i, fill=self.tema_atual['linha'])
            elif self.canvas.type(i) == "arc": self.canvas.itemconfig(i, outline=self.tema_atual['porta'])
        for i in self.canvas.find_withtag("escada_caracol"):
            if self.canvas.type(i) == "line" and self.canvas.itemcget(i, "arrow") != "": self.canvas.itemconfig(i, fill=self.tema_atual['escada'])
            elif self.canvas.type(i) == "line": self.canvas.itemconfig(i, fill=self.tema_atual['escada'])
            else: self.canvas.itemconfig(i, outline=self.tema_atual['escada'])

    def redimensionar_tela(self, v):
        self.cw += v; self.ch += v
        self.canvas.config(scrollregion=(0,0, self.cw, self.ch), width=self.cw, height=self.ch); self.desenhar_malha()

    def set_ferramenta(self, f):
        self.ferramenta_atual = f
        cursores = {'borracha': 'dot box', 'texto': 'xterm', 'mover_texto': 'fleur', 'trim': 'pencil', 'escada_caracol': 'crosshair'}
        self.canvas.config(cursor=cursores.get(f, 'crosshair'))

    def desenhar_malha(self):
        self.canvas.delete("grid")
        gs = int(self.grid_size)
        if gs < 5: return 
        color = self.tema_atual['grid']
        for i in range(0, self.cw, gs): self.canvas.create_line(i, 0, i, self.ch, fill=color, tags="grid", dash=(2, 4))
        for j in range(0, self.ch, gs): self.canvas.create_line(0, j, self.cw, j, fill=color, tags="grid", dash=(2, 4))
        self.canvas.tag_lower("grid")

    def snap(self, v): return round(v / self.grid_size) * self.grid_size

    def gerenciar_juncao(self, x, y):
        itens = self.canvas.find_overlapping(x - 2, y - 2, x + 2, y + 2)
        th = tv = False; juncs = []
        for i in itens:
            if str(self.canvas.itemcget(i, 'state')) == 'hidden': continue
            tags = self.canvas.gettags(i)
            if "juncao" in tags: juncs.append(i)
            if "parede" in tags and "linha_fina" not in tags:
                c = self.canvas.coords(i)
                if abs(c[0] - c[2]) < 1: tv = True
                elif abs(c[1] - c[3]) < 1: th = True
        if th and tv:
            if not juncs: self.canvas.create_oval(x-self.espessura_parede/2, y-self.espessura_parede/2, x+self.espessura_parede/2, y+self.espessura_parede/2, fill=self.tema_atual['linha'], outline="", tags=("desenho", "juncao"))
            elif len(juncs) > 1:
                for j in juncs[1:]: self.canvas.delete(j)
        else:
            for j in juncs: self.canvas.delete(j)

    def atualizar_juncoes_dos_itens(self, itens):
        pts = []
        for i in itens:
            if "parede" in self.canvas.gettags(i) and "linha_fina" not in self.canvas.gettags(i):
                c = self.canvas.coords(i); 
                if len(c)==4: pts.extend([(c[0], c[1]), (c[2], c[3])])
        for p in set(pts): self.gerenciar_juncao(p[0], p[1])

    def desenhar_escada_caracol_temp(self, xc, yc, r_externo):
        for item in self.itens_escada_atual: self.canvas.delete(item)
        self.itens_escada_atual = []
        if r_externo < self.grid_size: return 
        r_interno = r_externo * 0.2
        cor_escada = self.tema_atual['escada']
        miolo = self.canvas.create_oval(xc-r_interno, yc-r_interno, xc+r_interno, yc+r_interno, outline=cor_escada, width=2, tags=("desenho", "escada_caracol"))
        self.itens_escada_atual.append(miolo)
        corrimao = self.canvas.create_arc(xc-r_externo, yc-r_externo, xc+r_externo, yc+r_externo, start=0, extent=270, style=tk.ARC, outline=cor_escada, width=2, tags=("desenho", "escada_caracol"))
        self.itens_escada_atual.append(corrimao)
        for i in range(13):
            ang_rad = math.radians(i * (270/12))
            x1, y1 = xc + r_interno * math.cos(ang_rad), yc - r_interno * math.sin(ang_rad) 
            x2, y2 = xc + r_externo * math.cos(ang_rad), yc - r_externo * math.sin(ang_rad)
            degrau = self.canvas.create_line(x1, y1, x2, y2, fill=cor_escada, width=self.espessura_fina, tags=("desenho", "escada_caracol"))
            self.itens_escada_atual.append(degrau)
            if i == 0:
                mx, my = (x1+x2)/2, (y1+y2)/2
                pa = ang_rad + math.pi/2
                fx, fy = mx + (r_externo-r_interno)*0.2 * math.cos(pa), my - (r_externo-r_interno)*0.2 * math.sin(pa)
                fl = self.canvas.create_line(mx, my, fx, fy, arrow=tk.LAST, fill=cor_escada, width=2, tags=("desenho", "escada_caracol"))
                self.itens_escada_atual.append(fl)

    # --- MOUSE EVENTS ---
    def clicar(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        x_s, y_s = self.snap(cx), self.snap(cy)
        if self.ferramenta_atual in ['linha', 'linha_fina']:
            self.inicio_x, self.inicio_y = x_s, y_s
            self.inicio_x_real, self.inicio_y_real = event.x, event.y
            w = self.espessura_parede if self.ferramenta_atual == 'linha' else self.espessura_fina
            tags_f = ("desenho", "parede") if self.ferramenta_atual == 'linha' else ("desenho", "parede", "linha_fina")
            self.linha_atual = self.canvas.create_line(x_s, y_s, x_s, y_s, width=w, fill=self.tema_atual['linha'], capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tags_f)
            if self.ferramenta_atual == 'linha': self.gerenciar_juncao(x_s, y_s)
        elif self.ferramenta_atual == 'porta':
            self.inicio_x, self.inicio_y, self.inicio_x_real, self.inicio_y_real = x_s, y_s, event.x, event.y
            self.linha_atual = self.canvas.create_line(x_s, y_s, x_s, y_s, width=self.espessura_fina, fill=self.tema_atual['linha'], tags=("desenho", "porta"))
            self.arco_atual = self.canvas.create_arc(x_s, y_s, x_s, y_s, style=tk.ARC, outline=self.tema_atual['porta'], width=2, tags=("desenho", "porta"))
        elif self.ferramenta_atual == 'escada_caracol': self.inicio_x, self.inicio_y, self.itens_escada_atual = x_s, y_s, []
        elif self.ferramenta_atual == 'trim': self.executar_trim(event)
        elif self.ferramenta_atual == 'texto': self.abrir_caixa_texto(event.x_root, event.y_root, x_s, y_s)
        elif self.ferramenta_atual == 'mover_texto':
            item = self.canvas.find_closest(cx, cy)
            if item and "texto" in self.canvas.gettags(item[0]):
                self.item_movendo = item[0]
                self.move_start_x, self.move_start_y, self.dx_total, self.dy_total = cx, cy, 0, 0
        elif self.ferramenta_atual == 'borracha': self.apagados_na_sessao = []; self.apagar_item(event)

    def arrastar(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.ferramenta_atual in ['linha', 'linha_fina'] and self.linha_atual:
            x_s, y_s = self.snap(cx), self.snap(cy)
            if self.ortogonal_ativo:
                if abs(event.x - self.inicio_x_real) > abs(event.y - self.inicio_y_real): y_s = self.inicio_y
                else: x_s = self.inicio_x
            self.canvas.coords(self.linha_atual, self.inicio_x, self.inicio_y, x_s, y_s)
        elif self.ferramenta_atual == 'porta' and self.linha_atual:
            x_s, y_s = self.snap(cx), self.snap(cy)
            if self.ortogonal_ativo:
                if abs(event.x - self.inicio_x_real) > abs(event.y - self.inicio_y_real): y_s = self.inicio_y
                else: x_s = self.inicio_x
            self.canvas.coords(self.linha_atual, self.inicio_x, self.inicio_y, x_s, y_s)
            R = math.hypot(x_s - self.inicio_x, y_s - self.inicio_y)
            if R > 0:
                ang_leaf = math.atan2(-(y_s - self.inicio_y), x_s - self.inicio_x)
                ang_open = ang_leaf - math.radians(90 * self.flip_porta)
                self.canvas.coords(self.arco_atual, self.inicio_x - R, self.inicio_y - R, self.inicio_x + R, self.inicio_y + R)
                self.canvas.itemconfig(self.arco_atual, start=math.degrees(ang_open), extent=90 * self.flip_porta)
        elif self.ferramenta_atual == 'escada_caracol':
            r_externo = math.hypot(cx - self.inicio_x, cy - self.inicio_y)
            self.desenhar_escada_caracol_temp(self.inicio_x, self.inicio_y, r_externo)
        elif self.ferramenta_atual == 'trim': self.executar_trim(event)
        elif self.ferramenta_atual == 'mover_texto' and self.item_movendo:
            self.canvas.move(self.item_movendo, cx - self.move_start_x, cy - self.move_start_y)
            self.dx_total += cx - self.move_start_x; self.dy_total += cy - self.move_start_y; self.move_start_x, self.move_start_y = cx, cy
        elif self.ferramenta_atual == 'borracha': self.apagar_item(event)

    def soltar(self, event):
        if self.ferramenta_atual in ['linha', 'linha_fina'] and self.linha_atual:
            c = self.canvas.coords(self.linha_atual)
            if self.ferramenta_atual == 'linha': self.gerenciar_juncao(c[0], c[1]); self.gerenciar_juncao(c[2], c[3]) 
            self.registrar_acao({'tipo': 'add', 'itens': [self.linha_atual]}); self.linha_atual = None
        elif self.ferramenta_atual == 'porta' and self.linha_atual:
            self.registrar_acao({'tipo': 'add', 'itens': [self.linha_atual, self.arco_atual]}); self.linha_atual = self.arco_atual = None
        elif self.ferramenta_atual == 'escada_caracol' and self.itens_escada_atual:
            self.registrar_acao({'tipo': 'add', 'itens': self.itens_escada_atual}); self.itens_escada_atual = []
        elif self.ferramenta_atual == 'mover_texto' and self.item_movendo:
            if self.dx_total or self.dy_total: self.registrar_acao({'tipo': 'move', 'item': self.item_movendo, 'dx': self.dx_total, 'dy': self.dy_total})
            self.item_movendo = None
        elif self.ferramenta_atual == 'borracha' and self.apagados_na_sessao:
            self.registrar_acao({'tipo': 'delete', 'itens': list(set(self.apagados_na_sessao))}); self.apagados_na_sessao = []

    def apagar_item(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for i in self.canvas.find_overlapping(cx-10, cy-10, cx+10, cy+10):
            if str(self.canvas.itemcget(i, 'state')) == 'hidden': continue
            tags = self.canvas.gettags(i)
            if "desenho" in tags and ("parede" in tags or "texto" in tags or "porta" in tags or "escada_caracol" in tags):
                self.canvas.itemconfig(i, state='hidden'); self.apagados_na_sessao.append(i)
                if "parede" in tags and "linha_fina" not in tags: c = self.canvas.coords(i); self.gerenciar_juncao(c[0], c[1]); self.gerenciar_juncao(c[2], c[3])

    def iniciar_pan(self, e): self.canvas.config(cursor="fleur"); self.canvas.scan_mark(e.x, e.y)
    def arrastar_pan(self, e): self.canvas.scan_dragto(e.x, e.y, gain=1)
    def soltar_pan(self, e): self.set_ferramenta(self.ferramenta_atual)
    def usar_zoom_mouse(self, e): self.aplicar_zoom(1.1 if e.delta > 0 else 0.9)
    def aplicar_zoom(self, f):
        if 5 <= self.grid_size * f <= 100:
            self.grid_size *= f
            self.canvas.scale("desenho", 0, 0, f, f)
            self.desenhar_malha()

    def exportar_png(self):
        if not TEM_PILLOW: return
        caminho = fd.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
        if not caminho: return
        estava_no_escuro = self.modo_noturno
        if estava_no_escuro: self.alternar_modo_noturno()
        self.canvas.itemconfig("grid", state="hidden"); self.root.update() 
        try:
            x, y = self.canvas.winfo_rootx(), self.canvas.winfo_rooty()
            ImageGrab.grab().crop((x, y, x + self.canvas.winfo_width(), y + self.canvas.winfo_height())).save(caminho)
        except Exception as e: pass
        finally:
            if estava_no_escuro: self.alternar_modo_noturno()
            else: self.canvas.itemconfig("grid", state="normal")
            self.root.update()

    def limpar_tudo(self):
        if tk.messagebox.askyesno("Limpar", "Tem certeza? Isso apaga todo o histórico."):
            self.canvas.delete("desenho"); self.historico.clear(); self.futuro.clear()

if __name__ == "__main__":
    app = CroquiApp(tk.Tk())
    app.root.mainloop()