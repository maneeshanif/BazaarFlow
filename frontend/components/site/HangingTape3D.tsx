"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { gsap } from "gsap";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import * as THREE from "three";
import { motionAllowed, register } from "@/components/site/motion";
import { createLoop, play } from "@/components/site/sound";

/** Reads an identity colour from the token layer, so the 3D scene never carries its own colour values. */
function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "white";
}

const H = 1500; // canvas height in px; the camera is orthographic, so one world unit is one screen pixel
const W = 150; // tape width
const R = 62; // roll radius
const TOP = 100; // how far the roll's centre is below the canvas top
const CY = H / 2 - TOP; // roll centre in world units (y up)
const MAX = H - TOP - R - 12; // longest the strip can be
const SEGMENTS = 96;

/** What the scroll controller tells the scene, read every frame. */
type Pose = { angle: number; len: number; cutOff: number; cut: number; home: number };

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const smooth = (v: number) => v * v * (3 - 2 * v);
/** A soft minimum: follows the smaller of a and b, blending over `r` where they cross. */
function softMin(a: number, b: number, r: number) {
  const n = clamp01(0.5 + (0.5 * (b - a)) / r);
  return b * (1 - n) + a * n - r * n * (1 - n);
}
const docTop = (el: Element) => el.getBoundingClientRect().top + window.scrollY;

/**
 * A roll of clear tape on its side with a strip leaving its underside. The strip's length comes from the scroll controller
 * and the roll turns by exactly the length paid out divided by its radius, so the two stay locked like a real roll being
 * pulled. The loose end curls and drifts; once the strip is cut it lies flat on the card and the roll swings back to rest.
 */
function Scene({ pose }: { pose: Pose }) {
  const turn = useRef<THREE.Group>(null);
  const tilt = useRef<THREE.Group>(null);
  const strip = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshPhysicalMaterial>(null);
  const colors = useMemo(() => ({ cream: token("--color-cream"), kraft: token("--color-kraft"), sunny: token("--color-sunny") }), []);
  const base = useMemo(() => {
    const g = new THREE.PlaneGeometry(W, MAX, 1, SEGMENTS);
    g.translate(0, -MAX / 2, 0);
    return g;
  }, []);
  const rest = useMemo(() => Float32Array.from(base.attributes.position.array as Float32Array), [base]);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    const { len, cutOff, home, angle } = pose;
    if (tilt.current) {
      // the roll starts seen from above and to the side (35 deg) and turns to face the page (90 deg) as it is pulled
      tilt.current.rotation.y = 0.52 - ((angle - 35) / 55) * 0.52;
      tilt.current.rotation.x = 0.2 - ((angle - 35) / 55) * 0.12;
      tilt.current.rotation.z = Math.sin(t * 0.9) * 0.025 * home;
    }
    if (turn.current) turn.current.rotation.x = -len / R; // unrolling: arc length = angle x radius
    const mesh = strip.current;
    if (!mesh) return;
    const loose = 1 - home; // a stuck piece lies flat; a hanging one moves
    const pos = mesh.geometry.attributes.position as THREE.BufferAttribute;
    const span = Math.max(len - cutOff, 0);
    for (let i = 0; i < pos.count; i += 1) {
      const u = -rest[i * 3 + 1] / MAX; // 0 at the roll end of the strip, 1 at the free end
      const hang = (len / MAX) * u;
      pos.setY(i, -(cutOff + u * span));
      pos.setZ(i, loose * (Math.sin(t * 1.1 + hang * 5) * 5 * hang * hang + 26 * hang ** 5 + 3 * hang) + 0.6);
      pos.setX(i, rest[i * 3] + loose * Math.sin(t * 0.8 + hang * 3) * 7 * hang * hang);
    }
    pos.needsUpdate = true;
    mesh.geometry.computeVertexNormals();
    mesh.visible = span > 1;
    if (mat.current) mat.current.opacity = 0.34 + 0.18 * home;
  });

  return (
    <>
      <ambientLight intensity={1.1} />
      <directionalLight position={[240, 320, 420]} intensity={2.4} />
      <directionalLight position={[-300, -100, 200]} intensity={0.6} />
      <group ref={tilt} position={[0, CY, 0]}>
        <group ref={turn}>
          <group rotation={[0, 0, Math.PI / 2]}>
            {/* the wound tape: clear, so the card can be seen through it */}
            <mesh>
              <cylinderGeometry args={[R, R, W, 72, 1]} />
              <meshPhysicalMaterial color={colors.cream} transparent opacity={0.62} roughness={0.12} clearcoat={1} clearcoatRoughness={0.1} />
            </mesh>
            {/* the cardboard core, a little proud of the tape on both sides */}
            <mesh>
              <cylinderGeometry args={[R * 0.5, R * 0.5, W + 6, 48, 1]} />
              <meshStandardMaterial color={colors.kraft} roughness={0.9} />
            </mesh>
            {/* a printed band that turns with the roll, so the turning can be seen */}
            <mesh>
              <cylinderGeometry args={[R + 0.6, R + 0.6, W * 0.42, 72, 1, true, 0.4, 1.7]} />
              <meshStandardMaterial color={colors.sunny} roughness={0.5} side={THREE.DoubleSide} transparent opacity={0.92} />
            </mesh>
          </group>
        </group>
        <mesh ref={strip} geometry={base} position={[0, -R + 1, 0]} visible={false}>
          <meshPhysicalMaterial ref={mat} color={colors.cream} transparent opacity={0.34} roughness={0.08} clearcoat={1} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
      </group>
    </>
  );
}

let webgl: boolean | undefined;
function hasWebGL(): boolean {
  if (webgl === undefined) {
    try {
      const c = document.createElement("canvas");
      webgl = !!(c.getContext("webgl2") || c.getContext("webgl"));
    } catch {
      webgl = false;
    }
  }
  return webgl;
}

/**
 * The reference's loose roll of tape, rebuilt as a real 3D roll. It drops in, then scrolling pulls the strip out of it and down
 * over the card (it never winds back in). When the strip reaches the bottom of the card it is cut with a snip: the roll
 * swings back to rest and the cut piece stays stuck flat on the card. A roll with a pulled strip is decoration only, so
 * without WebGL, or with reduced motion, nothing is drawn.
 */
export default function HangingTape3D() {
  const ok = useSyncExternalStore(
    () => () => {},
    () => hasWebGL() && motionAllowed(),
    () => false,
  );
  const host = useRef<HTMLDivElement | null>(null);
  const inner = useRef<HTMLDivElement | null>(null);
  const [pose] = useState<Pose>(() => ({ angle: 35, len: 0, cutOff: 0, cut: 0, home: 0 }));
  const [live, setLive] = useState(false);
  const dropped = useRef(false);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setLive(e.isIntersecting), { rootMargin: "50% 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, [ok]);

  // it drops in the first time it is near the screen (the reference: 13vw of travel, a small overshoot, 1.3 s)
  useEffect(() => {
    if (!live || dropped.current || !inner.current) return;
    dropped.current = true;
    gsap.fromTo(inner.current, { y: window.innerWidth * 0.13, scale: 0.82, transformOrigin: "50% 0%" }, { y: 0, scale: 1, duration: 1.3, ease: "back.out(1.5)" });
  }, [live]);

  useLayoutEffect(() => {
    const el = host.current;
    if (!el || !ok) return;
    register();
    const loop = createLoop();
    let phase: "scrub" | "finale" | "done" = "scrub";
    let pulled = 0; // the furthest the page has been scrolled past the start: it only ever grows
    let strip = 0; // the longest the strip has been: it only ever grows
    let last = -1;
    let tl: gsap.core.Timeline | null = null;
    const state = { cut: 0, home: 0 };

    const geometry = () => {
      const top = docTop(el);
      const m = top + TOP; // roll centre, document coordinates
      const card = document.querySelector("[data-tape-card]");
      const cardTop = card ? docTop(card) : top + 700;
      const cardBottom = card ? cardTop + card.clientHeight : top + 1300;
      const iw = window.innerWidth;
      return {
        m,
        start: m - window.innerHeight / 2 - 200,
        reach: Math.min(cardBottom + 0.0625 * iw - m, H - TOP - R - 20), // how far the strip can go: just past the card's bottom
        cutAt: Math.max(cardTop - 0.04167 * iw - m, 0), // where it is cut: just above the card
      };
    };

    const tick = (_time: number, deltaMs: number) => {
      if (phase === "done") return;
      const g = geometry();
      if (phase === "finale") {
        pose.angle = 90 - 55 * state.home;
        pose.cutOff = state.cut * g.cutAt;
        pose.cut = state.cut;
        pose.home = state.home;
        return;
      }
      const sy = window.scrollY;
      pulled = Math.max(pulled, sy - g.start, 0);
      const x = Math.max(pulled - 420, 0);
      const target = sy + window.innerHeight - g.m - 160; // the free end follows the bottom of the screen
      strip = Math.max(strip, softMin(softMin((4 * x * x) / (x + 250), target, 250), g.reach, 250), 0);
      pose.angle = 35 + 55 * smooth(clamp01(pulled / 550));
      pose.len = Math.min(strip, MAX);
      // the stretching sound follows how fast the strip is being pulled
      const speed = last < 0 || deltaMs <= 0 ? 0 : (strip - last) / deltaMs;
      last = strip;
      const intensity = clamp01(speed / 2);
      loop.set(0.8 * intensity, 0.85 + 0.4 * intensity);
      if (g.reach > 0 && strip >= g.reach - 4) {
        phase = "finale";
        loop.set(0);
        play("tapeCut");
        // already far down the page when it loads: skip the show and just lay it flat
        if (pulled > 2600) {
          state.cut = 1;
          state.home = 1;
          phase = "done";
          pose.angle = 35;
          pose.cutOff = g.cutAt;
          pose.cut = 1;
          pose.home = 1;
          return;
        }
        tl = gsap
          .timeline({ onComplete: () => {
            phase = "done";
          } })
          .to(state, { cut: 1, duration: 0.7, ease: "power2.in" }, 0)
          .to(state, { home: 1, duration: 1, ease: "power3.inOut" }, 0.35);
      }
    };
    gsap.ticker.add(tick);
    return () => {
      gsap.ticker.remove(tick);
      tl?.kill();
      loop.stop();
    };
  }, [ok, pose]);

  if (!ok) return null;
  return (
    <div ref={host} aria-hidden className="pointer-events-none absolute left-[36%] top-4 z-30 hidden w-[360px] -translate-x-1/2 md:block" style={{ height: H }}>
      <div ref={inner} className="h-full w-full">
        <Canvas orthographic camera={{ zoom: 1, position: [0, 0, 600], near: 1, far: 2000 }} dpr={[1, 2]} gl={{ alpha: true, antialias: true }} frameloop={live ? "always" : "never"}>
          <Scene pose={pose} />
        </Canvas>
      </div>
    </div>
  );
}
