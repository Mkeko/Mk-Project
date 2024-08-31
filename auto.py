import subprocess

import threading

import time

import os

BLUE = "\033[94m"

RESET = "\033[0m"

def start_process(script_name):

    """Start a process and return the Popen object."""

    return subprocess.Popen(["python3", script_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def monitor_main():

    """Monitor and restart the main process if it crashes."""

    while True:

        process = start_process("main.py")

        stdout, stderr = process.communicate()

        if process.returncode != 0:

            print(f"{BLUE}ERROR:{RESET} main.py crashed with exit code {process.returncode}. Restarting...")

            print(f"{BLUE}STDOUT:{RESET} {stdout.decode()}")

            print(f"{BLUE}STDERR:{RESET} {stderr.decode()}")

def run_backup():

    """Run the backup process every 30 minutes."""

    while True:

        process = start_process("auto_backup.py")

        stdout, stderr = process.communicate()  

        print(f"{BLUE}INFO:{RESET} auto_backup.py finished.")

        print(f"{BLUE}STDOUT:{RESET} {stdout.decode()}")

        print(f"{BLUE}STDERR:{RESET} {stderr.decode()}")

        print(f"{BLUE}INFO:{RESET} Next run in 30 minutes.")

        time.sleep(1800)  # Sleep for 30 minutes

if __name__ == "__main__":

    main_thread = threading.Thread(target=monitor_main)

    backup_thread = threading.Thread(target=run_backup)

    

    main_thread.start()

    backup_thread.start()

    try:

        main_thread.join()

        backup_thread.join()

    except KeyboardInterrupt:

        print(f"{BLUE}INFO:{RESET} Processes terminated.")

        os._exit(0)  # Ensure the program exits completely


