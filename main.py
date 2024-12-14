import tkinter as tk
from tkinter import ttk, font
import pymem
import pymem.process
import keyboard
import time
import logging
from pynput.mouse import Controller, Button
from win32gui import GetWindowText, GetForegroundWindow
from random import uniform
from requests import get
from threading import Thread

# Global mouse controller
mouse = Controller()

class TriggerBotApp(tk.Tk):
    # Constants
    WINDOW_SIZE = "800x600"
    BG_COLOR = "#2d2d2d"
    BUTTON_BG = "#444444"
    TEXT_COLOR = "#ffffff"
    DEFAULT_TOGGLE_KEY = "K"
    
    def __init__(self):
        super().__init__()
        self.setup_window()
        self.setup_styles()
        self.initialize_state()
        self.create_widgets()
        self.start_bot()

    def setup_window(self):
        """Initialize window properties"""
        self.title("TriggerBot")
        self.geometry(self.WINDOW_SIZE)
        self.configure(bg=self.BG_COLOR)
        
    def setup_styles(self):
        """Configure application styles and fonts"""
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        
        # Setup fonts
        self.title_font = font.Font(family="Helvetica", size=16, weight="bold")
        self.label_font = font.Font(family="Helvetica", size=12)
        self.button_font = font.Font(family="Helvetica", size=12)

        # Configure widget styles
        self._configure_widget_styles()

    def _configure_widget_styles(self):
        """Helper method to configure widget styles"""
        self.style.configure(
            "TButton",
            foreground=self.TEXT_COLOR,
            background=self.BUTTON_BG,
            padding=10,
            font=self.button_font,
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
        )
        self.style.configure(
            "TLabel",
            foreground=self.TEXT_COLOR,
            background=self.BG_COLOR,
            font=self.label_font,
        )

    def initialize_state(self):
        """Initialize application state"""
        self.toggle_active = False
        self.toggleKey = self.DEFAULT_TOGGLE_KEY
        keyboard.on_press_key(self.toggleKey, self.on_key_press)

    def start_bot(self):
        """Start the triggerbot in a separate thread"""
        self.bot_thread = Thread(target=self.run_triggerbot, daemon=True)
        self.bot_thread.start()

    def create_widgets(self):
        """Create and layout all UI widgets"""
        self._create_title()
        self._create_content_frame()
        self._create_status_widgets()
        self._create_control_buttons()
        self._create_language_buttons()

    def _create_title(self):
        """Create title label"""
        self.title_label = ttk.Label(
            self,
            text="TriggerBot",
            font=self.title_font,
            padding=10,
        )
        self.title_label.pack(pady=20)

    def _create_content_frame(self):
        """Create main content frame"""
        self.content_frame = ttk.Frame(self, padding=10)
        self.content_frame.pack(pady=10)

    def _create_status_widgets(self):
        """Create status related widgets"""
        self.status_label = ttk.Label(
            self.content_frame,
            text="TriggerBot is Off",
            font=self.label_font,
            padding=5,
        )
        self.status_label.grid(row=0, column=0, pady=5)

        self.toggle_label = ttk.Label(
            self.content_frame,
            text=f"Toggle Key: {self.toggleKey}",
            font=self.label_font,
            padding=5,
        )
        self.toggle_label.grid(row=3, column=0, pady=5)

    def _create_control_buttons(self):
        """Create On/Off control buttons"""
        self.on_button = ttk.Button(
            self.content_frame,
            text="On",
            command=self.turn_on,
            padding=5,
        )
        self.on_button.grid(row=1, column=0, pady=5)

        self.off_button = ttk.Button(
            self.content_frame,
            text="Off",
            command=self.turn_off,
            padding=5,
        )
        self.off_button.grid(row=2, column=0, pady=5)

    def _create_language_buttons(self):
        """Create language selection buttons"""
        self.language_frame = ttk.Frame(self.content_frame, padding=10)
        self.language_frame.grid(row=4, column=0, pady=10)

        languages = [
            ("PL", self.set_pl_language),
            ("ENG", self.set_eng_language),
            ("RU", self.set_ru_language)
        ]

        for idx, (text, command) in enumerate(languages):
            btn = ttk.Button(
                self.language_frame,
                text=text,
                command=command,
                padding=5,
            )
            btn.grid(row=0, column=idx, padx=5, pady=5)

    # Game-related methods
    def fetch_offsets(self):
        """Fetch game offsets from GitHub"""
        try:
            offset = get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json").json()
            client = get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client.dll.json").json()
            return offset, client
        except Exception as e:
            logging.error(f"Failed to fetch offsets: {e}")
            return None, None

    def initialize_pymem(self):
        """Initialize PyMem for game interaction"""
        try:
            return pymem.Pymem("cs2.exe")
        except pymem.exception.PymemError as e:
            logging.error(f"Cannot open cs2.exe: {e}")
            return None

    def get_client_module(self, pm):
        """Get client.dll module address"""
        client_module = pymem.process.module_from_name(pm.process_handle, "client.dll")
        if not client_module:
            logging.error("Cannot find client.dll module.")
            return None
        return client_module.lpBaseOfDll

    def get_entity(self, pm, base_address, index):
        """Get entity by index"""
        try:
            ent_list = pm.read_longlong(base_address + dwEntityList)
            ent_entry = pm.read_longlong(ent_list + 0x8 * (index >> 9) + 0x10)
            return pm.read_longlong(ent_entry + 120 * (index & 0x1FF))
        except Exception as e:
            logging.error(f"Entity read error: {e}")
            return None

    def is_game_active(self):
        """Check if CS2 window is active"""
        return GetWindowText(GetForegroundWindow()) == application_name

    def should_trigger(self, entity_team, player_team, entity_health):
        """Determine if trigger should activate"""
        return entity_team != player_team and entity_health > 0

    # UI control methods
    def turn_on(self):
        self.toggle_active = True
        self.status_label.config(text="TriggerBot is On")
        logging.info("TriggerBot turned on.")

    def turn_off(self):
        self.toggle_active = False
        self.status_label.config(text="TriggerBot is Off")
        logging.info("TriggerBot turned off.")

    def on_key_press(self, event):
        self.toggle_active = not self.toggle_active
        state = "On" if self.toggle_active else "Off"
        self.status_label.config(text=f"TriggerBot is {state}")
        logging.info(f"TriggerBot {state}.")

    def run_triggerbot(self):
        """Main triggerbot loop"""
        offsets, client_data = self.fetch_offsets()
        if offsets is None or client_data is None:
            return

        global dwEntityList, dwLocalPlayerPawn, m_iHealth, m_iTeamNum, m_iIDEntIndex
        # Initialize game offsets
        dwEntityList = offsets["client.dll"]["dwEntityList"]
        dwLocalPlayerPawn = offsets["client.dll"]["dwLocalPlayerPawn"]
        m_iHealth = client_data["client.dll"]["classes"]["C_BaseEntity"]["fields"]["m_iHealth"]
        m_iTeamNum = client_data["client.dll"]["classes"]["C_BaseEntity"]["fields"]["m_iTeamNum"]
        m_iIDEntIndex = client_data["client.dll"]["classes"]["C_CSPlayerPawnBase"]["fields"]["m_iIDEntIndex"]

        pm = self.initialize_pymem()
        if pm is None:
            return

        client_base = self.get_client_module(pm)
        if client_base is None:
            return

        last_shot_time = 0

        while True:
            try:
                if not self.is_game_active():
                    time.sleep(0.05)
                    continue

                if self.toggle_active:
                    self._process_triggerbot(pm, client_base, last_shot_time)
                    time.sleep(0.01)
                else:
                    time.sleep(0.05)
            except KeyboardInterrupt:
                logging.info("TriggerBot stopped by user.")
                break
            except Exception as e:
                logging.error(f"Unexpected error: {e}")

    def _process_triggerbot(self, pm, client_base, last_shot_time):
        """Process triggerbot logic"""
        player = pm.read_longlong(client_base + dwLocalPlayerPawn)
        entity_id = pm.read_int(player + m_iIDEntIndex)

        if entity_id > 0:
            entity = self.get_entity(pm, client_base, entity_id)
            if entity:
                entity_team = pm.read_int(entity + m_iTeamNum)
                player_team = pm.read_int(player + m_iTeamNum)
                entity_health = pm.read_int(entity + m_iHealth)

                if self.should_trigger(entity_team, player_team, entity_health):
                    current_time = time.time()
                    if current_time - last_shot_time >= 0.05:
                        self._perform_shot()
                        last_shot_time = current_time

    def _perform_shot(self):
        """Perform shooting action"""
        time.sleep(uniform(0.01, 0.02))
        mouse.press(Button.left)
        time.sleep(uniform(0.01, 0.03))
        mouse.release(Button.left)

    # Language methods
    def set_pl_language(self):
        self.on_button.config(text="Włącz")
        self.off_button.config(text="Wyłącz")
        self.status_label.config(text="TriggerBot jest wyłączony")
        self.toggle_label.config(text=f"Klawisz przełączania: {self.toggleKey}")
        logging.info("Changed language to Polish.")

    def set_eng_language(self):
        self.on_button.config(text="On")
        self.off_button.config(text="Off")
        self.status_label.config(text="TriggerBot is turned off")
        self.toggle_label.config(text=f"Toggle Key: {self.toggleKey}")
        logging.info("Changed language to English.")

    def set_ru_language(self):
        self.on_button.config(text="Включить")
        self.off_button.config(text="Выключить")
        self.status_label.config(text="ТриггерБот отключен")
        self.toggle_label.config(text=f"Клавиша переключения: {self.toggleKey}")
        logging.info("Changed language to Russian.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    application_name = "Counter-Strike 2"
    app = TriggerBotApp()
    app.mainloop()
