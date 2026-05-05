import time
from typing import Any

import httpx


TOKEN_REFRESH_BUFFER_SECONDS = 300


class BnetClient:
    def __init__(self, client_id: str, client_secret: str, *, timeout: float = 15.0):
        self._id = client_id
        self._secret = client_secret
        self._http = httpx.Client(timeout=timeout)
        self._tokens: dict[str, tuple[str, float]] = {}
        self._cache: dict[tuple[str, str, str, str], tuple[Any, float]] = {}

    def _token(self, region: str) -> str:
        cached = self._tokens.get(region)
        now = time.time()
        if cached and cached[1] - TOKEN_REFRESH_BUFFER_SECONDS > now:
            return cached[0]

        resp = self._http.post(
            f"https://{region}.battle.net/oauth/token",
            data={"grant_type": "client_credentials"},
            auth=(self._id, self._secret),
        )
        resp.raise_for_status()
        body = resp.json()
        token = body["access_token"]
        expires_at = now + float(body.get("expires_in", 86400))
        self._tokens[region] = (token, expires_at)
        return token

    def get(
        self,
        path: str,
        namespace: str,
        region: str,
        *,
        params: dict | None = None,
        cache_ttl: int | None = None,
    ) -> dict:
        cache_key: tuple[str, str, str, str] | None = None
        if cache_ttl:
            params_key = "" if not params else "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            cache_key = (path, namespace, region, params_key)
            hit = self._cache.get(cache_key)
            if hit and hit[1] > time.time():
                return hit[0]

        request_params = {"namespace": f"{namespace}-{region}", "locale": "en_US"}
        if params:
            request_params.update(params)

        resp = self._http.get(
            f"https://{region}.api.blizzard.com{path}",
            params=request_params,
            headers={"Authorization": f"Bearer {self._token(region)}"},
        )
        resp.raise_for_status()
        data = resp.json()

        if cache_key is not None and cache_ttl:
            self._cache[cache_key] = (data, time.time() + cache_ttl)
        return data

    def close(self) -> None:
        self._http.close()
