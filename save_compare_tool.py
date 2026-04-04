import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import gzip
import re
from pathlib import Path

def extract_all_missions(content_str):
    """Extract all missions with their full details"""
    missions = []
    
    block_pattern = r'<location[^>]*>(.*?)</location>'
    location_matches = list(re.finditer(block_pattern, content_str, re.DOTALL))
    
    for loc_match in location_matches:
        loc_content = loc_match.group(1)
        
        name_match = re.search(r'name="([^"]+)"', loc_content)
        type_match = re.search(r'type="([^"]+)"', loc_content)
        
        loc_name = name_match.group(1) if name_match else "Unknown"
        loc_type = type_match.group(1) if type_match else "Unknown"
        
        mission_blocks = re.findall(r'<missions>(.*?)</missions>', loc_content, re.DOTALL)
        
        for block_idx, block_content in enumerate(mission_blocks):
            missions_in_block = re.findall(r'<mission([^/>]*)/>', block_content)
            
            for mission_xml in missions_in_block:
                prefab_match = re.search(r'prefabid="([^"]+)"', mission_xml)
                dest_match = re.search(r'destinationindex="(\d+)"', mission_xml)
                origin_match = re.search(r'origin="(\d+)"', mission_xml)
                times_match = re.search(r'TimesAttempted="(\d+)"', mission_xml)
                selected_match = re.search(r'selected="([^"]+)"', mission_xml)
                
                if prefab_match:
                    missions.append({
                        'location': loc_name,
                        'type': loc_type,
                        'prefabid': prefab_match.group(1),
                        'destinationindex': dest_match.group(1) if dest_match else "N/A",
                        'origin': origin_match.group(1) if origin_match else "N/A",
                        'TimesAttempted': int(times_match.group(1)) if times_match else 0,
                        'selected': selected_match.group(1) == "true" if selected_match else False
                    })
    
    return missions

def load_save_file(filepath):
    """Load and parse a save file"""
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        
        level0 = gzip.decompress(data)
        content_str = level0.decode('utf-8', errors='ignore')
        
        missions = extract_all_missions(content_str)
        
        max_match = re.search(r'MaxMissionCount="(\d+)"', content_str)
        char_match = re.search(r'<Character[^>]*>', content_str)
        char_name = "Unknown"
        
        if char_match:
            name_match = re.search(r'name="([^"]+)"', char_match.group(0))
            if name_match:
                char_name = name_match.group(1)
        
        return {
            'filepath': filepath,
            'filename': Path(filepath).name,
            'total_missions': len(missions),
            'missions': missions,
            'max_mission_count': max_match.group(1) if max_match else "N/A",
            'character': char_name
        }
    except Exception as e:
        return {'error': str(e)}

class SaveCompareTool(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Barotrauma Save Compare Tool")
        self.geometry("1000x700")
        
        # Find all save files
        self.save_files = sorted([str(p) for p in Path('.').glob('*.save')])
        newer_saves = list(Path('newer-saves').glob('*.save')) if Path('newer-saves').exists() else []
        self.save_files.extend([str(p) for p in newer_saves])
        
        # Load all saves
        self.saves = {}
        for filepath in self.save_files:
            save_data = load_save_file(filepath)
            key = Path(filepath).name
            if 'error' not in save_data:
                self.saves[key] = save_data
        
        self.setup_ui()
    
    def setup_ui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Summary tab
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="Summary")
        self.create_summary_tab(summary_frame)
        
        # Comparison tab
        compare_frame = ttk.Frame(notebook)
        notebook.add(compare_frame, text="Compare Saves")
        self.create_compare_tab(compare_frame)
    
    def create_summary_tab(self, frame):
        # Title
        title_label = tk.Label(frame, text="Save File Summary", font=('Arial', 14, 'bold'))
        title_label.pack(pady=10)
        
        # Scrollable list of saves
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create table
        headers = ["File", "Character", "Total Missions", "Max Mission Count"]
        for col, header in enumerate(headers):
            tk.Label(scroll_frame, text=header, font=('Arial', 10, 'bold'), width=25).grid(row=0, column=col, padx=5, pady=5)
        
        row = 1
        for filename, save_data in sorted(self.saves.items()):
            tk.Label(scroll_frame, text=filename, width=25).grid(row=row, column=0, padx=5, pady=2)
            tk.Label(scroll_frame, text=save_data.get('character', 'N/A'), width=25).grid(row=row, column=1, padx=5, pady=2)
            tk.Label(scroll_frame, text=save_data.get('total_missions', 0), width=25).grid(row=row, column=2, padx=5, pady=2)
            tk.Label(scroll_frame, text=save_data.get('max_mission_count', 'N/A'), width=25).grid(row=row, column=3, padx=5, pady=2)
            row += 1
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_compare_tab(self, frame):
        # Title
        title_label = tk.Label(frame, text="Compare Two Save Files", font=('Arial', 14, 'bold'))
        title_label.pack(pady=10)
        
        # Dropdown selectors
        select_frame = ttk.Frame(frame)
        select_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(select_frame, text="Save File 1:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.save1_var = tk.StringVar(value=list(self.saves.keys())[0] if self.saves else "")
        save1_combo = ttk.Combobox(select_frame, textvariable=self.save1_var, values=list(self.saves.keys()))
        save1_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(select_frame, text="Save File 2:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.save2_var = tk.StringVar(value=list(self.saves.keys())[1] if len(self.saves) > 1 else "")
        save2_combo = ttk.Combobox(select_frame, textvariable=self.save2_var, values=list(self.saves.keys()))
        save2_combo.pack(side=tk.LEFT)
        
        # Compare button
        compare_btn = tk.Button(frame, text="Compare", command=self.compare_saves, bg='#4CAF50', fg='white')
        compare_btn.pack(pady=10)
        
        # Results area
        self.results_text = scrolledtext.ScrolledText(frame, height=25, width=90)
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    def compare_saves(self):
        save1_key = self.save1_var.get()
        save2_key = self.save2_var.get()
        
        if not save1_key or not save2_key:
            messagebox.showwarning("Select Files", "Please select two save files to compare")
            return
        
        if save1_key == save2_key:
            messagebox.showinfo("Same File", "Please select two different save files")
            return
        
        save1 = self.saves[save1_key]
        save2 = self.saves[save2_key]
        
        # Clear results
        self.results_text.delete(1.0, tk.END)
        
        # Calculate differences
        set1 = {(m['prefabid'], m['destinationindex']) for m in save1['missions']}
        set2 = {(m['prefabid'], m['destinationindex']) for m in save2['missions']}
        
        added = sorted(set2 - set1)
        removed = sorted(set1 - set2)
        
        # Display results
        self.results_text.insert(tk.END, "="*70 + "\n")
        self.results_text.insert(tk.END, f"COMPARISON: {save1_key} vs {save2_key}\n")
        self.results_text.insert(tk.END, "="*70 + "\n\n")
        
        # Basic stats
        self.results_text.insert(tk.END, "--- BASIC STATS ---\n")
        self.results_text.insert(tk.END, f"Save 1 ({save1_key}):\n")
        self.results_text.insert(tk.END, f"  Character: {save1['character']}\n")
        self.results_text.insert(tk.END, f"  Total Missions: {save1['total_missions']}\n")
        self.results_text.insert(tk.END, f"  Max Mission Count: {save1['max_mission_count']}\n\n")
        
        self.results_text.insert(tk.END, f"Save 2 ({save2_key}):\n")
        self.results_text.insert(tk.END, f"  Character: {save2['character']}\n")
        self.results_text.insert(tk.END, f"  Total Missions: {save2['total_missions']}\n")
        self.results_text.insert(tk.END, f"  Max Mission Count: {save2['max_mission_count']}\n\n")
        
        # Difference summary
        net_change = len(added) - len(removed)
        self.results_text.insert(tk.END, "--- DIFFERENCE SUMMARY ---\n")
        self.results_text.insert(tk.END, f"Missions added to {save2_key}: {len(added)}\n")
        self.results_text.insert(tk.END, f"Missions removed from {save2_key}: {len(removed)}\n")
        self.results_text.insert(tk.END, f"Net change: {'+' if net_change >= 0 else ''}{net_change} missions\n\n")
        
        # Added missions
        self.results_text.insert(tk.END, f"--- MISSIONS ADDED TO {save2_key.upper()} ---\n")
        for prefab, dest in added[:15]:  # Show first 15
            self.results_text.insert(tk.END, f"  + {prefab:40s} -> Dest: {dest}\n")
        
        if len(added) > 15:
            self.results_text.insert(tk.END, f"  ... and {len(added)-15} more\n")
        
        # Removed missions
        self.results_text.insert(tk.END, f"\n--- MISSIONS REMOVED FROM {save2_key.upper()} ---\n")
        for prefab, dest in removed[:15]:
            self.results_text.insert(tk.END, f"  - {prefab:40s} -> Dest: {dest}\n")
        
        if len(removed) > 15:
            self.results_text.insert(tk.END, f"  ... and {len(removed)-15} more\n")
        
        # Active missions
        active1 = [m for m in save1['missions'] if m['selected']]
        active2 = [m for m in save2['missions'] if m['selected']]
        
        self.results_text.insert(tk.END, f"\n--- ACTIVE MISSIONS ---\n")
        self.results_text.insert(tk.END, f"{save1_key}: {len(active1)} selected\n")
        for m in active1[:3]:
            self.results_text.insert(tk.END, f"  - {m['prefabid']}\n")
        
        self.results_text.insert(tk.END, f"\n{save2_key}: {len(active2)} selected\n")
        for m in active2[:3]:
            self.results_text.insert(tk.END, f"  - {m['prefabid']}\n")

if __name__ == "__main__":
    app = SaveCompareTool()
    app.mainloop()
