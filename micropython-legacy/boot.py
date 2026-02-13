# This file is executed on every boot (including wake-boot from deepsleep)
import uos
import machine
import gc

def apply_update():
    try:
        if "update.flag" in uos.listdir():
            if "main_new.py" in uos.listdir():
                if "main.py" in uos.listdir():
                    uos.remove("main.py")
                uos.rename("main_new.py", "main.py")
                print("Update applied successfully.")
                # update.flag NICHT löschen – wird in main.py ausgewertet
    except Exception as e:
        print("Error during update apply:", e)

apply_update()

gc.collect()
