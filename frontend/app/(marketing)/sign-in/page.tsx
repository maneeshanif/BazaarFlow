"use client";

import { useState } from "react";
import { Chrome, Lock, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const assurances = [
  "SSO-ready when you are",
  "Fine-grained workspace roles",
  "Audit trails across every agent",
];

export default function SignInPage() {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-10 px-6 py-16 lg:flex-row lg:items-center">
        <div className="flex-1 space-y-6">
          <Badge variant="secondary" className="bg-slate-900 text-white">
            Secure access
          </Badge>
          <h1 className="text-4xl font-semibold text-slate-900 sm:text-5xl">
            Welcome back to your BazaarFlow control room.
          </h1>
          <p className="text-lg text-slate-600">
            Sign in to orchestrate finance, sales, and marketing agents from one place. Two clicks and you&#39;re back
            to shipping automated workflows.
          </p>

          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <div className="flex flex-col gap-3 sm:flex-row">
              <DialogTrigger asChild>
                <Button size="lg" className="bg-slate-900 text-white hover:bg-slate-800">
                  Open sign-in modal
                </Button>
              </DialogTrigger>
              <Button size="lg" variant="outline" className="text-slate-700" asChild>
                <Link href="/register">Need an account?</Link>
              </Button>
            </div>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Sign in to BazaarFlow</DialogTitle>
                <DialogDescription>All authentication is simulated here—connect it to your backend later.</DialogDescription>
              </DialogHeader>
              <form className="space-y-4" onSubmit={(event) => event.preventDefault()}>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" placeholder="founder@brand.com" required />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password">Password</Label>
                    <Button variant="link" className="px-0 text-sm" type="button">
                      Forgot password?
                    </Button>
                  </div>
                  <Input id="password" type="password" placeholder="••••••••" required />
                </div>
                <Button type="button" variant="outline" className="w-full border-slate-200">
                  <Chrome className="mr-2 h-4 w-4" /> Continue with Google
                </Button>
                <DialogFooter className="flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <ShieldCheck className="h-4 w-4" />
                    <span>Protected with SOC 2 practices.</span>
                  </div>
                  <Button type="submit" className="w-full sm:w-auto">
                    Sign in
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <Card className="flex-1 border-slate-200">
          <CardContent className="space-y-6 p-8">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-3 text-slate-600">
                <Lock className="h-5 w-5" />
                <p className="text-sm uppercase tracking-wide">Single sign-on ready</p>
              </div>
              <p className="mt-4 text-xl font-semibold text-slate-900">
                “Our entire team signs in with Google while IT preps the real SSO.”
              </p>
              <p className="mt-2 text-sm text-slate-500">
                The engineering lead at River &amp; Co. used this exact flow to preview the UI before wiring the API.
              </p>
            </div>
            <div className="space-y-4">
              {assurances.map((item) => (
                <div key={item} className="flex items-start gap-3">
                  <ShieldCheck className="mt-1 h-5 w-5 text-emerald-500" />
                  <p className="text-slate-600">{item}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
