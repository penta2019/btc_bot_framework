#!/usr/bin/env python3
import sys
import getpass
from cryptography.fernet import Fernet

key = getpass.getpass('key> ')
enc = Fernet(key).encrypt(sys.stdin.buffer.read())
sys.stdout.buffer.write(enc)
