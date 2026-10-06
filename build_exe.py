"""
Build script to compile GladiBot into a standalone Windows .exe using PyInstaller.
Run:
    python build_exe.py
"""

import os
import subprocess
import sys

def build():
    print("=" * 60)
    print("Building GladiBot V3 Standalone Executable (.exe)...")
    print("=" * 60)

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=GladiBotV3",
        "--onedir",
        "--windowed",
        "--clean",
        "--collect-all=playwright",
        "--collect-all=pynput",
        "Gladibot.py"
    ]

    print(f"Running command: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print("Executable located in: dist/GladiBotV3/GladiBotV3.exe")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print(f"BUILD FAILED with exit code {result.returncode}")
        print("=" * 60)

if __name__ == "__main__":
    build()
