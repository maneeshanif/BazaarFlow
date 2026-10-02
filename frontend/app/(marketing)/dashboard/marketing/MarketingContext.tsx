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
  reply_metadata?: {
    reply_text: string;
    replied_at: string;
  };
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

interface GeneratedCampaignPostSummary {
  facebook?: unknown;
  post?: MarketingPost | CampaignDraftPost;
  [key: string]: unknown;
}

interface CampaignDraftPost {
  record_id?: string;
  message?: string;
  image_url?: string | null;
  hashtags?: string[];
  product_sku?: string | null;
  call_to_action?: string | null;
  extra?: Record<string, unknown> | null;
  raw_campaign?: Record<string, unknown> | null;
  title?: string | null;
}

type GeneratedCampaignPost = GeneratedCampaignPostSummary | CampaignDraftPost | MarketingPost;

interface GeneratedCampaignResult {
  campaign_id: string;
  strategy_summary?: string;
  posts?: GeneratedCampaignPost[];
}

interface ScheduledPostDraft {
  index: number;
  post: CampaignDraftPost;
  scheduledAt: string;
}

export interface ScheduledPostRecord {
  scheduled_post_id: string;
  scheduled_campaign_id: string;
  account_id: string;
  user_id: string;
  campaign_post_index: number;
  post_payload: {
    message?: string;
    image_url?: string | null;
    hashtags?: string[];
    product_sku?: string | null;
    call_to_action?: string | null;
    [key: string]: unknown;
  };
  scheduled_at: string;
  status: "pending" | "posted" | "cancelled" | "failed" | string;
  facebook_post_id?: string | null;
  error?: string | null;
}

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
export const MAX_SCHEDULE_TIMES = 3;
export const defaultTimes = ["09:00", "13:00"];
export const DEV_USER_ID = process.env.NEXT_PUBLIC_DEV_USER_ID || "dev_admin";

const padTimeUnit = (value: number): string => value.toString().padStart(2, "0");
const clamp = (value: number, min: number, max: number): number => Math.min(Math.max(value, min), max);

const normaliseScheduleTime = (rawValue: string): string => {
  const raw = (rawValue ?? "").trim();
  if (!raw) {
    return "";
  }

  const ampmMatch = raw.match(/^(\d{1,2}):(\d{1,2})\s*(AM|PM)$/i);
  if (ampmMatch) {
    let hour = clamp(parseInt(ampmMatch[1], 10) || 0, 1, 12);
    const minute = clamp(parseInt(ampmMatch[2], 10) || 0, 0, 59);
    const period = ampmMatch[3].toUpperCase();
    if (period === "PM" && hour !== 12) {
      hour += 12;
    }
    if (period === "AM" && hour === 12) {
      hour = 0;
    }
    return `${padTimeUnit(hour)}:${padTimeUnit(minute)}`;
  }

  const twentyFourMatch = raw.match(/^(\d{1,2}):(\d{1,2})$/);
  if (twentyFourMatch) {
    const hour = clamp(parseInt(twentyFourMatch[1], 10) || 0, 0, 23);
    const minute = clamp(parseInt(twentyFourMatch[2], 10) || 0, 0, 59);
    return `${padTimeUnit(hour)}:${padTimeUnit(minute)}`;
  }

  return raw;
};

const normaliseDraftPost = (candidate: unknown, index: number): CampaignDraftPost => {
  if (!candidate || typeof candidate !== "object") {
    return {
      record_id: `draft_${index}`,
      message: "",
      hashtags: [],
      image_url: null,
      extra: null,
    };
  }

  const raw = candidate as Record<string, unknown>;
  const hashtags = Array.isArray(raw.hashtags) ? raw.hashtags.map((tag) => String(tag)) : [];
  const imageUrl = typeof raw.image_url === "string" ? raw.image_url : null;
  const productSku = typeof raw.product_sku === "string" ? raw.product_sku : null;
  const callToAction = typeof raw.call_to_action === "string" ? raw.call_to_action : null;
  const extra = raw.extra && typeof raw.extra === "object" && !Array.isArray(raw.extra) ? (raw.extra as Record<string, unknown>) : null;
  const rawCampaign = raw.raw_campaign && typeof raw.raw_campaign === "object" && !Array.isArray(raw.raw_campaign)
    ? (raw.raw_campaign as Record<string, unknown>)
    : null;

  return {
    record_id: typeof raw.record_id === "string" ? raw.record_id : `draft_${index}`,
    message: typeof raw.message === "string" ? raw.message : "",
    image_url: imageUrl,
    hashtags,
    product_sku: productSku,
    call_to_action: callToAction,
    extra,
    raw_campaign: rawCampaign,
    title: typeof raw.title === "string" ? raw.title : typeof raw.angle === "string" ? raw.angle : null,
  };
};

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
  replyingCommentIds: Record<string, boolean>;
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
  replyToComment: (facebookPostId: string, comment: MarketingComment) => Promise<boolean>;
  insightsSummary: CampaignSummary;
  publishing: boolean;
  savingSchedule: boolean;
  savingCredentials: boolean;
  lastRefreshedAt: Date | null;
  postsAutoRefreshIntervalMs: number;
  lastGeneratedCampaign: GeneratedCampaignResult | null;
  postCount: number;
  setPostCount: Dispatch<SetStateAction<number>>;
  schedulePrompt: string;
  setSchedulePrompt: Dispatch<SetStateAction<string>>;
  previewedScheduledCampaign: GeneratedCampaignResult | null;
  scheduledPostsDraft: ScheduledPostDraft[];
  previewingScheduledCampaign: boolean;
  savingScheduledCampaign: boolean;
  setScheduledPostsDraft: Dispatch<SetStateAction<ScheduledPostDraft[]>>;
  previewScheduledCampaign: () => Promise<GeneratedCampaignResult | null>;
  createScheduledCampaign: () => Promise<{
    ok: boolean;
    campaign?: unknown;
    posts?: unknown;
  } | null>;
  scheduledPosts: ScheduledPostRecord[];
  scheduledPostsLoading: boolean;
  updateScheduledPost: (
    scheduledPostId: string,
    updates: {
      message?: string;
      hashtags?: string[];
      call_to_action?: string | null;
      image_url?: string | null;
      product_sku?: string | null;
      scheduled_at?: string;
    },
  ) => Promise<ScheduledPostRecord | null>;
  deleteScheduledPost: (scheduledPostId: string) => Promise<boolean>;
  deleteScheduledCampaign: (scheduledCampaignId: string) => Promise<boolean>;
}

const MarketingContext = createContext<MarketingContextValue | undefined>(undefined);

export function MarketingProvider({ children }: { children: React.ReactNode }) {
  const [accounts, setAccounts] = useState<MarketingAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [credentialsForm, setCredentialsForm] = useState({
    userId: DEV_USER_ID,
    pageId: "",
    pageName: "",
    accessToken: "",
    verify: true,
  });
  const [scheduleForm, setScheduleForm] = useState({
    userId: DEV_USER_ID,
    timezone: "UTC",
    times: defaultTimes,
  });
  const [scheduleMeta, setScheduleMeta] = useState<MarketingSchedule | null>(null);
  const [manualPrompt, setManualPrompt] = useState("");
  const [overridesInput, setOverridesInput] = useState("{}");
  const [posts, setPosts] = useState<MarketingPost[]>([]);
  const [commentsByPost, setCommentsByPost] = useState<Record<string, PostCommentsSummary>>({});
  const [commentsLoading, setCommentsLoading] = useState<Record<string, boolean>>({});
  const [replyingCommentIds, setReplyingCommentIds] = useState<Record<string, boolean>>({});
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [refreshingPostId, setRefreshingPostId] = useState<string | null>(null);
  const [postsLoading, setPostsLoading] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);
  const [deletingPostId, setDeletingPostId] = useState<string | null>(null);
  const [lastGeneratedCampaign, setLastGeneratedCampaign] = useState<GeneratedCampaignResult | null>(null);
  const [postCount, setPostCount] = useState<number>(3);
  const [schedulePrompt, setSchedulePrompt] = useState<string>("");
  const [previewedScheduledCampaign, setPreviewedScheduledCampaign] =
    useState<GeneratedCampaignResult | null>(null);
  const [scheduledPostsDraft, setScheduledPostsDraft] = useState<ScheduledPostDraft[]>([]);
  const [previewingScheduledCampaign, setPreviewingScheduledCampaign] = useState(false);
  const [savingScheduledCampaign, setSavingScheduledCampaign] = useState(false);
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPostRecord[]>([]);
  const [scheduledPostsLoading, setScheduledPostsLoading] = useState(false);

  const postsAutoRefreshIntervalMs = 30000;

  const selectedAccount = useMemo(() => {
    if (!selectedAccountId) {
      return null;
    }
    return accounts.find((account) => account.account_id === selectedAccountId) ?? null;
  }, [accounts, selectedAccountId]);

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

  const fetchScheduledActivity = useCallback(
    async (accountId: string) => {
      setScheduledPostsLoading(true);
      try {
        const response = await axios.get(
          `${API_BASE_URL}/api/marketing/accounts/${accountId}/scheduled/activity`,
        );
        const records: ScheduledPostRecord[] = response.data.posts ?? [];
        setScheduledPosts(records);
      } catch (error) {
        console.error("Failed to load scheduled activity", error);
        toast.error("Unable to fetch scheduled activity");
      } finally {
        setScheduledPostsLoading(false);
      }
    },
    [],
  );

  const updateScheduledPost = useCallback(
    async (
      scheduledPostId: string,
      updates: {
        message?: string;
        hashtags?: string[];
        call_to_action?: string | null;
        image_url?: string | null;
        product_sku?: string | null;
        scheduled_at?: string;
      },
    ): Promise<ScheduledPostRecord | null> => {
      if (!selectedAccountId) {
        toast.error("Select an account first");
        return null;
      }

      try {
        const response = await axios.patch(
          `${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/scheduled/posts/${scheduledPostId}`,
          {
            message: updates.message,
            hashtags: updates.hashtags,
            call_to_action: updates.call_to_action ?? undefined,
            image_url: updates.image_url ?? undefined,
            product_sku: updates.product_sku ?? undefined,
            scheduled_at: updates.scheduled_at,
          },
        );

        const updated: ScheduledPostRecord = response.data.post;
        setScheduledPosts((prev) =>
          prev.map((record) => (record.scheduled_post_id === scheduledPostId ? updated : record)),
        );
        toast.success("Scheduled post updated");
        return updated;
      } catch (error) {
        console.error("Failed to update scheduled post", error);
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
        toast.error(detail || "Unable to update scheduled post");
        return null;
      }
    },
    [selectedAccountId],
  );

  const deleteScheduledPost = useCallback(
    async (scheduledPostId: string): Promise<boolean> => {
      if (!selectedAccountId) {
        toast.error("Select an account first");
        return false;
      }

      try {
        await axios.delete(
          `${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/scheduled/posts/${scheduledPostId}`,
        );
        setScheduledPosts((prev) => prev.filter((record) => record.scheduled_post_id !== scheduledPostId));
        toast.success("Scheduled post removed");
        return true;
      } catch (error) {
        console.error("Failed to delete scheduled post", error);
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
        toast.error(detail || "Unable to delete scheduled post");
        return false;
      }
    },
    [selectedAccountId],
  );

  const deleteScheduledCampaign = useCallback(
    async (scheduledCampaignId: string): Promise<boolean> => {
      if (!selectedAccountId) {
        toast.error("Select an account first");
        return false;
      }

      try {
        await axios.delete(
          `${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/scheduled/campaigns/${scheduledCampaignId}`,
        );
        setScheduledPosts((prev) => prev.filter((record) => record.scheduled_campaign_id !== scheduledCampaignId));
        toast.success("Scheduled campaign removed");
        return true;
      } catch (error) {
        console.error("Failed to delete scheduled campaign", error);
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
        toast.error(detail || "Unable to delete scheduled campaign");
        return false;
      }
    },
    [selectedAccountId],
  );

  const refreshAll = useCallback(async () => {
    try {
      await fetchAccounts();
      if (selectedAccountId) {
        await Promise.all([
          fetchSchedule(selectedAccountId),
          fetchPosts(selectedAccountId),
          fetchScheduledActivity(selectedAccountId),
        ]);
      }
    } finally {
      setLastRefreshedAt(new Date());
    }
  }, [fetchAccounts, fetchSchedule, fetchPosts, fetchScheduledActivity, selectedAccountId]);

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
    const userId = scheduleForm.userId || DEV_USER_ID;
    setPublishing(true);
    try {
  const baseOverrides = parseOverridesInput();
  const clampedPostCount = clamp(postCount, 1, 6);
      const response = await axios.post(`${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/campaign`, {
        user_id: userId,
        prompt: manualPrompt || undefined,
        overrides: { ...baseOverrides, post_count: clampedPostCount },
      });
      const result: GeneratedCampaignResult = response.data.result;

      const postCountFromResult = Array.isArray(result.posts) ? result.posts.length : 0;
      toast.success(
        postCountFromResult > 1
          ? `Campaign published to Facebook with ${postCountFromResult} posts`
          : "Campaign published to Facebook",
      );
      setLastGeneratedCampaign(result);
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
  }, [fetchPosts, manualPrompt, parseOverridesInput, scheduleForm.userId, selectedAccountId, triggerConfetti, postCount]);

  const previewScheduledCampaign = useCallback(async () => {
    if (!selectedAccountId) {
      toast.error("Select an account first");
      return null;
    }
    const userId = scheduleForm.userId || DEV_USER_ID;
    if (!schedulePrompt.trim()) {
      toast.error("Add a prompt for the scheduled campaign");
      return Promise.reject(new Error("Missing prompt"));
    }

    setPreviewingScheduledCampaign(true);
    try {
      const baseOverrides = parseOverridesInput();
      const clampedPostCount = clamp(postCount, 1, 6);
      const response = await axios.post(
        `${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/scheduled/preview`,
        {
          user_id: userId,
          prompt: schedulePrompt,
          post_count: clampedPostCount,
          overrides: { ...baseOverrides, post_count: clampedPostCount },
        },
      );

      const result: GeneratedCampaignResult = response.data.campaign;
      setPreviewedScheduledCampaign(result);

      const drafts: ScheduledPostDraft[] = (result.posts || []).map((item, index) => {
        const payload =
          item && typeof item === "object" && "post" in item && item.post
            ? (item.post as CampaignDraftPost | MarketingPost)
            : item;
        return {
          index,
          post: normaliseDraftPost(payload, index),
          scheduledAt: "",
        };
      });
      setScheduledPostsDraft(drafts);
      toast.success("Draft posts generated. Pick times and schedule them.");
      return result;
    } catch (error) {
      console.error("Scheduled preview failed", error);
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
      toast.error(detail || "Could not generate scheduled campaign preview");
      throw error;
    } finally {
      setPreviewingScheduledCampaign(false);
    }
  }, [parseOverridesInput, postCount, scheduleForm.userId, schedulePrompt, selectedAccountId]);

  const createScheduledCampaign = useCallback(async () => {
    if (!selectedAccountId) {
      toast.error("Select an account first");
      return null;
    }
    const userId = scheduleForm.userId || DEV_USER_ID;
    if (!previewedScheduledCampaign || scheduledPostsDraft.length === 0) {
      toast.error("Generate posts first, then pick times");
      return Promise.reject(new Error("No drafts"));
    }

    const missingTime = scheduledPostsDraft.find((draft) => !draft.scheduledAt);
    if (missingTime) {
      toast.error("Pick a scheduled time for every post");
      return Promise.reject(new Error("Missing scheduled time"));
    }

    setSavingScheduledCampaign(true);
    try {
      const baseOverrides = parseOverridesInput();
      const payloadPosts = scheduledPostsDraft.map((draft, index) => ({
        post_payload: {
          message: draft.post.message ?? "",
          image_url: draft.post.image_url ?? undefined,
          hashtags: draft.post.hashtags ?? [],
          product_sku: draft.post.product_sku ?? undefined,
          call_to_action: draft.post.call_to_action ?? undefined,
          extra: draft.post.extra ?? undefined,
          raw_campaign: draft.post.raw_campaign ?? undefined,
          title: draft.post.title ?? undefined,
          record_id: draft.post.record_id ?? `draft_${index}`,
        },
        scheduled_at: draft.scheduledAt,
      }));

      const response = await axios.post(
        `${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/scheduled`,
        {
          user_id: userId,
          prompt: schedulePrompt,
          overrides: baseOverrides,
          posts: payloadPosts,
        },
      );

      const body = response.data as {
        ok: boolean;
        campaign?: unknown;
        posts?: unknown;
      };

      if (!body.ok) {
        toast.error("Failed to save scheduled campaign");
        return body;
      }

      toast.success("Scheduled campaign saved. Posts will go out automatically.");
      setPreviewedScheduledCampaign(null);
      setScheduledPostsDraft([]);
      setSchedulePrompt("");
      return body;
    } catch (error) {
      console.error("Create scheduled campaign failed", error);
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
      toast.error(detail || "Could not save scheduled campaign");
      throw error;
    } finally {
      setSavingScheduledCampaign(false);
    }
  }, [parseOverridesInput, previewedScheduledCampaign, scheduleForm.userId, schedulePrompt, scheduledPostsDraft, selectedAccountId]);

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
      nextTimes[index] = normaliseScheduleTime(value);
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

      const derivedUserId =
        scheduleForm.userId.trim() || selectedAccount?.user_id || DEV_USER_ID;

      const timezoneValue = scheduleForm.timezone.trim();
      if (!timezoneValue) {
        toast.error("Pick a timezone before saving");
        return;
      }

      const normalisedTimes = scheduleForm.times
        .map((time) => normaliseScheduleTime(time))
        .filter((time) => !!time);

      if (normalisedTimes.length === 0) {
        toast.error("Provide at least one posting time");
        return;
      }

      setScheduleForm((prev) => ({
        ...prev,
        userId: derivedUserId,
        timezone: timezoneValue,
        times: normalisedTimes,
      }));

      setSavingSchedule(true);
      try {
        const response = await axios.put(`${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/schedule`, {
          user_id: derivedUserId,
          times: normalisedTimes,
          timezone_name: timezoneValue,
        });
        const savedSchedule: MarketingSchedule = response.data.schedule;
        setScheduleMeta(savedSchedule);
        setScheduleForm((prev) => ({
          ...prev,
          userId: savedSchedule?.user_id || derivedUserId,
          timezone: savedSchedule?.timezone || timezoneValue,
          times: Array.isArray(savedSchedule?.times) && savedSchedule.times.length > 0
            ? savedSchedule.times
            : normalisedTimes,
        }));
        toast.success("Schedule updated");
      } catch (error) {
        console.error("Failed to save schedule", error);
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
        toast.error(detail || "Could not save schedule");
      } finally {
        setSavingSchedule(false);
      }
    },
    [scheduleForm, selectedAccount, selectedAccountId],
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
    setReplyingCommentIds({});
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

  const replyToComment = useCallback(
    async (facebookPostId: string, comment: MarketingComment) => {
      if (!selectedAccountId) {
        toast.error("Select an account first");
        return false;
      }
      const commentId = comment.comment_id;
      setReplyingCommentIds((prev) => ({ ...prev, [commentId]: true }));
      try {
        const response = await axios.post(
          `${API_BASE_URL}/api/marketing/accounts/${selectedAccountId}/posts/${facebookPostId}/comments/${commentId}/reply`,
          {
            comment_message: comment.message || undefined,
            commenter_name: comment.from_user?.name || comment.from_user?.username || undefined,
          },
        );

        const replyMetadata = response.data?.reply_metadata;
        const replyText: string = replyMetadata?.reply_text || response.data?.reply || "Thanks for reaching out!";
        const repliedAt = replyMetadata?.replied_at || new Date().toISOString();

        setCommentsByPost((prev) => {
          const summary = prev[facebookPostId];
          if (!summary) {
            return prev;
          }
          const updatedComments = summary.comments.map((item) =>
            item.comment_id === commentId
              ? {
                  ...item,
                  reply_metadata: {
                    reply_text: replyText,
                    replied_at: repliedAt,
                  },
                }
              : item,
          );
          return {
            ...prev,
            [facebookPostId]: {
              ...summary,
              comments: updatedComments,
            },
          };
        });

        toast.success("Reply sent on Facebook");
        return true;
      } catch (error) {
        console.error("Failed to reply to Facebook comment", error);
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
        toast.error(detail || "Unable to send reply");
        return false;
      } finally {
        setReplyingCommentIds((prev) => {
          const next = { ...prev };
          delete next[commentId];
          return next;
        });
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
    replyingCommentIds,
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
    replyToComment,
    insightsSummary,
    publishing,
    savingSchedule,
    savingCredentials,
    lastRefreshedAt,
    postsAutoRefreshIntervalMs,
    lastGeneratedCampaign,
    postCount,
    setPostCount,
    schedulePrompt,
    setSchedulePrompt,
    previewedScheduledCampaign,
    scheduledPostsDraft,
    previewingScheduledCampaign,
    savingScheduledCampaign,
    setScheduledPostsDraft,
    previewScheduledCampaign,
    createScheduledCampaign,
  scheduledPosts,
  scheduledPostsLoading,
  updateScheduledPost,
    deleteScheduledPost,
    deleteScheduledCampaign,
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
