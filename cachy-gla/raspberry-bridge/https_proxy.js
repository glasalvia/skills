const https = require('https');
const http = require('http');
const fs = require('fs');
const { execSync } = require('child_process');

const TARGET = { host: '127.0.0.1', port: 18789 };
const PORT = 1443;
const CERT_DIR = '/home/glasalvia/.openclaw/https-proxy-certs';

if (!fs.existsSync(CERT_DIR)) {
    fs.mkdirSync(CERT_DIR, { recursive: true });
}
if (!fs.existsSync(`${CERT_DIR}/key.pem`) || !fs.existsSync(`${CERT_DIR}/cert.pem`)) {
    execSync(`openssl req -x509 -newkey rsa:2048 -keyout ${CERT_DIR}/key.pem -out ${CERT_DIR}/cert.pem -days 3650 -nodes -subj '/CN=raspberry' 2>/dev/null`);
}

const opts = {
    key: fs.readFileSync(`${CERT_DIR}/key.pem`),
    cert: fs.readFileSync(`${CERT_DIR}/cert.pem`),
};

const server = https.createServer(opts, (req, res) => {
    const pr = http.request({ host: TARGET.host, port: TARGET.port, path: req.url, method: req.method, headers: req.headers }, (prRes) => {
        res.writeHead(prRes.statusCode, prRes.headers);
        prRes.pipe(res);
    });
    pr.on('error', () => { res.writeHead(502); res.end(); });
    req.pipe(pr);
});

server.on('upgrade', (req, socket, head) => {
    const pr = http.request({ host: TARGET.host, port: TARGET.port, path: req.url, method: 'GET', headers: req.headers });
    pr.on('upgrade', (prRes, prSocket) => {
        socket.write('HTTP/1.1 101 Switching Protocols\r\n' +
            'Upgrade: websocket\r\n' +
            'Connection: Upgrade\r\n' +
            `Sec-WebSocket-Accept: ${prRes.headers['sec-websocket-accept']}\r\n` +
            '\r\n');
        prSocket.pipe(socket);
        socket.pipe(prSocket);
    });
    pr.on('error', () => socket.end());
    pr.end();
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`HTTPS proxy on https://0.0.0.0:${PORT} → http://${TARGET.host}:${TARGET.port}`);
});