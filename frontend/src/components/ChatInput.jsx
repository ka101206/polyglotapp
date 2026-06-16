import React from 'react';
import { Send, Mic, Square, Phone } from 'lucide-react';

export default function ChatInput({
  input,
  setInput,
  sendText,
  isRecording,
  toggleRecording,
  isAiSpeaking,
  isThinking,
  wordBankPool,
  assembledWords,
  addWordToAssembly,
  removeWordFromAssembly,
  language,
  ttsSpeed,
  setTtsSpeed,
  replaySpeed,
  setReplaySpeed,
  onRepeat,
  isConversationMode,
  setIsConversationMode
}) {
  return (
    <div className="p-4 bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 shrink-0 z-10">
      {(wordBankPool.length > 0 || assembledWords.length > 0) && (
        <div className="mb-3 bg-slate-200 dark:bg-slate-800/50 border border-slate-300 dark:border-slate-700/50 rounded-xl p-3">
          <div className="text-[10px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-2">Build your response</div>
          <div className="min-h-[2.5rem] flex flex-wrap gap-1.5 items-center bg-slate-50 dark:bg-slate-900/50 border-b border-slate-300 dark:border-slate-700 p-2 rounded-t-lg mb-2">
            {assembledWords.length === 0 && (
              <span className="text-slate-500 italic text-xs">Select words from the bank below...</span>
            )}
            {assembledWords.map((word, idx) => (
              <button
                key={`assembled-${idx}`}
                onClick={() => removeWordFromAssembly(word, idx)}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-black dark:text-white rounded-lg shadow-sm text-sm transition-transform active:scale-95"
              >
                {word}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-1.5 justify-center min-h-[2.5rem]">
            {wordBankPool.map((word, idx) => (
              <button
                key={`pool-${idx}`}
                onClick={() => addWordToAssembly(word, idx)}
                className="px-3 py-1.5 bg-slate-300 dark:bg-slate-700 hover:bg-slate-400 dark:bg-slate-600 text-slate-800 dark:text-slate-200 border border-slate-400 dark:border-slate-600 rounded-lg shadow-sm text-sm transition-transform active:scale-95"
              >
                {word}
              </button>
            ))}
          </div>
        </div>
      )}
      
      <div className="flex items-center gap-2 mb-2">

        <div className="flex items-center gap-2 bg-slate-200 dark:bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700/50 shrink-0 w-72">
          <span className="text-[9px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider whitespace-nowrap min-w-[65px]">Voice: {ttsSpeed.toFixed(1)}x</span>
          <input type="range" min="0.5" max="2.0" step="0.1" value={ttsSpeed} onChange={(e) => setTtsSpeed(parseFloat(e.target.value))} className="w-full accent-blue-500" />
        </div>
        <div className="flex items-center gap-2 bg-slate-200 dark:bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700/50 shrink-0 w-72">
          <span className="text-[9px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider whitespace-nowrap min-w-[65px]">Replay: {replaySpeed.toFixed(1)}x</span>
          <input type="range" min="0.5" max="2.0" step="0.1" value={replaySpeed} onChange={(e) => setReplaySpeed(parseFloat(e.target.value))} className="w-full accent-blue-500" />
        </div>

        <div className="flex-1 flex justify-end items-center min-w-[80px]">
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border transition-colors ${
            isRecording 
              ? 'bg-red-500/10 text-red-400 border-red-500/20' 
              : isAiSpeaking
                ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                : isThinking
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  : 'bg-slate-200 dark:bg-slate-800/50 text-slate-500 border-slate-300 dark:border-slate-700/50'
          }`}>
            {(isRecording || isAiSpeaking || isThinking) && (
              <span className="relative flex h-1.5 w-1.5">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  isRecording ? 'bg-red-400' : isAiSpeaking ? 'bg-blue-400' : 'bg-amber-400'
                }`}></span>
                <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${
                  isRecording ? 'bg-red-500' : isAiSpeaking ? 'bg-blue-500' : 'bg-amber-500'
                }`}></span>
              </span>
            )}
            {!isRecording && !isAiSpeaking && !isThinking && (
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-600"></span>
            )}
            {isRecording ? 'Listening' : isAiSpeaking ? 'Speaking' : isThinking ? 'Thinking' : 'Idle'}
          </div>
        </div>
      </div>
      <form onSubmit={sendText} className="flex gap-2 max-w-full mx-auto">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          className="flex-1 bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-3 text-sm text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-slate-500"
        />
        <button
          type="submit"
          disabled={!input.trim()}
          className="w-12 h-12 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-200 dark:disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-xl flex items-center justify-center transition-all shadow-lg shadow-blue-500/20 shrink-0"
        >
          <Send size={18} className={input.trim() ? "translate-x-0.5" : ""} />
        </button>
        <button
          type="button"
          onClick={toggleRecording}
          title="Conversation Mode (Microphone)"
          className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all shadow-lg shrink-0 ${
            isRecording 
              ? 'bg-red-500 hover:bg-red-600 text-white shadow-red-500/30 animate-pulse' 
              : isConversationMode
                ? 'bg-green-500 hover:bg-green-600 text-white shadow-green-500/30'
                : 'bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700'
          }`}
        >
          {isConversationMode ? <Square size={18} /> : <Mic size={18} />}
        </button>
      </form>
    </div>
  );
}
