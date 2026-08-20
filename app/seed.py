"""Fill the database with demo data. Run once: python -m app.seed"""

from app.agent.prompts import DEFAULT_SYSTEM_PROMPT
from app.config import settings
from app.database import execute, init_db, query_one

PROPERTIES = [
    ("Sunny 2+1 near the metro", "Istanbul", "Kadikoy", "apartment", 2, 4200000,
     "Bright corner flat, 5 min walk to Kadikoy metro, south facing balcony."),
    ("Modern 3+1 with sea view", "Istanbul", "Besiktas", "apartment", 3, 9500000,
     "Renovated in 2023, sea view from the living room, closed parking."),
    ("Quiet 1+1 studio", "Istanbul", "Sisli", "apartment", 1, 2750000,
     "Ideal for a single professional, furnished, 24/7 security."),
    ("Family villa with garden", "Izmir", "Urla", "villa", 4, 15800000,
     "Detached villa, 400 m2 garden, private pool, 10 min to the sea."),
    ("Seafront 2+1", "Izmir", "Karsiyaka", "apartment", 2, 5300000,
     "Directly on the promenade, open kitchen, elevator building."),
    ("Central 3+1 office-friendly", "Ankara", "Cankaya", "apartment", 3, 6100000,
     "Suitable for home office, close to embassies, underfloor heating."),
]

FAQS = [
    ("What documents do I need to buy a property?",
     "You need your ID or passport, a Turkish tax number, and for foreign buyers an "
     "official valuation report. We handle the title deed appointment for you.",
     "document,documents,paperwork,id,passport,tax number,title deed,tapu"),
    ("Do you charge a commission?",
     "Our commission is 2% of the sale price plus VAT, paid only after the sale closes. "
     "Viewings and consultations are free.",
     "commission,fee,fees,charge,cost,percentage"),
    ("Can foreigners buy property?",
     "Yes. Foreign nationals can buy residential property in Turkey. Purchases above "
     "USD 400,000 may also qualify the buyer for citizenship by investment.",
     "foreigner,foreigners,foreign,expat,citizenship,residence permit,visa"),
    ("How long does the purchase process take?",
     "Typically 2 to 4 weeks from accepted offer to title deed transfer, assuming the "
     "valuation report and paperwork are ready.",
     "how long,duration,timeline,process,take,weeks,days"),
    ("What are your office hours?",
     "Our offices are open Monday to Saturday, 09:00 to 18:00. Viewings can also be "
     "arranged on Sunday by appointment.",
     "office hours,open,opening,working hours,available,sunday"),
]


def seed():
    init_db()

    if not query_one("SELECT id FROM properties LIMIT 1"):
        for title, city, district, ptype, bedrooms, price, description in PROPERTIES:
            execute(
                "INSERT INTO properties "
                "(title, city, district, property_type, bedrooms, price, currency, description) "
                "VALUES (?, ?, ?, ?, ?, ?, 'TRY', ?)",
                (title, city, district, ptype, bedrooms, price, description),
            )
        print("Seeded %d properties." % len(PROPERTIES))

    if not query_one("SELECT id FROM faqs LIMIT 1"):
        for question, answer, keywords in FAQS:
            execute(
                "INSERT INTO faqs (question, answer, keywords) VALUES (?, ?, ?)",
                (question, answer, keywords),
            )
        print("Seeded %d FAQs." % len(FAQS))

    if not query_one("SELECT key FROM settings WHERE key = 'system_prompt'"):
        execute(
            "INSERT INTO settings (key, value) VALUES ('system_prompt', ?)",
            (DEFAULT_SYSTEM_PROMPT,),
        )
        print("Seeded the default system prompt.")

    print("Database ready at %s" % settings.database_path)


if __name__ == "__main__":
    seed()
