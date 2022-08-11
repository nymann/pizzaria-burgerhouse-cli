from datetime import datetime

from pizzaria_burgerhouse_cli.main import Order
from pizzaria_burgerhouse_cli.main import PizzariaBurgerhouseCli


def test_reorder(auth_cli: PizzariaBurgerhouseCli):
    order = Order(
        id=44028,
        dt=datetime(2022, 8, 11, 19, 7),
        products_count=1,
        price=76.0,
        status="Bestilt",
        customer_id=2879,
    )
    auth_cli.reorder(order=order)
