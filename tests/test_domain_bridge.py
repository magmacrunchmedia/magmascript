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


# ── Host objects: properties, attribute writes, lazy construction ────


@dataclass
class MockInputState:
    """Shaped like texastoast's InputState: fields plus derived properties."""

    left: bool = False
    right: bool = False

    @property
    def dx(self) -> float:
        return (1.0 if self.right else 0.0) - (1.0 if self.left else 0.0)

    def is_moving(self) -> bool:
        return self.dx != 0.0


class MockEntity2:
    """A plain host class, the way a game entity arrives from a domain."""

    def __init__(self):
        self.x = 0.0
        self.speed = 100

    @property
    def center_x(self) -> float:
        return self.x + 8

    @property
    def frozen(self) -> bool:
        return True


class TestDataclassWrapperProperties:
    def test_property_is_readable(self):
        wrapper = wrap_result(MockInputState(right=True))
        assert isinstance(wrapper, DataclassWrapper)
        # A field still works...
        assert wrapper.right is True
        # ...and so does a property over the fields, which is the only way a
        # script can ask "which way is the player pressing".
        assert wrapper.dx == 1.0

    def test_method_is_reachable(self):
        wrapper = wrap_result(MockInputState(left=True))
        assert wrapper.is_moving() is True

    def test_missing_attribute_still_raises(self):
        wrapper = wrap_result(MockInputState())
        with pytest.raises(AttributeError, match="has no attribute 'nope'"):
            wrapper.nope

    def test_private_attribute_is_not_exposed(self):
        wrapper = wrap_result(MockInputState())
        with pytest.raises(AttributeError):
            wrapper._obj_should_not_be_reachable_this_way

    def test_property_read_through_the_interpreter(self):
        mock_client = MagicMock()
        mock_client.poll.return_value = MockInputState(right=True)

        env = Interpreter()
        env.globals.define("pad", DomainProxy("pad", mock_client))
        env.run(parse('s = pad.poll()\nresult = s.dx\n'))
        assert env.globals.variables["result"] == 1.0


class TestHostAttributeAssignment:
    def test_script_can_set_an_attribute(self):
        entity = MockEntity2()
        env = Interpreter()
        env.globals.define("player", entity)
        env.run(parse('player.speed = 250\n'))
        assert entity.speed == 250

    def test_fixed_width_values_are_unwrapped(self):
        entity = MockEntity2()
        env = Interpreter()
        env.globals.define("player", entity)
        env.run(parse('player.speed = i32(250)\n'))
        # Stored as a plain int, so host arithmetic on it still works.
        assert entity.speed == 250
        assert isinstance(entity.speed, int)

    def test_read_only_property_reports_the_line(self):
        env = Interpreter()
        env.globals.define("player", MockEntity2())
        with pytest.raises(Exception, match="Cannot set 'frozen'"):
            env.run(parse('player.frozen = false\n'))

    def test_unknown_attribute_is_still_rejected(self):
        env = Interpreter()
        env.globals.define("player", MockEntity2())
        with pytest.raises(Exception, match="Cannot set property"):
            env.run(parse('player.no_such_field = 1\n'))

    def test_private_attribute_is_rejected(self):
        entity = MockEntity2()
        entity._secret = 1
        env = Interpreter()
        env.globals.define("player", entity)
        with pytest.raises(Exception, match="Cannot set property"):
            env.run(parse('player._secret = 2\n'))
        assert entity._secret == 1


class TestLazyDomainConstruction:
    def test_client_is_not_built_until_used(self):
        built = []

        def factory():
            built.append(True)
            return MagicMock()

        proxy = DomainProxy("lazy", factory=factory)
        assert built == []          # constructing the proxy builds nothing
        proxy.anything()
        assert built == [True]
        proxy.anything()
        assert built == [True]      # and only once

    def test_close_does_not_build_a_client(self):
        built = []

        def factory():
            built.append(True)
            return MagicMock()

        DomainProxy("lazy", factory=factory).close()
        assert built == []


class TestEntryPointDiscovery:
    """Domains published by other installed packages."""

    class _FakeEntryPoint:
        def __init__(self, name, loader):
            self.name = name
            self._loader = loader

        def load(self):
            return self._loader()

    def test_third_party_domain_is_registered(self):
        from magmascript.core.registry import REGISTRY
        from magmascript.lang import domain_bridge

        class ToastDomain:
            def __init__(self, config=None):
                pass

        entry = self._FakeEntryPoint("toast_test", lambda: ToastDomain)
        with patch("importlib.metadata.entry_points", return_value=[entry]):
            domain_bridge.discover_domains()
        try:
            assert REGISTRY.get("toast_test") is ToastDomain
        finally:
            REGISTRY.pop("toast_test", None)

    def test_a_broken_entry_point_does_not_stop_startup(self):
        from magmascript.core.registry import REGISTRY
        from magmascript.lang import domain_bridge

        def explode():
            raise ImportError("no such package")

        entries = [
            self._FakeEntryPoint("broken_test", explode),
            self._FakeEntryPoint("ok_test", lambda: MagicMock),
        ]
        with patch("importlib.metadata.entry_points", return_value=entries):
            domain_bridge.discover_domains()
        try:
            assert "broken_test" not in REGISTRY
            assert "ok_test" in REGISTRY
        finally:
            REGISTRY.pop("ok_test", None)

    def test_builtins_win_a_name_clash(self):
        from magmascript.core.registry import REGISTRY, get_domain
        from magmascript.lang import domain_bridge

        original = get_domain("gh")
        entry = self._FakeEntryPoint("gh", lambda: MagicMock)
        with patch("importlib.metadata.entry_points", return_value=[entry]):
            domain_bridge.discover_domains()
        assert REGISTRY["gh"] is original
