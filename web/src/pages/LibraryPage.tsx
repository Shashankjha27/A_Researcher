import { Link } from "react-router"

import { useAgreementStats, usePapers } from "@/api/hooks"
import type { PaperSummary } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"

function LibraryTable({ papers }: { papers: PaperSummary[] }) {
  if (papers.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No papers yet. Upload one on the Verify page to build your library.
      </p>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Title</TableHead>
          <TableHead>Authors</TableHead>
          <TableHead>Year</TableHead>
          <TableHead>Claims</TableHead>
          <TableHead>Status</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>

      <TableBody>
        {papers.map((paper) => (
          <TableRow key={paper.paper_id}>
            <TableCell className="max-w-64 truncate font-medium">
              {paper.title}
            </TableCell>

            <TableCell className="max-w-48 truncate text-muted-foreground">
              {paper.authors?.length
                ? paper.authors.slice(0, 3).join(", ") +
                  (paper.authors.length > 3
                    ? ` +${paper.authors.length - 3}`
                    : "")
                : "—"}
            </TableCell>

            <TableCell>{paper.year}</TableCell>

            <TableCell>{paper.claim_count}</TableCell>

            <TableCell>
              {paper.retraction_status === "retracted" ? (
                <Badge className="border-transparent bg-red-100 text-red-800 uppercase">
                  Retracted
                </Badge>
              ) : (
                <span className="text-xs text-muted-foreground">
                  {paper.retraction_status}
                </span>
              )}
            </TableCell>

            <TableCell className="text-right">
              <Button asChild variant="ghost" size="sm">
                <Link to={`/reports/${paper.paper_id}`}>Report</Link>
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export function LibraryPage() {
  const { data: papers, isLoading } = usePapers()
  const { data: agreement } = useAgreementStats()

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <h1 className="text-2xl font-bold">Library</h1>

      {agreement &&
      agreement.total_verdicts > 0 &&
      agreement.accept_rate != null ? (
        <p className="text-sm text-muted-foreground">
          Model–human agreement:{" "}
          <span className="font-semibold text-foreground">
            {Math.round(agreement.accept_rate * 100)}%
          </span>{" "}
          ({agreement.total_verdicts - agreement.overridden}/
          {agreement.total_verdicts} verdicts accepted,{" "}
          {agreement.overridden} overridden)
        </p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Paper library</CardTitle>

          <CardDescription>
            Every ingested paper and its claim count.
          </CardDescription>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[0, 1, 2, 3].map((row) => (
                <Skeleton key={row} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <LibraryTable papers={papers ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
