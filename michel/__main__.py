# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

if __package__ == '':
    path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, path)

import michel

if __name__ == "__main__":
    michel.main()
