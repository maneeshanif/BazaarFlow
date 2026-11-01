/**
 * The site's sounds. Off until the visitor turns them on (a toggle, bottom right), as on the reference. Every sound is made
 * here with the Web Audio API, so there are no sound files to ship; a recorded sound can replace any of them later by
 * decoding a file into the same `play` call. Nothing here runs on the server.
 */
export type SoundName = "click" | "toggle" | "menuPull" | "menuHover" | "slideChange" | "tapeCut" | "tapePress" | "ballHit" | "hover";

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let noise: AudioBuffer | null = null;
let on = false;
const listeners = new Set<(v: boolean) => void>();

export const isSoundOn = () => on;
export function onSoundChange(fn: (v: boolean) => void): () => void {
  listeners.add(fn);
  return () => void listeners.delete(fn);
}

function ensure(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = 0.7;
    master.connect(ctx.destination);
    noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
    const d = noise.getChannelData(0);
    for (let i = 0; i < d.length; i += 1) d[i] = Math.random() * 2 - 1;
  }
  void ctx.resume();
  return ctx;
}

export function setSoundOn(v: boolean) {
  on = v;
  if (v) {
    ensure();
    play("toggle");
  }
  listeners.forEach((fn) => fn(v));
}

/** A short pitched blip that slides from one pitch to another. */
function tone(c: AudioContext, at: number, from: number, to: number, dur: number, vol: number, type: OscillatorType = "sine") {
  const o = c.createOscillator();
  const g = c.createGain();
  o.type = type;
  o.frequency.setValueAtTime(from, at);
  o.frequency.exponentialRampToValueAtTime(Math.max(to, 20), at + dur);
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(vol, at + 0.008);
  g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
  o.connect(g).connect(master!);
  o.start(at);
  o.stop(at + dur + 0.02);
}

/** A burst of filtered noise; the filter can sweep. */
function hiss(c: AudioContext, at: number, dur: number, vol: number, type: BiquadFilterType, from: number, to: number, q = 1) {
  const s = c.createBufferSource();
  s.buffer = noise;
  const f = c.createBiquadFilter();
  f.type = type;
  f.Q.value = q;
  f.frequency.setValueAtTime(from, at);
  f.frequency.exponentialRampToValueAtTime(Math.max(to, 20), at + dur);
  const g = c.createGain();
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(vol, at + Math.min(0.015, dur / 3));
  g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
  s.connect(f).connect(g).connect(master!);
  s.start(at);
  s.stop(at + dur + 0.02);
}

/** Plays one sound if sound is on. `vol` is 0..1. */
export function play(name: SoundName, vol = 1) {
  if (!on) return;
  const c = ensure();
  if (!c || !master) return;
  const t = c.currentTime;
  switch (name) {
    case "click":
      tone(c, t, 900, 520, 0.05, 0.22 * vol, "triangle");
      hiss(c, t, 0.025, 0.1 * vol, "highpass", 3000, 3000);
      break;
    case "toggle":
      tone(c, t, 520, 520, 0.09, 0.2 * vol);
      tone(c, t + 0.09, 780, 780, 0.12, 0.2 * vol);
      break;
    case "menuPull": // paper pulled down: a soft sweep and a low thump when it lands
      hiss(c, t, 0.4, 0.28 * vol, "bandpass", 400, 1800, 0.8);
      tone(c, t + 0.28, 170, 90, 0.18, 0.25 * vol);
      break;
    case "menuHover":
      tone(c, t, 1250, 1050, 0.035, 0.1 * vol);
      break;
    case "hover":
      tone(c, t, 1500, 1400, 0.03, 0.08 * vol);
      break;
    case "slideChange": // a card flipped over
      hiss(c, t, 0.14, 0.22 * vol, "bandpass", 2600, 900, 1.2);
      tone(c, t, 320, 170, 0.12, 0.15 * vol, "triangle");
      break;
    case "tapeCut": // scissors: one sharp snip
      hiss(c, t, 0.09, 0.4 * vol, "highpass", 3500, 3500);
      tone(c, t, 1900, 420, 0.08, 0.2 * vol, "square");
      break;
    case "tapePress": // a hand pressing tape flat
      hiss(c, t, 0.14, 0.3 * vol, "lowpass", 900, 200);
      tone(c, t, 150, 70, 0.15, 0.3 * vol);
      break;
    case "ballHit":
      tone(c, t, 240, 110, 0.12, 0.3 * vol, "triangle");
      hiss(c, t, 0.05, 0.12 * vol, "lowpass", 1500, 400);
      break;
  }
}

/** A looping sound whose loudness and pitch follow something (the tape stretching as it is pulled). */
export function createLoop() {
  let src: AudioBufferSourceNode | null = null;
  let gain: GainNode | null = null;
  let filter: BiquadFilterNode | null = null;
  const start = () => {
    const c = ensure();
    if (!c || !master || !noise) return false;
    src = c.createBufferSource();
    src.buffer = noise;
    src.loop = true;
    filter = c.createBiquadFilter();
    filter.type = "bandpass";
    filter.Q.value = 2.2;
    filter.frequency.value = 1400;
    gain = c.createGain();
    gain.gain.value = 0;
    src.connect(filter).connect(gain).connect(master);
    src.start();
    return true;
  };
  return {
    /** level 0..1, rate around 0.85..1.25 */
    set(level: number, rate = 1) {
      if (!on || level <= 0.001) {
        if (gain && ctx) gain.gain.setTargetAtTime(0, ctx.currentTime, 0.06);
        return;
      }
      if (!src && !start()) return;
      if (ctx && gain && filter) {
        gain.gain.setTargetAtTime(level * 0.35, ctx.currentTime, 0.06);
        filter.frequency.setTargetAtTime(1400 * rate, ctx.currentTime, 0.06);
      }
    },
    stop() {
      try {
        src?.stop();
      } catch {
        /* already stopped */
      }
      src?.disconnect();
      gain?.disconnect();
      src = gain = null;
      filter = null;
    },
  };
}
