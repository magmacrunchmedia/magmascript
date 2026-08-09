"""Tests for the MagmaScript domain bridge."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from magmascript.lang.domain_bridge import (
    DomainProxy,
    DataclassWrapper,
    ListWrapper,
    wrap_result,
    create_domain_proxies,
)
from magmascript.lang.interpreter import Interpreter, run
from magmascript.lang.parser import parse


@dataclass
class MockEntity:
    name: str
    value: int


class TestDomainProxy:
    def test_method_call(self):
        mock_client = MagicMock()
        mock_client.search.return_value = [1, 2, 3]

        proxy = DomainProxy("test", mock_client)
        result = proxy.search("query")

        mock_client.search.assert_called_once_with("query")
        assert isinstance(result, ListWrapper)
        assert len(result) == 3

    def test_method_not_found(self):
        mock_client = MagicMock(spec=[])  # No methods
        proxy = DomainProxy("test", mock_client)

        with pytest.raises(AttributeError, match="has no method"):
            proxy.nonexistent()

    def test_close(self):
        mock_client = MagicMock()
        proxy = DomainProxy("test", mock_client)
        proxy.close()
        mock_client.close.assert_called_once()

    def test_repr(self):
        mock_client = MagicMock()
        proxy = DomainProxy("mcp", mock_client)
        assert repr(proxy) == "<domain:mcp>"


class TestWrapResult:
    def test_none(self):
        assert wrap_result(None) is None

    def test_primitives(self):
        assert wrap_result(42) == 42
        assert wrap_result(3.14) == 3.14
        assert wrap_result("hello") == "hello"
        assert wrap_result(True) is True

    def test_list(self):
        result = wrap_result([1, 2, 3])
        assert isinstance(result, ListWrapper)
        assert len(result) == 3

    def test_dataclass(self):
        entity = MockEntity(name="test", value=42)
        result = wrap_result(entity)
        assert isinstance(result, DataclassWrapper)
        assert result.name == "test"
        assert result.value == 42

    def test_callable(self):
        def my_func():
            return 42
        result = wrap_result(my_func)
        assert result is my_func


class TestListWrapper:
    def test_index(self):
        wrapper = ListWrapper([10, 20, 30])
        assert wrapper[0] == 10
        assert wrapper[2] == 30

    def test_length(self):
        wrapper = ListWrapper([1, 2, 3])
        assert len(wrapper) == 3

    def test_iteration(self):
        wrapper = ListWrapper([1, 2, 3])
        items = list(wrapper)
        assert items == [1, 2, 3]

    def test_out_of_bounds(self):
        wrapper = ListWrapper([1, 2, 3])
        with pytest.raises(IndexError):
            wrapper[10]


class TestDataclassWrapper:
    def test_attribute_access(self):
        entity = MockEntity(name="test", value=42)
        wrapper = DataclassWrapper(entity)
        assert wrapper.name == "test"
        assert wrapper.value == 42

    def test_unknown_attribute(self):
        entity = MockEntity(name="test", value=42)
        wrapper = DataclassWrapper(entity)
        with pytest.raises(AttributeError, match="has no attribute"):
            wrapper.nonexistent

    def test_repr(self):
        entity = MockEntity(name="test", value=42)
        wrapper = DataclassWrapper(entity)
        assert repr(wrapper) == "MockEntity(name='test', value=42)"


class TestDomainBridgeIntegration:
    def test_proxy_in_interpreter(self):
        mock_client = MagicMock()
        mock_client.search.return_value = [MockEntity(name="result1", value=1)]

        with patch("magmascript.lang.domain_bridge.create_domain_proxies") as mock_create:
            mock_create.return_value = {"mcp": DomainProxy("mcp", mock_client)}

            source = 'results = mcp.search("query")\nprint(results[0].name)\n'
            env = Interpreter()
            # Override the globals to use our mock
            env.globals.define("mcp", DomainProxy("mcp", mock_client))
            env.run(parse(source))

            mock_client.search.assert_called_once_with("query")

    def test_domain_method_returns_dataclass(self):
        mock_client = MagicMock()
        mock_client.get_entity.return_value = MockEntity(name="entity1", value=100)

        with patch("magmascript.lang.domain_bridge.create_domain_proxies") as mock_create:
            mock_create.return_value = {"mcp": DomainProxy("mcp", mock_client)}

            source = 'e = mcp.get_entity("type", "key")\nprint(e.name)\n'
            env = Interpreter()
            env.globals.define("mcp", DomainProxy("mcp", mock_client))
            env.run(parse(source))

            mock_client.get_entity.assert_called_once_with("type", "key")

    def test_domain_method_returns_list(self):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            MockEntity(name="a", value=1),
            MockEntity(name="b", value=2),
        ]

        with patch("magmascript.lang.domain_bridge.create_domain_proxies") as mock_create:
            mock_create.return_value = {"mcp": DomainProxy("mcp", mock_client)}

            source = 'results = mcp.search("test")\nprint(results[0].name)\n'
            env = Interpreter()
            env.globals.define("mcp", DomainProxy("mcp", mock_client))
            env.run(parse(source))

            mock_client.search.assert_called_once_with("test")

    def test_unavailable_domain(self):
        source = 'x = nonexistent.search("test")\n'
        env = Interpreter()
        # Don't define nonexistent - it should fail
        with pytest.raises(Exception, match="Undefined variable"):
            env.run(parse(source))
