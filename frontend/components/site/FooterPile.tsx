"use client";

import Link from "next/link";
import { useLayoutEffect, useRef } from "react";
import { BrandImage } from "@/components/brand/BrandImage";
import type { Tone } from "@/components/brand/tones";
import { motionAllowed } from "@/components/site/motion";

type Item = { key: string; size: string; x: number; kind: "disc"; file: string; label: string; tone: Tone } | { key: string; size: string; x: number; kind: "link"; href: string; label: string };

/** x is where the item first drops in, as a share of the width. */
const ITEMS: Item[] = [
  { key: "khata", kind: "disc", file: "disc-khata.png", label: "Khata", tone: "indigo", size: "h-36 w-36 lg:h-52 lg:w-52", x: 0.14 },
  { key: "stock", kind: "disc", file: "disc-stock.png", label: "Stock", tone: "sunny", size: "h-32 w-32 lg:h-48 lg:w-48", x: 0.3 },
  { key: "sales", kind: "disc", file: "disc-sales.png", label: "Sales", tone: "coral", size: "h-36 w-36 lg:h-52 lg:w-52", x: 0.62 },
  { key: "money", kind: "disc", file: "disc-money.png", label: "Money", tone: "sky", size: "h-32 w-32 lg:h-48 lg:w-48", x: 0.8 },
  { key: "demo", kind: "link", href: "/demo", label: "Demo", size: "h-24 w-24 lg:h-32 lg:w-32", x: 0.46 },
  { key: "sign-in", kind: "link", href: "/sign-in", label: "Sign in", size: "h-24 w-24 lg:h-32 lg:w-32", x: 0.92 },
];

type Body = { el: HTMLElement; r: number; x: number; y: number; vx: number; vy: number; a: number; va: number };

/**
 * The piled-up footer of the reference, as a small physics toy. The round things fall in the first time the footer is seen,
 * pile up on its floor, bump into each other and the walls, can be picked up and thrown, and get nudged by the pointer going
 * by. The simulation (gravity, bounce, circle collisions) runs only while the footer is on screen. With reduced motion, or on
 * a phone, there is no simulation: they are laid out as a plain row.
 */
export function FooterPile() {
  const root = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    const host = root.current;
    if (!host || !window.matchMedia("(min-width: 768px)").matches) return;
    const nodes = [...host.querySelectorAll<HTMLElement>("[data-body]")];
    let W = host.clientWidth;
    let H = host.clientHeight;
    const bodies: Body[] = nodes.map((el, i) => {
      const r = el.offsetWidth / 2;
      return { el, r, x: ITEMS[i].x * W, y: -r - i * 140, vx: (Math.random() - 0.5) * 3, vy: 0, a: (Math.random() - 0.5) * 40, va: (Math.random() - 0.5) * 2 };
    });
    if (!motionAllowed()) {
      // no simulation: they simply lie on the floor of the footer
      for (const b of bodies) b.el.style.transform = `translate3d(${(b.x - b.r).toFixed(0)}px,${(H - b.r * 2).toFixed(0)}px,0)`;
      return;
    }
    host.dataset.live = "1";

    const G = 0.55; // gravity per frame at 60 fps
    const BOUNCE = 0.5;
    const pointer = { x: -999, y: -999, px: -999, py: -999, vx: 0, vy: 0 };
    let held: { b: Body; dx: number; dy: number; moved: number; sx: number; sy: number } | null = null;
    let raf = 0;
    let last = 0;
    let visible = false;

    const step = (t: number) => {
      raf = requestAnimationFrame(step);
      const dt = Math.min(2, last ? (t - last) / 16.667 : 1);
      last = t;
      for (const b of bodies) {
        if (held?.b === b) continue;
        b.vy += G * dt;
        b.vx *= 0.995;
        b.x += b.vx * dt;
        b.y += b.vy * dt;
        b.a += b.va * dt;
        b.va *= 0.99;
        // the pointer going by gives a push
        const dx = b.x - pointer.x;
        const dy = b.y - pointer.y;
        const d = Math.hypot(dx, dy);
        const speed = Math.hypot(pointer.vx, pointer.vy);
        if (!held && d < b.r + 30 && speed > 1.5) {
          b.vx += Math.max(-14, Math.min(14, pointer.vx * 0.22));
          b.vy += Math.max(-14, Math.min(14, pointer.vy * 0.22)) - 0.3;
          b.va += pointer.vx * 0.02;
        }
        // walls and floor
        if (b.x < b.r) {
          b.x = b.r;
          b.vx = Math.abs(b.vx) * BOUNCE;
        } else if (b.x > W - b.r) {
          b.x = W - b.r;
          b.vx = -Math.abs(b.vx) * BOUNCE;
        }
        if (b.y < b.r && b.vy < 0 && b.y > -H) {
          b.y = b.r;
          b.vy = Math.abs(b.vy) * BOUNCE;
        }
        if (b.y > H - b.r) {
          b.y = H - b.r;
          b.vy = -Math.abs(b.vy) * BOUNCE;
          if (Math.abs(b.vy) < 1) b.vy = 0;
          b.vx *= 0.96;
          b.va = b.vx / b.r * 57; // rolling
        }
      }
      // circles push each other apart and swap a little speed
      for (let i = 0; i < bodies.length; i += 1) {
        for (let j = i + 1; j < bodies.length; j += 1) {
          const p = bodies[i];
          const q = bodies[j];
          const dx = q.x - p.x;
          const dy = q.y - p.y;
          const d = Math.hypot(dx, dy) || 0.001;
          const min = p.r + q.r;
          if (d >= min) continue;
          const nx = dx / d;
          const ny = dy / d;
          const push = min - d;
          const pm = held?.b === p ? 0 : 1;
          const qm = held?.b === q ? 0 : 1;
          const total = pm + qm || 1;
          p.x -= nx * push * (pm / total);
          p.y -= ny * push * (pm / total);
          q.x += nx * push * (qm / total);
          q.y += ny * push * (qm / total);
          const rel = (q.vx - p.vx) * nx + (q.vy - p.vy) * ny;
          if (rel < 0) {
            const j2 = -(1 + BOUNCE) * rel * 0.5;
            if (pm) {
              p.vx -= j2 * nx;
              p.vy -= j2 * ny;
            }
            if (qm) {
              q.vx += j2 * nx;
              q.vy += j2 * ny;
            }
          }
        }
      }
      if (held) {
        const hb = held.b;
        const tx = pointer.x - held.dx;
        const ty = pointer.y - held.dy;
        hb.vx = (tx - hb.x) * 0.6;
        hb.vy = (ty - hb.y) * 0.6;
        hb.x += hb.vx;
        hb.y += hb.vy;
        hb.x = Math.max(hb.r, Math.min(W - hb.r, hb.x));
        hb.y = Math.max(hb.r, Math.min(H - hb.r, hb.y));
      }
      pointer.vx *= 0.8;
      pointer.vy *= 0.8;
      for (const b of bodies) b.el.style.transform = `translate3d(${(b.x - b.r).toFixed(1)}px,${(b.y - b.r).toFixed(1)}px,0) rotate(${b.a.toFixed(1)}deg)`;
    };

    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      if (visible && !raf) {
        last = 0;
        raf = requestAnimationFrame(step);
      } else if (!visible && raf) {
        cancelAnimationFrame(raf);
        raf = 0;
      }
    });
    io.observe(host);

    const local = (e: PointerEvent) => {
      const r = host.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    };
    const onMove = (e: PointerEvent) => {
      const p = local(e);
      pointer.vx = p.x - (pointer.px === -999 ? p.x : pointer.px);
      pointer.vy = p.y - (pointer.py === -999 ? p.y : pointer.py);
      pointer.px = pointer.x = p.x;
      pointer.py = pointer.y = p.y;
      if (held) held.moved = Math.max(held.moved, Math.hypot(p.x - held.sx, p.y - held.sy));
    };
    const onDown = (e: PointerEvent) => {
      const p = local(e);
      const hit = bodies.find((b) => b.el.contains(e.target as Node));
      if (!hit) return;
      pointer.x = pointer.px = p.x;
      pointer.y = pointer.py = p.y;
      held = { b: hit, dx: p.x - hit.x, dy: p.y - hit.y, moved: 0, sx: p.x, sy: p.y };
      host.setPointerCapture?.(e.pointerId);
      hit.el.style.zIndex = "5";
    };
    const onUp = () => {
      if (!held) return;
      // thrown with the speed the pointer had
      held.b.vx = Math.max(-22, Math.min(22, pointer.vx * 0.9));
      held.b.vy = Math.max(-22, Math.min(22, pointer.vy * 0.9));
      held.b.va += held.b.vx * 0.6;
      held.b.el.style.zIndex = "";
      held = null;
    };
    // a link that was dragged is not also followed
    const onClick = (e: MouseEvent) => {
      if (host.dataset.dragged === "1") {
        e.preventDefault();
        e.stopPropagation();
      }
      host.dataset.dragged = "0";
    };
    const onDownMark = () => (host.dataset.dragged = "0");
    const onMoveMark = () => {
      if (held && held.moved > 6) host.dataset.dragged = "1";
    };
    const onResize = () => {
      W = host.clientWidth;
      H = host.clientHeight;
    };
    host.addEventListener("pointerdown", onDownMark, true);
    host.addEventListener("pointermove", onMoveMark, true);
    host.addEventListener("click", onClick, true);
    window.addEventListener("pointermove", onMove);
    host.addEventListener("pointerdown", onDown);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      host.removeEventListener("pointerdown", onDownMark, true);
      host.removeEventListener("pointermove", onMoveMark, true);
      host.removeEventListener("click", onClick, true);
      window.removeEventListener("pointermove", onMove);
      host.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
      window.removeEventListener("resize", onResize);
      delete host.dataset.live;
      for (const b of bodies) {
        b.el.style.transform = "";
        b.el.style.zIndex = "";
      }
    };
  }, []);

  return (
    <div ref={root} className="group/pile pointer-events-none absolute inset-0 hidden md:block">
      {ITEMS.map((it) =>
        it.kind === "disc" ? (
          <div
            key={it.key}
            data-body
            className={`pointer-events-auto absolute left-0 top-0 cursor-grab touch-none select-none overflow-hidden rounded-full shadow-card active:cursor-grabbing [&_img]:pointer-events-none ${it.size}`}
          >
            <BrandImage file={it.file} alt="" decorative label={it.label} tone={it.tone} />
          </div>
        ) : (
          <Link
            key={it.key}
            href={it.href}
            data-body
            draggable={false}
            className={`pointer-events-auto absolute left-0 top-0 grid cursor-grab touch-none select-none place-items-center rounded-full bg-lime font-display text-ui-lg uppercase text-forest-ink active:cursor-grabbing focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-cream ${it.size}`}
          >
            {it.label}
          </Link>
        ),
      )}
    </div>
  );
}
