"""Unit tests for tool building functionality"""
import inspect
from typing import Optional, List, Dict, Union
import pytest
from yakker.tool import get_json_type, create_items


class TestGetJsonType:
    """Tests for get_json_type function"""

    def test_str_annotation(self):
        assert get_json_type(annotation=str) == 'string'

    def test_int_annotation(self):
        assert get_json_type(annotation=int) == 'integer'

    def test_float_annotation(self):
        assert get_json_type(annotation=float) == 'number'

    def test_bool_annotation(self):
        assert get_json_type(annotation=bool) == 'boolean'

    def test_dict_annotation(self):
        assert get_json_type(annotation=dict) == 'object'

    def test_list_annotation(self):
        assert get_json_type(annotation=list) == 'array'

    def test_optional_annotation(self):
        assert get_json_type(annotation=Optional[list]) == 'array'

    def test_nested_optional_annotation(self):
        assert get_json_type(annotation=Optional[Optional[Optional[dict]]]) == 'object'

    def test_union_annotation(self):
        with pytest.raises(TypeError, match="Union types are not supported"):
            get_json_type(annotation=Union[str, int])

    def test_missing_annotation(self):
        assert get_json_type(inspect.Parameter.empty) == 'string'

class TestGetToolProperty:
    """Test the create_items function"""

    def test_create_items_for_list(self):
        expected = {
                'type': 'integer'
            }
        assert create_items(annotation=list[int]) == expected

    def test_create_items_for_nested_list(self):
        expected = {
                'type': 'array',
                'items': {
                    'type': 'string'
                }
            }
        assert create_items(annotation=list[list[str]]) == expected

    def test_dont_create_items_for_empty_list(self):
        expected = None
        assert create_items(annotation=list) == expected

    def test_dont_create_items_for_basic_type(self):
        expected = None
        assert create_items(annotation=str) == expected