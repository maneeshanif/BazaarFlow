import type { ReactNode } from "react";
import { Chip } from "@/components/brand/Chip";
import { CutTitle } from "@/components/site/CutTitle";
import { WordText } from "@/components/site/text";

/**
 * The top of every public page after the home page: crumpled lime paper, a small chip, a title of very large hand-cut
 * capitals and one plain sentence under it (the reference's inner pages open the same way).
 */
export function SubHero({ chip, lines, lead, children }: { chip: string; lines: string[]; lead: string; children?: ReactNode }) {
  return (
    <section aria-label={chip} style={{ zIndex: 100 }} className="paper-lime seam-arc relative flex min-h-[85vh] flex-col items-center px-4 pb-32 pt-32 text-forest-ink md:px-8">
      <Chip>{chip}</Chip>
      <CutTitle lines={lines} className="mt-6 w-full max-w-[110rem] text-center font-display uppercase text-forest-ink" />
      <WordText text={lead} className="mx-auto mt-8 max-w-prose text-center text-ui-xl font-medium" />
      {children}
    </section>
  );
}
