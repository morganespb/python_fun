import numpy as np
import pygame

# one breathing creature, drawn by a glsl shader.
# the shader runs off screen (moderngl), then the picture is copied into pygame.
# that way it works on macs too, where pygame only gets an old opengl.

SHADER = """
#version 330
uniform vec2 res;
uniform float time;
uniform vec2 look;
uniform float curl;
out vec4 color;

// smooth minimum: melts two shapes together
float smin(float a, float b, float k) {
    float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}

mat2 rot(float a) { return mat2(cos(a), -sin(a), sin(a), cos(a)); }

// distance from any point to the creature's skin
float creature(vec3 p) {
    float skin = 0.05 * sin(3.0 * p.x + time * 1.3) * sin(3.0 * p.y + time) * sin(3.0 * p.z - time * 0.7);
    float d = length(p) - (0.62 + 0.04 * sin(time * 1.4) + skin);
    float orbit = mix(0.95, 0.55, curl);
    for (int i = 0; i < 5; i++) {
        float f = float(i);
        vec3 c = vec3(sin(time * 0.5 + f * 1.26), cos(time * 0.37 + f * 2.1) * 0.5, cos(time * 0.5 + f * 1.26)) * orbit;
        d = smin(d, length(p - c) - 0.17, 0.38);
    }
    return d;
}

vec3 normal(vec3 p) {
    vec2 e = vec2(0.0015, 0.0);
    return normalize(vec3(creature(p + e.xyy) - creature(p - e.xyy),
                          creature(p + e.yxy) - creature(p - e.yxy),
                          creature(p + e.yyx) - creature(p - e.yyx)));
}

void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * res) / res.y;
    vec3 ro = vec3(0.0, 0.0, 3.6), rd = normalize(vec3(uv, -1.4));
    ro.yz *= rot(look.y); rd.yz *= rot(look.y);
    ro.xz *= rot(look.x); rd.xz *= rot(look.x);

    vec3 bg = vec3(0.04, 0.035, 0.03) * (1.2 - length(uv));
    vec3 col = bg;
    float t = 0.0;
    for (int i = 0; i < 96; i++) {           // walk along the ray by the distance to the skin
        vec3 p = ro + rd * t;
        float d = creature(p);
        if (d < 0.001) {
            vec3 n = normal(p);
            vec3 sun = normalize(vec3(-0.6, 0.7, 0.5));
            vec3 r = reflect(rd, n);
            float diffuse = max(dot(n, sun), 0.0);
            float shine = pow(max(dot(r, sun), 0.0), 40.0);          // silver highlight
            float edge = pow(1.0 - max(dot(n, -rd), 0.0), 2.0);       // light through thin edges
            float sky = 0.5 + 0.5 * r.y;                              // a soft fake reflection
            vec3 silver = vec3(0.81, 0.82, 0.83), brown = vec3(0.41, 0.30, 0.22);
            vec3 lit = brown * 0.08 + silver * (0.25 * diffuse * diffuse + 0.12 * sky * sky) + silver * shine
                     + brown * edge * 0.5;
            col = mix(pow(lit, vec3(0.4545)), bg, smoothstep(2.0, 4.5, t));
            break;
        }
        t += d * 0.9;
        if (t > 6.0) break;
    }
    color = vec4(col, 1.0);
}
"""

QUAD = """
#version 330
in vec2 pos;
void main() { gl_Position = vec4(pos, 0.0, 1.0); }
"""


def gl_context():
    import moderngl
    try:
        return moderngl.create_standalone_context(require=330)
    except Exception:
        return moderngl.create_standalone_context(backend="egl")    # linux without a screen


class Creature:
    title = "Creature"
    hint = "move the mouse to look around · hold the button and it curls up"
    glow = 0.3

    def __init__(self, size):
        self.w, self.h = size
        self.gl = gl_context()
        self.fbo = self.gl.simple_framebuffer(size)
        self.fbo.use()
        self.prog = self.gl.program(vertex_shader=QUAD, fragment_shader=SHADER)
        quad = self.gl.buffer(np.array([-1, -1, 3, -1, -1, 3], "f4"))
        self.vao = self.gl.vertex_array(self.prog, [(quad, "2f", "pos")])
        self.t, self.look, self.curl = 0, np.zeros(2), 0.0

    def update(self, dt, mouse):
        self.t += dt
        aim = np.array([(mouse.x / self.w - 0.5) * 3, (mouse.y / self.h - 0.5) * 1.2])
        self.look += (aim - self.look) * min(1, dt * 3)
        self.curl += (mouse.down - self.curl) * min(1, dt * 2)

    def draw(self, screen):
        self.prog["res"].value = (self.w, self.h)
        self.prog["time"].value = self.t
        self.prog["look"].value = tuple(self.look)
        self.prog["curl"].value = float(self.curl)
        self.vao.render()
        img = pygame.image.frombuffer(self.fbo.read(components=3), (self.w, self.h), "RGB")
        screen.blit(pygame.transform.flip(img, False, True), (0, 0))   # opengl is upside down

    def close(self):
        self.gl.release()
