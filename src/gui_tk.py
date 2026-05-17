#!/usr/bin/env python3
"""Tkinter GUI for Barotrauma save file viewer — simple and working."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
import json
import csv

try:
    from parser.data import SaveFile
    from parser.decode import parse_save
except ImportError:
    from data import SaveFile
    from decode import parse_save


class SaveViewerTk:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Barotrauma Save Viewer")
        self.root.geometry("1000x700")
        
        self.sf: SaveFile | None = None
        self.file_path: Path | None = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Menu
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Save File", command=self._on_open)
        file_menu.add_command(label="Export JSON", command=self._on_export_json)
        file_menu.add_command(label="Export CSV", command=self._on_export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Open a .save file to begin.")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Main content area
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Characters tab
        self.chars_frame = tk.Frame(notebook)
        notebook.add(self.chars_frame, text="Characters")
        
        # Submarine tab
        self.sub_frame = tk.Frame(notebook)
        notebook.add(self.sub_frame, text="Submarine")
        
        # Hulls tab
        self.hulls_frame = tk.Frame(notebook)
        notebook.add(self.hulls_frame, text="Hulls")
        
        # Items tab
        self.items_frame = tk.Frame(notebook)
        notebook.add(self.items_frame, text="Items")
        
        # Missions tab
        self.missions_frame = tk.Frame(notebook)
        notebook.add(self.missions_frame, text="Missions")
        
        # Raw XML tab
        self.xml_frame = tk.Frame(notebook)
        notebook.add(self.xml_frame, text="Raw XML")
        
        # Scrollable text widget for XML
        self.xml_text = tk.Text(self.xml_frame, wrap=tk.NONE)
        self.xml_text.pack(fill=tk.BOTH, expand=True)
        
        # Drop zone
        drop_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        drop_frame.pack(fill=tk.X, padx=10, pady=5)
        self.drop_label = tk.Label(drop_frame, text="Click File → Open Save File to open a .save file", fg="gray")
        self.drop_label.pack()
    
    def _on_open(self):
        filepath = filedialog.askopenfilename(
            title="Open Barotrauma Save File",
            filetypes=[("Save files", "*.save"), ("All files", "*.*")],
            initialdir=str(Path.home() / "AppData" / "LocalLow" / "Eyefish" / "Barotrauma" / "saves"),
        )
        if filepath:
            self._load_file(filepath)
    
    def _load_file(self, filepath):
        path = Path(filepath)
        if not path.exists():
            return
        
        self.file_path = path
        
        try:
            self.sf = parse_save(path)
            self.status_var.set(
                f"Loaded: {path.name} | {len(self.sf.characters)} chars "
                f"| {len(self.sf.hulls)} hulls | {len(self.sf.items)} items | "
                f"{len(self.sf.missions)} missions"
            )
            self._update_display()
        except Exception as e:
            self.status_var.set(f"Error loading file: {e}")
            self.sf = None
    
    def _update_display(self):
        if not self.sf:
            return
        
        # Update characters tab
        for widget in self.chars_frame.winfo_children():
            widget.destroy()
        
        if self.sf.characters:
            for char in self.sf.characters:
                frame = tk.Frame(self.chars_frame, bd=1, relief=tk.RAISED, padx=5, pady=5)
                frame.pack(fill=tk.X, pady=2)
                tk.Label(frame, text=f"Name: {char.name}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
                tk.Label(frame, text=f"Status: {char.status}").pack(anchor=tk.W)
                tk.Label(frame, text=f"Condition: {char.condition}").pack(anchor=tk.W)
                tk.Label(frame, text=f"Role: {char.role}").pack(anchor=tk.W)
        else:
            tk.Label(self.chars_frame, text="No characters found").pack(pady=10)
        
        # Update submarine tab
        for widget in self.sub_frame.winfo_children():
            widget.destroy()
        
        if self.sf.submarine:
            sub = self.sf.submarine
            frame = tk.Frame(self.sub_frame, bd=1, relief=tk.RAISED, padx=5, pady=5)
            frame.pack(fill=tk.X, pady=2)
            tk.Label(frame, text=f"Name: {sub.name}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
            tk.Label(frame, text=f"Health: {sub.health_pct}%").pack(anchor=tk.W)
        
        # Update hulls tab
        for widget in self.hulls_frame.winfo_children():
            widget.destroy()
        
        print(f"Hulls count: {len(self.sf.hulls)}")  # Debug
        if self.sf.hulls:
            for hull in self.sf.hulls:
                frame = tk.Frame(self.hulls_frame, bd=1, relief=tk.RAISED, padx=5, pady=5)
                frame.pack(fill=tk.X, pady=2)
                tk.Label(frame, text=f"Name: {hull.name}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
                tk.Label(frame, text=f"Health: {hull.health_pct}%").pack(anchor=tk.W)
        else:
            tk.Label(self.hulls_frame, text="No hulls found").pack(pady=10)
        
        # Update items tab
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        
        if self.sf.items:
            for item in self.sf.items:
                frame = tk.Frame(self.items_frame, bd=1, relief=tk.RAISED, padx=5, pady=5)
                frame.pack(fill=tk.X, pady=2)
                tk.Label(frame, text=f"Name: {item.name}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
                tk.Label(frame, text=f"Type: {item.type}").pack(anchor=tk.W)
                tk.Label(frame, text=f"Condition: {item.condition}").pack(anchor=tk.W)
        else:
            tk.Label(self.items_frame, text="No items found").pack(pady=10)
        
        # Update missions tab
        for widget in self.missions_frame.winfo_children():
            widget.destroy()
        
        if self.sf.missions:
            for mission in self.sf.missions:
                frame = tk.Frame(self.missions_frame, bd=1, relief=tk.RAISED, padx=5, pady=5)
                frame.pack(fill=tk.X, pady=2)
                tk.Label(frame, text=f"Title: {mission.title}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
                tk.Label(frame, text=f"Status: {mission.status}").pack(anchor=tk.W)
                tk.Label(frame, text=f"Description: {mission.description}").pack(anchor=tk.W)
        else:
            tk.Label(self.missions_frame, text="No missions found").pack(pady=10)
        
        # Update XML tab
        if self.sf.raw_xml:
            self.xml_text.delete(1.0, tk.END)
            self.xml_text.insert(1.0, self.sf.raw_xml[:10000])
            if len(self.sf.raw_xml) > 10000:
                self.xml_text.insert(tk.END, "\n\n...(truncated)")
        else:
            self.xml_text.delete(1.0, tk.END)
            self.xml_text.insert(1.0, "No raw XML available.")
    
    def _on_export_json(self):
        if not self.sf:
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Export to JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(self.file_path.parent) if self.file_path else None,
        )
        if filepath:
            self._write_json(filepath)
    
    def _on_export_csv(self):
        if not self.sf:
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Export Characters to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=str(self.file_path.parent) if self.file_path else None,
        )
        if filepath:
            self._write_csv(filepath)
    
    def _write_json(self, filepath):
        if not self.sf:
            return
        
        data = {
            "filename": str(self.sf.path),
            "submarine": vars(self.sf.submarine) if self.sf.submarine else None,
            "characters": [vars(c) for c in self.sf.characters],
            "hulls": [vars(h) for h in self.sf.hulls],
            "structures": [vars(s) for s in self.sf.structures],
            "items": [vars(i) for i in self.sf.items],
            "locations": [vars(l) for l in self.sf.locations],
            "missions": [vars(m) for m in self.sf.missions],
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        self.status_var.set(f"Exported to JSON: {filepath}")
    
    def _write_csv(self, filepath):
        if not self.sf:
            return
        
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Status", "Condition", "Role", "Health", "Permanently Dead"])
            for char in self.sf.characters:
                writer.writerow([
                    char.name,
                    char.status,
                    char.condition,
                    char.role,
                    getattr(char, "health", "N/A"),
                    getattr(char, "permanently_dead", False),
                ])
        
        self.status_var.set(f"Exported to CSV: {filepath}")
    
    def run(self):
        self.root.mainloop()


def main():
    app = SaveViewerTk()
    app.run()


if __name__ == "__main__":
    main()
