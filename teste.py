import os

# print(os.urandom(10).hex())

from werkzeug.security import generate_password_hash, check_password_hash #hash de senha


senha_gerada = generate_password_hash("123456")

print(senha_gerada)

checagem = check_password_hash(senha_gerada, "123456")

print(checagem)