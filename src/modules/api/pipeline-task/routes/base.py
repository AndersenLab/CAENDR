from itsdangerous import json
from flask import Blueprint, jsonify
import os


base_bp = Blueprint('base_bp', __name__)


@base_bp.route('/', methods=['GET', 'POST'])
def test_fn():
  return jsonify({}), 200

@base_bp.route('/version', methods=['GET'])
def version():
  version = os.getenv("MODULE_VERSION", "n/a")
  git_commit = os.getenv("GIT_COMMIT", "n/a")
  return jsonify({'version': version, 'git_commit': git_commit})