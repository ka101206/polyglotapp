import { useState, useEffect, useRef, useCallback } from 'react';

export default function useChatWebSocket(user_id, language, difficulty, readingMode, ttsSpeed, enableGrammar, enableWordBank, voiceGender, onWordBankReceived) {
  const [messages, setMessages] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  const [tutorChatHistory, setTutorChatHistory] = useState([]);
  const [isTutorTyping, setIsTutorTyping] = useState(false);
  const [isTTSWarmingUp, setIsTTSWarmingUp] = useState(false);
  
  const ws = useRef(null);
  const audioRef = useRef(new Audio());

  const onWordBankRef = useRef(onWordBankReceived);
  useEffect(() => {
    onWordBankRef.current = onWordBankReceived;
  }, [onWordBankReceived]);

  const activeScenarioRef = useRef(null);

  useEffect(() => {
    const wsUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8081').replace('http', 'ws');
    const socket = new WebSocket(`${wsUrl}/ws/chat/${user_id}`);
    ws.current = socket;

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
        audioRef.current.src = "data:audio/mp3;base64," + base64Audio;
        audioRef.current.onended = () => {
          playNextInQueue();
        };
        audioRef.current.onerror = (e) => {
          console.error("Audio element error:", e);
          playNextInQueue();
        };
        await audioRef.current.play();
      } catch (e) {
        console.error("Audio playback error:", e);
        playNextInQueue();
      }
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setIsThinking(false);
      
      if (data.type === 'scenario_start') {
        activeScenarioRef.current = data.scenario;
        setMessages(prev => {
          const newMsg = prev.map(m => m.type === 'scenario' && m.status === 'active' ? { ...m, status: 'completed' } : m);
          newMsg.push({ type: 'scenario', id: data.scenario, goal: data.goal, status: 'active', messages: [] });
          return newMsg;
        });
      } else if (data.type === 'scenario_complete') {
        activeScenarioRef.current = null;
        setMessages(prev => {
          const newMsg = [...prev];
          const last = newMsg.length > 0 ? { ...newMsg[newMsg.length - 1] } : null;
          if (last && last.type === 'scenario' && last.status === 'active') {
            last.status = 'completed';
            newMsg[newMsg.length - 1] = last;
          }
          return newMsg;
        });
      } else if (data.type === 'text') {
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
        // Obsolete handler removed
      } else if (data.type === 'scenario_complete') {
        // Obsolete handler removed
      } else if (data.type === 'word_bank') {
        if (onWordBankRef.current) onWordBankRef.current(data.words);
      } else if (data.type === 'tutor_reply') {
        setIsTutorTyping(false);
        setTutorChatHistory(prev => [...prev, { role: 'ai', content: data.content }]);
      } else if (data.type === 'audio') {
        audioPlayQueue.push(data.data);
        if (!isPlaying) playNextInQueue();
      } else if (data.type === 'error') {
        console.error("AI Error:", data.content);
      } else if (data.type === 'tokens') {
        setMessages(prev => {
          const newMsg = [...prev];
          const last = newMsg.length > 0 ? { ...newMsg[newMsg.length - 1] } : null;
          if (last && last.type === 'scenario' && last.status === 'active') {
             const sMsgs = [...last.messages];
             if (sMsgs.length > 0 && sMsgs[sMsgs.length - 1].role === 'ai') {
               sMsgs[sMsgs.length - 1].tokens = data.content;
             }
             last.messages = sMsgs;
             newMsg[newMsg.length - 1] = last;
          } else if (newMsg.length > 0 && newMsg[newMsg.length - 1].role === 'ai') {
             newMsg[newMsg.length - 1].tokens = data.content;
          }
          return newMsg;
        });
      } else if (data.type === 'tts_warmup_start') {
        setIsTTSWarmingUp(true);
      } else if (data.type === 'tts_warmup_done') {
        setIsTTSWarmingUp(false);
      }
    };

    socket.onopen = () => {
      // Warmup on initial connection
      setIsTTSWarmingUp(true);
      socket.send(JSON.stringify({ type: 'warmup_tts', language, gender: voiceGender }));
    };

    return () => {
      socket.close();
      if (ws.current === socket) ws.current = null;
    };
  }, [user_id]);

  const prevLangForWarmup = useRef(language);
  const prevGenderForWarmup = useRef(voiceGender);

  useEffect(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      if (prevLangForWarmup.current !== language || prevGenderForWarmup.current !== voiceGender) {
        setIsTTSWarmingUp(true);
        ws.current.send(JSON.stringify({ type: 'warmup_tts', language, gender: voiceGender }));
        prevLangForWarmup.current = language;
        prevGenderForWarmup.current = voiceGender;
      }
    }
  }, [language, voiceGender]);

  const unlockAudio = useCallback(() => {
    // Play a tiny silent WAV to unlock the audio engine on Safari and clear previous src
    audioRef.current.src = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=";
    audioRef.current.play().catch(() => {});
  }, []);

  const sendMessage = useCallback((textToSend, duration = null) => {
    if (!textToSend.trim() || !ws.current) return;
    
    // Play a silent sound to unlock audio engine on Safari and clear previous src
    unlockAudio();
    
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

    // Send the message OUTSIDE the state updater function to prevent double execution in React Strict Mode!
    ws.current.send(JSON.stringify({
      type: 'chat',
      text: textToSend,
      duration: duration,
      language,
      difficulty,
      scenario: activeScenarioRef.current,
      reading_mode: readingMode,
      speed: ttsSpeed,
      enable_grammar: enableGrammar,
      enable_word_bank: enableWordBank,
      gender: voiceGender
    }));

    setIsThinking(true);
    if (onWordBankRef.current) onWordBankRef.current([]);
  }, [language, difficulty, readingMode, ttsSpeed, enableGrammar, enableWordBank, voiceGender]);

  const replayText = useCallback((text, speed) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'repeat', text, language, speed, gender: voiceGender }));
    }
  }, [language, voiceGender]);

  const sendTutorMessage = useCallback((tutorInput, inlineFeedbackPopup) => {
    if (!tutorInput.trim() || !ws.current) return;
    
    unlockAudio();
    
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
  }, [tutorChatHistory, language, readingMode]);

  const triggerScenario = useCallback((scenarioId) => {
    unlockAudio();

    if (ws.current) {
        ws.current.send(JSON.stringify({
            type: 'start_scenario',
            scenario: scenarioId,
            language,
            difficulty,
            reading_mode: readingMode,
            speed: ttsSpeed,
            enable_grammar: enableGrammar,
            enable_word_bank: enableWordBank,
            gender: voiceGender
        }));
    }
    
    // Clear any previous word bank pool
    if (onWordBankRef.current) onWordBankRef.current([]);
  }, [language, difficulty, readingMode, ttsSpeed, enableGrammar, enableWordBank, voiceGender]);

  return {
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
  };
}
