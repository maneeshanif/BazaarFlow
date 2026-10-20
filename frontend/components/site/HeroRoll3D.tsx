"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import { useMemo, useRef, useSyncExternalStore, type ReactNode } from "react";
import type { Group } from "three";

/** Reads an identity colour from the token layer, so the 3D scene never carries its own colour values. */
function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "white";
}

type RollProps = { body: string; hole: string; label: string; position: [number, number, number]; scale?: number; spin?: number };

function Roll({ body, hole, label, position, scale = 1, spin = 0.25 }: RollProps) {
  const ref = useRef<Group>(null);
  useFrame((state, dt) => {
    if (!ref.current) return;
    ref.current.rotation.y += dt * spin;
    // lean toward the pointer a little
    ref.current.rotation.x += (state.pointer.y * 0.5 - ref.current.rotation.x) * 0.05;
    ref.current.rotation.z += (-state.pointer.x * 0.4 - ref.current.rotation.z) * 0.05;
  });
  return (
    <Float speed={1.6} rotationIntensity={0.15} floatIntensity={0.9}>
      <group ref={ref} position={position} scale={scale} name={label}>
        <mesh>
          <torusGeometry args={[1.15, 0.55, 40, 72]} />
          <meshStandardMaterial color={body} roughness={0.55} metalness={0.05} />
        </mesh>
        <mesh>
          <torusGeometry args={[0.62, 0.08, 20, 56]} />
          <meshStandardMaterial color={hole} roughness={0.7} />
        </mesh>
      </group>
    </Float>
  );
}

function Scene() {
  const colors = useMemo(
    () => ({ lime: token("--color-lime"), forest: token("--color-forest"), coral: token("--color-coral"), sky: token("--color-sky"), sunny: token("--color-sunny") }),
    [],
  );
  return (
    <>
      <ambientLight intensity={1.1} />
      <directionalLight position={[3, 4, 5]} intensity={2.2} />
      <Roll body={colors.forest} hole={colors.lime} label="main" position={[0, 0, 0]} scale={0.95} />
      <Roll body={colors.coral} hole={colors.forest} label="coral" position={[-2.9, -1.1, -1]} scale={0.55} spin={0.45} />
      <Roll body={colors.sky} hole={colors.forest} label="sky" position={[2.9, 1.3, -1]} scale={0.5} spin={-0.4} />
      <Roll body={colors.sunny} hole={colors.forest} label="sunny" position={[2.4, -1.6, 0.4]} scale={0.38} spin={0.6} />
    </>
  );
}

let webgl: boolean | undefined;
/** Probed once: React reads the snapshot several times and each probe would open a WebGL context. */
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
 * The hero object: a few paper rolls that turn and lean toward the pointer. Mounted only on the client, only with
 * WebGL and only when motion is allowed, so `fallback` (the plain picture) is what everyone else sees.
 */
export default function HeroRoll3D({ fallback }: { fallback: ReactNode }) {
  // false on the server and during hydration, then the real answer: no state set inside an effect
  const ok = useSyncExternalStore(
    () => () => {},
    () => hasWebGL() && !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false,
  );
  if (!ok) return <>{fallback}</>;
  return (
    <div className="h-full w-full" aria-hidden>
      <Canvas camera={{ position: [0, 0, 9.5], fov: 40 }} dpr={[1, 1.75]} gl={{ alpha: true, antialias: true }}>
        <Scene />
      </Canvas>
    </div>
  );
}
