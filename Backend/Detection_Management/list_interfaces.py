# list_interfaces.py
# Run this to see available network interfaces for tshark
import subprocess
import sys

def list_interfaces():
    try:
        result = subprocess.run(
            ["tshark", "-D"],
            capture_output=True,
            text=True,
            timeout=10
        )
        print("Available network interfaces:")
        print("-" * 50)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
    except FileNotFoundError:
        print("❌ tshark not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_interfaces()
