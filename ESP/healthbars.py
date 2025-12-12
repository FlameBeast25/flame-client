from FlameClient.ESP.globals import *

def get_health_color(health, max_health):
    ratio = health / max_health if max_health > 0 else 0
    if ratio > 1: ratio = 1
    if ratio < 0: ratio = 0
    
    # Simple Red to Green interpolation
    # Full Health (1.0) -> Green (0, 255, 0)
    # Low Health (0.0) -> Red (255, 0, 0)
    
    r = int((1.0 - ratio) * 255)
    g = int(ratio * 255)
    b = 0
    
    return argb.color(255, r, g, b)

def draw(draw_context, entity, left, top, right, bottom):
    if not SETTINGS["SHOW_HEALTH"]:
        return

    draw_func = DRAWING.new
    
    health, max_health = entity.getHealth(), entity.getMaxHealth()
    ratio = health / max_health if max_health > 0 else 0
    if ratio > 1: ratio = 1
    
    height = (ratio * (bottom - top))
    
    # Health Bar Dimensions
    start = left - 6
    end = left - 2
    
    bar_top = bottom - height
    
    # Get solid color
    color = get_health_color(health, max_health)
    
    # Draw Solid Bar
    draw_func("filled_rect", draw_context, start, bar_top, end, bottom, color)
