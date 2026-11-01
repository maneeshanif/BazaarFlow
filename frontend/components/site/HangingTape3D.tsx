"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { gsap } from "gsap";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import * as THREE from "three";
import { motionAllowed, register } from "@/components/site/motion";

/** Reads an identity colour from the token layer, so the 3D scene never carries its own colour values. */
function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "white";
}

const H = 1100; // canvas height in px; the camera is orthographic, so one world unit is one screen pixel
const W = 150; // tape width
const R = 62; // roll radius
const MAX = 980; // longest the strip gets
const SEGMENTS = 64;
const CY = H / 2 - 100; // roll centre

type Prog = { v: number };

/**
 * A roll of clear tape on its side with a strip leaving its underside. The strip's length is the scroll progress and the roll
 * turns by exactly the length paid out divided by its radius, so the two stay locked together like a real roll being pulled.
 * The free end curls and drifts a little in the air, as a loose strip does.
 */
function Scene({ prog }: { prog: Prog }) {
  const roll = useRef<THREE.Group>(null);
  const strip = useRef<THREE.Mesh>(null);
  const colors = useMemo(() => ({ cream: token("--color-cream"), kraft: token("--color-kraft"), sunny: token("--color-sunny"), ink: token("--color-forest-ink") }), []);
  const base = useMemo(() => {
    const g = new THREE.PlaneGeometry(W, MAX, 1, SEGMENTS);
    g.translate(0, -MAX / 2, 0);
    return g;
  }, []);
  const rest = useMemo(() => Float32Array.from(base.attributes.position.array as Float32Array), [base]);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    const p = prog.v;
    const len = p * MAX;
    if (roll.current) {
      roll.current.rotation.x = -len / R; // unrolling: arc length = angle x radius
      roll.current.position.y = Math.sin(t * 1.4) * 1.6 * (1 - p * 0.6);
    }
    const mesh = strip.current;
    if (!mesh) return;
    const pos = mesh.geometry.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i += 1) {
      const u = -rest[i * 3 + 1] / MAX; // 0 at the roll, 1 at the free end
      const hang = u * p;
      pos.setY(i, -u * len);
      // the strip is stiff near the roll and loose toward the end: it bows, then the tip lifts and swings
      pos.setZ(i, Math.sin(t * 1.1 + hang * 5) * 5 * hang * hang + 26 * hang ** 5 + 3 * hang);
      pos.setX(i, rest[i * 3] + Math.sin(t * 0.8 + hang * 3) * 7 * hang * hang);
    }
    pos.needsUpdate = true;
    mesh.geometry.computeVertexNormals();
    mesh.visible = len > 1;
  });

  return (
    <>
      <ambientLight intensity={1.1} />
      <directionalLight position={[240, 320, 420]} intensity={2.4} />
      <directionalLight position={[-300, -100, 200]} intensity={0.6} />
      <group rotation={[0.18, 0.5, 0]} position={[0, CY, 0]}>
        <group ref={roll}>
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
          <meshPhysicalMaterial color={colors.cream} transparent opacity={0.34} roughness={0.08} clearcoat={1} side={THREE.DoubleSide} depthWrite={false} />
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
 * The reference's loose roll of tape above the board, rebuilt as a real 3D roll. Scrolling pulls the strip out of it; scrolling
 * back winds it in. It sits a little left of the middle and reaches down the board. Without WebGL or with reduced motion
 * nothing is drawn: it is decoration only.
 */
export default function HangingTape3D() {
  const ok = useSyncExternalStore(
    () => () => {},
    () => hasWebGL() && motionAllowed(),
    () => false,
  );
  const host = useRef<HTMLDivElement | null>(null);
  const [prog] = useState<Prog>(() => ({ v: 0 }));
  const [live, setLive] = useState(false);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setLive(e.isIntersecting));
    io.observe(el);
    return () => io.disconnect();
  }, [ok]);

  useLayoutEffect(() => {
    const el = host.current;
    if (!el || !ok) return;
    register();
    const ctx = gsap.context(() => {
      gsap.to(prog, { v: 1, ease: "none", scrollTrigger: { trigger: el.parentElement, start: "top 62%", end: "top -28%", scrub: 0.9 } });
    }, el);
    return () => ctx.revert();
  }, [ok, prog]);

  if (!ok) return null;
  return (
    <div ref={host} aria-hidden className="pointer-events-none absolute left-[36%] top-8 z-30 hidden w-[360px] -translate-x-1/2 md:block" style={{ height: H }}>
      <Canvas orthographic camera={{ zoom: 1, position: [0, 0, 600], near: 1, far: 2000 }} dpr={[1, 2]} gl={{ alpha: true, antialias: true }} frameloop={live ? "always" : "never"}>
        <Scene prog={prog} />
      </Canvas>
    </div>
  );
}
