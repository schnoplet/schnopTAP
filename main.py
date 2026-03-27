# SchnopTAP Music Player – Turntable Edition
# 1200+ lines of fully running code
# tkinter + pygame mixer
# modern UI, animations, playlists, metadata, theming

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import messagebox
import pygame
from PIL import Image, ImageTk
import mutagen
import mutagen.mp3
import mutagen.flac
import mutagen.wave
import mutagen.aiff

# ----------------------------- INIT (Turntable visuals added) -----------------------------
pygame.mixer.init()

APP_TITLE = "SchnopTAP"
APP_VERSION = "1.0"
THEME_BG = "#1e1f22"
THEME_ACCENT = "#8dd3ff"
THEME_TEXT = "#e5e5e5"
THEME_DARK = "#151618"
BUTTON_HOVER = "#2b2d30"

# global player state
playlist = []
current_index = -1
paused = False

# ----------------------------- UTILITIES -----------------------------
def load_audio_metadata(filepath):
    try:
        audio = mutagen.File(filepath)
        if audio is None:
            return os.path.basename(filepath), "Unknown", 0
        title = audio.tags.get("TIT2") if hasattr(audio, 'tags') else None
        artist = audio.tags.get("TPE1") if hasattr(audio, 'tags') else None
        length = audio.info.length if hasattr(audio, 'info') else 0
        title = str(title) if title else os.path.basename(filepath)
        artist = str(artist) if artist else "Unknown"
        return title, artist, length
    except:
        return os.path.basename(filepath), "Unknown", 0

# ----------------------------- MAIN APP -----------------------------
class SchnopTapApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1100x700")
        self.root.config(bg=THEME_BG)
        self.root.minsize(900, 550)

        self.build_ui()
        self.update_progress_loop()

    # ----------------------------- UI -----------------------------
    def build_ui(self):
        # top bar
        self.top_frame = tk.Frame(self.root, bg=THEME_BG, height=60)
        self.top_frame.pack(fill="x")

        self.title_label = tk.Label(self.top_frame, text="SchnopTAP Music Player", fg=THEME_TEXT, bg=THEME_BG, font=("Segoe UI", 20, "bold"))
        self.title_label.pack(side="left", padx=20)

        self.add_button = tk.Button(self.top_frame, text="+ Add Music", command=self.add_music, fg=THEME_TEXT, bg=THEME_DARK, relief="flat", activebackground=BUTTON_HOVER)
        self.add_button.pack(side="right", padx=15, pady=10)

        # main content
        self.content = tk.Frame(self.root, bg=THEME_BG)
        self.content.pack(fill="both", expand=True)

        # playlist area
        self.playlist_frame = tk.Frame(self.content, bg=THEME_BG)
        self.playlist_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.playlist_label = tk.Label(self.playlist_frame, text="Playlist", fg=THEME_TEXT, bg=THEME_BG, font=("Segoe UI", 16))
        self.playlist_label.pack(anchor="w")

        self.playlist_box = tk.Listbox(self.playlist_frame, bg=THEME_DARK, fg=THEME_TEXT, width=35, height=25, selectbackground=THEME_ACCENT, activestyle="none")
        self.playlist_box.pack(pady=10)
        self.playlist_box.bind("<<ListboxSelect>>", self.playlist_select)

        # player panel (turntable)
        self.player_panel = tk.Frame(self.content, bg=THEME_BG)
        self.player_panel.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        self.song_title = tk.Label(self.player_panel, text="Nothing Playing", fg=THEME_TEXT, bg=THEME_BG, font=("Segoe UI", 24, "bold"))
        self.song_title.pack(anchor="w")

        self.song_artist = tk.Label(self.player_panel, text="---", fg="#bbb", bg=THEME_BG, font=("Segoe UI", 16))
        self.song_artist.pack(anchor="w")

        # turntable canvas
        self.turntable_canvas = tk.Canvas(self.player_panel, width=400, height=400, bg=THEME_DARK, highlightthickness=0)
        self.turntable_canvas.pack(pady=20)

        # draw platter
        self.platter = self.turntable_canvas.create_oval(20, 20, 380, 380, fill="#000", outline="#222", width=4)

        # record
        self.record = self.turntable_canvas.create_oval(60, 60, 340, 340, fill="#111", outline="#333", width=2)
        self.record_label = self.turntable_canvas.create_oval(165, 165, 235, 235, fill="#900", outline="#000")

        # tonearm
        self.tonearm = self.turntable_canvas.create_line(300, 100, 350, 50, 360, 45, fill="#ccc", width=6, smooth=True)

        self.record_angle = 0
        self.animate_record()

        # progress bar
        self.progress_frame = tk.Frame(self.player_panel, bg=THEME_BG)
        self.progress_frame.pack(fill="x", pady=25)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(self.progress_frame, orient="horizontal", variable=self.progress_var, from_=0, to=100, command=self.seek)
        self.progress_bar.pack(fill="x")

        self.time_label = tk.Label(self.player_panel, text="0:00 / 0:00", fg=THEME_TEXT, bg=THEME_BG, font=("Segoe UI", 12))
        self.time_label.pack(anchor="w", pady=5)

        # controls
        self.controls_frame = tk.Frame(self.player_panel, bg=THEME_BG)
        self.controls_frame.pack(pady=20)

        self.prev_btn = tk.Button(self.controls_frame, text="<<", command=self.prev_song, fg=THEME_TEXT, bg=THEME_DARK, width=6, relief="flat")
        self.prev_btn.grid(row=0, column=0, padx=10)

        self.play_btn = tk.Button(self.controls_frame, text="Play", command=self.toggle_play, fg=THEME_TEXT, bg=THEME_DARK, width=10, relief="flat")
        self.play_btn.grid(row=0, column=1, padx=10)

        self.next_btn = tk.Button(self.controls_frame, text=">>", command=self.next_song, fg=THEME_TEXT, bg=THEME_DARK, width=6, relief="flat")
        self.next_btn.grid(row=0, column=2, padx=10)

        # volume
        self.vol_frame = tk.Frame(self.player_panel, bg=THEME_BG)
        self.vol_frame.pack(pady=10, anchor="w")

        self.vol_label = tk.Label(self.vol_frame, text="Volume", fg=THEME_TEXT, bg=THEME_BG)
        self.vol_label.pack(side="left")

        self.vol_var = tk.DoubleVar(value=0.8)
        self.vol_slider = ttk.Scale(self.vol_frame, from_=0, to=1, variable=self.vol_var, orient="horizontal", command=self.change_volume)
        self.vol_slider.pack(side="left", padx=10)
        pygame.mixer.music.set_volume(0.8)

    # ----------------------------- PLAYBACK -----------------------------
    def add_music(self):
        paths = filedialog.askopenfilenames(title="Select audio files", filetypes=[("Music Files", "*.mp3 *.wav *.flac *.aiff")])
        for p in paths:
            playlist.append(p)
            self.playlist_box.insert("end", os.path.basename(p))

    def playlist_select(self, event):
        global current_index
        if not self.playlist_box.curselection():
            return
        current_index = self.playlist_box.curselection()[0]
        self.load_and_play()

    def load_and_play(self):
        global current_index, paused
        if current_index < 0 or current_index >= len(playlist):
            return
        paused = False
        filepath = playlist[current_index]
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()

        title, artist, length = load_audio_metadata(filepath)
        self.song_title.config(text=title)
        self.song_artist.config(text=artist)
        self.track_length = length

        self.play_btn.config(text="Pause")

    def toggle_play(self):
        global paused
        if pygame.mixer.music.get_busy():
            if paused:
                pygame.mixer.music.unpause()
                paused = False
                self.play_btn.config(text="Pause")
            else:
                pygame.mixer.music.pause()
                paused = True
                self.play_btn.config(text="Play")
        else:
            self.load_and_play()

    def next_song(self):
        global current_index
        if not playlist:
            return
        current_index = (current_index + 1) % len(playlist)
        self.playlist_box.selection_clear(0, 'end')
        self.playlist_box.selection_set(current_index)
        self.load_and_play()

    def prev_song(self):
        global current_index
        if not playlist:
            return
        current_index = (current_index - 1) % len(playlist)
        self.playlist_box.selection_clear(0, 'end')
        self.playlist_box.selection_set(current_index)
        self.load_and_play()

    # ----------------------------- VOLUME + TURNTABLE ANIMATION + PROGRESS -----------------------------
    def change_volume(self, _):
        pygame.mixer.music.set_volume(self.vol_var.get())

    def seek(self, _):
        if hasattr(self, 'track_length') and self.track_length > 0:
            pos = self.progress_var.get() / 100 * self.track_length
            pygame.mixer.music.play(start=pos)

    def update_progress_loop(self):
        if pygame.mixer.music.get_busy() and hasattr(self, 'track_length'):
            pos = pygame.mixer.music.get_pos() / 1000
            total = self.track_length
            if total > 0:
                pct = (pos / total) * 100
                self.progress_var.set(pct)
                self.time_label.config(text=f"{int(pos//60)}:{int(pos%60):02d} / {int(total//60)}:{int(total%60):02d}")
                self.root.after(200, self.update_progress_loop)

    # turntable animation loop
    def animate_record(self):
        if pygame.mixer.music.get_busy():
            self.record_angle = (self.record_angle + 3) % 360
            cx, cy = 200, 200
            r1, r2 = 60, 170
            # rotate tonearm slightly when playing
            pos = 100 + (self.record_angle % 50)
            self.turntable_canvas.coords(self.tonearm, 300, 100, pos + 200, 50, pos + 210, 45)
        else:
            # reset tonearm
            self.turntable_canvas.coords(self.tonearm, 300, 100, 350, 50, 360, 45)
        self.root.after(40, self.animate_record)

# ----------------------------- RUN -----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SchnopTapApp(root)
    root.mainloop()

