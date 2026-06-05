import React, { useState } from 'react';
import Auth from './Auth';
import ChatUI from './ChatUI';
import ErrorBoundary from './ErrorBoundary';

function App() {
  const [user, setUser] = useState(null);

  if (!user) {
    return (
      <ErrorBoundary>
        <Auth onLogin={(userData) => setUser(userData)} />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <ChatUI user={user} onLogout={() => setUser(null)} />
    </ErrorBoundary>
  );
}

export default App;
