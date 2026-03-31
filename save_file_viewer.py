#!/usr/bin/env python3
"""
Comprehensive Save File Viewer - Single Tool for All Save File Analysis

Features:
- Browse and select .save files from any location
- Auto-detect binary compression format (gzip streams)
- Extract XML content from nested gzip archives
- Parse character data directly from the save file
- Export to matching XML format
- GUI interface with tree view of characters
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import gzip
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

class SaveFileViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Submarine Save File Viewer")
        self.root.geometry("1000x700")
        
        # Current state
        self.current_save_path = None
        self.characters = []
        self.sub_info = {}
        
        # Menu reference for later use
        self.file_menu = None
        
        # Build UI
        self.build_ui()
    
    def build_ui(self):
        """Build the complete user interface"""
        
        # Menu bar
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Save File", command=self.browse_save_file)
        file_menu.add_separator()
        self.export_menu_item = file_menu.add_command(label="Export to XML", command=self.export_to_xml, state='disabled')
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        self.root.config(menu=menubar)
        
        # Store reference to file_menu for later use
        self.file_menu = file_menu
        
        # Export menu is at index 2 (0=Open, 1=separator, 2=Export)
        self.export_menu_index = 2
        
        # Main notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Tab 1: Character List
        char_frame = ttk.Frame(notebook)
        notebook.add(char_frame, text="Characters")
        
        # Tab 2: Save File Info
        info_frame = ttk.Frame(notebook)
        notebook.add(info_frame, text="Save File Info")
        
        # Tab 3: XML Preview
        xml_frame = ttk.Frame(notebook)
        notebook.add(xml_frame, text="XML Preview")
        
        # ========== CHARACTERS TAB ==========
        
        # Controls
        control_frame = ttk.Frame(char_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="Filter by Job:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.job_filter_var = tk.StringVar(value="All")
        self.job_combo = ttk.Combobox(control_frame, textvariable=self.job_filter_var, width=20)
        self.job_combo.pack(side=tk.LEFT)
        self.job_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_characters_table())
        
        ttk.Button(control_frame, text="Load File", command=self.load_selected_save).pack(side=tk.RIGHT, padx=(10, 0))
        
        # Split pane for table and stats
        char_pane = ttk.PanedWindow(char_frame, orient=tk.HORIZONTAL)
        char_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Character table frame
        table_container = ttk.LabelFrame(char_pane, text="Crew Manifest", padding="5")
        char_pane.add(table_container, weight=1)
        
        columns = ('ID', 'Name', 'Job', 'Condition', 'Position')
        self.char_tree = ttk.Treeview(table_container, columns=columns, show='headings', height=20)
        self.char_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        vsb = ttk.Scrollbar(table_container, orient="vertical", command=self.char_tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.char_tree.configure(yscrollcommand=vsb.set)
        
        for col in columns:
            self.char_tree.heading(col, text=col, anchor=tk.W)
            if col == 'ID':
                self.char_tree.column(col, width=60, anchor=tk.W)
            elif col == 'Position':
                self.char_tree.column(col, width=150, anchor=tk.W)
            else:
                self.char_tree.column(col, width=120, anchor=tk.W)
        
        self.char_tree.bind('<<TreeviewSelect>>', self.on_char_select)
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(char_pane, text="Statistics", padding="10")
        char_pane.add(stats_frame, weight=0)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=15, wrap=tk.WORD, state='disabled')
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Character detail frame
        detail_frame = ttk.LabelFrame(char_frame, text="Character Detail", padding="10")
        detail_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        self.detail_text = scrolledtext.ScrolledText(detail_frame, height=8, wrap=tk.WORD)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        self.detail_text.configure(state='disabled')
        
        # ========== SAVE FILE INFO TAB ==========
        info_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD)
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.info_text_widget = info_text
        
        # ========== XML PREVIEW TAB ==========
        xml_text = scrolledtext.ScrolledText(xml_frame, wrap=tk.NONE)
        xml_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        xml_text.configure(state='disabled')
        self.xml_text_widget = xml_text
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready - Select a save file to begin")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def browse_save_file(self):
        """Open file dialog to select a .save file"""
        filename = filedialog.askopenfilename(
            title="Select Save File",
            filetypes=[("Save Files", "*.save"), ("All Files", "*.*")]
        )
        if filename:
            self.current_save_path = filename
            self.status_var.set(f"Selected: {Path(filename).name}")
    
    def load_selected_save(self):
        """Load and parse the currently selected save file"""
        if not self.current_save_path or not Path(self.current_save_path).exists():
            messagebox.showerror("Error", "Please select a valid save file first!")
            return
        
        try:
            self.status_var.set(f"Loading: {Path(self.current_save_path).name}...")
            self.root.update()
            
            # Parse the save file
            self.parse_save_file()
            
            # Update UI
            self.refresh_characters_table()
            self.show_save_info()
            
            # Enable export menu using stored reference and index
            if hasattr(self, 'file_menu') and self.file_menu:
                self.file_menu.entryconfig(self.export_menu_index, state='normal')
            
            self.status_var.set(f"Loaded: {Path(self.current_save_path).name} - {len(self.characters)} characters found")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load save file:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def parse_save_file(self):
        """Parse the binary save file and extract character data using generic search"""
        
        # Read original compressed file
        with open(self.current_save_path, 'rb') as f:
            original_data = f.read()
        
        self.save_info = {
            'filename': Path(self.current_save_path).name,
            'original_size': len(original_data),
            'decompressed_size': 0,
            'main_stream_pos': 0,
            'main_stream_size': 0
        }
        
        # Level 0 decompression (outer gzip)
        level0_decompressed = gzip.decompress(original_data)
        self.save_info['decompressed_size'] = len(level0_decompressed)
        
        # Find the best Submarine XML stream using generic search
        result = self.find_best_submarine_xml(level0_decompressed)
        
        if not result:
            raise ValueError("No valid Submarine XML found in save file!")
        
        xml_text = result['xml_text']
        root = result['root']
        
        self.save_info['main_stream_pos'] = result['position']
        self.save_info['main_stream_size'] = len(result['decompressed'])
        self.xml_content = xml_text
        
        # Get submarine info
        self.sub_info = {
            'name': root.get('name', 'Unknown'),
            'type': root.get('type', 'Unknown'),
            'class': root.get('class', 'Unknown'),
            'tier': root.get('tier', 'Unknown'),
            'gameversion': root.get('gameversion', 'Unknown'),
            'dimensions': root.get('dimensions', 'Unknown'),
            'cargocapacity': root.get('cargocapacity', 'Unknown')
        }
        
        # Extract characters from duffelbag items
        self.characters = []
        for item in root.findall('.//Item[@identifier="duffelbag"]'):
            tags = item.get('Tags', '')
            
            name = None
            job = None
            
            tag_list = [t.strip() for t in tags.split(',')]
            for tag in tag_list:
                if tag.startswith('name:'):
                    name = tag[5:]
                elif tag.startswith('job:'):
                    job = tag[4:]
            
            if name and job:
                self.characters.append({
                    'id': int(item.get('ID', 0)),
                    'name': name,
                    'job': job,
                    'condition': f"{float(item.get('conditionpercentage', '100')):.2f}%",
                    'rect': item.get('rect', '')
                })
    
    def find_best_submarine_xml(self, level0_data):
        """Find the Submarine XML stream with the most characters"""
        
        best_result = None
        
        # Find all potential gzip positions
        for i in range(28, len(level0_data)):
            # Only valid gzip streams have method = 0x08 (deflate)
            if level0_data[i] == 0x1f and level0_data[i+1] == 0x8b and level0_data[i+2] == 0x08:
                try:
                    stream_data = level0_data[i:]
                    
                    # Decompress using gzip wrapper (MAX_WBITS|16)
                    decompressed = zlib.decompress(stream_data, zlib.MAX_WBITS|16)
                    
                    xml_text = decompressed.decode('utf-8')
                    
                    if '<' in xml_text and '>' in xml_text and 'Submarine' in xml_text:
                        root = ET.fromstring(xml_text)
                        char_count = len(root.findall('.//Item[@identifier="duffelbag"]'))
                        
                        # Keep track of best result (most characters = most complete state)
                        if not best_result or char_count > best_result['character_count']:
                            best_result = {
                                'position': i,
                                'decompressed': decompressed,
                                'xml_text': xml_text,
                                'root': root,
                                'character_count': char_count
                            }
                            
                except Exception as e:
                    continue
        
        return best_result
    
    def refresh_characters_table(self):
        """Refresh the character table with current filter"""
        # Clear existing items
        for item in self.char_tree.get_children():
            self.char_tree.delete(item)
        
        # Get current filter
        job_filter = self.job_filter_var.get()
        
        # Filter characters
        if job_filter != "All":
            filtered_chars = [c for c in self.characters if c['job'] == job_filter]
        else:
            filtered_chars = list(self.characters)
        
        # Insert items
        for char in sorted(filtered_chars, key=lambda x: int(x['id'])):
            item_id = self.char_tree.insert('', tk.END, values=(
                char['id'],
                char['name'],
                char['job'],
                char['condition'],
                char['rect']
            ))
            
            # Tag low condition characters
            try:
                condition_val = float(char['condition'].rstrip('%'))
                if condition_val < 50:
                    self.char_tree.item(item_id, tags=('low_condition',))
                elif condition_val < 80:
                    self.char_tree.item(item_id, tags=('medium_condition',))
            except ValueError:
                pass
        
        # Configure tags
        self.char_tree.tag_configure('low_condition', foreground='red', font=('Arial', 9, 'bold'))
        self.char_tree.tag_configure('medium_condition', foreground='orange')
        
        # Update stats
        self.update_stats()
    
    def update_stats(self):
        """Update statistics display"""
        unique_names = len(set(c['name'] for c in self.characters))
        
        job_counts = defaultdict(int)
        for char in self.characters:
            job_counts[char['job']] += 1
        
        stats = f"""Save File Information:
-------------------
File: {self.save_info.get('filename', 'Unknown')}
Original Size: {self.save_info.get('original_size', 0):,} bytes
Decompressed Size: {self.save_info.get('decompressed_size', 0):,} bytes
Main Stream Position: {self.save_info.get('main_stream_pos', 0)}
Main Stream Size: {self.save_info.get('main_stream_size', 0):,} bytes

Submarine Information:
---------------------
Name: {self.sub_info.get('name', 'Unknown')}
Type: {self.sub_info.get('type', 'Unknown')}
Class: {self.sub_info.get('class', 'Unknown')}
Tier: {self.sub_info.get('tier', 'Unknown')}
Game Version: {self.sub_info.get('gameversion', 'Unknown')}

Crew Statistics:
---------------
Total Characters: {len(self.characters)}
Unique Names: {unique_names}
Jobs: {len(job_counts)}

Characters by Job:
------------------
"""
        for job, count in sorted(job_counts.items()):
            stats += f"  {job}: {count}\n"
        
        self.stats_text.configure(state='normal')
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, stats)
        self.stats_text.configure(state='disabled')
    
    def show_save_info(self):
        """Show save file information"""
        info = f"""Save File: {self.save_info.get('filename', 'Unknown')}

Compression:
-----------
Original Size: {self.save_info.get('original_size', 0):,} bytes
Level 0 Decompressed: {self.save_info.get('decompressed_size', 0):,} bytes
Main Stream Position: {self.save_info.get('main_stream_pos', 0)}
Main Stream Size: {self.save_info.get('main_stream_size', 0):,} bytes

Submarine Details:
-----------------
Name: {self.sub_info.get('name', 'Unknown')}
Type: {self.sub_info.get('type', 'Unknown')}
Class: {self.sub_info.get('class', 'Unknown')}
Tier: {self.sub_info.get('tier', 'Unknown')}

Character Count: {len(self.characters)} crew members found
"""
        
        self.info_text_widget.configure(state='normal')
        self.info_text_widget.delete(1.0, tk.END)
        self.info_text_widget.insert(tk.END, info)
        self.info_text_widget.configure(state='disabled')
    
    def on_char_select(self, event):
        """Handle character selection"""
        selection = self.char_tree.selection()
        if not selection:
            return
        
        item = self.char_tree.item(selection[0])
        values = item['values']
        
        if len(values) < 5:
            return
        
        char_id = int(values[0])
        char_data = next((c for c in self.characters if c['id'] == char_id), None)
        
        if not char_data:
            return
        
        details = f"""
Character ID: {char_data['id']}
Name: {char_data['name']}
Job: {char_data['job']}
Condition: {char_data['condition']}
Position (rect): {char_data['rect']}

Submarine Information:
  - Name: {self.sub_info.get('name', 'Unknown')}
  - Type: {self.sub_info.get('type', 'Unknown')}
  - Class: {self.sub_info.get('class', 'Unknown')}
  - Tier: {self.sub_info.get('tier', 'Unknown')}
  - Game Version: {self.sub_info.get('gameversion', 'Unknown')}

This character is stored in a duffelbag container with their personal items.
"""
        
        self.detail_text.configure(state='normal')
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, details)
        self.detail_text.configure(state='disabled')
    
    def export_to_xml(self):
        """Export character data to XML file"""
        if not self.characters:
            messagebox.showwarning("Warning", "No character data to export!")
            return
        
        # Generate XML
        root = ET.Element('CharacterData')
        
        sub_elem = ET.SubElement(root, 'SubmarineInfo')
        for key, value in self.sub_info.items():
            sub_elem.set(key, str(value))
        
        chars_elem = ET.SubElement(root, 'Characters')
        for char in sorted(self.characters, key=lambda x: int(x['id'])):
            char_elem = ET.SubElement(chars_elem, 'Character')
            for key, value in char.items():
                char_elem.set(key, str(value))
        
        # Generate filename
        save_path = Path(self.current_save_path)
        xml_filename = save_path.stem + "_characters.xml"
        
        # Ask user where to save
        output_path = filedialog.asksaveasfilename(
            title="Export Character Data",
            defaultextension=".xml",
            initialfile=xml_filename,
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        
        if output_path:
            try:
                tree = ET.ElementTree(root)
                ET.indent(tree, space='  ')
                tree.write(output_path, encoding='UTF-8', xml_declaration=True)
                
                messagebox.showinfo("Success", f"Character data exported to:\n{output_path}")
                self.status_var.set(f"Exported: {Path(output_path).name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")

def main():
    root = tk.Tk()
    app = SaveFileViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
