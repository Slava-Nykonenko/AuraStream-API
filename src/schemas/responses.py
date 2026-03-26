from schemas.user import MessageSchema

AUTH_ERRORS = {
    401: {
        "model": MessageSchema,
        "description": "Bearer token is missing or invalid"},
    403: {"model": MessageSchema,
          "description": "Insufficient permissions or account inactive"},
}

NOT_FOUND = {
    404: {"model": MessageSchema,
          "description": "The requested resource does not exist"},
}

VALIDATION_ERROR = {
    400: {"model": MessageSchema,
          "description": "Business logic violation or invalid input data"},
}

ADMIN_ONLY = {
    403: {"model": MessageSchema,
          "description": "Administrative privileges required"},
}

CART_ERRORS = {
    400: {"model": MessageSchema,
          "description": "Movie already owned or already in cart"},
    404: {"model": MessageSchema,
          "description": "Movie or cart item not found in database"},
    500: {"model": MessageSchema,
          "description": "Server failed to process the cart update"},
}

MOVIE_Theater_ERRORS = {
    400: {"model": MessageSchema,
          "description": "Movie already exists or cannot be deleted due to active purchases"},
    404: {"model": MessageSchema,
          "description": "Movie, genre, or requested resource not found"},
    500: {"model": MessageSchema,
          "description": "Internal database error during movie processing"},
}

SOCIAL_ERRORS = {
    401: {"model": MessageSchema,
          "description": "Authentication required for this social action"},
    403: {"model": MessageSchema,
          "description": "Insufficient permissions or missing user profile"},
}

ORDER_ERRORS = {
    400: {"model": MessageSchema,
          "description": "Action failed: The cart is empty or the request is invalid"},
    404: {"model": MessageSchema,
          "description": "The requested order was not found or access was denied"},
}

PAYMENT_ERRORS = {
    400: {"model": MessageSchema,
          "description": "No valid items selected or payment not eligible for action"},
    404: {"model": MessageSchema,
          "description": "The associated order or Stripe session was not found"},
    500: {"model": MessageSchema,
          "description": "Critical error communicating with the Stripe Gateway"},
}

PROFILE_ERRORS = {
    400: {"model": MessageSchema,
          "description": "Profile already exists for this user"},
    404: {"model": MessageSchema,
          "description": "Profile or parent comment not found"},
}
