import { Route, Routes } from "react-router"

import { AppShell } from "@/components/AppShell"
import { BenchmarkPage } from "@/pages/BenchmarkPage"
import { ClaimPage } from "@/pages/ClaimPage"
import { HomePage } from "@/pages/HomePage"
import { LibraryPage } from "@/pages/LibraryPage"
import { PaperViewPage } from "@/pages/PaperViewPage"
import { ReportPage } from "@/pages/ReportPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { VerifyPage } from "@/pages/VerifyPage"

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<HomePage />} />

        <Route path="/verify" element={<VerifyPage />} />

        <Route path="/library" element={<LibraryPage />} />

        <Route path="/reports/:paperId" element={<ReportPage />} />

        <Route
          path="/reports/:paperId/claims/:claimId"
          element={<ClaimPage />}
        />

        <Route path="/papers/:paperId/view" element={<PaperViewPage />} />

        <Route path="/settings" element={<SettingsPage />} />

        <Route path="/benchmark" element={<BenchmarkPage />} />
      </Route>
    </Routes>
  )
}
