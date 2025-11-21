import socket
import json

#konfig server
SERVER_IP = '0.0.0.0'   
SERVER_PORT = 9999     

dns_records = {}

def start_dns_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    
    print(f"[*] DNS Server berjalan di Port {SERVER_PORT}...")
    print(f"[*] Menunggu client (Register / Query / Get Users)...")

    while True:
        try:
            try:
                data, addr = sock.recvfrom(4096)
            except ConnectionResetError:
                continue 
            except OSError as e:
                if e.winerror == 10054: continue
                else: raise e
                
            request = json.loads(data.decode())
            response = {}
            command = request.get('type')
            
            if command == 'REGISTER':
                domain = request.get('domain')
                ip = request.get('ip')
                dns_records[domain] = ip
                print(f"[+] REGISTER: {domain} -> {ip} (dari {addr})")
                response = {"status": "OK", "message": f"{domain} registered"}
            
            elif command == 'QUERY':
                domain = request.get('domain')
                target_ip = dns_records.get(domain)
                
                if target_ip:
                    print(f"[?] QUERY: Mencari {domain} -> DITEMUKAN: {target_ip}")
                    response = {"status": "FOUND", "ip": target_ip}
                else:
                    print(f"[!] QUERY: Mencari {domain} -> TIDAK DITEMUKAN")
                    response = {"status": "NOT_FOUND"}

            elif command == 'GET_USERS':
                online_list = []
                for user, ip_addr in dns_records.items():
                    online_list.append({"username": user, "ip": ip_addr})
                
                print(f"[i] GET_USERS: Mengirim {len(online_list)} user ke {addr}")
                response = {"status": "OK", "users": online_list}
            
            sock.sendto(json.dumps(response).encode(), addr)
            
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    start_dns_server()