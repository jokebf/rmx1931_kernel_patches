#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python 3 compatible version of gcc-wrapper.py

import subprocess
import sys
import re

def run_gcc():
    args = sys.argv[1:]
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode == 0:
            sys.stdout.write(out.decode('utf-8', errors='replace'))
            sys.stdout.flush()
        else:
            for line in err.decode('utf-8', errors='replace').split('\n'):
                m = re.search(r'(.*error:.*)', line)
                if m:
                    print("error, forbidden warning:", m.group(1), file=sys.stderr)
                else:
                    print(line, file=sys.stderr)
        sys.exit(p.returncode)
    except OSError as e:
        print(args[0] + ':', e.strerror, file=sys.stderr)
        print('Is your PATH set correctly?', file=sys.stderr)
        print(' '.join(args), str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    run_gcc()
