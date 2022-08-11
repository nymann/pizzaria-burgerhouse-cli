import pytest

from pizzaria_burgerhouse_cli.main import PizzariaBurgerhouseCli


@pytest.mark.skip()
def test_login_bad_creds() -> None:
    cli = PizzariaBurgerhouseCli()
    with pytest.raises(Exception) as err:
        cli.login(username="test@test.com", password="test123!")

    assert "Bad credentials" in str(err.value)
