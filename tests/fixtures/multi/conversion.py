def custom_caller(instance, args):
    operation, left, right = args
    if operation == "add":
        return instance.add(left, right)
    if operation == "multiply":
        return instance.multiply(left, right)
    raise ValueError(f"unknown operation: {operation}")
