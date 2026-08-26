from slowapi import Limiter
from slowapi.util import get_remote_address

# এখানে Limiter কে ইনিশিয়ালাইজ করছি, যাতে যে কেউ স্বাধীনভাবে একে ডাকতে পারে
limiter = Limiter(key_func=get_remote_address)