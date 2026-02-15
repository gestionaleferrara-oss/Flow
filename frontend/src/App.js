import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
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

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar />
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
          </Routes>
        </main>
        <Toaster 
          theme="dark" 
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              color: 'hsl(var(--foreground))'
            }
          }}
        />
      </div>
    </BrowserRouter>
  );
}

export default App;
