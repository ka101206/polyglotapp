import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';

const MessageList = memo(function MessageList({
  messages,
  language,
  readingMode,
  setInlineFeedbackPopup,
  setSelectionToolbar,
  setDefinitionPopup,
  messagesEndRef
}) {
  const handleMouseUp = (e) => {
    const selection = window.getSelection().toString().trim();
    if (selection && selection.length > 0 && selection.length < 200) {
      const x = Math.min(e.clientX, window.innerWidth - 220);
      const y = Math.max(e.clientY - 50, 10);
      setSelectionToolbar({ word: selection, x, y });
      setDefinitionPopup(null);
    } else {
      setSelectionToolbar(null);
    }
  };

  const handleClick = () => {
    if (!window.getSelection().toString().trim()) {
      setSelectionToolbar(null);
      setDefinitionPopup(null);
    }
  };

  const renderMessage = (m, keyStr) => {
    if (m.type === 'scenario') {
      if (m.status === 'active') {
        return (
          <div key={`scenario-${keyStr}`} className="flex flex-col space-y-6 my-4">
            <div className="bg-blue-500/10 border border-blue-500/20 text-blue-300 p-5 rounded-2xl flex flex-col gap-3 shadow-lg shadow-blue-500/5">
              <div className="font-bold uppercase tracking-wider text-xs flex items-center gap-3">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
                </span>
                Active Scenario: {m.id}
              </div>
              <div className="text-sm font-medium text-blue-100 flex items-start gap-2">
                <span className="text-blue-400 font-bold">Goal:</span> {m.goal}
              </div>
            </div>
            {m.messages.map((sMsg, j) => renderMessage(sMsg, `${keyStr}-${j}`))}
          </div>
        );
      } else {
        return (
          <details key={`scenario-${keyStr}`} className="bg-slate-800/40 border border-slate-700/50 rounded-2xl overflow-hidden group my-2">
            <summary className="p-4 font-bold text-slate-300 cursor-pointer hover:bg-slate-700/50 transition-colors flex items-center justify-between outline-none">
              <span className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-green-500/20 text-green-400 flex items-center justify-center text-xs border border-green-500/30">✓</div>
                Completed: {m.id}
              </span>
              <span className="text-xs font-semibold text-slate-500 bg-slate-800/80 px-2 py-1.5 rounded-lg border border-slate-700">{m.messages.length} messages</span>
            </summary>
            <div className="p-6 space-y-6 bg-slate-900/60 border-t border-slate-700/50">
               {m.messages.map((sMsg, j) => renderMessage(sMsg, `${keyStr}-${j}`))}
            </div>
          </details>
        );
      }
    }
    
    return (
      <motion.div 
        key={keyStr}
        initial={{ opacity: 0, y: 10, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
      >
        <div className={`relative max-w-[75%] p-4 rounded-2xl ${
          m.role === 'user' 
            ? 'bg-blue-600 text-white rounded-tr-none shadow-blue-500/20' 
            : 'bg-slate-800 text-slate-100 rounded-tl-none border border-slate-700/50 shadow-xl'
        } shadow-lg text-[15px] leading-relaxed`}>
          {m.role === 'user' && (m.grammar || m.pronunciation) && (
            <button 
              onClick={() => setInlineFeedbackPopup(m)}
              className="absolute -left-12 top-2 p-2 bg-slate-800 text-amber-400 rounded-full shadow-lg border border-slate-700 hover:bg-slate-700 hover:text-amber-300 transition-colors z-10"
              title="View Feedback"
            >
              <AlertTriangle size={18} />
            </button>
          )}
          {m.role === 'ai' && (m.content.includes('<ruby>') || (language === 'Japanese' && readingMode === 'ふりがな')) ? (
             <div dangerouslySetInnerHTML={{ __html: m.content }} />
          ) : (
             m.content
          )}
        </div>
      </motion.div>
    );
  };

  return (
    <div 
      className="flex-1 overflow-y-auto p-6 space-y-6"
      onMouseUp={handleMouseUp}
      onClick={handleClick}
    >
      {messages.map((msg, i) => renderMessage(msg, i.toString()))}
      <div ref={messagesEndRef} />
    </div>
  );
});

export default MessageList;
