# main_staff.py
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from api_client import ApiClient

api = ApiClient()

Builder.load_file('staff.kv')


# ---------- модальное окно с формой ----------
class FormPopup(Popup):
    def __init__(self, title, fields, on_submit, **kw):
        super().__init__(title=title, size_hint=(0.9, 0.8), **kw)
        self.on_submit = on_submit
        self.inputs = {}
        box = BoxLayout(orientation='vertical', spacing=8, padding=8)
        for f in fields:
            box.add_widget(Label(text=f, size_hint_y=None, height=25))
            ti = TextInput(multiline=False, size_hint_y=None, height=45)
            box.add_widget(ti)
            self.inputs[f] = ti
        btn = Button(text='OK', size_hint_y=None, height=50)
        btn.bind(on_release=self.submit)
        box.add_widget(btn)
        self.content = box

    def submit(self, *a):
        data = {k: v.text.strip() for k, v in self.inputs.items()}
        self.on_submit(data)
        self.dismiss()


# ================= ЛОГИКА ЭКРАНОВ =================
class StaffHome(Screen):
    pass


class StaffOrders(Screen):
    rv_data = ListProperty([])

    def on_pre_enter(self):
        self.load_orders()

    def load_orders(self):
        orders = api.get_orders()
        self.rv_data = [{'item': o} for o in orders] if isinstance(orders, list) else []

    def change_status(self, o):
        def submit(data):
            api.update_status(o['id'], data['status'])
            self.load_orders()
        FormPopup('Новый статус (new/cooking/delivering/done/cancelled)',
                  ['status'], submit).open()

    def show_details(self, o):
        full = api.get_order(o['id'])
        text = f"Заказ #{full['id']}\nКлиент: {full['user_id']}\n"
        text += f"Статус: {full['status']}\nСумма: {full['total']}₽\n"
        text += f"Способ: {full['delivery_method']}\n\nСостав:\n"
        for it in full.get('items', []):
            text += f"• блюдо {it['menu_item_id']} × {it['quantity']} = {it['price']}₽\n"
        Popup(title='Детали заказа', content=Label(text=text),
              size_hint=(0.9, 0.8)).open()

    def delete_order(self, o):
        api.delete_order(o['id'])
        self.load_orders()


class StaffMenu(Screen):
    rv_data = ListProperty([])

    def on_pre_enter(self):
        self.load_menu()

    def load_menu(self):
        menu = api.get_menu()
        self.rv_data = [{'item': m} for m in menu] if isinstance(menu, list) else []

    def add_item(self):
        def submit(data):
            api.create_menu_item(
                name=data['name'],
                price=float(data['price']),
                category=data['category'],
                description=data.get('description', ''),
                is_available=True,
            )
            self.load_menu()
        FormPopup('Новое блюдо',
                  ['name', 'price', 'category', 'description'],
                  submit).open()

    def delete_item(self, item):
        api.delete_menu_item(item['id'])
        self.load_menu()


class StaffUsers(Screen):
    rv_data = ListProperty([])

    def on_pre_enter(self):
        self.load_users()

    def load_users(self):
        users = api.get_users()
        print('===========================')
        print(users)
        self.rv_data = [{'item': u} for u in users] if isinstance(users, list) else []

    def delete_user(self, u):
        api.delete_user(u['id'])
        self.load_users()


class StaffPromos(Screen):
    rv_data = ListProperty([])

    def add_promo(self):
        def submit(data):
            api.create_promotion(
                user_id=int(data['user_id']),
                description=data['description'],
                discount=float(data['discount']),
                start_date=data['start_date'],
                end_date=data['end_date'],
            )
        FormPopup('Новая акция',
                  ['user_id', 'description', 'discount',
                   'start_date', 'end_date'], submit).open()

    def load_promos(self):
        uid = self.ids.uid.text.strip()
        if not uid:
            return
        promos = api.get_promotions(int(uid))
        self.rv_data = [{'item': p} for p in promos] if isinstance(promos, list) else []

    def delete_promo(self, p):
        api.delete_promotion(p['id'])
        self.load_promos()


class StaffLoyalty(Screen):
    rv_data = ListProperty([])

    def load_loyalty(self):
        uid = self.ids.uid.text.strip()
        if not uid:
            return
        lst = api.get_loyalty(int(uid))
        self.rv_data = [{'item': l} for l in lst] if isinstance(lst, list) else []

    def add_points(self):
        uid = self.ids.uid.text.strip()
        if not uid:
            return

        def submit(data):
            api.create_loyalty(
                user_id=int(uid),
                points=int(data['points']),
                operation_type=data['operation_type'],
            )
            self.load_loyalty()
        FormPopup('Начислить/списать бонусы',
                  ['points', 'operation_type'], submit).open()


class StaffFavs(Screen):
    rv_data = ListProperty([])

    def load_favs(self):
        uid = self.ids.uid.text.strip()
        if not uid:
            return
        favs = api.get_favorites(int(uid))
        self.rv_data = [{'item': f} for f in favs] if isinstance(favs, list) else []

    def delete_fav(self, f):
        api.delete_favorite(f['id'])
        self.load_favs()


# ================= ПРИЛОЖЕНИЕ =================
class RestaurantStaffApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(StaffHome(name='home'))
        sm.add_widget(StaffOrders(name='orders'))
        sm.add_widget(StaffMenu(name='menu'))
        sm.add_widget(StaffUsers(name='users'))
        sm.add_widget(StaffPromos(name='promos'))
        sm.add_widget(StaffLoyalty(name='loyalty'))
        sm.add_widget(StaffFavs(name='favs'))
        return sm


if __name__ == '__main__':
    RestaurantStaffApp().run()