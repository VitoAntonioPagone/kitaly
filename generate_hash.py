from werkzeug.security import generate_password_hash
import sys

def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = input("Enter the password to hash: ")
    
    hashed = generate_password_hash(password)
    print("\n--- SECURE HASH GENERATED ---")
    print(hashed)
    print("-----------------------------\n")
    print("Copy the hash above and paste it into your .env file as:")
    print(f"ADMIN_PASSWORD_HASH={hashed}")

if __name__ == "__main__":
    main()
