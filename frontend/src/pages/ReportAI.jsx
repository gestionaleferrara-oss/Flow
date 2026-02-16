import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  FileText,
  Sparkles,
  Calendar,
  RefreshCw,
  Clock,
  TrendingUp,
  Users,
  FileDown,
  ChevronRight,
  Download,
  Trash2
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { formatCurrency, formatDate, cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ReportAI() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [reportType, setReportType] = useState('dashboard');

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const response = await axios.get(`${API}/ai-reports`);
      setReports(response.data);
      if (response.data.length > 0 && !selectedReport) {
        setSelectedReport(response.data[0]);
      }
    } catch (error) {
      console.error('Error loading reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async () => {
    setGenerating(true);
    try {
      const response = await axios.post(`${API}/ai-reports/generate?report_type=${reportType}`);
      setSelectedReport(response.data);
      loadReports();
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Errore durante la generazione del report. Riprova.');
    } finally {
      setGenerating(false);
    }
  };

  const deleteReport = async (reportId, e) => {
    e.stopPropagation();
    if (!window.confirm('Sei sicuro di voler eliminare questo report?')) return;
    
    try {
      await axios.delete(`${API}/ai-reports/${reportId}`);
      // Update local state
      setReports(reports.filter(r => r.id !== reportId));
      // If the deleted report was selected, clear selection or select another
      if (selectedReport?.id === reportId) {
        const remaining = reports.filter(r => r.id !== reportId);
        setSelectedReport(remaining.length > 0 ? remaining[0] : null);
      }
    } catch (error) {
      console.error('Error deleting report:', error);
      alert('Errore durante l\'eliminazione del report.');
    }
  };

  const exportPdf = async () => {
    if (!selectedReport) return;
    setExporting(true);
    try {
      const response = await axios.post(`${API}/ai-reports/export-pdf`, selectedReport, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${selectedReport.tipo}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export PDF error:', e);
    } finally {
      setExporting(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><LoadingSpinner /></div>;

  return (
    <PageWrapper>
      <PageHeader
        title="Report AI"
        subtitle="Report automatici generati dall'intelligenza artificiale"
      >
        <div className="flex items-center gap-3">
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="report-type-select"
          >
            <option value="dashboard">Dashboard</option>
            <option value="settimanale">Settimanale</option>
            <option value="mensile">Mensile</option>
          </select>
          <Button
            onClick={generateReport}
            disabled={generating}
            className="gap-2"
            data-testid="generate-report-btn"
          >
            {generating ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Generazione...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Genera Report
              </>
            )}
          </Button>
        </div>
      </PageHeader>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Report List */}
        <div className="lg:col-span-1">
          <div className="glass-card p-4">
            <h3 className="font-semibold text-sm text-slate-400 uppercase tracking-wider mb-4">
              Report Precedenti
            </h3>
            <div className="space-y-2 max-h-[600px] overflow-auto">
              {reports.length === 0 ? (
                <div className="text-center py-8">
                  <FileText className="w-10 h-10 mx-auto text-slate-600 mb-2" />
                  <p className="text-sm text-slate-500">Nessun report generato</p>
                  <p className="text-xs text-slate-600 mt-1">
                    Clicca "Genera Report" per iniziare
                  </p>
                </div>
              ) : (
                reports.map((report, index) => (
                  <div
                    key={report.id}
                    className={cn(
                      "w-full text-left p-3 rounded-lg transition-all relative group",
                      selectedReport?.id === report.id
                        ? "bg-blue-500/20 border border-blue-500/30"
                        : "bg-white/[0.02] hover:bg-white/[0.05] border border-transparent"
                    )}
                  >
                    <button
                      onClick={() => setSelectedReport(report)}
                      className="w-full text-left"
                      data-testid={`report-item-${index}`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn(
                          "px-2 py-0.5 text-xs rounded-full",
                          report.tipo === 'settimanale' 
                            ? "bg-purple-500/20 text-purple-300"
                            : report.tipo === 'dashboard'
                            ? "bg-emerald-500/20 text-emerald-300"
                            : "bg-blue-500/20 text-blue-300"
                        )}>
                          {report.tipo === 'settimanale' ? '7gg' : report.tipo === 'dashboard' ? 'DASH' : '30gg'}
                        </span>
                        <span className="text-xs text-slate-500">
                          {formatDate(report.created_at)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-slate-300 truncate">
                          {formatCurrency(report.metriche?.fatturato || 0)}
                        </span>
                        <ChevronRight className="w-4 h-4 text-slate-600" />
                      </div>
                    </button>
                    {/* Delete button */}
                    <button
                      onClick={(e) => deleteReport(report.id, e)}
                      className="absolute top-2 right-2 p-1.5 rounded-md bg-red-500/0 hover:bg-red-500/20 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                      data-testid={`delete-report-${index}`}
                      title="Elimina report"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Report Content */}
        <div className="lg:col-span-3">
          {selectedReport ? (
            <motion.div
              key={selectedReport.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card overflow-hidden"
            >
              {/* Report Header */}
              <div className="p-6 border-b border-white/5 bg-gradient-to-r from-purple-500/10 to-blue-500/10">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <div className="p-2 rounded-lg bg-purple-500/20">
                        <Sparkles className="w-5 h-5 text-purple-400" />
                      </div>
                      <div>
                        <h2 className="text-xl font-semibold">
                          Report {selectedReport.tipo === 'settimanale' ? 'Settimanale' : selectedReport.tipo === 'dashboard' ? 'Dashboard' : 'Mensile'}
                        </h2>
                        <p className="text-sm text-slate-400">
                          {formatDate(selectedReport.periodo_inizio)} - {formatDate(selectedReport.periodo_fine)}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Clock className="w-3 h-3" />
                    Generato il {formatDate(selectedReport.created_at)}
                  </div>
                </div>

                {/* Quick Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
                  <div className="p-3 bg-white/5 rounded-lg">
                    <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                      <TrendingUp className="w-3 h-3" />
                      Fatturato
                    </div>
                    <p className="text-lg font-semibold text-emerald-400">
                      {formatCurrency(selectedReport.metriche?.fatturato || 0)}
                    </p>
                  </div>
                  <div className="p-3 bg-white/5 rounded-lg">
                    <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                      <FileText className="w-3 h-3" />
                      Transazioni
                    </div>
                    <p className="text-lg font-semibold text-blue-400">
                      {selectedReport.metriche?.num_vendite || 0}
                    </p>
                  </div>
                  <div className="p-3 bg-white/5 rounded-lg">
                    <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                      <Users className="w-3 h-3" />
                      Clienti Inattivi
                    </div>
                    <p className="text-lg font-semibold text-amber-400">
                      {selectedReport.metriche?.clienti_inattivi || 0}
                    </p>
                  </div>
                </div>
              </div>

              {/* Report Body - Markdown */}
              <div className="p-6">
                <div className="prose prose-invert prose-sm max-w-none
                  prose-headings:font-semibold prose-headings:text-slate-200
                  prose-h1:text-2xl prose-h1:mb-4 prose-h1:mt-6
                  prose-h2:text-xl prose-h2:mb-3 prose-h2:mt-5 prose-h2:text-blue-400
                  prose-h3:text-lg prose-h3:mb-2 prose-h3:mt-4
                  prose-p:text-slate-300 prose-p:leading-relaxed
                  prose-strong:text-white prose-strong:font-semibold
                  prose-ul:my-2 prose-li:text-slate-300 prose-li:my-1
                  prose-ol:my-2
                  prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
                ">
                  <ReactMarkdown>{selectedReport.contenuto}</ReactMarkdown>
                </div>
              </div>
            </motion.div>
          ) : (
            <div className="glass-card p-12 text-center">
              <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-purple-500/10 flex items-center justify-center">
                <Sparkles className="w-10 h-10 text-purple-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Genera il tuo primo report</h3>
              <p className="text-slate-400 mb-6 max-w-md mx-auto">
                L'AI analizzerà i tuoi dati aziendali e genererà un report completo con 
                insights, trend e raccomandazioni personalizzate.
              </p>
              <Button
                onClick={generateReport}
                disabled={generating}
                size="lg"
                className="gap-2"
              >
                {generating ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Generazione in corso...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Genera Report {reportType === 'settimanale' ? 'Settimanale' : reportType === 'dashboard' ? 'Dashboard' : 'Mensile'}
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      </div>
    </PageWrapper>
  );
}
