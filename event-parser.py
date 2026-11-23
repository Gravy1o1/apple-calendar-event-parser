import re
from datetime import datetime, timezone

PARSING_RULES = [
    # --- CATEGORY 1: EXAMS & QUIZZES (Highest Priority) ---
    {
        "keywords": ["quiz", "exam", "test", "midterm", "examen", "interro"],
        "icon": "exclamationmark.triangle.fill",
        "speech_template": "Heads up, you have an evaluation: {item}."
    },
    {
        "keywords": ["submit", "hand in", "turn in", "homework", "assignment", "essay", "remettre", "devoir"],
        "icon": "pencil.and.list.clipboard",
        "speech_template": "Make sure to submit your work: {item}."
    },

    # --- CATEGORY 2: DIGITAL APPS & LINKS ---
    {
        "keywords": ["zoom", "teams", "meet", "call", "appel"],
        "icon": "video.fill",
        "speech_template": "Join your online meeting: {item}."
    },
    {
        "keywords": ["moodle", "classroom", "omnivox", "léa", "open", "app", "brightspace", "website", "ouvrir"],
        "icon": "arrow.up.forward.app.fill",
        "speech_template": "Digital action needed: {item}."
    },

    # --- CATEGORY 3: SPECIFIC MATERIALS ---
    {
        "keywords": ["laptop", "macbook", "pc", "computer", "ordinateur"],
        "icon": "laptopcomputer",
        "speech_template": "Pack your computer: {item}."
    },
    {
        "keywords": ["tablet", "ipad", "tablette"],
        "icon": "ipad",
        "speech_template": "Bring your tablet: {item}."
    },
    {
        "keywords": ["textbook", "book", "novel", "manual", "livre", "manuel"],
        "icon": "book.closed.fill",
        "speech_template": "Bring your book: {item}."
    },
    {
        "keywords": ["notebook", "binder", "folder", "cahier", "cartable"],
        "icon": "folder.fill",
        "speech_template": "Pack your folder or notebook: {item}."
    },
    {
        "keywords": ["calculator", "ti-84", "calculatrice"],
        "icon": "function",
        "speech_template": "Don't forget your calculator: {item}."
    },

    # --- CATEGORY 4: GENERIC CATCH-ALL (Always Last!) ---
    {
        "keywords": ["bring", "pack", "forget", "apporter", "prendre"],
        "icon": "backpack.fill",
        "speech_template": "Remember to {item}."
    }
]


# Common leading verbs/fillers in English and French
LEADING_FILLERS = re.compile(
    r"^(?:"
    r"don't forget to|remember to|make sure to|need to|please|"
    r"bring|pack|take|grab|open|launch|check|submit|hand in|turn in|"
    r"ne pas oublier de|n'oublie pas de|penser à|pense à|"
    r"apporter|apportez|prendre|prenez|ouvrir|ouvrez|remettre|remettez|rendre"
    r")\s+(?:your|my|the|a|an|ton|ta|tes|votre|vos|le|la|les|un|une|des)?\s*",
    re.IGNORECASE
)

def clean_item_text(raw_item: str) -> str:
    """Strips redundant starter verbs and articles while keeping the core noun."""
    cleaned = LEADING_FILLERS.sub("", raw_item).strip()
    
    # Safety check: If stripping left almost nothing (e.g., note was just "Open"), keep original
    if len(cleaned) < 2:
        return raw_item.strip()
        
    return cleaned

def get_icon_and_speech(raw_item: str) -> tuple[str, str]:
    lower_raw = raw_item.lower()
    cleaned = clean_item_text(raw_item)
    
    for rule in PARSING_RULES:
        for kw in rule["keywords"]:
            if re.search(rf"\b{re.escape(kw)}\b", lower_raw):
                # If the cleaned item is basically just the keyword itself (e.g. "calculator"),
                # avoid repeating it twice!
                if cleaned.lower() == kw.lower():
                    speech = rule["speech_template"].split(":")[0] + "."
                else:
                    speech = rule["speech_template"].format(item=cleaned)
                    
                return rule["icon"], speech
                
    return "checklist", f"{cleaned}." #Default if the parsing 


def class_event_parser(title: str, location: str, start_time: str, notes: str) -> list[dict]:
    """
    This method seperates the main information of a Apple Calendar Event (title, location, date and notes)
    into a list of dictionnairies representing Apple Watch pages indicating :
    - The text that should be on the screen (maximum 3 words);
    - The text that should be spoken if the user wishes to have a Voice Over;
    - The name or an idicator of the icon that should appear on the screen;

    The format for each dictionnary (page) is :
    ```python
    {
        "displayedText" : "Example class",
        "systemIcon" : "this_is_an_icon",
        "spokenText" : "You have your Example class in 5 minutes."
    }
    ```

    Args :
        title (string): The title of the event.
        location (string): The location of the event.
        start_time (string): The starting time of the event, in ISO format (ex: "2026-11-22T21:36:00Z").
        notes (string): What is written in the "notes" section of the event.

    Returns :
        list[dict]: A list of the information each page (represented by a dictionnary) should hold.

    """
    pages = []

    #Page 1 : event announcement, shows the event icon (that the user chose) and in how much time the event is in.
    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    mins_left = int((start_dt - datetime.now(timezone.utc)).total_seconds() / 60)

    if mins_left > 0 :
        pages.append({
            "displayedText" : f"{mins_left} mins",
            "systemIcon" : "chosen_event_icon",
            "spokenText" : f"You have f{title} in {mins_left} minutes."
        })
    else :
        pages.append({
            "displayedText" : "NOW",
            "systemIcon" : "chosen_event_icon",
            "spokenText" : f"Hurry. You have f{title} right now."
        })

    #Page 2 : event location.
    if location and location.strip() : #adds a page if there is a location (location != none and location dosn't just contain spaces)
        clean_location = location.strip()
        if len(clean_location.split()) <= 3:
            pages.append({
                "displayedText" : f"{clean_location}",
                "systemIcon" : "map_tag",
                "spokenText" : f"Go to {clean_location}."
            })
        else :
            print("Hello World!")
            # This is the scenario where the event location was a real location that was transformed
            # into an EKStructuredLocation object by the calendar.
            # Or the scenario where they put too much info about the location, or the building has a real
            # long name or something.
            # idk what to do with this yet...


    #Pages 3+ (the most important pages) : event notes, each distinct information (bullet point) in the event notes is seperated in pages.
    if notes and notes.strip():
        raw_items = re.split(r'(?:\r?\n|\s*[•\-*]\s+|\s*\d+[.;)]\s*)', notes)
        
        for raw in raw_items:
            raw_stripped = raw.strip(" .")
            if len(raw_stripped) < 2:
                continue
            
            # Get icon & natural spoken sentence 
            icon, spoken = get_icon_and_speech(raw_stripped)
            
            # Clean redundant words for the text displayed on the watch
            short_clean = clean_item_text(raw_stripped)
            # Capitalize first letter cleanly (without lowercasing acronym)
            short_clean = short_clean[0].upper() + short_clean[1:]
            
            short_display = f"<{short_clean[:16]}...>" if len(short_clean) > 16 else f"<{short_clean}>"
            
            pages.append({
                "displayedText" : short_display,
                "systemIcon" : icon,
                "spokenText" : spoken
            })

    #Page n : end of announcement, shows a checkmark to show the user that they have seen everything in the event.
    pages.append({
        "displayedText": "Done",
        "systemIcon" : "checkmark.circle.fill",
        "spokenText" : "That was all of the information about this event."
    })

    return pages
