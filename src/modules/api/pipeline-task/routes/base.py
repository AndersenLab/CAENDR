from flask import Blueprint, jsonify


base_bp = Blueprint('base_bp', __name__)


@base_bp.route('/', methods=['GET', 'POST'])
def test_fn():
    return jsonify({}), 200
