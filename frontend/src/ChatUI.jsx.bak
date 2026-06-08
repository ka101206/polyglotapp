import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Send, Mic, Square, LogOut, BarChart2, Settings, X, Trash2, BookOpen, BookmarkPlus, AlertTriangle, ChevronDown, Volume2 } from 'lucide-react';
import AnalyticsDashboard from './AnalyticsDashboard';
import ErrorBoundary from './ErrorBoundary';

const parseDefinition = (text) => {
  if (!text) return { definition: "", reading: null };
  const parts = text.split(/Reading:\s*/i);
  if (parts.length > 1) {
    return {
      definition: parts[0].trim().replace(/\.$/, ''),
      reading: parts[1].trim()
    };
  }
  return { definition: text, reading: null };
};

export default function ChatUI({ user, onLogout }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem('polyglot_language') || 'Japanese';
  });
  const [difficulty, setDifficulty] = useState(() => {
    const savedLang = localStorage.getItem('polyglot_language') || 'Japanese';
    return localStorage.getItem(`polyglot_difficulty_${savedLang}`) || 'Intermediate';
  });
  const [readingMode, setReadingMode] = useState('なし');
  const [ttsSpeed, setTtsSpeed] = useState(1.0);
  const [replaySpeed, setReplaySpeed] = useState(0.8);

  const [sidebarTab, setSidebarTab] = useState('notebook');

  const SCENARIOS = [
    { id: 'Restaurant', name: 'Ordering at a Restaurant', icon: '🍽️', description: 'Order a meal and pay the bill.' },
    { id: 'Classroom', name: 'New Class Introduction', icon: '🏫', description: 'Introduce yourself to a new classmate.' },
    { id: 'Shopping', name: 'Buying Clothes', icon: '🛍️', description: 'Ask for a different size and purchase.' },
    { id: 'Directions', name: 'Asking for Directions', icon: '🗺️', description: 'Ask how to get to the train station.' },
    { id: 'Convenience Store', name: 'Convenience Store', icon: '🏪', description: 'Buy a drink and ask for a bag.' }
  ];

  const [notebook, setNotebook] = useState([]);
  const [micSensitivity, setMicSensitivity] = useState(50);
  const [silenceTimeout, setSilenceTimeout] = useState(2.5);
  const [showSettings, setShowSettings] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [definitionPopup, setDefinitionPopup] = useState(null);
  const [selectionToolbar, setSelectionToolbar] = useState(null);
  const [inlineFeedbackPopup, setInlineFeedbackPopup] = useState(null);
  
  const [tutorChatHistory, setTutorChatHistory] = useState([]);
  const [tutorInput, setTutorInput] = useState('');
  const [isTutorTyping, setIsTutorTyping] = useState(false);
  const recordingStartTime = useRef(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  const [isThinking, setIsThinking] = useState(false);

  const [wordBankPool, setWordBankPool] = useState([]);
  const [assembledWords, setAssembledWords] = useState([]);

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
    
    // Only update if it doesn't match what is currently saved for this new language
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
  
  const ws = useRef(null);
  const audioContext = useRef(null);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);
  const messagesEndRef = useRef(null);

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

  // Initialize WebSocket and Audio Context
  useEffect(() => {
    const wsUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8081').replace('http', 'ws');
    ws.current = new WebSocket(`${wsUrl}/ws/chat/${user.user_id}`);

    // Queue for sequential audio playback
    const audioPlayQueue = [];
    let isPlaying = false;

    const playNextInQueue = async () => {
      if (audioPlayQueue.length === 0) {
        isPlaying = false;
        setIsAiSpeaking(false);
        return;
      }
      
      isPlaying = true;
      setIsAiSpeaking(true);
      const base64Audio = audioPlayQueue.shift();
      
      try {
        if (!audioContext.current) {
          audioContext.current = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        const binaryString = window.atob(base64Audio);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        
        const audioBuffer = await audioContext.current.decodeAudioData(bytes.buffer);
        const source = audioContext.current.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.current.destination);
        source.onended = playNextInQueue;
        source.start(0);
      } catch (e) {
        console.error("Audio playback error:", e);
        playNextInQueue();
      }
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setIsThinking(false);
      if (data.type === 'text') {
        setMessages(prev => {
          const newMsg = [...prev];
          const last = newMsg.length > 0 ? { ...newMsg[newMsg.length - 1] } : null;
          if (last && last.type === 'scenario' && last.status === 'active') {
             const sMsgs = [...last.messages];
             if (sMsgs.length > 0 && sMsgs[sMsgs.length - 1].role === 'ai') {
               const aiMsg = { ...sMsgs[sMsgs.length - 1] };
               aiMsg.content += data.content;
               if (data.raw_content) aiMsg.raw_content = (aiMsg.raw_content || "") + data.raw_content;
               sMsgs[sMsgs.length - 1] = aiMsg;
             } else {
               sMsgs.push({ role: 'ai', content: data.content, raw_content: data.raw_content || data.content });
             }
             last.messages = sMsgs;
             newMsg[newMsg.length - 1] = last;
          } else {
             if (newMsg.length > 0 && newMsg[newMsg.length - 1].role === 'ai') {
               const aiMsg = { ...newMsg[newMsg.length - 1] };
               aiMsg.content += data.content;
               if (data.raw_content) aiMsg.raw_content = (aiMsg.raw_content || "") + data.raw_content;
               newMsg[newMsg.length - 1] = aiMsg;
             } else {
               newMsg.push({ role: 'ai', content: data.content, raw_content: data.raw_content || data.content });
             }
          }
          return newMsg;
        });
      } else if (data.type === 'grammar') {
        setMessages(prev => {
          const newMsg = [...prev];
          const last = newMsg.length > 0 ? { ...newMsg[newMsg.length - 1] } : null;
          if (last && last.type === 'scenario' && last.status === 'active') {
             const sMsgs = [...last.messages];
             for (let i = sMsgs.length - 1; i >= 0; i--) {
               if (sMsgs[i].role === 'user') {
                 sMsgs[i] = { ...sMsgs[i], grammar: data.content };
                 break;
               }
             }
             last.messages = sMsgs;
             newMsg[newMsg.length - 1] = last;
          } else {
             for (let i = newMsg.length - 1; i >= 0; i--) {
               if (newMsg[i].role === 'user') {
                 newMsg[i] = { ...newMsg[i], grammar: data.content };
                 break;
               }
             }
          }
          return newMsg;
        });
      } else if (data.type === 'pronunciation') {
        setMessages(prev => {
          const newMsg = [...prev];
          const last = newMsg.length > 0 ? { ...newMsg[newMsg.length - 1] } : null;
          if (last && last.type === 'scenario' && last.status === 'active') {
             const sMsgs = [...last.messages];
             for (let i = sMsgs.length - 1; i >= 0; i--) {
               if (sMsgs[i].role === 'user') {
                 sMsgs[i] = { ...sMsgs[i], pronunciation: data.content };
                 break;
               }
             }
             last.messages = sMsgs;
             newMsg[newMsg.length - 1] = last;
          } else {
             for (let i = newMsg.length - 1; i >= 0; i--) {
               if (newMsg[i].role === 'user') {
                 newMsg[i] = { ...newMsg[i], pronunciation: data.content };
                 break;
               }
             }
          }
          return newMsg;
        });
      } else if (data.type === 'scenario_start') {
        setMessages(prev => [
          ...prev, 
          { type: 'scenario', id: data.scenario, goal: data.goal, status: 'active', messages: [] }
        ]);
      } else if (data.type === 'scenario_complete') {
        setMessages(prev => {
          const newMsg = [...prev];
          const last = newMsg.length > 0 ? { ...newMsg[newMsg.length - 1] } : null;
          if (last && last.type === 'scenario' && last.status === 'active') {
             last.status = 'completed';
             newMsg[newMsg.length - 1] = last;
          }
          return newMsg;
        });
      } else if (data.type === 'word_bank') {
        setWordBankPool(data.words);
        setAssembledWords([]);
      } else if (data.type === 'tutor_reply') {
        setIsTutorTyping(false);
        setTutorChatHistory(prev => [...prev, { role: 'ai', content: data.content }]);
      } else if (data.type === 'audio') {
        audioPlayQueue.push(data.data);
        if (!isPlaying) playNextInQueue();
      } else if (data.type === 'audio_done') {
        // AI finished streaming all audio chunks
      } else if (data.type === 'error') {
        console.error("AI Error:", data.content);
      }
    };

    return () => {
      if (ws.current) ws.current.close();
      if (audioContext.current) audioContext.current.close();
    };
  }, [user.user_id]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = (textToSend, duration = null) => {
    if (!textToSend.trim() || !ws.current) return;
    
    const lastMsg = messages.length > 0 ? messages[messages.length - 1] : null;
    const isScenarioActive = lastMsg && lastMsg.type === 'scenario' && lastMsg.status === 'active';
    const activeScenario = isScenarioActive ? lastMsg.id : null;

    setMessages(prev => {
      const newMsg = [...prev];
      const last = newMsg.length > 0 ? { ...newMsg[newMsg.length - 1] } : null;

      if (last && last.type === 'scenario' && last.status === 'active') {
        last.messages = [...last.messages, { role: 'user', content: textToSend }];
        newMsg[newMsg.length - 1] = last;
      } else {
        newMsg.push({ role: 'user', content: textToSend });
      }

      return newMsg;
    });

    ws.current.send(JSON.stringify({
      type: 'chat',
      text: textToSend,
      duration: duration,
      language,
      difficulty,
      scenario: activeScenario,
      reading_mode: readingMode,
      speed: ttsSpeed
    }));
    setIsThinking(true);
    setWordBankPool([]);
    setAssembledWords([]);
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

  const sendText = (e) => {
    e?.preventDefault();
    sendMessage(input);
    setInput('');
  };

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorder.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      
      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };

      mediaRecorder.current.onstop = async () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
        audioChunks.current = [];
        const duration = (Date.now() - recordingStartTime.current) / 1000;
        
        // Transcribe audio
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');
        
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8081';
        try {
          const res = await fetch(`${apiUrl}/api/audio/transcribe`, {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          if (data.text) {
            sendMessage(data.text, duration);
          }
        } catch (err) {
          console.error("Transcription error:", err);
        }
        
        // Stop all tracks to release mic
        stream.getTracks().forEach(track => track.stop());
      };

      audioChunks.current = [];
      recordingStartTime.current = Date.now();
      mediaRecorder.current.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access denied:", err);
    }
  };

  const sendTutorMessage = (e) => {
    e?.preventDefault();
    if (!tutorInput.trim() || !ws.current) return;
    
    setTutorChatHistory(prev => [...prev, { role: 'user', content: tutorInput }]);
    setIsTutorTyping(true);
    
    ws.current.send(JSON.stringify({
      type: 'tutor_chat',
      question: tutorInput,
      original_text: inlineFeedbackPopup?.content,
      grammar_correction: inlineFeedbackPopup?.grammar,
      history: tutorChatHistory,
      language,
      readingMode
    }));
    
    setTutorInput('');
  };

  return (
    <ErrorBoundary>
      <div lang={langCode} className="flex h-screen bg-slate-900 text-slate-100 font-sans relative overflow-hidden">
      
      {/* Main Chat Area (Left Side) */}
      <div className="flex-1 flex flex-col relative">
        <div className="h-2 bg-slate-900 border-b border-slate-800 shrink-0 z-10 w-full" />
        {/* Chat Thread */}
        <div 
          className="flex-1 overflow-y-auto p-6 space-y-6"
          onMouseUp={(e) => {
            const selection = window.getSelection().toString().trim();
            if (selection && selection.length > 0 && selection.length < 200) {
              const x = Math.min(e.clientX, window.innerWidth - 220);
              const y = Math.max(e.clientY - 50, 10);
              setSelectionToolbar({ word: selection, x, y });
              setDefinitionPopup(null);
            } else {
              setSelectionToolbar(null);
            }
          }}
          onClick={(e) => {
            // Dismiss toolbar on click if no selection
            if (!window.getSelection().toString().trim()) {
              setSelectionToolbar(null);
              setDefinitionPopup(null);
            }
          }}
        >
          {messages.map((msg, i) => {
            const renderMessage = (m, keyStr) => {
              if (m.type === 'scenario') {
                if (m.status === 'active') {
                  return (
                    <div key={`scenario-${keyStr}`} className="flex flex-col space-y-6 my-4">
                      <div className="bg-blue-500/10 border border-blue-500/20 text-blue-300 p-5 rounded-2xl flex flex-col gap-3 shadow-lg shadow-blue-500/5">
                        <div className="font-bold uppercase tracking-wider text-xs flex items-center gap-3">
                          <span className="relative flex h-2.5 w-2.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
                          </span>
                          Active Scenario: {m.id}
                        </div>
                        <div className="text-sm font-medium text-blue-100 flex items-start gap-2">
                          <span className="text-blue-400 font-bold">Goal:</span> {m.goal}
                        </div>
                      </div>
                      {m.messages.map((sMsg, j) => renderMessage(sMsg, `${keyStr}-${j}`))}
                    </div>
                  );
                } else {
                  return (
                    <details key={`scenario-${keyStr}`} className="bg-slate-800/40 border border-slate-700/50 rounded-2xl overflow-hidden group my-2">
                      <summary className="p-4 font-bold text-slate-300 cursor-pointer hover:bg-slate-700/50 transition-colors flex items-center justify-between outline-none">
                        <span className="flex items-center gap-3">
                          <div className="w-6 h-6 rounded-full bg-green-500/20 text-green-400 flex items-center justify-center text-xs border border-green-500/30">✓</div>
                          Completed: {m.id}
                        </span>
                        <span className="text-xs font-semibold text-slate-500 bg-slate-800/80 px-2 py-1.5 rounded-lg border border-slate-700">{m.messages.length} messages</span>
                      </summary>
                      <div className="p-6 space-y-6 bg-slate-900/60 border-t border-slate-700/50">
                         {m.messages.map((sMsg, j) => renderMessage(sMsg, `${keyStr}-${j}`))}
                      </div>
                    </details>
                  );
                }
              }
              
              return (
                <motion.div 
                  key={keyStr}
                  initial={{ opacity: 0, y: 10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`relative max-w-[75%] p-4 rounded-2xl ${
                    m.role === 'user' 
                      ? 'bg-blue-600 text-white rounded-tr-none shadow-blue-500/20' 
                      : 'bg-slate-800 text-slate-100 rounded-tl-none border border-slate-700/50 shadow-xl'
                  } shadow-lg text-[15px] leading-relaxed`}>
                    {m.role === 'user' && (m.grammar || m.pronunciation) && (
                      <button 
                        onClick={() => setInlineFeedbackPopup(m)}
                        className="absolute -left-12 top-2 p-2 bg-slate-800 text-amber-400 rounded-full shadow-lg border border-slate-700 hover:bg-slate-700 hover:text-amber-300 transition-colors z-10"
                        title="View Feedback"
                      >
                        <AlertTriangle size={18} />
                      </button>
                    )}
                    {m.role === 'ai' && (m.content.includes('<ruby>') || (language === 'Japanese' && readingMode === 'ふりがな')) ? (
                       <div dangerouslySetInnerHTML={{ __html: m.content }} />
                    ) : (
                       m.content
                    )}
                  </div>
                </motion.div>
              );
            };
            return renderMessage(msg, i.toString());
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Selection Toolbar */}
        {selectionToolbar && (
          <div
            className="fixed z-[60] flex items-center gap-1 bg-slate-800 border border-slate-600 shadow-2xl rounded-lg p-1 backdrop-blur-md"
            style={{ top: selectionToolbar.y, left: selectionToolbar.x }}
          >
            <button
              onClick={async () => {
                const word = selectionToolbar.word;
                const x = selectionToolbar.x;
                const y = selectionToolbar.y + 45;
                setSelectionToolbar(null);
                const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8081';
                try {
                  const res = await fetch(`${apiUrl}/api/ai/definition`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ word, language })
                  });
                  const data = await res.json();
                  if (data.definition) {
                    setDefinitionPopup({
                      word,
                      text: data.definition,
                      x: Math.min(x, window.innerWidth - 300),
                      y: Math.min(y, window.innerHeight - 250)
                    });
                  }
                } catch (err) {
                  console.error('Definition error:', err);
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 rounded-md transition-colors"
              title="Look up definition"
            >
              <BookOpen size={14} /> Dictionary
            </button>
            <div className="w-px h-5 bg-slate-600" />
            <button
              onClick={() => {
                const text = selectionToolbar.word;
                setSelectionToolbar(null);
                window.getSelection().removeAllRanges();
                if (ws.current) {
                  ws.current.send(JSON.stringify({ type: 'repeat', text, language, speed: replaySpeed }));
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 rounded-md transition-colors"
              title="Replay this text"
            >
              <Volume2 size={14} /> Replay
            </button>
            <div className="w-px h-5 bg-slate-600" />
            <button
              onClick={() => {
                setSelectionToolbar(null);
                window.getSelection().removeAllRanges();
              }}
              className="px-1.5 py-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded-md transition-colors"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Definition Popup */}
        {definitionPopup && (() => {
          const { definition, reading } = parseDefinition(definitionPopup.text);
          return (
            <div 
              className="fixed z-50 bg-slate-800 border border-slate-700 shadow-2xl rounded-xl p-4 w-72 backdrop-blur-md"
              style={{ top: definitionPopup.y, left: definitionPopup.x }}
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-bold text-blue-400 text-lg">{definitionPopup.word}</h3>
                <button 
                  onClick={() => {
                    setDefinitionPopup(null);
                    window.getSelection().removeAllRanges();
                  }}
                  className="text-slate-400 hover:text-white"
                >
                  <X size={16} />
                </button>
              </div>
              {reading && <div className="text-sm font-medium text-slate-400 mb-2">{reading}</div>}
              <p className="text-sm text-slate-200">{definition}</p>
              <div className="mt-4 pt-4 border-t border-slate-700/50 flex justify-end">
                <button 
                  onClick={() => saveToNotebook(definitionPopup.word, definitionPopup.text, "")}
                  className="flex items-center gap-2 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-xs font-semibold rounded-lg transition-colors"
                >
                  <BookmarkPlus className="w-4 h-4" /> Save to Notebook
                </button>
              </div>
            </div>
          );
        })()}

        {/* Inline Feedback Popup */}
        {inlineFeedbackPopup && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 shadow-2xl rounded-2xl p-6 w-full max-w-md backdrop-blur-md">
              <div className="flex justify-between items-start mb-6 border-b border-slate-800 pb-4">
                <h3 className="font-bold text-white text-lg flex items-center gap-2">
                  <AlertTriangle className="text-amber-400" size={20} /> 
                  Feedback
                </h3>
                <button onClick={() => {
                  setInlineFeedbackPopup(null);
                  setTutorChatHistory([]);
                  setTutorInput('');
                }} className="text-slate-400 hover:text-white bg-slate-800 p-1.5 rounded-lg">
                  <X size={18} />
                </button>
              </div>
              <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2 pb-2">
                <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                  <div className="text-xs text-slate-400 mb-1 font-semibold uppercase tracking-wide">You said</div>
                  <div className="text-slate-300 italic">"{inlineFeedbackPopup.content}"</div>
                </div>
                {inlineFeedbackPopup.grammar && (
                  <div>
                    <div className="text-xs text-orange-400 mb-1 font-semibold uppercase tracking-wide">Grammar Correction</div>
                    <div className="text-slate-100 font-medium bg-orange-500/10 border border-orange-500/20 p-3 rounded-lg whitespace-pre-wrap">{inlineFeedbackPopup.grammar}</div>
                  </div>
                )}
                {inlineFeedbackPopup.pronunciation && (
                  <div>
                    <div className="text-xs text-purple-400 mb-1 font-semibold uppercase tracking-wide">Pronunciation Hint</div>
                    <div className="text-slate-100 font-medium bg-purple-500/10 border border-purple-500/20 p-3 rounded-lg whitespace-pre-wrap">{inlineFeedbackPopup.pronunciation}</div>
                  </div>
                )}
                
                {/* Tutor Chat Area */}
                {tutorChatHistory.length > 0 && (
                  <div className="mt-6 space-y-3 pt-4 border-t border-slate-700/50">
                    <div className="text-xs text-blue-400 mb-2 font-semibold uppercase tracking-wide">Tutor Chat</div>
                    {tutorChatHistory.map((msg, idx) => (
                      <div key={idx} className={`p-3 rounded-lg text-sm ${msg.role === 'user' ? 'bg-slate-800 text-slate-200 ml-8' : 'bg-blue-500/10 border border-blue-500/20 text-slate-100 mr-8'}`}>
                        {msg.role === 'ai' ? (
                          <div dangerouslySetInnerHTML={{ __html: msg.content }} />
                        ) : (
                          msg.content
                        )}
                      </div>
                    ))}
                    {isTutorTyping && (
                      <div className="p-3 rounded-lg text-sm bg-blue-500/10 border border-blue-500/20 text-slate-100 mr-8 flex items-center gap-2">
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"></span>
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{animationDelay: '150ms'}}></span>
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{animationDelay: '300ms'}}></span>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <form onSubmit={sendTutorMessage} className="mt-4 pt-4 border-t border-slate-700/50 flex gap-2">
                <input
                  type="text"
                  value={tutorInput}
                  onChange={(e) => setTutorInput(e.target.value)}
                  disabled={isTutorTyping}
                  placeholder={isTutorTyping ? "Tutor is thinking..." : "Ask the tutor a question..."}
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors placeholder:text-slate-500 disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!tutorInput.trim() || isTutorTyping}
                  className="px-3 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-lg flex items-center justify-center transition-colors shrink-0"
                >
                  <Send size={16} />
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Input Dock */}
        <div className="p-4 bg-slate-900 border-t border-slate-800 shrink-0 z-10">
          {(wordBankPool.length > 0 || assembledWords.length > 0) && (
            <div className="mb-3 bg-slate-800/50 border border-slate-700/50 rounded-xl p-3">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Build your response</div>
              <div className="min-h-[2.5rem] flex flex-wrap gap-1.5 items-center bg-slate-900/50 border-b border-slate-700 p-2 rounded-t-lg mb-2">
                {assembledWords.length === 0 && (
                  <span className="text-slate-500 italic text-xs">Select words from the bank below...</span>
                )}
                {assembledWords.map((word, idx) => (
                  <button
                    key={`assembled-${idx}`}
                    onClick={() => removeWordFromAssembly(word, idx)}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg shadow-sm text-sm transition-transform active:scale-95"
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
                    className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-600 rounded-lg shadow-sm text-sm transition-transform active:scale-95"
                  >
                    {word}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          <div className="flex items-center gap-2 mb-2">
            <button 
              onClick={() => {
                const lastAiMsg = [...messages].reverse().find(m => m.role === 'ai');
                if (lastAiMsg) {
                  ws.current?.send(JSON.stringify({ type: 'repeat', text: lastAiMsg.raw_content || lastAiMsg.content, language, speed: replaySpeed }));
                }
              }}
              className="text-[10px] font-semibold uppercase tracking-wider bg-slate-800 hover:bg-slate-700 px-3 py-2 rounded-lg text-slate-300 transition-colors border border-slate-700 shadow-sm shrink-0"
            >
              Repeat Last
            </button>

            <div className="flex items-center gap-2 bg-slate-800/50 px-2 py-1.5 rounded-lg border border-slate-700/50 shrink-0 w-48">
              <span className="text-[9px] font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">Voice: {ttsSpeed.toFixed(1)}x</span>
              <input type="range" min="0.5" max="2.0" step="0.1" value={ttsSpeed} onChange={(e) => setTtsSpeed(parseFloat(e.target.value))} className="w-full accent-blue-500" />
            </div>
            <div className="flex items-center gap-2 bg-slate-800/50 px-2 py-1.5 rounded-lg border border-slate-700/50 shrink-0 w-48">
              <span className="text-[9px] font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">Replay: {replaySpeed.toFixed(1)}x</span>
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
                      : 'bg-slate-800/50 text-slate-500 border-slate-700/50'
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
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
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
              className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-slate-500"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="w-12 h-12 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-xl flex items-center justify-center transition-all shadow-lg shadow-blue-500/20 shrink-0"
            >
              <Send size={18} className={input.trim() ? "translate-x-0.5" : ""} />
            </button>
            <button
              type="button"
              onClick={toggleRecording}
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all shadow-lg shrink-0 ${
                isRecording 
                  ? 'bg-red-500 hover:bg-red-600 text-white shadow-red-500/30 animate-pulse' 
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
              }`}
            >
              {isRecording ? <Square size={20} fill="currentColor" /> : <Mic size={20} />}
            </button>
          </form>
        </div>
      </div>

      {/* Right Sidebar */}
      <div className="w-72 bg-slate-950 border-l border-slate-800 flex flex-col z-20">
        {/* User Profile */}
        <div className="p-6 border-b border-slate-800 shrink-0 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shrink-0">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <h2 className="font-semibold truncate">{user.username}</h2>
              <p className="text-[10px] text-slate-400">Polyglot Student</p>
            </div>
          </div>
          <div className="relative shrink-0">
            <button onClick={() => setShowDropdown(!showDropdown)} className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors">
              <ChevronDown className={`w-5 h-5 transition-transform ${showDropdown ? 'rotate-180' : ''}`} />
            </button>
            {showDropdown && (
              <div className="absolute right-0 top-full mt-2 w-48 bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden py-1 z-50">
                <button 
                  onClick={() => { setShowSettings(true); setShowDropdown(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white flex items-center gap-2 transition-colors"
                >
                  <Settings size={16} /> App Settings
                </button>
                <button 
                  onClick={() => { setShowAnalytics(true); setShowDropdown(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white flex items-center gap-2 transition-colors"
                >
                  <BarChart2 size={16} /> Analytics
                </button>
                <div className="h-px bg-slate-700 my-1"></div>
                <button 
                  onClick={onLogout}
                  className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 transition-colors flex items-center gap-2"
                >
                  <LogOut size={16} /> Sign Out
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Tabs */}
        <div className="flex p-2 shrink-0 border-b border-slate-800/50">
          <button 
            onClick={() => setSidebarTab('notebook')}
            className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider rounded-lg transition-colors ${
              sidebarTab === 'notebook' ? 'bg-slate-800 text-white shadow-sm border border-slate-700' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            Notebook
          </button>
          <button 
            onClick={() => setSidebarTab('scenarios')}
            className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider rounded-lg transition-colors ${
              sidebarTab === 'scenarios' ? 'bg-slate-800 text-white shadow-sm border border-slate-700' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            Scenarios
          </button>
        </div>

        {/* Sidebar Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {sidebarTab === 'notebook' ? (
            <div className="space-y-4">
              <div className="text-xs font-semibold text-slate-400 px-2 uppercase tracking-wide">Saved Vocabulary</div>
              {notebook.map((item) => {
                const { definition, reading } = parseDefinition(item.definition);
                return (
                  <div key={item.id} className="p-4 bg-slate-900 rounded-xl border border-slate-700 relative group shadow-sm">
                    <button onClick={() => deleteFromNotebook(item.id)} className="absolute top-3 right-3 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <div className="font-bold text-blue-300 text-lg">{item.word}</div>
                    {reading && <div className="text-sm font-medium text-slate-400 mb-1">{reading}</div>}
                    <div className="text-sm text-slate-300 mt-2 leading-relaxed">{definition}</div>
                  </div>
                );
              })}
              {notebook.length === 0 && (
                <div className="text-slate-500 text-sm text-center py-8">Notebook is empty. Highlight words in the chat to save them!</div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-xs font-semibold text-slate-400 px-2 mb-1 uppercase tracking-wide">Scenarios</div>
              {SCENARIOS.map((s) => (
                <button 
                  key={s.id}
                  onClick={() => {
                    // Check if a scenario is already active
                    const lastMsg = messages[messages.length - 1];
                    if (lastMsg && lastMsg.type === 'scenario' && lastMsg.status === 'active') {
                      alert("Please finish the current scenario before starting a new one!");
                      return;
                    }
                    ws.current?.send(JSON.stringify({ 
                      type: 'start_scenario',
                      scenario: s.id,
                      language,
                      reading_mode: readingMode,
                      speed: ttsSpeed
                    }));
                  }}
                  className="w-full text-left p-4 bg-slate-800/60 hover:bg-slate-700/80 border border-slate-700/50 hover:border-slate-600 rounded-xl transition-all shadow-sm group relative overflow-hidden"
                >
                  <div className="flex items-center gap-3">
                    <div className="text-2xl group-hover:scale-110 transition-transform">{s.icon}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-bold text-slate-200 group-hover:text-blue-300 transition-colors text-sm truncate">{s.name}</div>
                    </div>
                  </div>
                  <div className="grid grid-rows-[0fr] group-hover:grid-rows-[1fr] transition-[grid-template-rows] duration-300">
                    <div className="overflow-hidden">
                      <div className="text-xs text-slate-400 mt-2 leading-relaxed">{s.description}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
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

            </div>
          </div>
        </div>
      )}

      {/* Analytics Modal */}
      {showAnalytics && <AnalyticsDashboard user={user} onClose={() => setShowAnalytics(false)} />}

    </div>
    </ErrorBoundary>
  );
}
