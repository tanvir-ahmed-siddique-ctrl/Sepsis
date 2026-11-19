import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "Forward Deployed Engineering | Auralis",
  description: "Auralis FDE works with hospital teams on readiness, integration, deployment, training and ongoing technical support.",
};

export default function FdePage() {
  return (
    <div>
      <MarketingHero
        eyebrow="Forward Deployed Engineering"
        title={
          <>
            The people who get the model{" "}
            <span className="text-teal">onto the ward.</span>
          </>
        }
        description="We bring a holdout-proven sepsis model — then stay for readiness, connectivity, integration, silent evaluation and handover. FDE exists because a good model still needs people who wire the hospital."
      />
      <MarketingSection eyebrow="Delivery workspace" title="What an FDE project tracks.">
        <FeatureGrid items={[
          { title: "Project overview", body: "Owners, category, milestones, blockers, dependencies and next actions." },
          { title: "Site-readiness passport", body: "Checklist states with evidence — not invented numerical scores." },
          { title: "Integration engineering", body: "Approved connectors, mapping versions, validation and quarantine status." },
          { title: "Infrastructure & equipment", body: "Requirements, ownership model, procurement and acceptance records." },
          { title: "Evaluation & governance", body: "Permissions, silent-mode dates, alert burden and unresolved safety concerns." },
          { title: "Training & handover", body: "Separate records for doctors, nurses, admin, clinical IT and leadership." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
