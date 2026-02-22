from starlette.responses import HTMLResponse, JSONResponse
from starlette.schemas import SchemaGenerator

schema = SchemaGenerator(
    {
        "openapi": "3.0.2",
        "info": {"title": "TienLen API", "version": "1.0.0"},
    }
)


async def openapi(request):
    return JSONResponse(schema.get_schema(routes=request.app.routes))


async def swagger_ui(request):
    return HTMLResponse(
        """
        <!doctype html>
        <html>
          <head>
            <title>API Docs</title>
            <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css">
          </head>
          <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
            <script>
              window.onload = () => {
                SwaggerUIBundle({ url: '/openapi.json', dom_id: '#swagger-ui' });
              };
            </script>
          </body>
        </html>
        """
    )
