import { useState } from "react";
import { Key, Save, Shield } from "lucide-react";
import { getStoredApiKey, setApiKey } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useTheme } from "@/context/ThemeContext";
import { useToast } from "@/context/ToastContext";

export function SettingsPage() {
  const [apiKey, setApiKeyState] = useState(getStoredApiKey());
  const { theme, setTheme } = useTheme();
  const { push } = useToast();

  const saveKey = () => {
    setApiKey(apiKey);
    push({ type: "success", title: "API key saved", message: "Applied to all API requests" });
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-[hsl(var(--muted))]">Configure your workspace</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            API Authentication
          </CardTitle>
          <CardDescription>
            Set the API key matching your backend <code className="text-xs">API_KEY</code> env var.
            Leave empty in development when API_KEY is not set.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            type="password"
            placeholder="X-API-Key value"
            value={apiKey}
            onChange={(e) => setApiKeyState(e.target.value)}
            aria-label="API key"
          />
          <Button onClick={saveKey}>
            <Save className="h-4 w-4" />
            Save API key
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Choose your preferred theme</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            {(["light", "dark", "system"] as const).map((t) => (
              <Button
                key={t}
                variant={theme === t ? "primary" : "outline"}
                size="sm"
                onClick={() => setTheme(t)}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Compliance
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-[hsl(var(--muted))]">
          <p>
            Human approval is required before any outbound message. No emails or SMS are sent
            automatically in the current phase.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
