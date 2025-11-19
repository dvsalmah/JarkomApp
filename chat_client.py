import socket
import threading
import json
import time

# konfigurasi
print("=== P2P CHAT APP ===")
MY_DOMAIN = input("Masukkan Username/Domain kamu (contoh: alice): ")
DNS_IP = input("Masukkan IP Laptop Server DNS: ") # Minta IP Laptop server
DNS_PORT = 9999
MY_CHAT_PORT = 5000 

# Ambil IP Laptop sendiri secara otomatis
hostname = socket.gethostname()
MY_IP = socket.gethostbyname(hostname)

# fungsi komunikasi dengan DNS server
def dns_request(payload):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3) # Timeout jika server mati
    try:
        sock.sendto(json.dumps(payload).encode(), (DNS_IP, DNS_PORT))
        data, _ = sock.recvfrom(1024)
        return json.loads(data.decode())
    except Exception as e:
        print(f"[DNS Error] {e}")
        return None

def register_self():
    payload = {"type": "REGISTER", "domain": MY_DOMAIN, "ip": MY_IP}
    resp = dns_request(payload)
    if resp and resp['status'] == 'OK':
        print(f"[*] Berhasil register ke DNS: {MY_DOMAIN} @ {MY_IP}")
    else:
        print("[!] Gagal register ke DNS!")

def resolve_domain(target_domain):
    print(f"[*] Bertanya ke DNS: Siapa IP dari {target_domain}?")
    payload = {"type": "QUERY", "domain": target_domain}
    resp = dns_request(payload)
    if resp and resp['status'] == 'FOUND':
        return resp['ip']
    return None

# fungsi menerima pesan (TCP SERVER)
def listen_for_messages():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', MY_CHAT_PORT))
    server.listen(5)
    
    while True:
        client_sock, addr = server.accept()
        data = client_sock.recv(1024).decode()
        print(f"\n\n[PESAN MASUK] {data}")
        print(f"{MY_DOMAIN}> ", end="", flush=True) # Balikin prompt ketik
        client_sock.close()

# fungsi mengirim pesan (TCP CLIENT)
def send_message():
    target_user = input("Mau chat siapa (username): ")
    message = input("Isi Pesan: ")
    
    # Cari IP teman melalui DNS
    target_ip = resolve_domain(target_user)

    if target_ip:
        print(f"[*] IP {target_user} ditemukan: {target_ip}")
        # Kirim langsung via TCP [cite: 24]
        try:
            chat_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            chat_sock.connect((target_ip, MY_CHAT_PORT))
            full_msg = f"Dari {MY_DOMAIN}: {message}"
            chat_sock.send(full_msg.encode())
            chat_sock.close()
            print("[*] Pesan terkirim!")
        except Exception as e:
            print(f"[!] Gagal kirim chat: {e}")
    else:
        print("[!] User tidak ditemukan di DNS Server.")

if __name__ == "__main__":
    listener = threading.Thread(target=listen_for_messages, daemon=True)
    listener.start()
    
    register_self()
    
    while True:
        print(f"\n{MY_DOMAIN}> (Tekan Enter untuk kirim pesan)")
        input()
        send_message()