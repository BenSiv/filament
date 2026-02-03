
import pgeocode
import pandas as pd

nomi = pgeocode.Nominatim('ca')
# Check if query_postal_code works with city name? Unlikely.
# pgeocode uses data from geonames. 
# It has a dataframe access.

try:
    print("Searching for Vancouver...")
    res = nomi.query_postal_code("V6B") # Vancouver postal code prefix
    print(f"V6B: {res.latitude}, {res.longitude}, {res.place_name}")
    
    # Can we search by place name?
    # Access the underlying dataframe
    # nomi._data is the dataframe? Or valid extraction?
    # It seems pgeocode downloads data on first use.
    
    # Let's try to query a city name
    # There isn't a direct "query_city" method in basic usage.
    # But usually one searches by postal code.
    
    # If I don't have postal codes, I might need another way.
    pass
except Exception as e:
    print(e)
