import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { uploadDocument } from "@/lib/api-contract";
import { useDemo } from "@/context/demo";
import { Button } from "@/components/ui/Button";

export function DocumentUploadPanel({ compact = false }: { compact?: boolean }) {
  const { bootstrap } = useDemo();
  const inputRef = useRef<HTMLInputElement>(null);
  const [syncKb, setSyncKb] = useState(Boolean(bootstrap?.sync_kb_default));
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const maxMb = bootstrap?.max_upload_mb ?? 5;
  const allowed = bootstrap?.allowed_types?.join(", ") || ".pdf, .md, .txt";

  const onPick = async (file: File | null) => {
    if (!file) return;
    setPending(true);
    setError(null);
    setStatus(null);
    try {
      const result = await uploadDocument(file, syncKb);
      const syncNote = result.sync_started
        ? result.ingestion_job_id
          ? `Synced to Bedrock Knowledge Base (job ${result.ingestion_job_id})`
          : "Synced to Bedrock Knowledge Base"
        : "Uploaded to local project knowledge base — Bedrock sync required";
      setStatus(`${result.filename} uploaded · ${syncNote}`);
      if (result.sync_warning) {
        setStatus(`${result.filename} uploaded · ${result.sync_warning}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setPending(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className={`doc-upload${compact ? " doc-upload-compact" : ""}`}>
      {!compact ? (
        <p className="doc-upload-hint">
          Upload runbooks to S3{syncKb ? " and trigger Bedrock KB ingestion" : ""}. Max {maxMb} MB · {allowed}
        </p>
      ) : null}
      <div className="doc-upload-row">
        <input
          ref={inputRef}
          type="file"
          className="doc-upload-input"
          hidden
          accept={bootstrap?.allowed_types?.map((t) => `.${t.replace(/^\./, "")}`).join(",")}
          onChange={(e) => void onPick(e.target.files?.[0] ?? null)}
          disabled={pending}
        />
        <label className="doc-upload-sync">
          <input type="checkbox" checked={syncKb} onChange={(e) => setSyncKb(e.target.checked)} />
          Sync to KB
        </label>
        <Button
          variant="secondary"
          size="sm"
          loading={pending}
          onClick={() => inputRef.current?.click()}
        >
          <Upload size={14} /> Upload doc
        </Button>
      </div>
      {status ? (
        <p className="doc-upload-status" role="status">
          {status}
        </p>
      ) : null}
      {error ? (
        <p className="doc-upload-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
