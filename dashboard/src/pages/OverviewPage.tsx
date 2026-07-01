import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Activity, Building2, MapPin, TrendingUp } from "lucide-react";
import { api, type Health, type LeadStats } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/context/ToastContext";

const CHART_COLORS = ["#1a7ff5", "#339dff", "#59bdff", "#8ed7ff", "#1368e1"];

function StatCard({
  label,
  value,
  icon: Icon,
  delay,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
    >
      <Card className="glass-panel overflow-hidden">
        <CardContent className="flex items-center gap-4 p-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600/10 text-brand-600">
            <Icon className="h-6 w-6" aria-hidden />
          </div>
          <div>
            <p className="text-sm text-[hsl(var(--muted))]">{label}</p>
            <p className="text-2xl font-bold tracking-tight">{value}</p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function OverviewPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<LeadStats | null>(null);
  const [loading, setLoading] = useState(true);
  const { push } = useToast();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [h, s] = await Promise.all([api.health(), api.stats()]);
        if (!cancelled) {
          setHealth(h);
          setStats(s);
        }
      } catch (e) {
        if (!cancelled) {
          push({
            type: "error",
            title: "Failed to load dashboard",
            message: e instanceof Error ? e.message : "Unknown error",
          });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [push]);

  const countyData = stats
    ? Object.entries(stats.by_county).map(([name, value]) => ({ name, value }))
    : [];

  const signalData = stats
    ? Object.entries(stats.by_signal).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
        <p className="mt-1 text-[hsl(var(--muted))]">
          Distressed property leads across Texas and Florida counties
        </p>
      </div>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total leads" value={stats?.total ?? 0} icon={Building2} delay={0} />
          <StatCard
            label="Counties active"
            value={Object.keys(stats?.by_county ?? {}).length}
            icon={MapPin}
            delay={0.05}
          />
          <StatCard
            label="Distress signals"
            value={Object.keys(stats?.by_signal ?? {}).length}
            icon={TrendingUp}
            delay={0.1}
          />
          <StatCard
            label="System status"
            value={health?.status === "ok" ? "Healthy" : "Degraded"}
            icon={Activity}
            delay={0.15}
          />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Leads by county</CardTitle>
            <CardDescription>Distribution across TX and FL counties</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            {loading ? (
              <Skeleton className="h-full w-full" />
            ) : countyData.length === 0 ? (
              <p className="flex h-full items-center justify-center text-sm text-[hsl(var(--muted))]">
                No leads yet — fetch from Sources
              </p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={countyData}>
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 12,
                      border: "1px solid hsl(var(--border))",
                      background: "hsl(var(--surface-elevated))",
                    }}
                  />
                  <Bar dataKey="value" fill="#1a7ff5" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Distress signals</CardTitle>
            <CardDescription>Most common motivation indicators</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            {loading ? (
              <Skeleton className="h-full w-full" />
            ) : signalData.length === 0 ? (
              <p className="flex h-full items-center justify-center text-sm text-[hsl(var(--muted))]">
                No signals recorded yet
              </p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={signalData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={4}
                  >
                    {signalData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {health && (
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Badge label={`phase ${health.phase}`} />
            <Badge label={`db ${health.database}`} />
            {health.tx_counties.map((c) => (
              <Badge key={c} label={c} />
            ))}
            {health.require_human_approval && <Badge label="human approval" />}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
