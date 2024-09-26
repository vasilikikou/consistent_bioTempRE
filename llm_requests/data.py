import os
# import stanza
import xml.etree.ElementTree as ET

from tqdm import tqdm
from lxml import etree
from typing import List, Tuple, Dict
from nltk.tokenize import sent_tokenize
from xml.etree.ElementTree import Element, SubElement, ElementTree


def get_xml_files(data_path: str) -> List:
    """
    :param data_path: Path to folder that contains the data files
    :return: Array with the filenames of the xml data files
    """
    filenames = os.listdir(data_path)
    xml_files = []
    for f in filenames:
        if f.split(".")[-1] == "xml":
            xml_files.append(f)
    return xml_files


def load_data(
    data_path: str, filenames: List
) -> Tuple[List[str], List[List[Dict]], List]:
    """

    :param data_path: Path to folder that contains the data files
    :param filenames: Array with the filenames with want to load

    :return: cl_note_texts: Array with the clinical notes texts
            cl_note_events: Array of dictionaries with the attributes of all the events
            cl_note_tlinks: Array of dictionaries with the attributes of all the temporal links
    """

    cl_note_texts, cl_note_events, cl_note_tlinks = [], [], []

    for f in filenames:  # for all retrieved files
        parser = etree.XMLParser(recover=True)
        root = etree.parse(os.path.join(data_path, f), parser=parser)

        # Get the text
        text = root.find("TEXT").text.strip()
        # Remove new line symbols
        text = text.replace("\n", " ")

        cl_note_texts.append(text)

        sectimes = {}
        for s in root.find("TAGS").findall("SECTIME"):
            sectimes[s.attrib["type"]] = s.attrib["text"]

        # Extract the events
        events = []
        for event in root.find("TAGS").findall("EVENT"):
            event_values = dict(event.attrib.items())
            # event_values["event_type"] = "EVENT"
            event_values["SECTIME"] = False
            events.append(event_values)

        # Extract Timex3 events
        timexs = []
        for timex in root.find("TAGS").findall("TIMEX3"):
            timex_values = dict(timex.attrib.items())
            # timex_values["event_type"] = "TIMEX3"
            if timex_values["text"] in list(
                sectimes.values()
            ):  # if timex_values["text"] is either admission or discahrge date
                index = list(sectimes.values()).index(timex_values["text"])
                timex_values["SECTIME"] = True
            else:
                timex_values["SECTIME"] = False
            timexs.append(timex_values)

        # Merge events and timex3s
        cl_note_events.append(events + timexs)

        # Extract Tlinks
        tlinks = []
        for link in root.find("TAGS").findall("TLINK"):
            tlinks.append(dict(link.attrib.items()))

        cl_note_tlinks.append(tlinks)

    return cl_note_texts, cl_note_events, cl_note_tlinks


def load_pairs(pairs_file, files):
    # Read xml file
    tree = ET.parse(pairs_file)
    root = tree.getroot()

    reports = root.findall("Report")

    report_pairs = {}
    for r in reports:
        pairs = []
        for p in r.findall("Pair"):
            pairs.append(
                {
                    "char_span_start": f'{p.attrib["char_span_start"]}',
                    "char_span_end": f'{p.attrib["char_span_end"]}',
                    "tlinkID": p.attrib["tlinkID"],
                    "fromID": p.attrib["fromID"],
                    "fromText": p.attrib["fromText"],
                    "fromStart": p.attrib["fromStart"],
                    "fromEnd": p.attrib["fromEnd"],
                    "toID": p.attrib["toID"],
                    "toText": p.attrib["toText"],
                    "toStart": p.attrib["toStart"],
                    "toEnd": p.attrib["toEnd"],
                }
            )
        report_pairs[r.attrib["filename"]] = pairs

    all_pairs = []
    for f in files:
        all_pairs.append(report_pairs[f])

    return all_pairs
