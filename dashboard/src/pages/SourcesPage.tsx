import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Download, Globe, RefreshCw, AlertTriangle } from "lucide-react";
import { api, type FetchResult, type SourceInfo } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/context/ToastContext";

type FetchMode = "all" | "tx" | "fl";

export function SourcesPage() {
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [results, setResults] = useState<FetchResult[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState<FetchMode | null>(null);
  const [params] = useSearchParams();
  const { push } = useToast();

  useEffect(() => {
    api
      .sources()
      .then(setSources)
      .catch((e) =>
        push({ type: "error", title: "Failed to load sources", message: e.message }),
      )
      .finally(() => setLoading(false));
  }, [push]);

  const txSources = useMemo(() => sources.filter((s) => s.state === "TX"), [sources]);
  const flSources = useMemo(() => sources.filter((s) => s.state === "FL"), [sources]);

  const runFetch = async (mode: FetchMode) => {
    setFetching(mode);
    setResults(null);
    try {
      const res =
        mode === "tx"
          ? await api.fetchTx()
          : mode === "fl"
            ? await api.fetchFl()
            : await api.fetchAll();
      setResults(res.results);
      const total = res.results.reduce((n, r) => n + r.leads_fetched, 0);
      push({
        type: "success",
        title: "Fetch complete",
        message: `${total} leads fetched · ${res.total_leads_in_db ?? 0} in database`,
      });
    } catch (e) {
      push({
        type: "error",
        title: "Fetch failed",
        message: e instanceof Error ? e.message : undefined,
      });
    } finally {
      setFetching(null);
    }
  };

  useEffect(() => {
    if (params.get("fetch") === "1" && !loading) runFetch("all");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, params]);

  const renderGrid = (items: SourceInfo[]) => (
    <div className="grid gap-4 md:grid-cols-3">
      {items.map((src) => (
        <Card key={src.key} className="transition-transform hover:-translate-y-0.5">
          <CardHeader>
            <div className="flex items-start justify-between">
              <CardTitle className="text-base">{src.name}</CardTitle>
              <Globe className="h-4 w-4 text-brand-600" aria-hidden />
            </div>
            <CardDescription>{src.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Badge label={src.state} />
              <Badge label={src.county} />
            </div>
            <p className="mt-3 font-mono text-xs text-[hsl(var(--muted))]">{src.key}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Data Sources</h1>
          <p className="mt-1 text-[hsl(var(--muted))]">
            TX + FL county connectors — live fetch with fixture fallback
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button loading={fetching === "tx"} variant="outline" onClick={() => runFetch("tx")}>
            <Download className="h-4 w-4" />
            Fetch TX
          </Button>
          <Button loading={fetching === "fl"} variant="outline" onClick={() => runFetch("fl")}>
            <Download className="h-4 w-4" />
            Fetch FL
          </Button>
          <Button loading={fetching === "all"} onClick={() => runFetch("all")}>
            <Download className="h-4 w-4" />
            Fetch all
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-2xl" />
          ))}
        </div>
      ) : (
        <>
          <section className="space-y-4">
            <h2 className="text-lg font-semibold">Texas ({txSources.length})</h2>
            {renderGrid(txSources)}
          </section>
          <section className="space-y-4">
            <h2 className="text-lg font-semibold">Florida ({flSources.length})</h2>
            {renderGrid(flSources)}
          </section>
        </>
      )}

      {results && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5" />
              Last fetch results
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {results.map((r) => (
              <div
                key={r.source_key}
                className="rounded-xl border border-[hsl(var(--border))] p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">{r.county}</p>
                    <p className="text-xs text-[hsl(var(--muted))]">{r.source_key}</p>
                  </div>
                  {r.error ? (
                    <Badge label="error" />
                  ) : (
                    <div className="flex items-center gap-2">
                      {r.used_fixture_fallback && (
                        <span className="flex items-center gap-1 text-xs text-amber-600">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          Fixture fallback
                        </span>
                      )}
                      <span className="text-lg font-bold">{r.leads_fetched}</span>
                      <span className="text-xs text-[hsl(var(--muted))]">leads</span>
                    </div>
                  )}
                </div>
                {r.error && (
                  <p className="mt-2 text-sm text-red-600 dark:text-red-400">{r.error}</p>
                )}
                {r.ingest && (
                  <p className="mt-2 text-xs text-[hsl(var(--muted))]">
                    DB: {r.ingest.created} created, {r.ingest.updated} updated
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
