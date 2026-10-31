"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import { useMemo, useRef, useSyncExternalStore, type ReactNode } from "react";
import type { Group } from "three";

/** Reads an identity colour from the token layer, so the 3D scene never carries its own colour values. */
function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "white";
}

type Colors = Record<"kraft" | "cream" | "coral" | "forest" | "sunny" | "lime", string>;

/** Wraps a piece so it floats a little and leans toward the pointer. */
function Piece({ children, position, spin = 0, lean = 1 }: { children: ReactNode; position: [number, number, number]; spin?: number; lean?: number }) {
  const ref = useRef<Group>(null);
  useFrame((state, dt) => {
    const g = ref.current;
    if (!g) return;
    g.rotation.y += dt * spin;
    g.rotation.x += (state.pointer.y * 0.35 * lean - g.rotation.x) * 0.05;
    g.rotation.z += (-state.pointer.x * 0.25 * lean - g.rotation.z) * 0.05;
  });
  return (
    <Float speed={1.4} rotationIntensity={0.1} floatIntensity={0.7}>
      <group ref={ref} position={position}>
        {children}
      </group>
    </Float>
  );
}

/** A delivery parcel: a kraft box with a band of tape over the lid and down both sides. */
function Parcel({ size, body, tape }: { size: [number, number, number]; body: string; tape: string }) {
  const [w, h, d] = size;
  return (
    <group>
      <mesh>
        <boxGeometry args={size} />
        <meshStandardMaterial color={body} roughness={0.85} />
      </mesh>
      <mesh>
        <boxGeometry args={[w * 0.16, h * 1.02, d * 1.02]} />
        <meshStandardMaterial color={tape} roughness={0.35} />
      </mesh>
    </group>
  );
}

/** A tiffin carrier: a round tin with a lid and a small carry handle. */
function Tiffin({ body, lid }: { body: string; lid: string }) {
  return (
    <group>
      <mesh>
        <cylinderGeometry args={[0.62, 0.66, 1.25, 40]} />
        <meshStandardMaterial color={body} roughness={0.45} metalness={0.2} />
      </mesh>
      <mesh position={[0, 0.7, 0]}>
        <cylinderGeometry args={[0.68, 0.68, 0.16, 40]} />
        <meshStandardMaterial color={lid} roughness={0.5} />
      </mesh>
      <mesh position={[0, 0.95, 0]} rotation={[0, 0, 0]}>
        <torusGeometry args={[0.3, 0.05, 16, 40, Math.PI]} />
        <meshStandardMaterial color={lid} roughness={0.5} />
      </mesh>
    </group>
  );
}

/** A small roll of tape, to echo the taped details of the page. */
function TapeRoll({ body, hole }: { body: string; hole: string }) {
  return (
    <group rotation={[Math.PI / 2.4, 0, 0]}>
      <mesh>
        <torusGeometry args={[0.5, 0.26, 28, 56]} />
        <meshStandardMaterial color={body} roughness={0.5} />
      </mesh>
      <mesh>
        <torusGeometry args={[0.27, 0.03, 12, 40]} />
        <meshStandardMaterial color={hole} roughness={0.7} />
      </mesh>
    </group>
  );
}

function Scene() {
  const c = useMemo<Colors>(
    () => ({ kraft: token("--color-kraft"), cream: token("--color-cream"), coral: token("--color-coral"), forest: token("--color-forest"), sunny: token("--color-sunny"), lime: token("--color-lime") }),
    [],
  );
  return (
    <>
      <ambientLight intensity={1.15} />
      <directionalLight position={[3, 4, 5]} intensity={2.2} />
      <Piece position={[0, -0.2, 0]} spin={0.12} lean={0.8}>
        <group rotation={[0.1, 0.55, 0]}>
          <Parcel size={[2.3, 1.5, 1.7]} body={c.kraft} tape={c.cream} />
        </group>
      </Piece>
      <Piece position={[-2.4, -0.65, 0.5]} spin={-0.2}>
        <group rotation={[0.05, -0.4, 0.04]}>
          <Parcel size={[1.35, 0.95, 1.1]} body={c.kraft} tape={c.sunny} />
        </group>
      </Piece>
      <Piece position={[2.45, -0.45, 0.4]} spin={0.3}>
        <Tiffin body={c.coral} lid={c.forest} />
      </Piece>
      <Piece position={[1.0, 1.25, -0.6]} spin={0.5}>
        <TapeRoll body={c.sunny} hole={c.forest} />
      </Piece>
    </>
  );
}

let webgl: boolean | undefined;
/** Probed once: React reads the snapshot several times and each probe would open a WebGL context. */
function hasWebGL(): boolean {
  if (webgl === undefined) {
    try {
      const canvas = document.createElement("canvas");
      webgl = !!(canvas.getContext("webgl2") || canvas.getContext("webgl"));
    } catch {
      webgl = false;
    }
  }
  return webgl;
}

/**
 * The hero object: a small stack of delivery parcels, a tiffin carrier and a roll of tape that float and lean toward the
 * pointer. Mounted only on the client, only with WebGL and only when motion is allowed, so `fallback` (the plain
 * picture) is what everyone else sees.
 */
export default function HeroParcels3D({ fallback }: { fallback: ReactNode }) {
  // false on the server and during hydration, then the real answer: no state set inside an effect
  const ok = useSyncExternalStore(
    () => () => {},
    () => hasWebGL() && !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false,
  );
  if (!ok) return <>{fallback}</>;
  return (
    <div className="h-full w-full" aria-hidden>
      <Canvas camera={{ position: [0, 0.4, 9.5], fov: 40 }} dpr={[1, 1.75]} gl={{ alpha: true, antialias: true }}>
        <Scene />
      </Canvas>
    </div>
  );
}
