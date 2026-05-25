#!/usr/bin/env python3
"""
PlayStation 2 Virtual Memory Card Graphical User Interface.
PS2-VMC-GUI uses ps2vmc-tool to manage saves on a VMC file.
Ported from PowerShell to Python for Linux.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter import simpledialog
import subprocess
import os
import sys
import platform
import tempfile
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
import urllib.request
import threading
from PIL import Image, ImageTk
from io import BytesIO
import struct
import re

class PS2VMCGui:
    def __init__(self, root):
        self.root = root
        self.root.title("PS2 Virtual Memory Card GUI")
        self.root.geometry("900x800")
        
        # Configuration paths
        self.script_path = Path(__file__).parent
        self.temp_dir = Path(tempfile.gettempdir()) / "ps2-vmc-gui"
        self.temp_dir.mkdir(exist_ok=True)
        
        self.license_file = self.script_path / "LICENSE.txt"
        self.setup_files_zip = self.script_path / "SetupFiles.zip"
        self.vmc_tool = self.temp_dir / ("ps2vmc-tool.exe" if platform.system() == "Windows" else "ps2vmc-tool")
        self.blank_vmc_zip = self.temp_dir / "BlankVMC.zip"
        
        self.box_art_database = "https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/default/"
        self.default_dir = str(Path.home() / "Desktop")
        
        self.current_vmc = None
        self.box_art_enabled = False
        self.art_photo = None
        
        # Encodings
        self.jis_encoding = 'shift_jis'
        self.w1252_encoding = 'cp1252'
        
        # Check license first
        if not self.check_license():
            sys.exit(0)
        
        # Setup files
        self.setup_environment()
        
        # Create GUI
        self.create_widgets()
    
    def check_license(self):
        """Show license dialog"""
        if not self.license_file.exists():
            messagebox.showerror("Error", "License file not detected")
            return False
        
        with open(self.license_file, 'r', encoding='utf-8') as f:
            license_text = f.read()
        
        # Create license window
        license_window = tk.Toplevel(self.root)
        license_window.title("Please Read the Software License")
        license_window.geometry("800x500")
        license_window.transient(self.root)
        license_window.grab_set()
        license_window.focus_force()
        
        text_widget = scrolledtext.ScrolledText(license_window, wrap=tk.WORD, bg='white')
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, license_text)
        text_widget.config(state=tk.DISABLED)
        
        frame = tk.Frame(license_window)
        frame.pack(pady=10)
        
        result = [None]
        
        def accept():
            result[0] = True
            license_window.destroy()
        
        def decline():
            result[0] = False
            license_window.destroy()
        
        tk.Button(frame, text="Accept", command=accept, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Decline", command=decline, width=10).pack(side=tk.LEFT, padx=5)
        
        license_window.wait_window()
        return result[0]
    
    def setup_environment(self):
        """Extract setup files"""
        if self.setup_files_zip.exists():
            try:
                with zipfile.ZipFile(self.setup_files_zip, 'r') as zip_ref:
                    zip_ref.extractall(self.temp_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to extract setup files: {e}")
                sys.exit(0)
        else:
            messagebox.showerror("Error", "SetupFiles zip file not detected")
            sys.exit(0)
    
    def create_widgets(self):
        """Create main GUI widgets"""
        
        # Top frame - VMC selection
        top_frame = ttk.Frame(self.root)
        top_frame.pack(padx=10, pady=10, fill=tk.X)
        
        ttk.Label(top_frame, text="Please Choose a VMC file:").pack(side=tk.LEFT)
        
        ttk.Button(top_frame, text="Open File", command=self.open_vmc_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Create New", command=self.create_new_vmc).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Scan Folder", command=self.scan_folder).pack(side=tk.LEFT, padx=5)
        
        self.box_art_var = tk.BooleanVar()
        ttk.Checkbutton(top_frame, text="Display Box Art", variable=self.box_art_var, 
                       command=self.toggle_box_art).pack(side=tk.LEFT, padx=5)
        
        # VMC file label
        self.label_vmc = ttk.Label(self.root, text="", foreground="blue")
        self.label_vmc.pack(padx=10, pady=5, fill=tk.X)
        
        # VMC info text box
        self.text_vmc_info = scrolledtext.ScrolledText(self.root, height=8, wrap=tk.WORD)
        self.text_vmc_info.pack(padx=10, pady=5, fill=tk.BOTH, expand=False)
        self.text_vmc_info.insert(tk.END, "Please Click Open File and select a VMC file.")
        self.text_vmc_info.config(state=tk.DISABLED)
        
        # Buttons frame - operations
        buttons_frame = ttk.Frame(self.root)
        buttons_frame.pack(padx=10, pady=5, fill=tk.X)
        
        ttk.Button(buttons_frame, text="ERASE and Format VMC", command=self.format_vmc).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Import Save File (.psu)", command=self.import_psu).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Import Save File (.PSV)", command=self.import_psv).pack(side=tk.LEFT, padx=2)
        
        # ListView for saves
        columns = ("Name", "Friendly Name", "Size", "Date")
        self.vmc_listview = ttk.Treeview(self.root, columns=columns, height=12, show='headings')
        
        self.vmc_listview.column("Name", width=200)
        self.vmc_listview.column("Friendly Name", width=300)
        self.vmc_listview.column("Size", width=80)
        self.vmc_listview.column("Date", width=100)
        
        self.vmc_listview.heading("Name", text="Name")
        self.vmc_listview.heading("Friendly Name", text="Friendly Name")
        self.vmc_listview.heading("Size", text="Size")
        self.vmc_listview.heading("Date", text="Date")
        
        self.vmc_listview.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.vmc_listview.bind('<<TreeviewSelect>>', self.on_save_selected)
        
        # Bottom buttons frame
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(padx=10, pady=10, fill=tk.X)
        
        ttk.Button(bottom_frame, text="DELETE Save", command=self.delete_save).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom_frame, text="Export Save File (.psu)", command=self.export_psu).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom_frame, text="Export ALL Saves (.psu)", command=self.export_all_psu).pack(side=tk.LEFT, padx=2)
        ttk.Button(bottom_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT, padx=2)
    
    def run_command(self, cmd):
        """Run shell command and return output"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
            return result.stdout + result.stderr
        except Exception as e:
            return str(e)
    
    def get_vmc_tool_path(self):
        """Get the path to ps2vmc-tool (check in temp dir and system)"""
        # First try temp directory
        if self.vmc_tool.exists():
            return str(self.vmc_tool)
        
        # Try system paths with platform-specific executable naming
        if platform.system() == "Windows":
            tool_names = ["ps2vmc-tool.exe", "ps2vmc-tool"]
            search_cmd = "where"
            null_redirect = "2>nul"
        else:
            tool_names = ["ps2vmc-tool", "ps2vmc-tool.exe"]
            search_cmd = "which"
            null_redirect = "2>/dev/null || command -v"
        
        for tool_name in tool_names:
            if platform.system() == "Windows":
                result = self.run_command(f"{search_cmd} {tool_name} {null_redirect}")
            else:
                result = self.run_command(f"{search_cmd} {tool_name} {null_redirect} {tool_name}")
            if result.strip():
                return result.strip()
        
        return None
    
    def get_save_name(self, icon_sys_file):
        """Extract save name from icon.sys file"""
        try:
            with open(icon_sys_file, 'rb') as f:
                data = f.read()
            
            # Extract save name from bytes 192-259
            save_name_bytes = data[192:260]
            
            # Try to decode with shift_jis
            try:
                save_name = save_name_bytes.decode(self.jis_encoding)
            except:
                save_name = save_name_bytes.decode(self.w1252_encoding, errors='ignore')
            
            # Clean up
            save_name = save_name.split('\x00')[0].strip()
            return save_name if save_name else None
        except Exception as e:
            print(f"Error reading save name: {e}")
            return None

    def parse_list_line(self, line):
        """Parse a ps2vmc-tool list output line into components"""
        if not line or line.strip() == "":
            return None

        # Newer ps2vmc-tool output uses pipe-separated columns
        if '|' in line and not line.startswith('PS2VMC-TOOL'):
            fields = [field.strip() for field in line.split('|')]
            if len(fields) < 5:
                return None
            name = fields[0]
            file_type = fields[1]
            size = fields[2]
            date = ' '.join(fields[4:]).strip()
            return {
                'name': name,
                'type': file_type,
                'size': size,
                'date': date,
            }

        # Fallback: older output style with slash separators
        if '/' in line:
            parts = [p.strip() for p in line.split('/')]
            if len(parts) < 4:
                return None
            name = parts[0]
            file_type = parts[1]
            size = parts[2]
            date = parts[3] if len(parts) > 3 else ''
            return {
                'name': name,
                'type': file_type,
                'size': size,
                'date': date,
            }

        return None
    
    def open_vmc_file(self):
        """Open VMC file dialog"""
        file_path = filedialog.askopenfilename(
            initialdir=self.default_dir,
            filetypes=[
                ("VMC Files", ("*.bin", "*.BIN", "*.vmc", "*.VMC", "*.ps2", "*.PS2", "*.mcd", "*.MCD")),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            self.default_dir = str(Path(file_path).parent)
            self.load_vmc(file_path)
    
    def load_vmc(self, vmc_file):
        """Load and display VMC file info"""
        vmc_path = Path(vmc_file)
        
        if not vmc_path.exists():
            messagebox.showerror("Error", "VMC file not found")
            return
        
        vmc_size = vmc_path.stat().st_size
        
        # Validate size (4MB to 8GB, multiple of 4MB)
        if vmc_size <= 0 or vmc_size > 0x20000000 or (vmc_size % 0x400000) != 0:
            messagebox.showerror("Error", 
                f"The Selected VMC File is either too big, too small, or not 4MB or 8MB aligned.\n"
                f"The VMC File Size is {vmc_size / 1024 / 1024:.2f} MB.")
            return
        
        self.current_vmc = vmc_file
        self.label_vmc.config(text=vmc_file)
        
        # Get VMC info
        tool_path = self.get_vmc_tool_path()
        if not tool_path:
            messagebox.showerror("Error", "ps2vmc-tool not found. Please ensure it's installed or in SetupFiles.zip")
            return
        
        info_output = self.run_command(f'"{tool_path}" "{vmc_file}" --mc-info')
        
        self.text_vmc_info.config(state=tk.NORMAL)
        self.text_vmc_info.delete(1.0, tk.END)
        
        if "no PS2 Memory Card detected" in info_output or "Error" in info_output:
            self.text_vmc_info.insert(tk.END, info_output + "\nThe VMC file is unreadable.")
        else:
            self.text_vmc_info.insert(tk.END, info_output)
            
            # Get free space
            free_output = self.run_command(f'"{tool_path}" "{vmc_file}" --mc-free')
            for line in free_output.split('\n'):
                if line and 'PS2VMC-TOOL' not in line and 'Calculating' not in line:
                    self.text_vmc_info.insert(tk.END, line + '\n')
            
            # Load saves list
            self.load_vmc_list(vmc_file)
        
        self.text_vmc_info.config(state=tk.DISABLED)
    
    def load_vmc_list(self, vmc_file):
        """Load and display list of saves in VMC"""
        tool_path = self.get_vmc_tool_path()
        if not tool_path:
            return
        
        # Clear listview
        for item in self.vmc_listview.get_children():
            self.vmc_listview.delete(item)
        
        # Get root directory
        list_output = self.run_command(f'"{tool_path}" "{vmc_file}" --list /')
        
        for line in list_output.split('\n'):
            if any(x in line for x in ['PS2VMC-TOOL', '----------', '"."', '".."']):
                continue
            
            if not line.strip():
                continue
            
            parsed = self.parse_list_line(line)
            if not parsed:
                continue
            
            folder_name = parsed['name']
            file_type = parsed['type']
            size = parsed['size']
            time_str = parsed['date']
            
            if folder_name in ['.', '..']:
                continue
            
            if "<file>" in file_type:
                messagebox.showwarning("Error", "You must manually delete all files from root as this GUI does not support them")
                continue
            
            all_size = 0
            if re.search(r'\d+', size):
                all_size = int(re.sub(r'[^0-9]', '', size))
            
            # Get files in save folder
            save_list_output = self.run_command(f'"{tool_path}" "{vmc_file}" --list {folder_name}')
            
            for save_line in save_list_output.split('\n'):
                if any(x in save_line for x in ['PS2VMC-TOOL', '----------']):
                    continue
                
                if not save_line.strip():
                    continue
                
                save_parsed = self.parse_list_line(save_line)
                if not save_parsed:
                    continue
                
                save_name = save_parsed['name']
                if save_name in ['.', '..']:
                    continue
                
                save_file_type = save_parsed['type']
                save_file_size = save_parsed['size']
                
                if "<dir>" in save_file_type:
                    messagebox.showwarning(
                        "Error",
                        "You must manually delete all subfolders as this GUI does not support them"
                    )
                    continue
                
                if re.search(r'\d+', save_file_size):
                    all_size += int(re.sub(r'[^0-9]', '', save_file_size))
            
            # Get friendly name from icon.sys
            friendly_name = None
            if "icon.sys" in save_list_output:
                extract_output = self.run_command(
                    f'"{tool_path}" "{vmc_file}" --extract-file {folder_name}/icon.sys {self.temp_dir}/icon.sys'
                )
                
                if "Error" not in extract_output:
                    friendly_name = self.get_save_name(str(self.temp_dir / "icon.sys"))
            
            # Format size
            rounded_size = f"{all_size // 1024}KB"
            
            # Extract date
            date_str = time_str.split()[0] if time_str else ""
            
            # Add to listview
            self.vmc_listview.insert('', tk.END, values=(
                folder_name,
                friendly_name or "",
                rounded_size,
                date_str
            ))
    
    def create_new_vmc(self):
        """Create new VMC file"""
        file_path = filedialog.asksaveasfilename(
            initialdir=self.default_dir,
            defaultextension=".bin",
            initialfile="NewVMC8MB.bin",
            filetypes=[
                ("VMC Files", ("*.bin", "*.BIN", "*.vmc", "*.VMC", "*.ps2", "*.PS2", "*.mcd", "*.MCD")),
                ("All Files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        self.default_dir = str(Path(file_path).parent)
        
        tool_path = self.get_vmc_tool_path()
        if not tool_path:
            messagebox.showerror("Error", "ps2vmc-tool not found")
            return
        
        # Extract blank VMC if needed
        if self.blank_vmc_zip.exists():
            try:
                with zipfile.ZipFile(self.blank_vmc_zip, 'r') as zip_ref:
                    zip_ref.extractall(self.temp_dir)
                
                blank_vmc = self.temp_dir / "BlankVMC.bin"
                if blank_vmc.exists():
                    shutil.copy(blank_vmc, file_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create VMC: {e}")
                return
        
        # Format the new VMC
        format_output = self.run_command(f'"{tool_path}" "{file_path}" --mc-format')
        messagebox.showinfo("Format Complete", format_output)
        
        self.load_vmc(file_path)
    
    def scan_folder(self):
        """Scan folder for VMC files"""
        folder = filedialog.askdirectory()
        if not folder:
            return
        
        tool_path = self.get_vmc_tool_path()
        if not tool_path:
            messagebox.showerror("Error", "ps2vmc-tool not found")
            return
        
        output = f"List of all saves found in {folder} as of {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}\n\n"
        
        patterns = [
            "*.bin", "*.BIN",
            "*.vmc", "*.VMC",
            "*.ps2", "*.PS2",
            "*.mcd", "*.MCD"
        ]
        seen_files = set()
        for pattern in patterns:
            for vmc_file in Path(folder).glob(pattern):
                if vmc_file in seen_files:
                    continue
                seen_files.add(vmc_file)
                result = self.get_vmc_scan_list(str(vmc_file), tool_path)
                if result:
                    output += f"{vmc_file.name}\n{result}\n"
        
        # Show results in text window
        result_window = tk.Toplevel(self.root)
        result_window.title(f"List of all saves found in {folder}")
        result_window.geometry("600x400")
        
        text_widget = scrolledtext.ScrolledText(result_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, output)
        text_widget.config(state=tk.DISABLED)
    
    def get_vmc_scan_list(self, vmc_file, tool_path):
        """Get scan list for a VMC file"""
        result = ""
        list_output = self.run_command(f'"{tool_path}" "{vmc_file}" --list /')
        
        for line in list_output.split('\n'):
            if any(x in line for x in ['PS2VMC-TOOL', '----------', '"."', '".."']):
                continue
            
            if not line.strip():
                continue
            
            parsed = self.parse_list_line(line)
            if not parsed:
                continue
            
            folder_name = parsed['name']
            time_str = parsed['date']
            
            # Similar logic to load_vmc_list but simpler
            friendly_name = ""
            size = "0KB"
            
            result += f"{folder_name}\t\"{friendly_name}\"\t{size}\t{time_str}\n"
        
        return result
    
    def format_vmc(self):
        """Format (erase) VMC file"""
        if not self.current_vmc:
            messagebox.showwarning("Warning", "Please select a VMC file first")
            return
        
        if messagebox.askyesno("WARNING", "WARNING THIS WILL DELETE ALL SAVE DATA\n\nARE YOU SURE?"):
            tool_path = self.get_vmc_tool_path()
            if not tool_path:
                messagebox.showerror("Error", "ps2vmc-tool not found")
                return
            
            output = self.run_command(f'"{tool_path}" "{self.current_vmc}" --mc-format')
            messagebox.showinfo("Format Complete", output)
            self.load_vmc(self.current_vmc)
    
    def import_psu(self):
        """Import PSU save file"""
        if not self.current_vmc:
            messagebox.showwarning("Warning", "Please select a VMC file first")
            return
        
        file_path = filedialog.askopenfilename(
            initialdir=self.default_dir,
            filetypes=[("LaunchELF (.psu)", "*.psu"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
        
        tool_path = self.get_vmc_tool_path()
        if not tool_path:
            messagebox.showerror("Error", "ps2vmc-tool not found")
            return
        
        file_size = Path(file_path).stat().st_size
        if file_size > 0x600000:
            messagebox.showerror("Error", "The Selected LaunchELF .psu file is too large.")
            return
        
        output = self.run_command(f'"{tool_path}" "{self.current_vmc}" --psu-import "{file_path}"')
        
        if "Error" in output:
            messagebox.showerror("Error", f"Failed to import save:\n{output}")
        else:
            messagebox.showinfo("Success", "Save imported successfully")
        
        self.load_vmc(self.current_vmc)
    
    def import_psv(self):
        """Import PSV save file"""
        if not self.current_vmc:
            messagebox.showwarning("Warning", "Please select a VMC file first")
            return
        
        file_path = filedialog.askopenfilename(
            initialdir=self.default_dir,
            filetypes=[("PS2 Save for PS3 (.PSV)", "*.PSV"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
        
        tool_path = self.get_vmc_tool_path()
        if not tool_path:
            messagebox.showerror("Error", "ps2vmc-tool not found")
            return
        
        file_size = Path(file_path).stat().st_size
        if file_size > 0x600000:
            messagebox.showerror("Error", "The Selected .PSV file is too large.")
            return
        
        output = self.run_command(f'"{tool_path}" "{self.current_vmc}" --psv-import "{file_path}"')
        
        if "Error" in output:
            messagebox.showerror("Error", f"Failed to import save:\n{output}")
        else:
            messagebox.showinfo("Success", "Save imported successfully")
        
        self.load_vmc(self.current_vmc)
    
    def export_psu(self):
        """Export single save as PSU"""
        if not self.current_vmc:
            messagebox.showwarning("Warning", "Please select a VMC file first")
            return
        
        selected = self.vmc_listview.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a save to export")
            return
        
        item = selected[0]
        save_name = self.vmc_listview.item(item)['values'][0]
        
        file_path = filedialog.asksaveasfilename(
            initialdir=self.default_dir,
            defaultextension=".psu",
            initialfile=f"{save_name}.psu",
            filetypes=[("LaunchELF (.psu)", "*.psu"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
        
        tool_path = self.get_vmc_tool_path()
        if not tool_path:
            messagebox.showerror("Error", "ps2vmc-tool not found")
            return
        
        output = self.run_command(f'"{tool_path}" "{self.current_vmc}" --psu-export "{save_name}" "{file_path}"')
        
        if "Error" in output:
            messagebox.showerror("Error", f"Failed to export save:\n{output}")
        else:
            messagebox.showinfo("Success", "Save exported successfully")
            self.default_dir = str(Path(file_path).parent)
    
    def export_all_psu(self):
        """Export all saves as PSU"""
        if not self.current_vmc:
            messagebox.showwarning("Warning", "Please select a VMC file first")
            return
        
        folder = filedialog.askdirectory()
        if not folder:
            return
        
        tool_path = self.get_vmc_tool_path()
        if not tool_path:
            messagebox.showerror("Error", "ps2vmc-tool not found")
            return
        
        for item in self.vmc_listview.get_children():
            save_name = self.vmc_listview.item(item)['values'][0]
            export_file = os.path.join(folder, f"{save_name}.psu")
            
            output = self.run_command(
                f'"{tool_path}" "{self.current_vmc}" --psu-export "{save_name}" "{export_file}"'
            )
            
            if "Error" in output:
                messagebox.showwarning("Warning", f"Failed to export {save_name}")
        
        messagebox.showinfo("Success", "All saves exported successfully")
    
    def delete_save(self):
        """Delete a save from VMC"""
        if not self.current_vmc:
            messagebox.showwarning("Warning", "Please select a VMC file first")
            return
        
        selected = self.vmc_listview.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a save to delete")
            return
        
        if messagebox.askyesno("WARNING", "WARNING THIS WILL DELETE SAVE DATA\n\nARE YOU SURE?"):
            item = selected[0]
            save_name = self.vmc_listview.item(item)['values'][0]
            
            tool_path = self.get_vmc_tool_path()
            if not tool_path:
                messagebox.showerror("Error", "ps2vmc-tool not found")
                return
            
            # Get files in save folder
            list_output = self.run_command(f'"{tool_path}" "{self.current_vmc}" --list {save_name}')
            
            # Delete each file
            for line in list_output.split('\n'):
                if any(x in line for x in ['PS2VMC-TOOL', '----------', '"."', '".."']):
                    continue
                
                if not line.strip():
                    continue
                
                parts = [p.strip() for p in line.split('/')]
                if len(parts) < 2:
                    continue
                
                file_name = parts[0]
                
                delete_output = self.run_command(
                    f'"{tool_path}" "{self.current_vmc}" --remove {save_name}/{file_name}'
                )
                
                if "Error" in delete_output:
                    messagebox.showerror("Error", f"Failed to delete file: {delete_output}")
            
            # Delete directory
            delete_dir_output = self.run_command(
                f'"{tool_path}" "{self.current_vmc}" --remove-directory {save_name}'
            )
            
            if "Error" in delete_dir_output:
                messagebox.showerror("Error", f"Failed to delete save directory: {delete_dir_output}")
            else:
                messagebox.showinfo("Success", "Save deleted successfully")
            
            self.load_vmc(self.current_vmc)
    
    def on_save_selected(self, event):
        """Handle save selection"""
        if self.box_art_var.get():
            self.load_box_art()
    
    def toggle_box_art(self):
        """Toggle box art display"""
        if self.box_art_var.get():
            self.load_box_art()
        else:
            # Hide box art
            pass
    
    def load_box_art(self):
        """Load and display box art"""
        selected = self.vmc_listview.selection()
        if not selected:
            return
        
        item = selected[0]
        save_name = self.vmc_listview.item(item)['values'][0]
        
        # Extract serial (first 10 characters, format: SLUS-12345)
        serial = save_name[:10] if len(save_name) >= 10 else save_name
        
        # Thread to download without blocking UI
        def download():
            try:
                url = f"{self.box_art_database}{serial}.jpg"
                with urllib.request.urlopen(url, timeout=5) as response:
                    image_data = response.read()
                    image = Image.open(BytesIO(image_data))
                    image.thumbnail((300, 450), Image.Resampling.LANCZOS)
                    self.art_photo = ImageTk.PhotoImage(image)
                    # Show in a new window
                    art_window = tk.Toplevel(self.root)
                    art_window.title(f"Box Art - {serial}")
                    label = tk.Label(art_window, image=self.art_photo)
                    label.pack()
            except Exception as e:
                print(f"Could not load box art: {e}")
        
        thread = threading.Thread(target=download, daemon=True)
        thread.start()


def main():
    root = tk.Tk()
    app = PS2VMCGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
