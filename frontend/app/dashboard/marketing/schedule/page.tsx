"use client";

import { Fragment, useMemo } from "react";
import type { LucideIcon } from "lucide-react";
import { CalendarClock, Loader2, MoonStar, Plus, Sunrise, Sun, Sunset } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  const [hour = "09", minute = "00"] = value.split(":");
  return `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
};

const derivePeriod = (value: string): PeriodOption => {
  const hour = Number(value.split(":")[0] ?? 0);
  return hour >= 12 ? "PM" : "AM";
};

const convertWithPeriod = (value: string, period: PeriodOption): string => {
  const safeValue = ensureTimeValue(value);
  let [hour, minute] = safeValue.split(":");
  let hourNum = Number(hour);
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
  let [hour, minute] = safeValue.split(":");
  let hourNum = Number(hour);
  const period = hourNum >= 12 ? "PM" : "AM";
  hourNum = hourNum % 12;
  if (hourNum === 0) {
    hourNum = 12;
  }
  return `${hourNum.toString().padStart(2, "0")}:${minute.padStart(2, "0")}` + ` ${period}`;
};

export default function MarketingSchedulePage() {
  const {
    scheduleForm,
    setScheduleForm,
    scheduleMeta,
    handleScheduleTimeChange,
    handleAddScheduleTime,
    handleRemoveScheduleTime,
    handleScheduleSubmit,
    savingSchedule,
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
