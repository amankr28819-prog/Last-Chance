import os
import sys
import socket
import argparse
import webbrowser
import subprocess
from typing import Optional, Tuple

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks whether a TCP port is currently in use or unavailable to bind."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return False
    except OSError:
        return True

def find_process_on_port(port: int) -> Optional[Tuple[int, str, str]]:
    """Identifies the PID and process command line using the given port on Windows."""
    try:
        if sys.platform == "win32":
            cmd = f'powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1"'
            output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
            if output and output.isdigit():
                pid = int(output)
                # Query process name / command line
                cmd_proc = f'powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \\"ProcessId = {pid}\\").CommandLine"'
                cmd_line = subprocess.check_output(cmd_proc, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
                cmd_name = f'powershell -NoProfile -Command "(Get-Process -Id {pid} -ErrorAction SilentlyContinue).ProcessName"'
                proc_name = subprocess.check_output(cmd_name, shell=True, text=True, stderr=subprocess.DEVNULL).strip() or "Unknown"
                return pid, proc_name, cmd_line
    except Exception:
        pass
    return None

def find_next_available_port(start_port: int = 8000, max_attempts: int = 20) -> int:
    """Finds the next available local port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        if not is_port_in_use(p):
            return p
    raise RuntimeError(f"Could not find an available port between {start_port} and {start_port + max_attempts}")

def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    default_port = int(os.environ.get("LASTCHANCE_PORT", os.environ.get("STUDYPILOT_PORT", 8000)))
    default_host = os.environ.get("LASTCHANCE_HOST", os.environ.get("STUDYPILOT_HOST", "127.0.0.1"))

    parser = argparse.ArgumentParser(description="Last Chance — Personal Study Management Application")
    parser.add_argument("--port", type=int, default=default_port, help="Port to run the server on (default: 8000)")
    parser.add_argument("--host", type=str, default=default_host, help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the default web browser")
    parser.add_argument("--auto-port", action="store_true", default=True, help="Automatically use the next available port if port is occupied")
    args = parser.parse_args()

    port = args.port
    host = args.host

    print("=" * 68)
    print("      Last Chance — Personal Study Management Application")
    print("      4h Academic Study • 2 Daily DSA • 30m English Practice")
    print("=" * 68)

    # Pre-check port availability
    if is_port_in_use(port, host):
        proc_info = find_process_on_port(port)
        if proc_info:
            pid, name, cmdline = proc_info
            is_our_app = "main.py" in cmdline or "Last Chance" in cmdline or "Last-Chance" in cmdline
            
            print(f"\n[NOTICE] Port {port} is already in use by process '{name}' (PID: {pid}).")
            if is_our_app:
                print(f"         Another Last Chance instance appears to be running!")
                print(f"         Active URL: http://{host}:{port}")
                print(f"\nOptions:")
                print(f"  1. Open the existing instance in your browser: http://{host}:{port}")
                print(f"  2. To stop the existing instance: Stop-Process -Id {pid} (in PowerShell)")
            else:
                print(f"         Command: {cmdline}")
                print(f"\nOptions:")
                print(f"  1. Stop process {pid} if you no longer need it.")
                print(f"  2. Run Last Chance on another port with: python main.py --port <port>")

        if args.auto_port:
            next_port = find_next_available_port(port + 1)
            print(f"\n--> Automatically switching to available port: {next_port}")
            port = next_port
        else:
            print(f"\n[ERROR] Cannot bind to port {port}. Use --auto-port or choose another port with --port <number>.")
            sys.exit(1)

    url = f"http://{host}:{port}"
    print(f"\n[OK] Starting Last Chance server at: {url}")
    print(f"     Press Ctrl+C in this console window to stop the application.\n")

    # Launch browser after a short delay
    if not args.no_browser:
        import threading
        import time
        def open_browser():
            time.sleep(1.2)
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    # Import FastAPI app
    try:
        uvicorn.run("backend.app:app", host=host, port=port, reload=False, log_level="info")
    except Exception as e:
        print(f"\n[ERROR] Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
