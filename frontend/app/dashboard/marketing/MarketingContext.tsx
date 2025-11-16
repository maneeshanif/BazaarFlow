"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import axios from "axios";
import confetti from "canvas-confetti";
import { toast } from "sonner";

export interface MarketingAccount {
  account_id: string;
  user_id: string;
  page_id: string;
  page_name?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface MarketingSchedule {
  schedule_id?: string;
  account_id?: string;
  user_id?: string;
  times: string[];
  timezone?: string;
  last_triggered_at?: string | null;
  updated_at?: string;
}

export interface ReactionBreakdown {
  like?: number;
  love?: number;
  wow?: number;
  haha?: number;
  sad?: number;
  angry?: number;
  care?: number;
  [key: string]: number | undefined;
}

export interface PostInsightsRecord {
  reach?: number;
  impressions?: number;
  clicked?: number;
  comments_count?: number;
  shares_count?: number;
  engagement_rate?: number;
  reactions?: ReactionBreakdown;
  retrieved_at?: string;
}

export interface MarketingPost {
  record_id: string;
  facebook_post_id: string;
  account_id: string;
  user_id: string;
  message: string;
  image_url?: string | null;
  product_sku?: string | null;
  hashtags?: string[];
  angle?: string | null;
  source?: string;
  created_at: string;
  updated_at: string;
  insights?: PostInsightsRecord | null;
  extra?: Record<string, unknown>;
}

export interface MarketingComment {
  comment_id: string;
  post_id: string;
  message: string;
  from_user?: Record<string, string>;
  created_time?: string;
  like_count?: number;
  comment_count?: number;
  is_hidden?: boolean;
  parent_comment_id?: string | null;
  attachment?: Record<string, unknown> | null;
}

interface MarketingCommentKeyword {
  keyword: string;
  count: number;
  [key: string]: unknown;
}

interface PostCommentsSummary {
  comments: MarketingComment[];
  totalCount: number;
  hasNextPage: boolean;
  nextCursor?: string | null;
  keywords?: MarketingCommentKeyword[];
  fetchedAt: string;
}

interface CampaignSummary {
  reach: number;
  impressions: number;
  clicks: number;
  reactions: number;
  postsWithInsights: number;
}

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
export const MAX_SCHEDULE_TIMES = 3;
export const defaultTimes = ["09:00", "13:00"];

export const TIMEZONE_PRESETS = [
  {
    group: "United States",
    zones: [
      { value: "America/Los_Angeles", label: "Pacific Time (PST/PDT)" },
      { value: "America/Denver", label: "Mountain Time (MST/MDT)" },
      { value: "America/Chicago", label: "Central Time (CST/CDT)" },
      { value: "America/New_York", label: "Eastern Time (EST/EDT)" },
      { value: "America/Phoenix", label: "Arizona Time (MST)" },
    ],
  },
  {
    group: "Canada",
    zones: [
      { value: "America/Vancouver", label: "Pacific - Vancouver" },
      { value: "America/Edmonton", label: "Mountain - Edmonton" },
      { value: "America/Winnipeg", label: "Central - Winnipeg" },
      { value: "America/Toronto", label: "Eastern - Toronto" },
      { value: "America/Halifax", label: "Atlantic - Halifax" },
    ],
  },
  {
    group: "United Kingdom & Europe",
    zones: [
      { value: "UTC", label: "UTC (Coordinated Universal Time)" },
      { value: "Europe/London", label: "United Kingdom - London" },
      { value: "Europe/Dublin", label: "Ireland - Dublin" },
      { value: "Europe/Paris", label: "France - Paris" },
      { value: "Europe/Berlin", label: "Germany - Berlin" },
    ],
  },
  {
    group: "Middle East & South Asia",
    zones: [
      { value: "Asia/Dubai", label: "UAE - Dubai" },
      { value: "Asia/Riyadh", label: "Saudi Arabia - Riyadh" },
      { value: "Asia/Qatar", label: "Qatar - Doha" },
      { value: "Asia/Karachi", label: "Pakistan - Karachi" },
      { value: "Asia/Kolkata", label: "India - Kolkata" },
    ],
  },
  {
    group: "Asia Pacific",
    zones: [
      { value: "Asia/Singapore", label: "Singapore" },
      { value: "Asia/Hong_Kong", label: "Hong Kong" },
      { value: "Asia/Tokyo", label: "Japan - Tokyo" },
      { value: "Australia/Sydney", label: "Australia - Sydney" },
      { value: "Pacific/Auckland", label: "New Zealand - Auckland" },
    ],
  },
];

interface MarketingContextValue {
  accounts: MarketingAccount[];
  loadingAccounts: boolean;
  selectedAccountId: string | null;
  selectedAccount: MarketingAccount | null;
  setSelectedAccountId: (value: string | null) => void;
  credentialsForm: {
    userId: string;
    pageId: string;
    pageName: string;
    accessToken: string;
    verify: boolean;
  };
  setCredentialsForm: Dispatch<SetStateAction<{
    userId: string;
    pageId: string;
    pageName: string;
    accessToken: string;
    verify: boolean;
  }>>;
  scheduleForm: {
    userId: string;
    timezone: string;
    times: string[];
  };
  setScheduleForm: Dispatch<SetStateAction<{
    userId: string;
    timezone: string;
    times: string[];
  }>>;
  scheduleMeta: MarketingSchedule | null;
  manualPrompt: string;
  setManualPrompt: Dispatch<SetStateAction<string>>;
  overridesInput: string;
  setOverridesInput: Dispatch<SetStateAction<string>>;
  posts: MarketingPost[];
  postsLoading: boolean;
  refreshingPostId: string | null;
  commentsByPost: Record<string, PostCommentsSummary>;
  commentsLoading: Record<string, boolean>;
  deletingPostId: string | null;
  refreshAll: () => Promise<void>;
  handleManualCampaign: () => Promise<unknown>;
  handleScheduleSubmit: (event: React.FormEvent) => Promise<void>;
  handleCredentialsSubmit: (event: React.FormEvent) => Promise<void>;
  handleScheduleTimeChange: (index: number, value: string) => void;
  handleAddScheduleTime: () => void;
  handleRemoveScheduleTime: (index: number) => void;
  handleRefreshInsights: (postId: string) => Promise<void>;
  fetchCommentsForPost: (facebookPostId: string) => Promise<PostCommentsSummary | undefined>;
  deletePost: (facebookPostId: string) => Promise<boolean>;
  insightsSummary: CampaignSummary;
  publishing: boolean;
  savingSchedule: boolean;
  savingCredentials: boolean;
  lastRefreshedAt: Date | null;
  postsAutoRefreshIntervalMs: number;
}

const MarketingContext = createContext<MarketingContextValue | undefined>(undefined);

export function MarketingProvider({ children }: { children: React.ReactNode }) {
  const [accounts, setAccounts] = useState<MarketingAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [credentialsForm, setCredentialsForm] = useState({
    userId: "",
    pageId: "",
    pageName: "",
    accessToken: "",
    verify: true,
  });
  const [scheduleForm, setScheduleForm] = useState({
    userId: "",
    timezone: "UTC",
    times: defaultTimes,
  });
  const [scheduleMeta, setScheduleMeta] = useState<MarketingSchedule | null>(null);
  const [manualPrompt, setManualPrompt] = useState("");
  const [overridesInput, setOverridesInput] = useState("{}");
  const [posts, setPosts] = useState<MarketingPost[]>([]);
  const [commentsByPost, setCommentsByPost] = useState<Record<string, PostCommentsSummary>>({});
  const [commentsLoading, setCommentsLoading] = useState<Record<string, boolean>>({});
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [refreshingPostId, setRefreshingPostId] = useState<string | null>(null);
  const [postsLoading, setPostsLoading] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);
  const [deletingPostId, setDeletingPostId] = useState<string | null>(null);

  const postsAutoRefreshIntervalMs = 30000;

  const triggerConfetti = useCallback(() => {
    const defaults = { origin: { y: 0.65 } };

    confetti({ ...defaults, particleCount: 160, spread: 70 });
    confetti({ ...defaults, particleCount: 120, angle: 120, spread: 55, origin: { x: 0.25, y: 0.7 } });
    confetti({ ...defaults, particleCount: 120, angle: 60, spread: 55, origin: { x: 0.75, y: 0.7 } });
  }, []);

  const fetchAccounts = useCallback(async () => {
    setLoadingAccounts(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/marketing/accounts`);
      const accountsData: MarketingAccount[] = response.data.accounts ?? [];
      setAccounts(accountsData);

      if (accountsData.length > 0 && !selectedAccountId) {
        setSelectedAccountId(accountsData[0].account_id);
      }

      const matchingAccount = accountsData.find((account) => account.account_id === selectedAccountId);
      const fallbackAccount = accountsData[0];

      if (matchingAccount || fallbackAccount) {
        const activeAccount = matchingAccount ?? fallbackAccount;
        setCredentialsForm((prev) => ({
          ...prev,
          userId: activeAccount.user_id || prev.userId,
          pageId: activeAccount.page_id || prev.pageId,
          pageName: activeAccount.page_name || prev.pageName,
        }));
      }
    } catch (error) {
      console.error("Failed to load marketing accounts", error);
      toast.error("Unable to fetch marketing accounts");
    } finally {
      setLoadingAccounts(false);
    }
  }, [selectedAccountId]);

  const fetchSchedule = useCallback(
    async (accountId: string) => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/marketing/accounts/${accountId}/schedule`);
        const schedule: MarketingSchedule = response.data.schedule;
        setScheduleMeta(schedule);
        setScheduleForm({
          userId: schedule.user_id || credentialsForm.userId,
          timezone: schedule.timezone || "UTC",
          times: Array.isArray(schedule.times) && schedule.times.length > 0 ? schedule.times : defaultTimes,
        });
      } catch (error) {
        if (axios.isAxiosError(error) && error.response?.status === 404) {
          setScheduleMeta(null);
          setScheduleForm((prev) => ({
            userId: prev.userId || credentialsForm.userId,
            timezone: "UTC",
            times: defaultTimes,
          }));
        } else {
          console.error("Failed to load schedule", error);
          toast.error("Unable to fetch schedule");
        }
      }
    },
    [credentialsForm.userId],
  );

  const fetchPosts = useCallback(
    async (accountId: string) => {
      setPostsLoading(true);
      try {
        const response = await axios.get(`${API_BASE_URL}/api/marketing/accounts/${accountId}/posts`, {
          params: { limit: 20 },
        });
        setPosts(response.data.posts || []);
      } catch (error) {
        console.error("Failed to load marketing posts", error);
        toast.error("Unable to fetch marketing posts");
      } finally {
        setPostsLoading(false);
      }
    },
    [],
  );

  const refreshAll = useCallback(async () => {
    try {
      await fetchAccounts();
      if (selectedAccountId) {
        await Promise.all([fetchSchedule(selectedAccountId), fetchPosts(selectedAccountId)]);
      }
    } finally {
      setLastRefreshedAt(new Date());
    }
  }, [fetchAccounts, fetchSchedule, fetchPosts, selectedAccountId]);

  const parseOverridesInput = useCallback((): Record<string, unknown> => {
    const raw = overridesInput.trim();
    if (!raw) {
      return {};
    }

    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
      throw new Error("Overrides JSON must be an object");
    } catch (jsonError) {
      const result: Record<string, unknown> = {};
      const segments = raw.replace(/;/g, "\n").split(/\n+/);

      for (const segment of segments) {
        const chunk = segment.trim();
        if (!chunk) {
          continue;
        }

        let key: string | undefined;
        let value: string | undefined;

        if (chunk.includes(":")) {
          const [k, ...rest] = chunk.split(":");
          key = k?.trim();
          value = rest.join(":").trim();
        } else if (chunk.includes("=")) {
          const [k, ...rest] = chunk.split("=");
          key = k?.trim();
          value = rest.join("=").trim();
        }

        if (!key || !value) {
          toast.error("Overrides must be JSON or key:value pairs (e.g. theme: summer)");
          throw jsonError instanceof Error ? jsonError : new Error("Invalid overrides format");
        }

        result[key] = value;
      }

      return result;
    }
  }, [overridesInput]);

  const handleManualCampaign = useCallback(async () => {
    if (!selectedAccountId) {
      toast.error("Select an account first");
      return Promise.reject(new Error("No account"));
    }
    if (!scheduleForm.userId) {
      toast.error("Associate a user ID to launch campaigns");
      return Promise.reject(new Error("Missing user id"));
    }
    setPublishing(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/campaign`, {
        user_id: scheduleForm.userId,
        prompt: manualPrompt || undefined,
        overrides: parseOverridesInput(),
      });
      const result = response.data.result;
      toast.success("Campaign published to Facebook");
      triggerConfetti();
      setManualPrompt("");
      await fetchPosts(selectedAccountId);
      return result;
    } catch (error) {
      console.error("Manual campaign failed", error);
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
      toast.error(detail || "Campaign run failed");
      throw error;
    } finally {
      setPublishing(false);
    }
  }, [fetchPosts, manualPrompt, parseOverridesInput, scheduleForm.userId, selectedAccountId, triggerConfetti]);

  const handleCredentialsSubmit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!credentialsForm.userId || !credentialsForm.pageId || !credentialsForm.accessToken) {
        toast.error("Please provide user ID, page ID, and access token");
        return;
      }
      setSavingCredentials(true);
      try {
        const response = await axios.post(`${API_BASE_URL}/api/marketing/accounts`, {
          user_id: credentialsForm.userId,
          page_id: credentialsForm.pageId,
          page_name: credentialsForm.pageName || undefined,
          access_token: credentialsForm.accessToken,
          verify: credentialsForm.verify,
        });
        const account: MarketingAccount = response.data.account;
        toast.success("Credentials saved");
        await fetchAccounts();
        setSelectedAccountId(account.account_id);
        setCredentialsForm((prev) => ({ ...prev, accessToken: "" }));
      } catch (error) {
        console.error("Failed to save credentials", error);
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
        toast.error(detail || "Could not save credentials");
      } finally {
        setSavingCredentials(false);
      }
    },
    [credentialsForm, fetchAccounts],
  );

  const handleScheduleTimeChange = useCallback((index: number, value: string) => {
    setScheduleForm((prev) => {
      const nextTimes = [...prev.times];
      nextTimes[index] = value;
      return { ...prev, times: nextTimes };
    });
  }, []);

  const handleAddScheduleTime = useCallback(() => {
    setScheduleForm((prev) => {
      if (prev.times.length >= MAX_SCHEDULE_TIMES) {
        return prev;
      }
      return { ...prev, times: [...prev.times, "17:30"] };
    });
  }, []);

  const handleRemoveScheduleTime = useCallback((index: number) => {
    setScheduleForm((prev) => {
      const nextTimes = prev.times.filter((_, idx) => idx !== index);
      return { ...prev, times: nextTimes.length > 0 ? nextTimes : ["09:00"] };
    });
  }, []);

  const handleScheduleSubmit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!selectedAccountId) {
        toast.error("Select an account first");
        return;
      }
      if (scheduleForm.times.some((time) => !time.trim())) {
        toast.error("Provide valid posting times");
        return;
      }
      setSavingSchedule(true);
      try {
        const response = await axios.put(`${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/schedule`, {
          user_id: scheduleForm.userId,
          times: scheduleForm.times,
          timezone_name: scheduleForm.timezone,
        });
        setScheduleMeta(response.data.schedule);
        toast.success("Schedule updated");
      } catch (error) {
        console.error("Failed to save schedule", error);
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
        toast.error(detail || "Could not save schedule");
      } finally {
        setSavingSchedule(false);
      }
    },
    [scheduleForm, selectedAccountId],
  );

  const handleRefreshInsights = useCallback(
    async (postId: string) => {
      if (!selectedAccountId) {
        return;
      }
      setRefreshingPostId(postId);
      try {
        await axios.post(`${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/posts/${postId}/insights`);
        await fetchPosts(selectedAccountId);
        toast.success("Insights refreshed");
      } catch (error) {
        console.error("Failed to refresh insights", error);
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
        toast.error(detail || "Could not refresh insights");
      } finally {
        setRefreshingPostId(null);
      }
    },
    [fetchPosts, selectedAccountId],
  );

  useEffect(() => {
    setCommentsByPost({});
    setCommentsLoading({});
  }, [selectedAccountId]);

  const fetchCommentsForPost = useCallback(
    async (facebookPostId: string) => {
      if (!selectedAccountId) {
        toast.error("Select an account first");
        return undefined;
      }

      setCommentsLoading((prev) => ({ ...prev, [facebookPostId]: true }));
      try {
        const response = await axios.get(
          `${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/posts/${facebookPostId}/comments`,
          {
            params: { limit: 50 },
          },
        );

        const summary: PostCommentsSummary = {
          comments: response.data.comments ?? [],
          totalCount: response.data.total_count ?? 0,
          hasNextPage: response.data.has_next_page ?? false,
          nextCursor: response.data.next_cursor ?? null,
          keywords: response.data.keywords ?? undefined,
          fetchedAt: response.data.fetched_at ?? new Date().toISOString(),
        };

        setCommentsByPost((prev) => ({ ...prev, [facebookPostId]: summary }));
        return summary;
      } catch (error) {
        console.error("Failed to fetch post comments", error);
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
        toast.error(detail || "Unable to load comments");
        return undefined;
      } finally {
        setCommentsLoading((prev) => ({ ...prev, [facebookPostId]: false }));
      }
    },
    [selectedAccountId],
  );

  const deletePost = useCallback(
    async (facebookPostId: string) => {
      if (!selectedAccountId) {
        toast.error("Select an account first");
        return false;
      }

      setDeletingPostId(facebookPostId);
      try {
        await axios.delete(
          `${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/posts/${facebookPostId}`,
          {
            params: { remove_remote: true },
          },
        );

        setPosts((prev) => prev.filter((post) => post.facebook_post_id !== facebookPostId));
        setCommentsByPost((prev) => {
          const next = { ...prev };
          delete next[facebookPostId];
          return next;
        });
        setCommentsLoading((prev) => {
          const next = { ...prev };
          delete next[facebookPostId];
          return next;
        });
        toast.success("Post deleted");
        return true;
      } catch (error) {
        console.error("Failed to delete marketing post", error);
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
        toast.error(detail || "Unable to delete post");
        return false;
      } finally {
        setDeletingPostId(null);
      }
    },
    [selectedAccountId],
  );

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    const intervalId = setInterval(() => {
      void refreshAll();
    }, postsAutoRefreshIntervalMs);
    return () => clearInterval(intervalId);
  }, [refreshAll, postsAutoRefreshIntervalMs]);

  useEffect(() => {
    if (!selectedAccountId) {
      return;
    }
    const account = accounts.find((item) => item.account_id === selectedAccountId);
    if (account) {
      setCredentialsForm((prev) => ({
        ...prev,
        userId: account.user_id,
        pageId: account.page_id,
        pageName: account.page_name || "",
        accessToken: "",
      }));
      setScheduleForm((prev) => ({
        ...prev,
        userId: account.user_id,
      }));
      void fetchSchedule(account.account_id);
      void fetchPosts(account.account_id);
    }
  }, [accounts, fetchPosts, fetchSchedule, selectedAccountId]);

  const insightsSummary = useMemo(() => {
    let reach = 0;
    let impressions = 0;
    let clicks = 0;
    let reactions = 0;
    let postsWithInsights = 0;

    posts.forEach((post) => {
      if (!post.insights) {
        return;
      }
      postsWithInsights += 1;
      reach += post.insights.reach || 0;
      impressions += post.insights.impressions || 0;
      clicks += post.insights.clicked || 0;
      const breakdown = post.insights.reactions || {};
      let reactionTotal = 0;
      for (const value of Object.values(breakdown)) {
        if (typeof value === "number") {
          reactionTotal += value;
        }
      }
      reactions += reactionTotal;
    });

    return {
      reach,
      impressions,
      clicks,
      reactions,
      postsWithInsights,
    };
  }, [posts]);

  const selectedAccount = useMemo(() => {
    if (!selectedAccountId) {
      return null;
    }
    return accounts.find((account) => account.account_id === selectedAccountId) ?? null;
  }, [accounts, selectedAccountId]);

  const value: MarketingContextValue = {
    accounts,
    loadingAccounts,
    selectedAccountId,
    selectedAccount,
    setSelectedAccountId,
    credentialsForm,
    setCredentialsForm,
    scheduleForm,
    setScheduleForm,
    scheduleMeta,
    manualPrompt,
    setManualPrompt,
    overridesInput,
    setOverridesInput,
    posts,
    postsLoading,
    refreshingPostId,
    commentsByPost,
    commentsLoading,
    deletingPostId,
    refreshAll,
    handleManualCampaign,
    handleScheduleSubmit,
    handleCredentialsSubmit,
    handleScheduleTimeChange,
    handleAddScheduleTime,
    handleRemoveScheduleTime,
    handleRefreshInsights,
    fetchCommentsForPost,
    deletePost,
    insightsSummary,
    publishing,
    savingSchedule,
    savingCredentials,
    lastRefreshedAt,
    postsAutoRefreshIntervalMs,
  };

  return <MarketingContext.Provider value={value}>{children}</MarketingContext.Provider>;
}

export function useMarketing() {
  const context = useContext(MarketingContext);
  if (!context) {
    throw new Error("useMarketing must be used within a MarketingProvider");
  }
  return context;
}

export function useFormattedLastRefreshed(lastRefreshedAt: Date | null) {
  return useMemo(() => {
    if (!lastRefreshedAt) {
      return "Syncing…";
    }
    return lastRefreshedAt.toLocaleTimeString();
  }, [lastRefreshedAt]);
}
