import React, { useState } from 'react';
import { Settings, X, Languages } from 'lucide-react';
import { useTranslation, UI_LANGUAGES } from '../i18n';

export default function SettingsModal({
  user,
  setUser,
  onLogout,
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
  setEnableWordBank,
  voiceGender,
  setVoiceGender,
  tokenMode,
  setTokenMode,
  showTokens,
  setShowTokens,
  isDarkMode,
  setIsDarkMode
}) {
  const { t, uiLang, setUiLang } = useTranslation();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [isUpdatingUsername, setIsUpdatingUsername] = useState(false);
  const [newNickname, setNewNickname] = useState('');
  const [isUpdatingNickname, setIsUpdatingNickname] = useState(false);

  if (!showSettings) return null;

  const handleUpdateNickname = async () => {
    if (!newNickname.trim()) return;
    setIsUpdatingNickname(true);
    try {
      const apiUrl = '';
      const res = await fetch(`${apiUrl}/api/users/${user.user_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: newNickname.trim() })
      });
      const data = await res.json();
      if (res.ok) {
        setUser(data);
        setNewNickname('');
        alert(t('nicknameSaved'));
      } else {
        alert(data.detail || t('failedUpdateNickname'));
      }
    } catch (err) {
      console.error(err);
      alert(t('errorUpdatingNickname'));
    } finally {
      setIsUpdatingNickname(false);
    }
  };

  const handleUpdateUsername = async () => {
    if (!newUsername.trim()) return;
    setIsUpdatingUsername(true);
    try {
      const apiUrl = '';
      const res = await fetch(`${apiUrl}/api/users/${user.user_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: newUsername.trim() })
      });
      const data = await res.json();
      if (res.ok) {
        setUser(data);
        setNewUsername('');
        alert(t('usernameUpdated'));
      } else {
        alert(data.detail || t('failedUpdateUsername'));
      }
    } catch (err) {
      console.error(err);
      alert(t('errorUpdatingUsername'));
    } finally {
      setIsUpdatingUsername(false);
    }
  };

  const handleDeleteAccount = async () => {
    try {
      const apiUrl = '';
      const res = await fetch(`${apiUrl}/api/users/${user.user_id}`, { method: 'DELETE' });
      if (res.ok) {
        onLogout();
      } else {
        alert(t('failedDeleteAccount'));
      }
    } catch (err) {
      console.error(err);
      alert(t('errorDeletingAccount'));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-2xl w-full max-w-md shadow-2xl flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-xl font-bold text-black dark:text-white flex items-center gap-2">
            <Settings className="w-5 h-5 text-blue-400" />
            {t('settings')}
          </h2>
          <button onClick={() => setShowSettings(false)} className="text-slate-600 dark:text-slate-400 hover:text-black dark:text-white">
            <X className="w-6 h-6" />
          </button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[70vh] space-y-6">
          <div className="space-y-3">
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">{t('targetLanguage')}</label>
            <select disabled={!!user.forced_language} value={language} onChange={(e) => setLanguage(e.target.value)} className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-800 dark:text-slate-200 outline-none focus:border-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              {user?.is_admin && <option value="None">None</option>}
              <option value="Japanese">Japanese</option>
              <option value="Spanish">Spanish</option>
              <option value="French">French</option>
              <option value="Italian">Italian</option>
              <option value="Chinese">Chinese</option>
              <option value="Korean">Korean</option>
              <option value="English">English</option>
            </select>
            {user.forced_language && <p className="text-xs text-blue-500 mt-1">{t('languageForced')}</p>}
          </div>

          <div className="space-y-3">
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">{t('difficulty')}</label>
            <select disabled={!!user.forced_difficulty} value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-800 dark:text-slate-200 outline-none focus:border-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
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
            {user.forced_difficulty && <p className="text-xs text-blue-500 mt-1">{t('difficultyForced')}</p>}
          </div>

          {language === 'Japanese' && (
            <div className="space-y-3">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">{t('readingHelp')}</label>
              <select value={readingMode} onChange={(e) => setReadingMode(e.target.value)} disabled={!!user.forced_reading_mode} className={`w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-800 dark:text-slate-200 outline-none focus:border-blue-500 transition-colors ${user.forced_reading_mode ? 'opacity-50 cursor-not-allowed' : ''}`}>
                <option value="なし">None (Kanji)</option>
                <option value="ふりがな">Furigana</option>
                <option value="かなのみ">Kana Only</option>
              </select>
              {user.forced_reading_mode && <p className="text-xs text-blue-500 mt-1">{t('readingModeForced')}</p>}
            </div>
          )}

          {language === 'Chinese' && (
            <div className="space-y-3">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">{t('readingHelp')}</label>
              <select value={readingMode} onChange={(e) => setReadingMode(e.target.value)} disabled={!!user.forced_reading_mode} className={`w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-800 dark:text-slate-200 outline-none focus:border-blue-500 transition-colors ${user.forced_reading_mode ? 'opacity-50 cursor-not-allowed' : ''}`}>
                <option value="なし">None (Hanzi)</option>
                <option value="拼音">Pinyin</option>
              </select>
              {user.forced_reading_mode && <p className="text-xs text-blue-500 mt-1">{t('readingModeForced')}</p>}
            </div>
          )}

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">{t('micSensitivity')}</label>
              <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{micSensitivity}</span>
            </div>
            <input type="range" min="0" max="100" step="1" value={micSensitivity} onChange={(e) => setMicSensitivity(parseInt(e.target.value))} className="w-full accent-blue-500" />
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">{t('silenceTimeout')}</label>
              <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{silenceTimeout.toFixed(1)}s</span>
            </div>
            <input type="range" min="1.0" max="10.0" step="0.5" value={silenceTimeout} onChange={(e) => setSilenceTimeout(parseFloat(e.target.value))} className="w-full accent-blue-500" />
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('enableGrammarTutor')}</span>
              <div className="relative">
                <input type="checkbox" className="sr-only peer" checked={enableGrammar} onChange={(e) => setEnableGrammar(e.target.checked)} />
                <div className="w-11 h-6 bg-slate-300 dark:bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
              </div>
            </label>

            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('enableWordBank')}</span>
              <div className="relative">
                <input type="checkbox" className="sr-only peer" checked={enableWordBank} onChange={(e) => setEnableWordBank(e.target.checked)} />
                <div className="w-11 h-6 bg-slate-300 dark:bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
              </div>
            </label>

          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">{t('voice')}</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setVoiceGender('female')}
                className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  voiceGender === 'female'
                    ? 'bg-pink-500/20 border border-pink-500 text-pink-300'
                    : 'bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-500'
                }`}
              >
                {t('female')}
              </button>
              <button
                type="button"
                onClick={() => setVoiceGender('male')}
                className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  voiceGender === 'male'
                    ? 'bg-blue-500/20 border border-blue-500 text-blue-300'
                    : 'bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-500'
                }`}
              >
                {t('male')}
              </button>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">{t('changeUsername')}</label>
              <div className="flex gap-2">
                <input 
                  type="text" 
                  placeholder={user?.username || "New username"}
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="flex-1 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2 text-sm text-black dark:text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
                <button 
                  onClick={handleUpdateUsername}
                  disabled={!newUsername.trim() || isUpdatingUsername}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 disabled:text-black dark:text-white/50 text-black dark:text-white rounded-xl text-sm font-medium transition-colors"
                >
                  {isUpdatingUsername ? t('updating') : t('update')}
                </button>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">{t('nickname')}</label>
              <div className="flex gap-2">
                <input 
                  type="text" 
                  placeholder={user?.nickname || "Nickname"}
                  value={newNickname}
                  onChange={(e) => setNewNickname(e.target.value)}
                  className="flex-1 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2 text-sm text-black dark:text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
                <button 
                  onClick={handleUpdateNickname}
                  disabled={!newNickname.trim() || isUpdatingNickname}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 disabled:text-black dark:text-white/50 text-black dark:text-white rounded-xl text-sm font-medium transition-colors"
                >
                  {isUpdatingNickname ? t('saving') : t('save')}
                </button>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('darkMode')}</span>
              <div className="relative">
                <input type="checkbox" className="sr-only peer" checked={isDarkMode} onChange={(e) => setIsDarkMode(e.target.checked)} />
                <div className="w-11 h-6 bg-slate-300 dark:bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
              </div>
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('showTokenUsage')}</span>
              <div className="relative">
                <input type="checkbox" className="sr-only peer" checked={showTokens} onChange={(e) => setShowTokens(e.target.checked)} />
                <div className="w-11 h-6 bg-slate-300 dark:bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
              </div>
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <div className="flex flex-col">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('lowTokenMode')}</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">{t('lowTokenModeDesc')}</span>
              </div>
              <div className="relative ml-4">
                <input disabled={!!user.force_low_token_mode} type="checkbox" className="sr-only peer" checked={tokenMode === 'low'} onChange={(e) => setTokenMode(e.target.checked ? 'low' : 'high')} />
                <div className={`w-11 h-6 bg-slate-300 dark:bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-500 ${user.force_low_token_mode ? 'opacity-50 cursor-not-allowed' : ''}`}></div>
              </div>
            </label>
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Languages className="w-3.5 h-3.5" /> {t('interfaceLanguage')}
            </label>
            <select value={uiLang} onChange={(e) => setUiLang(e.target.value)} className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-800 dark:text-slate-200 outline-none focus:border-blue-500 transition-colors">
              {UI_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-4">
            {!showDeleteConfirm ? (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="w-full py-3 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/50 rounded-xl font-medium transition-colors"
              >
                {t('deleteAccount')}
              </button>
            ) : (
              <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4 space-y-3">
                <p className="text-sm text-red-400 font-medium text-center">{t('deleteConfirm')}</p>
                <div className="flex gap-3">
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    className="flex-1 py-2 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg font-medium transition-colors"
                  >
                    {t('cancel')}
                  </button>
                  <button
                    onClick={handleDeleteAccount}
                    className="flex-1 py-2 bg-red-600 hover:bg-red-500 text-black dark:text-white rounded-lg font-medium transition-colors"
                  >
                    {t('yesDelete')}
                  </button>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
