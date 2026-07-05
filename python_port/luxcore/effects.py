"""Post-effets — shaders bildspur portés en GLSL 330 pour moderngl.

Portés 1:1 des fragments de linux-amd64/lib/shader/*.glsl (conventions Processing
`vertTexCoord`/`texture`/`gl_FragColor` -> `uv`/`tex`/`frag`). Appliqués en
ping-pong FBO plein écran. L'ordre du pipeline (do_effects puis blades puis
do_blade_blur) est géré par le renderer.

Paramètres (depuis les canaux DMX, cf. draw_functions.pde) :
  pixelate : amount = map(ch22,0,255,255,20)   si ch22 > 1
  sobel    : bistable                          si ch23 > 128
  rgbSplit : delta = ch24                       si ch24 > 1
  saturVib : saturation=ch25, vibrance=ch26     si l'un > 0.001
  chroma   : bistable                          si ch27 > 128
  blur     : blurSize=ch20, sigma=ch21 (2 passes) si l'un > 0.1  (après blades)
"""

# Vertex plein écran commun à tous les post-effets
FULLSCREEN_VERT = """
#version 330
in vec2 in_pos;
out vec2 uv;
void main() { uv = in_pos * 0.5 + 0.5; gl_Position = vec4(in_pos, 0.0, 1.0); }
"""

PIXELATE_FRAG = """
#version 330
in vec2 uv; out vec4 frag;
uniform sampler2D tex;
uniform vec2 resolution;
uniform float amount;
void main() {
    float d = 1.0 / amount;
    float ar = resolution.x / resolution.y;
    float u = floor(uv.x / d) * d;
    d = ar / amount;
    float v = floor(uv.y / d) * d;
    frag = texture(tex, vec2(u, v));
}
"""

SOBEL_FRAG = """
#version 330
in vec2 uv; out vec4 frag;
uniform sampler2D tex;
uniform vec2 resolution;
void main() {
    float x = 1.0 / resolution.x;
    float y = 1.0 / resolution.y;
    vec4 h = vec4(0.0);
    h -= texture(tex, vec2(uv.x - x, uv.y - y)) * 1.0;
    h -= texture(tex, vec2(uv.x - x, uv.y    )) * 2.0;
    h -= texture(tex, vec2(uv.x - x, uv.y + y)) * 1.0;
    h += texture(tex, vec2(uv.x + x, uv.y - y)) * 1.0;
    h += texture(tex, vec2(uv.x + x, uv.y    )) * 2.0;
    h += texture(tex, vec2(uv.x + x, uv.y + y)) * 1.0;
    vec4 v = vec4(0.0);
    v -= texture(tex, vec2(uv.x - x, uv.y - y)) * 1.0;
    v -= texture(tex, vec2(uv.x    , uv.y - y)) * 2.0;
    v -= texture(tex, vec2(uv.x + x, uv.y - y)) * 1.0;
    v += texture(tex, vec2(uv.x - x, uv.y + y)) * 1.0;
    v += texture(tex, vec2(uv.x    , uv.y + y)) * 2.0;
    v += texture(tex, vec2(uv.x + x, uv.y + y)) * 1.0;
    vec3 edge = sqrt((h.rgb * h.rgb) + (v.rgb * v.rgb));
    frag = vec4(edge, texture(tex, uv).a);
}
"""

RGBSPLIT_FRAG = """
#version 330
in vec2 uv; out vec4 frag;
uniform sampler2D tex;
uniform vec2 resolution;
uniform float delta;
void main() {
    vec2 dir = uv - vec2(0.5);
    float d = 0.7 * length(dir);
    vec2 value = d * dir * delta;
    vec4 c1 = texture(tex, uv - value / resolution.x);
    vec4 c2 = texture(tex, uv);
    vec4 c3 = texture(tex, uv + value / resolution.y);
    frag = vec4(c1.r, c2.g, c3.b, c1.a + c2.a + c3.b);
}
"""

SATURATION_FRAG = """
#version 330
in vec2 uv; out vec4 frag;
uniform sampler2D tex;
uniform float saturation;
uniform float vibrance;
void main() {
    vec4 col = texture(tex, uv);
    vec3 color = col.rgb;
    float luminance = color.r*0.299 + color.g*0.587 + color.b*0.114;
    float mn = min(min(color.r, color.g), color.b);
    float mx = max(max(color.r, color.g), color.b);
    float sat = (1.0-(mx - mn)) * (1.0-mx) * luminance * 5.0;
    vec3 lightness = vec3((mn + mx)/2.0);
    color = mix(color, mix(color, lightness, -vibrance), sat);
    color = mix(color, lightness, (1.0-lightness)*(1.0-vibrance)/2.0*abs(vibrance));
    color = mix(color, vec3(luminance), -saturation);
    frag = vec4(mix(col.rgb, color, col.a), col.a);
}
"""

CHROMATIC_FRAG = """
#version 330
out vec4 frag;
uniform sampler2D tex;
uniform vec2 resolution;
vec2 barrelDistortion(vec2 coord, float amt) {
    vec2 cc = coord - 0.5;
    float dist = dot(cc, cc);
    return coord + cc * dist * amt;
}
float sat(float t) { return clamp(t, 0.0, 1.0); }
float linterp(float t) { return sat(1.0 - abs(2.0*t - 1.0)); }
float remap(float t, float a, float b) { return sat((t - a) / (b - a)); }
vec4 spectrum_offset(float t) {
    vec4 ret;
    float lo = step(t, 0.5);
    float hi = 1.0 - lo;
    float w = linterp(remap(t, 1.0/6.0, 5.0/6.0));
    ret = vec4(lo, 1.0, hi, 1.0) * vec4(1.0-w, w, 1.0-w, 1.0);
    return pow(ret, vec4(1.0/2.2));
}
const float max_distort = 2.2;
const int num_iter = 12;
const float reci_num_iter_f = 1.0 / float(num_iter);
void main() {
    vec2 uv = (gl_FragCoord.xy / resolution.xy * 0.5) + 0.25;
    vec4 sumcol = vec4(0.0);
    vec4 sumw = vec4(0.0);
    for (int i = 0; i < num_iter; ++i) {
        float t = float(i) * reci_num_iter_f;
        vec4 w = spectrum_offset(t);
        sumw += w;
        sumcol += w * texture(tex, barrelDistortion(uv, 0.6 * max_distort * t));
    }
    frag = sumcol / sumw;
}
"""

# Blur gaussien incrémental, séparable (2 passes : horizontal puis vertical)
BLUR_FRAG = """
#version 330
in vec2 uv; out vec4 frag;
uniform sampler2D tex;
uniform vec2 texOffset;        // (1/w, 1/h)
uniform int blurSize;
uniform int horizontalPass;    // 1 = horizontal, 0 = vertical
uniform float sigma;
const float pi = 3.14159265;
void main() {
    float numBlurPixelsPerSide = float(blurSize / 2);
    vec2 blurMultiplyVec = 0 < horizontalPass ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec3 incrementalGaussian;
    incrementalGaussian.x = 1.0 / (sqrt(2.0 * pi) * sigma);
    incrementalGaussian.y = exp(-0.5 / (sigma * sigma));
    incrementalGaussian.z = incrementalGaussian.y * incrementalGaussian.y;
    vec4 avgValue = vec4(0.0);
    float coefficientSum = 0.0;
    avgValue += texture(tex, uv) * incrementalGaussian.x;
    coefficientSum += incrementalGaussian.x;
    incrementalGaussian.xy *= incrementalGaussian.yz;
    for (float i = 1.0; i <= numBlurPixelsPerSide; i++) {
        avgValue += texture(tex, uv - i * texOffset * blurMultiplyVec) * incrementalGaussian.x;
        avgValue += texture(tex, uv + i * texOffset * blurMultiplyVec) * incrementalGaussian.x;
        coefficientSum += 2.0 * incrementalGaussian.x;
        incrementalGaussian.xy *= incrementalGaussian.yz;
    }
    frag = avgValue / coefficientSum;
}
"""
