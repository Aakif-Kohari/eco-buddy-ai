"""
EcoBuddy AI Sustainability Insights REST API Service.

Provides secure REST API endpoints exposing carbon calculations, historical insights,
sustainability recommendations, reduction goals, API key provisioning, and OpenAPI/Swagger documentation.
"""

import json
import http.server
import urllib.parse
from emissions import calculate_footprint, calculate_eco_score
from recommendations import generate_recommendations
from database import get_assessments, get_active_goal
from goals import evaluate_progress
from api_auth import authenticate_request, generate_api_key, init_api_keys_db


OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "EcoBuddy AI Sustainability Insights API",
        "version": "1.0.0",
        "description": "REST API exposing EcoBuddy AI insights for integration with third-party applications."
    },
    "servers": [
        {"url": "http://localhost:8000", "description": "Local API Server"}
    ],
    "components": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer"
            }
        }
    },
    "security": [
        {"ApiKeyAuth": []},
        {"BearerAuth": []}
    ],
    "paths": {
        "/api/v1/health": {
            "get": {
                "summary": "Health Check",
                "description": "Check if API service is online.",
                "responses": {
                    "200": {"description": "API is healthy"}
                }
            }
        },
        "/api/v1/auth/keys": {
            "post": {
                "summary": "Create API Key",
                "description": "Provision a new API key for third-party application integration.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "app_name": {"type": "string", "example": "My Green App"},
                                    "user_id": {"type": "string", "example": "user_123"}
                                },
                                "required": ["app_name"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "API Key created successfully"},
                    "400": {"description": "Invalid input"}
                }
            }
        },
        "/api/v1/insights/calculate": {
            "post": {
                "summary": "Calculate Sustainability Insights",
                "description": "Calculate annual carbon emissions, Eco Score, and personalized insights from lifestyle inputs.",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "transport": {"type": "string", "example": "Car"},
                                    "distance": {"type": "number", "example": 15.0},
                                    "electricity": {"type": "number", "example": 250.0},
                                    "diet": {"type": "string", "example": "Omnivore"},
                                    "flights": {"type": "integer", "example": 2}
                                },
                                "required": ["transport", "distance", "electricity", "diet", "flights"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Calculated insights"},
                    "401": {"description": "Unauthorized"}
                }
            }
        },
        "/api/v1/insights/assessments": {
            "get": {
                "summary": "Get Historical Assessments",
                "description": "Retrieve user's historical footprint assessments.",
                "security": [{"ApiKeyAuth": []}],
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 10}}
                ],
                "responses": {
                    "200": {"description": "Historical assessment list"},
                    "401": {"description": "Unauthorized"}
                }
            }
        },
        "/api/v1/insights/recommendations": {
            "get": {
                "summary": "Get Recommendations",
                "description": "Get prioritized action items to lower carbon footprint.",
                "security": [{"ApiKeyAuth": []}],
                "parameters": [
                    {"name": "transport", "in": "query", "schema": {"type": "string"}},
                    {"name": "electricity", "in": "query", "schema": {"type": "number"}},
                    {"name": "diet", "in": "query", "schema": {"type": "string"}},
                    {"name": "flights", "in": "query", "schema": {"type": "integer"}}
                ],
                "responses": {
                    "200": {"description": "Sustainability recommendations"},
                    "401": {"description": "Unauthorized"}
                }
            }
        },
        "/api/v1/insights/goals": {
            "get": {
                "summary": "Get Active Reduction Goals",
                "description": "Retrieve status and evaluation of active carbon reduction goals.",
                "security": [{"ApiKeyAuth": []}],
                "responses": {
                    "200": {"description": "Active reduction goal and progress evaluation"},
                    "401": {"description": "Unauthorized"}
                }
            }
        }
    }
}


SWAGGER_UI_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>EcoBuddy AI - Swagger UI</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
    *, *:before, *:after { box-sizing: inherit; }
    body { margin: 0; background: #fafafa; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function() {
      window.ui = SwaggerUIBundle({
        url: '/api/v1/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ]
      });
    };
  </script>
</body>
</html>
"""


def process_api_request(method: str, path: str, headers: dict, body: dict = None, query_params: dict = None) -> tuple:
    """
    Process an API request cleanly and return (status_code, json_payload_or_html, content_type).
    """
    headers = headers or {}
    query_params = query_params or {}

    # Health check
    if method == "GET" and path == "/api/v1/health":
        return 200, {
            "status": "healthy",
            "service": "EcoBuddy AI Sustainability Insights API",
            "version": "1.0.0"
        }, "application/json"

    # OpenAPI spec
    if method == "GET" and path == "/api/v1/openapi.json":
        return 200, OPENAPI_SPEC, "application/json"

    # Swagger UI
    if method == "GET" and path in ("/docs", "/api/v1/docs"):
        return 200, SWAGGER_UI_HTML, "text/html"

    # Create API Key (Public / Developer endpoint)
    if method == "POST" and path == "/api/v1/auth/keys":
        app_name = body.get("app_name") if body else None
        if not app_name:
            return 400, {"error": "Bad Request", "message": "Missing 'app_name' parameter."}, "application/json"
        
        user_id = body.get("user_id", "default_user")
        key_data = generate_api_key(app_name, user_id=user_id)
        return 201, {
            "success": True,
            "message": "API key generated successfully. Save this key, it will not be shown again.",
            "data": key_data
        }, "application/json"

    # Authenticate all protected endpoints
    is_auth, auth_res = authenticate_request(headers)
    if not is_auth:
        return 401, {"error": "Unauthorized", "message": auth_res}, "application/json"

    user_id = auth_res.get("user_id", "default_user")

    # Endpoint: Calculate Insights
    if method == "POST" and path == "/api/v1/insights/calculate":
        if not body:
            return 400, {"error": "Bad Request", "message": "JSON body is required."}, "application/json"

        try:
            transport = str(body.get("transport", "Car"))
            distance = float(body.get("distance", 10.0))
            electricity = float(body.get("electricity", 150.0))
            diet = str(body.get("diet", "Omnivore"))
            flights = int(body.get("flights", 0))

            footprint, category_breakdown = calculate_footprint(
                transport, distance, electricity, diet, flights
            )
            eco_score = calculate_eco_score(footprint, category_breakdown)
            insight, recs = generate_recommendations(
                transport, electricity, diet, flights, category_breakdown
            )

            return 200, {
                "success": True,
                "data": {
                    "annual_footprint_kg_co2": round(footprint, 2),
                    "eco_score": round(eco_score, 1),
                    "category_breakdown": category_breakdown,
                    "insight": insight,
                    "recommendations": recs
                }
            }, "application/json"
        except Exception as e:
            return 400, {"error": "Calculation Error", "message": str(e)}, "application/json"

    # Endpoint: Get Assessments
    if method == "GET" and path == "/api/v1/insights/assessments":
        limit = int(query_params.get("limit", [10])[0]) if "limit" in query_params else 10
        raw_assessments = get_assessments() or []

        assessments = []
        for r in raw_assessments[:limit]:
            if isinstance(r, (list, tuple)) and len(r) >= 9:
                assessments.append({
                    "id": r[0],
                    "date": r[1],
                    "transport": r[2],
                    "distance": r[3],
                    "electricity": r[4],
                    "diet": r[5],
                    "flights": r[6],
                    "footprint_kg": r[7],
                    "eco_score": r[8]
                })

        return 200, {
            "success": True,
            "count": len(assessments),
            "data": assessments
        }, "application/json"

    # Endpoint: Recommendations
    if method == "GET" and path == "/api/v1/insights/recommendations":
        transport = query_params.get("transport", ["Car"])[0]
        electricity = float(query_params.get("electricity", [200.0])[0])
        diet = query_params.get("diet", ["Omnivore"])[0]
        flights = int(query_params.get("flights", [1])[0])

        footprint, category_breakdown = calculate_footprint(
            transport, 10.0, electricity, diet, flights
        )
        eco_score = calculate_eco_score(footprint, category_breakdown)
        insight, recs = generate_recommendations(
            transport, electricity, diet, flights, category_breakdown
        )

        return 200, {
            "success": True,
            "data": {
                "insight": insight,
                "recommendations": recs
            }
        }, "application/json"

    # Endpoint: Reduction Goals
    if method == "GET" and path == "/api/v1/insights/goals":
        goal = get_active_goal(user_id)
        if not goal:
            return 200, {
                "success": True,
                "data": None,
                "message": "No active reduction goal found for user."
            }, "application/json"

        raw_assessments = get_assessments(user_id=user_id) or []
        eval_data = evaluate_progress(goal, raw_assessments)

        return 200, {
            "success": True,
            "data": {
                "goal": goal,
                "evaluation": eval_data
            }
        }, "application/json"

    return 404, {"error": "Not Found", "message": f"Endpoint '{path}' with method '{method}' not found."}, "application/json"


class SustainabilityAPIRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP Request Handler for standalone EcoBuddy AI REST API server."""

    def log_message(self, format, *args):
        # Quiet standard HTTP server logs during testing
        pass

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def _handle(self, method):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        headers = {k: v for k, v in self.headers.items()}
        body = None
        if "Content-Length" in self.headers:
            content_length = int(self.headers["Content-Length"])
            if content_length > 0:
                raw_body = self.rfile.read(content_length)
                try:
                    body = json.loads(raw_body.decode('utf-8'))
                except json.JSONDecodeError:
                    body = {}

        status_code, response_data, content_type = process_api_request(
            method, path, headers, body=body, query_params=query_params
        )

        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key, Authorization")
        self.end_headers()

        if content_type == "application/json" and isinstance(response_data, (dict, list)):
            self.wfile.write(json.dumps(response_data, indent=2).encode('utf-8'))
        elif isinstance(response_data, str):
            self.wfile.write(response_data.encode('utf-8'))
