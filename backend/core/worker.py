import hashlib
import json
from pathlib import Path
from traceback import print_exc

from core.queueing import QUEUE, broker
from domain.learning import calculate, sweep

pulse = Path('/tmp/compute-heartbeat')
TTL = 86400

# 原子收尾：仅首个完成者写入最终记录，并发重试的其余完成者直接丢弃。
FINALIZE = """
if redis.call('set', KEYS[1], ARGV[1], 'nx', 'ex', ARGV[2]) then
  redis.call('set', KEYS[2], ARGV[3], 'ex', ARGV[2])
  return 1
end
return 0
"""

def sweep_key(job):
    canonical = json.dumps(job['input'], sort_keys=True, separators=(',', ':'))
    return 'sweep:' + hashlib.sha256(canonical.encode()).hexdigest()

def compute(job):
    data = job['input']
    if 'penalties' not in data:
        return calculate(data)
    key = sweep_key(job)
    def checkpoint(penalty, score):
        with broker.pipeline() as pipe:
            pipe.hset(key, str(penalty), score)
            pipe.expire(key, TTL)
            pipe.execute()
    return sweep(data, broker.hgetall(key), checkpoint)

def finalize(job, item, record):
    token = job['token']
    broker.eval(FINALIZE, 2, f'compute:{token}:finalized', f'compute:{token}',
                job['owner'], TTL, json.dumps(record, allow_nan=False))
    broker.lrem(f'{QUEUE}:processing', 1, item)

def serve():
    while True:
        broker.ping()
        pulse.touch()
        item = broker.blmove(QUEUE, f'{QUEUE}:processing', timeout=2, src='LEFT', dest='RIGHT')
        if item is None:
            continue
        job = json.loads(item)
        record = {'owner': job['owner'], 'input': job['input']}
        try:
            record.update(status='ready', result=compute(job))
        except ValueError as exc:
            record.update(status='rejected', detail=str(exc))
        except Exception:
            print_exc()
            record.update(status='rejected', detail='计算失败，请检查输入和 worker 日志')
        finalize(job, item, record)
        pulse.touch()

if __name__ == '__main__':
    for raw in broker.lrange(f'{QUEUE}:processing', 0, -1):
        with broker.pipeline() as pipe:
            pipe.lpush(QUEUE, raw)
            pipe.lrem(f'{QUEUE}:processing', 1, raw)
            pipe.execute()
    serve()
