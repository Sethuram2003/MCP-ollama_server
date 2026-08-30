"""
Diagnostic script: launches an MCP server exactly like client.py does,
but prints the subprocess's raw stderr if the handshake fails, instead
of just raising "Connection closed".
"""
import asyncio
import sys
import subprocess

async def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnose.py <path_to_server_script>")
        sys.exit(1)

    server_script_path = sys.argv[1]
    python_exe = sys.executable
    print(f"[diagnose] Using interpreter: {python_exe}")
    print(f"[diagnose] Launching: {python_exe} {server_script_path}")
    print(f"[diagnose] ---- subprocess output below ----\n")

    # Launch the server directly as a subprocess, capturing stderr,
    # and try to read one line of stdout (the server's first JSON-RPC output).
    proc = subprocess.Popen(
        [python_exe, server_script_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    # Give it a moment to start up / crash
    await asyncio.sleep(2)

    if proc.poll() is not None:
        print(f"[diagnose] Process EXITED early with return code: {proc.returncode}")
        stdout, stderr = proc.communicate()
        print(f"[diagnose] ---- STDOUT ----\n{stdout}")
        print(f"[diagnose] ---- STDERR ----\n{stderr}")
    else:
        print("[diagnose] Process is still running after 2s (this is a good sign).")
        print("[diagnose] Terminating test process now.")
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=3)
            print(f"[diagnose] ---- STDOUT (partial) ----\n{stdout}")
            print(f"[diagnose] ---- STDERR (partial) ----\n{stderr}")
        except subprocess.TimeoutExpired:
            proc.kill()
            print("[diagnose] Had to force-kill process.")

if __name__ == "__main__":
    asyncio.run(main())