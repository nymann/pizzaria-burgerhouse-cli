from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from bs4 import ResultSet
from bs4 import Tag
import httpx
from rich.console import Console
import typer

app = typer.Typer()
c = Console()


def get_delivery_time(response: dict) -> Optional[str]:
    data = response["data"]
    return data.get("shopDeliverytime")


@dataclass
class Order:
    id: int
    dt: datetime
    products_count: int
    price: float
    status: str
    customer_id: int

    @classmethod
    def from_order_detail_row(cls, order_detail: Tag) -> "Order":
        cols: ResultSet = order_detail.find_all(name="td")
        return cls(
            id=text(cols[0], int),
            dt=text(cols[1], datetime.strptime, "%d-%m-%y %H:%M"),
            products_count=text(cols[2], int),
            price=text(cols[3], price_converter),
            status=text(cols[4]),
            customer_id=get_customer_id(cols[5]),
        )


class NewOrder:
    def __init__(self, id: int, status_token: str) -> None:
        self.id = id
        self.status_token = status_token
        self._ts = datetime.now()

    @classmethod
    def from_line(cls, line: str) -> "NewOrder":
        b = line[line.index('"') :]
        b = b.replace('"', "").replace(");", "").split(",")
        return cls(
            id=int(b[2]),
            status_token=b[0],
        )

    @property
    def time_running(self) -> int:
        delta = datetime.now() - self._ts
        return int(delta.total_seconds())


@dataclass
class CartItem:
    delete: str  # href="cart.php?remove=3496801837"
    product: str  # 164 Kylling
    count: int  # 1
    price: float  # 76,00 DKK

    @classmethod
    def from_row(cls, row: Tag) -> "CartItem":
        cols: ResultSet = row.find_all(name="td")
        del_tag = cols[0].find_all(href=True)[0]
        return cls(
            delete=del_tag.get("href"),
            product=cols[1].text.strip(),
            count=text(cols[2], int),
            price=text(cols[3], price_converter),
        )


def price_converter(price: str) -> float:
    p = price.replace(" DKK", "")
    p = p.replace(".", "")
    p = p.replace(",", ".")
    return float(p)


def get_customer_id(col: Tag) -> int:
    input_tag: Tag = col.find_all(name="input", attrs={"name": "customerId"})[0]
    res = input_tag.get("value")
    if not isinstance(res, str):
        raise Exception(f"{res} should be a string!")
    return int(res)


def text(col: Tag, parse: Callable = str, *args) -> Any:
    for child in col.children:
        text = child.text.strip()
        if text == "":
            continue
        return parse(text, *args)
    return parse(col.text.strip(), *args)


@app.command()
def reorder_pizza(username: str, password_file: Path = Path("/home/knj/.cache/pizza")) -> None:
    with open(password_file, "r") as file:
        password = file.read().strip("\n")
    a = PizzariaBurgerhouseCli()
    a.login(username, password)
    # 1. add something to the checking cart.
    a.reorder(a.my_ten_last_orders()[0])
    # 2. check the checking cart
    # order_items = a.check_cart()
    # for item in order_items:
    #    typer.echo(f"Item in cart: {item.product} ({item.price})")
    # 3. order them
    a.checkout_process()
    a.checkout_finalize()
    new_order = a.get_new_order()
    order_tui_printer(new_order=new_order, a=a)


def order_tui_printer(new_order: NewOrder, a: PizzariaBurgerhouseCli):
    c.print("Waiting for pizzaria to accept the order", end="")
    delivery: datetime = wait_for_order_to_be_accepted(new_order=new_order, a=a)
    c.clear()
    remaining = delivery - current_time()
    while remaining.total_seconds() > 0:
        c.print(f"{remaining} until the order is ready for pickup")
        sleep(1)
        remaining = delivery - datetime.now(tz=ZoneInfo("Europe/Copenhagen"))
        c.clear()
    c.print("Go pickup your pizza :-)")


def current_time() -> datetime:
    return datetime.now(tz=ZoneInfo("Europe/Copenhagen"))


def wait_for_order_to_be_accepted(new_order: NewOrder, a: PizzariaBurgerhouseCli) -> datetime:
    delivery_time = None
    while delivery_time is None:
        response = a.order_details(order=new_order)
        delivery_time = get_delivery_time(response=response)
        c.print(".", end="")
        sleep(3)
    current = current_time()
    hour, minute = delivery_time.split(":")
    return current.replace(hour=int(hour), minute=int(minute))


def is_product_row(tag: Tag) -> bool:
    attrs = tag.attrs
    if "class" not in attrs:
        return False
    class_names = attrs["class"]
    if "cart-row" not in class_names:
        return False
    for name in class_names:
        if name.startswith("customizeable"):
            return False
    return True


class PizzariaBurgerhouseCli:
    def __init__(self, base_url="http://pizzaria-burgerhouse.dk") -> None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 Edg/104.0.1293.47"
        }
        self.sess: httpx.Client = httpx.Client(base_url=base_url, headers=headers)

    def login(self, username: str, password: str) -> bool:
        data = {
            "username": username,
            "password": password,
            "doLogin": " Log ind ",
        }
        response = self.sess.post("/login.php", data=data)
        if response.status_code == 200:
            raise Exception("Bad credentials")

        return response.status_code == 302

    def my_ten_last_orders(self) -> list[Order]:
        text = self.sess.get("/mypage.php").text
        soup = BeautifulSoup(markup=text, features="html.parser")
        table: Tag = soup.find_all(name="table", attrs={"title": "Mine bestillinger"})[0]
        order_detail_trs = table.find_all(name="tr", attrs={"class": "myOrderDetails"})
        return [Order.from_order_detail_row(order_detail) for order_detail in order_detail_trs]

    def reorder(self, order: Order):
        data = {
            "orderId": order.id,
            "customerId": order.customer_id,
            # "x": "6",
            # "y": "5",
        }
        response = self.sess.post("/reorder.php", data=data)
        if response.status_code != 302:
            raise Exception("Something went wrong")

    def check_cart(self) -> list[CartItem]:
        text = self.sess.get("/cart.php").text
        soup = BeautifulSoup(markup=text, features="html.parser")
        table: Tag = soup.find_all(name="table", attrs={"id": "cartTableId"})[0]
        row = table.find_all(is_product_row)[0]
        return [CartItem.from_row(row)]

    def delete(self, item: CartItem) -> httpx.Response:
        return self.sess.get(item.delete)

    def _checkout_token(self) -> str:
        text = self.sess.get("/checkout_information.php").text
        soup = BeautifulSoup(markup=text, features="html.parser")
        token_tag: Tag = soup.find_all(name="input", attrs={"id": "token", "name": "token"})[0]
        token_value = token_tag.get("value")
        if not isinstance(token_value, str):
            raise Exception(f"{token_value} should be a string!")
        return token_value

    def checkout_process(self):
        # token can be found in /checkout_information
        data: dict[str, Any] = {
            "delivery": "1",
            "deliveryTime": "1",
            "deliveryDate": "",
            "payment": "1",
            "cust_id": "",
            "cust_name": "Kristian+Jakobsen",
            "cust_address": "H%F8jagerparken+5%2C+2",
            "cityList": "30_2750_Ballerup",
            "token": self._checkout_token(),
            "cust_zip": "2750",
            "cust_city": "Ballerup",
            "cust_mobile": "22805326",
            "cust_phone": "",
            "cust_email": "nymannjakobsen@gmail.com",
            "cust_email_verify": "nymannjakobsen@gmail.com",
            "cust_comments": "",
            "couponKey": "",
            "show-timeslot-pop": "0",
        }
        self.sess.post("/processors/checkout_process.php", data=data)

    def checkout_finalize(self):
        params = {"cartId": self.sess.cookies["PHPSESSID"]}
        data = {"terms": "ok"}
        response = self.sess.post("/processors/checkout_finalize.php", params=params, data=data)
        if response.status_code != 302:
            raise Exception("Something went wrong in checkout_finalize()")

    def get_new_order(self) -> NewOrder:
        lines = self.sess.get("/checkout_success.php").text.splitlines()
        for line in lines:
            if "startOrderVerificationProcess" not in line:
                continue
            return NewOrder.from_line(line=line)

        raise Exception("Order status token not found")

    def order_details(self, order: NewOrder):
        params = {
            "token": order.status_token,
            "action": "checkshopresponse",
            "format": "json",
            "orderid": f"{order.id}",
            "timerunning": f"{order.time_running}",
        }
        response = self.sess.get("/ajax/_ajax.php", params=params, headers={"X-Requested-With": "XMLHttpRequest"})
        return response.json()


if __name__ == "__main__":
    app()
