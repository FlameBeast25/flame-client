from system.pyj.minescript import *;

# MC
resource_location = JavaClass("net.minecraft.resources.ResourceLocation");

style = JavaClass("net.minecraft.network.chat.Style");
component = JavaClass("net.minecraft.network.chat.Component");

minecraft_class = JavaClass("net.minecraft.client.Minecraft");
argb = JavaClass("net.minecraft.util.ARGB");

vector3 = JavaClass("net.minecraft.world.phys.Vec3");
vector2 = JavaClass("net.minecraft.world.phys.Vec2");

# JAVA
j_float = JavaClass("java.lang.Float");
j_integer = JavaClass("java.lang.Integer");
j_math = JavaClass("java.lang.Math");

# FABRIC
hud_render_callback = JavaClass("net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback");
