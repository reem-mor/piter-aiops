import type { ChatResponse } from "@/types/api";
import { PiterAnalysisPanel } from "./PiterAnalysisPanel";

export function PiterResponseView({
  response,
  onFollowUp,
}: {
  response: ChatResponse;
  onFollowUp?: (question: string) => void;
}) {
  return <PiterAnalysisPanel response={response} onFollowUp={onFollowUp} />;
}
