import requests
import socket
import urllib3
import time

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_ip(ip, port):
    print(f"\n--- Testing network connection to {ip}:{port} ---")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3.0)
    try:
        result = sock.connect_ex((ip, port))
        if result == 0:
            print(f"[SUCCESS] Port {port} is open on {ip}!")
        else:
            print(f"[ERROR] Port {port} is closed or unreachable on {ip}. Error code: {result}")
            print("Troubleshooting: Are your phone and laptop on the SAME Wi-Fi network? If not, connect the laptop to the phone's Hotspot.")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
    finally:
        sock.close()

def test_http_endpoint(url):
    print(f"\n--- Testing HTTP endpoint: {url} ---")
    try:
        start = time.time()
        # Stream=True so we just read the headers and not the infinite video feed
        response = requests.get(url, verify=False, stream=True, timeout=5.0)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {response.headers}")
        
        if response.status_code == 200:
            print(f"[SUCCESS] Successfully reached the camera endpoint!")
            
            # Try to read just a little bit of data to confirm it's sending bytes
            data = next(response.iter_content(chunk_size=1024))
            print(f"Received {len(data)} bytes of stream data.")
            if b'image/jpeg' in data or b'\xff\xd8' in data:
                 print("[SUCCESS] Data looks like a valid JPEG stream!")
                 
        elif response.status_code == 401:
            print("[ERROR] 401 Unauthorized. You need to provide the correct Username and Password!")
        else:
            print(f"[ERROR] Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectTimeout:
        print("[ERROR] Connection timed out. The IP address might be wrong or the phone is unreachable.")
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] Connection failed. Is the app actually running on the phone? Error: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")

if __name__ == "__main__":
    target_ip = "10.79.84.100"
    target_port = 4444
    target_url = f"https://{target_ip}:{target_port}/video/mjpeg"
    
    test_ip(target_ip, target_port)
    test_http_endpoint(target_url)
    
    # Also test standard HTTP just in case it's not HTTPS
    target_url_http = f"http://{target_ip}:{target_port}/video/mjpeg"
    test_http_endpoint(target_url_http)
