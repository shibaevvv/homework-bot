from types import SimpleNamespace

import pytest
import requests


@pytest.mark.parametrize('scenario', ['network', 'http', 'api'])
def test_api_errors_do_not_expose_authorization(monkeypatch, homework_module,
                                               scenario):
    token = 'private-test-practicum-token'
    headers = {'Authorization': f'OAuth {token}'}
    monkeypatch.setattr(homework_module, 'HEADERS', headers)

    def mock_get(**kwargs):
        # Authentication must still be passed to the API.
        assert kwargs['headers'] == headers
        if scenario == 'network':
            raise requests.RequestException('Connection failed')
        return SimpleNamespace(
            status_code=503 if scenario == 'http' else 200,
            json=lambda: {'error': 'Service unavailable'},
        )

    monkeypatch.setattr(requests, 'get', mock_get)
    expected_error = {
        'network': ConnectionError,
        'http': homework_module.HttpStatusError,
        'api': homework_module.APIResponseError,
    }[scenario]

    with pytest.raises(expected_error) as exc_info:
        homework_module.get_api_answer(12345)

    message = str(exc_info.value)
    assert token not in message
    assert 'Authorization' not in message
    assert homework_module.ENDPOINT in message
    assert '12345' in message
