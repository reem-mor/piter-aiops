import { useCallback, useEffect, useState } from "react";
import { fetchBootstrap, fetchKbManifest } from "@/lib/api-contract";
import type { BootstrapResponse, KbManifestDocument } from "@/types/api";
import { DocumentUploadPanel } from "@/components/shell/DocumentUploadPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingSkeleton } from "@/components/noc/LoadingSkeleton";
import { ErrorState } from "@/components/noc/ErrorState";

export function KnowledgeBasePage() {
  const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null);
  const [documents, setDocuments] = useState<KbManifestDocument[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    const [bootResult, manifestResult] = await Promise.allSettled([
      fetchBootstrap(),
      fetchKbManifest(),
    ]);
    if (bootResult.status === "fulfilled") {
      setBootstrap(bootResult.value);
    }
    if (manifestResult.status === "fulfilled") {
      setDocuments(manifestResult.value.documents || []);
    }
    if (bootResult.status === "rejected" && manifestResult.status === "rejected") {
      setError("Failed to load knowledge base configuration");
    } else if (bootResult.status === "rejected") {
      setError("Configuration unavailable — manifest loaded from local corpus");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="grid-stack">
        <PageHeader title="Knowledge Base" subtitle="Runbooks and Bedrock retrieval sources" />
        <LoadingSkeleton lines={4} />
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  const kbSource = bootstrap?.s3_bucket ? "S3 + Bedrock KB" : "Local corpus";

  return (
    <div className="grid-stack">
      <PageHeader
        title="Knowledge Base"
        subtitle="Documents indexed for RAG — uploads go to S3 with optional Bedrock ingestion"
      />

      <section className="panel">
        <h2 className="panel-title">Configuration</h2>
        <dl className="config-dl">
          <dt>KB ID</dt>
          <dd className="mono">{bootstrap?.kb_id || "— (local fallback)"}</dd>
          <dt>S3 bucket</dt>
          <dd className="mono">{bootstrap?.s3_bucket || "—"}</dd>
          <dt>S3 prefix</dt>
          <dd className="mono">{bootstrap?.s3_prefix || "—"}</dd>
          <dt>RAG backend</dt>
          <dd className="mono">{(bootstrap as BootstrapResponse & { rag_backend?: string })?.rag_backend || "—"}</dd>
          <dt>Max upload</dt>
          <dd>{bootstrap?.max_upload_mb ?? 5} MB</dd>
        </dl>
      </section>

      <section className="panel">
        <div className="stream-header">
          <h2 className="panel-title" style={{ margin: 0 }}>
            Document manifest
          </h2>
          <span className="pill">{documents.length} indexed</span>
        </div>
        <div className="table-wrap">
          <table className="data-table data-table-compact">
            <thead>
              <tr>
                <th>Title</th>
                <th>Type</th>
                <th>Source</th>
                <th>Last sync</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={5} className="mono" style={{ color: "var(--text-muted)" }}>
                    No documents in manifest — check knowledge_base/ corpus.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.doc_id}>
                    <td>{doc.title}</td>
                    <td className="mono">{doc.doc_type}</td>
                    <td className="mono">{kbSource}</td>
                    <td className="mono">{doc.last_updated || "—"}</td>
                    <td>
                      <span className={`pill ${doc.indexed ? "pill-success" : ""}`}>
                        {doc.sync_status || (doc.indexed ? "indexed" : "pending")}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2 className="panel-title">Upload runbook</h2>
        <DocumentUploadPanel />
      </section>
    </div>
  );
}
