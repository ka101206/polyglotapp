import React from 'react';
import { Settings, X } from 'lucide-react';

export default function SettingsModal({
  showSettings,
  setShowSettings,
  language,
  setLanguage,
  difficulty,
  setDifficulty,
  readingMode,
  setReadingMode,
  micSensitivity,
  setMicSensitivity,
  silenceTimeout,
  setSilenceTimeout,
  enableGrammar,
  setEnableGrammar,
  enableWordBank,
  setEnableWordBank
}) {
  if (!showSettings) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md shadow-2xl flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Settings className="w-5 h-5 text-blue-400" />
            Settings
          </h2>
          <button onClick={() => setShowSettings(false)} className="text-slate-400 hover:text-white">
            <X className="w-6 h-6" />
          </button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[70vh] space-y-6">
          <div className="space-y-3">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Target Language</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value)} className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 outline-none focus:border-blue-500 transition-colors">
              <option value="Japanese">Japanese</option>
              <option value="Spanish">Spanish</option>
              <option value="French">French</option>
              <option value="Italian">Italian</option>
              <option value="Chinese">Chinese</option>
              <option value="Korean">Korean</option>
            </select>
          </div>
          
          <div className="space-y-3">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Difficulty</label>
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 outline-none focus:border-blue-500 transition-colors">
              {language === 'Japanese' ? (
                <>
                  <option value="JLPT N5 (Beginner)">JLPT N5 (Beginner)</option>
                  <option value="JLPT N4 (Elementary)">JLPT N4 (Elementary)</option>
                  <option value="JLPT N3 (Intermediate)">JLPT N3 (Intermediate)</option>
                  <option value="JLPT N2 (Pre-Advanced)">JLPT N2 (Pre-Advanced)</option>
                  <option value="JLPT N1 (Advanced)">JLPT N1 (Advanced)</option>
                </>
              ) : language === 'Chinese' ? (
                <>
                  <option value="HSK 1-2 (Beginner)">HSK 1-2 (Beginner)</option>
                  <option value="HSK 3 (Elementary)">HSK 3 (Elementary)</option>
                  <option value="HSK 4 (Intermediate)">HSK 4 (Intermediate)</option>
                  <option value="HSK 5 (Upper Intermediate)">HSK 5 (Upper Intermediate)</option>
                  <option value="HSK 6 (Advanced)">HSK 6 (Advanced)</option>
                </>
              ) : language === 'Korean' ? (
                <>
                  <option value="TOPIK Level 1 (Beginner)">TOPIK Level 1 (Beginner)</option>
                  <option value="TOPIK Level 2 (Elementary)">TOPIK Level 2 (Elementary)</option>
                  <option value="TOPIK Level 3 (Intermediate)">TOPIK Level 3 (Intermediate)</option>
                  <option value="TOPIK Level 4 (Upper Intermediate)">TOPIK Level 4 (Upper Intermediate)</option>
                  <option value="TOPIK Level 5-6 (Advanced)">TOPIK Level 5-6 (Advanced)</option>
                </>
              ) : (
                <>
                  <option value="CEFR A1 (Beginner)">CEFR A1 (Beginner)</option>
                  <option value="CEFR A2 (Elementary)">CEFR A2 (Elementary)</option>
                  <option value="CEFR B1 (Intermediate)">CEFR B1 (Intermediate)</option>
                  <option value="CEFR B2 (Upper Intermediate)">CEFR B2 (Upper Intermediate)</option>
                  <option value="CEFR C1 (Advanced)">CEFR C1 (Advanced)</option>
                </>
              )}
            </select>
          </div>

          {language === 'Japanese' && (
            <div className="space-y-3">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Reading Help</label>
              <select value={readingMode} onChange={(e) => setReadingMode(e.target.value)} className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 outline-none focus:border-blue-500 transition-colors">
                <option value="なし">None (Kanji)</option>
                <option value="ふりがな">Furigana</option>
                <option value="かなのみ">Kana Only</option>
              </select>
            </div>
          )}

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Mic Sensitivity</label>
              <span className="text-xs font-medium text-slate-300">{micSensitivity}</span>
            </div>
            <input type="range" min="0" max="100" step="1" value={micSensitivity} onChange={(e) => setMicSensitivity(parseInt(e.target.value))} className="w-full accent-blue-500" />
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Silence Timeout</label>
              <span className="text-xs font-medium text-slate-300">{silenceTimeout.toFixed(1)}s</span>
            </div>
            <input type="range" min="1.0" max="10.0" step="0.5" value={silenceTimeout} onChange={(e) => setSilenceTimeout(parseFloat(e.target.value))} className="w-full accent-blue-500" />
          </div>

          <div className="pt-4 border-t border-slate-800 space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm font-medium text-slate-300">Enable Grammar Tutor</span>
              <div className="relative">
                <input type="checkbox" className="sr-only peer" checked={enableGrammar} onChange={(e) => setEnableGrammar(e.target.checked)} />
                <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
              </div>
            </label>

            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm font-medium text-slate-300">Enable Word Bank</span>
              <div className="relative">
                <input type="checkbox" className="sr-only peer" checked={enableWordBank} onChange={(e) => setEnableWordBank(e.target.checked)} />
                <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
              </div>
            </label>
          </div>

        </div>
      </div>
    </div>
  );
}
