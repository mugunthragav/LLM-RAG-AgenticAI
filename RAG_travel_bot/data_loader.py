import mwparserfromhell
import bz2
import xml.etree.ElementTree as ET
from io import StringIO


def extract_text_from_wikivoyage(xml_dump_path, output_file="data/wikivoyage_combined.txt"):
    # Buffer to accumulate plain text
    full_text = []
    context = ET.iterparse(StringIO(), events=("start", "end"))  # Initial empty context

    # Open the bz2 file
    with bz2.open(xml_dump_path, "rt", encoding="utf-8") as file:
        # Parse XML incrementally
        context = ET.iterparse(file, events=("start", "end"))
        current_text = None

        for event, elem in context:
            if event == "start" and elem.tag.endswith("text"):  # Start of <text> tag
                current_text = ""  # Reset buffer for new text section
            elif event == "end" and elem.tag.endswith("text"):  # End of <text> tag
                if elem.text:
                    wiki_code = mwparserfromhell.parse(elem.text)
                    plain_text = wiki_code.strip_code().strip()  # Remove wiki markup
                    if plain_text:  # Only add non-empty text
                        full_text.append(plain_text)
            # Clear element to free memory
            elem.clear()

    # Save all extracted text to a file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_text))  # Separate articles with double newlines
    print(f"Extracted text saved to {output_file}. Total articles: {len(full_text)}")


# Path to your Wikivoyage dump
xml_dump = "data/enwikivoyage-latest-pages-articles.xml.bz2"
extract_text_from_wikivoyage(xml_dump)