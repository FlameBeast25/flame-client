from FlameClient.ESP.imports import *;
from FlameClient.config import COLORS, SETTINGS;

def parse_color(hex_str):
    if not isinstance(hex_str, str): return hex_str
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 8:
        a = int(hex_str[0:2], 16)
        r = int(hex_str[2:4], 16)
        g = int(hex_str[4:6], 16)
        b = int(hex_str[6:8], 16)
    elif len(hex_str) == 6:
        a = 255
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
    else:
        return 0xFFFFFFFF
    return argb.color(a, r, g, b)

def update_colors():
    for key in COLORS:
        COLORS[key] = parse_color(COLORS[key])

# Initial load
update_colors()

FLAGS = style.EMPTY.withShadowColor(0xFFFFFF);

MINECRAFT = minecraft_class.getInstance();
WINDOW = MINECRAFT.getWindow();

GAME_RENDERER = MINECRAFT.gameRenderer;
LEVEL = MINECRAFT.level;

OPTIONS = MINECRAFT.options;
FONT = MINECRAFT.font;

# Access protected field for font manager if needed (kept from original)
try:
    FONT_MANAGER = MINECRAFT.getClass().getDeclaredField("field_1708");
    FONT_MANAGER.setAccessible(True);
except:
    pass # Might fail on different mappings/versions

import FlameClient.ESP.drawing as DRAWING;
import FlameClient.ESP.math as MATH;

class EVENT_MANAGER_CLASS:
    def __init__(self):
        self.events = { };
        
    def register(self, name, callback):
        self.events[name] = callback;

EVENT_MANAGER = EVENT_MANAGER_CLASS();

def HUD_RENDER(draw_context, _):
    for name, callback in EVENT_MANAGER.events.items():
        callback(draw_context);

# Register the HUD render callback
hud_render_callback.EVENT.register(hud_render_callback(ManagedCallback(HUD_RENDER)));
