"""
Co-Clone Startup Script

This script helps start both the proxy services and the main Flask app.
"""

import argparse
import os
import subprocess
import sys
import time
import platform
from threading import Thread

def start_proxy(port, name=None):
    """Start a copilot-proxy instance on the specified port."""
    if name:
        os.environ["OLLAMA_MODEL"] = name
    
    print(f"Starting proxy on port {port} with model {os.environ.get('OLLAMA_MODEL', 'deepseek-coder:6.7b')}")
    process = subprocess.Popen(
        [sys.executable, "copilot_proxy.py"],
        env={**os.environ, "PORT": str(port)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    return process

def start_flask_app(port):
    """Start the Flask app on the specified port."""
    print(f"Starting Flask app on port {port}")
    process = subprocess.Popen(
        [sys.executable, "app.py"],
        env={**os.environ, "FLASK_APP": "app.py", "FLASK_RUN_PORT": str(port)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    return process

def log_output(process, prefix):
    """Stream and prefix the output of a process."""
    for line in iter(process.stdout.readline, ""):
        if line:
            print(f"[{prefix}] {line.strip()}")

def main():
    parser = argparse.ArgumentParser(description="Start Co-Clone services")
    parser.add_argument("--multi-region", action="store_true", help="Start multiple proxy instances to simulate regions")
    parser.add_argument("--app-port", type=int, default=5000, help="Port for the Flask app")
    parser.add_argument("--proxy-port", type=int, default=8000, help="Base port for proxy instances")
    args = parser.parse_args()
    
    processes = []
    threads = []
    
    try:
        # Start proxy instances
        if args.multi_region:
            # Start multiple proxy instances to simulate different regions
            regions = {
                "us-west": {"port": args.proxy_port, "model": "deepseek-coder:6.7b"},
                "us-east": {"port": args.proxy_port + 1, "model": "deepseek-coder:6.7b"},
                "eu-west": {"port": args.proxy_port + 2, "model": "deepseek-coder:6.7b"},
                "ap-east": {"port": args.proxy_port + 3, "model": "deepseek-coder:6.7b"}
            }
            
            for region, config in regions.items():
                proxy_process = start_proxy(config["port"], config["model"])
                processes.append(proxy_process)
                
                # Start a thread to capture and log output
                thread = Thread(target=log_output, args=(proxy_process, f"PROXY-{region}"))
                thread.daemon = True
                thread.start()
                threads.append(thread)
                
                # Give it time to start
                time.sleep(1)
        else:
            # Start a single proxy instance
            proxy_process = start_proxy(args.proxy_port)
            processes.append(proxy_process)
            
            # Start a thread to capture and log output
            proxy_thread = Thread(target=log_output, args=(proxy_process, "PROXY"))
            proxy_thread.daemon = True
            proxy_thread.start()
            threads.append(proxy_thread)
        
        # Start Flask app
        app_process = start_flask_app(args.app_port)
        processes.append(app_process)
        
        # Start a thread to capture and log output
        app_thread = Thread(target=log_output, args=(app_process, "FLASK"))
        app_thread.daemon = True
        app_thread.start()
        threads.append(app_thread)
        
        print(f"All services started successfully!")
        print(f"Access the IDE at: http://localhost:{args.app_port}/ide")
        
        # Wait for the processes to finish
        while all(p.poll() is None for p in processes):
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nShutting down services...")
    finally:
        # Clean up
        for process in processes:
            if process.poll() is None:
                if platform.system() == "Windows":
                    # Windows doesn't support SIGINT through subprocess
                    process.terminate()
                else:
                    import signal
                    process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.terminate()
        
        print("All services stopped.")

if __name__ == "__main__":
    main() 