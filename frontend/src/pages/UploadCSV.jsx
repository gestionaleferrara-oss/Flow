import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  FileSpreadsheet,
  CheckCircle,
  AlertCircle,
  Users,
  Truck,
  Package,
  ShoppingCart,
  X,
  Files
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function UploadCSV() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [uploadMode, setUploadMode] = useState('incremental'); // 'incremental' or 'full'

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFiles(prev => [...prev, ...acceptedFiles]);
      setResult(null);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    multiple: true
  });

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setError(null);

    const formData = new FormData();
    
    if (files.length === 1) {
      formData.append('file', files[0]);
      try {
        const response = await axios.post(`${API}/upload-csv`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        setResult(response.data);
        setFiles([]);
      } catch (err) {
        setError(err.response?.data?.detail || 'Errore durante il caricamento');
      }
    } else {
      files.forEach(file => {
        formData.append('files', file);
      });
      try {
        const response = await axios.post(`${API}/upload-multiple`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        setResult(response.data);
        setFiles([]);
      } catch (err) {
        setError(err.response?.data?.detail || 'Errore durante il caricamento');
      }
    }
    
    setUploading(false);
  };

  const resetUpload = () => {
    setFiles([]);
    setResult(null);
    setError(null);
  };

  return (
    <PageWrapper>
      <PageHeader
        title="Importa Dati"
        subtitle="Carica uno o più file CSV/XLSX per importare vendite, clienti e prodotti"
      />

      {uploading && <LoadingSpinner fullScreen />}

      <div className="max-w-3xl mx-auto">
        {/* Drop Zone */}
        {!result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div
              {...getRootProps()}
              data-testid="dropzone"
              className={cn(
                'drop-zone cursor-pointer',
                isDragActive && 'active tracing-border'
              )}
            >
              <input {...getInputProps()} data-testid="file-input" />
              
              <div className="flex flex-col items-center gap-4">
                {files.length > 0 ? (
                  <>
                    <Files className="w-16 h-16 text-primary" />
                    <div className="text-center">
                      <p className="text-lg font-medium">{files.length} file selezionati</p>
                      <p className="text-sm text-muted-foreground">
                        Clicca o trascina per aggiungerne altri
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <Upload className="w-16 h-16 text-muted-foreground" />
                    <div>
                      <p className="text-lg font-medium">
                        {isDragActive ? 'Rilascia i file qui' : 'Trascina file CSV o XLSX'}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        oppure clicca per selezionare (anche multipli)
                      </p>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* File List */}
            {files.length > 0 && (
              <div className="mt-4 space-y-2">
                {files.map((file, index) => (
                  <motion.div
                    key={`${file.name}-${index}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-sm"
                  >
                    <div className="flex items-center gap-3">
                      <FileSpreadsheet className="w-5 h-5 text-primary" />
                      <div>
                        <p className="text-sm font-medium">{file.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {(file.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(index);
                      }}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </motion.div>
                ))}
              </div>
            )}

            {files.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 flex justify-center gap-4"
              >
                <Button
                  variant="outline"
                  onClick={() => setFiles([])}
                  data-testid="clear-files-btn"
                >
                  Cancella tutto
                </Button>
                <Button
                  onClick={handleUpload}
                  disabled={uploading}
                  data-testid="upload-btn"
                  className="uppercase tracking-wider"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Carica {files.length > 1 ? `${files.length} File` : 'e Elabora'}
                </Button>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Error Message */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mt-6 p-4 bg-destructive/10 border border-destructive/50 rounded-sm"
              data-testid="error-message"
            >
              <div className="flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-destructive" />
                <p className="text-destructive">{error}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Success Result */}
        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-6"
            >
              {/* Success Header */}
              <div className="text-center">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', delay: 0.2 }}
                >
                  <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-4" />
                </motion.div>
                <h2 className="font-heading text-2xl font-bold uppercase">
                  Importazione Completata
                </h2>
                <p className="text-muted-foreground mt-2">
                  {result.stats?.rows_processed || 0} righe elaborate con successo
                </p>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatBox
                  label="Vendite"
                  value={result.stats?.vendite_created || 0}
                  icon={ShoppingCart}
                  color="text-green-500"
                />
                <StatBox
                  label="Acquisti"
                  value={result.stats?.ordini_created || 0}
                  icon={Truck}
                  color="text-blue-500"
                />
                <StatBox
                  label="Cessioni/Omaggi"
                  value={result.stats?.cessioni_created || 0}
                  icon={Package}
                  color="text-purple-500"
                />
                <StatBox
                  label="Altri Mov."
                  value={result.stats?.other_movements || 0}
                  icon={Files}
                  color="text-slate-500"
                />
              </div>
              
              {/* Additional Stats */}
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="p-3 bg-muted/50 rounded-sm">
                  <p className="text-2xl font-bold text-blue-400">{result.stats?.new_clienti || 0}</p>
                  <p className="text-xs text-muted-foreground">Nuovi Clienti</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-sm">
                  <p className="text-2xl font-bold text-purple-400">{result.stats?.new_fornitori || 0}</p>
                  <p className="text-xs text-muted-foreground">Nuovi Fornitori</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-sm">
                  <p className="text-2xl font-bold text-amber-400">{result.stats?.new_prodotti || 0}</p>
                  <p className="text-xs text-muted-foreground">Nuovi Prodotti</p>
                </div>
              </div>

              {/* Errors if any */}
              {result.stats?.errors?.length > 0 && (
                <div className="p-4 bg-amber-500/10 border border-amber-500/50 rounded-sm">
                  <h3 className="font-semibold text-amber-500 mb-2">Avvisi</h3>
                  <ul className="text-sm space-y-1">
                    {result.stats.errors.slice(0, 5).map((err, i) => (
                      <li key={i} className="text-muted-foreground">{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Action Button */}
              <div className="flex justify-center">
                <Button onClick={resetUpload} data-testid="upload-another-btn">
                  Carica un altro file
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Instructions */}
        {!result && (
          <div className="mt-8 p-6 bg-muted/50 rounded-sm">
            <h3 className="font-heading text-lg font-semibold uppercase mb-4">
              Formati Supportati
            </h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• <strong>CSV</strong>: Separatore punto e virgola (;) o virgola (,)</li>
              <li>• <strong>XLSX</strong>: File Excel (Microsoft Excel)</li>
              <li>• Colonne: Movimento, Data, Codice Cl./Fo., Decodifica Cl./Fo., Codice, Decodifica, Quantita, Importo</li>
              <li>• I nuovi clienti, fornitori e prodotti vengono creati automaticamente</li>
              <li>• Movimento "SCARICO" = Vendita, "CARICO" = Acquisto</li>
            </ul>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}

function StatBox({ label, value, icon: Icon, color }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 bg-card border border-border/50 rounded-sm text-center"
    >
      <Icon className={cn('w-8 h-8 mx-auto mb-2', color)} />
      <p className="font-heading text-2xl font-bold">{value}</p>
      <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
    </motion.div>
  );
}
