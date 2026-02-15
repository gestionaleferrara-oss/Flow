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
  X
} from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { Button } from '@/components/ui/button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { cn } from '@/lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function UploadCSV() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setResult(null);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.csv']
    },
    maxFiles: 1
  });

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/upload-csv`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult(response.data);
      setFile(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore durante il caricamento');
    } finally {
      setUploading(false);
    }
  };

  const resetUpload = () => {
    setFile(null);
    setResult(null);
    setError(null);
  };

  return (
    <PageWrapper>
      <PageHeader
        title="Importa Dati"
        subtitle="Carica un file CSV per importare vendite, clienti e prodotti"
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
                {file ? (
                  <>
                    <FileSpreadsheet className="w-16 h-16 text-primary" />
                    <div>
                      <p className="text-lg font-medium">{file.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {(file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                      }}
                      data-testid="remove-file-btn"
                    >
                      <X className="w-4 h-4 mr-2" />
                      Rimuovi
                    </Button>
                  </>
                ) : (
                  <>
                    <Upload className="w-16 h-16 text-muted-foreground" />
                    <div>
                      <p className="text-lg font-medium">
                        {isDragActive ? 'Rilascia il file qui' : 'Trascina un file CSV'}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        oppure clicca per selezionare
                      </p>
                    </div>
                  </>
                )}
              </div>
            </div>

            {file && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 flex justify-center"
              >
                <Button
                  onClick={handleUpload}
                  disabled={uploading}
                  data-testid="upload-btn"
                  className="uppercase tracking-wider"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Carica e Elabora
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
                  label="Nuovi Clienti"
                  value={result.stats?.new_clienti || 0}
                  icon={Users}
                  color="text-blue-500"
                />
                <StatBox
                  label="Nuovi Fornitori"
                  value={result.stats?.new_fornitori || 0}
                  icon={Truck}
                  color="text-purple-500"
                />
                <StatBox
                  label="Nuovi Prodotti"
                  value={result.stats?.new_prodotti || 0}
                  icon={Package}
                  color="text-amber-500"
                />
                <StatBox
                  label="Vendite Create"
                  value={result.stats?.vendite_created || 0}
                  icon={ShoppingCart}
                  color="text-green-500"
                />
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
              Formato CSV Supportato
            </h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Separatore: punto e virgola (;) o virgola (,)</li>
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
