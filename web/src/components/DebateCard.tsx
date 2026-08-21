import { useDebate, useRunDebate } from "@/api/hooks"
import type { DebateTurn } from "@/api/types"
import { VerdictBadge } from "@/components/VerdictBadge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

const TURN_STYLES: Record<
  DebateTurn["role"],
  { label: string; classes: string }
> = {
  defender: {
    label: "Defender",
    classes: "border-emerald-500 bg-emerald-500/5",
  },
  attacker: {
    label: "Attacker",
    classes: "border-red-500 bg-red-500/5",
  },
  judge: {
    label: "Judge",
    classes: "border-amber-400 bg-amber-400/10",
  },
}

function TurnBubble({ turn }: { turn: DebateTurn }) {
  const style = TURN_STYLES[turn.role] ?? TURN_STYLES.judge

  return (
    <div
      className={`rounded-lg border-l-4 p-3 text-sm leading-relaxed ${style.classes}`}
    >
      <p className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
        {style.label}
      </p>

      <p className="whitespace-pre-wrap">{turn.text}</p>
    </div>
  )
}

export function DebateCard({ claimId }: { claimId: string }) {
  const { data: debate, isLoading } = useDebate(claimId)
  const runDebate = useRunDebate(claimId)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <div className="space-y-1">
            <CardTitle>Adversarial debate</CardTitle>

            <CardDescription>
              A defender and an attacker argue the claim against the
              paper's own evidence; a judge renders the verdict.
            </CardDescription>
          </div>

          {!debate && !isLoading ? (
            <Button
              size="sm"
              onClick={() =>
                runDebate.mutate(undefined, {
                  onError: (error) => {
                    import("sonner").then(({ toast }) =>
                      toast.error(
                        error instanceof Error
                          ? error.message
                          : "Debate failed.",
                      ),
                    )
                  },
                })
              }
              disabled={runDebate.isPending}
            >
              {runDebate.isPending ? "Debating…" : "Run debate"}
            </Button>
          ) : null}
        </div>

        {debate ? (
          <p className="font-mono text-xs text-muted-foreground">
            model: {debate.model} · verdict:{" "}
            <VerdictBadge verdict={debate.judge_verdict} />
          </p>
        ) : null}
      </CardHeader>

      {debate ? (
        <CardContent className="space-y-3">
          {debate.turns.map((turn, index) => (
            <TurnBubble key={index} turn={turn} />
          ))}
        </CardContent>
      ) : null}

      {runDebate.isPending ? (
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Running three LLM turns — this can take a minute…
          </p>
        </CardContent>
      ) : null}
    </Card>
  )
}
