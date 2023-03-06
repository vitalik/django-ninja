/**JS file for handling the SwaggerUIBundle and avoid inline script */
let openapi_url = document.getElementById("openapi_url")
let api_csrf = document.getElementById("api_csrf")
let csrf_token = document.getElementById("csrf_token")

openapi_url = openapi_url ? openapi_url.value : null
api_csrf = api_csrf ? api_csrf.value : null
csrf_token = csrf_token ? csrf_token.value : null

SwaggerUIBundle({
    url: openapi_url,
    dom_id: '#swagger-ui',
    presets: [
    SwaggerUIBundle.presets.apis,
    SwaggerUIBundle.SwaggerUIStandalonePreset
    ],
    layout: "BaseLayout",
    requestInterceptor: (req) => {
        if (api_csrf && csrf_token) {
            req.headers['X-CSRFToken'] = csrf_token
            return req;
        }
    },
    deepLinking: true
})