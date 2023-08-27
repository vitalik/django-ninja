/**JS file for handling the SwaggerUIBundle and avoid inline script */
const csrfSettings = document.querySelector("body").dataset
const configJson = document.getElementById("swagger-settings").textContent;
const configObject = JSON.parse(configJson);

configObject.dom_id = "#swagger-ui";
configObject.presets = [
    SwaggerUIBundle.presets.apis,
    SwaggerUIBundle.SwaggerUIStandalonePreset
];

if (csrfSettings.apiCsrf && csrfSettings.csrfToken) {
    configObject.requestInterceptor = (req) => {
        req.headers['X-CSRFToken'] = csrfSettings.csrfToken
        return req;
    };
};


// {% if add_csrf %}
// configObject.requestInterceptor = (req) => {
//     req.headers['X-CSRFToken'] = "{{csrf_token}}";
//     return req;
// };
// {% endif %}

const ui = SwaggerUIBundle(configObject);



// SwaggerUIBundle({
//     url: swaggerUi.dataset.openapiUrl,
//     dom_id: '#swagger-ui',
//     presets: [
//         SwaggerUIBundle.presets.apis,
//         SwaggerUIBundle.SwaggerUIStandalonePreset
//     ],
//     layout: "BaseLayout",
//     requestInterceptor: (req) => {
//         if (swaggerUi.dataset.apiCsrf && swaggerUi.dataset.csrfToken) {
//             req.headers['X-CSRFToken'] = swaggerUi.dataset.csrfToken
//         }
//         return req;
//     },
//     deepLinking: true
// })