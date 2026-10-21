"use client";

import { Fragment, useMemo } from "react";
import type { LucideIcon } from "lucide-react";
import { CalendarClock, Loader2, MessageCircle, MoonStar, Plus, Sunrise, Sun, Sunset } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

import { MAX_SCHEDULE_TIMES, TIMEZONE_PRESETS, useMarketing } from "../MarketingContext";

type PeriodOption = "AM" | "PM";

const PERIOD_OPTIONS: PeriodOption[] = ["AM", "PM"];

type ShortcutOption = {
  label: string;
  description: string;
  value: string;
  icon: LucideIcon;
};

const TIME_SHORTCUTS: ShortcutOption[] = [
  {
    label: "Morning Buzz",
    description: "Commute + coffee scroll",
    value: "09:00",
    icon: Sunrise,
  },
  {
    label: "Lunch Drop",
    description: "Break-time browsers",
    value: "13:00",
    icon: Sun,
  },
  {
    label: "Prime Time",
    description: "Evening social peak",
    value: "18:30",
    icon: Sunset,
  },
  {
    label: "Night Owl",
    description: "Late-night deal hunters",
    value: "21:00",
    icon: MoonStar,
  },
];

const ensureTimeValue = (value: string): string => {
  if (!value || !value.includes(":")) {
    return "09:00";
  }
  const [rawHour = "09", rawMinute = "00"] = value.split(":");
  const hour = rawHour;
  const minute = rawMinute;
  return `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
};

const derivePeriod = (value: string): PeriodOption => {
  const hour = Number(value.split(":")[0] ?? 0);
  return hour >= 12 ? "PM" : "AM";
};

const convertWithPeriod = (value: string, period: PeriodOption): string => {
  const safeValue = ensureTimeValue(value);
  const [rawHour, minute] = safeValue.split(":");
  let hourNum = Number(rawHour);
  if (Number.isNaN(hourNum)) {
    hourNum = 9;
  }

  if (period === "PM" && hourNum < 12) {
    hourNum += 12;
  }
  if (period === "AM" && hourNum >= 12) {
    hourNum -= 12;
  }

  return `${hourNum.toString().padStart(2, "0")}:${minute.padStart(2, "0")}`;
};

const formatFriendlyLabel = (value: string): string => {
  const safeValue = ensureTimeValue(value);
  const [rawHour, minute] = safeValue.split(":");
  let hourNum = Number(rawHour);
  const period = hourNum >= 12 ? "PM" : "AM";
  hourNum = hourNum % 12;
  if (hourNum === 0) {
    hourNum = 12;
  }
  return `${hourNum.toString().padStart(2, "0")}:${minute.padStart(2, "0")}` + ` ${period}`;
};

export default function MarketingSchedulePage() {
  const {
    // recurring schedule form
    scheduleForm,
    setScheduleForm,
    scheduleMeta,
    handleScheduleTimeChange,
    handleAddScheduleTime,
    handleRemoveScheduleTime,
    handleScheduleSubmit,
    savingSchedule,
    // scheduled campaign studio
    schedulePrompt,
    setSchedulePrompt,
    postCount,
    setPostCount,
    previewScheduledCampaign,
    previewedScheduledCampaign,
    scheduledPostsDraft,
    setScheduledPostsDraft,
    previewingScheduledCampaign,
    createScheduledCampaign,
    savingScheduledCampaign,
  } = useMarketing();

  const presetTimezoneValue = useMemo(() => {
    for (const group of TIMEZONE_PRESETS) {
      const match = group.zones.find((zone) => zone.value === scheduleForm.timezone);
      if (match) {
        return match.value;
      }
    }
    return undefined;
  }, [scheduleForm.timezone]);

  return (
    <div className="space-y-6">
      {/* Scheduled Campaign Studio */}
      <Card className="border-2 border-sky-100 bg-gradient-to-br from-sky-50 via-white to-slate-50 shadow-lg dark:border-sky-900/60 dark:from-slate-900 dark:via-slate-900/70 dark:to-slate-950">
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <MessageCircle className="w-5 h-5 text-sky-600" />
                Scheduled Campaign Studio
              </CardTitle>
              <CardDescription className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                Ask the marketing agent for {postCount} posts, review the drafts, then pick exact times for each.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Prompt + post count */}
          <div className="space-y-3">
            <Label className="flex items-center justify-between text-sm font-medium text-slate-700 dark:text-slate-300">
              <span>Campaign brief</span>
              <span className="text-xs font-normal text-slate-500 dark:text-slate-400">
                Describe what you want to promote, the audience, and any offers.
              </span>
            </Label>
            <Textarea
              value={schedulePrompt}
              onChange={(event) => setSchedulePrompt(event.target.value)}
              placeholder="e.g. Promote our weekend mega sale on winter jackets, targeting budget-conscious college students."
              className="min-h-[90px] resize-y rounded-2xl border-slate-200 bg-white/80 text-sm shadow-sm focus-visible:ring-sky-500 dark:border-slate-700 dark:bg-slate-900/70"
            />

            <div className="space-y-2 rounded-2xl border border-slate-200/80 bg-slate-50/70 p-3 text-xs dark:border-slate-700/80 dark:bg-slate-900/60">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-slate-700 dark:text-slate-200">Number of posts</span>
                <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">{postCount} posts</span>
              </div>
              <Slider
                value={[postCount]}
                min={1}
                max={6}
                step={1}
                onValueChange={([value]) => setPostCount(value)}
                className="mt-1"
              />
              <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                We recommend 2–4 posts for most campaigns. You can always re-generate if the ideas don&apos;t feel right.
              </p>
            </div>

            <div className="flex justify-end">
              <Button
                type="button"
                size="sm"
                onClick={() => void previewScheduledCampaign()}
                disabled={previewingScheduledCampaign}
              >
                {previewingScheduledCampaign && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Generate draft posts
              </Button>
            </div>
          </div>

          {/* Generated posts with per-post datetime */}
          {previewedScheduledCampaign && (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">Generated posts</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Review each caption and pick the exact date &amp; time it should go out.
                  </p>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {scheduledPostsDraft.map((draft, index) => (
                  <div
                    key={`${draft.post.record_id ?? index}`}
                    className="flex flex-col gap-3 rounded-2xl border border-slate-200/80 bg-white/90 p-3 shadow-sm dark:border-slate-700/80 dark:bg-slate-900/70"
                  >
                    <div className="space-y-1">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        Post {index + 1}
                      </p>
                      <p className="line-clamp-4 text-sm text-slate-800 dark:text-slate-100">
                        {draft.post.message || "No caption included. Try regenerating."}
                      </p>
                    </div>
                    {draft.post.image_url && (
                      <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-slate-50 dark:border-slate-700/80 dark:bg-slate-900/60">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={draft.post.image_url}
                          alt="Generated campaign visual"
                          className="h-44 w-full object-cover"
                        />
                      </div>
                    )}
                    {draft.post.hashtags && draft.post.hashtags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {draft.post.hashtags.map((tag) => (
                          <span
                            key={tag}
                            className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                          >
                            #{tag.replace(/^#/, "")}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="space-y-1">
                      <Label className="text-xs font-medium text-slate-600 dark:text-slate-300">
                        Scheduled time
                      </Label>
                      <Input
                        type="datetime-local"
                        value={draft.scheduledAt}
                        onChange={(event) => {
                          const value = event.target.value;
                          setScheduledPostsDraft((prev) =>
                            prev.map((item, i) => (i === index ? { ...item, scheduledAt: value } : item)),
                          );
                        }}
                        className="w-full rounded-xl border-slate-200 bg-slate-50/80 text-xs font-mono text-slate-900 shadow-sm focus-visible:ring-sky-500 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-100"
                      />
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">
                        Use your local timezone; the backend will normalise to UTC.
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex flex-col items-stretch gap-2 rounded-2xl border border-slate-200/80 bg-slate-50/80 p-3 text-xs dark:border-slate-700/80 dark:bg-slate-900/70 md:flex-row md:items-center md:justify-between">
                <p className="text-slate-600 dark:text-slate-300">
                  When you&apos;re happy with the plan, schedule all posts in one go. The scheduler will publish them
                  automatically.
                </p>
                <Button
                  type="button"
                  size="sm"
                  className="md:min-w-[190px]"
                  onClick={() => void createScheduledCampaign()}
                  disabled={savingScheduledCampaign}
                >
                  {savingScheduledCampaign && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Schedule all posts
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recurring Posting Schedule (existing behaviour) */}
      <Card className="border-2 border-slate-200 bg-gradient-to-br from-white via-slate-50 to-slate-100 shadow-lg dark:border-slate-800 dark:from-slate-900 dark:via-slate-900/70 dark:to-slate-900">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CalendarClock className="w-5 h-5 text-sky-600" />
            Posting Schedule
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleScheduleSubmit} noValidate className="space-y-4">
            <div className="grid gap-3">
              <div>
                <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Posting Times</label>
                <div className="space-y-3">
                  {scheduleForm.times.map((time, index) => {
                    const period = derivePeriod(time);
                    const friendly = formatFriendlyLabel(time);
                    return (
                      <div
                        key={`${time}-${index}`}
                        className={cn(
                          "space-y-4 rounded-2xl border border-slate-200/80 bg-white/70 p-4 shadow-inner backdrop-blur-sm",
                          "dark:border-slate-700/70 dark:bg-slate-900/60",
                        )}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <Input
                            type="time"
                            value={time || ""}
                            onChange={(event) => handleScheduleTimeChange(index, event.target.value)}
                            className="w-40 rounded-xl border-slate-200 bg-slate-50/70 font-mono text-base tracking-wide text-slate-900 shadow-sm focus-visible:ring-sky-500 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-100"
                            aria-label={`Posting time ${index + 1}`}
                          />
                          <Select
                            value={period}
                            onValueChange={(value) =>
                              handleScheduleTimeChange(index, convertWithPeriod(time, value as PeriodOption))
                            }
                          >
                            <SelectTrigger className="w-28 rounded-xl border-slate-200 bg-slate-50/70 dark:border-slate-700 dark:bg-slate-900/80">
                              <SelectValue placeholder="AM/PM" />
                            </SelectTrigger>
                            <SelectContent>
                              {PERIOD_OPTIONS.map((option) => (
                                <SelectItem key={option} value={option}>
                                  {option}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          {scheduleForm.times.length > 1 && (
                            <Button type="button" variant="ghost" onClick={() => handleRemoveScheduleTime(index)}>
                              Remove
                            </Button>
                          )}
                        </div>
                        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-dashed border-slate-200/80 bg-slate-50/60 px-3 py-2 text-xs text-slate-600 dark:border-slate-700/70 dark:bg-slate-900/40 dark:text-slate-300">
                          <span className="font-medium">Slot {index + 1} shows as {friendly}</span>
                          <span className="font-mono text-slate-500">{scheduleForm.timezone || "UTC"}</span>
                        </div>
                        <div className="space-y-2 rounded-xl border border-dashed border-slate-200/80 bg-white/60 p-3 dark:border-slate-700/70 dark:bg-slate-900/40">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Quick suggestions</p>
                          <div className="grid gap-2 sm:grid-cols-2">
                            {TIME_SHORTCUTS.map((shortcut) => {
                              const Icon = shortcut.icon;
                              const isActive = ensureTimeValue(time) === shortcut.value;
                              return (
                                <button
                                  key={`${shortcut.value}-${index}`}
                                  type="button"
                                  onClick={() => handleScheduleTimeChange(index, shortcut.value)}
                                  className={cn(
                                    "flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-left text-xs font-medium transition-colors",
                                    isActive
                                      ? "border-sky-500/80 bg-sky-50/80 text-slate-900 dark:border-sky-500/60 dark:bg-sky-500/10 dark:text-slate-100"
                                      : "border-slate-200/80 bg-slate-50/40 text-slate-600 hover:border-slate-300 dark:border-slate-700/70 dark:bg-slate-900/30 dark:text-slate-300",
                                  )}
                                  aria-label={`Apply ${shortcut.label} time to slot ${index + 1}`}
                                >
                                  <Icon className="h-4 w-4 text-sky-500" />
                                  <div className="flex flex-col leading-tight">
                                    <span>{shortcut.label}</span>
                                    <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400">
                                      {shortcut.description}
                                    </span>
                                  </div>
                                  <span className="ml-auto font-mono text-[11px] text-slate-500 dark:text-slate-400">
                                    {formatFriendlyLabel(shortcut.value)}
                                  </span>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                {scheduleForm.times.length < MAX_SCHEDULE_TIMES && (
                  <Button type="button" variant="ghost" size="sm" className="mt-2" onClick={handleAddScheduleTime}>
                    <Plus className="w-4 h-4 mr-1" /> Add slot
                  </Button>
                )}
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Timezone</label>
                <Select
                  value={presetTimezoneValue}
                  onValueChange={(value) =>
                    setScheduleForm((prev) => ({
                      ...prev,
                      timezone: value,
                    }))
                  }
                >
                  <SelectTrigger className="mt-1 w-full">
                    <SelectValue placeholder="Quick pick a timezone" />
                  </SelectTrigger>
                  <SelectContent>
                    {TIMEZONE_PRESETS.map((group, index) => (
                      <Fragment key={group.group}>
                        <SelectGroup>
                          <SelectLabel>{group.group}</SelectLabel>
                          {group.zones.map((zone) => (
                            <SelectItem key={zone.value} value={zone.value}>
                              {zone.label}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                        {index < TIMEZONE_PRESETS.length - 1 ? <SelectSeparator /> : null}
                      </Fragment>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  value={scheduleForm.timezone}
                  onChange={(event) => setScheduleForm((prev) => ({ ...prev, timezone: event.target.value }))}
                  placeholder="UTC"
                  aria-label="Timezone override"
                  className="mt-2 rounded-xl border-slate-200 bg-white/70 shadow-sm focus-visible:ring-sky-500 dark:border-slate-700 dark:bg-slate-900/70"
                />
                <p className="mt-1 text-xs text-slate-500">
                  Use the dropdown for common options or provide any valid IANA name (e.g. Asia/Karachi).
                </p>
              </div>
            </div>

            {scheduleMeta?.last_triggered_at && (
              <div className="rounded-lg bg-slate-100 dark:bg-slate-800 p-3 text-xs text-slate-600 dark:text-slate-300">
                Last automated run: {new Date(scheduleMeta.last_triggered_at).toLocaleString()}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={savingSchedule}>
              {savingSchedule && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Save Schedule
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
