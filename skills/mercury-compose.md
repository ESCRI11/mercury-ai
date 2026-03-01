# Mercury Live Coding Composition

Compose music in the Mercury live coding language and send it to the running Mercury Playground webapp. Use this skill when the user asks you to create music, play sounds, express something musically, or interact with the Mercury Playground.

## Workflow

There are two modes of working: composing a new piece from scratch, and gradually evolving an existing piece. **Always prefer gradual editing when a piece is already playing.**

**Prerequisite**: The Mercury Playground server must be running (`node server.js` in `~/mercury-playground`) and the browser must be open at `http://localhost:8080`. The user must have clicked "play" at least once to initialize the audio context.

### Persistent state file

The current playing piece is always stored in `~/mercury-playground/current_piece.txt`. This file is the single source of truth for what is currently playing.

- When composing a **new piece from scratch**, write the full Mercury code to `current_piece.txt` using the Write tool, then send it.
- When **evolving an existing piece**, always read `current_piece.txt` first, then make targeted edits with StrReplace, then send.

### Gradual composition (default mode)

Live coding is about step-wise evolution, not wholesale replacement. When a piece is already playing:

1. **Read** `current_piece.txt` to see the current state.
2. **Make 3-4 targeted edits** using StrReplace -- tweak a parameter, swap a sample, add/remove a line, change an effect. Never rewrite the whole file.
3. **Send** the updated file to the server.
4. **Describe each change** briefly so the user knows what shifted (a table works well).

This mirrors how a real live coder works: small, deliberate tweaks that evolve the sound gradually. For larger transformations (e.g. changing genre), plan multiple rounds of 3-4 changes each and execute them in sequence.

### Sending code to the server

Use node (available in the project) to read the file and POST it:

```bash
node -e "
const http = require('http');
const fs = require('fs');
const code = fs.readFileSync('current_piece.txt', 'utf-8');
const data = JSON.stringify({ code });
const req = http.request({
  hostname: 'localhost', port: 8080, path: '/api/code',
  method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
}, res => { let b=''; res.on('data',c=>b+=c); res.on('end',()=>console.log(b)); });
req.write(data); req.end();
"
```

Run this from `~/mercury-playground`. Always use `required_permissions: ["full_network"]`.

### Stopping all sound

```bash
curl -s -X POST http://localhost:8080/api/silence \
  -H 'Content-Type: application/json' \
  -d '{}'
```

## Mercury Language Reference

### Global Settings

```
set tempo <bpm>                    // set beats per minute (60-200+)
set scale <name> <root>            // constrain notes to a scale
set randomSeed <number>            // fix random sequences for reproducibility
set volume <0-1>                   // master volume
set highPass <freq>                // master high-pass filter
set lowPass <freq>                 // master low-pass filter
```

Scale names: `major`, `minor`, `dorian`, `mixolydian`, `lydian`, `phrygian`, `locrian`, `harmonic_minor`, `melodic_minor`, `minor_pentatonic`, `major_pentatonic`, `chromatic`, `whole_tone`, `blues`, `arabic`, `japanese`, and more. Use `set scale none` to allow all chromatic notes.

### Instruments

```
new sample <name>                  // play a sound file
new synth <waveform>               // create a synthesizer
new noise <type>                   // create noise generator
new polySynth <waveform>           // polyphonic synth (chords)
new polySample <name>              // polyphonic sample player
new loop <name>                    // loop a sample continuously
```

Waveforms: `saw`, `sine`, `square`, `triangle`
Noise types: `white`, `pink`, `brown`, `lofi`, `crackle`, `dust`

### Core Methods (applied to instruments)

```
time(<division>)                   // timing: 1/4, 1/8, 1/16, 1/2, etc.
time(<div1> <div2>)                // alternating timing pattern
note(<value> <octave>)             // pitch as semitone offset + octave
note(<list> <octave>)              // melody from a list
shape(<attack> <release>)          // envelope in ms or divisions
shape(<attack> <sustain> <release>)
shape(off)                         // continuous tone (no envelope)
play(<list>)                       // rhythm pattern of 1s and 0s
gain(<0-1>)                        // volume per instrument
pan(<-1 to 1>)                     // stereo position (-1=L, 1=R)
pan(random)                        // random panning per trigger
name(<id>)                         // give instrument a name for `set`
speed(<value>)                     // sample playback speed
start(<0-1>)                       // sample start position
slide(<time>)                      // portamento between notes
super(<voices> <detune>)           // unison/supersaw (detune in semitones)
wait(<division>)                   // delay before first trigger
timediv(<list>)                    // time division multiplier
human(<ms>)                        // humanize timing by +/- ms
```

### Setting instrument properties by name

```
new synth saw name(bass)
    set bass note(0 1) time(1/4)
    set bass fx(reverb 0.5 3)
```

### Apply effects/settings to all instruments

```
set all fx(reverb 0.5 5)
set all fx(delay 3/16 5/16 0.8)
set all super(3 0.12)
```

### Effects

```
fx(reverb <wet 0-1> <decay seconds>)
fx(delay <timeL> <timeR> <feedback 0-1>)
fx(distort <amount>)                        // alias: drive
fx(fuzz <amount> <mix>)
fx(filter <type> <cutoff> <resonance>)      // type: low, high, band
fx(filter <type> <modSpeed> <min> <max> <resonance>)
fx(triggerFilter <type> <attack> <release> <max> <min> <resonance>)
fx(shift <semitones>)                       // pitch shift
fx(shift <list>)                            // melodic pitch shift
fx(squash <amount>)                         // compression
fx(compress)                                // gentle compression
fx(degrade <amount 0-1>)                    // bitcrusher/lo-fi
fx(chorus <rate> <depth>)
fx(vibrato <rate> <depth>)
fx(lfo <rate> <depth>)
```

### Lists

Lists hold sequences of numbers or words used for melodies, rhythms, effects modulation.

```
list <name> [<values separated by spaces>]
list melody [0 3 5 7 12 7 5 3]
list beat [1 0 1 0 0 1 0 1]
list sounds [kick_808 hat_808 snare_808]
```

2D lists for chords (polySynth):
```
list chord [ [0 4 7] [2 5 9] [4 7 11] ]
```

### Algorithmic List Generators

```
spread(size low high)              // evenly spaced integers
spreadFloat(size low high)         // evenly spaced floats
spreadInclusive(size low high)     // includes the high value
random(size low high)              // random integers
randomF(size low high)             // random floats
drunk(size step)                   // random walk
choose(size [options])             // random pick from list
shuffle([values])                  // randomize order
euclid(steps beats)                // euclidean rhythm
euclid(steps beats rotate)         // with rotation
hex('<hexstring>')                 // hex to binary rhythm
sine(size periods lo hi)           // sine wave as list
cosine(size periods lo hi)         // cosine wave as list
saw(size periods lo hi)            // sawtooth as list
clave(size hits shift)             // clave-style rhythm
fibonacci(length)                  // fibonacci sequence
pisano(mod)                        // pisano periods
```

### List Transformations

```
reverse(<list>)                    // reverse order
palin(<list>)                      // palindrome
rotate(<list> <n>)                 // rotate by n positions
invert(<list> <lo> <hi>)           // invert values
clone(<list> <offsets...>)         // repeat with transpositions
join(<list1> <list2>)              // concatenate
repeat(<list> <n>)                 // repeat n times
lace(<list1> <list2>)              // interleave
flat(<list>)                       // flatten 2D to 1D
slice(<list> <start> <end>)        // extract sublist
add(<list> <value or list>)        // add values
subtract(<list> <value>)           // subtract
multiply(<list> <value>)           // multiply
divide(<list> <value>)             // divide
normalize(<list>)                  // normalize to 0-1
```

### Chord Generation

```
chordsFromNumerals([I IV V VIm])           // Roman numeral chords
chordsFromNumerals([I7 IIIm7 IV7 V7])     // with 7ths
chordsFromNames([Cmaj Fmaj Gmaj Am])       // named chords
```

### Utility

```
print <list>                       // print list to console
silence                            // stop all sound
```

## Available Sounds

### Drums - Kicks
kick_808, kick_808_dist, kick_909, kick_909_dist, kick_909_dist_long, kick_909_long, kick_deep, kick_dub, kick_house, kick_min, kick_nord, kick_nord_long, kick_sub, kick_ua, kick_vintage

### Drums - Snares
snare_808, snare_909, snare_909_short, snare_ac, snare_dnb, snare_dub, snare_fat, snare_hvy, snare_min, snare_nord, snare_nord_hi, snare_rock, snare_step

### Drums - Hats
hat_808, hat_808_half, hat_808_open, hat_909, hat_909_half, hat_909_open, hat_909_short, hat_click, hat_dub, hat_min, hat_min_open, hat_nord, hat_nord_open

### Drums - Claps & Percussion
clap_808, clap_808_short, clap_909, clap_min, clap_nord, block, block_lo, bongo, bongo_lo, clave_808, cowbell_808, cymbal_808, maracas_808, wood_nord_hi, wood_nord_lo, wood_nord_mid

### Drums - Toms & Tabla
tom_808, tom_hi, tom_lo, tom_mid, tom_nord_hi, tom_nord_lo, tabla_01, tabla_02, tabla_03, tabla_hi, tabla_hi_long, tabla_hi_short, tabla_lo, tabla_lo_long, tabla_lo_short, tabla_mid, tabla_mid_long, tabla_mid_short, tongue, tongue_lo

### Metallic & Textural
shatter, metal, metal_lo, wobble, wobble_02, door, scrape, scrape_01, wood_hit, wood_metal, wood_plate

### Bells & Pitched Percussion
bell, bell_c4, bell_c5, bell_f5, bell_g4, chimes, chimes_chord, chimes_chord_01, chimes_chord_02, chimes_hi, chimes_l, glock_c5, glock_c6, glock_g4, glock_g5, gong_hi, gong_lo, kalimba_a, kalimba_ab, kalimba_cis, kalimba_e, kalimba_g, marimba_b2, marimba_c2, marimba_c4, marimba_f3, marimba_g2, marimba_g4

### Tuned Percussion & Keys
bamboo_a, bamboo_c, bamboo_f, bamboo_g, box_a4, box_b4, box_b5, box_c5, box_d5, box_d6, box_g3, box_g5, bowl_hi, bowl_lo, bowl_mid, xylo_c4, xylo_c5, xylo_c6, xylo_g3, xylo_g4, xylo_g5, rhodes_8bit, piano_a, piano_b, piano_c, piano_d, piano_e, piano_f, piano_g

### Strings & Orchestral
violin_a, violin_b, violin_c, violin_d, violin_e, violin_f, violin_g, harp_a2, harp_a4, harp_b3, harp_b5, harp_c3, harp_c5, harp_d4, harp_down, harp_e3, harp_e5, harp_f4, harp_g3, harp_g5, harp_up, pluck_a, pluck_b, pluck_c, pluck_d, pluck_e, pluck_f, pluck_g

### Woodwinds
clarinet_a2, clarinet_a3, clarinet_d2, clarinet_d3, clarinet_f2, clarinet_f3, flute_a3, flute_a4, flute_c3, flute_c4, flute_c5, flute_e3, flute_e4, oboe_a2, oboe_a3, oboe_d3, oboe_d4, oboe_f3, oboe_f4

### Vocals & Atmosphere
choir_01, choir_02, choir_03, choir_o, noise_a, noise_c, noise_e, noise_e_01, noise_mw, noise_p, noise_r, drone_cymbal, drone_cymbal_01, wiper, wiper_out, wood_l, wood_l_01

### Breakbeats
amen, amen_alt, amen_break, amen_fill, house

## Composition Tips by Mood

### Ambient / Dreamy
- Tempo: 60-90 BPM
- Scales: `dorian`, `minor_pentatonic`, `lydian`
- Use `shape(off)` or long shapes for drones
- Heavy `fx(reverb 0.6-0.8 8-15)`
- `super()` with small detune for warmth
- `slide()` for gliding between notes
- Sine and triangle waveforms
- Bowl, chimes, and harp samples

### Techno / Acid
- Tempo: 125-140 BPM
- 4-on-the-floor kick: `new sample kick_909 time(1/4)`
- Hihats on 1/8 or 1/16
- Saw synth with `fx(filter low ...)` modulation
- `fx(distort)` or `fx(drive)` for grit
- `fx(delay)` for groove

### Lo-fi / Hip-hop
- Tempo: 75-95 BPM
- Scales: `minor`, `minor_pentatonic`, `blues`
- Chopped samples with `start()` and `shape()`
- `fx(degrade)` for lo-fi character
- Rhodes and piano samples
- Soft kicks and snares

### Drum & Bass / Jungle
- Tempo: 160-180 BPM
- Chopped amen breaks with `new loop amen`
- Fast hihats on 1/16
- Deep bass with `fx(triggerFilter)`
- Complex rhythms via `euclid()` and `hex()`

### Cinematic / Blade Runner
- Tempo: 30-60 BPM
- Scales: `dorian`, `phrygian`, `harmonic_minor`
- Multiple detuned saws with `super(3-5 0.1-0.2)`
- `shape(off)` for pads
- `slide()` for slow pitch movement
- `fx(reverb 0.7 10-15)`, `fx(compress)`
- Choir and string samples

### Generative / Algorithmic
- Use `random()`, `drunk()`, `choose()` for variety
- `set randomSeed` for reproducibility
- `euclid()` and `hex()` for rhythmic patterns
- `sine()`, `cosine()` for smooth parameter modulation
- `clone()` with offsets for thematic development
- Long lists for evolving textures

## Complete Examples

### Ambient Pad
```
set tempo 72
set scale dorian d
set randomSeed 9182

list notes shuffle(spreadInclusive(8 0 12))
new synth saw note(notes 0) time(2/1) slide(1/2) pan(random)
new synth saw note(notes -1) time(2/1) slide(1/2) pan(random)
set all super(3 0.132) shape(off)
set all fx(filter low 4/1 1000 4000 0.4)
set all fx(reverb 0.7 12) fx(compress)
```

### Techno Beat
```
set tempo 131

new sample kick_909 time(1/4) name(kick)
    set kick speed(0.9) fx(drive 5) gain(0.9)
    set kick fx(delay 7/16 6/16 0.7)

new sample [[hat_808 hat_808_open]] time(1/4 1/8)

new synth saw time(1/16) shape(1 1/32 1) name(bass)
    set bass fx(filter low random(16 50 3000))
    set bass fx(reverb 0.5 5) super(3 0.01532)
```

### Generative Melody
```
set tempo 98
set scale minor_pentatonic b

list theme sine(16 5 0 24)
list variation invert(theme 0 24)
list phrase join(theme variation)
list section clone(phrase 0 5 9 7)

new synth triangle name(arpy)
    set arpy time(1/16) shape(1 170) note(section 0)
    set arpy pan(random) fx(filter low 2300 0.4) fx(delay 4/16 5/16 0.8)
```

### Chord Progression
```
set tempo 110
set scale dorian d

list progression chordsFromNumerals([I7 IIIm7 IV7 V7])
new polySynth saw name(chrd)
    set chrd note(progression 1) time(2/1) shape(1 2/1)
    set chrd fx(triggerFilter low 1/1 1/1 4000 100) super(3 0.132)

set all fx(squash 1) fx(reverb 0.4 7)
```

## Visuals (Hydra) are now separate

Hydra visual guidance has moved to the `mercury-hydra` skill so this skill stays focused on audio composition and sound design.

When the user asks for visuals, background animations, or `visual()` usage, load and follow the `mercury-hydra` skill.
