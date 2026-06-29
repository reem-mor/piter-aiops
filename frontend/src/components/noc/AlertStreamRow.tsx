import { memo } from "react";
import type { AlertRow, Priority } from "@/types/api";
import { PriorityBadge } from "@/components/noc/PriorityBadge";

type AlertStreamRowProps = {
  row: AlertRow;
  rowClass: string;
  streamStatus: string;
  onAsk: (row: AlertRow) => void;
};

export const AlertStreamRow = memo(function AlertStreamRow({
  row,
  rowClass,
  streamStatus,
  onAsk,
}: AlertStreamRowProps) {
  return (
    <tr className={rowClass || undefined}>
      <td className="mono">{row.timestamp.slice(11, 19)}</td>
      <td className="mono">{row.service}</td>
      <td className="mono">{row.title}</td>
      <td>
        <PriorityBadge priority={(row.severity as Priority) || "P4"} />
      </td>
      <td className="mono stream-status">{streamStatus}</td>
      <td>
        <button type="button" className="btn btn-sm" onClick={() => onAsk(row)}>
          Ask agent
        </button>
      </td>
    </tr>
  );
});
