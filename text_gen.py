"""
Offline text content generator.
No AI models, no external APIs. Pure local data + template/combinatorial
generation, so output is effectively unlimited and always available offline.

Two generation strategies are combined:
  1. Curated banks: hand-written lines per category (used for "Random").
  2. Template engine: mad-lib style templates with slots that get filled
     from local word lists and (optionally) the user's topic, giving
     unlimited topic-specific variations without repeating verbatim.
"""
import random
import re

# ---------------------------------------------------------------------------
# Local word banks used to fill template slots
# ---------------------------------------------------------------------------

POSITIVE_ADJ = ["powerful", "quiet", "unstoppable", "simple", "rare", "honest",
                "bold", "gentle", "fierce", "steady", "small", "lasting"]
VIRTUES = ["patience", "discipline", "courage", "honesty", "focus", "kindness",
           "consistency", "gratitude", "curiosity", "resilience", "humility"]
OBSTACLES = ["fear", "doubt", "comfort", "excuses", "distraction", "noise",
             "the crowd", "yesterday", "your old self", "the easy way out"]
TIMEFRAMES = ["today", "this week", "right now", "one step at a time",
              "before you're ready", "starting small"]
PLACES = ["a quiet kitchen", "a small garage", "a rented room", "a college dorm",
          "a park bench", "an old notebook", "a late-night shift", "a long walk"]
ANIMALS = ["octopus", "penguin", "platypus", "honeybee", "narwhal", "sloth",
           "seahorse", "hedgehog", "otter", "flamingo", "tardigrade", "raccoon"]
SPACE_WORDS = ["neutron star", "black hole", "comet", "moon", "galaxy",
               "solar flare", "asteroid belt", "meteor shower"]
FOOD_WORDS = ["honey", "chocolate", "coffee", "garlic", "cinnamon", "avocado",
              "banana", "pineapple", "ginger", "tomato"]
HISTORY_WORDS = ["ancient Rome", "the Ming dynasty", "Victorian England",
                 "the Renaissance", "ancient Egypt", "medieval Europe"]
PROFESSIONS = ["teacher", "founder", "nurse", "developer", "artist", "chef",
               "student", "parent", "freelancer", "coach", "writer", "athlete"]
TIME_UNITS = ["5 minutes", "10 minutes", "one evening", "your lunch break",
              "one weekend", "15 minutes a day"]
TOOLS = ["a notebook", "your phone", "a free app", "a whiteboard", "a timer",
         "a sticky note", "a spreadsheet", "a simple checklist"]
CREATURES = ["a fox", "an old owl", "a young crow", "a stray cat", "a turtle",
             "a squirrel", "a raven", "a wandering goat"]
TWIST_WORDS = ["a locked door", "a second sun", "a letter with no return address",
               "a clock that ran backwards", "a map with no ending",
               "a light that shouldn't be there", "footprints leading nowhere",
               "a voice with no source"]


def _topic_or(default_list, topic):
    """Return the user topic if given, else a random pick from default_list."""
    if topic and topic.strip():
        return topic.strip()
    return random.choice(default_list)


def _cap(s):
    return s[0].upper() + s[1:] if s else s


# ---------------------------------------------------------------------------
# Curated banks (used mainly for "Random", no topic given)
# ---------------------------------------------------------------------------

QUOTE_BANK = [
    "Small steps every day beat big plans that never start.",
    "Discipline is choosing what you want most over what you want now.",
    "You don't need more time, you need a decision.",
    "Progress is quiet. It rarely looks impressive from the outside.",
    "The work you avoid is usually the work that matters most.",
    "Confidence is built in the reps nobody sees.",
    "Consistency beats intensity in the long run, every time.",
    "You are not behind. You are exactly where your effort has taken you.",
    "Comfort and growth have never lived in the same room.",
    "Start before you feel ready. Ready is a myth.",
]

FACT_BANK = [
    "Honey never spoils; archaeologists have found 3,000-year-old honey that's still edible.",
    "Octopuses have three hearts and blue blood.",
    "A day on Venus is longer than a year on Venus.",
    "Bananas are berries, but strawberries aren't.",
    "The Eiffel Tower grows about 6 inches taller in summer heat.",
    "Sharks existed before trees appeared on Earth.",
    "Your nose can remember around 50,000 different scents.",
    "A single cloud can weigh more than a million pounds.",
    "Wombat poop is cube-shaped.",
    "There are more possible chess games than atoms in the observable universe.",
]

TIP_BANK = [
    "Write tomorrow's top 3 tasks tonight — decisions are easier with a clear head.",
    "Put your phone in another room while you do deep work. Willpower is overrated; distance works better.",
    "Batch small tasks into one 20-minute block instead of scattering them all day.",
    "Drink a glass of water before your morning coffee. It helps more than you'd think.",
    "Use the 2-minute rule: if it takes less than 2 minutes, do it now, not later.",
    "Keep a 'done' list, not just a to-do list. It's good for momentum on hard days.",
    "Prep your workspace the night before. Future you will move faster.",
    "Say your goal out loud to one person. Spoken goals are easier to keep.",
]

JOKE_BANK = [
    "I told my computer I needed a break, and it said no problem, it'll go to sleep too.",
    "Why did the coffee file a police report? It got mugged.",
    "I'm reading a book on anti-gravity. It's impossible to put down.",
    "I used to be a banker, but I lost interest.",
    "Parallel lines have so much in common. It's a shame they'll never meet.",
    "My bed is a magical place where I suddenly remember everything I forgot to do.",
    "I'm on a seafood diet. I see food, and I eat it.",
    "Why don't scientists trust atoms? Because they make up everything.",
]

RIDDLE_BANK = [
    "I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I? (An echo)",
    "The more you take, the more you leave behind. What am I? (Footsteps)",
    "I have keys but no locks, space but no room. You can enter but not go inside. What am I? (A keyboard)",
    "What has hands but can't clap? (A clock)",
    "What gets wetter the more it dries? (A towel)",
    "I'm tall when young and short when old. What am I? (A candle)",
    "What has a neck but no head? (A bottle)",
]

STORY_OPENERS = [
    "The old lighthouse keeper had a rule: never open the door after midnight. Tonight, someone knocked twice.",
    "She found the letter tucked inside a library book that hadn't been checked out in forty years.",
    "Every morning the same fox waited at the bus stop, and every morning it left before the bus arrived.",
    "The last text on his phone was one word: 'Look.' He hadn't sent it.",
    "The town had one rule for the well: never look down. Nobody remembered why, until she did.",
]

CATEGORY_BANKS = {
    "quotes": QUOTE_BANK, "facts": FACT_BANK, "tips": TIP_BANK,
    "jokes": JOKE_BANK, "riddles": RIDDLE_BANK, "stories": STORY_OPENERS,
}

# ---------------------------------------------------------------------------
# Template engine (used when a topic is given, or to add variety to Random)
# ---------------------------------------------------------------------------

QUOTE_TEMPLATES = [
    lambda t: f"The secret to {t} isn't speed. It's {random.choice(VIRTUES)}.",
    lambda t: f"{_cap(random.choice(POSITIVE_ADJ))} {t} starts with beating {random.choice(OBSTACLES)}.",
    lambda t: f"Nobody talks about the {random.choice(OBSTACLES)} you have to beat before {t} gets easy.",
    lambda t: f"{_cap(t)} isn't a talent. It's a decision you repeat {random.choice(TIMEFRAMES)}.",
    lambda t: f"Every expert in {t} was once terrible at {t}, {random.choice(TIMEFRAMES)}.",
    lambda t: f"You don't find {t}. You build it, {random.choice(TIMEFRAMES)}, with {random.choice(VIRTUES)}.",
]

FACT_TEMPLATES = [
    lambda t: f"Here's something most people don't know about {t}: it's more connected to {random.choice(SPACE_WORDS + ANIMALS)} than you'd guess.",
    lambda t: f"Fun fact about {t}: researchers have compared it to {random.choice(ANIMALS)} behavior more than once.",
    lambda t: f"{_cap(t)} has a strange history — it was studied heavily during {random.choice(HISTORY_WORDS)}.",
    lambda t: f"One overlooked detail about {t}: it changes more in {random.choice(TIME_UNITS)} than people realize.",
]

TIP_TEMPLATES = [
    lambda t: f"Getting better at {t}? Try {random.choice(TIME_UNITS)} with {random.choice(TOOLS)} — nothing fancy, just consistency.",
    lambda t: f"The fastest way to improve at {t} is a {random.choice(TIME_UNITS)} daily habit, tracked with {random.choice(TOOLS)}.",
    lambda t: f"Struggling with {t}? Remove one distraction before you start, then give it {random.choice(TIME_UNITS)}.",
    lambda t: f"A simple {t} tip: prep with {random.choice(TOOLS)} the night before, not the morning of.",
]

JOKE_TEMPLATES = [
    lambda t: f"I tried to get better at {t} today. {t.capitalize()} won.",
    lambda t: f"They say practice makes perfect at {t}. My {t} still disagrees.",
    lambda t: f"My relationship with {t} is complicated. Mostly it's complicated.",
    lambda t: f"I told my friend I was an expert at {t}. My friend has not seen my {t}.",
]

RIDDLE_TEMPLATES = [
    lambda t: f"What grows every time you practice {t} but disappears the moment you quit? (Your skill)",
    lambda t: f"I'm never finished, always improving, and connected to {t}. What am I? (Progress)",
]

STORY_TEMPLATES = [
    lambda t: f"Every day at {random.choice(PLACES)}, someone practiced {t} in secret. Then one day, {random.choice(CREATURES)} showed up and watched.",
    lambda t: f"The note simply said: 'Master {t} by Friday.' Nobody remembered who wrote it, or why {random.choice(TWIST_WORDS)} was taped underneath.",
    lambda t: f"She'd spent years avoiding {t}, until she found {random.choice(TWIST_WORDS)} hidden in {random.choice(PLACES)}.",
]

CATEGORY_TEMPLATES = {
    "quotes": QUOTE_TEMPLATES, "facts": FACT_TEMPLATES, "tips": TIP_TEMPLATES,
    "jokes": JOKE_TEMPLATES, "riddles": RIDDLE_TEMPLATES, "stories": STORY_TEMPLATES,
}

RANDOM_TOPICS = [
    "discipline", "cooking", "running", "coding", "saving money", "public speaking",
    "gardening", "chess", "painting", "guitar", "photography", "focus",
    "morning routines", "small business", "writing", "fitness", "traveling light",
]


def generate_text(category, topic=None):
    """
    Generate a single piece of content text for the given category.
    category: one of quotes, facts, tips, stories, jokes, riddles
    topic: optional user-provided topic string; if empty, a random one is used
           and/or the curated bank is sampled.
    Returns: (text, topic_used)
    """
    category = category.lower().strip()
    if category not in CATEGORY_BANKS:
        category = "quotes"

    has_topic = bool(topic and topic.strip())
    topic_used = topic.strip() if has_topic else random.choice(RANDOM_TOPICS)

    # If no topic was given, sometimes pull straight from the curated bank
    # for authentic hand-written variety; otherwise (or the rest of the time)
    # use the template engine seeded with a topic for unlimited variation.
    if not has_topic and random.random() < 0.5:
        text = random.choice(CATEGORY_BANKS[category])
    else:
        template_fn = random.choice(CATEGORY_TEMPLATES[category])
        text = template_fn(topic_used.lower())
        text = re.sub(r"\s+", " ", text).strip()

    return text, topic_used


def generate_batch(category, topic=None, count=1):
    """Generate `count` non-trivial-duplicate texts."""
    seen = set()
    out = []
    tries = 0
    while len(out) < count and tries < count * 8:
        tries += 1
        text, used_topic = generate_text(category, topic)
        if text not in seen:
            seen.add(text)
            out.append((text, used_topic))
    return out
