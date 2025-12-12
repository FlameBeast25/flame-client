import minescript
import time
import threading
import ctypes
import math
import json
import os
from FlameClient.config import SETTINGS

# Import feature logic
# We can import them as modules if they are in the path, or just implement logic here.
# Since we want to keep it simple, let's implement the loops here or import classes.
# But `aimbot.py` etc are currently scripts. Let's make them modules.
# Actually, let's just copy the logic into classes here for cleaner integration.

import random

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "latest.log")

def log(message):
    prefix = [
        {"text": "F", "color": "#FF8600", "bold": True},
        {"text": "l", "color": "#FD791A", "bold": True},
        {"text": "a", "color": "#FA6B33", "bold": True},
        {"text": "m", "color": "#F85E4D", "bold": True},
        {"text": "e", "color": "#F65066", "bold": True},
        {"text": "C", "color": "#F34380", "bold": True},
        {"text": "l", "color": "#F13599", "bold": True},
        {"text": "i", "color": "#EF28B3", "bold": True},
        {"text": "e", "color": "#EC1ACC", "bold": True},
        {"text": "n", "color": "#EA0DE6", "bold": True},
        {"text": "t", "color": "#E700FF", "bold": True},
        {"text": " ", "color": "white", "bold": False}
    ]
    full_msg = [""] + prefix + [{"text": str(message), "color": "white"}]
    minescript.echo_json(json.dumps(full_msg))
    
    try:
        with open(LOG_FILE, "a") as f:
            timestamp = time.strftime("%H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except: pass

# ==========================================
#           FEATURE LOGIC
# ==========================================

CURRENT_SCREEN = None

def is_active_window_minecraft():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
    return "Minecraft" in buff.value

def is_key_held(vk):
    if not vk: return False
    if not is_active_window_minecraft():
        return False
    
    # Disable keybinds in any GUI (Chat, Inventory, etc.)
    if CURRENT_SCREEN is not None:
        return False

    return (ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000) != 0

def find_hotbar_slot(item_name):
    """Find an item in the hotbar (slots 0-8) and return its slot number."""
    try:
        inventory = minescript.player_inventory()
        for item in inventory:
            if item and item.slot is not None and item.slot < 9:  # Hotbar slots 0-8
                if item_name.lower() in item.item.lower():
                    return item.slot
    except: pass
    return None

def is_looking_at_block(keyword, reach=6.0):
    try:
        targeted_block = minescript.player_get_targeted_block(reach)
        if targeted_block and targeted_block.type:
            return keyword in targeted_block.type.lower()
    except: pass
    return False

def is_looking_at_entity(keyword, reach=6.0):
    try:
        targeted_entity = minescript.player_get_targeted_entity(reach)
        if targeted_entity and targeted_entity.type:
            return keyword in targeted_entity.type.lower()
    except: pass
    return False

class SwordBot:
    def __init__(self):
        self.active = False
        self.current_target_name = None
        self.last_run = 0
        self.was_key_down = False
        
        # Cooldown & Strafe State
        self.last_attack_time = 0
        self.resume_w_time = 0
        self.was_chasing = False
        
        # Strafe Toggle
        self.strafe_active = SETTINGS.get("STRAFE_ENABLED", True)
        self.was_strafe_key_down = False
        
        # Randomness State
        self.random_yaw_offset = 0
        self.random_pitch_offset = 0
        self.last_random_update = 0

    def run(self):
        if not SETTINGS.get("SWORDBOT_ENABLED", False): return
        
        # 1. SwordBot Toggle Check
        key = SETTINGS.get("SWORDBOT_KEY", 0xC0)
        is_down = is_key_held(key)
        
        if is_down and not self.was_key_down:
            self.active = not self.active
            log(f"§fSword Bot: {'§aON' if self.active else '§cOFF'}")
            if not self.active:
                self.current_target_name = None
                self.stop_movement()
        self.was_key_down = is_down

        # 2. Strafe Toggle Check
        strafe_key = SETTINGS.get("STRAFE_KEY", 74) # Default 'J'
        is_strafe_down = is_key_held(strafe_key)
        
        if is_strafe_down and not self.was_strafe_key_down:
            self.strafe_active = not self.strafe_active
            SETTINGS["STRAFE_ENABLED"] = self.strafe_active # Update runtime setting
            log(f"§fStrafing: {'§aON' if self.strafe_active else '§cOFF'}")
        self.was_strafe_key_down = is_strafe_down

        if not self.active: return

        # Safety: Stop if in menu
        if CURRENT_SCREEN is not None:
            if self.was_chasing:
                self.stop_movement()
                self.was_chasing = False
            return

        # Logic
        try:
            target = self.get_target()
            if target:
                self.aim_at(target)
            else:
                if self.was_chasing:
                    self.stop_movement()
                    self.was_chasing = False
        except Exception as e:
            pass

    def stop_movement(self):
        minescript.player_press_forward(False)
        minescript.player_press_left(False)
        minescript.player_press_right(False)
        minescript.player_press_attack(False)

    def get_target(self):
        # 1. Try to maintain lock
        if self.current_target_name:
            try:
                candidates = minescript.players(max_distance=SETTINGS["KEEP_TARGET_DISTANCE"])
                target = next((p for p in candidates if p.name == self.current_target_name), None)
                if target: return target
            except: pass
            self.current_target_name = None

        # 2. Find new target
        try:
            min_dist = SETTINGS.get("SWORDBOT_MIN_DIST", 1.0)
            # Increased limit to 2 to avoid only picking local player
            # Increased max_distance to 6 for better acquisition
            enemies = minescript.players(sort='nearest', limit=2, min_distance=min_dist, max_distance=8)
            if enemies:
                valid = [e for e in enemies if not e.local]
                if valid:
                    self.current_target_name = valid[0].name
                    log(f"§fTargeting: §c{self.current_target_name}")
                    return valid[0]
        except: pass
        return None

    def aim_at(self, target):
        pos = target.position
        my_pos = minescript.player_position()
        
        # Distance check
        dist = math.sqrt((pos[0] - my_pos[0])**2 + 
                         (pos[1] - my_pos[1])**2 + 
                         (pos[2] - my_pos[2])**2)
        
        min_dist = SETTINGS.get("SWORDBOT_MIN_DIST", 1.0)
        if dist < min_dist:
            self.stop_movement()
            return

        # Aim Logic with Intensity (Smoothing)
        intensity = SETTINGS.get("SWORDBOT_INTENSITY", 5.0)
        randomness = SETTINGS.get("SWORDBOT_RANDOMNESS", 0.0)
        
        # Random offsets are now updated after each hit (see below)

        if intensity >= 5.0:
            # Instant snap (with randomness)
            dx = pos[0] - my_pos[0]
            dy = (pos[1] + 1.6) - (my_pos[1] + 1.62)
            dz = pos[2] - my_pos[2]
            
            target_yaw = -math.degrees(math.atan2(dx, dz)) + self.random_yaw_offset
            horiz_dist = math.sqrt(dx**2 + dz**2)
            target_pitch = -math.degrees(math.atan2(dy, horiz_dist)) + self.random_pitch_offset
            
            minescript.player_set_orientation(target_yaw, target_pitch)
        else:
            # Smooth aim
            dx = pos[0] - my_pos[0]
            dy = (pos[1] + 1.6) - (my_pos[1] + 1.62) # Target Eye - My Eye
            dz = pos[2] - my_pos[2]
            
            # Calculate target angles
            target_yaw = -math.degrees(math.atan2(dx, dz)) + self.random_yaw_offset
            horiz_dist = math.sqrt(dx**2 + dz**2)
            target_pitch = -math.degrees(math.atan2(dy, horiz_dist)) + self.random_pitch_offset
            
            current_yaw, current_pitch = minescript.player_orientation()
            
            # Normalize yaw difference (-180 to 180)
            diff_yaw = (target_yaw - current_yaw + 180) % 360 - 180
            diff_pitch = target_pitch - current_pitch
            
            # Interpolate based on intensity (0.1 to 0.5 factor roughly)
            factor = intensity * 0.15
            if factor > 1.0: factor = 1.0
            
            new_yaw = current_yaw + diff_yaw * factor
            new_pitch = current_pitch + diff_pitch * factor
            
            minescript.player_set_orientation(new_yaw, new_pitch)
        
        # Auto Attack & Movement Logic
        if dist <= 3.5:
            self.was_chasing = True
            
            # Handle W-Tap Pause
            if self.resume_w_time > 0:
                if time.time() >= self.resume_w_time:
                    # Pause finished, resume movement
                    minescript.player_press_forward(True)
                    self.resume_w_time = 0
                    
                    # Change strafe direction
                    if self.strafe_active:
                        strafe = random.choice(['left', 'right', 'stop'])
                        if strafe == 'left':
                            minescript.player_press_left(True)
                            minescript.player_press_right(False)
                        elif strafe == 'right':
                            minescript.player_press_left(False)
                            minescript.player_press_right(True)
                        else:
                            minescript.player_press_left(False)
                            minescript.player_press_right(False)
                else:
                    # Still pausing
                    pass
            else:
                # Not pausing - Chase or Attack
                if SETTINGS.get("SWORDBOT_AXE_MODE", False):
                    SWORD_COOLDOWN = 1.0 # Axe Attack Speed
                else:
                    SWORD_COOLDOWN = 0.63 # Sword Attack Speed
                
                if time.time() - self.last_attack_time >= SWORD_COOLDOWN:
                    # Attack Sequence
                    minescript.player_press_forward(True) # Sprint Hit
                    minescript.player_press_attack(True)
                    minescript.player_press_attack(False)
                    minescript.player_press_forward(False) # Stop for W-Tap
                    
                    self.last_attack_time = time.time()
                    self.resume_w_time = time.time() + 0.15 # 150ms pause
                    
                    # Update Random Offsets (New Spot after hit)
                    randomness = SETTINGS.get("SWORDBOT_RANDOMNESS", 0.0)
                    if randomness > 0:
                        self.random_yaw_offset = random.uniform(-randomness, randomness)
                        self.random_pitch_offset = random.uniform(-randomness, randomness)
                    else:
                        self.random_yaw_offset = 0
                        self.random_pitch_offset = 0
                else:
                    # Just chase
                    minescript.player_press_forward(True)
        else:
            # Target out of attack range but locked on -> Chase
            minescript.player_press_forward(True)
            self.was_chasing = True


class Triggerbot:
    def __init__(self):
        self.active = False
        self.was_key_down = False
        self.last_attack_time = 0

    def run(self):
        if not SETTINGS.get("TRIGGERBOT_ENABLED", False): return
        
        # Toggle Logic
        key = SETTINGS.get("TRIGGERBOT_KEY", 82) # Default 'R'
        is_down = is_key_held(key)
        
        if is_down and not self.was_key_down:
            self.active = not self.active
            log(f"§fTriggerbot: {'§aON' if self.active else '§cOFF'}")
        self.was_key_down = is_down

        if not self.active: return

        if CURRENT_SCREEN is not None:
            return

        # Logic
        try:
            # Check if looking at entity
            targeted_entity = minescript.player_get_targeted_entity(3.0)
            if targeted_entity and targeted_entity.type:
                if "player" in targeted_entity.type.lower(): # Loose match
                    # Cooldown Check
                    SWORD_COOLDOWN = 0.02 # ~1.6 Attack Speed
                    if time.time() - self.last_attack_time >= SWORD_COOLDOWN:
                        minescript.player_press_attack(True)
                        time.sleep(0.05) # Hold for 50ms
                        minescript.player_press_attack(False)
                        self.last_attack_time = time.time()
        except: pass


class Bridge:
    def run(self):
        if not SETTINGS["BRIDGE_ENABLED"]: return
        
        key = SETTINGS.get("BRIDGE_KEY", 0x33)
        if is_key_held(key):
            pos = minescript.player_position()
            if not pos: return
            
            x, y, z = pos
            bx, by, bz = int(math.floor(x)), int(math.floor(y - 1)), int(math.floor(z))
            
            block = minescript.get_block(bx, by, bz)
            if "air" in block:
                minescript.player_press_sneak(True)
                minescript.player_press_use(True)
                minescript.player_press_use(False)
            else:
                minescript.player_press_sneak(False)


class BreezilyBridge:
    def __init__(self):
        self.was_active = False
        self.last_place_time = 0

    def run(self):
        if not SETTINGS.get("GODBRIDGE_ENABLED", False): return
        
        key = SETTINGS.get("GODBRIDGE_KEY", 0x47)
        if is_key_held(key):
            if not self.was_active:
                # 1. Snap Yaw to nearest 90 degrees (Cardinal for Witchly)
                yaw, pitch = minescript.player_orientation()
                snapped_yaw = round(yaw / 90) * 90
                
                # 2. Set Pitch
                minescript.player_set_orientation(snapped_yaw, 80)
            
            self.was_active = True
            
            # 3. Move Backward (S)
            minescript.player_press_forward(False)
            minescript.player_press_backward(True)
            
            # 4. Alternate A (Left) and D (Right)
            # Cycle: 0.4s total (0.2s Left, 0.2s Right) - Slower strafe for Breezily
            cycle = time.time() % 0.4
            if cycle < 0.2:
                minescript.player_press_left(True)
                minescript.player_press_right(False)
            else:
                minescript.player_press_left(False)
                minescript.player_press_right(True)
            
            # 5. Timed Place
            if time.time() - self.last_place_time >= 0.001:
                minescript.player_press_use(True)
                minescript.player_press_use(False)
                self.last_place_time = time.time()
        else:
            if self.was_active:
                minescript.player_press_backward(False)
                minescript.player_press_left(False)
                minescript.player_press_right(False)
                self.was_active = False


class AutoAnchor:
    def __init__(self):
        self.active = False
        self.was_key_down = False
        self.last_anchor_time = 0
        self.executing = False

    def run(self):
        if not SETTINGS["ANCHOR_ENABLED"]: return
        
        # Toggle Logic
        key = SETTINGS.get("ANCHOR_KEY", 90) # Default 'Z'
        is_down = is_key_held(key)
        
        if is_down and not self.was_key_down:
            self.active = not self.active
            log(f"§fAuto Anchor: {'§aON' if self.active else '§cOFF'}")
        self.was_key_down = is_down

        if not self.active: return

        # Logic
        if time.time() - self.last_anchor_time >= 0.5 and not self.executing:
            if is_looking_at_block("respawn_anchor"):
                self.executing = True
                log("§eAnchor detected! §fCharging...")
                threading.Thread(target=self.sequence).start()

    def sequence(self):
        try:
            glowstone_slot = find_hotbar_slot("glowstone")
            if glowstone_slot is not None:
                minescript.player_inventory_select_slot(glowstone_slot)
                time.sleep(0.05)
                
                # Save original camera
                yaw, pitch = minescript.player_orientation()
                
                # Charge 1
                minescript.player_press_use(True)
                time.sleep(0.02)
                minescript.player_press_use(False)
                time.sleep(0.05)
                
                # Move camera down
                minescript.player_set_orientation(yaw, pitch + 20)
                time.sleep(0.02)
                
                # Charge 2
                minescript.player_press_use(True)
                time.sleep(0.02)
                minescript.player_press_use(False)
                time.sleep(0.05)
                
                # Reset camera
                minescript.player_set_orientation(yaw, pitch) 
                time.sleep(0.05)
                
                # Explode
                sword_slot = find_hotbar_slot("sword")
                if sword_slot is not None:
                    minescript.player_inventory_select_slot(sword_slot)
                    time.sleep(0.3)
                    
                    minescript.player_press_use(True)
                    time.sleep(0.02)
                    minescript.player_press_use(False)
                    
                    log("§cBOOM! §fAnchor exploded.")
                    self.last_anchor_time = time.time()
        except Exception as e:
            print(f"Anchor Error: {e}")
        finally:
            self.executing = False

class AutoCrystal:
    def __init__(self):
        self.active = False
        self.was_key_down = False
        self.last_crystal_time = 0
        self.last_explode_time = 0
        self.executing = False

    def run(self):
        if not SETTINGS["CRYSTAL_ENABLED"]: return
        
        # Toggle Logic
        key = SETTINGS.get("CRYSTAL_KEY", 67) # Default 'C'
        is_down = is_key_held(key)
        
        if is_down and not self.was_key_down:
            self.active = not self.active
            log(f"§fAuto Crystal: {'§aON' if self.active else '§cOFF'}")
        self.was_key_down = is_down

        if not self.active: return

        # Logic
        if self.executing: return

        # Explode (High Priority)
        if is_looking_at_entity("end_crystal"):
            # Removed delay for instant reaction
            self.executing = True
            threading.Thread(target=self.explode_sequence).start()
        
        # Place (Low Priority)
        elif is_looking_at_block("obsidian"):
            self.executing = True
            threading.Thread(target=self.place_sequence).start()

    def place_sequence(self):
        try:
            crystal_slot = find_hotbar_slot("end_crystal")
            if crystal_slot is not None:
                minescript.player_inventory_select_slot(crystal_slot)
                
                minescript.player_press_use(True)
                minescript.player_press_use(False)
                
                log("§aPlaced Crystal")
                self.last_crystal_time = time.time()
        except: pass
        finally:
            self.executing = False

    def explode_sequence(self):
        try:
            sword_slot = find_hotbar_slot("sword")
            if sword_slot is not None:
                minescript.player_inventory_select_slot(sword_slot)
                
                minescript.player_press_attack(True)
                minescript.player_press_attack(False)
                
                log("§cExploded Crystal")
                self.last_explode_time = time.time()
        except: pass
        finally:
            self.executing = False


# ==========================================
#           MAIN LOOP
# ==========================================

def main():
    global SETTINGS
    log("§fCore Loaded!")
    
    # 1. Start ESP (Pyjinn Script)
    if SETTINGS["ESP_ENABLED"]:
        minescript.execute(r"\FlameClient\ESP\main")
        log("§fESP Started.")

    # 2. Initialize Features
    swordbot = SwordBot()
    triggerbot = Triggerbot()
    bridge = Bridge()
    breezily = BreezilyBridge()
    anchor = AutoAnchor()
    crystal = AutoCrystal()

    # Menu State
    menu_visible = True
    was_rshift_down = False
    menu_state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "menu_state.txt")
    
    # Initialize menu state file
    try:
        with open(menu_state_path, "w") as f:
            f.write("OPEN")
    except: pass

    log("§fFeatures Active.")

    # 3. Main Loop
    global CURRENT_SCREEN
    last_config_check = 0
    
    while True:
        try:
            # Reload Config every 1s
            if time.time() - last_config_check > 1.0:
                try:
                    import importlib
                    import FlameClient.config
                    importlib.reload(FlameClient.config)
                    from FlameClient.config import SETTINGS
                    last_config_check = time.time()
                except: pass

            CURRENT_SCREEN = minescript.screen_name()
            
            swordbot.run()
            triggerbot.run()
            bridge.run()
            breezily.run()
            anchor.run()
            crystal.run()
            
            time.sleep(0.01) # 100 ticks/sec roughly
        except Exception as e:
            log(f"§cError: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
