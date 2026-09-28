"""Юнит-тест ModExpError.create_response(): должен возвращать Flask Response
с JSON-телом и ненулевым (по умолчанию 500) HTTP-статусом.

До исправления метод возвращал обычную строку (json.dumps(...)) —
Flask отдавал её как 200 OK text/html, то есть об ошибке нельзя было
узнать ни по коду ответа, ни по Content-Type.
"""
import json

from flask import Response

from experiment.experiment import ModExpError


def test_create_response_is_flask_response_with_json_and_default_500():
    e = ModExpError(error='boom', exception_message='detail')
    resp = e.create_response()

    assert isinstance(resp, Response)
    assert resp.status_code == 500
    assert resp.mimetype == 'application/json'

    body = json.loads(resp.get_data(as_text=True))
    assert body == {
        'success': False,
        'exception message': 'detail',
        'error': 'boom',
        'result': None,
    }


def test_create_response_accepts_custom_status():
    e = ModExpError(error='bad request')
    resp = e.create_response(status=400)
    assert resp.status_code == 400
