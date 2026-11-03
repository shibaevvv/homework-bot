from unittest.mock import Mock

import pytest
import requests


def test_api_request_has_connect_and_read_timeout(monkeypatch, homework_module):
    response_data = {'homeworks': [], 'current_date': 12345}
    response = Mock(status_code=200)
    response.json.return_value = response_data
    mock_get = Mock(return_value=response)
    monkeypatch.setattr(requests, 'get', mock_get)

    assert homework_module.get_api_answer(12345) == response_data

    mock_get.assert_called_once_with(
        url=homework_module.ENDPOINT,
        headers=homework_module.HEADERS,
        params={'from_date': 12345},
        timeout=(5, 30),
    )


def test_api_timeout_becomes_connection_error_without_token(
        monkeypatch, homework_module):
    token = 'private-timeout-test-token'
    monkeypatch.setattr(
        homework_module, 'HEADERS', {'Authorization': f'OAuth {token}'},
    )
    timeout_error = requests.Timeout('Request timed out')
    mock_get = Mock(side_effect=timeout_error)
    monkeypatch.setattr(requests, 'get', mock_get)

    with pytest.raises(ConnectionError) as exc_info:
        homework_module.get_api_answer(12345)

    assert exc_info.value.__cause__ is timeout_error
    message = str(exc_info.value)
    assert 'Request timed out' in message
    assert token not in message
    assert 'Authorization' not in message
