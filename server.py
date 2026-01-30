from flask import Flask, render_template_string, request, jsonify
import secrets
import time
import threading
from collections import defaultdict
from datetime import datetime
import signal
import sys

app = Flask(__name__)

active_streams = {}
stream_frames = defaultdict(dict)
STREAM_TIMEOUT = 120

def cleanup_old_streams():
    while True:
        time.sleep(30)
        now = time.time()
        to_remove = []

        for key, stream in list(active_streams.items()):
            if now - stream['last_update'] > STREAM_TIMEOUT:
                to_remove.append(key)

        for key in to_remove:
            print(f"🗑️ Removendo stream expirada: {key}")
            del active_streams[key]
            if key in stream_frames:
                del stream_frames[key]

COMMUNITY_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>🔴 LIVE COMMUNITY - STREAM TEMPORÁRIO</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0f0f23;
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }
        .warning {
            background: linear-gradient(90deg, #ff416c, #ff4b2b);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
            border: 2px solid #ff0000;
            animation: pulse 3s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 10px #ff0000; }
            50% { box-shadow: 0 0 20px #ff0000; }
            100% { box-shadow: 0 0 10px #ff0000; }
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .streams-container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .live-count {
            background: rgba(255,255,255,0.1);
            padding: 10px 20px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .stream-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }
        .stream-card {
            background: #1a1a2e;
            border-radius: 15px;
            overflow: hidden;
            border: 1px solid #333;
            transition: all 0.3s;
            cursor: pointer;
        }
        .stream-card:hover {
            transform: translateY(-5px);
            border-color: #00d2ff;
            box-shadow: 0 10px 30px rgba(0, 210, 255, 0.3);
        }
        .stream-card:hover .enter-live-btn {
            background: #00d2ff;
        }
        .stream-preview {
            width: 100%;
            height: 180px;
            background: #000;
            position: relative;
            overflow: hidden;
        }
        .stream-preview img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s;
        }
        .stream-card:hover .stream-preview img {
            transform: scale(1.05);
        }
        .stream-info {
            padding: 15px;
        }
        .stream-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .streamer-name {
            font-weight: bold;
            font-size: 1.1em;
            color: #fff;
        }
        .live-badge {
            background: #ff416c;
            color: white;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .stream-stats {
            display: flex;
            gap: 15px;
            margin-top: 10px;
            font-size: 0.9em;
            color: #aaa;
        }
        .enter-live-btn {
            margin-top: 15px;
            width: 100%;
            padding: 10px;
            background: #3a7bd5;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }
        .enter-live-btn:hover {
            background: #00d2ff;
        }
        .no-streams {
            text-align: center;
            padding: 50px;
            color: #666;
            font-size: 1.2em;
            grid-column: 1 / -1;
        }
        .join-section {
            background: rgba(255,255,255,0.05);
            padding: 25px;
            border-radius: 15px;
            max-width: 500px;
            margin: 30px auto;
            text-align: center;
            border: 1px solid #333;
        }
        .code-input {
            width: 100%;
            padding: 15px;
            margin: 15px 0;
            background: rgba(255,255,255,0.1);
            border: 2px solid #3a7bd5;
            border-radius: 10px;
            color: white;
            font-size: 1.2em;
            text-align: center;
            letter-spacing: 3px;
            font-family: monospace;
        }
        .code-input::placeholder {
            color: #888;
        }
        .primary-btn {
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.3s;
        }
        .primary-btn:hover {
            transform: scale(1.05);
        }
        .stream-page {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .stream-player {
            background: #000;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 20px;
            position: relative;
        }
        .stream-player img {
            width: 100%;
            display: block;
        }
        .back-btn {
            background: rgba(255,255,255,0.1);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            margin-bottom: 20px;
        }
        .viewer-count {
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(0,0,0,0.7);
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: bold;
        }
        .auto-refresh-note {
            text-align: center;
            margin-top: 20px;
            color: #888;
            font-size: 0.9em;
        }
        .loading {
            text-align: center;
            padding: 50px;
            color: #00d2ff;
            font-size: 1.2em;
        }
    </style>
</head>
<body>
    <div id="app">
        <div class="warning">
            ⚠️ ATENÇÃO: Todas as lives são TEMPORÁRIAS! TUDO some quando o servidor desliga!
            Nada é salvo. Como uma call do Discord - quando acaba, SOME!
        </div>

        <div class="header">
            <h1>🔴 LIVE COMMUNITY</h1>
            <p>Streams em tempo real • Tudo em memória • Sem salvamento</p>
        </div>

        <div class="join-section">
            <h3>🎬 Entre em uma Live</h3>
            <p>Digite o código da live (6 caracteres):</p>
            <input type="text" class="code-input" id="streamKeyInput"
                   placeholder="Ex: AbC123" maxlength="6" autocomplete="off">
            <br>
            <button class="primary-btn" onclick="enterLive()">
                🚀 ENTRAR NA LIVE
            </button>
            <p id="joinStatus" style="margin-top: 15px;"></p>
        </div>

        <div class="streams-container">
            <div class="live-count" id="liveCount">
                🔴 <span id="streamCount">0</span> streams ativas
            </div>

            <div class="stream-grid" id="streamContainer"></div>
        </div>

        <div class="auto-refresh-note">
            Lista atualiza a cada 5 minutos • Live atualiza a cada 2 segundos
        </div>
    </div>

    <script>
        let currentPage = 'community';
        let currentStreamKey = null;
        let currentViewers = {};

        function enterLive() {
            const key = document.getElementById('streamKeyInput').value.trim().toUpperCase();
            const status = document.getElementById('joinStatus');

            if (!key || key.length !== 6) {
                status.textContent = '❌ Código inválido! Precisa ter 6 caracteres';
                status.style.color = '#ff416c';
                return;
            }

            status.textContent = '🔄 Verificando live...';
            status.style.color = '#00d2ff';

            fetch(`/api/check_stream/${key}`)
                .then(r => r.json())
                .then(data => {
                    if (data.exists) {
                        if (currentStreamKey && currentStreamKey !== key) {
                            fetch(`/api/viewer_left/${currentStreamKey}`, {method: 'POST'});
                            delete currentViewers[currentStreamKey];
                        }

                        fetch(`/api/viewer_joined/${key}`, {method: 'POST'});
                        currentViewers[key] = true;
                        currentStreamKey = key;

                        showStreamPage(key);
                    } else {
                        status.textContent = '❌ Live não encontrada ou expirada!';
                        status.style.color = '#ff416c';
                    }
                })
                .catch(() => {
                    status.textContent = '❌ Erro ao conectar no servidor';
                    status.style.color = '#ff416c';
                });
        }

        function enterLiveWithKey(key) {
            if (currentStreamKey && currentStreamKey !== key) {
                fetch(`/api/viewer_left/${currentStreamKey}`, {method: 'POST'});
                delete currentViewers[currentStreamKey];
            }

            fetch(`/api/viewer_joined/${key}`, {method: 'POST'});
            currentViewers[key] = true;
            currentStreamKey = key;

            showStreamPage(key);
        }

        function showStreamPage(key) {
            currentPage = 'stream';

            document.getElementById('app').innerHTML = `
                <div class="stream-page">
                    <button class="back-btn" onclick="showCommunityPage()">← Voltar para Comunidade</button>

                    <div class="stream-player">
                        <div id="streamFrameContainer" class="loading">
                            🎬 Conectando à live...
                        </div>
                        <div class="viewer-count" id="viewerCount">👁️ 0 espectadores</div>
                    </div>

                    <div style="text-align: center; margin-top: 20px;">
                        <h3>🔑 Código da Live: <span style="color: #00d2ff; font-family: monospace;">${key}</span></h3>
                        <p>Compartilhe este código para outros entrarem</p>
                    </div>
                </div>
            `;

            updateStreamFrame();
            setInterval(updateStreamFrame, 2000);
        }

        function updateStreamFrame() {
            if (!currentStreamKey) return;

            const container = document.getElementById('streamFrameContainer');
            const viewerCount = document.getElementById('viewerCount');

            fetch(`/api/frame/${currentStreamKey}?_=${Date.now()}`)
                .then(r => r.text())
                .then(frame => {
                    if (frame && frame !== 'NO_FRAME') {
                        container.innerHTML = `<img src="data:image/jpeg;base64,${frame}"
                                               alt="Live Stream"
                                               style="width:100%;"
                                               onerror="this.src='data:image/jpeg;base64,';">`;
                    } else {
                        container.innerHTML = '<div class="loading">⏳ Aguardando transmissão...</div>';
                    }
                })
                .catch(() => {
                    container.innerHTML = '<div class="loading">❌ Erro ao carregar stream</div>';
                });

            fetch(`/api/stream_info/${currentStreamKey}`)
                .then(r => r.json())
                .then(data => {
                    if (data.viewers !== undefined) {
                        viewerCount.textContent = `👁️ ${data.viewers} espectadores`;
                    }
                });
        }

        function showCommunityPage() {
            if (currentStreamKey) {
                fetch(`/api/viewer_left/${currentStreamKey}`, {method: 'POST'});
                delete currentViewers[currentStreamKey];
                currentStreamKey = null;
            }

            currentPage = 'community';
            loadCommunityPage();
        }

        function loadCommunityPage() {
            fetch('/community_html')
                .then(r => r.text())
                .then(html => {
                    document.getElementById('app').innerHTML = html;
                    loadStreams();
                });
        }

        function loadStreams() {
            fetch('/api/streams')
                .then(r => r.json())
                .then(streams => {
                    const container = document.getElementById('streamContainer');
                    const countElement = document.getElementById('streamCount');

                    countElement.textContent = streams.length;

                    if (streams.length === 0) {
                        container.innerHTML = '<div class="no-streams">📡 Nenhuma live ativa no momento</div>';
                        return;
                    }

                    let html = '';
                    streams.forEach(stream => {
                        html += `
                            <div class="stream-card" onclick="enterLiveWithKey('${stream.key}')">
                                <div class="stream-preview">
                                    ${stream.last_frame ?
                                        `<img src="data:image/jpeg;base64,${stream.last_frame}"
                                              alt="${stream.name}"
                                              onerror="this.style.display='none';this.parentElement.innerHTML='🖥️ Preview indisponível';">` :
                                        '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#666;">🖥️ Preview indisponível</div>'
                                    }
                                </div>
                                <div class="stream-info">
                                    <div class="stream-header">
                                        <div class="streamer-name">${stream.name}</div>
                                        <div class="live-badge">● LIVE</div>
                                    </div>
                                    <div class="stream-stats">
                                        <div>👁️ ${stream.viewers} espectadores</div>
                                        <div>🕒 ${formatTime(stream.started)}</div>
                                    </div>
                                    <button class="enter-live-btn" onclick="event.stopPropagation();enterLiveWithKey('${stream.key}');">
                                        ENTRAR NA LIVE
                                    </button>
                                </div>
                            </div>
                        `;
                    });

                    container.innerHTML = html;

                    Object.keys(currentViewers).forEach(key => {
                        if (!streams.find(s => s.key === key)) {
                            fetch(`/api/viewer_left/${key}`, {method: 'POST'});
                            delete currentViewers[key];
                            if (currentStreamKey === key) {
                                currentStreamKey = null;
                            }
                        }
                    });
                })
                .catch(e => {
                    console.error('Erro ao carregar streams:', e);
                    document.getElementById('streamContainer').innerHTML =
                        '<div class="no-streams">❌ Erro ao carregar streams</div>';
                });
        }

        function formatTime(isoString) {
            const date = new Date(isoString);
            const now = new Date();
            const diffHours = Math.floor((now - date) / (1000 * 60 * 60));

            if (diffHours < 1) {
                return 'Agora';
            } else if (diffHours === 1) {
                return 'Há 1 hora';
            } else {
                return `Há ${diffHours} horas`;
            }
        }

        function autoRefreshStreams() {
            if (currentPage === 'community') {
                loadStreams();
            }
        }

        window.addEventListener('beforeunload', function() {
            if (currentStreamKey) {
                navigator.sendBeacon(`/api/viewer_left/${currentStreamKey}`);
            }
        });

        loadStreams();
        setInterval(autoRefreshStreams, 300000);

        setTimeout(() => {
            const input = document.getElementById('streamKeyInput');
            if (input) input.focus();
        }, 500);
    </script>
</body>
</html>
'''

@app.route('/')
def community():
    return render_template_string(COMMUNITY_HTML)

@app.route('/community_html')
def community_html():
    return COMMUNITY_HTML

@app.route('/api/streams')
def get_streams():
    now = time.time()

    streams = []
    for key, stream in list(active_streams.items()):
        if now - stream['last_update'] > STREAM_TIMEOUT:
            del active_streams[key]
            if key in stream_frames:
                del stream_frames[key]
            continue

        streams.append({
            'key': key,
            'name': stream['name'],
            'viewers': stream.get('viewers', 0),
            'started': stream['started'],
            'last_frame': stream_frames[key].get('frame') if key in stream_frames else None
        })

    return jsonify(streams)

@app.route('/api/register', methods=['POST'])
def register_stream():
    data = request.json
    stream_key = secrets.token_urlsafe(6)[:6].upper()

    active_streams[stream_key] = {
        'name': data.get('name', f'Streamer-{stream_key}'),
        'started': datetime.now().isoformat(),
        'last_update': time.time(),
        'viewers': 0
    }

    return jsonify({
        'success': True,
        'key': stream_key,
        'message': f'Use esta chave no streamer.py: {stream_key}',
        'view_url': f'/?stream={stream_key}'
    })

@app.route('/api/update_frame/<key>', methods=['POST'])
def update_frame(key):
    if key not in active_streams:
        return jsonify({'success': False, 'error': 'Stream não encontrada'}), 404

    active_streams[key]['last_update'] = time.time()

    try:
        frame_data = request.json.get('frame')
        if frame_data:
            stream_frames[key] = {
                'frame': frame_data,
                'timestamp': time.time()
            }
    except:
        pass

    return jsonify({
        'success': True,
        'viewers': active_streams[key].get('viewers', 0)
    })

@app.route('/api/frame/<key>')
def get_frame(key):
    if key in stream_frames and time.time() - stream_frames[key]['timestamp'] < 5:
        return stream_frames[key]['frame'] or 'NO_FRAME'
    return 'NO_FRAME'

@app.route('/api/check_stream/<key>')
def check_stream(key):
    if key in active_streams and time.time() - active_streams[key]['last_update'] < STREAM_TIMEOUT:
        return jsonify({'exists': True})
    return jsonify({'exists': False})

@app.route('/api/stream_info/<key>')
def stream_info(key):
    if key in active_streams:
        return jsonify({
            'viewers': active_streams[key].get('viewers', 0),
            'name': active_streams[key]['name'],
            'started': active_streams[key]['started']
        })
    return jsonify({'error': 'Stream não encontrada'}), 404

@app.route('/api/viewer_joined/<key>', methods=['POST'])
def viewer_joined(key):
    if key in active_streams:
        active_streams[key]['viewers'] = active_streams[key].get('viewers', 0) + 1
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/viewer_left/<key>', methods=['POST'])
def viewer_left(key):
    if key in active_streams:
        active_streams[key]['viewers'] = max(0, active_streams[key].get('viewers', 0) - 1)
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

def signal_handler(sig, frame):
    print("\n\n💀 Servidor sendo encerrado...")
    print("🗑️  TODOS OS DADOS SERÃO PERDIDOS!")
    print("👋 Adeus!")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    print("="*60)
    print("🌐 SERVIDOR DE STREAM COMUNITÁRIO")
    print("="*60)
    print("⚠️  AVISO: Tudo é temporário! Se o servidor desligar, tudo some!")
    print("💾 Nada é salvo no PC. Tudo em memória RAM.")

    cleanup_thread = threading.Thread(target=cleanup_old_streams, daemon=True)
    cleanup_thread.start()

    print("\n🔥 Servidor rodando na porta 5000")
    print("\n📌 PARA DEIXAR PÚBLICO, USE:")
    print("1. ngrok:   ngrok http 5000")
    print("2. cloudflare:  cloudflared tunnel --url http://localhost:5000")
    print("\n⚠️  COMPARTILHE O LINK GERADO PELO NGROK/CLOUDFLARE")
    print("\n⏹️  Ctrl+C para encerrar (TUDO SERÁ PERDIDO)")
    print("="*60)

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
