'''Enable ``python -m ccbalancer`` to invoke the CLI.'''

import sys

from ccbalancer.cli import main

if __name__ == '__main__':
    sys.exit(main())
