
import sys
import os
sys.path.append('scripts')
from match_travelers import extract_features_nlp, extract_date

def test():
    print("Testing NLP extraction")
    text = "He has a large dragon tattoo on his back and was last seen wearing a blue hoodie and black jeans."
    features = extract_features_nlp(text)
    print(f"Features: {features}")
    
    # "a large dragon" is captured because 'dragon' is in tattoo_heads
    assert 'dragon' in str(features['tattoos'])
    assert 'hoodie' in str(features['clothing'])
    print("NLP Passed.")

    print("Testing Date Extraction")
    date_text = "Terry FIELD left Lost Nation structure on August 26th, 1986."
    dt = extract_date(date_text)
    print(f"Extracted Date: {dt}")
    assert dt is not None
    assert dt.year == 1986
    assert dt.month == 8
    assert dt.day == 26
    
    print("Date Test Passed!")

if __name__ == "__main__":
    test()
