"use client";

import { useMemo } from "react";
import { BarChart3, Loader2, Megaphone, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

import { useFormattedLastRefreshed, useMarketing } from "../MarketingContext";

export default function MarketingOverviewPage() {
  const {
    selectedAccount,
    manualPrompt,
    setManualPrompt,
    overridesInput,
    setOverridesInput,
    handleManualCampaign,
    publishing,
    insightsSummary,
    lastRefreshedAt,
    postsAutoRefreshIntervalMs,
  } = useMarketing();

  const formattedLastRefreshed = useFormattedLastRefreshed(lastRefreshedAt);
  const autoRefreshLabel = useMemo(() => `${Math.round(postsAutoRefreshIntervalMs / 1000)}s auto refresh`, [
    postsAutoRefreshIntervalMs,
  ]);

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <Badge className="mb-3 bg-gradient-to-r from-[#174143] to-[#427A76] text-white border-none px-4 py-1.5">
              <Megaphone className="w-3.5 h-3.5 mr-1" />
              Marketing Agent
            </Badge>
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Overview</h2>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Review high-level stats, trigger manual campaigns, and monitor system health.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="outline" className="text-xs">
              {autoRefreshLabel}
            </Badge>
            <span className="text-xs text-slate-500 dark:text-slate-400">Last sync: {formattedLastRefreshed}</span>
            {selectedAccount && (
              <Badge variant="outline" className="text-xs">
                {selectedAccount.page_name || "Unnamed page"} • {selectedAccount.page_id}
              </Badge>
            )}
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
          <Card className="h-full border-2 border-slate-200 dark:border-slate-700 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Sparkles className="w-5 h-5 text-fuchsia-600" />
                Manual Campaign
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Creative Brief (optional)</label>
                <Textarea
                  value={manualPrompt}
                  onChange={(event) => setManualPrompt(event.target.value)}
                  placeholder="Highlight the new gaming laptops with a Ramadan bundle."
                  rows={4}
                />
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-400">
                  Advanced Overrides
                  <Badge variant="outline" className="text-xs">JSON</Badge>
                </label>
                <Textarea
                  value={overridesInput}
                  onChange={(event) => setOverridesInput(event.target.value)}
                  placeholder='{"image_query": "bazaar electronics storefront"}'
                  rows={3}
                />
                <p className="mt-1 text-xs text-slate-500">
                  Provide optional JSON to steer the agent. Leave empty to rely on live sales &amp; inventory data.
                </p>
              </div>
              <Button onClick={handleManualCampaign} disabled={publishing} className="w-full">
                {publishing && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Generate &amp; Publish
              </Button>
            </CardContent>
          </Card>

          <Card className="h-full border-2 border-slate-200 dark:border-slate-700 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <BarChart3 className="w-5 h-5 text-blue-600" />
                Performance Snapshot
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                {[{
                  label: "Total Reach",
                  value: insightsSummary.reach.toLocaleString(),
                }, {
                  label: "Total Impressions",
                  value: insightsSummary.impressions.toLocaleString(),
                }, {
                  label: "Link Clicks",
                  value: insightsSummary.clicks.toLocaleString(),
                }, {
                  label: "Reactions",
                  value: insightsSummary.reactions.toLocaleString(),
                }].map((item) => (
                  <div key={item.label} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">{item.label}</p>
                    <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{item.value}</p>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-xs text-slate-500">
                {insightsSummary.postsWithInsights} post{insightsSummary.postsWithInsights === 1 ? "" : "s"} with refreshed insights.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
