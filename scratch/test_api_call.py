import requests
import json

def test():
    try:
        r = requests.get("http://localhost:5000/api/kanban/cards")
        print(f"Status: {r.status_code}")
        cards = r.json()
        print(f"Number of cards: {len(cards)}")
        for card in cards:
            hist = card.get("historico", [])
            if hist:
                print(f"Card {card['titulo']} has {len(hist)} history items.")
                print(f"First item: {json.dumps(hist[0], indent=2)}")
                break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
