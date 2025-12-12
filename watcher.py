import minescript
import os
import time

# Configuration
MAIN_SCRIPT_CMD = r"\FlameClient\main"
CONFIG_FILENAME = "config.py"

def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))

def get_config_path():
    return os.path.join(get_script_dir(), CONFIG_FILENAME)

def normalize_cmd(cmd):
    return cmd.replace("\\", "/").lower()

def kill_client_jobs():
    """Kills any running instances of the Flame Client scripts."""
    try:
        jobs = minescript.job_info()
        
        for job in jobs:
            if not job.command: continue
            cmd = normalize_cmd(job.command[0])
            
            # Kill main script and ESP script
            if "flameclient/main" in cmd or "flameclient/esp/main" in cmd:
                minescript.execute(f"\\killjob {job.job_id}")
    except Exception as e:
        minescript.echo(f"Error killing jobs: {e}")

def main():
    config_path = get_config_path()
    if not os.path.exists(config_path):
        minescript.echo(f"Error: Config file not found at {config_path}")
        return

    minescript.echo("§6[FlameClient] §aWatcher Started!")
    
    # Initial start
    kill_client_jobs()
    minescript.execute(MAIN_SCRIPT_CMD)
    
    last_mtime = os.path.getmtime(config_path)
    
    while True:
        time.sleep(1) # Check every second
        try:
            current_mtime = os.path.getmtime(config_path)
            if current_mtime > last_mtime:
                last_mtime = current_mtime
                minescript.echo("§6[FlameClient] Config change detected! Reloading...")
                
                kill_client_jobs()
                minescript.execute(MAIN_SCRIPT_CMD)
                
        except Exception as e:
            minescript.echo(f"§cWatcher Error: {e}")

if __name__ == "__main__":
    main()
