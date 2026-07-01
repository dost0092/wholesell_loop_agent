import { useCallback, useEffect, useState } from "react";
import { Shield } from "lucide-react";
import { api, type ApprovalItem } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/context/ToastContext";

export function ApprovalPage() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<ApprovalItem | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const { push } = useToast();

  const load = useCallback(() => {
    setLoading(true);
    api
      .approvalQueue()
      .then((res) => setItems(res.items))
      .catch((e) =>
        push({
          type: "error",
          title: "Failed to load queue",
          message: e instanceof Error ? e.message : undefined,
        }),
      )
      .finally(() => setLoading(false));
  }, [push]);

  useEffect(() => {
    load();
  }, [load]);

  const openItem = (item: ApprovalItem) => {
    setOpen(item);
    setSubject(item.draft_subject ?? "");
    setBody(item.draft_body);
  };

  const act = async (label: string, fn: () => Promise<unknown>, msg: string) => {
    setBusy(label);
    try {
      await fn();
      push({ type: "success", title: msg });
      setOpen(null);
      load();
    } catch (e) {
      push({
        type: "error",
        title: `${label} failed`,
        message: e instanceof Error ? e.message : undefined,
      });
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Approval Queue</h1>
        <p className="mt-1 text-[hsl(var(--muted))]">
          Human review required before any outbound message is sent
        </p>
      </div>

      <Card className="overflow-hidden">
        {loading ? (
          <TableSkeleton rows={4} cols={4} />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<Shield className="h-7 w-7" />}
            title="Queue is empty"
            description="Draft outreach from a lead (Leads → open a lead → Draft email) to populate this queue."
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
                  <tr
                    key={item.id}
                    className="cursor-pointer border-b border-[hsl(var(--border))] transition-colors hover:bg-[hsl(var(--surface-muted))]/50"
                    onClick={() => openItem(item)}
                  >
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

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 backdrop-blur-sm sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-label="Review draft"
          onClick={() => setOpen(null)}
        >
          <Card
            className="max-h-[85vh] w-full max-w-xl overflow-y-auto animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-[hsl(var(--border))] p-6">
              <h2 className="text-lg font-semibold">Review draft · Lead #{open.lead_id}</h2>
              <p className="text-sm text-[hsl(var(--muted))]">
                Edit if needed, then approve. Nothing sends without your action.
              </p>
            </div>
            <div className="space-y-4 p-6 text-sm">
              <div>
                <label className="mb-1 block text-xs font-medium text-[hsl(var(--muted))]">
                  Subject
                </label>
                <Input value={subject} onChange={(e) => setSubject(e.target.value)} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-[hsl(var(--muted))]">
                  Body
                </label>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  rows={12}
                  className="w-full rounded-xl border border-[hsl(var(--border))] bg-transparent p-3 font-mono text-xs focus-visible:outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <Button
                  size="sm"
                  variant="outline"
                  loading={busy === "Approve"}
                  disabled={busy !== null}
                  onClick={() =>
                    act(
                      "Approve",
                      () => api.approveItem(open.id, { reviewer: "operator", subject, body }),
                      "Draft approved",
                    )
                  }
                >
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="primary"
                  loading={busy === "Send"}
                  disabled={busy !== null}
                  onClick={() =>
                    act(
                      "Send",
                      () =>
                        api.approveItem(open.id, {
                          reviewer: "operator",
                          subject,
                          body,
                          send_now: true,
                        }),
                      "Approved & sent",
                    )
                  }
                >
                  Approve &amp; send
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  loading={busy === "Reject"}
                  disabled={busy !== null}
                  onClick={() => act("Reject", () => api.rejectItem(open.id), "Draft rejected")}
                >
                  Reject
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setOpen(null)}>
                  Cancel
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
