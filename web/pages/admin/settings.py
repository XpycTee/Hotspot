from flask import Blueprint, jsonify

from web.pages.admin.utils import login_required


settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/get/<setting>', methods=['GET'])
@login_required
def get_setting(setting):
    return jsonify({})