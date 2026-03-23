# how to write nanodjango-bolt

- there's documentation in nanodjango/docs/plugins.rst on how to write a plugin for nandodjango.
Here's a summary:
##PluginSystem                                                                                                                                                     
                                                                                                                                                                    
  Nanodjango uses pluggy for plugins. You write hooks with the @hookimpl decorator:                                                                                 
 ````                                                                                                                                                                   
  from nanodjango import hookimpl, Django                                                                                                                           
                                                                                                                                                                    
  @hookimpl                                                                                                                                                         
  def django_post_setup(app: Django):                                                                                                                               
      # runs after Django is configured
      pass
```

### Available Hooks (defined in nanodjango/hookspecs.py)

-  Lifecycle: django_pre_setup, django_post_setup

-  Routing: django_route_path_fn, django_route_path_kwargs — customize path functions and kwargs (e.g., django-distill uses this to add distill=True support to
  @app.route())

-  Conversion (~20 hooks): convert_init, convert_build_settings, convert_build_app_models, convert_build_app_views, convert_build_app_api, convert_build_app_urls,
  etc. — called during nanodjango convert to control how code is split into a full Django project.

###  Loading Plugins

- CLI flag: nanodjango --plugin=myplugin.py run script.py
- Same script: app.pm.hook.register(sys.modules[__name__])
- pip package: Add a [project.entry-points.nanodjango] entry in pyproject.toml:
```toml
  [project.entry-points.nanodjango]
  myproject = "myproject.nanodjango"
```
  Real Examples

  Three built-in plugins in nanodjango/contrib/ serve as references:
  - django_browser_reload.py — simplest; adds app/middleware in django_pre_setup, adds URL in convert_build_app_urls
  - django_distill.py — overrides path function via django_route_path_fn
  - django_ninja.py — most complex; does AST inspection during conversion to split API code into app/api.py

The **django_ninja.py** plugin  is basically the model for this plugin
