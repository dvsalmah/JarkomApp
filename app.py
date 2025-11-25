from flask import Flask, render_template, request, jsonify
import socket
import threading
import json
import time

app = Flask(__name__)

#konfig client
print("=== KONFIGURASI CLIENT ===")
MY_USERNAME = input("Masukkan Username: ")
MY_P2P_PORT = int(input("Masukkan Port untuk Chat P2P (cth: 6000): "))
DNS_SERVER_IP = input("Masukkan IP DNS Server: ")
DNS_PORT = 9999

hostname = socket.gethostname()
MY_IP = socket.gethostbyname(hostname) 

chat_history = [] 

def p2p_listener():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_sock.bind(('0.0.0.0', MY_P2P_PORT))
        server_sock.listen(5)
        print(f"\n[SYSTEM] P2P Listener berjalan di Port {MY_P2P_PORT}...")
        
        while True:
            client, addr = server_sock.accept()
            data = client.recv(1024).decode()
            if ":" in data:
                sender_name = data.split(":")[0]
                msg_content = data.split(":", 1)[1]
                chat_history.append({"sender": sender_name, "msg": msg_content, "type": "in"})
            else:
                chat_history.append({"sender": "Unknown", "msg": data, "type": "in"})
                
            client.close()
    except Exception as e:
        print(f"[ERROR Listener] {e}")

def register_dns():
    try:
        payload = {
            "type": "REGISTER", 
            "domain": MY_USERNAME, 
            "ip": MY_IP, 
            "port": MY_P2P_PORT 
        }
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps(payload).encode(), (DNS_SERVER_IP, DNS_PORT))
        print(f"[SYSTEM] Terdaftar di DNS sebagai {MY_USERNAME} ({MY_IP}:{MY_P2P_PORT})")
    except Exception as e:
        print(f"[ERROR DNS] {e}")


@app.route('/')
def index():
    return render_template('index.html', username=MY_USERNAME, ip=MY_IP, port=MY_P2P_PORT)

@app.route('/get_chats')
def get_chats():
    return jsonify(chat_history)

@app.route('/get_active_users')
def get_active_users():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2) 
        
        request_payload = {"type": "GET_USERS"}
        sock.sendto(json.dumps(request_payload).encode(), (DNS_SERVER_IP, DNS_PORT))
        
        data, _ = sock.recvfrom(4096)
        response = json.loads(data.decode())
        
        users = response.get('users', [])
        
        
        return jsonify(users)
    except Exception as e:
        print(f"[ERROR get_users] {e}")
        return jsonify([]) 

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    target_user = data['target']
    message = data['message']
    
    try:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.settimeout(2)
        query = {"type": "QUERY", "domain": target_user}
        udp_sock.sendto(json.dumps(query).encode(), (DNS_SERVER_IP, DNS_PORT))
        
        resp_data, _ = udp_sock.recvfrom(1024)
        resp = json.loads(resp_data.decode())
        
        if resp['status'] == 'FOUND':
            target_ip = resp['ip']
            target_port = MY_P2P_PORT 
            
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.connect((target_ip, target_port))
            
            full_msg = f"{MY_USERNAME}: {message}"
            tcp_sock.send(full_msg.encode())
            tcp_sock.close()
            
            chat_history.append({"sender": "ME", "msg": f"Ke {target_user}: {message}", "type": "out"})
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "msg": "User tidak ditemukan/Offline!"})
            
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

if __name__ == '__main__':
    t = threading.Thread(target=p2p_listener, daemon=True)
    t.start()
    
    register_dns()
    
    print("[SYSTEM] Buka Browser di: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)