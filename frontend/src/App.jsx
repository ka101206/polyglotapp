import React, { useState } from 'react';
import Auth from './Auth';
import ChatUI from './ChatUI';

function App() {
  const [user, setUser] = useState(null);

  if (!user) {
    return <Auth onLogin={(userData) => setUser(userData)} />;
  }

  return <ChatUI user={user} onLogout={() => setUser(null)} />;
}

export default App;
