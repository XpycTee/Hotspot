from flask import Blueprint, abort, jsonify, render_template, request

from core.admin.tables.settings.verificators import get_verificators, update_verificator
from core.utils.language import get_translate
from web.pages.admin.utils import login_required


verificators_bp = Blueprint('verificators', __name__, url_prefix='/verificators')


@verificators_bp.route('', methods=['GET'])
@login_required(group='full')
def index():
    data = get_verificators()
    
    template = render_template(
        'admin/settings/verificators.html',
        verificators=data,
    )

    return template


@verificators_bp.route('/update', methods=['POST'])
@login_required(group='full')
def update():
    req: dict = request.json
    if not req:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))
        
    order = req.get('order')
    verificators = req.get('verificators')

    for v in verificators:
        vid = v.get('id').strip()
        enabled = v.get('enabled')
        fields = v.get('fields')
        
        response = update_verificator(vid, enabled, fields, order)

        status = response.get('status')
        if status != 'OK':
            error_message = response.get('error_message')
            return jsonify({'success': False, 'error_message': error_message})
    
    return jsonify({'success': True})
