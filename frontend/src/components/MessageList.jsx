import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, User } from 'lucide-react';

const MessageList = memo(function MessageList({
  user,
  messages,
  language,
  readingMode,
  setInlineFeedbackPopup,
  setSelectionToolbar,
  setDefinitionPopup,
  messagesEndRef,
  showTokens
}) {
  const handleMouseUp = (e) => {
    const selection = window.getSelection().toString().trim();
    if (selection) {
      setSelectionToolbar({
        word: selection,
        text: selection,
        x: e.clientX,
        y: e.clientY - 40
      });
    } else {
      setSelectionToolbar(null);
    }
  };

  const handleClick = (e) => {
    if (!window.getSelection().toString().trim()) {
      setSelectionToolbar(null);
    }
  };

  const renderMessage = (m, keyStr) => {
    if (m.role === 'system') {
      return (
        <div key={`system-${keyStr}`} className="flex justify-center my-3">
          <div className="bg-slate-200 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700/50 text-slate-600 dark:text-slate-400 text-xs font-medium px-4 py-1.5 rounded-full">
            {m.content}
          </div>
        </div>
      );
    }
    if (m.type === 'scenario') {
      if (m.status === 'active') {
        return (
          <div key={`scenario-${keyStr}`} className="flex flex-col space-y-4 my-2">
            <div className="bg-blue-500/10 border border-blue-500/20 text-blue-300 p-4 rounded-2xl flex flex-col gap-3 shadow-lg shadow-blue-500/5">
              <div className="font-bold uppercase tracking-wider text-xs flex items-center gap-3">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
                </span>
                Active Scenario: {m.id}
              </div>
              <div className="text-sm font-medium text-blue-900 dark:text-blue-100 flex items-start gap-2">
                <span className="text-blue-700 dark:text-blue-400 font-bold">Goal:</span> {m.goal}
              </div>
            </div>
            {m.messages.map((sMsg, j) => renderMessage(sMsg, `${keyStr}-${j}`))}
          </div>
        );
      } else {
        return (
          <details key={`scenario-${keyStr}`} className="bg-slate-200 dark:bg-slate-800/40 border border-slate-300 dark:border-slate-700/50 rounded-2xl overflow-hidden group my-2">
            <summary className="p-4 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-300 dark:bg-slate-700/50 transition-colors flex items-center justify-between outline-none">
              <span className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-green-500/20 text-green-600 dark:text-green-400 flex items-center justify-center text-xs border border-green-500/30">✓</div>
                Completed: {m.id}
              </span>
              <span className="text-xs font-semibold text-slate-500 bg-slate-200 dark:bg-slate-800/80 px-2 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700">{m.messages.length} messages</span>
            </summary>
            <div className="p-4 space-y-2 bg-slate-50 dark:bg-slate-900/60 border-t border-slate-300 dark:border-slate-700/50">
               {m.messages.map((sMsg, j) => renderMessage(sMsg, `${keyStr}-${j}`))}
            </div>
          </details>
        );
      }
    }
    
    return (
      <motion.div 
        key={keyStr}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex gap-3 w-full group hover:bg-slate-200 dark:hover:bg-slate-700/50 dark:bg-slate-800/30 py-2 px-3 rounded-2xl transition-colors"
      >
        <div className="shrink-0 mt-1">
          {m.role === 'user' ? (
            <div className={`w-8 h-8 rounded-full bg-gradient-to-tr ${user?.gradientClass || 'from-blue-500 to-indigo-500'} flex items-center justify-center text-black dark:text-white shadow-lg shadow-blue-500/20 shrink-0 overflow-hidden`}>
              <User className="w-5 h-5 mt-1 opacity-90" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 flex items-center justify-center text-slate-600 dark:text-slate-400 shrink-0 overflow-hidden">
              <User className="w-5 h-5 mt-1 opacity-80" />
            </div>
          )}
        </div>
        
        <div className="flex-1 relative space-y-1">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
               <span className="font-semibold text-slate-800 dark:text-slate-200 text-sm">{m.role === 'user' ? (user?.nickname || user?.username || 'You') : 'Polyglot AI'}</span>
               {m.role === 'user' && ((m.grammar && m.grammar.replace(/[^a-zA-Z]/g, '').toUpperCase() !== 'PERFECT') || m.pronunciation) && (
                 <button 
                   onClick={() => setInlineFeedbackPopup(m)}
                   className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/10 text-amber-700 dark:text-amber-400 rounded-full border border-amber-500/30 dark:border-amber-500/20 hover:bg-amber-500/20 transition-colors text-[10px] font-bold tracking-wide uppercase shadow-sm"
                   title="View Feedback"
                 >
                   <AlertTriangle size={12} /> Feedback
                 </button>
               )}
            </div>
            {showTokens && m.tokens && (
               <span className="text-[10px] font-medium text-slate-400">Tokens: {m.tokens}</span>
            )}
          </div>
          
          <div className="text-[17px] leading-relaxed text-slate-700 dark:text-slate-300 font-medium">
            {m.role === 'ai' && (m.content.includes('<ruby>') || (language === 'Japanese' && readingMode === 'ふりがな') || (language === 'Chinese' && readingMode === '拼音')) ? (
               <div dangerouslySetInnerHTML={{ __html: m.content }} />
            ) : (
               m.content
            )}
          </div>
        </div>
      </motion.div>
    );
  };

  return (
    <div 
      className="flex-1 overflow-y-auto px-2 py-4 space-y-0"
      onMouseUp={handleMouseUp}
      onClick={handleClick}
    >
      {messages.map((msg, i) => renderMessage(msg, i.toString()))}
      <div ref={messagesEndRef} />
    </div>
  );
});

export default MessageList;
