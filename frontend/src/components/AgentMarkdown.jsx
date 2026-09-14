import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Download } from 'lucide-react';

// Rende il markdown dell'agente AI: tabelle leggibili e link ai PDF che puntano al backend
const components = {
  a: ({ href, children, ...props }) => {
    const url = href?.startsWith('/api') ? `${process.env.REACT_APP_BACKEND_URL}${href}` : href;
    const isPdf = href?.includes('.pdf') || href?.includes('/export/pdf')
      || href?.includes('/api/analisi/export') || href?.includes('/api/ai/report');
    return (
      <a
        {...props}
        href={url}
        target="_blank"
        rel="noreferrer"
        download={isPdf ? '' : undefined}
        data-testid="agent-link"
        className={isPdf
          ? 'inline-flex items-center gap-1.5 my-1 px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium no-underline transition-colors'
          : 'text-violet-300 underline decoration-violet-500/40 hover:text-violet-200'}
      >
        {isPdf && <Download className="w-3.5 h-3.5" />}
        {children}
      </a>
    );
  },
};

export const AgentMarkdown = ({ content }) => (
  <div className="agent-markdown">
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{content}</ReactMarkdown>
  </div>
);

export default AgentMarkdown;
