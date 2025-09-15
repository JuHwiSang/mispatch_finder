def to_jsonable(obj):
    """Convert various Python objects to JSON-serializable format.
    
    Handles:
    - Basic types (str, int, float, bool, None)
    - Collections (list, tuple, dict)
    - Pydantic models
    - Dataclasses
    - Bytes/Bytearray
    - Objects with to_jsonable method
    - Objects with __dict__
    
    Args:
        obj: Any Python object
        
    Returns:
        A JSON-serializable version of the object
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    elif isinstance(obj, (list, tuple)):
        return [to_jsonable(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    elif hasattr(obj, 'model_dump'):  # Pydantic v2
        return to_jsonable(obj.model_dump())
    elif hasattr(obj, 'dict'):  # Pydantic v1
        return to_jsonable(obj.dict())
    elif hasattr(obj, '__dataclass_fields__'):  # Dataclass
        from dataclasses import asdict
        return to_jsonable(asdict(obj))
    elif hasattr(obj, 'to_jsonable'):
        return obj.to_jsonable()
    elif hasattr(obj, '__dict__'):
        return to_jsonable(obj.__dict__)
    else:
        return str(obj)

