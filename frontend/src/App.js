import "@/App.css";
import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { Menu } from "lucide-react";
import Sidebar from "@/components/Sidebar";

// Pages
import Dashboard from "@/pages/Dashboard";
import UploadCSV from "@/pages/UploadCSV";
import Magazzino from "@/pages/Magazzino";
import Vendite from "@/pages/Vendite";
import Clienti from "@/pages/Clienti";
import Fornitori from "@/pages/Fornitori";
import Ordini from "@/pages/Ordini";
import Statistiche from "@/pages/Statistiche";
import Notizie from "@/pages/Notizie";
import ReportAI from "@/pages/ReportAI";

function App() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="app-container">
        {/* Noise texture overlay */}
        <div className="noise-overlay" />

        {/* Mobile top bar */}
        <div className="mobile-topbar" data-testid="mobile-topbar">
          <button
            onClick={() => setMobileOpen(true)}
            className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            data-testid="mobile-menu-toggle"
          >
            <Menu className="w-5 h-5" />
          </button>
          <span className="text-sm font-semibold text-white tracking-wide">Flusso</span>
          <div className="w-9" />
        </div>

        <Sidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<UploadCSV />} />
            <Route path="/magazzino" element={<Magazzino />} />
            <Route path="/vendite" element={<Vendite />} />
            <Route path="/clienti" element={<Clienti />} />
            <Route path="/fornitori" element={<Fornitori />} />
            <Route path="/ordini" element={<Ordini />} />
            <Route path="/statistiche" element={<Statistiche />} />
            <Route path="/notizie" element={<Notizie />} />
            <Route path="/report-ai" element={<ReportAI />} />
          </Routes>
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
