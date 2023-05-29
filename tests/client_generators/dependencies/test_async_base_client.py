import json
from datetime import datetime
from typing import Optional

import httpx
import pytest
from pydantic import BaseModel

from ariadne_codegen.client_generators.dependencies.async_base_client import (
    AsyncBaseClient,
)
from ariadne_codegen.client_generators.dependencies.base_model import UNSET
from ariadne_codegen.client_generators.dependencies.exceptions import (
    GraphQLClientGraphQLMultiError,
    GraphQLClientHttpError,
    GraphQlClientInvalidResponseError,
)


@pytest.mark.asyncio
async def test_execute_sends_post_to_correct_url_with_correct_payload(httpx_mock):
    httpx_mock.add_response()

    client = AsyncBaseClient(url="http://base_url/endpoint")
    query_str = """
    query Abc($v: String!) {
        abc(v: $v) {
            field1
        }
    }
    """

    await client.execute(query_str, {"v": "Xyz"})

    request = httpx_mock.get_request()
    assert request.url == "http://base_url/endpoint"
    content = json.loads(request.content)
    assert content == {"query": query_str, "variables": {"v": "Xyz"}}


@pytest.mark.asyncio
async def test_execute_parses_pydantic_variables_before_sending(httpx_mock):
    class TestModel1(BaseModel):
        a: int

    class TestModel2(BaseModel):
        nested: TestModel1

    httpx_mock.add_response()
    client = AsyncBaseClient(url="http://base_url")
    query_str = """
    query Abc($v1: TestModel1!, $v2: TestModel2) {
        abc(v1: $v1, v2: $v2){
            field1
        }
    }
    """

    await client.execute(
        query_str, {"v1": TestModel1(a=5), "v2": TestModel2(nested=TestModel1(a=10))}
    )

    request = httpx_mock.get_request()
    content = json.loads(request.content)
    assert content == {
        "query": query_str,
        "variables": {"v1": {"a": 5}, "v2": {"nested": {"a": 10}}},
    }


@pytest.mark.asyncio
async def test_execute_correctly_parses_top_level_list_variables(httpx_mock):
    class TestModel1(BaseModel):
        a: int

    httpx_mock.add_response()
    client = AsyncBaseClient(url="http://base_url")
    query_str = """
    query Abc($v1: [[TestModel1!]!]!) {
        abc(v1: $v1){
            field1
        }
    }
    """

    await client.execute(
        query_str,
        {
            "v1": [[TestModel1(a=1), TestModel1(a=2)]],
        },
    )

    request = httpx_mock.get_request()
    content = json.loads(request.content)
    assert content == {
        "query": query_str,
        "variables": {"v1": [[{"a": 1}, {"a": 2}]]},
    }
    assert not any(isinstance(x, BaseModel) for x in content["variables"]["v1"][0])


@pytest.mark.asyncio
async def test_execute_sends_payload_without_unset_arguments(httpx_mock):
    httpx_mock.add_response()
    client = AsyncBaseClient(url="http://base_url")
    query_str = """
    query Abc($arg1: TestInputA, $arg2: String, $arg3: Float, $arg4: Int!) {
        abc(arg1: $arg1, arg2: $arg2, arg3: $arg3, arg4: $arg4){
            field1
        }
    }
    """

    await client.execute(
        query_str, {"arg1": UNSET, "arg2": UNSET, "arg3": None, "arg4": 2}
    )

    request = httpx_mock.get_request()
    content = json.loads(request.content)
    assert content == {
        "query": query_str,
        "variables": {"arg3": None, "arg4": 2},
    }


@pytest.mark.asyncio
async def test_execute_sends_payload_without_unset_input_fields(httpx_mock):
    class TestInputB(BaseModel):
        required_b: str
        optional_b: Optional[str]

    class TestInputA(BaseModel):
        required_a: str
        optional_a: Optional[str]
        input_b1: Optional[TestInputB]
        input_b2: Optional[TestInputB]
        input_b3: Optional[TestInputB]

    httpx_mock.add_response()
    client = AsyncBaseClient(url="http://base_url")
    query_str = """
    query Abc($arg: TestInputB) {
        abc(arg: $arg){
            field1
        }
    }
    """

    await client.execute(
        query_str,
        {
            "arg": TestInputA(
                required_a="a", input_b1=TestInputB(required_b="b"), input_b3=None
            )
        },
    )

    request = httpx_mock.get_request()
    content = json.loads(request.content)
    assert content == {
        "query": query_str,
        "variables": {
            "arg": {
                "required_a": "a",
                "input_b1": {"required_b": "b"},
                "input_b3": None,
            }
        },
    }


@pytest.mark.asyncio
async def test_execute_sends_payload_with_serialized_datetime_without_exception(
    httpx_mock,
):
    httpx_mock.add_response()
    client = AsyncBaseClient(url="http://base_url")
    query_str = "query Abc($arg: DATETIME) { abc }"
    arg_value = datetime(2023, 12, 31, 10, 15)

    await client.execute(query_str, {"arg": arg_value})

    request = httpx_mock.get_request()
    content = json.loads(request.content)
    assert content["variables"]["arg"] == arg_value.isoformat()


@pytest.mark.parametrize(
    "status_code, response_content",
    [
        (401, {"msg": "Unauthorized"}),
        (403, {"msg": "Forbidden"}),
        (404, {"msg": "Not Found"}),
        (500, {"msg": "Internal Server Error"}),
    ],
)
def test_get_data_raises_graphql_client_http_error(
    mocker, status_code, response_content
):
    client = AsyncBaseClient(url="base_url", http_client=mocker.MagicMock())
    response = httpx.Response(
        status_code=status_code, content=json.dumps(response_content)
    )

    with pytest.raises(GraphQLClientHttpError) as exc:
        client.get_data(response)
        assert exc.status_code == status_code
        assert exc.response == response


@pytest.mark.parametrize("response_content", ["invalid_json", {"not_data": ""}, ""])
def test_get_data_raises_graphql_client_invalid_response_error(
    mocker, response_content
):
    client = AsyncBaseClient(url="base_url", http_client=mocker.MagicMock())
    response = httpx.Response(status_code=200, content=json.dumps(response_content))

    with pytest.raises(GraphQlClientInvalidResponseError) as exc:
        client.get_data(response)
        assert exc.response == response


@pytest.mark.parametrize(
    "response_content",
    [
        {
            "data": {},
            "errors": [
                {
                    "message": "Error message",
                    "locations": [{"line": 6, "column": 7}],
                    "path": ["field1", "field2", 1, "id"],
                }
            ],
        },
        {
            "data": {},
            "errors": [
                {
                    "message": "Error message type A",
                    "locations": [{"line": 6, "column": 7}],
                    "path": ["field1", "field2", 1, "id"],
                },
                {
                    "message": "Error message type B",
                    "locations": [{"line": 6, "column": 7}],
                    "path": ["field1", "field2", 1, "id"],
                },
            ],
        },
    ],
)
def test_get_data_raises_graphql_client_graphql_multi_error(mocker, response_content):
    client = AsyncBaseClient(url="base_url", http_client=mocker.MagicMock())

    with pytest.raises(GraphQLClientGraphQLMultiError):
        client.get_data(
            httpx.Response(status_code=200, content=json.dumps(response_content))
        )


@pytest.mark.parametrize(
    "response_content",
    [{"errors": [], "data": {}}, {"errors": None, "data": {}}, {"data": {}}],
)
def test_get_data_doesnt_raise_exception(mocker, response_content):
    client = AsyncBaseClient(url="base_url", http_client=mocker.MagicMock())

    data = client.get_data(
        httpx.Response(status_code=200, content=json.dumps(response_content))
    )

    assert data == response_content["data"]


@pytest.mark.asyncio
async def test_base_client_used_as_context_manager_closes_http_client(mocker):
    fake_client = mocker.AsyncMock()
    async with AsyncBaseClient(url="base_url", http_client=fake_client) as base_client:
        await base_client.execute("")

    assert fake_client.aclose.called
