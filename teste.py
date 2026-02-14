import os

# print(os.urandom(10).hex())

from werkzeug.security import generate_password_hash, check_password_hash #hash de senha


senha_gerada = generate_password_hash("123456")

print(senha_gerada)

# checagem = check_password_hash("scrypt:32768:8:1$PbmSHrT2snux13VK$c951207f2af0c1d1d315f0a48f72dc86463d4fe1100d2e80a9c4e9c1563c2f43ece4188c563fa77482c641dc3d712d9614c923fdb593eb6c7179179416e545a8", "teste123")

# print(checagem)