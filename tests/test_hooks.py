"""Tests for plugin hooks (django_pre_setup and convert_build_app_api)."""

import ast
from unittest.mock import MagicMock, patch

from django.conf import settings

from nanodjango_bolt import convert_build_app_api, django_pre_setup


class TestDjangoPreSetup:
    def test_adds_django_bolt_when_installed(self):
        apps = [a for a in settings.INSTALLED_APPS if a != "django_bolt"]
        settings.INSTALLED_APPS = apps

        with patch("nanodjango_bolt.defer") as mock_defer:
            mock_defer.is_installed.return_value = True
            django_pre_setup(app=MagicMock())

        assert "django_bolt" in settings.INSTALLED_APPS

    def test_skips_when_not_installed(self):
        apps = [a for a in settings.INSTALLED_APPS if a != "django_bolt"]
        settings.INSTALLED_APPS = apps

        with patch("nanodjango_bolt.defer") as mock_defer:
            mock_defer.is_installed.return_value = False
            django_pre_setup(app=MagicMock())

        assert "django_bolt" not in settings.INSTALLED_APPS

    def test_no_duplicate_when_already_present(self):
        if "django_bolt" not in settings.INSTALLED_APPS:
            settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + ["django_bolt"]

        with patch("nanodjango_bolt.defer") as mock_defer:
            mock_defer.is_installed.return_value = True
            django_pre_setup(app=MagicMock())

        count = list(settings.INSTALLED_APPS).count("django_bolt")
        assert count == 1


def _make_converter(source: str):
    """Build a mock converter from Python source code."""
    tree = ast.parse(source)
    converter = MagicMock()
    converter.ast = tree
    return converter


def _make_resolver():
    resolver = MagicMock()
    resolver.add_object = MagicMock()
    resolver.add_references = MagicMock()
    return resolver


class TestConvertBuildAppApi:
    def test_detects_boltapi_assignment(self):
        source = "bolt = BoltAPI()"
        converter = _make_converter(source)
        resolver = _make_resolver()
        extra_src = []

        result_resolver, result_src = convert_build_app_api(converter, resolver, extra_src)

        resolver.add_object.assert_any_call("bolt")
        assert len(result_src) == 1
        assert "BoltAPI" in result_src[0]

    def test_detects_attribute_boltapi(self):
        """Detect bolt = nanodjango_bolt.BoltAPI()"""
        source = "bolt = nanodjango_bolt.BoltAPI()"
        converter = _make_converter(source)
        resolver = _make_resolver()
        extra_src = []

        convert_build_app_api(converter, resolver, extra_src)

        resolver.add_object.assert_any_call("bolt")
        assert len(extra_src) == 1

    def test_detects_decorated_async_function(self):
        source = """\
bolt = BoltAPI()

@bolt.get("/hello")
async def hello(request):
    return {"message": "hello"}
"""
        converter = _make_converter(source)
        resolver = _make_resolver()
        extra_src = []

        convert_build_app_api(converter, resolver, extra_src)

        # Should detect both the assignment and the function
        resolver.add_object.assert_any_call("bolt")
        resolver.add_object.assert_any_call("hello")
        assert len(extra_src) == 2

    def test_detects_decorated_sync_function(self):
        source = """\
bolt = BoltAPI()

@bolt.post("/items")
def create_item(request):
    return {"id": 1}
"""
        converter = _make_converter(source)
        resolver = _make_resolver()
        extra_src = []

        convert_build_app_api(converter, resolver, extra_src)

        resolver.add_object.assert_any_call("create_item")
        assert len(extra_src) == 2

    def test_detects_all_http_methods(self):
        methods = ["get", "post", "put", "patch", "delete", "websocket"]
        for method in methods:
            source = f"""\
bolt = BoltAPI()

@bolt.{method}("/test")
async def handler(request):
    pass
"""
            converter = _make_converter(source)
            resolver = _make_resolver()
            extra_src = []

            convert_build_app_api(converter, resolver, extra_src)

            resolver.add_object.assert_any_call("handler"), f"Failed for method: {method}"
            assert len(extra_src) == 2, f"Failed for method: {method}"

    def test_ignores_non_bolt_functions(self):
        source = """\
bolt = BoltAPI()

def regular_function():
    pass

@some_other_decorator
def other_function():
    pass
"""
        converter = _make_converter(source)
        resolver = _make_resolver()
        extra_src = []

        convert_build_app_api(converter, resolver, extra_src)

        # Only the BoltAPI assignment should be detected
        assert len(extra_src) == 1
        assert "BoltAPI" in extra_src[0]

    def test_ignores_unknown_method_on_bolt(self):
        """@bolt.options or other unknown methods should not be detected."""
        source = """\
bolt = BoltAPI()

@bolt.options("/test")
async def handler(request):
    pass
"""
        converter = _make_converter(source)
        resolver = _make_resolver()
        extra_src = []

        convert_build_app_api(converter, resolver, extra_src)

        # Only the BoltAPI assignment, not the handler
        assert len(extra_src) == 1

    def test_multiple_api_instances(self):
        source = """\
api1 = BoltAPI()
api2 = BoltAPI()

@api1.get("/a")
async def route_a(request):
    pass

@api2.post("/b")
async def route_b(request):
    pass
"""
        converter = _make_converter(source)
        resolver = _make_resolver()
        extra_src = []

        convert_build_app_api(converter, resolver, extra_src)

        resolver.add_object.assert_any_call("api1")
        resolver.add_object.assert_any_call("api2")
        resolver.add_object.assert_any_call("route_a")
        resolver.add_object.assert_any_call("route_b")
        assert len(extra_src) == 4

    def test_empty_module(self):
        converter = _make_converter("")
        resolver = _make_resolver()
        extra_src = []

        result_resolver, result_src = convert_build_app_api(converter, resolver, extra_src)

        resolver.add_object.assert_not_called()
        assert len(result_src) == 0

    def test_collects_references(self):
        source = """\
bolt = BoltAPI()

@bolt.get("/hello")
async def hello(request):
    return some_helper()
"""
        converter = _make_converter(source)
        resolver = _make_resolver()
        extra_src = []

        convert_build_app_api(converter, resolver, extra_src)

        # add_references should be called for both the assignment and the function
        assert resolver.add_references.call_count == 2

    def test_called_decorator_with_kwargs(self):
        """@bolt.get("/path", auth=True) style decorators should still work."""
        source = """\
bolt = BoltAPI()

@bolt.get("/hello", auth=True)
async def hello(request):
    pass
"""
        converter = _make_converter(source)
        resolver = _make_resolver()
        extra_src = []

        convert_build_app_api(converter, resolver, extra_src)

        resolver.add_object.assert_any_call("hello")
        assert len(extra_src) == 2
