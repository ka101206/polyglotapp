import { useState, useRef } from 'react';

export default function useMicrophone(onTranscription, silenceTimeoutSec = 2.5, language = "Japanese", userId = null) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);
  const recordingStartTime = useRef(null);

  const stopRecording = () => {
    if (!isRecording) return;
    mediaRecorder.current?.stop();
    setIsRecording(false);
  };

  const startRecording = async () => {
    if (isRecording) return;

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert("Microphone is not supported in this environment. Please ensure you are using HTTPS or localhost.");
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Safari supports audio/mp4, Chrome/Firefox support audio/webm
      let mimeType = 'audio/webm';
      if (!MediaRecorder.isTypeSupported('audio/webm')) {
        if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
        } else {
          mimeType = ''; // Fallback to browser default
        }
      }

      mediaRecorder.current = new MediaRecorder(stream, { mimeType });
      
      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };

      // VAD Implementation
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      analyser.fftSize = 512;
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      
      let silenceStart = null;
      let hasSpoken = false;

      const checkSilence = () => {
        if (!mediaRecorder.current || mediaRecorder.current.state === 'inactive') return;

        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        let average = sum / bufferLength;

        if (average > 10) {
          hasSpoken = true;
          silenceStart = null;
        } else {
          if (hasSpoken) {
            if (!silenceStart) {
              silenceStart = Date.now();
            } else if (Date.now() - silenceStart > silenceTimeoutSec * 1000) {
              mediaRecorder.current.stop();
              setIsRecording(false);
              return;
            }
          }
        }
        requestAnimationFrame(checkSilence);
      };

      mediaRecorder.current.onstop = async () => {
        // Stop all tracks to release mic immediately
        stream.getTracks().forEach(track => track.stop());
        if (audioContext.state !== 'closed') {
          audioContext.close();
        }

        const audioBlob = new Blob(audioChunks.current, { type: mimeType || 'audio/webm' });
        audioChunks.current = [];
        const duration = (Date.now() - recordingStartTime.current) / 1000;
        
        // Transcribe audio
        const formData = new FormData();
        // The backend uses ffmpeg, so it can handle any extension, but we label it based on mimeType
        const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
        formData.append('file', audioBlob, `recording.${ext}`);
        formData.append('language', language);
        if (userId !== null) {
          formData.append('user_id', userId.toString());
        }
        
        const apiUrl = '';
        try {
          const res = await fetch(`${apiUrl}/api/audio/transcribe`, {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          if (data.text && onTranscription) {
            onTranscription(data.text, duration, data.speech);
          }
        } catch (err) {
          console.error("Transcription error:", err);
        }
      };

      audioChunks.current = [];
      recordingStartTime.current = Date.now();
      mediaRecorder.current.start();
      setIsRecording(true);
      checkSilence();
    } catch (err) {
      console.error("Microphone access denied:", err);
      alert("Microphone access denied!\\n\\nIf you are testing on an IP address (HTTP), Safari and Chrome will strictly block the microphone for security reasons. You must use HTTPS or localhost.");
    }
  };

  const toggleRecording = () => {
    if (isRecording) stopRecording();
    else startRecording();
  };

  return { isRecording, startRecording, stopRecording, toggleRecording };
}
