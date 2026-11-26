    import json

with open("data/users.json", encoding="utf-8") as f:
    data = json.load(f)

for user in data:
    if user.get("username") == "nguyen_van_a":
        total_balance = sum([w.get("currentBalance", 0) for w in user.get("wallets", [])])
        print(f"Total wallet balance: {total_balance}")
        print("Wallets:")
        for w in user.get("wallets", []):
            print(f"  {w['name']}: {w.get('currentBalance', 0)}")
