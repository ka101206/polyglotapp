const WebSocket = require('ws');
const ws = new WebSocket('ws://localhost:18084/ws/chat/1');
ws.on('open', () => {
  console.log('Connected');
  ws.send(JSON.stringify({"type": "chat", "text": "hello"}));
});
ws.on('message', (msg) => {
  console.log('Received:', msg.toString());
});
ws.on('error', (err) => console.log('Error:', err));
