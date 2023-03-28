import ast
from typing import List, Union

from ariadne_codegen.client_generators.constants import OPTIONAL, UNION
from ariadne_codegen.codegen import generate_union_annotation


def test_generate_union_annotation_returns_union_annotation():
    types: List[Union[ast.Name, ast.Subscript]] = [
        ast.Name(id="Xyz1"),
        ast.Name(id="Xyz2"),
    ]

    result = generate_union_annotation(types, False)

    assert isinstance(result, ast.Subscript)
    assert isinstance(result.value, ast.Name)
    assert result.value.id == UNION
    assert isinstance(result.slice, ast.Tuple)
    assert result.slice.elts == types


def test_generate_union_annotation_returns_optional_union_annotation():
    types: List[Union[ast.Name, ast.Subscript]] = [
        ast.Name(id="Xyz1"),
        ast.Name(id="Xyz2"),
    ]

    result = generate_union_annotation(types, True)

    assert isinstance(result, ast.Subscript)
    assert isinstance(result.value, ast.Name)
    assert result.value.id == OPTIONAL
    assert isinstance(result.slice, ast.Subscript)
    assert isinstance(result.slice.value, ast.Name)
    assert result.slice.value.id == UNION
    assert isinstance(result.slice.slice, ast.Tuple)
    assert result.slice.slice.elts == types
