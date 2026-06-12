import React, { useState, useEffect } from 'react';
import Auth from './Auth';
import LanguageSelect from './LanguageSelect';
import ChatUI from './ChatUI';
import ErrorBoundary from './ErrorBoundary';

function App() {
  const [user, setUser] = useState(null);
  const [selectedLanguage, setSelectedLanguage] = useState(null);
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

  if (!user) {
    return (
      <ErrorBoundary>
        <Auth onLogin={(userData) => setUser(userData)} />
      </ErrorBoundary>
    );
  }

  if (!selectedLanguage) {
    return (
      <ErrorBoundary>
        <LanguageSelect
          user={user}
          onSelect={(lang) => setSelectedLanguage(lang)}
        />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <ChatUI
        user={user}
        initialLanguage={selectedLanguage}
        onLogout={() => { setUser(null); setSelectedLanguage(null); }}
        setUser={setUser}
        isDarkMode={isDarkMode}
        setIsDarkMode={setIsDarkMode}
      />
    </ErrorBoundary>
  );
}

export default App;
