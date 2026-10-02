import { notFound } from "next/navigation";
import { AppShell } from "@/components/app/AppShell";
import PreviewContent from "./PreviewContent";

// Read at request time: the preview is available in development, and in production only when UI_PREVIEW=1.
export const dynamic = "force-dynamic";

export default function UiPreviewPage() {
  if (process.env.NODE_ENV === "production" && process.env.UI_PREVIEW !== "1") notFound();
  return (
    <AppShell role="owner" platformAdmin tenantName="Ali Mart" userName="Ali" activeHref="/dashboard">
      <PreviewContent />
    </AppShell>
  );
}
