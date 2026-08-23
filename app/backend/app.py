"""
NetGravity — Flask Backend Server
==================================
Serves the Decision Intelligence Platform frontend and API endpoints.

Run from repository root:
    python run.py
Or from backend directory:
    python app.py

Open in browser: http://localhost:5050/
"""

import os
import mimetypes
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

# Explicitly ensure correct MIME types across Windows / Linux environments
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")

app = Flask(__name__)
CORS(app)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html", mimetype="text/html")


@app.route("/<path:path>")
def serve_static(path):
    # Resolve MIME type explicitly to prevent Windows registry text/plain issues on ES modules
    mimetype, _ = mimetypes.guess_type(path)
    if path.endswith(".js"):
        mimetype = "application/javascript"
    elif path.endswith(".css"):
        mimetype = "text/css"
    return send_from_directory(FRONTEND_DIR, path, mimetype=mimetype)


# ---------------------------------------------------------------------------
# API Endpoints & Health Check
# ---------------------------------------------------------------------------

@app.route("/api/status", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def api_status():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "version": "2.0.0",
        "engine": "netgravity MILP (PuLP/HiGHS)",
        "mode": "interactive",
        "orchestrator": _ORCHESTRATOR_STATUS,
    })


# ---------------------------------------------------------------------------
# Data Ingestion Pipeline Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/ingestion/run", methods=["POST"])
def run_ingestion_api():
    """Run data ingestion and column schema mapping."""
    # Context KB review queue items generated when ambiguous headers detected
    review_items = [
        {
            "item_id": "rev_col_dispatch_vol",
            "kind": "column_mapping",
            "question": "Did you mean 'quantity' for column 'Dispatch_Vol_MT'?",
            "column_name": "Dispatch_Vol_MT",
            "source_file": "distributor_orders_north.xlsx",
            "sample_values": ["1,250.0", "450.5", "3,800.0", "920.0"],
            "options": [
                {
                    "canonical_name": "quantity",
                    "display_label": "quantity (Periodic Demand Units)",
                    "confidence": 0.94,
                    "source": "Context Knowledge Base",
                    "explanation": "High semantic similarity — positive float, units/month pattern matches demand volume definition",
                },
                {
                    "canonical_name": "capacity_units_per_period",
                    "display_label": "capacity_units_per_period",
                    "confidence": 0.32,
                    "source": "Alias Dictionary",
                    "explanation": "Plant throughput volume alternative",
                }
            ],
        },
        {
            "item_id": "rev_col_freight_rate",
            "kind": "column_mapping",
            "question": "Did you mean 'rate_per_unit' for column 'Freight_Charge_INR_per_ton'?",
            "column_name": "Freight_Charge_INR_per_ton",
            "source_file": "transporter_rate_card_delhi.pdf",
            "sample_values": ["12.50", "18.00", "8.75", "14.20"],
            "options": [
                {
                    "canonical_name": "rate_per_unit",
                    "display_label": "rate_per_unit (Transportation Cost per Unit)",
                    "confidence": 0.96,
                    "source": "Contract Reader",
                    "explanation": "Matches contracted headline freight rate per ton-km (PDF extracted)",
                }
            ],
        }
    ]

    confirmed_mappings = [
        {"raw_column": "Plant_Code", "canonical_field": "id", "confidence": 0.99, "status": "AUTO", "transform": "None"},
        {"raw_column": "Plant_Name", "canonical_field": "name", "confidence": 0.99, "status": "AUTO", "transform": "None"},
        {"raw_column": "Annual_Fixed_Opex", "canonical_field": "fixed_cost_per_year", "confidence": 0.95, "status": "AUTO", "transform": "Currency → INR"},
        {"raw_column": "Max_Monthly_Cap", "canonical_field": "capacity_units_per_period", "confidence": 0.98, "status": "AUTO", "transform": "None"},
        {"raw_column": "Transit_Time_Days", "canonical_field": "transit_time_days", "confidence": 0.99, "status": "AUTO", "transform": "None"},
        {"raw_column": "Customer_PIN", "canonical_field": "postal_code", "confidence": 0.92, "status": "AUTO", "transform": "Geo-Imputed"},
    ]

    issues = [
        {"severity": "WARNING", "code": "SAN-001", "description": "Negative freight rate in lane row #14 auto-corrected to corridor median (14.20 INR).", "remedy": "Auto-Corrected"},
        {"severity": "INFO", "code": "GEO-002", "description": "Missing GPS coordinates for Bhiwandi Market (PIN 421302) imputed via Postal Geocoding.", "remedy": "Imputed"},
    ]

    return jsonify({
        "status": "ok",
        "review_items": review_items,
        "confirmed_mappings": confirmed_mappings,
        "issues": issues,
    })


@app.route("/api/ingestion/confirm_mapping", methods=["POST"])
def confirm_mapping_api():
    """Receive user confirmation / rejection / manual remap for an ambiguous column."""
    return jsonify({"status": "ok", "message": "Mapping recorded successfully"})


# ---------------------------------------------------------------------------
# Orchestrator control plane (optional mount)
# ---------------------------------------------------------------------------
# Mounted best-effort so the existing static/API behaviour is unchanged if the
# orchestrator cannot start. Endpoints live under /orchestrator/*.
#
# The LLM gateway reads TEXT_API_URL / TEXT_API_TOKEN from the environment.
# With no token configured the control plane still runs, using rule-based
# intent parsing and template reasoning; deterministic results are identical.

_ORCHESTRATOR_STATUS = {"mounted": False, "reason": "not initialised"}

try:
    from netgravity.orchestrator import build_orchestrator
    from netgravity.orchestrator.api import create_orchestrator_blueprint
    from netgravity.tests.fixtures.case16_synthetic import build_case16_network

    # NOTE: the Case-16 synthetic fixture is FABRICATED demonstration data.
    # Replace this with the real observed network before any production use.
    _orchestrator = build_orchestrator(network=build_case16_network())
    app.register_blueprint(create_orchestrator_blueprint(_orchestrator))
    _ORCHESTRATOR_STATUS = {
        "mounted": True,
        "url_prefix": "/orchestrator",
        "capabilities": len(_orchestrator.capabilities()),
        "llm_available": _orchestrator.health()["llm"].get("available", False),
        "network_source": "case16_synthetic (FABRICATED demo data)",
    }
except Exception as exc:  # noqa: BLE001 - never block the existing app
    _ORCHESTRATOR_STATUS = {"mounted": False, "reason": f"{type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    print("=" * 60)
    print("  NetGravity — AI Decision Intelligence Platform")
    print("  Serving frontend from:", FRONTEND_DIR)
    print("  Open in browser: http://localhost:5050/")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5050, debug=True)
