import time
import subprocess
import sys
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ChangeHandler(FileSystemEventHandler):

    def __init__(self, script_name):
        self.script_name = script_name
        self.process = None
        self.start_process()

    def start_process(self):

       
        if self.process:
            print("[HOT-RELOAD] Parando o servidor antigo...")
            self.process.terminate()
            self.process.wait() 

        print(f"[HOT-RELOAD] Iniciando '{self.script_name}'...")
       
        self.process = subprocess.Popen([sys.executable, self.script_name])

    def on_modified(self, event):

       
        if event.src_path.endswith(self.script_name):
            os.system('cls')
            print(f"[HOT-RELOAD] Alteração detectada em '{self.script_name}'. Reiniciando o servidor...")
            self.start_process()


if __name__ == "__main__":
    script_to_watch = "server.py" 
    path = "."  

   
    event_handler = ChangeHandler(script_to_watch)
    
    
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False) 
    observer.start()
    
    print(f"[HOT-RELOAD] Vigilante iniciado. Monitorando '{script_to_watch}' por alterações.")
    print("Pressione Ctrl+C para parar.")

    try:
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        
        print("[HOT-RELOAD] Parando o vigilante e o servidor...")
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
            event_handler.process.wait()
    
    observer.join()
    print("[HOT-RELOAD] Desligado.")
