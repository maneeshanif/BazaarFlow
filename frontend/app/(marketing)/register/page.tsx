"use client";

import { useState } from "react";
import { Check, Chrome, Sparkles, Users } from "lucide-react";
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

const benefits = [
  "Automated campaign planning",
  "Unified chat + inventory",
  "WhatsApp + Facebook agents",
];

const highlights = [
  { label: "Merchants onboarded", value: "2,400+" },
  { label: "Avg. launch time", value: "8 mins" },
  { label: "Campaign accuracy", value: "96%" },
];

export default function RegisterPage() {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 text-white">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-6 py-16 lg:flex-row lg:items-center">
        <div className="flex-1 space-y-6">
          <Badge className="bg-white/10 text-xs uppercase tracking-[0.3em] text-slate-200" variant="outline">
            Early Access
          </Badge>
          <h1 className="text-4xl font-semibold leading-tight sm:text-5xl lg:text-6xl">
            Launch your BazaarFlow workspace in minutes.
          </h1>
          <p className="text-lg text-slate-300">
            Create a shared command center for your sales, marketing, and agent workflows. Your account owner can
            invite teammates later—today is all about getting you through the door quickly.
          </p>

          <div className="grid gap-4 sm:grid-cols-2">
            {benefits.map((benefit) => (
              <div key={benefit} className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="rounded-full bg-emerald-500/20 p-2 text-emerald-300">
                  <Check className="h-4 w-4" />
                </div>
                <p className="text-base text-slate-100">{benefit}</p>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-6 text-slate-300">
            {highlights.map((highlight) => (
              <div key={highlight.label}>
                <p className="text-2xl font-semibold text-white">{highlight.value}</p>
                <p className="text-sm uppercase tracking-wide text-slate-400">{highlight.label}</p>
              </div>
            ))}
          </div>

          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <div className="flex flex-col gap-3 sm:flex-row">
              <DialogTrigger asChild>
                <Button size="lg" className="bg-emerald-500 text-slate-900 hover:bg-emerald-400">
                  Get started for free
                </Button>
              </DialogTrigger>
              <Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10" asChild>
                <Link href="/sign-in">Already have an account?</Link>
              </Button>
            </div>
            <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                <Badge variant="secondary" className="w-max bg-emerald-50 text-emerald-600">
                  Create workspace
                </Badge>
                <DialogTitle>Tell us about your business</DialogTitle>
                <DialogDescription>
                  We&#39;ll spin up your dashboard instantly. These fields are UI-only for now—you&#39;ll be able to hook up
                  the backend later.
                </DialogDescription>
              </DialogHeader>
              <form className="space-y-4" onSubmit={(event) => event.preventDefault()}>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="fullName">Full name</Label>
                    <Input id="fullName" placeholder="Amna Yousaf" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="role">Role</Label>
                    <Input id="role" placeholder="Growth Lead" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="workEmail">Work email</Label>
                  <Input id="workEmail" type="email" placeholder="you@brand.com" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="storeName">Store or brand name</Label>
                  <Input id="storeName" placeholder="Bazaar Studio" required />
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <Input id="password" type="password" placeholder="••••••" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirm">Confirm password</Label>
                    <Input id="confirm" type="password" placeholder="••••••" required />
                  </div>
                </div>
                <Button type="button" variant="outline" className="w-full border-slate-200">
                  <Chrome className="mr-2 h-4 w-4" /> Continue with Google
                </Button>
                <DialogFooter className="flex-col gap-3 sm:flex-row sm:justify-between">
                  <p className="text-xs text-slate-500">
                    By continuing you agree to the <span className="font-semibold text-slate-700">Terms</span> and
                    <span className="font-semibold text-slate-700"> Privacy Policy</span>.
                  </p>
                  <Button type="submit" className="w-full sm:w-auto">
                    Create workspace
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <Card className="flex-1 border-white/10 bg-white/5 text-slate-100 backdrop-blur">
          <CardContent className="space-y-6 p-8">
            <div className="flex items-center gap-3 text-slate-300">
              <Users className="h-6 w-6" />
              <div>
                <p className="text-sm uppercase tracking-wide text-slate-400">Collaboration</p>
                <p className="text-xl font-semibold text-white">Invite your entire team</p>
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-900/40 p-5">
              <p className="text-lg font-medium text-white">“We replaced six tools with BazaarFlow.”</p>
              <p className="mt-3 text-sm text-slate-400">
                Sadaf from Meridian Retail plugged the WhatsApp finance agent, inventory agent, and marketing campaigns
                in one afternoon. The onboarding wizard guided her through everything without touching code.
              </p>
            </div>
            <div className="space-y-4">
              {["Agent-powered replies", "Unified audit log", "Built for commerce"]
                .map((item) => (
                  <div key={item} className="flex items-start gap-3">
                    <Sparkles className="mt-1 h-5 w-5 text-emerald-300" />
                    <p className="text-slate-200">{item}</p>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
