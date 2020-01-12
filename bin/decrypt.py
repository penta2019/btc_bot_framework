#!/usr/bin/env python3
import sys
import getpass
from cryptography.fernet import Fernet

key = getpass.getpass('key> ')
dec = Fernet(key).decrypt(sys.stdin.buffer.read())
sys.stdout.buffer.write(dec)
