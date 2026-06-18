const WebSocket = require('ws');
const ws = new WebSocket('ws://10.74.10.244:18084/ws/chat/1');
ws.on('open', () => {
    console.log('Connected');
    ws.close();
});
ws.on('error', (err) => {
    console.error('Error:', err);
});
