import "@/App.css";
import { useState, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { Menu } from "lucide-react";
import Sidebar from "@/components/Sidebar";

// Lightweight page loader - no fullscreen block
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-32">
      <div className="w-5 h-5 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin" />
    </div>
  );
}

// Lazy-loaded pages for instant navigation
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const UploadCSV = lazy(() => import("@/pages/UploadCSV"));
const Forecast = lazy(() => import("@/pages/Forecast"));
const Magazzino = lazy(() => import("@/pages/Magazzino"));
const Vendite = lazy(() => import("@/pages/Vendite"));
const Clienti = lazy(() => import("@/pages/Clienti"));
const Fornitori = lazy(() => import("@/pages/Fornitori"));
const Ordini = lazy(() => import("@/pages/Ordini"));
const Statistiche = lazy(() => import("@/pages/Statistiche"));
const Notizie = lazy(() => import("@/pages/Notizie"));
const ReportAI = lazy(() => import("@/pages/ReportAI"));

function App() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="app-container">
        <div className="noise-overlay" />
        <div className="mobile-topbar" data-testid="mobile-topbar">
          <button
            onClick={() => setMobileOpen(true)}
            className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            data-testid="mobile-menu-toggle"
          >
            <Menu className="w-5 h-5" />
          </button>
          <span className="text-sm font-semibold text-white tracking-wide">Flow</span>
          <div className="w-9" />
        </div>
        <Sidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
        <main className="main-content">
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/upload" element={<UploadCSV />} />
              <Route path="/forecast" element={<Forecast />} />
              <Route path="/magazzino" element={<Magazzino />} />
              <Route path="/vendite" element={<Vendite />} />
              <Route path="/clienti" element={<Clienti />} />
              <Route path="/fornitori" element={<Fornitori />} />
              <Route path="/ordini" element={<Ordini />} />
              <Route path="/statistiche" element={<Statistiche />} />
              <Route path="/notizie" element={<Notizie />} />
              <Route path="/report-ai" element={<ReportAI />} />
            </Routes>
          </Suspense>
        </main>
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'rgba(15, 23, 42, 0.9)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: 'white'
            }
          }}
        />
      </div>
    </BrowserRouter>
  );
}

export default App;
