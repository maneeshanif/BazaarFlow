"use client";

import { ShieldCheck, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

import { useMarketing } from "../MarketingContext";

export default function MarketingCredentialsPage() {
  const {
    accounts,
    loadingAccounts,
    selectedAccountId,
    setSelectedAccountId,
    credentialsForm,
    setCredentialsForm,
    savingCredentials,
    handleCredentialsSubmit
  } = useMarketing();

  const hasAccounts = accounts.length > 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Credentials</h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 max-w-2xl">
          Connect BazaarFlow to new Facebook pages or rotate access tokens for operators already in use.
        </p>
      </div>

      <Card className="border-2 border-slate-200 dark:border-slate-700 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <ShieldCheck className="h-5 w-5 text-emerald-600" />
            Facebook Credentials
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Connected Accounts</p>
              <div className="flex flex-wrap gap-2">
                {loadingAccounts && !hasAccounts ? (
                  <Badge className="bg-slate-100 text-slate-500 border-slate-200">Loading...</Badge>
                ) : !hasAccounts ? (
                  <Badge className="bg-slate-100 text-slate-500 border-slate-200">No accounts yet</Badge>
                ) : (
                  accounts.map((account) => {
                    const active = account.account_id === selectedAccountId;
                    return (
                      <Button
                        key={account.account_id}
                        variant={active ? "default" : "outline"}
                        className={`h-9 rounded-full ${
                          active
                            ? "bg-gradient-to-r from-[#174143] to-[#427A76]"
                            : "border-slate-200 dark:border-slate-700"
                        }`}
                        onClick={() => setSelectedAccountId(account.account_id)}
                      >
                        {account.page_name || `Page ${account.page_id}`}
                      </Button>
                    );
                  })
                )}
              </div>
            </div>

            <Separator />

            <form onSubmit={handleCredentialsSubmit} className="space-y-4">
              <div className="grid gap-3">
                <div>
                  <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Operator / User ID</label>
                  <Input
                    value={credentialsForm.userId}
                    onChange={(event) => setCredentialsForm((prev) => ({ ...prev, userId: event.target.value }))}
                    placeholder="e.g. marketing-admin"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Facebook Page ID</label>
                  <Input
                    value={credentialsForm.pageId}
                    onChange={(event) => setCredentialsForm((prev) => ({ ...prev, pageId: event.target.value }))}
                    placeholder="1234567890"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Display Name (optional)</label>
                  <Input
                    value={credentialsForm.pageName}
                    onChange={(event) => setCredentialsForm((prev) => ({ ...prev, pageName: event.target.value }))}
                    placeholder="BazaarFlow Electronics"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Page Access Token</label>
                  <Input
                    value={credentialsForm.accessToken}
                    onChange={(event) => setCredentialsForm((prev) => ({ ...prev, accessToken: event.target.value }))}
                    placeholder="EAABsbCS1iHgBA..."
                    required
                    type="password"
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Use a long-lived token with permissions to publish content, read insights, and manage comments.
                  </p>
                </div>
              </div>
              <Button type="submit" className="w-full" disabled={savingCredentials}>
                {savingCredentials && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save Credentials
              </Button>
            </form>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
