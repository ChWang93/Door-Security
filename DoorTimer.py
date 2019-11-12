import sys
import time
from Functions import Timer


t = Timer(sys.argv[1])

while True:
    try:
        t.CheckLock()
        print("Iteration")
        time.sleep(60)
    except KeyboardInterrupt:
        break
