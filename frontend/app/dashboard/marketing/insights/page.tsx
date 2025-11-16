import Link from "next/link";
import { BarChart3, LineChart, PieChart, RefreshCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const insightHighlights = [
  {
    label: "Average reach per campaign",
    value: "--",
    helper: "Populate by refreshing insights on the overview tab.",
  },
  {
    label: "Click-through rate",
    value: "--",
    helper: "BazaarFlow calculates CTR once Facebook impressions are synced.",
  },
  {
    label: "Positive reactions",
    value: "--",
    helper: "Emoji sentiment rolls up every time insights refresh succeeds.",
  },
];

export default function MarketingInsightsPage() {
  return (
    <div className="space-y-6">
      <Card className="border-2 border-slate-200 dark:border-slate-800 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <BarChart3 className="h-5 w-5 text-blue-600" />
            Insights Workspace
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-slate-600 dark:text-slate-400">
          <p>
            Run analytics without leaving BazaarFlow. Sync Facebook metrics from the overview page, then come here to compare reach, clicks, sentiment, and conversion patterns across every campaign.
          </p>
          <div className="flex flex-wrap gap-3">
            <Badge variant="outline">Cross-campaign rollups</Badge>
            <Badge variant="outline">Engagement sentiment</Badge>
            <Badge variant="outline">SKU-level tagging</Badge>
          </div>
          <Button asChild size="sm" variant="outline" className="w-fit">
            <Link href="/dashboard/marketing#recent-activity">
              Refresh campaign insights
              <RefreshCcw className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <LineChart className="h-5 w-5 text-emerald-600" />
              Timeline & pacing
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
            <p>
              Coming soon: overlay campaign cadence with sales orders to identify the most effective posting schedule. Export-ready CSVs will follow shortly after so analysts can dig deeper.
            </p>
          </CardContent>
        </Card>
        <Card className="border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <PieChart className="h-5 w-5 text-purple-600" />
              Segment drilldowns
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
            <p>
              Define audiences by SKU, campaign angle, or custom tags. The dashboard groups reactions, reach, and conversions so you can spot which stories resonate best with each cohort.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/60">
        <CardHeader>
          <CardTitle className="text-base">Snapshot metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {insightHighlights.map((item) => (
              <div key={item.label} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{item.label}</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{item.value}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{item.helper}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
