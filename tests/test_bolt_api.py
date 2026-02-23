"""Tests for the BoltAPI subclass."""

import sys
import types

from django.conf import settings

from nanodjango_bolt import BoltAPI


class TestBoltAPIInit:
    def test_adds_django_bolt_to_installed_apps(self):
        # Remove django_bolt if already present so we can test it gets added
        apps = [a for a in settings.INSTALLED_APPS if a != "django_bolt"]
        settings.INSTALLED_APPS = apps

        BoltAPI()
        assert "django_bolt" in settings.INSTALLED_APPS

    def test_no_duplicate_installed_apps(self):
        """Instantiating twice should not duplicate the entry."""
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS)
        BoltAPI()
        BoltAPI()
        count = settings.INSTALLED_APPS.count("django_bolt")
        assert count == 1

    def test_captures_calling_module_name(self):
        bolt = BoltAPI()
        assert bolt._module_name == __name__

    def test_bolt_api_not_configured_initially(self):
        bolt = BoltAPI()
        assert bolt._bolt_api_configured is False

    def test_isinstance_of_real_bolt_api(self):
        from django_bolt.api import BoltAPI as RealBoltAPI

        bolt = BoltAPI()
        assert isinstance(bolt, RealBoltAPI)


class TestConfigureBoltAPI:
    def test_sets_bolt_api_setting_on_first_route(self):
        # Create a fake module and register our BoltAPI instance in it
        mod = types.ModuleType("fake_module_for_test")
        bolt = BoltAPI()
        bolt._module_name = "fake_module_for_test"
        mod.my_bolt = bolt
        sys.modules["fake_module_for_test"] = mod

        try:
            # Clear any existing BOLT_API
            if hasattr(settings, "BOLT_API"):
                del settings.BOLT_API

            bolt._configure_bolt_api()

            assert bolt._bolt_api_configured is True
            assert "fake_module_for_test:my_bolt" in settings.BOLT_API
        finally:
            del sys.modules["fake_module_for_test"]

    def test_skips_if_already_configured(self):
        bolt = BoltAPI()
        bolt._bolt_api_configured = True

        # Should return immediately without touching settings
        if hasattr(settings, "BOLT_API"):
            del settings.BOLT_API

        bolt._configure_bolt_api()
        assert not hasattr(settings, "BOLT_API") or "BOLT_API" not in dir(settings)

    def test_skips_if_module_not_found(self):
        bolt = BoltAPI()
        bolt._module_name = "nonexistent_module_xyz"

        bolt._configure_bolt_api()
        assert bolt._bolt_api_configured is False

    def test_no_duplicate_bolt_api_entries(self):
        mod = types.ModuleType("fake_module_dedup")
        bolt = BoltAPI()
        bolt._module_name = "fake_module_dedup"
        mod.api = bolt
        sys.modules["fake_module_dedup"] = mod

        try:
            settings.BOLT_API = ["fake_module_dedup:api"]
            bolt._configure_bolt_api()
            count = settings.BOLT_API.count("fake_module_dedup:api")
            assert count == 1
        finally:
            del sys.modules["fake_module_dedup"]


class TestHTTPMethodDecorators:
    """Each HTTP method decorator should trigger _configure_bolt_api."""

    def _make_bolt_in_module(self):
        mod = types.ModuleType("fake_mod_http")
        bolt = BoltAPI()
        bolt._module_name = "fake_mod_http"
        mod.bolt = bolt
        sys.modules["fake_mod_http"] = mod
        return bolt, mod

    def _cleanup(self):
        sys.modules.pop("fake_mod_http", None)

    def test_get_triggers_configure(self):
        bolt, mod = self._make_bolt_in_module()
        try:
            assert bolt._bolt_api_configured is False

            @bolt.get("/test")
            async def handler(request):
                return {"ok": True}

            assert bolt._bolt_api_configured is True
        finally:
            self._cleanup()

    def test_post_triggers_configure(self):
        bolt, mod = self._make_bolt_in_module()
        try:
            @bolt.post("/test")
            async def handler(request):
                return {"ok": True}

            assert bolt._bolt_api_configured is True
        finally:
            self._cleanup()

    def test_put_triggers_configure(self):
        bolt, mod = self._make_bolt_in_module()
        try:
            @bolt.put("/test")
            async def handler(request):
                return {"ok": True}

            assert bolt._bolt_api_configured is True
        finally:
            self._cleanup()

    def test_patch_triggers_configure(self):
        bolt, mod = self._make_bolt_in_module()
        try:
            @bolt.patch("/test")
            async def handler(request):
                return {"ok": True}

            assert bolt._bolt_api_configured is True
        finally:
            self._cleanup()

    def test_delete_triggers_configure(self):
        bolt, mod = self._make_bolt_in_module()
        try:
            @bolt.delete("/test")
            async def handler(request):
                return {"ok": True}

            assert bolt._bolt_api_configured is True
        finally:
            self._cleanup()

    def test_websocket_triggers_configure(self):
        bolt, mod = self._make_bolt_in_module()
        try:
            @bolt.websocket("/test")
            async def handler(request):
                pass

            assert bolt._bolt_api_configured is True
        finally:
            self._cleanup()
