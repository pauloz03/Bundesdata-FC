import redis
import config
from fastapi import HTTPException, Request
from redis.exceptions import RedisError
import logging



logging.basicConfig(level=logging.INFO)
logger= logging.getLogger(__name__)

redis_client= redis.Redis(host= config.REDIS_HOST,
                          port= int(config.REDIS_PORT), 
                          db= int(config.REDIS_DB))



def get_client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host



def hit_rate_limit(key: str):
    attempts= redis_client.incr(key)
    timer_checker = redis_client.ttl(key)

    if attempts == 1 or timer_checker <0:    
        redis_client.expire(key, int(config.RATE_LIMIT_EXPIRE))

    return int(attempts) #means the request is allowed


def set_rate_limit(email: str, client_ip: str | None = None):
    email_key = f"rate_limit:email:{(email or '').strip().lower()}"

    try:
        if hit_rate_limit(email_key) > int(config.RATE_LIMIT_ATTEMPTS):
            raise HTTPException(status_code=429, detail="Too many requests, try again later")

        if client_ip:
            ip_key = f"rate_limit:ip:{client_ip}"
            if hit_rate_limit(ip_key) > int(config.RATE_LIMIT_ATTEMPTS):
                raise HTTPException(status_code=429, detail="Too many requests, try again later")
    
    except RedisError:
        logger.warning("Redis unavailable, skipping rate limit")
        return True

    return True