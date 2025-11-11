import hashlib

def get_cache_key(*args, **kwargs):
    """
    Generate a cache key from multiple arguments and keyword arguments
    """
    # Convert all arguments to strings
    key_parts = [str(arg) for arg in args]
    
    # Add sorted keyword arguments
    if kwargs:
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    
    # Join all parts with underscore
    return '_'.join(key_parts) 