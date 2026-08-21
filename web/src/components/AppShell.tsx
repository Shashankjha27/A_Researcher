import { useState } from "react"
import { Link, NavLink, Outlet } from "react-router"

import { useHealth } from "@/api/hooks"
import { CommandPalette } from "@/components/CommandPalette"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Logo } from "@/components/Logo"
import { ThemeToggle } from "@/components/ThemeToggle"
import {
  FlaskConical,
  House,
  Library as LibraryIcon,
  PanelLeftClose,
  PanelLeftOpen,
  ScanSearch,
  Settings as SettingsIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"

const COLLAPSE_KEY = "ar.sidebar.collapsed"

interface NavItem {
  to: string
  label: string
  end?: boolean
  icon: React.ReactNode
}

const NAV_ITEMS: NavItem[] = [
  {
    to: "/",
    label: "Home",
    end: true,
    icon: <House className="size-4 shrink-0" aria-hidden />,
  },
  {
    to: "/verify",
    label: "Verify",
    icon: <ScanSearch className="size-4 shrink-0" aria-hidden />,
  },
  {
    to: "/library",
    label: "Library",
    icon: <LibraryIcon className="size-4 shrink-0" aria-hidden />,
  },
  {
    to: "/benchmark",
    label: "Benchmark",
    icon: <FlaskConical className="size-4 shrink-0" aria-hidden />,
  },
  {
    to: "/settings",
    label: "Settings",
    icon: <SettingsIcon className="size-4 shrink-0" aria-hidden />,
  },
]

function HealthDot({ labelClassName }: { labelClassName?: string }) {
  const { data, isError } = useHealth()

  const ok = !isError && data?.status === "ok"

  return (
    <span
      title={ok ? "API online" : "API offline"}
      className="flex items-center gap-2 text-xs text-muted-foreground"
    >
      <span
        className={cn(
          "inline-block size-2 shrink-0 rounded-full",
          ok ? "bg-emerald-500" : "bg-red-500",
        )}
      />
      <span className={labelClassName}>{ok ? "API online" : "API offline"}</span>
    </span>
  )
}

export function AppShell() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === "1"
    } catch {
      return false
    }
  })

  const toggleCollapsed = () => {
    setCollapsed((previous) => {
      try {
        localStorage.setItem(COLLAPSE_KEY, previous ? "0" : "1")
      } catch {
        // ignore storage failures
      }

      return !previous
    })
  }

  return (
    <div className="flex min-h-svh flex-col md:flex-row">
      <CommandPalette />

      <aside
        className={cn(
          "flex shrink-0 flex-col gap-4 border-b p-3 transition-[width] duration-200 md:sticky md:top-0 md:h-svh md:overflow-hidden md:border-r md:border-b-0",
          collapsed ? "md:w-[68px]" : "md:w-56",
        )}
      >
        <div
          className={cn(
            "flex items-center gap-2 pt-1",
            collapsed && "md:flex-col",
          )}
        >
          <Link to="/" aria-label="A_Researcher home">
            <Logo />
          </Link>

          <div
            className={cn(
              "min-w-0 flex-1",
              collapsed && "md:hidden",
            )}
          >
            <p className="truncate text-base font-bold leading-tight">
              A_Researcher
            </p>

            <p className="truncate text-xs text-muted-foreground">
              Cross-examining papers
            </p>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={toggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={cn(
              "text-muted-foreground hover:text-foreground max-md:hidden",
              collapsed && "md:mx-auto",
            )}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4" />
            ) : (
              <PanelLeftClose className="size-4" />
            )}
          </Button>
        </div>

        <nav className="flex flex-row flex-wrap gap-1 md:flex-col">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? false}
              title={item.label}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  collapsed && "md:justify-center md:px-0",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              {item.icon}

              <span className={cn(collapsed && "md:hidden")}>
                {item.label}
              </span>
            </NavLink>
          ))}
        </nav>

        <div
          className={cn(
            "flex flex-wrap items-center gap-3 md:mt-auto md:flex-col md:items-stretch",
            collapsed && "md:items-center",
          )}
        >
          <div className={cn("min-w-0 flex-1", collapsed && "md:hidden")}>
            <ThemeToggle />
          </div>

          <Badge
            variant="outline"
            className={cn("w-fit", collapsed && "md:hidden")}
          >
            NLI core
          </Badge>

          <HealthDot labelClassName={cn(collapsed && "md:hidden")} />
        </div>
      </aside>

      <main className="min-w-0 flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}
