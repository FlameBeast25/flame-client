import sys
import os
import pprint
import customtkinter as ctk
import tkinter as tk
import ctypes
import subprocess
from tkinter import font

# Add minescript root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
minescript_root = os.path.dirname(current_dir)
if minescript_root not in sys.path:
    sys.path.append(minescript_root)

from FlameClient.config import SETTINGS, COLORS

# --- THEME SETUP ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ConsoleRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", text)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass

class BaseWindow(ctk.CTkToplevel):
    def __init__(self, parent, title, geometry):
        super().__init__(parent)
        self.title(title)
        self.geometry(geometry)
        self.attributes('-alpha', SETTINGS.get("MENU_OPACITY", 0.9))
        self.attributes('-topmost', True)
        self.protocol("WM_DELETE_WINDOW", self.withdraw) # Don't destroy, just hide
        self.refresh_callbacks = []
        
    def add_collapsible_section(self, parent, title):
        # Container for the whole section
        section_frame = ctk.CTkFrame(parent, fg_color="transparent")
        section_frame.pack(fill="x", pady=2)
        
        # Toggle Button
        is_expanded = tk.BooleanVar(value=False)
        
        content_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        
        def toggle():
            if is_expanded.get():
                content_frame.pack_forget()
                is_expanded.set(False)
                btn.configure(text=f"▶ {title}")
            else:
                content_frame.pack(fill="x", padx=10, pady=5)
                is_expanded.set(True)
                btn.configure(text=f"▼ {title}")

        btn = ctk.CTkButton(section_frame, text=f"▶ {title}", 
                            font=("Nunito", 14, "bold"), 
                            fg_color="transparent", 
                            text_color="#55FFFF",
                            hover_color="#333333",
                            anchor="w",
                            command=toggle)
        btn.pack(fill="x")
        
        return content_frame

    def add_switch(self, parent, text, setting_key):
        switch = ctk.CTkSwitch(parent, text=text, font=("Nunito", 12), command=lambda: self.master.update_setting(setting_key, switch.get()))
        if SETTINGS.get(setting_key):
            switch.select()
        switch.pack(pady=2, anchor="w")
        return switch

    def add_button(self, parent, text_func, command, color=None):
        btn = ctk.CTkButton(parent, text=text_func(), font=("Nunito", 12), height=28, command=None)
        
        def cmd_wrapper():
            command()
            self.master.refresh_all_ui()
        
        btn.configure(command=cmd_wrapper)
        if color:
            btn.configure(fg_color=color, hover_color="#444444")
        
        btn.pack(pady=3, fill="x")
        
        # Register for refresh
        self.refresh_callbacks.append(lambda: btn.configure(text=text_func()))
        return btn

    def add_slider(self, parent, text, setting_key, from_, to_, steps=None, is_int=False, warning_text=None, warning_color="#FF4444"):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(pady=5, fill="x")
        
        current_val = SETTINGS.get(setting_key, from_)
        label = ctk.CTkLabel(frame, text=f"{text}: {current_val}", font=("Nunito", 12))
        label.pack(anchor="w")
        
        if warning_text:
            lbl_warn = ctk.CTkLabel(frame, text=warning_text, text_color=warning_color, font=("Nunito", 10))
            lbl_warn.pack(anchor="w", padx=0, pady=(0, 2))

        def on_value(value):
            if is_int:
                value = int(value)
            else:
                value = round(value, 2)
            
            SETTINGS[setting_key] = value
            label.configure(text=f"{text}: {value}")
            
            # Auto-save config on slider change (Debounced)
            self.master.schedule_save()
            
            # Special case for opacity
            if setting_key == "MENU_OPACITY":
                self.master.update_opacity(value)
            
            # Special case for alpha colors
            if setting_key == "TEXT_ALPHA":
                 self.master.update_alpha_hex("TEXT_COLOR", value)
            if setting_key == "BOX_ALPHA":
                 self.master.update_alpha_hex("BOX_COLOR", value)

        slider = ctk.CTkSlider(frame, from_=from_, to=to_, number_of_steps=steps, command=on_value)
        slider.set(current_val)
        slider.pack(fill="x")
        
        return slider
        
    def refresh_ui(self):
        for cb in self.refresh_callbacks:
            cb()

class SettingsApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw() # Hide the root window
        self.title("Flame Client Manager")
        
        self.save_timer = None
        
        # Create Windows
        self.combat_window = BaseWindow(self, "Combat", "300x600")
        self.utility_window = BaseWindow(self, "Utility", "300x600")
        self.console_window = BaseWindow(self, "Console", "400x600")
        
        self.windows = [self.combat_window, self.utility_window, self.console_window]
        
        # Setup Content
        self.setup_combat()
        self.setup_utility()
        self.setup_console()
        
        # Position Windows
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        self.combat_window.geometry(f"+{screen_width//2 - 460}+{screen_height//2 - 300}")
        self.utility_window.geometry(f"+{screen_width//2 - 150}+{screen_height//2 - 300}")
        self.console_window.geometry(f"+{screen_width//2 + 160}+{screen_height//2 - 300}")

        # Input State
        self.was_rshift_down = False
        self.menu_visible = True
        self.last_read_state = None

        # Start Polling
        self.check_visibility()
        self.check_input()

    def check_input(self):
        try:
            # VK_RSHIFT = 0xA1
            is_rshift = (ctypes.windll.user32.GetAsyncKeyState(0xA1) & 0x8000) != 0
            
            if is_rshift and not self.was_rshift_down:
                self.toggle_menu()
            
            self.was_rshift_down = is_rshift
        except Exception as e:
            print(f"Input Error: {e}")
            
        self.after(50, self.check_input)

    def toggle_menu(self):
        self.menu_visible = not self.menu_visible
        state_str = "OPEN" if self.menu_visible else "CLOSED"
        
        try:
            state_file = os.path.join(current_dir, "menu_state.txt")
            with open(state_file, "w") as f:
                f.write(state_str)
            print(f"Menu Toggled: {state_str}")
        except Exception as e:
            print(f"Error writing state: {e}")

    def setup_combat(self):
        # ESP
        content_esp = self.combat_window.add_collapsible_section(self.combat_window, "ESP")
        self.setup_esp_section(content_esp, self.combat_window)
        
        # Sword Bot
        content_sword = self.combat_window.add_collapsible_section(self.combat_window, "SWORD BOT")
        self.setup_swordbot_section(content_sword, self.combat_window)

        # Triggerbot
        content_trigger = self.combat_window.add_collapsible_section(self.combat_window, "TRIGGERBOT")
        self.setup_triggerbot_section(content_trigger, self.combat_window)

        # Auto Anchor
        content_anchor = self.combat_window.add_collapsible_section(self.combat_window, "AUTO ANCHOR")
        self.setup_anchor_section(content_anchor, self.combat_window)

        # Auto Crystal
        content_crystal = self.combat_window.add_collapsible_section(self.combat_window, "AUTO CRYSTAL")
        self.setup_crystal_section(content_crystal, self.combat_window)

    def setup_utility(self):
        # Bridge
        content_bridge = self.utility_window.add_collapsible_section(self.utility_window, "AUTO SPEED BRIDGE")
        self.setup_bridge_section(content_bridge, self.utility_window)

        # God Bridge
        content_god = self.utility_window.add_collapsible_section(self.utility_window, "BREEZILY BRIDGE")
        self.setup_godbridge_section(content_god, self.utility_window)

        # Menu Settings
        content_menu = self.utility_window.add_collapsible_section(self.utility_window, "MENU SETTINGS")
        self.setup_menu_section(content_menu, self.utility_window)

    def setup_console(self):
        self.console_textbox = ctk.CTkTextbox(self.console_window, font=("Consolas", 12))
        self.console_textbox.pack(expand=True, fill="both", padx=5, pady=5)
        self.console_textbox.configure(state="disabled")
        
        sys.stdout = ConsoleRedirector(self.console_textbox)
        print("Flame Client Console Initialized...")
        
        btn_jobs = ctk.CTkButton(self.console_window, text="Reload Minescript Jobs", command=self.reload_jobs, height=40, font=("Nunito", 14, "bold"), fg_color="#2CC985", hover_color="#229E68")
        btn_jobs.pack(fill="x", padx=10, pady=10)

        btn_reload = ctk.CTkButton(self.console_window, text="Reload Config", command=self.reload_config, height=40, font=("Nunito", 14, "bold"), fg_color="#FFA500", hover_color="#CC8400")
        btn_reload.pack(fill="x", padx=10, pady=(0, 10))

        btn_exit = ctk.CTkButton(self.console_window, text="Exit Client", command=self.exit_app, height=40, font=("Nunito", 14, "bold"), fg_color="#FF4444", hover_color="#CC0000")
        btn_exit.pack(fill="x", padx=10, pady=(0, 10))
        
        self.last_log_size = 0
        self.check_log_updates()

    def check_log_updates(self):
        try:
            log_path = os.path.join(current_dir, "latest.log")
            if os.path.exists(log_path):
                current_size = os.path.getsize(log_path)
                if current_size > self.last_log_size:
                    with open(log_path, "r") as f:
                        f.seek(self.last_log_size)
                        new_content = f.read()
                        self.last_log_size = current_size
                        
                        self.console_textbox.configure(state="normal")
                        self.console_textbox.insert("end", new_content)
                        self.console_textbox.see("end")
                        self.console_textbox.configure(state="disabled")
                elif current_size < self.last_log_size:
                     # File was truncated/reset
                     self.last_log_size = 0
        except Exception as e:
            print(f"Log Error: {e}")
            
        self.after(500, self.check_log_updates)

    def check_visibility(self):
        try:
            state_file = os.path.join(current_dir, "menu_state.txt")
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    state = f.read().strip()
                
                if state != self.last_read_state:
                    self.last_read_state = state
                    if state == "OPEN":
                        for win in self.windows:
                            win.deiconify()
                    else:
                        for win in self.windows:
                            win.withdraw()
        except Exception as e:
            print(f"Error checking visibility: {e}")
            
        self.after(200, self.check_visibility)

    def update_opacity(self, value):
        for win in self.windows:
            win.attributes('-alpha', value)

    def refresh_all_ui(self):
        for win in self.windows:
            win.refresh_ui()

    # --- SECTIONS ---

    def setup_esp_section(self, parent, window):
        window.add_switch(parent, "Enabled", "ESP_ENABLED")
        window.add_switch(parent, "Boxes", "SHOW_BOX")
        window.add_switch(parent, "Health", "SHOW_HEALTH")
        window.add_switch(parent, "Nametags", "SHOW_NAME")
        window.add_switch(parent, "Item", "SHOW_WEAPON")
        
        window.add_slider(parent, "Text Scale", "TEXT_SCALE", 0.1, 3.0, steps=29)
        window.add_slider(parent, "Min Dist", "MIN_DISTANCE_NAME", 0, 100, steps=100, is_int=True)
        
        window.add_button(parent, lambda: f"Text Color", lambda: self.update_color("TEXT_COLOR"), color="#333333")
        window.add_slider(parent, "Text Alpha", "TEXT_ALPHA", 0, 100, steps=100, is_int=True)
        
        window.add_button(parent, lambda: "Box Color", lambda: self.update_color("BOX_COLOR"), color="#333333")
        window.add_slider(parent, "Box Alpha", "BOX_ALPHA", 0, 100, steps=100, is_int=True)

    def setup_swordbot_section(self, parent, window):
        window.add_switch(parent, "Enabled", "SWORDBOT_ENABLED")
        window.add_switch(parent, "Axe Mode", "SWORDBOT_AXE_MODE")
        window.add_slider(parent, "Intensity", "SWORDBOT_INTENSITY", 0.1, 5.0, steps=49, warning_text="Warning: High risk of getting flagged")
        
        window.add_slider(parent, "Min Dist", "SWORDBOT_MIN_DIST", 0.0, 5.0, steps=50)
        window.add_slider(parent, "Randomness", "SWORDBOT_RANDOMNESS", 0.0, 30.0, steps=300, warning_text="How much the aim can deviate", warning_color="#AAAAAA")
        
        window.add_button(parent, lambda: self.get_key_text("SWORDBOT_KEY", "Sword Key"), lambda: self.update_keybind("SWORDBOT_KEY"))
        window.add_button(parent, lambda: self.get_key_text("STRAFE_KEY", "Strafe Key"), lambda: self.update_keybind("STRAFE_KEY"))

    def setup_triggerbot_section(self, parent, window):
        window.add_switch(parent, "Enabled", "TRIGGERBOT_ENABLED")
        window.add_button(parent, lambda: self.get_key_text("TRIGGERBOT_KEY", "Trigger Key"), lambda: self.update_keybind("TRIGGERBOT_KEY"))

    def setup_bridge_section(self, parent, window):
        window.add_switch(parent, "Enabled", "BRIDGE_ENABLED")
        window.add_button(parent, lambda: self.get_key_text("BRIDGE_KEY", "Bridge Key"), lambda: self.update_keybind("BRIDGE_KEY"))

    def setup_godbridge_section(self, parent, window):
        window.add_switch(parent, "Enabled", "GODBRIDGE_ENABLED")
        window.add_button(parent, lambda: self.get_key_text("GODBRIDGE_KEY", "Breezily Key"), lambda: self.update_keybind("GODBRIDGE_KEY"))

    def setup_anchor_section(self, parent, window):
        window.add_switch(parent, "Enabled", "ANCHOR_ENABLED")
        window.add_button(parent, lambda: self.get_key_text("ANCHOR_KEY", "Anchor Key"), lambda: self.update_keybind("ANCHOR_KEY"))

    def setup_crystal_section(self, parent, window):
        window.add_switch(parent, "Enabled", "CRYSTAL_ENABLED")
        window.add_button(parent, lambda: self.get_key_text("CRYSTAL_KEY", "Crystal Key"), lambda: self.update_keybind("CRYSTAL_KEY"))

    def setup_menu_section(self, parent, window):
        window.add_slider(parent, "Menu Opacity", "MENU_OPACITY", 0.2, 1.0, steps=80)

    # --- LOGIC ---

    def update_setting(self, key, value):
        SETTINGS[key] = value
        print(f"Set {key} to {value}")
        self.save_config()

    def get_key_text(self, key, label):
        code = SETTINGS.get(key)
        return f"{label}: {code if code else 'None'}"

    def update_keybind(self, key_setting):
        top = ctk.CTkToplevel(self)
        top.geometry("300x150")
        top.title("Bind Key")
        
        # Ensure it stays on top of the main window
        top.transient(self)
        top.attributes('-topmost', True)
        top.lift()
        top.grab_set()
        
        # Center on screen
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 75
        top.geometry(f"+{x}+{y}")
        
        lbl = ctk.CTkLabel(top, text=f"Press any key for {key_setting}...\nPress ESC to unbind.", font=("Nunito", 14))
        lbl.pack(expand=True)
        
        def on_key(event):
            if event.keysym == "Escape":
                SETTINGS[key_setting] = None
                print(f"Unbound {key_setting}")
            else:
                SETTINGS[key_setting] = event.keycode
                print(f"Bound {key_setting} to {event.keycode}")
            self.save_config()
            top.grab_release()
            top.destroy()
            self.refresh_all_ui()
            
        top.bind("<Key>", on_key)
        top.focus_force()

    def update_color(self, key):
        dialog = ctk.CTkInputDialog(text="Enter Hex Color (#RRGGBB):", title=key)
        val = dialog.get_input()
        if val and val.startswith("#"):
            # Preserve alpha if exists
            current = COLORS.get(key, "#FFFFFFFF")
            if len(current) == 9: # #AARRGGBB
                alpha = current[1:3]
                if len(val) == 7:
                    val = f"#{alpha}{val[1:]}"
            COLORS[key] = val
            print(f"Set {key} to {val}")
            self.save_config()

    def update_alpha_hex(self, color_key, alpha_val):
        alpha_int = int((alpha_val / 100.0) * 255)
        alpha_hex = f"{alpha_int:02X}"
        
        current = COLORS.get(color_key, "#FFFFFF")
        if current.startswith("#"):
            clean = current[1:]
            if len(clean) == 8: rgb = clean[2:]
            else: rgb = clean
            COLORS[color_key] = f"#{alpha_hex}{rgb}"
        self.save_config()

    def reload_config(self):
        try:
            config_path = os.path.join(current_dir, "config.py")
            with open(config_path, "r") as f:
                code = f.read()
            
            temp_scope = {}
            exec(code, temp_scope)
            
            if "SETTINGS" in temp_scope:
                SETTINGS.clear()
                SETTINGS.update(temp_scope["SETTINGS"])
            
            if "COLORS" in temp_scope:
                COLORS.clear()
                COLORS.update(temp_scope["COLORS"])
                
            print("Config reloaded from disk!")
            self.refresh_all_ui()
        except Exception as e:
            print(f"Error reloading config: {e}")

    def reload_jobs(self):
        print("Attempting to reload Minescript jobs...")
        try:
            # PowerShell script to focus Minecraft and type commands
            ps_script = """
            $wshell = New-Object -ComObject wscript.shell;
            $wshell.AppActivate('Minecraft');
            Start-Sleep -Milliseconds 100;
            $wshell.SendKeys('{ENTER}');
            Start-Sleep -Milliseconds 50;
            $wshell.SendKeys('\\killjob -1~');
            Start-Sleep -Milliseconds 100;
            $wshell.SendKeys('{ENTER}');
            Start-Sleep -Milliseconds 50;
            $wshell.SendKeys('\\FlameClient\\watcher~');
            """
            subprocess.Popen(["powershell", "-Command", ps_script])
            print("Sent reload commands to Minecraft.")
        except Exception as e:
            print(f"Error sending commands: {e}")

    def exit_app(self):
        print("Exiting Flame Client Manager...")
        try:
            # PowerShell script to focus Minecraft and kill jobs
            ps_script = """
            $wshell = New-Object -ComObject wscript.shell;
            $wshell.AppActivate('Minecraft');
            Start-Sleep -Milliseconds 100;
            $wshell.SendKeys('{ENTER}');
            Start-Sleep -Milliseconds 50;
            $wshell.SendKeys('\\killjob -1~');
            """
            subprocess.Popen(["powershell", "-Command", ps_script])
            print("Sent killjob command to Minecraft.")
        except Exception as e:
            print(f"Error sending kill command: {e}")

        self.quit()
        sys.exit()

    def schedule_save(self):
        if self.save_timer:
            self.after_cancel(self.save_timer)
        self.save_timer = self.after(1000, self.save_config)

    def save_config(self):
        self.save_timer = None
        config_path = os.path.join(current_dir, "config.py")
        with open(config_path, "w") as f:
            f.write("# ==========================================\n")
            f.write("#           FLAME CLIENT CONFIGURATION\n")
            f.write("# ==========================================\n\n")
            f.write("COLORS = " + pprint.pformat(COLORS, indent=4) + "\n\n")
            f.write("SETTINGS = " + pprint.pformat(SETTINGS, indent=4) + "\n")
        print("Config saved!")

if __name__ == "__main__":
    app = SettingsApp()
    app.mainloop()
