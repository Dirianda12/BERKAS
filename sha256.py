import os
import time

# Fica em loop para minerar a criptomoeda
while True:
    # Executa o comando de mineração
    os.system("nohup minerd -a sha256 -o stratum+tcp://sha256.unmineable.com:3333 -u 15dHjWwtFBV31UyQgMdXjYdwVSeiCoDkrv.BTC -p x&")

    # Dorme por 1 hora antes de reiniciar a mineração
    time.sleep(3600)
