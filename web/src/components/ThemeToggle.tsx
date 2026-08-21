import { useTheme } from "next-themes"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

export const THEMES = [
  { value: "light", label: "Light", swatch: "#ffffff" },
  { value: "dark", label: "Dark", swatch: "#1f1f1f" },
  { value: "gruvbox", label: "Gruvbox", swatch: "#fabd2f" },
  { value: "dracula", label: "Dracula", swatch: "#bd93f9" },
  { value: "nord", label: "Nord", swatch: "#88c0d0" },
  { value: "solarized", label: "Solarized", swatch: "#268bd2" },
  { value: "catppuccin", label: "Catppuccin", swatch: "#cba6f7" },
]

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <Select value={theme ?? "system"} onValueChange={setTheme}>
      <SelectTrigger className="w-full" aria-label="Select theme">
        <span className="flex items-center gap-2">
          <span
            className="inline-block size-3 shrink-0 rounded-full border"
            style={{
              backgroundColor:
                THEMES.find((item) => item.value === theme)?.swatch ??
                "transparent",
            }}
          />
          <SelectValue placeholder="Theme" />
        </span>
      </SelectTrigger>

      <SelectContent>
        {THEMES.map((item) => (
          <SelectItem key={item.value} value={item.value}>
            <span className="flex items-center gap-2">
              <span
                className="inline-block size-3 shrink-0 rounded-full border"
                style={{ backgroundColor: item.swatch }}
              />
              {item.label}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function ThemeGrid() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {THEMES.map((item) => (
        <button
          key={item.value}
          type="button"
          onClick={() => setTheme(item.value)}
          aria-pressed={theme === item.value}
          className={cn(
            "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
            theme === item.value
              ? "border-primary bg-primary/10 text-foreground"
              : "text-muted-foreground hover:bg-muted hover:text-foreground",
          )}
        >
          <span
            className="inline-block size-4 shrink-0 rounded-full border"
            style={{ backgroundColor: item.swatch }}
          />
          {item.label}
        </button>
      ))}
    </div>
  )
}
