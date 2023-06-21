/**JS file for handling the SwaggerUIBundle and avoid inline script */
const swaggerUi = document.querySelector("body")

SwaggerUIBundle({
    url: swaggerUi.dataset.openapiUrl,
    dom_id: '#swagger-ui',
    presets: [
    SwaggerUIBundle.presets.apis,
    SwaggerUIBundle.SwaggerUIStandalonePreset
    ],
    layout: "BaseLayout",
    requestInterceptor: (req) => {
        if (swaggerUi.dataset.apiCsrf && swaggerUi.dataset.csrfToken) {
            req.headers['X-CSRFToken'] = swaggerUi.dataset.csrfToken
        }
        return req;
    },
    deepLinking: true
})