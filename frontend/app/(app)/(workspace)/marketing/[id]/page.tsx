"use client";

import { useParams } from "next/navigation";
import { PageHeader } from "@/components/app/PageHeader";
import { RequireRole } from "@/components/app/RequireRole";
import { ErrorState, UnauthorizedState } from "@/components/app/StateViews";
import { PostEditor } from "@/components/marketing/PostEditor";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { MarketingPost } from "@/lib/api/types";

function Loaded() {
  const { id } = useParams<{ id: string }>();
  const loaded = useLoad(() => apiGet<MarketingPost>(`/marketing/posts/${id}`), [id]);

  if (loaded.state === "loading") {
    return (
      <div role="status" aria-busy="true" aria-label="Loading post" className="flex max-w-3xl flex-col gap-3">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (loaded.state === "unauthorized") return <UnauthorizedState />;
  if (loaded.state === "error" || !loaded.data) {
    const missing = loaded.error?.status === 404;
    return <ErrorState message={missing ? "That post does not exist." : (loaded.error?.message ?? "Could not load this post.")} onRetry={missing ? undefined : loaded.reload} />;
  }
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Marketing studio" description="Edit the draft, then send it for approval." />
      <PostEditor key={loaded.data.updated_at} post={loaded.data} />
    </div>
  );
}

/** One marketing post (PRD F-014). Owners and managers only. */
export default function MarketingPostPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <Loaded />
    </RequireRole>
  );
}
