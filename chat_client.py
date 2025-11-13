import socket
import threading
import sys
import os

# --- Konfigurasi ---
# IP ini HARUS IP LOKAL (Wi-Fi) dari laptop yang menjalankan dns_server.py
# Jika kamu tes di laptop yang sama, biarkan 'localhost'
# Jika beda laptop, ganti jadi IP server, misal: '192.168.1.5'
DNS_SERVER_IP = 'localhost' 
DNS_SERVER_PORT = 53000

# Port ini akan digunakan oleh SEMUA klien untuk MENDENGARKAN chat
# Harus sama di semua klien.
CHAT_LISTEN_PORT = 9000 
# --------------------

# Fungsi ini akan berjalan di thread terpisah
def listen_for_messages(my_username):
    """
    Menjalankan Server TCP di background untuk mendengarkan pesan masuk.
    """
    # 1. Buat Server Socket TCP
    # AF_INET = IPv4, SOCK_STREAM = TCP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # 2. Bind ke '0.0.0.0' agar bisa terima dari IP manapun
        server_socket.bind(('0.0.0.0', CHAT_LISTEN_PORT))
        # 3. Mulai mendengarkan
        server_socket.listen()
        print(f"[{my_username}] Siap menerima chat di port {CHAT_LISTEN_PORT}...")

        while True:
            # 4. Terima koneksi yang masuk
            client_socket, client_address = server_socket.accept()
            
            # 5. Terima data pesan
            message = client_socket.recv(1024).decode('utf-8')
            
            # Tampilkan pesan di terminal
            # Kita pakai '\r' dan ' ' agar menimpa prompt input
            print(f"\r[Pesan Masuk] {message}          ")
            print("> ", end="", flush=True) # Tampilkan ulang prompt
            
            # Tutup koneksi klien (karena P2P-nya per-pesan)
            client_socket.close()
            
    except OSError as e:
        print(f"Error di listener thread: {e}")
    finally:
        server_socket.close()

def send_udp_to_dns(message):
    """Fungsi helper untuk kirim/terima pesan UDP ke DNS Server."""
    try:
        # Buat socket UDP
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set timeout 10 detik
        udp_socket.settimeout(10.0)
        
        server_addr = (DNS_SERVER_IP, DNS_SERVER_PORT)
        
        # Kirim pesan
        udp_socket.sendto(message.encode('utf-8'), server_addr)
        
        # Terima balasan
        data, _ = udp_socket.recvfrom(1024)
        return data.decode('utf-8')
        
    except socket.timeout:
        return "ERROR: DNS_TIMEOUT"
    except Exception as e:
        print(f"Error komunikasi UDP: {e}")
        return f"ERROR: {e}"
    finally:
        udp_socket.close()

def main():
    """Fungsi utama untuk menjalankan chat client."""
    
    # --- 1. Pendaftaran Nama Pengguna ---
    while True:
        username = input("Masukkan nama pengguna (tanpa spasi): ")
        if ' ' not in username and username:
            break
        print("Nama tidak boleh kosong atau mengandung spasi.")

    # --- 2. Register ke DNS Server ---
    print(f"Mendaftarkan {username} ke DNS Server di {DNS_SERVER_IP}...")
    response = send_udp_to_dns(f"REGISTER {username}")
    print(f"[DNS Server]: {response}")
    
    if "ERROR" in response:
        print("Gagal mendaftar ke DNS Server. Program berhenti.")
        sys.exit()

    # --- 3. Jalankan Listener Thread ---
    # Daemon=True agar thread otomatis mati saat program utama selesai
    listener = threading.Thread(target=listen_for_messages, args=(username,), daemon=True)
    listener.start()

    print("\n--- Selamat Datang di P2P Chat ---")
    print("Perintah:")
    print("  kirim <nama_teman> <isi_pesan>")
    print("  exit (untuk keluar)")
    print("----------------------------------\n")

    # --- 4. Loop Input Pengguna (Main Thread) ---
    try:
        while True:
            # Prompt input
            user_input = input("> ")
            parts = user_input.split(' ', 2) # Pisah jadi 3 bagian: command, target, message
            command = parts[0].lower()

            if command == 'kirim' and len(parts) == 3:
                target_name = parts[1]
                message_content = parts[2]
                
                # a. Tanya IP teman ke DNS Server
                print(f"Mencari IP untuk {target_name}...")
                ip_response = send_udp_to_dns(f"QUERY {target_name}")
                
                if "ERROR" in ip_response:
                    print(f"[Error] Gagal menemukan {target_name}: {ip_response}")
                    continue
                
                target_ip = ip_response
                print(f"Berhasil menemukan {target_name} di IP {target_ip}.")
                
                # b. Kirim pesan via TCP ke teman
                try:
                    # Buat socket TCP baru untuk *mengirim*
                    send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    send_socket.connect((target_ip, CHAT_LISTEN_PORT))
                    
                    # Format pesan: "Dari <username>: <pesan>"
                    formatted_message = f"Dari {username}: {message_content}"
                    send_socket.sendall(formatted_message.encode('utf-8'))
                    
                    print(f"[Pesan Terkirim] ke {target_name}.")
                
                except Exception as e:
                    print(f"[Error] Gagal mengirim pesan ke {target_ip}: {e}")
                finally:
                    send_socket.close()

            elif command == 'exit':
                break

            else:
                print("Perintah tidak valid. Gunakan: kirim <nama> <pesan>")
                
    except KeyboardInterrupt:
        print("\nKeluar dari program...")
    finally:
        # --- 5. Deregister dari DNS Server ---
        print(f"Membatalkan pendaftaran {username} dari DNS Server...")
        response = send_udp_to_dns(f"DEREGISTER {username}")
        print(f"[DNS Server]: {response}")
        print("Program ditutup.")
        os._exit(0) # Paksa keluar untuk mematikan daemon thread

if __name__ == "__main__":
    main()