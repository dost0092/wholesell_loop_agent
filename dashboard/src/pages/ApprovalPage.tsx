import { useEffect, useState } from "react";
import { Shield } from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/context/ToastContext";

interface ApprovalItem {
  id: number;
  lead_id: number;
  channel: string;
  draft_subject: string | null;
  draft_body: string;
  status: string;
  created_at: string;
}

export function ApprovalPage() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const { push } = useToast();

  useEffect(() => {
    api
      .approvalQueue()
      .then((res) => setItems(res.items))
      .catch((e) =>
        push({
          type: "error",
          title: "Failed to load queue",
          message:
            e instanceof Error
              ? e.message
              : "Check that the API is running and the database is connected.",
        }),
      )
      .finally(() => setLoading(false));
  }, [push]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Approval Queue</h1>
        <p className="mt-1 text-[hsl(var(--muted))]">
          Human review required before any outbound message (Phase 5+)
        </p>
      </div>

      <Card className="overflow-hidden">
        {loading ? (
          <TableSkeleton rows={4} cols={4} />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<Shield className="h-7 w-7" />}
            title="Queue is empty"
            description="When outreach is enabled, draft emails and SMS will appear here for your approval before sending."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-muted))]/50 text-left text-xs uppercase text-[hsl(var(--muted))]">
                  <th className="px-4 py-3">Lead</th>
                  <th className="px-4 py-3">Channel</th>
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-[hsl(var(--border))]">
                    <td className="px-4 py-3">#{item.lead_id}</td>
                    <td className="px-4 py-3">
                      <Badge label={item.channel} />
                    </td>
                    <td className="max-w-xs truncate px-4 py-3">
                      {item.draft_subject ?? "(no subject)"}
                    </td>
                    <td className="px-4 py-3">
                      <Badge label={item.status} />
                    </td>
                    <td className="px-4 py-3 text-[hsl(var(--muted))]">
                      {formatDate(item.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
