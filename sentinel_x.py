import subprocess, sys, os, platform, ctypes, threading, socket, time
import tkinter as tk
from tkinter import messagebox
import winreg

# =================================================================
# 0. SYSTEM CHECK & AUTO-INSTALLER
# =================================================================

def prompt_user(title, message):
    root = tk.Tk()
    root.withdraw()
    return messagebox.askokcancel(title, message)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

def ensure_package(pkg):
    try:
        __import__(pkg)
        print(f"[OK] {pkg} installed")
    except ImportError:
        print(f"[!] {pkg} missing — installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

def is_npcap_installed():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Npcap")
        winreg.CloseKey(key)
        return True
    except:
        return False

def install_npcap():
    url = "https://nmap.org/npcap/dist/npcap-1.79.exe"
    installer = "npcap_installer.exe"

    print("[!] Downloading Npcap...")
    subprocess.run(["powershell", "-Command", f"Invoke-WebRequest '{url}' -OutFile '{installer}'"])

    print("[!] Installing Npcap...")
    subprocess.run([installer, "/S"], shell=True)

def run_system_check():
    print("=== SentinelX System Check ===")

    # Admin
    if not is_admin():
        if prompt_user("SentinelX Requires Admin",
                       "SentinelX needs administrator privileges.\nClick OK to relaunch with elevation."):
            elevate()
        else:
            print("[ERROR] Cannot continue without admin rights.")
            sys.exit()

    # Python version
    if sys.version_info < (3, 10):
        messagebox.showerror("Python Version Error",
                             "Python 3.10+ is required. Please update Python.")
        sys.exit()

    # Required Python packages
    required_packages = ["scapy", "psutil", "rich"]
    for pkg in required_packages:
        ensure_package(pkg)

    # Npcap
    if not is_npcap_installed():
        if prompt_user("Npcap Required",
                       "Npcap is required for packet sniffing.\nClick OK to install it now."):
            install_npcap()
        else:
            print("[ERROR] Npcap missing — cannot continue.")
            sys.exit()

    print("\n[✓] System is ready.\n")

# Run system check BEFORE anything else
run_system_check()

# =================================================================
# 1. BOOTSTRAP & ELEVATION (kept for safety)
# =================================================================
def bootstrap():
    if platform.system() == "Windows" and not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
bootstrap()

from scapy.all import sniff, IP, TCP, ARP, Ether, srp, Raw

# =================================================================
# 2. RECON ENGINE & WIKI DATABASE
# =================================================================
class ReconEngine:
    def __init__(self):
        self.targets = []
        self.is_scanning = False
        self.wiki = {
            21: ["FTP", "Common", "Cleartext file transfer using ports 20/21.", "Legacy file updates.", "Sniffing credentials; bounce attacks."],
            22: ["SSH", "Common", "Encrypted terminal access.", "Secure remote management.", "Brute-forcing root; tunneling."],
            23: ["Telnet", "Legacy", "Cleartext terminal protocol.", "Testing hardware ports.", "Sniffing passwords; botnets."],
            25: ["SMTP", "Common", "Email routing.", "Internal alerts.", "Mail spoofing; spam relays."],
            53: ["DNS", "Core", "Hostname resolution.", "AD health.", "DNS tunneling; cache poisoning."],
            80: ["HTTP", "Common", "Web traffic.", "Dashboards & APIs.", "XSS; session hijacking."],
            135: ["RPC", "Windows", "Endpoint mapper.", "Remote admin.", "RPC overflows."],
            161: ["SNMP", "Uncommon", "Monitoring protocol.", "Printer/router stats.", "Leaking community strings."],
            443: ["HTTPS", "Common", "TLS web traffic.", "Secure comms.", "C2 hiding in SSL."],
            445: ["SMB", "Windows", "Windows file sharing.", "File/printer sharing.", "EternalBlue; ransomware."],
            554: ["RTSP", "Uncommon", "Video streaming.", "IP cameras.", "Unauthorized feed access."],
            666: ["Doom", "Malware", "Old game port.", "Rarely used.", "Backdoor trojans."],
            1433: ["MSSQL", "Common", "SQL Server.", "Enterprise DB.", "SQL injection; SA takeover."],
            3128: ["Squid", "Uncommon", "Proxy cache.", "Bandwidth filtering.", "Firewall bypassing."],
            3306: ["MySQL", "Common", "Database engine.", "Web app storage.", "Brute-forcing DB creds."],
            3389: ["RDP", "Windows", "Remote Desktop.", "Server management.", "BlueKeep; MITM harvesting."],
            5900: ["VNC", "Common", "Screen sharing.", "Remote support.", "Auth bypass; spying."],
            5985: ["WinRM", "Windows", "PS Remoting.", "Automation.", "Remote code execution."],
            6667: ["IRC", "Legacy", "Chat protocol.", "Legacy chat.", "Botnet C2."],
            8080: ["HTTP-Alt", "Uncommon", "Dev servers.", "Testing apps.", "Hiding web shells."]
        }

    def get_subnet(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]
        except: ip = "192.168.1.0/24"
        finally: s.close()
        return ".".join(ip.split(".")[:-1]) + ".0/24"

    def scan(self, mode="active"):
        self.is_scanning = True
        new_targets = []
        if mode == "active":
            ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=self.get_subnet()), timeout=2, verbose=False)
            for s, r in ans:
                self.add_to_list(r.psrc, r.hwsrc, new_targets)
        self.targets = new_targets
        self.is_scanning = False

    def add_to_list(self, ip, mac, target_list):
        try: name = socket.gethostbyaddr(ip)[0]
        except: name = "Unknown"
        srvs = []
        for port in self.wiki.keys():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.01)
            if sock.connect_ex((ip, port)) == 0:
                srvs.append(self.wiki[port][0])
            sock.close()
        target_list.append({'ip': ip, 'name': name, 'mac': mac, 'services': srvs})

    def spawn_intelligence(self):
        wiki_str = str(self.wiki)
        code = f"""
import os
WIKI = {wiki_str}
def intel_loop():
    while True:
        os.system('cls')
        print("=== SENTINEL-X WIKI INTELLIGENCE ===")
        print(f"{{'ID':<4}} | {{'PORT':<6}} | {{'SERVICE':<15}} | {{'CATEGORY'}}")
        print("-" * 50)
        for i, port in enumerate(WIKI.keys()):
            print(f" [{{i:<2}}] | {{port:<6}} | {{WIKI[port][0]:<15}} | {{WIKI[port][1]}}")
        print("-" * 50)
        print(" [1] View Wiki Entry    [5] Back to Main")
        
        cmd = input("\\nINTEL > ")
        if cmd == '5': break
        if cmd == '1':
            idx = input("Enter ID number: ")
            try:
                p_key = list(WIKI.keys())[int(idx)]
                data = WIKI[p_key]
                os.system('cls')
                print(f"=== WIKI ENTRY: {{data[0]}} (Port {{p_key}}) ===")
                print(f"\\n[MECHANICS]:\\n{{data[2]}}")
                print(f"\\n[WHITE HAT USE]:\\n{{data[3]}}")
                print(f"\\n[BLACK HAT ABUSE]:\\n{{data[4]}}")
                input("\\n[5] BACK TO LIST")
            except: pass
intel_loop()
"""
        with open("wiki.py", "w") as f: f.write(code)
        subprocess.Popen(["start", "cmd", "/k", sys.executable, "wiki.py"], shell=True)

    def listen(self, ip):
        code = f"from scapy.all import sniff, IP, TCP, Raw; print('Sniffing {ip}...'); sniff(filter='host {ip}', prn=lambda x: print(x.summary()), store=0)"
        with open("monitor.py", "w") as f: f.write(code)
        subprocess.Popen(["start", "cmd", "/k", sys.executable, "monitor.py"], shell=True)

# =================================================================
# 3. MAIN TERMINAL
# =================================================================
def draw_main(engine):
    os.system('cls')
    print("===============================================================================")
    print(" SENTINEL-X COMMAND CENTER")
    print("===============================================================================")
    print(f"{'ID':<4} | {'IP ADDRESS':<15} | {'SERVICES':<20} | {'NAME'}")
    print("-" * 79)
    for i, t in enumerate(engine.targets):
        s = ", ".join(t['services']) if t['services'] else "-"
        print(f" [{i}] | {t['ip']:<15} | {s:<20} | {t['name']}")
    print("===============================================================================")

if __name__ == "__main__":
    engine = ReconEngine()
    while True:
        draw_main(engine)
        print(" [1] DISCOVERY    [2] LISTENER    [3] INTELLIGENCE    [5] EXIT")
        cmd = input("\nMAIN > ")
        if cmd == '1':
            engine.is_scanning = True
            threading.Thread(target=engine.scan).start()
            while engine.is_scanning:
                print(".", end="", flush=True)
                time.sleep(0.5)
        elif cmd == '2':
            idx = input("Target ID: ")
            engine.listen(engine.targets[int(idx)]['ip'])
        elif cmd == '3':
            engine.spawn_intelligence()
        elif cmd == '5':
            break
