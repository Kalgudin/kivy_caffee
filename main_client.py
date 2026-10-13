# main_client.py — клиентское приложение ресторана
import os
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.properties import ListProperty

from api_client import ApiClient

api = ApiClient()

# Абсолютный путь к KV-файлу, чтобы не зависеть от CWD
HERE = os.path.dirname(os.path.abspath(__file__))
KV_PATH = os.path.join(HERE, 'client.kv')
print(f">>> Loading KV from: {KV_PATH}")
Builder.load_file(KV_PATH)
print(">>> KV loaded successfully")


# =========================================================
#  ЛОГИН
# =========================================================
class LoginScreen(Screen):
    def do_login(self):
        phone = self.ids.phone.text.strip()
        password = self.ids.password.text.strip()
        if not phone or not password:
            self.ids.msg.text = 'Заполните все поля'
            return

        user = api.login(phone, password)
        if user and 'id' in user:
            app = App.get_running_app()
            app.user = user
            self.ids.msg.text = ''
            app.root.current = 'menu'
        else:
            self.ids.msg.text = 'Неверный телефон или пароль'

    def do_register(self):
        App.get_running_app().root.current = 'register'


# =========================================================
#  РЕГИСТРАЦИЯ
# =========================================================
class RegisterScreen(Screen):
    def do_register(self):
        name = self.ids.name.text.strip()
        phone = self.ids.phone.text.strip()
        password = self.ids.password.text.strip()
        if not (name and phone and password):
            self.ids.msg.text = 'Заполните все поля'
            return

        res = api.create_user(name, phone, password)
        if isinstance(res, dict) and 'id' in res:
            self.ids.msg.text = ''
            App.get_running_app().root.current = 'login'
        else:
            self.ids.msg.text = f'Ошибка: {res}'


# =========================================================
#  МЕНЮ
# =========================================================
class MenuScreen(Screen):
    rv_data = ListProperty([])

    def on_pre_enter(self):
        self.load_menu()

    def load_menu(self):
        menu = api.get_menu()
        self.rv_data.clear()
        if isinstance(menu, list):
            self.rv_data.extend({'item': m} for m in menu)

    def add_to_cart(self, item):
        if not item:
            return
        app = App.get_running_app()
        for c in app.cart:
            if c['id'] == item['id']:
                c['qty'] += 1
                break
        else:
            app.cart.append({
                'id': item['id'],
                'name': item['name'],
                'price': item['price'],
                'qty': 1,
            })
        app.root.current = 'cart'

    def add_favorite(self, item):
        if not item:
            return
        app = App.get_running_app()
        if app.user:
            api.add_favorite(app.user['id'], item['id'])

    def logout(self):
        app = App.get_running_app()
        app.user = None
        app.cart = []
        app.root.current = 'login'


# =========================================================
#  КОРЗИНА
# =========================================================
class CartScreen(Screen):
    rv_data = ListProperty([])

    def on_pre_enter(self):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.rv_data.clear()
        self.rv_data.extend({'item': c} for c in app.cart)
        total = sum(c['price'] * c['qty'] for c in app.cart)
        self.ids.total.text = f"Итого: {total}₽"

    def remove_item(self, c):
        if not c:
            return
        app = App.get_running_app()
        c['qty'] -= 1
        if c['qty'] <= 0:
            app.cart.remove(c)
        self.refresh()

    def place_order(self):
        app = App.get_running_app()
        if not app.user or not app.cart:
            return

        items = [{
            'menu_item_id': c['id'],
            'quantity': c['qty'],
            'drink_options': '',
        } for c in app.cart]

        res = api.create_order(app.user['id'], items, self.ids.delivery.text)
        if isinstance(res, dict) and 'id' in res:
            bonus = int(res.get('total', 0) * 0.05)
            if bonus > 0:
                api.create_loyalty(app.user['id'], bonus, 'accrual', res['id'])
            app.cart = []
            app.root.current = 'orders'


# =========================================================
#  ЗАКАЗЫ
# =========================================================
class OrdersScreen(Screen):
    rv_data = ListProperty([])

    def on_pre_enter(self):
        self.load_orders()

    def load_orders(self):
        app = App.get_running_app()
        if not app.user:
            return
        all_orders = api.get_orders()
        mine = [o for o in all_orders if o.get('user_id') == app.user['id']] \
            if isinstance(all_orders, list) else []
        self.rv_data.clear()
        self.rv_data.extend({'item': o} for o in mine)

    def show_details(self, o):
        if not o:
            return
        full = api.get_order(o['id'])
        if not isinstance(full, dict) or 'id' not in full:
            return

        text = f"Заказ #{full['id']}\nСтатус: {full['status']}\n"
        text += f"Сумма: {full['total']}₽\nСпособ: {full['delivery_method']}\n\n"
        for it in full.get('items', []):
            text += (f"• блюдо {it['menu_item_id']} × {it['quantity']}"
                     f" = {it['price']}₽\n")
        Popup(title='Детали заказа', content=Label(text=text),
              size_hint=(0.9, 0.7)).open()


# =========================================================
#  ИЗБРАННОЕ
# =========================================================
class FavoritesScreen(Screen):
    rv_data = ListProperty([])

    def on_pre_enter(self):
        self.load_favorites()

    def load_favorites(self):
        app = App.get_running_app()
        if not app.user:
            return
        favs = api.get_favorites(app.user['id'])
        self.rv_data.clear()
        if isinstance(favs, list):
            self.rv_data.extend({'item': f} for f in favs)

    def delete_fav(self, f):
        if not f:
            return
        api.delete_favorite(f['id'])
        self.load_favorites()


# =========================================================
#  АКЦИИ
# =========================================================
class PromotionsScreen(Screen):
    rv_data = ListProperty([])

    def on_pre_enter(self):
        self.load_promotions()

    def load_promotions(self):
        app = App.get_running_app()
        if not app.user:
            return
        promos = api.get_promotions(app.user['id'])
        self.rv_data.clear()
        if isinstance(promos, list):
            self.rv_data.extend({'item': p} for p in promos)

    def delete_promo(self, p):
        if not p:
            return
        api.delete_promotion(p['id'])
        self.load_promotions()


# =========================================================
#  БОНУСЫ
# =========================================================
class LoyaltyScreen(Screen):
    rv_data = ListProperty([])

    def on_pre_enter(self):
        self.load_loyalty()

    def load_loyalty(self):
        app = App.get_running_app()
        if not app.user:
            return
        lst = api.get_loyalty(app.user['id'])
        self.rv_data.clear()
        if isinstance(lst, list):
            self.rv_data.extend({'item': l} for l in lst)


# =========================================================
#  ПРИЛОЖЕНИЕ
# =========================================================
class RestaurantClientApp(App):
    user = None
    cart = []

    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(CartScreen(name='cart'))
        sm.add_widget(OrdersScreen(name='orders'))
        sm.add_widget(FavoritesScreen(name='favorites'))
        sm.add_widget(PromotionsScreen(name='promotions'))
        sm.add_widget(LoyaltyScreen(name='loyalty'))
        return sm


if __name__ == '__main__':
    RestaurantClientApp().run()