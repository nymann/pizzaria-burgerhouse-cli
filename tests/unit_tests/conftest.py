import os

import pytest

from pizzaria_burgerhouse_cli.main import PizzariaBurgerhouseCli


@pytest.fixture
def auth_cli() -> PizzariaBurgerhouseCli:
    cli = PizzariaBurgerhouseCli()
    cli.login(username=os.environ["PIZZA_USER"], password=os.environ["PIZZA_PASS"])
    return cli
