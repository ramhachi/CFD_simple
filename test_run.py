import subprocess
import pty

master, slave = pty.openpty()
inputs = b"20\ny\ny\n1\n50\n0\n0\n0\n10\n0\n0\n0\n20\n0\n"

process = subprocess.Popen(['python3', 'run_cfd.py', '--no-docker'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate(input=inputs)

print("--- STDOUT ---")
print(stdout.decode())
print("--- STDERR ---")
print(stderr.decode())

print("\n--- setup_stl.sh content ---")
with open('setup_stl.sh', 'r') as f:
    print(f.read())

print("\n--- cfd_params.txt content ---")
with open('cfd_params.txt', 'r') as f:
    print(f.read())
