import Link from "next/link";
import { ArrowRight, CalendarClock, Image as ImageIcon, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function MarketingStudioPage() {
  return (
    <div className="space-y-6">
      <Card className="border-2 border-slate-200 dark:border-slate-800 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Sparkles className="h-5 w-5 text-fuchsia-600" />
            Campaign Studio Overview
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-slate-600 dark:text-slate-400">
          <p>
            The Campaign Studio is where marketers combine AI copy, merchandising data, and brand assets to publish polished Facebook posts in minutes. Use the live brief to steer tone, activate overrides to specify imagery, and let BazaarFlow execute the publish workflow for you.
          </p>
          <div className="flex flex-wrap gap-3">
            <Badge variant="outline">Inventory-aware prompts</Badge>
            <Badge variant="outline">Hashtag curation</Badge>
            <Badge variant="outline">Auto image lookup</Badge>
          </div>
          <Button asChild size="sm" className="mt-2 w-fit">
            <Link href="/dashboard/marketing#campaign-launchpad">
              Jump to manual launchpad
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <ImageIcon className="h-5 w-5 text-sky-600" />
              Creative Overrides
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
            <p>
              Drop JSON snippets or key-value tokens to override any part of the generated payload. Common fields include <code>image_query</code>, <code>call_to_action</code>, and <code>target_audience</code>.
            </p>
            <p>
              BazaarFlow safely merges overrides with agent output, keeping defaults intact so you never lose the AI suggestions.
            </p>
          </CardContent>
        </Card>

        <Card className="border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CalendarClock className="h-5 w-5 text-emerald-600" />
              Scheduling Assist
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
            <p>
              Campaign Studio honors the posting windows configured on the overview tab. When a manual campaign is published outside a set slot, the AI gently adjusts copy to feel timely and on-brand.
            </p>
            <Button asChild variant="outline" size="sm" className="mt-1 w-fit">
              <Link href="/dashboard/marketing#account-scheduling">Update posting slots</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
