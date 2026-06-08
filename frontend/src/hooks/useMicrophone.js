import { useState, useRef } from 'react';

export default function useMicrophone(onTranscription) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);
  const recordingStartTime = useRef(null);

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
          if (data.text && onTranscription) {
            onTranscription(data.text, duration);
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

  return { isRecording, toggleRecording };
}
