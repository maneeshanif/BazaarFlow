"use client";

import { Volume2, VolumeX } from "lucide-react";
import { useEffect, useState } from "react";
import { isSoundOn, onSoundChange, play, setSoundOn } from "@/components/site/sound";

/**
 * The sound switch, fixed at the bottom right (off until pressed, as on the reference). It also gives every other click on
 * the page its small click sound once sound is on, except clicks on the menu tab and on this switch, which have their own.
 */
export function SoundToggle() {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const off = onSoundChange(setOn);
    const click = (e: MouseEvent) => {
      if (e.target instanceof Element && e.target.closest("[data-own-sound]")) return;
      play("click");
    };
    document.addEventListener("click", click);
    return () => {
      off();
      document.removeEventListener("click", click);
    };
  }, []);
  return (
    <button
      type="button"
      data-own-sound
      aria-label="Sound"
      aria-pressed={on}
      onClick={() => setSoundOn(!isSoundOn())}
      className="fixed bottom-4 right-4 z-[130] flex h-10 w-[4.5rem] items-center rounded-pill bg-cream/90 px-1 text-forest-ink shadow-popover transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus"
    >
      <span aria-hidden className={`grid h-8 w-8 place-items-center rounded-full bg-lime transition-transform duration-300 [transition-timing-function:var(--ease-bounce)] ${on ? "translate-x-8" : ""}`}>
        {on ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
      </span>
    </button>
  );
}
