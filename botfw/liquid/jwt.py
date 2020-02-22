# https://github.com/QuoineFinancial/liquid-tap-python/blob/b8c1187fa846bc472dcb790e0c486d94d0b28e81/liquidtap/utils.py
import hmac
import hashlib
import json
import base64
import re
import time


def base64url(utfbytes):
    s = base64.b64encode(utfbytes).decode('utf-8')
    s = re.sub(r'=+$', "",  s)
    s = re.sub(r'\+', '-', s)
    s = re.sub(r'\/', '_', s)
    return s


def stringify64(data):
    return base64url(json.dumps(data, separators=(',', ':')).encode('utf-8'))


def create_sha256_signature(message, secret):
    secret = secret.encode('utf-8')  # convert to byte array
    message = message.encode('utf-8')
    return hmac.new(secret, message, hashlib.sha256).digest()


def create_jwt(tokenId, tokenSecret):
    return encode_jwt({
        'path': '/realtime',
        'token_id': str(tokenId),
        'nonce': round(time.time() * 1000)
    }, tokenSecret)


def encode_jwt(data, secret):
    header = {
        'typ': 'JWT',
        'alg': 'HS256'
    }

    encodedHeader = stringify64(header)
    encodedData = stringify64(data)

    token = encodedHeader + '.' + encodedData

    signature = create_sha256_signature(token, secret)
    signedToken = token + '.' + base64url(signature)

    return signedToken
