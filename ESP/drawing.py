import FlameClient.ESP.globals as main;

def text(draw_context, text_str, x, y, color):
    scale = main.SETTINGS.get("TEXT_SCALE", 1.0)
    
    if scale == 1.0:
        draw_context.drawString(main.FONT, text_str, int(x), int(y), color);
    else:
        pose = draw_context.pose()
        pose.pushMatrix()
        pose.scale(scale, scale)
        draw_context.drawString(main.FONT, text_str, int(x / scale), int(y / scale), color)
        pose.popMatrix()

def outline_text(draw_context, tstr, x, y, color):
    outline = main.COLORS.get("TEXT_OUTLINE_COLOR", "#B3000000"); # Use outline color from config
    offset = main.SETTINGS.get("OUTLINE_OFFSET", 1.0)

    text(draw_context, tstr, x - offset, y, outline);
    text(draw_context, tstr, x + offset, y, outline);
    text(draw_context, tstr, x, y - offset, outline);
    text(draw_context, tstr, x, y + offset, outline);
    
    text(draw_context, tstr, x, y, color);

def filled_rect(draw_context, start_x, start_y, end_x, end_y, color):    
    start_x, start_y = int(start_x), int(start_y);
    end_x, end_y = int(end_x), int(end_y);
    
    draw_context.fill(start_x, start_y, end_x, end_y, color);

def parse_color(color):
    if isinstance(color, str):
        if color.startswith("#"):
            color = color[1:]
        val = int(color, 16)
        if val > 0x7FFFFFFF:
            val -= 0x100000000
        return val
    return color

def filled_gradient(draw_context, start_x, start_y, end_x, end_y, upper, lower):
    start_x, start_y = int(start_x), int(start_y);
    end_x, end_y = int(end_x), int(end_y);

    upper = parse_color(upper)
    lower = parse_color(lower)

    # Force Java Integer to avoid Long inference
    upper = main.j_integer(int(upper))
    lower = main.j_integer(int(lower))

    draw_context.fillGradient(start_x, start_y, end_x, end_y, upper, lower);

def rect(draw_context, start_x, start_y, end_x, end_y, color):
    filled_rect(draw_context, start_x, start_y, end_x, start_y + 1, color);
    filled_rect(draw_context, start_x, end_y - 1, end_x, end_y, color);
    filled_rect(draw_context, start_x, start_y, start_x + 1, end_y, color);
    filled_rect(draw_context, end_x - 1, start_y, end_x, end_y, color);

def new(draw_type, *args):
    global callbacks;

    if (draw_type not in callbacks): 
        return; 

    return callbacks[draw_type](*args);

callbacks = {"outline_text": outline_text, "text": text, "filled_rect": filled_rect, "filled_gradient": filled_gradient, "rect": rect};
