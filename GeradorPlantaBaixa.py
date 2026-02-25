import tkinter as tk
import tkinter.simpledialog as sd
import tkinter.filedialog as fd
import math

# --- CORREÇÃO DE DPI PARA MÚLTIPLOS MONITORES NO WINDOWS ---
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

TEM_PILLOW = False
try:
    from PIL import ImageGrab
    TEM_PILLOW = True
except ImportError:
    pass

CORES = {
    'dia': {'fundo': 'white', 'linha': '#444444', 'grid': '#dddddd', 'texto': 'black', 'porta': 'red', 'escada': 'red', 'eixo': '#bbbbbb'},
    'noite': {'fundo': '#222222', 'linha': '#eeeeee', 'grid': '#333333', 'texto': '#eeeeee', 'porta': '#ff5555', 'escada': '#ff5555', 'eixo': '#555555'}
}

class CroquiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gerador de Croqui - V20.5 (Versão Estável e Clean)")
        
        # Plano cartesiano imenso (8000x8000) centrado no (0,0)
        self.cw = self.ch = 8000
        self.cx_min, self.cx_max = -self.cw // 2, self.cw // 2
        self.cy_min, self.cy_max = -self.ch // 2, self.ch // 2
        
        self.grid_size = 20.0      
        self.zoom_factor = 1.0     
        
        self.ferramenta_atual = 'linha'
        self.espessura_parede = 8 
        self.espessura_fina = 3 
        
        self.modo_noturno = True            
        self.tema_atual = CORES['noite']   
        self.ortogonal_ativo = True        
        self.grid_visivel = True   
        self.flip_porta = 1 
        
        self.block_counter = 0

        self.historico = []
        self.futuro = []
        self.aguardando_a = False 
        
        # Controladores da janela de texto única
        self.janela_texto_ativa = None
        self.salvar_texto_ativo = None

        # --- LAYOUT ---
        self.frame_ferramentas = tk.Frame(root, width=180)
        self.frame_ferramentas.pack(side=tk.LEFT, fill=tk.Y)
        
        self.frame_canvas = tk.Frame(root)
        self.frame_canvas.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=0, pady=0)

        self.canvas = tk.Canvas(self.frame_canvas, bg=self.tema_atual['fundo'], cursor="crosshair", highlightthickness=0)
        self.canvas.pack(expand=True, fill=tk.BOTH)
        
        self.canvas.config(scrollregion=(self.cx_min, self.cy_min, self.cx_max, self.cy_max))

        self.criar_botoes_ferramentas()
        self.desenhar_malha()

        self.inicio_x = self.inicio_y = self.inicio_x_real = self.inicio_y_real = None
        self.linha_atual = self.arco_atual = None
        self.itens_movendo = [] 
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
        
        self.root.after(100, self.arranque_acelerado)

    def arranque_acelerado(self):
        try:
            self.root.state('zoomed')
        except:
            pass
        self.root.update_idletasks() 
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        x_frac = 0.5 - (w / (2 * self.cw))
        y_frac = 0.5 - (h / (2 * self.ch))
        self.canvas.xview_moveto(x_frac)
        self.canvas.yview_moveto(y_frac)

    def criar_botoes_ferramentas(self):
        bg_panel = "#f0f0f0" 
        bg_hover = "#e0e0e0" 
        fg_text = "#333333"  
        font_ui = ("Segoe UI", 10) 
        
        self.frame_ferramentas.config(bg=bg_panel)

        def add_flat_button(parent, text, icon, command, fg_color=fg_text):
            frame = tk.Frame(parent, bg=bg_panel)
            frame.pack(fill=tk.X, pady=2, padx=8) 
            
            lbl_icon = tk.Label(frame, text=icon, bg=bg_panel, fg=fg_color, font=("Segoe UI Emoji", 11))
            lbl_icon.pack(side=tk.LEFT, padx=(2, 6))
            
            btn_text = tk.Button(frame, text=text, command=command, 
                                 bg=bg_panel, activebackground=bg_hover,
                                 fg=fg_color, relief="flat", bd=0,
                                 font=font_ui, anchor="w", cursor="hand2")
            btn_text.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
            
            lbl_icon.bind("<Button-1>", lambda e: command())
            for widget in [frame, lbl_icon, btn_text]:
                widget.bind("<Enter>", lambda e, f=frame, l=lbl_icon, b=btn_text: (f.config(bg=bg_hover), l.config(bg=bg_hover), b.config(bg=bg_hover)))
                widget.bind("<Leave>", lambda e, f=frame, l=lbl_icon, b=btn_text: (f.config(bg=bg_panel), l.config(bg=bg_panel), b.config(bg=bg_panel)))

        def add_separator(parent):
            tk.Frame(parent, height=1, bg="#d0d0d0").pack(fill=tk.X, pady=12, padx=15)

        # --- AÇÕES (Undo/Redo) ---
        frame_undo_redo = tk.Frame(self.frame_ferramentas, bg=bg_panel)
        frame_undo_redo.pack(pady=(20, 5), padx=8, fill=tk.X)
        
        for text, cmd in [("⟲", self.desfazer_acao), ("⟳", self.refazer_acao)]:
            btn = tk.Button(frame_undo_redo, text=text, command=cmd,
                            bg=bg_panel, activebackground=bg_hover, fg=fg_text,
                            relief="flat", bd=0, font=("Segoe UI Symbol", 14), cursor="hand2")
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, ipady=2)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=bg_hover))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=bg_panel))

        add_separator(self.frame_ferramentas)

        # --- FERRAMENTAS DE DESENHO ---
        add_flat_button(self.frame_ferramentas, "Parede", "✏️", lambda: self.set_ferramenta('linha'))
        add_flat_button(self.frame_ferramentas, "Linha Fina", "📏", lambda: self.set_ferramenta('linha_fina'))
        add_flat_button(self.frame_ferramentas, "Tracejada", "✂️", lambda: self.set_ferramenta('linha_tracejada'))
        add_flat_button(self.frame_ferramentas, "Porta", "🚪", lambda: self.set_ferramenta('porta'))
        add_flat_button(self.frame_ferramentas, "Escada Caracol", "🌀", lambda: self.set_ferramenta('escada_caracol'))
        add_flat_button(self.frame_ferramentas, "Trim (Cortar)", "🔪", lambda: self.set_ferramenta('trim'))
        add_flat_button(self.frame_ferramentas, "Texto", "🔤", lambda: self.set_ferramenta('texto'))
        
        add_separator(self.frame_ferramentas)

        # --- EDIÇÃO E CONTROLE ---
        add_flat_button(self.frame_ferramentas, "Mover", "✋", lambda: self.set_ferramenta('mover_objeto'))
        add_flat_button(self.frame_ferramentas, "Borracha", "🧼", lambda: self.set_ferramenta('borracha'))
        
        self.btn_ortogonal_frame = tk.Frame(self.frame_ferramentas, bg=bg_panel)
        self.btn_ortogonal_frame.pack(fill=tk.X, pady=2, padx=8)
        self.lbl_orto_icon = tk.Label(self.btn_ortogonal_frame, text="📐", bg=bg_panel, fg=fg_text, font=("Segoe UI Emoji", 11))
        self.lbl_orto_icon.pack(side=tk.LEFT, padx=(2, 6))
        self.btn_ortogonal = tk.Button(self.btn_ortogonal_frame, text="Trava 90°: ON", command=self.alternar_ortogonal, 
                                       bg=bg_panel, activebackground=bg_hover, fg=fg_text, relief="flat", bd=0, font=font_ui, anchor="w", cursor="hand2")
        self.btn_ortogonal.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self.lbl_orto_icon.bind("<Button-1>", lambda e: self.alternar_ortogonal())
        for w in [self.btn_ortogonal_frame, self.lbl_orto_icon, self.btn_ortogonal]:
            w.bind("<Enter>", lambda e, f=self.btn_ortogonal_frame, l=self.lbl_orto_icon, b=self.btn_ortogonal: (f.config(bg=bg_hover), l.config(bg=bg_hover), b.config(bg=bg_hover)))
            w.bind("<Leave>", lambda e, f=self.btn_ortogonal_frame, l=self.lbl_orto_icon, b=self.btn_ortogonal: (f.config(bg=bg_panel), l.config(bg=bg_panel), b.config(bg=bg_panel)))

        self.btn_grid_frame = tk.Frame(self.frame_ferramentas, bg=bg_panel)
        self.btn_grid_frame.pack(fill=tk.X, pady=2, padx=8)
        self.lbl_grid_icon = tk.Label(self.btn_grid_frame, text="🌐", bg=bg_panel, fg=fg_text, font=("Segoe UI Emoji", 11))
        self.lbl_grid_icon.pack(side=tk.LEFT, padx=(2, 6))
        self.btn_grid = tk.Button(self.btn_grid_frame, text="Malha: ON", command=self.alternar_malha, 
                                  bg=bg_panel, activebackground=bg_hover, fg=fg_text, relief="flat", bd=0, font=font_ui, anchor="w", cursor="hand2")
        self.btn_grid.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self.lbl_grid_icon.bind("<Button-1>", lambda e: self.alternar_malha())
        for w in [self.btn_grid_frame, self.lbl_grid_icon, self.btn_grid]:
            w.bind("<Enter>", lambda e, f=self.btn_grid_frame, l=self.lbl_grid_icon, b=self.btn_grid: (f.config(bg=bg_hover), l.config(bg=bg_hover), b.config(bg=bg_hover)))
            w.bind("<Leave>", lambda e, f=self.btn_grid_frame, l=self.lbl_grid_icon, b=self.btn_grid: (f.config(bg=bg_panel), l.config(bg=bg_panel), b.config(bg=bg_panel)))

        add_separator(self.frame_ferramentas)

        # --- VISUALIZAÇÃO E ARQUIVO ---
        add_flat_button(self.frame_ferramentas, "Expandir Tela", "➕", lambda: self.redimensionar_tela(2000))
        add_flat_button(self.frame_ferramentas, "Modo Noturno", "🌗", self.alternar_modo_noturno)
        add_flat_button(self.frame_ferramentas, "Exportar PNG", "💾", self.exportar_png)
        
        add_separator(self.frame_ferramentas)
        
        add_flat_button(self.frame_ferramentas, "Limpar Tudo", "🗑️", self.limpar_tudo, fg_color="#c0392b")

    def gerenciar_atalhos(self, event):
        if isinstance(event.widget, tk.Text) or isinstance(event.widget, tk.Spinbox): return
        if event.keysym == 'F7': self.alternar_ortogonal(); return
        if event.keysym == 'plus' or (event.keysym == 'equal' and event.state & 0x0001): self.redimensionar_tela(2000); return

        char = event.char.lower()
        if not char: return

        if char == 'w': self.aguardando_a = True; return 
        if self.aguardando_a:
            if char == 'a': self.set_ferramenta('linha')
            self.aguardando_a = False; return

        if char == 'l': self.set_ferramenta('linha_fina')
        elif char == 'd': self.set_ferramenta('linha_tracejada')
        elif char == 'p': self.set_ferramenta('porta')
        elif char == 'e': self.set_ferramenta('escada_caracol')
        elif char == 'c': self.set_ferramenta('trim')
        elif char == 't': self.set_ferramenta('texto')
        elif char == 'm': self.set_ferramenta('mover_objeto')
        elif char == 'b': self.set_ferramenta('borracha')

    # --- TEXTO AUTOMÁTICO - FIX SINGLETON ---
    def abrir_caixa_texto(self, x_tela, y_tela, x_canvas, y_canvas):
        # Garante que se tiver outra caixa aberta, ela seja salva e fechada
        if getattr(self, 'janela_texto_ativa', None) and self.janela_texto_ativa.winfo_exists():
            try:
                self.salvar_texto_ativo()
            except:
                pass

        top = tk.Toplevel(self.root)
        self.janela_texto_ativa = top
        top.title("Texto")
        top.geometry(f"+{x_tela}+{y_tela}")
        top.attributes('-topmost', True)
        
        txt = tk.Text(top, width=22, height=3, font=("Arial", 11), wrap=tk.WORD)
        txt.pack(padx=5, pady=5)
        txt.focus_force() 

        frame_ctrl = tk.Frame(top)
        frame_ctrl.pack(fill=tk.X, padx=5, pady=(0,5))
        
        tk.Label(frame_ctrl, text="Tamanho da Fonte:").pack(side=tk.LEFT)
        var_tamanho = tk.IntVar(value=12)
        spin_tam = tk.Spinbox(frame_ctrl, from_=6, to=72, textvariable=var_tamanho, width=5)
        spin_tam.pack(side=tk.LEFT, padx=(5,5))

        salvo = False
        def salvar(event=None):
            nonlocal salvo
            if salvo: return
            salvo = True
            
            conteudo = txt.get("1.0", tk.END).strip()
            tamanho = var_tamanho.get()
            
            self.janela_texto_ativa = None
            self.salvar_texto_ativo = None
            
            top.destroy()
            if conteudo:
                tam_zoom = max(1, int(tamanho * self.zoom_factor))
                id_texto = self.canvas.create_text(
                    x_canvas, y_canvas, 
                    text=conteudo, 
                    font=("Arial", tam_zoom, "bold"), 
                    fill=self.tema_atual['texto'], 
                    tags=("desenho", "texto", f"fontsize_{tamanho}"), 
                    justify=tk.CENTER
                )
                self.registrar_acao({'tipo': 'add', 'itens': [id_texto]})
                
        self.salvar_texto_ativo = salvar
        
        def on_focus_out(event):
            top.after(150, check_focus)
            
        def check_focus():
            try:
                focused = self.root.focus_get()
                if focused is None or not str(focused).startswith(str(top)):
                    salvar()
            except Exception:
                pass

        top.bind("<FocusOut>", on_focus_out)

        def on_enter(e):
            if not e.state & 0x0001: salvar(); return "break"

        txt.bind("<Return>", on_enter)
        top.bind("<Escape>", lambda e: top.destroy())

    def atualizar_todas_juncoes(self):
        self.canvas.delete("juncao")
        paredes = self.canvas.find_withtag("parede")
        pontos = {}
        for i in paredes:
            if str(self.canvas.itemcget(i, 'state')) == 'hidden': continue
            tags = self.canvas.gettags(i)
            if "linha_fina" in tags or "linha_tracejada" in tags: continue
            
            c = self.canvas.coords(i)
            if len(c) == 4:
                x1, y1, x2, y2 = round(c[0], 2), round(c[1], 2), round(c[2], 2), round(c[3], 2)
                is_h = abs(y1 - y2) < 1
                is_v = abs(x1 - x2) < 1
                
                p1, p2 = (x1, y1), (x2, y2)
                
                if p1 not in pontos: pontos[p1] = {'h': False, 'v': False}
                if is_h: pontos[p1]['h'] = True
                if is_v: pontos[p1]['v'] = True
                
                if p2 not in pontos: pontos[p2] = {'h': False, 'v': False}
                if is_h: pontos[p2]['h'] = True
                if is_v: pontos[p2]['v'] = True

        r_zoom = (self.espessura_parede * self.zoom_factor) / 2
        cor = self.tema_atual['linha']
        for p, orient in pontos.items():
            if orient['h'] and orient['v']:
                self.canvas.create_oval(p[0]-r_zoom, p[1]-r_zoom, p[0]+r_zoom, p[1]+r_zoom, 
                                        fill=cor, outline="", 
                                        tags=("desenho", "juncao"))

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
            d_dash = self.canvas.itemcget(item_id, "dash") 
            
            for i in range(len(pontos_unicos) - 1):
                if i == segmento_removido_idx: continue
                p1, p2 = pontos_unicos[i], pontos_unicos[i+1]
                if math.hypot(p2[0]-p1[0], p2[1]-p1[1]) > 1:
                    nl = self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], width=w, fill=cor, dash=d_dash, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tags)
                    novas_linhas.append(nl)
            
            self.registrar_acao({'tipo': 'trim', 'original': item_id, 'novos': novas_linhas})
            self.atualizar_todas_juncoes()

    def inverter_porta(self, event=None):
        if self.ferramenta_atual == 'porta' and self.arco_atual: self.flip_porta *= -1

    def registrar_acao(self, acao):
        self.historico.append(acao); self.futuro.clear()

    def desfazer_acao(self, event=None):
        if not self.historico: return
        acao = self.historico.pop(); self.futuro.append(acao)
        if acao['tipo'] == 'add':
            for i in acao['itens']: self.canvas.itemconfig(i, state='hidden')
        elif acao['tipo'] == 'delete':
            for i in acao['itens']: self.canvas.itemconfig(i, state='normal')
        elif acao['tipo'] == 'move': 
            for i in acao['itens']: self.canvas.move(i, -acao['dx'], -acao['dy'])
        elif acao['tipo'] == 'trim':
            self.canvas.itemconfig(acao['original'], state='normal')
            for nl in acao['novos']: self.canvas.itemconfig(nl, state='hidden')
            
        self.atualizar_todas_juncoes()

    def refazer_acao(self, event=None):
        if not self.futuro: return
        acao = self.futuro.pop(); self.historico.append(acao)
        if acao['tipo'] == 'add':
            for i in acao['itens']: self.canvas.itemconfig(i, state='normal')
        elif acao['tipo'] == 'delete':
            for i in acao['itens']: self.canvas.itemconfig(i, state='hidden')
        elif acao['tipo'] == 'move': 
            for i in acao['itens']: self.canvas.move(i, acao['dx'], acao['dy'])
        elif acao['tipo'] == 'trim':
            self.canvas.itemconfig(acao['original'], state='hidden')
            for nl in acao['novos']: self.canvas.itemconfig(nl, state='normal')
            
        self.atualizar_todas_juncoes()

    def alternar_ortogonal(self):
        self.ortogonal_ativo = not self.ortogonal_ativo
        self.btn_ortogonal.config(text=f"Trava 90°: {'ON' if self.ortogonal_ativo else 'OFF'}")

    def alternar_malha(self):
        self.grid_visivel = not self.grid_visivel
        self.canvas.itemconfig("grid", state="normal" if self.grid_visivel else "hidden")
        self.btn_grid.config(text=f"Malha: {'ON' if self.grid_visivel else 'OFF'}")

    def alternar_modo_noturno(self):
        self.modo_noturno = not self.modo_noturno
        self.tema_atual = CORES['noite'] if self.modo_noturno else CORES['dia']
        self.canvas.config(bg=self.tema_atual['fundo'])
        self.desenhar_malha()
        for i in self.canvas.find_withtag("parede"): self.canvas.itemconfig(i, fill=self.tema_atual['linha'])
        for i in self.canvas.find_withtag("linha_tracejada"): self.canvas.itemconfig(i, fill=self.tema_atual['linha'])
        for i in self.canvas.find_withtag("juncao"): self.canvas.itemconfig(i, fill=self.tema_atual['linha'], outline="")
        for i in self.canvas.find_withtag("texto"): self.canvas.itemconfig(i, fill=self.tema_atual['texto'])
        for i in self.canvas.find_withtag("porta"):
            if self.canvas.type(i) == "line": self.canvas.itemconfig(i, fill=self.tema_atual['linha'])
            elif self.canvas.type(i) == "arc": self.canvas.itemconfig(i, outline=self.tema_atual['porta'])
        for i in self.canvas.find_withtag("escada_caracol"):
            if self.canvas.type(i) == "line" and self.canvas.itemcget(i, "arrow") != "": self.canvas.itemconfig(i, fill=self.tema_atual['escada'])
            elif self.canvas.type(i) == "line": self.canvas.itemconfig(i, fill=self.tema_atual['escada'])
            else: self.canvas.itemconfig(i, outline=self.tema_atual['escada'])
        self.atualizar_todas_juncoes()

    def redimensionar_tela(self, v):
        self.cw += v
        self.ch += v
        self.cx_min, self.cx_max = -self.cw // 2, self.cw // 2
        self.cy_min, self.cy_max = -self.ch // 2, self.ch // 2
        self.canvas.config(scrollregion=(self.cx_min, self.cy_min, self.cx_max, self.cy_max))
        self.desenhar_malha()

    def set_ferramenta(self, f):
        if getattr(self, 'janela_texto_ativa', None) and self.janela_texto_ativa.winfo_exists():
            try: self.salvar_texto_ativo()
            except: pass
            
        self.ferramenta_atual = f
        cursores = {'borracha': 'dot box', 'texto': 'xterm', 'mover_objeto': 'fleur', 'trim': 'pencil', 'escada_caracol': 'crosshair'}
        self.canvas.config(cursor=cursores.get(f, 'crosshair'))

    def desenhar_malha(self):
        self.canvas.delete("grid")
        gs = int(self.grid_size)
        if gs < 5: return 
        color = self.tema_atual['grid']
        
        start_x = (self.cx_min // gs) * gs
        start_y = (self.cy_min // gs) * gs
        
        for i in range(start_x, self.cx_max + 1, gs): 
            self.canvas.create_line(i, self.cy_min, i, self.cy_max, fill=color, tags="grid", dash=(2, 4))
        for j in range(start_y, self.cy_max + 1, gs): 
            self.canvas.create_line(self.cx_min, j, self.cx_max, j, fill=color, tags="grid", dash=(2, 4))
            
        color_axis = self.tema_atual['eixo']
        self.canvas.create_line(0, self.cy_min, 0, self.cy_max, fill=color_axis, tags="grid", width=1.5)
        self.canvas.create_line(self.cx_min, 0, self.cx_max, 0, fill=color_axis, tags="grid", width=1.5)
            
        self.canvas.tag_lower("grid")
        if not self.grid_visivel:
            self.canvas.itemconfig("grid", state="hidden")

    def snap(self, v): return round(v / self.grid_size) * self.grid_size

    def desenhar_escada_caracol_temp(self, xc, yc, r_externo):
        for item in self.itens_escada_atual: self.canvas.delete(item)
        self.itens_escada_atual = []
        if r_externo < self.grid_size: return 
        r_interno = r_externo * 0.2
        cor_escada = self.tema_atual['escada']
        
        w_fina = self.espessura_fina * self.zoom_factor
        w_grossa = 2 * self.zoom_factor
        
        miolo = self.canvas.create_oval(xc-r_interno, yc-r_interno, xc+r_interno, yc+r_interno, outline=cor_escada, width=w_grossa, tags=("desenho", "escada_caracol", "esc_arco"))
        self.itens_escada_atual.append(miolo)
        corrimao = self.canvas.create_arc(xc-r_externo, yc-r_externo, xc+r_externo, yc+r_externo, start=0, extent=270, style=tk.ARC, outline=cor_escada, width=w_grossa, tags=("desenho", "escada_caracol", "esc_arco"))
        self.itens_escada_atual.append(corrimao)
        for i in range(13):
            ang_rad = math.radians(i * (270/12))
            x1, y1 = xc + r_interno * math.cos(ang_rad), yc - r_interno * math.sin(ang_rad) 
            x2, y2 = xc + r_externo * math.cos(ang_rad), yc - r_externo * math.sin(ang_rad)
            degrau = self.canvas.create_line(x1, y1, x2, y2, fill=cor_escada, width=w_fina, tags=("desenho", "escada_caracol", "esc_degrau"))
            self.itens_escada_atual.append(degrau)
            if i == 0:
                mx, my = (x1+x2)/2, (y1+y2)/2
                pa = ang_rad + math.pi/2
                fx, fy = mx + (r_externo-r_interno)*0.2 * math.cos(pa), my - (r_externo-r_interno)*0.2 * math.sin(pa)
                fl = self.canvas.create_line(mx, my, fx, fy, arrow=tk.LAST, fill=cor_escada, width=w_grossa, tags=("desenho", "escada_caracol", "esc_seta"))
                self.itens_escada_atual.append(fl)

    def clicar(self, event):
        if getattr(self, 'janela_texto_ativa', None) and self.janela_texto_ativa.winfo_exists():
            try: self.salvar_texto_ativo()
            except: pass
            
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        x_s, y_s = self.snap(cx), self.snap(cy)
        
        if self.ferramenta_atual in ['linha', 'linha_fina', 'linha_tracejada']:
            self.inicio_x, self.inicio_y = x_s, y_s
            self.inicio_x_real, self.inicio_y_real = event.x, event.y
            
            w_base = self.espessura_parede if self.ferramenta_atual == 'linha' else self.espessura_fina
            w = w_base * self.zoom_factor
            tags_f = ("desenho", "parede", self.ferramenta_atual)
            d_dash = (max(2, int(6 * self.zoom_factor)), max(2, int(6 * self.zoom_factor))) if self.ferramenta_atual == 'linha_tracejada' else ""
            
            self.linha_atual = self.canvas.create_line(x_s, y_s, x_s, y_s, width=w, dash=d_dash, fill=self.tema_atual['linha'], capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tags_f)
            
        elif self.ferramenta_atual == 'porta':
            self.inicio_x, self.inicio_y, self.inicio_x_real, self.inicio_y_real = x_s, y_s, event.x, event.y
            w_linha = self.espessura_fina * self.zoom_factor
            w_arco = 2 * self.zoom_factor
            self.linha_atual = self.canvas.create_line(x_s, y_s, x_s, y_s, width=w_linha, fill=self.tema_atual['linha'], tags=("desenho", "porta", "porta_linha"))
            self.arco_atual = self.canvas.create_arc(x_s, y_s, x_s, y_s, style=tk.ARC, outline=self.tema_atual['porta'], width=w_arco, tags=("desenho", "porta", "porta_arco"))
        
        elif self.ferramenta_atual == 'escada_caracol': 
            self.inicio_x, self.inicio_y, self.itens_escada_atual = x_s, y_s, []
        
        elif self.ferramenta_atual == 'trim': 
            self.executar_trim(event)
        
        elif self.ferramenta_atual == 'texto': 
            self.abrir_caixa_texto(event.x_root, event.y_root, x_s, y_s)
        
        elif self.ferramenta_atual == 'mover_objeto':
            itens = self.canvas.find_overlapping(cx-10, cy-10, cx+10, cy+10)
            item_valido = None
            for i in reversed(itens): 
                if "desenho" in self.canvas.gettags(i) and "juncao" not in self.canvas.gettags(i):
                    if str(self.canvas.itemcget(i, 'state')) != 'hidden':
                        item_valido = i
                        break
            if item_valido:
                self.move_start_x, self.move_start_y, self.dx_total, self.dy_total = cx, cy, 0, 0
                tags = self.canvas.gettags(item_valido)
                bloco_tag = next((t for t in tags if t.startswith("bloco_")), None)
                if bloco_tag:
                    self.itens_movendo = self.canvas.find_withtag(bloco_tag)
                else:
                    self.itens_movendo = [item_valido]
                
        elif self.ferramenta_atual == 'borracha': 
            self.apagados_na_sessao = []
            self.apagar_item(event)

    def arrastar(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.ferramenta_atual in ['linha', 'linha_fina', 'linha_tracejada'] and self.linha_atual:
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
        elif self.ferramenta_atual == 'mover_objeto' and self.itens_movendo:
            dx, dy = cx - self.move_start_x, cy - self.move_start_y
            for item in self.itens_movendo:
                self.canvas.move(item, dx, dy)
            self.dx_total += dx; self.dy_total += dy; self.move_start_x, self.move_start_y = cx, cy
        elif self.ferramenta_atual == 'borracha': self.apagar_item(event)

    def soltar(self, event):
        if self.ferramenta_atual in ['linha', 'linha_fina', 'linha_tracejada'] and self.linha_atual:
            self.registrar_acao({'tipo': 'add', 'itens': [self.linha_atual]})
            self.linha_atual = None
            self.atualizar_todas_juncoes()
        elif self.ferramenta_atual == 'porta' and self.linha_atual:
            self.block_counter += 1
            tag_bloco = f"bloco_{self.block_counter}"
            self.canvas.addtag_withtag(tag_bloco, self.linha_atual)
            self.canvas.addtag_withtag(tag_bloco, self.arco_atual)
            self.registrar_acao({'tipo': 'add', 'itens': [self.linha_atual, self.arco_atual]})
            self.linha_atual = self.arco_atual = None
        elif self.ferramenta_atual == 'escada_caracol' and self.itens_escada_atual:
            self.block_counter += 1
            tag_bloco = f"bloco_{self.block_counter}"
            for item in self.itens_escada_atual:
                self.canvas.addtag_withtag(tag_bloco, item)
            self.registrar_acao({'tipo': 'add', 'itens': self.itens_escada_atual})
            self.itens_escada_atual = []
        elif self.ferramenta_atual == 'mover_objeto' and self.itens_movendo:
            if self.dx_total or self.dy_total: 
                self.registrar_acao({'tipo': 'move', 'itens': list(self.itens_movendo), 'dx': self.dx_total, 'dy': self.dy_total})
                self.atualizar_todas_juncoes()
            self.itens_movendo = []
        elif self.ferramenta_atual == 'borracha' and self.apagados_na_sessao:
            self.registrar_acao({'tipo': 'delete', 'itens': list(set(self.apagados_na_sessao))})
            self.apagados_na_sessao = []

    def apagar_item(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        itens_apagados_agora = []
        
        for i in self.canvas.find_overlapping(cx-10, cy-10, cx+10, cy+10):
            if str(self.canvas.itemcget(i, 'state')) == 'hidden': continue
            tags = self.canvas.gettags(i)
            if "desenho" in tags and "juncao" not in tags:
                bloco_tag = next((t for t in tags if t.startswith("bloco_")), None)
                if bloco_tag:
                    for bi in self.canvas.find_withtag(bloco_tag):
                        if str(self.canvas.itemcget(bi, 'state')) != 'hidden' and bi not in itens_apagados_agora:
                            self.canvas.itemconfig(bi, state='hidden')
                            itens_apagados_agora.append(bi)
                else:
                    if i not in itens_apagados_agora:
                        self.canvas.itemconfig(i, state='hidden')
                        itens_apagados_agora.append(i)
                        
        if itens_apagados_agora:
            self.apagados_na_sessao.extend(itens_apagados_agora)
            self.atualizar_todas_juncoes()

    def iniciar_pan(self, e): self.canvas.config(cursor="fleur"); self.canvas.scan_mark(e.x, e.y)
    def arrastar_pan(self, e): self.canvas.scan_dragto(e.x, e.y, gain=1)
    def soltar_pan(self, e): self.set_ferramenta(self.ferramenta_atual)
    
    def usar_zoom_mouse(self, e): self.aplicar_zoom(1.1 if e.delta > 0 else 0.9)
    
    def aplicar_zoom(self, f):
        if 5 <= self.grid_size * f <= 100:
            self.grid_size *= f
            self.zoom_factor *= f
            self.canvas.scale("desenho", 0, 0, f, f)
            self.desenhar_malha()

            for i in self.canvas.find_withtag("desenho"):
                tags = self.canvas.gettags(i)
                tipo = self.canvas.type(i)

                if tipo in ["line", "arc"]:
                    base_w = 2
                    if "parede" in tags and "linha" in tags: base_w = self.espessura_parede
                    elif "linha_fina" in tags or "linha_tracejada" in tags: base_w = self.espessura_fina
                    elif "porta" in tags: base_w = 2 if "porta_arco" in tags else self.espessura_fina
                    elif "escada_caracol" in tags: base_w = self.espessura_fina if "esc_degrau" in tags else 2
                    
                    self.canvas.itemconfig(i, width=base_w * self.zoom_factor)
                    
                    if "linha_tracejada" in tags:
                        d_len = max(2, int(6 * self.zoom_factor))
                        self.canvas.itemconfig(i, dash=(d_len, d_len))

                elif tipo == "text":
                    base_size = 12
                    for t in tags:
                        if t.startswith("fontsize_"): base_size = int(t.split("_")[1])
                    new_size = max(1, int(base_size * self.zoom_factor))
                    self.canvas.itemconfig(i, font=("Arial", new_size, "bold"))
            
            self.atualizar_todas_juncoes()

    def exportar_png(self):
        if not TEM_PILLOW: return
        caminho = fd.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
        if not caminho: return
        
        estava_no_escuro = self.modo_noturno
        if estava_no_escuro: self.alternar_modo_noturno()
        
        self.canvas.itemconfig("grid", state="hidden")
        self.root.update() 
        
        try:
            x = self.canvas.winfo_rootx()
            y = self.canvas.winfo_rooty()
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            
            try:
                img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
            except TypeError:
                img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            img.save(caminho)
            tk.messagebox.showinfo("Sucesso", "Croqui exportado com sucesso!")
        except Exception as e: 
            tk.messagebox.showerror("Erro", f"Falha ao exportar PNG:\n{e}")
        finally:
            if estava_no_escuro: self.alternar_modo_noturno()
            else: 
                if self.grid_visivel: self.canvas.itemconfig("grid", state="normal")
            self.root.update()

    def limpar_tudo(self):
        if tk.messagebox.askyesno("Limpar", "Tem certeza? Isso apaga todo o desenho."):
            self.canvas.delete("desenho"); self.historico.clear(); self.futuro.clear()

if __name__ == "__main__":
    app = CroquiApp(tk.Tk())
    app.root.mainloop()