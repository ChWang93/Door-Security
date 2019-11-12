import sys
from Functions import MotionSensor

Building = sys.argv[1]
Door = sys.argv[2]

ms = MotionSensor(Building,Door)
ms.Loop()
