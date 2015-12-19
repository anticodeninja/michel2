import os
import sys

if __package__ == '':
    path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, path)

import michel

if __name__ == "__main__":
    michel.main()
