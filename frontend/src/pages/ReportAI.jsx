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
  Trash2,
  LayoutDashboard,
  Target,
  Lightbulb,
  RotateCcw
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
      setReports(reports.filter(r => r.id !== reportId));
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

  const handleReset = () => {
    setSelectedReport(null);
    setReportType('dashboard');
  };

  if (loading) return <div className="flex items-center justify-center h-64"><LoadingSpinner /></div>;

  const getReportIcon = (tipo) => {
    switch(tipo) {
      case 'dashboard': return <LayoutDashboard className="w-4 h-4" />;
      case 'settimanale': return <Calendar className="w-4 h-4" />;
      case 'mensile': return <TrendingUp className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  const getReportColor = (tipo) => {
    switch(tipo) {
      case 'dashboard': return { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30' };
      case 'settimanale': return { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30' };
      case 'mensile': return { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' };
      default: return { bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500/30' };
    }
  };

  return (
    <PageWrapper>
      <PageHeader 
        title="Report AI" 
        subtitle="Report automatici generati dall'intelligenza artificiale"
      />

      {/* Selection Panel - Step Cards like Forecast */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Step 1: Select Report Type */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-full bg-purple-500/20 text-purple-400 text-xs font-bold flex items-center justify-center">1</div>
            <span className="text-sm font-medium text-white">Seleziona Tipo Report</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setReportType('dashboard')}
              data-testid="tipo-dashboard"
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                reportType === 'dashboard' 
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" 
                  : "bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:bg-white/[0.06]"
              )}
            >
              <LayoutDashboard className="w-4 h-4" />
              Dashboard
            </button>
            <button
              onClick={() => setReportType('settimanale')}
              data-testid="tipo-settimanale"
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                reportType === 'settimanale' 
                  ? "bg-purple-500/20 text-purple-400 border border-purple-500/30" 
                  : "bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:bg-white/[0.06]"
              )}
            >
              <Calendar className="w-4 h-4" />
              7gg
            </button>
            <button
              onClick={() => setReportType('mensile')}
              data-testid="tipo-mensile"
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                reportType === 'mensile' 
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30" 
                  : "bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:bg-white/[0.06]"
              )}
            >
              <TrendingUp className="w-4 h-4" />
              30gg
            </button>
          </div>
        </motion.div>

        {/* Step 2: Generate Button */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-full bg-amber-500/20 text-amber-400 text-xs font-bold flex items-center justify-center">2</div>
            <span className="text-sm font-medium text-white">Genera Nuovo Report</span>
          </div>
          <Button
            onClick={generateReport}
            disabled={generating}
            className="w-full gap-2 h-10"
            data-testid="generate-report-btn"
          >
            {generating ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Generazione AI...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Genera Report {reportType === 'dashboard' ? 'Dashboard' : reportType === 'settimanale' ? 'Settimanale' : 'Mensile'}
              </>
            )}
          </Button>
        </motion.div>

        {/* Step 3: Actions */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 text-xs font-bold flex items-center justify-center">3</div>
            <span className="text-sm font-medium text-white">Azioni</span>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={exportPdf}
              disabled={!selectedReport || exporting}
              className="flex-1 gap-2"
              data-testid="export-report-pdf"
            >
              {exporting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
              Esporta PDF
            </Button>
            <Button
              variant="outline"
              onClick={handleReset}
              className="gap-2"
              data-testid="reset-report"
            >
              <RotateCcw className="w-4 h-4" />
            </Button>
          </div>
        </motion.div>
      </div>

      {/* Generating Loading State */}
      {generating && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center py-16"
        >
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500/20 to-amber-500/20 flex items-center justify-center mb-4">
            <Sparkles className="w-8 h-8 text-purple-400 animate-pulse" />
          </div>
          <p className="text-white font-medium mb-1">Generazione in corso...</p>
          <p className="text-sm text-slate-500">L'AI sta analizzando i tuoi dati aziendali</p>
        </motion.div>
      )}

      {/* Main Content Grid */}
      {!generating && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Report List - Sidebar */}
          <motion.div 
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-1"
          >
            <div className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4">
              <div className="flex items-center gap-2 mb-4">
                <FileText className="w-4 h-4 text-slate-400" />
                <h3 className="font-semibold text-sm text-slate-300">Report Precedenti</h3>
                <span className="ml-auto text-[10px] text-slate-500 bg-white/[0.05] px-2 py-0.5 rounded-full">
                  {reports.length}
                </span>
              </div>
              <div className="space-y-2 max-h-[500px] overflow-auto pr-1 scrollbar-thin">
                {reports.length === 0 ? (
                  <div className="text-center py-8">
                    <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-purple-500/10 flex items-center justify-center">
                      <FileText className="w-6 h-6 text-purple-400/50" />
                    </div>
                    <p className="text-sm text-slate-500">Nessun report</p>
                    <p className="text-xs text-slate-600 mt-1">
                      Genera il primo report AI
                    </p>
                  </div>
                ) : (
                  reports.map((report, index) => {
                    const colors = getReportColor(report.tipo);
                    return (
                      <motion.div
                        key={report.id}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.03 }}
                        className={cn(
                          "relative group rounded-lg transition-all cursor-pointer",
                          selectedReport?.id === report.id
                            ? `${colors.bg} border ${colors.border}`
                            : "bg-white/[0.02] hover:bg-white/[0.05] border border-transparent hover:border-white/[0.08]"
                        )}
                      >
                        <button
                          onClick={() => setSelectedReport(report)}
                          className="w-full text-left p-3"
                          data-testid={`report-item-${index}`}
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <div className={cn("p-1.5 rounded-md", colors.bg)}>
                              {getReportIcon(report.tipo)}
                            </div>
                            <span className={cn("text-xs font-medium", colors.text)}>
                              {report.tipo === 'settimanale' ? 'Settimanale' : report.tipo === 'dashboard' ? 'Dashboard' : 'Mensile'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm font-semibold text-white">
                                {formatCurrency(report.metriche?.fatturato || 0)}
                              </p>
                              <p className="text-[10px] text-slate-500">
                                {formatDate(report.created_at)}
                              </p>
                            </div>
                            <ChevronRight className={cn(
                              "w-4 h-4 transition-colors",
                              selectedReport?.id === report.id ? colors.text : "text-slate-600"
                            )} />
                          </div>
                        </button>
                        {/* Delete button */}
                        <button
                          onClick={(e) => deleteReport(report.id, e)}
                          className="absolute top-2 right-2 p-1.5 rounded-md bg-red-500/0 hover:bg-red-500/20 text-slate-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                          data-testid={`delete-report-${index}`}
                          title="Elimina report"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </motion.div>
                    );
                  })
                )}
              </div>
            </div>
          </motion.div>

          {/* Report Content - Main Area */}
          <div className="lg:col-span-3">
            {selectedReport ? (
              <motion.div
                key={selectedReport.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                {/* Header Card */}
                <div className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={cn("p-2.5 rounded-lg", getReportColor(selectedReport.tipo).bg)}>
                        <Sparkles className={cn("w-5 h-5", getReportColor(selectedReport.tipo).text)} />
                      </div>
                      <div>
                        <h2 className="text-lg font-semibold text-white">
                          Report {selectedReport.tipo === 'settimanale' ? 'Settimanale' : selectedReport.tipo === 'dashboard' ? 'Dashboard' : 'Mensile'}
                        </h2>
                        <p className="text-xs text-slate-500">
                          {formatDate(selectedReport.periodo_inizio)} - {formatDate(selectedReport.periodo_fine)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <Clock className="w-3.5 h-3.5" />
                      Generato: {formatDate(selectedReport.created_at)}
                    </div>
                  </div>

                  {/* Metrics Grid */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                      <div className="flex items-center gap-2 text-emerald-400/70 text-[10px] uppercase tracking-wider mb-1">
                        <TrendingUp className="w-3 h-3" />
                        Fatturato
                      </div>
                      <p className="text-xl font-bold text-emerald-400">
                        {formatCurrency(selectedReport.metriche?.fatturato || 0)}
                      </p>
                    </div>
                    <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                      <div className="flex items-center gap-2 text-blue-400/70 text-[10px] uppercase tracking-wider mb-1">
                        <FileText className="w-3 h-3" />
                        Transazioni
                      </div>
                      <p className="text-xl font-bold text-blue-400">
                        {selectedReport.metriche?.num_vendite || 0}
                      </p>
                    </div>
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <div className="flex items-center gap-2 text-amber-400/70 text-[10px] uppercase tracking-wider mb-1">
                        <Users className="w-3 h-3" />
                        Clienti Inattivi
                      </div>
                      <p className="text-xl font-bold text-amber-400">
                        {selectedReport.metriche?.clienti_inattivi || 0}
                      </p>
                    </div>
                  </div>
                </div>

                {/* AI Analysis Card */}
                <div className="rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4">
                  <div className="flex items-center gap-2 mb-4">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <span className="text-sm font-medium text-white">Analisi AI</span>
                    <span className={cn(
                      "ml-auto text-[10px] px-2 py-0.5 rounded-full",
                      getReportColor(selectedReport.tipo).bg,
                      getReportColor(selectedReport.tipo).text
                    )}>
                      {selectedReport.tipo === 'settimanale' ? 'Ultimi 7 giorni' : selectedReport.tipo === 'dashboard' ? 'Overview' : 'Ultimi 30 giorni'}
                    </span>
                  </div>
                  <div className="prose prose-invert prose-sm max-w-none text-slate-300 overflow-auto max-h-[450px] pr-2 scrollbar-thin">
                    <ReactMarkdown
                      components={{
                        h1: ({ children }) => <div className="text-sm font-bold text-white bg-white/[0.05] px-3 py-2 rounded-lg mt-4 mb-2 first:mt-0">{children}</div>,
                        h2: ({ children }) => <div className="text-sm font-bold text-amber-400 mt-4 mb-2 flex items-center gap-2"><span className="w-1 h-4 bg-amber-400 rounded-full"></span>{children}</div>,
                        h3: ({ children }) => <div className="text-sm font-semibold text-slate-200 mt-3 mb-1.5">{children}</div>,
                        p: ({ children }) => <p className="text-sm text-slate-400 mb-2 leading-relaxed">{children}</p>,
                        strong: ({ children }) => <strong className="text-emerald-400 font-semibold">{children}</strong>,
                        ul: ({ children }) => <ul className="space-y-1.5 my-2 ml-1">{children}</ul>,
                        li: ({ children }) => <li className="text-sm text-slate-400 flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-1.5 shrink-0"></span><span>{children}</span></li>,
                        em: ({ children }) => <em className="text-cyan-400 not-italic">{children}</em>,
                      }}
                    >
                      {selectedReport.contenuto}
                    </ReactMarkdown>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center py-16 text-center rounded-xl border border-white/[0.08] bg-gradient-to-br from-white/[0.04] to-white/[0.01]"
              >
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-500/10 to-amber-500/10 flex items-center justify-center mb-4">
                  <Sparkles className="w-10 h-10 text-purple-400/50" />
                </div>
                <h3 className="text-lg font-medium text-white mb-2">Report AI Intelligenti</h3>
                <p className="text-sm text-slate-500 max-w-md">
                  Genera report automatici con analisi AI dei tuoi dati aziendali.
                  Scegli tra Dashboard, Settimanale o Mensile.
                </p>
                <div className="flex items-center gap-4 mt-6 text-xs text-slate-600">
                  <div className="flex items-center gap-1.5">
                    <LayoutDashboard className="w-3.5 h-3.5" />
                    <span>Overview business</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Target className="w-3.5 h-3.5" />
                    <span>Trend e insights</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Lightbulb className="w-3.5 h-3.5" />
                    <span>Raccomandazioni AI</span>
                  </div>
                </div>
                <Button
                  onClick={generateReport}
                  disabled={generating}
                  size="lg"
                  className="gap-2 mt-6"
                >
                  <Sparkles className="w-5 h-5" />
                  Genera il tuo primo report
                </Button>
              </motion.div>
            )}
          </div>
        </div>
      )}
    </PageWrapper>
  );
}
