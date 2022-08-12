from pizzaria_burgerhouse_cli.main import PizzariaBurgerhouseCli


def test_latest_ten_orders(auth_cli: PizzariaBurgerhouseCli):
    orders = auth_cli.my_ten_last_orders()
    assert len(orders) == 10
