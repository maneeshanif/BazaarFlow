"use client";

import { Fragment, useMemo } from "react";
import { CalendarClock, Loader2, Plus } from "lucide-react";

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

import { MAX_SCHEDULE_TIMES, TIMEZONE_PRESETS, useMarketing } from "../MarketingContext";

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
      <Card className="border-2 border-slate-200 dark:border-slate-700 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CalendarClock className="w-5 h-5 text-sky-600" />
            Posting Schedule
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleScheduleSubmit} className="space-y-4">
            <div className="grid gap-3">
              <div>
                <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Posting Times</label>
                <div className="space-y-2">
                  {scheduleForm.times.map((time, index) => (
                    <div key={index} className="flex gap-2">
                      <Input
                        value={time}
                        onChange={(event) => handleScheduleTimeChange(index, event.target.value)}
                        placeholder="HH:MM"
                        pattern="^([01]\\d|2[0-3]):[0-5]\\d$"
                        required
                      />
                      {scheduleForm.times.length > 1 && (
                        <Button type="button" variant="outline" onClick={() => handleRemoveScheduleTime(index)}>
                          Remove
                        </Button>
                      )}
                    </div>
                  ))}
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
                  required
                  className="mt-2"
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
