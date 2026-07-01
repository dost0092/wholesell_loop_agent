import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

const commands = [
  { id: "overview", label: "Go to Overview", path: "/" },
  { id: "leads", label: "Go to Leads", path: "/leads" },
  { id: "sources", label: "Go to Sources", path: "/sources" },
  { id: "fetch", label: "Fetch TX leads", path: "/sources?fetch=1" },
  { id: "approval", label: "Go to Approval Queue", path: "/approval" },
  { id: "settings", label: "Go to Settings", path: "/settings" },
];

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const filtered = commands.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase()),
  );

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (open) onClose();
        else {
          /* parent toggles */
        }
      }
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  const run = (path: string) => {
    navigate(path);
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
            onClick={onClose}
            aria-label="Close command palette"
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2 overflow-hidden rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] shadow-2xl"
          >
            <div className="flex items-center gap-3 border-b border-[hsl(var(--border))] px-4">
              <Search className="h-4 w-4 text-[hsl(var(--muted))]" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type a command or search..."
                className="h-12 flex-1 bg-transparent text-sm outline-none"
              />
            </div>
            <ul className="max-h-72 overflow-y-auto p-2">
              {filtered.length === 0 ? (
                <li className="px-3 py-6 text-center text-sm text-[hsl(var(--muted))]">
                  No commands found
                </li>
              ) : (
                filtered.map((cmd, i) => (
                  <li key={cmd.id}>
                    <button
                      type="button"
                      onClick={() => run(cmd.path)}
                      className={cn(
                        "flex w-full items-center rounded-xl px-3 py-2.5 text-left text-sm hover:bg-[hsl(var(--surface-muted))]",
                        i === 0 && "bg-[hsl(var(--surface-muted))]",
                      )}
                    >
                      {cmd.label}
                    </button>
                  </li>
                ))
              )}
            </ul>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
