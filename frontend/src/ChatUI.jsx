import React, { useState, useEffect, useRef } from 'react';
import AnalyticsDashboard from './AnalyticsDashboard';
import ErrorBoundary from './ErrorBoundary';
import useChatWebSocket from './hooks/useChatWebSocket';
import useMicrophone from './hooks/useMicrophone';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import Sidebar from './components/Sidebar';
import SettingsModal from './components/SettingsModal';
import { SelectionToolbar, DefinitionPopup, InlineFeedbackPopup } from './components/Popups';

export default function ChatUI({ user, onLogout }) {
  const [language, setLanguage] = useState(() => localStorage.getItem('polyglot_language') || 'Japanese');
  const [difficulty, setDifficulty] = useState(() => {
    const savedLang = localStorage.getItem('polyglot_language') || 'Japanese';
    return localStorage.getItem(`polyglot_difficulty_${savedLang}`) || 'Intermediate';
  });
  const [readingMode, setReadingMode] = useState('なし');
  const [ttsSpeed, setTtsSpeed] = useState(1.0);
  const [replaySpeed, setReplaySpeed] = useState(0.8);
  const [sidebarTab, setSidebarTab] = useState('notebook');
  const [notebook, setNotebook] = useState([]);
  const [micSensitivity, setMicSensitivity] = useState(50);
  const [silenceTimeout, setSilenceTimeout] = useState(2.5);
  const [showSettings, setShowSettings] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [definitionPopup, setDefinitionPopup] = useState(null);
  const [selectionToolbar, setSelectionToolbar] = useState(null);
  const [inlineFeedbackPopup, setInlineFeedbackPopup] = useState(null);
  const [tutorInput, setTutorInput] = useState('');
  const [input, setInput] = useState('');
  const [wordBankPool, setWordBankPool] = useState([]);
  const [assembledWords, setAssembledWords] = useState([]);
  
  const messagesEndRef = useRef(null);
  const langCode = language === 'Japanese' ? 'ja' : language === 'Chinese' ? 'zh-CN' : language === 'Korean' ? 'ko' : language === 'Spanish' ? 'es' : language === 'French' ? 'fr' : language === 'Italian' ? 'it' : 'en';

  useEffect(() => {
    let levelStr = "Intermediate";
    if (difficulty.includes("Beginner")) levelStr = "Beginner";
    else if (difficulty.includes("Elementary")) levelStr = "Elementary";
    else if (difficulty.includes("Upper Intermediate")) levelStr = "Upper Intermediate";
    else if (difficulty.includes("Intermediate")) levelStr = "Intermediate";
    else if (difficulty.includes("Pre-Advanced")) levelStr = "Pre-Advanced";
    else if (difficulty.includes("Advanced")) levelStr = "Advanced";

    let newDiff = "Intermediate";
    if (language === 'Japanese') {
      if (levelStr === "Beginner") newDiff = "JLPT N5 (Beginner)";
      else if (levelStr === "Elementary") newDiff = "JLPT N4 (Elementary)";
      else if (levelStr === "Intermediate") newDiff = "JLPT N3 (Intermediate)";
      else if (levelStr === "Upper Intermediate" || levelStr === "Pre-Advanced") newDiff = "JLPT N2 (Pre-Advanced)";
      else if (levelStr === "Advanced") newDiff = "JLPT N1 (Advanced)";
    } else if (language === 'Chinese') {
      if (levelStr === "Beginner") newDiff = "HSK 1-2 (Beginner)";
      else if (levelStr === "Elementary") newDiff = "HSK 3 (Elementary)";
      else if (levelStr === "Intermediate") newDiff = "HSK 4 (Intermediate)";
      else if (levelStr === "Upper Intermediate" || levelStr === "Pre-Advanced") newDiff = "HSK 5 (Upper Intermediate)";
      else if (levelStr === "Advanced") newDiff = "HSK 6 (Advanced)";
    } else if (language === 'Korean') {
      if (levelStr === "Beginner") newDiff = "TOPIK Level 1 (Beginner)";
      else if (levelStr === "Elementary") newDiff = "TOPIK Level 2 (Elementary)";
      else if (levelStr === "Intermediate") newDiff = "TOPIK Level 3 (Intermediate)";
      else if (levelStr === "Upper Intermediate" || levelStr === "Pre-Advanced") newDiff = "TOPIK Level 4 (Upper Intermediate)";
      else if (levelStr === "Advanced") newDiff = "TOPIK Level 5-6 (Advanced)";
    } else {
      if (levelStr === "Beginner") newDiff = "CEFR A1 (Beginner)";
      else if (levelStr === "Elementary") newDiff = "CEFR A2 (Elementary)";
      else if (levelStr === "Intermediate") newDiff = "CEFR B1 (Intermediate)";
      else if (levelStr === "Upper Intermediate" || levelStr === "Pre-Advanced") newDiff = "CEFR B2 (Upper Intermediate)";
      else if (levelStr === "Advanced") newDiff = "CEFR C1 (Advanced)";
    }
    
    const savedForNewLang = localStorage.getItem(`polyglot_difficulty_${language}`);
    if (savedForNewLang) {
      setDifficulty(savedForNewLang);
    } else {
      setDifficulty(newDiff);
    }
  }, [language]);

  useEffect(() => {
    if (difficulty) {
      localStorage.setItem(`polyglot_difficulty_${language}`, difficulty);
      if (!difficulty.includes("Beginner") && !difficulty.includes("Elementary")) {
        setWordBankPool([]);
        setAssembledWords([]);
      }
    }
    localStorage.setItem('polyglot_language', language);
  }, [difficulty, language]);

  const fetchNotebook = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8081';
      const res = await fetch(`${apiUrl}/api/notebook?user_id=${user.user_id}`);
      const data = await res.json();
      setNotebook(data);
    } catch (e) {
      console.error("Fetch notebook error:", e);
    }
  };

  const saveToNotebook = async (word, definition, context) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8081';
      await fetch(`${apiUrl}/api/notebook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.user_id, word, definition, context })
      });
      fetchNotebook();
      setDefinitionPopup(null);
    } catch (e) {
      console.error(e);
    }
  };

  const deleteFromNotebook = async (id) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8081';
      await fetch(`${apiUrl}/api/notebook/${id}`, { method: 'DELETE' });
      fetchNotebook();
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchNotebook();
  }, [user.user_id]);

  const {
    messages,
    isThinking,
    isAiSpeaking,
    tutorChatHistory,
    setTutorChatHistory,
    isTutorTyping,
    sendMessage,
    replayText,
    sendTutorMessage,
    triggerScenario
  } = useChatWebSocket(user.user_id, language, difficulty, readingMode, ttsSpeed, (words) => {
    setWordBankPool(words);
    setAssembledWords([]);
  });

  const { isRecording, toggleRecording } = useMicrophone((text, duration) => {
    sendMessage(text, duration);
  });

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendText = (e) => {
    e?.preventDefault();
    sendMessage(input);
    setInput('');
  };

  const onSendTutorMessage = (e) => {
    e?.preventDefault();
    sendTutorMessage(tutorInput, inlineFeedbackPopup);
    setTutorInput('');
  };

  const addWordToAssembly = (word, index) => {
    const newPool = [...wordBankPool];
    newPool.splice(index, 1);
    setWordBankPool(newPool);
    const newAssembled = [...assembledWords, word];
    setAssembledWords(newAssembled);
    setInput(newAssembled.join(language === 'Chinese' || language === 'Japanese' ? '' : ' '));
  };

  const removeWordFromAssembly = (word, index) => {
    const newAssembled = [...assembledWords];
    newAssembled.splice(index, 1);
    setAssembledWords(newAssembled);
    setWordBankPool([...wordBankPool, word]);
    setInput(newAssembled.join(language === 'Chinese' || language === 'Japanese' ? '' : ' '));
  };

  const repeatLast = () => {
    const lastAiMsg = [...messages].reverse().find(m => m.role === 'ai');
    if (lastAiMsg && replayText) {
      replayText(lastAiMsg.raw_content || lastAiMsg.content, replaySpeed);
    }
  };

  return (
    <ErrorBoundary>
      <div lang={langCode} className="flex h-screen bg-slate-900 text-slate-100 font-sans relative overflow-hidden">
        
        {/* Main Chat Area (Left Side) */}
        <div className="flex-1 flex flex-col relative">
          <div className="h-2 bg-slate-900 border-b border-slate-800 shrink-0 z-10 w-full" />
          
          <MessageList 
            messages={messages}
            language={language}
            readingMode={readingMode}
            setInlineFeedbackPopup={setInlineFeedbackPopup}
            setSelectionToolbar={setSelectionToolbar}
            setDefinitionPopup={setDefinitionPopup}
            messagesEndRef={messagesEndRef}
          />

          <SelectionToolbar 
            selectionToolbar={selectionToolbar} 
            setSelectionToolbar={setSelectionToolbar} 
            setDefinitionPopup={setDefinitionPopup} 
            language={language} 
            replayText={replayText}
            replaySpeed={replaySpeed}
            repeatLast={repeatLast}
          />

          <DefinitionPopup 
            definitionPopup={definitionPopup} 
            setDefinitionPopup={setDefinitionPopup} 
            saveToNotebook={saveToNotebook} 
          />

          <InlineFeedbackPopup 
            inlineFeedbackPopup={inlineFeedbackPopup}
            setInlineFeedbackPopup={setInlineFeedbackPopup}
            tutorChatHistory={tutorChatHistory}
            setTutorChatHistory={setTutorChatHistory}
            tutorInput={tutorInput}
            setTutorInput={setTutorInput}
            sendTutorMessage={onSendTutorMessage}
            isTutorTyping={isTutorTyping}
          />

          <ChatInput 
            input={input}
            setInput={setInput}
            sendText={sendText}
            isRecording={isRecording}
            toggleRecording={toggleRecording}
            isAiSpeaking={isAiSpeaking}
            isThinking={isThinking}
            wordBankPool={wordBankPool}
            assembledWords={assembledWords}
            addWordToAssembly={addWordToAssembly}
            removeWordFromAssembly={removeWordFromAssembly}
            language={language}
            ttsSpeed={ttsSpeed}
            setTtsSpeed={setTtsSpeed}
            replaySpeed={replaySpeed}
            setReplaySpeed={setReplaySpeed}
            onRepeat={repeatLast}
          />
        </div>

        <Sidebar 
          user={user}
          onLogout={onLogout}
          showDropdown={showDropdown}
          setShowDropdown={setShowDropdown}
          setShowSettings={setShowSettings}
          setShowAnalytics={setShowAnalytics}
          sidebarTab={sidebarTab}
          setSidebarTab={setSidebarTab}
          notebook={notebook}
          deleteFromNotebook={deleteFromNotebook}
          messages={messages}
          triggerScenario={triggerScenario}
        />

        <SettingsModal 
          showSettings={showSettings}
          setShowSettings={setShowSettings}
          language={language}
          setLanguage={setLanguage}
          difficulty={difficulty}
          setDifficulty={setDifficulty}
          readingMode={readingMode}
          setReadingMode={setReadingMode}
          micSensitivity={micSensitivity}
          setMicSensitivity={setMicSensitivity}
          silenceTimeout={silenceTimeout}
          setSilenceTimeout={setSilenceTimeout}
        />

        {showAnalytics && <AnalyticsDashboard user={user} onClose={() => setShowAnalytics(false)} />}
      </div>
    </ErrorBoundary>
  );
}
