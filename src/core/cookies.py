from __future__ import annotations

from typing import Literal, TypedDict, cast

from fastapi import Response

from src.core.config import settings


class CookieOptions(TypedDict, total=False):
    httponly: bool
    secure: bool
    samesite: Literal["lax", "strict", "none"] 
    max_age: int
    path: str
    domain: str


def auth_cookie_options(*, max_age: int) -> CookieOptions:
    options: CookieOptions = {
        "httponly": True,
        "secure": settings.SECURE_COOKIES,
        "samesite": cast(
            Literal["lax", "strict", "none"],
            settings.COOKIE_SAMESITE,
        ),
        "max_age": max_age,
        "path": "/",
    }

    if settings.COOKIE_DOMAIN:
        options["domain"] = settings.COOKIE_DOMAIN

    return options


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
) -> None:
    response.set_cookie(
        key=settings.ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        **auth_cookie_options(
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )

    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        **auth_cookie_options(
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        ),
    )


def clear_auth_cookies(response: Response) -> None:
    delete_options = {
        "secure": settings.SECURE_COOKIES,
        "httponly": True,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
    }

    if settings.COOKIE_DOMAIN:
        delete_options["domain"] = settings.COOKIE_DOMAIN

    response.delete_cookie(
        key=settings.ACCESS_TOKEN_COOKIE_NAME,
        **delete_options,
    )

    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        **delete_options,
    )