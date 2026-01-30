# streamer.py - CLIENTE STREAMER (SÓ URL EXTERNA)
import mss
import cv2
import numpy as np
import base64
import io
import time
import requests
from PIL import Image

def capture_and_stream(server_url, stream_key, streamer_name):
    print(f"\n🎬 INICIANDO TRANSMISSÃO")
    print("="*50)
    print(f"🔑 Seu código: {stream_key}")
    print(f"🌐 Servidor: {server_url}")
    print(f"👤 Nome: {streamer_name}")
    print("="*50)
    print("\n🖥️  Capturando tela...")
    print("⏹️  Pressione Ctrl+C para parar\n")

    sct = mss.mss()
    stats_interval = 10
    last_stats_time = time.time()
    frame_count = 0
    error_count = 0
    max_errors = 5

    try:
        while True:
            try:
                screenshot = sct.grab(sct.monitors[1])
                img = np.array(screenshot)

                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
                pil_img = Image.fromarray(img_rgb)

                pil_img.thumbnail((1280, 720))

                buffer = io.BytesIO()
                pil_img.save(buffer, format='JPEG', quality=65, optimize=True)
                buffer.seek(0)
                img_base64 = base64.b64encode(buffer.getvalue()).decode()

                response = requests.post(
                    f"{server_url}/api/update_frame/{stream_key}",
                    json={'frame': img_base64},
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()
                    frame_count += 1
                    error_count = 0

                    current_time = time.time()
                    if current_time - last_stats_time >= stats_interval:
                        fps = frame_count / stats_interval
                        viewers = data.get('viewers', 0)
                        print(f"📊 Stats: {fps:.1f} FPS | 👁️ {viewers} espectadores")
                        frame_count = 0
                        last_stats_time = current_time
                else:
                    error_count += 1
                    if error_count >= max_errors:
                        print("❌ Muitos erros. Verifique conexão.")
                        break

            except requests.exceptions.SSLError:
                error_count += 1
                if error_count >= max_errors:
                    print("❌ Erro SSL! Tente usar HTTP em vez de HTTPS")
                time.sleep(2)

            except requests.exceptions.RequestException:
                error_count += 1
                if error_count >= max_errors:
                    print("❌ Conexão perdida com o servidor")
                time.sleep(2)

            except Exception as e:
                error_count += 1
                if error_count >= max_errors:
                    print(f"❌ Erro na captura: {e}")
                time.sleep(1)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n⏹️  TRANSMISSÃO ENCERRADA")
        print("="*50)
        print(f"🔑 Seu código ainda funciona por 2 minutos: {stream_key}")
        print(f"🔗 URL da comunidade: {server_url}")
        print("="*50)

    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")

def main():
    print("="*60)
    print("🎬 STREAMER.PY - Transmissor de Tela")
    print("="*60)
    print("📢 ESTE É O CLIENTE - VOCÊ VAI TRANSMITIR SUA TELA")
    print("="*60)

    print("\n📌 PRIMEIRO, NO PC DO HOST:")
    print("1. Execute: python server.py")
    print("2. Depois execute: ngrok http 5000")
    print("3. OU: cloudflared tunnel --url http://localhost:5000")
    print("\n🔗 Copie o link HTTPS gerado (ex: https://xxxx.ngrok-free.app)")
    print("="*60)

    while True:
        server_url = input("\n🌐 Cole a URL do servidor (NGROK/CLOUDFLARE): ").strip()

        if not server_url:
            print("❌ URL inválida!")
            continue

        if server_url.endswith('/'):
            server_url = server_url[:-1]

        print(f"\n🔄 Testando conexão com {server_url}...")
        try:
            response = requests.get(f"{server_url}/api/streams", timeout=5)
            if response.status_code == 200:
                print("✅ Conexão estabelecida!")
                break
            else:
                print(f"❌ Servidor respondeu com erro: {response.status_code}")
        except requests.exceptions.SSLError:
            print("⚠️  Erro SSL! Tente usar HTTP em vez de HTTPS")
            if server_url.startswith('https://'):
                http_url = server_url.replace('https://', 'http://')
                print(f"💡 Tente: {http_url}")
                use_http = input("Usar HTTP? (s/n): ").lower().strip()
                if use_http == 's':
                    server_url = http_url
                    break
        except requests.exceptions.RequestException as e:
            print(f"❌ Não consegui conectar: {e}")
            print("💡 Verifique:")
            print("1. O servidor está rodando no host?")
            print("2. Ngrok/Cloudflare está ativo?")
            print("3. URL está correta?")

    streamer_name = input("\n👤 Seu nome/nick (ENTER para 'Streamer'): ").strip()
    if not streamer_name:
        streamer_name = "Streamer"

    print(f"\n🔄 Registrando stream em {server_url}...")
    try:
        response = requests.post(
            f"{server_url}/api/register",
            json={'name': streamer_name},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            stream_key = data['key']

            print("\n" + "="*60)
            print("✅ STREAM CRIADA COM SUCESSO!")
            print("="*60)
            print(f"\n🔑 SEU CÓDIGO ÚNICO: {stream_key}")
            print(f"🌐 URL DA COMUNIDADE: {server_url}")
            print("\n" + "="*60)
            print("\n📢 PARA ESPECTADORES:")
            print("1. Acesse a URL acima")
            print(f"2. Digite o código: {stream_key}")
            print("3. Clique em 'ENTRAR NA LIVE'")
            print("\n" + "="*60)
            print("\n🎥 Iniciando transmissão em 3 segundos...")

            time.sleep(3)

            capture_and_stream(server_url, stream_key, streamer_name)

        else:
            print(f"❌ Erro {response.status_code}: Não foi possível criar a stream")

    except requests.exceptions.SSLError:
        print("❌ Erro SSL! Tente usar HTTP em vez de HTTPS")
        print("💡 Reinicie o streamer.py e use HTTP://")

    except requests.exceptions.RequestException as e:
        print(f"❌ Não foi possível conectar ao servidor!")
        print(f"💡 Erro: {e}")
        print("💡 O servidor pode ter caído ou o ngrok/cloudflare expirou")

    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Encerrado pelo usuário")
    except Exception as e:
        print(f"\n💀 ERRO CRÍTICO: {e}")
    finally:
        input("\nPressione ENTER para sair...")
