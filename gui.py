import os
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import re
import subprocess

from ai_client import AIClient
from formatter import TextFormatter
from tts_engine import TTSEngine
from european_tts import EuropeanTTSEngine
from chinese_tts import ChineseTTSEngine
from korean_tts import KoreanTTSEngine
from stt_engine import STTEngine
from dictionary_client import DictionaryClient
import config

# --- SCROLLABLE FRAME UTILITY ---
class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

# --- CUSTOM TOOLTIP CLASS ---
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.widget.bind("<Enter>", self.enter, add="+")
        self.widget.bind("<Leave>", self.leave, add="+")

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def showtip(self, event=None):
        if not self.text:
            return
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify="left",
                      background="#2c2c2c", foreground="white", relief="solid", borderwidth=1,
                      font=("Arial", 10, "normal"), wraplength=250)
        label.pack(ipadx=4, ipady=4)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class PolyglotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Polyglot AI Tutor")
        self.root.geometry("1000x650")


        
        self.ai = AIClient()
        self.dict_client = DictionaryClient()
        self.formatter = TextFormatter()
        # Audio playback via browser
        self._audio_pending_file = None
        self._audio_done_event = threading.Event()
        self._audio_lock = threading.Lock()
        self._composing_preview_len = 0

        self.ja_tts = TTSEngine(audio_player=self.play_audio_in_browser)
        self.euro_tts = EuropeanTTSEngine(audio_player=self.play_audio_in_browser)
        self.zh_tts = ChineseTTSEngine(audio_player=self.play_audio_in_browser)
        self.ko_tts = KoreanTTSEngine(audio_player=self.play_audio_in_browser)
        self.stt = STTEngine()
        
        self.vocabulary_log = {}
        self.fetching_words = set() # NEW: Prevents API spam
        self.notebook_window = None
        self.settings_window = None
        
        # Tooltip State
        self.current_hovered_word = None
        self.chat_tw = None
        
        # State Tracking
        self.conversation_running = False
        self.partial_replay_mode = False 
        self.ime_active = False
        self.is_ai_talking = False
        self.is_processing = False
        self.last_spoken_text = "" 

        # UI Variables
        self.timeout_var = tk.DoubleVar(value=config.DEFAULT_SILENCE_TIMEOUT)
        self.mic_sens_var = tk.DoubleVar(value=config.DEFAULT_SENSITIVITY)
        self.talk_speed_var = tk.DoubleVar(value=config.DEFAULT_TTS_SPEED)
        self.replay_speed_var = tk.DoubleVar(value=config.DEFAULT_TTS_SPEED)
        self.tts_volume_var = tk.DoubleVar(value=1.0)
        
        self.lang_var = tk.StringVar(value="Japanese")
        self.reading_var = tk.StringVar(value="ふりがな")

        self.lang_codes = {
            "Japanese": "ja-JP", "Spanish": "es-ES", "French": "fr-FR",
            "Italian": "it-IT", "Chinese": "zh-CN", "Korean": "ko-KR"
        }
        
        self.setup_ui()
        self.start_ime_sync_server()
        self.root.after(100, self.show_welcome_help)

    def start_ime_sync_server(self):
        import http.server
        import socketserver
        import json
        import threading
        
        class IMESyncHandler(http.server.BaseHTTPRequestHandler):
            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress HTTP server log spam

            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    text = data.get('text', '')
                    path = self.path

                    if path == '/compose':
                        # Live preview: update composition preview at end of input field
                        self.server.app_ref.root.after(0, self.server.app_ref.compose_preview, text)
                    elif path == '/insert':
                        # Finalize composition: replace preview with final text
                        self.server.app_ref.root.after(0, self.server.app_ref.compose_finalize, text)
                    elif path == '/toggle_grammar':
                        self.server.app_ref.root.after(0, self.server.app_ref.toggle_grammar_panel)
                    elif path == '/type':
                        if text:
                            self.server.app_ref.root.after(0, self.server.app_ref.insert_and_send, text)
                    else:
                        if text:
                            self.server.app_ref.root.after(0, self.server.app_ref.insert_and_send, text)

                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"status": "success"}')
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"status": "error"}')

            def do_GET(self):
                try:
                    path = self.path
                    if path == '/toggle_grammar':
                        self.server.app_ref.root.after(0, self.server.app_ref.toggle_grammar_panel)
                        self.send_response(200)
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(b'{"status": "success"}')
                    elif path == '/audio/status':
                        # Return current pending audio file for browser to play
                        app = self.server.app_ref
                        pending = app._audio_pending_file
                        if pending:
                            self.send_response(200)
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            import urllib.parse
                            encoded = urllib.parse.quote(os.path.basename(pending))
                            volume = app.tts_volume_var.get()
                            self.wfile.write(f'{{"file": "/audio/file/{encoded}", "volume": {volume}}}'.encode())
                        else:
                            self.send_response(200)
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(b'{"file": null}')
                    elif path.startswith('/audio/file/'):
                        # Serve the actual audio file
                        filename = path.split('/audio/file/')[-1]
                        import urllib.parse
                        filename = urllib.parse.unquote(filename)
                        # Security: only serve from working directory
                        filepath = os.path.join(os.getcwd(), filename)
                        if os.path.exists(filepath) and os.path.isfile(filepath):
                            self.send_response(200)
                            self.send_header('Access-Control-Allow-Origin', '*')
                            if filepath.endswith('.mp3'):
                                self.send_header('Content-Type', 'audio/mpeg')
                            else:
                                self.send_header('Content-Type', 'audio/wav')
                            self.send_header('Content-Length', str(os.path.getsize(filepath)))
                            self.send_header('Cache-Control', 'no-cache')
                            self.end_headers()
                            with open(filepath, 'rb') as f:
                                self.wfile.write(f.read())
                        else:
                            self.send_response(404)
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(b'{"error": "not found"}')
                    elif path == '/audio/done':
                        # Browser finished playing audio
                        app = self.server.app_ref
                        app._audio_pending_file = None
                        app._audio_done_event.set()
                        self.send_response(200)
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(b'{"status": "ok"}')
                    else:
                        self.send_response(200)
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(b'{"status": "ok"}')
                except Exception:
                    self.send_response(500)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"status": "error"}')

        def run_server():
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("", 8081), IMESyncHandler) as httpd:
                httpd.app_ref = self
                httpd.serve_forever()
                
        threading.Thread(target=run_server, daemon=True).start()

    def play_audio_in_browser(self, filepath):
        """Queue an audio file for browser playback and block until it finishes."""
        if not os.path.exists(filepath):
            print(f"⚠️ Audio file not found: {filepath}")
            return
        
        print(f"🔊 Queuing audio for browser: {filepath}")
        self._audio_done_event.clear()
        self._audio_pending_file = filepath
        
        # Block until the browser finishes playing (or timeout after 60s)
        self._audio_done_event.wait(timeout=60.0)
        print(f"✅ Browser finished playing: {filepath}")

    def insert_and_send(self, text):
        if not text: return
        self.input_field.delete(0, "end")
        self.input_field.insert(0, text)
        self.send_message()

    def set_input_text(self, text):
        """Replace input field content entirely."""
        self.input_field.delete(0, "end")
        if text:
            self.input_field.insert(0, text)
        self._composing_preview_len = 0

    def compose_preview(self, text):
        """Update the live IME composition preview at the end of the input field."""
        # Remove previous preview characters from the end
        if self._composing_preview_len > 0:
            current = self.input_field.get()
            base = current[:-self._composing_preview_len]
            self.input_field.delete(0, "end")
            self.input_field.insert(0, base)
        # Append new preview
        if text:
            self.input_field.insert("end", text)
            self._composing_preview_len = len(text)
        else:
            self._composing_preview_len = 0

    def compose_finalize(self, text):
        """Finalize IME composition — replace preview with final text, keep everything before it."""
        # Remove the preview
        if self._composing_preview_len > 0:
            current = self.input_field.get()
            base = current[:-self._composing_preview_len]
            self.input_field.delete(0, "end")
            self.input_field.insert(0, base)
        # Append final composed text
        if text:
            self.input_field.insert("end", text)
        self._composing_preview_len = 0

    def insert_text_only(self, text):
        """Append text into the input field without sending (used by IME composition)."""
        if not text: return
        self.input_field.insert("end", text)

    # --- HELP POP-UP ---
    def center_window(self, win, w, h):
        x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (w // 2)
        y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

    def show_welcome_help(self):
        help_win = tk.Toplevel(self.root)
        help_win.title("How to Use")
        self.center_window(help_win, 500, 450)
        help_win.configure(bg="#f0f0f0")
        help_win.transient(self.root)
        help_win.grab_set()

        title = tk.Label(help_win, text="Polyglot Interface Guide", font=("Arial", 18, "bold"), bg="#f0f0f0", pady=15)
        title.pack()

        scroll_container = ScrollableFrame(help_win)
        scroll_container.pack(fill="both", expand=True, padx=10)

        instructions = [
            ("▤", "Notebook: View saved vocabulary. Hover over a word to see its definition. Press Delete/Backspace to remove."),
            ("✎", "Grammar Tutor: Open the side panel for grammar explanations."),
            ("⚙", "Settings: Adjust voice speed, mic sensitivity, silence timeout, and reading modes."),
            ("⟳", "Full Replay: Re-play the last response at your chosen playback speed."),
            ("⚯", "Partial Replay: Click this, then highlight text in chat and press Return/Enter to hear just that part."),
            ("1.0x", "Speed Menu: Change playback speed for all replays."),
            ("➤", "Send: Push your typed message to the AI."),
            ("✆", "Conversation: Toggle hands-free voice-to-voice mode."),
            ("💡", "Definitions: Highlight any word in the chat, then hover your mouse over the highlight to see its definition.")
        ]

        for symbol, desc in instructions:
            row = tk.Frame(scroll_container.scrollable_frame, bg="#f0f0f0", pady=8)
            row.pack(fill="x")
            
            s_lbl = tk.Label(row, text=symbol, font=("Arial", 20), width=3, bg="#f0f0f0", anchor="w")
            s_lbl.pack(side="left")
            
            d_lbl = tk.Label(row, text=desc, font=("Arial", 11), bg="#f0f0f0", wraplength=350, justify="left")
            d_lbl.pack(side="left", padx=10)

        close_btn = tk.Button(help_win, text="Got it!", command=help_win.destroy, font=("Arial", 12, "bold"), pady=5, padx=20)
        close_btn.pack(pady=10)

    # --- BUTTON BINDING HELPERS ---
    def bind_btn(self, lbl, command):
        lbl.bind("<Button-1>", lambda e: lbl.config(bg="#d0d0d0"))
        lbl.bind("<ButtonRelease-1>", lambda e: [lbl.config(bg="#e0e0e0"), command()])
        lbl.bind("<Enter>", lambda e: lbl.config(bg="#e0e0e0"))
        lbl.bind("<Leave>", lambda e: lbl.config(bg="#ececec"))

    def bind_toggle_btn(self, lbl, command, state_check):
        def on_enter(e):
            if not state_check(): lbl.config(bg="#e0e0e0")
        def on_leave(e):
            lbl.config(bg="#a0a0a0" if state_check() else "#ececec")
        def on_release(e):
            command()
        lbl.bind("<Button-1>", lambda e: lbl.config(bg="#808080" if state_check() else "#d0d0d0"))
        lbl.bind("<ButtonRelease-1>", on_release)
        lbl.bind("<Enter>", on_enter)
        lbl.bind("<Leave>", on_leave)

    def update_button_visuals(self):
        self.partial_lbl.config(bg="#a0a0a0" if self.partial_replay_mode else "#ececec")
        self.conv_lbl.config(bg="#a0a0a0" if self.conversation_running else "#ececec")

    def setup_ui(self):
        # --- TOP BAR ---
        self.ctrl_frame = tk.Frame(self.root)
        self.ctrl_frame.pack(side="top", pady=10, fill="x", padx=15)

        self.lang_menu = ttk.Combobox(self.ctrl_frame, textvariable=self.lang_var, 
                                     values=config.SUPPORTED_LANGUAGES, state="readonly", width=12)
        self.lang_menu.pack(side="left", padx=5)
        self.lang_menu.bind("<<ComboboxSelected>>", self.on_language_change)

        self.notebook_btn = tk.Label(self.ctrl_frame, text="▤", font=("Arial", 28), cursor="hand2")
        self.notebook_btn.pack(side="left", padx=10)
        self.notebook_btn.bind("<Button-1>", lambda e: self.toggle_notebook())
        ToolTip(self.notebook_btn, "View saved vocabulary. Hover over a word to see its definition. Press Delete/Backspace to remove.")

        self.grammar_btn = tk.Label(self.ctrl_frame, text="✎", font=("Arial", 28), cursor="hand2",
                                     bg="#ececec", highlightbackground="#aaa", highlightthickness=1)
        self.grammar_btn.pack(side="left", padx=10)
        self.grammar_btn.bind("<ButtonRelease-1>", lambda e: self.toggle_grammar_panel())
        ToolTip(self.grammar_btn, "Open the side panel for grammar explanations.")

        self.settings_btn = tk.Label(self.ctrl_frame, text="⚙", fg="black", font=("Arial", 32), cursor="hand2")
        self.settings_btn.pack(side="right", padx=10)
        self.settings_btn.bind("<Button-1>", lambda e: self.toggle_settings())
        ToolTip(self.settings_btn, "Settings")

        # --- BOTTOM DOCK ---
        self.bottom_bar = tk.Frame(self.root, pady=15, padx=15)
        self.bottom_bar.pack(side="bottom", fill="x")

        # --- MAIN CHAT AREA ---
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(side="top", fill="both", expand=True, padx=15)

        self.chat_display = tk.Text(self.main_container, state="disabled", wrap="word", borderwidth=1, relief="solid", font=("Arial", 16))
        self.chat_display.pack(side="left", fill="both", expand=True)
        
        self.chat_display.tag_config("vocab_word", foreground="#FF8C00", font=("Arial", 16, "bold"))
        self.chat_display.tag_config("ai_clickable", foreground="#003366")

        self.chat_display.bind("<Motion>", self.on_chat_hover)
        self.chat_display.bind("<Leave>", lambda e: self.hide_chat_tooltip())

        # --- GRAMMAR TUTOR (Toplevel popup window) ---
        self.grammar_window = None
        self.grammar_text = None
        self.grammar_input_field = None
        self.current_grammar_context = ""

        # --- BUILD BOTTOM BAR CONTENT ---
        self.input_field = ttk.Entry(self.bottom_bar, font=("Arial", 18))
        self.input_field.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_field.bind("<Return>", lambda e: self.send_message())

        # --- UNIFIED REPLAY DOCK ---
        replay_dock = tk.Frame(self.bottom_bar, bg="#aaa", highlightbackground="#aaa", highlightthickness=1)
        replay_dock.pack(side="left", padx=(0, 10))

        fr_f = tk.Frame(replay_dock, width=46, height=46); fr_f.pack_propagate(False); fr_f.pack(side="left", padx=(0, 1))
        self.fr_lbl = tk.Label(fr_f, text="⟳", fg="black", bg="#ececec", cursor="hand2", font=("Arial", 24))
        self.fr_lbl.pack(fill="both", expand=True)
        self.bind_btn(self.fr_lbl, self.trigger_replay)
        ToolTip(self.fr_lbl, "Re-play the last response at your chosen playback speed.")

        pr_f = tk.Frame(replay_dock, width=46, height=46); pr_f.pack_propagate(False); pr_f.pack(side="left", padx=(0, 1))
        self.partial_lbl = tk.Label(pr_f, text="⚯", fg="black", bg="#ececec", cursor="hand2", font=("Arial", 24))
        self.partial_lbl.pack(fill="both", expand=True)
        self.bind_toggle_btn(self.partial_lbl, self.toggle_partial_replay, lambda: self.partial_replay_mode)
        ToolTip(self.partial_lbl, "Click this, then highlight text in chat and press Return/Enter to hear just that part.")

        sm_f = tk.Frame(replay_dock, width=65, height=46); sm_f.pack_propagate(False); sm_f.pack(side="left")
        self.speed_lbl = tk.Label(sm_f, text="1.0x ▾", fg="black", bg="#ececec", cursor="hand2", font=("Arial", 14))
        self.speed_lbl.pack(fill="both", expand=True)
        
        self.speed_menu = tk.Menu(self.root, tearoff=0)
        for s in [0.5, 0.8, 1.0, 1.2, 1.5]:
            self.speed_menu.add_command(label=f"{s}x", command=lambda val=s: self.set_replay_speed(val))
        
        self.speed_lbl.bind("<ButtonRelease-1>", lambda e: self.speed_menu.post(e.x_root, e.y_root))
        ToolTip(self.speed_lbl, "Change playback speed for all replays.")

        # --- SQUARE ACTION BUTTONS ---
        send_f = tk.Frame(self.bottom_bar, width=46, height=46, highlightbackground="#aaa", highlightthickness=1)
        send_f.pack_propagate(False); send_f.pack(side="left", padx=5)
        self.send_lbl = tk.Label(send_f, text="➤", fg="black", bg="#ececec", cursor="hand2", font=("Arial", 24))
        self.send_lbl.pack(fill="both", expand=True)
        self.bind_btn(self.send_lbl, self.send_message)
        ToolTip(self.send_lbl, "Push your typed message to the AI.")

        conv_f = tk.Frame(self.bottom_bar, width=46, height=46, highlightbackground="#aaa", highlightthickness=1)
        conv_f.pack_propagate(False); conv_f.pack(side="left", padx=5)
        self.conv_lbl = tk.Label(conv_f, text="✆", fg="black", bg="#ececec", cursor="hand2", font=("Arial", 24))
        self.conv_lbl.pack(fill="both", expand=True)
        self.bind_toggle_btn(self.conv_lbl, self.toggle_conversation, lambda: self.conversation_running)
        ToolTip(self.conv_lbl, "Toggle hands-free voice-to-voice mode.")

        self.status_label = tk.Label(self.bottom_bar, text="○", font=("Arial", 20), foreground="gray")
        self.status_label.pack(side="left", padx=10)
    # --- DEFINITION HOVER TOOLTIP LOGIC ---
    def on_chat_hover(self, event):
        if event.state & 0x0100:
            self.hide_chat_tooltip()
            return

        try:
            index = self.chat_display.index(f"@{event.x},{event.y}")
            tags = self.chat_display.tag_names(index)
            
            if "sel" in tags:
                word = self.chat_display.get("sel.first", "sel.last").strip()
                if not word:
                    self.hide_chat_tooltip()
                    return
                
                if self.lang_var.get() == "Japanese":
                    word = re.sub(r'[\(\[（].*?[\)\]）]', '', word)
                
                if self.current_hovered_word != word:
                    self.current_hovered_word = word
                    self.show_chat_tooltip(event.x_root, event.y_root, word)
            else:
                self.hide_chat_tooltip()
        except Exception:
            self.hide_chat_tooltip()

    def show_chat_tooltip(self, x, y, word):
        self.hide_chat_tooltip()
        self.chat_tw = tk.Toplevel(self.root)
        self.chat_tw.wm_overrideredirect(True)
        self.chat_tw.wm_geometry(f"+{x+15}+{y+15}")
        
        self.chat_tt_label = tk.Label(self.chat_tw, text=f"Searching '{word}'...",
                                      background="#2c2c2c", foreground="white", relief="solid", borderwidth=1,
                                      font=("Arial", 11), wraplength=300, justify="left")
        self.chat_tt_label.pack(ipadx=10, ipady=10)

        if word in self.vocabulary_log:
            self.root.after(10, lambda: self.update_tooltip_label(word, self.vocabulary_log[word]))
        elif word not in self.fetching_words:
            self.fetching_words.add(word)
            threading.Thread(target=self.fetch_definition_background, args=(word, self.lang_var.get()), daemon=True).start()

    def fetch_definition_background(self, word, lang):
        res, success = self.dict_client.fetch_definition(word, lang, immersion_mode=False)
        
        # FIX: Only cache the word if the lookup was successful
        if success:
            self.vocabulary_log[word] = res 
            
        if word in self.fetching_words:
            self.fetching_words.remove(word)

        # FIX: Only highlight it as a vocab word if it successfully found a definition
        self.root.after(0, lambda: [
            self.update_tooltip_label(word, res), 
            self.highlight_vocabulary() if success else None
        ])
        
    def update_tooltip_label(self, word, full_res):
        clean_def = re.split(r'(?i)Example:|Ex:|Synonyms:|Usage:', full_res)[0].strip()
        if self.chat_tw and self.chat_tw.winfo_exists():
            self.chat_tt_label.config(text=f"{word}:\n\n{clean_def}")

    def hide_chat_tooltip(self):
        self.current_hovered_word = None
        if self.chat_tw:
            self.chat_tw.destroy()
            self.chat_tw = None


    # --- NOTEBOOK & SETTINGS ---
    def toggle_settings(self):
        if self.settings_window and tk.Toplevel.winfo_exists(self.settings_window):
            self.settings_window.lift()
            return
        
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        self.center_window(self.settings_window, 350, 320)
        f = ttk.Frame(self.settings_window, padding=20)
        f.pack(fill="both", expand=True)
        
        ttk.Label(f, text="Voice Speed:").pack(anchor="w")
        ttk.Scale(f, from_=0.5, to=2.0, variable=self.talk_speed_var).pack(fill="x", pady=5)
        
        ttk.Label(f, text="Mic Sensitivity:").pack(anchor="w", pady=(10,0))
        ttk.Scale(f, from_=0, to=100, variable=self.mic_sens_var).pack(fill="x", pady=5)

        ttk.Label(f, text="Silence Timeout (s):").pack(anchor="w", pady=(10,0))
        ttk.Scale(f, from_=1.0, to=10.0, variable=self.timeout_var).pack(fill="x", pady=5)

        ttk.Label(f, text="TTS Volume:").pack(anchor="w", pady=(10,0))
        ttk.Scale(f, from_=0.0, to=1.0, variable=self.tts_volume_var).pack(fill="x", pady=5)

        if self.lang_var.get() == "Japanese":
            ttk.Label(f, text="Reading Mode:").pack(anchor="w", pady=(10,0))
            ttk.Combobox(f, textvariable=self.reading_var, values=config.JAPANESE_MODES, state="readonly").pack(fill="x")

    def toggle_notebook(self):
        if self.notebook_window and tk.Toplevel.winfo_exists(self.notebook_window):
            self.notebook_window.lift()
            return

        self.notebook_window = tk.Toplevel(self.root)
        self.notebook_window.title("Notebook")
        self.center_window(self.notebook_window, 300, 450)
        lb = tk.Listbox(self.notebook_window, font=("Arial", 12), borderwidth=0, highlightthickness=0)
        lb.pack(fill="both", expand=True, padx=10, pady=10)
        
        for w in self.vocabulary_log: 
            lb.insert("end", w)

        def on_lb_hover(e):
            idx = lb.nearest(e.y)
            if idx >= 0:
                bbox = lb.bbox(idx)
                # Ensure the cursor is actually vertically within the text item's bounding box
                if bbox and bbox[1] <= e.y <= (bbox[1] + bbox[3]):
                    word = lb.get(idx)
                    if self.current_hovered_word != word:
                        self.current_hovered_word = word
                        self.show_chat_tooltip(e.x_root, e.y_root, word)
                else:
                    self.hide_chat_tooltip()
            else: 
                self.hide_chat_tooltip()

        def delete_entry(e):
            sel = lb.curselection()
            if sel:
                word = lb.get(sel[0])
                lb.delete(sel[0])
                if word in self.vocabulary_log: 
                    del self.vocabulary_log[word]
                self.highlight_vocabulary()
                self.hide_chat_tooltip()

        lb.bind("<Motion>", on_lb_hover)
        lb.bind("<Leave>", lambda e: self.hide_chat_tooltip())
        lb.bind("<Delete>", delete_entry)
        lb.bind("<BackSpace>", delete_entry)


    # --- GRAMMAR PANEL LOGIC ---
    def toggle_grammar_panel(self):
        """Toggle the grammar tutor popup window."""
        try:
            if self.grammar_window is not None and self.grammar_window.winfo_exists():
                self.grammar_window.destroy()
                self.grammar_window = None
                self.grammar_text = None
                self.grammar_input_field = None
            else:
                self._create_grammar_window()
        except Exception:
            self._create_grammar_window()

    def _create_grammar_window(self):
        """Create the grammar tutor popup window."""
        self.grammar_window = tk.Toplevel(self.root)
        self.grammar_window.title("Grammar Tutor")
        self.grammar_window.geometry("450x500")
        self.grammar_window.transient(self.root)

        # Position next to the main window
        x = self.root.winfo_x() + self.root.winfo_width() + 10
        y = self.root.winfo_y()
        # If it would go off-screen, position it overlapping
        if x + 450 > self.root.winfo_screenwidth():
            x = self.root.winfo_x() + self.root.winfo_width() - 460
        self.grammar_window.geometry(f"450x500+{x}+{y}")

        # Grammar text display
        self.grammar_text = tk.Text(self.grammar_window, wrap="word", state="disabled",
                                    font=("Arial", 13), bg="#fcfcfc")
        self.grammar_text.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # Input frame at bottom
        input_frame = tk.Frame(self.grammar_window)
        input_frame.pack(fill="x", side="bottom", padx=8, pady=(4, 8))

        self.grammar_input_field = ttk.Entry(input_frame, font=("Arial", 12))
        self.grammar_input_field.pack(side="left", fill="x", expand=True)
        self.grammar_input_field.bind("<Return>", lambda e: self.send_grammar_question())

        send_btn = ttk.Button(input_frame, text="Ask", command=self.send_grammar_question)
        send_btn.pack(side="right", padx=(5, 0))

        # Show initial text
        self.grammar_text.config(state="normal")
        self.grammar_text.insert("1.0", "Grammar Tutor ready.\n\nDouble-click an AI response in the chat to analyze its grammar, or type a question below.\n")
        self.grammar_text.config(state="disabled")

        # Handle window close
        self.grammar_window.protocol("WM_DELETE_WINDOW", self.toggle_grammar_panel)


    # --- REMAINING LOGIC (AI, TTS, STT) ---
    def on_language_change(self, e=None):
        self.ai.clear_history()
        if self.grammar_window is not None and self.grammar_window.winfo_exists():
            self.grammar_window.destroy()
            self.grammar_window = None
        self.update_chat("System", f"Switched to {self.lang_var.get()}. Memory wiped.")

    def play_tts(self, text, lang, speed):
        engines = {"Japanese": self.ja_tts, "Chinese": self.zh_tts, "Korean": self.ko_tts}
        engine = engines.get(lang, self.euro_tts)
        self.set_status("speaking")
        kwargs = {"on_done": lambda: self.set_status("idle")}
        if engine == self.euro_tts: kwargs["language"] = lang
        engine.speak(text, speed=speed, **kwargs)

    def play_tts_blocking(self, text, lang, speed):
        self.set_status("speaking")
        engines = {"Japanese": self.ja_tts, "Chinese": self.zh_tts, "Korean": self.ko_tts}
        engine = engines.get(lang, self.euro_tts)
        finished = threading.Event()
        kwargs = {"on_done": lambda: finished.set()}
        if engine == self.euro_tts: kwargs["language"] = lang
        engine.speak(text, speed=speed, **kwargs)
        finished.wait(timeout=60.0); time.sleep(0.4)

    def set_replay_speed(self, value):
        self.replay_speed_var.set(value)
        self.speed_lbl.config(text=f"{value}x ▾")

    def set_status(self, state):
        colors = {"listening": ("#2ca02c", "●"), "thinking": ("#d62728", "●"), "speaking": ("#1f77b4", "●"), "idle": ("gray", "○")}
        color, symbol = colors.get(state, colors["idle"])
        self.root.after(0, lambda: self.status_label.config(text=symbol, foreground=color))

    def update_chat(self, sender, text):
        self.chat_display.config(state="normal")
        start_index = self.chat_display.index("insert")
        self.chat_display.insert("end", f"{sender}: {text}\n\n")
        
        if sender == "AI":
            text_start = f"{start_index} + 4c" 
            text_end = self.chat_display.index("end - 2c")
            self.chat_display.tag_add("ai_clickable", text_start, text_end)
            
            # (The tag_config line that was here has been removed)
            
            self.chat_display.tag_bind("ai_clickable", "<Double-Button-1>", self.on_ai_text_click)
            self.chat_display.tag_bind("ai_clickable", "<Enter>", lambda e: self.chat_display.config(cursor="hand2"))
            self.chat_display.tag_bind("ai_clickable", "<Leave>", lambda e: self.chat_display.config(cursor=""))

        self.chat_display.config(state="disabled")
        self.chat_display.see("end")
        self.highlight_vocabulary()

    def highlight_vocabulary(self):
        self.chat_display.tag_remove("vocab_word", "1.0", tk.END)
        content = self.chat_display.get("1.0", tk.END)
        for word in self.vocabulary_log.keys():
            pattern = r'(?:[\(\[（].*?[\)\]）])?'.join([re.escape(c) for c in word])
            for m in re.finditer(pattern, content):
                self.chat_display.tag_add("vocab_word", f"1.0 + {m.start()} chars", f"1.0 + {m.end()} chars")

        self.chat_display.tag_raise("vocab_word")

    def send_message(self):
        text = self.input_field.get()
        if not text: return
        self.update_chat("You", text)
        self.input_field.delete(0, "end")
        self.set_status("thinking")
        threading.Thread(target=self.run_ai_logic, args=(text, self.lang_var.get()), daemon=True).start()

    def run_ai_logic(self, text, lang):
        reply, success = self.ai.get_reply(text, lang)
        if success:
            display = self.formatter.process(reply, lang, self.reading_var.get()) if lang == "Japanese" else reply
            self.root.after(0, lambda: self.update_chat("AI", display))
            self.last_spoken_text = re.sub(r'[\*#\-]', '', reply).replace('\n', ' ')
            self.play_tts(self.last_spoken_text, lang, self.talk_speed_var.get())
        else:
            self.root.after(0, lambda: self.update_chat("System", reply))
            self.set_status("idle")

    def trigger_replay(self):
        if self.last_spoken_text:
            threading.Thread(target=self.play_tts, args=(self.last_spoken_text, self.lang_var.get(), self.replay_speed_var.get()), daemon=True).start()

    def toggle_partial_replay(self):
        self.partial_replay_mode = not self.partial_replay_mode
        if self.partial_replay_mode:
            self.root.bind("<Return>", self.execute_partial_replay)
        else:
            self.root.unbind("<Return>")
            self.input_field.bind("<Return>", lambda ev: self.send_message())
        self.update_button_visuals()

    def execute_partial_replay(self, e=None):
        try:
            if self.chat_display.tag_ranges("sel"):
                text = self.chat_display.get("sel.first", "sel.last").strip()
                if self.lang_var.get() == "Japanese": text = re.sub(r'[\(\[（].*?[\)\]）]', '', text)
                threading.Thread(target=self.play_tts, args=(text, self.lang_var.get(), self.replay_speed_var.get()), daemon=True).start()
        finally:
            self.partial_replay_mode = False
            self.root.unbind("<Return>")
            self.input_field.bind("<Return>", lambda ev: self.send_message())
            self.update_button_visuals()

    def toggle_conversation(self):
        self.conversation_running = not self.conversation_running
        self.update_button_visuals()
        if self.conversation_running: 
            threading.Thread(target=self.conversation_loop, daemon=True).start()
        else: self.set_status("idle")

    def toggle_keyboard(self):
        self.ime_active = not self.ime_active
        if self.ime_active:
            self.kbd_lbl.config(text="あ", bg="#a0a0a0")
            lang = self.lang_var.get()
            engine = {"Japanese": "anthy", "Korean": "hangul", "Chinese": "googlepinyin"}.get(lang, "fcitx-keyboard-us")
            try:
                subprocess.run(["fcitx-remote", "-s", engine], check=False)
                subprocess.run(["fcitx-remote", "-o"], check=False)
            except: pass
        else:
            self.kbd_lbl.config(text="A", bg="#ececec")
            try:
                subprocess.run(["fcitx-remote", "-c"], check=False)
            except: pass

    def conversation_loop(self):
        while self.conversation_running:
            if self.is_processing or self.is_ai_talking or self._audio_pending_file:
                time.sleep(0.5); continue
            self.set_status("listening")
            try:
                speech = self.stt.listen_and_transcribe(target_language=self.lang_codes.get(self.lang_var.get(), "en-US"), timeout=self.timeout_var.get())
                if not self.conversation_running: break
                if speech and not speech.startswith("ERROR:"):
                    self.execute_full_turn(speech.strip())
            except: 
                if self.conversation_running: self.set_status("idle"); time.sleep(1)
        self.set_status("idle")

    def execute_full_turn(self, user_text):
        self.is_processing = True; self.is_ai_talking = True
        self.root.after(0, lambda: self.update_chat("You", user_text))
        lang = self.lang_var.get()
        reply, success = self.ai.get_reply(user_text, lang)
        if success:
            display = self.formatter.process(reply, lang, self.reading_var.get()) if lang == "Japanese" else reply
            self.root.after(0, lambda: self.update_chat("AI", display))
            self.last_spoken_text = re.sub(r'[\*#\-]', '', reply).replace('\n', ' ')
            self.play_tts_blocking(self.last_spoken_text, lang, self.talk_speed_var.get())
        self.is_processing = False; self.is_ai_talking = False; self.set_status("idle")

    def on_ai_text_click(self, event):
        # Find the line that was clicked
        index = self.chat_display.index(f"@{event.x},{event.y}")
        line_text = self.chat_display.get(f"{index} linestart", f"{index} lineend").strip()
        
        if line_text.startswith("AI: "):
            line_text = line_text[4:]
            
        if not line_text:
            return

        # Open the grammar panel if it's closed
        if self.grammar_window is None or not self.grammar_window.winfo_exists():
            self._create_grammar_window()

        self.current_grammar_context = line_text
        self.update_grammar_panel("System", f"Analyzing grammar for:\n'{line_text}'...", clear=True)
        
        threading.Thread(target=self.fetch_grammar_explanation_bg, args=(line_text,), daemon=True).start()

    def fetch_grammar_explanation_bg(self, text_line):
        lang = self.lang_var.get()
        prompt = f"Break down and explain the grammar and sentence structure of this {lang} sentence in English: '{text_line}'"
        
        # USE THE NEW METHOD HERE
        reply, success = self.ai.get_stateless_reply(prompt) 
        
        if success:
            self.root.after(0, lambda: self.update_grammar_panel("Tutor", reply, clear=True))
        else:
            self.root.after(0, lambda: self.update_grammar_panel("Error", "Failed to fetch explanation.", clear=True))

    def send_grammar_question(self):
        if self.grammar_input_field is None:
            return
        question = self.grammar_input_field.get()
        if not question: 
            return

        self.grammar_input_field.delete(0, "end")
        self.update_grammar_panel("You", question)

        threading.Thread(target=self.fetch_grammar_followup_bg, args=(question,), daemon=True).start()

    def fetch_grammar_followup_bg(self, question):
        lang = self.lang_var.get()
        context = self.current_grammar_context if self.current_grammar_context else "general grammar"
        prompt = f"Regarding the {lang} sentence '{context}', the user asks: {question}. Please clarify in English."
        
        reply, success = self.ai.get_stateless_reply(prompt)
        
        if success:
            self.root.after(0, lambda: self.update_grammar_panel("Tutor", reply))
        else:
            self.root.after(0, lambda: self.update_grammar_panel("Error", "Failed to fetch response."))

    def update_grammar_panel(self, sender, text, clear=False):
        if self.grammar_text is None:
            return
        try:
            self.grammar_text.config(state="normal")
            if clear:
                self.grammar_text.delete("1.0", "end")
            self.grammar_text.insert("end", f"{sender}:\n{text}\n\n")
            self.grammar_text.config(state="disabled")
            self.grammar_text.see("end")
        except tk.TclError:
            pass  # Window was closed

if __name__ == "__main__":
    root = tk.Tk()
    app = PolyglotApp(root)
    root.mainloop()