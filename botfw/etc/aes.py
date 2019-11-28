import json
import sys
import getpass

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random


def create_aes(password, iv):
    sha = SHA256.new()
    sha.update(password.encode())
    key = sha.digest()
    return AES.new(key, AES.MODE_CFB, iv)


def encrypt(data, password):
    iv = Random.new().read(AES.block_size)
    return iv + create_aes(password, iv).encrypt(data)


def decrypt(data, password):
    iv, cipher = data[:AES.block_size], data[AES.block_size:]
    return create_aes(password, iv).decrypt(cipher)


def cmd_encrypt():
    password = getpass.getpass('password> ')
    password2 = getpass.getpass('confirm> ')
    if password != password2:
        print('Password confirmation failed.')
        sys.exit(0)
    enc = encrypt(sys.stdin.buffer.read(), password)
    sys.stdout.buffer.write(enc)


def cmd_decrypt():
    password = getpass.getpass('password> ')
    dec = decrypt(sys.stdin.buffer.read(), password)
    sys.stdout.buffer.write(dec)


def load_encrypted_json_file(file_path):
    password = getpass.getpass('password> ')
    dec = decrypt(open(file_path, 'rb').read(), password)
    try:
        return json.loads(dec.decode())
    except Exception:
        raise Exception('Wrong password')
