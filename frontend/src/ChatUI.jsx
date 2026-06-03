import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Send, Mic, Square, LogOut, BarChart2 } from 'lucide-react';
import AnalyticsDashboard from './AnalyticsDashboard';

export default function ChatUI({ user, onLogout }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  
  const ws = useRef(null);
  const audioContext = useRef(null);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);
  const messagesEndRef = useRef(null);

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
      const audioData = audioPlayQueue.shift();
      
      try {
        if (!audioContext.current) {
          audioContext.current = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        // Decode base64 to array buffer
        const binaryString = window.atob(audioData);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        
        const audioBuffer = await audioContext.current.decodeAudioData(bytes.buffer);
        const source = audioContext.current.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.current.destination);
        source.onended = () => {
          playNextInQueue();
        };
        source.start(0);
      } catch (err) {
        console.error("Audio playback error:", err);
        playNextInQueue();
      }
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'text') {
        setMessages(prev => [...prev, { role: 'ai', content: data.content }]);
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

  const sendText = (e) => {
    e?.preventDefault();
    if (!input.trim() || !ws.current) return;
    
    setMessages(prev => [...prev, { role: 'user', content: input }]);
    ws.current.send(JSON.stringify({ text: input }));
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
            setMessages(prev => [...prev, { role: 'user', content: data.text }]);
            ws.current.send(JSON.stringify({ text: data.text }));
          }
        } catch (err) {
          console.error("Transcription error:", err);
        }
        
        // Stop all tracks to release mic
        stream.getTracks().forEach(track => track.stop());
      };

      audioChunks.current = [];
      mediaRecorder.current.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access denied:", err);
    }
  };

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 font-sans relative">
      {showAnalytics && <AnalyticsDashboard user={user} onClose={() => setShowAnalytics(false)} />}
      
      {/* Sidebar - Analytics & Settings */}
      <div className="w-80 bg-slate-950 border-r border-slate-800 flex flex-col">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 className="font-semibold">{user.username}</h2>
              <p className="text-xs text-slate-400">Polyglot Student</p>
            </div>
          </div>
          
          <div className="space-y-2">
            <button 
              onClick={() => setShowAnalytics(!showAnalytics)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${showAnalytics ? 'bg-blue-500/10 text-blue-400' : 'hover:bg-slate-800 text-slate-300'}`}
            >
              <BarChart2 size={18} />
              <span className="font-medium">Analytics Dashboard</span>
            </button>
          </div>
        </div>

        <div className="mt-auto p-6">
          <button 
            onClick={onLogout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-red-500/10 text-red-400 transition-all"
          >
            <LogOut size={18} />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative">
        
        {/* Header */}
        <header className="h-16 border-b border-slate-800 flex items-center px-6 justify-between bg-slate-900/80 backdrop-blur-md z-10">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="font-medium text-slate-200">Conversation Active</span>
          </div>
          {isAiSpeaking && (
            <div className="flex items-center gap-2 bg-blue-500/10 text-blue-400 px-3 py-1 rounded-full text-sm border border-blue-500/20">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
              </span>
              AI Speaking...
            </div>
          )}
        </header>

        {/* Chat Thread */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
              <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center">
                <Mic size={24} className="text-slate-400" />
              </div>
              <p>Say "Hello" in Japanese to start learning!</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 10, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[75%] p-4 rounded-2xl ${
                  msg.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-tr-none shadow-blue-500/20' 
                    : 'bg-slate-800 text-slate-100 rounded-tl-none border border-slate-700/50 shadow-xl'
                } shadow-lg text-[15px] leading-relaxed`}>
                  {msg.content}
                </div>
              </motion.div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Dock */}
        <div className="p-6 bg-slate-900/80 backdrop-blur-xl border-t border-slate-800">
          <form onSubmit={sendText} className="flex gap-3 max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 bg-slate-800 border border-slate-700 rounded-2xl px-6 py-4 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-slate-500"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="w-14 h-14 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-2xl flex items-center justify-center transition-all shadow-lg shadow-blue-500/20"
            >
              <Send size={20} className={input.trim() ? "translate-x-0.5" : ""} />
            </button>
            <button
              type="button"
              onClick={toggleRecording}
              className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all shadow-lg ${
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
    </div>
  );
}
