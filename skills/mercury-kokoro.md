---
name: mercury-kokoro
description: Guide for using the Kokoro neural text-to-speech instrument in Mercury Playground to create high-quality musical compositions with spoken words. Use when writing Mercury code with the kokoro instrument or composing with neural speech synthesis.
---

# Mercury Kokoro -- Neural Voice as Musical Instrument

Mercury Playground is a live-coding environment for making music in the browser. The `kokoro` instrument uses the Kokoro-82M neural TTS model to generate high-quality, natural-sounding speech that flows through Tone.js -- fully sequenceable and effects-processable.

Kokoro renders audio asynchronously: text is pre-rendered when you evaluate code. The first evaluation with new text may have a brief delay before audio plays, but subsequent beats use cached audio instantly.

## Quick Reference

```
new kokoro time(1/4) say(hello world) voice(af_heart)
new kokoro time(2/1) say(hello_world how_are_you) voice(af_heart)
```

Every `kokoro` instance is a sequenced instrument. On each beat (controlled by `time()`), it speaks the next item from the `say()` list, cycling through them. Items can be single words (space-separated) or full phrases (underscore-joined).

## Core Parameters

### say(...words) -- what to speak
Words are cycled through per beat, one at a time:
```
new kokoro time(1/2) say(the future is now)
```

**Full phrases with underscores:** Use underscores to join words into a single phrase. Each underscore-joined token is rendered as one natural speech clip by the TTS engine:
```
new kokoro time(2/1) say(hello_how_are_you nice_to_meet_you) voice(af_heart)
```
This cycles between *"hello how are you"* and *"nice to meet you"* every 2 bars, spoken as complete natural phrases.

**When to use which:**
- **Individual words** (`say(yes no maybe)`) -- rhythmic, percussive speech; one word per beat
- **Phrases** (`say(the_future_is_now we_are_alive)`) -- natural narration; full sentences per beat

Pair phrases with slower time divisions (`time(1/1)`, `time(2/1)`, `time(4/1)`) so the speech has room to play out fully.

### time(division) -- rhythm
Standard Mercury time divisions:
```
time(1/4)    // quarter notes
time(1/2)    // half notes
time(1/1)    // whole notes
time(3/16)   // dotted eighth
```

### voice(name) -- neural voice selection
Kokoro provides high-quality voice models. Pass the voice ID directly:

**American English (Female):**
`af_heart` (best, default), `af_bella`, `af_nicole`, `af_sarah`, `af_kore`, `af_aoede`, `af_nova`, `af_alloy`, `af_jessica`, `af_river`, `af_sky`

**American English (Male):**
`am_fenrir`, `am_michael`, `am_puck`, `am_eric`, `am_adam`, `am_echo`, `am_liam`, `am_onyx`, `am_santa`

**British English (Female):**
`bf_emma`, `bf_isabella`, `bf_alice`, `bf_lily`

**British English (Male):**
`bm_george`, `bm_fable`, `bm_daniel`, `bm_lewis`

```
new kokoro time(1/2) say(good morning) voice(af_heart)
new kokoro time(1/2) say(good evening) voice(bm_george)
```

### speed(rate) -- playback rate
Changes the Tone.js playback rate (pitch + tempo shift):
```
new kokoro time(1/4) say(slowed down) speed(0.5)
new kokoro time(1/8) say(chipmunk) speed(2)
```

### renderSpeed(rate) -- TTS generation speed
Controls the Kokoro model's speaking speed during audio generation (default 1). Unlike `speed()` which changes playback pitch, this adjusts how fast the model speaks while preserving natural pitch:
```
new kokoro time(1/2) say(speaking quickly) renderSpeed(1.5)
new kokoro time(1/1) say(speaking slowly) renderSpeed(0.7)
```

### env(attack release) -- amplitude envelope
Shapes each note's volume:
```
new kokoro time(1/4) say(hello) env(5 200)
```

### amp(gain) -- volume
```
new kokoro time(1/4) say(quiet) amp(0.3)
```

### pan(position) -- stereo placement
-1 (left) to 1 (right):
```
new kokoro time(1/2) say(left right) pan(-0.8 0.8)
```

### fx(effect ...params) -- effects chain
All Mercury effects work: reverb, delay, distort, filter, chorus, etc.
```
new kokoro time(1/2) say(vast spaces) voice(af_heart) fx(reverb 0.9) fx(delay 3/16 0.6)
```

## Composition Patterns

### Spoken word poetry (phrases)
```
set tempo 60
new kokoro time(2/1) say(time_flows_like_water through_open_hands) voice(af_heart) fx(reverb 0.8) amp(0.6)
```

### Dual narrator (phrases)
```
set tempo 80
new kokoro time(2/1) say(once_upon_a_time in_a_world_of_sound) voice(af_bella) pan(-0.6) fx(reverb 0.4)
new kokoro time(2/1) say(the_story_begins and_never_ends) voice(bm_george) pan(0.6) fx(reverb 0.4)
```

### Rhythmic speech (individual words)
```
set tempo 100
new kokoro time(1/4) say(yes no maybe so) voice(af_kore) env(5 100)
```

### Layered with instruments (phrase + words mix)
```
set tempo 90
new sample kick_house time(1/4)
new synth sine time(1/8) note(0 3 7 0) shape(1 1/8)
new kokoro time(2/1) say(we_are_the_music_makers and_we_are_the_dreamers) voice(af_heart) fx(reverb 0.7) amp(0.5)
```

### Character voices (phrases)
```
set tempo 70
new kokoro time(2/1) say(greetings_human I_come_in_peace) voice(am_fenrir) speed(0.8) fx(reverb 0.3)
new kokoro time(2/1) say(hello_there nice_to_meet_you) voice(af_bella) speed(1.1) pan(0.5)
```

### Industrial rave (phrases + words)
```
set tempo 140
new sample kick_909 time(1/4) gain(0.9) fx(drive 6)
new kokoro time(2/1) say(move_your_body never_stop_the_noise) voice(af_kore) fx(drive 4) amp(0.7)
new kokoro time(1/4) say(bass bass drop bass) voice(am_fenrir) fx(drive 5) amp(0.5)
```

## Tips for LLM Expression

1. **Use phrases for narration** -- `say(the_future_is_now)` with `time(2/1)` or `time(4/1)` for natural-sounding speech
2. **Use individual words for rhythm** -- `say(yes no maybe so)` with `time(1/4)` for percussive, beat-synced speech
3. **Mix both in one piece** -- phrases on slow kokoro layers for narration, single words on fast layers for texture
4. **Pre-render buffer time** -- first evaluation renders audio; wait for the "pre-rendered" console log before expecting sound
5. **Stack effects** -- reverb + delay creates cinematic vocal spaces; drive distorts voice for industrial textures
6. **Vary voices across layers** -- different kokoro voices for call-and-response patterns
7. **Use `renderSpeed()` for natural tempo changes** -- unlike `speed()`, it preserves pitch
