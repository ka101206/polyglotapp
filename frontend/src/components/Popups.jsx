import React from 'react';
import { X, BookmarkPlus, AlertTriangle, Send } from 'lucide-react';
import { parseDefinition, ANNOTATION_LABEL_KEYS, formatAnnotation } from './Sidebar';
import { useTranslation } from '../i18n';

export function SelectionToolbar({ selectionToolbar, setSelectionToolbar, setDefinitionPopup, language, replayText, replaySpeed, repeatLast }) {
  const { t } = useTranslation();
  if (!selectionToolbar) return null;
  return (
    <div
      className="fixed z-[60] flex items-center gap-1 bg-slate-200 dark:bg-slate-800 border border-slate-400 dark:border-slate-600 shadow-2xl rounded-lg p-1 backdrop-blur-md"
      style={{ top: selectionToolbar.y, left: selectionToolbar.x }}
    >
      <button
        onClick={async () => {
          const word = selectionToolbar.word;
          const x = selectionToolbar.x;
          const y = selectionToolbar.y + 45;
          setSelectionToolbar(null);
          window.getSelection().removeAllRanges();
          const apiUrl = '';
          try {
            const res = await fetch(`${apiUrl}/api/ai/definition`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ word, language })
            });
            const data = await res.json();
            if (data.definition) {
              setDefinitionPopup({
                word,
                text: data.definition,
                x: Math.min(x, window.innerWidth - 300),
                y: Math.min(y, window.innerHeight - 250)
              });
            }
          } catch (err) {
            console.error('Definition error:', err);
          }
        }}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-300 dark:bg-slate-700 rounded-md transition-colors"
        title={t('lookUpDefinition')}
      >
        <BookmarkPlus size={14} className="text-blue-400" />
        {t('define')}
      </button>
      <div className="w-px h-5 bg-slate-400 dark:bg-slate-600" />
      <button
        onClick={() => {
          const text = selectionToolbar.word;
          setSelectionToolbar(null);
          window.getSelection().removeAllRanges();
          if (replayText) {
            replayText(text, replaySpeed || 0.8);
          }
        }}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-300 dark:bg-slate-700 rounded-md transition-colors"
        title={t('replayPronunciation')}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>
        {t('replay')}
      </button>
      <div className="w-px h-5 bg-slate-400 dark:bg-slate-600" />
      <button
        onClick={() => {
          setSelectionToolbar(null);
          window.getSelection().removeAllRanges();
          if (repeatLast) {
            repeatLast();
          }
        }}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-300 dark:bg-slate-700 rounded-md transition-colors"
        title={t('replayFullMessage')}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 18v-6a9 9 0 0 1 18 0v6"></path><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path></svg>
        {t('fullReplay')}
      </button>
      <div className="w-px h-5 bg-slate-400 dark:bg-slate-600" />
      <button
        onClick={() => {
          setSelectionToolbar(null);
          window.getSelection().removeAllRanges();
        }}
        className="px-1.5 py-1.5 text-slate-600 dark:text-slate-400 hover:text-black dark:text-white hover:bg-slate-300 dark:bg-slate-700 rounded-md transition-colors"
      >
        <X size={14} />
      </button>
    </div>
  );
}

export function DefinitionPopup({ definitionPopup, setDefinitionPopup, saveToNotebook }) {
  const { t } = useTranslation();
  if (!definitionPopup) return null;
  const { definition, reading, annotation, annotationLabel } = parseDefinition(definitionPopup.text);
  return (
    <div 
      className="fixed z-50 bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 shadow-2xl rounded-xl p-4 w-72 backdrop-blur-md"
      style={{ top: definitionPopup.y, left: definitionPopup.x }}
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-bold text-blue-400 text-lg">{definitionPopup.word}</h3>
        <button 
          onClick={() => {
            setDefinitionPopup(null);
            window.getSelection().removeAllRanges();
          }}
          className="text-slate-600 dark:text-slate-400 hover:text-black dark:text-white"
        >
          <X size={16} />
        </button>
      </div>
      {annotation && (
        <div className="mb-1 inline-flex items-center gap-1.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
          <span className="uppercase tracking-wide text-[9px] text-amber-500/70">{t(ANNOTATION_LABEL_KEYS[annotationLabel] || 'annotation')}</span>
          <span>{formatAnnotation(annotationLabel, annotation, t)}</span>
        </div>
      )}
      {reading && <div className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">{reading}</div>}
      <p className="text-sm text-slate-800 dark:text-slate-200">{definition}</p>
      <div className="mt-4 pt-4 border-t border-slate-300 dark:border-slate-700/50 flex justify-end">
        <button 
          onClick={() => saveToNotebook(definitionPopup.word, definitionPopup.text, "")}
          className="flex items-center gap-2 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-black dark:text-white text-xs font-semibold rounded-lg transition-colors"
        >
          <BookmarkPlus className="w-4 h-4" /> {t('saveToNotebook')}
        </button>
      </div>
    </div>
  );
}

export function InlineFeedbackPopup({ 
  inlineFeedbackPopup, 
  setInlineFeedbackPopup, 
  tutorChatHistory, 
  setTutorChatHistory, 
  tutorInput, 
  setTutorInput, 
  sendTutorMessage,
  isTutorTyping
}) {
  const { t } = useTranslation();
  if (!inlineFeedbackPopup) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl rounded-2xl p-6 w-full max-w-md backdrop-blur-md flex flex-col max-h-[90vh]">
        <div className="flex justify-between items-start mb-6 border-b border-slate-200 dark:border-slate-800 pb-4 shrink-0">
          <h3 className="font-bold text-black dark:text-white text-lg flex items-center gap-2">
            <AlertTriangle className="text-amber-400" size={20} />
            {t('feedback')}
          </h3>
          <button onClick={() => {
            setInlineFeedbackPopup(null);
            setTutorChatHistory([]);
            setTutorInput('');
          }} className="text-slate-600 dark:text-slate-400 hover:text-black dark:text-white bg-slate-200 dark:bg-slate-800 p-1.5 rounded-lg">
            <X size={18} />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
          {inlineFeedbackPopup.grammar && (
            <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl text-amber-900 dark:text-amber-200/90 text-sm leading-relaxed whitespace-pre-wrap font-medium">
              <div className="text-amber-700 dark:text-amber-400 font-bold mb-2 uppercase tracking-wider text-xs flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-600 dark:bg-amber-400"></div>
                {t('grammarLabel')}
              </div>
              {inlineFeedbackPopup.grammar}
            </div>
          )}
          {/* Confidence/Flow are shown only in Analytics, not in this per-message
              feedback popup. This popup surfaces grammar issues only. */}

          {tutorChatHistory.length > 0 && (
            <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-800 space-y-4">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">{t('tutorChat')}</div>
              {tutorChatHistory.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] p-3 rounded-xl text-sm ${
                    msg.role === 'user' 
                      ? 'bg-blue-600 text-black dark:text-white rounded-tr-none' 
                      : 'bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-tl-none border border-slate-300 dark:border-slate-700'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {isTutorTyping && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] p-3 rounded-xl text-sm bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-tl-none border border-slate-300 dark:border-slate-700 flex items-center gap-2">
                    <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <form onSubmit={sendTutorMessage} className="flex gap-2 shrink-0 border-t border-slate-200 dark:border-slate-800 pt-4">
          <input
            type="text"
            value={tutorInput}
            onChange={(e) => setTutorInput(e.target.value)}
            placeholder={t('askQuestion')}
            className="flex-1 bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2 text-sm text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
          <button
            type="submit"
            disabled={!tutorInput.trim() || isTutorTyping}
            className="w-10 h-10 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-200 dark:disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-xl flex items-center justify-center transition-all"
          >
            <Send size={16} className={tutorInput.trim() ? "translate-x-0.5" : ""} />
          </button>
        </form>
      </div>
    </div>
  );
}
