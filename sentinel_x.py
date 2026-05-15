import subprocess, sys, os, platform, ctypes, threading, socket, time

# =================================================================
# 1. BOOTSTRAP & ELEVATION
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
        # Wiki Database: {Port: [Name, Category, Mechanics, White Hat, Black Hat]}
        self.wiki = {
            21: ["FTP", "Common", "Cleartext file transfer using ports 20 (data) and 21 (control).", "Legacy file updates in isolated labs.", "Sniffing credentials; 'Bounce attacks' to bypass firewalls."],
            22: ["SSH", "Common", "Encrypted terminal access replacing Telnet.", "Secure remote management of servers.", "Brute-forcing 'root' passwords; SSH tunneling to hide exfiltration."],
            23: ["Telnet", "Legacy", "Ancient cleartext terminal protocol.", "Testing connectivity to basic hardware ports.", "Extremely easy to sniff passwords; used by Mirai botnets."],
            25: ["SMTP", "Common", "Simple Mail Transfer Protocol for email routing.", "Internal server alerts and notification systems.", "Mail spoofing; open relays used for global spam campaigns."],
            53: ["DNS", "Core", "Translates hostnames to IP addresses via UDP/TCP.", "Essential network resolution and Active Directory health.", "DNS Tunneling (hiding data in queries); Cache poisoning."],
            80: ["HTTP", "Common", "Foundation of the unencrypted World Wide Web.", "Internal web dashboards and API testing.", "Cross-Site Scripting (XSS); Session Hijacking."],
            135: ["RPC", "Windows", "Microsoft's endpoint mapper for remote procedures.", "DCOM communication and remote Windows administration.", "Enumerating system info; entry point for RPC buffer overflows."],
            161: ["SNMP", "Uncommon", "Simple Network Management Protocol for monitoring.", "Checking printer toner or router CPU stats remotely.", "Leaking community strings to map the entire network topology."],
            443: ["HTTPS", "Common", "TLS-encrypted web traffic.", "Standard secure communication for all modern apps.", "Hiding Command & Control (C2) traffic inside valid SSL certs."],
            445: ["SMB", "Windows", "The 'backbone' of Windows networking and file shares.", "Direct file access and printer sharing across the domain.", "The primary vector for Ransomware (WannaCry) via EternalBlue."],
            554: ["RTSP", "Uncommon", "Real-Time Streaming Protocol for video feeds.", "Monitoring IP security cameras in the lab.", "Unauthorized 'voyeur' access to private security feeds."],
            666: ["Doom", "Malware", "Old game port, now often used by trojans/backdoors.", "Rarely used in modern labs; suspicious if found.", "Classic 'Satan' backdoor port; signifies a compromised host."],
            1433: ["MSSQL", "Common", "Microsoft SQL Server database engine.", "Backend data storage for enterprise applications.", "SQL Injection; database dumping; gaining 'sa' account control."],
            3128: ["Squid", "Uncommon", "Standard port for web proxy caches.", "Filtering web traffic to save bandwidth in large labs.", "Bypassing firewalls by tunneling traffic through the proxy."],
            3306: ["MySQL", "Common", "Open-source database engine.", "Web application data storage (WordPress, etc).", "Brute-forcing database passwords to steal user PII."],
            3389: ["RDP", "Windows", "Remote Desktop Protocol (GUI access).", "Managing Windows Server 2022 without a monitor.", "BlueKeep exploit; credential harvesting via Man-in-the-Middle."],
            5900: ["VNC", "Common", "Virtual Network Computing for screen sharing.", "Cross-platform remote support (Mac/Linux/Windows).", "VNC Auth Bypass; observing user screens without consent."],
            5985: ["WinRM", "Windows", "Windows Remote Management (PowerShell Remoting).", "Running automated PowerShell scripts across the lab.", "Remote code execution if listeners are poorly secured."],
            6667: ["IRC", "Legacy", "Internet Relay Chat protocol.", "Legacy team chat servers.", "Historically the #1 port for Botnet Command & Control."],
            8080: ["HTTP-Alt", "Uncommon", "Standard port for dev servers and web proxies.", "Testing web apps before they go live on port 80.", "Hiding web shells in non-standard locations to avoid detection."]
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
            for s, r in ans: self.add_to_list(r.psrc, r.hwsrc, new_targets)
        self.targets = new_targets
        self.is_scanning = False

    def add_to_list(self, ip, mac, target_list):
        try: name = socket.gethostbyaddr(ip)[0]
        except: name = "Unknown"
        srvs = []
        for port in self.wiki.keys():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.01)
            if sock.connect_ex((ip, port)) == 0: srvs.append(self.wiki[port][0])
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
            while engine.is_scanning: print(".", end="", flush=True); time.sleep(0.5)
        elif cmd == '2':
            idx = input("Target ID: ")
            engine.listen(engine.targets[int(idx)]['ip'])
        elif cmd == '3':
            engine.spawn_intelligence()
        elif cmd == '5': break
