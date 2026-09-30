import requests
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup

# ====================== НАСТРОЙКИ ======================
# IP компьютера, где запущен FastAPI. НЕ localhost!
# Узнать IP: ipconfig в PowerShell, строка "IPv4-адрес"
API = "http://localhost:8000"

# ====================== СОСТОЯНИЕ ======================
current_user = {}
cart = []


def show_message(title, text):
    Popup(title=title, content=Label(text=text), size_hint=(0.8, 0.3)).open()


# ====================== ЭКРАН ВХОДА ======================
class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = BoxLayout(orientation="vertical", padding=20, spacing=10)
        box.add_widget(Label(text="Кафе", font_size=32))

        self.phone = TextInput(hint_text="Телефон", multiline=False)
        self.password = TextInput(hint_text="Пароль", password=True, multiline=False)
        self.name_input = TextInput(hint_text="Имя (для регистрации)", multiline=False)  # ← переименовали

        box.add_widget(self.phone)
        box.add_widget(self.password)
        box.add_widget(self.name_input)

        box.add_widget(Button(text="Войти", on_press=self.do_login))
        box.add_widget(Button(text="Зарегистрироваться", on_press=self.do_register))

        self.add_widget(box)

    def do_login(self, *args):
        try:
            r = requests.post(API + "/login",
                              json={"phone": self.phone.text, "password": self.password.text},
                              timeout=5)
        except Exception as e:
            show_message("Ошибка сети", str(e))
            return
        if r.status_code != 200:
            show_message("Ошибка", r.json().get("detail", "Не удалось войти"))
            return
        current_user.clear()
        current_user.update(r.json())
        self.manager.current = "menu"

    def do_register(self, *args):
        try:
            r = requests.post(API + "/users",
                              json={"name": self.name_input.text,   # ← тут тоже
                                    "phone": self.phone.text,
                                    "password": self.password.text},
                              timeout=5)
        except Exception as e:
            show_message("Ошибка сети", str(e))
            return
        if r.status_code != 200:
            show_message("Ошибка", r.json().get("detail", "Ошибка регистрации"))
            return
        show_message("Готово", "Теперь можно войти")


# ====================== ЭКРАН МЕНЮ ======================
class MenuScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = BoxLayout(orientation="vertical")

        top = BoxLayout(size_hint_y=None, height=50, spacing=5)
        top.add_widget(Button(text="Корзина", on_press=lambda *a: setattr(self.manager, "current", "cart")))
        top.add_widget(Button(text="Заказы", on_press=lambda *a: setattr(self.manager, "current", "orders")))
        top.add_widget(Button(text="Профиль", on_press=lambda *a: setattr(self.manager, "current", "profile")))
        top.add_widget(Button(text="Обновить", on_press=self.load_menu))
        box.add_widget(top)

        self.scroll = ScrollView()
        self.list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        box.add_widget(self.scroll)
        self.add_widget(box)

    def on_enter(self):
        self.load_menu()

    def load_menu(self, *args):
        self.list_box.clear_widgets()
        try:
            r = requests.get(API + "/menu", timeout=5)
        except Exception as e:
            show_message("Ошибка сети", str(e))
            return
        for item in r.json():
            if not item["is_available"]:
                continue
            row = BoxLayout(size_hint_y=None, height=60, spacing=5)
            row.add_widget(Label(text=f"{item['name']} — {item['price']}₽", size_hint_x=0.7))
            btn = Button(text="+", size_hint_x=0.3)
            btn.bind(on_press=lambda b, i=item: self.add_to_cart(i))
            row.add_widget(btn)
            self.list_box.add_widget(row)

    def add_to_cart(self, item):
        for c in cart:
            if c["id"] == item["id"]:
                c["quantity"] += 1
                show_message("Корзина", f"{item['name']} x{c['quantity']}")
                return
        cart.append({"id": item["id"], "name": item["name"],
                     "price": float(item["price"]), "quantity": 1})
        show_message("Добавлено", item["name"])


# ====================== ЭКРАН КОРЗИНЫ ======================
class CartScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = BoxLayout(orientation="vertical")

        top = BoxLayout(size_hint_y=None, height=50, spacing=5)
        top.add_widget(Button(text="Назад", on_press=lambda *a: setattr(self.manager, "current", "menu")))
        top.add_widget(Button(text="Оформить", on_press=self.create_order))
        top.add_widget(Button(text="Очистить", on_press=self.clear_cart))
        box.add_widget(top)

        self.scroll = ScrollView()
        self.list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        box.add_widget(self.scroll)

        self.total_label = Label(text="Итого: 0₽", size_hint_y=None, height=40)
        box.add_widget(self.total_label)
        self.add_widget(box)

    def on_enter(self):
        self.refresh()

    def refresh(self):
        self.list_box.clear_widgets()
        total = 0
        for c in cart:
            total += c["price"] * c["quantity"]
            row = BoxLayout(size_hint_y=None, height=50, spacing=5)
            row.add_widget(Label(text=f"{c['name']} x{c['quantity']} = {c['price'] * c['quantity']}₽"))
            btn = Button(text="-", size_hint_x=0.3)
            btn.bind(on_press=lambda b, i=c: self.remove_one(i))
            row.add_widget(btn)
            self.list_box.add_widget(row)
        self.total_label.text = f"Итого: {total}₽"

    def remove_one(self, item):
        item["quantity"] -= 1
        if item["quantity"] <= 0:
            cart.remove(item)
        self.refresh()

    def clear_cart(self, *args):
        cart.clear()
        self.refresh()

    def create_order(self, *args):
        if not cart:
            show_message("Пусто", "Добавь что-нибудь в корзину")
            return

        items = [{"menu_item_id": c["id"], "quantity": c["quantity"], "drink_options": ""}
                 for c in cart]
        try:
            r = requests.post(API + "/orders",
                              json={"user_id": current_user["id"],
                                    "delivery_method": "pickup",
                                    "items": items},
                              timeout=5)
        except Exception as e:
            show_message("Ошибка сети", str(e))
            return
        if r.status_code != 200:
            show_message("Ошибка", r.text)
            return
        cart.clear()
        show_message("Готово", "Заказ оформлен!")
        self.manager.current = "orders"


# ====================== ЭКРАН ЗАКАЗОВ ======================
class OrdersScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = BoxLayout(orientation="vertical")

        top = BoxLayout(size_hint_y=None, height=50, spacing=5)
        top.add_widget(Button(text="В меню", on_press=lambda *a: setattr(self.manager, "current", "menu")))
        top.add_widget(Button(text="Обновить", on_press=self.load_orders))
        box.add_widget(top)

        self.scroll = ScrollView()
        self.list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        box.add_widget(self.scroll)
        self.add_widget(box)

    def on_enter(self):
        self.load_orders()

    def load_orders(self, *args):
        self.list_box.clear_widgets()
        try:
            r = requests.get(API + "/orders", timeout=5)
        except Exception as e:
            show_message("Ошибка сети", str(e))
            return
        for o in r.json():
            if o["user_id"] != current_user["id"]:
                continue
            text = f"Заказ #{o['id']} — {o['total']}₽ [{o['status']}]"
            self.list_box.add_widget(Label(text=text, size_hint_y=None, height=40))


# ====================== ЭКРАН ПРОФИЛЯ ======================
class ProfileScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = BoxLayout(orientation="vertical", padding=20, spacing=10)
        box.add_widget(Button(text="Назад", size_hint_y=None, height=50,
                              on_press=lambda *a: setattr(self.manager, "current", "menu")))
        self.info = Label(text="")
        box.add_widget(self.info)
        box.add_widget(Button(text="Обновить", size_hint_y=None, height=50, on_press=self.refresh))
        box.add_widget(Button(text="Выйти", size_hint_y=None, height=50, on_press=self.logout))
        self.add_widget(box)

    def on_enter(self):
        self.refresh()

    def refresh(self, *args):
        try:
            r = requests.get(f"{API}/users/{current_user['id']}", timeout=5)
        except Exception as e:
            self.info.text = f"Ошибка сети: {e}"
            return
        u = r.json()
        self.info.text = (f"Имя: {u['name']}\n"
                          f"Телефон: {u['phone']}\n"
                          f"Баллы: {u['balance_points']}")

    def logout(self, *args):
        current_user.clear()
        cart.clear()
        self.manager.current = "login"


# ====================== ПРИЛОЖЕНИЕ ======================
class CustomerApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(CartScreen(name="cart"))
        sm.add_widget(OrdersScreen(name="orders"))
        sm.add_widget(ProfileScreen(name="profile"))
        sm.current = "login"
        return sm


if __name__ == "__main__":
    CustomerApp().run()