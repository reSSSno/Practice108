import os
import json
import uuid
import redis
from flask import Flask, request, jsonify
from prometheus_client import Counter, generate_latest, REGISTRY

app = Flask(__name__)

# Собственная метрика: счётчик запросов на генерацию
GENERATE_REQUESTS = Counter('generate_requests_total', 'Total number of password generation requests')

redis_client = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), port=6379, db=0)

@app.route('/api/generate', methods=['POST'])
def generate():
    GENERATE_REQUESTS.inc()  # увеличиваем счётчик
    data = request.json
    task_id = str(uuid.uuid4())
    task_data = {
        'status': 'pending',
        'length': data['length'],
        'use_digits': data['use_digits'],
        'use_special': data['use_special']
    }
    redis_client.set(f"task:{task_id}", json.dumps(task_data))
    redis_client.lpush('password_tasks', task_id)
    return jsonify({'task_id': task_id})

@app.route('/api/result/<task_id>', methods=['GET'])
def result(task_id):
    task_data = redis_client.get(f"task:{task_id}")
    if task_data:
        return jsonify(json.loads(task_data))
    return jsonify({'status': 'not_found'}), 404

@app.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
