from FlameClient.ESP.globals import *;

def get_fov(player): # semi accurate, mc's getfov method is protected/priv so you cant access it w/o java reflection (which i dont wanna use)
    base_value = OPTIONS.fov().get().intValue();

    return base_value + (player.getFieldOfViewModifier(True, j_float(base_value)));

def world_to_screen(game_renderer, destination):
    p2s = game_renderer.projectPointToScreen(destination); # NDC
    
    if (p2s.z >= 1.0): # off screen
        return;

    # NDC --> PIXELS
    x = (j_float(p2s.x) + 1.0) * 0.5 * WINDOW.getGuiScaledWidth();
    y = ((1.0 - j_float(p2s.y))) * 0.5 * WINDOW.getGuiScaledHeight();

    return vector2(j_float(int(x)), j_float(int(y)));

def get_screen_scale(origin, destination, width, height, player):
    distance = origin.distanceTo(destination);

    if (distance < 1.0): 
        distance = 1.0;

    scale = 1.0 / j_math.tan(get_fov(player) / 57.295779513 / 2.0); 
    return vector2(j_float(int(((width * 360.0) / distance) * scale)), j_float(int(((height * 300.0) / distance) * scale)));
