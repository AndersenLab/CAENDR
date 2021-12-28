src/modules/site
=============================================================================

The site module is an App Engine Flex container which uses Gunicorn as the Python WSGI HTTP Server (Web Server Gateway Interface) and Flask as the web framework with Jinja as the HTML template engine.

The contents of the `ext_assets` directory are copied to cloud storage by terraform and made public to the web. To embed an external asset in an HTML template use the `ext_asset()` jinja macro with the objects relative path in the ext_assets directory.

The `templates` directory contains all of the jinja HTML templates which are processed and returned by the view blueprints

The `base` directory includes:

- `base/views` - blueprint objects which define the site's structure and server-side page logic
- `base/utils` - utility functions which are either re-used or are too large to include within a view function
- `base/static` - static site resources, accessible from the *.com/static/ path because they must be served from the same domain (and I haven't set up a load balancer yet)
- `base/forms` - Flask forms and validators
