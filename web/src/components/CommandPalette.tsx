import { useEffect, useState } from "react"
import { useNavigate } from "react-router"

import { useAllClaims, usePapers } from "@/api/hooks"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  FileText,
  FlaskConical,
  House,
  Library as LibraryIcon,
  Quote,
  ScanSearch,
  Settings as SettingsIcon,
} from "lucide-react"

const PAGES = [
  { to: "/", label: "Home", icon: <House className="size-4" /> },
  { to: "/verify", label: "Verify papers", icon: <ScanSearch className="size-4" /> },
  { to: "/library", label: "Library", icon: <LibraryIcon className="size-4" /> },
  { to: "/benchmark", label: "Benchmark", icon: <FlaskConical className="size-4" /> },
  { to: "/settings", label: "Settings", icon: <SettingsIcon className="size-4" /> },
]

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  const { data: papers } = usePapers()
  const { data: claims } = useAllClaims()

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        setOpen((previous) => !previous)
      }
    }

    document.addEventListener("keydown", onKeyDown)

    return () => document.removeEventListener("keydown", onKeyDown)
  }, [])

  const run = (action: () => void) => {
    setOpen(false)
    action()
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Jump to a page, paper, or claim…" />

      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Pages">
          {PAGES.map((page) => (
            <CommandItem
              key={page.to}
              value={`page ${page.label}`}
              onSelect={() => run(() => navigate(page.to))}
            >
              {page.icon}

              {page.label}
            </CommandItem>
          ))}
        </CommandGroup>

        {(papers ?? []).length > 0 ? (
          <CommandGroup heading="Papers">
            {(papers ?? []).map((paper) => (
              <CommandItem
                key={paper.paper_id}
                value={`paper ${paper.title} ${paper.paper_id}`}
                onSelect={() =>
                  run(() => navigate(`/reports/${paper.paper_id}`))
                }
              >
                <FileText className="size-4 shrink-0 text-muted-foreground" />

                <span className="truncate">{paper.title}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        ) : null}

        {(claims ?? []).length > 0 ? (
          <CommandGroup heading="Claims">
            {(claims ?? []).map((claim) => (
              <CommandItem
                key={claim.claim_id}
                value={`claim ${claim.claim_text} ${claim.claim_id}`}
                onSelect={() =>
                  run(() =>
                    navigate(
                      `/reports/${claim.paper_id}/claims/${claim.claim_id}`,
                    ),
                  )
                }
              >
                <Quote className="size-4 shrink-0 text-muted-foreground" />

                <span className="truncate">{claim.claim_text}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        ) : null}
      </CommandList>
    </CommandDialog>
  )
}
