"use client";

import { useEffect, useMemo, useState } from "react";
import { Image as ImageIcon, Link2, Loader2, Megaphone, MessageCircle, RefreshCcw, Send, Trash2 } from "lucide-react";

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
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

import { useMarketing } from "../MarketingContext";

export default function MarketingActivityPage() {
  const {
    posts,
    postsLoading,
    refreshingPostId,
    handleRefreshInsights,
    refreshAll,
    selectedAccount,
    loadingAccounts,
    commentsByPost,
    commentsLoading,
    fetchCommentsForPost,
    deletePost,
    deletingPostId,
    replyToComment,
    replyingCommentIds,
    lastGeneratedCampaign,
  } = useMarketing();

  const [activePostId, setActivePostId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [postPendingDelete, setPostPendingDelete] = useState<string | null>(null);

  const campaigns = useMemo(() => {
    const groups = new Map<string, typeof posts>();

    posts.forEach((post) => {
      const extra = (post.extra as Record<string, unknown> | undefined) ?? {};
      const rawCampaignId = (extra.campaign_id ?? (extra.campaign as Record<string, unknown> | undefined)?.campaign_id) as
        | string
        | undefined;
      const campaignId = typeof rawCampaignId === "string" && rawCampaignId.trim() ? rawCampaignId : "__solo__";
      if (!groups.has(campaignId)) {
        groups.set(campaignId, []);
      }
      groups.get(campaignId)!.push(post);
    });

    const campaignBlocks = Array.from(groups.entries()).map(([campaignId, groupPosts]) => {
      const sorted = [...groupPosts].sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
      const first = sorted[0];
      const extra = (first.extra as Record<string, unknown> | undefined) ?? {};
      const rawStrategy =
        (extra.strategy_summary as string | undefined) ||
        (extra.campaign as Record<string, unknown> | undefined)?.strategy_summary;
      const strategySummary = typeof rawStrategy === "string" ? rawStrategy : undefined;
      return {
        id: campaignId,
        posts: sorted,
        strategySummary,
      };
    });

    // Put non-campaign/single posts at the end for clarity
    const multi = campaignBlocks.filter((block) => block.id !== "__solo__" && block.posts.length > 1);
    const solo = campaignBlocks.filter((block) => block.id === "__solo__" || block.posts.length === 1);
    return [...multi, ...solo];
  }, [posts]);

  const orderedPosts = useMemo(
    () => [...posts].sort((a, b) => (a.created_at < b.created_at ? 1 : -1)),
    [posts],
  );

  const activePost = useMemo(() => {
    if (!activePostId) {
      return null;
    }
    return posts.find((post) => post.facebook_post_id === activePostId) ?? null;
  }, [activePostId, posts]);

  const activeSummary = activePostId ? commentsByPost[activePostId] : undefined;
  const activeCommentsLoading = activePostId ? Boolean(commentsLoading[activePostId]) : false;

  const pendingDeletePost = useMemo(() => {
    if (!postPendingDelete) {
      return null;
    }
    return posts.find((post) => post.facebook_post_id === postPendingDelete) ?? null;
  }, [postPendingDelete, posts]);

  const isDeletingPendingPost = postPendingDelete ? deletingPostId === postPendingDelete : false;

  useEffect(() => {
    if (!activePostId) {
      return;
    }
    if (activeSummary || activeCommentsLoading) {
      return;
    }
    void fetchCommentsForPost(activePostId);
  }, [activePostId, activeCommentsLoading, activeSummary, fetchCommentsForPost]);

  const openDeleteDialog = (postId: string) => {
    setPostPendingDelete(postId);
    setDeleteDialogOpen(true);
  };

  const confirmDeletePost = async () => {
    if (!postPendingDelete) {
      return;
    }
    const removed = await deletePost(postPendingDelete);
    if (removed && activePostId === postPendingDelete) {
      setActivePostId(null);
    }
    if (removed) {
      setDeleteDialogOpen(false);
      setPostPendingDelete(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Activity</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Review every campaign BazaarFlow publishes and keep insights fresh.
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => void refreshAll()}
          disabled={postsLoading || loadingAccounts}
          className="self-start md:self-auto"
        >
          <RefreshCcw className="mr-2 h-4 w-4" />
          Sync now
        </Button>
      </div>

      {selectedAccount && (
        <Badge variant="outline" className="text-xs">
          {selectedAccount.page_name || "Unnamed page"} • {selectedAccount.page_id}
        </Badge>
      )}

      <Card className="border-2 border-slate-200 dark:border-slate-700 shadow-sm">
        <CardContent className="space-y-4 pt-6">
          {postsLoading ? (
            <div className="flex h-40 items-center justify-center text-slate-500">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading campaigns...
            </div>
          ) : orderedPosts.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center text-slate-500">
              <Megaphone className="mb-2 h-8 w-8" />
              No campaigns have been recorded yet.
            </div>
          ) : (
            <div className="space-y-4">
              {campaigns.map((campaignBlock) => {
                const isAdHoc = campaignBlock.id === "__solo__";
                const label = isAdHoc
                  ? campaignBlock.posts.length > 1
                    ? `Ad-hoc group (${campaignBlock.posts.length} posts)`
                    : "Single post"
                  : `Campaign ${campaignBlock.id.slice(0, 8)} • ${campaignBlock.posts.length} post${
                      campaignBlock.posts.length > 1 ? "s" : ""
                    }`;

                return (
                  <div
                    key={campaignBlock.id}
                    className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900/40"
                  >
                    <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                      <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                        <Badge variant="outline" className="bg-white/60 dark:bg-slate-900/40">
                          {label}
                        </Badge>
                        {campaignBlock.strategySummary && (
                          <span className="line-clamp-1 text-[11px] text-slate-500 dark:text-slate-400">
                            {campaignBlock.strategySummary}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="space-y-3">
                      {campaignBlock.posts.map((post) => {
                        const campaign = (post.extra as Record<string, unknown> | undefined)?.campaign as
                          | Record<string, unknown>
                          | undefined;
                        const hashtags: string[] = (campaign?.hashtags as string[] | undefined) ?? post.hashtags ?? [];
                        const angleSource = campaign?.angle ?? post.angle;
                        const campaignAngle = typeof angleSource === "string" ? angleSource : undefined;
                        const reactionTotal = Object.values(post.insights?.reactions ?? {}).reduce<number>(
                          (accumulator, value) => accumulator + (typeof value === "number" ? value : 0),
                          0,
                        );
                        const isRefreshing = refreshingPostId === post.facebook_post_id;
                        const cachedSummary = commentsByPost[post.facebook_post_id];
                        const commentsCount = cachedSummary?.totalCount ?? post.insights?.comments_count ?? 0;
                        const isLoadingComments = Boolean(commentsLoading[post.facebook_post_id]);
                        const isDeleting = deletingPostId === post.facebook_post_id;

                        return (
                          <div
                            key={post.record_id}
                            className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800"
                          >
                    <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {post.source === "scheduled" ? "Scheduled" : "Manual"}
                          </Badge>
                          <span className="text-xs text-slate-500">{new Date(post.created_at).toLocaleString()}</span>
                        </div>
                        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700 dark:text-slate-200">
                          {post.message}
                        </p>
                        {hashtags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {hashtags.map((tag: string) => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                #{tag.replace(/^#/g, "")}
                              </Badge>
                            ))}
                          </div>
                        )}
                        <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                          <span>Facebook ID: {post.facebook_post_id}</span>
                          {campaignAngle && <span>Angle: {campaignAngle}</span>}
                          {post.product_sku && <span>SKU: {post.product_sku}</span>}
                        </div>
                      </div>
                      {post.image_url && (
                        <div className="relative mt-3 md:mt-0">
                          <div className="h-40 w-40 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-100">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={post.image_url} alt="Campaign creative" className="h-full w-full object-cover" />
                          </div>
                          <Badge
                            className="absolute -top-2 -right-2 bg-white text-slate-600 border-slate-200 shadow"
                            variant="outline"
                          >
                            <ImageIcon className="mr-1 h-3 w-3" />
                            Creative
                          </Badge>
                        </div>
                      )}
                    </div>

                    <div className="mt-3 flex flex-wrap items-center gap-3">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleRefreshInsights(post.facebook_post_id)}
                        disabled={isRefreshing}
                      >
                        {isRefreshing ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCcw className="mr-2 h-4 w-4" />
                        )}
                        Refresh Insights
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setActivePostId(post.facebook_post_id)}
                        disabled={isLoadingComments}
                      >
                        {isLoadingComments ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <MessageCircle className="mr-2 h-4 w-4" />
                        )}
                        View Comments
                        <span className="ml-1 text-xs text-slate-500">({commentsCount})</span>
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => openDeleteDialog(post.facebook_post_id)}
                        disabled={isDeleting}
                      >
                        {isDeleting ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="mr-2 h-4 w-4" />
                        )}
                        Delete Post
                      </Button>
                      <a
                        href={`https://www.facebook.com/${post.facebook_post_id.replace("_", "/posts/")}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                      >
                        <Link2 className="h-3 w-3" /> View on Facebook
                      </a>
                    </div>

                    {post.insights && (
                      <div className="mt-3 grid gap-3 text-xs text-slate-600 dark:text-slate-300 sm:grid-cols-4">
                        <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-700/60">
                          Reach
                          <div className="text-base font-semibold text-slate-900 dark:text-white">
                            {post.insights.reach?.toLocaleString() || "0"}
                          </div>
                        </div>
                        <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-700/60">
                          Impressions
                          <div className="text-base font-semibold text-slate-900 dark:text-white">
                            {post.insights.impressions?.toLocaleString() || "0"}
                          </div>
                        </div>
                        <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-700/60">
                          Clicks
                          <div className="text-base font-semibold text-slate-900 dark:text-white">
                            {post.insights.clicked?.toLocaleString() || "0"}
                          </div>
                        </div>
                        <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-700/60">
                          Reactions
                          <div className="text-base font-semibold text-slate-900 dark:text-white">
                            {reactionTotal.toLocaleString()}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Sheet
        open={Boolean(activePostId)}
        onOpenChange={(isOpen: boolean) => {
          if (!isOpen) {
            setActivePostId(null);
          }
        }}
      >
        <SheetContent side="right" className="flex h-full w-full flex-col gap-4 overflow-hidden sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>Post Comments</SheetTitle>
            <SheetDescription>
              {activePost ? `Published ${new Date(activePost.created_at).toLocaleString()}` : ""}
            </SheetDescription>
          </SheetHeader>
          {activePost && (
            <div className="flex flex-1 flex-col gap-3 overflow-hidden text-sm text-slate-700 dark:text-slate-200">
              <p className="rounded-lg bg-slate-100 p-3 text-slate-800 dark:bg-slate-900/40 dark:text-slate-100">
                {activePost.message}
              </p>
              {activeSummary?.keywords && activeSummary.keywords.length > 0 && (
                <div className="flex flex-wrap gap-2 text-xs">
                  {activeSummary.keywords.map((keyword) => (
                    <Badge key={keyword.keyword} variant="secondary">
                      #{keyword.keyword}
                      <span className="ml-1 text-[10px] text-slate-500">{keyword.count}</span>
                    </Badge>
                  ))}
                </div>
              )}
              <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                <span>
                  Total comments: {activeSummary?.totalCount ?? "?"}
                </span>
                {activeSummary?.fetchedAt && (
                  <span>Fetched {new Date(activeSummary.fetchedAt).toLocaleTimeString()}</span>
                )}
              </div>
              <div className="flex-1 overflow-y-auto pr-2">
                {activeCommentsLoading ? (
                  <div className="flex h-40 items-center justify-center text-slate-500">
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading comments...
                  </div>
                ) : activeSummary && activeSummary.comments.length > 0 ? (
                  <div className="space-y-3">
                    {activeSummary.comments.map((comment) => {
                      const authorName =
                        typeof comment.from_user?.name === "string"
                          ? comment.from_user.name
                          : comment.from_user?.username;
                      const isReplying = Boolean(replyingCommentIds[comment.comment_id]);
                      const replyMeta = comment.reply_metadata;
                      const hasReply = Boolean(replyMeta);
                      const replyTimestamp = replyMeta?.replied_at
                        ? new Date(replyMeta.replied_at).toLocaleString()
                        : null;
                      return (
                        <div
                          key={comment.comment_id}
                          className="rounded-lg border border-slate-200 bg-white p-3 text-slate-700 dark:border-slate-700 dark:bg-slate-900/30 dark:text-slate-100"
                        >
                          <div className="mb-1 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                            <span>{authorName || "Anonymous"}</span>
                            {comment.created_time && (
                              <span>{new Date(comment.created_time).toLocaleString()}</span>
                            )}
                          </div>
                          <p className="whitespace-pre-wrap text-sm leading-relaxed">{comment.message}</p>
                          <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400">
                            {typeof comment.like_count === "number" && (
                              <span>Likes: {comment.like_count}</span>
                            )}
                            {typeof comment.comment_count === "number" && (
                              <span>Replies: {comment.comment_count}</span>
                            )}
                            {comment.is_hidden && <span className="text-amber-600">Hidden</span>}
                          </div>
                          <div className="mt-3 flex flex-wrap items-center gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                if (activePostId) {
                                  void replyToComment(activePostId, comment);
                                }
                              }}
                              disabled={isReplying || hasReply || !activePostId}
                            >
                              {isReplying ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              ) : (
                                <Send className="mr-2 h-4 w-4" />
                              )}
                              {hasReply ? "Reply Sent" : "Reply"}
                            </Button>
                            {hasReply && replyTimestamp && (
                              <span className="text-[11px] text-emerald-600 dark:text-emerald-400">
                                Sent {replyTimestamp}
                              </span>
                            )}
                          </div>
                          {replyMeta && (
                            <div className="mt-2 rounded-lg bg-slate-100 p-2 text-xs text-slate-600 dark:bg-slate-800/70 dark:text-slate-200">
                              <span className="font-medium">Reply:</span> {replyMeta.reply_text}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="flex h-40 items-center justify-center text-slate-500">No comments yet.</div>
                )}
              </div>
              {activeSummary?.hasNextPage && (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Additional comments exist on Facebook. Use the Facebook link to review more.
                </p>
              )}
            </div>
          )}
          <div className="flex justify-end">
            <Button variant="outline" onClick={() => setActivePostId(null)}>
              Close
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      <Dialog
        open={deleteDialogOpen}
        onOpenChange={(open) => {
          setDeleteDialogOpen(open);
          if (!open) {
            setPostPendingDelete(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Delete campaign post</DialogTitle>
            <DialogDescription>
              This removes the post from BazaarFlow {"and"} Facebook. You can always rebuild the campaign later, but
              existing engagement will be gone.
            </DialogDescription>
          </DialogHeader>
          {pendingDeletePost && (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm dark:border-slate-800 dark:bg-slate-900/40">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                {new Date(pendingDeletePost.created_at).toLocaleString()}
              </p>
              <p className="mt-2 text-slate-700 dark:text-slate-200">{pendingDeletePost.message}</p>
            </div>
          )}
          <DialogFooter className="flex-col gap-3 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setDeleteDialogOpen(false);
                setPostPendingDelete(null);
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void confirmDeletePost()}
              disabled={!postPendingDelete || isDeletingPendingPost}
            >
              {isDeletingPendingPost ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Delete post
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
