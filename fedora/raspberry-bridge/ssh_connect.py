#!/usr/bin/env python3
import pexpect, sys

host = sys.argv[1]
user = sys.argv[2]
password = sys.argv[3]
command = sys.argv[4] if len(sys.argv) > 4 else "echo connected"

child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {user}@{host} "{command}"', timeout=15)
idx = child.expect([pexpect.TIMEOUT, 'password:', pexpect.EOF])
if idx == 1:
    child.sendline(password)
    child.expect(pexpect.EOF, timeout=15)
print(child.before.decode() if hasattr(child, 'before') and child.before else "")
