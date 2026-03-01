---
name: mercury-hydra
description: Compose Hydra visuals for Mercury Playground and attach them to instruments with visual(). Use when the user asks for visuals, animation, Hydra syntax, background graphics, or audio-reactive visual coding.
---

# Mercury Hydra -- Visual Coding for Mercury Playground

Use this skill for Hydra visuals only. Keep audio composition concerns in `mercury-compose`.

## Mercury + Hydra Syntax

Mercury attaches Hydra code strings to instruments via `visual()`. Store Hydra code as single-quoted strings inside a Mercury list. Multiple strings cycle on each trigger.

```
list vis ['osc(10,0.1,2).rotate(0.1).out()' 'noise(3).color(0.2,0.4,0.8).out()']
new sample kick_909 time(1/4) visual(vis)
```

For static background visuals, attach `visual()` to an instrument that triggers regularly (kick or hat is a good default).

Important parsing rule: keep Hydra strings single-quoted, use commas in Hydra arguments, and avoid single quotes inside the Hydra code.

## Hydra Architecture

Hydra compiles chained JavaScript calls into WebGL fragment shaders. Every function belongs to one of five GLSL types that determine what it receives and returns:

| Type | Category | Receives | Returns | Role |
|------|----------|----------|---------|------|
| `src` | Source | `vec2 _st` (UV coords) | `vec4` | Generate initial visual signal |
| `coord` | Geometry | `vec2 _st` | `vec2` | Transform coordinates |
| `color` | Color | `vec4 _c0` | `vec4` | Transform color values |
| `combine` | Blend | `vec4 _c0, vec4 _c1` | `vec4` | Combine two textures by color |
| `combineCoord` | Modulate | `vec2 _st, vec4 _c0` | `vec2` | Warp geometry using another texture |

Chain rule: every chain **must** start with a `src`-type function and end with `.out()`. Between them, add `coord`, `color`, `combine`, and `combineCoord` transforms in any order. The `combine` and `combineCoord` types take a texture as their first argument (another chain, output buffer, or external source).

## Hydra Function Reference

### Sources

```
osc(freq=60, sync=0.1, offset=0)           // vertical bands; offset 0=grayscale, nonzero=rainbow (0 to 2pi)
noise(scale=10, offset=0.1)                // Perlin noise; outputs negative values -- beware when modulating
voronoi(scale=5, speed=0.3, blending=0.3)  // cell diagram; blending 0=sharp edges, higher=soft
shape(sides=3, radius=0.3, smoothing=0.01) // polygon; high sides=circle, smoothing 0 may not render
gradient(speed=0)                           // UV-based gradient; R=x, G=y, B=sin(time*speed)
solid(r=0, g=0, b=0, a=1)                  // flat fill
src(texture)                                // read buffer (o0-o3) or external source (s0-s3)
prev()                                      // previous frame of current buffer (feedback)
```

### Geometry Transforms

```
.rotate(angle=10, speed=0)                          // radians; default 10 = ~1.6 full turns (intentional)
.scale(amount=1.5, xMult=1, yMult=1, offsetX=0.5, offsetY=0.5) // >1 zooms OUT, <1 zooms IN
.pixelate(pixelX=20, pixelY=20)                    // mosaic effect
.repeat(repeatX=3, repeatY=3, offsetX=0, offsetY=0) // tile grid
.repeatX(reps=3, offset=0)                         // tile horizontally
.repeatY(reps=3, offset=0)                         // tile vertically
.kaleid(nSides=4)                                   // kaleidoscope; 50+ = mandala
.scroll(scrollX=0.5, scrollY=0.5, speedX=0, speedY=0)
.scrollX(scrollX=0.5, speed=0)
.scrollY(scrollY=0.5, speed=0)
```

### Color Transforms

```
.color(r=1, g=1, b=1, a=1)             // multiply channels; color(1,0,0) = isolate red
.invert(amount=1)                      // 1=full invert, 0=none, fractional=partial
.brightness(amount=0.4)                // adds flat value to RGB
.contrast(amount=1.6)                  // >1 increases, <1 decreases
.saturate(amount=2)                    // 0=grayscale, 1=unchanged, >1=oversaturate
.hue(hue=0.4)                          // shift hue in HSV; 0-1 = full rotation
.luma(threshold=0.5, tolerance=0.1)    // alpha mask by brightness; use with .layer()
.thresh(threshold=0.5, tolerance=0.04) // hard black/white cutoff; tolerance must be >0
.posterize(bins=3, gamma=0.6)          // quantize to N color levels
.shift(r=0.5, g=0, b=0, a=0)          // shift channels with fract() wrapping
.colorama(amount=0.005)                // HSV color cycling; small=shimmer, large=psychedelic
.r(scale=1, offset=0)                  // extract red channel
.g(scale=1, offset=0)                  // extract green channel
.b(scale=1, offset=0)                  // extract blue channel
.a(scale=1, offset=0)                  // extract alpha channel
```

### Blend Transforms

All blend functions take a texture as first argument. `diff`, `layer`, and `mask` accept **no** extra numeric parameter.

```
.add(texture, amount=1)      // additive; negative amount subtracts
.sub(texture, amount=1)      // subtractive
.blend(texture, amount=0.5)  // linear mix; 0=base only, 1=texture only
.mult(texture, amount=1)     // multiply; dark areas in either = dark result
.diff(texture)               // abs difference; identical areas = black
.layer(texture)              // alpha composite; combine with .luma() for clean overlays
.mask(texture)               // luminance of texture controls base visibility
```

### Modulate Transforms

Modulation uses color values of a secondary texture to **displace coordinates** of the primary. Red channel drives X, green drives Y (for basic `modulate`). Each mirrors a geometry transform but applies it variably based on modulator brightness.

```
.modulate(texture, amount=0.1)                        // general displacement
.modulateScale(texture, multiple=1, offset=1)        // variable zoom
.modulateRotate(texture, multiple=1, offset=0)       // variable rotation
.modulatePixelate(texture, multiple=10, offset=3)    // variable pixelation
.modulateHue(texture, amount=1)                      // warp by channel differences (G-R for X, B-G for Y)
.modulateKaleid(texture, nSides=4)                   // variable kaleidoscope
.modulateRepeat(texture, repeatX=3, repeatY=3, offsetX=0.5, offsetY=0.5)
.modulateRepeatX(texture, reps=3, offset=0.5)
.modulateRepeatY(texture, reps=3, offset=0.5)
.modulateScrollX(texture, scrollX=0.5, speed=0)
.modulateScrollY(texture, scrollY=0.5, speed=0)
```

### Output and Multi-Buffer Workflows

4 output buffers (`o0`-`o3`) and 4 source buffers (`s0`-`s3`). Every chain ends with `.out(buffer)`.

```
.out(output=o0)   // render chain to buffer
render(output=o0) // show one buffer fullscreen
render()          // quad view: o0 top-left, o1 bottom-left, o2 top-right, o3 bottom-right
hush()            // clear all outputs (does not reset speed/bpm)
```

Cross-reference buffers with `src()` for layering, feedback, and complex routing:

```js
osc(10).out(o0)
noise(3).out(o1)
src(o0).modulate(src(o1), 0.1).out(o2)
render(o2)
```

Feedback loop pattern -- read back from the same buffer you write to:

```js
src(o0).rotate(0.01).scale(1.01).color(0.99,0.98,1).out(o0)
```

### Dynamic Values and Sequencing

Any numeric parameter accepts three input types:

**Static values:** plain numbers.

**Arrays** -- step-sequenced at `bpm` rate (default 30):

```js
osc([10, 20, 50, 100], 0.1, [0, 0.5, 1]).out()
```

Array methods:
- `.fast(mult)` -- speed multiplier relative to bpm; `.fast(4)` = 4x faster
- `.smooth(amount)` -- interpolate between steps instead of hard-switching
- `.ease(name)` -- easing curve for smooth; options: `'linear'`, `'easeInQuad'`, `'easeOutQuad'`, `'easeInOutQuad'`, `'easeInCubic'`, `'easeOutCubic'`, `'easeInOutCubic'`, `'easeInQuart'`, `'easeOutQuart'`, `'easeInOutQuart'`, `'easeInQuint'`, `'easeOutQuint'`, `'easeInOutQuint'`, `'sin'`
- `.offset(n)` -- timing offset (0-1)
- `.fit(min, max)` -- remap values into range

```js
osc([10, 30, 60].smooth().ease('easeInOutCubic').fast(2)).out()
```

Arrays of textures do **not** work as function arguments.

**Arrow functions** -- evaluated every frame:

```js
osc(() => 100 * Math.sin(time * 0.1)).out()
```

Key globals: `time` (seconds elapsed), `mouse.x` / `mouse.y` (pixels -- normalize with `window.innerWidth`/`innerHeight`), `speed` (time multiplier, default 1), `bpm` (array rate, default 30).

### Audio Reactivity

Hydra uses Meyda for real-time FFT of microphone input. All methods live on the global `a` object.

```js
a.show()              // display FFT overlay
a.hide()              // hide overlay
a.setBins(n)          // number of frequency bands (default 4)
a.setCutoff(n)        // noise gate threshold
a.setScale(n)         // loudness ceiling
a.setSmooth(n)        // 0 = jumpy, 1 = frozen
```

Use `a.fft[n]` (0-1 range) inside arrow functions for audio-driven parameters:

```js
osc(20, 0.1, () => a.fft[0] * 10)
  .rotate(() => a.fft[1])
  .kaleid()
  .out()
```

## Critical: Keep Hydra Strings Simple

Mercury can fail silently on complex Hydra strings (audio still plays but visuals disappear). Keep visuals robust with these rules:

1. Max 4-5 chained calls per string.
2. Avoid nesting source functions inside blend/modulate args.
3. Avoid arrow functions and heavy JS expressions inside single-quoted strings.
4. Prefer multiple simple list entries over one very complex chain.
5. If visuals fail, test with a minimal pattern first.

Simple test:
```
list test ['osc(10,0.1,2).out()']
new sample kick_house time(1/4) visual(test)
```

Good:
```
list vis ['osc(8,0.1,1).rotate(0,0.05).color(0.3,0.5,0.9).out()' 'noise(3).color(0.2,0.1,0.3).out()']
```

Too complex (avoid):
```
list vis ['noise(3,0.1).color(0.15,0.1,0.35).modulate(o0,0.12).rotate(0,0.015).blend(o0,0.88).saturate(1.3).contrast(1.1).out()']
```

## Visual Recipes by Mood

Each recipe keeps chains short. Use multiple entries for richness.

Dark / Mysterious:
```
'noise(3,0.1).color(0.1,0.05,0.2).contrast(1.3).out()'
'src(o0).scale(1.01).rotate(0,0.01).color(0.95,0.93,1).out()'
```

Warm / Sunrise:
```
'osc(6,0.08,1.5).color(1,0.6,0.2).rotate(0.1,0.05).out()'
'noise(2,0.1).color(1,0.8,0.3).brightness(0.1).out()'
```

Dreamy / Ethereal:
```
'voronoi(4,0.1,0.3).color(0.3,0.5,0.8).rotate(0,0.02).out()'
'osc(3,0.05,1).color(0.5,0.4,0.9).kaleid(3).out()'
```

Pulsing / Rhythmic:
```
'osc(20,0.1,0).kaleid(4).color(0.5,0.2,0.8).out()'
'osc(15,0.2,1).rotate(0,0.1).color(0.8,0.3,0.5).out()'
```

Minimal / Clean:
```
'shape(4,0.3,0.01).rotate(0,0.1).color(0.8,0.9,1).out()'
'shape(6,0.2,0.01).color(0.9,0.8,1).repeat(3,3).out()'
```

Feedback / Evolving:
```
'src(o0).scale(1.01).rotate(0,0.02).color(0.97,0.95,1.02).out()'
'osc(6,0,1).color(0.9,0.7,1).modulate(o0,0.08).out()'
```

Organic / Fluid:
```
'noise(3,0.1).color(0.4,0.7,0.5).rotate(0,0.05).out()'
'voronoi(5,0.2,0.5).color(0.3,0.6,0.4).scale(1.5).out()'
```

## Combined Usage Snippet

Use this minimal integration pattern when users want synced audio + visuals:

```
set tempo 90
list bg ['noise(3,0.1).color(0.2,0.3,0.6).rotate(0,0.02).out()' 'osc(4,0.05,1).color(0.3,0.2,0.5).kaleid(3).out()']
new synth saw note([0 -5] 0) time(1/1) shape(off) name(pad)
    set pad visual(bg)
new sample kick_deep time(1/4) gain(0.6)
```

## Additional Resources

For the complete 52-function API with detailed behavioral descriptions, external sources, mouse interactivity, custom GLSL, and global settings, see [hydra-reference.md](hydra-reference.md).
