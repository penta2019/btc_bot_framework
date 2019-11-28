cd $(dirname $(dirname $(readlink -fm "$0")))
python3 -c 'import botfw.etc.aes as aes; aes.cmd_decrypt()'