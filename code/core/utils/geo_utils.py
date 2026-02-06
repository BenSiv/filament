import math

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth 
    using their latitude and longitude in decimal degrees.
    
    Returns distance in miles.
    """
    if None in (lat1, lon1, lat2, lon2):
        return None

    # Radius of Earth in miles
    R = 3958.8
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def calculate_geo_score(distance_miles: float) -> float:
    """
    Calculate a geographic score (0.0 to 1.0) using exponential decay.
    Close proximity (< 50 miles) yields near 1.0.
    Score drops significantly after 500 miles.
    """
    if distance_miles is None:
        return 0.5  # Neutral score for missing data
        
    # Exponential decay formula: e^(-d/k)
    # k = 250 means at 250 miles, the score is ~0.36
    # k = 500 means at 500 miles, the score is ~0.36
    k = 300 
    return math.exp(-distance_miles / k)
