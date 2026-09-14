import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Send, RotateCcw, Wrench, Check, Loader2, User, Zap } from 'lucide-react';
import PageWrapper, { PageHeader } from '@/components/PageWrapper';
import { AgentMarkdown } from '@/components/AgentMarkdown';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SUGGERIMENTI = [
  'Preparami il rendiconto PDF del mese scorso con la provvigione al 3%',
  'Quali sono i 5 prodotti con il margine più basso questo mese?',
  'Quando è finito il lotto di noci e a che margine l\'ho venduto?',
  'Chi mi vende le noci al prezzo migliore?',
  'Confronta le vendite di questo mese con lo stesso mese dell\'anno scorso',
  'Ricalcola le giacenze e dimmi quanti prodotti sono esauriti',
];

// Link ai PDF generati dall'agente: gestiti in AgentMarkdown
function ToolChip({ tool }) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border',
        tool.scrittura
          ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
          : 'bg-cyan-500/10 border-cyan-500/25 text-cyan-300'
      )}
      data-testid="agent-tool-chip"
    >
      {tool.done ? <Check className="w-3 h-3" /> : <Loader2 className="w-3 h-3 animate-spin" />}
      {tool.scrittura ? <Zap className="w-3 h-3" /> : <Wrench className="w-3 h-3" />}
      {tool.label}
    </div>
  );
}

export default function Assistente() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    const saved = localStorage.getItem('flow_agent_session');
    if (saved) return saved;
    const id = `agent-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem('flow_agent_session', id);
    return id;
  });
  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/ai-agent/history?session_id=${encodeURIComponent(sessionId)}`);
        const d = await r.json();
        if (d.messages?.length) {
          setMessages(d.messages.map((m) => ({ role: m.role, content: m.content, tools: [] })));
        }
      } catch (e) { /* nuova sessione */ }
    })();
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, streaming]);

  const send = useCallback(async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || streaming) return;
    setInput('');
    setStreaming(true);
    setMessages((m) => [...m, { role: 'user', content: msg }, { role: 'assistant', content: '', tools: [] }]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`${API}/ai-agent/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, session_id: sessionId }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const patchLast = (fn) => setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = fn(copy[copy.length - 1]);
        return copy;
      });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';
        for (const part of parts) {
          const line = part.split('\n').find((l) => l.startsWith('data: '));
          if (!line) continue;
          let ev;
          try { ev = JSON.parse(line.slice(6)); } catch { continue; }

          if (ev.type === 'delta') {
            patchLast((last) => ({ ...last, content: last.content + ev.content }));
          } else if (ev.type === 'tool_start') {
            patchLast((last) => ({
              ...last,
              tools: [...(last.tools || []), { name: ev.name, label: ev.label, scrittura: ev.scrittura, done: false }],
            }));
          } else if (ev.type === 'tool_done') {
            patchLast((last) => ({
              ...last,
              tools: (last.tools || []).map((t) => (t.name === ev.name && !t.done ? { ...t, done: true } : t)),
            }));
          } else if (ev.type === 'error') {
            toast.error(`Errore AI: ${ev.message}`);
            patchLast((last) => ({ ...last, content: last.content || `⚠️ ${ev.message}` }));
          }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        toast.error('Errore di connessione con l\'agente AI');
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last && last.role === 'assistant' && !last.content) copy.pop();
          return copy;
        });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, streaming, sessionId]);

  const reset = async () => {
    if (abortRef.current) abortRef.current.abort();
    try { await fetch(`${API}/ai-agent/session?session_id=${encodeURIComponent(sessionId)}`, { method: 'DELETE' }); } catch (e) { /* ignora */ }
    const id = `agent-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem('flow_agent_session', id);
    setSessionId(id);
    setMessages([]);
    setStreaming(false);
    toast.success('Nuova conversazione avviata');
  };

  return (
    <PageWrapper>
      <PageHeader title="Assistente AI" subtitle="Chiedi qualsiasi cosa: l'agente legge i dati ed esegue azioni nel gestionale">
        <Button variant="outline" size="sm" onClick={reset} data-testid="agent-reset-btn">
          <RotateCcw className="w-4 h-4 mr-2" /> Nuova chat
        </Button>
      </PageHeader>

      <div
        className="rounded-2xl border border-white/[0.07] overflow-hidden flex flex-col"
        style={{
          background: 'linear-gradient(180deg, rgba(13,18,33,0.92) 0%, rgba(8,12,24,0.92) 100%)',
          height: 'calc(100vh - 210px)',
          minHeight: 460,
        }}
        data-testid="agent-chat-panel"
      >
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-5">
          {messages.length === 0 && (
            <div className="max-w-2xl mx-auto text-center pt-6" data-testid="agent-empty-state">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-violet-500/10 border border-violet-500/25 flex items-center justify-center mb-4">
                <Sparkles className="w-7 h-7 text-violet-300" />
              </div>
              <h2 className="text-lg font-semibold text-white">Cosa vuoi fare oggi?</h2>
              <p className="text-sm text-slate-400 mt-2 mb-6">
                Posso analizzare vendite, acquisti, margini e giacenze — e modificare direttamente i dati (quantità minime, scadenze, esclusioni, anagrafiche, ricalcoli).
              </p>
              <div className="grid sm:grid-cols-2 gap-2 text-left">
                {SUGGERIMENTI.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => send(s)}
                    data-testid={`agent-suggestion-${i}`}
                    className="px-3.5 py-2.5 rounded-xl border border-white/[0.07] bg-white/[0.02] hover:bg-violet-500/10 hover:border-violet-500/30 text-xs text-slate-300 hover:text-violet-200 transition-colors duration-200"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((m, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className={cn('flex gap-3', m.role === 'user' ? 'justify-end' : 'justify-start')}
                data-testid={`agent-message-${m.role}`}
              >
                {m.role === 'assistant' && (
                  <div className="w-8 h-8 shrink-0 rounded-xl bg-violet-500/10 border border-violet-500/25 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-violet-300" />
                  </div>
                )}
                <div className={cn('max-w-[85%] space-y-2', m.role === 'user' && 'items-end flex flex-col')}>
                  {m.tools?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {m.tools.map((t, i) => <ToolChip key={i} tool={t} />)}
                    </div>
                  )}
                  {(m.content || m.role === 'user') && (
                    <div
                      className={cn(
                        'rounded-2xl px-4 py-3 text-sm leading-relaxed',
                        m.role === 'user'
                          ? 'bg-cyan-500/15 border border-cyan-500/25 text-cyan-50'
                          : 'bg-white/[0.03] border border-white/[0.07] text-slate-200'
                      )}
                    >
                      {m.role === 'assistant' ? (
                        <AgentMarkdown content={m.content} />
                      ) : (
                        m.content
                      )}
                    </div>
                  )}
                  {m.role === 'assistant' && !m.content && streaming && idx === messages.length - 1 && (
                    <div className="flex items-center gap-2 text-xs text-slate-500 px-1">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> elaboro i dati...
                    </div>
                  )}
                </div>
                {m.role === 'user' && (
                  <div className="w-8 h-8 shrink-0 rounded-xl bg-cyan-500/10 border border-cyan-500/25 flex items-center justify-center">
                    <User className="w-4 h-4 text-cyan-300" />
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        <div className="border-t border-white/[0.06] p-3 sm:p-4 bg-black/20">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
              }}
              rows={1}
              placeholder="Scrivi una richiesta... (Invio per inviare, Shift+Invio per andare a capo)"
              className="flex-1 resize-none max-h-32 rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-violet-500/40 transition-colors"
              data-testid="agent-input"
              disabled={streaming}
            />
            <Button
              onClick={() => send()}
              disabled={!input.trim() || streaming}
              className="h-11 px-4 bg-violet-600 hover:bg-violet-500"
              data-testid="agent-send-btn"
            >
              {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 px-1">
            L'agente esegue le modifiche immediatamente. Le azioni di scrittura sono evidenziate in ambra.
          </p>
        </div>
      </div>
    </PageWrapper>
  );
}
