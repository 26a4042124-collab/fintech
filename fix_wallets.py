import json

with open("data/users.json", encoding="utf-8") as f:
    data = json.load(f)

for user in data:
    if user.get("username") == "nguyen_van_a":
        for wallet in user.get("wallets", []):
            # Reset currentBalance về initialBalance
            wallet["currentBalance"] = wallet.get("initialBalance", 0)
        print(f"Đã reset số dư ví cho {user['username']}")
        
with open("data/users.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Hoàn tất!")
