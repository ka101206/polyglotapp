import React, { useState } from 'react';
import Auth from './Auth';
import LanguageSelect from './LanguageSelect';
import ChatUI from './ChatUI';
import ErrorBoundary from './ErrorBoundary';

function App() {
  const [user, setUser] = useState(null);
  const [selectedLanguage, setSelectedLanguage] = useState(null);

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
      />
    </ErrorBoundary>
  );
}

export default App;
