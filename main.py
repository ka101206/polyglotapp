# main.py
import tkinter as tk
from gui import PolyglotApp

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x650")
    app = PolyglotApp(root)
    root.mainloop()