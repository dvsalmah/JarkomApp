import socket
import json
import os

# --- Konfigurasi ---
HOST = '0.0.0.0'  # Mendengarkan di semua alamat IP yang tersedia
PORT = 53000      # Port untuk server DNS kita (bisa diganti)
DB_FILE = 'dns_records.json' # Nama file untuk menyimpan record DNS
BUFFER_SIZE = 1024
# --------------------

def load_records():
    """Memuat record dari file JSON. Jika file tidak ada, buat file baru."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump({}, f) # Buat file JSON kosongan
        return {}
    
    try:
        with open(DB_FILE, 'r') as f:
            # Cek jika file kosong
            if os.path.getsize(DB_FILE) == 0:
                return {}
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: File {DB_FILE} korup atau kosong. Membuat file baru.")
        with open(DB_FILE, 'w') as f:
            json.dump({}, f)
        return {}
    except Exception as e:
        print(f"Error saat memuat DB: {e}")
        return {}

def save_records(records):
    """Menyimpan dictionary record ke file JSON."""
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(records, f, indent=4)
    except Exception as e:
        print(f"Error saat menyimpan DB: {e}")

def handle_request(data, addr, records):
    """Memproses pesan yang masuk dan menentukan respons."""
    
    try:
        message = data.decode('utf-8').strip()
        parts = message.split(' ')
        command = parts[0].upper()
        
        # Alamat IP pengirim
        client_ip = addr[0]

        # 1. Perintah REGISTER
        # Format: REGISTER <nama>
        if command == 'REGISTER' and len(parts) == 2:
            name = parts[1]
            records[name] = client_ip
            save_records(records)
            print(f"[REGISTER] {name} -> {client_ip}")
            return f"OK: {name} berhasil didaftarkan dengan IP {client_ip}".encode('utf-8')

        # 2. Perintah QUERY
        # Format: QUERY <nama>
        elif command == 'QUERY' and len(parts) == 2:
            name = parts[1]
            ip = records.get(name) # .get() aman jika nama tidak ada (hasilnya None)
            
            if ip:
                print(f"[QUERY] {name} -> {ip}")
                return ip.encode('utf-8')
            else:
                print(f"[QUERY] {name} -> NOT_FOUND")
                return "ERROR: NOT_FOUND".encode('utf-8')

        # 3. Perintah DEREGISTER
        # Format: DEREGISTER <nama>
        elif command == 'DEREGISTER' and len(parts) == 2:
            name = parts[1]
            if name in records:
                del records[name]
                save_records(records)
                print(f"[DEREGISTER] {name} dihapus.")
                return f"OK: {name} berhasil dihapus".encode('utf-8')
            else:
                print(f"[DEREGISTER] {name} tidak ditemukan.")
                return "ERROR: NOT_FOUND".encode('utf-8')
        
        # 4. Perintah tidak valid
        else:
            print(f"[INVALID] Perintah tidak dikenal: {message}")
            return "ERROR: INVALID_COMMAND".encode('utf-8')

    except Exception as e:
        print(f"Error saat memproses data: {e}")
        return "ERROR: SERVER_ERROR".encode('utf-8')

def start_server():
    """Fungsi utama untuk menjalankan server."""
    
    # Muat record saat server pertama kali jalan
    records = load_records()
    
    # 1. Membuat Socket UDP
    # AF_INET = IPv4, SOCK_DGRAM = UDP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # 2. Bind socket ke alamat dan port
        s.bind((HOST, PORT))
        print(f"DNS Server (UDP) berjalan di {HOST}:{PORT}...")
        print(f"Database record disimpan di: {DB_FILE}")

        # 3. Loop utama server
        while True:
            # Menunggu pesan masuk
            data, addr = s.recvfrom(BUFFER_SIZE)
            
            print(f"\n[PESAN MASUK] dari {addr}")
            
            # Proses pesan
            response = handle_request(data, addr, records)
            
            # Kirim balasan kembali ke pengirim
            s.sendto(response, addr)
            
    except OSError as e:
        print(f"Socket error: {e}")
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
    finally:
        s.close()
        print("Socket server ditutup.")

# --- Jalankan Server ---
if __name__ == "__main__":
    start_server()