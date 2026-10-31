/** A round badge with a sentence running around its edge that turns slowly (stopped for reduced motion by the global rule). */
export function SpinBadge({ text, className }: { text: string; className?: string }) {
  return (
    <div aria-hidden className={className}>
      <svg viewBox="0 0 200 200" className="h-full w-full animate-[spin_22s_linear_infinite]">
        <defs>
          <path id="spin-badge-ring" d="M 100 100 m -72 0 a 72 72 0 1 1 144 0 a 72 72 0 1 1 -144 0" />
        </defs>
        <circle cx="100" cy="100" r="96" className="fill-forest" />
        <text className="fill-lime font-display uppercase" style={{ fontSize: 21, letterSpacing: "0.12em" }}>
          <textPath href="#spin-badge-ring" textLength="448" lengthAdjust="spacing">{`${text} • `}</textPath>
        </text>
      </svg>
      <span className="absolute inset-0 grid place-items-center font-display text-ui-2xl text-lime">&#8599;</span>
    </div>
  );
}
