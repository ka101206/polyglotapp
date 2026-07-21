import React, { useState, useEffect } from 'react';
import Auth from './Auth';
import LanguageSelect from './LanguageSelect';
import ChatUI from './ChatUI';
import ErrorBoundary from './ErrorBoundary';
import AdminDashboard from './AdminDashboard';
import { I18nProvider } from './i18n';

function App() {
  const [user, setUser] = useState(null);
  const [selectedLanguage, setSelectedLanguage] = useState(null);
  const [isAdminView, setIsAdminView] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(() => localStorage.getItem('polyglot_theme') === 'dark');

  // Apply dark class to html tag
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('polyglot_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('polyglot_theme', 'light');
    }
  }, [isDarkMode]);

  // Poll for admin overrides
  useEffect(() => {
    if (!user) return;
    const fetchOverrides = async () => {
      try {
        const res = await fetch(`/api/users/${user.user_id}/overrides`);
        if (!res.ok) return;
        const data = await res.json();
        let changed = false;
        const newUser = { ...user };
        
        if (data.forced_language !== user.forced_language) {
          newUser.forced_language = data.forced_language;
          changed = true;
          if (data.forced_language) setSelectedLanguage(data.forced_language);
        }
        if (data.forced_difficulty !== user.forced_difficulty) {
          newUser.forced_difficulty = data.forced_difficulty;
          changed = true;
        }
        if (data.forced_reading_mode !== user.forced_reading_mode) {
          newUser.forced_reading_mode = data.forced_reading_mode;
          changed = true;
        }
        if (data.force_low_token_mode !== user.force_low_token_mode) {
          newUser.force_low_token_mode = data.force_low_token_mode;
          changed = true;
        }
        
        if (changed) {
          setUser(newUser);
        }
      } catch (err) {}
    };
    
    fetchOverrides();
    const interval = setInterval(fetchOverrides, 3000);
    return () => clearInterval(interval);
  }, [user?.user_id, user?.forced_language, user?.forced_difficulty, user?.forced_reading_mode, user?.force_low_token_mode]);

  if (!user) {
    return (
      <I18nProvider>
        <ErrorBoundary>
          <Auth onLogin={(userData) => setUser(userData)} />
        </ErrorBoundary>
      </I18nProvider>
    );
  }

  return (
    <I18nProvider>
    <ErrorBoundary>
      {isAdminView && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-50 dark:bg-slate-900">
          <AdminDashboard user={user} onBack={() => setIsAdminView(false)} />
        </div>
      )}
      {(!selectedLanguage && user?.is_admin !== true) ? (
        <LanguageSelect
          user={user}
          onSelect={(lang) => setSelectedLanguage(lang)}
          onAdminClick={() => setIsAdminView(true)}
        />
      ) : (
        <ChatUI
          user={user}
          initialLanguage={selectedLanguage}
          onLogout={() => { setUser(null); setSelectedLanguage(null); }}
          setUser={setUser}
          isDarkMode={isDarkMode}
          setIsDarkMode={setIsDarkMode}
          onAdminClick={() => setIsAdminView(true)}
        />
      )}
    </ErrorBoundary>
    </I18nProvider>
  );
}

export default App;
