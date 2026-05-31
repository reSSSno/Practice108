import redis
import json
import random
import string
import os
import time

redis_client = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379, db=0)

def generate_password(length, use_digits, use_special):
    chars = string.ascii_letters
    if use_digits:
        chars += string.digits
    if use_special:
        chars += '!@#$%^&*()'
    return ''.join(random.choice(chars) for _ in range(length))

# Этот код будет выполняться ТОЛЬКО при запуске worker.py как скрипта,
# но НЕ при импорте из тестов
if __name__ == "__main__":
    while True:
        task_id = redis_client.brpop('password_tasks')[1].decode()
        time.sleep(2)  # имитация долгой обработки
        task_data = json.loads(redis_client.get(f"task:{task_id}"))
        try:
            password = generate_password(
                task_data['length'],
                task_data['use_digits'],
                task_data['use_special']
            )
            task_data['status'] = 'completed'
            task_data['password'] = password
        except Exception as e:
            task_data['status'] = 'failed'
            task_data['error'] = str(e)
        redis_client.set(f"task:{task_id}", json.dumps(task_data))
