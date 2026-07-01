import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { api, type Lead, type LeadDetail } from "@/lib/api";
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
  const [stateFilter, setStateFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Lead | null>(null);
  const [detail, setDetail] = useState<LeadDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [running, setRunning] = useState<string | null>(null);
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
      if (stateFilter) params.state = stateFilter;
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
  }, [page, debouncedSearch, county, stateFilter, push]);

  useEffect(() => {
    load();
  }, [load]);

  const openLead = useCallback(
    async (lead: Lead) => {
      setSelected(lead);
      setDetail(null);
      setDetailLoading(true);
      try {
        setDetail(await api.lead(lead.id));
      } catch (e) {
        push({
          type: "error",
          title: "Failed to load lead detail",
          message: e instanceof Error ? e.message : undefined,
        });
      } finally {
        setDetailLoading(false);
      }
    },
    [push],
  );

  const runAction = useCallback(
    async (
      label: string,
      fn: () => Promise<unknown>,
      successMsg: string,
    ) => {
      setRunning(label);
      try {
        await fn();
        if (selected) setDetail(await api.lead(selected.id));
        await load();
        push({ type: "success", title: successMsg });
      } catch (e) {
        push({
          type: "error",
          title: `${label} failed`,
          message: e instanceof Error ? e.message : undefined,
        });
      } finally {
        setRunning(null);
      }
    },
    [selected, load, push],
  );

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
            <optgroup label="Texas">
              <option value="Harris">Harris</option>
              <option value="Dallas">Dallas</option>
              <option value="Tarrant">Tarrant</option>
            </optgroup>
            <optgroup label="Florida">
              <option value="Miami-Dade">Miami-Dade</option>
              <option value="Broward">Broward</option>
              <option value="Hillsborough">Hillsborough</option>
            </optgroup>
          </Select>
          <Select
            value={stateFilter}
            onChange={(e) => {
              setStateFilter(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by state"
          >
            <option value="">All states</option>
            <option value="TX">Texas</option>
            <option value="FL">Florida</option>
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
                  <th className="px-4 py-3 font-medium">Score</th>
                  <th className="px-4 py-3 font-medium">Signals</th>
                  <th className="px-4 py-3 font-medium">Added</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr
                    key={lead.id}
                    className="cursor-pointer border-b border-[hsl(var(--border))] transition-colors hover:bg-[hsl(var(--surface-muted))]/50"
                    onClick={() => openLead(lead)}
                  >
                    <td className="max-w-xs truncate px-4 py-3 font-medium">
                      {lead.property_address}
                    </td>
                    <td className="px-4 py-3">{lead.county}</td>
                    <td className="px-4 py-3">
                      {lead.deal_score != null ? (
                        <span className="font-semibold">{lead.deal_score}</span>
                      ) : (
                        <span className="text-[hsl(var(--muted))]">—</span>
                      )}
                    </td>
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
            <div className="flex items-start justify-between border-b border-[hsl(var(--border))] p-6">
              <div>
                <h2 className="text-lg font-semibold">{selected.property_address}</h2>
                <p className="text-sm text-[hsl(var(--muted))]">
                  {selected.county}, {selected.state}
                </p>
              </div>
              {detail?.deal_score != null && (
                <div className="text-right">
                  <div className="text-2xl font-bold">{detail.deal_score}</div>
                  <div className="text-xs text-[hsl(var(--muted))]">deal score</div>
                </div>
              )}
            </div>

            <div className="space-y-4 p-6 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge label={detail?.status ?? selected.status} />
                {(selected.distress_signals ?? []).map((s) => (
                  <Badge key={s} label={s} />
                ))}
              </div>

              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                <Button
                  size="sm"
                  variant="primary"
                  loading={running === "Pipeline"}
                  disabled={running !== null}
                  onClick={() =>
                    runAction("Pipeline", () => api.runPipeline(selected.id), "Pipeline complete")
                  }
                >
                  Run pipeline
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  loading={running === "Score"}
                  disabled={running !== null}
                  onClick={() => runAction("Score", () => api.scoreLead(selected.id), "Lead scored")}
                >
                  Score
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  loading={running === "Trace"}
                  disabled={running !== null}
                  onClick={() => runAction("Trace", () => api.traceLead(selected.id), "Owner traced")}
                >
                  Trace owner
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  loading={running === "Validate"}
                  disabled={running !== null}
                  onClick={() =>
                    runAction("Validate", () => api.validateLead(selected.id), "Contacts validated")
                  }
                >
                  Validate
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  loading={running === "Draft"}
                  disabled={running !== null}
                  onClick={() =>
                    runAction("Draft", () => api.draftLead(selected.id), "Draft added to queue")
                  }
                >
                  Draft email
                </Button>
              </div>

              {detailLoading && (
                <p className="text-[hsl(var(--muted))]">Loading enrichment…</p>
              )}

              {detail?.motivation_summary && (
                <div className="rounded-xl bg-[hsl(var(--surface-muted))] p-3">
                  <p className="mb-1 text-xs font-semibold uppercase text-[hsl(var(--muted))]">
                    Motivation
                  </p>
                  <p>{detail.motivation_summary}</p>
                </div>
              )}
              {detail?.offer_strategy && (
                <div className="rounded-xl bg-[hsl(var(--surface-muted))] p-3">
                  <p className="mb-1 text-xs font-semibold uppercase text-[hsl(var(--muted))]">
                    Offer strategy
                  </p>
                  <p>{detail.offer_strategy}</p>
                </div>
              )}
              {detail?.score_reasoning && (
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase text-[hsl(var(--muted))]">
                    Score reasoning
                  </p>
                  <p className="text-[hsl(var(--muted))]">{detail.score_reasoning}</p>
                </div>
              )}

              {detail && detail.owners.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase text-[hsl(var(--muted))]">
                    Owners &amp; contacts
                  </p>
                  {detail.owners.map((owner) => (
                    <div
                      key={owner.id}
                      className="rounded-xl border border-[hsl(var(--border))] p-3"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{owner.name ?? "Unknown owner"}</span>
                        {owner.is_llc && <Badge label="entity" />}
                      </div>
                      {owner.entity_name && (
                        <p className="text-xs text-[hsl(var(--muted))]">{owner.entity_name}</p>
                      )}
                      <div className="mt-2 space-y-1">
                        {owner.contacts.length === 0 && (
                          <p className="text-xs text-[hsl(var(--muted))]">No contacts yet</p>
                        )}
                        {owner.contacts.map((c) => (
                          <div key={c.id} className="flex items-center justify-between text-xs">
                            <span className="font-mono">
                              {c.value}
                              {c.line_type ? ` (${c.line_type})` : ""}
                            </span>
                            <Badge label={c.validated ? "valid" : "unverified"} />
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

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
