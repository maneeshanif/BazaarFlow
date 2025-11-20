"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Activity,
  MessageSquare,
  Package,
  CheckCircle2,
  Clock,
  Zap,
  Database,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const LOG_SOURCES = [
  {
    key: "agents",
    label: "Agent SDK",
    description: "Verbose traces from openai.agents logger",
    params: { logger: "openai.agents" },
  },
  {
    key: "turns",
    label: "Agent Turns",
    description: "Structured turn-level breadcrumbs",
    params: { action: "agent_turn" },
  },
];

type LiveLogEntry = {
  id: string;
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  agent?: string;
  action?: string;
  status?: string;
  tool?: string;
  reasoning?: string;
  toolInvoked?: string;
  turn?: number;
};

const levelColors: Record<string, string> = {
  info: "text-blue-700 bg-blue-100",
  warning: "text-amber-700 bg-amber-100",
  error: "text-red-700 bg-red-100",
  default: "text-slate-700 bg-slate-100",
};

const normalizeLevel = (entry: LiveLogEntry) => {
  const level = (entry.level || "info").toLowerCase();
  if (level.includes("err")) return "error";
  if (level.includes("warn")) return "warning";
  return "info";
};

const deriveAgentRun = (message: string) => {
  const match = /Running agent\s+([\w-]+)\s*\(turn\s*(\d+)/i.exec(message);
  if (!match) return null;
  return { agent: match[1], turn: Number(match[2]) };
};

const iconForLog = (message: string) => {
  if (message.toLowerCase().startsWith("calling llm")) return Zap;
  if (message.toLowerCase().startsWith("received model response")) return CheckCircle2;
  if (message.toLowerCase().includes("tool")) return Database;
  if (message.toLowerCase().includes("tracing")) return Activity;
  if (message.toLowerCase().includes("http")) return Package;
  return MessageSquare;
};

export default function AgentLogsPage() {
  const [logs, setLogs] = useState<LiveLogEntry[]>([]);
  const [sourceKey, setSourceKey] = useState(LOG_SOURCES[0].key);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeSource = useMemo(() => {
    return LOG_SOURCES.find((source) => source.key === sourceKey) ?? LOG_SOURCES[0];
  }, [sourceKey]);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "200" });
      Object.entries(activeSource.params).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      const response = await fetch(`${API_BASE}/api/logs?${params.toString()}`);
      if (!response.ok) {
        throw new Error("Failed to fetch live logs");
      }
      const result = await response.json();
      const payload: LiveLogEntry[] = (result.logs || []).map((entry: LiveLogEntry) => entry);
      setLogs(payload);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to fetch logs");
    } finally {
      setLoading(false);
    }
  }, [activeSource]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (!autoRefresh) {
      return;
    }
    const interval = setInterval(fetchLogs, 4000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchLogs]);

  const formatTime = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "--:--";
    }
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 py-8 px-4">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <Badge className="mb-4 px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-0">
            <Activity className="w-4 h-4 mr-2" />
            Real-Time Monitoring
          </Badge>
          <h1 className="text-4xl font-bold mb-2 text-slate-900">Agent Interaction Logs</h1>
          <p className="text-slate-600">MCP Server Communication & Multi-Agent Reasoning</p>
        </motion.div>

        {/* Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-6 flex flex-wrap gap-3 justify-center"
        >
          {LOG_SOURCES.map((option) => (
            <Button
              key={option.key}
              variant={sourceKey === option.key ? "default" : "outline"}
              onClick={() => setSourceKey(option.key)}
              className={sourceKey === option.key ? "bg-[#174143]" : ""}
            >
              {option.label}
            </Button>
          ))}
          <Button
            variant="outline"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={autoRefresh ? "border-green-500 text-green-600" : ""}
          >
            {autoRefresh ? "🟢 Live" : "⏸️ Paused"}
          </Button>
          <Button variant="outline" onClick={fetchLogs} disabled={loading}>
            Refresh now
          </Button>
        </motion.div>

        <p className="text-center text-sm text-slate-500 mb-4">{activeSource.description}</p>

        {error && (
          <p className="text-center text-sm text-red-600 mb-4">{error}</p>
        )}
        {loading && !error && (
          <p className="text-center text-sm text-slate-500 mb-4">Fetching latest logs…</p>
        )}

        {/* Logs Timeline */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="space-y-4"
        >
          <AnimatePresence>
            {logs.map((log, index) => {
              const level = normalizeLevel(log);
              const colorClass = levelColors[level] || levelColors.default;
              const agentRun = deriveAgentRun(log.message || "");
              const Icon = iconForLog(log.message || "");

              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.03 }}
                >
                  <Card className="border border-slate-100 shadow-sm hover:shadow-lg transition-shadow">
                    <CardContent className="p-5">
                      <div className="flex items-start gap-4">
                        <div className={`w-12 h-12 rounded-full ${colorClass} flex items-center justify-center flex-shrink-0`}>
                          <Icon className="w-6 h-6" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge className={colorClass}>{agentRun?.agent || log.logger}</Badge>
                              {agentRun?.turn && (
                                <Badge variant="outline" className="text-xs">
                                  turn {agentRun.turn}
                                </Badge>
                              )}
                              <Badge variant="outline" className="text-xs uppercase">
                                {level}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-slate-500">
                              <Clock className="w-3 h-3" />
                              {formatTime(log.timestamp)}
                            </div>
                          </div>
                          <p className="mt-3 font-mono text-sm text-slate-900 whitespace-pre-wrap break-words">
                            {log.message}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </motion.div>

        {logs.length === 0 && (
          <div className="text-center py-12">
            <Activity className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500">No logs found for this filter</p>
          </div>
        )}
      </div>
    </div>
  );
}

