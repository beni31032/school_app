from utils.security import hash_password

plain_password = "admin123"
hashed = hash_password(plain_password)

print("Mot de passe hashé :")
print(hashed)