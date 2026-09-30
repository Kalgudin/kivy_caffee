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
API = "http://localhost:8000" # API = "http://192.168.1.9.100:8000" #    IPv4-адрес. . . . . . . . . . . . : 192.168.1.9
ADMIN_PASSWORD = "admin123"     # пароль для входа в админку
# uvicorn main:app --reload --host 0.0.0.0 --port 8000

def show_message(title, text):
    Popup(title=title, content=Label(text=text), size_hint=(0.8, 0.3)).open()


# ====================== ЭКРАН ВХОДА ======================
class AdminLoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = BoxLayout(orientation="vertical", padding=20, spacing=10)
        box.add_widget(Label(text="Админ-панель", font_size=32))

        self.password = TextInput(hint_text="Пароль", password=True, multiline=False)
        box.add_widget(self.password)
        box.add_widget(Button(text="Войти", on_press=self.do_login))

        self.add_widget(box)

    def do_login(self, *args):
        if self.password.text != ADMIN_PASSWORD:
            show_message("Ошибка", "Неверный пароль")
            return
        self.manager.current = "orders"


# ====================== ЭКРАН ЗАКАЗОВ ======================
class AdminOrdersScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = BoxLayout(orientation="vertical")

        top = BoxLayout(size_hint_y=None, height=50, spacing=5)
        top.add_widget(Button(text="Обновить", on_press=self.load_orders))
        top.add_widget(Button(text="Меню", on_press=lambda *a: setattr(self.manager, "current", "menu")))
        top.add_widget(Button(text="Выйти", on_press=self.logout))
        box.add_widget(top)

        self.scroll = ScrollView()
        self.list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=10, padding=5)
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
            card = BoxLayout(orientation="vertical", size_hint_y=None, height=200, spacing=3)

            head = Label(text=f"Заказ #{o['id']} | {o['total']}₽ | {o['status']}",
                         size_hint_y=None, height=30)
            card.add_widget(head)

            # состав заказа
            items_text = ""
            for it in o.get("items", []):
                items_text += f"• item#{it['menu_item_id']} x{it['quantity']} ({it['drink_options'] or '—'})\n"
            card.add_widget(Label(text=items_text or "нет позиций", size_hint_y=None, height=100))

            # кнопки статуса
            btns = BoxLayout(size_hint_y=None, height=40, spacing=3)
            for status, label in [("preparing", "Готовится"),
                                  ("ready", "Готов"),
                                  ("completed", "Выдан"),
                                  ("cancelled", "Отмена")]:
                b = Button(text=label, font_size=12)
                b.bind(on_press=lambda x, oid=o["id"], s=status: self.set_status(oid, s))
                btns.add_widget(b)
            card.add_widget(btns)

            self.list_box.add_widget(card)

    def set_status(self, order_id, status):
        try:
            requests.patch(f"{API}/orders/{order_id}/status?status={status}", timeout=5)
        except Exception as e:
            show_message("Ошибка сети", str(e))
            return
        self.load_orders()

    def logout(self, *args):
        self.manager.current = "login"


# ====================== ЭКРАН УПРАВЛЕНИЯ МЕНЮ ======================
class AdminMenuScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = BoxLayout(orientation="vertical")

        top = BoxLayout(size_hint_y=None, height=50, spacing=5)
        top.add_widget(Button(text="Заказы", on_press=lambda *a: setattr(self.manager, "current", "orders")))
        top.add_widget(Button(text="Обновить", on_press=self.load_menu))
        box.add_widget(top)

        # форма добавления
        form = BoxLayout(size_hint_y=None, height=40, spacing=5)
        self.new_name = TextInput(hint_text="Название")
        self.new_price = TextInput(hint_text="Цена")
        self.new_category = TextInput(hint_text="Категория")
        form.add_widget(self.new_name)
        form.add_widget(self.new_price)
        form.add_widget(self.new_category)
        form.add_widget(Button(text="Добавить", on_press=self.add_item))
        box.add_widget(form)

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
            row = BoxLayout(size_hint_y=None, height=50, spacing=5)
            row.add_widget(Label(text=f"#{item['id']} {item['name']} — {item['price']}₽",
                                 size_hint_x=0.7))
            btn = Button(text="Удалить", size_hint_x=0.3)
            btn.bind(on_press=lambda b, i=item: self.delete_item(i["id"]))
            row.add_widget(btn)
            self.list_box.add_widget(row)

    def add_item(self, *args):
        if not self.new_name.text or not self.new_price.text:
            show_message("Ошибка", "Заполни название и цену")
            return
        try:
            requests.post(API + "/menu",
                          json={"name": self.new_name.text,
                                "price": float(self.new_price.text),
                                "category": self.new_category.text or "other"},
                          timeout=5)
        except Exception as e:
            show_message("Ошибка сети", str(e))
            return
        self.new_name.text = ""
        self.new_price.text = ""
        self.new_category.text = ""
        self.load_menu()

    def delete_item(self, item_id):
        try:
            requests.delete(f"{API}/menu/{item_id}", timeout=5)
        except Exception as e:
            show_message("Ошибка сети", str(e))
            return
        self.load_menu()


# ====================== ПРИЛОЖЕНИЕ ======================
class AdminApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(AdminLoginScreen(name="login"))
        sm.add_widget(AdminOrdersScreen(name="orders"))
        sm.add_widget(AdminMenuScreen(name="menu"))
        sm.current = "login"
        return sm


if __name__ == "__main__":
    AdminApp().run()