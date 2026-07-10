import React, { useState, useEffect, useRef } from 'react';
import { Inbox as InboxIcon } from 'lucide-react';
import AnalyticsDashboard from './AnalyticsDashboard';
import ErrorBoundary from './ErrorBoundary';
import useChatWebSocket from './hooks/useChatWebSocket';
import useMicrophone from './hooks/useMicrophone';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import Sidebar from './components/Sidebar';
import SettingsModal from './components/SettingsModal';
import { SelectionToolbar, DefinitionPopup, InlineFeedbackPopup } from './components/Popups';
import Inbox from './Inbox';
import SRSReviewModal from './components/SRSReviewModal';

export default function ChatUI({ user, initialLanguage, onLogout, setUser, isDarkMode, setIsDarkMode, onAdminClick }) {
  const [language, setLanguage] = useState(() => {
    if (initialLanguage) return initialLanguage;
    if (user?.is_admin) return 'None';
    return localStorage.getItem('polyglot_language') || 'Japanese';
  });
  const [difficulty, setDifficulty] = useState(() => {
    const savedLang = user?.is_admin && !initialLanguage ? 'None' : (localStorage.getItem('polyglot_language') || 'Japanese');
    return localStorage.getItem(`polyglot_difficulty_${savedLang}`) || 'Intermediate';
  });
  const [readingMode, setReadingMode] = useState('なし');
  const [ttsSpeed, setTtsSpeed] = useState(1.0);
  const [replaySpeed, setReplaySpeed] = useState(0.8);
  const [sidebarTab, setSidebarTab] = useState('notebook');
  const [notebook, setNotebook] = useState([]);
  const [micSensitivity, setMicSensitivity] = useState(() => {
    const saved = localStorage.getItem('polyglot_mic_sensitivity');
    return saved !== null ? parseInt(saved, 10) : 50;
  });
  const [silenceTimeout, setSilenceTimeout] = useState(() => {
    const saved = localStorage.getItem('polyglot_silence_timeout');
    return saved !== null ? parseFloat(saved) : 2.5;
  });
  const [enableGrammar, setEnableGrammar] = useState(() => localStorage.getItem('polyglot_enable_grammar') !== 'false');
  const [enableWordBank, setEnableWordBank] = useState(() => localStorage.getItem('polyglot_enable_word_bank') !== 'false');
  const [voiceGender, setVoiceGender] = useState(() => localStorage.getItem('polyglot_voice_gender') || 'female');
  const [tokenMode, setTokenMode] = useState(() => localStorage.getItem('polyglot_token_mode') || 'high');
  const [showTokens, setShowTokens] = useState(() => localStorage.getItem('polyglot_show_tokens') === 'true');
  const [showSettings, setShowSettings] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showInbox, setShowInbox] = useState(false);
  const [showSRSReview, setShowSRSReview] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [definitionPopup, setDefinitionPopup] = useState(null);
  const [selectionToolbar, setSelectionToolbar] = useState(null);
  const [inlineFeedbackPopup, setInlineFeedbackPopup] = useState(null);
  const [tutorInput, setTutorInput] = useState('');
  const [input, setInput] = useState('');
  const [wordBankPool, setWordBankPool] = useState([]);
  const [assembledWords, setAssembledWords] = useState([]);
  const [isConversationMode, setIsConversationMode] = useState(false);
  
  const messagesEndRef = useRef(null);
  const langCode = language === 'Japanese' ? 'ja' : language === 'Chinese' ? 'zh-CN' : language === 'Korean' ? 'ko' : language === 'Spanish' ? 'es' : language === 'French' ? 'fr' : language === 'Italian' ? 'it' : 'en';

  const getLocalizedDifficulty = (diffStr, lang) => {
    let levelStr = "Intermediate";
    if (diffStr.includes("Beginner")) levelStr = "Beginner";
    else if (diffStr.includes("Elementary")) levelStr = "Elementary";
    else if (diffStr.includes("Upper Intermediate")) levelStr = "Upper Intermediate";
    else if (diffStr.includes("Intermediate")) levelStr = "Intermediate";
    else if (diffStr.includes("Pre-Advanced")) levelStr = "Pre-Advanced";
    else if (diffStr.includes("Advanced")) levelStr = "Advanced";

    if (lang === 'Japanese') {
      if (levelStr === "Beginner") return "JLPT N5 (Beginner)";
      if (levelStr === "Elementary") return "JLPT N4 (Elementary)";
      if (levelStr === "Intermediate") return "JLPT N3 (Intermediate)";
      if (levelStr === "Upper Intermediate" || levelStr === "Pre-Advanced") return "JLPT N2 (Pre-Advanced)";
      if (levelStr === "Advanced") return "JLPT N1 (Advanced)";
    } else if (lang === 'Chinese') {
      if (levelStr === "Beginner") return "HSK 1-2 (Beginner)";
      if (levelStr === "Elementary") return "HSK 3 (Elementary)";
      if (levelStr === "Intermediate") return "HSK 4 (Intermediate)";
      if (levelStr === "Upper Intermediate" || levelStr === "Pre-Advanced") return "HSK 5 (Upper Intermediate)";
      if (levelStr === "Advanced") return "HSK 6 (Advanced)";
    } else if (lang === 'Korean') {
      if (levelStr === "Beginner") return "TOPIK Level 1 (Beginner)";
      if (levelStr === "Elementary") return "TOPIK Level 2 (Elementary)";
      if (levelStr === "Intermediate") return "TOPIK Level 3 (Intermediate)";
      if (levelStr === "Upper Intermediate" || levelStr === "Pre-Advanced") return "TOPIK Level 4 (Upper Intermediate)";
      if (levelStr === "Advanced") return "TOPIK Level 5-6 (Advanced)";
    } else {
      if (levelStr === "Beginner") return "CEFR A1 (Beginner)";
      if (levelStr === "Elementary") return "CEFR A2 (Elementary)";
      if (levelStr === "Intermediate") return "CEFR B1 (Intermediate)";
      if (levelStr === "Upper Intermediate" || levelStr === "Pre-Advanced") return "CEFR B2 (Upper Intermediate)";
      if (levelStr === "Advanced") return "CEFR C1 (Advanced)";
    }
    return "CEFR B1 (Intermediate)";
  };

  useEffect(() => {
    const savedForNewLang = localStorage.getItem(`polyglot_difficulty_${language}`);
    if (savedForNewLang) {
      setDifficulty(savedForNewLang);
    } else {
      setDifficulty(getLocalizedDifficulty(difficulty, language));
    }
  }, [language]);

  useEffect(() => {
    if (difficulty) {
      localStorage.setItem(`polyglot_difficulty_${language}`, difficulty);
      if (!difficulty.includes("Beginner") && !difficulty.includes("Elementary") && !difficulty.includes("Intermediate")) {
        setWordBankPool([]);
        setAssembledWords([]);
      }
    }
    localStorage.setItem('polyglot_language', language);
    localStorage.setItem('polyglot_token_mode', tokenMode);
  }, [difficulty, language, tokenMode]);

  // Apply forced overrides when user object updates
  useEffect(() => {
    if (user.forced_language && user.forced_language !== language) {
      setLanguage(user.forced_language);
    }
  }, [user.forced_language, language]);

  useEffect(() => {
    if (user.forced_difficulty) {
      const localized = getLocalizedDifficulty(user.forced_difficulty, language);
      if (localized !== difficulty) {
        setDifficulty(localized);
      }
    }
  }, [user.forced_difficulty, difficulty, language]);

  useEffect(() => {
    if (user.force_low_token_mode && tokenMode !== 'low') {
      setTokenMode('low');
    }
  }, [user.force_low_token_mode, tokenMode]);

  useEffect(() => {
    if (user.forced_reading_mode && user.forced_reading_mode !== readingMode) {
      setReadingMode(user.forced_reading_mode);
    }
  }, [user.forced_reading_mode, readingMode]);

  const fetchNotebook = async () => {
    try {
      const apiUrl = '';
      const res = await fetch(`${apiUrl}/api/notebook?user_id=${user.user_id}&requester_id=${user.user_id}`);
      const data = await res.json();
      setNotebook(data);
    } catch (e) {
      console.error("Fetch notebook error:", e);
    }
  };

  const saveToNotebook = async (word, definition, context) => {
    try {
      const apiUrl = '';
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
      const apiUrl = '';
      await fetch(`${apiUrl}/api/notebook/${id}`, { method: 'DELETE' });
      fetchNotebook();
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchNotebook();
  }, [user.user_id]);

  const effectiveEnableWordBank = enableWordBank && (difficulty.includes("Beginner") || difficulty.includes("Elementary") || difficulty.includes("Intermediate"));

  const {
    messages,
    setMessages,
    isThinking,
    isAiSpeaking,
    tutorChatHistory,
    setTutorChatHistory,
    isTutorTyping,
    sendMessage,
    replayText,
    sendTutorMessage,
    triggerScenario,
    isTTSWarmingUp
  } = useChatWebSocket(user.user_id, language, difficulty, readingMode, ttsSpeed, enableGrammar, effectiveEnableWordBank, voiceGender, tokenMode, (words) => {
    setWordBankPool(words);
    setAssembledWords([]);
  });

  const prevLangRef = useRef(language);
  useEffect(() => {
    if (prevLangRef.current !== language) {
      setMessages(prev => [...prev, { role: 'system', content: `Language switched to ${language}` }]);
      prevLangRef.current = language;
    }
  }, [language]);

  // Adaptive CEFR Leveling
  const prevMsgLengthRef = useRef(messages.length);
  useEffect(() => {
    if (messages.length > prevMsgLengthRef.current) {
      prevMsgLengthRef.current = messages.length;
      let recentUserMsgs = messages.filter(m => m.role === 'user').slice(-3);
      if (recentUserMsgs.length === 3) {
        let errorCount = 0;
        let perfectCount = 0;
        for (const m of recentUserMsgs) {
          if (m.grammar) {
            const gStr = m.grammar.replace(/[^a-zA-Z]/g, '').toUpperCase();
            if (gStr === 'PERFECT') perfectCount++;
            else errorCount++;
          }
        }
        
        const levels = ["Beginner", "Elementary", "Intermediate", "Upper-Intermediate", "Advanced", "Proficient"];
        const currIdx = levels.indexOf(difficulty);
        
        if (errorCount === 3 && currIdx > 0 && !user.forced_difficulty) {
           setDifficulty(levels[currIdx - 1]);
           setMessages(prev => [...prev, { role: 'system', content: `Adaptive Leveling: Lowered difficulty to ${levels[currIdx - 1]} to provide more scaffolding.` }]);
        } else if (perfectCount === 3 && currIdx !== -1 && currIdx < levels.length - 1 && !user.forced_difficulty) {
           setDifficulty(levels[currIdx + 1]);
           setMessages(prev => [...prev, { role: 'system', content: `Adaptive Leveling: Raised difficulty to ${levels[currIdx + 1]} based on excellent performance.` }]);
        }
      }
    }
  }, [messages, difficulty, user.forced_difficulty]);

  const { isRecording, startRecording, stopRecording } = useMicrophone((text, duration) => {
    sendMessage(text, duration);
  }, silenceTimeout, language, user.user_id);

  const handleMicClick = () => {
    if (isConversationMode) {
      setIsConversationMode(false);
      stopRecording();
    } else {
      setIsConversationMode(true);
      startRecording();
    }
  };

  const prevAiSpeaking = useRef(isAiSpeaking);
  useEffect(() => {
    if (prevAiSpeaking.current && !isAiSpeaking) {
      if (isConversationMode && !isRecording) {
        startRecording();
      }
    }
    prevAiSpeaking.current = isAiSpeaking;
  }, [isAiSpeaking, isConversationMode, isRecording, startRecording]);

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
      <div lang={langCode} className="flex h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-sans relative overflow-hidden">
        
        {isTTSWarmingUp && (
          <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-900/80 backdrop-blur-sm transition-opacity duration-300">
            <div className="w-16 h-16 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mb-6"></div>
            <p className="text-2xl font-medium text-slate-800 dark:text-slate-200">Warming up voice model...</p>
            <p className="text-base text-slate-600 dark:text-slate-400 mt-2">Loading high-quality TTS for {language}</p>
          </div>
        )}

        {/* Main Chat Area (Left Side) */}
        <div className="flex-1 flex flex-col relative">
          <div className="h-2 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 shrink-0 z-10 w-full" />
          
          <MessageList 
            user={user}
            messages={messages}
            language={language}
            readingMode={readingMode}
            setInlineFeedbackPopup={setInlineFeedbackPopup}
            setSelectionToolbar={setSelectionToolbar}
            setDefinitionPopup={setDefinitionPopup}
            messagesEndRef={messagesEndRef}
            showTokens={showTokens}
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
            toggleRecording={handleMicClick}
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
            onRepeat={(speed) => replayText(messages[messages.length - 1]?.content, speed)}
            isConversationMode={isConversationMode}
          />
        </div>

        <Sidebar 
          user={user}
          onLogout={onLogout}
          showDropdown={showDropdown}
          setShowDropdown={setShowDropdown}
          setShowSettings={setShowSettings}
          setShowAnalytics={setShowAnalytics}
          setShowInbox={setShowInbox}
          sidebarTab={sidebarTab}
          setSidebarTab={setSidebarTab}
          notebook={notebook}
          deleteFromNotebook={deleteFromNotebook}
          messages={messages}
          triggerScenario={triggerScenario}
          onAdminClick={onAdminClick}
          setShowSRSReview={setShowSRSReview}
        />

        <SettingsModal 
          user={user}
          setUser={setUser}
          onLogout={onLogout}
          showSettings={showSettings}
          setShowSettings={setShowSettings}
          language={language}
          setLanguage={setLanguage}
          difficulty={difficulty}
          setDifficulty={setDifficulty}
          readingMode={readingMode}
          setReadingMode={setReadingMode}
          micSensitivity={micSensitivity}
          setMicSensitivity={(val) => {
            setMicSensitivity(val);
            localStorage.setItem('polyglot_mic_sensitivity', val);
          }}
          silenceTimeout={silenceTimeout}
          setSilenceTimeout={(val) => {
            setSilenceTimeout(val);
            localStorage.setItem('polyglot_silence_timeout', val);
          }}
          enableGrammar={enableGrammar}
          setEnableGrammar={(val) => {
            setEnableGrammar(val);
            localStorage.setItem('polyglot_enable_grammar', val);
          }}
          enableWordBank={enableWordBank}
          setEnableWordBank={(val) => {
            setEnableWordBank(val);
            localStorage.setItem('polyglot_enable_word_bank', val);
          }}
          tokenMode={tokenMode}
          setTokenMode={(val) => {
            setTokenMode(val);
            localStorage.setItem('polyglot_token_mode', val);
          }}
          voiceGender={voiceGender}
          setVoiceGender={(val) => {
            setVoiceGender(val);
            localStorage.setItem('polyglot_voice_gender', val);
          }}
          showTokens={showTokens}
          setShowTokens={(val) => {
            setShowTokens(val);
            localStorage.setItem('polyglot_show_tokens', val);
          }}
          isDarkMode={isDarkMode}
          setIsDarkMode={setIsDarkMode}
        />

        {showAnalytics && <AnalyticsDashboard user={user} onClose={() => setShowAnalytics(false)} />}
        {showInbox && <Inbox user={user} onClose={() => setShowInbox(false)} />}
        {showSRSReview && <SRSReviewModal user={user} onClose={() => setShowSRSReview(false)} />}
      </div>
    </ErrorBoundary>
  );
}
