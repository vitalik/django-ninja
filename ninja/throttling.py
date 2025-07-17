import hashlib
import time
from typing import Dict, List, Optional, Tuple

from django.core.cache import cache as default_cache
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest


class BaseThrottle:
    """
    Rate throttling of requests.
    """

    def allow_request(self, request: HttpRequest) -> bool:
        """
        Return `True` if the request should be allowed, `False` otherwise.
        """
        raise NotImplementedError(".allow_request() must be overridden")

    def get_ident(self, request: HttpRequest) -> Optional[str]:
        """
        Identify the machine making the request by parsing HTTP_X_FORWARDED_FOR
        if present and number of proxies is > 0. If not use all of
        HTTP_X_FORWARDED_FOR if it is available, if not use REMOTE_ADDR.
        """
        from ninja.conf import settings

        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        remote_addr = request.META.get("REMOTE_ADDR")
        num_proxies = settings.NUM_PROXIES

        if num_proxies is not None:
            if num_proxies == 0 or xff is None:
                return remote_addr
            addrs: List[str] = xff.split(",")
            client_addr = addrs[-min(num_proxies, len(addrs))]
            return client_addr.strip()

        return "".join(xff.split()) if xff else remote_addr

    def wait(self) -> Optional[float]:
        """
        Optionally, return a recommended number of seconds to wait before
        the next request.
        """
        return None


class SimpleRateThrottle(BaseThrottle):
    """
    A simple cache implementation, that only requires `.get_cache_key()`
    to be overridden.

    The rate (requests / seconds) is set by a `rate` attribute on the Throttle
    class.  The attribute is a string of the form 'number_of_requests/period'.

    Period should be one of: ('s', 'sec', 'm', 'min', 'h', 'hour', 'd', 'day')

    Previous request information used for throttling is stored in the cache.
    """

    from ninja.conf import settings

    cache = default_cache
    timer = time.time
    cache_format = "throttle_%(scope)s_%(ident)s"
    scope: Optional[str] = None
    THROTTLE_RATES: Dict[str, Optional[str]] = settings.DEFAULT_THROTTLE_RATES
    _PERIODS = {
        "s": 1,
        "m": 60,
        "h": 60 * 60,
        "d": 60 * 60 * 24,
        "sec": 1,
        "min": 60,
        "hour": 60 * 60,
        "day": 60 * 60 * 24,
    }

    def __init__(self, rate: Optional[str] = None):
        self.rate: Optional[str]
        if rate:
            self.rate = rate
        else:
            self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

    def get_cache_key(self, request: HttpRequest) -> Optional[str]:
        """
        Should return a unique cache-key which can be used for throttling.
        Must be overridden.

        May return `None` if the request should not be throttled.
        """
        raise NotImplementedError(".get_cache_key() must be overridden")

    def get_rate(self) -> Optional[str]:
        """
        Determine the string representation of the allowed request rate.
        """
        if not getattr(self, "scope", None):
            msg = f"You must set either `.scope` or `.rate` for '{self.__class__.__name__}' throttle"
            raise ImproperlyConfigured(msg)

        try:
            return self.THROTTLE_RATES[self.scope]  # type: ignore
        except KeyError:
            msg = f"No default throttle rate set for '{self.scope}' scope"
            raise ImproperlyConfigured(msg) from None

    def parse_rate(self, rate: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
        """
        Given the request rate string, return a two tuple of:
        <allowed number of requests>, <period of time in seconds>
        """
        if rate is None:
            return (None, None)

        try:
            count, rest = rate.split("/", 1)

            for unit in self._PERIODS:
                if rest.endswith(unit):
                    multi = int(rest[: -len(unit)]) if rest[: -len(unit)] else 1
                    period = self._PERIODS[unit]
                    break
            else:
                multi, period = int(rest), 1

            return int(count), multi * period

        except (ValueError, IndexError):
            raise ValueError(f"Invalid rate format: {rate}") from None

    def allow_request(self, request: HttpRequest) -> bool:
        """
        Implement the check to see if the request should be throttled.

        On success calls `throttle_success`.
        On failure calls `throttle_failure`.
        """
        # if self.rate is None:
        #     return True

        self.key = self.get_cache_key(request)
        if self.key is None:
            return True

        self.history = self.cache.get(self.key, [])
        self.now = self.timer()  # type: ignore

        # Drop any requests from the history which have now passed the
        # throttle duration
        while self.history and self.history[-1] <= self.now - self.duration:  # type: ignore
            self.history.pop()
        if len(self.history) >= self.num_requests:  # type: ignore
            return self.throttle_failure()
        return self.throttle_success()

    def throttle_success(self) -> bool:
        """
        Inserts the current request's timestamp along with the key
        into the cache.
        """
        self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, self.duration)
        return True

    def throttle_failure(self) -> bool:
        """
        Called when a request to the API has failed due to throttling.
        """
        return False

    def wait(self) -> Optional[float]:
        """
        Returns the recommended next request time in seconds.
        """
        if self.history:
            remaining_duration = self.duration - (self.now - self.history[-1])
        else:
            remaining_duration = self.duration

        available_requests = self.num_requests - len(self.history) + 1  # type: ignore
        if available_requests <= 0:
            return None

        return remaining_duration / float(available_requests)  # type: ignore


class AnonRateThrottle(SimpleRateThrottle):
    """
    Limits the rate of API calls that may be made by a anonymous users.

    The IP address of the request will be used as the unique cache key.
    """

    scope = "anon"

    def get_cache_key(self, request: HttpRequest) -> Optional[str]:
        if getattr(request, "auth", None) is not None:
            return None  # Only throttle unauthenticated requests.

        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class AuthRateThrottle(SimpleRateThrottle):
    """
    Limits the rate of API calls that may be made by a given user.

    The string representation of request.auth object will be used as a unique cache key.
    If you use custom auth objects make sure to implement __str__ method.
    For anonymous requests, the IP address of the request will be used.
    """

    scope = "auth"

    def get_cache_key(self, request: HttpRequest) -> str:
        if getattr(request, "auth", None) is not None:
            ident = hashlib.sha256(str(request.auth).encode()).hexdigest()  # type: ignore
            # TODO: ^maybe auth should have an attribute that developer can overwrite
        else:
            ident = self.get_ident(request)  # type: ignore

        return self.cache_format % {"scope": self.scope, "ident": ident}


class UserRateThrottle(SimpleRateThrottle):
    """
    Limits the rate of API calls that may be made by a given user.

    The user id will be used as a unique cache key if the user is
    authenticated.  For anonymous requests, the IP address of the request will
    be used.
    """

    scope = "user"

    def get_cache_key(self, request: HttpRequest) -> str:
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {"scope": self.scope, "ident": ident}
