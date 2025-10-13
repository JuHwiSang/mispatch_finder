from dataclasses import dataclass
import re

from mispatch_finder.shared.to_jsonable import to_jsonable


def test_to_jsonable_basic_types():
    assert to_jsonable(None) is None
    assert to_jsonable("test") == "test"
    assert to_jsonable(123) == 123
    assert to_jsonable(45.67) == 45.67
    assert to_jsonable(True) is True
    assert to_jsonable(False) is False


def test_to_jsonable_collections():
    assert to_jsonable([1, 2, 3]) == [1, 2, 3]
    assert to_jsonable((1, 2, 3)) == [1, 2, 3]
    assert to_jsonable({"a": 1, "b": 2}) == {"a": 1, "b": 2}


def test_to_jsonable_nested():
    data = {
        "list": [1, 2, {"nested": "value"}],
        "tuple": (3, 4, 5),
        "dict": {"key": "value"},
    }
    result = to_jsonable(data)
    assert result == {
        "list": [1, 2, {"nested": "value"}],
        "tuple": [3, 4, 5],
        "dict": {"key": "value"},
    }


def test_to_jsonable_bytes():
    assert to_jsonable(b"\x01\x02\x03") == "010203"
    assert to_jsonable(bytearray(b"\xff\xfe")) == "fffe"


def test_to_jsonable_dataclass():
    @dataclass
    class TestData:
        name: str
        value: int
    
    obj = TestData(name="test", value=42)
    result = to_jsonable(obj)
    
    assert result == {"name": "test", "value": 42}


def test_to_jsonable_nested_dataclass():
    @dataclass
    class Inner:
        x: int
    
    @dataclass
    class Outer:
        inner: Inner
        y: str
    
    obj = Outer(inner=Inner(x=10), y="test")
    result = to_jsonable(obj)
    
    assert result == {"inner": {"x": 10}, "y": "test"}


def test_to_jsonable_object_with_dict():
    class CustomObj:
        def __init__(self):
            self.foo = "bar"
            self.num = 123
    
    obj = CustomObj()
    result = to_jsonable(obj)
    
    assert result == {"foo": "bar", "num": 123}


def test_to_jsonable_object_with_method():
    class CustomObj:
        def to_jsonable(self):
            return {"custom": "serialization"}
    
    obj = CustomObj()
    result = to_jsonable(obj)
    
    assert result == {"custom": "serialization"}


def test_to_jsonable_fallback_to_str():
    """Test fallback to str() for objects without standard serialization."""
    # Create an object that will use str() fallback
    # Use a built-in type that doesn't have __dict__ or special serialization
    pattern = re.compile(r"test")
    
    result = to_jsonable(pattern)
    assert isinstance(result, str)
    assert "test" in result or "re.compile" in result.lower()


def test_to_jsonable_dict_with_non_string_keys():
    data = {1: "one", 2: "two", "three": 3}
    result = to_jsonable(data)
    
    # Keys should be converted to strings
    assert result == {"1": "one", "2": "two", "three": 3}

