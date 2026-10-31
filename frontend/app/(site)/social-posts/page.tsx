import type { Metadata } from "next";
import { BrandImage } from "@/components/brand/BrandImage";
import { Bob } from "@/components/site/motion";
import { ProductPage } from "@/components/site/ProductPage";

export const metadata: Metadata = {
  title: "Marketing - BazaarFlow",
  description: "A posting agent drafts picture posts for your Facebook Page, schedules them, and publishes once you approve. Comment replies and insights included.",
};

const STEPS = [
  { title: "Set the goal", text: "Say what you want to promote, how many posts a day, in what window and in what tone.", note: "Eid offer, 2 posts a day", tone: "bg-sunny" },
  { title: "The agent drafts", text: "The posting agent writes each caption and picks a picture, and lays the posts out on a schedule.", note: "Draft ready: 6 posts", tone: "bg-cream" },
  { title: "You approve", text: "Each post waits for a manager or the owner. Or turn on automatic mode for the shop, if you trust the tone.", note: "approved", tone: "bg-lime" },
  { title: "It goes out", text: "At the scheduled time the post goes to your Facebook Page. If it fails it retries, and the failure is written down.", note: "Posted 10:30", tone: "bg-sky" },
  { title: "Comments and results", text: "Comments are fetched and the agent proposes replies for you to approve. Insights show what went out and how it did.", note: "3 replies to check", tone: "bg-coral" },
];

const FACTS = [
  { label: "Picture posts", text: "The agent writes a caption and chooses or makes a picture for it." },
  { label: "Scheduling", text: "Posts per day, a time window and a tone, set once and kept." },
  { label: "Approval", text: "Nothing is published until a manager or the owner says yes, unless the shop turns on automatic mode." },
  { label: "Facebook Page", text: "Posts are published to your Facebook Page through your own connection.", later: true },
  { label: "Comment replies", text: "Replies are proposed by the agent and approved by you.", later: true },
  { label: "Instagram", text: "Not yet. It is planned after Facebook.", later: true },
  { label: "Video", text: "Not yet. The agent makes pictures only for now.", later: true },
];

export default function MarketingPage() {
  return (
    <ProductPage
      chip="Marketing"
      lines={["Posts that", "post themselves."]}
      lead="A posting agent drafts, schedules and publishes picture posts to your Facebook Page. You approve every one."
      steps={STEPS}
      stepsTitle="From goal to posted."
      facts={FACTS}
      factsTitle="What it does, and what it does not."
      visual={
        <Bob amount={14} seconds={4}>
          <div className="mx-auto w-full max-w-sm rotate-2 overflow-hidden rounded-card bg-cream shadow-card">
            <div className="aspect-square">
              <BrandImage file="photo-bakery-box.jpg" alt="A bakery box tied with twine, the kind of picture a post uses" label="Post picture" tone="sunny" />
            </div>
            <div className="p-5">
              <p className="font-slip text-ui-lg">Fresh boxes out by noon. Order before 11.</p>
              <p className="mt-2 text-ui-sm font-medium">Scheduled for 10:30 · waiting for approval</p>
            </div>
          </div>
        </Bob>
      }
    />
  );
}
