import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";

export default function TechnicalPracticePage() {
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Technical practice"
        description="Dedicated technical drill mode is planned. Your mock interviews already include technical questions from resume analysis."
      />
      <EmptyState
        title="Coming soon"
        description="Use Mock Interviews today for technical, behavioral and mixed practice with AI evaluation."
        actionLabel="Go to mock interviews"
        actionHref="/dashboard/interviews"
      />
    </div>
  );
}
