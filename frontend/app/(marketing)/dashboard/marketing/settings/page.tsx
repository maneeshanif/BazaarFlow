import Link from "next/link";
import { ShieldCheck, SlidersHorizontal, Globe2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function MarketingSettingsPage() {
  return (
    <div className="space-y-6">
      <Card className="border-2 border-slate-200 dark:border-slate-800 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <ShieldCheck className="h-5 w-5 text-emerald-600" />
            Credentials & permissions
          </CardTitle>
          <CardDescription className="text-sm text-slate-600 dark:text-slate-400">
            Rotate tokens, update operator IDs, and confirm which Facebook business assets BazaarFlow can access.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-slate-600 dark:text-slate-400">
          <p>
            The primary credential management UI lives on the overview screen. Use the quick links below to jump straight into the forms you already configured.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="sm" variant="outline">
              <Link href="/dashboard/marketing#account-scheduling">Manage Facebook tokens</Link>
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link href="/dashboard/marketing#account-scheduling">Update operator ID</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <SlidersHorizontal className="h-5 w-5 text-sky-600" />
            Automation defaults
          </CardTitle>
          <CardDescription className="text-sm text-slate-600 dark:text-slate-400">
            Fine-tune which behaviours the marketing agent should adopt by default when generating copy.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Tone directive
            </label>
            <Input placeholder="Upbeat, product-led, bilingual..." />
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Saved directives automatically seed the creative brief for each manual or scheduled campaign.
            </p>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Default hashtags
            </label>
            <Input placeholder="#BazaarFlow #ShopLocal" />
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Separate hashtags with spaces. The agent still adds context-aware tags based on inventory trends.
            </p>
          </div>
          <Badge variant="outline" className="w-fit text-xs uppercase tracking-wide">
            Roadmap: persist settings via API
          </Badge>
        </CardContent>
      </Card>

      <Card className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Globe2 className="h-5 w-5 text-purple-600" />
            Locale coverage
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
          <p>
            Use the timezone presets on the overview tab to shift schedules quickly across regional teams. Additional regional defaults (copy language, CTA templates, compliance banners) are planned for an upcoming release.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
