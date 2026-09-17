import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from search.query_generator import generate_buyer_queries
from search.relevance_filter import evaluate_singing_bowl_relevance
import config

def test_tavily_removed():
    print("\n--- TEST 1: Tavily Removal Check ---")
    assert not hasattr(config, 'TAVILY_API_KEY'), "TAVILY_API_KEY should be removed from config"
    print("PASS: config.py does not contain TAVILY_API_KEY")

def test_query_generator():
    print("\n--- TEST 2: State Query Generator ---")
    queries_ca = generate_buyer_queries("Singing Bowls", "USA", "California")
    print(f"Sample California query: '{queries_ca[0]}'")
    assert "California USA" in queries_ca[0], f"Expected 'California USA' in query, got '{queries_ca[0]}'"

    queries_tx = generate_buyer_queries("Singing Bowls", "USA", "Texas")
    print(f"Sample Texas query: '{queries_tx[0]}'")
    assert "Texas USA" in queries_tx[0], f"Expected 'Texas USA' in query, got '{queries_tx[0]}'"

    queries_ny = generate_buyer_queries("Singing Bowls", "USA", "New York")
    print(f"Sample New York query: '{queries_ny[0]}'")
    assert "New York USA" in queries_ny[0], f"Expected 'New York USA' in query, got '{queries_ny[0]}'"

    print("PASS: State query generation working correctly for California, Texas, New York")

def test_relevance_filter():
    print("\n--- TEST 3: Strict Singing Bowl Relevance Filter ---")
    
    # Candidate 1: Genuine Singing Bowl Wholesaler (HIGH)
    g1, rel1, r1 = evaluate_singing_bowl_relevance(
        "Himalayan Singing Bowls Wholesale & Distributor",
        "We are a leading wholesaler of authentic Tibetan singing bowls, chakra bowl sets, and gongs in California USA.",
        "https://www.himalayansingingbowls.com"
    )
    print(f"Candidate 1: Grade={g1}, Relevant={rel1} ({r1})")
    assert g1 == "HIGH" and rel1 is True

    # Candidate 2: Sound Therapy / Meditation shop with Singing Bowls (MEDIUM)
    g2, rel2, r2 = evaluate_singing_bowl_relevance(
        "Sacred Sound Therapy & Meditation Store",
        "Offering authentic hand-hammered singing bowls, tingshas, and sound healing instruments.",
        "https://www.sacredsoundshop.com"
    )
    print(f"Candidate 2: Grade={g2}, Relevant={rel2} ({r2})")
    assert rel2 is True

    # Candidate 3: Generic Wellness / Yoga studio without Singing Bowl evidence (LOW)
    g3, rel3, r3 = evaluate_singing_bowl_relevance(
        "Zen Wellness & Yoga Center",
        "Join our daily yoga classes, meditation sessions, and holistic wellness workshops.",
        "https://www.zenwellnessyoga.com"
    )
    print(f"Candidate 3: Grade={g3}, Relevant={rel3} ({r3})")
    assert g3 == "LOW" and rel3 is False

    # Candidate 4: News / Article / Market Research (LOW)
    g4, rel4, r4 = evaluate_singing_bowl_relevance(
        "Market Research Report on Global Singing Bowl Trends 2026",
        "Comprehensive market report analyzing industry leaders and revenue statistics.",
        "https://www.dataintelresearch.com"
    )
    print(f"Candidate 4: Grade={g4}, Relevant={rel4} ({r4})")
    assert g4 == "LOW" and rel4 is False

    print("PASS: Relevance filter correctly accepts genuine Singing Bowl candidates and rejects generic wellness/news")

if __name__ == "__main__":
    test_tavily_removed()
    test_query_generator()
    test_relevance_filter()
    print("\n[OK] ALL PIPELINE UNIT TESTS PASSED!")
