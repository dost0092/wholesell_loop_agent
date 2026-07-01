import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { api, type Lead } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input, Select } from "@/components/ui/Input";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/context/ToastContext";

export function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [county, setCounty] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Lead | null>(null);
  const { push } = useToast();

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: 25 };
      if (debouncedSearch) params.search = debouncedSearch;
      if (county) params.county = county;
      const res = await api.leads(params);
      setLeads(res.items);
      setTotal(res.total);
      setPages(res.pages);
    } catch (e) {
      push({
        type: "error",
        title: "Failed to load leads",
        message: e instanceof Error ? e.message : undefined,
      });
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, county, push]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Leads</h1>
          <p className="mt-1 text-[hsl(var(--muted))]">{total} distressed properties</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Input
            icon
            placeholder="Search address, parcel..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-64"
            aria-label="Search leads"
          />
          <Select
            value={county}
            onChange={(e) => {
              setCounty(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by county"
          >
            <option value="">All counties</option>
            <option value="Harris">Harris</option>
            <option value="Dallas">Dallas</option>
            <option value="Tarrant">Tarrant</option>
          </Select>
        </div>
      </div>

      <Card className="overflow-hidden">
        {loading ? (
          <TableSkeleton rows={8} cols={5} />
        ) : leads.length === 0 ? (
          <EmptyState
            title="No leads found"
            description="Fetch leads from county sources to populate your pipeline."
            actionLabel="Go to Sources"
            onAction={() => (window.location.href = "/sources")}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-muted))]/50 text-left text-xs uppercase tracking-wide text-[hsl(var(--muted))]">
                  <th className="px-4 py-3 font-medium">Address</th>
                  <th className="px-4 py-3 font-medium">County</th>
                  <th className="px-4 py-3 font-medium">Parcel</th>
                  <th className="px-4 py-3 font-medium">Signals</th>
                  <th className="px-4 py-3 font-medium">Added</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr
                    key={lead.id}
                    className="cursor-pointer border-b border-[hsl(var(--border))] transition-colors hover:bg-[hsl(var(--surface-muted))]/50"
                    onClick={() => setSelected(lead)}
                  >
                    <td className="max-w-xs truncate px-4 py-3 font-medium">
                      {lead.property_address}
                    </td>
                    <td className="px-4 py-3">{lead.county}</td>
                    <td className="px-4 py-3 font-mono text-xs">{lead.parcel_id ?? "—"}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(lead.distress_signals ?? []).slice(0, 2).map((s) => (
                          <Badge key={s} label={s} />
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[hsl(var(--muted))]">
                      {formatDate(lead.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && total > 0 && (
          <div className="flex items-center justify-between border-t border-[hsl(var(--border))] px-4 py-3">
            <p className="text-xs text-[hsl(var(--muted))]">
              Page {page} of {pages} · {total} total
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= pages}
                onClick={() => setPage((p) => p + 1)}
                aria-label="Next page"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 backdrop-blur-sm sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-label="Lead details"
          onClick={() => setSelected(null)}
        >
          <Card
            className="max-h-[85vh] w-full max-w-lg overflow-y-auto animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-[hsl(var(--border))] p-6">
              <h2 className="text-lg font-semibold">{selected.property_address}</h2>
              <p className="text-sm text-[hsl(var(--muted))]">
                {selected.county}, {selected.state}
              </p>
            </div>
            <div className="space-y-4 p-6 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge label={selected.status} />
                {(selected.distress_signals ?? []).map((s) => (
                  <Badge key={s} label={s} />
                ))}
              </div>
              <dl className="grid gap-2">
                <div className="flex justify-between">
                  <dt className="text-[hsl(var(--muted))]">Parcel ID</dt>
                  <dd className="font-mono">{selected.parcel_id ?? "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-[hsl(var(--muted))]">Source</dt>
                  <dd>{selected.source_module}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-[hsl(var(--muted))]">Added</dt>
                  <dd>{formatDate(selected.created_at)}</dd>
                </div>
              </dl>
              {selected.raw_data && (
                <pre className="max-h-40 overflow-auto rounded-xl bg-[hsl(var(--surface-muted))] p-3 text-xs">
                  {JSON.stringify(selected.raw_data, null, 2)}
                </pre>
              )}
              <Button variant="outline" className="w-full" onClick={() => setSelected(null)}>
                Close
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
