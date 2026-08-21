import { useEffect, useState } from "react"
import { toast } from "sonner"

import {
  useClearConfig,
  useConfig,
  useSaveConfig,
} from "@/api/hooks"
import type { LLMProvider } from "@/api/types"
import { ThemeGrid } from "@/components/ThemeToggle"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"

const PROVIDERS: { value: LLMProvider; label: string }[] = [
  { value: "ollama", label: "Ollama (local)" },
  { value: "openai", label: "OpenAI" },
  { value: "gemini", label: "Gemini" },
  { value: "claude", label: "Claude" },
]

export function SettingsPage() {
  const { data: config, isLoading } = useConfig()
  const saveConfig = useSaveConfig()
  const clearConfig = useClearConfig()

  const [provider, setProvider] = useState<LLMProvider>("ollama")
  const [model, setModel] = useState("")
  const [apiKey, setApiKey] = useState("")

  useEffect(() => {
    if (!config) {
      return
    }

    if (
      PROVIDERS.some((entry) => entry.value === config.provider)
    ) {
      setProvider(config.provider as LLMProvider)
    }

    setModel(config.model ?? "")
  }, [config])

  function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    saveConfig.mutate(
      {
        provider,
        model,
        ...(apiKey ? { api_key: apiKey } : {}),
      },
      {
        onSuccess: () => {
          setApiKey("")
          toast.success("LLM configuration saved.")
        },
        onError: (error) => {
          toast.error(
            error instanceof Error ? error.message : "Failed to save.",
          )
        },
      },
    )
  }

  function handleClear() {
    if (!window.confirm("Clear stored LLM configuration?")) {
      return
    }

    clearConfig.mutate(undefined, {
      onSuccess: () => toast.success("Configuration cleared."),
      onError: (error) => {
        toast.error(
          error instanceof Error ? error.message : "Failed to clear.",
        )
      },
    })
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>

          <CardDescription>
            Pick a color theme — the choice is remembered on this device.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <ThemeGrid />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>LLM configuration</CardTitle>

          <CardDescription>
            Used for claim extraction. The API key is stored in your OS
            keychain — never in plain text.
            {config?.has_key ? " A key is currently stored." : ""}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-9 w-full" />

              <Skeleton className="h-9 w-full" />

              <Skeleton className="h-9 w-40" />
            </div>
          ) : (
            <form onSubmit={handleSave} className="space-y-4">
              <div className="space-y-1.5">
                <Label>Provider</Label>

                <Select
                  value={provider}
                  onValueChange={(value) =>
                    setProvider(value as LLMProvider)
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>

                  <SelectContent>
                    {PROVIDERS.map((entry) => (
                      <SelectItem key={entry.value} value={entry.value}>
                        {entry.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="cfg-model">Model</Label>

                <Input
                  id="cfg-model"
                  value={model}
                  onChange={(event) => setModel(event.target.value)}
                  placeholder={
                    provider === "ollama"
                      ? "llama3.2:latest"
                      : provider === "openai"
                        ? "gpt-4o-mini"
                        : provider === "gemini"
                          ? "gemini-2.0-flash"
                          : "claude-3-5-haiku-latest"
                  }
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="cfg-key">API key</Label>

                <Input
                  id="cfg-key"
                  type="password"
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder={
                    config?.has_key ? "•••••••• (stored)" : "Not stored"
                  }
                  autoComplete="off"
                />
              </div>

              <div className="flex gap-2">
                <Button type="submit" disabled={saveConfig.isPending}>
                  Save configuration
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  onClick={handleClear}
                  disabled={clearConfig.isPending}
                >
                  Clear
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
