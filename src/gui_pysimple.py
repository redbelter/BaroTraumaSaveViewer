#!/usr/bin/env python3
"""PySimpleGUI for Barotrauma save file viewer — simple and working."""

from __future__ import annotations

import json
import csv
import datetime
import math
from pathlib import Path
import PySimpleGUI as sg

try:
    from parser.data import SaveFile
    from parser.decode import parse_save
except ImportError:
    from data import SaveFile
    from decode import parse_save


def format_char(char):
    """Format character info for display."""
    return f"  {char.name} ({char.status})\n    Job: {char.job} | Condition: {char.condition}"


def format_hull(hull):
    """Format hull info for display."""
    return f"  {hull.name} - Health: {hull.health_pct}%"


def format_item(item):
    """Format item info for display."""
    return f"  {item.identifier} ({item.item_type}) - Condition: {item.condition_pct}%"


def format_mission(mission):
    """Format mission info for display."""
    status = "✓" if mission.selected else " "
    return f"  [{status}] {mission.prefab_id}\n    Location: {mission.location}"


def draw_map(window, data):
    """Draw a map of locations on the canvas."""
    canvas = window["-MAP-"].Widget
    
    # Clear canvas
    canvas.delete("all")
    
    if not data.locations:
        canvas.create_text(400, 250, text="No locations available", fill="gray", font=("Arial", 16))
        return
    
    # Find bounds
    all_positions = []
    for loc in data.locations:
        if loc.position:
            try:
                x, y = map(float, loc.position.split(","))
                all_positions.append((x, y))
            except:
                pass
    
    if not all_positions:
        canvas.create_text(400, 250, text="No position data available", fill="gray", font=("Arial", 16))
        return
    
    min_x = min(p[0] for p in all_positions)
    max_x = max(p[0] for p in all_positions)
    min_y = min(p[1] for p in all_positions)
    max_y = max(p[1] for p in all_positions)
    
    # Scale to canvas
    canvas_width = 800
    canvas_height = 500
    padding = 50
    
    def scale_x(x):
        if max_x == min_x:
            return canvas_width / 2
        return padding + (x - min_x) / (max_x - min_x) * (canvas_width - 2 * padding)
    
    def scale_y(y):
        if max_y == min_y:
            return canvas_height / 2
        return padding + (y - min_y) / (max_y - min_y) * (canvas_height - 2 * padding)
    
    # Draw connections between locations
    for i, loc in enumerate(data.locations):
        if loc.position:
            try:
                x, y = map(float, loc.position.split(","))
                cx = scale_x(x)
                cy = scale_y(y)
                
                # Draw connections to other locations
                for other_loc in data.locations[i+1:]:
                    if other_loc.position:
                        try:
                            ox, oy = map(float, other_loc.position.split(","))
                            cx2 = scale_x(ox)
                            cy2 = scale_y(oy)
                            # Draw line if within reasonable distance
                            dist = math.sqrt((cx - cx2)**2 + (cy - cy2)**2)
                            if dist < 300:  # Only connect nearby locations
                                canvas.create_line(cx, cy, cx2, cy2, fill="gray", width=1, dash=(2, 2))
                        except:
                            pass
                
                # Draw circle
                radius = 8
                canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, 
                                  fill=color, outline="white", width=2)
                
                # Draw label
                canvas.create_text(cx, cy - radius - 10, text=loc.name[:20], 
                                  fill="white", font=("Arial", 8), anchor="center")
            except:
                pass
    
    # Draw legend
    canvas.create_text(400, 15, text="Map - Locations", fill="white", font=("Arial", 14, "bold"))
    
    y_pos = 480
    for biome, color in biome_colors.items():
        canvas.create_oval(10, y_pos - 5, 20, y_pos + 5, fill=color, outline="white")
        canvas.create_text(25, y_pos, text=biome, fill="white", font=("Arial", 8), anchor="w")
        y_pos += 15


def main():
    sg.theme("DarkGrey10")
    
    # Menu definition
    menu_def = [
        ["File", ["Open Save File", "Export JSON", "Export CSV", "---", "Exit"]],
        ["Help", ["About"]],
    ]
    
    # Layout
    layout = [
        [sg.Menu(menu_def, tearoff=False)],
        [sg.Text("Ready. Open a .save file to begin.", key="-STATUS-", size=(80, 1), relief=sg.RELIEF_SUNKEN)],
        [sg.TabGroup([
            [sg.Tab("Characters", [[sg.Multiline(size=(100, 20), key="-CHARS-", disabled=True)]])],
            [sg.Tab("Submarine", [[sg.Multiline(size=(100, 10), key="-SUB-", disabled=True)]])],
            [sg.Tab("Hulls", [[sg.Multiline(size=(100, 15), key="-HULLS-", disabled=True)]])],
            [sg.Tab("Items", [[sg.Multiline(size=(100, 15), key="-ITEMS-", disabled=True)]])],
            [sg.Tab("Missions", [[sg.Multiline(size=(100, 15), key="-MISSIONS-", disabled=True)]])],
            [sg.Tab("Map", [[sg.Canvas(size=(900, 550), key="-MAP-", background_color="black")]]),
             sg.Column([[sg.Text("Locations:", size=(20, 1))],
                       [sg.Listbox(values=[], size=(40, 20), key="-LOCATIONS-", enable_events=True)]])],
            [sg.Tab("Raw XML", [[sg.Multiline(size=(100, 25), key="-XML-", disabled=True, wrap_lines=False)]])],
        ])],
        [sg.Text("Log:", size=(80, 1))],
        [sg.Multiline(size=(80, 8), key="-LOG-", disabled=True, autoscroll=True)],
    ]
    
    window = sg.Window("Barotrauma Save Viewer", layout, size=(900, 700), finalize=True)
    
    current_file = None
    current_data = None
    
    def log_message(msg):
        """Add a message to the log window."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        window["-LOG-"].update(f"[{timestamp}] {msg}\n", append=True)
    
    log_message("Application started")
    
    while True:
        event, values = window.read()
        
        if event in (sg.WIN_CLOSED, "Exit"):
            break
        
        if event == "Open Save File":
            filepath = sg.popup_get_file(
                "Open Barotrauma Save File",
                file_types=[("Save files", "*.save"), ("All files", "*.*")],
                initial_folder=str(Path.home() / "AppData" / "LocalLow" / "Eyefish" / "Barotrauma" / "saves"),
                no_window=True,  # Just show the file browser
            )
            if filepath:
                try:
                    current_data = parse_save(Path(filepath))
                    current_file = filepath
                    
                    # Update status
                    log_message(f"Loaded: {Path(filepath).name}")
                    window["-STATUS-"].update(
                        f"Loaded: {Path(filepath).name} | {len(current_data.characters)} chars | "
                        f"{len(current_data.hulls)} hulls | {len(current_data.items)} items | "
                        f"{len(current_data.missions)} missions"
                    )
                    
                    # Update characters tab
                    chars_text = "\n".join(format_char(c) for c in current_data.characters)
                    window["-CHARS-"].update(chars_text if chars_text else "No characters found")
                    
                    # Update submarine tab
                    if current_data.submarine:
                        sub = current_data.submarine
                        sub_text = f"Name: {sub.name}\nType: {sub.sub_type}/{sub.class_}\nTier: {sub.tier}\n"
                        sub_text += f"Dimensions: {sub.dimensions}\nCargo Capacity: {sub.cargo_capacity}\n"
                        sub_text += f"Price: {sub.price}\nTags: {sub.tags}"
                        window["-SUB-"].update(sub_text)
                    else:
                        window["-SUB-"].update("No submarine data")
                    
                    # Update hulls tab
                    hulls_text = "\n".join(format_hull(h) for h in current_data.hulls)
                    window["-HULLS-"].update(hulls_text if hulls_text else "No hulls found")
                    
                    # Update items tab
                    items_text = "\n".join(format_item(i) for i in current_data.items)
                    window["-ITEMS-"].update(items_text if items_text else "No items found")
                    
                    # Update missions tab
                    missions_text = "\n".join(format_mission(m) for m in current_data.missions)
                    window["-MISSIONS-"].update(missions_text if missions_text else "No missions found")
                    
                    # Update map tab
                    draw_map(window, current_data)
                    
                    # Update locations list
                    location_names = [f"{loc.name} ({loc.biome})" for loc in current_data.locations]
                    window["-LOCATIONS-"].update(values=location_names)
                    
                    # Update XML tab
                    if current_data.raw_xml:
                        window["-XML-"].update(current_data.raw_xml)
                    else:
                        window["-XML-"].update("No raw XML available")
                    
                except Exception as e:
                    error_msg = f"Error loading file: {e}"
                    log_message(error_msg)
                    sg.popup_error(error_msg)
                    window["-STATUS-"].update(f"Error: {e}")
        
        elif event == "-LOCATIONS-":
            # Handle location selection
            if values["-LOCATIONS-"]:
                selected = values["-LOCATIONS-"][0]
                log_message(f"Selected: {selected}")
        
        elif event == "Export JSON":
            if not current_data:
                sg.popup_error("No file loaded!")
                continue
            
            filepath = sg.popup_get_file(
                "Export to JSON",
                save_as=True,
                default_extension=".json",
                file_types=[("JSON files", "*.json"), ("All files", "*.*")],
                initial_folder=str(Path(current_file).parent) if current_file else None,
            )
            if filepath:
                data = {
                    "filename": str(current_data.path),
                    "submarine": vars(current_data.submarine) if current_data.submarine else None,
                    "characters": [vars(c) for c in current_data.characters],
                    "hulls": [vars(h) for h in current_data.hulls],
                    "structures": [vars(s) for s in current_data.structures],
                    "items": [vars(i) for i in current_data.items],
                    "locations": [vars(l) for l in current_data.locations],
                    "missions": [vars(m) for m in current_data.missions],
                }
                with open(filepath, "w") as f:
                    json.dump(data, f, indent=2)
                log_message(f"Exported to {filepath}")
                sg.popup(f"Exported to {filepath}")
        
        elif event == "Export CSV":
            if not current_data:
                sg.popup_error("No file loaded!")
                continue
            
            filepath = sg.popup_get_file(
                "Export Characters to CSV",
                save_as=True,
                default_extension=".csv",
                file_types=[("CSV files", "*.csv"), ("All files", "*.*")],
                initial_folder=str(Path(current_file).parent) if current_file else None,
            )
            if filepath:
                with open(filepath, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Name", "Status", "Condition", "Job", "Health", "Dead"])
                    for char in current_data.characters:
                        writer.writerow([
                            char.name,
                            char.status,
                            char.condition,
                            char.job,
                            getattr(char, "health", "N/A"),
                            getattr(char, "permanently_dead", False),
                        ])
                log_message(f"Exported CSV to {filepath}")
                sg.popup(f"Exported to {filepath}")
        
        elif event == "About":
            sg.popup(
                "Barotrauma Save Viewer\n\n"
                "A simple tool to view Barotrauma save files.\n\n"
                "Uses PySimpleGUI for the UI.",
                title="About",
            )
    
    window.close()


if __name__ == "__main__":
    main()
