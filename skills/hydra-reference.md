# Hydra Complete Function Reference

Full API reference for all 52 built-in GLSL functions, external sources, audio, mouse, globals, and custom GLSL. Verified against `glsl-functions.js` in the hydra-synth repository.

---

## Source Functions (type: `src`) -- 8 functions

### osc( frequency = 60, sync = 0.1, offset = 0 )

Vertical bands scrolling horizontally. `frequency` sets cycle count across screen. `sync` controls scroll speed (multiplied by both time and frequency). `offset` shifts RGB channels apart over 0 to 2pi -- 0 produces grayscale, nonzero creates rainbow patterns.

```js
osc(10, 0.1, 1.5).out()
```

### noise( scale = 10, offset = 0.1 )

Animated 2D Perlin noise. `scale` controls zoom. `offset` controls evolution speed. Outputs both positive and negative values -- can produce unexpected results when used as a modulator.

```js
noise(3, 0.1).out()
```

### voronoi( scale = 5, speed = 0.3, blending = 0.3 )

Voronoi cell diagram. `scale` sets cell density. `speed` controls animation. `blending` controls edge softness -- 0 gives sharp boundaries, higher values blend cells.

```js
voronoi(25, 0, 0).out()  // sharp, static cells
```

### shape( sides = 3, radius = 0.3, smoothing = 0.01 )

Centered polygon. `sides` sets edge count (2 = line, large values approximate circle). `radius` controls size (0-1). `smoothing` controls edge gradient -- near 0 = sharp, 1 = maximally fuzzy. Setting smoothing to exactly 0 may not render correctly.

```js
shape(6, 0.5, 0.01).out()  // hexagon
```

### gradient( speed = 0 )

UV-based gradient: red channel = x coordinate, green = y coordinate, blue oscillates via `sin(time * speed)`. Static at speed=0.

```js
gradient(1).out()
```

### solid( r = 0, g = 0, b = 0, a = 1 )

Uniform solid color fill. All four RGBA channels directly controllable.

```js
solid(1, 0.5, 0, 1).out()  // solid orange
```

### src( tex )

Reads from an existing texture -- output buffer (`o0`-`o3`) or external source buffer (`s0`-`s3`). Used for camera feeds, images, videos, feedback loops, and cross-buffer routing.

```js
src(o0).rotate(0.1).out(o0)  // feedback loop
src(s0).out()                 // external source
```

### prev( )

Returns previous frame output from the current buffer. No parameters. Useful for feedback without explicitly referencing a buffer.

```js
osc(10).blend(prev(), 0.9).out()  // trails
```

---

## Geometry Transforms (type: `coord`) -- 10 functions

### rotate( angle = 10, speed = 0 )

Rotates texture. `angle` in radians (default 10 = ~1.6 full rotations, intentional for an interesting default). `speed` adds continuous rotation over time.

```js
osc(10).rotate(0.5, 0.1).out()
```

### scale( amount = 1.5, xMult = 1, yMult = 1, offsetX = 0.5, offsetY = 0.5 )

Scales texture. `amount` > 1 zooms out, < 1 zooms in. `xMult`/`yMult` independently scale axes. `offsetX`/`offsetY` set scaling origin (0.5 = center). Aspect ratio correction: `scale(1, 1, () => window.innerWidth/window.innerHeight)`.

```js
shape().scale(2, 1, 1).out()
```

### pixelate( pixelX = 20, pixelY = 20 )

Quantizes texture into a grid of `pixelX` x `pixelY` segments.

```js
noise().pixelate(20, 20).out()
```

### repeat( repeatX = 3, repeatY = 3, offsetX = 0, offsetY = 0 )

Tiles texture into a grid. `offsetX`/`offsetY` shift each tile (animate for patterns).

```js
shape().repeat(3, 3, 0, 0).out()
```

### repeatX( reps = 3, offset = 0 )

Horizontal tiling only.

```js
osc(5, 0, 1).repeatX(3, 0.5).out()
```

### repeatY( reps = 3, offset = 0 )

Vertical tiling only.

```js
osc(5, 0, 1).repeatY(3, 0.5).out()
```

### kaleid( nSides = 4 )

Kaleidoscope reflecting across `nSides` radial axes. Small values = geometric, 50+ = mandala.

```js
osc(25, -0.1, 0.5).kaleid(50).out()
```

### scroll( scrollX = 0.5, scrollY = 0.5, speedX = 0, speedY = 0 )

Offsets texture position with independent speed for both axes.

```js
osc().scroll(0.5, 0.5, 0.1, 0).out()
```

### scrollX( scrollX = 0.5, speed = 0 )

Horizontal scroll. `scrollX` = initial offset, `speed` = continuous movement.

```js
osc(10, 0, 1).scrollX(0, 0.1).out()
```

### scrollY( scrollY = 0.5, speed = 0 )

Vertical scroll.

```js
gradient(1).scrollY(0, () => Math.sin(time * 0.05) * 0.05).out()
```

---

## Color Transforms (type: `color`) -- 16 functions

### color( r = 1, g = 1, b = 1, a = 1 )

Multiplies each channel by the value. `color(1,0,0)` isolates red. `color(0.5,0.5,0.5)` darkens.

```js
osc().color(1, 0, 0.5).out()
```

### invert( amount = 1 )

Inverts colors. 1 = full invert, 0 = no effect, fractional = partial.

```js
osc(4, 0.1, 2).invert().out()
```

### brightness( amount = 0.4 )

Adds flat value to all color channels.

```js
noise().brightness(0.3).out()
```

### contrast( amount = 1.6 )

Adjusts contrast. > 1 pushes toward extremes, < 1 flattens.

```js
osc(10).contrast(2).out()
```

### saturate( amount = 2 )

HSV saturation. 0 = grayscale, 1 = unchanged, > 1 = oversaturated.

```js
osc(10, 0, 1).saturate(3).out()
```

### hue( hue = 0.4 )

Shifts hue in HSV space. 0-1 = full rotation through color wheel.

```js
osc(10, 0, 1).hue(0.5).out()
```

### luma( threshold = 0.5, tolerance = 0.1 )

Alpha mask by luminance. Brighter than `threshold` stays visible, darker becomes transparent. `tolerance` controls transition smoothness (smoothstep). Combine with `.layer()` for compositing.

```js
osc(10, 0, 1).luma(0.5, 0.1).out()
```

### thresh( threshold = 0.5, tolerance = 0.04 )

Hard threshold: brighter = white, darker = black. Alpha preserved. `tolerance` must be > 0.

```js
noise(3, 0.1).thresh(0.5, 0.04).out()
```

### posterize( bins = 3, gamma = 0.6 )

Quantizes to `bins` discrete levels per channel. `gamma` adjusts curve before quantization.

```js
gradient(0).posterize(3, 0.6).out()
```

### shift( r = 0.5, g = 0, b = 0, a = 0 )

Shifts each channel by adding the value, wrapping via `fract()`. Produces color cycling.

```js
osc(10).shift(0.5, 0.3, 0.1).out()
```

### colorama( amount = 0.005 )

HSV-based color cycling. Small values = subtle shimmer, larger = intense psychedelic shifts.

```js
osc(10, 0, 1).colorama(0.01).out()
```

### sum( scale = 1 )

Sums all color channels weighted by `scale` (vec4 type). Collapses color into luminance-like value.

### r( scale = 1, offset = 0 )

Extracts red channel: `_c0.r * scale + offset` fills all output channels.

```js
osc(10, 0, 1).r(1, 0).out()
```

### g( scale = 1, offset = 0 )

Extracts green channel via `_c0.g * scale + offset`.

### b( scale = 1, offset = 0 )

Extracts blue channel via `_c0.b * scale + offset`.

### a( scale = 1, offset = 0 )

Extracts alpha channel via `_c0.a * scale + offset`.

---

## Blend Transforms (type: `combine`) -- 7 functions

The first texture is the chain's current source (`_c0`), the second is passed as the argument (`_c1`).

### add( texture, amount = 1 )

Additive blending. `amount` multiplies the second texture before adding. Negative values subtract.

```js
osc(9, 0.1, 1).add(osc(13, 0.5, 5), 0.5).out()
```

### sub( texture, amount = 1 )

Subtractive blending.

```js
osc(9).sub(shape(), 0.5).out()
```

### blend( texture, amount = 0.5 )

Linear interpolation. 0 = base only, 1 = texture only. Values outside 0-1 produce overblended results.

```js
osc(9, 0.1, 1).blend(noise(3), 0.4).out()
```

### mult( texture, amount = 1 )

Multiplicative blending. Dark in either source = dark result. `amount` interpolates between unaffected and fully multiplied.

```js
osc(9, 0.1, 2).mult(osc(13, 0.5, 5)).out()
```

### diff( texture )

Absolute difference: `abs(_c0 - _c1)`. No extra numeric parameter. Identical = black, different = bright.

```js
osc(10).diff(osc(200).rotate(0.2)).out()
```

### layer( texture )

Alpha compositing -- overlays second texture using its alpha for transparency. No extra parameter. Works well with `.luma()` or `.shape()` which produce alpha.

```js
solid(1, 0, 0).layer(shape(4).luma()).out()
```

### mask( texture )

Luminance of second texture becomes alpha mask for the first. Bright = visible, dark = transparent. No extra numeric parameter.

```js
osc(10, 0, 1).mask(shape(4)).out()
```

---

## Modulate Transforms (type: `combineCoord`) -- 11 functions

Modulate functions use color values of one source to warp the coordinates of another. Red channel drives X-displacement, green drives Y-displacement (for basic `modulate`). Each mirrors a geometry transform but applies it variably based on modulator brightness.

### modulate( texture, amount = 0.1 )

General coordinate modulation. Bright areas in modulator = more displacement.

```js
osc(21, 0).modulate(noise(3), 0.1).out()
```

### modulateScale( texture, multiple = 1, offset = 1 )

Variable scaling. `multiple` controls intensity, `offset` sets base scale (1 = no change).

```js
gradient(5).repeat(50, 50)
  .modulateScale(osc(4, -0.5, 0).kaleid(50).scale(0.5), 15, 0)
  .out()
```

### modulatePixelate( texture, multiple = 10, offset = 3 )

Variable pixelation. Different brightness = different pixelation levels.

```js
voronoi(10, 1, 5).modulatePixelate(noise(25, 0.5), 100).out()
```

### modulateRotate( texture, multiple = 1, offset = 0 )

Variable rotation. `offset` adds constant rotation.

```js
voronoi(100, 3, 5)
  .modulateRotate(osc(1, 0.5, 0).kaleid(50).scale(0.5), 15, 0)
  .out()
```

### modulateHue( texture, amount = 1 )

Warps coordinates by color channel differences: horizontal from G-R, vertical from B-G. Creates complex organic motion from colorful modulators.

```js
osc(10, 0, 1).modulateHue(osc(3, 0.1, 2), 1).out()
```

### modulateRepeat( texture, repeatX = 3, repeatY = 3, offsetX = 0.5, offsetY = 0.5 )

Variable tiling modulated by texture.

```js
shape(4, 0.9).modulateRepeat(osc(10), 3, 3, 0.5, 0.5).out()
```

### modulateRepeatX( texture, reps = 3, offset = 0.5 )

Variable horizontal tiling.

```js
shape(4, 0.9).mult(osc(4, 0.25, 1))
  .modulateRepeatX(osc(10), 5.0, ({time}) => Math.sin(time) * 5)
  .out()
```

### modulateRepeatY( texture, reps = 3, offset = 0.5 )

Variable vertical tiling.

### modulateKaleid( texture, nSides = 4 )

Variable kaleidoscope.

```js
osc(9, -0.1, 0.1).modulateKaleid(osc(11, 0.5, 0), 50).out()
```

### modulateScrollX( texture, scrollX = 0.5, speed = 0 )

Variable horizontal scroll. Bright areas scroll more.

```js
voronoi(25, 0, 0).modulateScrollX(osc(10), 0.5, 0.25).out()
```

### modulateScrollY( texture, scrollY = 0.5, speed = 0 )

Variable vertical scroll.

```js
voronoi(25, 0, 0).modulateScrollY(osc(10), 0.5, 0.25).out()
```

---

## External Sources

Four source buffers `s0`-`s3` load external media. Initialize first, then access via `src()`.

### s0.initCam( index = 0, params )

Webcam. `index` selects camera (0, 1, 2...). Optional `params` for regl texture options (e.g. `{mag: 'linear'}` for smooth scaling).

```js
s0.initCam()
src(s0).saturate(2).kaleid(4).out()
```

### s0.initImage( url, params )

Static image from URL. Formats: jpeg, png, bmp, gif, webp (webp animation unsupported). Subject to CORS -- use imgur/Wikimedia or local server.

```js
s0.initImage("https://upload.wikimedia.org/wikipedia/commons/2/25/Hydra-Foto.jpg")
src(s0).out()
```

### s0.initVideo( url, params )

Video file. Formats: mp4, ogg, webm. YouTube/Vimeo URLs do not work (return webpages). After init, control via `s0.src`:

```js
s0.initVideo("https://example.com/video.mp4")
s0.src.playbackRate = 2
s0.src.currentTime = 10
s0.src.loop = false
src(s0).out()
```

### s0.initScreen( params )

Screen capture via browser dialog.

```js
s0.initScreen()
src(s0).kaleid(3).out()
```

### s0.init( opts, params )

Generic initializer for any regl-compatible source (canvas, video element). Use `{dynamic: true}` for updating sources.

```js
s0.init({src: myCanvasElement, dynamic: true})
```

### s0.initStream( streamName, params )

WebRTC stream from another Hydra editor. Currently broken due to server issues.

---

## Audio Reactivity (the `a` object)

Uses Meyda for real-time FFT of microphone input (not desktop audio).

| Method | Description |
|--------|-------------|
| `a.show()` | Display FFT visualization overlay |
| `a.hide()` | Hide FFT visualization |
| `a.fft[n]` | FFT bin value mapped 0-1; use inside arrow functions |
| `a.setBins(n)` | Number of frequency bands |
| `a.setCutoff(n)` | Noise gate threshold; bins below return 0 |
| `a.setScale(n)` | Loudness ceiling; bins at or above return 1 |
| `a.setSmooth(n)` | Smoothing (0 = jumpy, 1 = frozen) |

Additional properties: `a.bins` (raw values), `a.prevBins` (previous frame), `a.vol` (overall volume), per-bin settings via `a.settings[n].cutoff` and `a.settings[n].scale`.

```js
a.show()
a.setBins(5)
a.setSmooth(0.8)
a.setScale(8)
a.setCutoff(0.1)

osc(20, 0.1, () => a.fft[0] * 10)
  .rotate(() => a.fft[1])
  .kaleid()
  .out()
```

---

## Mouse Interactivity

`mouse` object tracks cursor position in pixels. Normalize for Hydra parameters:

| Expression | Range | Use |
|-----------|-------|-----|
| `() => mouse.x / window.innerWidth` | 0-1 | General control |
| `() => mouse.y / window.innerHeight` | 0-1 | General control |
| `() => mouse.x / window.innerWidth * 2 * Math.PI` | 0-2pi | Rotation |
| `() => mouse.x / window.innerWidth - 0.5` | -0.5 to 0.5 | Centered offset |

```js
osc(() => mouse.x / window.innerWidth * 60, 0.1, 0)
  .rotate(() => mouse.y / window.innerHeight * Math.PI * 2)
  .out()
```

---

## Global Settings and Variables

| Setting | Default | Description |
|---------|---------|-------------|
| `time` | -- | Seconds since Hydra started (read-only) |
| `speed` | 1 | Time multiplier (0 = frozen, 2 = double) |
| `bpm` | 30 | Beats per minute for array sequencing |
| `width` | 1280 | Canvas width in pixels (read-only) |
| `height` | 720 | Canvas height in pixels (read-only) |
| `mouse.x`, `mouse.y` | -- | Mouse pixel position |
| `setResolution(w, h)` | -- | Change canvas resolution |
| `hush()` | -- | Clear all outputs (does not reset speed/bpm) |
| `update = (dt) => {}` | -- | Per-frame callback; dt = time since last frame |
| `render(buffer)` | all | Display output(s) on screen |

---

## Custom GLSL with setFunction

Extend Hydra with custom shader functions:

```js
setFunction({
  name: 'myEffect',
  type: 'color',  // 'src', 'coord', 'color', 'combine', 'combineCoord'
  inputs: [
    { type: 'float', name: 'intensity', default: 1.0 }
  ],
  glsl: `return vec4(_c0.rgb * intensity, _c0.a);`
})
osc().myEffect(2.0).out()
```

Input types: `'float'`, `'vec2'`, `'vec3'`, `'vec4'`, `'sampler2D'`.

Built-in GLSL helpers available in all shaders:
- `_luminance(vec3 rgb)` -- perceptual luminance (0.2125R + 0.7154G + 0.0721B)
- `_rgbToHsv(vec3 c)` -- RGB to HSV
- `_hsvToRgb(vec3 c)` -- HSV to RGB
- `time` (float) and `resolution` (vec2) uniforms

---

## MIDI Support

Via `hydra-midi` extension:

```js
await loadScript('https://cdn.jsdelivr.net/npm/hydra-midi@latest/dist/index.js')
await midi.start().show()
osc(30, 0.01).invert(note('C4')).out()
osc().rotate(cc(45).range(0, Math.PI * 2)).out()
```

---

## Quick Reference Table (all 52 functions)

| # | Function | Type | Parameters (name = default) |
|---|----------|------|-----------------------------|
| 1 | `osc` | src | frequency=60, sync=0.1, offset=0 |
| 2 | `noise` | src | scale=10, offset=0.1 |
| 3 | `voronoi` | src | scale=5, speed=0.3, blending=0.3 |
| 4 | `shape` | src | sides=3, radius=0.3, smoothing=0.01 |
| 5 | `gradient` | src | speed=0 |
| 6 | `solid` | src | r=0, g=0, b=0, a=1 |
| 7 | `src` | src | tex (sampler2D) |
| 8 | `prev` | src | *(none)* |
| 9 | `rotate` | coord | angle=10, speed=0 |
| 10 | `scale` | coord | amount=1.5, xMult=1, yMult=1, offsetX=0.5, offsetY=0.5 |
| 11 | `pixelate` | coord | pixelX=20, pixelY=20 |
| 12 | `repeat` | coord | repeatX=3, repeatY=3, offsetX=0, offsetY=0 |
| 13 | `repeatX` | coord | reps=3, offset=0 |
| 14 | `repeatY` | coord | reps=3, offset=0 |
| 15 | `kaleid` | coord | nSides=4 |
| 16 | `scroll` | coord | scrollX=0.5, scrollY=0.5, speedX=0, speedY=0 |
| 17 | `scrollX` | coord | scrollX=0.5, speed=0 |
| 18 | `scrollY` | coord | scrollY=0.5, speed=0 |
| 19 | `color` | color | r=1, g=1, b=1, a=1 |
| 20 | `invert` | color | amount=1 |
| 21 | `brightness` | color | amount=0.4 |
| 22 | `contrast` | color | amount=1.6 |
| 23 | `saturate` | color | amount=2 |
| 24 | `hue` | color | hue=0.4 |
| 25 | `luma` | color | threshold=0.5, tolerance=0.1 |
| 26 | `thresh` | color | threshold=0.5, tolerance=0.04 |
| 27 | `posterize` | color | bins=3, gamma=0.6 |
| 28 | `shift` | color | r=0.5, g=0, b=0, a=0 |
| 29 | `colorama` | color | amount=0.005 |
| 30 | `sum` | color | scale=1 (vec4) |
| 31 | `r` | color | scale=1, offset=0 |
| 32 | `g` | color | scale=1, offset=0 |
| 33 | `b` | color | scale=1, offset=0 |
| 34 | `a` | color | scale=1, offset=0 |
| 35 | `add` | combine | texture, amount=1 |
| 36 | `sub` | combine | texture, amount=1 |
| 37 | `blend` | combine | texture, amount=0.5 |
| 38 | `mult` | combine | texture, amount=1 |
| 39 | `diff` | combine | texture *(no extra params)* |
| 40 | `layer` | combine | texture *(no extra params)* |
| 41 | `mask` | combine | texture *(no extra params)* |
| 42 | `modulate` | combineCoord | texture, amount=0.1 |
| 43 | `modulateScale` | combineCoord | texture, multiple=1, offset=1 |
| 44 | `modulatePixelate` | combineCoord | texture, multiple=10, offset=3 |
| 45 | `modulateRotate` | combineCoord | texture, multiple=1, offset=0 |
| 46 | `modulateHue` | combineCoord | texture, amount=1 |
| 47 | `modulateRepeat` | combineCoord | texture, repeatX=3, repeatY=3, offsetX=0.5, offsetY=0.5 |
| 48 | `modulateRepeatX` | combineCoord | texture, reps=3, offset=0.5 |
| 49 | `modulateRepeatY` | combineCoord | texture, reps=3, offset=0.5 |
| 50 | `modulateKaleid` | combineCoord | texture, nSides=4 |
| 51 | `modulateScrollX` | combineCoord | texture, scrollX=0.5, speed=0 |
| 52 | `modulateScrollY` | combineCoord | texture, scrollY=0.5, speed=0 |
