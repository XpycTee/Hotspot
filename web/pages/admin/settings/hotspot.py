from flask import Blueprint, jsonify, request, session

from web.pages.admin.utils import login_required

hotspot_bp = Blueprint('hotspot', __name__, url_prefix='/hotspot')


@hotspot_bp.route('', methods=['POST', 'GET'])
@login_required
def index():
    return jsonify({
        'data': ''
    })


@hotspot_bp.route('/update', methods=['POST'])
@login_required
def update():
    data: dict = request.json
    return jsonify({'success': True})
