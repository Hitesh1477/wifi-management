from flask import Blueprint, request, jsonify

# Create blueprint
# We keep this file to avoid breaking imports in app.py, 
# but all actual logic is now handled by admin_routes.py to ensure authentication
filtering_blueprint = Blueprint('filtering', __name__)

# Routes have been moved to admin_routes.py for better security and consolidation
