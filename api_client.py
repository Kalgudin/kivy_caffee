# api_client.py
import requests

# Для эмулятора Android: 10.0.2.2 — это хост-машина.
# Для реального телефона укажите IP вашего ПК в локальной сети, например 192.168.1.100.
# BASE_URL = "http://127.0.0.1:8000"
BASE_URL = "https://cafe-api-wmag.onrender.com"

class ApiClient:
    def __init__(self, base_url=BASE_URL):
        self.base = base_url
        self.session = requests.Session()

    # Универсальный запрос с логированием
    def _req(self, method, path, **kw):
        url = f"{self.base}{path}"
        try:
            r = self.session.request(method, url, timeout=10, **kw)
            print(f"[API] {method} {path} -> {r.status_code}")
            r.raise_for_status()
            # некоторые эндпоинты возвращают пустой ответ
            if r.text:
                try:
                    return r.json()
                except ValueError:
                    return {}
            return {}
        except requests.HTTPError as e:
            print(f"[API] HTTP ERROR {e.response.status_code}: {e.response.text}")
            return {"error": str(e), "status": e.response.status_code}
        except requests.RequestException as e:
            print(f"[API] CONNECTION ERROR: {e}")
            return {"error": str(e)}

    # ---------- ROOT ----------
    def root(self):
        return self._req("GET", "/")

    # ---------- USERS ----------
    def get_users(self):
        return self._req("GET", "/users")

    def create_user(self, name, phone, password):
        return self._req("POST", "/users",
                         json={"name": name, "phone": phone, "password": password})

    def get_user(self, user_id):
        return self._req("GET", f"/users/{user_id}")

    def delete_user(self, user_id):
        return self._req("DELETE", f"/users/{user_id}")

    def login(self, phone, password):
        r = self._req("POST", "/login", json={"phone": phone, "password": password})
        return r if isinstance(r, dict) and "id" in r else None

    # ---------- MENU ----------
    def get_menu(self):
        return self._req("GET", "/menu")

    def create_menu_item(self, name, price, category,
                         description="", is_available=True):
        return self._req("POST", "/menu", json={
            "name": name, "price": price, "category": category,
            "description": description, "is_available": is_available,
        })

    def get_menu_item(self, item_id):
        return self._req("GET", f"/menu/{item_id}")

    def delete_menu_item(self, item_id):
        return self._req("DELETE", f"/menu/{item_id}")

    # ---------- ORDERS ----------
    def get_orders(self):
        return self._req("GET", "/orders")

    def create_order(self, user_id, items, delivery_method="pickup"):
        return self._req("POST", "/orders", json={
            "user_id": user_id, "delivery_method": delivery_method, "items": items,
        })

    def get_order(self, order_id):
        return self._req("GET", f"/orders/{order_id}")

    def delete_order(self, order_id):
        return self._req("DELETE", f"/orders/{order_id}")

    def update_status(self, order_id, status):
        return self._req("PATCH", f"/orders/{order_id}/status",
                         params={"status": status})

    # ---------- FAVORITES ----------
    def add_favorite(self, user_id, menu_item_id):
        return self._req("POST", "/favorites",
                         json={"user_id": user_id, "menu_item_id": menu_item_id})

    def get_favorites(self, user_id):
        return self._req("GET", f"/favorites/{user_id}")

    def delete_favorite(self, fav_id):
        return self._req("DELETE", f"/favorites/{fav_id}")

    # ---------- PROMOTIONS ----------
    def create_promotion(self, user_id, description, discount,
                         start_date, end_date):
        return self._req("POST", "/promotions", json={
            "user_id": user_id, "description": description, "discount": discount,
            "start_date": start_date, "end_date": end_date,
        })

    def get_promotions(self, user_id):
        return self._req("GET", f"/promotions/{user_id}")

    def delete_promotion(self, promo_id):
        return self._req("DELETE", f"/promotions/{promo_id}")

    # ---------- LOYALTY ----------
    def create_loyalty(self, user_id, points, operation_type, order_id=None):
        payload = {"user_id": user_id, "points": points,
                   "operation_type": operation_type}
        if order_id is not None:
            payload["order_id"] = order_id
        return self._req("POST", "/loyalty", json=payload)

    def get_loyalty(self, user_id):
        return self._req("GET", f"/loyalty/{user_id}")